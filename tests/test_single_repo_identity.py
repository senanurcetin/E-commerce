"""Prevent stale standalone Greenweez repository links in maintained NEXUS surfaces."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SINGLE_REPO_SURFACES = (
    "README.md",
    "integrations/README.md",
    "integrations/greenweez/README.md",
    "dashboard/README.md",
    "dashboard/greenweez_finance.py",
    "scripts/greenweez_bridge.py",
    "docs/NEXUS_UNIFIED_COMMERCE_PLAN.md",
    "docs/COMMERCE_KPI_SEMANTICS.md",
    "integrations/greenweez/docs/GOOGLE_SHEETS_CAMPAIGN_LINKAGE.md",
)


class SingleRepoIdentityTests(unittest.TestCase):
    def test_no_active_standalone_repo_urls_or_sibling_import_paths(self):
        for rel in SINGLE_REPO_SURFACES:
            with self.subTest(file=rel):
                body = (ROOT / rel).read_text(encoding="utf-8")
                self.assertNotIn(
                    "https://github.com/senanurcetin/greenweez-finance-campaign-analytics",
                    body,
                )
                self.assertNotIn(
                    "../greenweez-finance-campaign-analytics/target/",
                    body,
                )

    def test_consolidated_identity_and_source_module_are_visible(self):
        landing = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertTrue(landing.startswith("# NEXUS Commerce Intelligence"))
        self.assertIn("integrations/greenweez/", landing)
        self.assertIn("docs/REPOSITORY_CONSOLIDATION.md", landing)
        self.assertIn("migration", landing.lower())
        guide = (ROOT / "docs/REPOSITORY_CONSOLIDATION.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("80 / 80", guide)
        self.assertIn("RENAME and DELETE PENDING", guide)
