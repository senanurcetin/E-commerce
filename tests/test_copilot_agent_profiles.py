"""Offline regression tests for Copilot agent profile policy (no CI/network)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_copilot_agents import check_repository

PROFILE = """---
name: Test Agent
description: Offline quality review for source code
user-invocable: true
disable-model-invocation: true
include-custom-instructions: true
tools: ["read", "search", "edit", "execute"]
---

""" + ("Verify local evidence, report exactly what was tested, never run CI.\n" * 3)


class AgentProfilePolicyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.agents = self.root / ".github" / "agents"
        self.agents.mkdir(parents=True)
        (self.root / ".github" / "copilot-instructions.md").write_text(
            "# Safe repository boundaries\n", encoding="utf-8"
        )
        self.agent = self.agents / "test.agent.md"
        self.agent.write_text(PROFILE, encoding="utf-8")

    def test_valid_profile_is_accepted(self):
        self.assertEqual(check_repository(self.root), [])

    def test_missing_repository_instructions_is_reported(self):
        (self.root / ".github" / "copilot-instructions.md").unlink()
        self.assertTrue(any("missing .github/copilot-instructions.md" in x
                            for x in check_repository(self.root)))

    def test_missing_agent_profiles_is_reported(self):
        self.agent.unlink()
        self.assertTrue(any("no custom agent profiles" in x
                            for x in check_repository(self.root)))

    def test_automatic_invocation_is_rejected(self):
        self.agent.write_text(PROFILE.replace("disable-model-invocation: true",
                                              "disable-model-invocation: false"),
                              encoding="utf-8")
        self.assertTrue(any("disable-model-invocation must be true" in x
                            for x in check_repository(self.root)))

    def test_unrestricted_tools_are_rejected(self):
        self.agent.write_text(PROFILE.replace(
            '["read", "search", "edit", "execute"]', '["*"]'), encoding="utf-8")
        self.assertTrue(any("unauthorized tool aliases" in x
                            for x in check_repository(self.root)))

    def test_missing_repo_inheritance_is_rejected(self):
        self.agent.write_text(PROFILE.replace("include-custom-instructions: true",
                                              "include-custom-instructions: false"),
                              encoding="utf-8")
        self.assertTrue(any("include-custom-instructions must be true" in x
                            for x in check_repository(self.root)))

    def test_duplicate_display_names_are_rejected(self):
        (self.agents / "another.agent.md").write_text(PROFILE, encoding="utf-8")
        self.assertTrue(any("duplicate agent name" in x
                            for x in check_repository(self.root)))

    def test_invalid_json_tool_list_is_rejected(self):
        self.agent.write_text(PROFILE.replace(
            '["read", "search", "edit", "execute"]', "[read, search]"), encoding="utf-8")
        self.assertTrue(any("JSON-style YAML" in x
                            for x in check_repository(self.root)))

    def test_duplicate_frontmatter_fields_are_rejected(self):
        self.agent.write_text(PROFILE.replace(
            "name: Test Agent", "name: Test Agent\nname: Extra Agent"), encoding="utf-8")
        self.assertTrue(any("duplicate frontmatter field" in x
                            for x in check_repository(self.root)))

    def test_missing_frontmatter_marker_is_rejected(self):
        self.agent.write_text(PROFILE.removeprefix("---\n"), encoding="utf-8")
        self.assertTrue(any("missing opening YAML frontmatter" in x
                            for x in check_repository(self.root)))

    def test_empty_prompt_is_rejected(self):
        self.agent.write_text(PROFILE.split("---\n\n")[0] + "---\n", encoding="utf-8")
        self.assertTrue(any("prompt is missing or too short" in x
                            for x in check_repository(self.root)))


if __name__ == "__main__":
    unittest.main()
