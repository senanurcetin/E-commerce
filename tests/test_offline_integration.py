"""Offline combined-source acceptance refuses empty, corrupted or partial evidence."""
from pathlib import Path
import tempfile
import unittest

from scripts.verify_offline_pipeline import verify


class OfflineIntegrationTests(unittest.TestCase):
    def test_empty_source_workspace_fails_without_generating_project(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(ValueError, "Both independently"):
                verify(root, root / "out")
            self.assertFalse((root / "out").exists())

    def test_corrupt_partial_source_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            snapshot = root / "target/ecommerce_bridge/snapshot.json"
            snapshot.parent.mkdir(parents=True)
            snapshot.write_text('{"fabricated": 123}', encoding="utf-8")
            with self.assertRaises(ValueError):
                verify(root, root / "out")
