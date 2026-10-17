"""Read-only inventory of candidate BigQuery tables across the owner's two projects.

No SQL queries, row contents, data exports, dataset mutations or credentials on disk.

Windows:
  cd C:\Users\MONSTER\E-commerce
  python -m scripts.cloud_source_inventory

Uses the user's existing gcloud auth login. This module calls only
BigQuery dataset-list and table-list metadata endpoints, never jobs.query.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

PROJECTS = ("workintech-working", "data-analiz-490513")
OUT = Path("target/cloud_inventory/bq_source_locations.json")
API = "https://bigquery.googleapis.com/bigquery/v2"
EXPECTED = {
    "ecommerce": ("events", "order_items", "products", "users"),
    "greenweez_raw": (
        "raw_gz_sales", "raw_gz_product", "raw_gz_ship",
        "raw_gz_adwords", "raw_gz_bing", "raw_gz_criterio", "raw_gz_facebook",
    ),
    "greenweez_gsheet": (
        "gwz_finance_orders_orders", "gwz_finance_shipping_shipping",
        "gwz_finance_refund_sheet_1", "gwz_finance_campaign",
    ),
}
INTERESTING = re.compile(
    r"e.?commerce|e.?ticaret|green|gwz|gz_|fvt|gsheet|thelook|shop|orders?|"
    r"events?|finance|mart|dbt|staging|raw", re.I,
)


def gcloud_user_token() -> str:
    cli = "gcloud.cmd" if os.name == "nt" else "gcloud"
    try:
        p = subprocess.run(
            [cli, "auth", "print-access-token"], text=True,
            capture_output=True, check=False, timeout=45,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("gcloud CLI unavailable or timed out") from None
    if p.returncode != 0 or not p.stdout.strip():
        # Never forward the gcloud stderr or token to logs/output.
        raise RuntimeError("Run gcloud auth login with a user who can list both projects")
    return p.stdout.strip()


def get_json(url: str, token: str) -> dict:
    req = Request(url, headers={"Authorization": "Bearer " + token,
                                "Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as resp:
            payload = json.load(resp)
    except HTTPError as exc:
        # Do not log the response body, token, request authorization headers.
        if exc.code == 403:
            raise PermissionError("HTTP 403: dataset/table metadata listing permission missing") from None
        if exc.code == 404:
            raise FileNotFoundError("HTTP 404: project or resource not found") from None
        raise RuntimeError("BigQuery metadata API returned HTTP " + str(exc.code)) from None
    except URLError:
        raise ConnectionError("Unable to connect to BigQuery metadata API") from None
    if not isinstance(payload, dict):
        raise ValueError("Unexpected metadata API response")
    return payload


def paged(token: str, url: str, key: str) -> list[dict]:
    rows: list[dict] = []
    cursor = ""
    seen = set()
    for _ in range(100):
        separator = "&" if "?" in url else "?"
        page_url = url + (separator + urlencode({"pageToken": cursor}) if cursor else "")
        payload = get_json(page_url, token)
        part = payload.get(key, [])
        if not isinstance(part, list):
            raise ValueError("Malformed BigQuery " + key + " response")
        rows.extend(part)
        cursor = payload.get("nextPageToken", "")
        if not cursor:
            return rows
        if cursor in seen:
            raise ValueError("Repeated BigQuery pagination cursor")
        seen.add(cursor)
    raise RuntimeError("Too many metadata pages; refusing incomplete scan")


def project_inventory(project: str, token: str) -> dict:
    if project not in PROJECTS:
        raise ValueError("Only the owner's two specified projects can be read")
    result = {"project": project, "status": "unverified", "datasets": [],
              "metadata_errors": []}
    try:
        dsets = paged(token, f"{API}/projects/{quote(project, safe='')}/datasets"
                            "?all=true&maxResults=1000", "datasets")
    except (PermissionError, FileNotFoundError, RuntimeError, ConnectionError) as exc:
        result["status"] = "access_denied_or_unavailable"
        result["metadata_errors"].append({"stage": "datasets", "reason": str(exc)})
        return result
    result["status"] = "listed"
    for dataset in dsets:
        if not isinstance(dataset, dict):
            continue
        did = (dataset.get("datasetReference") or {}).get("datasetId")
        if not isinstance(did, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,1024}", did):
            continue
        entry = {"dataset": did, "status": "listed", "table_count": None,
                 "matches": {}, "candidate_tables": []}
        try:
            tables = paged(token, f"{API}/projects/{quote(project, safe='')}/datasets/"
                           f"{quote(did, safe='')}/tables?maxResults=1000", "tables")
        except (PermissionError, FileNotFoundError, RuntimeError, ConnectionError) as exc:
            entry["status"] = "table_list_unavailable"
            result["metadata_errors"].append({"dataset": did, "reason": str(exc)})
            result["datasets"].append(entry)
            continue
        names = {str((t.get("tableReference") or {}).get("tableId", ""))
                 for t in tables if isinstance(t, dict)}
        names.discard("")
        entry["table_count"] = len(names)
        entry["candidate_tables"] = sorted(n for n in names if INTERESTING.search(n))
        for domain, required in EXPECTED.items():
            found = sorted(names.intersection(required))
            if found:
                entry["matches"][domain] = {
                    "found": found, "coverage": len(found),
                    "expected": len(required),
                    "all_required_tables_present": len(found) == len(required),
                }
        result["datasets"].append(entry)
    return result


def format_summary(result: dict) -> list[str]:
    project = result["project"]
    datasets = result["datasets"]
    out = [project + ": " + result["status"] + "; visible datasets: " + str(len(datasets))]
    for ds in datasets:
        if ds["matches"] or INTERESTING.search(ds["dataset"]):
            domains = "; ".join(f"{k}={v['coverage']}/{v['expected']} tables"
                                for k, v in ds["matches"].items())
            out.append("  " + project + "." + ds["dataset"] +
                       " | " + ds["status"] +
                       (" | " + domains if domains else " | no exact source table match"))
            if ds["candidate_tables"]:
                out.append("    candidate table names: " +
                           ", ".join(ds["candidate_tables"][:40]))
    if result["metadata_errors"]:
        out.append("  Warning: " + str(len(result["metadata_errors"])) +
                   " dataset/table listing errors. Missing may mean NO ACCESS.")
    return out


def run(projects: tuple[str, ...] = PROJECTS, output: Path = OUT) -> dict:
    token = gcloud_user_token()
    # Tokens are used for read-only metadata requests and not stored.
    inventory = [project_inventory(project, token) for project in projects]
    report = {
        "schema_version": 1, "scanned_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "BigQuery datasets.list + tables.list metadata only; NO SQL/jobs/data rows",
        "results": inventory,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    for result in inventory:
        for line in format_summary(result):
            print(line)
    print("Report (metadata only):", output)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    try:
        report = run(output=args.output)
    except (OSError, RuntimeError, ValueError) as exc:
        print("BLOCKED: " + type(exc).__name__ + ": " + str(exc))
        return 2
    return 0 if all(p["status"] == "listed" and not p["metadata_errors"]
                    for p in report["results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
