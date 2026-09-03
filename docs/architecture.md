# Architecture

```text
AI WORKSTATION
      |
      +-- capabilities
      +-- providers/models
      +-- global skills
      +-- harness adapters
              |
              v
           PROJECT
      project semantics
```

Workstation provides capabilities. Projects provide semantics.

The workstation owns reusable agent infrastructure: generic skills, logical model tiers, adapter rendering, validation, and user-level installation mechanics. Projects own their goals, tasks, acceptance criteria, evidence, and project-local instructions.

## Canonical Sources

- `AGENTS.md` is the canonical global agent contract.
- `skills/*/SKILL.md` is the canonical skill content.
- `config/models.example.yaml` documents model-tier shape.
- `config/models.local.yaml`, when present, is the local concrete model source and is not committed.
- `config/workstation.yaml` defines owned install paths and role-to-tier mapping.

Installed files are generated or linked from these sources:

- `~/.codex/AGENTS.md` is generated from repository `AGENTS.md`.
- `~/.agents/skills/<skill>` links to `skills/<skill>`.
- `~/.cline/skills/<skill>` links to `skills/<skill>`.
- `~/.codex/*.config.toml` files are generated from model tiers.
- `~/.cline/ai-workstation/*.json` files are generated from model tiers and role mappings.

## Adapter Decisions

Codex supports user configuration under `~/.codex`, profile files selected by profile name, global `AGENTS.md`, and global skills. The workstation therefore installs profile files instead of rewriting the user's primary `~/.codex/config.toml`.

Cline stores credentials and provider configuration under its data settings area. The workstation does not write credential-bearing provider files. It installs global skills and non-secret model-tier metadata that wrappers, operators, or future adapter code can consume.

## Managed State

Every generated file starts with `Managed by _ai_workstation`. Managed symlinks point back into this repository. Existing unmanaged files are preserved by timestamped backup before replacement.

The installer is idempotent: rerunning it updates managed files, preserves unmanaged files, and leaves already-correct links unchanged.
