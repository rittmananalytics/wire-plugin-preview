---
description: Generate per-domain reference files collocated with dbt models
argument-hint: <release-folder>
---

# Generate per-domain reference files collocated with dbt models

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
    'command': 'ads_knowledge-skill-generate',
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
artifact: knowledge_skill
domain: agentic_data_stack
release_types:
  - agentic_data_stack
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: canonical_models
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Generate per-domain reference files collocated with dbt models — the agent's knowledge base
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Knowledge Skill Generate

Follow `specs/utils/agentic_data_stack_delegate.md` before executing the workflow below.

## Purpose

Produce per-domain `DOMAIN_REFERENCE.md` files and colocate them with the dbt mart models they describe. These files are the agent's knowledge base — they narrow the search space from hundreds of tables to the specific entities, metrics, and query patterns relevant to a given domain. They live in the dbt repo and update when models change.

This directly implements the "knowledge skill" pattern from Anthropic's self-service analytics architecture: structured reference files maintained as engineering practice, not documentation overhead.

## Usage

```bash
/wire:ads_knowledge-skill-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `semantic_layer.review: approved`
- `canonical_models.review: approved`
- dbt project path accessible

## Workflow

### Step 1: Read Inputs

For each domain:
1. Read the canonical model schema.yml (column descriptions, tests, relationships)
2. Read `artifacts/governance_design.md` (canonical table, owner, tiering)
3. Read `artifacts/metric_audit.md` (metric definitions for this domain)
4. Read `artifacts/query_audit.md` (common question patterns for this domain — especially Raw-only patterns that need documentation)

### Step 2: Generate DOMAIN_REFERENCE.md for Each Domain

For each domain, write `<dbt_project_path>/models/marts/<domain>/DOMAIN_REFERENCE.md`:

```markdown
---
domain: orders
canonical_table: fct_orders
owner: data-platform@company.com
last_updated: YYYY-MM-DD
semantic_layer: dbt_semantic_layer  # or lookml | none
---

# Orders Domain Reference

## What This Domain Covers

Revenue from confirmed customer orders — net of returns and tax. Use this domain for 
questions about order volume, revenue, channels, and product performance.

**Not in this domain:** marketing attribution (see `marketing/DOMAIN_REFERENCE.md`), 
customer lifetime value (see `customers/DOMAIN_REFERENCE.md`).

## Canonical Table

**`project.analytics.fct_orders`**  
Grain: one row per order. Includes only confirmed and completed orders. Cancelled orders 
are excluded. Returns are captured via the `return_amount` field — they do not generate 
a separate row.

| Field | Type | Description |
|---|---|---|
| order_pk | STRING | Surrogate key (surrogate_key([order_id, source])) |
| order_id | STRING | Source system order identifier |
| customer_fk | STRING | FK → dim_customers.customer_pk |
| order_date | DATE | Date order was placed (not shipped) |
| net_revenue | NUMERIC | Revenue after returns and tax |
| gross_revenue | NUMERIC | Pre-deduction gross amount |
| channel | STRING | Acquisition channel: organic, paid_search, email, direct, affiliate |
| status | STRING | confirmed, shipped, delivered, returned |
| product_category | STRING | Top-level category from dim_products |

## Semantic Layer Metrics (use these first)

| Metric | dbt SL / LookML name | What it measures |
|---|---|---|
| Total Revenue | `total_revenue` | SUM(net_revenue) WHERE status = 'confirmed' |
| Order Count | `order_count` | COUNT DISTINCT order_pk WHERE status = 'confirmed' |
| Average Order Value | `avg_order_value` | total_revenue / order_count |
| Return Rate | `return_rate` | SUM(return_amount) / SUM(gross_revenue) |

Always query via the semantic layer for these metrics. Do not write raw SQL for `total_revenue` — 
the semantic layer filter is the canonical definition and raw SQL will silently include returns.

## Common Questions and How to Answer Them

### "What was revenue last month by channel?"
→ Semantic layer: `dbt sl query --metrics total_revenue --group-by channel,order__order_date__month`

### "How many orders were placed this week?"
→ Semantic layer: `dbt sl query --metrics order_count --group-by order__order_date__week`

### "Show me the top 10 customers by order value"
→ Curated SQL (no semantic metric for customer-level ranking):
```sql
SELECT
  c.customer_name,
  SUM(o.net_revenue) AS total_spend,
  COUNT(DISTINCT o.order_pk) AS order_count
FROM `project.analytics.fct_orders` o
JOIN `project.analytics.dim_customers` c ON o.customer_fk = c.customer_pk
WHERE o.status = 'confirmed'
GROUP BY c.customer_name
ORDER BY total_spend DESC
LIMIT 10
```

### "What's the return rate by product category?"
→ Semantic layer: `dbt sl query --metrics return_rate --group-by product_category`

## Known Limitations and Edge Cases

- Revenue figures are **net** throughout this domain. For gross comparisons (e.g. to external ad platforms reporting gross), use `gross_revenue` explicitly.
- `channel = 'unknown'` accounts for ~3% of orders. These are orders placed directly via the API without attribution data. Do not exclude them from totals.
- Orders placed on the last day of a month may appear in the following month's figures due to UTC timezone handling in `order_date`. For finance reporting, use `order_date_adjusted` which applies the client's local timezone.

## Deprecated Tables — Do Not Use

| Table | Replacement | Sunset date |
|---|---|---|
| orders_raw | fct_orders | YYYY-MM-DD |
| revenue_v2 | fct_orders | YYYY-MM-DD |
```

### Step 3: Colocate in dbt Project

Place each file alongside the canonical model:
```
<dbt_project_path>/models/marts/
  orders/
    fct_orders.sql
    fct_orders.yml
    DOMAIN_REFERENCE.md   ← generated here
  customers/
    dim_customers.sql
    dim_customers.yml
    DOMAIN_REFERENCE.md
```

### Step 4: Add CI Check (Optional but Recommended)

Add a check to the dbt project CI that flags when a model PR does not update the collocated DOMAIN_REFERENCE.md. This keeps the skill files current as the models evolve.

Create `.github/workflows/check-domain-reference.yml` (or equivalent):

```yaml
name: Check domain reference files
on: [pull_request]
jobs:
  check-domain-refs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      - name: Check for reference file updates
        run: |
          changed_models=$(git diff --name-only origin/main...HEAD -- 'models/marts/**/*.sql')
          if [ -n "$changed_models" ]; then
            for model in $changed_models; do
              domain_dir=$(dirname "$model")
              if [ ! -f "$domain_dir/DOMAIN_REFERENCE.md" ]; then
                echo "WARNING: $model changed but no DOMAIN_REFERENCE.md exists in $domain_dir"
              fi
            done
          fi
```

### Step 5: Write Knowledge Skill Index

Write `.wire/<release-folder>/artifacts/knowledge_skill_index.md` — a single index of all domain reference files and their locations, used by agent_config to route questions to the right file:

```markdown
# Knowledge Skill Index

| Domain | File path | Key entities | Last updated |
|---|---|---|---|
| orders | models/marts/orders/DOMAIN_REFERENCE.md | fct_orders, revenue, channels | YYYY-MM-DD |
| customers | models/marts/customers/DOMAIN_REFERENCE.md | dim_customers, segments | YYYY-MM-DD |
```

### Step 6: Update Status

```yaml
knowledge_skill:
  generate: complete
  generated_date: YYYY-MM-DD
  domains_covered: N
  files_written: N
  ci_check_added: true  # or false
```

## Edge Cases

### No dbt Project

If there is no dbt project, write the DOMAIN_REFERENCE files to `.wire/<release-folder>/artifacts/knowledge_skill/` instead. Note in the review that colocation with transformation code is not possible — the CI check for maintenance cannot be applied, and files will need manual updates when the warehouse schema changes.

## Output

- `DOMAIN_REFERENCE.md` files in `<dbt_project_path>/models/marts/<domain>/` (or artifacts folder)
- `.wire/<release-folder>/artifacts/knowledge_skill_index.md`
- `.github/workflows/check-domain-reference.yml` (if CI check requested)
- Updated `status.md`

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
