---
sidebar_position: 7
title: Extending Wire
---

# Extending Wire

Wire is designed to be extended — new release types, new artifact types, new utility commands, and project-specific customisations are all first-class.

## Adding a new release type

**Since v4.0.0**, a release type is a YAML file conforming to [`wire/schemas/release-type-schema.md`](https://github.com/rittmananalytics/wire/blob/main/wire/schemas/release-type-schema.md) — phases, an ordered list of artifacts per phase (each with `id`, `command`, `depends_on`, `sequence`, `required`), plus the corresponding spec files. This isn't something you edit directly in this repo: `wire/release-types/*.yaml` and `wire/specs/**/*.md` are a synced, pinned mirror of the private `rittmananalytics/wire-process-registry` repo, branch-protected with mandatory review. See [The Process and Data Model Registries](./registries) for why it's externalized this way and how the sync works.

If you're an RA maintainer adding a release type for real:

1. **Open a PR against `wire-process-registry`**, not this repo. Add the new `release-types/<name>.yaml` there, following the schema — phases, artifacts, `depends_on` edges, `sequence` for tie-breaking within a phase.
2. **Write a spec file per artifact** at `specs/<domain>/<artifact>/generate.md` (and `validate.md`/`review.md` where applicable) in the same registry repo, with `wire_schema` front-matter conforming to [`wire/schemas/command-schema.md`](https://github.com/rittmananalytics/wire/blob/main/wire/schemas/command-schema.md) — `command`, `artifact`, `domain`, `release_types`, `action_type`, `preconditions` (a static list, or the `dynamic` sentinel if the correct precondition genuinely varies by release type), and so on.
3. **Get it reviewed and merged** — one approving review is required.
4. **Sync it into this repo**: `wire/scripts/sync-process-registry.sh` mirrors both directories and pins the resolved commit SHA.
5. **Build the packages**:

```bash
./wire/scripts/build-packages.sh
```

This bundles the newly-synced `wire/release-types/*.yaml` and inlines the specs into `commands/*.md`/`.toml`, regenerating the Claude Code plugin and Gemini extension.

Once bundled, the [precondition gate](../getting-started/core-concepts#the-precondition-gate) and [Autopilot](./autopilot) both read the new YAML's `depends_on`/`sequence` graph automatically at runtime — nothing else in the framework needs to know a new release type exists.

## Writing a spec file

A spec file is a Markdown document that Claude reads as an instruction set for the command. It should specify:

**For generate specs:**
- The inputs to read (upstream artifacts, source files, MCP data)
- The output document structure (required sections and their content)
- Any code to generate (file names, content patterns)
- Fathom/meeting context to surface

**For validate specs:**
- The checks to run (automated tests, structural validation, code compilation)
- How to classify each check (blocking vs. advisory)
- The PASS/FAIL summary format

**For review specs:**
- The document to present
- The context to gather (validation results, meeting transcripts, prior decisions)
- The questions to ask the reviewer
- How to record the decision

A minimal spec structure:

```markdown
# my_first_artifact — generate

## Inputs
- Upstream: `problem_definition.md`
- Source: read `dbt_project.yml` from the project root

## Output: my_first_artifact.md

### Required sections
1. Executive Summary (3–5 sentences)
2. Scope table (source systems, included / excluded)
3. Open questions (any items requiring client clarification)

## Meeting context
Search Fathom for meetings in the last 30 days mentioning [client name].
Surface any decisions related to scope or data sources.

## Completion criteria
- All three required sections present
- No placeholder text remaining
- Open questions table has at least one entry OR an explicit "None" marker
```

## Adding a project-specific command

For a single engagement, you can add a custom command without modifying the shared Wire source. Place the spec at:

```
.wire/releases/<release-folder>/custom-commands/<command-name>.md
```

Wire will pick it up automatically. These commands are available as:

```
/wire:custom-<command-name> <release-folder>
```

## Adding utility commands

Utility commands (prefixed `/wire:utils-`) are general-purpose commands not tied to a specific release type. They live in `wire/specs/utils/`.

Example: the document analysis utility at `wire/specs/utils/doc_analyze.md` reads an arbitrary document and extracts Wire-relevant information from it (deliverables, stakeholders, constraints). It's invoked as `/wire:utils-doc-analyze`.

## Customising the status template

The status report template is at `wire/TEMPLATES/status-template.md`. Copy it to `.wire/releases/<release-folder>/status-template.md` to override it for a specific engagement. Wire reads the local override first.

## Customising the CLAUDE.md template

When `/wire:new` creates a new engagement, it populates a `CLAUDE.md` file from the template at `wire/TEMPLATES/claude-md-template.md`. Modify the template to change what Wire captures at setup for all new engagements.

## Distributing your extensions

Extensions to Wire can be distributed as separate plugins. A Wire extension plugin follows the same structure as the core Wire plugin, with:
- Spec files in `specs/` (or your own equivalent directory)
- A `build-packages.sh`-style entry point that inlines specs into `commands/*.md`

Users install an extension plugin alongside the core Wire plugin:

```
/plugin install my-extension@my-org
/reload-plugins
```

Extension commands coexist with core Wire commands. Namespacing is by convention — use a prefix that distinguishes your extension from the core (e.g. `/wire:ext_mycompany_*`).
