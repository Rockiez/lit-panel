# Host adapters

`core/lit-panel/` is the single runtime source of truth. `scripts/build_dist.py` combines it with one adapter per host:

- `codex/`: Agent Plugins + native Codex plugin metadata; optional `.codex/agents/*.toml` enhancement.
- `claude/`: Claude Code plugin manifest, commands and `agents/*.md`.
- `antigravity/`: Antigravity native plugin manifest and custom `agents/*.md`.

Do not edit generated `dist/` or root compatibility copies directly. Update `core/` or an adapter, then rebuild and run `scripts/build_dist.py --check`.
