"""No-network regression tests for Greenweez Google Sheets linkage coverage."""
from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from scripts import audit_sheet_campaign_links as gw


ORDERS = [
    list(gw.ORDER_HEADER),
    [44410, "1001", 1, "33.00€", 1, "Paid", "Facebook", "fb_1", "Campaign A"],
    [44411, "1002", 1, "25,50€", 1, "Paid", "Facebook", "fb_1", "Campaign A"],
    [44410, "1003", 0, "15.00€", 0, "Organic", "Organic", "", ""],
    [44410, "1004", 0, "22€", 1, "Paid", "Unknown", "not_spent", ""],
]

CAMPAIGN_HEADERS = list(gw.CAMPAIGN_HEADER)


def campaign_tab(source):
    key = "fb_1" if source == "facebook" else f"{source}_unknown"
    return [
        CAMPAIGN_HEADERS,
        ["2021-08-02", key, source, "Campaign A", "10€", "100", "8"],
    ]


class GreenweezSheetLinkageTests(unittest.TestCase):
    def test_normalize_date_serial_and_text(self):
        self.assertEqual(gw.sheet_date(44410), "2021-08-02")
        self.assertEqual(gw.sheet_date("2021-08-02"), "2021-08-02")
        for value in [True, 44410.5, "2021-13-01", None]:
            with self.assertRaises(ValueError):
                gw.sheet_date(value)

    def test_money_without_unit_guesswork(self):
        for value, expected in [
            ("€25,50", "25.50"), ("25,50€", "25.50"), ("33.00€", "33.00"),
            ("120€", "120"), (15, "15"), ("1 234,56€", "1234.56"),
        ]:
            if expected is None:
                with self.assertRaises(ValueError):
                    gw.money(value, "turnover")
            else:
                self.assertEqual(gw.money(value, "turnover"), Decimal(expected))
        for value in [float("nan"), "1,200.30€", "usd10", None]:
            with self.assertRaises(ValueError):
                gw.money(value, "cost")

    def test_campaign_identifiers_are_not_coerced_or_guessed(self):
        self.assertEqual(gw.campaign_key(6209368149375), "6209368149375")
        self.assertEqual(gw.campaign_key("criteo_mid_funnel"), "criteo_mid_funnel")
        self.assertIsNone(gw.campaign_key(""))
        with self.assertRaises(ValueError):
            gw.campaign_key(float(2**54))

    def test_reject_duplicate_order_id(self):
        values = [ORDERS[0], ORDERS[1], ORDERS[1]]
        with self.assertRaisesRegex(ValueError, "duplicate order_id"):
            gw.parse_orders(values)

    def test_reject_source_schema_drift(self):
        bad = [list(gw.ORDER_HEADER), ORDERS[1]]
        bad[0][3] = "GMV_changed"
        with self.assertRaisesRegex(ValueError, "unexpected header"):
            gw.parse_orders(bad)

    def test_reject_duplicate_ad_campaign_day(self):
        tabs = {tab: campaign_tab(tab) for tab in gw.SOURCE_TABS}
        tabs["facebook"].append(tabs["facebook"][1])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            gw.parse_campaigns(tabs)

    def test_reject_bad_ad_counts(self):
        tabs = {tab: campaign_tab(tab) for tab in gw.SOURCE_TABS}
        tabs["facebook"][1][6] = "101"
        with self.assertRaisesRegex(ValueError, "clicks exceeds impressions"):
            gw.parse_campaigns(tabs)

    def test_exact_date_campaign_join_not_cross_date(self):
        orders = gw.parse_orders(ORDERS)
        campaigns = gw.parse_campaigns({
            tab: campaign_tab(tab) for tab in gw.SOURCE_TABS
        })
        sources, totals = gw.audit(orders, campaigns)
        self.assertEqual(totals["orders_total"], 4)
        self.assertEqual(totals["orders_without_campaign_key"], 1)
        self.assertEqual(totals["orders_with_campaign_key"], 3)
        self.assertEqual(totals["orders_matched_exact_day_key"], 1)
        self.assertEqual(totals["orders_unmatched_day_key"], 2)
        self.assertEqual(totals["match_rate_all_orders"], 0.25)
        self.assertEqual(totals["turnover_matched_eur"], Decimal("33"))
        fb = next(r for r in sources if r["source"] == "facebook")
        self.assertEqual(fb["matched_order_count"], 1)
        self.assertEqual(fb["spend_eur"], Decimal("10"))

    def test_cross_platform_collision_cannot_attribute(self):
        tabs = {tab: campaign_tab(tab) for tab in gw.SOURCE_TABS}
        tabs["adwords"][1][1] = "fb_1"
        campaign_rows = gw.parse_campaigns(tabs)
        _, summary = gw.audit(gw.parse_orders(ORDERS), campaign_rows)
        self.assertEqual(summary["orders_matched_exact_day_key"], 0)
        self.assertEqual(summary["orders_ambiguous_multiple_platforms"], 1)

    def test_only_aggregate_output_no_orders_or_keys(self):
        sources, summary = gw.audit(
            gw.parse_orders(ORDERS),
            gw.parse_campaigns({tab: campaign_tab(tab) for tab in gw.SOURCE_TABS}),
        )
        with tempfile.TemporaryDirectory() as root:
            target = Path(root)
            gw.write_report(target, sources, summary)
            manifest = json.loads((target / "coverage_manifest.json").read_text())
            csv_text = (target / "paid_source_linkage_audit.csv").read_text()
            self.assertFalse(manifest["attribution_validated"])
            self.assertFalse(manifest["roas_validated"])
            self.assertEqual(manifest["orders_matched_exact_day_key"], 1)
            self.assertNotIn("1001", csv_text)
            self.assertNotIn("fb_1", csv_text)
            self.assertNotIn("orders_id", csv_text)
            self.assertNotIn("1001", json.dumps(manifest))


if __name__ == "__main__":
    unittest.main()
