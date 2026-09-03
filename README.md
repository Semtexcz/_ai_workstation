# _ai_workstation

Portable, version-controlled configuration for a developer's AI-agent workstation.

This repository provides cross-project agent capabilities for Codex, Cline, shared skills, logical model tiers, and small reusable utilities. It is intentionally not a project template.

## What Belongs Here

- Agent harness installation and user-level configuration.
- Global, domain-neutral skills.
- Logical model/provider profiles.
- Thin Codex and Cline adapters.
- Install, update, status, uninstall, and validation utilities.

## What Does Not Belong Here

- Project goals, milestones, work packages, tasks, evidence logs, or acceptance criteria.
- Project-local `AGENTS.md` semantics.
- Software-specific Definition of Done rules.
- Project-specific routing requirements such as `cheap`, `strong`, or `frontier`.
- Credentials, API keys, tokens, or private MCP secrets.

## Quick Start

```bash
git clone <repo>
cd _ai_workstation
make install
make status
make validate
```

To customize concrete models, create `config/models.local.yaml` from `config/models.example.yaml` and edit the provider, model, base URL, reasoning effort, and environment variable names. `config/models.local.yaml` is ignored by Git.

## Codex And Cline

The workstation installs the same canonical skills into Codex and Cline global skill locations. Adapter files are thin and generated from the canonical repository sources.

Codex integration installs:

- `~/.codex/AGENTS.md`
- tier profiles such as `~/.codex/frontier.config.toml`
- role profiles such as `~/.codex/planner.config.toml`
- skills under `~/.agents/skills/`

Cline integration installs:

- skills under `~/.cline/skills/`
- non-secret tier metadata under `~/.cline/ai-workstation/`

## Model Tiers

Projects should refer to capability tiers, not concrete models:

- `frontier`: architecture, strategy, ambiguous problems, critical decisions.
- `strong`: bounded complex analysis, synthesis, integration, review.
- `cheap`: narrow execution, extraction, formatting, routine research.

Concrete providers and model IDs are workstation configuration. Changing them does not require touching project repositories.

## Security Model

Secrets are never committed. Configuration references credentials by environment variable name, for example `OPENAI_API_KEY`. Cline provider settings and Codex primary user settings are left user-managed unless a file is explicitly installed with the `_ai_workstation` marker.

See [docs/security.md](docs/security.md).
