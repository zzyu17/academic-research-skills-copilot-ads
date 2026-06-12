# ADS API Verification Protocol

**Status**: v3.11 ADS
**Used by**: `bibliography_agent`, `source_verification_agent`, `integrity_verification_agent`
**API base**: `https://api.adsabs.harvard.edu/v1/search/query`
**Rate limit**: 5000 req/day (with API token)
**Auth env var**: `ADS_API_TOKEN` (required — ADS does not support anonymous access)

---

## Purpose

Adds a fifth bibliographic-index lookup to the cross-index triangulation surface (S2 + OpenAlex + Crossref + arXiv + ADS) per `docs/superpowers/specs/2026-06-11-ads-integration-design.md`. ADS (SAO/NASA Astrophysics Data System) is the primary bibliographic index for astronomy and astrophysics — it is the source of truth for bibcodes and provides the most comprehensive index of astronomical literature.

Mirrors the structure of `arxiv_api_protocol.md` and `crossref_api_protocol.md`.

## Response format

The ADS query API returns **JSON**. A match yields a `{"response": {"docs": [...]}}` envelope; a miss yields `{"response": {"docs": []}}` (not a 404). Per-document fields the client reads:

- `title` — (list of strings, joined by space)
- `bibcode` — ADS canonical bibcode (e.g., `2024ApJ...967..123C`)
- `year` — publication year (int or string)
- `doi` — DOI if available
- `pub` — publication name
- `author` — author list

## Query Patterns

### Pattern 1: Bibcode Lookup with Title Cross-Check (primary when a bibcode is available)

```
GET /search/query?q=bibcode:"{bibcode}"&fl=title,bibcode,author,year,doi,pub&rows=5
```

**Matching rule (mirrors the arXiv ID_MISMATCH pattern):** Bibcode lookup hits are gated by a 0.70 title cross-check (same SequenceMatcher threshold as the sibling clients). If the resolved entry's title is below threshold → BIBCODE_MISMATCH, return None, fall through to title search. An empty docs array (non-existent bibcode) is a miss → None.

### Pattern 2: Title Search (fallback on bibcode-miss / BIBCODE_MISMATCH)

```
GET /search/query?q=title:"{title}"&fl=title,bibcode,author,year,doi,pub&rows=5
```

**Matching rule:** similarity >= 0.70. When multiple candidates pass, prefer the matching-year tiebreaker via a +0.05 score bonus.

## `ads_unmatched` derivation

`true` if and only if the citation **has a bibcode** AND the bibcode lookup either returns an empty docs array (miss) or misses the title cross-check, AND the title-search fallback returns no match meeting threshold.

A citation with **no bibcode** is `skipped` (not `unmatched`) — the resolver does not run and the caller omits `ads_unmatched` (absent ≠ false, #331 pattern). ADS applicability is bibcode-gated: a title-only miss against ADS for a non-astronomy work is a coverage gap, not non-existence evidence.

## Degradation handling

| Condition | Action |
|---|---|
| Docs array empty | Treat as miss — caller falls through to title search / reports unmatched. NOT a degradation. |
| HTTP 401 (invalid token) | Raise `AdsUnavailable` immediately. |
| HTTP 429 (rate limit) | Back off 2 seconds, retry up to 3 times. After exhaustion, raise `AdsUnavailable`. |
| HTTP 5xx | Raise `AdsUnavailable` immediately (no retry). |
| Network timeout (30s default) / URLError | Raise `AdsUnavailable`. |
| Malformed JSON body | Raise `AdsUnavailable`. |
| `ADS_API_TOKEN` not set | Raise `AdsUnavailable` immediately on first call. |
| `AdsUnavailable` raised | Caller MUST omit `ads_unmatched` from the entry (absent != false). Other indexes proceed independently. |

## ADS-specific notes

- **Applicability is bibcode-gated.** A citation with no bibcode is only checked by title search; the unified summary treats ADS as `skipped` (not `unmatched`) for non-astronomy published work.
- **Auth is mandatory.** Unlike S2 (optional key) or arXiv (anonymous), ADS requires `ADS_API_TOKEN` for all API access. Get one free at https://ui.adsabs.harvard.edu/user/settings/token.
- **JSON, not XML.** Mirrors OpenAlex/Crossref/S2 clients structurally; the only divergence from the arXiv client.

## Client implementation

See `scripts/ads_client.py`. Class `AdsClient` exposes `bibcode_lookup(bibcode, expected_title)` and `title_search(title, year=None)`. Both return `dict | None`. Both raise `AdsUnavailable` on degradation per the table above.

## Cross-references

- Spec: `docs/superpowers/specs/2026-06-11-ads-integration-design.md`
- Mirror template: `deep-research/references/arxiv_api_protocol.md`
- Sibling protocols: `deep-research/references/semantic_scholar_api_protocol.md`, `deep-research/references/openalex_api_protocol.md`, `deep-research/references/crossref_api_protocol.md`
