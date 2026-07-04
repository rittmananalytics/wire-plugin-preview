---
description: Design dbt model structure
argument-hint: <project-folder>
---

# Design dbt model structure

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
wire_schema: "1.0"
command: generate
artifact: data_model
domain: design
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: dynamic
delegates_to:
  - utils/precondition_gate
description: Generate dbt data model specification and physical ERD
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Data Model Generate Command

Follow `specs/utils/data_designer_delegate.md` before executing the workflow below.

## Purpose

Generate the full dbt-layer data model specification — covering staging, integration, and warehouse layers — together with a **Physical Entity-Relationship Diagram (ERD)** as a Mermaid erDiagram showing every model with its columns, primary keys, foreign keys, and relationships. This is the primary input for dbt code generation.

The data model specification narrows the LLM's generation space for the dbt phase: every model name, column name, join path, surrogate key composition, and test definition is determined here, not during code generation.

## Usage

```bash
/wire:data_model-generate YYYYMMDD_project_name
```

## Prerequisites

**Default** (all project types except `dashboard_first`):
- `requirements`: `review: approved`
- `conceptual_model`: `review: approved` — provides the entity framework
- `pipeline_design`: `review: approved` — provides source table names and replication details

**Dashboard-first** (`dashboard_first` project type):
- `requirements`: `review: approved`
- `viz_catalog`: `generate: complete` — provides the measures, dimensions, and dashboard structure

## Workflow

### Step 1: Verify Prerequisites and Read Inputs

1. Read `.wire/<project_id>/status.md`
2. Read `project_type` from frontmatter
3. **If `dashboard_first`**:
   - Verify `requirements.review` is `approved` and `viz_catalog.generate` is `complete`
   - Read the following in order:
     - `requirements/requirements_specification.md`
     - `design/visualization_catalog.md` (measures, dimensions, dashboard structure)
     - `design/dashboard_spec.md` (dashboard purpose and layout)
   - Also read `artifacts/` for SOW and domain context
4. **Otherwise (default)**:
   - Verify all three default prerequisites are met. For each that is not:
     ```
     Error: [artifact] must be approved before data model generation.
     Run: /wire:[artifact]:review <project_id>
     ```
   - Read the following in order:
     - `requirements/requirements_specification.md`
     - `design/conceptual_model.md` (entities, relationships)
     - `design/pipeline_architecture.md` (source tables, staging model names)
4. Use Glob to find all files in `.wire/<project_id>/artifacts/**/*`
5. Read any source schema examples, existing dbt models, or SQL files in `artifacts/`

### Step 1.5: Check for a Canonical Vertical Match (Automatic, Advisory)

This step runs automatically on every engagement — there's no opt-in flag to set. It has three possible outcomes: a proposal to the practitioner, a silent skip, or (if declined) no effect on anything downstream. It can never fail the command and never blocks Step 2.

1. **Resolve the registry location, dev mode first:**
   - Check for `wire/data-model-registry/` in the repo root (present only when developing Wire itself, from `wire/scripts/sync-data-model-registry.sh`).
   - If not found, check `~/.wire/data-model-registry/` (present only if this consultant has personally run `/wire:utils-data-model-registry-setup` and has access to the private `wire-data-model-registry` repo).
   - If neither exists, **skip silently to Step 2** — no message, no note in the output spec. Most engagements and most consultants will land here; this is expected, not a degraded path.

2. **Resolve the vertical:**
   - Read `.wire/engagement/context.md`. If `data_model_registry.vertical` is already set to a non-null value (a consultant can set this by hand at any time), use it directly and skip to step 3 below — an explicit manual value always wins over inference.
   - Otherwise, infer a candidate from the requirements and conceptual model already read in Step 1: match the client's stated industry/domain language against the vertical index in the registry root (`education`, `insurance`, `manufacturing`, `marketplace`, `retail`, `subscription-commerce`). This is a judgment call, not a keyword lookup — read the vertical's own schema descriptions to judge fit, don't just string-match the industry name.
   - If no vertical is a plausible fit, **skip silently to Step 2** — do not ask the practitioner to pick one from a list just to confirm "none apply." A non-match is exactly as valid an outcome as a match, and is the majority case for most industries (there is, for instance, no `saas` vertical yet — flagged as a gap in the registry's own README).

3. **If a vertical is resolved (manual or inferred), propose it — never auto-adopt:**
   - Read every file in `<registry_root>/verticals/<vertical>/schemas/*.yml` and the entity files each one references in `<registry_root>/verticals/<vertical>/entities/*.yml`.
   - Check `<registry_root>/cross-vertical/schemas/*.yml` for anything thematically relevant to this client's actual sources — e.g. propose layering `ga4_ecommerce` on top of a `retail` match if the client uses GA4, or `multi_touch_attribution` if they run paid media across multiple channels. Respect each schema's `depends_on_schemas` field for sequencing (e.g. `ga4_ecommerce` depends on `event_tracking_and_sessionization`).
   - Present the matched schema(s) — entities, `standard_marts`, grain, relationships — as a **proposed starting structure**:
     ```
     Wire found a canonical data model that may fit this engagement: [vertical] — [schema_name].
     Standard marts: [list from standard_marts]
     Entities: [list]

     Use this as the starting structure for the data model? (yes / adapt / no)
     ```
     - **yes** — use the canonical entity list, grain, and naming as the baseline for Steps 2–7, adjusted only for this client's actual source systems and column names. Record `data_model_registry.vertical: <vertical>` in `.wire/engagement/context.md` if it wasn't already set, so `data_model-validate` can find it later.
     - **adapt** — ask which specific entities/marts to keep, drop, or rename; use the rest as-is. Record the vertical as above.
     - **no** — proceed with Step 2 onward exactly as if no match were found. Do not write `data_model_registry.vertical` to context.md — an explicit decline should not get treated as a manual override on the next run. Worth a one-line note in the spec that a canonical match existed but wasn't used (useful signal for the registry's own maintainers), but no other effect.
4. For every model in the final data model that maps to a canonical entity (whether adopted as-is or adapted), carry that entity's `generation_constraints` and `reference_implementation` pointer(s) forward into that model's spec entry in Step 5 (or Step 3 for staging). This is the only place the registry's worked-example SQL becomes reachable — `dbt-generate` reads `data_model_specification.md` as its primary input either way, so it inherits these pointers automatically; no changes to `dbt-generate` itself are needed. Treat `reference_implementation` strictly as a worked example to read and adapt, never to copy verbatim — the registry's own README is explicit that a specific `.sql` file is not reusable across clients, only the pattern it demonstrates is.

### Step 2: Define Source Definitions

For each source system in the pipeline design, produce a complete dbt `_sources.yml` specification:

```yaml
version: 2

sources:
  - name: <source_system>
    database: <bigquery_project>
    schema: <dataset_name>
    freshness:
      warn_after: {count: <N>, period: hour}
      error_after: {count: <N>, period: hour}
    tables:
      - name: <table_name>
        description: "<Table description>"
        loaded_at_field: <timestamp_column>
        columns:
          - name: <column_name>
            description: "<Column description>"
            tests:
              - not_null
              - unique   # only on PK columns
```

Freshness thresholds must be calibrated to the replication cadence from the pipeline design:
- Real-time / CDC sources: `warn_after: 30 minutes`, `error_after: 60 minutes`
- Daily batch sources: `warn_after: 25 hours`, `error_after: 49 hours`
- Manual/on-demand: no freshness check

Note any columns that are excluded for data governance reasons (e.g. free-text fields excluded for safeguarding). Document exclusions explicitly.

### Step 3: Define Staging Models

For each source table, define the staging model:

**Naming**: `stg_<source_system>__<entity_name>` (double underscore between source and entity)

**Materialisation**: `view`

**Tags**: `['staging', '<source_system>']`

For each staging model, specify:
- **Grain**: One row per what? (e.g. "one row per daily attendance mark per student per session")
- **Surrogate key**: `dbt_utils.generate_surrogate_key(['<id_columns>'])` → `<entity>_pk`
- **Column renames**: Source column name → standard column name (snake_case, business-meaningful)
- **Derived columns**: Any simple transformations applied at staging (e.g. `is_present = mark_code IN ('/', 'L')`)
- **Exclusions**: Any source columns excluded and why
- **Filters**: Any `WHERE` clause applied (e.g. `WHERE _fivetran_deleted = false`)
- **Tests**: `not_null` and `unique` on `<entity>_pk`; `not_null` on any non-nullable business keys

Use this template format:

```
### stg_<source>__<entity>
**Source**: `<source_system>.<table_name>`
**Grain**: One row per [description]
**Surrogate key**: `generate_surrogate_key(['<col1>', '<col2>'])` → `<entity>_pk`

| Source column | Staged column | Type | Notes |
|--------------|---------------|------|-------|
| <SourceCol> | <staged_name> | string/date/int/bool | |
| <SourceCol> | <staged_name> | timestamp | Renamed from Fivetran audit column |

**Derived columns**:
- `<derived_col>`: `<expression>`

**Filters**: `WHERE <condition>`

**Tests**: `not_null(entity_pk)`, `unique(entity_pk)`, `not_null(<business_key>)`

**Canonical entity** (only if sourced from the data model registry per Step 1.5): `<vertical>/<entity>` — constraints: [`generation_constraints` from the entity YAML] — reference: [`reference_implementation` path(s)]
```

### Step 4: Define Integration Models (if applicable)

For complex transformations that span multiple staging models but are not yet warehouse-level:

**Naming**: `int__<subject>__<description>` (e.g. `int__student__risk_signals`)

**Materialisation**: `view` (or `ephemeral` for simple pass-throughs)

Use integration models for:
- Cross-system joins (e.g. joining ProSolution student IDs to Focus student IDs)
- Business logic that derives flags or categorisations
- Pre-aggregations that feed multiple warehouse models

### Step 5: Define Warehouse Models

For each fact table, dimension table, and aggregate:

**Fact table naming**: `<entity>_fct` (e.g. `attendance_fct`, `pastoral_notes_fct`)
**Dimension table naming**: `<entity>_dim` (e.g. `student_dim`, `course_dim`)
**Aggregate naming**: `<subject>_<grain>` (e.g. `student_risk_summary`, `daily_attendance_summary`)

**Materialisation**: `table`

**Tags**: `['warehouse', 'fact']` or `['warehouse', 'dimension']`

For each warehouse model specify:
- **Grain**: One row per what?
- **Surrogate key**: composition and name (e.g. `attendance_pk`)
- **Foreign keys**: which dimension PKs are referenced (e.g. `student_fk → student_dim.student_pk`)
- **Measures**: numeric columns with business descriptions
- **Flags/indicators**: boolean derived columns with their logic
- **Audit columns**: `dbt_updated_at: current_timestamp()`
- **Canonical entity** (only if sourced from the data model registry per Step 1.5): `<vertical>/<entity>` — constraints: [`generation_constraints` from the entity YAML] — reference: [`reference_implementation` path(s)]

### Step 6: Define Seed Files

For any configurable business logic (thresholds, mappings, categorisations), specify seed files:

```
### seeds/<seed_name>.csv
**Purpose**: [What business rule this encodes]
**Columns**: [column names and types]
**Sample rows**: [3-5 representative rows]
**Used by**: [which models reference this seed]
```

Common seed patterns:
- Mark type mappings (e.g. attendance mark codes → present/absent/late)
- Risk score thresholds
- Category hierarchies
- Grade orderings

### Step 7: Generate Physical ERD

Produce a Mermaid `erDiagram` showing every warehouse model (and key staging models) with their columns, data types, primary keys, and foreign key relationships. Write this as a `## Physical Data Model` section within the data model specification document.

Use this template:

```
## Physical Data Model

```mermaid
erDiagram
    ENTITY_FCT {
        string entity_pk PK
        string dimension_fk FK
        date event_date
        int measure_column
        bool flag_column
        timestamp dbt_updated_at
    }
    DIMENSION_DIM {
        string dimension_pk PK
        string natural_key
        string display_name
        string category
        timestamp dbt_updated_at
    }
    AGGREGATE_SUMMARY {
        string summary_pk PK
        string dimension_fk FK
        int count_metric
        float rate_metric
        date summary_date
        timestamp dbt_updated_at
    }
    ENTITY_FCT }|--|| DIMENSION_DIM : "dimension_fk"
    AGGREGATE_SUMMARY }|--|| DIMENSION_DIM : "dimension_fk"
```
```

**ERD conventions**:
- Include all warehouse models (facts, dims, aggregates)
- Include staging models only if they are directly referenced by semantic layer (unusual)
- Mark surrogate keys as `PK`, foreign keys as `FK`
- Use types: `string`, `int`, `float`, `bool`, `date`, `timestamp`
- All relationship lines must correspond to a FK → PK join defined in the model specs above
- Relationship label = the FK column name

### Step 8: Write Data Model Specification Document

Write to `.wire/<project_id>/design/data_model_specification.md`:

```markdown
# Data Model Specification: [Project Name]

**Client**: [Client Name]
**Project ID**: [Project ID]
**Generated**: [Date]
**Version**: 1.0

## 1. Source Definitions
[_sources.yml content for each source system]

## 2. Staging Models
[Per-model spec as defined in Step 3]

## 3. Integration Models
[Per-model spec as defined in Step 4, or "Not applicable"]

## 4. Warehouse Models
[Per-model spec as defined in Step 5]

## 5. Seed Files
[Per-seed spec as defined in Step 6, or "Not applicable"]

## 6. Cross-System Join Keys
[Table mapping natural keys across source systems, e.g.:]
| Left model | Column | Right model | Column | Notes |
|-----------|--------|------------|--------|-------|
| stg_focus__notes | enrolment_id | stg_prosolution__attendance | EnrolmentID | Case-sensitive match |

## 7. Physical Data Model

[Mermaid ERD as generated in Step 7]

## 8. dbt Test Coverage Plan
[Summary table: model → PK test → FK tests → custom tests]
```

### Step 9: Update Status

```yaml
data_model:
  generate: complete
  validate: not_started
  review: not_started
  file: design/data_model_specification.md
  generated_date: [today]
```

### Step 10: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `data_model`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 11: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `data_model`
- `artifact_name`: `Data Model`
- `file_path`: `.wire/releases/[release_folder]/design/data_model.md`
- `project_id`: the release folder path (e.g. `releases/01-discovery`)

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 12: Confirm and Suggest Next Steps

```
## Data Model Specification Generated

**File**: .wire/<project_id>/design/data_model_specification.md

**Staging models**: [count]
**Integration models**: [count]
**Warehouse models**: [count] ([fact count] facts, [dim count] dims, [agg count] aggregates)
**Seed files**: [count]
**Physical ERD**: included ([entity count] entities, [relationship count] relationships)
**Cross-system joins**: [count — flag if > 0, these are high-risk]
**Canonical vertical**: [vertical name and schema(s) used, or "None — no canonical match found or proposal declined" if Step 1.5 skipped or was declined]

### Next Steps

1. Validate the data model:
   /wire:data_model-validate <project_id>

2. After validation, review with analytics engineering lead:
   /wire:data_model-review <project_id>

NOTE: This is the most consequential review gate. Approving a model with
incorrect grain, wrong join keys, or missing entities is expensive to fix
after dbt code has been generated. Take time with this review.
```

## Edge Cases

### Source Column Names Unknown

If source schema examples are not in `artifacts/`, specify staging model columns at entity-attribute level from the conceptual model, and add:
```
NOTE: Column names are provisional — based on conceptual model attributes.
Actual source column names must be confirmed before dbt:generate.
Add source schema examples to artifacts/ and regenerate.
```

### Extending an Existing dbt Project

If the client has an existing dbt project:
1. Read existing staging models from `artifacts/` to understand current naming conventions
2. Follow those conventions for new models
3. Explicitly note which existing models are being extended vs which are net-new
4. Do not rename or restructure existing models — only add

### Complex Many-to-Many Relationships

If the conceptual model contains a many-to-many relationship, resolve it in the data model:
- Create a bridge/junction table (e.g. `student_course_bridge`)
- Name it clearly and document the resolution in Section 6

## Additional Output for `dashboard_first` Projects

When `project_type` is `dashboard_first`, additionally generate:

1. **`design/source_tables_ddl.sql`** — SQL DDL (CREATE TABLE statements) defining the expected source data schema, derived from the requirements, visualization catalog, and domain knowledge. Use the target warehouse dialect (e.g., BigQuery).

2. **`design/target_warehouse_ddl.sql`** — SQL DDL defining the target dimensional model (facts and dimensions) that will provide the measures and dimensions identified in the visualization catalog.

These DDL files serve as inputs for seed data generation (`/wire:seed_data-generate`) and the dbt project structure.

## Output

This command creates:
- `.wire/<project_id>/design/data_model_specification.md` (includes physical ERD)
- `.wire/<project_id>/design/source_tables_ddl.sql` (dashboard_first projects only)
- `.wire/<project_id>/design/target_warehouse_ddl.sql` (dashboard_first projects only)
- Updates `.wire/<project_id>/status.md`

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
