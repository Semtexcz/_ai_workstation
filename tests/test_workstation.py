import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import workstation


def valid_local_config(provider="openai"):
    tiers = {}
    for tier, model, effort in (
        ("frontier", "frontier-model", "high"),
        ("strong", "strong-model", "medium"),
        ("cheap", "cheap-model", "low"),
    ):
        entry = {
            "configured": True,
            "provider": provider,
            "model": model,
            "reasoning_effort": effort,
            "auth": "codex" if provider == "openai" else "env",
        }
        if provider != "openai":
            entry.update(
                {
                    "codex_provider_id": f"{provider}-workstation",
                    "base_url": "https://models.example.test/v1",
                    "env_key": "EXAMPLE_PROVIDER_API_KEY",
                }
            )
        tiers[tier] = entry
    return {"version": 1, "tiers": tiers}


class WorkstationTests(unittest.TestCase):
    def setUp(self):
        self.local_path = workstation.models_local_path()
        self.original_local = self.local_path.read_text(encoding="utf-8") if self.local_path.exists() else None
        if self.local_path.exists():
            self.local_path.unlink()

    def tearDown(self):
        if self.local_path.exists():
            self.local_path.unlink()
        if self.original_local is not None:
            self.local_path.write_text(self.original_local, encoding="utf-8")

    def write_local(self, data):
        self.local_path.write_text(json.dumps(data), encoding="utf-8")

    def run_with_home(self, func, extra_env=None):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"HOME": tmp}
            if extra_env:
                env.update(extra_env)
            with mock.patch.dict(os.environ, env):
                return Path(tmp), func(Path(tmp))

    def test_validate_repo_passes_without_local_config(self):
        result = workstation.validate_repo()
        self.assertEqual(result.errors, [])
        self.assertTrue(any("UNCONFIGURED" in warning for warning in result.warnings))

    def test_valid_local_config_is_accepted(self):
        self.write_local(valid_local_config())
        result = workstation.validate_repo()
        self.assertEqual(result.errors, [])
        self.assertFalse(any("UNCONFIGURED" in warning for warning in result.warnings))

    def test_malformed_local_config_fails_validation(self):
        self.local_path.write_text("{bad json", encoding="utf-8")
        result = workstation.validate_repo()
        self.assertTrue(any("valid JSON" in error for error in result.errors))

    def test_local_config_literal_secret_fails_validation(self):
        config = valid_local_config()
        config["api_key"] = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
        self.write_local(config)
        result = workstation.validate_repo()
        self.assertTrue(any("literal secret" in error for error in result.errors))

    def test_ignored_local_config_is_not_treated_as_committed_content(self):
        self.write_local(valid_local_config())
        result = workstation.validate_secret_state()
        self.assertFalse(any("must remain untracked" in error for error in result.errors))

    def test_unconfigured_install_skips_codex_model_profiles(self):
        def scenario(home):
            actions = workstation.install()
            self.assertTrue((home / ".codex" / "AGENTS.md").exists())
            self.assertFalse((home / ".codex" / "cheap.config.toml").exists())
            self.assertTrue(any("UNCONFIGURED" in action for action in actions))

        self.run_with_home(scenario)

    def test_configured_install_creates_profiles_and_launcher(self):
        self.write_local(valid_local_config())

        def scenario(home):
            workstation.install()
            self.assertTrue((home / ".codex" / "planner.config.toml").exists())
            self.assertTrue((home / ".local" / "bin" / "ai-cline").exists())
            profile = (home / ".codex" / "cheap.config.toml").read_text(encoding="utf-8")
            self.assertIn('model_provider = "openai"', profile)
            self.assertNotIn("[model_providers.openai]", profile)

        self.run_with_home(scenario)

    def test_idempotent_reinstall(self):
        self.write_local(valid_local_config())

        def scenario(home):
            workstation.install()
            return workstation.install()

        _, actions = self.run_with_home(scenario)
        self.assertTrue(any(action.startswith("unchanged") for action in actions))

    def test_uninstall_removes_managed_state(self):
        self.write_local(valid_local_config())

        def scenario(home):
            workstation.install()
            workstation.uninstall()
            self.assertFalse((home / ".codex" / "AGENTS.md").exists())
            self.assertFalse((home / ".agents" / "skills" / "research").exists())
            self.assertFalse((home / ".cline" / "ai-workstation" / "model-tiers.json").exists())
            self.assertFalse((home / ".local" / "bin" / "ai-cline").exists())

        self.run_with_home(scenario)

    def test_preserves_unmanaged_file(self):
        self.write_local(valid_local_config())

        def scenario(home):
            target = home / ".codex" / "planner.config.toml"
            target.parent.mkdir(parents=True)
            target.write_text("user config\n", encoding="utf-8")
            workstation.install()
            backups = list(target.parent.glob("planner.config.toml.backup.*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), "user config\n")
            workstation.uninstall()
            self.assertFalse(target.exists())
            self.assertTrue(backups[0].exists())

        self.run_with_home(scenario)

    def test_preserves_unmanaged_directory(self):
        def scenario(home):
            target = home / ".agents" / "skills" / "research"
            target.mkdir(parents=True)
            (target / "note.txt").write_text("mine", encoding="utf-8")
            workstation.install()
            backups = list(target.parent.glob("research.backup.*"))
            self.assertEqual(len(backups), 1)
            self.assertTrue((backups[0] / "note.txt").exists())
            workstation.uninstall()
            self.assertTrue(backups[0].exists())

        self.run_with_home(scenario)

    def test_preserves_unmanaged_symlink(self):
        def scenario(home):
            source = home / "other-skill"
            source.mkdir()
            target = home / ".agents" / "skills" / "research"
            target.parent.mkdir(parents=True)
            target.symlink_to(source, target_is_directory=True)
            workstation.install()
            backups = list(target.parent.glob("research.backup.*"))
            self.assertEqual(len(backups), 1)
            self.assertTrue(backups[0].is_symlink())
            workstation.uninstall()
            self.assertTrue(backups[0].is_symlink())

        self.run_with_home(scenario)

    def test_preserves_broken_unmanaged_symlink(self):
        def scenario(home):
            target = home / ".agents" / "skills" / "research"
            target.parent.mkdir(parents=True)
            target.symlink_to(home / "missing")
            self.assertTrue(target.is_symlink())
            self.assertFalse(target.exists())
            workstation.install()
            backups = list(target.parent.glob("research.backup.*"))
            self.assertEqual(len(backups), 1)
            self.assertTrue(backups[0].is_symlink())
            workstation.uninstall()
            self.assertTrue(backups[0].is_symlink())

        self.run_with_home(scenario)

    def test_managed_symlink_can_be_replaced(self):
        def scenario(home):
            workstation.install()
            target = home / ".agents" / "skills" / "research"
            self.assertTrue(workstation.is_managed_symlink(target))
            second = workstation.install()
            self.assertTrue(any(f"unchanged {target}" == action for action in second))

        self.run_with_home(scenario)

    def test_copied_fallback_directory_is_owned_and_uninstalled(self):
        def scenario(home):
            workstation.install()
            copied = [p for p in (home / ".agents" / "skills").iterdir() if p.is_dir() and not p.is_symlink()]
            self.assertTrue(copied)
            self.assertTrue((home / ".agents" / "skills" / "research" / ".ai-workstation-managed").exists())
            workstation.uninstall()
            self.assertFalse((home / ".agents" / "skills" / "research").exists())

        self.run_with_home(scenario, {"AI_WORKSTATION_FORCE_COPY": "1"})

    def test_builtin_openai_provider_rendering_does_not_redefine_provider(self):
        tier = valid_local_config()["tiers"]["cheap"]
        rendered = workstation.render_codex_profile("cheap", tier)
        self.assertIn('model_provider = "openai"', rendered)
        self.assertNotIn("[model_providers.openai]", rendered)

    def test_custom_provider_rendering_defines_non_reserved_provider(self):
        tier = valid_local_config("openai-compatible")["tiers"]["cheap"]
        rendered = workstation.render_codex_profile("cheap", tier)
        self.assertIn('model_provider = "openai-compatible-workstation"', rendered)
        self.assertIn("[model_providers.openai-compatible-workstation]", rendered)
        self.assertIn('env_key = "EXAMPLE_PROVIDER_API_KEY"', rendered)

    def test_cline_tier_command_generation(self):
        self.write_local(valid_local_config("cline"))
        command = workstation.build_cline_command("cheap", ["extract these values"])
        self.assertEqual(
            command,
            ["cline", "--provider", "cline", "--model", "cheap-model", "--thinking", "low", "extract these values"],
        )

    def test_unconfigured_cline_tier_command_fails(self):
        with self.assertRaises(workstation.WorkstationError):
            workstation.build_cline_command("cheap", ["hello"])

    def test_skill_synchronization_targets_all_skills(self):
        def scenario(home):
            workstation.install()
            expected = {"planning", "research", "source-validation", "task-review"}
            self.assertEqual({p.name for p in (home / ".agents" / "skills").iterdir()}, expected)
            self.assertEqual({p.name for p in (home / ".cline" / "skills").iterdir()}, expected)

        self.run_with_home(scenario)


if __name__ == "__main__":
    unittest.main()
