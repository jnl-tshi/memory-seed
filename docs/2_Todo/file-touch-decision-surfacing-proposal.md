---
title: "File-Touch Decision Surfacing Proposal"
date: "2026-08-04"
project: "memory-seed"
status: "shipped-v1 (Claude PostToolUse); other agents deferred"
priority: "P2"
next_action: "Observe the hook in real sessions; extend to Codex/Gemini/Cursor events when their PostToolUse equivalents are verified."
related:
  - "docs/2_Todo/attention-retrieval-signal-proposal.md"
  - "docs/3_Spec/graph-edge-contract.md"
  - "business/research/field-evidence-log.md"
---

# File-Touch Decision Surfacing Proposal

Status: **v1 SHIPPED 2026-08-04** - `.memory-seed/hooks/file-touch-decisions.py` (live + seed), registered as a Claude PostToolUse hook by `init_project`; tests in `tests/test_file_touch_hook.py`. Built the same day E8 showed the record-side alone cannot carry reversals and mid-turn injection is the only reach into a single-turn headless session. Five-question test: **Retrieval, Application**.

## Problem — the strongest field challenge on record

Field evidence **E7** (r/softwarearchitecture ADR-abandonment thread, 45K views): practitioners who
kept decision records report they died because *nothing ever surfaced them again* — and the only
records worth writing were the ones "a test failed and pointed back at". Three independent
responders converged on executable enforcement over written records. The gap in their position:
a test encodes *what* is forbidden, never *why*, and cannot carry a rejected alternative. The
synthesis: **tests are an excellent trigger and a poor record.** Memory Seed has the records; this
proposal builds the trigger.

## Proposal

A `PostToolUse` hook on Edit/Write (later: test-failure output) that maps the touched file path to
session entries whose `F:` references include it, and surfaces those decisions' summaries plus
lifecycle heads (`evolved_head`, `replacing_head`) as `additionalContext` — the decision arrives at
the moment its subject is being changed, unasked.

Mechanics, all existing:

- **Path → entries:** the `_entry_file_refs` scan (`semantic_cache.py`), continuity-aliased
  (`_continuity_alias_map`) — the same reverse lookup `retrieval-spec` path filters use. A derived
  index can come later if the linear scan ever matters; it does not at current corpus size.
- **Hook surface:** registered like `memory-retrieval-check.py` in `.claude/settings.json` plus the
  seed template under `memory_seed/seed/.memory-seed/hooks/` (both-locations rule), per-agent emit
  shapes copied from the existing hooks.
- **Rate limiting:** a stamp file keyed on (file, day) so repeatedly editing one file does not
  re-inject the same context every tool call.
- **Lifecycle honesty:** superseded decisions surface WITH their head pointed to — never hidden,
  never presented as current (Invariant #7; E7's over-authoritative-record failure mode).

## Interaction with the attention signal

Surfaced-by-trigger decisions are logged to the retrieval log with their own source tag
(`file_touch`), weight zero — a trigger impression must never inflate the attention score the
ranker may one day use. Same rule as search impressions.

## Acceptance criteria (when built)

1. Editing a file referenced by an entry's `F:` line injects that entry's summary + heads once per
   stamp window; editing an unreferenced file injects nothing.
2. A superseded matching entry surfaces its `replacing_head` prominently.
3. Hook failure is silent (fail-open) and never blocks the edit.
4. Fixture pair covering matched/unmatched paths and the renamed-file (continuity alias) case.
