---
title: ADR lifecycle sidecar contract
status: draft
spec_binding: draft
parent: ../../2_Todo/memory-seed-semantic-record-and-signal-foundation-plan.md
---

# ADR Lifecycle Sidecar Contract

Status: **DRAFT - NOT IMPLEMENTED**. This contract becomes live only after the walking skeleton and validator
are accepted.

*Amended 2026-07-26. Brought onto the first-hand / reconstructed split and the explicit `source:` provenance
field accepted in
[write-time-sidecar-consolidation-proposal.md](../../2_Todo/write-time-sidecar-consolidation-proposal.md).
This is an alignment pass on a draft, not a ratification: status stays `draft` and no runtime state is
created.*

## Authority

One append-only Markdown sidecar is authoritative for an ADR's promotion, stable identity, and lifecycle.
The original and decision-update entries are authoritative for narrative rationale and evidence. Current
project files and live specs remain authoritative for what is implemented now. Registries, databases,
`current_status`, and UI views are derived.

## Shape

Candidate location: `.memory-seed/decisions/<adr_id>.md`, one file per ADR. The directory is introduced only
when this draft is adopted; this documentation pass does not create runtime state.

```markdown
---
schema_version: 1
adr_id: adr_...
source_entry_id: mse_...
source_decision: d1
title: Use SQLite for the local index
topics:
  - storage
created_at: 2026-07-16T14:20:00Z
user_initials: JNL
agent_type: claude
agent_name: Claude Fable 5
source: write-time
---

## Proposed - 2026-07-16T14:20:00Z

update_entry_id: mse_...
source: write-time

## Accepted - 2026-07-16T16:10:00Z

update_entry_id: mse_...
expected_previous_status: proposed
source: write-time
```

`user_initials`, `agent_type`, and `agent_name` are the same three fields a session entry carries, and they
mean the same thing here: who the work was *for*, and which agent performed it. They are not a provenance
signal — see the next section for why `source:` is a separate field rather than something inferred from them.

Frontmatter identity fields are fixed after creation. Corrections, topic changes, status changes, rejection,
and supersession are appended transition blocks. `current_status` is the result of replaying the single valid
transition chain and is never authored as a second state field.

CLI and MCP writers should use one shared core operation, but the file remains directly readable and editable.
A direct append — by a person editing the file, or by an agent writing it outside the CLI — is authoritative
when it satisfies the same schema and validation rules; tooling must not claim exclusive ownership of
repository memory.

## First-hand and reconstructed

**The split this contract records is first-hand versus reconstructed, not human versus machine.** In this
repository the author is, in practice, an LLM: the decisions an ADR promotes were written by an agent, and
`user_initials` records who the session was *for*. So "what the author knew at write time" cannot mean "what a
person knew" — it means **write-time**, and the honest contrast is:

- **First-hand.** The agent had just made the decision when it marked the decision architecturally
  significant. It knows the alternatives it rejected and the constraint that forced the call, because it was
  the one doing the work.
- **Reconstructed.** A later sweep reads finished prose and infers, from the entry text alone, that a decision
  looks architecturally significant. It has the record, not the work.

That difference is real and worth preserving. It is not a difference in *species of author*, and this contract
does not treat one as trustworthy and the other as suspect on those grounds. It treats them differently
because one observed the decision and one is inferring it.

Measured support for the asymmetry: the topic-swarm pilot (aborted 2026-07-26) scored a cold sweep at
**0.583 / 0.613** macro-recall against what the write-time agent produced. That is weak as a *source* and
reasonable as a *check for omissions*, which is exactly the role the sweep is given below. The caveat carried
over from the pilot applies here too — if both sides are LLM judgments, that figure is inter-annotator
agreement rather than accuracy, and nobody has adjudicated who is right when they disagree.

### Provenance is a declared field, never a position

`source:` is declared **on the block**. It is never inferred from which file a value sits in, which tool wrote
it, or which of `user_initials` / `agent_type` / `agent_name` is populated. This mirrors the consolidation
proposal's rule for the topic and link families, and it uses that proposal's vocabulary rather than a second
one:

| Value | Meaning |
|---|---|
| `source: write-time` | the judgment was made in the same act that did the work |
| `source: derived` | the judgment was reconstructed later from finished prose |

It appears in two places, meaning the same thing in both:

- **On frontmatter**, it records where the *promotion judgment* originated — whether the decision was marked
  architecturally significant by the agent that made it, or proposed by a later sweep and then approved.
  It is an identity field: fixed after creation, like the rest of the frontmatter.
- **On each transition block**, it records where *that transition's* judgment originated.

A missing `source:` is a validation error, not a default. Inferring it would reintroduce exactly the implicit
second derivation this field exists to remove.

## Source decision identity

*Amended 2026-07-20 (JNL). The earlier text proposed, for legacy sources, "a sidecar-owned stable decision
key plus an exact heading path and optional source-text fingerprint". That is withdrawn: three mechanisms
to solve a problem the entry already solves.*

**A decision is identified by the pair `(source_entry_id, source_decision)`** — nothing else. The entry id
already fixes the location, so the ordinal only has to be unique *within* that entry:

```yaml
source_entry_id: mse_77cn2v0rg9na3w0v
source_decision: d1
```

### The ordinal is derived, never authored

No entry is edited to carry decision metadata. The ordinal is read from the structure the DRAFT grammar
already imposes, which covers every shape in the corpus.

*Amended 2026-07-22 (JNL), refreshed 2026-07-26. The counts below replace the hand-derived 2026-07-20
figures (125 / 346 / 1 / 140, totalling 612), which no classifier reproduces. They come from a committed
classifier, `scripts/count_decision_shapes.py` — re-run it rather than re-deriving by hand.*

**Population.** Every count in this section is the **stamped-heading population**: entries split by
`_ENTRY_HEADING_RE`, which requires a `## YYYY-MM-DD HH:MM - title` heading. That is the same splitter
`links check` validates against, so what is counted here and what a decision ref is checked against are the
same set by construction. Id-less / date-only legacy headings — the May-2026 entries written before the
timestamp convention — are **excluded**; there are 25 of them, and the looser boundary the semantic-cache
chunk extractor uses admits them for 661. Figures measured at commit `0dc423b` (2026-07-26).

| Entry shape | Count | Ordinal |
|---|---|---|
| `#### D1 - name`, `#### D2 - name` | 186 | from the heading number |
| singular `### Decision` | 407 | **`d1` by convention** — a single decision is the first decision |
| `### Decisions` with inline `- D1:` bullets | 1 | from the bullet label |
| no decision section | 42 | nothing to identify; not an ADR source |

Total **636 entries**, of which **593 carry at least one addressable decision** and **163 carry two or
more**. Those two figures are what `_entry_decision_ordinals` actually returns, not a sum of the table, so
coverage and validation cannot drift apart: the inline-bullet entry is a shape the table recognises but
yields no ordinal under the current implementation, which is why 186 + 407 = 593 and the inline row adds
nothing to it.

**Why the earlier numbers did not reconcile.** Both prior figures were re-derived on 2026-07-26 by running
today's classifier against the git trees of the days that produced them (`7d39214`, end of 2026-07-20;
`0f69e48`, end of 2026-07-21). The two disagreements have *different* causes:

- **The 2026-07-21 recount's 580 is real, and it is a looser-splitter count.** Its numbered (131) and
  singular (382) buckets sit between the end-of-20th and end-of-21st measurements (125 → 136 and
  369 → 383), placing it mid-day on the 21st; and its no-decision bucket of 66 matches the **date-only
  tolerant** splitter's 67, not the stamped splitter's 42. Under that boundary the same instant totals 581.
  So 580 and the stamped-splitter numbers were never in conflict — they counted different populations and
  neither said which.
- **The 2026-07-20 hand count's 612 is not reproducible under either splitter.** At that tree the
  classifier finds 537 stamped / 562 date-only-tolerant. Its numbered (125) and inline (1) are exactly
  right; the error is concentrated in the no-decision bucket, which claims 140 against a measured 42
  (stamped) or 67 (tolerant). The discrepancy decomposes cleanly: the total is 50 too high (612 − 562)
  while the no-decision bucket is 73 too high (140 − 67), and the 23-entry difference is exactly the
  singular shortfall (346 against a measured 369). So it is two errors, not one — roughly 50 non-entries
  swept in, *plus* roughly 23 real singular-decision entries misfiled as having none. The corpus holds one
  obvious population shaped like an entry heading but carrying no decision section: the `links/` and
  `diagrams/` sidecar families, which on 2026-07-20 held **99 such sidecar headings** (72 + 27) and are not
  session entries. A sweep that globbed `sessions/**/*.md` without excluding sidecars would absorb them
  exactly there. No subset reproduces 612 on the nose, so 612 is **superseded, not reconciled**.

**There was never a fall.** The premise that made this look impossible — 612 dropping to 580 under an
append-only corpus — dissolves once 612 is discarded as inflated: the measured stamped totals rise
monotonically, 537 (07-20) → 562 (07-21) → 636 (07-26).

Two buckets corroborate that the classifier itself is stable rather than drifting: **no decision section
is 42 at all three snapshots**, and the date-only legacy heading count is **25 at all three**. Those are
precisely the buckets append-only growth cannot move — new entries all carry a decision section, and no new
May-2026 date-only headings can appear — so the whole **+99 entries (537 → 636)** between 07-20 and 07-26
is corpus growth.

**Cross-checked against the other splitter's own implementation**, not just against a restatement of it:
`extract_memory_chunks` emits exactly one entry-level chunk per stamped entry plus one per date-only legacy
heading — 636 + 25 = **661** at `0dc423b`, re-verified at 662 against 637 + 25 one commit later. Of those
chunks, 628 carry an `entry_id`; the 34 that do not are the 25 date-only May-2026 headings plus 9 stamped
entries written before the id convention. Note that the population above is defined by **heading shape, not
by id presence**: those 9 stamped-but-id-less entries are counted, and only the 25 date-only ones are
excluded. Anyone re-deriving these numbers should filter on the heading, not on `entry_id`.

None of this disturbs the ADR's argument. The singular-to-`d1` convention is what makes the scheme total
rather than partial, and it holds at every one of these counts: without it the 407 single-decision entries
— still the clear majority — would have no addressable decision at all, and they are exactly the entries
most likely to hold one clean architectural call.

### Why not the section slug

Section chunks already exist for many decisions
(`mse_77cn2v0rg9na3w0v#decisions/d1-80-bit-generated-entry-ids`), and that anchor stays: it is how a
reader *retrieves* the decision text, and it is stable because entries are append-only.

But it is an **address, not an identity**, and it must not become the key:

- It is not total. A singular `### Decision` yields `#decision` with no ordinal; inline-bullet decisions
  yield no sub-anchor at all. The pair works for all three shapes.
- It carries the heading text, so the key would encode the title
  (`d1-rollup-lives-in-the-service-entryrollup-lense-adapts-presentation-only`) and change meaning if a
  title were ever reworded.
- It is longer than it needs to be for a value that is compared, indexed, and stored on every transition.

So: **compute on the pair, retrieve by the slug.** They are consistent — the slug's `dN` segment is the
same ordinal — but only one of them is the key.

### What this deletes

- No sidecar-owned decision key. Identity is derived from the source, not invented by the referrer.
- No heading path. The entry id already locates the decision.
- No source-text fingerprint. Append-only already guarantees the source cannot drift, so a fingerprint
  adds a failure mode (formatting changes break it) in exchange for a guarantee already held.

## The sidecar lifts; it does not mirror

The ADR sidecar records **which decisions are architecturally significant, and their lifecycle**. It does
not assign identity, and it is not a projection of every decision.

The corpus holds 876 addressable decisions across the 636 stamped entries counted above (`0dc423b`,
2026-07-26; 710 at the 2026-07-22 recount, and the earlier 471 was the superseded 612-entry table's sum).
It should not hold 876 ADRs. Most session decisions are
tactical — a scroll band, a lint message, a test rename — and stay entirely in their entry. An ADR is
created when a decision constrains future work in a topic area, and `topics:` is what groups them, so
"the storage decisions" or "the retrieval decisions" is a query rather than a folder.

This is the division of labour that makes both halves simple: **the entry owns what was decided; the
sidecar owns which of those decisions still governs.**

## Promotion authority — the sweep proposes, it never promotes

A decision may be marked architecturally significant **at write time**, by the agent that just made it. That
is the primary path, it is first-hand, and it is the only path that produces `source: write-time`.

A later sweep may **propose** promotion for decisions that received nothing at write time. That is its whole
job here: find omissions, not re-judge what was already judged.

**The rule, stated once: a swarm may never create an ADR sidecar or append a transition block.** Its output is
a promotion *candidate* in the ordinary suggestion channel — the same posture `link_swarm` already holds under
Invariant #5 — and a human-approved run of the promotion operation is what writes the file. The resulting
frontmatter then carries `source: derived`, which preserves the fact that the judgment was reconstructed even
though a person approved it. Provenance records where the judgment came from; approval records who let it in.
Those are two different questions and the file answers both.

So, without inference:

| Movement | May a sweep propose it? | Who commits it |
|---|---|---|
| create an ADR (first promotion) | yes, as a candidate | human approval, always |
| proposed → accepted | yes, as a candidate | human approval, always |
| proposed → rejected | yes, as a candidate | human approval, always |
| accepted → superseded | yes, as a candidate | human approval, always |

There is no row where a sweep writes. This is the plan's stated non-goal — *"no automatic ADR promotion or
confidence-to-authority upgrade"*, and *"leave historical records legacy/unclassified unless a human
explicitly promotes a decision"* — carried into the file format rather than left as a policy sentence
somewhere else.

Note the asymmetry with the topic and link families, which is deliberate. There, a sweep appends `source:
derived` blocks directly, because a wrong topic slug is cheap to retract. Here, the existence of the sidecar
*is* the promotion, so a written block is already an authority claim. Same vocabulary, stricter gate.

## Transition rules

- Every transition references exactly one `decision-update` entry, which is a first-hand record by
  construction: it is written by whoever is making the transition, at the moment they make it.
- The update entry names the ADR, expected previous status, new status, the session's `user_initials` and the
  acting agent, timestamp, rationale, and evidence references.
- Every transition block declares `source:`. In practice this is `write-time`; `derived` records that the
  transition originated as a sweep candidate and was then approved, per the section above.
- Allowed status transitions are versioned by schema. The initial set is proposed -> accepted/rejected and
  accepted -> superseded. Reconsideration requires an explicit later schema decision.
- Supersession names the replacement ADR; the inverse is computed rather than hand-maintained.
- Competing transitions from the same previous status are a conflict requiring explicit resolution, never a
  last-writer-wins merge.

## Validation

Validation must detect duplicate ADR IDs, broken source selectors, missing update entries, transition/order
errors, competing heads, unknown topics, malformed timestamps, and invalid supersession. It reports repair
guidance but does not silently mutate authored memory.

Provenance adds two checks, and both are errors rather than warnings:

- **Missing `source:`** on frontmatter or on any transition block. There is no default value; a block that
  does not say where its judgment came from is unvalidatable, not permissive.
- **`source:` outside `write-time | derived`.** A closed set, for the reason
  [provenance-authority-crosswalk.md](provenance-authority-crosswalk.md) records at length: a field validated
  only as "a non-empty string" is how an undeclared parallel vocabulary gets in.

Derived readers may report the write-time/derived split — how many ADRs originated first-hand versus from a
sweep — and that count is only honest because the field is declared rather than inferred.

## Derived readers

Readers may derive current status, transition timelines, topic indexes, supersession chains, and Trace
projections. Every value retains source sidecar and entry references, and a full rebuild from repository
Markdown must produce equivalent output.
