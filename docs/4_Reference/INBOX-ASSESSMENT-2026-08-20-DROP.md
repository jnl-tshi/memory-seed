---
title: Inbox assessment — 2026-08-20 proposal drop
status: inbox-assessed
date: 2026-08-21
promotion: none — findings and recommended dispositions only
---

# Inbox assessment: the 2026-08-20 drop

Four proposals (dated 2026-08-20) were found sitting untracked in the shared root checkout on
2026-08-21 and captured verbatim, without triage, in a separate commit. This assesses their content
against current shipped capability. No item is promoted, retired, or moved by this document.

## Documents in scope

1. [`active-truth-execution-control-proposal.md`](../1_Inbox/active-truth-execution-control-proposal.md) — 1223 lines, P0/Foundational
2. [`memory-seed-first-principles-proposal.md`](../1_Inbox/memory-seed-first-principles-proposal.md) — 408 lines, product strategy
3. [`memory-seed-governed-interactive-retrieval-proposal.md`](../1_Inbox/memory-seed-governed-interactive-retrieval-proposal.md) — 513 lines, retrieval protocol
4. [`semantic-compression-benchmark-proposal.md`](../1_Inbox/semantic-compression-benchmark-proposal.md) — 685 lines, experiment design

## Headline finding: the four are grounded in the ecosystem, not in the repository

The distinction matters and the first version of this assessment got it wrong, so it is stated
precisely here.

These four documents **do** know the project's component landscape: they name Memory Trace, Trail,
sidecars, the Constitution, ADRs, MCP/CLI/REST, Graphify, Semble, and ICM (Interpretable Context
Methodology, the methodology behind ICM Architect) — and they place each correctly relative to Memory
Seed. That is real grounding, and an earlier draft of this document wrongly flagged the ICM references
as invented. ICM is named in this repository's own
[`experiments/stack-benchmark/solar-filaments-001/PREREGISTRATION.md`](../../experiments/stack-benchmark/solar-filaments-001/PREREGISTRATION.md)
as one of the treatments evaluated alongside Memory Seed, Graphify, and Semble.

What they do **not** contain is any citation of shipped repository state: no file path, entry id, ADR
id, spec reference, or command output appears across their 2,829 lines. Ecosystem awareness is not the
same as checking what already ships, and it is the second kind of grounding that the crosswalk
discipline requires. Document 4 is the exception in spirit — it explicitly *requires* "Repository
Investigation First" (§16) before any implementation, and treats "document anything already present
that overlaps" as a mandatory step it has simply not performed yet.

This is precisely the failure mode `adr_inbox_promotion_workflow` exists to catch: proposals that "read
as missing capability only because they predated the code that shipped them." Below is the crosswalk
that documents 1–3 skipped.

## Crosswalk against shipped capability

| Proposed capability | Document | Already shipped as |
|---|---|---|
| Active-truth lifecycle (`Observed → Candidate → Proposed → Active → Superseded/Expired/Rejected`), `supersedes`/`superseded_by` metadata | Doc 1 §7 | Forward-only `supersedes`/`evolves`/`replaces` lifecycle edges, enforced by `links check`; ADR sidecar contract (`status: live`) with an explicit accepted/proposed/superseded head; `memory_session_append`'s mandatory ADR review preflight (refuses a write that contradicts an ADR without a `revise`/`no-change` outcome) |
| Typed knowledge states (Observation/Claim/Evidence/Assumption/Hypothesis/Decision/Rule/Exception/Open question/Rejected alternative/Outcome) | Doc 1 §8 | The DRAFT decision shape already separates Decision (D) from Reason (R), Alternatives (A, i.e. rejected alternatives), Files (F), Tests (T); the provenance/authority taxonomy proposal (steps 1–4 shipped) separately typed provenance, authority, and confidence as distinct fields rather than folding them into content |
| Write contract with risk-adaptive promotion, refusing agent-generated content into canonical memory unreviewed | Doc 1 §9 | `memory_session_append` already fails closed on malformed DRAFT shape, fabricated ref ids, out-of-order chronology, unknown topic vocabulary, and id collision — nothing is written when any guard fails; controlled topic vocabulary requires an explicit `proposed_topic` request rather than silently minting new slugs |
| Reproducible evidence packets with content hashes, inclusion/exclusion rationale | Doc 1 §11 | Evidence Pack Phase 1 already ships (referenced across `2_Todo/` and the 2026-07-18 `INBOX-ASSESSMENT.md`); decision-level chunk fetch already returns `entry_context` (Summary/Follow-up/Validation) rather than a bare fragment |
| Postflight validation against supplied rules | Doc 1 §12 | Partially: `docs check` / `links check` / ADR review preflight already block on specific rule classes at write time; a general worker-output compliance checker does not exist — this piece is a genuine gap, not a duplicate |
| Multi-agent concurrency, optimistic locking, conflict detection on canonical writes | Doc 1 §15 | `memory_session_integrate` already fails closed on any session-file conflict outside session files, restoring a clean tree rather than half-merging; branch = workstream policy already gives each agent an isolated append target; a cross-branch *decision-level* conflict detector is a genuine gap |
| Source trust / memory-poisoning quarantine for untrusted external content | Doc 1 §16 | Genuine gap — no existing mechanism explicitly quarantines or trust-labels externally sourced candidate memory. This is the one part of Document 1 with no shipped or in-flight owner found in this crosswalk. |
| Retrieval-quality metrics, decision-density product-fit framing, "prove memory quality before enrichment" sequencing | Doc 2 | `memory-quality-metrics-v0-proposal.md` already ships a v0 baseline (`status: v0-shipped-awaiting-usefulness-review`) measuring exactly this class of question; the constrained-context gold-set candidate inside it already targets grounded-decision quality |
| Interactive re-query during task execution, epistemic checkpoints before consequential actions | Doc 3 §2, §4 | Already policy, not just proposed: `history_retrieval.md`'s trigger registry requires retrieval "before consequential conclusions on non-obvious behavior"; `memory_search`/`memory_get_chunk` are already interactive MCP tools an agent calls mid-task, not only at bootstrap. What is genuinely new here is a **formal retrieval-trace schema and instrumented checkpoint policy** — that part does not exist |
| Decision-level identity distinct from entry-level identity | Doc 1 §7.3, Doc 2 §3 | Shipped: `entry_id:dN` decision refs, decision-level chunk fetch, decision-level lifecycle edges (2026-07-25 campaign landed 696 decision-level edges per project memory) |
| "Topics/links are derived, non-authoritative, regenerable" | Doc 1 §17.1–17.2, Doc 2 §7.7 | Already the stated design principle and already implemented — topic and link sidecars are separate append-only files from the canonical entry, never mutate it |

## Per-document assessment

### 1. `active-truth-execution-control-proposal.md`

The single largest document and the one with the most duplication. Perhaps a third of its ~25
sections (§7 active-truth lifecycle, §8 typed states, most of §9 write contract, §11 evidence packets,
§17.1–17.2) describe, in different vocabulary, mechanisms already shipped. The genuine deltas are
narrower than the P0/Foundational framing suggests: **postflight compliance validation** (§12),
**cross-agent write conflict detection at the decision level** (§15), and **source-trust quarantine for
externally derived content** (§16) have no shipped or in-flight owner in this repository. Those three
are worth carrying forward as scoped candidates. The rest should not be re-implemented under new names.

**My take:** don't promote as written. If any part advances, it should be the three genuine gaps above,
each scoped independently — not the "P0 workstream, implement before ontology/graph expansion" framing
the document argues for, which would mean re-deriving infrastructure that already exists.

### 2. `memory-seed-first-principles-proposal.md`

Less redundant than Document 1 because it operates at product-strategy altitude rather than proposing
new mechanisms. Its core claim — "Memory Seed is Git-native decision memory," retrieval quality is the
product core, prove core value before enrichment — is compatible with, and largely restates, existing
project discipline (the quality-v0 gate, the harness-gap-opportunity report's own non-goals around a
second quality framework). Its wedge identification (small AI-native teams on long-lived Git repos) and
benchmark design (baseline vs. core vs. enriched, A/B/C conditions) are a reasonable, non-duplicative
articulation, though close in spirit to the existing quality-v0 benchmark and the harness-gap report's
O1.

**My take:** the most defensible of the four to read and extract from, precisely because it doesn't
propose new build work — it's a positioning document. Worth reading as input to a product-strategy
decision, not worth promoting as an engineering workstream.

### 3. `memory-seed-governed-interactive-retrieval-proposal.md`

The best-scoped of the four. It doesn't claim interactive retrieval is missing (it isn't); it proposes
formalizing what already happens ad hoc — a versioned bootstrap-packet identity, a retrieval-trace
schema, and configurable "epistemic checkpoint" policies triggered by action class (architecture
change, new dependency, before completion). The distinction it draws between deterministic bootstrap
assembly and non-deterministic-but-traceable runtime search is a genuinely useful framing this repo's
current retrieval policy doesn't formalize.

**My take:** the strongest candidate for a scoped follow-up. Before building, it should be checked
against `memory_link_suggest`'s existing ranking-by-consulted-ids mechanism (a lightweight precedent for
"track what was actually used") and the O5 context-derivation experiment, which already measures
retrieval-packet composition — a new retrieval-trace schema should extend that experiment's fixtures
rather than invent a parallel one.

### 4. `semantic-compression-benchmark-proposal.md`

The most disciplined of the four by construction: explicit ablation design (raw → core → core+why →
core+why+constraint → structured), a stated null result as a valid outcome ("Outcome A: no semantic
layer required"), fidelity checks against meaning loss, and an explicit requirement to audit the
repository before writing implementation code. Its ICM references are correct — ICM (Interpretable
Context Methodology) is a real adjacent methodology, already named in this repository's
stack-benchmark preregistration as a treatment evaluated alongside Memory Seed.

Its topic overlaps with the already-retired `information-theoretic-evolution-exploration.md`
(2026-07-25, retired on arrival — see
[`information-theoretic-evolution-disposition.md`](information-theoretic-evolution-disposition.md)),
which covered adjacent ground (information-theoretic lenses on decision content) and was found to
mostly restate shipped capability. This proposal is narrower and more empirical than that one was, so
it isn't simply a repeat, but the disposition doc is required reading before scoping it.

**My take:** the proposal design itself is sound and could run largely as written — but only after its
own §16 "Repository Investigation First" is actually performed, and the 2026-07-25 disposition doc is
read so the experiment isn't re-deriving that one's already-answered questions.

## Overall recommendation

Do not promote any of the four as submitted. Two (Documents 3 and 4) are close enough to actionable
that a scoped rewrite — grounded in the crosswalk above, with the genuine deltas isolated from the
already-shipped restatement — could go to `2_Todo/` relatively cheaply. Document 2 is worth reading as
strategic input rather than building from. Document 1 needs the most cutting: three real gaps (§12
postflight validation, §15 decision-level write-conflict detection, §16 source-trust quarantine) survive
inside twenty-five sections of mostly-already-shipped mechanism restated under new names.

This is not applied here — captured only, per the same discipline the 2026-08-13 drop review used.
