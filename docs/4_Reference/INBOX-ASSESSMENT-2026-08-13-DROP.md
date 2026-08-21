---
title: Inbox assessment — 2026-08-13 harness-comparison drop
status: inbox-assessed
date: 2026-08-21
promotion: comparison lines retired 2026-08-21; opportunity register (O1-O10) still undispositioned
---

# Inbox assessment: the 2026-08-13 drop

This assesses the four documents that arrived in `docs/1_Inbox/` on 2026-08-13 and were recorded as
untriaged in [`0_NEXT_STEPS.md`](../2_Todo/0_NEXT_STEPS.md) ("2026-08-13 drop" section) on 2026-08-14.
It re-baselines the synthesis report's claims against the current tree (67 commits ahead of the report's
pinned snapshot) and recommends dispositions for the next triage pass to apply or reject.

> **2026-08-21 update:** JNL confirmed the retirement recommendation below. The two comparison lines
> have been moved to `7_Replaced/`, pointing back at the synthesis report, which remains in `1_Inbox/`
> (its own O1–O10 register is still undispositioned — that promotion was conditional on both the O1 note
> below and JNL confirming the §7 sequence, and only the former is done). The disposition table's rows
> for the two comparison lines are historical — read them as "recommended, now applied."

## Documents in scope

1. [`memory-seed-harness-gap-opportunity-report.md`](../1_Inbox/memory-seed-harness-gap-opportunity-report.md) — synthesis, O1–O10 opportunity register
2. [`harness-engineering-comparison-claude.md`](../7_Replaced/harness-engineering-comparison-claude.md) — Claude line (retired 2026-08-21, see update note above)
3. [`harness-engineering-comparison-codex.md`](../7_Replaced/harness-engineering-comparison-codex.md) — Codex line (retired 2026-08-21, see update note above)
4. [`agent-interaction-storylines-review.md`](../1_Inbox/agent-interaction-storylines-review.md) — living document, exempt from triage (JNL, on record)

## Headline finding: the outstanding decision is narrower than the README states

The Inbox `README.md` still frames the open question as "pick one comparison line, or fold them
together — deciding is itself the triage." That framing is stale. The synthesis report **is** that
fold: it already reconciles the two lines' shared conclusions, states what each line uniquely
contributes, and resolves their one substantive tension (are human review gates correct-now or
also unscalable) with an explicit, sourced answer. It was simply never recorded as the resolution, and
the two source lines were never retired to `7_Replaced/` the way the 2026-07-20 triage retired the prior
14-document set once its crosswalk survived.

**Recommendation:** apply the established precedent — keep the synthesis report as the surviving
record (rename/move to `4_Reference/` once its own opportunities are dispositioned), retire both
comparison lines to `7_Replaced/`, de-numbered, pointing back at the synthesis. This is a recommendation
for the next triage decision, not applied here.

Two smaller inconsistencies feed the same staleness:

- **Three-way status disagreement.** Claude line: "Unassessed external capture." Codex line: "Paired
  assessment in progress… has been evaluated against current repository capabilities." Synthesis
  report / README: "unassessed" / "neither supersedes the other." Worth reconciling in whichever
  document survives triage, since it bears on whether the outstanding decision is still fully open.
- **README undercounts.** `docs/1_Inbox/README.md`'s "Current contents" prose still says "3 documents
  awaiting or exempt from triage (2026-08-13)" and never names the gap-opportunity report — only the
  generated `docs-index` table lists it. This is a factual miscount, not a triage call; worth a
  one-line correction independent of the disposition decision above.

## Re-verification of the synthesis report's claims against current HEAD

The report pins repository facts to commit `9c4b8f8f` (2026-08-13). The branch under review is 67
commits ahead, through 2026-08-18. Every load-bearing claim checked held up:

| Claim | Report (08-13) | Re-checked at HEAD (08-21) | Status |
|---|---|---|---|
| Routing floor: `AGENTS.md` + `agent-rules.md` + `skills/orientation.md` | 452 lines / 30,391 chars | 452 lines / 30,443 chars | Holds (52-char drift, immaterial) |
| Routing + `skills/index.md` by first substantive turn | 776 lines / 45,492 chars | 776 lines / 45,544 chars | Holds |
| `docs check`: healthy, 16 warnings, no lifecycle errors | Stated | Reproduced exactly: 16 `missing-todo-yaml` warnings, "Docs lifecycle OK (213 file(s))" | Holds |
| O5 context-derivation experiment: preregistered, scored execution blocked pending owner approval | Stated | `PREREGISTRATION.md` still reads "DRAFT — scored execution blocked pending owner approval"; only unscored smoke/calibration artifacts exist in git history | Holds |
| O1 owner gate: quality-v0 "awaiting JNL usefulness review" | Stated | `memory-quality-metrics-v0-proposal.md` front matter: `status: v0-shipped-awaiting-usefulness-review`, unchanged `next_action` | Holds |
| O3 owner: workbench plan, three journeys not yet reconstructed | Stated | `next_action: Reconstruct three completed project journeys…` still open | Holds |
| O6 owner: taxonomy proposal, steps 1–4 shipped, 5–7 gated | Stated | `status: steps-1-4-shipped`, same gate language | Holds |
| O4 (per-worktree app observability) has no current owner | Stated | Confirmed against `7_Replaced/agent-workflow-observability-exploration.md` (superseded by the workbench plan, which is scoped to *workflow* evidence, not runtime telemetry) and the crosswalk (no hit for "observability") — genuinely distinct and genuinely unowned | Holds |

**No material drift found in the report's factual claims.** The measured numbers moved by rounding
noise only; every named owner's gate is in the same state it was on 2026-08-13.

## One finding the report could not have had: O1's central question is now in flight

This is the one place current work has overtaken the snapshot, and it is worth surfacing precisely
because the report's own §1 lists "measure decision and next-step quality" as opportunity #1.

Between 2026-08-13 (drop) and 2026-08-18, a separate, un-cross-referenced experiment track —
`experiments/decision-replay/` (pilot 2026-08-13, adjudicated 2026-08-14, extended through a v4
feasibility pilot and a corrected, blinded v5 relaunch on 2026-08-18) — has been directly testing
whether prescribed Memory Seed retrieval produces better task outcomes than a task-only control. That
is substantively the same question as O1 ("does preserved rationale improve a later decision"), run
through a different instrument than the one O1 names as owner (`memory-quality-metrics-v0-proposal.md`'s
constrained-context gold set).

This was already caught and recorded independently: `0_NEXT_STEPS.md` states "the decision-replay pilot
in the evidence programme above is the direct execution of the gap report's central question. Neither
counts as triage of the drop." That note is correct and this assessment does not re-litigate it — it is
flagged here only so the next triage pass folds the decision-replay track into O1's evidence base rather
than treating O1 as an untouched open question, and so the synthesis report gets a superseding note
pointing at `experiments/decision-replay/` if/when it is retained.

**No causal conclusion follows yet.** The 08-13 pilot result explicitly disclaims causal power (n=1
pair); the 08-18 relaunch is a fresh, corrected, blinded cohort with results not yet adjudicated as of
this review. This is a pointer to where O1's evidence is accumulating, not a verdict.

## Per-document disposition recommendation

| Document | Recommended disposition | Rationale |
|---|---|---|
| `memory-seed-harness-gap-opportunity-report.md` | Promote to `4_Reference/` as the surviving synthesis, once (a) the O1 note above is added and (b) JNL confirms the §7 recommended decision sequence against current owner states (all four still open per the table above, so the sequence is still actionable as written). | Already functions as the fold the README says is outstanding; nothing in re-verification invalidates its register. |
| `harness-engineering-comparison-claude.md` | **Applied 2026-08-21.** Retired to `7_Replaced/`, pointing at the synthesis (still in `1_Inbox/`, not yet promoted). | Its unique contributions (bottleneck/product reading, Amdahl framing) are already folded into synthesis §2. Nothing left un-synthesized that a reader needs the full line for. |
| `harness-engineering-comparison-codex.md` | **Applied 2026-08-21.** Retired to `7_Replaced/`, pointing at the synthesis (still in `1_Inbox/`, not yet promoted). | Same: its unique contributions (owner-aware disposition, empirical-loop framing) are already folded into synthesis §2. |
| `agent-interaction-storylines-review.md` | No action — remains in `1_Inbox/` by explicit JNL exemption on record. Not re-litigated here. | Living document, not an untriaged capture; R1–R13 tracked separately in `2_Todo/storyline-gap-tranche-implementation-plan.md`. |
| `1_Inbox/README.md` | Correct the stale "3 documents" count and name the fourth document in prose. | Factual correction, not a triage call — safe to make independent of the disposition above. |

## What this assessment does not decide

- Whether to actually retire the two comparison lines — that is JNL's call, following the same
  precedent applied in the 2026-07-20 triage.
- Whether the O1–O10 register's individual dispositions are correct on their merits — re-verification
  found no factual drift, but did not re-litigate the register's judgment calls.
- Any change to `experiments/decision-replay/` or its adjudication — out of scope; referenced only to
  correct the report's snapshot-dated claim about O1.
