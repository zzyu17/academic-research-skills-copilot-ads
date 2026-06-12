#!/usr/bin/env python3
"""Unit tests for ADS API client.

Tests bibcode lookup (hit/miss/mismatch), title search (match/no-match),
rate-limit retry, 5xx degradation, and missing token behavior.
Mirrors test structure from test_arxiv_client.py.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from ads_client import AdsClient, AdsUnavailable, _extract_title, _extract_year, _extract_bibcode, _doc_to_dict  # noqa: E402


class ExtractHelpersTest(unittest.TestCase):
    """Unit tests for ADS response field extraction helpers."""

    def test_extract_title_list(self):
        self.assertEqual(
            _extract_title({"title": ["A Study of Stars"]}),
            "A Study of Stars",
        )

    def test_extract_title_empty(self):
        self.assertEqual(_extract_title({}), "")
        self.assertEqual(_extract_title({"title": []}), "")

    def test_extract_title_multi(self):
        self.assertEqual(
            _extract_title({"title": ["Part One", "Part Two"]}),
            "Part One Part Two",
        )

    def test_extract_year_int(self):
        self.assertEqual(_extract_year({"year": 2024}), 2024)

    def test_extract_year_str(self):
        self.assertEqual(_extract_year({"year": "2024"}), 2024)

    def test_extract_year_missing(self):
        self.assertIsNone(_extract_year({}))

    def test_extract_bibcode(self):
        self.assertEqual(
            _extract_bibcode({"bibcode": "2024ApJ...967..123C"}),
            "2024ApJ...967..123C",
        )

    def test_doc_to_dict(self):
        doc = {
            "title": ["Test Paper"],
            "year": 2024,
            "bibcode": "2024Test..001A",
        }
        result = _doc_to_dict(doc)
        self.assertEqual(result, {
            "title": "Test Paper",
            "year": 2024,
            "bibcode": "2024Test..001A",
        })


class BibcodeLookupTest(unittest.TestCase):
    """Tests for AdsClient.bibcode_lookup."""

    def _mock_urlopen(self, docs, code=200):
        """Return a mock urlopen that returns the given docs as an ADS JSON response."""
        response_data = json.dumps({
            "response": {"docs": docs},
        }).encode("utf-8")
        mock = MagicMock()
        mock.getcode.return_value = code
        mock.read.return_value = response_data
        mock.__enter__.return_value = mock
        return mock

    @patch.dict("os.environ", {"ADS_API_TOKEN": "test-token"})
    def test_bibcode_hit_with_title_match(self):
        client = AdsClient()
        docs = [{"title": ["Galaxy Formation in Clusters"], "year": 2024, "bibcode": "2024ApJ...967..123C"}]
        with patch("urllib.request.urlopen", return_value=self._mock_urlopen(docs)):
            result = client.bibcode_lookup("2024ApJ...967..123C", "Galaxy Formation in Clusters")
        self.assertIsNotNone(result)
        self.assertEqual(result["bibcode"], "2024ApJ...967..123C")
        self.assertEqual(result["title"], "Galaxy Formation in Clusters")

    @patch.dict("os.environ", {"ADS_API_TOKEN": "test-token"})
    def test_bibcode_hit_title_below_threshold(self):
        """Title cross-check fails -> BIBCODE_MISMATCH -> None."""
        client = AdsClient()
        docs = [{"title": ["Completely Unrelated Paper"], "year": 2024, "bibcode": "2024ApJ...967..123C"}]
        with patch("urllib.request.urlopen", return_value=self._mock_urlopen(docs)):
            result = client.bibcode_lookup("2024ApJ...967..123C", "Galaxy Formation in Clusters")
        self.assertIsNone(result)

    @patch.dict("os.environ", {"ADS_API_TOKEN": "test-token"})
    def test_bibcode_miss_empty_docs(self):
        """No docs returned -> miss -> None."""
        client = AdsClient()
        with patch("urllib.request.urlopen", return_value=self._mock_urlopen([])):
            result = client.bibcode_lookup("2024ApJ...967..123C", "Galaxy Formation")
        self.assertIsNone(result)


class TitleSearchTest(unittest.TestCase):
    """Tests for AdsClient.title_search."""

    def _mock_urlopen(self, docs, code=200):
        response_data = json.dumps({
            "response": {"docs": docs},
        }).encode("utf-8")
        mock = MagicMock()
        mock.getcode.return_value = code
        mock.read.return_value = response_data
        mock.__enter__.return_value = mock
        return mock

    @patch.dict("os.environ", {"ADS_API_TOKEN": "test-token"})
    def test_title_search_match(self):
        client = AdsClient()
        docs = [{"title": ["Galaxy Formation in Clusters"], "year": 2024, "bibcode": "2024ApJ...967..123C"}]
        with patch("urllib.request.urlopen", return_value=self._mock_urlopen(docs)):
            result = client.title_search("Galaxy Formation in Clusters")
        self.assertIsNotNone(result)
        self.assertEqual(result["bibcode"], "2024ApJ...967..123C")

    @patch.dict("os.environ", {"ADS_API_TOKEN": "test-token"})
    def test_title_search_year_tiebreaker(self):
        """When two candidates have similar title similarity, matching-year gets +0.05 and wins."""
        client = AdsClient()
        docs = [
            {"title": ["Galaxy Formation in Clusters"], "year": 2023, "bibcode": "2023ApJ...001A"},
            {"title": ["Galaxy Formation in Clusters"], "year": 2024, "bibcode": "2024ApJ...002B"},
        ]
        with patch("urllib.request.urlopen", return_value=self._mock_urlopen(docs)):
            result = client.title_search("Galaxy Formation in Clusters", year=2024)
        # Both have identical title strings (= exact match), so same similarity.
        # Year=2024 gets +0.05 bonus and wins the tie.
        self.assertIsNotNone(result)
        self.assertEqual(result["bibcode"], "2024ApJ...002B")

    @patch.dict("os.environ", {"ADS_API_TOKEN": "test-token"})
    def test_title_search_no_match(self):
        client = AdsClient()
        with patch("urllib.request.urlopen", return_value=self._mock_urlopen([])):
            result = client.title_search("Nonexistent Paper Title XYZ")
        self.assertIsNone(result)


class AdsClientErrorHandlingTest(unittest.TestCase):
    """Tests for error/degradation handling."""

    def test_missing_token_raises(self):
        """Without ADS_API_TOKEN, all operations raise AdsUnavailable."""
        with patch.dict("os.environ", {}, clear=True):
            client = AdsClient()
            with self.assertRaises(AdsUnavailable):
                client.bibcode_lookup("2024ApJ...001A", "Title")

    @patch.dict("os.environ", {"ADS_API_TOKEN": "test-token"})
    def test_http_429_retries_then_raises(self):
        """3 retries exhausted -> AdsUnavailable."""
        from urllib.error import HTTPError

        client = AdsClient()
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 429
        mock_resp.read.return_value = b"{}"
        with patch("urllib.request.urlopen", side_effect=HTTPError(
            "http://fake", 429, "Too Many Requests", {}, mock_resp
        )):
            with self.assertRaises(AdsUnavailable):
                client.bibcode_lookup("2024ApJ...001A", "Title")

    @patch.dict("os.environ", {"ADS_API_TOKEN": "test-token"})
    def test_http_5xx_raises_immediately(self):
        """5xx -> AdsUnavailable without retry."""
        from urllib.error import HTTPError

        client = AdsClient()
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 500
        mock_resp.read.return_value = b"{}"
        with patch("urllib.request.urlopen", side_effect=HTTPError(
            "http://fake", 500, "Internal Server Error", {}, mock_resp
        )):
            with self.assertRaises(AdsUnavailable):
                client.bibcode_lookup("2024ApJ...001A", "Title")


if __name__ == "__main__":
    unittest.main()
