import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import workstation


def impl(configured=False, provider="openai", model="", effort="medium", harness="codex"):
    entry = {
        "configured": configured,
        "provider": provider,
        "model": model,
        "reasoning_effort": effort,
    }
    if harness == "codex":
        entry["auth"] = "codex" if provider == "openai" else "env"
        if provider != "openai":
            entry.update(
                {
                    "codex_provider_id": f"{provider}-workstation",
                    "provider_name": f"{provider} compatible",
                    "base_url": f"https://{provider}.example.test/v1",
                    "env_key": "EXAMPLE_PROVIDER_API_KEY",
                }
            )
    return entry


def v2_config(codex_tiers=(), cline_tiers=(), cline_providers=None):
    cline_providers = cline_providers or {}
    tiers = {}
    for tier, effort in (("frontier", "high"), ("strong", "medium"), ("cheap", "low")):
        tiers[tier] = {
            "codex": impl(tier in codex_tiers, "openai", f"codex-{tier}-model" if tier in codex_tiers else "", effort, "codex"),
            "cline": impl(
                tier in cline_tiers,
                cline_providers.get(tier, "anthropic"),
                f"cline-{tier}-model" if tier in cline_tiers else "",
                effort,
                "cline",
            ),
        }
    return {"version": 2, "tiers": tiers}


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

    def test_fully_unconfigured_workstation_passes_with_warnings(self):
        result = workstation.validate_repo()
        self.assertEqual(result.errors, [])
        self.assertTrue(any("Codex tier 'frontier' is UNCONFIGURED" in warning for warning in result.warnings))
        self.assertTrue(any("Cline tier 'cheap' is UNCONFIGURED" in warning for warning in result.warnings))

    def test_all_codex_tiers_configured_no_cline_tiers(self):
        self.write_local(v2_config(codex_tiers=workstation.TIERS))
        result = workstation.validate_repo()
        self.assertEqual(result.errors, [])
        self.assertTrue(any("Codex tier 'cheap'" in passed for passed in result.passes))
        self.assertTrue(any("Cline tier 'cheap' is UNCONFIGURED" in warning for warning in result.warnings))

    def test_all_cline_tiers_configured_no_codex_tiers(self):
        self.write_local(v2_config(cline_tiers=workstation.TIERS))
        result = workstation.validate_repo()
        self.assertEqual(result.errors, [])
        self.assertTrue(any("Cline tier 'frontier'" in passed for passed in result.passes))
        self.assertTrue(any("Codex tier 'strong' is UNCONFIGURED" in warning for warning in result.warnings))

    def test_mixed_cline_providers_per_tier(self):
        self.write_local(
            v2_config(
                cline_tiers=workstation.TIERS,
                cline_providers={"frontier": "anthropic", "strong": "gemini", "cheap": "deepseek"},
            )
        )
        self.assertEqual(workstation.build_cline_command("frontier", ["design"])[2], "anthropic")
        self.assertEqual(workstation.build_cline_command("strong", ["compare"])[2], "gemini")
        self.assertEqual(workstation.build_cline_command("cheap", ["extract"])[2], "deepseek")

    def test_partially_configured_tiers_are_valid(self):
        self.write_local(v2_config(codex_tiers=("cheap",), cline_tiers=("frontier",)))
        result = workstation.validate_repo()
        self.assertEqual(result.errors, [])
        self.assertTrue(any("Codex tier 'cheap'" in passed for passed in result.passes))
        self.assertTrue(any("Cline tier 'frontier'" in passed for passed in result.passes))
        self.assertTrue(any("Codex tier 'strong' is UNCONFIGURED" in warning for warning in result.warnings))

    def test_fully_configured_workstation(self):
        self.write_local(v2_config(codex_tiers=workstation.TIERS, cline_tiers=workstation.TIERS))
        result = workstation.validate_repo()
        self.assertEqual(result.errors, [])
        self.assertFalse(any("UNCONFIGURED" in warning for warning in result.warnings))

    def test_old_version_fails_clearly(self):
        self.write_local({"version": 1, "tiers": {"cheap": {"configured": True, "provider": "openai", "model": "x"}}})
        result = workstation.validate_repo()
        self.assertTrue(any("version must be 2" in error for error in result.errors))

    def test_malformed_local_config_fails_validation(self):
        self.local_path.write_text("{bad json", encoding="utf-8")
        result = workstation.validate_repo()
        self.assertTrue(any("valid JSON" in error for error in result.errors))

    def test_local_config_literal_secret_fails_validation(self):
        config = v2_config(codex_tiers=("cheap",))
        config["api_key"] = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
        self.write_local(config)
        result = workstation.validate_repo()
        self.assertTrue(any("literal secret" in error for error in result.errors))

    def test_ignored_local_config_is_not_treated_as_committed_content(self):
        self.write_local(v2_config(codex_tiers=("cheap",)))
        result = workstation.validate_secret_state()
        self.assertFalse(any("must remain untracked" in error for error in result.errors))

    def test_builtin_openai_provider_rendering_does_not_redefine_provider(self):
        tier = v2_config(codex_tiers=("cheap",))["tiers"]["cheap"]["codex"]
        rendered = workstation.render_codex_profile("cheap", tier)
        self.assertIn('model_provider = "openai"', rendered)
        self.assertNotIn("[model_providers.openai]", rendered)

    def test_custom_provider_rendering_defines_non_reserved_provider(self):
        tier = impl(True, "openai-compatible", "custom-model", "low", "codex")
        rendered = workstation.render_codex_profile("cheap", tier)
        self.assertIn('model_provider = "openai-compatible-workstation"', rendered)
        self.assertIn("[model_providers.openai-compatible-workstation]", rendered)
        self.assertIn('env_key = "EXAMPLE_PROVIDER_API_KEY"', rendered)

    def test_no_profile_generated_for_unconfigured_codex_tier(self):
        self.write_local(v2_config(codex_tiers=("cheap",)))

        def scenario(home):
            workstation.install()
            self.assertTrue((home / ".codex" / "cheap.config.toml").exists())
            self.assertTrue((home / ".codex" / "worker.config.toml").exists())
            self.assertFalse((home / ".codex" / "strong.config.toml").exists())
            self.assertFalse((home / ".codex" / "analyst.config.toml").exists())

        self.run_with_home(scenario)

    def test_role_mapping_uses_codex_tiers(self):
        self.write_local(v2_config(codex_tiers=("frontier", "strong", "cheap")))

        def scenario(home):
            workstation.install()
            planner = (home / ".codex" / "planner.config.toml").read_text(encoding="utf-8")
            worker = (home / ".codex" / "worker.config.toml").read_text(encoding="utf-8")
            self.assertIn('model = "codex-frontier-model"', planner)
            self.assertIn('model = "codex-cheap-model"', worker)

        self.run_with_home(scenario)

    def test_cline_command_uses_cline_config_not_codex_config(self):
        self.write_local(v2_config(codex_tiers=("cheap",), cline_tiers=("cheap",), cline_providers={"cheap": "gemini"}))
        command = workstation.build_cline_command("cheap", ["extract"])
        self.assertEqual(command, ["cline", "--provider", "gemini", "--model", "cline-cheap-model", "--thinking", "low", "extract"])

    def test_missing_cline_tier_fails_clearly(self):
        self.write_local(v2_config(codex_tiers=("cheap",)))
        with self.assertRaisesRegex(workstation.WorkstationError, "Cline implementation of tier 'cheap' is UNCONFIGURED"):
            workstation.build_cline_command("cheap", ["hello"])

    def test_global_agents_installed_from_same_source(self):
        def scenario(home):
            workstation.install()
            canonical = (workstation.REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
            codex = (home / ".codex" / "AGENTS.md").read_text(encoding="utf-8")
            shared = (home / ".agents" / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn(canonical, codex)
            self.assertIn(canonical, shared)
            workstation.uninstall()
            self.assertFalse((home / ".codex" / "AGENTS.md").exists())
            self.assertFalse((home / ".agents" / "AGENTS.md").exists())

        self.run_with_home(scenario)

    def test_namespaced_global_skills_installed_to_both_harnesses(self):
        def scenario(home):
            workstation.install()
            expected = {"generic-planning", "generic-research", "generic-source-validation", "generic-task-review"}
            self.assertEqual({p.name for p in (home / ".agents" / "skills").iterdir()}, expected)
            self.assertEqual({p.name for p in (home / ".cline" / "skills").iterdir()}, expected)
            self.assertNotIn("planning", {p.name for p in (home / ".agents" / "skills").iterdir()})
            self.assertNotIn("research", {p.name for p in (home / ".cline" / "skills").iterdir()})

        self.run_with_home(scenario)

    def test_status_shows_per_harness_state(self):
        self.write_local(v2_config(codex_tiers=("cheap",), cline_tiers=("frontier", "cheap")))

        def scenario(home):
            workstation.install()
            lines = workstation.status()
            self.assertIn("frontier", lines)
            self.assertIn("  Codex: UNCONFIGURED", lines)
            self.assertIn("  Cline: configured", lines)
            self.assertIn("cheap", lines)

        self.run_with_home(scenario)

    def test_preserves_unmanaged_file(self):
        self.write_local(v2_config(codex_tiers=("cheap",)))

        def scenario(home):
            target = home / ".codex" / "worker.config.toml"
            target.parent.mkdir(parents=True)
            target.write_text("user config\n", encoding="utf-8")
            workstation.install()
            backups = list(target.parent.glob("worker.config.toml.backup.*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), "user config\n")
            workstation.uninstall()
            self.assertFalse(target.exists())
            self.assertTrue(backups[0].exists())

        self.run_with_home(scenario)

    def test_preserves_unmanaged_directory(self):
        def scenario(home):
            target = home / ".agents" / "skills" / "generic-research"
            target.mkdir(parents=True)
            (target / "note.txt").write_text("mine", encoding="utf-8")
            workstation.install()
            backups = list(target.parent.glob("generic-research.backup.*"))
            self.assertEqual(len(backups), 1)
            self.assertTrue((backups[0] / "note.txt").exists())
            workstation.uninstall()
            self.assertTrue(backups[0].exists())

        self.run_with_home(scenario)

    def test_preserves_unmanaged_symlink(self):
        def scenario(home):
            source = home / "other-skill"
            source.mkdir()
            target = home / ".agents" / "skills" / "generic-research"
            target.parent.mkdir(parents=True)
            target.symlink_to(source, target_is_directory=True)
            workstation.install()
            backups = list(target.parent.glob("generic-research.backup.*"))
            self.assertEqual(len(backups), 1)
            self.assertTrue(backups[0].is_symlink())
            workstation.uninstall()
            self.assertTrue(backups[0].is_symlink())

        self.run_with_home(scenario)

    def test_preserves_broken_unmanaged_symlink(self):
        def scenario(home):
            target = home / ".agents" / "skills" / "generic-research"
            target.parent.mkdir(parents=True)
            target.symlink_to(home / "missing")
            self.assertTrue(target.is_symlink())
            self.assertFalse(target.exists())
            workstation.install()
            backups = list(target.parent.glob("generic-research.backup.*"))
            self.assertEqual(len(backups), 1)
            self.assertTrue(backups[0].is_symlink())
            workstation.uninstall()
            self.assertTrue(backups[0].is_symlink())

        self.run_with_home(scenario)

    def test_copied_fallback_directory_is_owned_and_uninstalled(self):
        def scenario(home):
            workstation.install()
            self.assertTrue((home / ".agents" / "skills" / "generic-research" / ".ai-workstation-managed").exists())
            workstation.uninstall()
            self.assertFalse((home / ".agents" / "skills" / "generic-research").exists())

        self.run_with_home(scenario, {"AI_WORKSTATION_FORCE_COPY": "1"})

    def test_idempotent_reinstall(self):
        self.write_local(v2_config(codex_tiers=("cheap",), cline_tiers=("cheap",)))

        def scenario(home):
            workstation.install()
            return workstation.install()

        _, actions = self.run_with_home(scenario)
        self.assertTrue(any(action.startswith("unchanged") for action in actions))

    def test_ci_compatible_state_without_local_config(self):
        result = workstation.validate_repo()
        self.assertEqual(result.errors, [])


if __name__ == "__main__":
    unittest.main()
