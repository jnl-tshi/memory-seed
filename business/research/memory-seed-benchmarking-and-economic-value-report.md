---
title: "Benchmarking & Economic Value Report"
date: "2026-08-01"
project: "memory-seed"
kind: "report"
next_action: "source-only"
author_context: "Prepared for Jean Nathan Tshibuyi (JNL). Report 4 of a seven-report research programme."
---

# Benchmarking & Economic Value Report

**Report 4 of 7.** Designs an evidence-based benchmark suite and economic model for Memory Seed.

**Headline: the literature does not contain the evidence a decision-memory ROI claim would need, so the
benchmark has to generate it. And at a realistic pilot scale you cannot generate a defensible ROI
multiplier — only a break-even threshold and a structured case study. This report builds those instead.**

---

## Inputs

| Input | Role |
|---|---|
| [Report 2](decision-governance-evidence-spine-report.md) | Verified capture surface — what can be measured at all |
| [Report 3](memory-seed-strategic-fit-report.md) | Positioning; the claims a benchmark must test |
| **`2_Todo/memory-quality-metrics-v0-proposal.md`** | **Live P1. Owns memory-quality measurement. This report does not duplicate it.** |
| **`4_Reference/memory-quality-v0-baseline.md`** | The shipped v0 baseline — real numbers, already measured |
| [`CONSTITUTION.md`](../../docs/CONSTITUTION.md) §8 | Memory quality is a `[candidate]` clause, not established |
| New research, 2026-08-01 | Productivity measurement, knowledge/onboarding measurement, small-N methodology, devtool ROI practice |

### What this report does not establish

- **No ROI figure.** It gives break-even thresholds and calculator inputs; it does not claim a return.
- **No targets for the v0 quality metrics.** Those are gated behind JNL's usefulness review (step 6).
- **No composite score.** Declined twice on the record; not reopened here.
- **No demand evidence.** Still nobody interviewed. Unchanged since Report 3.

---

## 1. Executive summary

**1. The evidence a documentation/decision-memory ROI claim would rest on does not exist.** Google's
ESEC/FSE 2022 causal study examined 39 productivity factors and found code quality, technical debt,
infrastructure, communication, goals, and organisational change causally linked to productivity —
**documentation quality was not among them** `[secondary, needs primary-PDF verification]`. There is no
validated instrument for documentation quality. KM maturity models are unvalidated by their own field's
systematic reviews. **ADR adoption has been measured across 921 repositories and never correlated with
any downstream outcome.** You cannot cite your way to this claim; you have to measure it.

**2. At 3–10 teams you cannot produce a defensible effect size.** Detecting a medium effect (d=0.5) at
80% power needs ~64 units per arm `[secondary, standard convention]`. Developer-to-developer variance
runs 5:1 to 25:1 — DeMarco and Lister measured 5.6:1 across 166 professionals `[secondary]`. Team
composition will swamp the tool effect. This is not pessimism; it is arithmetic.

**3. Self-report is disqualified as a productivity measure.** METR 2025: developers measured 19% slower
with AI while believing they were 20% faster — a ~39-point gap `[primary]`. DORA sees the same divergence
at industry scale. **Any "did this feel faster" question is an adoption signal, not a productivity
signal**, and inflates by a characterised margin.

**4. The AI-productivity literature disagrees with itself in a way that matters here.** METR found −19%
among experienced maintainers in familiar codebases; Cui et al. found **+26.1% across 4,867 developers**
and Microsoft's internal study **+24.0% PRs/engineer/day (CI +14.5% to +33.7%)**, both finding
*less-experienced* developers gained most `[secondary, vendor interest]`. Familiarity and seniority appear
to moderate the **sign**, not just the size, of the effect. Memory Seed's proposition sits precisely in
the population where AI helped least — which is either its strongest argument or its hardest problem.

**5. One peer-reviewed anchor genuinely supports the thesis.** Parnin and Rugaber instrumented ~10,000
sessions from 85 programmers: **only 10% resumed coding within a minute of interruption; only 7% needed
no navigation to rebuild context first** `[primary, ICPC 2009 / SQJ 2011]`. Context reconstruction is the
normal case. This is the single best external evidence for the "optimise for resumption" thesis in the
project's own strategic synthesis, and it is not vendor content.

**6. Therefore: replace ROI projection with break-even analysis.** You cannot credibly claim savings.
You can state, precisely and falsifiably, **what would have to be true** for the tool to pay for itself —
and then have the pilot test whether that threshold is plausible. §7 does this.

---

## 2. The measurement landscape — what is real

Assembled so the benchmark builds on validated ground and avoids the rest.

| Domain | Validated instrument? | Outcome evidence? | Usable here |
|---|---|---|---|
| Coupling/cohesion (CK metrics) | **Yes** — decades of replication | Predicts fault-proneness | Not relevant to this tool |
| Architectural drift | Tooled (ArchRuby, ADvISE) | Not against business outcomes | Marginal |
| ADR adoption | Measured — 921 repos, ~50% have 1–5 records | **None** | Context, not a metric |
| Retrieval quality (IR metrics) | Inherited from IR: precision@k, nDCG, MRR | Inherited | **Yes — directly usable** |
| RAG metrics (RAGAS) | Framework convention, not psychometrically validated | No | Partially |
| Documentation quality | **No** | **Google: null result** | No |
| Documentation freshness | Vendor tooling only | None | Weak |
| KM maturity models | **No — field says so itself** | No | No |
| Onboarding time-to-productivity | Defined (DX Core 4), **no disclosed benchmark norms** | Case studies only | Case narrative only |
| Governance maturity (CMMI/COBIT) | Framework-defined | Weak positive; SEI itself calls the evidence "not rigorous" | No |
| NIST CSF Tiers | **No** | **None found** | No |
| Cognitive load | NASA-TLX (not software-normed); DXI (vendor, unreviewed) | — | No |
| **Context sufficiency for agents** | **Does not exist** | — | **Build it — see §5** |

**Two conclusions.** First, most of what this product would like to claim sits in the unvalidated
column. Second, the one construct that matters most — *did the agent have enough context to do the task
correctly* — **has no established benchmark anywhere**. Building it means creating the first instrument
in that space, which is a real opportunity and a real cost.

### Frameworks worth knowing, and their limits

- **DORA** — now **five** metrics. Throughput (lead time, deployment frequency, failed deployment
  recovery time) and **Instability**, renamed from Stability because these are problem signals (change
  failure rate, plus the new **rework rate**). The report is now *State of AI-assisted Software
  Development*. Its 2025 headline: **AI is an amplifier**, magnifying existing strengths and weaknesses
  `[primary]`.
- **SPACE** — Satisfaction, Performance, Activity, Communication, Efficiency. Its argument is that no
  single metric works because proxies conflate activity with outcome. A live 2026 critique: **SPACE's
  Activity dimension has no mechanism for AI attribution** — it counts commits regardless of author,
  which breaks under agent-written code `[secondary]`.
- **DX Core 4** — speed, effectiveness, quality, impact. Methodologically serious but **a vendor
  product**; DX sells the platform that reports it.
- **McKinsey's 2023 framework** — the cautionary case. Beck and Orosz's rebuttal: four of five metrics
  measure effort, not outcomes, and such frameworks are often commissioned to justify headcount cuts
  `[primary, authors' own newsletter]`.

### Two traps to design around

**Goodhart's law is documented here, not theoretical.** Coverage targets produce assertion-free tests;
ticket-closure quotas produce tickets closed without fixes; story points get gamed by re-slicing.
Hillel Wayne's formulation is the sharpest: *even 100% honest pursuit of a metric, taken far enough, is
harmful to your goals* `[secondary]`.

**A terminology collision to avoid.** DORA's **rework rate** (unplanned deployments ÷ total deployments,
deployment-level) and GitClear's **churn** (lines rewritten within two weeks, code-level) are different
constructs sharing a word. Do not let a dashboard conflate them. Note also that GitClear ran **no
controlled comparison** — its AI-churn finding is correlational over a period when AI adoption rose, and
secondary coverage treating it as causal is overreach.

---

## 3. Relationship to the live P1 proposal — what this report must not duplicate

`memory-seed quality report` **already ships** with five metrics, a JSON schema, and a recorded baseline.
Its non-goals are explicit and this report honours all of them: no composite score, no telemetry, no
cross-project comparison, no targets before baseline, no metric feeding ranking or agent behaviour.

**Measured at revision `bc9b174`:**

| v0 metric | Status | Value |
|---|---|---|
| `unlinked_entry_rate` | measured | 95/431 (22.0%) — 0–30d: 15 · 31–90d: 80 · 90d+: 0 |
| `draft_reason_coverage` | measured | 403/403 (100%), 28 excluded |
| `generated_claim_citation_coverage` | **unavailable** | Blocked on BG1 (provenance taxonomy) |
| `provenance_coverage` | **unavailable** | Blocked on BG1 |
| `ranking_ab_regression_rate` | **not_applicable** | No `ranking-ab` run supplied |

**Three things the v0 work already got right, which this report inherits rather than re-invents.**

1. **The `unavailable` / `not_applicable` distinction.** *"'We have no way to look' and 'we looked and
   found nothing' are different claims, and collapsing them is how a metric starts lying."* Every metric
   below inherits this rule.
2. **The 100% is correctly discounted by its own author.** DRAFT reason coverage is 100% *because the
   write-time lint refuses malformed records*. It confirms the gate holds; it is **not** evidence the
   reasons are good. A vendor would have led with that number.
3. **The inherited candidate is the right benchmark.** *"Nothing measures whether a grounded decision was
   reached."* The proposed instrument — a gold set of real questions scored on completion time and
   accuracy against a bounded context, with the Evidence Pack supplying a deterministic comparison arm —
   is the core of §5 below. **This report does not propose a new instrument; it specifies that one.**

**Standing constraint:** targets, ESR surfacing, and Constitution §8 graduation are gated on JNL's
usefulness review. Nothing here proposes a target.

---

## 4. Triage of the 23 requested metrics

The brief listed 23 candidate metrics. Adopting all of them would produce a dashboard, not a benchmark.
Each is placed in one of four buckets.

### Bucket A — already owned by the v0 quality report (do not rebuild)

| Requested metric | Where it already lives |
|---|---|
| Decision provenance coverage | `provenance_coverage` — currently `unavailable`, blocked on BG1 |
| Knowledge graph coverage | `unlinked_entry_rate` — measured at 22.0% |

**Action: none.** Building parallel versions would fork the metric definitions the v0 proposal
deliberately froze.

> **Amendment, 2026-08-03 — add one metric from the field.** See the
> [field evidence log](field-evidence-log.md). A practitioner running a decision log describes the moment
> it started working: *"re-derivations started dying at the proposal stage — the agent finds the June
> record and says 'this was tried, here's why it failed' instead of proposing it. That exact sentence, from
> the agent, is how you know it's working."*
>
> **Adopt this as the primary field metric: proposal-stage re-derivation catches.** Count sessions where an
> agent declines its own proposal by citing a prior record. It is observable in normal work, needs no gold
> set, no grader, and no survey — which makes it cheaper and more direct than anything designed in §5, and
> it measures the outcome rather than a proxy for it. It does not replace the gold set (which controls
> conditions); it is what to watch in production.

> **Amendment, 2026-08-04 — two designed metrics now have values, and one is retired (E5/E6).**
>
> - **Capture rate** — measured. 0.05 with the write path alone, 0.77 with one `AGENTS.md` line,
>   0.83 / 0.91 at higher scaffolding. Report it as a *ladder*, never as a single headline number:
>   the figure is meaningless without stating the scaffolding level it was measured at.
> - **Faithfulness** — measured, and it is the strongest result available: 0 of 121 recorded reasons
>   judged a post-hoc reconstruction. Promote this above capture rate in any benchmark pack. It is
>   the only metric here that speaks to the product's actual promise rather than its throughput.
> - **Noise rate** — ~0 across 120 sessions. Worth quoting defensively (it answers "won't the store
>   fill with junk?") but it is not a selling metric.
> - **Threshold pass/fail verdicts — retired.** A pre-registered 0.80 reliability threshold flipped
>   between two identical 60-session matrices because every arm's confidence interval straddled it.
>   Any benchmark of this kind must report the interval, and must not be published as a binary at
>   feasible sample sizes. This is a lesson about the whole §5 benchmark design, not about capture.
>
> **Second amendment — token cost is a live counter-pressure, not a theoretical one.** Another responder
> deletes their context file once a problem is solved: *"removing it clears up context so lower token
> cost."* Someone is actively trading durable memory away to save tokens. That confirms §5.2's token
> efficiency as the right lead metric and adds a risk the economic model should carry: **accumulated
> decision history has an ongoing per-session cost**, so retrieval that loads *less* while answering the
> same question is itself the value, not merely an efficiency.

### Bucket B — specified by the inherited decision-quality candidate

| Requested metric | How the gold-set instrument covers it |
|---|---|
| Decision retrieval time | Task completion time, per question |
| Knowledge retrieval accuracy | Answer correctness against known ground truth |
| Mean time to understand | Same instrument, comprehension-class questions |
| Mean time to recover knowledge | Same instrument, resumption-class questions |
| Agent context quality | Same instrument, agent arm instead of human arm |
| Time to understand code | Subsumed by mean-time-to-understand; not separate |

**Action: build one instrument (§5), not six metrics.** These are six questions answered by the same
experimental apparatus. Treating them as separate metrics multiplies instrumentation cost without adding
information.

### Bucket C — genuinely new, cheap, deterministic, worth building

| Metric | Why it survives |
|---|---|
| **Prompt token reduction** | Directly countable, no judgment, no self-report. Deterministic given a fixed task set |
| **Context window efficiency** | Tokens consumed to reach a correct answer. Countable. Note: input tokens are 99.75–99.87% of usage in measured systems `[secondary]`, so this is where cost lives |
| **Repeated decision rate** | Corpus-measurable: decisions that re-decide something already decided. Needs a judgment rule, but the corpus and lifecycle edges make it tractable |
| **Change investigation time** | Measurable *if* paired with real changes; otherwise a lab task in the gold set |

**Action: build token metrics first.** They are the cheapest honest measurements available — no humans,
no survey, no confounders, and they map directly to a cost the buyer already pays.

### Bucket D — reject, defer, or demote

| Metric | Disposition | Reason |
|---|---|---|
| **Engineering onboarding time** | **Case narrative only — never a benchmark number** | No validated benchmark exists. Every circulating figure is vendor SEO with no methodology. "DORA elite teams: 1–2 days" is **fabricated** — time-to-first-commit is not a DORA metric |
| **Documentation freshness** | **Defer** | v0 explicitly declined a "stale memory" metric. No validated method exists. Reopening it without a definition repeats what v0 refused |
| **Duplicate work** | **Reject** | No operational definition, no attribution path. Unmeasurable without a controlled study nobody will run |
| **Context switching** | **Reject for v1** | Parnin & Rugaber give a method, but it requires IDE-level instrumentation far outside this tool's surface |
| **Architecture review effort** | **Reject** | No baseline, tiny N, high task heterogeneity |
| **AI task success rate** | **Demote to a component** | Entirely determined by task selection, therefore gameable. Usable only *inside* the gold set with a frozen task list |
| **Audit preparation time** | **Defer until the promotion layer exists** | Per Report 2, an evidence pack over a corpus with no governing-decision marking is not audit evidence. Measuring it now measures nothing |
| **Incident investigation time** | **Defer** | Requires real incidents and enough of them for signal. Not available at pilot scale |
| **Decision confidence** | **Reject as a metric; keep as a field** | Self-report. Report 2 found no confidence field on decisions; adding one may be useful for *authoring*, but its self-reported value is not a benchmark |
| **Human trust** | **Adoption signal only** | Self-report, no software-specific validated instrument. Never report as productivity |
| **AI trust** | **Adoption signal only** | Same |

**Eleven of twenty-three rejected or deferred.** That is the report doing its job. A benchmark suite that
measured all 23 would be measuring mostly noise, self-report, and constructs with no validated
instrument — and the ones with the most intuitive appeal (onboarding time, duplicate work, trust) are
precisely the least defensible.

---

## 5. The benchmark suite

### 5.1 Core instrument — the decision-recovery gold set

This specifies the inherited candidate from the P1 proposal.

**Construction.** 30–50 questions drawn from this repository's real history, of four classes:

| Class | Example shape | Ground truth source |
|---|---|---|
| **Rationale recovery** | "Why was X chosen over Y?" | The `R:` and `A:` of a known entry |
| **Supersession** | "What replaced decision X, and why?" | A known `replaces`/`evolves` chain |
| **Scope** | "What did decision X affect?" | The `F:` files of a known entry |
| **Negative control** | A question the corpus genuinely cannot answer | Verified absent |

**Negative controls are mandatory.** Without them the instrument cannot distinguish retrieval from
confabulation — and a system that confidently answers unanswerable questions is worse than one that
retrieves nothing. Target: correct abstention on negative controls, scored separately.

**Arms.** Each question is answered under bounded context by:

| Arm | Context supplied |
|---|---|
| A — baseline | Repository only: code, commits, README |
| B — corpus | Repository + Memory Seed corpus via `memory_search` |
| C — evidence pack | Repository + a deterministic Evidence Pack for the relevant window |

Arm C matters: the Evidence Pack is **already built, deterministic, and fingerprinted**, so it costs
nothing new and provides a structural-expansion comparison the P1 proposal already anticipated.

**Scored on:** answer correctness against ground truth (binary, blind-graded); time or tokens to answer;
citation accuracy — did it cite the entry that actually contains the answer; and abstention correctness
on negative controls.

**Grading must be blind to arm.** The grader should not know which arm produced an answer. This is the
single cheapest defence against the researcher-expectancy bias documented in the software-engineering
methodology literature, and it costs nothing but shuffling.

### 5.2 Token efficiency suite — the cheapest honest measurement

Run over the same frozen task set, no humans involved:

| Metric | Definition |
|---|---|
| Tokens to correct answer | Total input+output tokens consumed until a correct answer is produced |
| Input token share | Input ÷ total — expect 99%+; confirms where cost sits |
| Context efficiency | Correct answers ÷ million tokens consumed |
| Retrieval precision@k | Fraction of retrieved chunks that contain answer-bearing content |

These are deterministic for a fixed corpus revision, model, and task set — reproducible in the same way
the v0 quality report is, and reportable without a single survey question.

### 5.3 What gets reported

Every result carries: corpus revision, model and version, task-set version, arm, n, and **a confidence
interval, not a point estimate**. Following the P1 output contract, every metric declares population,
numerator, denominator, exclusions, and `not_applicable` behaviour.

---

## 6. Statistical methodology

### 6.1 What the design can and cannot deliver

**Cannot, at 3–10 teams:** a generalisable effect size; a defensible ROI multiplier; separation of
novelty from durable value inside a short window.

**Can:** directional mechanism-level findings — is it used, where does it help, what breaks; a
wide-interval estimate for internal planning, explicitly labelled; confirmation that the instrumentation
works at all; and a prioritised threats-to-validity list telling you what a powered study would need.

### 6.2 Design

**For the gold set (lab):** within-subject, each participant answering both arms on different questions,
with **randomised order** to control carryover. Within-subject is essential — it removes the 5:1–25:1
between-developer variance that would otherwise dominate.

**For the field pilot:** **stepped-wedge** — every team eventually receives the tool in randomised
staggered order, so early adopters serve as temporary controls and nobody is permanently excluded. Pair
with **per-team interrupted time series**: many repeated measurements per team, not one before/after
snapshot.

### 6.3 Reporting rules

- **Effect sizes and confidence intervals, never bare p-values.** Report the interval width as
  information: a 95% CI of [−10%, +60%] from six teams is an honest and useful output. "35% faster" is
  not, unless the interval is published with it. Even GitHub's n=95 Copilot RCT reported [21%, 89%].
- **Never report a self-report number as productivity.** Satisfaction data is an adoption signal, labelled
  as such.
- **Report the null.** If the gold set shows no difference between arms, that result gets published in
  the same place with the same prominence. A benchmark that can only produce good news is marketing.

### 6.4 Threats to validity, named in advance

| Threat | Mitigation |
|---|---|
| Developer variance (5:1–25:1) | Within-subject design |
| Selection bias — enthusiasts opt in | Document selection criteria; note METR's finding that 30–50% of developers refused randomisation away from AI |
| Learning effects | Randomised order; discount the ramp phase |
| Task heterogeneity | Frozen task set; report per-class results |
| Novelty effect | Discount weeks 1–4 entirely; stepped-wedge gives a novelty benchmark |
| Hawthorne effect | Measure a baseline period before anyone knows which arm they are in |
| **Researcher/vendor bias** | **Blind grading; pre-register the task set and analysis before running; publish the null** |

The last is the most important and the most uncomfortable: **this is the tool's author measuring the
tool.** The methodology literature documents expectancy effects as a recognised threat to construct
validity. Pre-registration and blind grading are the available defences; a genuinely independent
replication is the only real one.

---

## 7. Economic model — break-even, not ROI

### 7.1 Why not an ROI figure

Vendor ROI calculators are arithmetic wrapped around an unvalidated input. DX's produces a **39x ROI**
headline; every load-bearing number traces to a self-reported "2.4 hours saved per week" — the exact
class of input METR showed to be inflated by ~39 points. Forrester TEI studies are vendor-commissioned,
built on vendor-supplied reference customers, and compress a handful of interviews into a "composite
organization" with a point estimate and no confidence interval.

**Producing a number of that kind here would be indefensible and, given §2, unsupported by any
literature.**

### 7.2 What replaces it

State the **break-even threshold**: what would have to be true for the tool to pay for itself. This is
falsifiable, requires no unvalidated input, and converts the pilot from "prove the ROI" to "test whether
the threshold is plausible."

**Cost basis.** Use **fully-loaded** cost, not salary: 1.25×–1.4× base is the common convention, higher
once equipment and software are included `[secondary, convergent industry-finance practice, no single
primary source]`. Vendor calculators using raw salary understate the value of time saved by 30–40% —
a rare place their math is conservative.

**The break-even identity:**

```
minutes per engineer per week to break even
    = (annual price per seat) ÷ (fully-loaded hourly cost) × 60 ÷ 46 working weeks
```

**Worked illustration** — arithmetic only, not a claim:

| Input | Value |
|---|---|
| Base salary | £70,000 |
| Fully-loaded multiplier | 1.35× |
| Fully-loaded annual cost | £94,500 |
| Working hours (46 weeks × 37.5h) | 1,725 |
| Fully-loaded hourly cost | **£54.78** |

| Annual price/seat | Break-even minutes/engineer/week |
|---|---|
| £50 | **1.2** |
| £100 | **2.4** |
| £200 | **4.8** |
| £500 | **11.9** |

**Read this correctly.** It says: *at £100 per seat per year, the tool pays for itself if it saves each
engineer about 2.4 minutes a week.* It does **not** say it saves that. Whether 2.4 minutes is plausible
is exactly what the pilot tests — and it is a far more answerable question than "what is the ROI."

The threshold is low enough that the interesting risk is not economic. **At these prices the binding
constraint is adoption and trust, not payback** — which is consistent with Report 3's finding that the
budget line does not exist. That reframing is the most useful output of this section: the pricing
question is downstream of a demand question nobody has answered.

### 7.3 ROI calculator inputs — every assumption exposed

If a calculator is built, these are its inputs, each tagged by evidence quality:

| Input | Source | Quality |
|---|---|---|
| Number of engineers | Customer | Known |
| Base salary | Customer | Known |
| Fully-loaded multiplier | Convention 1.25–1.4× | `[secondary]` |
| Working weeks/year | Customer | Known |
| Price per seat | Vendor | Known |
| **Minutes saved per engineer per week** | **Pilot measurement only** | **`[unmeasured]` — the whole question** |
| Adoption rate | Pilot measurement | `[unmeasured]` |
| Decay factor after novelty | Pilot measurement | `[unmeasured]` |
| Conversion of saved time to output | **Not 1:1** — saved time is partly absorbed | `[unsourced]` |

**Design rule: any input tagged `[unmeasured]` must be user-supplied and its provenance shown in the
output.** A calculator that pre-fills the savings figure is a marketing artefact. One that forces the
user to supply it, and shows a range, is a business-case tool.

### 7.4 Where savings would plausibly arise, ranked by evidence

| Claim | Evidence status |
|---|---|
| **Reduced context reconstruction after interruption** | **Strongest.** Parnin & Rugaber: only 10% resume in under a minute, only 7% need no navigation `[primary]` |
| Reduced token spend for agent tasks | Directly measurable by §5.2; no external evidence needed |
| Fewer re-derived decisions | Plausible, measurable via repeated-decision rate; no external evidence |
| Faster onboarding | **No validated benchmark exists.** Case narrative only |
| Reduced audit effort | **Not yet claimable** — requires the promotion layer (Report 2) |
| Reduced compliance effort | **Not claimable.** Report 3: no budget line, and control state is not produced |

---

## 8. Pilot programme

**Do not run a pilot first.** Sequence deliberately:

**Phase 0 — internal gold set (weeks 1–4).** Build the 30–50 question set against this repository. Run
all three arms. Zero external dependency, no recruitment, no confounders. **If arm B does not beat arm A
here, on the corpus the tool's own author maintains, stop.** That is the cheapest possible disconfirmation
and it should be run before anything else.

**Phase 1 — token efficiency (weeks 3–6, parallel).** Deterministic, no humans. Produces the first
publishable numbers.

**Phase 2 — external replication (weeks 6–12).** Two or three teams build a gold set on **their own**
corpus. This is the step that escapes author bias, and it is the highest-value and least comfortable part
of the plan.

**Phase 3 — field pilot (12+ weeks).** Stepped-wedge, 3–10 teams, with a genuine baseline period.
Discount weeks 1–4 as novelty. Expect a case study with quantified uncertainty, and say so in advance.

**Pre-registration.** Before Phase 0, write down the task set, the arms, the scoring rule, and the
analysis. Publish it. If the result is null, publish that too, in the same place.

### Suggested experiments, ranked by value per unit cost

| # | Experiment | Cost | What it settles |
|---|---|---|---|
| 1 | Gold set, arms A vs B, blind-graded | Low | Whether the corpus helps at all |
| 2 | Token efficiency over frozen tasks | Very low | Whether it reduces the cost buyers already pay |
| 3 | Negative-control abstention rate | Very low | Whether it induces confabulation — a **risk** metric, and the one most likely to produce bad news |
| 4 | Arm C vs arm B (Evidence Pack vs raw search) | Low | Whether the pack adds value over search |
| 5 | External replication on a foreign corpus | Medium | Whether anything generalises beyond this repo |
| 6 | Stepped-wedge field pilot | High | Directional field behaviour only |

**Experiment 3 deserves emphasis.** It is the one designed to find harm rather than benefit, and a
benchmark suite with no such experiment is not a benchmark.

---

## 9. Limitations

1. **The Google null result on documentation needs primary verification.** It is load-bearing for §1 and
   was reached through secondary summaries; the paper itself was paywalled.
2. **The METR result is more qualified than it first appears.** METR themselves stated in February 2026
   that it has limited applicability and that developers are likely more sped up now. It remains valid
   for its stated population and period, and is not a general claim.
3. **The positive AI-productivity studies are vendor-authored** — Microsoft measuring Microsoft. Reported
   with the interest noted, not treated as independent.
4. **Fully-loaded multipliers are convention, not research.** No single primary source.
5. **No demand evidence.** Break-even thresholds say what would have to be true, not whether anyone will
   pay.
6. **This report cannot escape its own critique.** It proposes that the tool's author measure the tool.
   Pre-registration, blind grading, negative controls, and publishing nulls are mitigations, not a cure.
   External replication (Phase 2) is the only real answer, and it is the step most likely to be skipped.

---

*End of Report 4. Report 5 — ADR Standards — must align Memory Seed with existing decision-record
conventions, framed against the existing sidecar and graph-edge contracts rather than inventing a
parallel scheme.*
