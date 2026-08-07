---
memory-system-version: 2.19
tags:
  - memory-seed
  - proposal
  - topic-vocabulary
  - control-plane
priority: P1
next_action: none - accepted and implemented 2026-08-07; the topic swarm it unblocks is the next step
---

# Write-Time Topic Envelope: Closing the Leak

> **Status: ACCEPTED 2026-08-07 by JNL, and IMPLEMENTED the same day.** Successor to the **ACCEPTED**
> [`write-time-sidecar-consolidation-proposal.md`](write-time-sidecar-consolidation-proposal.md),
> whose build order this discharges. That document is accepted and is deliberately **not edited
> here** — this one carries the amendment for JNL to accept or reject on its own terms.

## The measurement that prompted this

JNL observed a drop in area/activity attribution per decision. Measured against the corpus on
2026-08-07:

| month | decisions | any topic | area+activity on the decision | decision-keyed | slugs/decision |
|---|---|---|---|---|---|
| 2026-05 | 51 | 100% | 100% | 100% | 2.73 |
| 2026-06 | 88 | 100% | 92% | 100% | 2.85 |
| 2026-07 | 942 | 99% | 95% | 92% | 4.27 |
| **2026-08** | **146** | **100%** | **52%** | **8%** | **2.10** |

Coverage did not fall — *granularity* did. Decisions still carry topics; they inherit them from the
entry instead of owning them. **Only 7 of 86 August entries have any topic sidecar at all**, and 3
of those 7 were written during the session that produced this document.

## Cause

Not agent discipline. `memory_session_append` (MCP) has required the `decisions` envelope since
`0e738ba` (2026-07-31), so those writes cannot have come through it. Two paths remain open:

1. **`memory-seed session append` accepts `--topics`** as an optional alternative to
   `--decisions-file`. Entry-level slugs, no sidecar, no decision keying.
2. **`session_logging.md:86` documents exactly that form** — `[--topics a,b]` — and never mentions
   `--decisions-file`. Every agent reading the canonical logging skill is taught the leaking path.

(2) is the more important half. A flag nobody is told to use leaks nothing; a skill that teaches the
wrong form leaks continuously.

## Proposal

### A. Discharge step 3 of the accepted build order

> 3. **Flip `session append` / `memory_session_append`** to fold `--topics`/`--related`/`--replaces`/
>    `--evolves` into the sidecar. Read path already unions, so this is invisible to consumers.

- `session append` requires the decision envelope. `--topics` continues to parse, but folds into the
  envelope as an entry-level attribution rather than writing entry YAML, and warns that it is doing
  so. A decision without one Area and at least one Activity is refused, exactly as MCP refuses it.
- `session_logging.md:86` is rewritten to document the envelope form first. **This is the change that
  actually closes the leak** and should land even if the CLI flip is deferred.

### B. New: a topic REQUEST, flagged rather than blocked

The gap JNL identified: an author who needs a slug the vocabulary lacks currently has two bad
options — force-fit an existing slug, or be blocked at write time.

Proposed: a `proposed_topic:` field on the decision envelope. It is **never** a topic. It:

- does not enter `topics.yaml`, does not resolve, and is never returned as an attribution;
- is written into the topic sidecar as a flagged request alongside the (still mandatory) real
  Area + Activity, so the write is never blocked;
- is surfaced by the ESR pass as a queue for adjudication, with the decision that requested it as
  evidence;
- becomes vocabulary only by a human editing `topics.yaml`.

This preserves the PROPOSE/ASSIGN split that `scripts/propose_topic_children.py` already enforces —
*"PROPOSE ... **cannot write to the corpus at all**"* — and honours the promotion rule recorded in
`topics.yaml`: **evidence, not taste.** A request accumulates evidence; it never becomes a slug by
being used.

## Sequencing, and why it comes before the swarm

201 decisions across 115 entries currently lack decision-keyed Area+Activity (117 with no
area+activity from any source; 84 on multi-decision entries where only a shared inherited list
exists; a further 50 are excluded as single-decision entries whose entry-level pair already says
everything a keyed one would).

That is a topic-swarm backlog. **It should not be run before this proposal lands.** The accepted
document is explicit: *"The sequence matters, because a sweep is worthless until there is a single
place to compare against."* Backfilling now means mopping with the tap running, and repeating the
campaign in a fortnight.

## Carried-forward open question

The accepted proposal's own caveat still stands and still gates how much the eventual sweep is
worth: the aborted pilot scored the swarm against authored topics **as if authored were ground
truth**. If both sides are model judgments, 0.613 is inter-annotator agreement, not accuracy. Leg B
— per-decision attribution against free inheritance, which measures the campaign's actual value —
never ran. Resolving it does not block anything proposed here.

## As implemented (2026-08-07)

One deliberate deviation from A, and the reason for it:

- **Both axes are now mandatory whenever the envelope is used**, in `core` rather than only in the
  MCP JSON schema — so the CLI and MCP paths finally agree. A decision without an Area, or without at
  least one Activity, is refused on both.
- **The legacy flags WARN rather than refuse.** Refusing outright would break any script still
  passing `--topics` mid-flight, for no gain the warning does not already deliver: the warning names
  the cost and the replacement, and the doc fix removed the instruction that was teaching the wrong
  form in the first place. Tightening to a refusal is a one-line change once the corpus stops
  producing entry-level writes; the ESR attribution-gap count is the signal for when that is safe.
- `proposed_topic` landed as specified, plus an addition JNL asked for: it is an object
  `{slug, axis}` rather than a bare slug, because a request nobody can place on an axis cannot be
  ruled on. Refused if the slug already resolves; rendered under its own `proposed_topics:` key
  (never inside `topics:`, which every reader treats as resolvable vocabulary); surfaced in the ESR
  Topics section with its axis and the requesting decision as evidence.
- **Assigned topics now declare their axis too**, in the nested shape `entry_topic_sidecars` has
  read since 2026-07-27 but no writer emitted:

  ```yaml
  topics:
    area:
      - lifecycle-edges:d1
    activity:
      - bugfix:d1
  proposed_topics:
    activity:
      - swarm-orchestration:d1
  ```

  The flat form left the axis to be looked up in `topics.yaml`, so a sidecar could not be read on
  its own terms. The nested form degrades safely — a reader that does not know the sub-keys still
  collects the same `- ` lines, seeing a correct if axis-blind list rather than none.

## Not proposed

- Changing the vocabulary itself, or the 3-slug-per-decision cap.
- Running the topic swarm (blocked on this).
- Retrofitting entry-level attributions already written; that is the sweep's job, afterwards.
