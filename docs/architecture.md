# Architecture

```text
AI WORKSTATION
      |
      +-- capabilities
      +-- authentication integration
      +-- providers/models
      +-- global skills
      +-- harness adapters
              |
              v
           PROJECT
      goals, milestones, work packages,
      tasks, evidence, project lifecycle
```

Workstation provides capabilities. Projects provide semantics.

`_ai_workstation` owns reusable user-level agent infrastructure: generic skills, logical model tiers, adapter rendering, validation, safe installation, and thin launchers.

`_ai_work_template` owns project semantics: goals, milestones, work packages, tasks, evidence, and lifecycle structure. This repository does not implement `_ai_work_template`.

## Canonical Sources

- `AGENTS.md` is the canonical global agent contract.
- `skills/*/SKILL.md` is the canonical skill content.
- `config/models.example.json` documents the model-tier shape and is intentionally unconfigured.
- `config/models.local.json`, when present, is the local concrete model source and is ignored by Git.
- `config/workstation.json` defines owned install paths and role-to-tier mapping.

Installed files are generated or linked from these sources:

- `~/.codex/AGENTS.md` is generated from repository `AGENTS.md`.
- `~/.agents/skills/<skill>` links to `skills/<skill>` or is a marked managed copy.
- `~/.cline/skills/<skill>` links to `skills/<skill>` or is a marked managed copy.
- `~/.codex/*.config.toml` files are generated only when local model tiers are configured.
- `~/.cline/ai-workstation/*.json` files are generated from model tiers and role mappings.
- `~/.local/bin/ai-cline` is a managed launcher.

## Adapter Decisions

Codex user configuration is layered under `~/.codex`; selected profiles are loaded from `~/.codex/<profile>.config.toml`. The workstation therefore installs separate tier and role profiles instead of rewriting the user's primary `~/.codex/config.toml`.

For the built-in Codex `openai` provider, generated profiles set `model`, `model_provider = "openai"`, and `model_reasoning_effort` only. They do not create `[model_providers.openai]`, so existing ChatGPT/Codex authentication and local Codex auth state remain user-managed.

Custom providers use non-reserved provider IDs and reference credentials through `env_key`. Literal secrets are never written.

Cline stores provider and credential settings under its own settings area. The workstation does not write credential-bearing Cline provider files. It installs global skills, non-secret model-tier metadata, and an `ai-cline` launcher that invokes Cline with `--provider`, `--model`, and `--thinking`.

## Managed State

Every generated file starts with `Managed by _ai_workstation`. Managed symlinks point back into this repository. Managed copied directories contain `.ai-workstation-managed`.

Existing unmanaged files, directories, valid symlinks, and broken symlinks are preserved by timestamped backup before replacement. Uninstall removes only state whose ownership can be proven.
