#!/usr/bin/env python3
"""Install and validate the portable AI workstation configuration."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
MANAGED_MARKER = "Managed by _ai_workstation"
TIERS = ("frontier", "strong", "cheap")
ROLE_TIERS = {
    "planner": "frontier",
    "analyst": "strong",
    "worker": "cheap",
    "reviewer": "strong",
}
REASONING = {"minimal", "low", "medium", "high", "xhigh"}
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{16,}"),
]


class WorkstationError(Exception):
    pass


def home() -> Path:
    return Path(os.environ.get("HOME", str(Path.home()))).expanduser()


def load_json_yaml(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkstationError(f"{path} must be JSON-compatible YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise WorkstationError(f"{path} must contain an object")
    return data


def workstation_config() -> dict[str, Any]:
    return load_json_yaml(REPO_ROOT / "config" / "workstation.yaml")


def models_path() -> Path:
    local = REPO_ROOT / "config" / "models.local.yaml"
    return local if local.exists() else REPO_ROOT / "config" / "models.example.yaml"


def models_config() -> dict[str, Any]:
    return load_json_yaml(models_path())


def managed_header(source: str) -> str:
    return f"# {MANAGED_MARKER}; source: {source}\n"


def backup_path(path: Path) -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return path.with_name(f"{path.name}.backup.{stamp}")


def is_managed_file(path: Path) -> bool:
    if not path.exists() or path.is_symlink() or not path.is_file():
        return False
    try:
        return MANAGED_MARKER in path.read_text(encoding="utf-8", errors="ignore")[:200]
    except OSError:
        return False


def is_managed_symlink(path: Path) -> bool:
    if not path.is_symlink():
        return False
    try:
        return REPO_ROOT in path.resolve().parents or path.resolve() == REPO_ROOT
    except FileNotFoundError:
        return False


def prepare_target(path: Path, actions: list[str]) -> None:
    if path.is_symlink():
        path.unlink()
        actions.append(f"replaced managed symlink {path}")
    elif path.exists() and is_managed_file(path):
        path.unlink()
        actions.append(f"replaced managed file {path}")
    elif path.exists():
        backup = backup_path(path)
        path.rename(backup)
        actions.append(f"preserved unmanaged {path} as {backup}")


def write_managed(path: Path, body: str, source: str, actions: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = managed_header(source) + body
    if path.exists() and not path.is_symlink() and path.read_text(encoding="utf-8") == content:
        actions.append(f"unchanged {path}")
        return
    prepare_target(path, actions)
    path.write_text(content, encoding="utf-8")
    actions.append(f"installed {path}")


def link_managed_dir(source: Path, target: Path, actions: list[str]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() and target.resolve() == source.resolve():
        actions.append(f"unchanged {target}")
        return
    prepare_target(target, actions)
    try:
        target.symlink_to(source, target_is_directory=True)
        actions.append(f"linked {target} -> {source}")
    except OSError:
        shutil.copytree(source, target)
        marker = target / ".ai-workstation-managed"
        marker.write_text(str(source), encoding="utf-8")
        actions.append(f"copied {source} to {target}")


def render_codex_profile(tier_name: str, tier: dict[str, Any]) -> str:
    provider = tier["provider"]
    lines = [
        f'model = "{tier["model"]}"',
        f'model_provider = "{provider}"',
        f'model_reasoning_effort = "{tier["reasoning_effort"]}"',
        "",
        f"[model_providers.{provider}]",
        f'name = "{provider}"',
        f'base_url = "{tier["base_url"]}"',
        f'env_key = "{tier["env_key"]}"',
        'wire_api = "responses"',
        "",
        f"# Logical tier: {tier_name}",
    ]
    return "\n".join(lines) + "\n"


def render_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def validate_model_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    tiers = config.get("tiers")
    if not isinstance(tiers, dict):
        return ["model config must contain a tiers object"]
    for tier in TIERS:
        entry = tiers.get(tier)
        if not isinstance(entry, dict):
            errors.append(f"missing model tier: {tier}")
            continue
        for key in ("provider", "model", "reasoning_effort", "env_key", "base_url"):
            if not isinstance(entry.get(key), str) or not entry[key]:
                errors.append(f"{tier}.{key} must be a non-empty string")
        effort = entry.get("reasoning_effort")
        if isinstance(effort, str) and effort not in REASONING:
            errors.append(f"{tier}.reasoning_effort must be one of {sorted(REASONING)}")
        env_key = entry.get("env_key", "")
        if isinstance(env_key, str) and not re.fullmatch(r"[A-Z][A-Z0-9_]*", env_key):
            errors.append(f"{tier}.env_key must name an environment variable, not a literal secret")
    return errors


def skill_dirs() -> list[Path]:
    root = REPO_ROOT / "skills"
    return sorted(path for path in root.iterdir() if path.is_dir())


def validate_skills() -> list[str]:
    errors: list[str] = []
    expected = {"research", "source-validation", "planning", "task-review"}
    found = {path.name for path in skill_dirs()}
    if found != expected:
        errors.append(f"skills must be exactly {sorted(expected)}, found {sorted(found)}")
    for path in skill_dirs():
        skill = path / "SKILL.md"
        if not skill.exists():
            errors.append(f"missing {skill}")
            continue
        text = skill.read_text(encoding="utf-8")
        for token in ("description:", "## Trigger", "## Boundaries", "## Escalate"):
            if token not in text:
                errors.append(f"{skill} missing {token}")
    return errors


def scan_for_secrets() -> list[str]:
    errors: list[str] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.name == "models.local.yaml":
            errors.append("config/models.local.yaml must not be committed or kept as canonical repo config")
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible secret in {path.relative_to(REPO_ROOT)}")
                break
    return errors


def validate_repo() -> list[str]:
    errors: list[str] = []
    required = [
        "README.md",
        "AGENTS.md",
        "Makefile",
        ".gitignore",
        "config/models.example.yaml",
        "config/workstation.yaml",
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
            errors.append(f"missing {rel}")
    for rel in ("config/models.example.yaml", "config/workstation.yaml"):
        try:
            load_json_yaml(REPO_ROOT / rel)
        except WorkstationError as exc:
            errors.append(str(exc))
    try:
        errors.extend(validate_model_config(models_config()))
    except WorkstationError as exc:
        errors.append(str(exc))
    errors.extend(validate_skills())
    errors.extend(scan_for_secrets())
    unfinished_marker = "TO" + "DO"
    if unfinished_marker in "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in REPO_ROOT.rglob("*")
        if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts
    ):
        errors.append("unfinished placeholders remain")
    return errors


def validate_links() -> list[str]:
    errors: list[str] = []
    for root in (home() / ".agents" / "skills", home() / ".cline" / "skills"):
        if not root.exists():
            continue
        for path in root.iterdir():
            if path.is_symlink() and not path.exists():
                errors.append(f"broken symlink: {path}")
    return errors


def install() -> list[str]:
    errors = validate_repo()
    if errors:
        raise WorkstationError("validation failed before install:\n" + "\n".join(errors))
    config = workstation_config()
    models = models_config()
    actions: list[str] = []

    write_managed(home() / ".codex" / "AGENTS.md", (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8"), "AGENTS.md", actions)
    for skill in skill_dirs():
        link_managed_dir(skill, home() / ".agents" / "skills" / skill.name, actions)
        link_managed_dir(skill, home() / ".cline" / "skills" / skill.name, actions)

    tiers = models["tiers"]
    for tier_name in TIERS:
        write_managed(
            home() / ".codex" / f"{tier_name}.config.toml",
            render_codex_profile(tier_name, tiers[tier_name]),
            f"config/{models_path().name}:{tier_name}",
            actions,
        )
    for role, tier_name in config["roles"].items():
        write_managed(
            home() / ".codex" / f"{role}.config.toml",
            render_codex_profile(tier_name, tiers[tier_name]) + f"# Logical role: {role}\n",
            f"config/{models_path().name}:{role}",
            actions,
        )

    cline_dir = home() / ".cline" / "ai-workstation"
    write_managed(cline_dir / "model-tiers.json", render_json(tiers), f"config/{models_path().name}", actions)
    write_managed(cline_dir / "roles.json", render_json(config["roles"]), "config/workstation.yaml", actions)
    return actions


def uninstall() -> list[str]:
    actions: list[str] = []
    targets = [
        home() / ".codex" / "AGENTS.md",
        home() / ".cline" / "ai-workstation" / "model-tiers.json",
        home() / ".cline" / "ai-workstation" / "roles.json",
    ]
    targets.extend(home() / ".codex" / f"{name}.config.toml" for name in (*TIERS, *ROLE_TIERS.keys()))
    targets.extend(home() / ".agents" / "skills" / skill.name for skill in skill_dirs())
    targets.extend(home() / ".cline" / "skills" / skill.name for skill in skill_dirs())
    for target in targets:
        if not target.exists() and not target.is_symlink():
            continue
        if target.is_symlink() or is_managed_file(target) or (target.is_dir() and (target / ".ai-workstation-managed").exists()):
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()
            actions.append(f"removed {target}")
        else:
            actions.append(f"left unmanaged {target}")
    return actions


def status() -> list[str]:
    paths = [
        home() / ".codex" / "AGENTS.md",
        home() / ".agents" / "skills",
        home() / ".cline" / "skills",
        home() / ".cline" / "ai-workstation" / "model-tiers.json",
    ]
    return [f"{path}: {'present' if path.exists() else 'missing'}" for path in paths]


def print_lines(lines: list[str]) -> None:
    for line in lines:
        print(line)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("install", "status", "validate", "update", "uninstall"))
    args = parser.parse_args(argv)
    try:
        if args.command == "install":
            print("workstation configuration validated")
            print_lines(install())
            print("global skills installed")
            print("Codex adapter configured")
            print("Cline adapter configured")
            print("model configuration initialized")
            print("no credentials committed")
        elif args.command == "update":
            print_lines(install())
            print("workstation updated")
        elif args.command == "uninstall":
            print_lines(uninstall())
            print("workstation uninstalled")
        elif args.command == "status":
            print_lines(status())
        elif args.command == "validate":
            errors = validate_repo() + validate_links()
            if errors:
                print_lines(errors)
                return 1
            print("validation passed")
    except WorkstationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
