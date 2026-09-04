---
sidebar_position: 2
title: The Release Director Model
---

# The Release Director Model

**Introduced**: v4.0.0

Wire ships 313 commands. Two usage reviews found that the command surface, not
the method, is what stops people using it.

| Observation | Where |
|---|---|
| Orientation commands (`start` 35 runs, `status` 19) were a third of all 182 executions | Migration engagement review, §3 |
| 969 of 1,646 free-form prompts were conversation, not commands | Second engagement review, §9 |
| Two client-side developers made 34 commits touching Wire artifacts and ran zero `/wire:` commands | Second engagement review, §9 |
| One client-side user ran `session-plan` 11 times and nothing else, on work `data_model-generate` and the `dbt-*` commands cover | Second engagement review, §8 |

On the migration engagement, the pattern that worked was not more commands. One
consultant directed in prose while an agent ran the commands. Typed `/wire:`
prompts fell from 4.98% to 0.91% of all prompts, while Wire executions per typed
prompt rose from 1.10 to 2.56.

From v4.0.0 that is how Wire works by default on Claude Code, on every release
type.

## What actually changes

**Nothing about the record.** Every step still runs the real Wire command, so
`status.md`, `execution_log.md`, the precondition gate, auto-validate, telemetry
and the artifacts on disk are identical whether a command was typed or
dispatched. What changes is who types.

## The three tiers

```mermaid
flowchart TB
    T1["<b>TIER 1 — RELEASE DIRECTOR</b><br/>one human per release<br/><br/>Client communications · Rulings and waivers<br/>Approval gates · Judgment catches<br/>Lane-count and budget decisions"]:::director

    T2["<b>TIER 2 — ORCHESTRATING SESSION</b><br/>one per release<br/><br/>Reads the release-type graph for what is runnable<br/>Dispatches and monitors lanes<br/>Single writer of status.md and the execution log<br/>Consolidation and backstop pass<br/>Records rulings in decisions.md the moment they land"]:::orch

    subgraph T3["TIER 3 — LANE AGENTS · flat, one scoped task each, own tree, own state file"]
        direction LR
        L1["Lane 1<br/>conceptual_model"]:::lane
        L2["Lane 2<br/>workshops"]:::lane
        L3["Lane 3<br/>seed_data"]:::lane
        LN["Lane N<br/>…"]:::lane
    end

    T1 <-->|"Down: intent, rulings, waivers, approvals<br/>Up: judgment catches, parked decisions"| T2
    T2 <-->|"Down: lane brief (state file, tree ownership, budget)<br/>Up: report once — complete, stalled, or needs a ruling"| L1
    T2 <--> L2
    T2 <--> L3
    T2 <--> LN

    classDef director fill:#181B25,stroke:#181B25,color:#FFFFFF
    classDef orch fill:#1a3a5c,stroke:#4a90d9,color:#fff
    classDef lane fill:#2d4a1e,stroke:#6abf4b,color:#fff
```

| Tier | Who | Duties |
|---|---|---|
| **Release director** | One human per release | States intent, makes rulings, approves at gates, sets the budget. Decides; does not execute. |
| **Orchestrating session** | One session per release | Computes what is runnable, dispatches lanes, single writer of `status.md` and `execution_log.md`, runs the consolidation pass, records rulings the moment they land. |
| **Lane agents** | 1 to 12 concurrent, flat | One scoped task each, in its own tree, with its own state file. Report once. |

The rules are specified in `specs/utils/director_operating_model.md`. The
`platform_migration` fleet model (`specs/utils/migration_fleet.md`) is now the
migration profile of it, and migration behaviour is unchanged.

## A worked session: `dashboard_first` from an empty repo

What the director said, and what Wire ran.

| You say | Wire does |
|---|---|
| "New engagement for Northwind Retail, store performance dashboards. SOW in `docs/sow.pdf`. No warehouse access for two weeks. Two lanes max, nothing against a warehouse, stop at decisions." | Reads the SOW, proposes `dashboard_first` / `seeded` **with the reason**, shows one confirmation block, asks the one open question. Runs `/wire:new`. Writes the budget block. |
| "Confirm. Skip business rules, agree at kickoff." | Writes ruling R-1 to `decisions.md`. |
| *(nothing — Wire continues)* | `requirements-generate` runs; auto-validate follows. One report: 14 requirements, PASS, 2 clarification markers, plus the client call that covers them. Frames the gate: approve now, or park. |
| "Approve internally, carry the markers to kickoff, prepare a workshop pack." | `requirements-review` records the approval. `workshops-generate` dispatched as a lane. |
| *(nothing)* | Requirements approval releases two: `conceptual_model` as a lane (its advisory business-rules gate satisfied by R-1, recorded), `mockups` in the foreground with you, because it needs your input. |
| "Approved." | `mockups-review`, then `viz_catalog-generate`. Lane report: conceptual model, 7 entities, PASS. |
| "Go. Report when done." | `data_model` and `seed_data` as two lanes, within budget. The data model lane parks on the registry proposal (PD-1). |
| "Adapt, inventory out of scope." | Records the ruling, clears PD-1. |

**Session close.** 14 Wire runs in the execution log. 0 typed commands. 9
director messages, 7 of them decisions a consultant makes anyway. Two parked
decisions open the next session.

## What is runnable

`specs/utils/runnable_set.md` reads the release-type YAML, the active profile,
`status.md` and `decisions.md`, and returns one state per artifact:

| State | Meaning |
|---|---|
| `runnable: generate` | The generate command can run now. |
| `runnable: validate` | Only where the generate command carries `auto_validate: false`. Otherwise validate already ran with generate, so a non-pass means re-generate. |
| `parked: needs ruling` | A director decision is needed. Every review edge is here. |
| `blocked: <unmet precondition>` | A blocking `depends_on` entry is unmet, named with its actual recorded value. |
| `not applicable` | Not part of this release under the active profile. |
| `complete` | Every present lifecycle step is done. |

`/wire:start`, `/wire:delegate`, `/wire:autopilot` and the orchestrating session
all read the same computation, so they cannot disagree about what comes next.
Autopilot used to keep its own copy, which is how its `full_platform` sequence
silently lost the `orchestration` artifact.

**Parallelism comes from the graph, not from item counts.** Two runnable
artifacts with no dependency between them are two lanes, up to
`budget.lanes_max`. An **interactive** artifact — one whose generate spec waits
on you, like `mockups` in `dashboard_first` — runs in the foreground, never as a
lane.

## Reviews are never run without a ruling

A review edge is never `runnable`. At a review the orchestrator presents the
artifact summary, the validate result, and the meeting or document-store context
the review spec already gathers, then asks for one of three:

| Answer | What runs | What is recorded |
|---|---|---|
| **Approve now** | `/wire:<artifact>-review` | Approval under your name, through the review spec's normal path |
| **Changes** | `generate` again | The change list in `decisions.md`, then the re-generate |
| **Park for client sign-off** | Nothing | A `parked_decisions` entry naming who is expected to sign off. No review row is written. |

## Parked decisions

`status.md` carries a list, not a single `paused_at` value — a release can be
waiting on more than one thing at once:

```yaml
parked_decisions:
  - id: PD-1
    artifact: data_model
    kind: review
    question: "Approve now, or park for client sign-off?"
    parked_at: "2026-09-02 16:02"
    awaiting: "Retail ops lead"
```

`kind` is one of `review`, `ruling`, `registry_proposal`, `budget` or
`safety_gate`. **The first line of every session is the count of these and their
questions.**

## Rulings

A decision goes into `decisions.md` **the moment it is given**, not when it is
used, in a form the precondition gate reads:

```markdown
## R-3 | 2026-09-02 14:12 | Mark Rittman | skip business_rules
Applies to: conceptual_model.depends_on.business_rules (advisory)
Ruling: skip. Reason: agree metric definitions at kickoff, 2026-09-09.
```

An **advisory** gate whose ruling names both this artifact and this dependency
is satisfied without asking again, and the override log row cites the ruling id.

Three things a ruling cannot do:

- **Satisfy a blocking gate.** Ever. The recorded override in
  [the precondition gate](../getting-started/core-concepts#the-precondition-gate)
  — a person's name and reason, given at the time — is the only way past one.
- **Cover a different artifact's gate.** A decision to skip `business_rules`
  before `conceptual_model` says nothing about skipping it before `data_model`.
- **Waive by saying "wait".** A ruling that says to wait is a decision to stop.

A ruling in the file survives the session that gave it. One held in conversation
memory does not.

## Budget

Optional, in `status.md`. You set it in prose; Wire writes the block.

```yaml
budget:
  lanes_max: 2                 # concurrent lanes; default 4
  model_tier: default          # default | economy
  warehouse_spend: none        # none | estimate_required | cap:<amount>
  stop_at: decisions           # decisions | phase_end | never
  set_by: "Mark Rittman"
  set_at: "2026-09-02"
```

| Setting | Effect |
|---|---|
| `lanes_max` | `/wire:delegate` refuses to dispatch beyond it. Work queues in the runnable set's order. |
| `warehouse_spend: none` | Refuses any lane whose command queries a warehouse, and says which and why. It never silently drops them. |
| `warehouse_spend: estimate_required` | The dry-run bound is the authorisation figure; overruns are disclosed in the lane's report. |
| `stop_at` | Where to stop: at the first parked decision, at the end of the phase, or not at all. |

An absent block means the defaults, not a budget of zero. Token and API spend
are not observable in-session and are out of scope.

## The lane contract

Every dispatch carries it, and every agent definition restates it.

| Rule | Why (the observed failure) |
|---|---|
| Write progress to your state file after **each** completed item | Two hard usage-limit outages resumed with near-zero loss only because every lane had incremental state |
| Write only inside the directories the brief names; commit exactly those files | A broad commit from one lane swept up another's half-written state file and corrupted both resume points |
| **Do not write `status.md` or `execution_log.md`** | 46 commits in 24 hours across four people; one merge silently discarded 54 models of completed work |
| Do not spawn sub-agents below yourself | Nested fan-out caused two hard usage-limit outages in one day |
| Report once — complete, stalled, or needs a ruling | Polling chatter burned context and tokens while the state files already held the answer |

The third rule is the change for linear release types. Outside orchestrated
mode, a delegated subagent still updates `status.md` itself, exactly as in 3.x.

**The consolidation pass is mandatory.** Before the orchestrator reports a
lane's artifact as ready for a ruling, it checks the files exist, validate ran
and its result matches the lane's claim, `status.md` was not written by the
lane, and warehouse results are re-checked against the warehouse rather than the
lane's word.

## The release claim

`status.md` records who is driving a release:

```yaml
agents:
  mode: orchestrated
  coordinator_session:
    user: "Mark Rittman"
    session_id: "<claude session id>"
    branch: "feat/03-store-dashboards"
    claimed_at: "2026-09-02 14:05"
    last_write: "2026-09-02 15:40"
```

| Claim state | What a second session does |
|---|---|
| None | Claims it and proceeds |
| Yours, this session or an older one | Resumes. One person cannot contend with themselves. |
| Another user, written within 30 minutes | **Does not dispatch.** Offers join as reviewer, or move to another release. |
| Another user, no write for over 30 minutes | **Does not dispatch.** Offers take-over, join, or move. |

A person typing a single command is a different case: they get a warning naming
the holder, and proceed. The claim stops agents colliding, not people working.

**One driver per release.** More than one person works at the engagement level:
different releases, different branches. A second person on the same release is a
reviewer, or a **human lane** — they own a named tree, work in "you drive" mode
scoped to it, and their work returns through a pull request the coordinating
session merges and records.

**Sessions end.** No long-running session is assumed. Lanes die with the session
that spawned them, and the resume contract makes that cost at most the in-flight
item. Work that must run unattended is a scheduled routine or a CI job, not a
lane.

## Which release you are working on

With two releases in flight, the old rule — most recently modified — silently
picked whichever was touched last. The order is now explicit:

1. A release named in your message or the command argument.
2. The release matching the current git worktree or branch.
3. The only release with a `status.md` write in the last 7 days.
4. Otherwise **ask**, listing the candidates. Never guess between two.

Recommended: one git worktree and one session per active release. Switching
context is switching terminal.

## Turning it off, per session or per engagement

No global switch. Four controls, resolving highest first:

| Level | Control | Effect |
|---|---|---|
| Runtime | Gemini CLI has no skills or agents | Resolves to `manual`, whatever anything else says |
| Conversation | Say **"you drive"** | `manual` for the rest of this session. "I'll drive", or any directive, hands it back. Both recorded as a `mode` row in the log. |
| Engagement | `orchestration.mode: manual` in `.wire/engagement/context.md` | Restores pre-4.0 behaviour exactly, including `/wire:start` printing the next action rather than offering to run it |
| Default | — | `orchestrated` on Claude Code |

Typing any `/wire:` command mid-session always works. The orchestrator re-reads
state afterwards and continues from it. **The command name is printed before
every run**, so a consultant who has never typed one still learns what the thing
they approved is called.

## Attribution: telling typed from dispatched

This model drives typed-command counts down by design, and typed-prompt counts
were the adoption measure. Two changes keep it readable.

`execution_log.md` rows gain two columns:

```markdown
| Timestamp | Command | Result | Detail | By | Session |
```

`By` is the git user. `Session` is `typed`, `orchestrator [id]`, a lane label
(`dbt-developer [staging 1/2]`), or `autopilot`. Rows written before v4.0.0 have
four data columns; they stay valid, are never rewritten, and an old row is
recorded as unknown rather than assumed to be typed.

Telemetry replaces the old hardcoded `autopilot: "false"` property with
`invoked_by`, carrying the same four values, read from the `WIRE_INVOKED_BY`
environment variable and defaulting to `typed`.

## What existing engagements get

`/wire:upgrade` adds `parked_decisions`, the expanded `agents` block and
`orchestration.mode` with defaults, and writes the profile field explicitly
where a release type has one and the release has been running on the default
implicitly. It deliberately does **not** write a `budget` block: an absent block
means no budget was set, and writing one would claim a decision nobody made.

Nothing changes for an existing engagement until a director gives a directive.

## Where the rules live

| Rule | Spec |
|---|---|
| Operating model, lane contract, claim, budget, parked decisions, co-existence | `specs/utils/director_operating_model.md` |
| What is runnable, and what runs in parallel | `specs/utils/runnable_set.md` |
| Rulings against advisory gates | `specs/utils/precondition_gate.md` Step 2a |
| Log columns, ordering, legacy rows | `specs/utils/execution_log.md` |
| `platform_migration` lane roster and stage ladder | `specs/utils/migration_fleet.md` |
| The orchestrating session in Claude Code | `wire/skills/release-director/SKILL.md` |

Each of the first four has a behavioural test — see [Testing](../reference/testing).

## See also

- [Tutorial: Looker to Omni Migration](../tutorials/looker-to-omni-migration): a batched release type run under this model, with every command Wire runs named
- [Wire Agents](./wire-agents) — the thirteen specialists that run as lanes
- [Wire Autopilot](./autopilot) — the fully autonomous end of the range
- [Core Concepts](../getting-started/core-concepts) — the precondition gate, auto-validate, profiles
