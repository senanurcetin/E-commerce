"""Offline checks: update only the existing wrong provider variable."""
import json
import subprocess
import unittest

from scripts.repair_nexus_wif_provider import (
    NEW_PROVIDER, OLD_PROVIDER, REPOSITORIES, environments, fix, main,
)


class FakeGh:
    def __init__(self, values=None, envs=None):
        self.values = values or {}
        self.envs = envs or {}
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs.get("input")))
        if argv[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(argv, 0, "ok", "")
        if argv[1] == "api":
            repo = argv[2].split("/")[2]
            return subprocess.CompletedProcess(
                argv, 0, "\n".join(self.envs.get(repo, [])), "")
        if argv[1:3] == ["variable", "list"]:
            fullname = argv[argv.index("--repo") + 1]
            environment = argv[argv.index("--env") + 1] if "--env" in argv else None
            value = self.values.get((fullname, environment))
            rows = [{"name": "GCP_WIF_PROVIDER", "value": value}] if value is not None else []
            return subprocess.CompletedProcess(argv, 0, json.dumps(rows), "")
        if argv[1:3] == ["variable", "set"]:
            fullname = argv[argv.index("--repo") + 1]
            environment = argv[argv.index("--env") + 1] if "--env" in argv else None
            self.values[(fullname, environment)] = kwargs["input"].strip()
            return subprocess.CompletedProcess(argv, 0, "", "")
        raise AssertionError(f"Unexpected mock command: {argv}")


class RepairTests(unittest.TestCase):
    def test_existing_repo_and_environment_variables_both_corrected(self):
        gh = FakeGh({
            ("senanurcetin/nexus-atlas", None): OLD_PROVIDER,
            ("senanurcetin/nexus-atlas", "production"): OLD_PROVIDER,
            ("senanurcetin/nexus-atlas", "other"): NEW_PROVIDER,
        }, {"nexus-atlas": ["production", "other"]})
        self.assertEqual(main(["--apply", "--repo", "nexus-atlas"], runner=gh), 0)
        self.assertEqual(gh.values[("senanurcetin/nexus-atlas", None)], NEW_PROVIDER)
        self.assertEqual(gh.values[("senanurcetin/nexus-atlas", "production")],
                         NEW_PROVIDER)
        self.assertEqual(sum(1 for c in gh.calls
                             if c[0][1:3] == ["variable", "set"]), 2)

    def test_existing_correct_value_is_not_touched(self):
        gh = FakeGh({("senanurcetin/nexus-atlas", None): NEW_PROVIDER})
        self.assertEqual(fix("nexus-atlas", None, apply=True, runner=gh).status,
                         "OK: already correct")
        self.assertFalse(any(c[0][1:3] == ["variable", "set"] for c in gh.calls))

    def test_another_provider_is_not_overwritten(self):
        gh = FakeGh({("senanurcetin/nexus-atlas", None): "other provider"})
        self.assertTrue(fix("nexus-atlas", None, apply=True, runner=gh)
                        .status.startswith("SKIP"))
        self.assertFalse(any(c[0][1:3] == ["variable", "set"] for c in gh.calls))

    def test_missing_variable_is_not_created(self):
        gh = FakeGh()
        self.assertEqual(fix("nexus-atlas", None, apply=True, runner=gh).status,
                         "SKIP: not configured")

    def test_dry_run_does_not_mutate(self):
        gh = FakeGh({("senanurcetin/nexus-atlas", None): OLD_PROVIDER})
        self.assertTrue(fix("nexus-atlas", None, apply=False, runner=gh)
                        .status.startswith("DRY-RUN"))
        self.assertEqual(gh.values[("senanurcetin/nexus-atlas", None)], OLD_PROVIDER)

    def test_scope_discovery_does_not_create_environments(self):
        gh = FakeGh(envs={"nexus-atlas": ["bigquery-readonly", "production"]})
        self.assertEqual(environments("nexus-atlas", runner=gh),
                         ["bigquery-readonly", "production"])
        self.assertEqual(len(REPOSITORIES), 13)
        self.assertNotIn("unrelated-repository", REPOSITORIES)

    def test_fail_closed_on_unauthorized_repo(self):
        gh = FakeGh()
        with self.assertRaises(SystemExit):
            main(["--apply", "--repo", "unlisted-repository"], runner=gh)


if __name__ == "__main__":
    unittest.main()
