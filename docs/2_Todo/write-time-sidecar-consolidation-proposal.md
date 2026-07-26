---
priority: P2
next_action: ACCEPTED 2026-07-26 by JNL. Build in order — (1) block format + `source` provenance field, (2) sidecar-first write ordering, (3) flip `session append`/`memory_session_append` to fold into the sidecar, (4) branch-scoped swarm sweep. The sweep is worthless until there is a single place for it to compare against. Step 4's weighting depends on the pilot-adjudication outcome; steps 1–3 do not.
---

# Write-time consolidation: topics and links live in the sidecar

Status: **ACCEPTED 2026-07-26 by JNL** (raised the same day). The conversation started from "all links
should live in the link sidecar" and arrived somewhere better by separating *where the author writes*
from *where the data lives*.

**Constitution v1.6** was ratified alongside this acceptance and supplies its governing clause:
provenance is **first-hand vs reconstructed, not human vs machine**, and must be *declared on the
record rather than inferred from where it is stored*. That is precisely the `source` field in step 1 —
so the design is no longer merely permitted by Invariant #6's partitioned authority, it is required by
Invariant #4's clarification. The mutability question flagged below is answered by the same amendment:
it is a §4 Policy change, since v1.6 adds and removes no capability.

## Problem

Topics and lifecycle edges have **two authored homes**: the entry's own YAML (written by
`session append` / `memory_session_append`) and the append-only sidecars (written afterwards). The
effective set is `union(entry YAML, sidecar)`, merged at read time.

Measured 2026-07-26 over 645 entries:

| | entry YAML | sidecar | both |
|---|---:|---:|---:|
| lifecycle edges | 671 edges / 454 entries | 595 edges / 362 entries | **294 entries** |
| topic slugs | 1,023 slugs / 439 entries | 0 | 0 |

294 entries populate both link homes. There is **no rule** saying which to use — an author picks, and
nothing validates the choice. That is the actual defect. "Two places" is a symptom.

Topics are the mirror image: everything is in entry YAML and the sidecar family, though built and
validated, is empty. So consolidating topics does not remove a split — it prevents one forming.

## The design

**Authoring does not change. Storage does.**

An agent still passes `--topics` / `--related` / `--replaces` / `--evolves` to the same gated tool.
That tool, as part of its run, folds those values into the entry's **sidecar block** instead of the
entry's YAML. One surface to write through; one place the data lives.

This matters because the two things were being conflated. Every objection raised against
"consolidate into the sidecar" was really an objection to *changing how authors work* — a separate
file to remember, a second step to forget. Keeping the authoring surface identical removes all of it.

What survives unchanged:

- **All nine write-time guards** (chronology, ref existence, forward-only lifecycle edges, topic
  vocabulary, id collision, DRAFT format, …) — it is the same gated tool, so **write-surface parity**
  (Invariant #2, v1.3) is untouched.
- **`dry_run`** still returns the byte-exact block a real call would append.
- **Append-only.** A sidecar block is appended, never rewritten.

### Provenance becomes explicit rather than positional

Today "authored vs inferred" is encoded by **which file** the value sits in. That is fragile, and it
is exactly the implicit second derivation `graphCommunities.ts` warns about — *"two derivations are
how a legend ends up quietly lying."*

With both in the sidecar, the distinction must become a **declared field on the block** — e.g.
`source: write-time` vs `source: derived`. This is strictly more honest than inferring it from a path,
and it is what lets `topics check` keep reporting an honest split between what an author declared and
what a sweep suggested.

**One correction this proposal forces into the open.** The current contract describes entry YAML as
what "the author knew at write time". In this repository the author is, in practice, an LLM: every one
of the 1,023 YAML slugs and 671 YAML edges was chosen by an agent, with `user_initials` recording who
the session was *for*. The honest distinction is **first-hand vs reconstructed** — an agent writing
the entry has just done the work; a sweep reading finished prose is reconstructing. That difference is
real and worth preserving, but it is not human-vs-machine and the contract should stop implying it is.

### Precedence: `source` outranks recency

*Added 2026-07-26 — a hole found while aligning the ADR contract, and closed rather than left open.*

Sidecar precedence today is **most-recent-wins**. Once write-time values live in the sidecar, that
sort would order first-hand and reconstructed blocks against each other, and a `derived` block
appended later would supersede a `write-time` one **on recency alone**. That directly contradicts
Constitution v1.6, which holds the two are *not equal evidence*.

**The rule has two halves** (second half set by JNL 2026-07-26, correcting a first draft that made
write-time values permanently uncorrectable):

1. **A `derived` block never *implicitly* supersedes a `write-time` block.** Precedence is
   `(source rank, then recency)`, not recency alone. Within a source class, most-recent-wins is
   unchanged. So a sweep appending later cannot quietly win by being newer.
2. **A `derived` block may override a `write-time` value only through an explicit `retracts:` naming
   it — and that retraction is reviewed by a human before it is written.** The override is possible,
   but it is a stated act rather than a side effect of ordering, and it is gated.

Half 1 alone would have been wrong. A write-time agent *can* be mistaken, and a sweep reading the
finished record sometimes has the better view — freezing first-hand values would forfeit exactly the
corrections worth having. What the two halves together preserve is that a reconstructed value never
displaces a first-hand one **silently**: it must say what it is retracting, and a person must agree.

This also keeps the mechanism honest with Constitution v1.6. "Not equal evidence" does not mean
"reconstructed is never right"; it means the burden sits on the reconstructed side, which is precisely
what an explicit, reviewed retraction expresses.

Consequence for the sweep: its default candidate set is **subjects with no write-time value** — cheap,
and it does not re-judge what the write-time agent already answered. Proposing a retraction of an
existing value is the deliberate, rarer second mode.

**Implementation note — this is not free for topics.** `retracts:` exists today for *links* only
(built 2026-07-25, with `malformed-retract` / `dangling-retract` / `retract-before-declaration`
validation), because a link edge is an independent assertion. Topics deliberately have no retract
construct: they supersede per entry, wholesale, on recency. Half 2 therefore requires extending a
retract-shaped mechanism to the topic family, or the cross-source override has no way to be *stated*
and would fall back to the implicit ordering half 1 forbids. Step 1 of the build order must cover
this; see `sidecar-supersession-model.md`, which currently documents topics as retract-free.

### The swarm becomes a sweep, not a source

Once write-time values land in the sidecar, a swarm's job is to find **lagging fields** — the relation
to something from three months ago that the author had no reason to think of. It compares against a
single place and appends to that same place.

This is the role the measurements support. The pilot (aborted 2026-07-26) scored a cold swarm at
**0.583 / 0.613** macro-recall against what the write-time agent produced. Weak as a *source*;
perfectly reasonable as a *check for omissions*, where the baseline is nothing at all.

It also fits the merge moment. A branch carries 1–5 entries, and `link audit` already generates
candidates deterministically from shared `F:` files and topics — now ranked with semantic scoring at
74% recall@5. So a sweep judges tens of pairs, not the 1,108 the campaign faced. **The backlog never
rebuilds**, because linking stops being a campaign and becomes a step.

Constraint that decides where it goes: **Invariant #1 — the core runs with no network.**
`session merge-branch` is core; a swarm needs network. So the sweep is a step in the merge *workflow*,
never inside the merge command. Extend the existing `link_swarm` skill with a branch-scoped mode
rather than building a second mechanism.

## Atomicity — the one real implementation risk

`session append` writes **one** file today (`write_text_file` → plain `path.write_text`, no
temp-and-rename). Under this proposal it writes **two**: the entry and its sidecar block. A crash
between them leaves inconsistent state.

The failure modes are not symmetric, and that is the cheap answer:

| Order | Crash leaves | Detected? |
|---|---|---|
| entry first, sidecar second | an entry with no topics/links | **No** — indistinguishable from a legitimately unlabelled entry |
| **sidecar first, entry second** | a sidecar block naming an entry_id that does not exist | **Yes** — already an error class (`orphan-topic-sidecar`, dangling link refs) |

**Recommendation: write the sidecar first.** It converts a silent, permanent data loss into a loud,
already-implemented validation error, with no new machinery. `links check` catches it on the next run
and the fix is to re-append.

Options considered and their cost:

- **A — ordered writes (recommended).** Zero new machinery; relies on `links check` being run. The
  window is milliseconds and the failure is self-announcing.
- **B — temp-write both, then `os.replace` both.** Narrows the window further but is still not atomic
  across two files; adds a temp-file dance to a path that currently has none. Buys little over A.
- **C — real two-file atomicity** (write to a staging dir, single rename of a directory). Genuinely
  atomic on POSIX, unreliable on Windows, which is the primary platform here. Rejected.
- **D — keep one file: emit the sidecar block only, and have the entry carry no topics/links.** This
  is what the proposal already does — "two files" means *entry prose* and *sidecar*, which the corpus
  writes separately today anyway when a diagram is authored. A is sufficient.

## What this does NOT achieve

**The legacy tail is permanent.** Invariant #2 forbids rewriting 645 published entries, so 671 edges
and 1,023 slugs stay in entry YAML forever. Readers union both channels indefinitely and **no reader
code simplifies**. What you get is that the split stops growing and everything from the cutover lives
in one place. "One location" is true for new work, not for the corpus — this should be stated plainly
wherever the change is documented, or it will be read as a promise it cannot keep.

**Write-time declarations become correctable.** Sidecar blocks carry `retracts:` and most-recent-wins
precedence; entry YAML is frozen. Folding write-time values into the sidecar makes an author's own
declaration as revisable as a machine suggestion. Defensible — both paths are append-only and audited
— but it is a deliberate change in mutability, not a side effect, and should be ratified as one.

**Entry self-description is reduced.** Opening a session file will no longer show what an entry is
about or relates to. Mitigating precedent: diagram sidecars already work exactly this way, and nobody
finds a sibling file unnatural. Invariant #6's promise is that a person can read the source with no
service — a sibling Markdown file honours that.

## Governance

Invariant #6 already permits "narrowly scoped Markdown sidecars to own declared fields or lifecycles
while entries retain rationale/evidence". This proposal moves a field from one Markdown owner to
another and gives it **exactly one** owner, which is closer to #6's letter than the status quo. So:

- **§4 Policy change** plus contract updates (`graph-edge-contract.md`,
  `lifecycle-edge-linking-sidecars.md`, `decision-level-topic-sidecars.md`) — yes.
- **Invariant amendment** — not obviously required. Confirm against §11 before building; if the
  mutability change above is judged to touch Invariant #2's meaning, it needs an amendment and this
  proposal should not proceed without one.

## Build order

The sequence matters, because a sweep is worthless until there is a single place to compare against.

1. **Block format + `source` provenance field**, in both the link and topic sidecar contracts —
   **plus a retract-shaped construct for topics**, which today have none (links already have
   `retracts:`). Without it the cross-source override in the precedence rule cannot be *stated*, and a
   `derived` value wanting to correct a `write-time` one would have no legal way to say so.
2. **Ordered write** (sidecar first), with a test asserting the crash-between-writes state is the
   *detected* one.
3. **Flip `session append` / `memory_session_append`** to fold `--topics`/`--related`/`--replaces`/
   `--evolves` into the sidecar. Read path already unions, so this is invisible to consumers.
4. **Branch-scoped sweep mode** on `link_swarm`, invoked from the merge workflow, never from
   `merge-branch` itself.

## Open question carried in from the pilot

The aborted pilot scored the swarm against authored topics **as if authored were ground truth**. If
both sides are LLM judgments, 0.613 is inter-annotator agreement, not accuracy — and nobody has
adjudicated who is right when they disagree. Leg B (per-decision attribution vs free inheritance),
which measured the campaign's actual value, never ran because Leg A gates first. Resolving that
changes how much weight step 4's sweep deserves, but does not block steps 1–3.
