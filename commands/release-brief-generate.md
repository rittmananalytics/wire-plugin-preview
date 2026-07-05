---
description: Generate formal release brief from the approved pitch
argument-hint: <release-folder>
---

# Generate formal release brief from the approved pitch

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
    'command': 'release-brief-generate',
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
artifact: release_brief
domain: discovery
release_types:
  - discovery_shape_up
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: pitch
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Generate formal release brief from the approved pitch

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Release Brief Generate Command

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

## Purpose

Generates a formal release brief from the approved pitch. The release brief is the commitment document — it specifies exactly what will be delivered, what the team will do, the timeline, the constraints, and the sign-off requirements. It is more precise than the pitch and is used to formally begin work.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/pitch.md` — must be reviewed and approved

## Workflow

### Step 1: Locate Release and Read Pitch

Resolve release folder. Read `planning/pitch.md`. Verify pitch has been approved (check status.md `pitch.review`). If not approved, stop and prompt the user to complete the pitch review first.

Also read:
- `engagement/context.md` if present
- `engagement/sow.md` if present (for budget and contract terms)

### Step 2: Identify Downstream Delivery Releases

From Section 8 of the pitch (Downstream Releases), extract the planned delivery releases. If Section 8 is empty or "TBD", ask:

```
Based on the approved pitch, what delivery releases will this discovery release produce?
(e.g. "01-data-foundation: pipeline_only, 02-reporting: dashboard_extension")

List them as: [name]: [type]
```

### Step 2b: Establish Primary Analytical Focus and Goal Hierarchy

Before generating the brief, ask explicitly:

```
The SOW/pitch lists the following engagement goals:
[list goals extracted from pitch or SOW]

1. Which of these is the PRIMARY use case — the single analytical domain that all discovery work is in service of?
   (e.g. "Customer acquisition funnel", "Merchant 360", "Operational productivity reporting")

2. For each remaining goal, assign a priority:
   - Primary: must achieve in this engagement
   - Secondary: assess and recommend only — do not design or build
   - Future: out of scope this engagement, note and defer
```

Record the answers as:
- `primary_analytical_focus`: [the ONE named use case]
- `goal_hierarchy`: a table of goals with assigned priorities

### Step 3: Generate the Release Brief

**Output location**: `.wire/releases/$ARGUMENTS/planning/release_brief.md`

```markdown
# Release Brief: [Release Name]

**Engagement**: [client_name]
**Release folder**: [folder_name]
**Date**: [generation_date]
**Version**: 1.0
**Status**: Draft

---

## 0. Primary Analytical Focus

**Priority use case**: [ONE named use case agreed with the client at kick-off]

All discovery work — stakeholder interviews, entity model, data source assessment, solution definition — is conducted in service of this use case. Other analytical domains surfaced during discovery will be noted for future phases but will not be scoped or designed during this release.

**Goal hierarchy**:

| Goal | Priority | What this engagement will do |
|------|----------|------------------------------|
| [Goal 1] | Primary | Design and deliver |
| [Goal 2] | Primary | Design and deliver |
| [Goal 3] | Secondary | Assess and recommend — do not design solutions |
| [Goal 4] | Secondary | Assess and recommend — do not design solutions |
| [Goal 5] | Future | Note and defer to a future release |

**What this discovery will not produce**: A comprehensive data strategy, a full analytics operating model, or remediation plans for organisational or governance issues that fall outside the analytical delivery function. Where root causes are found that go beyond this scope, they will be documented and handed back to the client.

## 1. Executive Summary

[2–3 sentence summary of what this release delivers and why. Written for a stakeholder who hasn't read the pitch.]

## 2. Appetite and Timeline

**Appetite**: [Small batch — 1–2 weeks | Big batch — 6 weeks]
**Confirmed by**: [who approved the pitch]
**Start date**: [date or TBD]
**End date**: [date or TBD]

## 3. Deliverables

| # | Deliverable | Description | Acceptance Criteria | Owner |
|---|------------|-------------|---------------------|-------|
| D1 | [name] | [what it is] | [how we know it's done] | [name/role] |
| D2 | [name] | [what it is] | [how we know it's done] | [name/role] |

**Completion definition**: This release is complete when all deliverables above are signed off by [approver role].

## 4. Downstream Releases Produced

This discovery release will produce the following delivery releases upon completion of the sprint plan:

| Release Name | Type | Scope Summary | Priority |
|--------------|------|---------------|----------|
| [name] | [type] | [1-line scope] | 1 |
| [name] | [type] | [1-line scope] | 2 |

These releases will be created by running: `/wire:release:spawn [folder]` at the end of the sprint plan.

## 5. What Is Out of Scope

[From pitch Section 5 (No-gos) — formalised as contractual boundaries]

- [Item 1]
- [Item 2]
- [Item 3]

**Scope change process**: Any additions to scope require a new pitch or formal change request.

## 6. Assumptions

| # | Assumption | Impact if Wrong | Owner |
|---|-----------|-----------------|-------|
| A1 | [assumption] | [impact] | [owner] |

## 7. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| [risk] | H/M/L | H/M/L | [mitigation] | [owner] |

## 8. Resources

| Role | Name | Allocation | Responsibilities |
|------|------|------------|-----------------|
| Engagement Lead | [name] | [%] | [responsibilities] |
| [role] | [name] | [%] | [responsibilities] |

## 9. Budget

**Engagement budget**: [from SOW, or "to be confirmed"]
**This release**: [estimated cost, or "included in engagement budget"]
**Payment milestone**: [when this release triggers a payment, if applicable]

## 10. Dependencies and Prerequisites

| Dependency | Owner | Required By | Status |
|-----------|-------|-------------|--------|
| [dependency] | [owner] | [date] | Open |

## 11. Communication and Governance

**Stakeholder updates**: [frequency and format]
**Decision-making authority**: [who can approve changes]
**Escalation path**: [who to escalate to if blocked]

## 12. Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Client sponsor | | | |
| Engagement lead | | | |

*Signature indicates agreement with the scope, timeline, budget, and deliverables defined in this document.*
```

### Step 4: Update Release Status

```yaml
release_brief:
  generate: "complete"
  validate: "not_started"
  review: "not_started"
  file: "planning/release_brief.md"
  generated_date: [today's date]
primary_analytical_focus: "[value captured in Step 2b]"
goal_hierarchy_captured: true
```

### Step 5: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `release_brief`
- `artifact_name`: `Release Brief`
- `file_path`: `.wire/releases/[release_folder]/artifacts/release_brief.md`
- `project_id`: the release folder path (e.g. `releases/01-discovery`)

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 6: Confirm and Suggest Next Steps

```
## Release Brief Generated

File: .wire/releases/[folder]/planning/release_brief.md

Downstream releases identified: [list from Section 4]

### Next Steps

1. Validate the release brief:
   /wire:release-brief-validate [folder]

2. Review and sign off with the client:
   /wire:release-brief-review [folder]

3. When signed off, generate the sprint plan:
   /wire:sprint-plan-generate [folder]
```

## Output Files

- `.wire/releases/[folder]/planning/release_brief.md`
- Updated `.wire/releases/[folder]/status.md`

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
