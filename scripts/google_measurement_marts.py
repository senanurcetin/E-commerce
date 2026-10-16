"""Validate real Google measurement snapshots and export source-isolated CSV marts.

No network, cloud writes, synthetic fallback, or dependence on existing dbt facts.
Only accepted collector JSON files under --input-dir are processed.

Usage:
    python scripts/google_measurement_marts.py --input-dir target/google_measurement
    python scripts/google_measurement_marts.py --input-dir target/google_measurement --allow-partial
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
import json
import math
from pathlib import Path


PREFIXES = ("ga4_data_", "gsc_search_analytics_", "pagespeed_insights_")
OUTPUT_FIELDS = {
    "ga4_data_api": (
        "source_system", "property_id", "date", "ga4_session_channel_group",
        "sessions", "engaged_sessions", "active_users", "ecommerce_purchases",
        "purchase_revenue_property_currency", "extracted_at_utc",
    ),
    "gsc_search_analytics_api": (
        "source_system", "site_property", "date", "device", "clicks",
        "impressions", "ctr_ratio", "average_position", "extracted_at_utc",
    ),
    "pagespeed_insights_api": (
        "source_system", "url", "strategy", "extracted_at_utc",
        "performance_score", "accessibility_score", "best_practices_score",
        "seo_score", "lab_fcp_ms", "lab_lcp_ms", "lab_speed_index_ms",
        "lab_total_blocking_time_ms", "lab_cls",
    ),
}
OUTPUT_NAMES = {
    "ga4_data_api": "ga4_channel_daily.csv",
    "gsc_search_analytics_api": "gsc_device_daily.csv",
    "pagespeed_insights_api": "pagespeed_lab_audits.csv",
}
LAB_KEYS = {
    "lab_fcp_ms": "first-contentful-paint",
    "lab_lcp_ms": "largest-contentful-paint",
    "lab_speed_index_ms": "speed-index",
    "lab_total_blocking_time_ms": "total-blocking-time",
    "lab_cls": "cumulative-layout-shift",
}
SCORE_KEYS = {
    "performance_score": "performance",
    "accessibility_score": "accessibility",
    "best_practices_score": "best-practices",
    "seo_score": "seo",
}


def required(obj: dict, name: str):
    if name not in obj or obj[name] is None or obj[name] == "":
        raise ValueError(f"missing required field {name!r}")
    return obj[name]


def iso_date(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"date must be an ISO date string: {value!r}")
    try:
        parsed = date.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"invalid ISO date: {value!r}") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"noncanonical ISO date: {value!r}")
    return value


def timestamp(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("extracted_at must be a timezone-aware timestamp")
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid extracted_at timestamp") from exc
    if ts.tzinfo is None:
        raise ValueError("extracted_at timestamp must have a timezone")
    return ts.astimezone(timezone.utc).isoformat()


def metric(value, name: str, *, integer: bool = False, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: expected a numeric value")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name}: non-finite value")
    if integer and (not number.is_integer() or not float(-2**53) < number < float(2**53)):
        raise ValueError(f"{name}: invalid integer")
    if minimum is not None and number < minimum:
        raise ValueError(f"{name}: below minimum")
    if maximum is not None and number > maximum:
        raise ValueError(f"{name}: exceeds maximum")
    return int(number) if integer else number


def normalize_snapshot(snapshot: dict, *, allow_partial: bool = False) -> tuple[str, list[dict]]:
    source = required(snapshot, "source")
    if source not in OUTPUT_FIELDS:
        raise ValueError(f"unknown Google measurement source {source!r}")
    if snapshot.get("partial") is True and not allow_partial:
        raise ValueError(f"{source}: partial API extraction; use --allow-partial explicitly")
    extracted = timestamp(required(snapshot, "fetched_at_utc"))
    results: list[dict] = []
    if source in ("ga4_data_api", "gsc_search_analytics_api"):
        first = iso_date(required(snapshot, "date_start"))
        last = iso_date(required(snapshot, "date_end"))
        if first > last:
            raise ValueError("snapshot start date is after end date")
        raw_rows = required(snapshot, "rows") if "rows" not in snapshot else snapshot["rows"]
        if not isinstance(raw_rows, list):
            raise ValueError("rows must be a JSON array")
        if source == "ga4_data_api":
            identity = str(required(snapshot, "property_id"))
            if not identity.isdigit():
                raise ValueError("GA4 property ID must be numeric")
        else:
            identity = str(required(snapshot, "site_property"))
            if not identity.startswith(("sc-domain:", "https://", "http://")):
                raise ValueError("invalid GSC property identifier")
        for row in raw_rows:
            if not isinstance(row, dict):
                raise ValueError("source row must be a JSON object")
            day = iso_date(required(row, "date"))
            if not first <= day <= last:
                raise ValueError("row date lies outside snapshot period")
            if source == "ga4_data_api":
                output = {
                    "source_system": "ga4_data_api",
                    "property_id": identity,
                    "date": day,
                    "ga4_session_channel_group": str(required(row, "ga4_session_channel_group")),
                    "sessions": metric(required(row, "sessions"), "sessions", integer=True, minimum=0),
                    "engaged_sessions": metric(required(row, "engaged_sessions"), "engaged_sessions", integer=True, minimum=0),
                    "active_users": metric(required(row, "active_users"), "active_users", integer=True, minimum=0),
                    "ecommerce_purchases": metric(required(row, "ecommerce_purchases"), "ecommerce_purchases", integer=True, minimum=0),
                    "purchase_revenue_property_currency": metric(
                        required(row, "purchase_revenue_property_currency"), "purchase_revenue_property_currency"
                    ),
                    "extracted_at_utc": extracted,
                }
                if output["engaged_sessions"] > output["sessions"]:
                    raise ValueError("engaged_sessions exceeds sessions")
            else:
                output = {
                    "source_system": "gsc_search_analytics_api",
                    "site_property": identity,
                    "date": day, "device": str(required(row, "device")),
                    "clicks": metric(required(row, "clicks"), "clicks", minimum=0),
                    "impressions": metric(required(row, "impressions"), "impressions", minimum=0),
                    "ctr_ratio": metric(required(row, "ctr_ratio"), "ctr_ratio", minimum=0, maximum=1),
                    "average_position": metric(required(row, "average_position"), "average_position", minimum=0),
                    "extracted_at_utc": extracted,
                }
                if output["clicks"] > output["impressions"]:
                    raise ValueError("clicks exceeds impressions")
            results.append(output)
    else:
        url = str(required(snapshot, "url"))
        if not url.startswith("https://"):
            raise ValueError("PageSpeed URL must be HTTPS")
        strategy = required(snapshot, "strategy")
        if strategy not in ("mobile", "desktop"):
            raise ValueError("PageSpeed strategy must be mobile or desktop")
        scores = required(snapshot, "lighthouse_scores_0_to_100")
        labs = required(snapshot, "lab_metrics")
        if not isinstance(scores, dict) or not isinstance(labs, dict):
            raise ValueError("PageSpeed scores and metrics must be objects")
        output = {
            "source_system": "pagespeed_insights_api",
            "url": url,
            "strategy": strategy,
            "extracted_at_utc": extracted,
        }
        for name, key in SCORE_KEYS.items():
            value = scores.get(key)
            output[name] = None if value is None else metric(value, name, minimum=0, maximum=100)
        for name, key in LAB_KEYS.items():
            value = labs.get(key)
            output[name] = None if value is None else metric(value, name, minimum=0)
        results.append(output)
    seen: set[tuple] = set()
    for row in results:
        grain = grain_key(source, row)
        if grain in seen:
            raise ValueError(f"{source}: duplicate grain within a single snapshot {grain!r}")
        seen.add(grain)
    return source, results


def grain_key(source: str, row: dict) -> tuple:
    if source == "ga4_data_api":
        return (row["property_id"], row["date"], row["ga4_session_channel_group"])
    if source == "gsc_search_analytics_api":
        return (row["site_property"], row["date"], row["device"])
    return (row["url"], row["strategy"], row["extracted_at_utc"])


def read_and_reconcile(input_dir: Path, *, allow_partial: bool = False) -> tuple[dict[str, list[dict]], dict]:
    paths = sorted(
        path for path in input_dir.glob("*.json")
        if path.name.startswith(PREFIXES)
    )
    if not paths:
        raise ValueError("No real GA4, GSC or PageSpeed snapshot JSON files found; refusing to create demo metrics")
    tables: dict[str, dict[tuple, dict]] = {source: {} for source in OUTPUT_FIELDS}
    properties: dict[str, set[str]] = {source: set() for source in OUTPUT_FIELDS}
    collisions = 0
    partial_count = 0
    for path in paths:
        with path.open(encoding="utf-8") as stream:
            snapshot = json.load(stream)
        if not isinstance(snapshot, dict):
            raise ValueError(f"{path.name}: snapshot must be a JSON object")
        source, rows = normalize_snapshot(snapshot, allow_partial=allow_partial)
        partial_count += int(snapshot.get("partial") is True)
        identifier = snapshot.get("property_id", snapshot.get("site_property", snapshot.get("url")))
        properties[source].add(str(identifier))
        for row in rows:
            key = grain_key(source, row)
            previous = tables[source].get(key)
            if previous is not None:
                collisions += 1
                if row["extracted_at_utc"] == previous["extracted_at_utc"] and row != previous:
                    raise ValueError(f"Conflicting values with same extraction timestamp for {key!r}")
                if row["extracted_at_utc"] <= previous["extracted_at_utc"]:
                    continue
            tables[source][key] = row
    export = {
        source: [records[key] for key in sorted(records)] for source, records in tables.items()
    }
    manifest = {
        "schema_version": 1,
        "data_status": "actual_api_snapshots_not_live_feed",
        "input_snapshot_count": len(paths),
        "partial_snapshot_count": partial_count,
        "replaced_overlapping_grains": collisions,
        "source_summary": {
            source: {"rows": len(export[source]), "distinct_properties": len(properties[source])}
            for source in OUTPUT_FIELDS
        },
        "warnings": [
            "GA4 active_users is not additive across days or channels; do not sum it for unique users.",
            "GA4 property currency is not in snapshots; do not combine purchase_revenue across properties.",
            "GSC CTR and average position are ratios/weighted metrics; never average row ratios.",
            "PageSpeed Lighthouse lab results are not CrUX real-user Core Web Vitals.",
            "No GA4/GSC/Ads join or Olist/Greenweez revenue join is inferred.",
        ],
    }
    return export, manifest


def export_marts(input_dir: Path, output_dir: Path, *, allow_partial: bool = False) -> dict:
    tables, manifest = read_and_reconcile(input_dir, allow_partial=allow_partial)
    output_dir.mkdir(parents=True, exist_ok=True)
    for source, fields in OUTPUT_FIELDS.items():
        with (output_dir / OUTPUT_NAMES[source]).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")
            writer.writeheader()
            writer.writerows(tables[source])
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("target/google_measurement"))
    parser.add_argument("--output-dir", type=Path, default=Path("target/google_measurement/marts"))
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    manifest = export_marts(args.input_dir, args.output_dir, allow_partial=args.allow_partial)
    print(json.dumps(manifest["source_summary"], indent=2))
    print(f"Validated snapshot marts: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
