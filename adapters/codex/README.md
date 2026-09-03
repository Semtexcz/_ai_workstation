# Codex Adapter

This adapter renders user-level Codex files from `config/models.local.json`. If only `config/models.example.json` exists, model tiers are treated as `UNCONFIGURED` and runnable Codex model profiles are not generated.

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

Codex docs state that user configuration lives under `~/.codex`, selected profiles use `~/.codex/<profile>.config.toml`, and global instructions load from `~/.codex/AGENTS.md`.

## Built-In OpenAI Provider

For `provider = "openai"`, generated profiles set:

```toml
model = "..."
model_provider = "openai"
model_reasoning_effort = "..."
```

They do not generate `[model_providers.openai]`. This preserves existing Codex authentication, including ChatGPT/Codex subscription auth and local API auth behavior.

## Custom Providers

For custom OpenAI-compatible providers, set a non-reserved `codex_provider_id`, `base_url`, and `env_key`. The generated TOML defines `[model_providers.<codex_provider_id>]` and reads credentials from the named environment variable.

Reserved provider IDs such as `openai`, `ollama`, and `lmstudio` are not used for custom provider definitions.
