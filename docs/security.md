# Security

## Secrets

Do not commit:

- API keys.
- Access tokens.
- OAuth tokens.
- Private MCP secrets.
- Provider files copied from a live Cline or Codex installation.

The repository stores environment variable names such as `OPENAI_API_KEY`, not credential values.

## Local Files

`config/models.local.yaml` is ignored by Git and may contain local provider choices. It still should not contain literal secrets. Use `env_key` to name the environment variable where the secret is stored.

Cline provider settings are not managed because Cline may store credentials under `~/.cline/data/settings/`. Codex authentication state and primary `~/.codex/config.toml` are not managed by this repository.

## Validation

`make validate` checks:

- Required repository structure.
- JSON-compatible YAML syntax.
- Required model tiers.
- Skill metadata.
- Broken managed symlinks in installed skill locations.
- Obvious committed secret patterns.
- Accidental committed `config/models.local.yaml`.
- Remaining placeholder markers for unfinished work.

Secret scanning is a guardrail, not a substitute for review.
