---
title: ADR ledger evolution and reasoning semantics plan
status: inbox
priority: P1
next_action: Independently review the semantic model and decide whether to promote a revised plan to docs/2_Todo; do not merge the stale v3 branch or migrate the corpus.
blocked_by:
  - Independent semantic and implementation review
sources:
  - git commit 4fb9d977fd031484e6ac478d9e083bec38cebaa3
  - git commit 92f4563ce9de5380131b28de90582575d8765fff
  - .memory-seed/sessions/2026-08/2026-08-31.md
  - ../7_Replaced/memory-seed-semantic-record-and-signal-foundation-plan.md
spec_binding: null
---

# ADR Ledger Evolution and Reasoning Semantics Plan

Status: **INBOX — REVIEW REQUIRED, NOT APPROVED IMPLEMENTATION.**

Priority if promoted: **P1**, after the shipped ADR foundation and before broader workflow-review or
semantic-projection work that depends on the meaning of ADR fields.

## Decision requested

Decide whether the ADR event model should distinguish three concepts that the current v2 `Impact` field
partly conflates:

1. **Reason** — why the decision was made, including a testable hypothesis where the decision can be
   evaluated empirically.
2. **Evolution** — how the event changes authority, lifecycle state, lineage, or the accepted head.
3. **Consequences** — optional downstream effects, costs, benefits, and operational implications.

This review preserves the useful semantic insight from the unmerged
`codex/feature/canonical-adr-ledger-v3` branch without treating that stale implementation as approved or
merge-ready.

## Provenance and current state

The preserved v3 branch contains two clean commits from 2026-08-31:

- `4fb9d977` changes the ADR format, validation, specification, Constitution, and Memory Trace model.
- `92f4563c` migrates the full ADR corpus and archives a byte-for-byte v2 preimage.

The branch proposed replacing `Impact` with `Evolution` because most lifecycle events use that field to
describe lineage or authority change rather than effects. It also proposed treating future Reasons as
hypotheses with expected and disconfirming observations.

The branch has no matching v3 session decision or independent review. Its specification contains stale
v2/`Impact` language, and it is far behind current `main`. A later main entry preserved it only because
the commits were unmerged; main neither adopted nor formally rejected the idea.

The two commits remain durable Git evidence even after their worktree is removed. The first commit holds
the Constitution, specification, implementation, UI-model, and test changes; the second holds the migrated
corpus and its complete v2 preimage archive. The branch may be retained until review disposition, but the
worktree is not required to recover or inspect either commit.

## Exact constitutional change proposed by the branch

The branch retains the ratified v2 exception and adds a second, one-time exception labelled Constitution
1.11. That proposed amendment would authorize only a corpus-locked v2-to-v3 terminology correction:

- rewrite `Decision` / `Reason` / `Impact` events as `Decision` / `Reason` / `Evolution`;
- archive every v2 preimage with its path, byte count, and SHA-256 before changing source bytes;
- preserve event IDs, timestamps, envelope facts, references, replay state, and Current-view meaning;
- publish a read-only audit classifying historical Reasons without rewriting them;
- refuse an unfamiliar corpus, a repeat run, or use as a general rewrite command; and
- treat future Reasons as hypotheses tested against stated observations.

The branch's amendment table labels 1.11 as authorized by JNL, but no matching session decision or review
receipt exists. This plan therefore treats the text as an unratified amendment proposal, not authority.

## Exact ADR structure proposed by the branch

The proposed canonical record uses `format: memory-seed-adr/3` and `schema_version: 3`. Stable identity
frontmatter remains unchanged. `Current view` and every event render the fields in this order:

1. `Decision`
2. `Reason`
3. `Evolution`

The proposed stage meanings are:

- **proposal:** candidate decision; testable Reason with expected and disconfirming observations; initial
  lineage/context;
- **acceptance or rejection:** transition; transition rationale; authority change;
- **review:** retain or change the decision; evidence testing the prior hypothesis; observed result and
  successor path; and
- **supersession or context:** scope decision; rationale; authority or context effect.

The migration copies historical v2 `Impact` prose into `Evolution`, removes the v3 event's Impact field,
and keeps the archived v2 preimage as the provenance record. It does not infer or strengthen historical
Reasons. The accompanying audit labels each Reason `testable`, `rationale-only`, or `absent` based on
whether it explicitly contains a hypothesis, expected observation, and disconfirming observation.

The prototype updates Python parsing/rendering/validation, the lifecycle specification, Constitution,
Memory Trace API/UI models, and ADR tests. Its own specification is unfinished: introductory text still
says writers emit v2, one event section still calls the shape v2, and a later event description still
requires `Impact`. These contradictions must become explicit review cases rather than being copied into a
new implementation.

## Value hypothesis

The proposal is valuable if it makes an ADR answer three different questions without ambiguity:

- Why did we believe this choice was appropriate?
- What changed in the decision chain when this event occurred?
- What effects did the choice produce or predict?

`Evolution` is a better name than `Impact` for lifecycle and authority movement. Requiring empirical
proposals to state what evidence would support or disconfirm their Reason should improve later review.
The model should not, however, force normative, preference-based, or purely administrative decisions into
false experimental language.

## Proposed semantics for review

| Event stage | Reason | Evolution | Consequences |
|---|---|---|---|
| Proposal | Rationale; testable hypothesis when applicable | Initial lineage and intended authority path | Optional predicted effects and tradeoffs |
| Acceptance or rejection | Why the transition is warranted | Authority/status transition | Optional immediate implications |
| Review | Evidence testing the earlier rationale or hypothesis | Retain, refine, or open a successor path | Observed effects and costs |
| Supersession or context | Why scope or ownership changed | Predecessor/successor and authority effect | Optional migration or operational impact |

The review must decide whether `Consequences` belongs in the canonical event schema, remains optional
prose, or should be omitted. It must also define when the hypothesis form is mandatory, recommended, or
inapplicable.

## Historical compatibility and migration

Do not assume every historical v2 `Impact` block is really Evolution. Before proposing a schema change:

1. classify a representative sample as lifecycle evolution, actual consequence, mixed, or unclear;
2. measure whether the proposed fields improve human review and retrieval;
3. define a lossless read path for v1 and v2 records;
4. prefer append-only or derived compatibility over corpus rewrite unless the evidence shows a rewrite is
   necessary;
5. if a one-time rewrite is still proposed, archive and hash every preimage, preserve all identities and
   references, prove replay equivalence, test repeat-run refusal, and obtain explicit constitutional
   ratification against the reviewed diff.

The old v3 migration implementation is evidence and a prototype only. It must not be run against current
main or used as the implementation base.

## Review questions

1. Does `Evolution` consistently describe the third field across every ADR event kind?
2. Are genuine consequences common enough to deserve their own canonical field?
3. Which decision classes can honestly carry a falsifiable Reason, and what is required for the rest?
4. Can v2 remain readable without rewriting the historical corpus?
5. Do current retrieval, ADR review, MCP, and Memory Trace surfaces benefit from the distinction?
6. Does the proposal conflict with append-only authority or any later ADR/provenance work on main?
7. Should the old v3 branch be retained as reference until the review concludes, then retired regardless
   of the review outcome?

## Non-goals

- No approval to merge or rebase the existing v3 branch.
- No ADR corpus migration, Constitution amendment, schema bump, or compatibility removal.
- No retroactive invention or strengthening of historical Reasons.
- No requirement that every decision be framed as an experiment.
- No change to current main behavior during review.

## Review and authorization gates

1. **Independent semantic review:** test the three-field model against representative real ADR events and
   identify counterexamples.
2. **Current-main implementation review:** inventory every reader, writer, validator, projection, and UI
   affected; treat the stale branch as a source, not a patch set.
3. **Migration decision:** compare no-rewrite compatibility, derived projection, and one-time conversion.
4. **User decision:** accept, revise, defer, or reject the proposal and record the rationale in a session
   entry.
5. **Promotion:** only an accepted, fully scoped plan moves to `docs/2_Todo/`.
6. **Constitutional authorization:** if the accepted design needs a historical rewrite or changes an
   invariant, present the exact amendment and migration evidence for explicit ratification before writes.

## Acceptance criteria for promotion

- Representative ADR events demonstrate that the proposed concepts are distinct and useful.
- Event-specific Reason requirements avoid fabricated hypotheses.
- Historical v2 fields have a measured classification, not a blanket rename assumption.
- Compatibility and migration choices name preservation, rollback, and repeat-run guarantees.
- All current-main affected surfaces and tests are inventoried.
- The old branch's useful tests and failure cases are mapped into the new plan without importing stale
  code blindly.
- An independent reviewer records a recommendation and unresolved risks.
- JNL explicitly approves promotion and any required constitutional amendment remains a later, separate
  ratification gate.
