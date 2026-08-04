---
title: "Developer Project-Memory Wedge"
status: active-hypothesis
last_reviewed: "2026-08-03"
next_review_due: "2026-10-01"
confidence: medium
---

# Developer project-memory wedge

## Purpose and current conclusion

This dossier defines Memory Seed's initial market wedge: **Git-native, decision-centric project memory
for developers and human-AI engineering teams**.

Memory Seed should enter through the recurring failure to preserve what was decided, why it was decided,
which evidence supported it, and what later replaced it across coding-agent sessions. It should not enter
as a generic chatbot memory, coding agent, project board, or enterprise search product.

## Operating premise

Ratified 2026-08-03 (JNL): **agents are the primary readers and writers of project memory; humans
curate, verify, and resolve disputes.**

Consequences this dossier now assumes:

- **One authoritative store, never fragmented.** Concern-scoped and per-audience views are derived
  projections over the single corpus; rationale is not scattered into per-concern documents. This is
  Constitution Invariant #6 applied as strategy, and it is the answer to the field critique that
  decisions belong "where people are looking" — views multiply, the store does not split.
- **Agent consumption is push-first.** Session-start loading and ranked retrieval are the primary read
  path. Token cost is the ergonomics, so minimal-but-sufficient context is a core product property
  rather than an aspiration.
- **Memory Trace is the human surface**, designed for the cold, high-stakes lookup — the incident
  "why", onboarding, promotion approval, verifying what agents recorded — not habitual reading. Field
  evidence says humans do not revisit decision records; Trace exists so the rare visit succeeds
  instantly.
- **Write-time capture runs through the agent that made the decision.** A validation-refused write
  costs an agent a retry, not resentment, which is how the field's cheapness criterion — "capturing
  must be cheaper than not capturing, at the moment it happens" — is met mechanically rather than by
  discipline.

Evidence: [field evidence log, E1–E3](../research/field-evidence-log.md). Standing caveats: the premise
does not date the agent-coding world's arrival or name who pays before it comes — the validation
requirements below stand unchanged — and it raises the urgency of the passive-capture test, because
agent transcripts are minable and first-hand capture's measured advantage over reconstruction
(0.583/0.613 macro-recall, topic-swarm pilot) is one repository's data.

## Initial customer and user

### Primary early user

- A developer or technical founder using more than one coding agent.
- Works in a Git repository over weeks or months.
- Repeatedly re-explains architecture, constraints, prior attempts, and project status.
- Values local control, readable files, portability, and evidence more than fully passive capture.

### First team buyer

- Engineering lead, platform lead, or AI enablement lead responsible for consistent agent behaviour.
- Needs onboarding, shared decisions, provenance, auditability, and handover across people and agents.
- Can adopt repository-local tooling without a broad enterprise-data integration project.

### Later enterprise buyer

- Platform engineering, developer experience, AI governance, or engineering productivity.
- Requires policy, permissions, reporting, support, controlled rollout, and deployment options.

## Problem statement

Coding agents are increasingly capable of real delegated work, but project context remains fragmented
across chats, branches, tickets, documents, tools, and individual memory. The failure is not just recall:
teams cannot reliably determine which decision is authoritative, why it exists, what evidence supports
it, or whether a later decision superseded it.

## Wedge promise

> One inspectable project memory, using the same plumbing for humans and agents.

The entry product should make four jobs materially easier:

1. Resume a project or task without reconstructing context manually.
2. Give a new human or agent the current decisions, constraints, risks, and recent state.
3. Trace a decision to evidence and see how it evolved or was superseded.
4. Move between coding agents without surrendering project memory to one vendor.

## Differentiators to prove

- Git-native Markdown as the durable, portable authority.
- Decisions, evidence, provenance, evolution, and supersession as first-class objects.
- One memory model exposed to humans, CLI workflows, and MCP-capable agents.
- Local-first operation with an optional managed path.
- Explicit governance and inspectability rather than opaque extraction alone.

These are hypotheses until customer evidence shows they affect adoption, retention, willingness to pay,
or switching behaviour.

## Adoption path

1. **Solo/local:** seed one repository and recover context across agent sessions.
2. **Multi-agent:** use the same project memory from Codex, Claude Code, Gemini, Cursor, and other clients.
3. **Team:** share decisions, onboarding, handovers, and reviewable agent work through Git.
4. **Managed team:** add hosted indexing, collaboration, policy, reporting, and administration.
5. **Enterprise:** add deployment control, permissions, compliance evidence, and support.

## Alternatives considered

| Alternative wedge | Why it is not first |
|---|---|
| Generic agent-memory API | Crowded and vulnerable to model-provider or hyperscaler bundling |
| Personal “remember everything” assistant | Requires passive capture, broad connectors, and consumer trust beyond the current product |
| Project-management board for agents | Competes with established systems and makes project state—not reasoning—the primary object |
| Enterprise search/context layer | Large integration burden and long sales cycle before the core decision-memory value is proven |
| Coding agent or orchestration platform | Places Memory Seed against better-capitalized execution products instead of beneath them |

## Evidence currently supporting the wedge

### Sourced market evidence

- Competitors increasingly describe memory as production agent infrastructure; see the
  [competitor landscape](../market/competitor-landscape.md).
- The cloud-native developer population provides a large technically compatible entry segment; see
  [market size](../market/market-size.md).
- Published competitor pricing supports free/open-source entry followed by paid individual and team
  tiers; see [competitor pricing](../market/competitor-pricing.md).

### Internal product evidence

- Memory Seed already implements repository-local Markdown memory, deterministic onboarding,
  session history, multi-agent routing, MCP retrieval, and human inspection surfaces.
- Existing market-fit and strategic reports repeatedly converge on portable project memory rather
  than another coding agent as the strongest position.

These observations demonstrate product-problem alignment, not product-market fit.

## Validation requirements

Before broadening the wedge, collect evidence from at least:

- 20 structured interviews across solo developers, technical founders, engineering leads, and AI/platform leads.
- 10 active repositories using Memory Seed for at least four weeks.
- Measured time-to-first-value and successful second-session recovery.
- Weekly retention, repositories retained, agent surfaces used, and memory retrieval frequency.
- At least five attempts to buy, including objections and preferred pricing unit.
- Direct comparisons against plain `AGENTS.md`, vendor chat memory, and at least one memory API.

## Failure and pivot signals

- Users value onboarding instructions but do not return to stored decisions.
- Git-authored memory is experienced as maintenance work rather than saved work.
- Passive capture consistently outperforms deliberate project records for the target job.
- Cross-agent portability does not influence tool choice or willingness to pay.
- Teams will pay only for a broader project-management, search, or observability product.

## Related dossiers

- [Market size](../market/market-size.md)
- [Competitor landscape](../market/competitor-landscape.md)
- [Competitor pricing](../market/competitor-pricing.md)
- [Earlier strategic synthesis](memory-seed-strategic-synthesis-report.md)
- [Earlier market-fit report](../market/memory-seed-market-fit-report.md)

## Unresolved validation questions

- ~~Do agents with the MCP write path available record decisions without being prompted?~~
  **ANSWERED (E5/E6, 120 sessions across two matrices).** Essentially never on the tool alone —
  pooled capture 0.05, an interval that does not approach any other arm; the full ladder L0→L3 is
  a trend at p ≈ 7e-14. **One line in `AGENTS.md` naming the store lifts it to ~0.77**, and capture
  keeps climbing with scaffolding: pooled L1 0.77 → L2 0.83 → L3 0.91. That further climb is
  *suggestive but not established* — Cochran-Armitage across L1–L3 gives p ≈ 0.11, and the ordering
  itself did not replicate (v2 put L2 fractionally above L3). Faithfulness held where it could be
  measured: 0 of 121 recorded reasons judged a post-hoc reconstruction. Treat the *pattern* as the
  finding; the pre-registered 0.80 threshold verdict flipped between two identical runs and is not
  a basis for any decision at feasible sample sizes.
  **Consequence for the premise:** write-time capture through the deciding agent works, but it is
  not free — it needs a routing instruction present, not merely a tool installed. E2's
  enforcement-is-not-cheapness criticism lands softer than v1 suggested and harder than v2 did: the
  entry price is one line. Whether the rest of the control plane buys the further ~14 points from
  0.77 to 0.91 is the open commercial question — direction consistent, significance not reached.
- Does the one-line result hold outside this stub project, these three tasks, and this model family?
  This is now the load-bearing generalisation question, and it is the cheapest remaining test.
- Do hooks earn their place under context pressure? The aggregate L1→L3 climb is flat, but a
  post-hoc split at median session length shows the L3−L1 gap running −0.20 in short sessions and
  **+0.34 in long ones** — L1 capture falling 1.00 → 0.62 as sessions lengthen while L3 holds at
  0.96. That split conditions on a post-treatment variable (scaffolding itself lengthens sessions,
  L0 16.6 → L3 28.1 mean turns) so it is **not** quotable, but it agrees with the maintainer's build
  experience and has a plausible mechanism: the fixtures' 12–27 turn tasks gave a `Stop` or
  `SessionStart` hook nothing to do. **Deferred, not scheduled** — design recorded as Test 4 in the
  roadmap report. Until it runs, argue the control plane on structure, retrieval and governance,
  not on capture.
- **What surfaces a decision again?** E7's strongest field challenge is that records read only at
  write time are dead weight, and that the half worth writing are the half a failing test pointed
  back at. Capture is measured and largely solved; the retrieval trigger is the contested ground.
  The concrete unbuilt move: surface the relevant decision when an execution artefact fails or is
  touched, using the `F:` file references and typed edges already recorded. Tests are a good
  trigger and a poor record — they carry no rejected alternative — so this is complementary to the
  store, not a substitute for it.
- **Can a stale record veto the user?** E7 records a practitioner whose ADR made the agent refuse a
  new product decision. Every property that makes this store reliable — validated, agent-loaded,
  enforced — also makes a stale record harder to override. Supersession is the designed answer;
  whether retrieval surfaces current status prominently enough is untested.
- Is the beachhead solo developers, technical founders, or an engineering-platform team? **E7
  complicates this**: the sharpest cost analysis in the field research says a solo developer does
  not need a decision record. The reconciliation — the solo developer is not the reader, their agent
  is — must be argued rather than assumed.
- Is the decisive paid feature hosted retrieval, team governance, Memory Trace, or handover reporting?
- How much deliberate authoring can users tolerate before passive assistance becomes necessary?
- Which outcome is easiest to measure: reduced re-explanation, faster onboarding, fewer repeated mistakes,
  or more trustworthy agent delegation?

## Change log

- **2026-08-04:** Closed the unprompted-agent-authoring question with E5/E6 (120 controlled
  sessions). The tool alone is not used; one `AGENTS.md` line carries most of the gain. Ratified by
  JNL that the pre-registered threshold verdict is not decision-grade at this sample size and that
  the replicated pattern, not the binary, governs. Added the generalisation question that replaces it.
- **2026-08-03:** Ratified the operating premise — agents are the primary readers and writers; one
  authoritative store with derived views; Trace as the human cold-lookup and trust surface;
  write-time capture through the deciding agent — with field evidence E1–E3 attached. Added the
  unprompted-agent-authoring validation question.
- **2026-08-01:** Created the living wedge dossier and defined the initial customer, promise,
  alternatives, validation requirements, and pivot signals.

