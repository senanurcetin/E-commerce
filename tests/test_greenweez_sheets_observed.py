"""CI-only source-sheet samples. Never used as business metrics."""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from scripts.greenweez_sheets_observed import (
    SOURCE, DATA_STATUS, validate_observed, load_observed,
)


def evidence():
    return {
        "schema_version": 1,
        "source_system": SOURCE,
        "data_status": DATA_STATUS,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_sheets": ["Media at Greenweez - orders", "Media at Greenweez - campaigns"],
        "row_counts": {"orders": 3, "campaigns": 2},
        "daily_orders": [
            {"date": "2021-08-01", "order_rows": 3, "distinct_order_ids": 2,
             "missing_order_ids": 1, "turnover_as_stored": 99.2},
        ],
        "daily_campaigns": [
            {"date": "2021-08-01", "paid_source": "facebook", "campaign_rows": 1,
             "cost_as_stored": 7.5, "impressions": 50, "clicks": 10},
            {"date": "2021-08-01", "paid_source": "adwords", "campaign_rows": 1,
             "cost_as_stored": 4.0, "impressions": 30, "clicks": 5},
        ],
    }


class GreenweezSourceSheetsTests(unittest.TestCase):
    def test_valid_aggregate_contract_only_and_no_raw_ids(self):
        item = evidence()
        validated = validate_observed(item)
        self.assertEqual(validated["row_counts"]["orders"], 3)
        self.assertEqual([x["paid_source"] for x in validated["daily_campaigns"]],
                         ["adwords", "facebook"])
        serialized = json.dumps(validated)
        for field in ('"orders_id"', '"campaign_key"', '"campaign_name"', '"email"'):
            self.assertNotIn(field, serialized)

    def test_missing_is_not_source_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(load_observed(Path(folder) / "missing.json"))

    def test_source_cannot_self_certify_business_data(self):
        for field, fake in (("source_system", "ga4_api"),
                            ("data_status", "verified_actual"),
                            ("schema_version", 99)):
            item = evidence()
            item[field] = fake
            with self.assertRaises(ValueError):
                validate_observed(item)

    def test_reject_identifiers_and_incorrect_aggregation(self):
        for mutation in ("order_id", "extra_col", "daily", "count", "duplicate", "future"):
            item = evidence()
            if mutation == "order_id":
                item["daily_orders"][0]["orders_id"] = 1001
            if mutation == "extra_col":
                item["daily_campaigns"][0]["campaign_name"] = "sensitive campaign name"
            if mutation == "daily":
                item["daily_orders"][0]["date"] = "not a day"
            if mutation == "count":
                item["row_counts"]["campaigns"] = 3
            if mutation == "duplicate":
                item["daily_campaigns"].append(dict(item["daily_campaigns"][0]))
                item["row_counts"]["campaigns"] = 3
            if mutation == "future":
                item["observed_at_utc"] = "2030-10-01T00:00:00+00:00"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_observed(item)

    def test_failed_worksheet_is_rejected_without_export(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text('{"source_system":"unknown","rows":[{"email":"x"}]}')
            with self.assertRaisesRegex(ValueError, "Rejected Greenweez"):
                load_observed(path)

    def test_source_cost_is_not_attributed_revenue(self):
        item = validate_observed(evidence())
        self.assertEqual({x["paid_source"] for x in item["daily_campaigns"]},
                         {"adwords", "facebook"})
        self.assertNotIn("roas", json.dumps(item))
        self.assertNotIn("purchase", json.dumps(item))
        self.assertNotIn("revenue", json.dumps(item))


if __name__ == "__main__":
    unittest.main()
