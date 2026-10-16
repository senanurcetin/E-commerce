"""Source-qualified, aggregate-only evidence from owned Greenweez Sheets.

This adapter reads ONLY an already-prepared local JSON summary of Google
Sheets values. Raw order/customer/campaign identifiers are never accepted in
the summary or displayed in the UI. The observed columns' financial semantics,
currency and original truthfulness remain UNVERIFIED.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
import math
from pathlib import Path

SOURCE = "greenweez_google_sheets_aggregate_observed"
DATA_STATUS = "source_observed_financial_semantics_unverified"
DEFAULT_PATH = Path("target/greenweez_bridge/google_sheets_observed.json")
ORDER_FIELDS = {"date", "order_rows", "distinct_order_ids", "missing_order_ids", "missing_turnover_rows", "turnover_as_stored"}
CAMPAIGN_FIELDS = {"date", "paid_source", "campaign_rows", "missing_cost_rows", "missing_impressions_rows", "missing_clicks_rows", "cost_as_stored", "impressions", "clicks"}
ALLOWED_SOURCES = {"adwords", "bing", "facebook", "criteo"}
COUNT_FIELDS = {"order_rows", "distinct_order_ids", "missing_order_ids", "missing_turnover_rows", "campaign_rows", "missing_cost_rows", "missing_impressions_rows", "missing_clicks_rows", "impressions", "clicks"}


def _day(value: object) -> str:
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("Greenweez observed date must be ISO YYYY-MM-DD")
    return date.fromisoformat(value).isoformat()


def _amount(value: object, field: str) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Invalid Greenweez observation: {field}")
    n = float(value)
    if not math.isfinite(n) or n < 0 or n > 2**53 - 1:
        raise ValueError(f"Nonfinite, negative or unsafe {field}")
    if field in COUNT_FIELDS:
        if not n.is_integer():
            raise ValueError(f"Noninteger {field}")
        return int(n)
    return n


def validate_observed(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != {
        "schema_version", "source_system", "data_status",
        "observed_at_utc", "source_sheets", "row_counts", "origin_coverage", "daily_orders", "daily_campaigns"
    }:
        raise ValueError("Unknown Greenweez source observation schema")
    if value["schema_version"] != 1 or value["source_system"] != SOURCE or value["data_status"] != DATA_STATUS:
        raise ValueError("Expected aggregate-only Greenweez Google Sheets observation")
    try:
        at = datetime.fromisoformat(value["observed_at_utc"].replace("Z", "+00:00"))
    except (ValueError, KeyError, AttributeError) as exc:
        raise ValueError("Invalid timestamp on source observation") from exc
    if at.tzinfo is None or at > datetime.now(timezone.utc):
        raise ValueError("Observation timestamp is invalid/future")
    if value["source_sheets"] != ["Media at Greenweez - orders", "Media at Greenweez - campaigns"]:
        raise ValueError("Greenweez sheet source names are not recognized")
    orders, campaigns = value["daily_orders"], value["daily_campaigns"]
    if not isinstance(orders, list) or not orders or not isinstance(campaigns, list):
        raise ValueError("Missing date-grained observations")
    order_dates = set()
    normalized_orders = []
    for row in orders:
        if not isinstance(row, dict) or set(row) != ORDER_FIELDS:
            raise ValueError("Invalid order observation fields; raw IDs are forbidden")
        day = _day(row["date"])
        if day in order_dates:
            raise ValueError("Duplicate Greenweez order daily date")
        order_dates.add(day)
        record = {"date": day}
        for field in ("order_rows", "distinct_order_ids", "missing_order_ids", "missing_turnover_rows", "turnover_as_stored"):
            record[field] = _amount(row[field], field)
        if record["missing_order_ids"] > record["order_rows"] or record["missing_turnover_rows"] > record["order_rows"]:
            raise ValueError("Missing data counters exceed source rows")
        if record["distinct_order_ids"] > record["order_rows"] - record["missing_order_ids"]:
            raise ValueError("Distinct known order IDs exceed rows with valid IDs")
        normalized_orders.append(record)

    campaign_grains = set()
    normalized_campaigns = []
    for row in campaigns:
        if not isinstance(row, dict) or set(row) != CAMPAIGN_FIELDS:
            raise ValueError("Invalid campaign observation fields; campaign names/keys are forbidden")
        day = _day(row["date"])
        source = row["paid_source"]
        if source not in ALLOWED_SOURCES:
            raise ValueError("Unexpected Greenweez campaign source")
        grain = day, source
        if grain in campaign_grains:
            raise ValueError("Duplicate campaign date/source grain")
        campaign_grains.add(grain)
        record = {"date": day, "paid_source": source}
        for field in ("campaign_rows", "missing_cost_rows", "missing_impressions_rows", "missing_clicks_rows", "cost_as_stored", "impressions", "clicks"):
            record[field] = _amount(row[field], field)
        if any(record[key] > record["campaign_rows"] for key in ("missing_cost_rows", "missing_impressions_rows", "missing_clicks_rows")):
            raise ValueError("Missing campaign values exceed source rows")
        if not (record["missing_clicks_rows"] or record["missing_impressions_rows"]) and record["clicks"] > record["impressions"]:
            raise ValueError("Campaign clicks exceed impressions")
        normalized_campaigns.append(record)

    counts = value["row_counts"]
    if not isinstance(counts, dict) or set(counts) != {"orders", "campaigns"}:
        raise ValueError("Invalid source worksheet row-count evidence")
    expected = {
        "orders": sum(row["order_rows"] for row in normalized_orders),
        "campaigns": sum(row["campaign_rows"] for row in normalized_campaigns),
    }
    if counts != expected:
        raise ValueError("Greenweez worksheets do not reconcile with daily aggregates")
    # The original Google Sheets source has is_ga=0/1 groups. For the owner's
    # observed August 2021 rows, missing turnover aligns exactly with is_ga=0.
    # Encode the cross-tab as independent source evidence, not a statement
    # about why the non-GA amount is unavailable.
    coverage = value["origin_coverage"]
    cover_fields = {"ga_rows", "non_ga_rows", "ga_missing_turnover",
                    "non_ga_missing_turnover"}
    if not isinstance(coverage, dict) or set(coverage) != cover_fields:
        raise ValueError("Missing is_ga / turnover coverage audit")
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0
           for v in coverage.values()):
        raise ValueError("Coverage values must be nonnegative integers")
    if coverage["ga_rows"] + coverage["non_ga_rows"] != counts["orders"]:
        raise ValueError("GA/non-GA source row coverage mismatch")
    if (coverage["ga_missing_turnover"] > coverage["ga_rows"]
            or coverage["non_ga_missing_turnover"] > coverage["non_ga_rows"]):
        raise ValueError("Origin missing turnover exceeds source rows")
    if (coverage["ga_missing_turnover"] + coverage["non_ga_missing_turnover"]
            != sum(row["missing_turnover_rows"] for row in normalized_orders)):
        raise ValueError("Missing turnover not reconciled across GA source classes")
    return {**value,
            "daily_orders": sorted(normalized_orders, key=lambda r: r["date"]),
            "daily_campaigns": sorted(normalized_campaigns, key=lambda r: (r["date"], r["paid_source"]))}


def load_observed(path: Path = DEFAULT_PATH) -> dict | None:
    if not path.is_file():
        return None
    try:
        return validate_observed(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        raise ValueError(f"Rejected Greenweez Google Sheets observations: {exc}") from exc
