---
memory-system-version: 2.19
tags:
  - memory-seed
  - proposal
  - documentation
  - control-plane
priority: P2
next_action: "ACCEPTED 2026-08-07 (JNL) - not a JNL gate any more. Blocked on the ADR backlog draining (open question 4: 36/38 ADRs unanswered) plus open questions 1-2 (attach- vs write-time; head-only vs every grounded decision) before implementation starts."
---

# Only ADR-Attached Decisions Earn a Diagram

> **Status: ACCEPTED 2026-08-07 by JNL**, from JNL's own suggestion during the ADR-diagram build.
> The ADR-level mechanism it extends landed the same day (`55cc393`).
>
> **Open question 3 is resolved: the per-entry trigger list is RETIRED, not kept alongside.** JNL's
> reasoning, recorded verbatim in substance: the per-entry trigger is *shown to degrade and has no
> teeth*, whereas the ADR link plus an ESR pass can make it an effective rule. `session_logging.md`
> and its seed twin were updated in the same turn.

## The problem it answers

Decision diagrams are the most-ignored convention in the corpus:

| period | entries | diagram blocks | rate |
|---|---|---|---|
| 2026-05 → 06 | 154 | 0 | 0% |
| 2026-07 | 629 | 43 | 6.8% |
| 2026-08 (to the 7th) | 86 | 2 | 2.3% |

The existing rule is a judgment call per entry — `session_logging.md` lists positive triggers
(topology, migration, schema/compatibility flow, concurrency, command lifecycle, retrieval pipeline)
and asks the author to decide. Two things follow from that:

1. **It cannot be enforced.** A keyword heuristic for "this entry needed a diagram" was prototyped
   against the real corpus, flagged **35% of all entries** (matching "worktree" in a passing
   validation line, "topology" in a feature name), and was rejected — a check that fires on one entry
   in three teaches its reader to skip it. That rejection is recorded in `esr.py`'s field comment.
2. **So it lapses silently**, and the numbers above are what that looks like.

ESR now reports the drift (`entries_since_last_diagram`), but reporting a lapse is not the same as
having a rule that can hold.

## The proposal

**A decision earns a diagram exactly when it is attached to an ADR.**

Not "when an author judges it structural". Attachment to an ADR is already a deliberate, recorded,
human-gated act — it means *this decision governs a standing concern*. That is a far better predictor
of "worth drawing" than any keyword, and it is mechanically determinable: the denominator is the set
of decisions appearing in ADR event ledgers, which is small, enumerable, and already validated.

### Why this is the right cut

- **The subjectivity moves to a decision already being made.** Nobody has to newly judge "is this
  structural?" — they judge "does this govern a concern?", which they are doing anyway when they
  attach it.
- **The denominator is tiny.** 7 ADRs currently carry a real decision head; 29 sit at `founding:`
  placeholders. Even fully populated this is tens of diagrams, not hundreds — and each one earns its
  place by definition.
- **It composes with what shipped.** The ADR-level rule (`55cc393`) already says every ADR owes an
  *answer*: a diagram, or `diagram_status: not_applicable`. This proposal supplies the principled
  reason an ADR would owe one at all, and extends the same obligation down to the decision that
  became its head.
- **It inverts the failure mode.** Today the rule covers everything and is therefore obeyed nowhere.
  This covers a little and can actually be enforced.

### What it would mean concretely

- A decision attached to an ADR (as head, or as grounded evidence) carries a diagram obligation.
- The obligation is discharged the same way as the ADR-level one: draw it, or record
  `diagram_status: not_applicable` with a reason. Mandatory to answer, not mandatory to draw.
- `grounded_in:` already links a diagram to the decisions whose shape it draws, so the evidence
  direction is built.
- Unattached decisions keep the current advisory rule. Nothing becomes *more* required than today.

## Open questions

1. **At attach time or at write time?** A decision is usually attached to an ADR after it is written,
   so the obligation arrives late. That is fine for an append-only sidecar, but it means the prompt
   belongs in the ADR review gate rather than in `session_logging.md`.
2. **Does grounded evidence owe a diagram, or only the head?** Attaching five supporting decisions
   should probably not mint five obligations. The head is the defensible minimum.
3. ~~**Does this retire the per-entry trigger list?**~~ **RESOLVED 2026-08-07 — yes, retired.** The
   trigger list degraded measurably and had no enforcement, while the ADR link plus an ESR pass can
   hold. The shapes it named survive as guidance for *what to draw* once a diagram is owed; they no
   longer govern *when* one is owed. Applied to `session_logging.md` (live and seed).
4. **Interaction with the ADR backlog.** 36 of 38 ADRs are currently unanswered. This proposal adds
   obligations on top of that backlog; it should land after the backlog is drained, or it will read
   as a second unpaid debt.

## Not proposed

- Any enforcement in `adrs check` (the ADR-level hard gate is already sequenced as a follow-up to
  `55cc393`).
- Changing the diagram sidecar format — `adr_id`, `grounded_in`, and `diagram_status` already carry
  everything this needs.
- Backfilling diagrams for existing ADR-attached decisions.
