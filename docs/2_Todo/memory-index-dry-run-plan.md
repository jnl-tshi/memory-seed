---
title: "Memory Index Dry-Run Plan"
date: "2026-08-05"
project: "memory-seed"
status: "RUN 2026-08-05 - kill condition TRIGGERED (71.0 < Zep 75.1); do not submit v0.2 without the capture-routing fix"
priority: "P1"
next_action: "Fix non-decision fact routing (durable facts belong in index.md per memory_consolidation - the seeding sessions left kickoff facts unstored), then re-run; only submit if the re-run clears 75.1."
related:
  - "business/research/field-evidence-log.md"
  - "business/market/competitor-landscape.md"
  - "docs/2_Todo/attention-retrieval-signal-proposal.md"
---

# Memory Index Dry-Run Plan

Status: **designed, not started.** Five-question test: **Trust, Retrieval**. Purpose: know Memory
Seed's approximate Agentic Memory Index score *privately* before deciding whether to submit via
verginglabs.com/radar for v0.2 (early September 2026). Never enter a published benchmark blind.

## What is being approximated

Verging Labs' six probe categories, reconstructed from their methodology page and the author's
thread. Their mechanics: the agent is **given the tool's own docs and left to follow them** across
simulated multi-week working sessions, then quizzed; 200 stored-fact questions + 72 never-stored
trap questions; judge calibrated against human labels; verdicts include *Fabricated Citation*.
A Memory Seed run therefore measures the shipped instruction surface (AGENTS.md routing,
agent-rules, session_logging, MCP tools) end to end — not the store in isolation.

## Design (reuses the agent-capture machinery wholesale)

**Fixture:** one claude-L3 fixture (full stock install = the product as shipped). **Store
population happens the way the benchmark does it**: N seeding sessions (headless, cwd=fixture),
each given a work-diary brief ("this week the team decided/learned/changed X, Y, Z…") and left to
store per the shipped instructions. ~10 sessions across a simulated 5-week arc, fact list frozen
in an answer key the sessions never see verbatim (facts are embedded in prose briefs).

Fact classes mirror their taxonomy:

| Their category | Our probe | Answer-key shape |
|---|---|---|
| Direct recall | "What did we decide about X?" | fact stored in week w |
| Updated facts | fact stated week 1, reversed week 3 | current answer + the superseded one |
| Thread growth | fact accreted across 3 sessions | composite answer |
| Synthesis | question spanning 2+ entries | requires joining entries |
| Long-term retention | week-1 fact quizzed at end | fact + age |
| False memory check | 24+ never-stored plausible questions | correct answer = abstain |

**Quiz phase:** fresh headless sessions (no seeding context), one question per session batch,
answering only from the store. **Blind judging:** the two-stage judge harness (`judge.py` pattern —
stage 1 never sees the answer key; stage 2 maps onto it; prompts over stdin per the Windows lesson).
Verdicts copied from theirs: correct / not addressed / incorrect / outdated / fabricated.

**Pre-registered expectations** (stated now so the result can't be read opportunistically):
- *Updated facts* and *false memory* are expected strengths (E8 stale-head navigation was 6/6;
  0 fabricated rationale in 121 v2-matrix judgements; `memory_search` exposes `replaced_by`/
  `evolved_head` on every row).
- *Arbitrary-fact direct recall* is the expected weakness: the store is decision-shaped, and the
  validators refuse unstructured writes — facts that aren't decisions must survive as Summary
  prose or be declined by the seeding agent. If the score dies here, the finding is "adapter
  needed" (a fact-note convention), not "memory is bad" — but that distinction must be measured,
  not assumed.
- **Kill condition for submission:** if the blended dry-run score lands below the published #8
  (Zep, 75.1), do not submit v0.2; fix what the dry-run exposes first.

**Cost/scope:** ~10 seeding + ~25 quiz sessions ≈ $25 at observed per-session costs; one day
wall-clock with the batch runner. Explicitly NOT a replication of their 272-probe set — it is a
directional private estimate with honest error bars, per the pattern-over-threshold rule.

## Results (2026-08-05, first run)

| Category | n | correct | not_addr | incorrect | outdated | fabricated |
|---|---|---|---|---|---|---|
| direct_recall | 6 | 3 | 0 | 3 | 0 | 0 |
| updated_facts | 6 | 4 | 0 | 2 | 0 | 0 |
| thread_growth | 3 | 3 | 0 | 0 | 0 | 0 |
| synthesis | 4 | 3 | 0 | 1 | 0 | 0 |
| long_term_retention | 4 | 1 | 2 | 1 | 0 | 0 |
| false_memory | 8 | **8** | 0 | 0 | 0 | **0** |

**Blended 22/31 = 71.0 — below Zep (75.1). Kill condition TRIGGERED: do not submit.**

**The pre-registered expectations both held.** False-memory was perfect (8/8, zero fabrications —
the published index winner failed exactly here), updated-facts/thread/synthesis strong. The losses
are concentrated in arbitrary-fact recall and retention — the predicted weakness of a
decision-shaped store.

**Every miss is an over-abstention, not a wrong answer.** All nine failures are the agent saying
"not recorded". Provenance split (checked against the seeded workspace):

- **Capture loss (~5):** the kickoff session (S1: roster, cadence, CI budget, codename) recorded
  ZERO entries — E5's capture finding replayed on fact-dense, no-code-change sessions. The facts
  died at storage, so recall never had a chance. The shipped instruction surface routes *decisions*
  to the store but gives diary-style *facts* no home; `index.md` is that home per
  `memory_consolidation.md`, and no seeding session used it.
- **Retrieval under-confidence (~4):** Sofia (stored, S9), the 40-minute original budget
  (recoverable from the superseding entry's own text), and the Granite codename (present in
  RELEASE.md) were all on disk and denied anyway.

**Reading:** the honesty posture that produces zero fabrications is the same posture that
over-abstains on weakly-stored facts. For *acting* agents that trade is right (a miss stalls
loudly; an invention proceeds confidently — the asymmetry a top thread comment argued). For this
*blended score* it loses ~9 points. The fix is not loosening honesty; it is (1) routing durable
non-decision facts to `index.md` at capture time, and (2) letting quiz-style retrieval trust
project files and superseding-entry context it already has.

Caveats: n=31, one run, own judge chain (Codex, calibrated only by rubric), timeline-compressed
retention. Directional, per the pattern-over-threshold rule.

## Contamination guard

Dry-run materials stay out of the published store paths (`experiments/memory-index-dryrun/`,
gitignored like the capture runs). Nothing from the answer key enters `.memory-seed/` in this
repo; the fixture's store is disposable.

## Out of scope

- The 5,000-page scale test (their separate scale probe) — revisit only if submission proceeds.
- Cost-per-answer accounting — theirs is subscription-vs-API sensitive; note qualitatively.
- Any contact with Verging Labs before the dry-run result is read.
