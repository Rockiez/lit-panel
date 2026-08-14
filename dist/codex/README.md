# Codex adapter

Requires Codex CLI 0.147.0 or newer. Agent Plugins v1 is the first-class install and discovery path: the plugin carries the complete skill, personas, criteria, schemas, report template, and scripts.

The portable manifest does not register custom subagent types. The default runtime therefore calls native `spawn_agent` once per seat and injects that seat's bundled persona and packet into an isolated context. Generated `.codex/agents/*.toml` files are an optional project/user enhancement for native agent naming; they are not required for plugin discovery and do not replace the isolation gate.

For every packet, the orchestrator writes the actual subagent context id, isolation flag, and completion status to `execution-receipt.json`. Each Seat 08 reader uses either a same-context `follow-up` or a different `sealed-new-context` carrying the frozen first-read text, and records its SHA-256. If `spawn_agent`, isolation, dispatch coverage, or this two-step proof cannot be demonstrated, the run must be `degraded=true` and can emit only a diagnostic with null bands.

The 2026-08-14 black-box smoke passed plugin discovery and provider-backed native `spawn_agent` for Seats 04 and 08. That evidence proves the Codex provider path; formal closure for any new run still requires the current run and execution receipts.
