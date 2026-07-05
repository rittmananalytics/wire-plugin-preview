---
description: Validate orchestration layer against pipeline design
argument-hint: <project-folder>
---

# Validate orchestration layer against pipeline design

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
    'command': 'orchestration-validate',
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
command: validate
artifact: orchestration
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: orchestration
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate the orchestration layer — checks Dagster asset graph or dbt Cloud job configs against the pipeline design
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Orchestration Validate Command

## Purpose

Validate the generated orchestration layer. The validation checks differ by tool:

- **Dagster**: verifies the asset graph loads cleanly, covers all dbt models, and the schedule cadences match the pipeline design
- **dbt Cloud**: verifies job configurations reference valid environments, selectors match existing dbt models, and schedules reflect the pipeline design cadences

## Prerequisites

- `orchestration` generate must be complete
- For Dagster: `dagster_orchestration/` directory must exist with a valid `Definitions` object

## Workflow

### Step 1: Read Configuration

1. Read `.wire/<project_id>/status.md` to determine `orchestration_tool`
2. If `orchestration_tool` is not set, stop with: "Run `/wire:orchestration-generate <project>` first to set up the orchestration layer."

### Step 2a: Validate Dagster (if tool = dagster)

#### 2a.1 — Check defs load

Run from the `dagster_orchestration/` directory:

```bash
cd dagster_orchestration
dg check defs
```

This verifies:
- All Python imports resolve
- All `@dg.asset` and `@dg.multi_asset` decorators are valid
- The `Definitions` object loads without errors
- No circular asset dependencies
- All referenced resources are defined

If `dg check defs` fails, report the full error and stop.

#### 2a.2 — Verify dbt model coverage

Run:
```bash
cd dagster_orchestration
dg list defs --select "kind:dbt"
```

Compare the listed dbt-kind assets against the models in the dbt project (`dbt ls --select "*" --output name`). Every dbt model should have a corresponding Dagster asset.

Report any missing models as validation findings.

#### 2a.3 — Verify schedule cadences

List all defined schedules:
```bash
dg list defs --select "type:schedule"
```

For each schedule, verify:
- The cron expression is valid (parseable)
- It matches a run cadence specified in `pipeline_design.md`
- It targets at least one asset or job

Report any cadences in the pipeline design that have no corresponding schedule.

#### 2a.4 — Check asset group completeness

Verify that every source system in `pipeline_design.md` has at least one ingestion asset defined in `assets/`.

#### 2a.5 — Compile validation report

Write `.wire/<project_id>/development/orchestration/.orchestration_validation.md`:

```markdown
# Orchestration Validation Report

**Date**: <date>
**Tool**: Dagster
**Result**: PASS | FAIL

## Checks

| Check | Result | Notes |
|-------|--------|-------|
| dg check defs | PASS/FAIL | [error if failed] |
| dbt model coverage | PASS/FAIL | [N of M models covered] |
| Schedule cadence coverage | PASS/FAIL | [missing cadences if any] |
| Source ingestion coverage | PASS/FAIL | [missing sources if any] |

## Findings

[List any warnings or required fixes]
```

### Step 2b: Validate dbt Cloud (if tool = dbt_cloud)

#### 2b.1 — Check config file completeness

Read `.wire/<project_id>/development/orchestration/dbt_cloud_config.md` and verify it contains:
- At least one Production environment definition
- At least one job per run cadence identified in `pipeline_design.md`
- A CI/PR job for pull request validation
- Notification configuration on each job

#### 2b.2 — Verify model selectors

For each job, verify the `dbt run --select <selector>` expression is valid by running:

```bash
dbt ls --select <selector>
```

If the selector returns 0 models, flag as a warning. If the command errors, flag as a failure.

#### 2b.3 — Verify cron expressions

For each scheduled job, confirm the cron expression is syntactically valid and matches the stated cadence description.

#### 2b.4 — Compile validation report

Write `.wire/<project_id>/development/orchestration/.orchestration_validation.md`:

```markdown
# Orchestration Validation Report

**Date**: <date>
**Tool**: dbt Cloud
**Result**: PASS | FAIL

## Checks

| Check | Result | Notes |
|-------|--------|-------|
| Config file completeness | PASS/FAIL | |
| Model selectors valid | PASS/FAIL | [any selectors matching 0 models] |
| Cron expressions valid | PASS/FAIL | |
| Cadence coverage | PASS/FAIL | [cadences from pipeline_design not covered] |

## Findings

[List any warnings or required fixes]
```

### Step 2c: Validate Airflow (if tool = airflow)

#### 2c.1 — DAG parse check

Run from the repo root:

```bash
python -c "from dags.<project_name>_pipeline import dag; print('DAG tasks:', dag.task_ids)"
```

If the import raises any error, report it in full and stop. A clean parse is a hard requirement before proceeding.

#### 2c.2 — Verify dbt model task coverage

List dbt models:
```bash
cd <dbt_project_path> && dbt ls --select "*" --output name
```

Inspect the DAG file and confirm every model has either:
- A corresponding `BashOperator` or `PythonOperator` task running `dbt run --select <model>`, or
- Is covered by a `DbtTaskGroup` that runs all models

Report any models not covered as validation findings.

#### 2c.3 — Verify source sensor coverage

Read `pipeline_design.md` source system list. Confirm there is at least one sensor task per source (e.g. `BigQueryTableExistenceSensor`, `HttpSensor`, or equivalent). Report any source systems with no upstream sensor.

#### 2c.4 — Verify cron expression

Extract the `schedule_interval` from the DAG file. Confirm:
- The cron expression is syntactically valid (parseable by a standard cron library)
- It matches the run cadence stated in `pipeline_design.md`

#### 2c.5 — Verify connection IDs documented

Check that `airflow_connections.md` exists and lists at least one connection per source system and one for the warehouse target.

#### 2c.6 — Compile validation report

Write `.wire/<project_id>/development/orchestration/.orchestration_validation.md`:

```markdown
# Orchestration Validation Report

**Date**: <date>
**Tool**: Airflow
**Result**: PASS | FAIL

## Checks

| Check | Result | Notes |
|-------|--------|-------|
| DAG parse check | PASS/FAIL | [error if failed] |
| dbt model task coverage | PASS/FAIL | [N of M models covered] |
| Source sensor coverage | PASS/FAIL | [missing sources if any] |
| Cron expression valid | PASS/FAIL | [expression and matched cadence] |
| Connection IDs documented | PASS/FAIL | |

## Findings

[List any warnings or required fixes]
```

### Step 3: Update Status

Update `.wire/<project_id>/status.md`:

```yaml
orchestration:
  validate: complete   # or failed
```

If any FAIL check was found, set `validate: failed` and include findings in the notes.

### Step 4: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `orchestration`
- Action: `validate`
- Status: `complete` or `failed`

### Step 5: Report Results

If PASS:
```
## Orchestration Validation: PASS

All checks passed. Ready for review.

Next step: `/wire:orchestration-review <project>`
```

If FAIL:
```
## Orchestration Validation: FAIL

[List failing checks and required fixes]

Fix the issues above and re-run: `/wire:orchestration-validate <project>`
```

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
