"""Read-only GA4 Lab API contract tests. Mock responses are TEST ONLY."""
import copy
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import lab_ga4_events as lab

TODAY = date.today().isoformat()


def response(rows=()):
    return {
        "dimensionHeaders": [{"name": s} for s in ("date", "eventName", "hostName")],
        "metricHeaders": [{"name": "eventCount"}],
        "rowCount": len(rows),
        "rows": [
            {"dimensionValues": [
                {"value": day.replace("-", "")},
                {"value": event},
                {"value": lab.HOSTNAME}],
             "metricValues": [{"value": str(count)}]}
            for day, event, count in rows
        ],
    }


class CommerceLabGA4Tests(unittest.TestCase):
    def test_api_query_restricts_hostname_and_events_with_numeric_property(self):
        data = response([(TODAY, "lab_page_view", 3), (TODAY, "lab_checkout_completed", 1)])
        with patch.object(lab, "access_token", return_value="CI_ONLY") as token, \
             patch.object(lab, "fetch_json", return_value=data) as fetch:
            snap = lab.collect_lab_events("123456789", TODAY, TODAY)
        token.assert_called_once()
        url, body, auth = fetch.call_args.args
        self.assertTrue(url.endswith("/properties/123456789:runReport"))
        self.assertEqual(auth, "CI_ONLY")
        self.assertEqual(body["metrics"], [{"name": "eventCount"}])
        self.assertEqual(body["dimensions"],
                         [{"name": "date"}, {"name": "eventName"}, {"name": "hostName"}])
        expressions = body["dimensionFilter"]["andGroup"]["expressions"]
        self.assertEqual(set(expressions[0]["filter"]["inListFilter"]["values"]), set(lab.EVENT_NAMES))
        self.assertEqual(expressions[1]["filter"]["stringFilter"]["value"], lab.HOSTNAME)
        self.assertEqual(snap["rows"][0]["event_count"], 3)
        self.assertEqual(snap["source"], lab.SOURCE)
        self.assertNotIn("purchase_revenue", json.dumps(snap))

    def test_require_id_before_credential_lookup_or_network(self):
        with patch.object(lab, "access_token") as token:
            for invalid in ("", "G-ABC123456", "abc", "1 or 1"):
                with self.assertRaisesRegex(ValueError, "numeric"):
                    lab.collect_lab_events(invalid, TODAY, TODAY)
            token.assert_not_called()

    def test_fake_purchase_and_foreign_host_are_rejected(self):
        bad = response([(TODAY, "purchase", 10)])
        with self.assertRaisesRegex(ValueError, "event/host"):
            lab.normalize_ga4_lab_response(bad)
        bad = response([(TODAY, "lab_add_to_cart", 1)])
        bad["rows"][0]["dimensionValues"][2]["value"] = "senanurcetin.github.io"
        with self.assertRaisesRegex(ValueError, "event/host"):
            lab.normalize_ga4_lab_response(bad)

    def test_missing_snapshot_is_not_zero_or_fabricated_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertIsNone(lab.load_lab_snapshot(Path(temp) / "not_found.json"))

    def test_invalid_row_counts_and_overlapping_grains_rejected(self):
        base = {
            "source": lab.SOURCE,
            "data_status": "actual_ga4_data_api_aggregate_not_live",
            "site_hostname": lab.HOSTNAME,
            "property_id": "123456789",
            "partial": False,
            "date_start": TODAY,
            "date_end": TODAY,
            "extracted_at_utc": datetime.now(timezone.utc).isoformat(),
            "rows": [
                {"date": TODAY, "event_name": "lab_add_to_cart", "event_count": 2},
            ],
        }
        self.assertEqual(len(lab.validate_lab_snapshot(base)), 1)
        for row in (
            {"date": TODAY, "event_name": "purchase", "event_count": 1},
            {"date": TODAY, "event_name": "lab_add_to_cart", "event_count": -1},
            {"date": TODAY, "event_name": "lab_add_to_cart", "event_count": "2"},
            {"date": TODAY, "event_name": "lab_add_to_cart", "event_count": True},
            {"date": TODAY, "event_name": "lab_add_to_cart", "event_count": 2, "revenue": 100},
        ):
            bad = copy.deepcopy(base)
            bad["rows"] = [row]
            with self.assertRaises(ValueError):
                lab.validate_lab_snapshot(bad)
        bad = copy.deepcopy(base)
        bad["rows"].append(dict(bad["rows"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            lab.validate_lab_snapshot(bad)
        bad = copy.deepcopy(base)
        bad["partial"] = True
        with self.assertRaisesRegex(ValueError, "Partial"):
            lab.validate_lab_snapshot(bad)

    def test_correct_empty_google_result_stays_empty_with_provenance(self):
        with patch.object(lab, "access_token", return_value="CI_ONLY"), \
             patch.object(lab, "fetch_json", return_value=response()):
            result = lab.collect_lab_events("123456789", TODAY, TODAY)
        self.assertEqual(result["rows"], [])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "lab.json"
            path.write_text(json.dumps(result), encoding="utf-8")
            rows, snap = lab.load_lab_snapshot(path)
            self.assertEqual(rows, [])
            self.assertEqual(snap["property_id"], "123456789")


if __name__ == "__main__":
    unittest.main()
