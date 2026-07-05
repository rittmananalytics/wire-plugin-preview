---
description: Run dbt models
argument-hint: <project-folder>
---

# Run dbt models

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
    'command': 'utils-run-dbt',
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
command: utility
artifact: utils
domain: utils
release_types: []
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Run dbt models for the project in dbt Cloud or locally

---

# Run dbt Utility Command

## Purpose

Execute dbt models for a project, either in dbt Cloud (recommended) or locally. Provides options for full refresh, selective runs, and test execution.

## Prerequisites

- dbt project with models generated (`/wire:dbt-generate` completed)
- dbt Cloud account OR dbt Core installed locally
- BigQuery/warehouse credentials configured

## Workflow

### Step 1: Determine dbt Execution Environment

**Ask user:**

```
How would you like to run dbt?

1. dbt Cloud (recommended)
2. dbt Core (local)
3. Show me the commands to run manually
```

### Step 2a: If dbt Cloud

**Process**:
1. Check if `.wire/config.md` has dbt Cloud project ID and API key
2. If not configured, prompt user to add credentials
3. Use dbt Cloud API to trigger job

**API Call**:
```bash
curl -X POST \
  https://cloud.getdbt.com/api/v2/accounts/{account_id}/jobs/{job_id}/run/ \
  -H "Authorization: Bearer {api_token}" \
  -H "Content-Type: application/json" \
  -d '{"cause": "Triggered by agent_v2"}'
```

**Monitor Run**:
```
dbt Cloud job triggered: Run #{run_id}

Status: Running...
View in dbt Cloud: https://cloud.getdbt.com/...

Checking status every 30 seconds...
```

**When complete**:
```
✓ dbt run completed successfully

Models run: [count]
Tests passed: [count]
Execution time: [time]

View full results: [dbt Cloud URL]
```

### Step 2b: If dbt Core (local)

**Process**:
1. Verify dbt is installed: `dbt --version`
2. Verify profiles.yml is configured
3. Run dbt commands via Bash tool

**Commands to run**:

```bash
# Navigate to dbt project
cd dbt/

# Install dependencies
dbt deps

# Run models
dbt run

# Run tests
dbt test

# Generate documentation
dbt docs generate
```

**Output results**:
```
✓ dbt deps completed
✓ dbt run completed: [count] models built
✓ dbt test completed: [count] tests passed

Models materialized:
- staging: [count] views
- integration: [count] views
- warehouse: [count] tables

Tests:
- Passed: [count]
- Failed: [count]

[If failures, show details]
```

### Step 2c: If show manual commands

**Output**:
```
## Manual dbt Execution

### Using dbt Cloud:
1. Go to https://cloud.getdbt.com
2. Navigate to your project
3. Click "Run" or trigger a job
4. Select environment and models to run

### Using dbt Core (command line):

```bash
# Navigate to dbt project
cd dbt/

# Install dependencies (first time only)
dbt deps

# Run all models
dbt run

# Run specific models
dbt run --select staging.<source_name>.*
dbt run --select +enrolment_fct  # model and all upstream
dbt run --select enrolment_fct+  # model and all downstream

# Run models in specific folders
dbt run --select warehouse.core.*

# Full refresh (rebuild incremental models)
dbt run --full-refresh

# Run tests
dbt test

# Run tests for specific models
dbt test --select enrolment_fct

# Generate documentation
dbt docs generate

# Serve documentation locally
dbt docs serve
```

### Useful Options:

```bash
# Run in target environment
dbt run --target prod

# Run with specific vars
dbt run --vars '{"current_academic_year": "24/25"}'

# Parallel threads
dbt run --threads 4

# Debug
dbt run --debug
```

### After Running:

Check the results and update project status:
/wire:dbt-validate <project_id>
```

### Step 3: Handle Errors

**If dbt run fails:**

1. Parse error messages
2. Identify failing models
3. Suggest fixes:

```
dbt run failed with [count] errors:

❌ Model staging.<source_name>.stg_<source_name>__<entity> failed
   Error: Syntax error at line 23

   Suggested fix:
   - Check SQL syntax in dbt/models/staging/<source_name>/stg_<source_name>__<entity>.sql
   - Verify column names match source schema

❌ Model warehouse.core.enrolment_fct failed
   Error: Dependency int__student not found

   Suggested fix:
   - Ensure upstream model runs first
   - Check ref() syntax: {{ ref('int__student') }}

To debug:
1. Review error details: [show full error]
2. Fix the model SQL
3. Re-run: /wire:utils-run-dbt <project_id>
```

### Step 4: Update Status

**If run successful:**

**Process**:
1. Read current status file
2. Update dbt artifact:
   ```yaml
   dbt:
     generate: complete
     validate: pass  # if tests also passed
     last_run: 2026-02-13T10:30:00Z
     models_run: [count]
     tests_passed: [count]
   ```
3. Write updated status.md

**Output**:
```
Status updated: dbt models validated successfully

Next steps:
- Review results in BigQuery/warehouse
- Update semantic layer if needed: /wire:semantic_layer-generate <project_id>
- Generate dashboards: /wire:dashboards-generate <project_id>
```

## Advanced Options

### Selective Runs

**Run only specific layers:**
```bash
# Only staging models
dbt run --select staging.*

# Only warehouse models
dbt run --select warehouse.*

# Specific model and dependencies
dbt run --select +enrolment_fct
```

### Full Refresh

**For incremental models:**
```bash
dbt run --full-refresh
```

### Test Specific Models

**Run tests for specific models:**
```bash
dbt test --select enrolment_fct
dbt test --select warehouse.core.*
```

## Edge Cases

### dbt Not Installed (local)

```
Error: dbt not found

dbt Core is not installed. Please:
1. Install dbt: pip install dbt-bigquery (or dbt-snowflake, etc.)
2. Configure profiles.yml
3. Try again

Or use dbt Cloud instead (recommended).
```

### profiles.yml Not Configured

```
Error: dbt profile not configured

Please configure ~/.dbt/profiles.yml with your warehouse credentials.

See: https://docs.getdbt.com/docs/core/connect-data-platform/profiles.yml
```

### dbt Cloud API Not Configured

```
Error: dbt Cloud credentials not found

Please add to .wire/config.md:

```yaml
dbt_cloud:
  account_id: "your_account_id"
  project_id: "your_project_id"
  api_token: "your_api_token"
```

Get your API token from: https://cloud.getdbt.com/settings/profile
```

### Models Already Built

If target tables already exist:

```
Warning: Some models already exist in the warehouse.

Options:
1. Run normally (will refresh existing models)
2. Full refresh (rebuild everything from scratch)
3. Cancel

Which would you prefer?
```

### MCP Tool Integration

When a dbt MCP server is configured in the project, prefer MCP tools over CLI commands for:
- Running models and tests (MCP handles authentication and error reporting)
- Querying the semantic layer
- Listing available models and metrics

Fall back to CLI commands when MCP tools are unavailable or when you need features not exposed by the MCP server (e.g., `dbt compile --select`, advanced selectors).

### Post-Run Analysis

After `dbt build` or `dbt run` completes, check `target/run_results.json` for detailed execution data:

```json
{
  "results": [
    {
      "unique_id": "model.project.stg_events",
      "status": "success",
      "execution_time": 3.42,
      "adapter_response": { "rows_affected": 150000 }
    }
  ]
}
```

Key fields to check:
- `status`: "success", "error", or "skipped"
- `execution_time`: seconds — flag models > 60s for optimization
- `adapter_response.rows_affected`: row count — useful for data validation
- `failures`: number of test failures (for test results)

## Output

This command:
- Executes dbt run (and optionally dbt test)
- Updates project status with run results
- Provides links to view results
- Suggests next steps

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
