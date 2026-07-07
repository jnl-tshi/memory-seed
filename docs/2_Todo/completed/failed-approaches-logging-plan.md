---
memory-system-version: 2.13
tags:
  - memory-seed
  - plan
  - session-logging
---

# Failed-Approaches Logging Nudge - Scope

> **Status: IMPLEMENTED 2026-07-03 (unreleased).** The one-sentence rule below was added to
> `session_logging.md`'s Reason Rules (live + seed twin) as specced. Source: external review doc
> `Memory-Seed Logic Capture Improvement.md` (its "Fail-Fast" documentation protocol, credited
> there to the Basic Memory framework).

## Motivation

`session_logging.md`'s Reason Rules already document an `A` (Alternatives) field: "Alternative
considered or rejected, with reason, if it mattered. (optional)." But "considered and rejected" and
"attempted and failed" are different in kind. A considered-but-untried alternative is a judgment
call; a failed attempt is empirical evidence - proof that a specific approach doesn't work in this
codebase, for a specific reason. Losing that evidence means a future session (a different agent, or
the same one months later) can waste real time rediscovering the same dead end. This is the same
failure mode the existing **POC-gate** Working Principle exists to prevent going forward
("prove a new pipeline on one throwaway case before scaling it") - this item is the matching rule
for recording it after the fact.

## What Exists Today

The `A` field is optional and framed around judgment ("if it mattered"), with no explicit prompt to
record an attempted-and-failed approach specifically. Nothing currently distinguishes "I thought
about X and chose not to" from "I tried X and it broke."

## Design

One sentence added to `session_logging.md`'s Reason Rules, no new field and no schema change:

> If an approach was **attempted and failed** or proved incompatible during the session, log it
> under `A` even when not explicitly asked to - this is empirical evidence for future sessions, not
> an optional nicety. State what was tried and why it failed in one line; that's enough for a future
> agent to skip it without re-deriving the failure.

Kept as a single unified `A:` bullet (not a new `A-failed:`/`A-considered:` split) to avoid schema
churn - the existing format already allows multiple `A` bullets in an entry when more than one
alternative is worth recording, per the current multi-decision entry shape.

This stays as plain session-log evidence, not a new decision-graph edge type. If a later entry needs
to connect to the failed approach, use existing graph mechanisms (`related_entries` for contextual
relationship, or `supersedes` once shipped when a later decision explicitly replaces an earlier one)
rather than inventing a separate "failed" edge.

## Definition of Done

- One sentence added to `session_logging.md`'s Reason Rules (and seed twin).
- No code changes, no schema change, no version bump beyond the normal control-plane bump that
  accompanies any `session_logging.md` content change.
