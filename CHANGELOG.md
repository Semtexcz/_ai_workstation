# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-03

First stable release of `_ai_workstation` — the workstation-level foundation
for AI-agent projects. Workstation provides capabilities; projects provide
semantics.

### Added

- Portable AI workstation configuration.
- Codex integration: tier and role profiles under `~/.codex`.
- Cline integration: shared skills, non-secret tier metadata, and the `ai-cline` launcher.
- Logical `frontier` / `strong` / `cheap` capability tiers.
- Independent per-harness model/provider mapping per tier.
- Shared canonical global `AGENTS.md`.
- Namespaced generic skills (`generic-*`).
- Safe, idempotent installation.
- Safe uninstall of owned state only.
- Local untracked model configuration (`config/models.local.json`).
- Secret handling by environment variable reference; no credentials in the repository.
- Deterministic repository validation (`make validate`).
- Automated tests (`make test`).
- GitHub Actions CI.

### Not included in v1.0.0

The following are intentionally **not** part of the v1.0.0 workstation scope and
belong to separate project-level tooling (project repositories / `_ai_work_template`):

- Project goals.
- Milestones.
- Tasks.
- Orchestration.
- Autonomous scheduling.
- Project state.
- `_ai_work_template`.
