---
title: "Ideal Customer Profile Report"
date: "2026-08-01"
project: "memory-seed"
kind: "report"
next_action: "source-only"
author_context: "Prepared for Jean Nathan Tshibuyi (JNL). Report 6 of a seven-report research programme."
---

# Ideal Customer Profile Report

**Report 6 of 7.** Determines the highest-value initial market, from evidence rather than intuition.

**Headline: the market analysis confirms the wedge you already chose — but the revenue analysis
contradicts the ambition attached to it by two orders of magnitude, and that fork matters more than the
ICP selection.**

---

## Inputs

| Input | Role |
|---|---|
| **`business/wedges/developer-project-memory.md`** | **The active wedge hypothesis, dated today. This report sharpens it; it does not replace it** |
| **`business/market/market-size.md`** | Sizing, and the $15M–$55M obtainable figure this report challenges |
| **`business/market/competitor-landscape.md`** | Ten named agent-memory competitors — a category Report 3 missed |
| [Report 1](standards-and-regulatory-landscape-report.md) | Which frameworks demand what, by vertical |
| [Report 3](memory-seed-strategic-fit-report.md) | No budget line for decision rationale |
| [Report 4](memory-seed-benchmarking-and-economic-value-report.md) | Break-even ≈ 1–5 min/engineer/week; adoption is the constraint |
| New research, 2026-08-01 | Regulated-vertical procurement and tool qualification; OSS commercialisation and devtool GTM |

---

## 1. Confronting the demand question

This programme has deferred demand four times. It cannot be deferred again, so state it precisely:

> **There is no demand evidence for Memory Seed. None. No user has been interviewed, no purchase has
> been attempted, no retention has been observed. Every market claim in this report is inference from
> vendor behaviour, regulatory text, and third-party benchmarks.**

The wedge dossier says the same thing in its own words: *"These observations demonstrate product-problem
alignment, not product-market fit."* That remains the correct status.

**What this report can therefore honestly do:** rank hypotheses by the evidence that *does* exist,
disqualify markets where entry is structurally impossible, name what would falsify each remaining
candidate, and design the cheapest test that would produce real demand evidence. **What it cannot do is
tell you anyone will buy this.** No amount of desk research substitutes for the twenty interviews the
wedge dossier already specifies and nobody has run.

**The single most consequential unknown**, from the competitor dossier's own watch list: *"passive-capture
products may accumulate context faster than deliberate authoring systems."* Memory Seed requires
deliberate authoring. Pieces and Unblocked capture passively. If passive capture wins for this job, the
wedge fails regardless of which vertical is chosen. **That is the first thing to test, not the last.**

---

## 2. Market analysis

Eleven markets, scored on the factors requested. **Adopt** = likelihood of adoption absent a sales team.
Scores are judgments from the evidence below, not measurements.

| Market | Compliance burden | Doc burden | Decision complexity | Eng maturity | Buying power | Sales difficulty | **Adopt** | Verdict |
|---|---|---|---|---|---|---|---|---|
| **Software engineering (horizontal)** | Low | Med | High | High | Low–Med | **Low** | **High** | **Beachhead** |
| **AI startups** | Low | Low | High | High | Low | **Low** | **High** | **Beachhead** |
| **Enterprise software** | Med | Med | High | Med–High | High | High | Med | Expansion |
| **Consulting / agencies** | Low | High | Med | Med | Med | Med | Med | Expansion |
| **Financial services** | High | High | High | Med–High | **Very high** | High | Low–Med | **Later, viable** |
| **Government (via contractors)** | High | High | Med | Med | High | High | Low | Later, indirect |
| **Manufacturing** | Med | High | Med | Low–Med | High | High | Low | Unlikely |
| **Automotive (non-safety)** | Med | High | Med | Med | High | High | Low | Edges only |
| **Automotive (safety-critical)** | Very high | Very high | High | High | Very high | Very high | **Very low** | **Disqualified** |
| **Medical devices** | Very high | Very high | High | Med | High | Very high | **Very low** | **Disqualified** |
| **Aerospace / defence (airborne)** | Very high | Very high | Very high | High | Very high | Very high | **Very low** | **Disqualified** |

### The finding that disqualifies the regulated verticals

**Traceability is not rationale, and the heavily regulated industries mandate the former.**

- **ISO 26262 and Automotive SPICE** require *bidirectional traceability* — SWE.1.BP6 requires linking
  system requirements to software requirements, and architecture to requirements `[secondary]`.
- **DO-178C** requires traceability across four levels: system requirements → high-level → low-level →
  source code → tests `[secondary]`.
- **Neither mandates recording why an alternative was rejected.** That is a documentation-culture
  choice.

So the industries with the heaviest compliance burden demand the artefact Memory Seed **does not
produce** (a traceability matrix linking requirements to code) and do not demand the one it does
(rationale). Incumbents — Polarion, Codebeamer, DOORS, Jama — sell exactly that matrix with
standard-specific templates.

**And tool qualification closes the door.**

- **Medical devices:** 21 CFR 820.70(i) requires validation of any software used in the quality system
  `[primary, eCFR]`. The tool enters the customer's audited QMS scope; a bug corrupting a Design History
  File becomes a finding against *their* quality system. Devices have 10+ year field lives, so vendor
  viability review structurally favours firms that can prove decade-long existence.
- **Airborne software:** **DO-330** defines tool qualification levels TQL-1 to TQL-5, triggered whenever
  a tool's output is relied upon without independent downstream verification `[secondary]`. This is a
  multi-year, capital-intensive process.

**State it plainly: a small, unfunded, open-source project should not target medical devices or airborne
aerospace. Not because the product is weak, but because the compliance artefact of record requires either
absorption into a validated system the customer already owns, or a qualification effort that cannot be
self-funded.**

### The regulated exception worth keeping

**Financial services is different, and the difference is linguistic.** SR 11-7 requires documentation
*"sufficiently detailed so that parties unfamiliar with a model can understand how the model operates,
its limitations, and its key assumptions"* `[secondary, quoting Fed guidance]`. That is *explain your
reasoning*, not *prove your links* — structurally the closest regulatory ask to what Memory Seed
produces. No DO-330 equivalent was found for general SDLC tooling in banking; the burden sits in internal
change-management and SOX controls. Bank third-party risk review is serious but tractable, and fintech
SaaS vendors clear it routinely.

**Keep financial services as the named expansion vertical.** Not first — the sales cycle and security
review are beyond current capacity — but it is the one regulated market where the regulatory language
matches the product.

### The live opening — AI governance, stated carefully

Evidence that a governance wall is forming around AI-written code:

- Defence reporting: *"defense ministries are drafting policies on AI-assisted software development…
  though such policies are difficult to enforce because the code is already being generated"* `[secondary]`.
- Controlled tests had AI models introducing security vulnerabilities in **45% of coding tasks** `[secondary]`.
- July 2025: malicious instructions injected into Amazon Q Developer, affecting **964,000+ installs** `[secondary]`.

**The careful reading:** this wall is being built around *AI writing code without traceable provenance*.
That is adjacent to Memory Seed's value, not identical to it. A decision record does not prevent prompt
injection or catch a vulnerability. **Do not conflate the two in a pitch** — the honest claim is "when an
agent made a consequential choice, you can see what it decided and why," which is real and narrower.

---

## 3. The five ICPs

Ranked by evidence of reachability, not by revenue potential.

### ICP-1 — The multi-agent solo builder *(the adoption wedge)*

| | |
|---|---|
| **Who** | Independent developer or technical founder running two or more coding agents |
| **Size** | 1–3 people |
| **Tooling** | Claude Code, Codex, Cursor, Copilot; Git; `AGENTS.md`/`CLAUDE.md`; often already hand-rolling context files |
| **Pain** | Re-explaining architecture and prior attempts every session; agents re-deriving decisions made weeks ago |
| **Decision maker & budget owner** | The same person. Personal card |
| **Trigger** | Adding a second agent; returning to a project after weeks away |
| **Objection** | *"I already have `AGENTS.md` and it's free."* This is the hardest objection in the set and it is correct until proven otherwise |
| **Budget** | $0–150/year. Comparables cluster at **$8–10/month** for individual devtools `[primary, vendor pricing]` |
| **Find them** | r/ClaudeCode (~4,200 weekly contributors `[secondary]`), r/cursor, r/ChatGPTCoding, Claude Code and Cursor Discords, Hacker News |
| **Titles** | Founder, Indie Developer, Staff Engineer, Solo Consultant |

**Why first:** zero procurement, zero security review, self-serve, and this is the population where the
pain is felt most acutely per person. **Why not sufficient:** individual conversion at OSS rates
(0.5–3%, likely sub-1%) does not produce a business on its own.

### ICP-2 — The small AI-forward engineering team *(the first real buyer)*

| | |
|---|---|
| **Who** | 5–30 engineers, AI-native or aggressively AI-adopting; SaaS or AI product company |
| **Tooling** | GitHub, Linear/Jira, Notion or Confluence, multiple coding agents, no ADR discipline |
| **Pain** | Agent-written code nobody can explain; onboarding a new engineer *or agent* takes weeks; decisions re-litigated |
| **Decision maker** | Engineering lead, VP Eng, or CTO |
| **Budget owner** | Same — at this size the eng lead controls tooling spend |
| **Trigger** | A painful onboarding; an incident traced to a decision nobody remembered; adopting a second agent platform |
| **Objection** | *"Who maintains this?"* and *"Will the team actually write these?"* — both legitimate, both about adoption not value |
| **Budget** | $2k–15k/year plausible at $8–20/seat/month |
| **Find them** | Local-First Conf, KubeCon Platform Engineering Day, AI-engineering Discords, technical blog readership |
| **Titles** | VP Engineering, Head of Platform, Staff/Principal Engineer, AI Enablement Lead |

**This is the wedge dossier's "first team buyer" and the evidence supports it.** Small enough to skip
procurement, large enough to have the pain, engineering-owned budget.

### ICP-3 — The AI-native startup with an enterprise customer

| | |
|---|---|
| **Who** | 10–50 engineers, selling AI features into enterprise or regulated buyers |
| **Pain** | Customer security questionnaires now ask about AI governance; SOC 2 underway; ISO 42001 appearing in RFPs |
| **Decision maker** | CTO or Head of Security |
| **Trigger** | **A customer questionnaire asking how AI decisions are governed.** This is a concrete, dated, external forcing function — the strongest trigger in the set |
| **Objection** | *"Our compliance platform already covers this"* — partly true (Report 3), and the honest answer is that Vanta covers control state, not design rationale |
| **Budget** | $5k–25k/year; already paying $10k–40k for compliance automation |
| **Find them** | Same channels as ICP-2, plus compliance-adjacent communities |

**Why this ICP matters:** it is the only one with an **external deadline**. The others buy on
discretionary pain; this one buys because a customer asked a question they cannot answer.

### ICP-4 — The engineering consultancy or agency

| | |
|---|---|
| **Who** | 10–100 engineers delivering client projects |
| **Pain** | Handover *is* the product; context loss between engagements is a direct cost; clients ask "why did you build it this way?" months later |
| **Decision maker** | Practice lead, delivery director |
| **Trigger** | A handover that went badly; a client dispute about a past decision |
| **Objection** | *"Clients won't pay for documentation time"* |
| **Budget** | $5k–30k/year; bills the time |
| **Find them** | Consultancy networks, LinkedIn (Delivery Director, Principal Consultant) |

**Distinctive strength:** consultancies are the one segment where *decision provenance is
client-facing revenue*, not internal hygiene. Under-explored and worth an interview or two.

### ICP-5 — Financial services engineering team *(expansion, not entry)*

| | |
|---|---|
| **Who** | 50+ engineers in a bank, insurer, or fintech; model risk or AI governance in scope |
| **Pain** | SR 11-7 model documentation; AI usage governance; internal audit asking how decisions were made |
| **Decision maker** | Head of Engineering or Model Risk Management |
| **Budget owner** | Risk or compliance, not engineering — **the buyer moves away from engineering here, which is the warning** |
| **Trigger** | A model-risk audit finding; an internal AI governance policy |
| **Objection** | Vendor security review, data residency, support SLA |
| **Budget** | $25k–150k/year, but 6–12 month cycle |

**Do not pursue until ICP-2 has produced retention evidence.** Listed because SR 11-7 is the one
regulatory text whose language matches the product, and because it should be a deliberate later target
rather than an accident.

---

## 4. Go-to-market

### Positioning

Report 3's statement, unchanged and consistent with the wedge dossier:

> **Memory Seed is the decision record that agents cannot skip.**

**Critically: do not attempt to create a category.** The evidence is explicit — *"for 90% of B2B SaaS
companies, trying to create a category is a death sentence"* `[secondary]`, category creation is
capital-intensive by nature, and **no example of a solo unfunded person successfully creating a software
category surfaced in this research.** The evidenced-favoured alternative is to position inside a budget
line that already exists.

**The existing line to sell into is AI coding-agent tooling** — teams already pay for Copilot, Cursor,
and Claude. "Your agents keep forgetting why" is a problem statement inside a budget that exists, rather
than a new category requiring market education.

### Landing page messaging

- **Headline:** the problem, not the category — *"Your coding agents keep re-deciding things you already decided."*
- **Proof above the fold:** a real decision record with `D:` and `R:` visible, and a supersession chain.
  The artefact *is* the pitch.
- **Against the hardest objection, directly:** a section titled *"I already have AGENTS.md"* — because
  ICP-1's top objection is correct until answered.
- **Not:** compliance, governance, audit, ISO. Report 3 established the compliance buyer is wrong and
  the claims are not yet supportable.

### Channels, ranked by evidence

| Channel | Evidence | Verdict |
|---|---|---|
| **Local-First Conf** (Berlin, **12–14 July 2026**) + monthly LoFi meetups | Small, technical, philosophically aligned `[primary]` | **Highest relevance per hour.** Best-fit community found |
| **r/ClaudeCode and agent Discords** | ~4,200 weekly contributors; community is Reddit/Discord-centric, no dedicated conference exists yet `[secondary]` | **High** — where ICP-1 actually is |
| **Documentation as SEO** | For devtools, docs are the primary SEO asset; devs search problems, not categories `[secondary]` | **High, slow** — 6–12 months |
| **Show HN** | 90% get no traction; successful launches 3,500–43,000 visitors; B2B conversion 1–2% | **One-shot spike.** Expect tens to low hundreds of signups, not a growth engine |
| **Product Hunt** | B2B typically "a few dozen to a few hundred signups" `[secondary]` | Low priority |
| **Conference talks (KubeCon etc.)** | Large but infra/ops-oriented | Poor fit for this tool |
| **Cold outreach** | **No evidence it works for bottom-up devtools.** All available material addresses companies with SDR teams | **Do not pursue** |

**SEO note specific to this problem:** the category has no search volume because it doesn't exist. The
evidenced tactic is to target *symptom* language — "how do I stop Claude Code forgetting context,"
"share context between Cursor and Claude," "ADR tooling that validates" — not category terms.

### Open-source strategy — a correction worth making

The existing commercialisation report cites **Obsidian, Raycast, and GitKraken** as models. **None of
them is open source.** All three are proprietary tools with generous free tiers `[primary, vendor pages]`.

The genuinely open comparables are **PostHog and Sentry** — and both raised $10M+ early and built
enterprise sales teams. Sentry moved off OSI-approved licensing to Fair Source in 2023 specifically to
control commercial cloning.

**The implication is a fork, not a tweak:** the "generous free tier + paid cloud" pattern that reaches
real revenue almost always involves either going *proprietary with a free tier* (Obsidian path) or
*raising capital to build sales* (PostHog path). Neither matches "one person, unfunded, staying fully
open source." That is not an argument against staying open — it is an argument for choosing the ambition
honestly. See §5.

### Pricing

Individual devtools cluster at **$8–10/month**; AI-augmented tools run $16–40 `[primary, checked 2026-08-01]`.
Memory Seed is not an AI-inference product, so the lower band applies.

**Recommendation:** free and open core, unlimited local use, forever — consistent with Constitution
Invariant #1. Paid tier at **$8–10/month individual, $15–20/seat/month team**, gated on convenience and
collaboration, never on access to your own memory. Report 4's break-even at ~2.4 minutes/engineer/week
at £100/seat/year means pricing is not the constraint; adoption is.

Free-tier design evidence favours **usage caps over feature gating**.

### Pilot strategy

Report 4's sequence applies: internal gold set → token efficiency → **external replication on a foreign
corpus** → field pilot. The third step is the one that escapes author bias and is most likely to be
skipped.

### Expansion

ICP-1 (adoption) → ICP-2 (first revenue) → ICP-3 (external forcing function) → ICP-4 (opportunistic) →
ICP-5 (only after retention evidence).

---

## 5. The revenue fork — the most important finding

`market-size.md` records a five-year obtainable range of **$15M–$55M ARR**, explicitly labelled *"low;
planning hypothesis."* The GTM evidence puts a different number on the same question.

| Path | Realistic outcome | Evidence |
|---|---|---|
| **Solo, unfunded, fully open source** | **$5,700–$14,200/month** (~$68k–$170k/year), a few hundred to low thousands of paying users | Disclosed indie OSS cases `[secondary]` |
| **Proprietary with free tier** (Obsidian/Raycast shape) | ~$25M ARR with a 7-person team (Obsidian, third-party estimate) | `[secondary, estimate]` |
| **Open source + venture funding + sales** (PostHog/Sentry shape) | $57.5M ARR at 6 years, after $100M+ raised; $100M+ ARR after $217M raised | `[secondary]` |

**These are two orders of magnitude apart, and the difference is not effort — it is structure.** Every
devtool that reached eight figures did so with capital and a sales motion. The genuinely comparable
cohort — solo, unfunded, still open — tops out in the low five figures monthly.

**This is not an argument that $15M–$55M is wrong. It is an argument that it belongs to a different path
than the one currently being walked**, and the fork should be a deliberate decision rather than a
discovered disappointment. Report 7 should treat "which path" as a first-class question, because it
determines the ICP, the licence, the pricing, and whether raising money is on the table at all.

Note also that OSS conversion runs **0.5–3%, likely sub-1%** for a mass-market individual tool. At 10,000
users that is 30–100 paying customers — which is the arithmetic behind the solo-path figure.

---

## 6. What would falsify this

| Claim | Falsifier |
|---|---|
| Multi-agent developers are the beachhead | 20 interviews find the pain is real but `AGENTS.md` is sufficient |
| Deliberate authoring beats passive capture | Pieces/Unblocked users report better recall with zero authoring effort |
| Engineering leads will pay | Five purchase attempts, five refusals, budget cited |
| Financial services is the expansion vertical | An SR 11-7 owner says model documentation lives in a system that will never accept an external record |
| The AI governance wall is an opening | Teams say the wall is about code scanning and prompt injection, not decision provenance |
| Category positioning inside agent tooling works | Buyers consistently file it under "documentation," a budget nobody defends |

---

## 7. The cheapest demand test

The wedge dossier specifies 20 interviews, 10 repositories, and 5 purchase attempts. **None has been
done.** Sequenced by cost:

1. **Ten conversations in r/ClaudeCode and the Local-First community** — no product change, ~2 weeks.
   Ask what happens when an agent re-derives a decision, and what they do about it today. **Do not
   pitch.** If the pain is not described unprompted, that is the answer.
2. **A landing page with the `AGENTS.md` objection answered**, measuring signups. Tests message, not
   product.
3. **Five deliberate purchase attempts** at $8–10/month with real payment. The wedge dossier's own bar.
   Willingness to pay is the only demand evidence that counts.
4. **Local-First Conf, Berlin, 12–14 July 2026** — the highest-density concentration of philosophically
   aligned potential users found anywhere in this research.

**Steps 1 and 2 cost almost nothing and would produce more decision-relevant evidence than this entire
seven-report programme.** That is not self-deprecation; it is the correct relationship between desk
research and market contact.

---

## 8. Limitations

1. **No demand evidence.** Stated at the top and unchanged. Every ICP is a hypothesis.
2. **The ICPs are constructed from inference**, not from interviews or observed purchases.
3. **Sales-cycle and market-size figures are estimates.** No sourced cycle-length data was found for any
   vertical; the regulated-vertical procurement claims are `[estimate]` or `[unsourced]`.
4. **The "% of engineering time spent on traceability" figure does not exist** in the literature. The
   circulating "40–60% reduction" claim is vendor marketing.
5. **ISO 26262 tool-confidence-level requirements were not verified** against clause 11 directly.
6. **Report 3 missed the agent-memory competitor category entirely** — ten named competitors including a
   $24M-funded player. That category is crowded even though the validated-decision-graph niche is empty,
   and the wedge sits at a narrower intersection than Report 3 implied.
7. **OSS conversion and indie revenue figures are drawn from self-reported indie cases**, which
   over-represent success — failures in this space go quiet rather than public.

---

*End of Report 6. Report 7 — the Strategic Roadmap — must resolve the revenue fork in §5 before it can
sequence anything else.*
