---
description: Set up document store (Confluence/Notion) for a project
argument-hint: <project-folder>
---

# Set up document store (Confluence/Notion) for a project

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
    'command': 'utils-docstore-setup',
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
description: Configure the optional document store for a Wire engagement
argument-hint: <project-folder>

---

# Document Store Setup Utility

## Purpose

Configure an external document store for a Wire engagement so that generated artifacts are automatically published and kept in sync. Supports Confluence, Notion, or both simultaneously. Called from `/wire:new` after the project folder and `status.md` have been created.

This utility:
- Asks the user which document store(s) to connect
- Validates that the chosen providers are accessible via their respective MCP servers
- Creates a top-level "Wire Documents" parent page/container in each configured provider
- Records all configuration in `status.md` frontmatter and `.wire/engagement/context.md`

If no document store is wanted, or if a provider's MCP is unavailable, the utility exits gracefully — document store configuration is entirely optional.

## Usage

```bash
/wire:utils-docstore-setup YYYYMMDD_project_name
```

Typically invoked automatically from `/wire:new` (Step 10.5). Can also be run standalone on an existing project to add or reconfigure document store settings.

## Prerequisites

- Project must exist with a valid `status.md`
- For Confluence: Atlassian MCP server must be configured
- For Notion: Notion MCP server must be configured
- Neither is required — the utility degrades gracefully if a provider is unavailable

---

## Workflow

### Step 1: Read Project Context

**Process**:
1. Locate the project folder under `.wire/` using the `project_id` argument
2. Read `status.md` from that folder
3. Extract from YAML frontmatter:
   - `project_name`
   - `client_name`
   - `docstore` section (check for existing configuration — see Step 1.5)

### Step 1.5: Check for Existing Configuration

If `status.md` already contains a `docstore.provider` that is not `null`:

```
Document store is already configured for this project.

Provider: [provider]
Confluence parent page: [page_url if available]
Notion parent page: [page_url if available]

Do you want to:
1. Keep existing configuration (no changes)
2. Reconfigure — replace the current document store settings
```

If the user chooses to keep existing configuration, exit. If reconfiguring, proceed to Step 2 and overwrite all docstore fields.

### Step 2: Choose Document Store Provider

Ask the user which document store to configure:

```json
{
  "questions": [{
    "question": "Which document store would you like to use for this engagement?",
    "header": "Document Store",
    "options": [
      {"label": "None", "description": "Don't sync artifacts to an external document store"},
      {"label": "Confluence", "description": "Publish artifacts to a Confluence space (requires Atlassian MCP)"},
      {"label": "Notion", "description": "Publish artifacts to a Notion workspace (requires Notion MCP)"},
      {"label": "Both", "description": "Publish to both Confluence and Notion simultaneously"}
    ],
    "multiSelect": false
  }]
}
```

**If "None"**: Write `docstore.provider: null` to `status.md` and exit. No further steps.

**If "Confluence"**: Proceed to Step 3 (Confluence setup). Skip Step 4.

**If "Notion"**: Skip Step 3. Proceed to Step 4 (Notion setup).

**If "Both"**: Run Step 3 and Step 4 independently. A failure in one does not block the other.

---

### Step 3: Confluence Setup

#### Step 3.1: Auto-Detect Atlassian Cloud ID

Use the Atlassian MCP to discover accessible cloud instances:

```
getAccessibleAtlassianResources
```

- If a single cloud instance is returned: use it automatically and inform the user:
  ```
  Detected Atlassian cloud: [cloudName] (ID: [cloudId])
  ```
- If multiple instances are returned: present them for selection:
  ```
  Multiple Atlassian clouds detected. Which one should be used?
  1. [cloudName 1] ([cloudId 1])
  2. [cloudName 2] ([cloudId 2])
  ```
- If no instances are returned or the MCP call fails: log the error and skip Confluence setup. Record `docstore.provider` as `notion` (if Notion was also selected) or `null`. Output:
  ```
  Note: Could not connect to Atlassian (MCP unavailable or no accessible resources).
  Skipping Confluence setup. You can configure it later by re-running:
  /wire:utils-docstore-setup [folder]
  ```

Store `cloud_id` for use in subsequent steps.

#### Step 3.2: Get Confluence Space Key

If a `confluence_space_key` was passed in by the calling command (e.g. from `/wire:new` or `/wire:autopilot`), use it directly — do not ask again.

Otherwise, ask the user for the Confluence space where engagement documents should live:

```
What is the Confluence space key for this engagement?
(e.g. PROJ, ACME, DATA — found in the space URL: /wiki/spaces/PROJ/...)
```

#### Step 3.3: Validate the Space

Use the Atlassian MCP to confirm the space exists and is accessible:

```
getConfluenceSpaces:
  cloudId: "[cloud_id]"
  spaceKey: "[space_key]"
```

- If the space is found: proceed.
- If not found or access denied:
  ```
  Error: Confluence space "[space_key]" could not be found or is not accessible.
  Please check the space key and your permissions, then re-run:
  /wire:utils-docstore-setup [folder]
  ```
  Skip the remainder of Confluence setup. Treat as if Confluence was not configured.

#### Step 3.4: Ask for Optional Parent Page

Ask the user (in chat) whether to create the engagement folder under a specific page, or at the space root:

```
Where in the "[space_key]" space should Wire documents be created?

- Press Enter to create at the space root
- Or enter the title of an existing page to nest documents under it
  (e.g. "Client Projects" or "Engagements 2026")
```

If the user provides a parent page title:
- Search for the page using:
  ```
  searchConfluenceUsingCql:
    cql: "space = \"[space_key]\" AND title = \"[parent_page_title]\" AND ancestor = root"
  ```
  (Broaden to `ancestor != null` if the root search returns no results.)
- If found: store the returned `page_id` as `confluence_parent_ancestor_id` for use in Step 3.5.
- If not found:
  ```
  Page "[parent_page_title]" was not found in space [space_key].
  Creating the Wire Documents folder at the space root instead.
  ```
  Use space root (omit `parentId` in the create call).

If the user presses Enter: create at the space root (no `parentId`).

#### Step 3.5: Create the Engagement Folder Page

Create a parent page in Confluence titled "[Engagement Name] — Wire Documents". Use `[client_name] [project_name]` as the engagement name:

```
createConfluencePage:
  cloudId: "[cloud_id]"
  spaceKey: "[space_key]"
  parentId: "[confluence_parent_ancestor_id]"  # omit if space root
  title: "[client_name] [project_name] — Wire Documents"
  body: "[build the body as described below]"
  representation: "storage"
```

Build the page body dynamically from `status.md` so the table only includes artifacts that are in-scope for this engagement:

```xml
<p>This page is the central index for all Wire Framework artifacts generated during the
<strong>[client_name] — [project_name]</strong> engagement.</p>

<p>Artifacts are published automatically each time a generate command completes.
Do not rename or move this page — the Wire Framework uses its page ID to locate and
update child pages.</p>

<table>
  <thead>
    <tr>
      <th><p>Artifact</p></th>
      <th><p>Status</p></th>
      <th><p>Last Synced</p></th>
    </tr>
  </thead>
  <tbody>
    <!-- One row per in-scope artifact from status.md (state != not_applicable): -->
    <tr>
      <td><p>[Artifact Display Name]</p></td>
      <td><p>Pending generation</p></td>
      <td><p>—</p></td>
    </tr>
  </tbody>
</table>
```

All rows start as "Pending generation" — they will be updated with live links by `docstore_sync.md` Step 3.5 each time an artifact is generated.

Record the returned `id` as `confluence_parent_page_id` and the `_links.webui` value as `confluence_parent_page_url`.

**If page creation fails**:
```
Note: Could not create Confluence parent page. Error: [error message]
Skipping Confluence setup. You can retry later:
/wire:utils-docstore-setup [folder]
```
Treat Confluence as unconfigured and continue.

---

### Step 4: Notion Setup

#### Step 4.1: Get Notion Parent Page

If a `notion_parent_page_id` was passed in by the calling command (e.g. from `/wire:new` or `/wire:autopilot`), use it directly — do not ask again.

Otherwise, ask the user for the Notion page under which all engagement documents should be created:

```
What is the Notion parent page for this engagement?

Paste the Notion page URL or page ID where Wire documents should be created as sub-pages.
(e.g. https://www.notion.so/My-Projects-abc123def456 or just the ID: abc123def456)

This page must already exist in your Notion workspace and be accessible via the Notion MCP.
```

Parse the input:
- If a full URL is provided: extract the page ID from the last path segment (after the final `-`)
- If a bare ID is provided: use directly

#### Step 4.2: Validate the Notion Page

Retrieve the page to confirm it exists and is accessible:

```
notion_get_page:
  page_id: "[notion_parent_page_id]"
```

- If successful: proceed. Extract the page title from the response for confirmation:
  ```
  Found Notion page: "[page title]"
  Wire documents will be created as sub-pages here.
  ```
- If not found or access denied:
  ```
  Error: Notion page "[id]" could not be found or is not accessible.
  Please check the page ID and ensure the Notion integration has access to it, then re-run:
  /wire:utils-docstore-setup [folder]
  ```
  Skip the remainder of Notion setup. Treat as if Notion was not configured.

#### Step 4.3: Create the Engagement Folder Page

Create a parent page in Notion titled "[client_name] [project_name] — Wire Documents":

```
notion_create_page:
  parent:
    page_id: "[notion_parent_page_id]"
  properties:
    title:
      title:
        - text:
            content: "[client_name] [project_name] — Wire Documents"
  children:
    - object: block
      type: paragraph
      paragraph:
        rich_text:
          - text:
              content: >
                This page is the central index for all Wire Framework artifacts generated
                during the [client_name] — [project_name] engagement. Artifacts are published
                automatically each time a generate command completes. Do not rename or move
                this page — the Wire Framework uses its page ID to locate and update child pages.
    - object: block
      type: heading_2
      heading_2:
        rich_text:
          - text:
              content: "Artifacts"
    - object: block
      type: paragraph
      paragraph:
        rich_text:
          - text:
              content: "Sub-pages will appear here as artifacts are generated."
```

Record the returned `id` as `notion_parent_page_id` (the new folder page, not the user-supplied parent) and the `url` as `notion_parent_page_url`.

**If page creation fails**:
```
Note: Could not create Notion parent page. Error: [error message]
Skipping Notion setup. You can retry later:
/wire:utils-docstore-setup [folder]
```
Treat Notion as unconfigured and continue.

---

### Step 5: Update status.md

Write the docstore configuration into the `status.md` YAML frontmatter. Determine the correct `provider` value:
- Only Confluence succeeded: `provider: confluence`
- Only Notion succeeded: `provider: notion`
- Both succeeded: `provider: both`
- Neither succeeded: `provider: null`

```yaml
docstore:
  provider: [confluence|notion|both|null]
  confluence:
    cloud_id: "[cloud_id]"                      # null if Confluence not configured
    space_key: "[space_key]"                    # null if Confluence not configured
    parent_page_id: "[confluence_parent_page_id]"  # the "Wire Documents" page created above
    parent_page_url: "[confluence_parent_page_url]"
    artifacts: {}                               # populated by docstore_sync.md
  notion:
    parent_page_id: "[notion_parent_page_id]"   # the "Wire Documents" page created above
    parent_page_url: "[notion_parent_page_url]"
    artifacts: {}                               # populated by docstore_sync.md
```

For any provider that was not configured, set all its fields to `null` and `artifacts: {}`.

### Step 6: Update engagement/context.md

Append (or create if absent) a `## Document Store` section to `.wire/engagement/context.md`:

```markdown
## Document Store

**Provider**: [None | Confluence | Notion | Both]

[If Confluence configured:]
**Confluence Space**: [space_key]
**Confluence Parent Page**: [[client_name] [project_name] — Wire Documents]([confluence_parent_page_url])
All generated artifacts will be published as child pages of this Confluence page.

[If Notion configured:]
**Notion Parent Page**: [[client_name] [project_name] — Wire Documents]([notion_parent_page_url])
All generated artifacts will be published as sub-pages of this Notion page.

[If None:]
No external document store configured. Artifacts are maintained only in the local .wire/ folder.
```

If a `## Document Store` section already exists (reconfiguration case), replace it entirely.

### Step 7: Report Results

Output a summary:

```
## Document Store Configured

[If Confluence:]
✓ Confluence
  Space: [space_key]
  Parent page: [client_name] [project_name] — Wire Documents
  URL: [confluence_parent_page_url]

[If Notion:]
✓ Notion
  Parent page: [client_name] [project_name] — Wire Documents
  URL: [notion_parent_page_url]

[If both:]
Artifacts will be synced to both providers each time a generate command completes.

[If none:]
Document store not configured. Artifacts will not be synced externally.
You can configure this later by running: /wire:utils-docstore-setup [folder]
```

### Step 8: Handle Edge Cases

**Atlassian MCP not configured:**
- Skip Confluence setup silently
- If the user selected "Confluence" or "Both", note: `"Note: Atlassian MCP is not configured. Skipping Confluence setup."`

**Notion MCP not configured:**
- Skip Notion setup silently
- If the user selected "Notion" or "Both", note: `"Note: Notion MCP is not configured. Skipping Notion setup."`

**Both providers fail:**
- Set `docstore.provider: null` in status.md
- Report what was attempted and suggest retrying

**Parent page creation succeeds but URL is not returned:**
- Store the `page_id` only; set `parent_page_url: null`
- The URL can be reconstructed later from the page ID if needed

**Running standalone (not from `/wire:new`):**
- After completing setup, remind the user: `"Re-run /wire:utils-docstore-setup at any time to update configuration."`

In all cases, the calling `/wire:new` workflow is never blocked — document store setup is additive and optional.

## Output

This utility:
- Configures zero, one, or two document store providers for the engagement
- Creates "Wire Documents" parent pages/containers in each configured provider
- Records `cloud_id`, `space_key`, `parent_page_id`, and `parent_page_url` in `status.md`
- Updates `.wire/engagement/context.md` with a human-readable summary
- Fails gracefully and individually per provider — one provider failing never blocks the other
- Can be re-run at any time to add or replace document store configuration

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
