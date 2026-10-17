"""Local no-network tests for NEXUS tracked-file hygiene."""
from pathlib import Path
import tempfile
import unittest

from scripts.repo_hygiene_guard import audit, violation_for_path


class RepoHygieneTests(unittest.TestCase):
    def test_reject_sensitive_files_anywhere_in_repository(self):
        for filename in (
            "gha-creds-b46c2.json", "integrations/greenweez/target/source.duckdb",
            "target/cloud_inventory/receipt.json", ".env", "dashboard/.env.local",
            "secrets/private.pem", "secrets/service-account.json",
            "integrations/greenweez/target/dbt/manifest.json",
        ):
            with self.subTest(filename=filename):
                self.assertIsNotNone(violation_for_path(filename))

    def test_allow_synthetic_seed_and_regular_assets(self):
        for filename in (
            "seeds/raw_orders.csv", "branding/nexus_official_transparent.png",
            ".github/workflows/ci.yml", "integrations/greenweez/seeds/orders.csv",
            "docs/GITHUB_ACTIONS_BIGQUERY_OIDC.md",
        ):
            with self.subTest(filename=filename):
                self.assertIsNone(violation_for_path(filename))

    def test_reject_embedded_pem_but_not_benign_json(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "safe.json").write_text('{"status":"synthetic_ci"}')
            (root / "unsafe.json").write_text(
                '{"private_key":"-----BEGIN PRIVATE KEY-----ABC"}'
            )
            self.assertEqual(audit(root, ["safe.json"]), [])
            findings = audit(root, ["safe.json", "unsafe.json"])
            self.assertEqual(len(findings), 1)
            self.assertIn("Embedded private key", findings[0])

    def test_no_tracked_credential_or_raw_export_in_actual_repo(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(audit(root), [])


if __name__ == "__main__":
    unittest.main()
