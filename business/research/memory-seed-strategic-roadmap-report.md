---
title: "Strategic Roadmap Report"
date: "2026-08-01"
project: "memory-seed"
kind: "report"
next_action: "source-only"
author_context: "Prepared for Jean Nathan Tshibuyi (JNL). Report 7 of 7 — the synthesis."
---

# Strategic Roadmap Report

**Report 7 of 7.** The final synthesis, drawing on all six prior reports.

**Headline: the strongest recommendation this programme can make is to stop researching and spend the
next ninety days buying demand evidence. Three tests, each capable of killing the thesis, none costing
more than a few weeks. The revenue fork cannot be resolved before them — and should not be.**

---

## Inputs

All six prior reports, plus the business dossiers ([wedge](../wedges/developer-project-memory.md),
[market size](../market/market-size.md), [competitors](../market/competitor-landscape.md)) and
[`CONSTITUTION.md`](../../docs/CONSTITUTION.md).

> **Amendment, 2026-08-03 — Test 1 has now run.** See the [field evidence log](field-evidence-log.md).
> Six of six responders described the pain unprompted; every one had built their own workaround. Two
> revisions follow. Neither changes the ninety-day plan in §4 — they change what §2 question 4 ranks first.
>
> **(a) The binding constraint is loading, not storage.** This report and the six before it treated the
> record as the product and retrieval as a feature. A practitioner who spent months on the problem reports
> the reverse: *"a rule only binds if it's in the prompt the session actually loads… rules that lived in a
> shared doc got ignored under pressure."* Push — startup-loading the decisions relevant to the task —
> beats pull, where the agent must remember to search. **The SessionStart hook and MCP retrieval move from
> plumbing to headline**, and belong alongside the promotion layer rather than below it.
>
> **(c) The #1 ranked feature shipped the same day.** §2 question 4 ranked *"mark which decisions govern"*
> first and called it *"the only one that changes the product's category."* It was built and merged on
> 2026-08-03 (`memory-seed adr`, three live ADRs, contract promoted out of draft — see the
> [ADR report's amendment](architecture-decision-record-standards-report.md)). **Year 1 Q2 of §10 is
> therefore complete before Q1's tests have run**, which inverts the sequencing this report argued for.
> That is not a failure — the capability is real and correctly built — but it means the ninety-day plan in
> §4 is now the *only* outstanding item, and the argument for running the tests before building is spent.
> Evidence Pack export becomes the next unbuilt feature on the list.
>
> **(b) The convergent design is a threat as well as a validation.** One person independently reproduced
> structured decision records, rejected-alternatives-as-a-field, never-delete-only-mark-superseded, and
> write-at-the-moment-of-abandonment — alone, part-time, with no prior art. **The moat is not the data
> model.** If one exists it is in what they did *not* build: validated referential integrity on
> supersession, enforcement that refuses a record without a reason, and guaranteed injection at session
> start. Risk #2 in §6 (nobody does the authoring) is partly answered by their mechanism — have the agent
> that lived the failure write it down before it moves on — which is worth adopting explicitly.

**Standing caveat, unchanged through seven reports: no user has been interviewed, no purchase attempted,
no retention observed.** Everything below is inference. The recommendations are ordered so the cheapest
disconfirmations come first, precisely because of that.

---

> **Amendment, 2026-08-04 — the capture experiment has run (E5/E6).** 120 controlled headless
> sessions across four scaffolding levels, blind cross-model judged. Three revisions.
>
> **(a) The MCP server is not the product; the routing line is.** With the write path installed and
> nothing else said, agents record 5% of their decisions. One line in `AGENTS.md` naming the store
> takes that to 77%. This is the hardest number in the programme (ladder p ≈ 7e-14, replicated
> across two independent 60-session matrices). **Install correctness therefore outranks feature
> depth in §4 and §9**: any integration path that registers the MCP server without writing a routing
> instruction ships a 5%-capture product. It also kills any "just add our MCP server" distribution
> story — a marketplace one-click MCP install, absent a routing line, will underperform badly and
> generate churn that reads as product failure.
>
> **(b) Recorded rationale is trustworthy, and that is the claim to sell.** Of 121 recorded
> decisions, **zero** were judged post-hoc reconstructions (104 faithful, 17 unclear). Noise was
> ~0 across 120 sessions. §7's benchmark list should lead with faithfulness and noise, which are now
> evidenced, rather than capture volume, which is not differentiating.
>
> **(c) Hooks look load-bearing under context pressure, not in short sessions.** Pooled L1→L3 is
> flat and non-significant, but that average hides an interaction: splitting at the median session
> length, the L3-minus-L1 gap is −0.20 in short sessions and **+0.34 in long ones** — L1 capture
> collapses from 1.00 to 0.62 as sessions lengthen while L3 holds at 0.96. This is a post-hoc split
> on a post-treatment variable and is **not** quotable as a result, but it agrees with the
> maintainer's independent build experience and has a plausible mechanism. It means the fixtures
> (12–27 turn tasks) were blind to what hooks are for. **Do not claim hooks improve capture; do not
> conclude they don't.** The properly-designed test is noted in §4 as deferred.

> **Amendment, 2026-08-05 — the veto and the benchmark (E8/E9).** Two revisions to §4 and §7.
>
> **(a) The shipped control plane refused user instructions, and that was a product decision nobody
> had made.** A seeded probe found 4 of 6 sessions declining a direct instruction that reversed a
> recorded decision, citing `risk_signaling.md`'s STOP category by name — reproducing verbatim the
> complaint a practitioner reported in E1. It is fixed (a live instruction is now the amendment
> authority, with a mandatory superseding entry; 6/6 comply post-fix), but the lesson generalises:
> **the control plane can encode a posture the roadmap never chose.** §7's research gaps should
> include periodic probes of what the shipped rules actually make agents *refuse*, not only what
> they make agents record.
>
> **(b) An independent benchmark now exists for this category, and the top of it is a Markdown
> pattern.** Verging Labs' Agentic Memory Index (v0.1, August 2026) ranks a self-curated Markdown
> wiki above every hosted product; Garry Tan's `gbrain` beats every hosted API but one. Both landed
> in April 2026. **That is market validation of the substrate, and it compresses the differentiation
> onto everything above the substrate** — validated writes, supersession, provenance — which is
> exactly where the benchmark's winners fail (the wiki was the only system to hallucinate on a
> never-stored question). §4 gains a dated decision point: v0.2 lands early September, submission is
> via their radar form, and a private dry-run precedes any submission. Do not quote an internal
> score externally.

## 1. Executive summary

**What the programme established.**

1. **Governance frameworks converge on eight evidence questions**, and *why* is the second most-demanded
   — REQUIRED in 12 of 19 frameworks, ahead of who, when, and who-approved (R1, R2).
2. **Memory Seed answers four of the eight structurally, three partially, one not at all** (R2).
3. **Its core mechanism is genuinely unoccupied.** No ADR tool validates anything — `adr-tools` last
   released 2018, Log4brains states it enforces no structure, Backstage only indexes, Notion has no
   required field. Supersession everywhere is a free-text link with zero referential integrity (R3, R5).
4. **`evolves` solves a problem the ADR ecosystem openly hasn't** — amending a decision without
   superseding it (R5).
5. **But nobody funds "decision rationale" as a budget line** (R3), the literature contains no evidence
   that documentation improves outcomes (R4), and **there is no demand evidence at all** (R6).
6. **The regulated verticals are disqualified structurally** — they mandate link traceability, not
   rationale, and tool qualification closes what remains (R6).
7. **The revenue paths differ by two orders of magnitude**, and the difference is structure, not
   effort (R6).

**What follows from it.** The product is real, the mechanism is defensible, the market is unproven, and
the ambition attached to it belongs to a path that isn't currently being walked. The correct response is
not to pick a path — it is to buy the evidence that would let you pick one, at the lowest possible cost.

---

## 2. The ten questions, answered

### 1. What should Memory Seed become?

**The decision-record substrate for engineering work done with AI agents** — the layer that captures what
was decided and why at the moment of work, refuses the record if the reason is missing, and maintains a
validated, append-only graph of how decisions superseded one another.

Not a governance platform. Not a compliance product. Not another memory API. The Constitution's own
vision statement is already correct and needs no revision: *"the local-first, model-independent memory
substrate that preserves a project's reasoning."*

### 2. What should it deliberately avoid?

| Avoid | Why | Source |
|---|---|---|
| **Creating a category** | Capital-intensive by nature; "a death sentence" for 90% of B2B SaaS without budget; **no solo unfunded example exists** | R6 |
| **Compliance positioning** | Wrong buyer, wrong artefact, and unsupportable until decisions are marked as governing | R2, R3 |
| **Framework-specific modules** | The gaps are *shared* — one capability set lifts most frameworks. Per-framework work inverts the leverage | R2 |
| **Competing on evidence collection** | Vanta ~$4B, ~400 integrations. Control state is not what Memory Seed produces | R3 |
| **Medical devices, airborne aerospace** | Tool qualification (21 CFR 820.70(i), DO-330) is structurally unfundable | R6 |
| **Cold outreach** | No evidence it works for bottom-up devtools | R6 |
| **New edge kinds / Szlenk relations** | Design-space configuration tooling, not decision memory | R5 |
| **Review cycles, mutable status, entry `type`** | Deliberate silence in every convention; already tried and replaced internally | R5 |
| **Claiming ADR conventions validate the product** | ADR adoption measured across 921 repos, never correlated with any outcome | R4, R5 |

### 3. Which industries first?

**Horizontal software engineering — specifically teams running multiple coding agents.** Not a vertical.

Order: multi-agent solo builders (adoption) → small AI-forward engineering teams, 5–30 engineers (first
revenue) → AI-native startups facing customer AI-governance questionnaires (the only external forcing
function) → consultancies (under-explored) → **financial services, later and deliberately**, because
SR 11-7's *"how the model operates, its limitations, and its key assumptions"* is the one regulatory text
whose language matches the product.

### 4. Which features create the highest commercial leverage?

Ranked, with the Constitution's five-question test applied:

| # | Feature | Leverage | Five-question test |
|---|---|---|---|
| 1 | **Mark which decisions govern** (ADR promotion layer) | Unlocks retrieval quality, evidence packs, and every governance claim. The corpus holds 876 addressable decisions and most are tactical | **Retrieval + Trust** |
| 2 | **Evidence Pack export** | The deterministic builder exists; there is no door out | **Application** |
| 3 | **Evaluation criteria** field | Demanded independently by MADR and CMMI DAR; absent | **Capture** |
| 4 | **PR-approval linkage** | Closes E7 by reference, inheriting auditor acceptance rather than rebuilding it | **Trust** |
| 5 | **Affected systems** beyond file paths | REQUIRED in 11 of 19 frameworks | **Capture** |

**Feature 1 is the only one that changes the product's category.** The rest are refinements.

### 5. Which standards should influence the architecture?

Only two, and both already have:

- **ISO/IEC/IEEE 42010:2022** — rationale as a first-class concept. Already reflected in mandatory `R:`.
- **The EU AI Act's Annex IV** — design-choice rationale, dated and attributed test evidence, lifecycle
  change records. The closest thing to a statutory specification for a decision record.

**MADR should influence the *grammar*** (its `Confirmation` field is functionally `T:`; its
`Decision Drivers` is the missing criteria field), but it is a template, not an architecture.

### 6. Which standards should simply be supported?

Supported as *evidence targets*, not architectural drivers: ISO/IEC 42001, ISO/IEC 27001 (Statement of
Applicability and A.8.32 change management), HIPAA §164.306(d)(3), CMMI DAR, NIST AI RMF.

**Explicitly not supported at all:** NIST CSF 2.0, ISO 31000, OECD AI Principles — confirmed false
opportunities across three reports, with nothing to attach evidence to.

### 7. Which benchmarks must exist before launch?

From R4, in order:

1. **The decision-recovery gold set** — 30–50 real questions, three context arms, blind-graded, with
   **mandatory negative controls** to distinguish retrieval from confabulation.
2. **Token efficiency** over a frozen task set — deterministic, no humans, and the only measurement that
   maps to a cost buyers already pay.
3. **Negative-control abstention rate** — the experiment designed to find harm rather than benefit.

**Not required before launch:** onboarding time (no validated benchmark exists anywhere), audit
preparation time (unmeasurable before the promotion layer), anything self-reported.

### 8. Which integrations are highest priority?

| # | Integration | Why |
|---|---|---|
| 1 | **GitHub PR review** | The approval record already exists, is authenticated, is bound to a commit SHA, and is already harvested by Vanta and Hyperproof. Link it, don't rebuild it |
| 2 | **MCP** (already shipped) | The distribution surface for every agent |
| 3 | **Backstage catalog** | Its catalog has ownership and dependency relations but **no Decision entity** — complementary, not competitive |
| 4 | **OpenTelemetry** | As an evidence *source* (E5), not an overlap |

### 9. What should the MVP include?

**The MVP already exists and is shipped.** The real question is what is missing for the first *paying*
user, and the answer is short:

- The promotion layer (feature 1)
- Evidence Pack export (feature 2)
- A landing page that answers *"I already have `AGENTS.md`"*

Nothing else. **Do not build any of it until §4's tests have run.**

### 10. The three-year roadmap

A three-year roadmap without demand evidence is fiction beyond the first year. Structured honestly:

**Year 1 — buy evidence, then build the unlock.**
- Q1: the three cheap tests (§4). Gate: does anyone describe this pain unprompted?
- Q2: promotion layer + Evidence Pack export, *if* Q1 passed.
- Q3: first paid tier at $8–10/month individual. Gate: five real purchases.
- Q4: evaluation criteria, PR-approval linkage; external gold-set replication on a foreign corpus.

**Years 2–3 — conditional branches, not a plan.**

| If Year 1 shows… | Then |
|---|---|
| Strong individual adoption, weak payment | Proprietary-with-free-tier fork (Obsidian shape), or accept a lifestyle-scale outcome |
| Team purchases and retention | Team tier, hosted sync, and the funding question becomes live |
| Passive capture wins | **Pivot or stop.** The wedge assumption failed |
| Neither adoption nor payment | Stop. It was a well-built tool for a problem nobody prioritises |

**Writing Years 2–3 as anything more specific would be manufacturing false confidence.**

---

## 3. Product thesis

> Engineering teams increasingly delegate work to AI agents that have no memory of why anything was
> decided. The reasoning behind a decision is the one artefact that cannot be recovered from the code,
> the commit history, or the ticket — and it is the artefact governance frameworks most consistently
> demand. Memory Seed captures it at the moment of work, refuses the record without it, and keeps a
> validated history of how decisions superseded one another, as plain files the user owns.

**What makes this defensible:** enforcement (no competitor does it), typed and validated lifecycle edges
(no competitor does it), and local-first Markdown ownership (a story SaaS cannot tell).

**What makes it fragile:** it requires deliberate authoring in a market where passive capture is
well-funded and improving, and there is no evidence anyone will pay for it.

---

## 4. Recommended next actions — the ninety-day plan

**Nothing in this plan is a build. All of it is evidence.**

### Test 1 — Does the pain exist? *(2 weeks, ~free)*

Ten unprompted conversations in r/ClaudeCode, the Cursor and Claude Code Discords, and the Local-First
community. One question: *what happens when an agent re-derives a decision you already made, and what do
you do about it today?*

**Do not pitch.** If the pain is not described unprompted, that is the answer.

### Test 2 — Does passive capture already win? *(1 week, ~free)*

Find people using Pieces or Unblocked. Ask: *when you ask why something was built a certain way, do you
get a real answer, or a summary of what happened?*

**This is the existential test and it is nearly free.** If passive capture answers "why" well enough, the
wedge fails regardless of market, feature, or vertical. It is listed as a watch point in the competitor
dossier and a pivot signal in the wedge dossier, and nobody has run it.

### Test 3 — Does the corpus actually help? *(4 weeks)*

R4's internal gold set: 30–50 real questions from this repository, three arms, blind-graded, with
negative controls.

**If the corpus arm does not beat the baseline arm on the corpus you maintain yourself, stop.** That is
the cheapest possible disconfirmation and it costs four weeks.

### Test 4 — Do hooks earn their place under context pressure? *(DEFERRED — noted, not scheduled)*

**Status: deliberately not running.** Recorded here so it is not lost, and so nobody re-derives it.

E5/E6 found the L1→L3 climb flat in aggregate but strongly length-dependent in a post-hoc split
(L3−L1 = −0.20 in short sessions, +0.34 in long ones), which the maintainer's build experience
independently corroborates. The existing fixtures cannot settle it: their tasks run 12–27 turns, and
a `SessionStart` orientation or `Stop` session-log check has nothing to do in a session that short.

**The design, when it is worth running:** long multi-decision tasks where session length is fixed
*by design* rather than measured after the fact — otherwise the analysis conditions on a
post-treatment variable, since scaffolding itself lengthens sessions (mean turns L0 16.6 → L3 28.1).
Score capture of decisions made **early** in a long session specifically; that is the decision a
`Stop` hook exists to rescue, and it is where the mechanism should show up if it is real.

**Why it matters commercially:** it decides whether the hooks and rules contract are load-bearing
for *capture*, or only for structure, retrieval, and governance. Until it runs, the control plane
must be argued on the latter. Unlike the 0.80 threshold question, this one is genuinely resolvable
by more data — it is a trend and an interaction, not a knife-edge against a fixed line.

### Then, and only then

A landing page answering the `AGENTS.md` objection, measuring signups. Followed by five deliberate
purchase attempts at $8–10/month — the wedge dossier's own bar, and the only demand evidence that counts.

---

## 5. The revenue fork — and why not to resolve it yet

R6 established three structurally different paths: solo unfunded open source (~$68k–$170k/year evidenced
ceiling), proprietary with a free tier (Obsidian shape, ~$25M ARR with seven people), or open source plus
capital and sales (PostHog/Sentry shape, $57M–$100M+ ARR after $100M–$217M raised).

**Recommendation: do not choose yet.** Choosing before the ninety-day tests would be choosing without
information, and the tests are cheap. Meanwhile:

- **Stay open source.** It is the reversible option — Sentry moved to Fair Source in 2023; going the
  other way is far harder. It also preserves Constitution Invariant #1.
- **Do not build a paid tier** until five people have tried to pay.
- **Keep the funding question live but unanswered.** It only becomes real if Year 1 produces team
  purchases and retention.

Constitution §10 already parks *which* commercial tier pending validation. This report extends that
parking to the path itself, on the same reasoning.

---

## 6. Risk assessment

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | **Passive capture wins** | **Existential** | Test 2, immediately. Nearly free |
| 2 | **Nobody does the authoring** | **Existential** | Enforcement helps only if the tool is in the loop; a skipped session is a skipped record. The 921-repo ADR study found ~50% of adopting repos have 1–5 records |
| 3 | **No budget line exists** | High | Position inside agent-tooling budget; never ask for a new line |
| 4 | **Hyperscaler bundling** | High | Named in the competitor dossier. Local-first ownership is the only durable answer |
| 5 | **Solo maintainer concentration** | High | The tool asks organisations to trust their reasoning to a one-person project. Mitigated by open source and plain Markdown — a user's memory survives the project's death |
| 6 | **The ambition/path mismatch** | Medium | §5. Resolve after evidence, deliberately |
| 7 | **Enforcement reads as friction** | Medium | The ECSA 2024 finding — ADRs work when the *operating model* is adopted, not just the artefact |
| 8 | **AI Act timing deflated** | Low | Annex III moved to Dec 2027. Do not build a strategy on it |

---

## 7. Research gaps

Honest list of what this programme could not establish:

1. **Demand — entirely.** Nobody interviewed, no purchase attempted.
2. **Whether deliberate authoring beats passive capture.** Untested, existential.
3. **Whether documentation improves outcomes.** Google's causal study found no link; needs primary
   verification (paywalled).
4. **Whether an auditor would accept a filtered engineering decision log.** An empirical question about
   human behaviour, never asked.
5. **ISO clause text** — `iso.org` returned 403 throughout; all ISO citations are secondary.
6. **Whether "no competitor does X" means unserved need or absent demand.** Structurally undecidable
   from desk research.
7. **The *Accelerate* approval finding** — cited second-hand; load-bearing for two recommendations.
8. **Real cost and sales-cycle data** for any framework or vertical.

---

## 8. What this programme was worth

Seven reports established a defensible product thesis, disqualified four false opportunities and two
verticals on structural grounds, corrected several assumptions that would have wasted months, and found
the one mechanism nobody else has built.

**It did not, and could not, establish that anyone wants this.**

Ten conversations and a landing page would produce more decision-relevant evidence than all of it. That
is not a criticism of the work — it is the correct relationship between desk research and market contact,
and the most useful thing this final report can say is: **the research phase is over. Go and ask
someone.**

---

*End of Report 7, and of the programme.*
