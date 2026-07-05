---
description: Sync artifact status to Jira
argument-hint: <project-folder> <artifact> <action>
---

# Sync artifact status to Jira

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
    'command': 'utils-jira-sync',
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
description: Sync a single artifact lifecycle state to Jira
argument-hint: <project-folder> <artifact> <action>

---

# Jira Status Sync Utility

## Purpose

Sync a single artifact's lifecycle state change to Jira. Transitions the corresponding Sub-task and adds a detailed comment with file names, revision history, reviewer details, and feedback. Also records the event in the artifact's `revision_history` in `status.md` for audit trail tracking. Called by generate/validate/review commands after they update `status.md`.

## Usage

```bash
/wire:utils-jira-sync YYYYMMDD_project_name requirements generate
```

Typically invoked automatically by lifecycle commands after updating status.md.

## Prerequisites

- Atlassian MCP server must be configured
- Project must have Jira keys in `status.md` (created by `/wire:utils-jira-create`)

## Workflow

### Step 1: Check Jira Configuration

**Process**:
1. Read the project's `status.md`
2. Check for `jira` section in YAML frontmatter
3. If no `jira` section exists, skip silently (no output, no error)
4. Extract `jira.project_key`, `jira.structure` (defaults to `subtasks` if absent — backwards compatible), and the artifact's issue keys

### Step 2: Look Up Issue Key

The lookup branches on `jira.structure`:

**If `jira.structure == "single_issue"`**:
1. Look up `jira.artifacts.[artifact].task_key` — this is the single Task that moves through workflow states for all three commands (generate / validate / review).
2. If the key is null or missing, skip silently.
3. Proceed to **Step 3 — Single-issue transitions** below.

**If `jira.structure == "subtasks"` (default — original behaviour)**:
1. Determine the sub-task key from `jira.artifacts.[artifact].[action]_key`
   - Example: for `requirements` + `generate`, look up `jira.artifacts.requirements.generate_key`
2. If the key is null or missing, skip silently.
3. Proceed to **Step 3 — Sub-task transitions** below.

### Step 3: Determine Target Transition

#### Step 3 — Single-issue transitions (`jira.structure == "single_issue"`)

The single Task moves through four workflow states as commands run. Map the local action + state to a target Jira state:

| Action | Local State | Target Jira Status | Notes |
|--------|-------------|-------------------|-------|
| generate | `complete` | "In Progress" | Generation done, awaiting validate |
| validate | `pass` | "In Review" | Validation passed, awaiting human review |
| validate | `fail` | "In Progress" | Generation needs rework; Task is back with the generator |
| review | `approved` | "Done" | All gates passed |
| review | `changes_requested` | "In Progress" | Reviewer requested changes; back to the generator |
| review | `pending` | (no change) | Review not yet started or in flight; leave as "In Review" |

Apply the transition to `task_key` (not a sub-task — there are no sub-tasks in this structure).

#### Step 3 — Sub-task transitions (`jira.structure == "subtasks"`)

Map the local status to a Jira transition on the relevant Sub-task:

| Action | Local State | Target Jira Status |
|--------|-------------|-------------------|
| generate | `complete` | "Done" |
| validate | `pass` | "Done" |
| validate | `fail` | "To Do" |
| review | `approved` | "Done" |
| review | `changes_requested` | "To Do" |
| review | `pending` | "In Progress" |

### Step 4: Get Available Transitions

Let `[target_issue_key]` refer to whichever key Step 2 resolved: the sub-task key under `subtasks` structure, or the task key under `single_issue` structure. The rest of the spec uses `[target_issue_key]` interchangeably.

```
getTransitionsForJiraIssue:
  issueKey: "[target_issue_key]"
```

**Resolve the target status label** using this two-step lookup:

**Step 4a — Check for custom state mapping in status.md**

Read `jira.state_mapping` from status.md. This optional block maps Wire's canonical state names to the custom Jira workflow labels used by this specific project:

```yaml
jira:
  state_mapping:
    done: "Internal QA Complete"
    in_progress: "In Development"
    in_review: "Awaiting Sign-off"
    to_do: "Backlog"
```

If `jira.state_mapping` is present and contains a key for the target state, use that label as the transition target. For example, if the target is "Done" and `state_mapping.done` is "Internal QA Complete", look for a transition named "Internal QA Complete".

**Step 4b — Fall back to default flexible matching**

If `jira.state_mapping` is absent or does not contain a key for the target state, match the target status name flexibly against the available transition names:
- "Done" matches: "Done", "Resolved", "Closed", "Complete"
- "To Do" matches: "To Do", "Open", "Reopened", "Backlog"
- "In Progress" matches: "In Progress", "In Development", "Active"
- "In Review" matches: "In Review", "Review", "Code Review", "In QA", "QA", "Awaiting Review"

### Step 5: Transition the Sub-task

**IMPORTANT: Only transition — do NOT call `editJiraIssue` to update the description. Issue descriptions are set at creation time and must never be modified by sync operations. All lifecycle progress is recorded as comments (Step 6), never by editing the description.**

```
transitionJiraIssue:
  issueKey: "[target_issue_key]"
  transitionId: "[matched_transition_id]"
```

### Step 5.5: Discover Generated Files

Before building the comment, identify the files this artifact produced. This provides concrete detail in the Jira comment.

**Process**:
1. Check `artifacts.[artifact].generated_files` in status.md
2. If the list is populated, use it directly
3. If empty or missing, discover files using Glob based on the artifact type. Use the project's subdirectory within `.wire/[folder]/` as the base path:

| Artifact | Glob Pattern |
|----------|-------------|
| requirements | `requirements/*.md` |
| workshops | `requirements/workshop*.md` |
| conceptual_model | `design/conceptual_model*.md` |
| pipeline_design | `design/pipeline*.md` |
| data_model | `design/data_model*.md` |
| mockups | `design/mockup*.md`, `design/dashboard_mockup*.md` |
| pipeline | `dev/pipeline*.*` |
| dbt | Use `models/**/*.sql` and `models/**/*.yml` in the **repository root** (dbt files live outside the project folder) |
| semantic_layer | Use `*.lkml` files in the repository's LookML project directory |
| dashboards | Use `dashboards/*.lkml` or `dev/dashboard*.md` |
| data_quality | `test/data_quality*.md` |
| uat | `test/uat*.md` |
| deployment | `deploy/*.md` |
| training | `enablement/training*.md` |
| documentation | `enablement/doc*.md`, `enablement/*_guide*.md` |

4. Update `artifacts.[artifact].generated_files` in status.md with the discovered list (so subsequent calls don't need to re-discover)

**For large file lists** (more than 10 files, common with dbt and semantic_layer): group by category in the comment rather than listing individually. For example: "12 files: 4 staging models, 3 integration models, 5 warehouse models" or "8 LookML files: 5 views, 2 explores, 1 dashboard".

### Step 5.6: Compute Revision Number

Determine how many times this artifact has been through the generate cycle, to provide context in the comment.

**Process**:
1. Read `artifacts.[artifact].revision_history` from status.md
2. If the list exists, count entries where `action` is `"generate"` — this is the current revision number
3. If revision_history doesn't exist or is empty, this is revision 1
4. If the current action is `generate` and this is a re-generation (revision_history already has a generate entry), the revision number is previous generate count + 1

**For review comments**: also extract the previous review entries from revision_history to show the feedback trail.

### Step 6: Add Comment with Details

Add a comment to the Sub-task with detailed information about the lifecycle event:

```
addCommentToJiraIssue:
  issueKey: "[target_issue_key]"
  body: "[comment_text]"
```

**Comment templates by action**:

**Generate complete:**
```
**[Artifact Display Name] — Generated**

**Revision**: [N] ([if N>1: "revised after feedback from [previous reviewer name from revision_history]"] / [if N=1: "initial generation"])
**Generated**: [generated_date from status.md]

**Files created:**
[For single-file artifacts:]
- [file path relative to project folder]

[For dbt, include:]
- [models_count] models, [tests_count] tests configured
[Then list files, grouped by layer if >10:]
- Staging: [list or count]
- Integration: [list or count]
- Warehouse: [list or count]
- YAML docs: [list or count]

[For multi-file artifacts with <=10 files, list each:]
- [file path 1]
- [file path 2]
- ...

**Next**: Validate → /wire:[artifact]:validate [folder]
```

**Validate pass:**
```
**[Artifact Display Name] — Validation Passed**

**Validated**: [today's date]
**Revision**: [N]

[For dbt, include test results:]
**Test results**: [tests_passed] passed, [tests_failed] failed

**Checks completed**: All validation checks passed.

**Next**: Submit for review → /wire:[artifact]:review [folder]
```

**Validate fail:**
```
**[Artifact Display Name] — Validation Failed**

**Validated**: [today's date]
**Revision**: [N]

[For dbt, include test results:]
**Test results**: [tests_passed] passed, [tests_failed] failed

**Action**: Fix issues and re-validate.
See validation report in status.md for details.
```

**Review approved:**
```
**[Artifact Display Name] — Approved**

**Reviewer**: [reviewed_by from status.md]
**Date**: [reviewed_date from status.md]
**Revision**: [N]

[If N > 1, include revision summary showing the path to approval:]
**Revision history:**
[For each previous entry in revision_history with action "review":]
- [date]: [result] by [reviewer][if feedback present: " — " + first 150 chars of feedback]

[Example:]
- 2026-02-05: Changes requested by Chris Loveday — "Need to add assignment marks model and cross-reference with ProSolution enrolment data"
- 2026-02-08: Approved by Chris Loveday

This artifact is now locked and ready for downstream phases.
```

**Review changes_requested:**
```
**[Artifact Display Name] — Changes Requested**

**Reviewer**: [reviewed_by from status.md]
**Date**: [reviewed_date from status.md]
**Revision**: [N]

**Feedback:**
> [Full feedback text from artifacts.[artifact].feedback in status.md]

[If N > 1, include previous review context:]
**Previous reviews:**
[For each previous entry in revision_history with action "review":]
- [date]: [result] by [reviewer]

**Action**: Address feedback, revise artifact, re-validate, and re-submit for review.
```

**Artifact display name mapping** (use the same mapping as `jira_create.md`):

| Artifact | Display Name |
|----------|-------------|
| requirements | Requirements Specification |
| workshops | Workshops |
| conceptual_model | Conceptual Model |
| pipeline_design | Pipeline Design |
| data_model | Data Model Design |
| mockups | Dashboard Mockups |
| pipeline | Data Pipeline |
| dbt | dbt Models |
| semantic_layer | Semantic Layer |
| dashboards | Dashboards |
| data_quality | Data Quality Tests |
| uat | User Acceptance Testing |
| deployment | Deployment |
| training | Training Materials |
| documentation | Documentation |

### Step 6.5: Record Revision History

After writing the Jira comment (whether or not the comment succeeded), append an entry to `artifacts.[artifact].revision_history` in status.md. This maintains an audit trail of all lifecycle events for the artifact.

**Process**:
1. Read the current `artifacts.[artifact].revision_history` list from status.md
2. If the list doesn't exist (older status.md without this field), create it as an empty list
3. Append a new entry based on the action:

**For generate:**
```yaml
- date: "[today's date YYYY-MM-DD]"
  action: "generate"
  files: [list from generated_files]
```

**For validate:**
```yaml
- date: "[today's date YYYY-MM-DD]"
  action: "validate"
  result: "[pass|fail]"
```

**For review (approved):**
```yaml
- date: "[today's date YYYY-MM-DD]"
  action: "review"
  result: "approved"
  reviewer: "[reviewed_by from status.md]"
```

**For review (changes_requested):**
```yaml
- date: "[today's date YYYY-MM-DD]"
  action: "review"
  result: "changes_requested"
  reviewer: "[reviewed_by from status.md]"
  feedback: "[feedback text from status.md]"
```

4. Write the updated `revision_history` list back to status.md

**Edge case**: If Jira sync failed (MCP unavailable, transition error), still record the revision history entry — the audit trail should be maintained regardless of Jira connectivity.

### Step 7: Check Parent Task Completion

After transitioning the Sub-task, check if all Sub-tasks under the parent Task are now "Done":

1. Look up the artifact's `task_key` from `jira.artifacts.[artifact].task_key`
2. Check all sub-task keys for this artifact (`generate_key`, `validate_key`, `review_key`)
3. Read their current states from `status.md`:
   - generate == `complete`
   - validate == `pass` (or artifact has no validate step)
   - review == `approved`
4. If all applicable steps are done, transition the parent Task to "Done"

```
getTransitionsForJiraIssue:
  issueKey: "[task_key]"

transitionJiraIssue:
  issueKey: "[task_key]"
  transitionId: "[done_transition_id]"

addCommentToJiraIssue:
  issueKey: "[task_key]"
  body: "All lifecycle steps complete. Artifact is ready."
```

### Step 8: Check Epic Completion

After transitioning a Task to "Done", check if all artifact Tasks under the Epic are done:

1. Read all artifact task states from `status.md`
2. For each in-scope artifact, check if all steps are complete
3. If ALL artifacts are fully complete, transition the Epic to "Done"

```
addCommentToJiraIssue:
  issueKey: "[epic_key]"
  body: "All project artifacts complete. Project ready for closure."
```

### Step 9: Handle Edge Cases

**Atlassian MCP not available:**
- Skip the Jira transition and comment silently. No output, no error. The lifecycle command continues normally.
- **Still record the revision history entry** in status.md (Step 6.5) — audit trail is maintained even without Jira.

**Sub-task already in target state:**
- Skip the transition (avoid duplicate transitions)
- Still add the comment for audit trail

**Transition not available:**
- Log a brief note: `Note: Could not transition [key] to [target]. Current Jira status may differ from local status.`
- Continue without failing

**API error:**
- Log a brief note: `Note: Jira sync failed for [key]. Local status updated successfully.`
- Continue without failing

**Missing revision_history field:**
- If `artifacts.[artifact].revision_history` doesn't exist in status.md (older projects created before this field was added), create it as an empty list and append the current entry. This provides forward compatibility with older status files.

**Missing generated_files field:**
- If `artifacts.[artifact].generated_files` doesn't exist, create it using the Glob discovery from Step 5.5. This provides forward compatibility with older status files.

In all cases, the calling lifecycle command is never blocked by Jira sync issues.

## Output

This utility:
- Transitions Jira Sub-tasks to match local artifact state
- Adds detailed comments with file lists, revision numbers, reviewer details, and feedback for audit trail
- Records each lifecycle event in `artifacts.[artifact].revision_history` in status.md
- Updates `artifacts.[artifact].generated_files` in status.md (via Glob discovery if not already populated)
- Cascades completion up to parent Task and Epic
- Fails gracefully and silently if Jira is unavailable
- Maintains revision_history even when Jira is unavailable

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
