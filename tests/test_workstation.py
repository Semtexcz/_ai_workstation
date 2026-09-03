import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import workstation


class WorkstationTests(unittest.TestCase):
    def run_with_home(self, func):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"HOME": tmp}):
                return Path(tmp), func(Path(tmp))

    def test_validate_repo_passes(self):
        self.assertEqual(workstation.validate_repo(), [])

    def test_install_into_temp_home(self):
        def scenario(home):
            actions = workstation.install()
            self.assertTrue((home / ".codex" / "AGENTS.md").exists())
            self.assertTrue((home / ".agents" / "skills" / "research").exists())
            self.assertTrue((home / ".cline" / "skills" / "research").exists())
            self.assertTrue((home / ".codex" / "planner.config.toml").exists())
            self.assertTrue((home / ".cline" / "ai-workstation" / "model-tiers.json").exists())
            return actions

        _, actions = self.run_with_home(scenario)
        self.assertTrue(any("installed" in action or "linked" in action for action in actions))

    def test_idempotent_reinstall(self):
        def scenario(home):
            workstation.install()
            second = workstation.install()
            return second

        _, actions = self.run_with_home(scenario)
        self.assertTrue(any(action.startswith("unchanged") for action in actions))

    def test_uninstall_removes_managed_state(self):
        def scenario(home):
            workstation.install()
            workstation.uninstall()
            self.assertFalse((home / ".codex" / "AGENTS.md").exists())
            self.assertFalse((home / ".agents" / "skills" / "research").exists())
            self.assertFalse((home / ".cline" / "ai-workstation" / "model-tiers.json").exists())

        self.run_with_home(scenario)

    def test_preserves_unmanaged_configuration(self):
        def scenario(home):
            target = home / ".codex" / "planner.config.toml"
            target.parent.mkdir(parents=True)
            target.write_text("user config\n", encoding="utf-8")
            workstation.install()
            backups = list(target.parent.glob("planner.config.toml.backup.*"))
            self.assertEqual(target.read_text(encoding="utf-8").splitlines()[0], "# Managed by _ai_workstation; source: config/models.example.yaml:planner")
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), "user config\n")

        self.run_with_home(scenario)

    def test_model_config_validation_failure(self):
        bad = {
            "tiers": {
                "frontier": {"provider": "x", "model": "m", "reasoning_effort": "bad", "env_key": "KEY", "base_url": "u"},
                "strong": {"provider": "x", "model": "m", "reasoning_effort": "low", "env_key": "KEY", "base_url": "u"},
                "cheap": {"provider": "x", "model": "m", "reasoning_effort": "low", "env_key": "literal-secret", "base_url": "u"},
            }
        }
        errors = workstation.validate_model_config(bad)
        self.assertTrue(any("reasoning_effort" in error for error in errors))
        self.assertTrue(any("env_key" in error for error in errors))

    def test_skill_synchronization_targets_all_skills(self):
        def scenario(home):
            workstation.install()
            expected = {"planning", "research", "source-validation", "task-review"}
            self.assertEqual({p.name for p in (home / ".agents" / "skills").iterdir()}, expected)
            self.assertEqual({p.name for p in (home / ".cline" / "skills").iterdir()}, expected)

        self.run_with_home(scenario)


if __name__ == "__main__":
    unittest.main()
