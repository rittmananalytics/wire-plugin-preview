---
sidebar_position: 9
title: Detailed Execution Tracing
---

# Detailed Execution Tracing

**Introduced**: v4.0.0

Every release already has an `execution_log.md` — one terse row per command (`timestamp | command | result | a detail string capped at 120 characters`). That's enough for a normal audit trail: what ran, when, pass or fail. It can't answer "what actually happened inside that command" — which files it read, what it inferred, what it proposed, what you decided, and why.

Tracing is for that. It's a complete, structured, step-by-step record of every command's execution — off by default, local-only, and yours to turn on when you actually want that depth (debugging something that went wrong, or understanding exactly how an optional feature like the [data model registry](./registries) behaved on a specific engagement).

## Turning it on

```bash
export WIRE_TRACE=true
```

That's it — no command to run, no config file to edit. Every Wire command checks this on every invocation; if it's unset or not `true`, nothing changes and there's zero overhead. Unset it (or set it to anything else) to turn it back off.

## Where it goes

`.wire/releases/<release_folder>/trace.jsonl` — JSON Lines, one event per line, append-only, sitting alongside that release's `status.md` and `execution_log.md`. Commands not scoped to a specific release write to `.wire/trace.jsonl` at the engagement level instead.

**This never leaves your machine.** Unlike the anonymous usage event Wire sends to Segment on every command (see the FAQ), trace files are plain local JSON in your own repo — nothing about them is transmitted anywhere.

## What gets logged

Three event types per command:

- `command_start` — once, before the workflow begins
- `step` — once per meaningful step within the command (not just its top-level numbered steps — a step with distinct internal sub-parts gets one event per sub-part too)
- `command_end` — once, with the same result value that would go into `execution_log.md`

Every event carries the release and release type it ran under, and a `detail` field with no length limit — the actual account of what happened, not a summary.

```json
{"ts":"2026-07-05T14:20:11Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.1","step_name":"Resolve the registry location","result":null,"detail":"Checked wire/data-model-registry/ (not found — not the Wire source repo). Checked ~/.wire/data-model-registry/ (found — cloned via /wire:utils-data-model-registry-setup on 2026-07-01)."}
{"ts":"2026-07-05T14:20:19Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.2","step_name":"Resolve the vertical","result":null,"detail":"No confident vertical match for Acme (B2B SaaS, no dedicated saas vertical in the registry). Adjacent match found: subscription-commerce — proposed as a structural analogue for Acme's MRR/NRR model."}
```

That level of detail is exactly what would have made [the data model registry's automatic-detection behavior](./registries) visible without reconstructing it by hand after the fact — was the registry reachable, what did it search, what matched, what didn't, what got carried into the generated model and why.

## What this is not

- **Not a replacement for `execution_log.md` or Telemetry.** Both continue exactly as before; tracing is additive, for the subset of engagements that want much finer detail.
- **Not retroactive.** Turning it on only captures what happens from that point forward — there's no way to reconstruct trace detail for commands that already ran before `WIRE_TRACE=true` was set.
- **Not a performance or cost concern when off.** The check is a single environment-variable comparison per command; with it off (the default), nothing else happens.

See [`wire/specs/utils/tracing.md`](https://github.com/rittmananalytics/wire/blob/main/wire/specs/utils/tracing.md) for the exact mechanism — it's injected into every command at build time, the same way the [process registry](./registries) content is, so it applies uniformly across all ~260 commands without any of them needing individual changes.
