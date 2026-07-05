---
description: Generate Fivetran connector migration runbook
argument-hint: <release-folder>
---

# Generate Fivetran connector migration runbook

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
    'command': 'ingestion-migration-generate',
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
artifact: ingestion_migration
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
delegates_to:
  - utils/precondition_gate
description: Execute ingestion connector migration via MCP server, or generate runbook if MCP unavailable

---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.

Follow `specs/utils/stale_artifact_check.md` with `artifact_id: ingestion_migration` and `artifact_file_path: migration/ingestion_migration_runbook.md` before proceeding.

---

## Data Safety — Read Before Proceeding

Before creating any connectors, read `data_safety` from status.md and output this reminder:

```
⚠️  DATA SAFETY REMINDER

Source platform ([source_platform]): READ ONLY.
  Do NOT modify, re-point, or delete any existing source connectors.
  Create new connectors pointing at the TARGET destination only.

Target writes go to: [data_safety.target_project or migration.target_project]

[If data_safety.production_projects is non-empty:]
BLOCKED production projects (do not create connectors pointing to these):
  [list each production project ID]
```

If a tool call would modify an existing source connector, or create a connector pointing to a production project listed in `data_safety.production_projects`, stop immediately and report the conflict before proceeding.

---

# Ingestion Migration — Generate

## Purpose

Migrates every in-scope connector from the source ingestion platform to the target platform destination. When the relevant ingestion tool's MCP server is available, Wire executes the migration directly — creating new connectors and generating setup/connect card URLs for the user to enter credentials. A runbook is generated as a fallback only when no MCP server is reachable.

**Default behaviour**: always create new connectors for the target destination. Never edit or re-point an existing connector's destination — that risks interrupting the source pipeline during the parallel-run window.

## Ingestion tool connectivity map

A project may use multiple ingestion tools simultaneously. Each tool has its own connectivity method — MCP server, direct API call, or runbook-only. This table covers all tools the ingestion audit can surface:

| Ingestion tool | Connectivity method | Key probe | Fallback |
|---|---|---|---|
| Fivetran | MCP — `mcp__fivetran__` | `mcp__fivetran__get_account_info` | Runbook |
| RudderStack | MCP — `mcp__plugin_wire_rudderstack__` | `mcp__plugin_wire_rudderstack__user_details` | Runbook |
| Coupler.io | MCP — `mcp__claude_ai_Coupler_io__` | `mcp__claude_ai_Coupler_io__list-dataflows` | Runbook |
| Airbyte | API — `AIRBYTE_TOKEN` + `AIRBYTE_BASE` env vars | `GET $AIRBYTE_BASE/workspaces` | Runbook |
| Segment | API — `SEGMENT_TOKEN` + `SEGMENT_BASE` env vars | `GET $SEGMENT_BASE/sources` | Runbook |
| Stitch | *(no MCP or API — runbook only)* | — | Runbook |
| Custom / other | Check available MCP tools for a matching prefix | — | Runbook |

Handle each tool group separately. Never mix-apply one tool's MCP server to another tool's connectors.

## Prerequisites

- `target_setup review: approved`
- Target warehouse schemas exist (target_setup scripts executed)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/ingestion_audit.md`
- `.wire/releases/$ARGUMENTS/migration/migration_strategy.md`

## Workflow

### Step 1: Confirm prerequisites

Confirm `target_setup review: approved`. If not, stop with message.

### Step 2: Pre-flight — identify all in-scope tools and check connectivity

Read `ingestion_audit.md`. Collect every distinct `service_type` or `ingestion_tool` that has at least one connector with `include_in_migration: true`. This is the in-scope tool list for this run.

For each tool in the in-scope list, determine its connectivity status using the table above:

- **MCP tools** (Fivetran, RudderStack, Coupler.io): run the key probe call with a 10-second timeout. Interpret the result:
  - Probe succeeds → `CONNECTED — will execute via MCP`
  - Auth error (401/403) → `AUTH REQUIRED — re-authenticate via /mcp before proceeding`
  - Timeout or tool unavailable → `NOT CONFIGURED — will fall back to runbook`
- **API tools** (Airbyte, Segment): check whether the required env vars are set (`AIRBYTE_TOKEN`/`AIRBYTE_BASE` or `SEGMENT_TOKEN`/`SEGMENT_BASE`). If set, attempt a lightweight API call. Interpret:
  - Call succeeds → `CONNECTED — will execute via API`
  - 401 / missing env var → `NOT CONFIGURED — will fall back to runbook`
- **Runbook-only tools** (Stitch, custom/other): mark as `RUNBOOK ONLY` without probing.

Output the pre-flight table before starting any migration work:

```
Ingestion Pre-flight Check
════════════════════════════════════════════════════════════════

  Tool          Connectors in scope   Connectivity              Migration path
  ──────────    ───────────────────   ──────────────────────    ──────────────
  Fivetran      18                    ✅ Connected (MCP)         Direct execution
  RudderStack   4                     ✅ Connected (MCP)         Direct execution
  Coupler.io    2                     ⚠️  Auth required (MCP)    Blocked — re-auth first
  Segment       3                     ❌ Not configured (API)    Runbook fallback

Total in scope: 27 connectors
MCP/API executable: 22   Runbook fallback: 5   Blocked: 2
```

If any tool shows `AUTH REQUIRED`, stop and instruct the user to re-authenticate that tool (run `/mcp` in Claude Code and re-authenticate, or re-set the env var). Do not proceed past this step until no tool is in a blocked state.

Once all tools are either CONNECTED or RUNBOOK fallback (none blocked), output:

```
Pre-flight complete. Proceeding with migration.
  Direct execution: [tools]
  Runbook fallback: [tools]
```

Then continue to Step 3 for each CONNECTED tool and Step 4 for each fallback tool.

### Step 3: MCP-driven migration (primary path)

For each connector in the ingestion audit with `include_in_migration: true` where an MCP server is available, working in order of ascending complexity (Low first):

1. **Identify the target destination**: use the MCP server's list/group call (e.g. `mcp__fivetran__list_groups`, `mcp__airbyte__list_destinations`) to find the destination that corresponds to the target warehouse, as named in the target setup.

2. **Create a new connector**: call the MCP server's create connection tool (e.g. `mcp__fivetran__create_connection`, `mcp__airbyte__create_connection`) with:
   - The same service/connector type as the source connector
   - The target destination identifier
   - Schema / schema prefix matching the source connector (as mapped in the ingestion audit)
   - Do **not** modify or re-point the source connector — it stays active for the parallel run

3. **Generate a setup link**: call the MCP server's connect card or setup URL tool (e.g. `mcp__fivetran__create_connect_card`). Record the returned URL. For tools without a connect card API, use whatever credential-entry URL the MCP server provides.

4. **Present the setup URL** to the user immediately with clear instructions: "Open this link to enter credentials for `<connector_name>`. Once saved, the initial sync will start automatically."

5. **Track completion**: after the user confirms credentials entered (or after a reasonable wait), call the MCP server's connection state tool to confirm the connector reaches `connected` / `active` state. Note the result.

6. **Credential rotation checklist**: for this connector, note:
   - Service accounts or API keys that need new target-platform credentials
   - IP allowlists that need updating for the target platform

For High-complexity connectors: add a note listing common failure modes and resolution steps specific to that connector type.

Write a per-connector status summary as each one completes.

### Step 4: Runbook fallback (MCP unavailable)

If no MCP server is reachable for a given set of connectors, generate a step-by-step runbook for those connectors.

**Output location**: `.wire/releases/$ARGUMENTS/migration/ingestion_migration_runbook.md`

For each connector with `include_in_migration: true`:

1. **Identify destination mapping**: map the source destination schema to its target platform equivalent (from the target setup DDL)
2. **Connector steps**: always document **new connector creation** steps — never "edit destination" on the existing connector
3. **Activation steps**: source connector stays active; new target connector is created, activated, synced, and equivalency-checked
4. **Credential rotation**: list service accounts, API keys, and IP allowlist changes needed

For High-complexity connectors: include an expanded diagnostic section with common failure modes.

Structure:
1. Pre-flight checklist
2. Per-connector migration steps (Low complexity first)
3. Credential rotation checklist
4. Post-migration validation steps
5. Source connector deactivation procedure (deferred to cutover phase)

### Step 5: Update status

```yaml
artifacts:
  ingestion_migration:
    generate: complete
    method: mcp_executed | runbook_generated
    file: migration/ingestion_migration_runbook.md   # runbook path only; omit for MCP path
    generated_date: "{{TODAY}}"
    connectors_migrated: N
    connectors_pending_credentials: N   # connectors with connect card URL not yet confirmed
```

### Step 6: Output next command

```
/wire:ingestion-migration-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/ingestion_migration_runbook.md` (runbook fallback only)
- Per-connector connect card URLs and status summary (MCP path, printed to console)
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `ingestion_migration` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `ingestion_migration` as artifact_id, `Ingestion Migration` as artifact_name, and the `file` value from `artifacts.ingestion_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `ingestion_migration` as artifact, `generate` as action.

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
