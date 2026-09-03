---
sidebar_position: 13
title: Business rules discovery
---

# Business rules discovery

Wire had no step that established what a metric means before the build started. `requirements-generate` reads documents. `workshops-generate` runs *after* requirements and only resolves clarification markers already written into them. Neither looked at the data, and neither looked at the competing definitions sitting in the legacy systems.

So a definition disagreement had nowhere to surface, and the first place it could appear was a number that did not tie in QA.

## The case it exists for

A requirements document asked for "Gross Sales Order Online" and a channel breakdown including the in-store order channel, and listed "standardised metric definitions" as a success factor. It never said whether in-store orders were inside the figure, or whether returns were deducted.

Eleven months later the number did not match the legacy dashboard. Nobody had been wrong. Nobody had been asked.

## Running it

```bash
/wire:business-rules-generate <release-folder> [--domain <name>] [--import <path>]
/wire:business-rules-validate <release-folder>
/wire:business-rules-review   <release-folder>
```

Available as an optional first phase on `full_platform`, `dbt_development`, `dashboard_first`, `dashboard_extension`, `pipeline_only` and `platform_migration`.

**One domain per run.** A register that tries to cover everything at once goes stale before it is agreed. `domains_covered` in `status.md` accumulates, and a later run appends rather than replacing.

`agentic_data_stack` does not get it: that release type already has `ads_metric-audit` plus `ads_governance-design`, which split find-conflicts from decide-conflicts between them.

## What a rule holds

| Field | Rule |
|---|---|
| `id` | `BR-n`, stable for the life of the register. Never renumbered, because the build cites it |
| `statement` | The rule in plain words, readable by whoever approves it |
| `variants[]` | Every competing definition, each with its `source` and `object`. A variant with no `object` does not enter the register |
| `disagreement` | What they actually differ on. Not "definitions vary" |
| `decision`, `approver`, `agreed_date` | The choice and who made it |
| `implemented_by[]` | The dbt models and LookML measures carrying this rule's id |
| `check` | The query that proves it |

## The four statuses

| Status | Meaning | Validate |
|---|---|---|
| `agreed` | Decided, with a named approver and a date | Needs an implementation once the release reaches development |
| `disputed` | Two or more variants, none chosen | Blocks review sign-off unless it has a named owner |
| `assumed` | Chosen without confirmation | Needs a confirmer and a `confirm_by` date, and **fails once that date passes** |
| `unknown` | Nobody has decided, no variant is authoritative | Never a failure on its own |

`unknown` passing is the whole point. A command that only records what it found cannot record the absence of a decision, and that absence is what the register exists to hold. It is also why the last attempt at this, a wiki page called Business Logic, sat empty: there was nowhere to write "we do not know".

## Reading systems Wire cannot read

dbt, LookML and `schema.yml` are text in a repository, so they are read directly. SAP BW, Hana SQL, SAC and Looker Studio are not, and pretending otherwise is how a register ends up covering only the easy systems.

```bash
--import <path>
```

Takes exported SQL or model text. Each definition it yields records `source`, `object`, `expression` **verbatim**, `export_date` and `exported_by`. An imported definition is a first-class variant. What it does not carry is freshness, so validate warns when an import is more than 90 days older than the register that cites it.

Where an export is illegible, the definition is recorded as `unknown` with the evidence attached and the person to ask. An invented expression is worse than a blank, because everything downstream treats it as fact.

## The gate is advisory, not blocking

Each of the six release types gains an advisory gate on its first design-phase artifact: `conceptual_model` for `full_platform`, `data_model` for `dbt_development`, `mockups` for `dashboard_extension`, and so on.

Advisory means the command warns, asks for a one-line reason, records an `advisory_skip` in `status.md` and the execution log, and proceeds.

That is deliberate. A hard gate on a team that already skips gates produces a bypass rather than a register. What matters is that a skip is *visible*: an omitted gate and an overlooked one look identical afterwards, and a logged skip does not.

## Reaching into the build

A dbt model or LookML measure that implements a rule cites it:

```yaml
models:
  - name: wh_commerce__sales_xa
    meta:
      wire_business_rule: BR-1
```

`business-rules-validate` then checks both directions: every `agreed` rule has an implementation once the release is building, and every citation names a rule that exists. A citation to a missing id usually means a rule was renumbered, which the register forbids.

`wire/scripts/lint_conventions.py` checks the citation format, at warning severity, and only where a citation is present, so a project that has not opted in is never flagged.

## Reconciliation, before the build rather than after

Every rule with a legacy variant gets a generated query comparing both readings against the legacy source, through the existing equivalency machinery. It runs at generate time.

A disputed gross sales rule therefore produces, on day one, the number each reading gives and which one matches the legacy dashboard. That is usually enough to settle the dispute without a meeting, and it is the same check QA would otherwise have run eleven months later.
