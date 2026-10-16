"""Source-isolated read-only data loader and KPI contracts for NEXUS Google dashboard.

Consumes only CSVs produced by scripts/google_measurement_marts.py.
No fixture fallback; it never joins disparate Google properties or commerce marts.
"""
from __future__ import annotations

from collections import defaultdict
import csv
from datetime import date, datetime
import json
import math
from pathlib import Path


SCHEMA = {
    "ga4": {
        "filename": "ga4_channel_daily.csv",
        "source_system": "ga4_data_api",
        "required": (
            "source_system", "property_id", "date", "ga4_session_channel_group",
            "sessions", "engaged_sessions", "active_users", "ecommerce_purchases",
            "purchase_revenue_property_currency", "extracted_at_utc",
        ),
    },
    "gsc": {
        "filename": "gsc_device_daily.csv",
        "source_system": "gsc_search_analytics_api",
        "required": (
            "source_system", "site_property", "date", "device",
            "clicks", "impressions", "ctr_ratio", "average_position", "extracted_at_utc",
        ),
    },
    "pagespeed": {
        "filename": "pagespeed_lab_audits.csv",
        "source_system": "pagespeed_insights_api",
        "required": (
            "source_system", "url", "strategy", "extracted_at_utc",
            "performance_score", "accessibility_score", "best_practices_score",
            "seo_score", "lab_fcp_ms", "lab_lcp_ms", "lab_speed_index_ms",
            "lab_total_blocking_time_ms", "lab_cls",
        ),
    },
}


def load_bundle(root: Path) -> tuple[dict[str, list[dict]], dict]:
    """Return isolated source tables; throw rather than presenting invented metrics."""
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("Validated snapshot manifest not found. Run google_measurement_marts.py first.")
    with manifest_path.open(encoding="utf-8") as stream:
        manifest = json.load(stream)
    if manifest.get("schema_version") != 1:
        raise ValueError("Google measurement mart contract version is unsupported")
    if manifest.get("data_status") != "actual_api_snapshots_not_live_feed":
        raise ValueError("Unverified or demo data manifest rejected")
    if int(manifest.get("partial_snapshot_count", 0)) > 0:
        raise ValueError("Partial source extraction rejected for dashboard publication")
    tables = {}
    for key, spec in SCHEMA.items():
        path = root / spec["filename"]
        if not path.is_file():
            raise FileNotFoundError(f"Required source export missing: {path.name}")
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != spec["required"]:
                raise ValueError(f"{path.name}: unexpected or missing column contract")
            records = list(reader)
        if any(row["source_system"] != spec["source_system"] for row in records):
            raise ValueError(f"{path.name}: source_system does not match file contract")
        expected_count = manifest.get("source_summary", {}).get(spec["source_system"], {}).get("rows")
        if expected_count is None or int(expected_count) != len(records):
            raise ValueError(f"{path.name}: row count differs from manifest")
        tables[key] = records
    return tables, manifest


def nonnegative(value: str, key: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key}: invalid numeric value") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{key}: negative or non-finite value")
    return number


def kpis_ga4(rows: list[dict]) -> dict:
    """Only additive session/purchase measures. No summation of active_users."""
    sessions = sum(nonnegative(r["sessions"], "sessions") for r in rows)
    engaged = sum(nonnegative(r["engaged_sessions"], "engaged_sessions") for r in rows)
    purchases = sum(nonnegative(r["ecommerce_purchases"], "ecommerce_purchases") for r in rows)
    revenue = sum(float(r["purchase_revenue_property_currency"]) for r in rows)
    if engaged > sessions:
        raise ValueError("Aggregate engaged sessions exceeds sessions")
    if not math.isfinite(revenue):
        raise ValueError("Non-finite GA4 purchase revenue")
    return {
        "sessions": round(sessions),
        "engaged_sessions": round(engaged),
        "engagement_rate": engaged / sessions if sessions else None,
        "ecommerce_purchases": round(purchases),
        "purchase_revenue_in_property_currency": revenue,
        "active_users_not_aggregated": True,
    }


def kpis_gsc(rows: list[dict]) -> dict:
    """Aggregate rates by their denominators; never average daily percentages."""
    clicks = sum(nonnegative(r["clicks"], "clicks") for r in rows)
    impressions = sum(nonnegative(r["impressions"], "impressions") for r in rows)
    if clicks > impressions:
        raise ValueError("GSC clicks cannot exceed impressions")
    weighted = sum(
        nonnegative(r["average_position"], "average_position")
        * nonnegative(r["impressions"], "impressions") for r in rows
    )
    return {
        "clicks": round(clicks),
        "impressions": round(impressions),
        "ctr": clicks / impressions if impressions else None,
        "impression_weighted_position": weighted / impressions if impressions else None,
    }


def latest_pagespeed(rows: list[dict]) -> list[dict]:
    """One latest Lighthouse lab run per (URL, device), not field CrUX results."""
    selected = {}
    for row in rows:
        if row["strategy"] not in ("mobile", "desktop"):
            raise ValueError("Unexpected PageSpeed strategy")
        try:
            timestamp = datetime.fromisoformat(row["extracted_at_utc"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Bad PageSpeed extraction timestamp") from exc
        if timestamp.tzinfo is None:
            raise ValueError("PageSpeed extracted_at must be timezone-aware")
        key = (row["url"], row["strategy"])
        current = selected.get(key)
        if current is None or timestamp > current[0]:
            selected[key] = (timestamp, row)
    return [record[1] for _, record in sorted(selected.items())]


def filter_dates(rows: list[dict], start: date, end: date) -> list[dict]:
    if start > end:
        raise ValueError("Date interval is reversed")
    return [row for row in rows if start.isoformat() <= row["date"] <= end.isoformat()]
