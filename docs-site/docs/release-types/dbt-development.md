---
sidebar_position: 6
title: dbt Development
---

# dbt Development Release

Use this when data is already in the warehouse (e.g. via Fivetran, Stitch, or manual loads) and you need to build or extend the dbt transformation layer.

**In-scope artifacts**: `requirements`, `conceptual_model`, `data_model`, `dbt`, `data_quality`

## Workflow

```
/wire:new                                         # release_type: dbt_development

/wire:business-rules-generate <release-folder>    # Optional, new in 4.0 — agree what the numbers mean first
/wire:business-rules-validate <release-folder>
/wire:business-rules-review <release-folder>

/wire:requirements-generate <release-folder>      # Focus on transformation requirements
/wire:requirements-validate <release-folder>
/wire:requirements-review <release-folder>

/wire:conceptual_model-generate <release-folder>
/wire:conceptual_model-validate <release-folder>
/wire:conceptual_model-review <release-folder>

/wire:data_model-generate <release-folder>        # Read existing source schema + requirements
/wire:data_model-validate <release-folder>
/wire:data_model-review <release-folder>

/wire:dbt-generate <release-folder>
/wire:dbt-validate <release-folder>
/wire:utils-run-dbt <release-folder>
/wire:dbt-review <release-folder>

/wire:data_quality-generate <release-folder>
/wire:data_quality-validate <release-folder>
/wire:data_quality-review <release-folder>

/wire:archive <release-folder>
```

:::info[Tutorial available]

A worked example of a dbt Development engagement — using a fictional client scenario with realistic command output, agent delegation, and reviewer decisions — is available in the [Tutorial: dbt Development](../tutorials/dbt-development).

:::


**Tips for dbt-only releases**:
- Add any existing dbt project files (existing `schema.yml`, source definitions, SQL examples) to `requirements/` before running `data_model:generate` — the AI will use them to understand the existing model structure and extend it correctly
- Store SQL examples from the source database (schema introspection results, sample queries) so the AI understands actual column names and types

> **Tip**: Run `/wire:playbook-generate <release-folder>` after requirements are approved.

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

**The gate is advisory.** ``data_model-generate`` warns when the register has not been
reviewed, asks for a one-line reason, records it as an `advisory_skip`, and
proceeds. Skipping is a real choice; what matters is that the choice is visible.

A transformation-only release is the case where this matters most: the models being
built or rebuilt are where a definition becomes permanent.

Full reference: [Business rules discovery](../advanced/business-rules.md).
