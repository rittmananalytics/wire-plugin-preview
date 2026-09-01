---
sidebar_position: 7
title: Dashboard Extension
---

# Dashboard Extension Release

Use this when the semantic layer already has the data, and you're adding new dashboards on top.

**In-scope artifacts**: `requirements`, `mockups`, `dashboards`, `uat`

## Workflow

```
/wire:new                                         # release_type: dashboard_extension

/wire:business-rules-generate <release-folder>     # Optional, new in 4.0
/wire:business-rules-validate <release-folder>
/wire:business-rules-review <release-folder>

/wire:requirements-generate <release-folder>      # Focus on dashboard/user requirements
/wire:requirements-validate <release-folder>
/wire:requirements-review <release-folder>

/wire:mockups-generate <release-folder>           # Wireframes for review with end users
/wire:mockups-review <release-folder>

/wire:dashboards-generate <release-folder>
/wire:dashboards-validate <release-folder>
/wire:dashboards-review <release-folder>

/wire:uat-generate <release-folder>
/wire:uat-review <release-folder>

/wire:archive <release-folder>
```

:::info[Tutorial available]

A worked example of a Dashboard Extension engagement — using a fictional client scenario with realistic command output, agent delegation, and reviewer decisions — is available in the [Tutorial: Dashboard Extension](../tutorials/dashboard-extension).

:::


**Tips**:
- Add existing LookML view files to `requirements/` before generating dashboards — the AI needs to know which dimensions and measures are available
- Screenshots of existing Looker explores also help

## Business rules discovery (optional first phase)

New in 4.0. `/wire:business-rules-generate` runs before design and establishes what
the numbers mean, one business domain at a time.

It reads the definitions that already exist — in dbt, in LookML, and through
`--import` from systems Wire cannot read such as SAP BW, Hana or SAC — then asks
the people who own the numbers to settle the ones that disagree. The output is a
register: one entry per rule, holding every competing definition with the file it
came from, what they disagree on, the decision, the named approver, and a
reconciliation query that runs at generate time rather than in QA.

A rule nobody has decided is recorded with status `unknown`, which passes
validate. That is the point of it: a register has to be able to say "nobody has
agreed whether in-store orders are in this figure", because that sentence is what
stops the number being wrong nine months later.

**The gate is advisory.** ``mockups-generate`` warns when the register has not been
reviewed, asks for a one-line reason, records it as an `advisory_skip`, and
proceeds. Skipping is a real choice; what matters is that the choice is visible.

Full reference: [Business rules discovery](../advanced/business-rules.md).
