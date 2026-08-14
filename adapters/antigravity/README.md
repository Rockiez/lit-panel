# Antigravity adapter

Requires Antigravity CLI 1.1.12 or a compatible IDE/2.0 build. Each generated custom agent is subagent-only and inherits the host model by default. The orchestrator issues one independent `invoke_subagent` call per packet and may run several calls concurrently; it does not assume an undocumented single batch-array API.

Every successful invocation must be correlated with its packet, custom-agent seat, reader id, context id, isolation, and status in `execution-receipt.json`. Each Seat 08 reader must prove either a same-context `follow-up` or a different `sealed-new-context`, including the SHA-256 of the frozen first-read text. Static plugin validation or discovery of 11 agents does not satisfy this runtime gate.

As of the 2026-08-14 local black-box run, plugin validation and installation passed, but the provider session did not produce a valid `invoke_subagent` receipt for the installed lit-panel agent. The Antigravity provider path therefore remains fail-closed: no formal bands may be emitted until the native invocation and closed execution receipt are observed.
