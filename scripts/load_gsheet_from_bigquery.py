"""Copy the Google Sheets export (BigQuery dataset fvt_gsheet) into a local DuckDB file.

The dbt project in `source_system: fvt_gsheet` mode reads these tables from the DuckDB target
`gsheet_real`, so the dashboard and the marts can be run on the real data without writing anything to
the warehouse. This script only runs `SELECT *` against BigQuery.

Credentials come from Application Default Credentials, e.g.
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
Never put the key file in the repository. The output goes to target/ (gitignored) and holds real
business data: do not commit or share it.

Usage: python scripts/load_gsheet_from_bigquery.py [--project workintech-working] [--dataset fvt_gsheet]
"""
import argparse
from pathlib import Path

import duckdb
import pandas as pd
from google.cloud import bigquery

TABLES = [
    "gwz_finance_orders_orders",
    "gwz_finance_shipping_shipping",
    "gwz_finance_refund_sheet_1",
    "gwz_finance_campaign",
]
OUTPUT = Path(__file__).resolve().parent.parent / "target" / "gsheet_real.duckdb"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", default="workintech-working")
    parser.add_argument("--dataset", default="fvt_gsheet")
    args = parser.parse_args()

    client = bigquery.Client(project=args.project)
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.unlink(missing_ok=True)
    con = duckdb.connect(str(OUTPUT))
    con.sql("create schema analytics")
    for table in TABLES:
        df = client.query(f"select * from `{args.project}.{args.dataset}.{table}`").to_dataframe()
        for column in df.columns:
            if str(df[column].dtype) == "dbdate":  # BigQuery DATE -> plain python date
                df[column] = pd.to_datetime(df[column].astype(str)).dt.date
        con.register("df", df)
        con.sql(f"create table analytics.{table} as select * from df")
        con.unregister("df")
        print(f"{table}: {len(df)} rows")
    con.close()
    print(f"written to {OUTPUT}")


if __name__ == "__main__":
    main()
