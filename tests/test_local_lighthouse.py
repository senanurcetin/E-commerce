"""No-network parsing checks for local Chrome Lighthouse reports."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.local_lighthouse import parse_lighthouse_report, load_lighthouse_reports


def report(device="mobile"):
    return {
        "lighthouseVersion": "12.8.2",
        "requestedUrl": "https://nexus-commerce-lab.vercel.app/",
        "finalDisplayedUrl": "https://nexus-commerce-lab.vercel.app/",
        "fetchTime": "2026-10-16T19:12:12.000Z",
        "configSettings": {"formFactor": device},
        "categories": {
            "performance": {"score": 0.91},
            "accessibility": {"score": 1},
            "best-practices": {"score": .86},
            "seo": {"score": .82},
        },
        "audits": {
            "first-contentful-paint": {"numericValue": 1200},
            "largest-contentful-paint": {"numericValue": 1700},
            "total-blocking-time": {"numericValue": 32},
            "speed-index": {"numericValue": 2200},
            "cumulative-layout-shift": {"numericValue": .03},
        },
    }


class LocalLighthouseTests(unittest.TestCase):
    def test_genuine_lhr_metadata_and_lab_metrics_only(self):
        x = parse_lighthouse_report(report())
        self.assertEqual(x["source_system"], "local_lighthouse_cli")
        self.assertTrue(x["lab_only"])
        self.assertEqual(x["device"], "mobile")
        self.assertEqual(x["scores"]["performance"], 91)
        self.assertEqual(x["lab_metrics"]["lcp_ms"], 1700)
        self.assertNotIn("ga4_sessions", x)
        self.assertNotIn("crux", x)

    def test_empty_folder_means_no_real_measurement(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(load_lighthouse_reports(Path(folder)), [])

    def test_unsupported_api_shape_and_missing_scores_rejected(self):
        with self.assertRaisesRegex(ValueError, "full Lighthouse CLI"):
            parse_lighthouse_report({"source": "pagespeed_insights_api", "performance": 100})
        missing = report()
        missing["categories"].pop("seo")
        with self.assertRaisesRegex(ValueError, "Missing Lighthouse score"):
            parse_lighthouse_report(missing)

    def test_reject_invalid_url_device_and_nonfinite_metrics(self):
        for mode in ("tablet", None):
            with self.assertRaises(ValueError):
                parse_lighthouse_report(report(device=mode))
        bad = report()
        bad["requestedUrl"] = "http://localhost/"
        with self.assertRaises(ValueError):
            parse_lighthouse_report(bad)
        bad = report()
        bad["audits"]["largest-contentful-paint"]["numericValue"] = float("nan")
        with self.assertRaisesRegex(ValueError, "invalid"):
            parse_lighthouse_report(bad)

    def test_local_scans_kept_separate_by_device(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            (p / "mobile.json").write_text(json.dumps(report("mobile")))
            (p / "desktop.json").write_text(json.dumps(report("desktop")))
            got = load_lighthouse_reports(p)
            self.assertEqual(len(got), 2)
            self.assertEqual({x["device"] for x in got}, {"mobile", "desktop"})

    def test_invalid_local_report_fails_instead_of_becoming_a_metric(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "invalid.json").write_text('{"demo":true}')
            with self.assertRaisesRegex(ValueError, "Not a full Lighthouse"):
                load_lighthouse_reports(Path(folder))


if __name__ == "__main__":
    unittest.main()
