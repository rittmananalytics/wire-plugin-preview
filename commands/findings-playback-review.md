---
description: Sponsor playback session — Sponsor Validation Checklist (the canonical gate)
argument-hint: <release-folder>
---

# Sponsor playback session — Sponsor Validation Checklist (the canonical gate)

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
    'command': 'findings-playback-review',
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
command: review
artifact: findings_playback
domain: sop_discovery
release_types:
  - sop_discovery
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: findings_playback
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Sponsor playback session — the canonical client-facing review gate

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Findings Playback — Review

## Purpose

**The canonical client-facing review gate of a SOP discovery release.**

This is not an internal review. The review action *is* the sponsor playback meeting — the deck is presented live (by Lewis or Mark per the playbook), the meeting is recorded via Fathom, and the **Sponsor Validation Checklist** is captured at the close.

State transitions:
- `complete` after the deck has been generated and validated
- `reviewed` after the playback meeting has been held (Fathom recording attached)
- `approved` **only when every item on the Sponsor Validation Checklist is `true`**

If any checklist item is `no`, the release stays at `reviewed` and a 30-minute follow-up sponsor session is scheduled (explicit in the playbook's failure modes).

Models Phase 4 (playback meeting + Sponsor Validation Checklist) of the Canonical Discovery Playbook.

## Inputs

- `.wire/releases/$ARGUMENTS/playback/findings_playback.html`
- `.wire/releases/$ARGUMENTS/playback/findings_playback_validation.md` (must be PASS or PASS WITH WARNINGS)
- `.wire/releases/$ARGUMENTS/planning/discovery_analyses.md`

## Workflow

### Step 1: Pre-flight

1. Resolve `$ARGUMENTS`. Confirm validation has passed. If FAIL, stop: "Resolve validation failures before holding the playback."
2. Confirm `status.md → sponsor_validation.vision_statement_excerpt` is set. If null, prompt the consultant to set it now from the deck's Vision Statement slide. The playback is partly about the sponsor signing off on this — it needs to exist.

### Step 2: Capture playback meeting context

Ask the consultant:

```
Has the playback meeting been held?

(a) Yes — recorded via Fathom, ready to capture the Sponsor Validation Checklist
(b) Not yet — confirm date and presenter
```

If (b): record the planned date and presenter under `status.md → sponsor_validation.playback_date` and `sponsor_validation.preferred_delivery_option: null`, then stop with: "Re-run this command after the playback has been held."

If (a): proceed.

### Step 3: Pull Fathom transcript

Ask for the Fathom URL for the playback recording. Use the Fathom MCP server to pull:
- Full transcript
- Meeting summary
- Sponsor's verbal endorsements (or refusals) on each of the seven Sponsor Validation Checklist items

This is the most important Fathom integration in Wire — the sponsor's verbal "yes, this is what we want" against the Vision Statement is, per the playbook, the most important artefact in the engagement after the SoW itself.

### Step 4: Pre-fill the checklist from the transcript

For each of the seven Sponsor Validation Checklist items, walk the transcript and propose a value (`true` / `false` / `unclear`). Surface the supporting quote (verbatim) for each.

Then present each item to the consultant for confirmation:

```
For each of the 7 Sponsor Validation Checklist items, confirm the value based on the Fathom transcript and your in-room recall.

1. **Maturity Curve pin agreed.**
   Proposed: <true/false/unclear> based on quote: "<verbatim>"
   Confirm? (yes / no / change to false / change to unclear)

2. **Hierarchy of Needs diagnosis agreed.** ...
3. **PPT diagnosis agreed.** ...
4. **Vision Statement endorsed (both paragraphs).** ...
5. **Solution Initiatives confirmed.** ...
6. **Preferred Delivery Option named (Build / Pair / Coach).** ...
7. **Open conflicts resolved (or follow-up scheduled).** ...
```

For item 6, also capture the named delivery option ("build" / "pair" / "coach" / null) under `sponsor_validation.preferred_delivery_option`.

For any `unclear` or `false`, ask:

```
What follow-up action is needed for this item?
```

### Step 5: Determine the review outcome

If every item is `true`, outcome = **Approved (playback signed off)**.

If any item is `false` or `unclear`, outcome = **Reviewed — follow-up required**. Schedule a 30-min sponsor follow-up session within 1 week. Record the follow-up date under `sponsor_validation.follow_up_session`.

### Step 6: Record the result

Update `status.md`:

```yaml
sponsor_validation:
  playback_held: true
  playback_date: <YYYY-MM-DD>
  playback_fathom_url: <URL>
  maturity_pin: "<confirmed pin>"
  vision_statement_excerpt: "<first 200 chars of vision statement>"
  preferred_delivery_option: "<build|pair|coach|null>"
  checklist:
    maturity_pin_agreed: <true|false>
    hierarchy_diagnosis_agreed: <true|false>
    ppt_diagnosis_agreed: <true|false>
    vision_statement_endorsed: <true|false>
    solution_initiatives_confirmed: <true|false>
    delivery_option_named: <true|false>
    conflicts_resolved: <true|false>
  follow_up_session: <YYYY-MM-DD or null>

artifacts:
  findings_playback:
    review: complete       # = playback held and checklist captured
                           # Note: this is "reviewed" in workflow terms,
                           # not "approved". Approved = checklist all true.
```

### Step 7: Write the Playback Meeting Notes

**Output**: `.wire/releases/$ARGUMENTS/playback/playback_meeting_notes.md`

```markdown
# Findings Playback — Meeting Notes

**Date**: <YYYY-MM-DD>
**Presenter**: <Lewis / Mark>
**Fathom recording**: <URL>
**Sponsor**: <name>
**Outcome**: <Approved (signed off) | Reviewed — follow-up required>

## Sponsor Validation Checklist

| # | Item | Result | Supporting quote |
|---|---|---|---|
| 1 | Maturity Curve pin agreed (<pin>) | ✅ / ❌ | "<quote>" |
| 2 | Hierarchy of Needs diagnosis agreed | ✅ / ❌ | "<quote>" |
| 3 | PPT diagnosis agreed | ✅ / ❌ | "<quote>" |
| 4 | Vision Statement endorsed | ✅ / ❌ | "<quote>" |
| 5 | Solution Initiatives 1–5 confirmed | ✅ / ❌ | "<quote>" |
| 6 | Preferred Delivery Option named (<option>) | ✅ / ❌ | "<quote>" |
| 7 | Open conflicts resolved | ✅ / ❌ | "<quote>" |

## Decisions taken

[Bullet list — what the sponsor decided in the meeting]

## Concerns raised (and how they were addressed)

[Bullet list]

## Follow-ups

- [ ] Owner — action — due date

## Next session

[If approved]: Delivery Roadmap session (or release-spawn directly).
[If follow-up required]: 30-min sponsor session on <date> to resolve <items>.
```

### Step 8: Sync to document store

Follow `specs/utils/docstore_sync.md`. The Playback Meeting Notes go to the Confluence "Playback Meeting Notes" page named in the playbook folder structure (`5. Findings Playback / Playback Meeting Notes`).

### Step 9: Output review summary

If approved:
```
## Findings Playback Review — Approved ✅

All 7 Sponsor Validation Checklist items signed off.

**Maturity pin**: <pin>
**Preferred Delivery Option**: <build/pair/coach>
**Vision Statement endorsed**: yes

### Next Steps

1. Generate the Delivery Roadmap:
   /wire:delivery-roadmap-generate $ARGUMENTS

2. Or spawn Release 1 directly:
   /wire:release-spawn $ARGUMENTS
```

If follow-up required:
```
## Findings Playback Review — Follow-up Required ⚠️

Items not yet endorsed:
- [list]

**Follow-up session**: <date>

The release will remain at `reviewed` until every checklist item is true. Do not start Release 1 until the playback is approved — the playbook's failure-mode table specifically calls out the catastrophic cost of skipping this.
```

### Step 10: Approval gate

The release-level "approved" state is only set when:
- `sponsor_validation.playback_held == true`, AND
- every `sponsor_validation.checklist.*` is `true`

This is checked by `/wire:status` and surfaced as a hard gate before `/wire:release-spawn` can chain into a delivery release.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/playback/findings_playback.html` (no body changes, but the review captures Fathom URL etc)
- `.wire/releases/$ARGUMENTS/playback/playback_meeting_notes.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`

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
