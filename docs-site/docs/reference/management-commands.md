---
sidebar_position: 6
title: Management Commands
---

# Management Commands

Every engagement needs a certain amount of housekeeping around the artifacts themselves: a release has to be created before anything can be generated, its status has to be reported to the client from time to time and, when it is finished, it has to be closed down tidily. Management commands do that work, operating on releases and engagements as a whole (creating, archiving, reporting status and performing housekeeping), and none of them generate or validate individual artifacts. We take them in the order you are likely to meet them, starting with `/wire:new`.

## `/wire:new`

Creates a new release, and it is always the first Wire command you run for an engagement.

```
/wire:new
```

Wire prompts for:
1. Release type
2. Client name and project name
3. Delivery start date
4. Optional: Jira project key
5. Optional: Linear project
6. Optional: Document store (Confluence space or Notion database)
7. Optional: Document store parent page/database

Wire creates:
- `.wire/releases/YYYYMMDD_<client>_<type>/`, the engagement folder
- `.wire/releases/YYYYMMDD_<client>_<type>/config.yaml`, the engagement configuration
- `.wire/releases/YYYYMMDD_<client>_<type>/status.md`, the initial status report
- `.wire/releases/YYYYMMDD_<client>_<type>/execution_log.md`, an empty execution log
- `CLAUDE.md` update, adding project context if it is not already present

---

## `/wire:status`

Shows the current status of all active releases, or of a specific release.

```
/wire:status
/wire:status <release-folder>
```

Output includes:
- Phase and artifact completion counts per release
- Any open review gates
- Any validation failures
- Jira/Linear sync status (if configured)
- Last activity timestamp

With a specific release folder the output is expanded to show every artifact and its current state.

`/wire:status` also performs reconciliation when integrations are configured, syncing any missing Jira/Linear updates and flagging divergences between the local execution log and the external trackers, so that the board your client looks at matches the record on disk.

---

## `/wire:status-sync`

What happens to the record when work is done outside a command run? Status tracking updates automatically only when work runs through Wire commands, and work done conversationally or with an agent's help, which is common in `custom` releases, leaves `status.md`, the execution log and the sprint plan behind. `/wire:status-sync` is the repair path for that (v3.11.8, #204): it reconciles a release's recorded state against evidence and then repairs the record with your confirmation, so that where `/wire:status` reports the record as it stands, `status-sync` fixes it when it has drifted.

```
/wire:status-sync <release-folder>
```

It diffs the recorded state (`status.md`, `execution_log.md`, the governing `sprint_plan.md`) against evidence from git history, files on disk and the log itself, classifies the drift deterministically (`record_behind`, `record_ahead`, `fields_incomplete`, `last_updated_stale`, `totals_stale`, `history_gap`) and presents a numbered drift report. Nothing is written without your explicit confirmation, and declining is side-effect-free. History is append-only (backfilled log rows carry the sync's own timestamp), and the command never downgrades a recorded state on the absence of evidence alone; `record_ahead` items are resolved one at a time with you. Run it before raising a PR for any work done outside command runs, as the PR checklist includes it.

---

## `/wire:archive`

Archives a completed or cancelled release, marking it as archived in the execution log, writing a final status snapshot and optionally exporting all of its artifacts to a client-facing package.

```
/wire:archive <release-folder>
```

Wire asks:
1. Reason for archiving (Completed / Cancelled / Superseded)
2. Whether to export a client package (Markdown files, rendered PDFs)
3. Whether to close associated Jira Epic / Linear Project (if configured)

Archived releases remain in `.wire/releases/` and are shown in `/wire:status` with an "Archived" badge, but they are not included in the active engagement counts.

---

## `/wire:status-report`

Generates a formatted status report for sharing with the client or internally, so that you are not assembling one by hand from `/wire:status` output.

```
/wire:status-report <release-folder>
/wire:status-report <release-folder> --format pdf
/wire:status-report <release-folder> --format confluence
```

Formats:
- **markdown** (default): writes to `.wire/releases/<release>/status_report_YYYYMMDD.md`
- **pdf**: renders to PDF via headless Chrome (requires Playwright installed)
- **confluence**: publishes to the configured Confluence space (requires Atlassian MCP)

The report includes:
- Engagement summary and current phase
- Artifact status table (phase, artifact, state, last updated)
- Open items (validation failures, pending reviews, stakeholder actions)
- Recent decisions log (last ten entries from the execution log)
- Next steps

---

## `/wire:execution-log`

Views or searches the execution log for a release, which is useful when you want the history of one kind of event rather than the whole file.

```
/wire:execution-log <release-folder>
/wire:execution-log <release-folder> --filter decisions
/wire:execution-log <release-folder> --filter failures
/wire:execution-log <release-folder> --since 2024-01-15
```

Filters:
- `decisions`: show only review decisions and stakeholder feedback
- `failures`: show only validation failures and their resolutions
- `approvals`: show only approved artifacts with their approvers
- `all` (default): show everything

---

## `/wire:utils-linear-create`

Creates the Linear project hierarchy for an engagement.

```
/wire:utils-linear-create <release-folder>
```

It creates a Linear Project, Issues (one per artifact) and Sub-issues (one per lifecycle step), and the Linear project and issue IDs are written to `.wire/releases/<release>/config.yaml` so that subsequent commands can sync to them.

---

## `/wire:utils-doc-analyze`

Analyses a source document and extracts the Wire-relevant information from it without creating any artifacts, which makes it a safe first step when a statement of work arrives.

```
/wire:utils-doc-analyze path/to/SoW.pdf
/wire:utils-doc-analyze path/to/SoW.pdf path/to/kickoff-notes.md
```

Output:
- Extracted deliverables with descriptions and acceptance criteria
- Wire match scores (how well each deliverable maps to an existing Wire command)
- Proposed engagement structure
- Open questions Wire cannot resolve from the document alone

It is useful for scoping an engagement before running `/wire:new`, as well as for verifying that a SoW is specific enough to drive Wire artifact generation.

---

## `/wire:utils-docstore-config`

Configures or reconfigures the document store integration for a release.

```
/wire:utils-docstore-config <release-folder>
```

This is the same configuration step that is offered during `/wire:new` Step 9.5, made available separately for releases that were set up without a document store.
