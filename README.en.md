[简体中文](README.md) | [English](README.en.md) | [Français](README.fr.md) | [Español](README.es.md)

# lit-panel

*An eleven-seat, mutual-blind literary review panel for Chinese memoir / narrative text — a Claude Code / Codex / Google Antigravity skill.*

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg) ![Version: 0.4.1](https://img.shields.io/badge/version-0.4.1-lightgrey.svg)

For the same Chinese memoir / narrative text, eleven review seats read independently without seeing each other's conclusions. Explicit rule-based orchestration logic synthesizes the output — yielding qualitative band assignments, verbatim evidence, and multi-dimensional scores mechanically derived from a criteria vector (the review seats themselves practice zero-scoring; scores are a derived view, not seat judgments).

## Why It Exists

Giving a memoir chapter a "7.5/10" seems objective, but in reality it compresses countless incommensurable judgments into a false precise number — change prompt phrasing or switch models, and this number often drifts without telling you what worked, what failed, or who made the decision.

Avoiding numeric scoring is not an aesthetic preference; it is an evidence-based choice. Multiple criteria in this project (TW series in Seats 04/05/06/07/09) are adapted from **TTCW** (Torrance Test of Creative Writing) — when TTCW itself evaluates creative writing quality, it uses a set of binary criteria evaluated item-by-item by professional writers rather than a continuous score; early research testing LLMs as TTCW reviewers showed model judgments often misaligned with professional human writers. Numeric scores flatten this misalignment into a deceptively certain number; lit-panel chooses to preserve divergence rather than flattening it.

The response of lit-panel is to abandon the continuous scale itself and produce only three concrete deliverables:

- **Criteria** — whether a specific, observable textual behavior is satisfied;
- **Evidence** — verbatim quote spans supporting the verdict, mechanically verified (unverifiable quotes are invalidated directly);
- **Bands** — A/B/C qualitative categorization instead of a continuous scale.

The final output of the report is **Bands (A/B/C) + Verbatim Citations + Disagreement Zone + Revision Package + Multi-Dimensional Scorecard mechanically derived from a criteria vector** (added in v0.4.0+). **The review seats themselves practice zero-scoring** — the Section 3.4 output contract has not changed a single word; seats do not generate or need awareness of numbers; scores are an open formula derived **view** from the criterion vector, fully reproducible across the text (see `SKILL.md` §5.8). The design opposes pseudo-precise numbers from model impression (unable to explain where "7.5/10" came from and drifting with every re-prompting), not numbers themselves. Qualitative bands remain qualitative conclusions, and scores are another presentation of the same criteria evidence — the two do not contradict nor replace each other.

## Core Mechanics

This section is a streamlined overview for users. The authoritative runtime specification is `skills/lit-panel/SKILL.md` (the single orchestration logic shared across platforms); the build-time specification is in `docs/DESIGN.md`. In case of conflict, `SKILL.md` takes precedence.

### Eleven-Seat Review Panel

| Seat | Direction | Activation Condition | Band Role / Special Permissions |
|---|---|---|---|
| **01** `lit-fidelity` | Sources only: claim backtracing with five-state labels (SUPPORTED/PERMISSIBLE_INFERENCE/UNSUPPORTED/CONTRADICTED/UNVERIFIABLE) | When `--source` provided | Sole source for Fidelity Band; Red-line veto power |
| **02** `lit-continuity` | In-text consistency: time/character/fact/norm consistency | Always | Evidence seat; Red-line veto power on confirmed contradictions |
| **03** `lit-slop` | AI artifacts: span tagging against pattern library (light/heavy) | Always | Evidence + feature seat; No veto power |
| **04** `lit-structure` | Narrative structure: scene/summary, setup/payoff, chapter layout | Always | Literary band core seat |
| **05** `lit-character` | Character & psychology: motive continuity, dialogue voice, anti-whitewashing | Always | Literary band core seat |
| **06** `lit-prose` | Language & rhythm: voice consistency, transitions, word precision | Always | Literary band core seat |
| **07** `lit-resonance` | Emotion & arrival: processed vs lived experience, anti-forced emotion | Always | Literary band core seat |
| **08** `lit-naive-reader` | Naive reader: no criteria before reading, pure experience report, post-test check | Always (strict two-step execution) | Synthesized judgment participant, excluded from criteria vector; post-test model |
| **09** `lit-originality` | Originality & cliché: human writing tropes, personal voice | Always | Bonus dimension (v0.4.1+ excluded from band, issues demoted to polish suggestions) |
| **10** `lit-brief` | Editorial intent: brief elements, dramatic purpose fulfillment | Preset scope contains 10 AND `--brief` provided | Excluded from band; unfulfilled items convert to revisions |
| **11** `lit-ethics` | Ethics & otherness: unilateral characterization, privacy necessity, dignity of vulnerable | Default active for memoir (`custom` explicit exclusion still triggers report warning) | Excluded from band; findings always force human arbitration |

**Preset tiers**: `quick`=01,02,03,08; `standard`=01–09+11 (does not include 10; when `--brief` is provided, 10 is automatically included without needing `custom`); `full`=01–11 (if 01/10 are not activated due to missing input, they are marked at **WARNING** level under "Skipped Seats & Reasons" in the report, because the explicit intent of full is to enable all eleven seats); `custom(<list>)`=select any seat numbers from the table above, e.g. `--preset custom(01,03,08)`. Numbers must be registered in `registry.md`, otherwise it is treated as a parameter error and halts immediately. Conditionally activated seats are automatically skipped when conditions are not met, with reasons noted in the report header.

### Three-Phase Process

```
Input: Target text + optional --source (source material) / --brief (editorial brief)
        │
        ▼
Phase 0 · Mechanical Pre-check —— Fatal failure gateway: text truncation/unclosed → immediate abort;
                      metadata stripping, genre check, brief mechanical verification
        │
        ▼
Phase 1 · Mutual-Blind Parallel Review —— 11 seats review independently with their own criteria files,
                          mutually blind (Seat 08 executes in 2 steps: pre-reading experience → post-reading check)
        │
        ▼
Phase 2 · Mechanical Quote Verification —— Verbatim quote verification for every quote against source;
                          unverified quotes invalidated (invalidation mechanism) ——
                          this is the defense line preventing fabricated quotes from "poisoning" the evidence chain
        │
        ▼
Phase 3 · Explicit Rule Synthesis —— Red-line alerts / criteria vector / band assignment / score export /
                          disagreement zone / human arbitration / decision recommendation / revision package,
                          mechanically summarized without secondary aesthetic adjudication
        │
        ▼
Output: Structured Review Report + Details Sidecar
     (references/report-template.md structure + <report_name>-details.md)
```

`--stability` appends an independent second run post-Phase 3 to measure criteria flip rates; `/lit-compare` runs an independent comparison pipeline (see "Parameter Reference") without reusing the Phase 3 band assignment/decision matrix.

### Three-Tier Criteria Banding

Fidelity Band (Seat 01) and Literary Band (Seats 04/05/06/07) are evaluated on their separate criteria sets and are never merged into a single total band.

Literary Band criteria are divided into three tiers:

- **veto** — at most ≤2 fatal core criteria per seat; a hit represents a structural collapse in that dimension. For example, Seat 07 (Resonance) fills its 2 veto slots: emotion completely un-dramatized and merely announced by narrator / emotion forcibly dramatized to distortion — hitting either symmetrical extreme means emotional execution in this chapter fundamentally fails. See `criteria/CHANGELOG.md` v0.2.0 for per-seat criteria listings and selection rationale.
- **core (ordinary)** — remaining non-veto criteria in that seat's core criteria table.
- **extended** — supplementary criteria that do not participate in band assignments, but are still evaluated normally and enter the criteria vector.

Band evaluation follows priority rules from top to bottom, stopping at the first hit:

1. Veto issue verdict present and severity=**HIGH** → Literary Band capped at **C**;
2. Veto issue verdict present but severity=MEDIUM/LOW → Maximum capped at **B** (does not trigger C) + forcibly escalated to Human Arbitration Zone;
3. Conditions 1 and 2 not met, but ordinary core criteria have any issue verdict → Maximum capped at **B**;
4. Veto + core all pass → **Candidate Band A** — candidate does not mean final; text texture must be checked against `anchors/band-a.md` to confirm equivalence to anchor samples; if noticeably inferior, demoted to B.

**Severity is not a descriptive ornament, but a direct switch operating in four mechanical places**:

1. Fidelity Band threshold — only UNSUPPORTED with severity=HIGH triggers Fidelity Band C cap; issues with severity=LOW cap at B;
2. Red-Line admission — only Seat 01 UNSUPPORTED and Seat 02 confirmed contradiction NO with severity=HIGH enter the Red-Line Zone;
3. Veto tier grading — for issue verdicts on the same veto criterion, severity=HIGH caps at C, while severity=MEDIUM/LOW caps at B and escalates to human arbitration;
4. Revision package ordering — severity (HIGH/MEDIUM/LOW) determines priority order for revision sessions, but does not convert into numerical deductions.

### Originality Bonus (Seat 09, Excluded from Band)

From v0.4.1+, Seat 09 (Originality & Cliche Review) exits the veto/core three-tier band system above — no point deductions, no band capping. Seat 09 is evaluated as usual (verdicts + quotes + free opinion unchanged), but its verdict results exclusively drive total score **bonuses**, with mechanical rules detailed in `SKILL.md` §5.8:

- O-series pass criteria (O2/O3/O5/O6) **all** YES and zero O-series issue verdicts → Total score **+5**;
- Pass criteria ≥3 items YES and zero issue verdicts → Total score **+3**;
- All other cases (including any O-series issue verdict) → **+0**, **no point deductions under any circumstances**.

Issue verdicts (such as O1 hitting overuse of clichés) are demoted to optional polish suggestions, entering the report's "Issues & Revision Suggestions" and "Individual Seat Commentary" sections without being silenced or affecting band assignments. The product stance of this change: originality for memoir text is icing on the cake, not a core obligation — a plain but authentic life story remains a qualified memoir and should not have its band dragged down by a lack of literary novelty (reasons detailed in `criteria/CHANGELOG.md` v0.4.1).

### Naive Reader Alarm

When all veto+core criteria across the four Literary Band core seats **pass completely**, which would normally produce a Candidate Band A, one extra check is performed: Seat 08 (Naive Reader) post-reading Question 4 — "Would you recommend this text to others?" (accepts only "Yes" / "No", rejecting vague answers like "It depends").

- **N=1**: Answer "Yes" → Candidate Band A stands as normal, proceeding to anchor matching. Answer "No" → Trigger alarm: **does not automatically issue A, nor demote because of it**; decision recommendation is rewritten to "**Candidate Band A (Pending manual confirmation — divergence between criteria and reader sentiment)**", forcibly transferred to Human Arbitration Zone.
- **N>1**: Governed by majority vote of "Yes" / "No" answers; ties are treated as "No" — preferring to trigger an extra manual check over silent approval.
- The alarm is meaningful only under the precondition of "zero core issue verdicts" — if the criteria evaluation has already capped the band at B or C due to veto/core issues, a "No" answer from naive readers does not trigger an extra alarm, as the issue was already captured by criteria.

This replaces the retired v0.1.1 design of "naive reader positive participation in Band A condition". The old design had naive readers directly participate in A/B/C verdicts; the new design excludes naive readers from band assignment, serving only as a final reader experience sanity check when criteria "look entirely clean" — once criteria and reader experience diverge, it is handed to humans, not decided by mechanism.

### Mutual Blindness & Anti-Bias Design

- **Swap-order double review (only `/lit-compare`)**: In comparison mode, each seat evaluates preference between A and B twice — once presented as (A,B), once presented as (B,A). Preferring the same text twice → record that seat's preference; preference flipping with presentation order → record **TIE**. This design specifically detects position bias where a reviewer simply favors presentation order. Output provides distribution counts only, without converting into total scores or weighted rankings.
- **Structural isolation in parallel path (Antigravity / Claude Code)**: Under Google Antigravity, the eleven seats are dispatched concurrently as isolated Subagents via `invoke_subagent`; under Claude Code, they are dispatched via Task tools. Both provide structural guarantees of mutual blindness.
- **Explicit declaration of forgetting in sequential path (Codex)**: Codex lacks native parallel capability. When the main session plays each seat sequentially, it must explicitly declare "This seat's review ends here; discarding all conclusions from this seat" before switching to the next seat. This uses explicit instructions to prompt the model to actively simulate forgetting — because in sequential execution, dialogue context is continuous. This statement is not a formality; it is the sole implementation of mutual blindness discipline in a non-parallel environment (it remains a simulation, details in "Known Boundaries and Risks" below).
- **Cross-family review recommendation**: If generation and review use the same model / same session, the "Model & Session Disclosure" field in the report header must disclose this truthfully, recommending cross-family review (e.g. Claude generation → Codex review, or vice versa) to reduce single-source blind spots where the same set of latent biases writes and judges.
- **Free opinion field & anti-Goodhart design**: Every seat output contract contains a "Free Opinion" section alongside its criteria table (1–3 paragraphs of professional intuition unconstrained by criteria). Together with Seat 08's "no criteria before reading" mechanism, these are the only two expression spaces outside the criteria table that cannot be bypassed by "cramming for the exam" — see Goodhart risk discussion below.

## Installation

### Google Antigravity (Skill Mode)

```bash
# Recommended: Use installer script for global installation (~/.gemini/config/skills/lit-panel)
./scripts/install-antigravity.sh

# Or install to current project workspace (.agents/skills/lit-panel)
./scripts/install-antigravity.sh --workspace
```

Antigravity automatically discovers the installed skill. Once installed, start a conversation with `/lit-review <text_path>` or a natural language review request. Antigravity will dispatch the 11 review seats concurrently via `invoke_subagent`, using lightweight and efficient intermediate reasoning models (`flash`) in physically isolated contexts, and interactively handle Seat 08's two-step follow-up via `send_message`.

### Claude Code (Plugin Mode)

Three methods, choose as needed:

```bash
# Method 1: Copy manually to local skills directory (auto-loaded as lit-panel@skills-dir on next Claude launch)
cp -r /path/to/lit-panel ~/.claude/skills/lit-panel
# Symlinks are also supported for easy repository updates:
ln -s /path/to/lit-panel ~/.claude/skills/lit-panel
```

```bash
# Method 2: Register as local marketplace and install (persistently active, another officially supported path)
# The repository root includes .claude-plugin/marketplace.json, no need to create manually.
claude plugin marketplace add /path/to/lit-panel
claude plugin install lit-panel
```

Tested and verified in an isolated HOME environment (`HOME=$(mktemp -d) claude plugin marketplace add ...`), the two commands output:

```
✔ Successfully added marketplace: lit-panel (declared in user settings)
✔ Successfully installed plugin: lit-panel@lit-panel (scope: user)
```

`claude plugin details lit-panel` confirms component manifest: 3 skills (`lit-panel` / `lit-review` / `lit-compare`) + 11 agents, matching source directory structure. If your local marketplace registration name differs from plugin name (e.g., if you changed the `name` field in `marketplace.json` after forking), verify registration name with `claude plugin marketplace list`, then install with `claude plugin install lit-panel@<registered_name>`.

**A detail discovered during testing**: After installing as a plugin, agent component names listed by `claude plugin details` are **filenames** (such as `ethics-reviewer`), not the `name` field in agent definition frontmatter (such as `lit-ethics`) — the "dispatch fallback rule" in `SKILL.md` §3.3 is prepared for this situation: if dispatching Task subagents by `registry.md` agent name fails, retry using the identifier actually listed by the platform.

```bash
# Method 3: Temporary single-session load (no persistent install, suitable for trying out)
claude --plugin-dir /path/to/lit-panel
```

Once installed, `/lit-review` and `/lit-compare` commands are ready to use. The eleven review seats are natively scheduled in parallel as subagents by Claude Code.

### Codex (Skill Mode)

```bash
# Recommended: Use installer script (detects existing installation and asks before overwriting, default no overwrite)
./scripts/install-codex.sh

# Or copy manually
cp -r skills/lit-panel ~/.agents/skills/lit-panel
```

**Newly installed skills are not automatically discovered in current session**: Codex scans skill directories only at session startup; active sessions will not re-scan. To use immediately after installation, choose one of two options: start a new Codex session; or directly instruct Codex to read `~/.agents/skills/lit-panel/SKILL.md` by absolute path without relying on auto-discovery.

Codex lacks native parallel subagent mechanisms like Claude Code. Therefore, the eleven review seats on Codex are orchestrated by `SKILL.md` for **sequential execution seat by seat** — mutual blindness semantics strive for equivalence (each seat remains an independent context invisible to others), but as described in "Known Boundaries and Risks" below, this is best-effort simulation, not true context isolation.

## Quick Start

```bash
# Single text review: standard preset (01–09+11) with interview source material to activate Seat 01 Fidelity Review
/lit-review chapter.md --source interview.md --preset standard
```

```bash
# A/B comparison: two texts of same origin/task, eleven seats default comparative review, swap-order evaluation per seat
/lit-compare a.md b.md
```

What the report looks like: A `/lit-review` report (restructured in v0.4.0+) strictly contains eight fixed sections, **section titles without numbers, physical sequence being reading sequence** — Executive Summary (panel review style summary, 2–3 paragraphs), Red-Line Alert (appears only when source provided and triggered, immediately following summary and preceding scorecard), Overall Scorecard (total score / band grade / one-sentence verdict, mechanically derived), Multi-Dimensional Scorecard (Literary four dimensions + Originality bonus dimension + AI Cleanliness + Reader Experience, with Fidelity added when source provided), Individual Seat Commentary (one paragraph per seat in true panelist tone, issue quotes woven inline, tables forbidden), Issues & Revision Suggestions (prose format of revision package), Human Arbitration Required (appears only when content exists; narrative entries detailing parties, respective positions, and why human decision is required, no criteria tables), Review Archive (streamlined header table) — fixed structure, regardless of text length or issue count. Full per-seat criteria tables, Stage 2 verification logs, and raw criteria tables for human arbitration are **not inline in main report**, but moved to sidecar file `<report_name>-details.md`, with pointers in Review Archive. Complete structure see `skills/lit-panel/references/report-template.md`. `/lit-compare` uses an independent comparison output structure (per-seat preferences + rationale + panel distribution), without reusing this band/scoring/decision framework.

## Parameter Reference

| Parameter | Values | Description |
|---|---|---|
| `--preset` | `quick\|standard\|full\|custom(<list>)` | Determines candidate seat scope for this run, default `standard`. Four preset definitions see "Eleven-Seat Review Panel" above; seat numbers in `custom(<list>)` must be registered in `registry.md`; unregistered numbers halt directly at mechanical pre-check. |
| `--source <source_path>` | File or directory path | Provides interview transcripts or source materials. Activates Seat 01 (Fidelity Review, sole source for Fidelity Band, red-line veto power). When omitted, Fidelity Band records N/A, and a mandatory warning header is output below report title. |
| `--brief <brief_path>` | File path | Provides editorial brief / assignment sheet. One of necessary conditions to activate Seat 10 (preset scope must also contain 10); triggers brief pre-processing in Phase 0 (extracting core dramatic purpose + key dramatic tasks summary) and hard constraint mechanical verification (word count range / specified start/end / structural components / forbidden keywords). |
| `--stability` | Flag (no value) | Triggers stability self-check: runs two quiet full evaluation passes on same text/config (mutually blind between runs), reporting per-seat criterion flip rates (no single aggregate rate). Supplementary output independent of main review report, without affecting decision recommendations. |
| `--readers=N` | Positive integer, default `1` | Number of independent reader instances for Seat 08 (Naive Reader). N readers are mutually blind, each completing two-step "no criteria before reading → post-reading check"; report lists sections by reader index. Unrelated to seat selection; filter participating seats using `--preset custom(<list>)`. |
| `--fast-compare` | Flag (no value), default off | Valid for `/lit-compare` only. Default swap-order double review unchanged; passing flag runs single pass per seat (no order swap) + intra-seat self-check declaration to gain speed, outputting mandatory disclosure in header: "Swap-order double evaluation omitted; position bias unprotected". Suitable for iteration rounds, not recommended for release gates. |

## Performance Expectations

Below are benchmark timing references measured in testing (not guarantees; actual runtime depends on text length, model, network, and concurrency rate limits):

- **Codex (xhigh reasoning tier)**: `quick` preset (4 seats sequential) ~10 minutes; `standard` preset (10–11 seats sequential) ~30–45 minutes — sequential path invokes full model call per seat, runtime scaling approximately linearly with active seats.
- **Claude Code (parallel subagent)**: `standard` preset approximately equals **slowest single seat** runtime (5–8 minutes), because eleven seats are batch parallel Task calls where total runtime is bounded by slowest seat rather than cumulative.

**Advice**:

- Use `quick` for iteration rounds (edit draft, inspect issues); use `standard` or `full` for release gates (final evaluation before release, formal delivery judgments) — do not downgrade presets at release gates to save time; `quick` contains no Literary Band core seats, yielding an incomplete foundation for band assignment.
- Under Codex sequential path, reasoning tier for review seats can use `medium` instead of `xhigh` — answering criteria tables is structured step-by-step verification rather than open creative writing requiring heavy reasoning; medium tier is usually sufficient and significantly compresses cumulative sequential runtime.
- For `--source`, supply only transcripts/materials directly relevant to the current chapter; do not pass bulk unrelated chapters — source-side quote verification (Phase 2) searches within these materials; larger materials slow down verification without improving fidelity accuracy.

**Expected effect of v0.3.0 performance optimizations (estimation, pending verification)**: Tiered citation requirements (pass verdicts for most criteria no longer force quote citations) and single-post body optimization on sequential path (Codex body text posted once at session start rather than re-posted per seat) are expected to compress Codex `standard` sequential runtime from ~30–45 minutes down to **15–20 minutes**. These are estimates based on token/call savings of each optimization, pending end-to-end real-machine timing verification; section should be updated once measured numbers are confirmed.

## Reading the Report

A report is assembled strictly according to the structure in `references/report-template.md` (eight sections, see "Quick Start" above, section titles without numbers, physical sequence being reading sequence). Below is how to read each section and where numbers come from.

**Where numbers come from** — Review seats practice **zero-scoring** from beginning to end: Section 3.4 output contract contains only verdict/quote/location/severity/note without numeric fields. Every number in Overall Scorecard and Multi-Dimensional Scorecard is **mechanically derived post-hoc** by the orchestrator in Phase 3 applying deterministic formulas from `SKILL.md` §5.8 to the criteria vector — Literary four dimensions (Structure/Character/Prose/Resonance) each start at baseline 90, veto criteria issue verdicts capped by severity (HIGH → ≤45, MEDIUM/LOW → ≤65), ordinary core issue verdicts −12 each, extended −5 each; AI Cleanliness (derived from Seat 03), Reader Experience (derived from Naive Reader R-series), Fidelity (taken from Fidelity Band letter when source provided) dimension formulas operate independently; total score = simple average of Literary four dimensions, overlaid with Seat 03 adjustments (−3 each, max cap −10), **Originality bonus** (v0.4.1 addition — Seat 09 O-series pass criteria all YES with zero issue verdicts → +5, ≥3 YES with zero issue verdicts → +3, otherwise with issue verdicts → +0, additions only), and Fidelity Band total score caps (Fidelity Band C → total score capped at 45 with decision forced to "Rewrite Recommended"; Fidelity Band B → capped at 75, both remaining effective after bonus additions). Formulas are fully public, allowing anyone to recalculate and verify against criteria vector — this is precisely the difference between "evidence-driven" and "impression-based scoring": what is opposed is not numbers, but numbers with unexplainable origins. Overall Scorecard itself is rendered with H2 heading + bold text (such as "## Total Score: 45/100 · C"), with the entire report having only one H1 heading.

**Meaning of Qualitative Bands** — Bands are two independent qualitative tracks parallel to scores, not merged into a total score nor reverse-engineered from scores:

Fidelity Band (fully based on Seat 01 five-state distribution; recorded as N/A when `--source` omitted, in which case Fidelity row is omitted from Multi-Dimensional Scorecard): A = five-state distribution completely clean; B = no CONTRADICTED and no UNSUPPORTED with severity=HIGH, but issues with severity=MEDIUM/LOW exist, or only PERMISSIBLE_INFERENCE/UNVERIFIABLE without UNSUPPORTED/CONTRADICTED; C = CONTRADICTED present, or UNSUPPORTED with severity=HIGH present.

Literary Band (based on Seats 04/05/06/07 veto/core criteria; not produced under `quick` preset when no core seats present. Seat 09 Originality from v0.4.1+ exits this band for independent "Originality Bonus", see "Originality Bonus (Seat 09, Excluded from Band)" above): Grading rules see "Three-Tier Criteria Banding" above; additionally includes special state — "**Candidate Band A (Pending manual confirmation — divergence between criteria and reader sentiment)**", produced when Naive Reader Alarm triggers. If both bands are N/A (e.g. `quick` preset without `--source`), decision recommendation becomes "**Diagnosis Only**", listing only issue verdicts for reference without outputting matrix defaults to fake real decisions; Overall Scorecard also omits standard score.

**Red-Line Alert** — Sources are two only: Seat 01 CONTRADICTED or UNSUPPORTED with severity=HIGH; Seat 02 confirmed contradiction NO verdict with severity=HIGH. Appears after Executive Summary and before Scorecard when source provided and triggered, featuring paired quotes (verdict quote + source/comparison quote). Non-empty Red-Line Zone does not halt report — all remaining sections are produced completely, and Overall Scorecard appears normally (with total score capped at 45 under Fidelity Band C).

**How Individual Seat Commentary is written** — One paragraph per seat, sourced exclusively from excerpts and light edits of that seat's free opinion / reader experience report. Issue quotes are woven inline as markdown blockquotes, with synthesis layer forbidden from adding any evaluations lacking source in these materials — commentary is "editing", not "reviewing", an explicit hard rule in `SKILL.md` §5.9.

**Human Arbitration Required (merged presentation of former disagreement and human arbitration zones, appearing only when content exists)** — This section **completely forbids tables**, with each category written as narrative entries: parties involved, one-sentence position, inline quote citations, and why human decision is required (raw criteria tables moved to details sidecar "Human Arbitration Details" section, with pointer at end of this section). Disagreement: co-existence of "issue verdict" and "pass verdict" on same text span, or one seat's free opinion explicitly contradicting another seat's conclusion, are counted as disagreement — **no averaging, no weighting, no deciding right/wrong**, with both positions listed as narrative side-by-side for human/editorial judgment. Human Arbitration: the following verdict categories are never auto-passed nor auto-blocked —

1. All ABSTAIN verdicts (including ABSTAIN demoted from "NA without applicability rationale");
2. **All** verdicts from Seat 11 (Ethics & Otherness), regardless of verdict value — ethics findings are neither auto-passed nor auto-blocked;
3. Verdicts failing Phase 2 mechanical verification and invalidated (with invalidation reason, for checking if verification itself misjudged);
4. Veto criteria issue verdicts with severity=MEDIUM/LOW (severity judgment directly affects band assignment, requiring manual verification);
5. NA on veto criteria (NA still requires applicability rationale; without rationale treated as ABSTAIN, falling under Category 1 above; veto criteria have direct cap/arbitration consequences, so NA means missing judgment tier); NA on ordinary core/extended criteria (with rationale) does not belong here, presented normally in details sidecar without escalation;
6. Naive Reader Alarm trigger records.

When any category above is empty, that entire section is omitted without leaving placeholder empty headings.

**How Issues & Revision Suggestions feed back to generation sessions** — Summarizes Red-Line entries + all "issue verdicts" from criteria vector, each item = location + inline quote + rationale + revision advice, ordered by severity, with item IDs retaining criterion IDs, suitable for pasting whole sections into next revision session as task list. When same text location hits multiple criteria, only one merged task is generated (taking highest severity, merging revision suggestions), avoiding duplicate entries for same location. **Manual review notice**: mechanical verification guarantees only that quotes exist in original text, not that quotes support verdict assertions — a notice is appended at bottom of section recommending item-by-item manual review before execution.

**Review Archive & Details Sidecar** — Streamlined header table containing text name / preset & active seats (skipped seats merged into one sentence) / model & fallback disclosure / verification statistics / rule version, plus file path pointer to details sidecar. Full per-seat criteria tables + Phase 2 verification logs + raw criteria tables for human arbitration are no longer inline in main report, stored in sidecar `<report_name>-details.md` using former "Per-Seat Criteria Table Summary" format with appended "Human Arbitration Details" section. When `--source` omitted, archive appends a line: "No --source provided in this run; factual check omitted; score reflects text internal quality only" — this is the sole appearance location of fidelity disclaimer from v0.4.0+, replacing forced full-line warning banners under main title (Overall Scorecard itself echoes same fact in small text when source omitted, which is sufficient).

## Customization and Extension

**Criteria files are editable**: Phrasing of criteria in `skills/lit-panel/references/criteria/*.md` can be polished, but semantics and polarity (`[Pass]` / `[Risk]`) cannot be altered — altering semantics equals altering review standards themselves, requiring expansion/CHANGELOG workflow below rather than casual rephrasing.

**Record deprecations in CHANGELOG**: Selection, replacement, and deprecation of criteria must be logged in `skills/lit-panel/references/criteria/CHANGELOG.md`, one line per entry with reasons. v0.2.0 serves as reference example — recording selection rationale for ≤2 veto criteria across four Literary Band core seats, alongside audit results from reading all 11 criteria files to check semantic overlap.

**Private criteria (`criteria/99-private.md` pattern)**: All criteria files are distributed publicly with package. To restore "blind test" effect (extra criteria unknown to generation side in advance), create `skills/lit-panel/references/criteria/99-private.md` (or similar name), add to your `.gitignore` (not distributed with repo, not in public criteria pool), and mount as new seat or merge into existing criteria file following expansion steps below. Optional hardening for local environments; lit-panel itself presets no private criteria content.

**Seat Expansion (opening a new review seat)**: Three-piece synchronous actions, none optional —

1. Append a row to `registry.md` "Seat Registry Table" (agent file / agent name / criteria file path / one-sentence direction / activation condition / band role / special permissions, 8 columns no empty cells);
2. Add a new `agents/*.md` seat definition file;
3. Add a corresponding `criteria/*.md` criteria file, recording selection in CHANGELOG.

Before opening new seat, must pass "Four Admission Rules" (answering whether to open a whole new seat, not criterion quality standard):

1. **Independent Reading Method** — reading approach differs from existing eleven seats, not a subset split from existing seat criteria table;
2. **Criteria Overlap <20%** — substantive evaluation overlap with any existing seat must be under 20%, otherwise merge into existing seat;
3. **Exclusive Evidence Form** — produces evidence form or process role unachievable by other seats (such as Seat 01 source quotes, Seat 08 two-step process, Seat 11 forced human arbitration);
4. **Removal Misses Defect Class** — if seat removed from `full` preset, does a real class of defects become completely uncaptured by any remaining seat? Answer "No, other seats cover it" fails admission.

All four rules must be satisfied to add seat. Independent second-tier check — **new criteria themselves** (whether added to existing or new seat) must pass criteria design meta-specification (end of `docs/criteria-pool.md`): RaR four elements, HealthBench three rules, Antislop context warning, ablation warning. Two checks govern different concerns (whether to open new seat / whether single criterion is well written), non-interchangeable. Full operational steps see `registry.md` "Seat Expansion Guide".

## Known Boundaries and Risks (Honesty Zone)

An anti-AI-slop tool would be hypocritical if its own README avoided risks and boundaries.

**Quote verification prevents fabrication, not misinterpretation**: Stage 2 verbatim verification solves one problem — whether text actually appears in original work. It prevents "fabricating quote non-existent in original", but not "quote exists, but note assertion/interpretation of quote is invalid". The latter is beyond mechanical verification capability, handled by mutual-blind cross-checking and human arbitration. Report users should know defense line stops here — do not read "quote passed verification" as "verdict assertion is guaranteed sound".

**Sequential path mutual blindness is best-effort simulation, not context isolation**: Under Claude Code, eleven seats are parallel Task subagents with naturally isolated context, providing structural guarantee of mutual blindness. Codex lacks native parallel subagents, main session playing each seat sequentially, relying on "explicitly declaring discarding previous seat conclusions" to simulate uncommunicative human panelists — role-play within same dialogue context, not truly independent processes or sessions. Semantics strive for equivalence, but underlying mechanics differ; scenarios requiring strict mutual blindness should recognize this distinction.

**Public criteria are a double-edged sword (Goodhart's Law)**: All criteria files are distributed publicly with package, providing foundation for "auditable, verifiable, refutable" tool design, but also meaning if generation models are specially trained or prompted to "cram for" specific criteria sentences, they could theoretically make criteria tables look better without improving text quality — once indicator becomes target, it loses value as indicator. Naive Reader (Seat 08) and per-seat "Free Opinion" fields serve as natural anti-cramming surfaces: naive reader sees zero criteria before reading, free opinion is unconstrained by criteria tables, neither being fixed targets bypassable by cramming. Scenarios requiring stronger resistance see "Private Criteria" above.

**Seat 11 does not replace offline pre-publication consent**: Seat 11 evaluates whether **in-text presentation** carries ethical risks (unilateral characterization, privacy necessity, misattribution, dignity of vulnerable), not replacing offline consent/authorization checks for real living individuals. Decent presentation in text does not equal obtaining publication consent from persons involved — this step still requires human completion outside text.

**LLM literary judgment has a ceiling; panel compresses variance, not replacing final editorial judgment**: Eleven-seat mutual blindness + mechanical verification + explicit rule synthesis achieves compressing subjective arbitrariness and one-off drift of "casual scoring", making judgments auditable, queryable, and refutable. What it cannot do is replace final editorial or critic judgment — Disagreement Zone intentionally preserves "panel seats may disagree with each other", without attempting to flatten disagreements into fake consensus using complex synthesis rules.

### Verification Boundaries (As of v0.4.1)

The following mechanisms **have real-machine execution evidence** (completed full review at least once with recorded logs): mutual-blind dispatch (both Claude Code parallel Task subagent path and Codex sequential simulation path tested); verbatim verification + poison invalidation (re-running verification after tampering quote, confirming verification pipeline blocks fabricated quote rather than self-declaration); report assembly under `quick`/`standard` presets; cross-family review (executing review across model families with zero deviation); **full fidelity chain** (v0.2.1 rule final test: `--source` directory file-by-file verification, five-state labels, CONTRADICTED triggering Red-Line Zone and Fidelity Band C, matrix output "Rewrite Recommended" — fidelity seat caught pivotal factual inaccuracy with 7/7 source quote hits); **veto three-tier banding** (veto criteria severity hit → "Max B + Manual Review" branch verified, contrasting old rule false-positive Band C cap from single ordinary core issue); **NA rules** (NA with rationale when core criteria precondition missing, avoiding mechanical band capping); **dual-quote note contract** (89/89 verifications with zero invalidations and zero format violations, old-style "/" quote concatenation eliminated); **disconnection handling protocol** (all ten seats returned, contrasting old round seat permanent loss); naive reader two-step check with follow-up collection.

The following mechanisms **have not undergone end-to-end real-machine execution verification**: Naive Reader Alarm "Block A" branch and Candidate A anchor matching (rule reachability confirmed, but requires Band A candidate text to trigger — no evaluated text reached this branch yet); Seat 10 (Editorial Brief Review, requiring `--brief`); `--stability` self-check; `/lit-compare` comparison mode (including `--fast-compare`); multi-reader aggregation with `--readers` > 1; native parallel scheduling **after installing as Claude Code plugin** (marketplace install chain verified with correct component listing, but actual parallel review invocation post-install unverified); **runtime re-measurement of v0.3.0 performance improvements** (v0.3.0 numbers in Performance Expectations section are estimations); **v0.4.0 report layer restructuring and score export layer overall** (§5.8 formulas verified by manual recalculation on historical real-machine data — zhang-ch01 v0.2.1 final test — confirming formula calculability and reproducibility, with `tests/runs/zhang-ch01-v040-format-sample.md` being rendered sample; but formulas not yet actually invoked by orchestrator during real end-to-end review run — manual recalculation does not equal real-machine execution verification); **v0.4.1 Originality Bonus system** (Seat 09 exit from veto/band to pure bonus) similarly unverified by real-machine re-testing — existing `tests/runs/` historical data originates from pre-v0.4.1 snapshot; this version sample is manual recalculation of old data using new formula, not end-to-end review run activating new rules; should be verified with real-machine run post-release.

This list will be updated with subsequent real-machine testing — before verification, treat these mechanisms as "consistently designed, not yet empirically verified" rather than "verified reliable".

## Privacy

- Package samples in `skills/lit-panel/references/anchors/` (A/B/C tier reference samples) are **entirely synthetic texts**, containing zero real biographical details.
- Submitted text and materials (`--source` / `--brief`) circulate only between your local Claude Code / Codex session and model APIs; lit-panel itself introduces no network transmission, collection, or exfiltration paths beyond model calls essential for review.
- **Recommendation for separate generation and review sessions**: Do not have model write draft and review its own writing in same conversation — generation side self-evaluation is not review truth, as accurately noted in report header "Model & Session Disclosure". Where possible, recommend cross-family review (e.g. Claude generation → Codex review, or vice versa) to reduce single-source blind spots.

## Method Tracing and Acknowledgments

Criteria are not written out of thin air. Every criterion carries a tracing label ([Verified] / [Translated] / [Second-hand pending] / [Self-developed]); complete per-criterion tracing list see `docs/criteria-pool.md`; here we list main sources system draws from:

- **TTCW** (Torrance Test of Creative Writing) — direct translation source for TW series criteria across narrative rhythm, scene/summary balance, ending naturalness, transition logic, character complexity, emotional flexibility, rhetorical complexity, distributed across Seats 04/05/06/07/09, with TW5 ("elements coalesce into unified, intelligible, satisfying whole") merged into Seat 02 (Continuity) as closing coherence criterion.
- **ConStory** — source for core factual/consistency conflict classification in Fidelity and Continuity review (naming confusion, quantity conflict, temporal conflict, simultaneity conflict, memory conflict, geographic conflict, social norm violation).
- **Measuring AI Slop** (with Antislop lexicon method) — source for Seat 03 AI Slop Detector 3-theme 11-dimension classification (density, template, repetition, unnatural language, verbosity, improper word choice, tone/register), as well as discipline rule that "lexicon hit does not equal error, verdict must pass context review".
- **EssayBench** — source for narrative writing technique criteria across structure, character, prose, resonance (material selection, layering, characterization, environment description, paragraph structure).
- **HANNA** — source for high anchor criteria in Naive Reader engagement and surprise.
- **HealthBench** — source for criteria design three rules (one criterion checks one observable behavior; listings after "e.g." non-exhaustive; risk criteria check whether bad phenomenon appears).
- **RaR** — source for criteria design four elements (expert guidance basis; covers common failure modes; core/extended/fatal tiering forbidding numerical weights; each self-contained and independently answerable).

Additionally, AlignBench, EQ-bench, factool, lechmazur, Gaokao essay grading standards are distributed across individual seat criteria; complete list see `docs/criteria-pool.md`.

**Special Thanks**: In Seat 03 criteria dictionary `slop-patterns-zh.md`, Chinese AI pattern classification references open-source classification ideas from **shuorenhua** (MIT License, Chinese AI taste detection project) and **speak-human-tw** — sample sentences re-written for memoir/oral history register without copying word-for-word or 1:1 mapping.

## License

MIT © 2026 Anamnese Project — see [`LICENSE`](./LICENSE).
