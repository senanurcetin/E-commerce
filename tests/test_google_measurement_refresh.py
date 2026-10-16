"""Credential-free tests for user-triggered real PageSpeed extraction pipeline."""
from __future__ import annotations

import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import google_dashboard_refresh as refresh


def real_api_shape():
    """Local mock response is only used inside tests, NEVER for dashboard content."""
    return {
        "source": "pagespeed_insights_api",
        "url": "https://public.example.org/",
        "strategy": "mobile",
        "lighthouse_scores_0_to_100": {
            "performance": 93, "accessibility": 98,
            "best-practices": 90, "seo": 99,
        },
        "lab_metrics": {
            "first-contentful-paint": 800,
            "largest-contentful-paint": 1800,
            "speed-index": 1200,
            "total-blocking-time": 75,
            "cumulative-layout-shift": 0.03,
        },
    }


class OnDemandPageSpeedTests(unittest.TestCase):
    def test_empty_google_accounts_allow_real_pagespeed_only(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "measurements" / "marts"
            with patch.object(refresh, "collect_pagespeed", return_value=real_api_shape()) as collector:
                outcome = refresh.audit_public_site(
                    " https://public.example.org/ ", "mobile", marts_dir=folder,
                )
            collector.assert_called_once_with("https://public.example.org/", "mobile")
            self.assertEqual(outcome["total_audits"], 1)
            self.assertTrue((folder / "manifest.json").is_file())
            for name in ("ga4_channel_daily.csv", "gsc_device_daily.csv"):
                with (folder / name).open(newline="", encoding="utf-8") as stream:
                    self.assertEqual(list(csv.DictReader(stream)), [], name)
            with (folder / "pagespeed_lab_audits.csv").open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["performance_score"], "93.0")
            self.assertEqual(rows[0]["url"], "https://public.example.org/")

    def test_empty_url_rejected_before_api_request(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(refresh, "collect_pagespeed") as call:
                with self.assertRaisesRegex(ValueError, "Enter a public"):
                    refresh.audit_public_site("  ", "mobile", marts_dir=Path(folder))
                with self.assertRaisesRegex(ValueError, "https"):
                    refresh.audit_public_site("http://example.org", "desktop", marts_dir=Path(folder))
                with self.assertRaisesRegex(ValueError, "Device"):
                    refresh.audit_public_site("https://example.org/", "tablet", marts_dir=Path(folder))
                call.assert_not_called()

    def test_failed_google_report_does_not_create_false_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "marts"
            blank = real_api_shape()
            blank["lighthouse_scores_0_to_100"] = {
                "performance": None, "accessibility": None,
                "best-practices": None, "seo": None,
            }
            with patch.object(refresh, "collect_pagespeed", return_value=blank):
                with self.assertRaisesRegex(ValueError, "no Lighthouse scores"):
                    refresh.audit_public_site("https://public.example.org/", "mobile", marts_dir=folder)
            self.assertFalse(folder.exists())


if __name__ == "__main__":
    unittest.main()
