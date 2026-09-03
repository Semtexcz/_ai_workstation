# Configuration

## Model Tiers

Copy the example file and customize it locally:

```bash
cp config/models.example.yaml config/models.local.yaml
```

`models.local.yaml` is JSON-compatible YAML so the repository can parse it with the Python standard library. Each tier has:

- `provider`: provider identifier used by generated adapter files.
- `model`: concrete model ID for this workstation.
- `reasoning_effort`: `minimal`, `low`, `medium`, `high`, or `xhigh`.
- `env_key`: environment variable name containing the secret.
- `base_url`: provider API base URL.

The required tiers are `frontier`, `strong`, and `cheap`.

## Codex

Codex profile files are generated under `~/.codex`:

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

Project repositories should not hard-code model IDs. They may describe task impact or requested tier, and the workstation resolves concrete models.

## Cline

Cline skills are installed under `~/.cline/skills`. Non-secret tier metadata is installed at:

```text
~/.cline/ai-workstation/model-tiers.json
~/.cline/ai-workstation/roles.json
```

Cline provider credentials and model selections remain local. Use Cline settings, Cline CLI flags, or future local wrappers to select the provider/model from the tier metadata. Different tiers may use different providers.

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
