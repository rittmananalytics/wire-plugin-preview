---
description: Create or update LookML view files for new and restructured canonical models (Looker only)
argument-hint: <release-folder>
---

# Create or update LookML view files for new and restructured canonical models (Looker only)

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
    'command': 'ads_lookml-views-generate',
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
artifact: lookml_views
domain: agentic_data_stack
release_types:
  - agentic_data_stack
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: canonical_models
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Create or update LookML view files for new and restructured canonical models — Looker projects only
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — LookML Views Generate

Follow `specs/utils/semantic_layer_developer_delegate.md` before executing the workflow below.

## Purpose

For every canonical model that was created or structurally changed during the `canonical_models` phase, create or update the corresponding LookML view file so the model is correctly exposed in Looker before `ads_semantic-layer-generate` adds metrics on top.

This step is **Looker-only**. When `bi_tool` is not `looker`, output a brief skip notice and set status to `skipped`.

## Usage

```bash
/wire:ads_lookml-views-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `canonical_models.review: approved`

## Workflow

### Step 1: Check BI Tool

Read `status.md`:

```yaml
bi_tool: looker   # must be "looker" to proceed
```

If `bi_tool` is not `looker`, output:

```
LookML Views — Skipped

bi_tool is not looker (found: <value>). This step is only required for Looker
projects. Proceeding directly to ads_semantic-layer-generate.
```

Then update status.md:

```yaml
lookml_views:
  generate: skipped
  validate: skipped
  review: skipped
```

Stop here.

---

### Step 2: Resolve LookML Project Path

Read `lookml_project_path` from status.md. If empty or not set, ask:

```
What is the path to the LookML project directory?
(The directory containing manifest.lkml or *.model.lkml files)
Examples: ./looker   ../analytics-looker   /workspace/looker-project
```

Once confirmed, store the path in status.md under `lookml_project_path`.

---

### Step 3: Read Canonical Model Changes

Read `.wire/<release-folder>/artifacts/canonical_models_lineage.md`.

Build two lists:

**New models** — created during `canonical_models` phase (did not exist before):
```
fct_orders        → project.analytics.fct_orders
dim_customers     → project.analytics.dim_customers
```

**Modified models** — restructured (columns renamed, added, or removed):
```
fct_subscriptions → columns: net_mrr renamed from mrr_amount; churn_date added
```

If `canonical_models_lineage.md` does not exist, read `artifacts/canonical_models.md` and ask the user to confirm which models are new vs pre-existing.

---

### Step 4: Scan Existing LookML Views

Scan `<lookml_project_path>` for all `.view.lkml` and `*.layer.lkml` files. For each file, extract `sql_table_name` or `derived_table` references to build a map of:

```
view_name → sql_table_name
```

Cross-reference against the new/modified model list to determine:

- **Missing views** — new canonical model, no existing view references its table
- **Stale views** — modified canonical model, existing view references its table (needs update)
- **Already covered** — view exists and matches; no action needed

---

### Step 5: Generate Views for New Canonical Models

For each missing view, generate a LookML view file following RA layered architecture conventions.

**File naming**: `<model_name>.view.lkml` in `<lookml_project_path>/views/` (or equivalent `base/` layer if the project uses the RA layered pattern).

**Template** — base view with dimensions only (measures added by `ads_semantic-layer-generate`):

```lookml
# Auto-generated by Wire Framework — agentic_data_stack / lookml_views phase
# Add measures in ads_semantic-layer-generate. Do not add measures here.

view: <model_name> {
  sql_table_name: `<fully_qualified_table_name>` ;;

  # ── Primary Key ──────────────────────────────────────────────────
  dimension: <pk_column> {
    primary_key: yes
    hidden: yes
    type: string
    sql: ${TABLE}.<pk_column> ;;
  }

  # ── Foreign Keys ─────────────────────────────────────────────────
  dimension: <fk_column> {
    hidden: yes
    type: string
    sql: ${TABLE}.<fk_column> ;;
  }

  # ── Dimensions ───────────────────────────────────────────────────
  dimension_group: <date_column> {
    type: time
    timeframes: [date, week, month, quarter, year]
    datatype: date
    sql: ${TABLE}.<date_column> ;;
  }

  dimension: <string_column> {
    type: string
    sql: ${TABLE}.<string_column> ;;
    label: "<Human Readable Label>"
    description: "<From schema.yml description>"
  }

  dimension: <numeric_column> {
    type: number
    sql: ${TABLE}.<numeric_column> ;;
    label: "<Human Readable Label>"
    value_format_name: decimal_2
  }
}
```

**Type mapping** — infer from dbt schema.yml column types:

| dbt / warehouse type | LookML dimension type |
|---|---|
| STRING, VARCHAR, TEXT | `string` |
| INTEGER, INT64, BIGINT | `number` |
| FLOAT, FLOAT64, NUMERIC | `number` (value_format_name: decimal_2) |
| BOOLEAN, BOOL | `yesno` |
| DATE | `time` (dimension_group, datatype: date) |
| DATETIME, TIMESTAMP | `time` (dimension_group, datatype: datetime) |
| ARRAY, STRUCT | omit — note in a comment for manual review |

Read column definitions from the model's `schema.yml` entry in the dbt project. Use `description` fields as the LookML `description` parameter. Convert `snake_case` column names to `Title Case` for labels.

**Primary key**: identify from `schema.yml` — look for the column with `_pk` suffix or a `unique` + `not_null` test combo. If ambiguous, add a comment: `# TODO: confirm primary_key — multiple candidates found`.

**Explore wiring**: after creating the view file, check whether an existing explore covers this domain. If yes, add a `join:` block referencing the new view in the explore file. If no explore covers this domain, note it in `artifacts/lookml_views_notes.md` — a new explore may be needed and is out of scope for this step.

---

### Step 6: Update Views for Modified Canonical Models

For each stale view (existing view where the underlying canonical model changed):

1. Open the existing view file.
2. For each **renamed column**: find the matching `dimension` or `dimension_group` block and update `sql: ${TABLE}.<new_column_name> ;;`. Add a comment: `# column renamed from <old_name> — Wire agentic_data_stack <date>`.
3. For each **removed column**: remove the matching dimension block. If the dimension is referenced in an existing measure (e.g. as a filter), add a `# TODO: dimension removed — review dependent measures` comment on the measure.
4. For each **new column**: add a new dimension block following the type-mapping table above.

Do not add or remove measures. Do not change explore join logic.

---

### Step 7: Write Notes File

Write `.wire/<release-folder>/artifacts/lookml_views_notes.md`:

```markdown
# LookML Views — Generation Notes

Generated: YYYY-MM-DD

## Views Created

| View | File | Canonical Model | Explores Updated |
|---|---|---|---|
| fct_orders | views/fct_orders.view.lkml | fct_orders | orders_explore |

## Views Updated

| View | File | Changes |
|---|---|---|
| fct_subscriptions | views/fct_subscriptions.view.lkml | mrr_amount → net_mrr renamed; churn_date added |

## Explores Needing Manual Review

List any new views not yet added to an explore. These must be wired into an
explore before the semantic layer step adds metrics — metrics on an unwired
view are unreachable in Looker.

## TODOs

Any ambiguous primary keys, ARRAY/STRUCT columns skipped, or complex joins
that need manual attention.
```

---

### Step 8: Update Status

```yaml
lookml_views:
  generate: complete
  generated_date: YYYY-MM-DD
  views_created: N
  views_updated: N
  explores_updated: N
  lookml_project_path: <path>
```

## Output

- New or updated `.view.lkml` files in `<lookml_project_path>`
- Updated explore files where new views were joined in
- `.wire/<release-folder>/artifacts/lookml_views_notes.md`
- Updated `status.md`

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
