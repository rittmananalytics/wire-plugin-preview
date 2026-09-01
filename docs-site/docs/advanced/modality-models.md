---
sidebar_position: 11
title: Modality models as an input
---

# Reading a Modality model into the design artifacts

[Modality](https://github.com/rittmananalytics/modality) is the tool the team uses to capture and model client data. It writes models as `.mml` text files into the client's own repository.

Wire's design commands derive their content from approved requirements and whatever sits in `artifacts/`. A model that already existed in Modality was invisible to them, so the entities got typed in again by hand and then diverged. This closes that.

## Linking a model

```bash
/wire:utils-modality-link <release-folder> [--path <dir>]
```

Finds `modality_project.yaml` (an explicit `--path` first, then `client_repo_local_path` for a dedicated client repo, then the Wire repo), reports what the model actually contains, and records `model_source: modality` and `modality_path` on the release.

The report includes one line that matters more than the counts: **where cardinality is readable from**. See below.

A model with zero conceptual entities is a scaffold rather than a model, and the command refuses to link it, because the design commands would produce empty documents.

To unlink, set `model_source: derived`. Nothing is deleted, and documents already generated keep their content and their citations.

## What each command reads

| Command | Takes from the model |
|---|---|
| `conceptual_model-generate` | Entities, attributes and domains for Section 1; relationships and cardinality for Section 2's ERD; `description` and `business_logic` for Section 3 |
| `logical_model-generate` | Per-entity sources from `sources.mml`; cardinality and foreign keys for Section 3; `entity_resolution` blocks for Section 4 |
| `pipeline_design-generate` | The source list and per-entity landing tables. Replication tool and schedule are not in MML and are still asked for |

The model does not replace the requirements. Both are read, and the difference between them is a finding: an entity in the model but not in the requirements is excluded with the reason "in the Modality model, not in requirements scope"; an entity in the requirements but not in the model becomes an open question. Neither is resolved silently.

Every value taken from the model cites the `.mml` file it came from.

## The two vocabularies

Modality's specification and its application export disagree, and both produce files in the wild. This is the thing to know about reading MML.

| | Specification | Application export |
|---|---|---|
| Written by | The MML authoring skill, and hand-authored files | Modality's own export |
| Cardinality | On the conceptual `relationship` block, as `type = "one-to-many"` | A separate `logical_relationship` block |
| Entity `type` | `entity`, `derived`, `aggregate` | `entity`, `metric`, `derivation` |
| Inline verbs | `belongs-to`, `has-many`, `leads-to`, `related-to` | `belongs-to`, `contains`, `leads-to`, `derived-from`, `parent-of` |
| `entity_resolution` | Not defined | Written |

A reader that handles one of these gets the other wrong, and quietly. So Wire accepts both, and resolves cardinality in a stated order:

1. A `logical_relationship` block for the pair
2. A `relationship` block for the pair, where `type` is a cardinality
3. An inline verb, but only where the verb implies cardinality: `has-many`, `contains` and `parent-of` give one-to-many; `belongs-to` gives many-to-one

Only when all three yield nothing is the cardinality `undetermined`. Verbs that are relationship kinds rather than cardinality (`leads-to`, `related-to`, `derived-from`) are undetermined by nature, and recorded as such rather than raised as a modelling failure.

## What absence means

Wire does not treat a silent file as a modelling failure, because the specification does not define every block the export writes.

| Absent | Reading |
|---|---|
| `logical_relationships.mml` | Fall through to `relationship`, then the inline verb |
| `entity_resolutions.mml` | **Never** a coverage failure. The specification does not define the block, so a spec-written model never has one. A multi-source entity with no resolution becomes an open question on the logical model |
| `sources.mml` | Sources are asked for instead |
| `physical/schema.mml` | Expected, and out of scope: MML writes one flat table per entity with `uuid` keys, and Wire's warehouse layer is a different design that `data_model` owns |

## The `modality_coverage` check

Run by the three validate commands when `model_source: modality`, and reported as SKIP with the reason otherwise, never as PASS.

1. Every conceptual entity in the `.mml` files appears in the Wire document, or is explicitly excluded **with a reason**.
2. Every entity in the Wire document maps to an MML entity or to a requirement.

Entities typed `metric` are outside direction 1: they are semantic-layer measure candidates, not conceptual entities.

## Out of scope

Data products, exposures, estimates and roadmap blocks are not read. The physical model is not read. There is no write-back: when the model is authored in Modality, Modality is where it is maintained.
