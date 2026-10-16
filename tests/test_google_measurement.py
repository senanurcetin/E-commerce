"""Offline, credential-free regression tests for the Google measurement integration."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import google_measurement as gm


class GoogleMeasurementTests(unittest.TestCase):
    def test_validate_dates(self):
        gm.validate_dates("2026-01-01", "2026-01-31")
        with self.assertRaises(ValueError):
            gm.validate_dates("2026-02-01", "2026-01-01")
        with self.assertRaises(ValueError):
            gm.validate_dates("2026-99-01", "2026-01-01")

    def test_ga4_normalization(self):
        raw = {
            "dimensionHeaders": [
                {"name": "date"}, {"name": "sessionDefaultChannelGroup"}
            ],
            "metricHeaders": [{"name": n} for n in (
                "sessions", "engagedSessions", "activeUsers",
                "ecommercePurchases", "purchaseRevenue"
            )],
            "rows": [{
                "dimensionValues": [{"value": "20261001"}, {"value": "Organic Search"}],
                "metricValues": [{"value": n} for n in ("10", "8", "9", "2", "99.55")],
            }],
        }
        output = gm.normalize_ga4(raw)
        self.assertEqual(output[0]["date"], "2026-10-01")
        self.assertEqual(output[0]["sessions"], 10)
        self.assertEqual(output[0]["ecommerce_purchases"], 2)
        self.assertEqual(output[0]["purchase_revenue_property_currency"], 99.55)
        self.assertNotIn("user_id", output[0])

    def test_ga4_schema_drift_rejected(self):
        with self.assertRaisesRegex(ValueError, "schema mismatch"):
            gm.normalize_ga4({"dimensionHeaders": [{"name": "other"}]})

    def test_ga4_pagination_and_provenance(self):
        header = {
            "dimensionHeaders": [{"name": "date"}, {"name": "sessionDefaultChannelGroup"}],
            "metricHeaders": [{"name": n} for n in (
                "sessions", "engagedSessions", "activeUsers",
                "ecommercePurchases", "purchaseRevenue"
            )],
            "rows": [],
            "rowCount": "0",
        }
        with patch.dict(gm.os.environ, {"GA4_PROPERTY_ID": "123"}), \
             patch.object(gm, "access_token", return_value="test-token"), \
             patch.object(gm, "fetch_json", return_value=header) as fetch:
            response = gm.collect_ga4("2026-10-01", "2026-10-02")
        self.assertEqual(response["source"], "ga4_data_api")
        self.assertEqual(response["rows"], [])
        self.assertFalse(response["partial"])
        self.assertTrue(fetch.called)
        self.assertIn("properties/123", fetch.call_args.args[0])

    def test_gsc_normalization(self):
        raw = {"rows": [
            {"keys": ["2026-10-01", "MOBILE"], "clicks": 5,
             "impressions": 100, "ctr": .05, "position": 4.2},
        ]}
        result = gm.normalize_gsc(raw)
        self.assertEqual(result[0]["device"], "MOBILE")
        self.assertEqual(result[0]["ctr_ratio"], .05)
        self.assertNotIn("query", result[0])
        with self.assertRaisesRegex(ValueError, "schema mismatch"):
            gm.normalize_gsc({"rows": [{"keys": ["2026-10-01"]}]})

    def test_gsc_scoped_property_read_only(self):
        with patch.dict(gm.os.environ, {"GSC_SITE_URL": "sc-domain:example.com"}), \
             patch.object(gm, "access_token", return_value="test-token"), \
             patch.object(gm, "fetch_json", return_value={"rows": []}) as fetch:
            result = gm.collect_gsc("2026-10-01", "2026-10-02")
        self.assertEqual(result["rows"], [])
        self.assertIn("sc-domain%3Aexample.com", fetch.call_args.args[0])
        self.assertEqual(fetch.call_args.args[1]["dimensions"], ["date", "device"])

    def test_pagespeed_lab_not_field(self):
        result = gm.normalize_pagespeed({
            "lighthouseResult": {
                "categories": {"performance": {"score": .93}},
                "audits": {"largest-contentful-paint": {"numericValue": 2200}},
            }
        })
        self.assertEqual(result["lighthouse_scores_0_to_100"]["performance"], 93)
        self.assertEqual(result["lab_metrics"]["largest-contentful-paint"], 2200)
        self.assertEqual(result["field_data"], "not_collected_use_crux_api")
        with self.assertRaisesRegex(ValueError, "public HTTPS"):
            gm.collect_pagespeed("http://localhost", "mobile")

    def test_snapshot_gitignored_location(self):
        with tempfile.TemporaryDirectory() as root:
            output = gm.save_snapshot({
                "source": "ga4_data_api",
                "date_start": "2026-10-01",
                "rows": [{"sessions": 10}],
            }, Path(root))
            saved = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(saved["rows"][0]["sessions"], 10)
            self.assertIn("fetched_at_utc", saved)
            self.assertEqual(output.parent, Path(root))


if __name__ == "__main__":
    unittest.main()
