---
title: "ADR reviewed-no-change recorder proposal"
date: "2026-08-10"
project: "memory-seed"
status: "proposed - design only, not built"
priority: "P2"
next_action: "JNL decides whether to approve building option (a); no build until then."
related:
  - "docs/CONSTITUTION.md"
---

# ADR `reviewed-no-change` recorder: closing the queue's silent half

Status: proposed (drafted by agent, 2026-08-10) - design only.

## Problem

The ESR ADR review queue (`adr_head_reviews`, closed R9 2026-08-10) now names both
answer paths verbatim for a stale head: propose a revision, or record
"reviewed-no-change". The revision path is a full CLI round-trip — `adr revise`
then `adr transition` — and works from either an agent's shell or a script. The
reviewed-no-change path has no equivalent. Its only writer is
`append_outcome_event` (`memory_seed/adr.py`), and the only caller that reaches
it is `session_append_entry`'s mandatory ADR review gate (`memory_seed/core.py`),
which only the MCP `memory_session_append` surface drives (`memory_adr_review`
context, answered with `{"adr_id": ..., "outcome": "no-change", "reason": ...}`).
The CLI has no equivalent — the ESR preamble says so in its own words: "no
standalone command."

That means a queue flag whose true answer is "nothing needs to change here" can
only be closed by authoring a full lifecycle-linked session entry through MCP.
The no-change case is exactly the one that should cost the least: a reviewer who
re-reads a decision and confirms it still holds is not doing new work, but the
only route to recording that confirmation asks them to write one anyway. A
CLI-only agent — or an MCP agent that has nothing else to say this turn — has no
way to answer the queue at all, so the flag either goes unanswered or gets
answered by manufacturing a pretextual entry just to reach the gate.

## The provenance question

Every `reviewed-no-change` outcome event carries `update_entry_id`
(`memory_seed/adr.py`, `AdrEvent.update_entry_id`) — this is the field
`append_outcome_event` requires and `adr.py`'s validation enforces
(`"{label} requires update_entry_id"`). The reviewing session entry is the
evidence: without it, a `reviewed-no-change` event is an assertion with no
author-visible trail back to *why* the reviewer believed the head still holds.
Any standalone recorder has to answer where that entry comes from. Three
options, in increasing distance from the current mechanism:

**(a) Point at an existing entry.** `adr reviewed --adr-id <id> --entry
<existing-entry-id> --reason <text>` requires the reviewer to name a real,
already-written session entry as the evidence — typically the entry from the
review turn itself, or an earlier one the reviewer is now re-affirming applies.
Keeps provenance exactly as strong as today's mechanism (a real entry backs the
event) at the cost of one extra lookup step: the reviewer must have (or find) an
entry id before the command will run.

**(b) Mint a minimal review entry.** The command authors a small session entry
of its own — title, a one-line D/R, no F/A needed — purely to carry the
`update_entry_id` the event requires, then writes the outcome event pointing at
it. Mechanically identical provenance to (a) with zero lookup cost, but every
no-op review adds a corpus entry whose entire content is "reviewed, no change" —
noise proportional to how often ADRs are reviewed and found fine, which by
design should be the common case once the queue is answered promptly.

**(c) Relax provenance for no-change events only.** Allow `update_entry_id` to
be optional (or a synthetic placeholder) specifically for `reviewed-no-change`,
on the reasoning that "nothing changed" needs no evidentiary entry the way a
revision does. Cheapest to build and cheapest to use, but it breaks the
every-outcome-event-has-an-entry invariant `adr.py` currently enforces
uniformly, and it does so asymmetrically: a CLI-only relaxation would let
`reviewed-no-change` events validate with looser rules than the MCP path
produces, which write-surface parity (Constitution Invariant #2, amended v1.3 —
"every write to memory to pass identical validation on any surface") exists
specifically to rule out. Loosening the CLI's rule without loosening MCP's would
recreate the exact asymmetry the v1.3 amendment closed; loosening both is a
larger, separately-justified change to what a `reviewed-no-change` event means,
not a small parity fix.

## Recommendation

(a): `adr reviewed --adr-id <id> --entry <entry-id> --reason <text>` (MCP twin,
`memory_adr_reviewed`, taking the same three fields). The reason is required,
not optional — a bare "reviewed, no change" with no reasoning is exactly the
kind of low-content record the corpus already has enough of, and requiring it
costs nothing extra now that the reviewer is already writing a `--reason`
string rather than a full entry. This keeps provenance at its current strength,
avoids (b)'s corpus noise, and avoids (c)'s parity risk. Ship it with the
ESR review-queue preamble updated to name the third path alongside the existing
two: revision (`adr revise` + `adr transition`), reviewed-no-change via a
lifecycle-linked entry (MCP `memory_session_append`'s review gate), and
reviewed-no-change via `adr reviewed` when the review itself does not warrant a
new entry.

Whatever ships must validate identically on CLI and MCP — the same `--entry`/
`--reason` (or `entry_id`/`reason`) fields, the same existing-entry-id check, the
same call into `append_outcome_event`. Two thin wrappers over one function, not
two independent implementations of the same rule.

## Explicitly out of scope

Building any of this. This document is a design proposal only — no CLI
subcommand, no MCP tool, and no change to `append_outcome_event` or the ESR
preamble ships with it.
