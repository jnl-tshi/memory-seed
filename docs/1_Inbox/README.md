# Inbox

Status: **6 documents awaiting or exempt from triage (2026-08-21)**. The two harness-engineering
comparison lines retired to `7_Replaced/` this same day — see
[`INBOX-ASSESSMENT-2026-08-13-DROP.md`](../4_Reference/INBOX-ASSESSMENT-2026-08-13-DROP.md). Four new
proposals dated 2026-08-20 were found sitting in the shared checkout on 2026-08-21, captured, and
assessed — see [`INBOX-ASSESSMENT-2026-08-20-DROP.md`](../4_Reference/INBOX-ASSESSMENT-2026-08-20-DROP.md).
None of the four is promoted; the assessment recommends against building any of them as submitted.

Place new, unassessed proposals and source captures here. Once evaluated, move each document to its canonical
active, reference, completed, rejected, superseded, or deferred lane. Do not leave an accepted actionable
proposal in the Inbox — and don't leave a fully-evaluated one here either: once a document has a clear
status, owner, and citation, it belongs in the lane that states that outcome, not in the folder for raw,
untriaged captures.

## Current contents

- [`agent-interaction-storylines-review.md`](agent-interaction-storylines-review.md) — a **living** review of
  every agent interaction storyline, kept synchronised with shipped behaviour. JNL explicitly recorded that it
  stays in this lane rather than moving to `4_Reference/`, so it is an exemption from the triage rule above,
  not an untriaged capture.
- [`memory-seed-harness-gap-opportunity-report.md`](memory-seed-harness-gap-opportunity-report.md) — the
  2026-08-13 synthesis of the (now-retired) Claude and Codex comparison lines into one ten-item
  opportunity register (O1–O10). Its own status line still says no opportunity is accepted work; the
  2026-08-21 assessment re-verified its claims against current HEAD and found no material drift, but its
  §7 recommended decision sequence has not been confirmed as JNL's actual sequence. See
  [`../4_Reference/INBOX-ASSESSMENT-2026-08-13-DROP.md`](../4_Reference/INBOX-ASSESSMENT-2026-08-13-DROP.md).
- [`memory-seed-evidence-first-governed-retrieval-plan.md`](memory-seed-evidence-first-governed-retrieval-plan.md)
  — promotion-ready synthesis of the four 2026-08-20 proposals and the Claude/Codex reviews. It proposes
  one evidence programme: instrument governed retrieval, test the zero-generation D/R compression
  baseline, then admit only execution-assurance gaps reproduced by negative controls. JNL explicitly
  asked that it remain in the Inbox pending review; it is not approved work yet.
- **Four proposals dated 2026-08-20** — `active-truth-execution-control-proposal.md`,
  `memory-seed-first-principles-proposal.md`, `memory-seed-governed-interactive-retrieval-proposal.md`,
  `semantic-compression-benchmark-proposal.md`. Found untracked in the shared root checkout on
  2026-08-21, captured verbatim, and assessed the same day. None cited this repository's actual code or
  prior triage decisions; the assessment found substantial overlap with already-shipped capability in
  the two largest documents. See
  [`../4_Reference/INBOX-ASSESSMENT-2026-08-20-DROP.md`](../4_Reference/INBOX-ASSESSMENT-2026-08-20-DROP.md)
  for the full crosswalk and per-document recommendation. Not triaged (moved or retired) — assessed only.

The warranty-claims ML project's file index that arrived here by mistake was assessed and moved to
[`../4_Reference/warranty-file-structure-index.md`](../4_Reference/warranty-file-structure-index.md) on
2026-08-13. It remains available as the source that informed Memory Seed's tree-first index format.

The Inbox stood empty from 2026-07-29, when the Superpowers collaboration proposal was approved for
implementation and promoted to
[`../2_Todo/superpowers-collaboration-integration-proposal.md`](../2_Todo/superpowers-collaboration-integration-proposal.md).

The two assessment artifacts and the design-reference folder that sat here after the 2026-07-20 triage
were themselves reference material, not undecided captures — moved the same day to
[`../4_Reference/`](../4_Reference/) once that was noticed:

- [`../4_Reference/INBOX-ASSESSMENT.md`](../4_Reference/INBOX-ASSESSMENT.md) — the 2026-07-18 pre-triage
  findings that stopped the two proposal sets from being promoted, and the corrected five-step sequence
  that replaced them.
- [`../4_Reference/INBOX-CAPABILITY-CROSSWALK.md`](../4_Reference/INBOX-CAPABILITY-CROSSWALK.md) — step 1
  of that sequence, and the surviving record of both retired sets: every claim mapped against what already
  exists and who owns it.
- [`../4_Reference/trace-humanised-dashboard-references/`](../4_Reference/trace-humanised-dashboard-references/README.md)
  — dashboard mockups for a warmer, more editorial Memory Trace design language. Its themes are already
  extracted and it is actively cited by a `2_Todo/` proposal, so it was triaged reference material sitting
  in the wrong lane, not a document still awaiting a decision.

## Triaged out on 2026-08-21

- **Both harness-engineering comparison lines → [`../7_Replaced/`](../7_Replaced/)**, pointing back at the
  synthesis report ([`memory-seed-harness-gap-opportunity-report.md`](memory-seed-harness-gap-opportunity-report.md),
  which stays in this lane — its own opportunities remain undispositioned). Retired rather than promoted:
  the synthesis already folds each line's unique contributions (Claude's bottleneck/product reading and
  Amdahl framing; Codex's owner-aware disposition and recorded-vs-measured evolution-loop framing) into
  one opportunity register, so the README's earlier framing — "picking one or folding them together is
  the outstanding decision" — was itself stale: the fold had already happened, just never recorded as the
  resolution. See
  [`../4_Reference/INBOX-ASSESSMENT-2026-08-13-DROP.md`](../4_Reference/INBOX-ASSESSMENT-2026-08-13-DROP.md)
  for the full re-verification against current HEAD.

## Triaged out on 2026-07-20

- **Both proposal sets (14 documents) → [`../7_Replaced/`](../7_Replaced/)**, de-numbered and renamed
  `-exploration`, each pointing back at the crosswalk. Retired rather than promoted: of 82 claims, most were
  already shipped law or shipped capability the proposals understated, five conflicted with explicit owner
  non-goals, and the genuine deltas were folded into the plans that own them. Nothing was deleted — the
  *why* is preserved, as with every prior set.
- `memory-trace-living-archive-and-editorial-focus-proposal.md` → promoted to
  [`../2_Todo/`](../2_Todo/memory-trace-living-archive-and-editorial-focus-proposal.md); its section 14 was
  answered the same day and the Community Decision Brief slice is approved to build.
- Seven raw iOS mood-board captures → archived to
  [`../4_Reference/archived/`](../4_Reference/archived/trace-humanised-dashboard-captures.md) once their
  themes had been extracted.
- The assessment doc, the crosswalk, and the humanising-references folder → moved to
  [`../4_Reference/`](../4_Reference/), later the same day, once JNL noticed they were already-evaluated
  reference material rather than undecided Inbox captures.

<!-- docs-index:begin -->
| Document | Priority | Blocked by | Next action / pointer |
|---|---|---|---|
| [active-truth-execution-control-proposal.md](active-truth-execution-control-proposal.md) | — | — | — |
| [agent-interaction-storylines-review.md](agent-interaction-storylines-review.md) | — | — | — |
| [memory-seed-evidence-first-governed-retrieval-plan.md](memory-seed-evidence-first-governed-retrieval-plan.md) | P1 | [] | JNL reviews this evidence-reconciled synthesis and decides whether to promote it to docs/2_Todo. |
| [memory-seed-first-principles-proposal.md](memory-seed-first-principles-proposal.md) | — | — | — |
| [memory-seed-governed-interactive-retrieval-proposal.md](memory-seed-governed-interactive-retrieval-proposal.md) | — | — | — |
| [memory-seed-harness-gap-opportunity-report.md](memory-seed-harness-gap-opportunity-report.md) | — | — | — |
| [reflection-board-cumulative-handoff-and-decision-harvest-proposal.md](reflection-board-cumulative-handoff-and-decision-harvest-proposal.md) | — | — | Assess the proposal against the current Reflection Board transaction contract before promotion … |
| [semantic-compression-benchmark-proposal.md](semantic-compression-benchmark-proposal.md) | — | — | — |
<!-- docs-index:end -->
