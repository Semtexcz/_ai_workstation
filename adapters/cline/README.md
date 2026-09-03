# Cline Adapter

This adapter installs shared skills, non-secret tier metadata, and a thin launcher.

Managed paths:

- `~/.cline/skills/<skill-name>`
- `~/.cline/ai-workstation/model-tiers.json`
- `~/.cline/ai-workstation/roles.json`
- `~/.local/bin/ai-cline`

Cline docs place global skills under `~/.cline/skills`, provider settings under `~/.cline/data/settings/`, and CLI overrides behind flags such as `--provider`, `--model`, `--thinking`, and `--config`.

The workstation does not write Cline provider credential files. The launcher resolves a logical tier from `config/models.local.json` and invokes:

```bash
cline --provider <provider> --model <model> --thinking <reasoning_effort> ...
```

Examples:

```bash
ai-cline cheap "extract these values"
ai-cline strong "compare these alternatives"
ai-cline frontier "design the approach"
```

Use `ai-cline --print-command <tier> ...` to inspect resolution without running Cline.
