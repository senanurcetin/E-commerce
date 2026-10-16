"""Read-only Greenweez Google Sheets campaign-key coverage audit (not ROAS).

Reads the user's authorized Google Sheets via Sheets Values API using ADC and
never modifies source Sheets, existing dbt marts or financial numbers.

Install optional dependency: pip install "google-auth[requests]>=2,<3"
Set GWZ_ORDERS_SHEET_ID and GWZ_CAMPAIGNS_SHEET_ID outside source control.
Run: python scripts/audit_sheet_campaign_links.py

Outputs only aggregated PII-free results under gitignored target/gsheet_audit.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import argparse
import csv
import json
import os
from pathlib import Path
import re
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


SOURCE_TABS = ("adwords", "bing", "facebook", "criteo")
ORDER_HEADER = (
    "date_date", "orders_id", "new", "turnover", "is_ga",
    "channel_grouping", "channel", "campaign_key", "campaign",
)
CAMPAIGN_HEADER = (
    "date_date", "campaign_key", "paid_source", "campaign_name",
    "cost", "impression", "click",
)
OUTPUT_DIR = Path("target/gsheet_audit")


def validate_header(values: list[list], required: tuple[str, ...], table: str):
    if not values:
        raise ValueError(f"{table}: empty spreadsheet range")
    header = tuple(str(x).strip().lower() for x in values[0][:len(required)])
    if header != required:
        raise ValueError(f"{table}: unexpected header {header!r}; expected {required!r}")


def cell(row: list, idx: int):
    return row[idx] if idx < len(row) else None


def sheet_date(value) -> str:
    if isinstance(value, bool) or value is None or value == "":
        raise ValueError("missing or invalid date")
    if isinstance(value, (int, float)):
        serial = float(value)
        if not serial.is_integer() or serial < 1 or serial > 100000:
            raise ValueError(f"invalid Sheets date serial {value!r}")
        return (date(1899, 12, 30) + timedelta(days=int(serial))).isoformat()
    if not isinstance(value, str):
        raise ValueError("date should be YYYY-MM-DD or Google Sheets serial")
    try:
        parsed = date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError(f"date is not ISO: {value!r}") from exc
    return parsed.isoformat()


def campaign_key(value) -> str | None:
    """Preserve campaign IDs as exact identifiers; don't approximate large floats."""
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValueError("campaign key cannot be boolean")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not value.is_integer() or abs(value) > 2**53:
            raise ValueError("campaign ID loses precision; export formatted text instead")
        return str(int(value))
    text = str(value).strip()
    if not text:
        return None
    if text.startswith("'"):
        text = text[1:]
    if not text or len(text) > 200:
        raise ValueError("invalid campaign key length")
    return text


def money(value, field: str) -> Decimal:
    """Normalize unambiguous EUR/numeric cells without silently guessing units."""
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field}: missing money amount")
    if isinstance(value, (float, int)):
        value = str(value)
    s = str(value).strip().replace("€", "").replace("\u202f", "").replace("\xa0", "").replace(" ", "")
    if not s or not re.fullmatch(r"-?[0-9]+(?:[.,][0-9]{1,2})?", s):
        raise ValueError(f"{field}: unsupported or ambiguous money representation")
    try:
        amount = Decimal(s.replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError(f"{field}: invalid amount") from exc
    if not amount.is_finite():
        raise ValueError(f"{field}: invalid amount")
    return amount


def nonnegative_count(value, field: str) -> int:
    if isinstance(value, bool) or value in ("", None):
        raise ValueError(f"{field}: missing count")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{field}: invalid integer") from exc
    if not number.is_finite() or number != int(number) or number < 0:
        raise ValueError(f"{field}: not a nonnegative integer")
    return int(number)


def parse_orders(values: list[list]) -> list[dict]:
    validate_header(values, ORDER_HEADER, "orders")
    output = []
    seen = set()
    for line, row in enumerate(values[1:], start=2):
        if not row or all(x == "" for x in row):
            continue
        order_id = campaign_key(cell(row, 1))
        if order_id is None:
            raise ValueError(f"orders row {line}: missing orders_id")
        if order_id in seen:
            raise ValueError(f"orders row {line}: duplicate order_id")
        seen.add(order_id)
        amount = money(cell(row, 3), f"orders row {line}: turnover")
        if amount < 0:
            raise ValueError(f"orders row {line}: negative turnover")
        output.append({
            "day": sheet_date(cell(row, 0)),
            "key": campaign_key(cell(row, 7)),
            "turnover": amount,
        })
    return output


def parse_campaigns(raw_by_tab: dict[str, list[list]]) -> list[dict]:
    output = []
    seen: set[tuple] = set()
    for tab in SOURCE_TABS:
        if tab not in raw_by_tab:
            raise ValueError(f"missing source tab {tab}")
        values = raw_by_tab[tab]
        validate_header(values, CAMPAIGN_HEADER, tab)
        for line, row in enumerate(values[1:], start=2):
            if not row or all(x == "" for x in row):
                continue
            day = sheet_date(cell(row, 0))
            key = campaign_key(cell(row, 1))
            if key is None:
                raise ValueError(f"{tab} row {line}: campaign_key is missing")
            cost = money(cell(row, 4), f"{tab} row {line}: cost")
            if cost < 0:
                raise ValueError(f"{tab} row {line}: negative ad cost")
            impressions = nonnegative_count(cell(row, 5), "impressions")
            clicks = nonnegative_count(cell(row, 6), "clicks")
            if clicks > impressions:
                raise ValueError(f"{tab} row {line}: clicks exceeds impressions")
            unique = (tab, day, key)
            if unique in seen:
                raise ValueError(f"{tab} row {line}: duplicate platform/day/campaign_key")
            seen.add(unique)
            output.append({"day": day, "key": key, "source": tab, "cost": cost,
                           "impressions": impressions, "clicks": clicks})
    return output


def audit(orders: list[dict], campaigns: list[dict]) -> tuple[list[dict], dict]:
    """Report exact-key/date linkage coverage, *not* marketing attribution or ROAS."""
    if not orders or not campaigns:
        raise ValueError("at least one real order and one real campaign row required")
    platforms_by_key: dict[tuple, set[str]] = defaultdict(set)
    for row in campaigns:
        platforms_by_key[(row["day"], row["key"])].add(row["source"])
    summary = {
        "orders_total": len(orders),
        "orders_without_campaign_key": 0,
        "orders_with_campaign_key": 0,
        "orders_matched_exact_day_key": 0,
        "orders_unmatched_day_key": 0,
        "orders_ambiguous_multiple_platforms": 0,
        "turnover_matched_eur": Decimal("0"),
        "turnover_total_eur": Decimal("0"),
    }
    by_source: dict[str, dict] = {
        tab: {"source": tab, "campaign_rows": 0, "spend_eur": Decimal("0"),
              "impressions": 0, "clicks": 0, "matched_order_count": 0,
              "matched_turnover_eur": Decimal("0")} for tab in SOURCE_TABS
    }
    for row in campaigns:
        group = by_source[row["source"]]
        group["campaign_rows"] += 1
        group["spend_eur"] += row["cost"]
        group["impressions"] += row["impressions"]
        group["clicks"] += row["clicks"]
    for order in orders:
        summary["turnover_total_eur"] += order["turnover"]
        if order["key"] is None:
            summary["orders_without_campaign_key"] += 1
            continue
        summary["orders_with_campaign_key"] += 1
        hits = platforms_by_key.get((order["day"], order["key"]), set())
        if len(hits) == 0:
            summary["orders_unmatched_day_key"] += 1
        elif len(hits) > 1:
            summary["orders_ambiguous_multiple_platforms"] += 1
        else:
            summary["orders_matched_exact_day_key"] += 1
            summary["turnover_matched_eur"] += order["turnover"]
            source = next(iter(hits))
            by_source[source]["matched_order_count"] += 1
            by_source[source]["matched_turnover_eur"] += order["turnover"]
    summary["campaign_records"] = len(campaigns)
    summary["match_rate_all_orders"] = round(summary["orders_matched_exact_day_key"] / len(orders), 6)
    summary["match_rate_keyed_orders"] = round(
        summary["orders_matched_exact_day_key"] / summary["orders_with_campaign_key"], 6
    ) if summary["orders_with_campaign_key"] else None
    return list(by_source.values()), summary


def adc_token() -> str:
    try:
        import google.auth
        from google.auth.transport.requests import Request as AuthRequest
    except ImportError as exc:
        raise RuntimeError('Install: pip install "google-auth[requests]>=2,<3"') from exc
    credentials, _ = google.auth.default(scopes=[
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ])
    credentials.refresh(AuthRequest())
    return credentials.token


def read_values(sheet_id: str, range_a1: str, token: str) -> list[list]:
    if not sheet_id or not re.fullmatch(r"[-\w]{15,150}", sheet_id):
        raise ValueError("Invalid Google Spreadsheet ID")
    url = ("https://sheets.googleapis.com/v4/spreadsheets/"
           + quote(sheet_id, safe="") + "/values/" + quote(range_a1, safe="")
           + "?" + urlencode({"valueRenderOption": "UNFORMATTED_VALUE"}))
    with urlopen(Request(url, headers={"Authorization": f"Bearer {token}"}), timeout=60) as resp:
        response = json.load(resp)
    if "values" not in response:
        raise ValueError(f"Sheet range is empty: {range_a1}")
    return response["values"]


def write_report(target: Path, rows: list[dict], summary: dict):
    target.mkdir(parents=True, exist_ok=True)
    labels = list(rows[0].keys())
    with (target / "paid_source_linkage_audit.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=labels)
        writer.writeheader()
        writer.writerows(rows)
    safe_summary = {
        **summary,
        "source_system": "google_sheets_readonly",
        "report_kind": "campaign_key_date_linkage_coverage_not_attribution",
        "attribution_validated": False,
        "roas_validated": False,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "caveats": [
            "Matched turnover is linked by campaign_key and exact date only, not evidence of ad causality.",
            "Sparse or blank campaign_key values bias coverage; never call matched turnover ROAS.",
            "Source workbook is August 2021 and independent of October 2021 fvt_gsheet finance tables.",
            "No order IDs, campaign IDs or customer details are exported.",
        ],
    }
    (target / "coverage_manifest.json").write_text(
        json.dumps(safe_summary, default=str, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    orders_id = os.environ.get("GWZ_ORDERS_SHEET_ID", "").strip()
    campaigns_id = os.environ.get("GWZ_CAMPAIGNS_SHEET_ID", "").strip()
    if not orders_id or not campaigns_id:
        parser.error("Set GWZ_ORDERS_SHEET_ID and GWZ_CAMPAIGNS_SHEET_ID")
    token = adc_token()
    orders = parse_orders(read_values(orders_id, "'orders'!A1:I", token))
    campaigns = parse_campaigns({
        tab: read_values(campaigns_id, f"'{tab}'!A1:G", token)
        for tab in SOURCE_TABS
    })
    rows, summary = audit(orders, campaigns)
    write_report(args.output_dir, rows, summary)
    print(
        f"Order count={summary['orders_total']}; "
        f"day+key matches={summary['orders_matched_exact_day_key']}; "
        f"coverage={summary['match_rate_all_orders']:.1%} (not attributed ROAS)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
