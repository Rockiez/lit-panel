[简体中文](README.md) | [English](README.en.md) | [Français](README.fr.md) | [Español](README.es.md)

# lit-panel

Version 0.5.1 is an eleven-seat literary-review plugin for Chinese memoir and narrative prose. Every seat runs in a real, isolated subagent context. Seats return structured judgments with verbatim evidence; scripts close the run, validate schemas, invalidate unsupported quotes, and derive a qualitative A/B/C/N/A band. Agent Plugins is the first-class installation and discovery path on Codex CLI 0.147.0 or newer.

## Support matrix

| Host | Minimum verified version | Native path | Notes |
|---|---:|---|---|
| Codex CLI / App | 0.147.0 | Agent Plugin + native `spawn_agent` | Agent Plugins v1 carries the skill; optional `.codex/agents/*.toml` files enhance installation |
| Claude Code | 2.1.63 | plugin `agents/*.md` + `Agent` tool | Uses the current `Agent` terminology and execution path |
| Google Antigravity | CLI 1.1.12 | plugin custom agents + repeated `invoke_subagent` calls | Calls may run concurrently; the project does not assume a guaranteed single array batch API |

The portable core of the open [Agent Plugins 1.0 specification](https://agent-plugins.org/specification) currently covers skills and MCP servers; it does not register one shared custom-agent definition across hosts. This repository therefore keeps runtime semantics in `core/` and generates host-native agent definitions through `adapters/`. A Codex Agent Plugin manifest and Codex custom-subagent configuration are two distinct capability layers.

## Installation

Normal installation does not require cloning the repository or running the Python builder first. Each host's native plugin manager reads its committed, self-contained distribution directly from the repository.

Codex:

```bash
codex plugin marketplace add Rockiez/lit-panel
codex plugin add lit-panel@lit-panel
```

Claude Code:

```bash
claude plugin marketplace add Rockiez/lit-panel
claude plugin install lit-panel@lit-panel
```

Antigravity:

```bash
agy plugin install https://github.com/Rockiez/lit-panel/tree/main/dist/antigravity
```

Start a new Codex task, Claude Code session, or Antigravity session after installation so the host refreshes plugin discovery.

Installation itself never runs `scripts/build_dist.py`. Verbatim verification and report derivation still require Python 3.10+ at runtime; that is an execution dependency, not an installation build step. The committed `dist/codex`, `dist/claude`, and `dist/antigravity` packages each include personas, criteria, schemas, the report template, and runtime scripts.

Clone the repository only for local/offline installation or development. In that case, `./scripts/install-codex.sh`, `./scripts/install-claude.sh`, and `./scripts/install-antigravity.sh` consume committed `dist` packages by default; maintainers can pass `--rebuild` after changing `core/` or `adapters/`. Codex's optional project Agent TOML files remain available through `./scripts/install-codex.sh --project-agents`.

## Runtime model

```text
prepare_run.py -> run.json + mutually blind seat packets
  -> one independent subagent per seat, running concurrently and mutually blind
  -> strict two-step Seat 08 flow for every reader, with context and first-read hash proof
  -> execution-receipt.json proves native subagents, isolation, dispatch status, and degradation
  -> validate against seat-output.schema.json
  -> verify_quotes.py checks verbatim evidence and invalidates failed criteria
  -> derive_report.py correlates all receipts and emits either a formal report or a diagnostic
```

The closed-run `verify_quotes.py` and standalone-audit `verify-quotes.py` share one Tier 1–5 engine. Tier 1 exact, Tier 2 normalized, and length-constrained Tier 3 ellipsis spans may verify; Tier 4 fuzzy alignment is only a non-passing arbitration candidate, while Tier 5 is a hard invalidation. Structured receipts record the actual tier, and Tier 4/5 evidence never reaches band derivation.

`prepare_run.py` accepts `--genre memoir|other` (default `memoir`) and `--readers=N` (default 1). The default `standard` preset enables Seats 01-09 and 11. `--source` satisfies fidelity Seat 01's input condition. `--brief` makes `standard` add editorial-intent Seat 10 and activates Seat 10 when `full` or `custom(...)` already selects it; `quick` does not expand merely because a brief is present. The base `quick` set is 01, 02, 03, and 08, but memoir runs automatically add ethics Seat 11; because the literary core is absent, a closed quick run has literary band N/A. `full` covers Seats 01-11, while missing source or brief inputs are disclosed as coverage gaps. A memoir `custom(...)` run that explicitly excludes Seat 11 also creates a warning gap.

Seat 03 criterion A7 is cross-chapter only. It enters the packet only when `--source` points to a directory containing at least two files recursively; no source, a single file, or a one-file directory does not activate A7.

Mutual blindness is a hard gate: formal review requires real, independent subagents. If the host cannot create isolated subagent contexts, execution fails closed by default. With explicit user approval it may produce only a diagnostic marked `degraded=true`; it must not claim mutual blindness. Derivation rebuilds the canonical run plan and verifies every dispatched packet SHA-256; abstentions cannot silently become an A band.

Each `lit-naive-reader` follows a strict two-step protocol. Step 1 receives only the target text and freezes the natural reading experience. Step 2 either follows up in the same context or starts a different context with the sealed Step 1 text. `execution-receipt.json` records `step_2_mode`, both context ids, and the Step 1 SHA-256 for every reader; multiple readers remain mutually isolated.

`derive_report.py` emits `formal=true` only when native subagents are proven, `degraded=false`, every dispatch/output and Seat 08 proof is complete, input digests and verification receipts match, and `coverage_gaps=[]`. Any degradation, failed or non-isolated dispatch, missing artifact, or invalidated quote produces a diagnostic with `bands.fidelity=null`, `bands.literary=null`, and recommendation `仅诊断`. Diagnostic `null` is distinct from a formal N/A for a dimension that was legitimately out of scope.

## Closed-run commands

```bash
python3 core/lit-panel/scripts/prepare_run.py text.md \
  --preset standard --genre memoir --readers 1 --output runs/example

# Dispatch native subagents from packets and write execution-receipt.json, then:
python3 core/lit-panel/scripts/validate_execution_receipt.py runs/example/execution-receipt.json
python3 core/lit-panel/scripts/verify_quotes.py runs/example/seat-outputs runs/example/text.txt \
  --output runs/example/verification-receipt.json
python3 core/lit-panel/scripts/derive_report.py \
  runs/example/seat-outputs runs/example/verification-receipt.json \
  runs/example/run.json runs/example/execution-receipt.json \
  core/lit-panel/references/criteria --text runs/example/text.txt \
  --output-json runs/example/derived-report.json \
  --output-markdown runs/example/report.md
```

When a source is present, pass the same `--source <file-or-directory>` to both `verify_quotes.py` and `derive_report.py`. When a brief is present, also pass the unchanged `--brief <file>` to `derive_report.py`. Its five positional arguments are seat outputs, verification receipt, run manifest, execution receipt, and criteria directory; the older interface is no longer valid. A non-null source/brief digest in `run.json` fails immediately if the matching argument is absent or its content changed.

## Evidence artifacts

A closed run preserves at least six artifact classes:

- `run.json`, freezing input digests, genre, reader count, seats, and expected outputs;
- `execution-receipt.json`, proving host-native isolation, packet dispatch, the Seat 08 two-step flow, and coverage gaps;
- one JSON response per seat conforming to `seat-output.schema.json`;
- `verification-receipt.json`, recording each quote match or invalidation;
- `derived-report.json`, containing mechanically derived bands, red lines, revisions, and arbitration items;
- `report.md`, either the human-facing formal review or an explicitly labeled diagnostic projection.

Every YES/NO judgment requires a verbatim quote. Schema validation and mechanical quote verification occur before synthesis; a failed quote invalidates the entire criterion, prevents formal closure for that run, and cannot affect a formal band. The project permits qualitative A/B/C/N/A bands only—never an aggregate numeric score, percentage, or weighted total.

## Architecture

```text
core/lit-panel/                 # single source of runtime semantics
  SKILL.md
  agents/
  references/
  schema/                       # run / execution / seat / verification / report
  scripts/
adapters/
  codex/
  claude/
  antigravity/
scripts/build_dist.py           # generates three dist trees and root compatibility surfaces
dist/                           # generated distributions
```

Do not edit `dist/`, root `skills/lit-panel/`, or root `agents/` directly. Change `core/` or `adapters/`, rebuild, and run:

```bash
python3 scripts/build_dist.py --check
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/release_check.py
claude plugin validate --strict dist/claude
agy plugin validate dist/antigravity
```

## Privacy and release

`tests/fixtures/` and `tests/runs/` are permanently excluded so real contributor material cannot be tracked or packaged. Release gates also reject these directories inside distributions, machine-local absolute paths, inconsistent manifest versions, and missing self-contained runtime assets.

See [compatibility and degradation](docs/COMPATIBILITY.md), [architecture](docs/ARCHITECTURE.md), and `core/lit-panel/SKILL.md` for the complete contract.

## Official references

- [Codex 0.147.0 release](https://github.com/openai/codex/releases/tag/rust-v0.147.0)
- [Build plugins for Codex](https://developers.openai.com/plugins/build/plugins)
- [Codex custom subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Claude Code subagents](https://code.claude.com/docs/en/sub-agents)
- [Antigravity CLI plugins](https://antigravity.google/docs/cli/plugins)
- [Antigravity subagents](https://antigravity.google/docs/subagents)

MIT License
