---
description: Report on all project statuses or specific project
argument-hint: [project-folder] or --archived
---

# Report on all project statuses or specific project

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
    'command': 'status',
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
command: lifecycle
artifact: status
domain: status
release_types: []
action_type: lifecycle
logs_execution: false
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Report on all project statuses

---

# Data Platform Project Status Report

## Purpose

Generate a concise status report showing artifact lifecycle progress. Outputs a table format with minimal verbosity.

## Usage

```bash
/wire:status                    # Show all project statuses
/wire:status 20260210_rowcal    # Show detailed status for specific project
/wire:status --archived         # Show archived projects
```

## Workflow

### Step 1: Scan Project Folders

**Process**:
1. If `--archived` flag is present, use Glob: `.wire/archive/[0-9]*_*/status.md`
2. Otherwise, use Glob to find all status files: `.wire/[0-9]*_*/status.md`
3. Extract folder names from the matched file paths
4. Build list of all projects

### Step 2: Parse Status Files

**For each project**:
1. Read `status.md`
2. Parse YAML frontmatter to extract:
   - `project_id`, `project_name`, `client`
   - `current_phase`
   - `jira` section (if configured): `epic_key`, artifact issue keys
   - `artifacts` lifecycle states

**Artifact State Mapping**:
```
generate: not_started → ⬜, pending → ⏳, complete → ✅
validate: not_started → ⬜, pending → ⏳, pass → ✅, fail → ❌
review:   not_started → ⬜, pending → ⏳, approved → ✅, changes_requested → 🔄
ready:    auto-calculated from above
```

**Ready Calculation**:
```
# Standard artifacts (brief, wireframe, schema, lookml):
ready = ✅ if (generate=complete AND validate=pass AND review=approved)
ready = ⬜ otherwise

# Mock data (requires Snowflake table):
ready = ✅ if (generate=complete AND validate=pass AND review=approved AND snowflake_table is set)
ready = ⬜ otherwise
```

### Step 3: Generate Output

Both overview and detail modes use the same artifact lifecycle table format.

**Artifact lifecycle table** (used in both modes):

```
| Artifact   | Generate   | Validate   | Review       | Ready |
|------------|------------|------------|--------------|-------|
| Brief      | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Wireframe  | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Catalog    | ✅          | -          | -            | ✅     |
| Schema     | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Mock Data  | ✅ complete | ⬜          | ⬜            | ⬜     |
| LookML     | ⬜          | ⬜          | ⬜            | ⬜     |
```

**Notes:**
- Catalog row shows "-" for Validate and Review columns since it's a generate-only artifact.
- Mock Data requires `snowflake_table` to be set for "Ready" status (shown in Highlights if missing)
- Artifacts with `not_applicable` state are hidden from the table
- If `jira.epic_key` exists, add a "Jira" column showing the artifact's `task_key` (e.g., `PROJ-124`)
- In overview mode, if Jira is configured, show the Epic key in the project header: `## name (ID | type | client | phase | PROJ-123)`

---

**If no specific project** (overview mode):

For each project, show a project header followed by the artifact lifecycle table and a Next action line:

```
# Data Platform Status

## omni_channel_retail_aws (20260205 | new_template | Internal | Prep)

| Artifact   | Generate   | Validate   | Review       | Ready |
|------------|------------|------------|--------------|-------|
| Brief      | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Wireframe  | ✅ complete | ✅ pass     | ⬜            | ⬜     |
| Catalog    | ✅          | -          | -            | ✅     |
| Schema     | ✅ complete | ✅ pass     | ⬜            | ⬜     |
| Mock Data  | ⬜          | ⬜          | ⬜            | ⬜     |
| LookML     | ⬜          | ⬜          | ⬜            | ⬜     |

**Next:** `/wire:wireframe-review 20260205_omni_channel_retail_aws`

---

Summary: 1 project(s) | 0 ready for Prod
```

**Overview format rules:**
- Each project gets an H2 header: `## name (ID | type | client | phase)`
- Followed by the standard artifact lifecycle table
- Followed by a single **Next:** line with the suggested command
- Projects separated by horizontal rules
- Summary line at the bottom

---

**If specific project requested** (detail mode):

Same artifact lifecycle table, plus a Highlights section with additional context:

```
# omni_channel_retail_aws - Status

| Artifact   | Generate   | Validate   | Review       | Ready |
|------------|------------|------------|--------------|-------|
| Brief      | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Wireframe  | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Catalog    | ✅          | -          | -            | ✅     |
| Schema     | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Mock Data  | ✅ complete | ⬜          | ⬜            | ⬜     |
| LookML     | ⬜          | ⬜          | ⬜            | ⬜     |

### Highlights

- **Next:** Run `/wire:mockdata-validate 20260210_rowcal` to validate mock data
- **Wireframe:** https://lovable.dev/projects/[ID]
- **Snowflake:** Mock data not loaded yet (run `/wire:utils-load-mock-data` when ready)
```

**Highlights section rules:**
- Always include "Next:" with the suggested command
- Include "Jira:" line if `jira.epic_key` exists, showing Epic key and link
- Include "Wireframe:" line only if a Lovable URL exists in status.md
- Include "Snowflake:" line if mock data generated but `snowflake_table` not set
- Include "LookML:" line if LookML generated, showing file count (from `generated_files` array length)
- Include "Blockers:" only if there are open clarification items
- Include other notable items (e.g., "Brief approved by [stakeholder] on [date]")
- Keep to 2-5 bullet points max

### Step 4: Determine Next Action

**Logic for next action**:

First, read the `project_type` from status.md frontmatter. Use the appropriate phase ordering:

**Default ordering**: brief → wireframe → catalog → schema → mockdata → lookml (or for newer projects: requirements → workshops → pipeline_design → data_model → mockups → pipeline → dbt → semantic_layer → dashboards → data_quality → uat → deployment → training → documentation)

**Dashboard-first ordering** (for `dashboard_first` projects): requirements → mockups → viz_catalog → data_model → seed_data → dbt → semantic_layer → dashboards → data_refactor → data_quality → uat → deployment → training → documentation

For each artifact in the appropriate phase order:

**For Brief, Wireframe, Schema** (full lifecycle):
1. If `generate` is not `complete`: suggest generate command
2. Else if `validate` is not `pass`: suggest validate command
3. Else if `review` is not `approved`: suggest review command
4. Else: artifact is ready, check next artifact

**For Catalog** (generate-only):
1. If `generate` is not `complete`: suggest generate command
2. Else: artifact is ready, check next artifact

**For Mock Data** (full lifecycle + snowflake_table for ready):
1. If `generate` is not `complete`: suggest generate command
2. Else if `validate` is not `pass`: suggest validate command
3. Else if `review` is not `approved`: suggest review command
4. Else if `snowflake_table` is not set: artifact NOT ready (show in Highlights)
5. Else: artifact is ready, check next artifact

**Note:** The load utility (`/wire:utils-load-mock-data`) is shown in Highlights when `snowflake_table` is not set, but does NOT block the normal lifecycle progression.

**For LookML** (full lifecycle):
1. If `generate` is not `complete`: suggest generate command
2. Else if `validate` is not `pass`: suggest validate command
3. Else if `review` is not `approved`: suggest review command
4. Else: artifact is ready, all Dev phase artifacts complete!

**Note:** When LookML is generated, show file count in Highlights (e.g., "LookML: 7 files generated").

**For Viz Catalog** (generate-only, `dashboard_first` projects only):
1. If `generate` is not `complete`: suggest generate command
2. Else: artifact is ready, check next artifact

**For Seed Data** (full lifecycle, `dashboard_first` projects only):
1. If `generate` is not `complete`: suggest generate command
2. Else if `validate` is not `pass`: suggest validate command
3. Else if `review` is not `approved`: suggest review command
4. Else: artifact is ready, check next artifact

**For Data Refactor** (full lifecycle, `dashboard_first` projects only):
1. If `generate` is not `complete`: suggest generate command
2. Else if `validate` is not `pass`: suggest validate command
3. Else if `review` is not `approved`: suggest review command
4. Else: artifact is ready, check next artifact

**Command Mapping**:
```
Artifacts:
  brief.generate       → /wire:brief-generate
  brief.validate       → /wire:brief-validate
  brief.review         → /wire:brief-review
  wireframe.generate   → /wire:wireframe-generate
  wireframe.validate   → /wire:wireframe-validate
  wireframe.review     → /wire:wireframe-review
  catalog.generate     → /wire:catalog-generate
  schema.generate      → /wire:schema-generate
  schema.validate      → /wire:schema-validate
  schema.review        → /wire:schema-review
  mockdata.generate    → /wire:mockdata-generate
  mockdata.load        → /wire:utils-load-mock-data  ← utility, not lifecycle step
  mockdata.validate    → /wire:mockdata-validate
  mockdata.review      → /wire:mockdata-review
  lookml.generate      → /wire:lookml-generate
  lookml.validate      → /wire:lookml-validate
  lookml.review        → /wire:lookml-review

Dashboard-first artifacts:
  viz_catalog.generate    → /wire:viz_catalog-generate     ← generate-only (like catalog)
  seed_data.generate      → /wire:seed_data-generate
  seed_data.validate      → /wire:seed_data-validate
  seed_data.review        → /wire:seed_data-review
  data_refactor.generate  → /wire:data_refactor-generate
  data_refactor.validate  → /wire:data_refactor-validate
  data_refactor.review    → /wire:data_refactor-review
```

### Output Examples

**Overview (all projects)**:
```
# Data Platform Status

## rowcal (0001 | new_client | RowCal | Dev)

| Artifact   | Generate   | Validate   | Review       | Ready |
|------------|------------|------------|--------------|-------|
| Brief      | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Wireframe  | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Catalog    | ✅          | -          | -            | ✅     |
| Schema     | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Mock Data  | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| LookML     | ⬜          | ⬜          | ⬜            | ⬜     |

**Next:** `/wire:lookml-generate 0001_rowcal`

---

Summary: 1 project(s) | 0 ready for Prod
```

**Detail (specific project)**:
```
# rowcal - Status

| Artifact   | Generate   | Validate   | Review       | Ready |
|------------|------------|------------|--------------|-------|
| Brief      | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Wireframe  | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Catalog    | ✅          | -          | -            | ✅     |
| Schema     | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Mock Data  | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| LookML     | ✅ complete | ⬜          | ⬜            | ⬜     |

### Highlights

- **Next:** Run `/wire:lookml-validate 0001_rowcal` to validate LookML
- **Wireframe:** https://lovable.dev/projects/c3dbf5fc-a317-4698-a9b5-c6f0c82e9ff7
- **LookML:** 7 files generated (3 views, 1 explore, 3 dashboards)
```

### Step 4.5: Sync Jira Status (Optional)

If `jira` section exists in `status.md` and `jira.epic_key` is not null:

1. Follow the full reconciliation workflow in `specs/utils/jira_status_sync.md`
2. Pass the project folder
3. The utility will sync all local artifact states to Jira Sub-tasks, Tasks, and Epic
4. If any discrepancies are found, add them to the Highlights section
5. If Atlassian MCP is unavailable, skip silently

This ensures Jira stays in sync every time `/wire:status` is run.

## State Icons Reference

| Icon | Meaning |
|------|---------|
| ⬜ | Not started |
| ⏳ | In progress / Pending |
| ✅ | Complete / Pass / Approved |
| ❌ | Failed |
| 🔄 | Changes requested (needs iteration) |

## Error Handling

- **No projects found**: Display message suggesting to create a project folder
- **Invalid status file**: Skip project with warning
- **Missing frontmatter**: Use default "not_started" states

## Design Philosophy

**Minimal verbosity, maximum clarity.**

Key principles:
1. **Table-first**: Primary output is always a table
2. **Icon-driven**: Use emoji for quick visual scanning
3. **Next action**: Always show what to do next
4. **Auto-calculate Ready**: Don't require manual "ready" state management
5. **Phase awareness**: Group artifacts by their relevant phase

Execute the complete workflow as specified above.
