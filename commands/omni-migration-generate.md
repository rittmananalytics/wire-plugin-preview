---
description: Generate Omni migration runbook — translate model view SQL on a branch, two-stage connection repoint
argument-hint: <release-folder>
---

# Generate Omni migration runbook — translate model view SQL on a branch, two-stage connection repoint

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
    'command': 'omni-migration-generate',
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
artifact: omni_migration
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: target_setup
    action: review
    outcome: approved
  - artifact: omni_audit
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Generate the Omni reporting-layer migration runbook — translate model view SQL on a branch, validate the branch against a pilot connection scope, promote and cut over the connection in two stages with rollback

---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: omni_migration` and `artifact_file_path: migration/omni_migration_runbook.md` before proceeding.

---

## Data Safety — Read Before Proceeding

Before modifying any Omni configuration, read `data_safety` from status.md and output this reminder:

```
⚠️  DATA SAFETY REMINDER

Source warehouse ([source_platform]): READ ONLY.
  Do NOT delete or repoint the production Omni connection during the
  migration phase. The existing [source_platform] connection stays live
  as the rollback path until cutover.

Validation runs against a MODEL BRANCH and a pilot / non-production
  connection scope only. Production workbooks, dashboards, and their
  consumers are never touched during validation — because most tiles
  query through topics rather than raw SQL, they pick up the model's
  target connection automatically once the branch is promoted, not before.

Target writes go to: [data_safety.target_project or migration.target_project]

[If data_safety.production_projects is non-empty:]
BLOCKED production projects (do not point any connection at these):
  [list each production project ID]
```

If any action would repoint or delete the production Omni connection outside the cutover sequence, or run validation against production workbooks, stop and report the conflict before proceeding.

---

# Omni Migration — Generate

## Purpose

Generates the runbook for migrating the client's Omni reporting layer from the source warehouse to the target. The pivot is the **Omni connection** — the migration adds a target connection alongside the source, translates the model's view SQL by approach on a **model branch**, validates the branch against a pilot/non-production connection scope, then promotes the branch and cuts over the primary connection in **two stages with per-stage rollback**.

This is a **reporting-layer** migration, the Omni counterpart to Metabase migration. It is **not gated by `migration.scope`** — it runs for any migration where the client uses Omni.

The model branch is Omni's own mechanism for developing model changes independently of live content, and it changes the shape of this migration compared to Metabase's. Metabase has no equivalent, so its migration validates against a throwaway decoy collection built and populated by hand. Omni doesn't need one: translation and validation happen on a branch that never touches the published model, and because most tiles query through topics rather than raw SQL, dashboards inherit the branch's connection change automatically the moment it is promoted — there is no per-tile repoint step to script for topic-backed content.

### Client-supplied inventory — judgement call

Metabase migration hard-blocks without a client-supplied card/SQL inventory, because Metabase's dialect-specific SQL is scattered across individually-authored native-SQL cards and inferring which ones are safe to translate isn't reliable at scale. Omni's object model doesn't have the same problem: dialect-specific SQL concentrates in the model's view definitions, and `omni_audit` already scans **every** view exhaustively, not a sample, because a typical Omni model has dozens of views maintained by a small modeling team rather than hundreds of ad hoc cards. An approved `omni_audit` already constitutes a complete, confirmed inventory of the model's dialect-specific SQL — a second client-supplied export would just be re-confirming numbers this command already has.

The exception is tiles with a raw-SQL override — the one place Omni's *content* layer, not its model, carries source-platform SQL. These are audited in `omni_audit` too, but a tile can be added or edited after the audit ran without appearing anywhere else, since content and model are versioned and audited independently. So this command does **not** hard-block on a separate client-supplied inventory the way Metabase does, but it does require the raw-SQL tile count to be reconfirmed live against the Omni instance before translation starts (Step 1). If the live count doesn't match `omni_audit`'s `raw_sql_tile_count`, stop and require a re-run of `omni-audit-generate` first — the drift means the audit's raw-SQL scope is no longer current, and that scope is the one place this migration can't safely infer from the model alone.

## Prerequisites

- `target_setup review: approved` — target warehouse objects exist
- `omni_audit review: approved`
- `dbt_migration: complete` for any batch containing models referenced by in-scope views
- Omni CLI configured with permission to create a model branch on the target profile

## Inputs

- `.wire/releases/$ARGUMENTS/audit/omni_audit.md`
- `.wire/releases/$ARGUMENTS/migration/migration_strategy.md`
- `.wire/releases/$ARGUMENTS/status.md`
- Canonical platform pair files at `wire/platform_pairs/<source>_to_<target>/` (translation guide, type mapping)

## Workflow

### Step 1: Confirm prerequisites and reconfirm raw-SQL tile scope

Confirm `target_setup review: approved` and `omni_audit review: approved`. Confirm `dbt_migration` batches referenced by in-scope views are complete.

Activate the `omni` skill for connection details and the object hierarchy. Using `omni-content-explorer`, recount the live raw-SQL tile total and compare it against `raw_sql_tile_count` in `artifacts.omni_audit` (status.md). If they differ, stop:

```
Raw-SQL tile count has drifted since the last audit (audit: N, live: M).
Re-run /wire:omni-audit-generate $ARGUMENTS to refresh scope, then re-run:
/wire:omni-migration-generate $ARGUMENTS
```

### Step 2: Add the target connection additively

Using `omni-admin`, add the target connection alongside the existing source connection. This is additive — the source connection stays in place and is not touched again until Stage 2.

### Step 3: Create a model branch for translation work

Using `omni-model-builder`, create a model branch off the current published model. All view SQL edits for this migration happen on the branch; nothing here affects the published model or live content until the branch is promoted (Step 7).

### Step 4: Translate views and raw-SQL tiles by approach

Load the view catalog from `omni_audit` and process `repoint` first, then `rewrite_sql`, then `rebuild`, on the branch:

- **repoint** — views with no SQL (`base_table`) or portable SQL: point the view at the target connection on the branch. Verify it resolves; if a `repoint` view fails, downgrade it to `rewrite_sql`.
- **rewrite_sql** — translate the view's base/derived table SQL from the source dialect to the target using the platform-pair guide (`wire/platform_pairs/<source>_to_<target>/translation_guide.md`). Test the translated SQL on the branch against the target connection — row count and result shape match a frozen source baseline. Record a before/after SQL diff in the runbook.
- **rebuild** — views depending on a source-only construct are rebuilt against the target connection on the branch; capture the original view definition first.

**Raw-SQL tiles don't participate in the branch** — content and model are versioned separately in Omni, so a tile's SQL can't be edited on the model branch. Translate each raw-SQL tile's SQL the same way (repoint / rewrite_sql / rebuild), but test the translated SQL as a standalone query via `omni-query` against the target connection, without touching the live tile. Hold the translated SQL as a pending edit; it gets applied to the live tile at Stage 2 cutover, alongside the connection repoint, with a saved before/after diff for rollback.

### Step 5: Run a schema refresh against the target connection

Using `omni-admin`, run a schema refresh against the target connection. The model branch cannot validate view translations against the target until this has run — a stale or absent schema on the target connection will surface as missing-object errors that look like translation failures but aren't.

### Step 6: Stage 1 — validate the branch against a pilot/non-production connection scope

Scope the target connection's schema refresh (or the branch's query scope) to a pilot subset — a non-production dataset, a pilot tenant, or a schema-level subset agreed in the migration strategy. Using `omni-query`, run each translated/rebuilt view's queries **against the branch** and compare row count, key columns, and aggregates against a **frozen source baseline** (not moving production), per the migration strategy's equivalency section. For raw-SQL tiles, run the held pending SQL standalone via `omni-query` against the same pilot scope and compare the same way.

Nothing is promoted or repointed at this stage. If validation fails for a view or tile, iterate the translation on the branch and re-validate; the published model and primary connection are untouched throughout.

**Rollback (Stage 1):** abandon or revert the branch. The primary connection was never touched, so there is nothing else to revert.

### Step 7: Stage 2 — promote the branch and repoint the primary connection

Once Stage 1 validation passes:

1. **Promote the branch** — merge the model branch into the published model. Because most content queries through topics rather than raw SQL, dashboards and tiles built on translated views now resolve against whatever connection the model points at — no per-tile repoint step is needed for topic-backed content.
2. **Repoint the primary connection** from source to target (`omni-admin`), so the promoted model's views resolve against the target warehouse in production.
3. **Apply the pending raw-SQL tile edits** saved in Step 4 — these are the one piece of content that doesn't inherit the connection change automatically, since they bypass the model.

**Rollback (Stage 2):** repoint the primary connection back to the source connection's details; revert the model to its pre-promotion state (a revert commit on the published model, or restore from the pre-promotion branch snapshot); restore each raw-SQL tile's SQL from the saved before/after diff.

### Step 8: Write the runbook

**Output location**: `.wire/releases/$ARGUMENTS/migration/omni_migration_runbook.md`

Structure:
1. Topology and rationale (additive target connection + model branch; connection is the cutover pivot; no decoy workbook needed — dashboards inherit via topics once the branch promotes)
2. Build steps (add target connection, create model branch)
3. Pre-flight checklist (target objects exist, dbt batches complete, omni_audit approved, raw-SQL tile count reconfirmed live, source baseline frozen, model branch created)
4. Per-view translation — repoint / rewrite_sql (with SQL diff) / rebuild (with rebuild plan)
5. Raw-SQL tile translation — pending edits table (tile, workbook, before/after SQL, `omni-query` test result, applied at Stage 2)
6. Branch validation procedure — Stage 1 result comparison via `omni-query` against a frozen baseline, on a pilot/non-production connection scope
7. **Two-stage cutover sequence with per-stage rollback**:
   - **Stage 1 — branch validation on a pilot/non-production connection scope.** Validate translated views and raw-SQL tiles on the branch against a frozen baseline. **Rollback:** abandon/revert the branch; the primary connection and published model are untouched.
   - **Stage 2 — promote the branch and repoint the primary connection.** Promote the branch (making the new model live), repoint the primary connection from source to target, apply the pending raw-SQL tile edits. **Rollback:** repoint the primary connection back to the source connection's details, revert the model to its pre-promotion state, restore raw-SQL tile SQL from the saved diffs.
8. Rollback procedures consolidated per stage, with the exact connection details and branch/tile state needed to revert each.

The source connection stays live and untouched until Stage 2, and remains the rollback path through Stage 2.

### Step 9: Update status

```yaml
artifacts:
  omni_migration:
    generate: complete
    file: migration/omni_migration_runbook.md
    generated_date: "{{TODAY}}"
    repoint_count: N
    rewrite_sql_count: N
    rebuild_count: N
    raw_sql_tile_translation_count: N
    model_branch: "{{BRANCH_NAME}}"
    raw_sql_tile_count_reconfirmed: true
```

### Step 10: Output next command

```
/wire:omni-migration-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/omni_migration_runbook.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_migration` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_migration` as artifact_id, `Omni Migration` as artifact_name, and the `file` value from `artifacts.omni_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_migration` as artifact, `generate` as action.

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
