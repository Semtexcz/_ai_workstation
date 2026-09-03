# Configuration

## File Format

Configuration is JSON to keep the workstation dependency-free:

- `config/workstation.json`
- `config/models.example.json`
- `config/models.local.json`

`models.local.json` is ignored by Git.

## Model Tiers

Copy the example file and customize it locally:

```bash
cp config/models.example.json config/models.local.json
```

Each tier has:

- `configured`: `true` only when the tier is runnable.
- `provider`: provider identifier for Codex/Cline.
- `model`: concrete model ID.
- `reasoning_effort`: `minimal`, `low`, `medium`, `high`, or `xhigh`.
- `auth`: documentation field such as `codex` or `env`.

For custom providers, also set:

- `codex_provider_id`: non-reserved Codex provider ID.
- `base_url`: OpenAI-compatible API base URL.
- `env_key`: environment variable name containing the API key.

## Codex

When all tiers are configured, Codex profile files are generated under `~/.codex`:

- `frontier.config.toml`
- `strong.config.toml`
- `cheap.config.toml`
- `planner.config.toml`
- `analyst.config.toml`
- `worker.config.toml`
- `reviewer.config.toml`

Role mapping:

- `planner -> frontier`
- `analyst -> strong`
- `worker -> cheap`
- `reviewer -> strong`

Use a generated profile with:

```bash
codex --profile planner
codex --profile cheap "format this table"
```

For `provider = "openai"`, the generated profile uses the built-in Codex OpenAI provider and does not redefine `[model_providers.openai]`.

For custom providers, the generated profile includes `[model_providers.<codex_provider_id>]` and references credentials through `env_key`.

## Authentication

ChatGPT/Codex authentication is user-managed by Codex and is preserved. OpenAI API authentication is also user-managed by Codex or environment variables. Custom provider authentication uses `env_key` only; do not place secret values in JSON.

## Cline

Cline skills are installed under `~/.cline/skills`. Non-secret tier metadata is installed at:

```text
~/.cline/ai-workstation/model-tiers.json
~/.cline/ai-workstation/roles.json
```

The `ai-cline` launcher resolves a logical tier and invokes Cline using supported CLI flags:

```bash
ai-cline cheap "extract these values"
ai-cline strong "compare these alternatives"
ai-cline frontier "design the approach"
```

To inspect the command without running Cline:

```bash
ai-cline --print-command cheap "extract these values"
```

## Commands

```bash
make install
make status
make validate
make update
make uninstall
make test
```

All commands honor `$HOME`, which allows tests and dry runs against temporary homes.
