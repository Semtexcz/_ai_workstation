# Cline Adapter

This adapter installs shared skills and a non-secret tier map for Cline.

Managed paths:

- `~/.cline/skills/<skill-name>`
- `~/.cline/ai-workstation/model-tiers.json`
- `~/.cline/ai-workstation/roles.json`

Cline docs currently place global skills under `~/.cline/skills`, provider settings under `~/.cline/data/settings/`, and CLI overrides behind flags such as `--provider`, `--model`, and `--thinking`. This workstation does not write `providers.json` because it may contain credentials or provider-specific local state.

Use `~/.cline/ai-workstation/model-tiers.json` as the local, non-secret tier selection source for wrappers or manual Cline runs.
