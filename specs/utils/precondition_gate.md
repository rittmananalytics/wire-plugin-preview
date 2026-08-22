---
description: Internal utility — resolves a command's declared preconditions against status.md and blocks by default when unmet; overrides require a recorded name and reason
---

# Precondition Gate Utility

Called at the start of any generate, validate, or review command whose own
front-matter declares a non-empty `preconditions` list. Confirms every
declared precondition is actually satisfied in `status.md` before the
calling spec does any substantive work — the enforcement half of the
`preconditions` field defined in `wire/schemas/command-schema.md`.

By default a consultant cannot skip a step this gate blocks. They can
override it, but the override is always recorded against their name with
their stated reason — never silent.

This is distinct from `stale_artifact_check.md` (asks whether to overwrite
an already-generated artifact) and `migration_preflight.md` (checks a batch
is safe to start). This gate asks a narrower question: is it even legitimate
to run this command yet, given what upstream artifacts have and haven't
completed.

## Inputs (read directly from the calling spec — no params to pass)

- `preconditions` — this command's own front-matter value: a list of
  `{artifact, action, outcome}` entries, the literal string `dynamic` (see
  Step 0), or absent/`[]`. If absent or `[]`, this gate is a no-op: return to
  the calling spec immediately with no output.
- `artifact` and `command` — this command's own front-matter values, used to
  label the override record and to compose the remediation command hint.
- `release_folder` — the release folder path passed to the calling spec.

## Procedure

### Step 0: Resolve `dynamic` preconditions, if declared

A handful of artifacts are shared across multiple release types whose
`wire/release-types/*.yaml` disagree on what gates them (e.g. `dbt-generate`
needs different upstream approval depending on whether the release is
`full_platform` or `dashboard_first`). Those commands declare
`preconditions: dynamic` in front-matter instead of a static list, since a
single static list would be right for one release type and wrong for
another.

If `preconditions` is the literal string `dynamic`:

1. Read `.wire/releases/<release_folder>/status.md` front-matter `project_type`.
2. Load `wire/release-types/<project_type>.yaml`. Find this command's own
   `artifact` value under `phases[].artifacts[].id`.
3. If found, use that entry's `depends_on` list as the effective
   preconditions for Step 1 below (an empty `depends_on: []` is a valid
   result — proceed with no gate, same as a static `preconditions: []`).
4. If this artifact doesn't appear in that YAML at all, treat it the same as
   an empty list — proceed with no gate. (Not every release type uses every
   shared artifact — e.g. `dbt_development` has no `mockups` phase at all.)

Then continue to Step 1 using the resolved list in place of the front-matter
value.

### Step 1: Check each precondition against status.md

Read `.wire/releases/<release_folder>/status.md`. For each `{artifact, action,
outcome}` entry in the (possibly Step-0-resolved) `preconditions`:

1. Look up `artifacts.<artifact>.<action>` in status.md.
2. Compare against the required `outcome`:
   - `outcome: complete` → recorded value must be `complete`
   - `outcome: PASS` → recorded value must be `pass` (case-insensitive)
   - `outcome: approved` → recorded value must be `approved`
3. Record whether each precondition is **met** or **unmet**. For unmet ones,
   capture the actual recorded value (or `not_started` if the key is absent)
   for the blocker message.

If every precondition is met, return to the calling spec immediately with no
output — this gate adds no friction to the compliant path.

### Step 2: Block by default

If any precondition is unmet, stop and output:

```
🚫 Precondition not met — <artifact>/<command> requires:
  - <dep_artifact>.<dep_action> = <required_outcome>   (currently: <actual_value>)
  [one line per unmet precondition]

This step is gated by default. Run the blocking command(s) first:
  /wire:<dep-artifact-with-dashes>-<dep_action> <release_folder>

A consultant can override this gate, but the override is recorded against
their name with a reason — it is never silent.

Override and proceed anyway? (yes / no)
```

- **no** — output `Stopping — clear the blocker(s) above, then re-run.` and do
  not proceed with the calling spec's workflow.
- **yes** — continue to Step 3.

### Step 3: Capture the override

Prompt:

```
Overriding requires your name and a reason. Both are required.

Your name:
Reason for overriding:
```

Both fields must be non-empty. Re-prompt on a blank answer — there is no
anonymous or unexplained override path.

### Step 4: Record the override

Update `.wire/releases/<release_folder>/status.md`:

1. Append one entry per unmet precondition to a top-level `precondition_overrides`
   array in the front-matter (create the array if it doesn't exist yet):

```yaml
precondition_overrides:
  - artifact: <artifact>
    action: <command>
    unmet_precondition: "<dep_artifact>.<dep_action> required <required_outcome>, was <actual_value>"
    overridden_by: "<consultant name>"
    reason: "<reason>"
    date: "{{TODAY}}"
```

2. Set `artifacts.<artifact>.gate_overridden: true` so the override is visible
   on the artifact's own status entry, not just in the override log.

3. Add or update a `## Precondition Overrides` section in the body of
   `status.md` (same visibility pattern as the existing `## Blockers`
   section):

```markdown
## Precondition Overrides

| Date | Artifact | Action | Unmet Precondition | Overridden By | Reason |
|------|----------|--------|---------------------|---------------|--------|
| {{TODAY}} | <artifact> | <command> | <dep_artifact>.<dep_action> required <required_outcome>, was <actual_value> | <consultant name> | <reason> |
```

### Step 5: Log and proceed

Append a row to `.wire/releases/<release_folder>/execution_log.md` following
`specs/utils/execution_log.md`, using `override` as the Result and a Detail
string of `<dep_artifact>.<dep_action> required <outcome>, was <actual> —
overridden by <name>: <reason>` (truncate to keep the row under 120
characters; replace any `|` with `—`).

Output `⚠️  Proceeding with override — recorded against <name>.` and return
control to the calling spec to continue its normal workflow.
