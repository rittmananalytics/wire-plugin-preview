---
description: Release-type-agnostic operating model — one release director, one orchestrating session, N flat lanes; the operating rules, lane brief, release claim, session and parked-decision handling, and the co-existence controls
---

# Utils — Release Director Operating Model

A shared operating doc, not a command. It defines how a Wire release is run
when a human directs and an agent operates: who decides, who dispatches, who
executes, and what each of them is allowed to write.

Referenced by `specs/start.md`, `specs/delegate.md`,
`specs/utils/runnable_set.md`, `specs/utils/migration_fleet.md` (the
`platform_migration` profile of this model), and the `release-director` skill
shipped with the Claude Code plugin.

It generalises `specs/utils/migration_fleet.md`, which a live platform
migration derived by trial and failure. The six rules below were already
release-type-agnostic; the lane roster and the fleet's stage ladder were not,
and stay in `migration_fleet.md`.

**Nothing about the record changes.** Every step still runs the real Wire
command, so `status.md`, `execution_log.md`, the precondition gate, telemetry
and the artifacts on disk are identical whether a command was typed or
dispatched. This model changes who types, not what runs.

## The three tiers

| Tier | Who | Duties |
|---|---|---|
| Release director | One human per release | Client communications, rulings and waivers, approval gates, judgment catches, lane-count and budget decisions. The director supervises and decides; the director does not execute tasks. |
| Orchestrating session | One session per release (highest-capability model available) | Reads the release-type graph for what is runnable (`specs/utils/runnable_set.md`), dispatches and monitors lanes, single writer of `status.md` and `execution_log.md`, runs the consolidation and backstop pass, assembles PR evidence, records rulings in `decisions.md` the moment they land. |
| Lane agents | 1 to 12 concurrent, flat | One scoped task each, in its own tree, with its own state file. Reports once: complete, stalled, or needs a ruling. |

**Who invokes Wire commands.** Under this model, almost nobody types them. The
director speaks in intents and rulings ("run what's next", "approve
internally", "two lanes, nothing against a warehouse"); the orchestrating
session translates those into Wire command invocations and lane dispatches;
lanes run their assigned commands and report back through their state files.
Typed-command counts dropping while the execution log fills with Wire runs is
the operating model working, not the framework falling out of use. The
`invoked_by` telemetry property (`specs/utils/telemetry.md`) is what keeps
that measurable.

### How the tiers differ by release type

The fleet model was built for a release with thousands of independent items
and 6 to 12 lanes. A `dbt_development` release has 5 required artifacts and 3
hard review gates. The tiers are the same; the orchestrator's job shifts.

| Tier | `platform_migration` (`migration_fleet.md`) | Linear release types | `bi_migration` |
|---|---|---|---|
| Release director | Rulings on waivers, fleet size, budget, client comms | Release type and profile choice, goal priorities, approvals at each review edge, registry proposals, budget  Parity or redesign per dashboard tier, the drop list, PDT disposition, permission mapping, topic architecture, batch order, parallel-run window, cutover date, decommission |
| Orchestrating session | Dispatch and monitor 6 to 12 lanes, single writer of register and verdict log, consolidation pass | Know where the release is, run the next runnable step(s), carry rulings to gates, report once, park at the next approval edge  Dispatch model slices, content batches and parity sweeps per batch; single writer of the register and verdict log; re-run `omni models validate` on the branch before reporting a batch ready |
| Lanes | Translation slices, build lanes, comparison sweeps, PR prep | One artifact each (the existing auto-delegation in `specs/delegate.md` Step 2), fan-out only where `delegate.md` Step 2.5 already defines it (dbt layers, explores)  One model batch, one content batch, or one parity sweep each; a permissions lane; all flat |

Parallelism on a linear release type comes from the graph, not from item
counts. `specs/utils/runnable_set.md` computes it: two artifacts with no
dependency between them are two lanes.

### bi_migration lane roster

A `bi_migration` release (Looker to Omni) is batched like a migration and gated like a linear release. The plan (`/wire:bi-migration-plan-generate`) cuts the batches; the graph releases each artifact; lanes take one batch each.

| Lane type | Scope | State file | Invokes |
|---|---|---|---|
| Model slice | One model batch of views and explores | progress manifest at `migration/omni_model/<batch>/lane.md` | `/wire:omni-model-generate <release> --batch N`, `/wire:omni-model-lint <release> --batch N`, `/wire:omni-model-validate <release> --batch N` |
| Content batch | One content batch of dashboards | plan and manifest under `migration/omni_content/<batch>/` | `/wire:omni-content-generate <release> --batch N`, `/wire:omni-content-validate <release> --batch N` |
| Parity sweep | One batch's tiles | verdict JSON per `specs/migration/equivalency/verdict_schema.md` | `/wire:bi-equivalency-validate <release> --batch N` |
| Permissions | Groups, user attributes, access grants from the plan | progress manifest | `/wire:omni-target-setup-generate <release>` |

Rulings the director makes, each a parked decision until made: parity or redesign per dashboard tier; the drop list; PDT disposition (dbt model, Omni query view, or drop); permission mapping; topic architecture (one topic per explore, or schema, shared and workbook layering); batch order; parallel-run window; cutover date; decommission. `/wire:bi-migration-plan-review` is where most of them close.

Budget note: parity runs query the same warehouse from both tools. The plan sets `bi_migration.parity_scope` (tiles of tier 1 dashboards by default, or all), a pinned as-of, and the cost governance rules below apply: the dry-run bound is the authorisation figure, and an overrun is disclosed in the lane's report.

Consolidation pass for this type: before a model batch is reported ready, the orchestrator re-runs `omni models validate` on the branch and reads the `needs_human` count from the batch's file, never from the lane's summary. Before a content batch is reported ready, it reads the manifest's `state` column. Before cutover, it reads tile verdicts from the register.

## Operating rules

Each rule states its enforcement: **mechanical** (a command refuses) or
**convention** (stated in every lane brief, checked by the orchestrator). A
convention is still binding; the difference is only who catches the violation.

| # | Rule | Enforcement | Why (observed failure) |
|---|---|---|---|
| 1 | Lanes run **flat**: no sub-agent fan-out below a lane | Convention (lane brief) | Nested fan-out multiplied token burn into two hard usage-limit outages in one day |
| 2 | **One build per warehouse project** at a time | Mechanical where a lock exists (`dbt-migration-defer-build`'s build-slot lock); convention elsewhere | Concurrent builds against one project contend and duplicate cost |
| 3 | **Tree ownership declared per lane**: each lane names the directories it may write; no two live lanes overlap | Convention (lane brief; orchestrator checks before dispatch) | A build lane and a reconciliation lane corrupted each other's file sets |
| 4 | Every lane writes **incremental state with a resume contract** (below) | Convention (lane brief template carries it) | Two hard outages resumed with near-zero loss only because every lane had incremental state |
| 5 | Every lane's spend counts against the release **budget** | Mechanical: `specs/delegate.md`'s budget check plus the cost governance rules below | A single unguarded build day cost four figures |
| 6 | **Single writer of `status.md` and `execution_log.md`: the orchestrating session.** Lanes write only their own artifact tree and their own state file | Convention (lane brief; orchestrator's consolidation check) | Concurrent writes corrupted rows; 46 commits in 24 hours across 4 people silently discarded 54 models of completed work |

**Rule 6 is the change for linear release types.** Outside orchestrated mode,
a delegated subagent updates `status.md` itself and that behaviour is
unchanged. Inside orchestrated mode, a lane writes its artifact and a state
file; the orchestrator reads the state file and writes `status.md`. The
orchestrator sets `WIRE_INVOKED_BY=lane` in the lane's environment, and the
lane brief states the rule; a lane that finds itself with `WIRE_INVOKED_BY=lane`
does not write `status.md` or `execution_log.md`.

## Lane state and resume contract

Every lane brief includes, verbatim:

- **State file**: the lane's own file at a path inside the lane's owned tree,
  rewritten after **each completed item**, never only at the end. Default path
  for a linear release type:
  `.wire/releases/<release>/lanes/<lane-label>.md` — one lane, one file, named
  by the lane label. Migration lanes keep their existing shapes (verdict JSON
  per `specs/migration/equivalency/verdict_schema.md` for comparison lanes, a
  progress manifest for translation, build and PR-prep lanes).
- **Resume contract**: on restart with the same brief, read the state file
  first and skip every completed item. Losing the session must cost at most
  the in-flight item.
- **Completion**: the final state-file write marks the lane `complete` with a
  one-line summary. The orchestrator treats a lane with no writes for 30
  minutes as stalled and may re-dispatch its remaining items to a new lane
  (the resume contract makes this safe).
- **Chunk ledgers with deterministic job ids.** A lane moving data in chunks (a
  bulk copy, a history bring-in) keeps a **chunk ledger** — one row per chunk:
  boundary keys, row count, load-job id, state — and derives each load-job id
  deterministically from the release, table, and chunk boundary (e.g.
  `wire_<release>_<table>_<chunk_floor>`), never from a timestamp or a random
  suffix. A deterministic id makes the re-run idempotent: re-submitting a
  completed chunk is rejected by the warehouse as a duplicate job instead of
  loading the rows twice.
- **Staged runbooks before credential stops.** When a lane can predict losing
  its credentials (an expiring token, a scheduled MCP re-auth), it writes the
  remaining steps as a staged runbook in its state file *before* the stop, so
  the resume — by the same lane or its replacement — starts from a plan rather
  than a reconstruction.
- **Resume-by-message.** A paused or killed session resumes by sending the same
  lane brief to a fresh agent; the state file carries the context. No lane may
  hold essential state only in conversation memory.

## Lane brief template

Every dispatch carries these fields. `specs/delegate.md` Step 6 composes them;
`migration_fleet.md`'s lane roster names the values for migration lanes.

```
Lane:          <lane label, e.g. "conceptual_model" or "dbt-developer [staging 1/2]">
Release:       <release folder>
Task:          <the Wire command(s) this lane runs, in order>
Owns:          <the directories this lane may write — nothing else>
State file:    .wire/releases/<release>/lanes/<lane-label>.md
Resume:        Read the state file first; skip every completed item.
               Rewrite it after each completed item, not at the end.
Budget:        <lane's share of the release budget; warehouse_spend setting>
Flat:          Do not spawn sub-agents. If the work is bigger than one lane,
               report that and stop — the orchestrator splits it.
Status:        Do not write status.md or execution_log.md. The orchestrator
               writes them from your state file.
Report:        Report once, at completion, at a stall, or when you hit a
               decision you cannot make. No running commentary.
```

## Report-once protocol

Progress lives in state files; the conversation gets **terminal reports only**
— a lane reports when it completes, stalls, or hits a decision it cannot make,
never a running commentary. The orchestrator reads progress from state files
(and answers the director from them); it does not poll lanes with "how is it
going" messages, and lanes do not emit unprompted status updates that bury the
signal. Observed failure: polling chatter between the orchestrator and busy
lanes consumed context and tokens while adding nothing the state files did not
already hold.

Outward-facing publishes (a PR raise, a client post, a merged-state update) are
**`&&`-gated chains**: every local step must succeed before the publish step
runs — build `&&` compare `&&` parity `&&` raise — so a failed precondition
stops the chain instead of publishing a claim the evidence does not back. A
publish that happened is reported once, with its reference; it is never
re-narrated.

## The consolidation and backstop pass (mandatory)

After lanes report, and **before the orchestrator reports a lane's artifact as
ready for a ruling**, it runs a consolidation pass over their output:

1. The artifact files the lane claimed exist on disk.
2. Validate ran for the artifact, and its recorded result matches what the
   lane reported. (`specs/utils/auto_validate.md` means most generates have
   already chained into validate; a missing validate result is a finding, not
   a gap to fill silently.)
3. `status.md` was not written by the lane. A lane that wrote it is a rule-6
   violation: report it, and reconcile the file from the lane's state file
   rather than trusting the lane's edit.
4. For warehouse-touching work: re-check build results against the warehouse,
   not the lane's claim, and scan for the engagement's documented traps.
5. Spot-check a sample at full depth.

This pass is not optional overhead. The controlled contrast that justifies it:
identical lane briefs run on a lower model tier produced format-faithful output
in which the consolidation pass caught two hard build failures and eight
recurrences of a documented trap. Backstop passes stay in the template
regardless of which model runs the lanes; the model choice changes how much the
backstop finds, not whether it runs.

## Rulings

Every director decision is appended to
`.wire/releases/<release>/decisions.md` **the moment it is given**, not when it
is used, with a structured header that `specs/utils/precondition_gate.md` can
read:

```markdown
## R-3 | 2026-09-02 14:12 | Mark Rittman | skip business_rules
Applies to: conceptual_model.depends_on.business_rules (advisory)
Ruling: skip. Reason: agree metric definitions at kickoff, 2026-09-09.
```

Fields:

| Field | Meaning |
|---|---|
| `R-<n>` | Ruling id, sequential within the release. Cited by the execution-log override row and by `runnable_set`. |
| Timestamp | `YYYY-MM-DD HH:MM`, when the director gave it. |
| Name | The director's name. A ruling is always attributable. |
| Summary | Four or five words, enough to find it. |
| `Applies to:` | `<artifact>.depends_on.<dep_artifact>` plus `(advisory)` or `(decision)`. An advisory gate ruling must name both artifacts, so a ruling for one artifact cannot satisfy another's gate. |
| `Ruling:` | The decision, then `Reason:` and the reason in the director's own words. |

Rulings survive session ends because they are in the file, not in conversation
memory (rule 4's principle applied to the director's own decisions).

**Advisory gates only.** A ruling can satisfy an advisory precondition. A
blocking precondition is never satisfied by a ruling: the existing override
path in `specs/utils/precondition_gate.md` Step 3 (a real name and a real
reason, recorded) is the only way past one, and the director supplies both in
person.

## Review as a ruling

A review edge is never `runnable`. At a review edge the orchestrator presents
the artifact summary, the validate result, and the external context the review
spec already gathers (Fathom, Confluence, the document store), then asks the
director for one of three answers:

| Answer | What runs | What is recorded |
|---|---|---|
| **Approve now** | `/wire:<artifact>-review <release>` | Approval under the director's name, through the review spec's normal path |
| **Changes** | `/wire:<artifact>-generate <release>` again | The change list in `decisions.md`, then the re-generate |
| **Park for client sign-off** | Nothing | A `parked_decisions` entry naming who is expected to sign off. No review row is written. |

Park is not a deferral of the record; it *is* the record. It is visible in
`status.md` and reported at the start of every session until it is resolved.

## Budget

An optional `budget:` block in `status.md`, limited to what an agent can
observe and enforce:

```yaml
budget:
  lanes_max: 2                 # concurrent lanes; default 4
  model_tier: default          # default | economy (lane model override)
  warehouse_spend: none        # none | estimate_required | cap:<amount>
  stop_at: decisions           # decisions | phase_end | never
  set_by: "Mark Rittman"
  set_at: "2026-09-02"
```

The director sets it in prose ("two lanes, nothing against a warehouse, stop at
decisions") and the orchestrator writes the block, echoing back what it wrote.

| Field | Enforcement |
|---|---|
| `lanes_max` | `specs/delegate.md` refuses to dispatch beyond it. Default 4 when the block is absent. |
| `model_tier` | `economy` passes a lower-tier model override to lane dispatch. The consolidation pass runs either way. |
| `warehouse_spend: none` | `delegate.md` refuses any lane whose command queries a warehouse. |
| `warehouse_spend: estimate_required` | The cost governance rules below apply to every such lane. |
| `warehouse_spend: cap:<amount>` | As `estimate_required`, plus: a lane whose estimate would take the release past the cap is not dispatched; it becomes a parked decision. |
| `stop_at: decisions` | The orchestrator stops at the first parked decision and reports. |
| `stop_at: phase_end` | It continues past parked decisions on other artifacts until the phase has no runnable work left. |
| `stop_at: never` | It runs until nothing is runnable. Parked decisions still park; they just do not stop the other lanes. |

Token and API spend are not observable in-session and are out of scope. The
budget covers lanes, models and warehouse spend only.

### Cost governance

Where `warehouse_spend` is `estimate_required` or a cap:

- **The dry-run bound is the authorisation figure.** A build or comparison
  authorises the cost its dry-run estimated; the actual is recorded next to it.
  An overrun (actual above the authorised estimate) is **disclosed in the
  lane's report**, never silently absorbed — repeated overruns mean the
  estimation method is wrong, which is itself a finding.
- **Views and external tables are estimated from object sizes, never a 0-byte
  dry-run.** A dry-run against a view or an external (e.g. Iceberg/BigLake)
  table can report 0 bytes while the real scan bills the full underlying
  object. Estimate from the referenced objects' storage metadata instead, and
  treat a 0-byte estimate on a non-trivial object as "unknown", not "free".
  Observed failure: an unguarded build day billed four figures, with one model
  accounting for a mid-three-figure scan a 0-byte dry-run had waved through.
- **Shared-credential attribution by destination dataset.** When several lanes
  run under one service account, attribute spend by each job's destination
  dataset (which rule 3's tree ownership makes unambiguous), so the per-lane
  budget lines stay meaningful under a shared credential.

## Contention rules

- **Worktree-per-branch, never the main checkout.** A lane that needs a branch
  checkout works in its own `git worktree`; the main delivery checkout is never
  switched under a running set of lanes. Observed failure: a branch switch in
  the shared checkout changed every other lane's view of the tree mid-run.
- **Acquire-per-build locks, released between builds.** A build lane holds its
  build lock for one build and releases it before its next item, rather than
  holding it for the lane's lifetime — other lanes' occasional builds
  interleave instead of starving.
- **File-scoped commits only.** A lane commits exactly the files it owns (rule
  3), named explicitly — never `git add -A` / `git commit -a`, which under
  concurrent lanes commits other lanes' in-flight work. Observed failure: a
  broad commit from one lane swept up another's half-written state file and
  corrupted both lanes' resume points.

## The release claim

`status.md`'s `agents` block carries the claim. The orchestrator writes it when
it takes a release on, and refreshes `last_write` after every write to
`status.md`:

```yaml
agents:
  mode: orchestrated
  coordinator_session:
    user: "Mark Rittman"
    session_id: "<claude session id>"
    branch: "feat/03-store-dashboards"
    claimed_at: "2026-09-02 14:05"
    last_write: "2026-09-02 15:40"
  last_orchestrated: "2026-09-02 15:40"
  active_sessions: []
  completed_sessions: []
```

**Claim resolution**, run before any dispatch:

| Claim state | Resolution |
|---|---|
| No `coordinator_session`, or it is `null` | Claim it. Write the block and proceed. |
| Claim held by **this** user and session | Resume. Proceed. |
| Claim held by this **user**, a different session | Resume, and rewrite `session_id` to this session. One person cannot contend with themselves; the older session is gone or idle. |
| Claim held by **another** user, `last_write` within 30 minutes | Ask. Offer: join as reviewer (read and rule, no dispatch), or move to another release. Do **not** dispatch. |
| Claim held by another user, `last_write` older than 30 minutes | Ask. Offer: take over (the stall rule), join as reviewer, or move. Taking over rewrites the claim and says whose it was. |

The 30-minute figure is the same stall threshold lanes use, for the same
reason: a session that has not written for half an hour is not mid-flight.

**One driver per release.** More than one person works at the engagement level:
different releases, different branches. A second person on the same release is
a reviewer. If a release must genuinely be split between two people, the second
is a **human lane**: they own a named tree, run in "you drive" mode scoped to
it, and their work returns through a PR the coordinating session merges and
records. The human lane obeys rules 3 and 6 like any other lane — a named tree,
and no `status.md` writes; the coordinating session records the merge.

**Sessions end.** No long-running session is assumed. Lanes die with the
session that spawned them; the resume contract makes that cost at most the
in-flight item. A new session re-reads state, resolves the claim (its own user,
so it resumes), reads the parked decisions and the lane state files, and
continues. Work that must run unattended is a scheduled routine or a CI job,
not a lane.

## Parked decisions

`status.md` carries a list, not a single `paused_at` value:

```yaml
parked_decisions:
  - id: PD-1
    artifact: data_model
    kind: review
    question: "Approve now, or park for client sign-off?"
    parked_at: "2026-09-02 16:02"
    awaiting: "Retail ops lead"
  - id: PD-2
    artifact: data_model
    kind: registry_proposal
    question: "Adopt retail vertical baseline: adopt / adapt / decline"
    parked_at: "2026-09-02 16:04"
```

`kind` is one of `review`, `ruling`, `registry_proposal`, `budget`,
`safety_gate`. `awaiting` is optional and names the person or role expected to
answer; absent means the director.

**The first line of every session in orchestrated mode is the count of parked
decisions and their questions.** A parked decision is cleared by a ruling: the
ruling is written to `decisions.md` (see "Rulings") and the entry is removed
from the list in the same write.

The single `agents.paused_at` field is superseded by this list. Readers that
still expect `paused_at` treat a non-empty `parked_decisions` list the same way
they treated a set `paused_at`.

## Co-existence with typed commands

There is no global switch. Four controls, matching surfaces Wire already uses:

| Level | Control | Effect |
|---|---|---|
| In the conversation | "You drive" hands control back for the rest of the session. "I'll drive", or any directive, hands it forward. | Both are recorded in `execution_log.md` as a `mode` row. Conversation state beats engagement state, for this session only. |
| Per command | Typing a `/wire:` command yourself. `--inline` already turns off delegation for one run. | Always works. The orchestrator re-reads state afterwards and continues from it. |
| Per engagement | `orchestration.mode: orchestrated \| manual` in `.wire/engagement/context.md`. | `manual` disables dispatch behaviour and reverts `/wire:start` to print-only. |
| Per runtime | Gemini CLI has no skills or agents, so it stays command-driven. | Gemini users get the runnable set, the claim, the log columns and the active-release rule through the command changes. |

**Precedence**, highest first:

1. Runtime: Gemini CLI resolves to `manual` regardless of anything else.
2. Conversation: "you drive" for the rest of this session.
3. Engagement: `orchestration.mode` in `context.md`.
4. Default: `orchestrated` on Claude Code.

**Collision guard.** A command started by hand on a release with a live claim
by another session, or on an artifact tree owned by a live lane, warns before
proceeding and names the holder. It does not block — a person typing a command
is exercising control, and the warning is what they need, not a refusal.
