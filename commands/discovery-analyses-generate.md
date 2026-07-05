---
description: Generate the three analyses: Hierarchy of Needs, PPT, and Maturity Curve
argument-hint: <release-folder>
---

# Generate the three analyses: Hierarchy of Needs, PPT, and Maturity Curve

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Tracing (opt-in, off by default)

# Tracing — Detailed, Opt-In, Step-Level Execution Trace

## Purpose

`execution_log.md` records one terse row per whole command (timestamp, command, result, a detail string capped at 120 characters). That's enough for a normal audit trail, but it can't answer "what actually happened inside that command, step by step" — which specific files it read, what it inferred, what it proposed, what a consultant decided, why. Tracing exists for engagements that want that depth: a complete, structured, append-only record of every step of every command, scoped to the release and release type it ran under.

**Off by default.** Tracing never runs unless `WIRE_TRACE=true` is set in the shell environment. If it isn't, skip this entire section — do nothing, check nothing further, proceed straight to the Workflow Specification exactly as if this section didn't exist. This is the common case and must add zero overhead.

## Where it writes

`.wire/releases/<release_folder>/trace.jsonl` — one JSON object per line (JSON Lines), append-only, alongside that release's `status.md` and `execution_log.md`.

For commands not scoped to a specific release (cross-cutting utilities with `release_types: []` in their own front-matter, or any command whose argument isn't a release folder), write to `.wire/trace.jsonl` at the engagement level instead, with `release` and `release_type` fields set to `null`.

This file is **local only** — nothing in it is ever sent anywhere, unlike the anonymous Segment telemetry event described elsewhere. It stays on the consultant's machine, inside the engagement's own repo, exactly like `execution_log.md`.

## What to log, and when

If `WIRE_TRACE=true`:

1. **Resolve context once, before anything else**: the release folder (from this command's own argument, if it has one) and `release_type` (read `.wire/releases/<release_folder>/status.md`'s `project_type` or `release_type` field). If this command has no release-folder argument, both are `null`.
2. **Emit a `command_start` event** before beginning the Workflow Specification below.
3. **As you work through the Workflow Specification's own numbered steps, emit a `step` event after completing each one** — and where a step itself has meaningfully distinct numbered sub-parts (e.g. "check location A, then location B, then infer a match, then propose it"), treat each of those as its own step event too rather than collapsing them into one. The `detail` field has no length limit and is not a summary — write what actually happened: values found, files read, decisions made and why, what was proposed and what the consultant chose. If this step involved the data model registry or any other external/optional resource, log it explicitly: whether it was reached, what was searched, what matched (or didn't, and why not), and whether/how the result was used downstream.
4. **Emit a `command_end` event** when the workflow finishes, with the same `result` value this command would write to `execution_log.md` (`complete`, `pass`, `fail`, `approved`, etc.).

## How to emit an event

Use this pattern for every event (adjust the heredoc body and the Python literals per call — this is a template, not a fixed script):

```bash
[ "${WIRE_TRACE:-false}" = "true" ] && {
  mkdir -p ".wire/releases/<release_folder>" 2>/dev/null
  cat > "/tmp/wire_trace_detail_$$.txt" << 'WIRE_TRACE_DETAIL_EOF'
<the full, untruncated detail text for this event — safe to include quotes,
newlines, code snippets, anything; this heredoc is not shell-interpreted>
WIRE_TRACE_DETAIL_EOF
  python3 -c "
import json, datetime
detail = open('/tmp/wire_trace_detail_$$.txt').read().rstrip('\n')
event = {
    'ts': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    'release': '<release_folder_or_null>',
    'release_type': '<release_type_or_null>',
    'command': 'discovery-analyses-generate',
    'event': '<command_start|step|command_end>',
    'step': '<step_number_or_null>',
    'step_name': '<step_heading_or_null>',
    'result': '<result_value_or_null>',
    'detail': detail,
}
with open('.wire/releases/<release_folder>/trace.jsonl', 'a') as f:
    f.write(json.dumps(event) + chr(10))
"
  rm -f "/tmp/wire_trace_detail_$$.txt"
}
```

- `<release_folder_or_null>` / `<release_type_or_null>`: from Step 1 above; write the literal JSON `null` (no quotes) if either doesn't apply, or a quoted string if it does.
- `event`: `command_start`, `step`, or `command_end`.
- `step` / `step_name`: `null` for `command_start`/`command_end`; the step's own number (e.g. `"1.5"`) and heading (e.g. `"Check for a Canonical Vertical Match"`) for a `step` event.
- `result`: `null` except on `command_end`.
- Adjust the file path in the final `open(...)` call to `.wire/trace.jsonl` for engagement-level (non-release-scoped) commands.

## Rules

1. **Never block or fail the workflow.** If a trace write fails for any reason (disk full, permissions), continue the workflow regardless — trace failures are never surfaced to the user and never stop anything.
2. **Append only** — never rewrite or delete existing lines in `trace.jsonl`.
3. **This is additive to `execution_log.md` and Telemetry, not a replacement for either.** All three continue exactly as documented elsewhere; tracing is a separate, optional, much finer-grained record for engagements that opt in.
4. **Don't summarize into brevity.** The entire point of this mechanism over `execution_log.md` is that it isn't limited to a 120-character line — write the real detail.

## Example

```json
{"ts":"2026-07-05T14:20:03Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_start","step":null,"step_name":null,"result":null,"detail":"Invoked for release 20260705_acme (full_platform)"}
{"ts":"2026-07-05T14:20:11Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.1","step_name":"Resolve the registry location","result":null,"detail":"Checked wire/data-model-registry/ (not found — not the Wire source repo). Checked ~/.wire/data-model-registry/ (found — cloned via /wire:utils-data-model-registry-setup on 2026-07-01)."}
{"ts":"2026-07-05T14:20:19Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.2","step_name":"Resolve the vertical","result":null,"detail":"No confident vertical match for Acme (B2B SaaS, no dedicated saas vertical in the registry). Adjacent match found: subscription-commerce — entity shape (subscriber, subscription, subscription_event, monthly_retention, subscription_revenue) proposed as a structural analogue for Acme's MRR/NRR model."}
{"ts":"2026-07-05T14:20:34Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.3","step_name":"Check cross-vertical patterns","result":null,"detail":"crm_identity_resolution flagged as relevant — requirements FR-12 describes reconciling Salesforce and HubSpot contact records, a 12% mismatch rate noted in discovery. Proposed alongside the subscription-commerce adjacent match."}
{"ts":"2026-07-05T14:21:02Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.4","step_name":"Propose and record decision","result":null,"detail":"Presented both proposals. Consultant chose 'adapt' on subscription-commerce (kept subscriber/subscription/subscription_revenue, dropped monthly_retention as out of scope for this phase, renamed subscription_event to billing_event to match client terminology) and 'yes' on crm_identity_resolution as-is. Recorded data_model_registry.vertical: subscription-commerce and cross_vertical_schemas: [crm_identity_resolution] in .wire/engagement/context.md."}
{"ts":"2026-07-05T14:34:47Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"5","step_name":"Carry reference pointers forward","result":null,"detail":"account_dim mapped to subscription-commerce's subscriber entity — generation_constraints and reference_implementation pointer carried into data_model_specification.md. subscription_fct mapped to subscription entity, same treatment. contact_identity_map (new, from crm_identity_resolution) added as its own integration model with that pattern's reference_implementation pointer."}
{"ts":"2026-07-05T14:41:15Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_end","step":null,"step_name":null,"result":"complete","detail":"Generated data_model_specification.md — 14 models (5 staging, 4 integration, 5 warehouse), including 2 informed by the accepted registry proposals above."}
```

## Workflow Specification

---
wire_schema: "1.0"
command: generate
artifact: discovery_analyses
domain: sop_discovery
release_types:
  - sop_discovery
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: requirements_matrix
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Generate the three analyses — Hierarchy of Needs, PPT, and Maturity Curve

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Discovery Analyses — Generate

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

## Purpose

Produces the three analyses applied to the consolidated requirements:

1. **Analytics Hierarchy of Needs** — bar chart + tier-by-tier prose diagnosis
2. **People / Process / Technology (PPT)** — bar chart + axis-by-axis prose diagnosis
3. **Data Analytics Maturity Curve** — single pin placement + prose justification

Plus the per-axis word-cloud labels, the verbatim quote selections, and the MoSCoW + Phase layering done after the diagnosis.

These analyses are the load-bearing diagnostic work of the discovery. They drive the Findings Playback deck (Phase 4) and they are what the sponsor signs off on at the playback. Per the playbook: this is **internal RA work** — the client does not see the matrix or this analyses file in raw form.

Models Phase 3 Steps 3–8 of the Canonical Discovery Playbook.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md` (reviewed and approved)
- All interview write-ups (for verbatim quote selection)

## Workflow

### Step 1: Pre-flight

1. Resolve `$ARGUMENTS`. Confirm `release_type: sop_discovery` and that the requirements matrix is `review: complete`.
2. If not, stop: "Requirements matrix has not been reviewed. Run `/wire:requirements-matrix-review $ARGUMENTS` first."

### Step 2: Hierarchy of Needs analysis

Walk every row of the matrix. Confirm or correct the Hierarchy tier. The rule:

> The lowest tier whose absence is blocking it.

Count rows per tier. Produce a bar chart specification (the rendered chart is generated at deck-build time; here we record the counts and the diagnostic prose).

Write a 4–6 bullet prose diagnosis explaining the shape of the chart **in the client's terms**. Reference specific verbatim quotes. Worked example from a prior engagement, for tone:

> "Modeling challenges, data ingestion issues from external vendors, frequent schema changes affecting pipeline stability... Critical issues include poor SAP reconciliation, poor testing/QA processes..."

If the distribution is unusual (all clean/no analyse, or top-heavy with no clean/collect), call that out explicitly — it is itself a finding.

### Step 3: PPT analysis

Walk the matrix again. Confirm or correct the PPT axis. The rule:

> The axis whose absence is causing it.

Count rows per axis. Write a 4–6 bullet axis-by-axis diagnosis:

- **People** — what skills, roles, structure, or accountability is the binding constraint?
- **Process** — what gates, QA, decision trees, or governance are missing?
- **Technology** — what tooling, infrastructure, or semantic layer gaps?

Worked example (14 Capabilities, 7 Technology, 5 People) — diagnosed as **fundamentally a Process problem** with adequate underlying tooling.

If the consultant tagged "Capabilities" as a fourth axis for any rows (inline-roadmap pattern), include a fourth section.

Refusing to choose one axis per row is refusing to diagnose. If any row reads as "a bit of all three", revisit during this step.

### Step 4: Maturity Curve placement

Pin the client at one of the five stages, based on the combined picture from the Hierarchy and PPT analyses:

- **Data Chaos** — fragmented, low-trust, firefighting (Prior engagements have landed here)
- **Order** — strategic and operational alignment, standard practices adhered to
- **Democratisation** — efficient self-service across departments
- **Innovation** — beyond the basics; new data products and solutions
- **Return** — innovation drives competitive advantage

Write a 3–5 bullet justification grounded in evidence from the interviews. **Do not place the pin generously to be polite.** Prior engagements have landed at Data Chaos — saying so was honest, not insulting. If the consultant has placed the pin and the diagnosis prose doesn't justify it, this is the moment to challenge.

### Step 5: Word cloud labels (per axis)

For each PPT axis (and the cross-cutting "Capabilities" axis if used), extract 6–12 short hashtag-style theme labels from the rows tagged to that axis. Labels should use the **client's own language** where possible.

Worked example — a prior engagement's Process word cloud:
`MissingQualityGates` `RushToProduction` `SkipArchitectureReview` `SkipBusinessValidation` `BrokenCommunication` `UnclearAccountability` `MissingDecisionTrees`

If the labels read like a glossary instead of the client's voice, redo them from the verbatim quotes.

### Step 6: Quote selection (per playback section)

For each of these sections of the playback deck, pick 3–4 verbatim quotes:

- Current State opener (dark navy divider)
- Hierarchy diagnosis (per-tier supporting quotes)
- PPT diagnosis (per-axis supporting quotes)
- Desired Future State opener
- Each per-axis section divider (3 quotes each)

Strong quotes are **short, specific, and emotionally accurate**. The "driving a car without a speedometer" quote from a prior engagement is the canonical example — it does more diagnostic work than a paragraph of prose.

### Step 7: MoSCoW and Phase layering

Now (and only now) layer in MoSCoW (Must / Should / Could / Won't) and Phase (1 / 2 / Future) tags on every row of the requirements matrix. Apply these directly to `requirements_matrix.md` — update the `MoSCoW` and `Phase` columns from `TBD` to actual values.

Rule of thumb:
- **Must / Phase 1** — sponsor-backed, foundation-tier, in-scope domain, count ≥ 2 stakeholders
- **Should / Phase 1** — strong support, in-scope, but de-risk-able
- **Could / Phase 2** — material but not on the critical path for the go/no-go decision
- **Won't / Future** — out-of-scope or premature

### Step 8: Resolve conflicts

Walk the Conflicts log. For each:
- Name the contradiction explicitly
- Name RA's recommendation (with reasoning)
- Mark whether the sponsor needs to decide it at the playback

Add a `## Sponsor decisions required` section listing every unresolved conflict.

### Step 9: Draft the analyses document

**Output**: `.wire/releases/$ARGUMENTS/planning/discovery_analyses.md`

```markdown
# Discovery Analyses: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_ID}}_{{RELEASE_NAME}}
**Date**: {{TODAY}}
**Status**: Internal RA — feeds Findings Playback deck

## 1. Analytics Hierarchy of Needs

### Distribution

| Tier | Count | % of total |
|---|---|---|
| Collect | N | NN% |
| Clean | N | NN% |
| Define & Track | N | NN% |
| Analyse | N | NN% |
| Optimise & Predict | N | NN% |

### Diagnosis

[4–6 bullets, in client's terms, supported by specific verbatim quotes]

### Supporting quotes (per tier)

- Collect: "..."
- Clean: "..."
- ...

## 2. People, Process, Technology

### Distribution

| Axis | Count | % of total |
|---|---|---|
| People | N | NN% |
| Process | N | NN% |
| Technology | N | NN% |

### Diagnosis

[4–6 bullets — name the binding constraint and the strength axis]

### Per-axis word clouds

**People**: `<label1>` `<label2>` ...
**Process**: `<label1>` `<label2>` ...
**Technology**: `<label1>` `<label2>` ...

### Supporting quotes (per axis)

- People: "..."
- Process: "..."
- Technology: "..."

## 3. Data Analytics Maturity Curve

### Pin: <Data Chaos | Order | Democratisation | Innovation | Return>

### Justification

[3–5 bullets grounded in interview evidence — explain why this pin, not the next one up]

## 4. MoSCoW and Phase summary

| Phase | Must | Should | Could | Won't |
|---|---|---|---|---|
| Phase 1 | N | N | — | — |
| Phase 2 | — | — | N | — |
| Future | — | — | — | N |

(Detailed MoSCoW / Phase tags are recorded directly on each row of `requirements_matrix.md`.)

## 5. Sponsor decisions required

[Every unresolved conflict from the Conflicts log + RA's recommendation. Each item will be forced to a sponsor decision at the playback.]

- [ ] Conflict X — Operations wants daily; Finance wants monthly. RA recommends daily for store-level, monthly for board-level. Sponsor to confirm.
- [ ] ...

## 6. Playback quote bank

(Curated for use in the Findings Playback deck — slide divider quotes and inline diagnostic quotes.)

### Current State opener
- "..."
- "..."
- "..."

### Desired Future State opener
- "..."
- "..."

### Per-axis dividers
[As above — 3 quotes each]
```

### Step 10: Update status

```yaml
artifacts:
  discovery_analyses:
    generate: complete
    file: planning/discovery_analyses.md
    generated_date: {{TODAY}}
    generated_files:
      - planning/discovery_analyses.md
      - planning/requirements_matrix.md   # MoSCoW + Phase columns now filled

sponsor_validation:
  maturity_pin: "<Data Chaos | Order | Democratisation | Innovation | Return>"
```

### Step 11: Sync to document store

Follow `specs/utils/docstore_sync.md`. The Confluence "Discovery Findings Working Document" (per-domain page set) referenced in the playbook is the natural destination.

### Step 12: Output summary

Show: Maturity pin, top-3 by Hierarchy tier, top-3 by PPT axis, conflict count, MoSCoW/Phase counts.

```
/wire:discovery-analyses-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/planning/discovery_analyses.md`
- Updated `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md` (MoSCoW + Phase columns)
- Updated `.wire/releases/$ARGUMENTS/status.md`

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

# Execution Log — Command and Skill Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file. Skills also append an entry on activation, making the log a unified trace of all agent activity — both explicit commands and auto-activated skills.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: Either the `/wire:*` command invoked, or `skill` for a skill activation entry
- **Result / Skill name**: For commands, the outcome; for skills, the skill identifier. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
  - `activated` — a skill was auto-activated (used with `skill` in the Command column)
  - `override` — `specs/utils/precondition_gate.md` recorded a consultant overriding an unmet precondition
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill
  - For override: the unmet precondition, who overrode it, and their reason

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
```

Skill identifiers:

| Skill | Identifier |
|-------|-----------|
| Engagement Context | `engagement-context` |
| Research Persistence | `research-persistence` |
| dbt Development | `dbt-development` |
| LookML Content Authoring | `lookml-authoring` |
| dbt Analytics QA | `dbt-analytics-qa` |
| dbt Migration | `dbt-migration` |
| dbt Troubleshooting | `dbt-troubleshooting` |
| dbt Semantic Layer | `dbt-semantic-layer` |
| dbt Unit Testing | `dbt-unit-testing` |
| dbt DAG | `dbt-dag` |
| Dagster | `dagster` |
| Fivetran | `fivetran` |
| Project Review | `project-review` |
| Looker Dashboard Mockup | `looker-dashboard-mockup` |

This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing across both explicit commands and automatic skill triggers.

## Rules

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
| 2026-02-24 09:05 | /wire:migration-strategy-generate | override | migration_inventory.review required approved, was not_started — overridden by Jane Smith: client demo tomorrow, inventory sign-off deferred to Monday |
```
