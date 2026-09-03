# _ai_workstation

Portable, version-controlled configuration for a developer's AI-agent workstation.

This repository provides cross-project capabilities for Codex, Cline, shared generic skills, logical model tiers, and small reusable utilities. It is intentionally not a project template.

Core rule:

> Workstation provides capabilities. Projects provide semantics.

## What Belongs Here

- Agent harness user-level configuration.
- Global, domain-neutral skills.
- Logical model/provider tiers.
- Thin Codex and Cline adapters.
- Install, update, status, uninstall, validation, and launcher utilities.

## What Does Not Belong Here

- Project goals, milestones, work packages, tasks, evidence logs, or acceptance criteria.
- Project-local `AGENTS.md` semantics.
- Software-specific Definition of Done rules.
- Project-specific routing requirements.
- Credentials, API keys, tokens, or private MCP secrets.

Those belong in project repositories or the future `_ai_work_template`.

## Quick Start

```bash
git clone <repo>
cd _ai_workstation
make install
make status
make validate
```

Without local model configuration, install still sets up instructions, skills, Cline tier metadata, and `ai-cline`, but model tiers show as `UNCONFIGURED` and Codex model profiles are not generated.

To configure concrete models:

```bash
cp config/models.example.json config/models.local.json
```

Then edit `config/models.local.json`. It is ignored by Git.

## Codex And Cline

Codex integration installs:

- `~/.codex/AGENTS.md`
- tier profiles such as `~/.codex/frontier.config.toml` when tiers are configured
- role profiles such as `~/.codex/planner.config.toml` when tiers are configured
- skills under `~/.agents/skills/`

Cline integration installs:

- skills under `~/.cline/skills/`
- non-secret tier metadata under `~/.cline/ai-workstation/`
- launcher `~/.local/bin/ai-cline`

Use Cline tiers:

```bash
ai-cline cheap "extract these values"
ai-cline strong "compare these alternatives"
ai-cline frontier "design the approach"
```

Use Codex tiers natively:

```bash
codex --profile cheap
codex --profile planner
```

No separate `ai-codex` wrapper is provided because Codex profiles already solve this cleanly.

## Model Tiers

Projects should refer to capability tiers, not concrete models:

- `frontier`: architecture, strategy, ambiguous problems, critical decisions.
- `strong`: bounded complex analysis, synthesis, integration, review.
- `cheap`: narrow execution, extraction, formatting, routine research.

Concrete providers and model IDs are workstation configuration. Changing them does not require touching project repositories.

## Security Model

Secrets are never committed. Configuration references credentials by environment variable name for custom providers. Built-in Codex/OpenAI profiles do not redefine `model_providers.openai`, so existing ChatGPT/Codex authentication can keep working.

See [docs/security.md](docs/security.md).
