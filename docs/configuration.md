# Configuration

The workstation is configured with dependency-free JSON files under `config/`. There is no separate build step: the same files are consumed by install, status, launchers, validation, and CI.

## Configuration Files

| File | Tracked | Purpose |
| --- | --- | --- |
| `config/workstation.json` | yes | Owned install paths and the role-to-tier mapping. |
| `config/models.example.json` | yes | Committed schema version 2 template. It is intentionally unconfigured and documents the expected shape. |
| `config/models.local.json` | no | Optional local concrete model configuration. Ignored by Git. |

### `config/models.local.json`

`config/models.local.json` is:

- optional — the workstation falls back to `config/models.example.json` when it is absent;
- ignored by Git (`.gitignore` ignores `config/models.local.*`);
- local workstation configuration, not project configuration;
- never allowed to contain committed credentials — it holds local provider/model choices, and validation treats an accidentally tracked `models.local.*` file as an error.

When only the example file exists, every tier is reported as `UNCONFIGURED` and validation emits warnings, not errors.

Create it from the template and edit it by hand:

```bash
cp config/models.example.json config/models.local.json
```

## Model Config Schema v2

The model configuration schema version is `2`. The document root is an object with a `version` and a `tiers` object:

```text
tiers
├── frontier
│   ├── codex
│   └── cline
├── strong
│   ├── codex
│   └── cline
└── cheap
    ├── codex
    └── cline
```

Each project-facing logical tier (`frontier`, `strong`, `cheap`) carries two independent harness implementations: one for Codex and one for Cline.

> Logical tier semantics are shared. Concrete tier implementations are harness-specific.

Codex reads only `tiers.<tier>.codex`. Cline reads only `tiers.<tier>.cline`. A tier may be configured for one harness and unconfigured for the other.

### Tier Fields

All harness implementations share the same core fields:

- `configured`: boolean; `true` only when the implementation is runnable.
- `provider`: provider identifier for the harness. Codex and Cline providers are independent and may differ within the same logical tier.
- `model`: concrete model ID (non-empty when `configured` is `true`).
- `reasoning_effort`: one of `minimal`, `low`, `medium`, `high`, `xhigh`.

Codex implementations may additionally use:

- `auth`: documentation field describing how the provider authenticates (for example `codex` for the built-in Codex OpenAI provider). It never stores a credential value.
- `codex_provider_id`: non-reserved Codex provider ID for custom providers (must not be `openai`, `ollama`, or `lmstudio`).
- `provider_name`: provider display name used for custom providers; defaults to `codex_provider_id`.
- `base_url`: OpenAI-compatible API base URL for custom providers.
- `env_key`: name of the environment variable holding a custom provider's credential. Secrets are referenced by environment variable name only.

Cline implementations use only the shared core fields.

### Fully Configured Example

The example below is a valid, fully configured `config/models.local.json`. Model names are illustrative placeholders only — replace them with the concrete model IDs you want to use locally. The file must not be committed.

```json
{
  "version": 2,
  "tiers": {
    "frontier": {
      "codex": {
        "configured": true,
        "provider": "openai",
        "model": "FRONTIER_CODEX_MODEL",
        "reasoning_effort": "high",
        "auth": "codex"
      },
      "cline": {
        "configured": true,
        "provider": "anthropic",
        "model": "FRONTIER_CLINE_MODEL",
        "reasoning_effort": "high"
      }
    },
    "strong": {
      "codex": {
        "configured": true,
        "provider": "openai",
        "model": "STRONG_CODEX_MODEL",
        "reasoning_effort": "medium",
        "auth": "codex"
      },
      "cline": {
        "configured": true,
        "provider": "gemini",
        "model": "STRONG_CLINE_MODEL",
        "reasoning_effort": "medium"
      }
    },
    "cheap": {
      "codex": {
        "configured": true,
        "provider": "openai",
        "model": "CHEAP_CODEX_MODEL",
        "reasoning_effort": "low",
        "auth": "codex"
      },
      "cline": {
        "configured": true,
        "provider": "deepseek",
        "model": "CHEAP_CLINE_MODEL",
        "reasoning_effort": "low"
      }
    }
  }
}
```

## Codex Configuration

Codex uses only `tiers.<tier>.codex`. The Codex implementation is installed as user-level profile files under `~/.codex`; the primary `~/.codex/config.toml` is never rewritten.

Runnable tier profiles are generated for every configured Codex tier:

```bash
codex --profile frontier
codex --profile strong
codex --profile cheap
```

Role profiles are generated for every role whose mapped Codex tier is configured:

```bash
codex --profile planner
codex --profile analyst
codex --profile worker
codex --profile reviewer
```

Role mapping:

```text
planner  -> frontier
analyst  -> strong
worker   -> cheap
reviewer -> strong
```

The same Codex tier implementation is reused by its mapped roles, so a role profile contains exactly the model, provider, and reasoning effort of the mapped tier.

### Built-In OpenAI Provider

For `provider = "openai"`, generated profiles set only:

```toml
model = "..."
model_provider = "openai"
model_reasoning_effort = "..."
```

They do not redefine `[model_providers.openai]`. The built-in OpenAI provider therefore keeps using the existing Codex/ChatGPT authentication, which remains user-managed by Codex. No `[model_providers.openai]` section is emitted, and no credentials are written.

### Custom Providers

Custom OpenAI-compatible providers use a non-reserved `codex_provider_id`. The generated profile defines `[model_providers.<codex_provider_id>]` and references the credential through `env_key` — the environment variable name, never the secret value.

## Cline Configuration

Cline uses only `tiers.<tier>.cline`. The `ai-cline` launcher resolves a logical tier and invokes Cline with CLI overrides:

```bash
ai-cline cheap "extract these values"
ai-cline strong "compare alternatives"
ai-cline frontier "design the approach"
```

Internally this expands to a `cline --provider <provider> --model <model> --thinking <reasoning_effort> ...` command built from `tiers.<tier>.cline`. Use `ai-cline --print-command <tier> ...` to inspect the resolution without running Cline.

Providers may differ between tiers — for example `anthropic` on `frontier`, `gemini` on `strong`, and `deepseek` on `cheap`.

Cline credentials remain managed by Cline and by user configuration under Cline's own settings area. The workstation does not duplicate credential storage and never writes credential-bearing Cline provider files. It installs shared global instructions, namespaced skills, and non-secret tier metadata only.

A missing or unconfigured Cline tier does not fall back to Codex. Invoking `ai-cline` on an unconfigured Cline tier fails with a clear error; at install and validation time the same state is a warning.

## Partial Configuration

Partial configuration is valid. The two harnesses are configured independently, and each logical tier can be configured for one harness and not the other. This is valid:

```text
Codex:
frontier ✓
strong   ✓
cheap    ✓

Cline:
frontier ✗
strong   ✗
cheap    ✓
```

So is this:

```text
Codex:
frontier ✗
strong   ✗
cheap    ✗

Cline:
frontier ✓
strong   ✓
cheap    ✓
```

An unconfigured harness implementation produces a warning, not a whole-workstation failure. Profiles and metadata are generated only for the harness implementations that are configured.

## Schema Version Migration

- `version: 1` → unsupported.
- `version: 2` → current.

Version 1 stored a single implementation per logical tier. Version 2 nests per-harness implementations under `tiers.<tier>.codex` and `tiers.<tier>.cline`. Validation rejects version 1 explicitly and asks for `tiers.<tier>` to be migrated to the nested shape.

No automatic migration is performed. Early v1 local configuration should be recreated from the current template:

```bash
cp config/models.example.json config/models.local.json
```

and then edited manually.

## Validation

`make validate` and `make test` treat repository structure and model configuration independently:

- structural, JSON, schema, and secret checks are errors;
- unconfigured tiers and missing generated profiles are warnings.

An unconfigured default state — no `config/models.local.json`, no API keys, no Codex or Cline authentication — is valid and passes with `UNCONFIGURED` warnings.

