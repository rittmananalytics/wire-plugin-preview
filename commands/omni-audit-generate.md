---
description: Catalog Omni connections, model (topics/views/dimensions/measures), and folders/workbooks/tiles
argument-hint: <release-folder>
---

# Catalog Omni connections, model (topics/views/dimensions/measures), and folders/workbooks/tiles

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
    'command': 'omni-audit-generate',
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
artifact: omni_audit
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: []
description: Catalog Omni connections, model (topics, views, dimensions, measures, relationships), folders/workbooks/tiles, with migration approach and warehouse dependency mapping

---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: omni_audit` and `artifact_file_path: audit/omni_audit.md` before proceeding.

---

# Omni Audit — Generate

## Purpose

Catalogs the client's Omni reporting layer: every connection, the model (topics, views, dimensions, measures, relationships), and the folder → workbook → tile content hierarchy, plus the warehouse objects each model view reads from. The output maps view-to-warehouse dependencies so the migration inventory can sequence cutover correctly — views cannot be repointed to the target until their source warehouse objects exist there — and records which model views, and which individual tiles, carry source-platform SQL dialect that needs translating.

This is a **reporting-layer** audit, the Omni counterpart to the Metabase and reverse ETL audits. It is **not gated by `migration.scope`** — it runs for any migration where the client uses Omni, full migration or tenant carve-out alike.

Omni's object model splits dialect-specific SQL differently to Metabase's. Metabase scatters native SQL across individually-authored cards; Omni concentrates it in the model's view definitions (base table SQL, derived table SQL), which a handful of modelers maintain centrally. Most tiles query through a topic and carry no SQL of their own — dialect-neutral, and they inherit whatever the model resolves to. A tile with a raw-SQL override is the exception, not the default, and gets the same source-dialect scan as a Metabase native-SQL card. This audit therefore classifies migration approach at the **view** level, not the tile level, and separately flags the smaller set of raw-SQL-override tiles for their own classification.

## Prerequisites

- Release folder with `release_type: platform_migration` in `status.md`
- `migration.reporting_tool: omni` set in `status.md`
- Omni CLI configured against the instance — a named profile (`omni config use <profile>`), or `OMNI_BASE_URL` + `OMNI_API_TOKEN` passed explicitly (see `skills/omni/SKILL.md` Step 0)

## Inputs

- `.wire/releases/$ARGUMENTS/status.md`
- The Omni instance, via the Omni CLI
- `.wire/releases/$ARGUMENTS/audit/dbt_audit.md` (if present — cross-reference dbt model dependencies)

## Workflow

### Step 1: Locate the release

Confirm `release_type: platform_migration` in `status.md`. Read `migration.reporting_tool` — if it is not `omni`, stop and output:

```
reporting_tool is not set to omni.
Set migration.reporting_tool: omni in status.md and re-run.
```

Activate the `omni` skill (`skills/omni/SKILL.md`) for connection details and the object hierarchy.

If the audit file already exists at `audit/omni_audit.md`, ask whether to re-generate (overwrite) or update (append new items only).

### Step 2: Connect to Omni

Per `skills/omni/SKILL.md` Step 0:

```
omni config show
omni config use <profile-name>
```

If no profile exists, try `--base-url "$OMNI_BASE_URL" --token "$OMNI_API_TOKEN"` explicitly. There is **no CSV/inventory fallback for Omni** — the CLI is the only supported access path. If neither a configured profile nor the environment variables are available, stop and output:

```
No Omni CLI access configured. Provide one of:

  1. A configured profile — run `omni config init`, or `omni config use <profile-name>`
     if one already exists
  2. OMNI_BASE_URL + OMNI_API_TOKEN environment variables

Then re-run: /wire:omni-audit-generate $ARGUMENTS
```

### Step 3: Catalog connections

Using `omni-admin`, enumerate every connection: id, name, engine (e.g. `snowflake`), and which model views run against each. The connection is the pivot for repointing at migration time.

### Step 4: Catalog the model

Using `omni-model-explorer`, walk the model: topics, and for every view exposed through a topic:

| Field | Source |
|---|---|
| `view_id` / `view_name` | view identifier / name |
| `topic_ids` | topics that expose this view |
| `connection_id` | the connection this view's table/query runs against |
| `sql_type` | `base_table` (points at a table, no SQL) / `base_table_sql` / `derived_table` |
| `sql_summary` | first 200 chars of the view's base or derived table SQL, where present |
| `warehouse_objects` | resolved source tables/views (see resolution below) |
| `source_resolved` | true if ≥1 object resolved, else false |
| `dimension_count` / `measure_count` | count of fields defined on the view |
| `relationships` | other views this one joins to |
| `complexity` | assigned in Step 6 |
| `migration_approach` | assigned in Step 6 |

**Warehouse object extraction**: for views with `sql_type: base_table`, resolve directly to the underlying warehouse table/view (dialect-neutral — no SQL to translate). For `base_table_sql` and `derived_table`, parse the view's SQL to extract referenced schema-qualified table/view names. Cross-reference resolved objects against the dbt audit where present, to confirm each is in migration scope. For any view where no source object resolves, set `warehouse_objects` empty **and** `source_resolved: false` so it is counted and listed, never silently dropped.

**Source-resolution coverage metric**: over active views, compute `active_view_count`, `resolved_view_count`, `unresolved_view_count`, and `source_resolution_coverage_pct = resolved / active`, broken down by `sql_type`.

### Step 5: Catalog folders, workbooks, and tiles

Using `omni-content-explorer`, walk the content hierarchy: folder → workbook/document → tile. For each tile:

| Field | Source |
|---|---|
| `tile_id` / `tile_name` | tile identifier / name |
| `workbook_id` / `workbook_name` | the tile's workbook/document |
| `folder_id` / `folder_name` | the workbook's folder |
| `query_surface` | `topic` (queries through the model) or `raw_sql` (SQL override) |
| `topic_id` | the topic queried, if `query_surface: topic` |
| `sql_summary` | first 200 chars of the raw SQL, if `query_surface: raw_sql` |
| `warehouse_objects` | resolved source objects, for `raw_sql` tiles only |
| `source_resolved` | for `raw_sql` tiles only |
| `migration_approach` | `inherits_via_model` for `topic` tiles; assigned in Step 6 for `raw_sql` tiles |
| `include_in_migration` | true (default) unless archived / unused >90 days |
| `migration_notes` | auto-generated |

A `topic`-backed tile needs no migration work of its own: once the model's connection swap and view translations are promoted, the tile resolves against the target automatically. Only `raw_sql` tiles carry their own dialect risk — scan each one's SQL for source-platform constructs the same way as a view.

### Step 6: Classify views and raw-SQL tiles

**Views** — assign complexity (Low / Medium / High) and migration approach:

- `repoint` — the view has no SQL (`base_table`) or portable SQL; only the connection changes after warehouse migration
- `rewrite_sql` — the view's base/derived table SQL uses source-platform dialect; translate to the target dialect before repointing
- `rebuild` — the view depends on a source-only construct with no direct translation; rebuild against the target connection

Default: `base_table` views → `repoint` (Low). Scan `base_table_sql` and `derived_table` SQL for source-dialect constructs (`::` casts, `FLATTEN`, `QUALIFY`, `IFF`, `NVL`, `CONVERT_TIMEZONE`, variant `:` paths) and reclassify `repoint` → `rewrite_sql` where found; reclassify to `rebuild` where no direct translation exists.

**Raw-SQL tiles** — assign the same three buckets (`repoint` / `rewrite_sql` / `rebuild`), scanned against the same construct list. Topic-backed tiles do not get their own bucket; they carry `migration_approach: inherits_via_model`.

### Step 7: Write the audit report

**Output location**: `.wire/releases/$ARGUMENTS/audit/omni_audit.md`

Include:
- Summary table (connections, topics, views by approach, views by complexity, tiles by query surface, raw-SQL tiles by approach)
- **Source-resolution coverage**: `resolved_view_count` / `active_view_count` (`source_resolution_coverage_pct`), broken down by `sql_type`
- Full model catalog: topic → view table (SQL summaries, dimension/measure counts, relationships)
- Content hierarchy: folder → workbook → tile
- Connection inventory (engine, views per connection)
- Warehouse object dependency map (which warehouse objects each view depends on)
- Raw-SQL tile catalog (tile, workbook, SQL summary, resolved objects, migration approach)
- **Unresolved views** — every active view with `source_resolved: false`, listed explicitly
- **Unresolved raw-SQL tiles** — every raw-SQL tile with `source_resolved: false`, listed explicitly
- dbt model dependencies (views that cannot be repointed until a dbt migration batch is complete)
- Excluded / decommission candidates (archived or unused workbooks/tiles)

### Step 8: Update status

```yaml
artifacts:
  omni_audit:
    generate: complete
    file: audit/omni_audit.md
    generated_date: "{{TODAY}}"
    tool: omni
    connection_count: N
    topic_count: N
    view_count: N
    folder_count: N
    workbook_count: N
    tile_count: N
    raw_sql_tile_count: N
    decommission_count: N
    active_view_count: N
    resolved_view_count: N
    unresolved_view_count: N
    source_resolution_coverage_pct: 0.00
```

### Step 9: Output summary

Print: totals, breakdown by approach/complexity, source-resolution coverage (with unresolved count called out), and next command:

```
/wire:omni-audit-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/omni_audit.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_audit` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_audit` as artifact_id, `Omni Audit` as artifact_name, and the `file` value from `artifacts.omni_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_audit` as artifact, `generate` as action.

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
