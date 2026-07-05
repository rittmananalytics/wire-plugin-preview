---
description: Generate orchestration layer (Dagster or dbt Cloud)
argument-hint: <project-folder>
---

# Generate orchestration layer (Dagster or dbt Cloud)

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
    'command': 'orchestration-generate',
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
command: generate
artifact: orchestration
domain: development
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
preconditions:
  - artifact: pipeline
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Generate orchestration layer — choose Dagster, dbt Cloud, or Apache Airflow to schedule and run the data pipeline
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Orchestration Generate Command

Follow `specs/utils/orchestration_engineer_delegate.md` before executing the workflow below.

## Purpose

Generate the orchestration layer for the data platform. This step determines how dbt models and data pipeline code are scheduled and executed in production. Supports three approaches:

- **Dagster** — open-source, Python-native, assets-first orchestrator; wraps dbt models as Dagster assets and ingestion scripts as software-defined assets
- **dbt Cloud** — managed service for scheduling dbt jobs; simpler setup, best when the project is dbt-only or already committed to dbt Cloud
- **Apache Airflow** — industry-standard DAG-based orchestrator; generates a Python DAG with a `DbtTaskGroup` and upstream sensor tasks per source; best when the client already runs Airflow infrastructure

## Prerequisites

**Required artifacts (must be approved)**:
- `pipeline_design` — defines run cadences, source systems, and data flow
- `dbt_warehouse` (or `dbt`) — dbt models must exist before orchestration can reference them

**Optional**:
- `pipeline` — if Dagster is chosen, pipeline ingestion code is wrapped as Dagster assets

## Workflow

### Step 1: Read Inputs

1. Read `.wire/<project_id>/design/pipeline_design.md` and extract:
   - Source systems and ingestion approach (batch, streaming, API)
   - Run cadences (daily, hourly, event-driven, etc.)
   - Data dependencies between pipeline stages
   - Any stated orchestration preferences or constraints
2. Read `.wire/<project_id>/status.md`:
   - Check `artifacts.orchestration.orchestration_tool` — if already set (from a previous run or project creation), use it and skip Step 2
   - Read `artifacts.pipeline.pipeline_tool` and `artifacts.pipeline.generate` — note whether a pipeline has been configured and which tool is in use
   - Note `project_type` to understand scope
3. Locate the dbt project root (search for `dbt_project.yml` in the repository)
4. **Check pipeline connection health** (if `pipeline.generate == complete`):
   Follow `wire/specs/utils/pipeline_tool_status.md` to verify all pipeline connections are healthy.
   - If result is `unhealthy`: warn the user and ask whether to proceed. Do not halt automatically — orchestration code can still be generated even if connections are temporarily unhealthy, but the warning should be visible.
   - If result is `degraded` or `healthy`: proceed normally.
   - If `pipeline.generate != complete`: skip this check and note that pipeline connections have not been set up yet.

### Step 2: Choose Orchestration Tool

If `orchestration_tool` is not already set in status.md, ask the user:

```
Which orchestration tool should be used for this project?

1. Dagster — Python-native orchestrator, wraps dbt + pipeline code as software-defined assets.
   Best for: projects with custom ingestion code, complex dependencies, or teams already using Python.

2. dbt Cloud — Managed dbt scheduling service. No additional infrastructure required.
   Best for: dbt-only or dbt-heavy projects where the team already uses dbt Cloud, or wants minimal ops overhead.

3. Apache Airflow — DAG-based orchestrator with a DbtTaskGroup and sensor tasks per source.
   Best for: clients who already run Airflow infrastructure and want to add the dbt pipeline to an existing environment.
```

Wait for the user's selection. Store the choice:
1. Write `orchestration_tool: "dagster"`, `orchestration_tool: "dbt_cloud"`, or `orchestration_tool: "airflow"` into the `artifacts.orchestration` section of status.md immediately, before generating any files.

### Step 3a: Generate Dagster Orchestration (if Dagster chosen)

Load the Dagster skill from `skills/dagster/SKILL.md` for Dagster-specific patterns and conventions.

#### 3a.1 — Scaffold Dagster project

If no `dagster_orchestration/` directory exists at the repo root, scaffold it:

```bash
uvx create-dagster project dagster_orchestration
```

This creates:
```
dagster_orchestration/
├── dagster_orchestration/
│   ├── __init__.py
│   ├── assets/
│   ├── resources/
│   └── schedules/
├── dagster_orchestration_tests/
├── pyproject.toml
└── dagster.yaml
```

If a `dagster_orchestration/` directory already exists, skip scaffolding and work within it.

#### 3a.2 — Add dagster-dbt integration

Add `dagster-dbt` to the project dependencies:

```bash
cd dagster_orchestration
uv add dagster-dbt
```

Create a `DbtProjectComponent` YAML configuration. Locate the dbt project root (directory containing `dbt_project.yml`) and create:

**`dagster_orchestration/dagster_orchestration/components/dbt_project.yaml`**:
```yaml
type: dagster_dbt.DbtProjectComponent

params:
  dbt_project_dir: ../../  # relative path to dbt project root
  select: "*"
  exclude: ""
  node_info_to_asset_check_specs:
    - data_tests: true
      model_schema_checks: true
```

This automatically generates one Dagster asset per dbt model, preserving the dbt dependency graph.

#### 3a.3 — Generate source ingestion assets

For each source system identified in `pipeline_design.md`, generate a Dagster asset definition in `dagster_orchestration/dagster_orchestration/assets/`:

**Pattern for each source** (`assets/<source_name>_ingestion.py`):

```python
import dagster as dg
from dagster import asset, AssetExecutionContext


@dg.asset(
    group_name="<source_group>",
    description="Ingest <source_name> data from <source_description>",
    compute_kind="python",
    tags={"layer": "ingestion", "source": "<source_name>"},
)
def <source_name>_raw(context: AssetExecutionContext) -> dg.MaterializeResult:
    """Ingest raw <source_name> data.

    Source: <source_system>
    Cadence: <run_cadence>
    Target: <target_table>
    """
    # TODO: Implement ingestion logic
    # Reference: development/pipeline/ for existing pipeline code
    context.log.info("Ingesting <source_name> data")

    return dg.MaterializeResult(
        metadata={
            "cadence": dg.MetadataValue.text("<run_cadence>"),
            "source": dg.MetadataValue.text("<source_system>"),
        }
    )
```

Use the pipeline design's source system list to generate one asset per source. If `pipeline/` code already exists, reference it from the asset rather than duplicating logic.

#### 3a.4 — Generate schedules and sensors

For each distinct run cadence in the pipeline design, generate a schedule in `dagster_orchestration/dagster_orchestration/schedules/`:

**`schedules/pipeline_schedules.py`**:
```python
import dagster as dg
from dagster import ScheduleDefinition, define_asset_job, AssetSelection

# Job: all ingestion + dbt assets
full_pipeline_job = define_asset_job(
    name="full_pipeline",
    selection=AssetSelection.all(),
    description="Full pipeline: ingestion → dbt staging → integration → warehouse",
)

# Schedule: <primary cadence from pipeline_design>
<cadence_name>_schedule = ScheduleDefinition(
    name="<cadence_name>_schedule",
    cron_schedule="<cron_expression>",
    job=full_pipeline_job,
    execution_timezone="<timezone>",  # from pipeline_design or default UTC
    default_status=dg.DefaultScheduleStatus.RUNNING,
)
```

For any event-driven triggers identified in pipeline_design (e.g. "run when new files arrive"), generate an asset sensor instead:

```python
@dg.asset_sensor(asset_key=dg.AssetKey("<upstream_asset>"), job=full_pipeline_job)
def <trigger_name>_sensor(context: dg.SensorEvaluationContext, asset_event):
    yield dg.RunRequest(run_key=context.cursor)
```

#### 3a.5 — Update `__init__.py`

Ensure all assets, schedules, and sensors are imported and registered in `dagster_orchestration/__init__.py`:

```python
import dagster as dg
from dagster_orchestration.assets import *
from dagster_orchestration.schedules.pipeline_schedules import *

defs = dg.Definitions(
    assets=dg.load_assets_from_modules([assets]),
    schedules=[<schedule_list>],
    sensors=[<sensor_list>],
)
```

#### 3a.6 — Generate setup documentation

Write `.wire/<project_id>/development/orchestration/dagster_setup.md`:

```markdown
# Dagster Orchestration Setup

**Project**: <project_name>
**Generated**: <date>
**Approach**: Dagster software-defined assets

## Overview

[Summary of the orchestration approach based on pipeline_design]

## Project Structure

[dagster_orchestration/ directory tree]

## Assets

| Asset | Group | Cadence | Description |
|-------|-------|---------|-------------|
[one row per generated asset]

## Schedules

| Schedule | Cron | Timezone | Assets |
|----------|------|----------|--------|
[one row per schedule]

## Local Development

```bash
cd dagster_orchestration
uv sync
dg dev                    # Start Dagster UI at http://localhost:3000
dg launch --assets "*"    # Materialize all assets
```

## Production Deployment

[Deployment notes based on project infrastructure from pipeline_design]
```

### Step 3b: Generate dbt Cloud Orchestration (if dbt Cloud chosen)

#### 3b.1 — Read pipeline design for run cadences

Extract from `pipeline_design.md`:
- Number of distinct run cadences (e.g. hourly refresh, daily full load)
- Source systems (to determine if custom steps needed beyond dbt)
- Environment names (dev, staging, prod)

#### 3b.2 — Generate environment configurations

Write `.wire/<project_id>/development/orchestration/dbt_cloud_config.md`:

```markdown
# dbt Cloud Configuration

**Project**: <project_name>
**Generated**: <date>

## Environments

### Development
- Connection: <warehouse_type> (dev credentials)
- Target schema: <project_name>_dev
- dbt version: 1.8+
- Threads: 4

### Production
- Connection: <warehouse_type> (prod service account)
- Target schema: <project_name>_prod
- dbt version: 1.8+
- Threads: 8

## Jobs

<for each cadence from pipeline_design>

### Job: <cadence_name> Refresh
- Environment: Production
- Commands:
  - `dbt source freshness`
  - `dbt run --select <scope>`
  - `dbt test --select <scope>`
- Schedule: <cron_expression>  (<human cadence>)
- Notifications: on failure → [team email / Slack channel]

### Job: CI — Pull Request
- Environment: Development
- Trigger: Pull request opened/updated
- Commands:
  - `dbt run --select state:modified+`
  - `dbt test --select state:modified+`
- Run on: slim CI (uses defer to production state)

## API Configuration (Terraform / IaC)

If managing dbt Cloud via Terraform (`dbt Cloud provider`):

```hcl
resource "dbtcloud_environment" "production" {
  name           = "Production"
  project_id     = var.dbt_cloud_project_id
  dbt_version    = "1.8.0-latest"
  type           = "deployment"
  credential_id  = dbtcloud_bigquery_credential.prod.credential_id
}

resource "dbtcloud_job" "<job_name>" {
  name           = "<cadence_name> Refresh"
  project_id     = var.dbt_cloud_project_id
  environment_id = dbtcloud_environment.production.id
  execute_steps  = ["dbt run", "dbt test"]
  schedule_type  = "cron"
  cron_schedule  = "<cron_expression>"
  num_threads    = 8
}
```
```

#### 3b.3 — Generate .env template

Write `.wire/<project_id>/development/orchestration/dbt_cloud.env.template`:

```
DBT_CLOUD_ACCOUNT_ID=
DBT_CLOUD_PROJECT_ID=
DBT_CLOUD_TOKEN=
DBT_CLOUD_ENVIRONMENT_ID_PROD=
DBT_CLOUD_ENVIRONMENT_ID_DEV=
```

### Step 3c: Generate Airflow Orchestration (if Airflow chosen)

#### 3c.1 — Scaffold DAG file

Create `dags/<project_name>_pipeline.py` at the repo root (or inside an existing `dags/` directory if one is present). The DAG uses the Astronomer Cosmos `DbtTaskGroup` pattern to wrap all dbt models as Airflow tasks, preserving the dbt dependency graph.

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.google.cloud.sensors.bigquery import BigQueryTableExistenceSensor
# If Cosmos is available:
# from cosmos import DbtTaskGroup, ProjectConfig, ProfileConfig, ExecutionConfig

default_args = {
    "owner": "<project_name>",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": True,
    "email": ["<data-team-email>"],
}

with DAG(
    dag_id="<project_name>_pipeline",
    default_args=default_args,
    description="<project_name> data pipeline: ingestion → dbt staging → integration → warehouse",
    schedule_interval="<cron_expression>",  # from pipeline_design cadence
    start_date=datetime(<year>, <month>, <day>),
    catchup=False,
    tags=["<project_name>", "dbt", "pipeline"],
) as dag:

    # --- Source readiness sensors (one per source system) ---
    # Replace with appropriate sensor for each source
    <source_name>_sensor = BigQueryTableExistenceSensor(
        task_id="check_<source_name>_loaded",
        project_id="<gcp_project>",
        dataset_id="<fivetran_dataset>",
        table_id="<source_table>",
        timeout=3600,
        poke_interval=60,
    )

    # --- dbt run: all models in dependency order ---
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            "cd <dbt_project_path> && "
            "dbt run --profiles-dir . --target prod --select '*'"
        ),
        env={"DBT_PROFILES_DIR": "<dbt_project_path>"},
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            "cd <dbt_project_path> && "
            "dbt test --profiles-dir . --target prod --select '*'"
        ),
    )

    # --- Task dependencies ---
    <source_name>_sensor >> dbt_run >> dbt_test
```

Generate one sensor task per source system from `pipeline_design.md`. If the client has Astronomer Cosmos installed, add a `DbtTaskGroup` block as an inline comment alternative that preserves per-model Airflow tasks.

#### 3c.2 — Generate Airflow connection IDs reference

Write `.wire/<project_id>/development/orchestration/airflow_connections.md`:

```markdown
# Airflow Connection Configuration

These connections must be configured in the Airflow UI (Admin → Connections) or via environment variables before the DAG runs.

| Connection ID | Type | Used by | Notes |
|---|---|---|---|
| `google_cloud_default` | Google Cloud | BigQuery sensors, dbt run | Service account with BigQuery Data Editor + Job User |
| `<source_name>_conn` | HTTP / custom | <source_name>_sensor | Connection details from pipeline_design |

## Environment variables (alternative to UI connections)

```bash
AIRFLOW__CORE__SQL_ALCHEMY_CONN=<airflow-db-url>
AIRFLOW_CONN_GOOGLE_CLOUD_DEFAULT=google-cloud-platform://?key_path=%2Fpath%2Fto%2Fkey.json
```
```

#### 3c.3 — Generate Airflow variables reference

Write `.wire/<project_id>/development/orchestration/airflow_variables.md`:

```markdown
# Airflow Variable Configuration

Set these via the Airflow UI (Admin → Variables) or with `airflow variables set`.

| Variable | Example value | Description |
|---|---|---|
| `<project_name>_dbt_project_path` | `/opt/airflow/dags/<project_name>` | Absolute path to dbt project root on the Airflow worker |
| `<project_name>_gcp_project` | `my-gcp-project` | GCP project for BigQuery |
| `<project_name>_dbt_target` | `prod` | dbt target profile to use in production |
```

#### 3c.4 — Generate setup documentation

Write `.wire/<project_id>/development/orchestration/airflow_setup.md`:

```markdown
# Airflow Orchestration Setup

**Project**: <project_name>
**Generated**: <date>
**Approach**: Apache Airflow DAG with BashOperator dbt tasks and source sensors

## Overview

[Summary of the orchestration approach based on pipeline_design]

## DAG

| Property | Value |
|---|---|
| DAG ID | `<project_name>_pipeline` |
| Schedule | `<cron_expression>` (<human cadence>) |
| Timezone | <timezone> |
| Catchup | False |

## Tasks

| Task ID | Type | Upstream | Description |
|---|---|---|---|
[one row per task]

## Connections required

[From airflow_connections.md summary]

## Deployment

1. Copy `dags/<project_name>_pipeline.py` to the Airflow DAGs folder (or ensure the repo is synced via Git Sync)
2. Configure connections in the Airflow UI
3. Set variables in the Airflow UI
4. Enable the DAG in the Airflow UI
5. Trigger a manual run to verify

## Local testing

```bash
# Parse check
python -c "from dags.<project_name>_pipeline import dag; print(dag.task_ids)"

# List tasks
airflow tasks list <project_name>_pipeline
```
```

### Step 4: Update Status

Read `.wire/<project_id>/status.md` and update the `orchestration` artifact section:

```yaml
orchestration:
  orchestration_tool: "dagster"  # or "dbt_cloud"
  generate: complete
  validate: not_started
  review: not_started
  generated_date: <today>
  generated_files:
    - development/orchestration/dagster_setup.md      # Dagster
    - development/orchestration/dbt_cloud_config.md   # dbt Cloud
    - development/orchestration/airflow_setup.md       # Airflow
    - development/orchestration/airflow_connections.md # Airflow
    - development/orchestration/airflow_variables.md   # Airflow
    - dagster_orchestration/  # (Dagster only)
    - dags/  # (Airflow only)
  revision_history:
    - date: <today>
      action: generate
      notes: "Initial orchestration scaffold using <tool>"
```

### Step 5: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `orchestration`
- Action: `generate`
- Status: `complete`

### Step 6: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `orchestration`
- `artifact_name`: `Orchestration Layer`
- `file_path`: `.wire/releases/[release_folder]/dev/orchestration.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 7: Confirm and Suggest Next Steps

```
## Orchestration Generated Successfully

**Tool**: <Dagster | dbt Cloud>
**Generated files**:
  [list files]

### Next Steps

1. **Validate orchestration**: `/wire:orchestration-validate <project>`
   - Dagster: runs `dg check defs` and verifies all dbt models have corresponding assets
   - dbt Cloud: validates job configs reference correct environments and model selectors
   - Airflow: parse-checks the DAG, verifies all dbt models are covered as tasks, checks cron expression

2. Review and customise generated asset/job definitions to match your infrastructure

3. After validation, review with the team: `/wire:orchestration-review <project>`
```

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
