# Security

## Secrets

Do not commit:

- API keys.
- Access tokens.
- OAuth tokens.
- Private MCP secrets.
- Provider files copied from a live Cline or Codex installation.

The repository stores environment variable names such as `EXAMPLE_PROVIDER_API_KEY`, not credential values.

## Local Files

`config/models.local.json` is ignored by Git and may contain local provider and model choices. It must not contain literal secrets. Use `env_key` to name the environment variable where a custom provider's secret is stored.

Cline provider settings are not managed because Cline stores provider and credential state under its settings area. Codex authentication state and primary `~/.codex/config.toml` are not managed by this repository.

## Validation

`make validate` separates errors from warnings. An unconfigured workstation is valid but warns that model tiers are `UNCONFIGURED`.

Validation checks:

- Required repository structure.
- JSON syntax.
- Required model tiers.
- Generated Codex TOML syntax.
- Cline tier mapping.
- Skill metadata.
- Managed symlink health.
- Obvious secret patterns in tracked files.
- Obvious literal secrets in local model config.
- Accidental tracked `config/models.local.json`.
- Remaining placeholder markers for unfinished work.

Secret scanning is a guardrail, not a substitute for review.
