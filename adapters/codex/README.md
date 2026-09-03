# Codex Adapter

This adapter renders user-level Codex files from `config/models.local.yaml` or, when absent, `config/models.example.yaml`.

Managed paths:

- `~/.codex/AGENTS.md`
- `~/.codex/frontier.config.toml`
- `~/.codex/strong.config.toml`
- `~/.codex/cheap.config.toml`
- `~/.codex/planner.config.toml`
- `~/.codex/analyst.config.toml`
- `~/.codex/worker.config.toml`
- `~/.codex/reviewer.config.toml`
- `~/.agents/skills/<skill-name>`

Codex docs state that personal defaults live in `~/.codex/config.toml`, selected profiles are loaded from `~/.codex/<profile>.config.toml`, and global instructions are read from `~/.codex/AGENTS.md`. This workstation leaves `~/.codex/config.toml` alone unless it does not exist, because it commonly contains user-managed preferences.

Credentials are referenced only through environment variable names such as `OPENAI_API_KEY`.
