---
priority: P3
next_action: SCOPE NARROWED 2026-07-23 — the "add a later edge to an already-blocked entry" case (the withheld-ledger driver, 8 edges) is SOLVED without amendment by link-sidecar block identity (entry_id, timestamp) - later declarations append new dated blocks (see lifecycle-edge-linking-sidecars.md). What remains here is only true IN-PLACE editing - diagram content refinement and link structure-repair/edge rewording - which still awaits JNL's shape decision; shapes touching link edges reopen ratified Invariant #2 (amendment 1.2) and need their own amendment.
---

# Sidecars as Editable Lenses — Conservative Refinement Proposal

Status: **PROPOSAL — needs design; scope narrowed 2026-07-23** (append-a-block landed as Evolution,
removing the additive-edge case from this proposal's scope). Raised 2026-07-23 by JNL while
ratifying Constitution v1.4.
Source: the v1.4 amendment discussion (diagram-sidecar syntax repair) and the maintainer's framing
that "sidecars act as lenses that improve the signal of the entry data, so a conservative but
editing-allowed approach to allow refinement" would benefit the corpus.

> This proposal is the **deferred half** of the v1.4 decision. v1.4 ratified the narrow, urgent case
> (repair a *diagram* sidecar whose Mermaid does not parse). The broader idea — that *any* sidecar is
> a refinable lens over its entry, under a standing conservative-edit posture — was deliberately not
> folded into that midnight bug-fix, because it reopens ratified amendment 1.2 and touches
> authoritative lifecycle data. It earns its own deliberate design. This doc captures it so it is not
> lost.

## The insight

A session entry is the primary record: the decision, its rationale, its evidence. A **sidecar**
(diagram or link) sits beside it and sharpens a particular signal — a diagram renders the decision's
shape; a link sidecar records the lifecycle edges an audit found. The maintainer's proposition: these
lenses would be more useful if they could be *refined* after the fact under a conservative, human-
gated standard, rather than being strictly frozen the moment they are written.

This is appealing because the alternative — "supersede with a whole new entry + new sidecar" — is
heavy for what is often a small sharpening (a clearer diagram, a corrected edge scope). The corpus
would carry higher-signal lenses if refinement were possible without a full superseding entry.

## The load-bearing distinction (verified, do not skip)

"Any sidecar" is **not one category.** The two sidecar types differ in what they *own*:

- **Diagram sidecar — a pure lens.** Owns no authoritative field. Its content is a rendering of a
  decision already stated in prose. Editing it changes no claim about the project. v1.4 already opened
  the narrowest slice of this (syntax repair).
- **Link sidecar — an authoritative owner.** Under Invariant #6 (amendment 1.1), a narrow sidecar
  *may own* lifecycle facts, and link sidecars do: they carry typed `supersedes`/`evolves`/`related`
  edges. **Verified 2026-07-23:** entry `mse_sewpap8b4q6sb0zj` declares no lifecycle edge in its own
  YAML, yet its link sidecar declares `evolves: mse_emv963patckeftx8`, and the Trail sources that edge
  from the sidecar (see `decision-level-link-sidecar-refs.md`). So a link sidecar is the *sole,
  authoritative home* of edges that shape the decision graph. Editing one edits an authoritative claim
  — which is exactly what amendment **1.2 walls off** ("typed lifecycle edges are never written into
  history [via curation]") and what the 2026-07-22 link-sidecar revert refused.

So a "refine any sidecar" posture is really two proposals with very different risk:

| Lens | Owns | Refinement risk | Precedent |
| --- | --- | --- | --- |
| Diagram | nothing (rendering) | low — no claim changes | v1.4 (syntax repair) already exists |
| Link | authoritative lifecycle edges | high — changes the decision graph | 1.2 forbids; 2026-07-22 revert |

## Design space (three shapes, in ascending weight)

1. **Diagram content refinement.** Extend v1.4 past *syntax repair* to *any conservative content
   edit* of a diagram sidecar (relabel a node, redraw a flow) — still fences-only, still human-gated,
   but no longer requiring the "was unrenderable" precondition. Low risk; owns nothing. The hardest
   question is where "refine the lens" ends and "revise the decision" begins, since a diagram can be
   edited to depict something the prose never decided.

2. **Link structure-repair only.** Allow fixing a *malformed* link sidecar (broken YAML, wrong date,
   duplicate block) but **not** editing any edge — the lifecycle claims stay append-only per 1.2. A
   middle ground that keeps 1.2 intact while removing the "no operation exists to fix a broken link
   sidecar" gap the 2026-07-22 revert surfaced.

3. **Editable link edges.** Let lifecycle edges themselves be refined (narrow an over-broad edge to
   `:d2` decision scope; correct a mis-typed edge). This is the fullest reading of the insight and
   **explicitly supersedes part of ratified 1.2.** The 2026-07-22 revert recorded that "the corpus has
   no sanctioned operation for narrowing an over-broad edge once written — which is itself the
   finding," so there is demonstrated demand. But it is the weightiest carve into Invariant #2 and
   needs the most care.

## Constitutional interactions (why this is amendment territory, not Evolution)

- **Reopens 1.2.** Shapes 2–3 touch typed lifecycle edges that 1.2 deliberately excluded from
  after-the-fact editing. Any of them is a change to a live invariant → §11 amendment, JNL-ratified.
- **One-off → standing.** The whole proposal shifts from 1.2/1.4's "one-off procedure, per-instance
  approval, no standing command" to a *standing conservative-edit posture*. That shift is the crux and
  must be chosen, not absorbed.
- **The control plane cannot self-verify the intent.** It cannot parse Mermaid, so it cannot confirm a
  diagram edit is a faithful refinement rather than a re-authoring; for link edges it *can* check
  structural narrowing (is the new edge a strict subset of the old scope?), which is why shape 3 is at
  least *machine-bounded* in a way diagram content is not. This asymmetry should shape the gate design.

## Open questions

- What does "conservative" mean operationally, per lens type? A machine-checkable predicate, or a
  human judgment at approval time (the 1.2 model), or both?
- Provenance: an edited lens should carry an audit trail (who refined it, when, from what). Where does
  that live — a new sidecar field, a session entry, a commit trailer — without itself becoming
  mutable?
- Is a standing command acceptable at all, or does the conservative posture still land as a one-off
  procedure invoked per refinement (as 1.2/1.4 are)?
- How does refinement interact with the fuse machinery's two append-only guards (`_plan_session_fuse`
  and `_apply_session_fuse_plan`), both of which currently reject any modified sidecar?

## Recommendation

Treat this as a genuine, own-standing proposal. Do **not** ride it in on a bug-fix. If pursued, the
likely sequence is: pick a shape (1, 2, or 3 — or a per-lens combination), draft the matching
constitutional amendment (flagging exactly what it overrides in 1.2), design the gate and provenance,
then implement against the fuse guards. Shape 2 (link structure-repair, 1.2 intact) plus shape 1
(diagram content refinement) is the lower-risk starting point; shape 3 is a separate, weightier
decision that the 2026-07-22 revert shows is wanted but not urgent.

## References

- `docs/CONSTITUTION.md` — Invariant #2 (append-only + exceptions 1.2, 1.4), Invariant #6 (partitioned
  Markdown authority, 1.1), §11 Governance.
- `docs/3_Spec/draft/adr-lifecycle-sidecar-contract.md`, `decision-level-link-sidecar-refs.md` — how
  link sidecars own and source lifecycle edges.
- 2026-07-22 link-sidecar revert (`revert(links): restore the demonstration sidecar edit`) — the
  finding that no operation exists to narrow a published edge.
- v1.4 amendment (2026-07-23) — the narrow diagram-syntax-repair exception this proposal generalises.
