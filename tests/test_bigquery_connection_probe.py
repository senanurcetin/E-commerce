"""NEXUS keyless GitHub BigQuery preflight never reads merchant data."""
from pathlib import Path
import unittest

from scripts.bigquery_connection_probe import DATA_PROJECT, SOURCES, probe


class Dataset:
    location = "EU"


class Client:
    def __init__(self, missing=None, cost=0):
        self.missing, self.cost, self.calls = missing, cost, []
    def get_dataset(self, name):
        self.calls.append(("dataset", name))
        return Dataset()
    def get_table(self, name):
        self.calls.append(("table", name))
        schema = () if self.missing == name else ("id",)
        return type("Table", (), {"schema": schema})()
    def query(self, query, *, location, job_config):
        self.calls.append(("query", query, location, job_config))
        return type("Job", (), {"total_bytes_processed": self.cost})()


class BQ:
    @staticmethod
    def QueryJobConfig(**kwargs):
        return kwargs


class BigQueryConnectionTests(unittest.TestCase):
    def test_exact_eight_table_metadata_no_business_queries(self):
        client = Client()
        report = probe(client, BQ())
        self.assertEqual(report["table_metadata_count"], 8)
        self.assertEqual(len(SOURCES), 2)
        self.assertFalse(report["rows_downloaded"])
        self.assertFalse(report["business_data_verified"])
        for call in client.calls:
            if call[0] in ("dataset", "table"):
                self.assertTrue(call[1].startswith(DATA_PROJECT + "."))
        queries = [call for call in client.calls if call[0] == "query"]
        self.assertEqual(len(queries), 1)
        self.assertEqual(queries[0][1], "SELECT 1 AS nexus_auth_probe")
        self.assertTrue(queries[0][3]["dry_run"])
        self.assertEqual(queries[0][3]["maximum_bytes_billed"], 0)

    def test_missing_metadata_rejected_before_dry_run(self):
        client = Client(missing="workintech-working.e_ticaret.events")
        with self.assertRaisesRegex(ValueError, "metadata unavailable"):
            probe(client, BQ())
        self.assertFalse(any(x[0] == "query" for x in client.calls))

    def test_misreported_bytes_rejected(self):
        with self.assertRaisesRegex(ValueError, "zero bytes"):
            probe(Client(cost=3), BQ())

    def test_workflow_manual_main_oidc_only(self):
        root = Path(__file__).resolve().parents[1]
        body = (root / ".github/workflows/bigquery-connection.yml").read_text()
        self.assertIn("workflow_dispatch:", body)
        self.assertIn("id-token: write", body)
        self.assertIn("google-github-actions/auth@v3", body)
        self.assertIn("github.ref == 'refs/heads/main'", body)
        self.assertIn("environment: bigquery-readonly", body)
        self.assertNotIn("credentials_json:", body)
        self.assertNotIn("--execute", body)
        self.assertIn("gha-creds-*.json", (root / ".gitignore").read_text())

    def test_existing_scripts_select_wif_adc_without_gcloud_user_token(self):
        root = Path(__file__).resolve().parents[1]
        for file in ("scripts/ecommerce_bigquery_preflight.py",
                     "integrations/greenweez/scripts/load_gsheet_from_bigquery.py"):
            with self.subTest(file=file):
                body = (root / file).read_text()
                self.assertIn('os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")', body)
                self.assertIn("bigquery.Client(", body)
