"""Read-only, source-isolated GA4 lab event-count extraction (no user IDs).

Run from the repository root:
  GA4_LAB_PROPERTY_ID=123456789 python -m scripts.lab_ga4_events --start 2026-10-01 --end 2026-10-16

Google Analytics *numeric property ID*, not public G-... Measurement ID.
The target property must be a dedicated owner-controlled Commerce Lab GA4
property; the old ToyStore and personal portfolio streams are not valid inputs.
Requires Application Default Credentials with Analytics read-only access.
No demonstration data or fallback metrics are exported.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
import math
import os
from pathlib import Path

from scripts.google_measurement import access_token, fetch_json, validate_dates, GA4_SCOPE

HOSTNAME = "nexus-commerce-lab.vercel.app"
EVENT_NAMES = (
    "lab_page_view", "lab_view_item", "lab_add_to_cart",
    "lab_remove_from_cart", "lab_checkout_completed",
)
SOURCE = "ga4_lab_events_data_api"
OUTPUT = Path("target/google_measurement/lab_ga4_events.json")
MAX_PAGES = 10
PAGE_SIZE = 10000


def _count(value: object) -> int:
    if not isinstance(value, str) or not value.isdigit():
        raise ValueError("GA4 lab eventCount must be a nonnegative integer string")
    number = int(value)
    if number > 2**53 - 1:
        raise ValueError("GA4 lab eventCount exceeds safe integer range")
    return number


def normalize_ga4_lab_response(response: dict) -> list[dict]:
    if not isinstance(response, dict):
        raise ValueError("GA4 response must be an object")
    dimensions = [x.get("name") for x in response.get("dimensionHeaders", [])]
    metrics = [x.get("name") for x in response.get("metricHeaders", [])]
    if dimensions != ["date", "eventName", "hostName"] or metrics != ["eventCount"]:
        raise ValueError("GA4 lab report schema mismatch")
    out = []
    for row in response.get("rows", []):
        d = row.get("dimensionValues", [])
        m = row.get("metricValues", [])
        if len(d) != 3 or len(m) != 1:
            raise ValueError("GA4 lab row dimension/metric count mismatch")
        raw_date, event, hostname = (x["value"] for x in d)
        if len(raw_date) != 8 or not raw_date.isdigit():
            raise ValueError("Invalid GA4 lab date")
        dt = date.fromisoformat(f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}")
        if event not in EVENT_NAMES or hostname != HOSTNAME:
            raise ValueError("GA4 lab event not from the expected event/host allowlist")
        out.append({
            "date": dt.isoformat(), "event_name": event,
            "event_count": _count(m[0]["value"]),
        })
    return out


def collect_lab_events(property_id: str, start: str, end: str) -> dict:
    if not isinstance(property_id, str) or not property_id.isdigit():
        raise ValueError("A dedicated numeric GA4_LAB_PROPERTY_ID is required")
    validate_dates(start, end)
    token = access_token(GA4_SCOPE)
    endpoint = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    rows = []
    offset = 0
    for page in range(MAX_PAGES):
        body = {
            "dateRanges": [{"startDate": start, "endDate": end}],
            "dimensions": [{"name": x} for x in ("date", "eventName", "hostName")],
            "metrics": [{"name": "eventCount"}],
            "dimensionFilter": {"andGroup": {"expressions": [
                {"filter": {"fieldName": "eventName", "inListFilter": {
                    "values": list(EVENT_NAMES), "caseSensitive": True,
                }}},
                {"filter": {"fieldName": "hostName", "stringFilter": {
                    "matchType": "EXACT", "value": HOSTNAME, "caseSensitive": True,
                }}},
            ]}},
            "limit": str(PAGE_SIZE), "offset": str(offset),
        }
        response = fetch_json(endpoint, body, token)
        part = normalize_ga4_lab_response(response)
        rows.extend(part)
        count = int(response.get("rowCount", len(rows)))
        offset += len(part)
        if offset >= count:
            break
        if not part:
            raise ValueError("GA4 stopped returning rows before rowCount reached")
    else:
        raise ValueError("GA4 lab extraction exceeds allowed pages; no partial export")
    snapshot = {
        "source": SOURCE,
        "data_status": "actual_ga4_data_api_aggregate_not_live",
        "property_id": property_id,
        "site_hostname": HOSTNAME,
        "date_start": start,
        "date_end": end,
        "extracted_at_utc": datetime.now(timezone.utc).isoformat(),
        "partial": False,
        "rows": rows,
        "interpretation": "Opted-in GA4 lab event counts; no purchases, revenue or unique users",
    }
    validate_lab_snapshot(snapshot)
    return snapshot


def validate_lab_snapshot(snapshot: dict) -> list[dict]:
    if not isinstance(snapshot, dict):
        raise ValueError("Lab source snapshot must be an object")
    if snapshot.get("source") != SOURCE or snapshot.get("data_status") != "actual_ga4_data_api_aggregate_not_live":
        raise ValueError("Unrecognized/fictional lab data source rejected")
    if snapshot.get("site_hostname") != HOSTNAME:
        raise ValueError("GA4 lab hostname mismatch")
    if not str(snapshot.get("property_id", "")).isdigit():
        raise ValueError("GA4 lab property must be a numeric ID")
    if snapshot.get("partial") is not False:
        raise ValueError("Partial lab extraction rejected")
    try:
        when = datetime.fromisoformat(snapshot["extracted_at_utc"].replace("Z", "+00:00"))
        first = date.fromisoformat(snapshot["date_start"])
        last = date.fromisoformat(snapshot["date_end"])
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Invalid lab snapshot date/timestamp") from exc
    if when.tzinfo is None or first > last:
        raise ValueError("Unbounded or reversed GA4 lab extraction date")
    rows = snapshot.get("rows")
    if not isinstance(rows, list):
        raise ValueError("Expected lab rows list")
    seen = set()
    cleaned = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"date", "event_name", "event_count"}:
            raise ValueError("Unexpected lab event row fields")
        dt = date.fromisoformat(row["date"])
        if dt < first or dt > last or row["event_name"] not in EVENT_NAMES:
            raise ValueError("Lab event outside expected date/event")
        count = row["event_count"]
        if isinstance(count, bool) or not isinstance(count, int) or count < 0 or count > 2**53 - 1:
            raise ValueError("Invalid lab event count")
        grain = (row["date"], row["event_name"])
        if grain in seen:
            raise ValueError("Duplicate lab date/event grain")
        seen.add(grain)
        cleaned.append(row)
    return cleaned


def load_lab_snapshot(path: Path = OUTPUT) -> tuple[list[dict], dict] | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as stream:
        snapshot = json.load(stream)
    return validate_lab_snapshot(snapshot), snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    property_id = os.environ.get("GA4_LAB_PROPERTY_ID", "").strip()
    snapshot = collect_lab_events(property_id, args.start, args.end)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp")
    temporary.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(f"Verified source: {snapshot['source']}; event rows: {len(snapshot['rows'])}")
    print(f"Output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
