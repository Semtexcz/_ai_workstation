#!/usr/bin/env python3
"""Install, launch, and validate the portable AI workstation configuration."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
MANAGED_MARKER = "Managed by _ai_workstation"
TIERS = ("frontier", "strong", "cheap")
HARNESSES = ("codex", "cline")
ROLE_TIERS = {
    "planner": "frontier",
    "analyst": "strong",
    "worker": "cheap",
    "reviewer": "strong",
}
REASONING = {"minimal", "low", "medium", "high", "xhigh"}
BUILTIN_CODEX_PROVIDERS = {"openai", "ollama", "lmstudio"}
GLOBAL_INSTRUCTION_SOURCES = ("AGENTS.md", "policies/python-engineering.md")
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{16,}"),
]


class WorkstationError(Exception):
    pass


@dataclass
class CheckResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    passes: list[str] = field(default_factory=list)

    def extend(self, other: "CheckResult") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.passes.extend(other.passes)


def home() -> Path:
    return Path(os.environ.get("HOME", str(Path.home()))).expanduser()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkstationError(f"{path} must contain valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise WorkstationError(f"{path} must contain a JSON object")
    return data


def workstation_config() -> dict[str, Any]:
    return load_json(REPO_ROOT / "config" / "workstation.json")


def models_local_path() -> Path:
    return REPO_ROOT / "config" / "models.local.json"


def models_example_path() -> Path:
    return REPO_ROOT / "config" / "models.example.json"


def models_path() -> Path:
    local = models_local_path()
    return local if local.exists() else models_example_path()


def models_config() -> dict[str, Any]:
    return load_json(models_path())


def global_instruction_source_paths() -> list[Path]:
    return [REPO_ROOT / rel for rel in GLOBAL_INSTRUCTION_SOURCES]


def composed_global_instructions() -> str:
    parts = [path.read_text(encoding="utf-8").strip() for path in global_instruction_source_paths()]
    return "\n\n".join(parts) + "\n"


def composed_global_instruction_source() -> str:
    return " + ".join(GLOBAL_INSTRUCTION_SOURCES)


def using_local_models() -> bool:
    return models_local_path().exists()


def managed_header(source: str) -> str:
    return f"# {MANAGED_MARKER}; source: {source}\n"


def backup_path(path: Path) -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = path.with_name(f"{path.name}.backup.{stamp}")
    suffix = 1
    while candidate.exists() or candidate.is_symlink():
        candidate = path.with_name(f"{path.name}.backup.{stamp}.{suffix}")
        suffix += 1
    return candidate


def resolved_symlink_target(path: Path) -> Path | None:
    if not path.is_symlink():
        return None
    raw = Path(os.readlink(path))
    if not raw.is_absolute():
        raw = path.parent / raw
    return raw.resolve(strict=False)


def path_is_under_repo(path: Path) -> bool:
    resolved = path.resolve(strict=False)
    repo = REPO_ROOT.resolve(strict=False)
    return resolved == repo or repo in resolved.parents


def is_managed_file(path: Path) -> bool:
    if not path.exists() or path.is_symlink() or not path.is_file():
        return False
    try:
        return MANAGED_MARKER in path.read_text(encoding="utf-8", errors="ignore")[:200]
    except OSError:
        return False


def is_managed_symlink(path: Path) -> bool:
    target = resolved_symlink_target(path)
    return target is not None and path_is_under_repo(target)


def is_managed_copied_dir(path: Path) -> bool:
    return path.is_dir() and not path.is_symlink() and (path / ".ai-workstation-managed").exists()


def prepare_target(path: Path, actions: list[str]) -> None:
    if path.is_symlink():
        if is_managed_symlink(path):
            path.unlink()
            actions.append(f"replaced managed symlink {path}")
            return
        backup = backup_path(path)
        path.rename(backup)
        actions.append(f"preserved unmanaged symlink {path} as {backup}")
        return
    if path.exists() and is_managed_file(path):
        path.unlink()
        actions.append(f"replaced managed file {path}")
        return
    if path.exists() and is_managed_copied_dir(path):
        shutil.rmtree(path)
        actions.append(f"replaced managed directory {path}")
        return
    if path.exists():
        backup = backup_path(path)
        path.rename(backup)
        actions.append(f"preserved unmanaged {path} as {backup}")


def write_managed(path: Path, body: str, source: str, actions: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = managed_header(source) + body
    if path.exists() and not path.is_symlink() and path.is_file() and path.read_text(encoding="utf-8") == content:
        actions.append(f"unchanged {path}")
        return
    prepare_target(path, actions)
    path.write_text(content, encoding="utf-8")
    actions.append(f"installed {path}")


def link_managed_dir(source: Path, target: Path, actions: list[str]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() and resolved_symlink_target(target) == source.resolve(strict=False):
        actions.append(f"unchanged {target}")
        return
    prepare_target(target, actions)
    if os.environ.get("AI_WORKSTATION_FORCE_COPY") == "1":
        shutil.copytree(source, target)
        (target / ".ai-workstation-managed").write_text(str(source), encoding="utf-8")
        actions.append(f"copied {source} to {target}")
        return
    try:
        target.symlink_to(source, target_is_directory=True)
        actions.append(f"linked {target} -> {source}")
    except OSError:
        shutil.copytree(source, target)
        (target / ".ai-workstation-managed").write_text(str(source), encoding="utf-8")
        actions.append(f"copied {source} to {target}")


def remove_owned(target: Path, actions: list[str]) -> None:
    if not target.exists() and not target.is_symlink():
        return
    if target.is_symlink() and is_managed_symlink(target):
        target.unlink()
        actions.append(f"removed {target}")
    elif is_managed_file(target):
        target.unlink()
        actions.append(f"removed {target}")
    elif is_managed_copied_dir(target):
        shutil.rmtree(target)
        actions.append(f"removed {target}")
    else:
        actions.append(f"left unmanaged {target}")


def tier_is_configured(tier: dict[str, Any]) -> bool:
    return tier.get("configured") is True and bool(tier.get("model"))


def tier_impl(config: dict[str, Any], tier_name: str, harness: str) -> dict[str, Any] | None:
    tiers = config.get("tiers", {})
    if not isinstance(tiers, dict):
        return None
    tier = tiers.get(tier_name)
    if not isinstance(tier, dict):
        return None
    impl = tier.get(harness)
    return impl if isinstance(impl, dict) else None


def harness_tier_is_configured(config: dict[str, Any], tier_name: str, harness: str) -> bool:
    impl = tier_impl(config, tier_name, harness)
    return impl is not None and tier_is_configured(impl)


def any_harness_tier_configured(config: dict[str, Any], harness: str) -> bool:
    return any(harness_tier_is_configured(config, tier, harness) for tier in TIERS)


def all_harness_tiers_configured(config: dict[str, Any], harness: str) -> bool:
    return all(harness_tier_is_configured(config, tier, harness) for tier in TIERS)


def codex_provider_id(tier: dict[str, Any]) -> str:
    provider = tier["provider"]
    if provider == "openai":
        return "openai"
    custom_id = tier.get("codex_provider_id") or provider
    if custom_id in BUILTIN_CODEX_PROVIDERS:
        raise WorkstationError(f"custom Codex provider id {custom_id!r} is reserved")
    return custom_id


def render_codex_profile(tier_name: str, tier: dict[str, Any]) -> str:
    provider_id = codex_provider_id(tier)
    lines = [
        f'model = "{tier["model"]}"',
        f'model_provider = "{provider_id}"',
        f'model_reasoning_effort = "{tier["reasoning_effort"]}"',
        "",
    ]
    if provider_id != "openai":
        lines.extend(
            [
                f"[model_providers.{provider_id}]",
                f'name = "{tier.get("provider_name", provider_id)}"',
                f'base_url = "{tier["base_url"]}"',
                f'env_key = "{tier["env_key"]}"',
                'wire_api = "responses"',
                "",
            ]
        )
    lines.append(f"# Logical tier: {tier_name}")
    rendered = "\n".join(lines) + "\n"
    tomllib.loads(rendered)
    return rendered


def render_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def obvious_secret_errors(path: Path, label: str) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    errors = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            errors.append(f"possible literal secret in {label}")
            break
    return errors


def validate_harness_impl(tier_name: str, harness: str, impl: dict[str, Any], *, local: bool) -> CheckResult:
    result = CheckResult()
    label = f"{harness} tier '{tier_name}'"
    if "configured" in impl and not isinstance(impl["configured"], bool):
        result.errors.append(f"{label}.configured must be boolean")
    configured = tier_is_configured(impl)
    if not configured:
        result.warnings.append(f"{harness.capitalize()} tier '{tier_name}' is UNCONFIGURED")
        return result
    result.passes.append(f"{harness.capitalize()} tier '{tier_name}'")
    if not local:
        result.warnings.append(f"{label} is configured in example config; prefer local config")
    for key in ("provider", "model", "reasoning_effort"):
        if not isinstance(impl.get(key), str) or not impl[key]:
            result.errors.append(f"{label}.{key} must be a non-empty string when configured")
    effort = impl.get("reasoning_effort")
    if isinstance(effort, str) and effort not in REASONING:
        result.errors.append(f"{label}.reasoning_effort must be one of {sorted(REASONING)}")
    if harness == "codex":
        provider = impl.get("provider")
        if provider == "openai":
            return result
        provider_id = impl.get("codex_provider_id") or provider
        if provider_id in BUILTIN_CODEX_PROVIDERS:
            result.errors.append(f"{label}.codex_provider_id must not use reserved provider id {provider_id!r}")
        for key in ("base_url", "env_key"):
            if not isinstance(impl.get(key), str) or not impl[key]:
                result.errors.append(f"{label}.{key} must be a non-empty string for custom providers")
        env_key = impl.get("env_key", "")
        if isinstance(env_key, str) and env_key and not re.fullmatch(r"[A-Z][A-Z0-9_]*", env_key):
            result.errors.append(f"{label}.env_key must name an environment variable, not a literal secret")
    return result


def validate_model_config(config: dict[str, Any], *, local: bool) -> CheckResult:
    result = CheckResult()
    version = config.get("version")
    if version != 2:
        result.errors.append(f"model config version must be 2; found {version!r}. Copy config/models.example.json and migrate tiers.<tier> to tiers.<tier>.codex/cline.")
        return result
    tiers = config.get("tiers")
    if not isinstance(tiers, dict):
        result.errors.append("model config must contain a tiers object")
        return result
    for tier_name in TIERS:
        entry = tiers.get(tier_name)
        if not isinstance(entry, dict):
            result.errors.append(f"missing model tier: {tier_name}")
            continue
        for harness in HARNESSES:
            impl = entry.get(harness)
            if not isinstance(impl, dict):
                result.errors.append(f"{tier_name}.{harness} must be an object")
                continue
            result.extend(validate_harness_impl(tier_name, harness, impl, local=local))
    return result


def skill_dirs() -> list[Path]:
    root = REPO_ROOT / "skills"
    return sorted(path for path in root.iterdir() if path.is_dir())


def validate_skills() -> CheckResult:
    result = CheckResult()
    expected = {"generic-research", "generic-source-validation", "generic-planning", "generic-task-review"}
    found = {path.name for path in skill_dirs()}
    if found != expected:
        result.errors.append(f"skills must be exactly {sorted(expected)}, found {sorted(found)}")
    for path in skill_dirs():
        skill = path / "SKILL.md"
        if not skill.exists():
            result.errors.append(f"missing {skill}")
            continue
        text = skill.read_text(encoding="utf-8")
        if f"name: {path.name}" not in text:
            result.errors.append(f"{skill} name must match directory {path.name}")
        for token in ("description:", "## Trigger", "## Boundaries", "## Escalate"):
            if token not in text:
                result.errors.append(f"{skill} missing {token}")
    return result


def tracked_files() -> list[Path]:
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=REPO_ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError):
        return [path.relative_to(REPO_ROOT) for path in REPO_ROOT.rglob("*") if path.is_file() and ".git" not in path.parts]
    return [Path(item.decode()) for item in proc.stdout.split(b"\0") if item]


def validate_secret_state() -> CheckResult:
    result = CheckResult()
    for rel in tracked_files():
        if rel.parent.as_posix() == "config" and rel.name.startswith("models.local."):
            result.errors.append(f"{rel.as_posix()} must remain untracked")
        path = REPO_ROOT / rel
        if path.is_file():
            result.errors.extend(obvious_secret_errors(path, rel.as_posix()))
    local = models_local_path()
    if local.exists():
        result.errors.extend(obvious_secret_errors(local, "local model config"))
    return result


def validate_repo() -> CheckResult:
    result = CheckResult()
    required = [
        "README.md",
        "AGENTS.md",
        "policies/python-engineering.md",
        "Makefile",
        ".gitignore",
        "config/models.example.json",
        "config/workstation.json",
        "adapters/codex/README.md",
        "adapters/cline/README.md",
        "docs/architecture.md",
        "docs/configuration.md",
        "docs/security.md",
        "scripts/workstation.py",
        "tests/test_workstation.py",
    ]
    for rel in required:
        if not (REPO_ROOT / rel).exists():
            result.errors.append(f"missing {rel}")
    for rel in ("config/models.example.json", "config/workstation.json"):
        try:
            load_json(REPO_ROOT / rel)
        except WorkstationError as exc:
            result.errors.append(str(exc))
    try:
        result.extend(validate_model_config(models_config(), local=using_local_models()))
    except WorkstationError as exc:
        result.errors.append(str(exc))
    result.extend(validate_skills())
    result.extend(validate_secret_state())
    marker = "TO" + "DO"
    for rel in tracked_files():
        path = REPO_ROOT / rel
        if path.is_file() and "__pycache__" not in path.parts and marker in path.read_text(encoding="utf-8", errors="ignore"):
            result.errors.append("unfinished placeholders remain")
            break
    return result


def validate_generated_codex() -> CheckResult:
    result = CheckResult()
    try:
        config = models_config()
    except WorkstationError as exc:
        result.errors.append(str(exc))
        return result
    model_check = validate_model_config(config, local=using_local_models())
    if model_check.errors:
        result.errors.extend(model_check.errors)
        return result
    for tier_name in TIERS:
        impl = tier_impl(config, tier_name, "codex")
        if not isinstance(impl, dict) or not tier_is_configured(impl):
            continue
        try:
            rendered = render_codex_profile(tier_name, impl)
            parsed = tomllib.loads(rendered)
        except (WorkstationError, tomllib.TOMLDecodeError) as exc:
            result.errors.append(f"invalid Codex TOML for {tier_name}: {exc}")
            continue
        if parsed.get("model_provider") == "openai" and "model_providers" in parsed:
            result.errors.append(f"{tier_name} redefines built-in Codex provider openai")
    return result


def validate_links() -> CheckResult:
    result = CheckResult()
    for root in (home() / ".agents" / "skills", home() / ".cline" / "skills"):
        if not root.exists():
            continue
        for path in root.iterdir():
            if path.is_symlink() and not path.exists() and is_managed_symlink(path):
                result.errors.append(f"broken managed symlink: {path}")
    return result


def validate_installation_state() -> CheckResult:
    result = CheckResult()
    result.extend(validate_links())
    expected_global_instructions = managed_header(composed_global_instruction_source()) + composed_global_instructions()
    for path in (home() / ".codex" / "AGENTS.md", home() / ".agents" / "AGENTS.md"):
        if path.exists() and is_managed_file(path) and path.read_text(encoding="utf-8") != expected_global_instructions:
            result.errors.append(f"installed global instructions are stale: {path}")
    models = models_config()
    if any_harness_tier_configured(models, "codex"):
        expected_profiles = [tier for tier in TIERS if harness_tier_is_configured(models, tier, "codex")]
        expected_profiles.extend(role for role, tier in ROLE_TIERS.items() if harness_tier_is_configured(models, tier, "codex"))
        for name in expected_profiles:
            path = home() / ".codex" / f"{name}.config.toml"
            if path.exists() and is_managed_file(path):
                try:
                    tomllib.loads(path.read_text(encoding="utf-8"))
                except tomllib.TOMLDecodeError as exc:
                    result.errors.append(f"installed Codex profile is invalid TOML: {path}: {exc}")
            else:
                result.warnings.append(f"Codex profile not installed: {path}")
    return result


def model_tier_status_lines() -> list[str]:
    try:
        config = models_config()
    except WorkstationError as exc:
        return [f"Model tiers: invalid ({exc})"]
    lines = ["Model tiers:"]
    tiers = config.get("tiers", {})
    for tier in TIERS:
        lines.append(tier)
        for harness in HARNESSES:
            entry = tier_impl(config, tier, harness)
            status = "configured" if isinstance(entry, dict) and tier_is_configured(entry) else "UNCONFIGURED"
            lines.append(f"  {harness.capitalize()}: {status}")
    return lines


def install() -> list[str]:
    repo_result = validate_repo()
    if repo_result.errors:
        raise WorkstationError("validation failed before install:\n" + "\n".join(repo_result.errors))
    config = workstation_config()
    models = models_config()
    actions: list[str] = []

    global_instructions = composed_global_instructions()
    global_instruction_source = composed_global_instruction_source()
    write_managed(home() / ".codex" / "AGENTS.md", global_instructions, global_instruction_source, actions)
    write_managed(home() / ".agents" / "AGENTS.md", global_instructions, global_instruction_source, actions)
    for skill in skill_dirs():
        link_managed_dir(skill, home() / ".agents" / "skills" / skill.name, actions)
        link_managed_dir(skill, home() / ".cline" / "skills" / skill.name, actions)

    launcher = home() / ".local" / "bin" / "ai-cline"
    write_managed(launcher, f'#!/usr/bin/env sh\nexec "{REPO_ROOT / "scripts" / "workstation.py"}" cline "$@"\n', "scripts/workstation.py", actions)
    launcher.chmod(0o755)

    if any_harness_tier_configured(models, "codex"):
        for tier_name in TIERS:
            impl = tier_impl(models, tier_name, "codex")
            if not isinstance(impl, dict) or not tier_is_configured(impl):
                actions.append(f"Codex tier '{tier_name}' UNCONFIGURED; skipped profile")
                continue
            write_managed(
                home() / ".codex" / f"{tier_name}.config.toml",
                render_codex_profile(tier_name, impl),
                f"config/{models_path().name}:{tier_name}",
                actions,
            )
        for role, tier_name in config["roles"].items():
            impl = tier_impl(models, tier_name, "codex")
            if not isinstance(impl, dict) or not tier_is_configured(impl):
                actions.append(f"Codex role '{role}' skipped because tier '{tier_name}' is UNCONFIGURED")
                continue
            write_managed(
                home() / ".codex" / f"{role}.config.toml",
                render_codex_profile(tier_name, impl) + f"# Logical role: {role}\n",
                f"config/{models_path().name}:{role}",
                actions,
            )
    else:
        actions.append("all Codex tiers UNCONFIGURED; skipped Codex model profiles")

    cline_dir = home() / ".cline" / "ai-workstation"
    write_managed(cline_dir / "model-tiers.json", render_json(models["tiers"]), f"config/{models_path().name}", actions)
    write_managed(cline_dir / "roles.json", render_json(config["roles"]), "config/workstation.json", actions)
    return actions


def uninstall() -> list[str]:
    actions: list[str] = []
    targets = [
        home() / ".codex" / "AGENTS.md",
        home() / ".agents" / "AGENTS.md",
        home() / ".cline" / "ai-workstation" / "model-tiers.json",
        home() / ".cline" / "ai-workstation" / "roles.json",
        home() / ".local" / "bin" / "ai-cline",
    ]
    targets.extend(home() / ".codex" / f"{name}.config.toml" for name in (*TIERS, *ROLE_TIERS.keys()))
    targets.extend(home() / ".agents" / "skills" / skill.name for skill in skill_dirs())
    targets.extend(home() / ".cline" / "skills" / skill.name for skill in skill_dirs())
    for target in targets:
        remove_owned(target, actions)
    return actions


def status() -> list[str]:
    skills_dir = home() / ".agents" / "skills"
    skills_count = sum(1 for path in skills_dir.glob("*") if path.exists()) if skills_dir.exists() else 0
    lines = [
        f"Codex: {'installed' if (home() / '.codex' / 'AGENTS.md').exists() else 'missing'}",
        f"Cline: {'installed' if (home() / '.agents' / 'AGENTS.md').exists() and (home() / '.cline' / 'ai-workstation').exists() else 'missing'}",
        f"Skills: {skills_count} installed",
    ]
    lines.extend(model_tier_status_lines())
    return lines


def build_cline_command(tier_name: str, extra_args: list[str]) -> list[str]:
    config = models_config()
    tier = tier_impl(config, tier_name, "cline")
    if not isinstance(tier, dict) or not tier_is_configured(tier):
        raise WorkstationError(f"Cline implementation of tier {tier_name!r} is UNCONFIGURED")
    command = ["cline", "--provider", tier["provider"], "--model", tier["model"], "--thinking", tier["reasoning_effort"]]
    command.extend(extra_args)
    return command


def run_cline(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="ai-cline")
    parser.add_argument("--print-command", action="store_true")
    parser.add_argument("tier", choices=TIERS)
    parser.add_argument("cline_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = build_cline_command(args.tier, args.cline_args)
    if args.print_command:
        print(json.dumps(command))
        return 0
    completed = subprocess.run(command)
    return completed.returncode


def format_validation(result: CheckResult) -> list[str]:
    lines = ["PASS repository" if not result.errors else "FAIL repository"]
    if not result.errors:
        lines.extend(["PASS skills", "PASS Codex adapter", "PASS Cline adapter", "PASS no tracked secrets detected"])
    for passed in result.passes:
        lines.append(f"PASS {passed}")
    for warning in result.warnings:
        lines.append(f"WARN {warning}")
    for error in result.errors:
        lines.append(f"ERROR {error}")
    return lines


def print_lines(lines: list[str]) -> None:
    for line in lines:
        print(line)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("install", "status", "validate", "update", "uninstall", "cline"))
    args, rest = parser.parse_known_args(argv)
    try:
        if args.command == "install":
            actions = install()
            print("workstation repository validated")
            print_lines(actions)
            print("global skills installed")
            print("Codex adapter configured")
            print("Cline adapter configured")
            models = models_config()
            print("Codex tiers configured" if all_harness_tiers_configured(models, "codex") else "Codex tiers partially configured or UNCONFIGURED")
            print("Cline tiers configured" if all_harness_tiers_configured(models, "cline") else "Cline tiers partially configured or UNCONFIGURED")
            print("no tracked credentials detected")
        elif args.command == "update":
            print_lines(install())
            print("workstation updated")
        elif args.command == "uninstall":
            print_lines(uninstall())
            print("workstation uninstalled")
        elif args.command == "status":
            print_lines(status())
        elif args.command == "validate":
            result = validate_repo()
            result.extend(validate_generated_codex())
            result.extend(validate_installation_state())
            print_lines(format_validation(result))
            return 1 if result.errors else 0
        elif args.command == "cline":
            return run_cline(rest)
    except WorkstationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
