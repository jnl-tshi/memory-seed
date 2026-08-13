# Memory Seed harness gap and opportunity report

Status: **Unassessed synthesis in Inbox (2026-08-13).** No opportunity in this report is accepted work,
assigned a roadmap priority, or authorised for implementation. The report consolidates the parallel
Codex and Claude assessments so the next triage decision can start from their combined context rather
than from either line alone.

Primary inputs:

- [Codex comparison](harness-engineering-comparison-codex.md)
- [Claude comparison](harness-engineering-comparison-claude.md)
- Ryan Lopopolo, [*Harness engineering: leveraging Codex in an agent-first world*](https://openai.com/index/harness-engineering/), OpenAI, 2026-02-11
- Marina Favaro and Jack Clark, [*When AI builds itself*](https://www.anthropic.com/institute/recursive-self-improvement), Anthropic Institute, accessed 2026-08-13

Repository facts were rechecked at commit `9c4b8f8faba96d8c84048c4b5c8a70f2ec1a9475`. Current code and
command output are used for what exists now; the two comparison documents and session lineage are used
for how the conclusions evolved and why earlier claims were withdrawn.

---

## 1. Executive finding

The two comparison lines have converged on a narrower and more defensible opportunity than either began
with.

OpenAI demonstrates the repository-level mechanism: agents become effective when the codebase, runtime,
tests, documentation, and recovery paths are made legible to them. Anthropic describes the likely
organizational consequence if execution capacity continues to increase: the bottleneck migrates toward
choosing goals, reviewing a much larger output surface, deciding which results to trust, and recognizing
dead ends. Memory Seed sits between those layers as a candidate continuity and governance substrate.

Its strongest present capability is not generic repository documentation. A capable team can hand-roll
that with Markdown, linters, and agents. The more differentiated part is portable brownfield installation
plus typed, retrievable, append-only rationale: what was decided, why, what was rejected, what replaced
it, and which source carries authority.

The strongest gap is equally narrow: Memory Seed preserves why a decision was made, but does not yet
demonstrate that the preserved rationale leads to a better later decision. It also does not measure the
human cost of reviewing agent-generated evidence, or prove that a maintainer can reconstruct and safely
override agent-generated work after time has passed.

The highest-leverage opportunities are therefore:

1. measure decision and next-step quality through the already-owned constrained-context benchmark;
2. measure whether evidence packets compress human review without weakening authority gates;
3. test whether the workflow workbench improves later human reconstruction and override ability;
4. evaluate an integrated per-worktree application-observability loop;
5. reduce fixed startup context only through the existing safety-equivalence experiment;
6. obtain external user and brownfield-adoption evidence before treating capability demand as product demand.

The wrong response would be to create a second quality framework, copy OpenAI's minimal merge posture
into the append-only corpus, optimize for output volume, or position Memory Seed as a recursive-self-
improvement safety system.

---

## 2. How the two readings combine

### Shared conclusions

Both lines now agree that:

- the external reports corroborate the importance of agent-legible, repository-local context, but do
  not validate demand for Memory Seed as a product;
- Memory Seed has no priority or independent-invention claim over the OpenAI pattern;
- the same evidence is a build-versus-buy warning because capable teams can construct a current-state
  knowledge layer themselves;
- OpenAI's why/history mechanisms are lighter than Memory Seed's, not absent;
- browser and rendered verification exist here, but a per-worktree whole-application telemetry loop does not;
- environment provenance and runtime observability are separate failure classes;
- the fixed startup routing cost is material even though the architecture is modular;
- quality instrumentation is partly shipped and must not be proposed again under a new name;
- human gates are load-bearing for authoritative, append-only memory changes;
- decision outcome quality, review capacity, and goal selection remain unproven;
- recursive self-improvement, model alignment, compute governance, and cross-lab verification are outside
  the product boundary.

### What Codex contributes to the synthesis

The Codex line contributes the cleaner owner-aware disposition. It distinguishes genuine gaps from work
that already ships, routes decision-quality questions to the existing gold-set candidate, separates
review compression from gate removal, identifies delayed human reconstruction as a testable benefit,
and makes the empirical-loop gap explicit:

```text
recorded evolution: proposal -> decision -> implementation -> session evidence
measured improvement: change -> repeated task outcomes -> comparison -> keep/revert decision
```

Memory Seed implements the first loop. It has not demonstrated the second.

### What Claude contributes to the synthesis

The Claude line contributes the stronger bottleneck and product reading. It connects OpenAI's harness to
Anthropic's compounding-efficiency scenario, states the Amdahl cost of human review plainly, reframes
rejected and deferred rationale as support for opportunity selection, and distinguishes a source that
publishes counter-evidence against its own headline from one that does not. It also demonstrates that
agent-to-agent review can improve an analysis while still sharing a correlated blind spot: both lines
missed shipped behavior until one checked the executable source.

### Remaining tension, resolved for this report

The main substantive tension is whether human gates are simply correct or also unscalable. This report
treats both as true hypotheses with different evidence status:

- **Correct now:** authoritative lineage changes and reconstructed overrides have asymmetric failure
  costs, so current human gates remain justified.
- **Potentially limiting:** neither line found evidence that the current review burden scales with a
  rapidly growing candidate surface.
- **Required next evidence:** measure review time, rework, escaped errors, and false confidence before
  narrowing any gate.

---

## 3. Current capability baseline

This table prevents opportunities from being defined against capabilities that already exist.

| Area | Verified current capability | Remaining gap |
|---|---|---|
| Repository routing | Thin `AGENTS.md`, deterministic skill registry, nearest-runtime discovery, tree-first index, task-triggered skills | Fixed mandatory context remains large; routing efficiency has not been shown safety-equivalent to a smaller packet |
| Durable rationale | DRAFT decisions, alternatives, files/tests, stable entry/decision identity, append-only correction, typed lifecycle edges, accepted ADR heads | No outcome measure showing that this rationale improves a later decision |
| Current-state versus why | Explicit authority split; current behavior checked in code, rationale in memory; agent rules now say never substitute one for the other | No systematic audit showing consequential evaluations consistently check both directions |
| Lifecycle and integrity | Forward-only validated links, session fuse, worktree guards, docs lifecycle checks, human-gated authority movement | Human review cost and safe automation boundary are unmeasured |
| Quality instrumentation | `memory-seed quality report --json` ships; at the snapshot it measured unlinked entries at 179/906 and structural DRAFT reason coverage at 862/862 with 44 excluded | It does not judge persuasiveness, decision quality, stale-rate, or product value; three metrics remain unavailable/not applicable |
| Trust and actionability | Provenance and authority are separate API/UI fields; the taxonomy owner reports steps 1-4 shipped | Policy-derived actionability, fail-closed fixtures, and Constitution section 7 graduation remain gated |
| Browser/application verification | Browser-oriented debugging procedure, rendered checks, fixtures, screenshots, `memory-trace --static-root` | No whole-app per-worktree launch with integrated queryable logs, metrics, traces, runtime budgets, and before/after evidence |
| Multi-agent review | Optional fan-out recipe, isolated worktrees, independent validator, bounded review-to-rework loop capped by a human handoff | No standing measure of review effectiveness, human time, rework, or correlated-review failure |
| Workflow reconstruction | Active evidence/review workbench plan can derive journeys from Markdown, lifecycle metadata, and Git | Three real journeys have not yet been reconstructed; delayed human comprehension and override are not measured |
| Context minimization | A preregistered context-derivation experiment exists with deterministic arms and hard safety gates | Scored execution is blocked pending owner approval; no smaller startup packet is authorised |
| Product evidence | Two frontier labs independently report the capability class as valuable or constraining | No evidence of willingness to adopt or pay for Memory Seed, no broad brownfield proof, and no proof that the why-store changes outcomes |

### Current routing measurement

The two source documents correctly separated the routing stack into two boundaries, but the exact text
has already moved slightly. At this snapshot:

| Boundary | Lines | Characters |
|---|---:|---:|
| `AGENTS.md` + `agent-rules.md` + `skills/orientation.md` | 452 | **30,391** |
| Above + complete `skills/index.md` by the first substantive turn | 776 | **45,492** |

This is not evidence that the guards are waste. It is evidence that any compression proposal must show
equivalent decisions and safety outcomes, not merely fewer characters.

---

## 4. Opportunity register

### O1. Decision and next-step quality benchmark

**Confidence:** High that the gap exists.

**Disposition:** Existing owner; strengthen, do not duplicate.

**Owner:** [`memory-quality-metrics-v0-proposal.md`](../2_Todo/memory-quality-metrics-v0-proposal.md),
especially its inherited constrained-context gold-set candidate.

**Current gate:** JNL's usefulness review of the shipped v0 baseline.

The quality report measures corpus structure and retrieval regressions, not whether a grounded decision
was reached. The existing candidate already calls for real-history questions, bounded-context arms,
blind grading, and negative controls. The combined comparison suggests three outcome classes worth
considering inside that one instrument:

- choosing the better next step from the available evidence;
- recognizing a dead end or a superseded direction;
- choosing justified non-action when the record does not support a change.

These additions should be accepted only if they fit a preregistered, small-N instrument. They should not
become a composite quality score or a dashboard of loosely related metrics.

**Useful evidence:** task accuracy, time to a justified answer, unsupported-claim rate, dead-end
recognition, and negative-control abstention.

**Stop condition:** if the Memory Seed context arm does not beat a bounded code-and-doc baseline, do not
claim that preserved rationale improves decisions.

### O2. Review compression without authority loss

**Confidence:** High that review is a likely bottleneck; unproven that Memory Seed reduces it.

**Disposition:** Bounded evaluation across existing owners.

**Owners:** the bounded review loop in `.memory-seed/skills/agent_collaboration.md`,
[`memory-seed-workflow-evidence-and-review-workbench-plan.md`](../2_Todo/memory-seed-workflow-evidence-and-review-workbench-plan.md),
and the actionability gate in
[`memory-provenance-and-authority-taxonomy-proposal.md`](../2_Todo/memory-provenance-and-authority-taxonomy-proposal.md).

The opportunity is not to remove human approval. It is to compress the material a human must inspect:
a small packet containing the requested decision, source evidence, authority, freshness, conflict state,
rejected alternatives, and exact affected artifacts.

**Useful evidence:** median human review time, correction/rework rate, escaped-error rate, disagreement
rate, and reviewer confidence calibration against a full-source control.

**Safety rule:** no machine score or reviewer consensus silently moves an ADR head, promotes generated
content, or overrides a write-time value.

**Stop condition:** if a compressed packet saves time by hiding evidence needed to reverse the proposed
decision, it fails even when reviewers approve faster.

### O3. Human reconstruction and cognitive continuity

**Confidence:** Medium-high; directly aligned with an active plan, but the benefit is still hypothetical.

**Disposition:** Existing owner; sharpen its evaluation.

**Owner:** [`memory-seed-workflow-evidence-and-review-workbench-plan.md`](../2_Todo/memory-seed-workflow-evidence-and-review-workbench-plan.md).

Anthropic's employee account of losing track of what one has been doing as delegation rises gives this
opportunity a concrete user outcome. The workbench already plans to reconstruct three completed journeys.
The stronger test is not merely whether the graph can render them, but whether a maintainer who did not
hold the original context can:

- explain why the work happened;
- distinguish shipped fact from recorded rationale;
- identify the rejected path and the live successor;
- locate the evidence needed to challenge the decision;
- safely override or continue the work after a delay.

**Useful evidence:** reconstruction completeness, time, incorrect authority claims, and ability to name
the safe override path.

**Non-goal:** a transcript warehouse or raw agent telemetry store.

### O4. Integrated per-worktree application observability

**Confidence:** High that the technical gap exists.

**Disposition:** Genuine bounded candidate with no clear current owner.

**Related capability:** `memory-trace --static-root`, browser-oriented debugging guidance, and rendered
verification. The superseded workflow-observability exploration now points to a workbench that explicitly
excludes raw telemetry, so it does not own this runtime-harness gap.

A focused evaluation would combine:

- an isolated whole-application instance per worktree;
- deterministic browser/protocol access;
- local, ephemeral logs and metrics tied to that instance;
- prompt-checkable functional and performance budgets;
- before/after rendered evidence;
- package, checkout, and asset provenance proving which code was exercised.

This should remain local, content-minimal, and disposable. Observability must not be confused with
environment provenance: runtime telemetry cannot prove that a stale global CLI or wrong checkout was
loaded.

**Useful evidence:** reproduction time, percentage of defects diagnosed without human runtime narration,
false-clean rate, and teardown reliability.

**Stop condition:** if the harness cannot bind evidence to an exact worktree, executable, and asset
revision, its extra telemetry creates confidence without provenance.

### O5. Safety-equivalent startup context compression

**Confidence:** High that the fixed cost exists; unknown whether it can be reduced safely.

**Disposition:** Existing experiment; no production change.

**Owner:** [`experiments/context-derivation/`](../../experiments/context-derivation/).

The preregistered experiment already has the right shape: multiple Claude/Codex arms, real and
adversarial cases, deterministic fingerprints, explicit absence, and hard failures for wrong authority
or edge typing. It is blocked pending owner approval of the preregistration and gold labels.

The opportunity is to extend the result carefully from retrieval packets toward the fixed routing stack,
not to invent an intuitive summary of `agent-rules.md`.

**Useful evidence:** equal or better task decisions, zero lost safety guards, lower irrelevant-token and
total-token counts, stable resolution, and no increase in confident wrong answers.

**Stop condition:** any packet that saves context while changing an approval, worktree, authority,
destructive-action, or source-verification decision is ineligible.

### O6. Complete trust-to-actionability rather than add a trust score

**Confidence:** High; an active, partially shipped owner already defines the gap.

**Disposition:** Continue only through the existing gate.

**Owner:** [`memory-provenance-and-authority-taxonomy-proposal.md`](../2_Todo/memory-provenance-and-authority-taxonomy-proposal.md).

The combined external reading reinforces why provenance, authority, confidence, lifecycle, and
actionability must remain separate. Research taste includes deciding which result to trust, but neither
external article supplies a reliable general truth score. Memory Seed should finish its reason-coded,
fail-closed actionability policy and fixtures only after the participant/role dependency and explicit
maintainer gate.

**Useful evidence:** generated and provider-inferred material cannot become actionable alone; every
actionability result explains its source, authority, freshness, conflict, scope, and role inputs.

**Non-goal:** a single numeric trust score or default ranking change.

### O7. Bidirectional current-state and rationale verification

**Confidence:** High; the comparison itself reproduced the failure.

**Disposition:** Partly absorbed into current agent rules; audit before proposing more process.

The paired review exposed both halves:

- code-only review can recommend work that recorded rationale already rejected or scoped elsewhere;
- memory-only review can report a capability gap that shipped code has already closed.

The current agent rules now explicitly say files are authority for what is true now and memory for why,
and forbid substituting one for the other. The remaining opportunity is to test whether consequential
reviews actually follow that rule.

**Useful evidence:** a sample of design reviews showing current implementation checks, retrieved prior
rationale, explicit disposition of conflicts, and fewer duplicate or stale recommendations.

**Non-goal:** loading all code and all history into every context.

### O8. Agent-legible refusals and bounded non-corpus gardening

**Confidence:** Medium; partly present and current lifecycle checks are healthy.

**Disposition:** Audit/operating practice, not a new product programme.

Two smaller OpenAI practices survive the paired review:

- every mechanical refusal should name the failed invariant, responsible surface, and exact recovery
  action when one exists;
- recurring, dry-run-first cleanup may suit ordinary code, generated indexes, broken links, and encoding
  drift.

Neither practice should auto-edit session prose or published sidecar blocks. At this snapshot `docs
check` is healthy with 16 incomplete-metadata warnings and no lifecycle errors, so there is no evidence
for an urgent generic cleanup agent.

**Useful evidence:** inventory of refusals lacking cause/owner/recovery; repeated non-corpus drift classes
that a deterministic check can identify.

**Stop condition:** do not build a recurring agent for a class that has no repeated, measurable residue.

### O9. Opportunity-selection and portfolio memory

**Confidence:** Medium; strategically plausible, not yet a defined product capability.

**Disposition:** Research question, not accepted work.

Claude's strongest product extension is that rejected and deferred rationale may help an organization
choose among more candidate directions than it can pursue. Memory Seed already stores alternatives,
rejections, deferrals, and successors. It does not model the complete opportunity set at the time of a
decision or show that the project selected the best available problem.

A defensible first question is smaller: can the existing corpus prevent a team from repeating a known
dead end or help it recognize that a candidate duplicates, conflicts with, or depends on prior work?
That can be evaluated through O1 before inventing portfolio-management state.

**Non-goals:** universal project management, automatic prioritization, or an agent deciding the product
roadmap from memory frequency.

### O10. Product validation and brownfield differentiation

**Confidence:** High that the evidence gap exists.

**Disposition:** Market/user research; not an engineering next step.

The OpenAI investment is evidence of demand for the capability. Anthropic's account strengthens the
hypothesis that knowing what to do next and what to trust becomes more important as execution scales.
Neither shows that an external team will install, retain, or pay for Memory Seed.

The product thesis should therefore be tested around the differentiated wedge:

- installation into an existing repository with pre-existing agent instructions and decision history;
- recovery of why behind a real changed or abandoned architecture;
- cross-agent continuity without a hosted authoritative store;
- review and reconstruction benefits that a team does not obtain from ordinary docs and Git alone.

**Useful evidence:** successful foreign-repository adoption, time to first useful retrieval, continued use,
decision/review outcome improvement, and stated willingness to adopt or pay.

**Stop condition:** if users value only current-state repository documentation, the build-versus-buy
threat dominates and Memory Seed's differentiated product claim weakens substantially.

---

## 5. Triage view

### Advance only through existing owners

1. Decision-quality benchmark -- after the quality-v0 usefulness review.
2. Workflow reconstruction -- begin with the workbench's three real journeys.
3. Trust/actionability -- complete the existing participant/role and maintainer gates.
4. Context minimization -- approve or reject the existing preregistration; do not fork it.

### Bounded candidates that still need an owner decision

1. Per-worktree whole-application observability.
2. Review-compression measurement across evidence packets and bounded review loops.
3. A refusal-message audit and evidence of repeated non-corpus drift before recurring gardening.

### Research and market questions

1. Does durable rationale improve next-step choice or only recall?
2. Can a maintainer reconstruct and override delegated work after delay?
3. Does rejected/deferred history reduce repeated dead ends?
4. Will brownfield teams adopt or pay for the why-store rather than hand-roll current-state docs?

### Explicitly reject or keep out of scope

- a second quality metric family or composite grade;
- treating entry, edge, decision, or code volume as product value;
- minimal merge gates or self-merging agents for authoritative memory writes;
- automatic promotion of generated or provider-inferred content;
- unbounded reviewer/reworker loops;
- autonomous control-plane self-modification;
- claims that Memory Seed secures recursive self-improvement, model weights, training runs, alignment, or compute.

---

## 6. Cross-cutting risks

### Optimizing the proxy

Both external reports use output measures that can outrun quality. Memory Seed has the same exposure if
it optimizes edge density, DRAFT coverage, entry count, or review speed without measuring correctness,
rework, and justified abstention.

### Review theater

Agent-to-agent review improved both source documents, but both also shared a memory-only blind spot. More
reviewers are not independent evidence when they inspect the same stale source. Review packets must show
which executable facts and which rationale records were checked.

### Over-authoritative memory

The system's reliability mechanisms can make a stale record harder for an agent to challenge. Human
gates alone do not solve that if the review surface hides current successors, conflicts, or code reality.
Every compression opportunity must preserve a clear override and correction path.

### Building against frontier-lab conditions

OpenAI and Anthropic describe unusually capable models, infrastructure, and teams. Their mechanisms are
useful design evidence, but their throughput and autonomy levels are not a representative customer
baseline. Portable degradation to plain files and ordinary file-reading agents remains a product
constraint, not legacy baggage.

### Expanding beyond the core wedge

Runtime observability, workflow review, opportunity selection, and governance can each become a separate
product. Memory Seed should own durable rationale and evidence linkage first, integrate with existing
runtime/issue/review systems where possible, and avoid becoming an orchestrator or telemetry warehouse.

---

## 7. Recommended decision sequence

This is a proposed order for triage, not approval:

1. **Make the existing quality-v0 usefulness decision.** It gates the decision-quality benchmark and
   prevents further metric proposals from circling the same unresolved owner decision.
2. **Run the workbench's three-journey reconstruction.** It is the cheapest direct test of the why-store's
   human value and reveals missing evidence references before new schema is proposed.
3. **Decide whether to approve the context-derivation preregistration.** The experiment already exists;
   leaving it indefinitely blocked preserves the startup-cost question without producing evidence.
4. **Scope one review-compression experiment.** Use existing evidence and actionability fields; change no
   authority gate during the test.
5. **Decide whether whole-app per-worktree observability belongs to Memory Seed or an integration.** The
   capability gap is real, but product ownership is not established.
6. **Seek foreign-repository evidence before expanding the product claim.** Validate the brownfield
   why-store wedge, not generic repository documentation.

The central test across all six decisions is the same: does the opportunity help a human or agent make,
review, reconstruct, or safely revise a better decision? If it only creates more artifacts, more scores,
or more automated output, it does not answer the gap the paired comparison identified.
