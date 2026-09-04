# _ai_workstation

Portable, version-controlled configuration for a developer's AI-agent workstation.

Core rule:

> Workstation provides capabilities. Projects provide semantics.

`_ai_workstation` provides cross-project capabilities for Codex, Cline, shared global instructions, namespaced generic skills, logical model tiers, and small reusable utilities. It is intentionally not a project template.

## Python Engineering Defaults

Workstation-level Python engineering defaults live in `policies/python-engineering.md`. Install/update deterministically compose the core global contract (`AGENTS.md`) with that concise policy and write the combined global instructions to both `~/.codex/AGENTS.md` and `~/.agents/AGENTS.md`. Healthy project-local conventions take precedence over these defaults. The global policy is intentionally concise to keep per-interaction agent context low.

## Status

Stable release: **v1.0.0** (repository version `1.0.0`, Git tag `v1.0.0`)

`_ai_workstation` is the workstation-level foundation for AI-agent projects.
Project semantics and orchestration belong in `_ai_work_template`.

> **v1 stability principle:** v1.x should preserve the workstation/project
> separation and the public logical tier interface (`frontier`, `strong`,
> `cheap`). Breaking changes to configuration schema or project-facing
> semantics require a major version.

## What Belongs Here

- Agent harness user-level configuration.
- Shared global agent instructions.
- Global, domain-neutral skills.
- Logical model tiers and per-harness implementations.
- Thin Codex and Cline adapters.
- Install, update, status, uninstall, validation, launcher, and CI utilities.

## What Does Not Belong Here

- Project goals, milestones, work packages, tasks, evidence logs, or acceptance criteria.
- Project-local `AGENTS.md` semantics.
- Software-specific Definition of Done rules.
- Project-specific routing requirements.
- Project-specific skills.
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

Without local model configuration, install still sets up global instructions, namespaced skills, Cline tier metadata, and `ai-cline`. Each Codex/Cline tier shows as `UNCONFIGURED` until configured locally.

To configure concrete models:

```bash
cp config/models.example.json config/models.local.json
```

Then edit `config/models.local.json`. It is ignored by Git.

## Model Tiers

Projects should refer only to capability tiers:

- `frontier`: architecture, strategy, ambiguous problems, critical decisions.
- `strong`: bounded complex analysis, synthesis, integration, review.
- `cheap`: narrow execution, extraction, formatting, routine research.

Logical tier semantics are shared. Concrete tier implementation is harness-specific.

```text
Project requests:

cheap
strong
frontier

Workstation resolves:

             Codex              Cline
cheap        model A            model D
strong       model B            model E
frontier     model C            model F
```

Codex and Cline may use different providers and models for the same tier. A tier implementation may be configured for one harness and unconfigured for the other.

## Codex And Cline

Codex integration installs:

- `~/.codex/AGENTS.md`
- tier profiles such as `~/.codex/frontier.config.toml` when `tiers.frontier.codex` is configured
- role profiles such as `~/.codex/planner.config.toml` when the mapped Codex tier is configured
- namespaced skills under `~/.agents/skills/`

Cline integration installs:

- shared global instructions at `~/.agents/AGENTS.md`
- namespaced skills under `~/.cline/skills/`
- non-secret tier metadata under `~/.cline/ai-workstation/`
- launcher `~/.local/bin/ai-cline`

Use Cline tiers:

```bash
ai-cline cheap "extract these values"
ai-cline strong "compare alternatives"
ai-cline frontier "design the approach"
```

Use Codex tiers natively:

```bash
codex --profile cheap
codex --profile planner
```

No separate `ai-codex` wrapper is provided because Codex profiles already solve this cleanly.

## Global Skills

Global skill names use the `generic-` prefix:

- `generic-planning`
- `generic-research`
- `generic-source-validation`
- `generic-task-review`

This leaves project templates free to define project-specific `planning`, `research`, `source-validation`, or `task-review` skills without relying on harness-specific precedence behavior.

## Security Model

Secrets are never committed. Configuration references credentials by environment variable name for custom providers. Built-in Codex/OpenAI profiles do not redefine `model_providers.openai`, so existing ChatGPT/Codex authentication can keep working.

See [docs/security.md](docs/security.md).
