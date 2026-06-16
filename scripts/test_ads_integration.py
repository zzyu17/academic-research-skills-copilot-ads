#!/usr/bin/env python3
"""Integration tests for ADS API client against the real ADS API.

Requires ADS_API_TOKEN env var. All tests are skipped if the token is not set.
Uses known real papers (Planck 2018, Gaia EDR3) as ground-truth fixtures.

Part of: docs/superpowers/plans/2026-06-16-ads-workflow-test-plan.md
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from unittest import mock

from ads_client import AdsClient, AdsUnavailable  # noqa: E402

# ---------------------------------------------------------------------------
# Ground-truth fixtures (verified against real ADS API 2026-06-16)
# ---------------------------------------------------------------------------
PLANCK_BIBCODE = "2020A&A...641A...6P"
PLANCK_TITLE = "Planck 2018 results. VI. Cosmological parameters"
PLANCK_YEAR = 2020

GAIA_BIBCODE = "2021A&A...649A...5F"
GAIA_TITLE = "Gaia Early Data Release 3. Catalogue validation"
GAIA_YEAR = 2021

# ---------------------------------------------------------------------------
# Skip decorator
# ---------------------------------------------------------------------------
_ads_token = os.environ.get("ADS_API_TOKEN", "")
requires_token = unittest.skipIf(
    not _ads_token,
    "ADS_API_TOKEN not set — skipping real-API integration test",
)


class RealBibcodeLookupTest(unittest.TestCase):
    """Real ADS API bibcode_lookup tests."""

    @requires_token
    def test_bibcode_hit_with_correct_title(self):
        """Known bibcode + correct title -> returns entry with matching fields."""
        client = AdsClient()
        result = client.bibcode_lookup(PLANCK_BIBCODE, PLANCK_TITLE)
        self.assertIsNotNone(result, "Planck bibcode should resolve with correct title")
        self.assertEqual(result["bibcode"], PLANCK_BIBCODE)
        self.assertEqual(result["year"], PLANCK_YEAR)
        self.assertIn("Planck", result["title"])

    @requires_token
    def test_bibcode_mismatch_wrong_title(self):
        """Known bibcode + completely unrelated title -> BIBCODE_MISMATCH -> None."""
        client = AdsClient()
        result = client.bibcode_lookup(
            PLANCK_BIBCODE, "Completely Unrelated Paper About Galaxy Morphology"
        )
        self.assertIsNone(result, "BIBCODE_MISMATCH should return None")

    @requires_token
    def test_nonexistent_bibcode_returns_none(self):
        """Fake bibcode -> empty docs -> None."""
        client = AdsClient()
        result = client.bibcode_lookup("9999ZZZZ...999Z", "Anything")
        self.assertIsNone(result, "Fake bibcode should return None")


class RealTitleSearchTest(unittest.TestCase):
    """Real ADS API title_search tests."""

    @requires_token
    def test_title_search_match(self):
        """Known paper title -> returns entry with bibcode."""
        client = AdsClient()
        result = client.title_search(PLANCK_TITLE)
        self.assertIsNotNone(result, "Planck title should resolve in ADS")
        self.assertEqual(result["bibcode"], PLANCK_BIBCODE)
        self.assertEqual(result["year"], PLANCK_YEAR)

    @requires_token
    def test_title_search_with_year_param(self):
        """Title search with year parameter returns paper with matching year."""
        client = AdsClient()
        result = client.title_search(PLANCK_TITLE, year=PLANCK_YEAR)
        self.assertIsNotNone(result)
        self.assertEqual(result["year"], PLANCK_YEAR,
                         f"Year should be {PLANCK_YEAR} when year param is set")

    @requires_token
    def test_title_search_no_match(self):
        """Gibberish title -> None."""
        client = AdsClient()
        result = client.title_search(
            "XyzzyFlibbertigibbetNonExistentPaperTitle42"
        )
        self.assertIsNone(result, "Gibberish title should return None")


class RealContaminationSignalsTest(unittest.TestCase):
    """Test build_signals_object with real AdsClient."""

    def _s2_client(self):
        """Return a mock S2 client (required arg; ADS test doesn't use it)."""
        s2 = mock.MagicMock()
        s2.lookup.return_value = {"matched": True}
        return s2

    @requires_token
    def test_build_signals_with_real_ads_hit(self):
        """Real astronomy entry with valid bibcode -> ads_unmatched=False."""
        from contamination_signals import build_signals_object  # noqa: E402

        ads = AdsClient()
        entry = {
            "title": PLANCK_TITLE,
            "bibcode": PLANCK_BIBCODE,
            "obtained_via": "zotero-bbt-export",
            "year": PLANCK_YEAR,
            "venue": "Astronomy & Astrophysics",
            "doi": "10.1051/0004-6361/201833910",
            "arxiv_id": "1807.06209",
        }
        result = build_signals_object(entry, self._s2_client(), ads_client=ads)
        self.assertIs(result["ads_unmatched"], False,
                      "Planck paper should match in ADS -> ads_unmatched=False")

    @requires_token
    def test_build_signals_with_ads_no_match(self):
        """Entry with fake bibcode + nonexistent title -> ads_unmatched=True."""
        from contamination_signals import build_signals_object  # noqa: E402

        ads = AdsClient()
        entry = {
            "title": "XyzzyFlibbertigibbetNonExistentPaperTitle42",
            "bibcode": "9999ZZZZ...999Z",
            "obtained_via": "folder-scan",
            "year": 2025,
            "venue": "Fake Journal",
        }
        result = build_signals_object(entry, self._s2_client(), ads_client=ads)
        self.assertIs(result["ads_unmatched"], True,
                      "Fake entry should not match in ADS -> ads_unmatched=True")

    @requires_token
    def test_build_signals_no_bibcode_skips(self):
        """Entry without bibcode -> ads_unmatched field omitted."""
        from contamination_signals import build_signals_object  # noqa: E402

        ads = AdsClient()
        entry = {
            "title": PLANCK_TITLE,
            "obtained_via": "zotero-bbt-export",
            "year": PLANCK_YEAR,
            "venue": "Astronomy & Astrophysics",
        }
        result = build_signals_object(entry, self._s2_client(), ads_client=ads)
        self.assertNotIn("ads_unmatched", result,
                         "No bibcode -> ads_unmatched should be omitted")


class RealAdsDegradationTest(unittest.TestCase):
    """Test degradation behavior with real API conditions."""

    def test_missing_token_raises_ads_unavailable(self):
        """Without ADS_API_TOKEN, AdsClient raises AdsUnavailable on first call."""
        with mock.patch.dict("os.environ", {}, clear=True):
            client = AdsClient()
            with self.assertRaises(AdsUnavailable):
                client.bibcode_lookup(PLANCK_BIBCODE, PLANCK_TITLE)


if __name__ == "__main__":
    unittest.main()
