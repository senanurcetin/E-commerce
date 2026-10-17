"""GitHub OIDC/ADC BigQuery connectivity probe; no source rows are selected.

Checks eight pinned table metadata contracts and constant SELECT 1 dry runs,
never extracts or publishes merchant records.
"""
from __future__ import annotations

import os
import re
from typing import Any

# Use the SAME required-column contracts as the later source-specific
# preflights. A metadata-only connection must not pass on arbitrary tables.
from scripts.ecommerce_bigquery_preflight import CONTRACT as ECOMMERCE_FIELDS
from integrations.greenweez.scripts.load_gsheet_from_bigquery import (
    TABLES as GREENWEEZ_FIELDS,
)

DATA_PROJECT = "workintech-working"
SOURCES = {
    "e_ticaret": ("events", "order_items", "products", "users"),
    "fvt_gsheet": (
        "gwz_finance_orders_orders", "gwz_finance_shipping_shipping",
        "gwz_finance_refund_sheet_1", "gwz_finance_campaign",
    ),
}
PROJECT_RE = re.compile(r"^[a-z][a-z0-9-]{4,62}$")
REQUIRED_FIELDS = {
    "e_ticaret": {
        table: frozenset(field.casefold() for field in ECOMMERCE_FIELDS[table])
        for table in SOURCES["e_ticaret"]
    },
    "fvt_gsheet": {
        table: frozenset(field.casefold() for field in GREENWEEZ_FIELDS[table])
        for table in SOURCES["fvt_gsheet"]
    },
}


def probe(client: Any, bigquery: Any) -> dict:
    count = 0
    fields_checked = 0
    locations = set()
    for dataset, names in SOURCES.items():
        metadata = client.get_dataset(f"{DATA_PROJECT}.{dataset}")
        location = str(getattr(metadata, "location", "") or "")
        if not location:
            raise ValueError(f"{dataset}: source region unavailable")
        locations.add(location)
        for table in names:
            schema = client.get_table(f"{DATA_PROJECT}.{dataset}.{table}").schema
            if not schema:
                raise ValueError(f"{dataset}.{table}: required metadata unavailable")
            observed = {str(getattr(field, "name", "")).casefold() for field in schema}
            required = REQUIRED_FIELDS[dataset][table]
            missing = required - observed
            if missing:
                # Column names are nonsecret schema metadata, not customer values.
                raise ValueError(
                    f"{dataset}.{table}: {len(missing)} required columns missing: "
                    + ", ".join(sorted(missing))
                )
            fields_checked += len(required)
            count += 1
        print(f"OK: {DATA_PROJECT}.{dataset} — {len(names)} table schemas, region {location}")
    # SELECT 1 has no source FROM. Dry run is checked for nonzero bytes.
    for location in sorted(locations):
        result = client.query(
            "SELECT 1 AS nexus_auth_probe",
            location=location,
            job_config=bigquery.QueryJobConfig(
                dry_run=True, use_query_cache=False, maximum_bytes_billed=0,
            ),
        )
        if int(result.total_bytes_processed or 0):
            raise ValueError("Connectivity probe must scan zero bytes")
    return {
        "schema_version": 1,
        "source_project": DATA_PROJECT,
        "dataset_count": len(SOURCES),
        "table_metadata_count": count,
        "required_field_count": fields_checked,
        "schema_contract_verified": True,
        "rows_downloaded": False,
        "business_data_verified": False,
        "real_source_dry_run_passed": False,
    }


def main() -> int:
    project = os.getenv("BILLING_PROJECT", "")
    if not PROJECT_RE.fullmatch(project):
        print("BLOCKED: billing project is not configured")
        return 2
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("BLOCKED: short-lived GitHub OIDC ADC not available")
        return 2
    try:
        from google.cloud import bigquery
        client = bigquery.Client(project=project)
        try:
            result = probe(client, bigquery)
        finally:
            client.close()
        print(
            "PASS: OIDC connection and metadata check — "
            f"{result['table_metadata_count']} tables, "
            f"{result['required_field_count']} required fields; no business rows"
        )
        print("HOLD: real source queries, finance reconciliation, Power BI Desktop")
        return 0
    except (OSError, RuntimeError, ValueError, KeyError, ImportError):
        # Never log OAuth tokens, identity metadata responses or private rows.
        print("BLOCKED: BigQuery metadata access or query job failed")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
