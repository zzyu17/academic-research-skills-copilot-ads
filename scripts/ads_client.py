#!/usr/bin/env python3
"""Minimal SAO/NASA Astrophysics Data System (ADS) API client wrapper.

Implements the lookup contract documented at
`deep-research/references/ads_api_protocol.md`. Bibcode-first with
title cross-check (BIBCODE_MISMATCH pattern), title-similarity fallback,
429 -> 2s backoff x 3 retries, network/5xx -> AdsUnavailable. Mirrors
`arxiv_client.py` / `crossref_client.py` / `openalex_client.py` structure.

ADS-specific differences from the arXiv sibling:
  - The query API returns JSON, NOT Atom XML.
  - The exact-key endpoint is keyed by bibcode, not arXiv ID:
    `?q=bibcode:"{bibcode}"` for bibcode lookup,
    `?q=title:"{title}"` for the title fallback.
    The base is `https://api.adsabs.harvard.edu/v1/search/query`.
  - Auth is via `ADS_API_TOKEN` env var in `Authorization: Bearer` header.
    ADS does not support anonymous access.
  - Rate limit: 5000 req/day; parse `X-RateLimit-Remaining` header.
    Min interval is 0.2s (much faster than arXiv's 3s).

Delta: docs/superpowers/specs/2026-06-11-ads-integration-design.md
"""
from __future__ import annotations

import http.client
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# Dual-path import: see openalex_client.py comment.
try:
    from _text_similarity import (
        _BACKOFF_SECONDS,
        _MAX_RETRIES,
        _TITLE_SIMILARITY_THRESHOLD,
        _similarity,
    )
except ImportError:
    from scripts._text_similarity import (
        _BACKOFF_SECONDS,
        _MAX_RETRIES,
        _TITLE_SIMILARITY_THRESHOLD,
        _similarity,
    )


_API_BASE = "https://api.adsabs.harvard.edu/v1/search/query"

# ADS allows ~5000 req/day; 0.2s min interval is conservative.
_ADS_MIN_INTERVAL = 0.2


def _extract_title(doc: dict[str, Any]) -> str:
    """Extract title from an ADS JSON response document.
    The 'title' field is a list of strings; join with space."""
    titles = doc.get("title", [])
    return " ".join(titles) if titles else ""


def _extract_year(doc: dict[str, Any]) -> int | None:
    """Extract publication year from an ADS JSON response document."""
    year = doc.get("year")
    if isinstance(year, int):
        return year
    if isinstance(year, str) and year.isdigit():
        return int(year)
    return None


def _extract_bibcode(doc: dict[str, Any]) -> str:
    """Extract bibcode from an ADS JSON response document."""
    return doc.get("bibcode", "")


def _doc_to_dict(doc: dict[str, Any]) -> dict[str, Any]:
    """Project an ADS JSON response document into the dict shape callers consume."""
    return {
        "title": _extract_title(doc),
        "year": _extract_year(doc),
        "bibcode": _extract_bibcode(doc),
    }


class AdsUnavailable(Exception):
    """ADS API degraded -- caller MUST omit `ads_unmatched`."""


class AdsClient:
    """Production lookup-by-(bibcode-with-cross-check-then-title) client.

    Concurrency note: rate-limit pacing is per-instance.
    """

    def __init__(self) -> None:
        self._min_interval = _ADS_MIN_INTERVAL
        self._last_request_at: float | None = None
        self._user_agent = "ARS-v3.11"
        self._token = os.environ.get("ADS_API_TOKEN", "")

    def _throttle(self) -> None:
        if self._last_request_at is None:
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

    def _search(self, query: str, fields: str = "title,bibcode,author,year,doi,pub,identifier") -> list[dict[str, Any]]:
        """GET the /search/query endpoint and return the list of response
        'docs' (empty list when no results)."""
        if not self._token:
            raise AdsUnavailable("ADS_API_TOKEN not set")

        params = {
            "q": query,
            "fl": fields,
            "rows": "5",
        }
        url = _API_BASE + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={
            "User-Agent": self._user_agent,
            "Authorization": f"Bearer {self._token}",
        })

        self._throttle()
        self._last_request_at = time.monotonic()

        for attempt in range(_MAX_RETRIES + 1):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    try:
                        body = resp.read()
                        data = json.loads(body)
                    except (OSError, http.client.HTTPException, json.JSONDecodeError) as e:
                        raise AdsUnavailable(
                            f"ADS response read/parse failed: {e}"
                        ) from e

                    # ADS returns a "response" wrapper with "docs" array.
                    response = data.get("response", {})
                    return response.get("docs", [])
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < _MAX_RETRIES:
                    time.sleep(_BACKOFF_SECONDS)
                    self._last_request_at = time.monotonic()
                    continue
                # ADS may return 401 for invalid token.
                if e.code == 401:
                    raise AdsUnavailable("ADS API token invalid (HTTP 401)") from e
                raise AdsUnavailable(f"ADS HTTP {e.code}: {e.reason}") from e
            except (urllib.error.URLError, TimeoutError) as e:
                raise AdsUnavailable(f"ADS network error: {e}") from e

        raise AdsUnavailable("ADS rate limit exhausted after retries")

    def bibcode_lookup(
        self, bibcode: str, expected_title: str,
    ) -> dict[str, Any] | None:
        """Bibcode lookup with mandatory 0.70 title cross-check.

        Returns the projected entry dict if the bibcode resolves AND the title
        cross-check passes; None on empty results (miss) or BIBCODE_MISMATCH.
        """
        docs = self._search(f'bibcode:"{bibcode}"')
        if not docs:
            return None
        doc = docs[0]
        title = _extract_title(doc)
        if _similarity(title, expected_title) >= _TITLE_SIMILARITY_THRESHOLD:
            return _doc_to_dict(doc)
        return None  # BIBCODE_MISMATCH

    def title_search(
        self, title: str, year: int | None = None,
    ) -> dict[str, Any] | None:
        """Title search with 0.70 similarity threshold + matching-year tiebreaker.

        Returns the best matching projected entry dict, or None if no
        candidate meets the threshold.
        """
        docs = self._search(f'title:"{title}"')
        scored = []
        for cand in docs:
            cand_title = _extract_title(cand)
            sim = _similarity(cand_title, title)
            if sim < _TITLE_SIMILARITY_THRESHOLD:
                continue
            year_match = year is not None and _extract_year(cand) == year
            score = sim + (0.05 if year_match else 0.0)
            scored.append((cand, score))
        if not scored:
            return None
        scored.sort(key=lambda cand_score: -cand_score[1])
        return _doc_to_dict(scored[0][0])
