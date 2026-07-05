---
description: Inventory warehouse tables, identify duplicates, grade governance maturity
argument-hint: <release-folder>
---

# Inventory warehouse tables, identify duplicates, grade governance maturity

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
    'command': 'ads_dataset-audit-generate',
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
artifact: dataset_audit
domain: agentic_data_stack
release_types:
  - agentic_data_stack
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: []
description: Inventory all warehouse tables, identify duplicates, and grade governance maturity per domain
argument-hint: <release-folder>

---

# Agentic Data Stack — Dataset Audit Generate

Follow `specs/utils/agentic_data_stack_delegate.md` before executing the workflow below.

## Purpose

Produce a complete inventory of tables in the client's warehouse, identify near-duplicate and redundant definitions, classify each table by governance tier, and grade the overall governance maturity per domain. This is the foundation for every downstream decision in the release — if the audit is shallow, the canonical model will be wrong.

## Usage

```bash
/wire:ads_dataset-audit-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `.wire/<release-folder>/status.md` exists with `project_type: agentic_data_stack`
- Warehouse access configured (BigQuery, Snowflake, Databricks, or Redshift)
- dbt project path recorded in status.md (optional — enriches the audit with lineage)

## Workflow

### Step 1: Read Context

1. Read `.wire/<release-folder>/status.md`
2. Note: `warehouse`, `bi_tool`, `semantic_layer`, `dbt_project_path`, `primary_domain`
3. Read `.wire/engagement/context.md` for business context and domain definitions
4. Read `.wire/engagement/sow.md` if present — SOW may name specific tables or subject areas

### Step 2: Discover Tables

Connect to the warehouse and enumerate all tables in the analytics schema(s). For each table, collect:

- Full table reference (project.dataset.table for BigQuery; database.schema.table for Snowflake)
- Row count and approximate size
- Last modified date
- Owner / creator (from information_schema where available)
- Column count and column names
- Description (from table metadata / dbt docs if available)

**BigQuery:**
```sql
SELECT
  table_catalog, table_schema, table_name,
  row_count, size_bytes, last_modified_time,
  ARRAY_AGG(column_name ORDER BY ordinal_position) AS columns
FROM `region-us`.INFORMATION_SCHEMA.TABLE_STORAGE
JOIN `region-us`.INFORMATION_SCHEMA.COLUMNS USING (table_catalog, table_schema, table_name)
GROUP BY 1,2,3,4,5,6
ORDER BY table_schema, table_name
```

**Snowflake:**
```sql
SELECT
  table_catalog, table_schema, table_name, table_type,
  row_count, bytes, last_altered, table_owner, comment
FROM information_schema.tables
WHERE table_schema NOT IN ('INFORMATION_SCHEMA')
ORDER BY table_schema, table_name
```

If direct warehouse access is unavailable, ask the consultant to run the query and paste results, or provide a CSV export from their warehouse console.

### Step 3: Identify Near-Duplicates

Group tables by semantic similarity. Flag as near-duplicate when two or more tables share:

- Overlapping column sets (>70% column name overlap)
- Similar naming (same root word with different suffixes: `_v2`, `_new`, `_old`, `_copy`, `_bak`, `_legacy`, year suffixes)
- Same grain but different sources or transformation levels

For each duplicate group, identify the canonical candidate — typically the one with:
- Most recent modification date
- Highest row count
- Clearest naming (follows dbt three-layer convention or agreed naming standard)
- dbt-managed (prefer managed over ad-hoc)

### Step 4: Classify by Governance Tier

Assign each table to one of three tiers:

| Tier | Criteria | Agent routing |
|---|---|---|
| **Semantic** | Defined metric in semantic layer (MetricFlow, LookML, dbt SL) | Route here first — always |
| **Curated** | dbt-managed mart or staging model, documented, tested | Route here if no semantic metric |
| **Raw** | Unmanaged, undocumented, or staging-only tables | Last resort fallback |

### Step 5: Grade Governance Maturity Per Domain

Group tables by business domain (orders, customers, marketing, finance, logistics, product, etc.) and assign a maturity grade:

| Grade | Criteria |
|---|---|
| **A** | One canonical table per entity; semantic layer coverage >80%; documented; tested |
| **B** | Clear canonical table; partial semantic layer; documented; some tests |
| **C** | Multiple candidates for canonical; sparse documentation; few tests |
| **D** | Widespread duplication; no documentation; no semantic layer; raw tables primary |

### Step 6: Write Dataset Audit Document

Write `.wire/<release-folder>/artifacts/dataset_audit.md`:

```markdown
---
artifact: dataset_audit
generated: YYYY-MM-DD
status: draft
---

# Dataset Audit

## Summary

| Metric | Value |
|---|---|
| Total tables discovered | N |
| Near-duplicate groups identified | N |
| Tables recommended for deprecation | N |
| Domains assessed | N |
| Overall governance grade | A/B/C/D |

## Domain Governance Grades

| Domain | Grade | Tables | Canonical Candidates | Issues |
|---|---|---|---|---|
| orders | B | 12 | fct_orders | 3 near-duplicates |
| ... | | | | |

## Near-Duplicate Groups

### [Group 1: Revenue Tables]

| Table | Rows | Last Modified | Assessment |
|---|---|---|---|
| orders_raw | 2.1M | 2024-11-01 | Raw — deprecate |
| revenue_v2 | 2.1M | 2024-09-15 | Stale copy — deprecate |
| fct_orders | 2.1M | 2025-03-01 | **Canonical — retain** |
| fct_orders_v3 | 1.8M | 2025-01-10 | Partial migration — deprecate |

**Recommendation:** Retain `fct_orders`. Deprecate `orders_raw`, `revenue_v2`, `fct_orders_v3` with 90-day sunset.

## Full Table Inventory

[Complete table listing with tier classification]

## Recommended Deprecations

[Ordered list of tables recommended for sunset with justification]
```

### Step 7: Update Status

```yaml
dataset_audit:
  generate: complete
  validate: not_started
  review: not_started
  generated_date: YYYY-MM-DD
  tables_discovered: N
  duplicate_groups: N
  domains_assessed: N
  overall_grade: B
```

### Step 8: Confirm and Suggest Next Steps

```
## Dataset Audit Generated ✓

Discovered N tables across N domains. Identified N near-duplicate groups 
affecting N tables. Overall governance grade: B.

**Highest-priority issues:**
- [Domain]: N competing definitions for [entity]
- [Domain]: Primary table undocumented, no dbt management

**Next steps:**
- /wire:ads_metric-audit-generate — inventory semantic layer coverage
- /wire:ads_query-audit-generate — analyse query history patterns
- /wire:ads_dataset-audit-validate — run automated checks on audit completeness
```

## Edge Cases

### No Direct Warehouse Access

If the consultant cannot provide direct SQL access, request a schema export:
- BigQuery: `bq ls --format=prettyjson project:dataset > schema.json`
- Snowflake: Information Schema CSV export from Snowflake console
- dbt: `dbt ls --output json` provides model inventory with metadata

Work from the export rather than blocking on access.

### Very Large Schemas (>500 tables)

Focus the audit on tables with >10,000 rows and tables modified in the last 12 months. Flag the tail of small/stale tables as "low-priority — likely safe to archive" rather than auditing individually.

### No dbt Project

If no dbt project exists, the governance grade ceiling is C — curated tier tables can only be identified by naming convention and metadata, not by lineage or test coverage. Note this explicitly and factor into the governance_design recommendations.

## Output

- `.wire/<release-folder>/artifacts/dataset_audit.md`
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
