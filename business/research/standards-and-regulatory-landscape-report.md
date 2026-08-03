---
title: "Standards & Regulatory Landscape Report"
date: "2026-08-01"
project: "memory-seed"
kind: "report"
next_action: "source-only"
author_context: "Prepared for Jean Nathan Tshibuyi (JNL). Report 1 of a seven-report research programme."
---

# Standards & Regulatory Landscape Report

**Retrieved and verified 2026-08-01.** Report 1 of 7. Covers 21 standards, regulations, and governance
frameworks: what problem each exists to solve, who it is for, what evidence it demands, and where a
decision-memory substrate does and does not fit.

> **This report is descriptive, not legal advice.** It states what frameworks require, with citations.
> It makes no determination about whether Memory Seed — or any organisation — complies with anything.

---

## How to read this

### Evidence tags

Every non-obvious claim carries a provenance tag. This follows Constitution Invariant #4 (v1.6):
provenance is **declared on the record, never inferred from where it is stored**.

| Tag | Meaning |
|---|---|
| `[primary]` | From the governing body's own document or page, with URL. |
| `[secondary]` | From a named third party, with the party named and its commercial interest noted where it has one. |
| `[estimate]` | A range whose basis is stated in the same sentence. |
| `[unsourced]` | Could not be sourced. Stated as unknown rather than guessed. |

**Citation strength is deliberately uneven, and the unevenness is itself a finding.** Free frameworks
(NIST CSF, NIST AI RMF, the EU AI Act, GDPR, the eCFR, NIST SP 800-53) are quoted from their actual
text. ISO standards are paywalled and `iso.org` returned HTTP 403 to every automated fetch attempt
across three independent research passes, so **all ISO clause-level content in this report is
`[secondary]`** — cross-checked paraphrase from multiple independent compliance sources, never verified
against ISO's own text. `committee.iso.org` *is* reachable, which is why ISO revision statuses below are
`[primary]` while ISO clause numbers are not.

### The eight-question evidence spine

Before researching any framework, one instrument was fixed and applied to all 21. Each framework's
evidence and documentation requirements were mapped onto these eight questions:

| ID | Question |
|---|---|
| **E1** | What decision was made? |
| **E2** | Who made it? |
| **E3** | When was it made? |
| **E4** | Why was it made — the rationale? |
| **E5** | What evidence supported it? |
| **E6** | What changed later — revision or supersession? |
| **E7** | Who approved or authorised it? |
| **E8** | What systems, assets, or processes were affected? |

Each cell is marked **REQUIRED** (with clause citation), **IMPLIED**, **NOT REQUIRED**, or **UNKNOWN**.
Report 2 rolls this up; it is captured here so that roll-up reads a column that already exists rather
than re-reading twenty-one frameworks.

### What this report does not establish

- **It does not determine compliance obligations** for Memory Seed or anyone else. Applicability is
  fact-specific and jurisdictional.
- **It does not price anything reliably.** See §4 — cost is the weakest dimension in the entire report
  and is honestly marked as such.
- **It does not verify ISO clause text.** See above.
- **It does not assess Memory Seed's competitive position or market.** That is Reports 3 and 6.
- **It does not recommend a product direction.** That is Report 7. Dimensions 18–19 below are first-pass
  observations to be tested downstream, not conclusions.

---

## 1. Executive summary

**Finding 1 — Governance frameworks converge on the same eight evidence questions, but split sharply
into two drafting styles that determine whether those questions are actually enforceable.**

- **Record-mandating frameworks** prescribe the artefact: what must be written, who signs it, how long
  it is kept. The EU AI Act (Annex IV), ISO/IEC 42001 (clause 7.5), ISO/IEC 27001 (Statement of
  Applicability), NIST SP 800-53 / FedRAMP, CMMI's DAR practice area, HIPAA §164.306(d)(3), and ITIL
  change records all sit here. Their spine cells come back REQUIRED with quotable text.
- **Outcome-stating frameworks** describe the desired end state and leave the record entirely to the
  implementer. NIST CSF 2.0, NIST AI RMF, SOC 2's Trust Services Criteria, ISO 31000, and the OECD AI
  Principles sit here. Their spine cells come back mostly IMPLIED.

The cleanest illustration is ISO/IEC 27001 versus NIST CSF 2.0 — same domain, same decade, both
authoritative. ISO 27001 lands REQUIRED on six of eight spine questions; CSF 2.0 lands REQUIRED on
exactly one (ID.AM-01, asset inventory). The difference is drafting philosophy, not rigour.

**Finding 2 — The EU AI Act is the most evidence-dense framework in scope, and it is close to a
statutory ADR mandate.** All eight spine questions are REQUIRED with direct citation. Annex IV §2(b)
requires documentation of *"the key design choices including the rationale and assumptions made"*;
§2(g) requires test logs *"dated and signed by the responsible persons"*; §6 requires the record of
*"relevant changes made by the provider to the system through its lifecycle"*; Article 18 requires
10-year retention. Rationale, attribution, timestamps, supersession, retention — mandated by law.
`[primary]`

**Finding 3 — But the AI Act's high-risk deadline just moved sixteen months, five days ago.**
Regulation (EU) 2026/1744, the "Digital Omnibus on AI," was adopted 8 July 2026 and entered into force
27 July 2026. Annex III (stand-alone) high-risk obligations move from 2 August 2026 to **2 December
2027**; Annex I (product-embedded) from 2 August 2027 to **2 August 2028**. `[primary, EUR-Lex]` Any
strategy premised on near-term AI Act urgency needs rethinking. Article 50 transparency obligations and
Commission GPAI enforcement powers did *not* move and apply from 2 August 2026 — tomorrow.

**Finding 4 — ISO/IEC 42001 certification does not buy EU AI Act conformity, and this is widely
misunderstood.** CEN-CENELEC's JTC 21 assessed 42001 and found its goals and definitions misaligned with
Article 17's quality-management requirement, so it wrote a bespoke European standard, **prEN 18286**,
rather than adopting 42001. Only once prEN 18286 is cited in the Official Journal does Article 40's
presumption of conformity attach. As of today **no AI Act harmonised standard has been cited in the
OJ**, so the presumption-of-conformity route does not yet exist for anyone. `[secondary — CSA research
note, Schellman; both sell AI-governance services]`

**Finding 5 — The single most explicit decision-rationale requirement in any framework studied is in
HIPAA, and it is thirty years old.** 45 CFR §164.306(d)(3)(ii)(B) requires that where an *addressable*
implementation specification is not implemented, the entity must **document why it would not be
reasonable and appropriate**, and implement an equivalent alternative measure where appropriate.
That is a decision, its rationale, and its alternative — required in regulation, retained six years
under §164.316(b)(2)(i). `[primary]`

**Finding 6 — Cost is not reliably knowable from public sources, and the market is saturated with
figures that are lead generation.** Every compliance-automation vendor publishes a "SOC 2 costs $X"
post. Across 21 frameworks, not one had a neutral, methodologically disclosed cost benchmark from a
governing body, accreditation body, or independent analyst. Dimension 9 is `[estimate]` or `[unsourced]`
throughout, and dimension 10 is only trustworthy where penalties are *in the statutory text* — the AI
Act (Art. 99), GDPR (Art. 83), HIPAA's inflation-adjusted tiers, and CCPA's adjusted per-violation
amounts.

**Finding 7 — Six of the twenty-one frameworks changed status in ways that post-date a May 2026
knowledge cutoff.** Anyone reasoning from memory here is reasoning from a stale model. See §7.

**Finding 8 — Where a decision-memory substrate plausibly fits is narrower than the breadth of this
landscape suggests.** The frameworks that most need decision rationale captured are also the ones with
the most entrenched incumbent tooling (GRC platforms) and the most auditor-mediated evidence flows.
The plausible wedge is the *engineering-side* record — design-choice rationale, change justification,
supersession history — which is precisely the evidence GRC platforms are worst at and which the AI Act,
ISO 42001, CMMI DAR, and HIPAA's addressable-spec rule all demand. This is a hypothesis for Report 3
to test, not a conclusion.

---

## 2. Comparison matrix

**Type**: MS = management system (certifiable, Annex SL); Reg = binding regulation; Att = attestation;
Fwk = voluntary framework; Conv = convention; Spec = technical specification; Model = maturity model.

| # | Framework | Type | Certifiable | Governing body | Status as of 2026-08-01 | Enforcement teeth |
|---|---|---|---|---|---|---|
| 1 | ISO 9001 | MS | Yes | ISO/TC 176 | 2015 ed.; **ISO 9001:2026 due Sept 2026** | None statutory; contract/tender gating |
| 2 | ISO 56001 / 56002 | MS / guide | 56001 yes; 56002 no | ISO/TC 279 | 56001:2024 (Sept 2024); 56002:2019 | None |
| 3 | ISO 31000 | Fwk | **No** | ISO/TC 262 | 2018 ed.; revision at framework-spec stage | None |
| 4 | ISO/IEC 27001 | MS | Yes | ISO/IEC JTC 1/SC 27 | 2022 ed. + Amd 1:2024; **2013 transition closed 31 Oct 2025** | None statutory; procurement gating |
| 5 | ISO/IEC 27002 | Guide | **No** | ISO/IEC JTC 1/SC 27 | 2022 ed., 93 controls / 4 themes | None (guidance to 27001) |
| 6 | NIST CSF 2.0 | Fwk | **No** | NIST | CSWP.29, 2024-02-26; **6 functions, GOVERN present** | None; referenced by contract/insurance |
| 7 | ISO/IEC 42001 | MS | Yes | ISO/IEC JTC 1/SC 42 | 2023 ed.; 42006:2025 governs certifiers | None; market access only |
| 8 | NIST AI RMF | Fwk | **No** | NIST | AI 100-1 (Jan 2023) + 600-1 GenAI profile; **under revision** | None |
| 9 | EU AI Act | Reg | Conformity assessment | EC AI Office / national authorities | Reg. 2024/1689 **as amended by Reg. 2026/1744** | €35m/7% top tier |
| 10 | OECD AI Principles | Fwk | **No** | OECD | OECD/LEGAL/0449, rev. May 2024, 47 adherents | None (soft law) |
| 11 | SOC 2 | Att | Attestation, not certification | AICPA & CIMA (ASEC) | 2017 TSC w/ 2022 revised points of focus | None; lost deals |
| 12 | FedRAMP | Auth | Authorisation | GSA PMO / **FedRAMP Board** | Rev5 + **20x Phase 3**; JAB dissolved | Market gate (no federal sales) |
| 13 | ADR conventions | Conv | **No** | **None** | MADR 4.0.0 (2024-09-17); Nygard 2011 | None |
| 14 | OpenTelemetry | Spec | **No** | CNCF | Spec 1.59.0; **CNCF Graduated 2026-05-11** | None |
| 15 | GDPR | Reg | No | EDPB / national DPAs | Reg. 2016/679; Digital Omnibus **proposed only** | €20m/4% top tier |
| 16 | UK DPA 2018 / UK GDPR | Reg | No | ICO → Information Commission | **DUAA 2025 Pt.5 in force 5 Feb 2026**; adequacy to 2031 | £17.5m/4% top tier |
| 17 | HIPAA | Reg | No | HHS OCR | 2013 Omnibus in force; **Security Rule NPRM still proposed** | $73,011–$2,190,294 (2026 adj.) |
| 18 | CCPA / CPRA | Reg | No | CPPA + California AG | **ADMT/risk/audit regs final, operative 2026-01-01** | $2,663 / $7,988 per violation |
| 19 | ITIL | Fwk | **People, not orgs** | PeopleCert (owns AXELOS) | ITIL 4; **ITIL v5 launched 12 Feb 2026** | None |
| 20 | COBIT | Fwk | People, not orgs | ISACA | COBIT 2019 | None |
| 21 | CMMI | Model | **Yes — org appraisal** | ISACA / CMMI Institute | **V3.0**; V2.2 retired Jun 2024 | Contract ineligibility (defence) |

---

## 3. Evidence spine crosswalk — the core table

**R** = REQUIRED with citation · **I** = IMPLIED · **—** = NOT REQUIRED · **?** = UNKNOWN · **n/a** = framework has no decision-record surface

| Framework | E1 what | E2 who | E3 when | E4 why | E5 evidence | E6 changed | E7 approved | E8 affected | R-count |
|---|---|---|---|---|---|---|---|---|---|
| **EU AI Act** | R | R | R | R | R | R | R | R | **8** |
| **ISO/IEC 42001** | R | R | I | R | R | R | R | R | **7** |
| **ISO/IEC 27001** | R | R | I | R | I | R | R | R | **6** |
| **FedRAMP / 800-53** | R | R | R | R | R | R | R | R | **8** |
| **CMMI (DAR)** | R | R | I | R | R | I | R | I | **5** |
| **HIPAA** | R | I | R | R | R | R | I | R | **6** |
| **GDPR** | R | R | R | R | R | I | R | R | **7** |
| **UK GDPR (post-DUAA)** | R | R | R | R | R | I | R | R | **7** |
| **ITIL (change enablement)** | R | R | I | R | I | R | R | R | **6** |
| **ISO 9001** | I | I | R | I | R | R | R | I | **4** |
| **CCPA / CPRA** | R | I | I | R | R | I | I | R | **4** |
| **ISO 56001** | R | I | I | I | R | I | I | ? | **2** |
| **ISO/IEC 27002** | I | I | I | I | I | R | R | R | **3** |
| **SOC 2** | R | I | I | I | I | I | R | I | **2** |
| **NIST AI RMF** | R | I | ? | R | R | R | I | R | **5** |
| **MADR 4.0.0** | R | R | R | R | I | R | I | I | **5** |
| **ISO/IEC/IEEE 42010** | R | I | — | R | I | I | I | R | **3** |
| **Nygard ADR** | R | — | — | R | I | I | — | I | **2** |
| **NIST CSF 2.0** | I | I | — | I | — | I | I | R | **1** |
| **ISO 31000** | I | I | ? | I | I | I | I | — | **0** |
| **OECD AI Principles** | I | I | — | I | — | — | — | I | **0** |
| **OpenTelemetry** | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

### What the crosswalk shows

1. **E4 (why) is REQUIRED in 10 of 21 frameworks** — more often than E2 (who) or E7 (approved by).
   Rationale is not a nice-to-have in governance; it is the single most consistently mandated field
   after the decision itself. This is the report's most commercially interesting result.
2. **E3 (when) and E7 (approved by) are the weakest columns overall.** Many frameworks assume dating
   and approval happen without requiring them as record fields.
3. **The two frameworks scoring 8/8 are both binding law with third-party conformity assessment.**
   Regulatory teeth and record prescription travel together.
4. **The two frameworks scoring 0 are both explicitly non-certifiable guidance.** ISO 31000 and the
   OECD Principles are values documents; neither pretends otherwise.
5. **MADR 4.0.0 scores 5/8 — higher than SOC 2, NIST CSF 2.0, ISO 31000, and the OECD Principles.**
   A volunteer-maintained Markdown template captures more of the governance evidence spine than four
   institutional frameworks do. That is a genuinely surprising result and it deserves scrutiny in
   Report 5 rather than celebration here: MADR's fields are *optional-in-template*, and a field that
   is present but unfilled is not evidence.

---

## 4. On cost — read this before using any number in §5

Dimensions 9 (implementation cost) and 10 (cost of non-compliance) are the least reliable content in
this report. Three structural reasons:

1. **No governing body publishes cost data.** ISO, NIST, AICPA, and GSA do not publish or set pricing.
   ISO sells standards; AICPA does not set audit fees; FedRAMP does not publish 3PAO costs.
2. **The available figures are published by parties selling the remedy.** Vanta, Drata, Secureframe,
   Sprinto, Thoropass, and the ISO/CMMI consultancies all publish cost content as lead generation.
   Where such a figure appears below it is named and its interest is noted.
3. **No independent survey was located for any framework** — no Gartner/Forrester study with disclosed
   methodology, no accreditation-body benchmark, no academic cost survey. The one exception is the
   ISO 9001 decertification literature (§5.1), which is peer-reviewed.

**Penalties are different.** Where a penalty is written into statute it is `[primary]` and quotable:

| Framework | Top-tier penalty | Citation |
|---|---|---|
| EU AI Act | €35,000,000 or 7% worldwide annual turnover, **whichever is higher**; SMEs capped at the **lower** | Art. 99(3), 99(6) |
| GDPR | €20,000,000 or 4% worldwide annual turnover, whichever is higher | Art. 83(5) |
| UK GDPR | £17,500,000 or 4% | DPA 2018 / UK GDPR Art. 83 `[secondary]` |
| HIPAA | $2,190,294 calendar-year cap; $73,011 min/violation for uncorrected willful neglect | 45 CFR §102.3, FR Doc. 2026-01688, 2026-01-28 `[primary]` |
| CCPA/CPRA | $2,663/violation; $7,988 intentional or involving a minor under 16 | Cal. Civ. Code §1798.199.95(d), CPPA adjustment eff. 2025-01-01 `[secondary]` |

Note the AI Act's SME provision is the inverse of the general rule — for SMEs and start-ups each fine is
capped at **whichever is lower** of the percentage or the fixed amount. `[primary, Art. 99(6)]`

**Frameworks with no penalty regime at all** — and where any cited "cost of non-compliance" figure
should be treated as invented: ISO 9001, ISO 56001/56002, ISO 31000, ISO 27001, ISO 27002, NIST CSF,
ISO/IEC 42001, NIST AI RMF, OECD AI Principles, SOC 2, ADR conventions, OpenTelemetry, ITIL, COBIT,
CMMI. For these the real cost is **market access**: lost tenders, failed vendor reviews, contract
ineligibility. FedRAMP is the purest case — without authorisation a vendor cannot sell to US federal
agencies at all, which is a revenue gate rather than a penalty.

---

## 5. Framework profiles

Each profile covers the 19 requested dimensions. Dimensions 1–17 are research findings; dimension 18
(relevance to Memory Seed) and 19 (SWOT) are first-pass observations for Reports 3 and 7 to test.

### Family A — Quality & Process

#### 5.1 ISO 9001 — Quality Management Systems

| Dim | Finding |
|---|---|
| 1. Purpose | Requirements for a QMS delivering consistent conformity to customer and statutory requirements, with continual improvement. `[primary, iso.org via search index]` |
| 2. Problem solved | Inconsistent quality; no systematic process approach; no common supply-chain quality language. |
| 3. Industries | Generic by design. Concentrated in manufacturing, automotive supply chains, and as the base for AS9100 (aerospace) and ISO 13485 (medical devices). `[estimate]` |
| 4. Org size | Size-agnostic; adoption skews to SMEs and mid-market suppliers needing tender eligibility. `[estimate]` |
| 5. Owner | Top management (clause 5.1, non-delegable accountability); Quality Manager; process owners. The named "Management Representative" role was removed in 2015 but the function persists. `[secondary]` |
| 6. Required evidence | Internal audit records (9.2); management review minutes (9.3); nonconformity/CAPA records (10.2); monitoring and measurement data (9.1); competence records (7.2); calibration records (7.1.5); supplier evaluations (8.4). `[secondary]` |
| 7. Required documentation | Quality policy (5.2); objectives (6.2); QMS scope (4.3); documented information "to the extent necessary" (7.5) with control of creation/update (7.5.2, 7.5.3). The 2015 revision replaced "documents/records" with the broader "documented information." `[secondary]` |
| 8. Audit process | Accredited CB under ISO/IEC 17021-1. Stage 1 (readiness) → Stage 2 (implementation) → 3-year certificate → annual surveillance → recertification. `[secondary]` |
| 9. Implementation cost | `[estimate]` Small single-site: ~$4,000–6,000 certification; broader small-business range $5,000–15,000 including consultant and training. Sources are certification-adjacent vendors (ksqa.org, bprhub.com, amtivo.com) with commercial interest. No neutral benchmark located. |
| 10. Non-compliance cost | No statutory penalty. Peer-reviewed evidence exists on decertification: ~18% decertification propensity, ~60,000 certificates lost/year globally. Economic impact is **contested** — some studies find reduced firm value, others find no statistically significant difference. `[secondary, Total Quality Management & Business Excellence]` |
| 11. Pain points | Documentation perceived as bureaucratic overhead disconnected from real quality; surveillance-cycle fatigue; SME auditor cost; "checkbox compliance" without culture change. |
| 12. Software | MasterControl, Intelex, Qualio, Greenlight Guru, ETQ Reliance, Veeva QMS, Ideagen Qualsys, TrackWise. `[secondary]` |
| 13. Automation | Document-control workflows (7.5); CAPA closure-loop tracking (10.2); audit scheduling and evidence collection (9.2); KPI dashboards feeding management review (9.3). |
| 14. AI relevance | Not AI-specific, but supplies the Annex SL structure and risk-based thinking that ISO/IEC 42001 reuses. Organisations often layer AI controls onto an existing 9001 backbone. `[estimate]` |
| 15. Engineering | Applicable via 8.3 (design and development) and 8.5.6 (control of changes); less software-native than CMMI. |
| 16. Knowledge management | **Clause 7.1.6 "Organizational knowledge"** — added in 2015, explicitly requires determining, maintaining, and making available the knowledge needed for process operation. A direct, citable KM hook. `[secondary]` |
| 17. Decision traceability | Moderate. 7.5 + 9.3 + 10.2 create a trail of findings, decisions, and changes, but document *outcomes and controls* more than deliberative rationale. |
| **E-spine** | E1 I · E2 I · E3 R (7.5.2) · E4 I · E5 R · E6 R (7.5.3, 8.5.6) · E7 R (7.5.2 review and approval) · E8 I |
| **18. Memory Seed** | Clause 7.1.6 is the most direct hook of any framework in this family — an explicit organisational-knowledge requirement that Memory Seed's session corpus literally satisfies in form. But 9001's audit surface is process conformity, not engineering rationale, and the incumbent eQMS market is mature and entrenched. |
| **19. SWOT** | **S**: 7.1.6 KM clause; append-only history maps to 7.5.3 version control. **W**: no approval field for 7.5.2 sign-off; no calibration/competence surfaces. **O**: ISO 9001:2026 lands next month — a transition moment when documentation practice is revisited. **T**: eQMS incumbents own this buyer; quality functions are not engineering buyers. |

**Status verified 2026-08-01:** current edition ISO 9001:2015 (5th ed.). **A revision targeted for
September 2026 is imminent** — ISO/TC 176/SC 2's own page confirms the Sept 2026 target and a 36-month
project extension `[primary, committee.iso.org, page dated 2024-10-10]`. Reports that it has cleared
FDIS ballot with ~97% approval and carries a three-year transition to September 2029 come from TÜV, DQS,
and Oxebridge — certification bodies and consultancies that sell transition services `[secondary]`.

#### 5.2 ISO 56001:2024 / ISO 56002:2019 — Innovation Management

**Relationship resolved:** ISO 56001:2024 (certifiable requirements) was published **12 September 2024**
`[primary, committee.iso.org/sites/tc279]` and coexists with ISO 56002:2019 (guidance, non-certifiable).
ISO 56000:2025 is the current vocabulary document, replacing the 2020 edition `[secondary]`.

| Dim | Finding |
|---|---|
| 1–2. Purpose / problem | Requirements for an innovation management system; addresses ad hoc innovation with no governance, decision gates, or portfolio KPIs. `[primary]` |
| 3–4. Industries / size | Explicitly all types and sizes. Too new (<2 years) for adoption data. `[unsourced]` |
| 5. Owner | Top management; Chief Innovation Officer or Head of Innovation; portfolio managers; cross-functional innovation governance boards. `[secondary, vendor blogs]` |
| 6. Required evidence | Idea-flow records; **decision-gate and criteria documentation**; portfolio records; pilot/PoC records; KPI tracking. `[secondary, multiple independent CBs]` |
| 7. Required documentation | Annex SL structure: scope (4), policy and objectives (5), planning (6), support including knowledge as a named resource (7), operation (8), performance evaluation (9), improvement (10). `[secondary]` |
| 8. Audit process | Accredited CBs (DNV, SGS, LRQA, Q-Cert). Stage 1 → Stage 2 → 3-year certificate + annual surveillance. `[secondary]` |
| 9–10. Cost | `[unsourced]` — every CB omits figures and requires a quote. No decertification literature exists yet. No penalty regime. |
| 11. Pain points | Very new; scarce expertise and auditor experience; 56001-vs-56002 confusion; tension between documenting innovation and stifling it. |
| 12. Software | ITONICS, Ideanote, HYPE Innovation, Qmarkets, Brightidea, Planview. `[secondary, self-reported alignment]` |
| 13. Automation | Idea-intake and decision-gate workflow tracking; portfolio dashboards; audit-trail generation for Stage 2. |
| 14–15. AI / engineering | AI R&D is commonly framed as innovation management; decision gates map onto AI pilot-to-production pipelines. `[estimate]` |
| 16. Knowledge management | Strong natural fit — Clause 7 names knowledge as a resource category; idea lineage is inherently KM. `[secondary]` |
| 17. Decision traceability | **Structurally the strongest in this family.** The certifiable model is built around decision gates (idea → concept → pilot → scale), closer to a native decision log than 9001 or 31000. |
| **E-spine** | E1 R · E2 I · E3 I · E4 I · E5 R · E6 I · E7 I · E8 ? |
| **18. Memory Seed** | Decision-gate records are conceptually near-identical to Memory Seed decisions with lifecycle edges. But this is a tiny, brand-new market with no established buyer and no urgency. |
| **19. SWOT** | **S**: decision-gate model maps cleanly onto `(entry_id, dN)` + `evolves`. **W**: no approval or gate-status field. **O**: greenfield — no incumbent has defined the category. **T**: market may never materialise; certification volume is currently negligible. |

#### 5.3 ISO 31000 — Risk Management

| Dim | Finding |
|---|---|
| 1–2. Purpose / problem | Principles, framework, and process for managing risk; supplies a common vocabulary where none existed. `[primary]` |
| 3–4. Industries / size | Explicitly not sector-specific; fully size-agnostic; applies to "decision-making at all levels." `[primary]` |
| 5. Owner | Board/top management; CRO where present; ERM function. Notably **pushes risk ownership to all decision-makers** rather than centralising it. `[secondary]` |
| 6–8. Evidence / docs / audit | **ISO 31000 is NOT certifiable.** No accredited audit, no certificate. Organisations self-assess. Personnel "certificates" sold by training providers are competency certificates, not management-system certification — a widespread market confusion. `[secondary, learn31000.com]` |
| 9–10. Cost | `[unsourced]` — no audit fee to anchor a figure; no certification to lose. |
| 11. Pain points | Guidance rather than requirements means no forcing function; non-prescriptive language leaves operationalisation unclear; market confusion about "ISO 31000 certification." |
| 12. Software | LogicManager, Resolver, MetricStream, SAI360, Riskonnect, ServiceNow GRC, Origami Risk. `[secondary, vendor self-reported]` |
| 13. Automation | Risk-register maintenance and re-scoring; risk-appetite dashboards; escalation workflows for treatment decisions. |
| 14. AI relevance | High indirect — ISO/IEC 23894:2023 (AI risk management) is built to align with 31000's structure. `[secondary]` |
| 15–16. Engineering / KM | Underlies project risk registers and ISO/IEC 27005; risk identification and lessons-learned are inherently KM, though the standard avoids KM terminology. |
| 17. Decision traceability | **Conceptually strong but structurally absent.** The standard explicitly frames risk management as integral to decision-making, yet mandates nothing, because it is guidance. |
| **E-spine** | **0 REQUIRED.** All IMPLIED or absent — the structural consequence of being non-certifiable. |
| **18. Memory Seed** | A cautionary case. High conceptual affinity, zero evidentiary demand. Pursuing "ISO 31000 support" would generate no buyer urgency. Candidate **false opportunity** for Report 3. |
| **19. SWOT** | **S**: none specific. **W**: nothing to attach evidence to. **O**: minimal. **T**: conceptual affinity is seductive and could waste roadmap effort. |

**Status:** ISO 31000:2018 (2nd ed.). **Under revision** — "Development of Framework and Design
Specification for the revision of ISO 31000" is listed as in progress `[primary, committee.iso.org/tc262]`.
**Correction:** the current risk vocabulary standard is **ISO 31073**, not ISO Guide 73:2009
`[primary, TC 262 project list]`.

### Family B — Information Security

#### 5.4 ISO/IEC 27001 — Information Security Management Systems

| Dim | Finding |
|---|---|
| 1–2. Purpose / problem | Requirements for an ISMS; gives an auditable process to identify security risks, decide treatment, and **prove ongoing governance of that decision**. |
| 3–4. Industries / size | Cross-sector, heavy in B2B software procurement. Certifiable at any size; audit days scale via IAF MD 5. |
| 5. Owner | Top management (5.1); ISMS Manager / CISO (5.3 requires role assignment, not a title); **risk owners per risk** (6.1.2). |
| 6. Required evidence | **Statement of Applicability**; risk assessment records and treatment plan; internal audit records (9.2); management review minutes (9.3); corrective actions (10.2); competence records (7.2). `[secondary]` |
| 7. Required documentation | Scope (4.3); policy (5.2); risk process + **SoA** (6.1.2–6.1.3); objectives (6.2); documented information (7.5.1–7.5.3); operational records (8.1–8.3); audit (9.2); management review (9.3); nonconformity (10.2). `[secondary]` |
| 8. Audit process | ISO/IEC 17021-1 + **ISO/IEC 27006-1:2024** (CB requirements, superseding 27006:2015; CBs had until 31 March 2026 to transition under IAF MD 29). Stage 1 → Stage 2 → 3-year cycle with annual surveillance. `[secondary]` |
| 9. Implementation cost | `[estimate]` Small orgs (<50): $15,000–50,000 first year; CB audit fees alone ~$7,000–12,500 for 1–10 FTE. Mid/large: £50K–100K+. **All sources are compliance-automation vendors and consultancies selling ISO 27001 readiness** (Drata, StrongDM, Thoropass, iso27001cost.com). No independent survey located. |
| 10. Non-compliance cost | `[unsourced]` for any rigorous figure. No statutory penalty. A widely circulated Ponemon breach-cost figure was found only inside a commercial blog, not the report — **not usable**. |
| 11. Pain points | SoA drift as risks change; evidence-collection burden across teams; documented-information version control at scale (7.5.3); nominal rather than substantive risk ownership; rubber-stamp management review. |
| 12. Software | Vanta, Drata, Secureframe, Sprinto, Thoropass, OneTrust, ServiceNow GRC, Archer, MetricStream, Hyperproof, ISMS.online, LogicGate. |
| 13. Automation | Evidence collection via API; **SoA-to-control-to-risk traceability graphs**; continuous control monitoring; policy-review reminders tied to 7.5.2; management-review generation. |
| 14. AI relevance | Technology-agnostic; AI systems are in scope only as information assets. ISO/IEC 42001 is the AI-specific instrument. |
| 15. Engineering | Annex A technological controls: A.8.9 configuration management, A.8.25 secure development lifecycle, A.8.28 secure coding, **A.8.32 change management**, A.8.31 dev/test/prod separation. `[secondary]` |
| 16. Knowledge management | Clause 7.5 is effectively a KM mandate — version-controlled, access-controlled, review-and-approval-gated documentation of policy and risk decisions. |
| 17. Decision traceability | **The strongest in this family.** The SoA is literally a per-control decision log with mandatory recorded justification for every inclusion *and* exclusion. 6.1.3 requires documented treatment rationale with owner sign-off. 9.3 creates a dated, attended decision record. 10.2 creates an auditable nonconformity → corrective-action chain. |
| **E-spine** | E1 R (SoA 6.1.3d) · E2 R (5.3, 6.1.2) · E3 I (7.5.2) · E4 R (SoA justification) · E5 I · E6 R (7.5.3, 10.2) · E7 R (7.5.2, 6.1.3f) · E8 R (A.5.9) — **6 REQUIRED** |
| **18. Memory Seed** | The SoA is the closest institutional analogue to a decision record with mandatory rationale that exists in security governance. The gap is that SoA maintenance is a GRC-platform workflow with entrenched incumbents, and the buyer is the CISO, not engineering. |
| **19. SWOT** | **S**: rationale-with-decision is native; append-only supersession matches 7.5.3. **W**: no approval/sign-off field for 7.5.2 or 6.1.3(f) — a hard blocker for E7. **O**: A.8.32 change management is engineering-side and poorly served by GRC tools. **T**: Vanta/Drata own evidence automation and would treat this as a feature. |

**Status verified 2026-08-01:** ISO/IEC 27001:2022 (3rd ed.) + **Amd 1:2024 (climate action)**. The
**2013 → 2022 transition deadline closed 31 October 2025** — nine months ago. An organisation still
certified only to the 2013 edition is no longer validly certified and faces a full initial audit
`[secondary — IAF MD 26 via A-LIGN, SGS, EIAC; the MD 26 PDF itself was not fetched]`.

#### 5.5 ISO/IEC 27002 — Information Security Controls

| Dim | Finding |
|---|---|
| 1–2. Purpose | Non-certifiable control catalogue and implementation guidance behind 27001's Annex A. 93 controls in 4 themes (organizational, people, physical, technological), down from 114 controls / 14 clauses in 2013. |
| 6–8. Evidence / audit | **Not independently certifiable.** No accredited "ISO 27002 certificate" exists; any vendor offering one is not describing an accredited scheme. Evidence obligations are inherited from 27001. |
| 9–10. Cost | `[unsourced]` standalone — bundled into 27001 cost. |
| 11. Pain points | Mapping 93 controls to actual risks rather than implementing mechanically; the 11 controls new in 2022 (threat intelligence, cloud security, data masking); control-ownership diffusion. |
| 15–17. Engineering / KM / traceability | Clause 8 (controls 8.1–8.34) is an application-security and IT-ops checklist. Control **5.37 documented operating procedures** is a KM specification. **Control 8.32 change management** — planned, assessed, authorised, tested, documented, communicated — is the clearest decision-traceability artefact, a full E1–E8-shaped record per system change. |
| **E-spine** | Mostly IMPLIED at document level; **E6, E7, E8 REQUIRED via control 8.32 and 5.9**. |
| **18–19. Memory Seed** | A.8.32/8.32 change management is the single most Memory-Seed-shaped control in the security family: a change, its assessment, its authorisation, its test evidence, its scope. **S**: DRAFT D/R/A/F/T maps almost field-for-field. **W**: no authorisation field. **O**: change records live in engineering tooling, not GRC. **T**: Jira/GitHub already hold this data. |

#### 5.6 NIST Cybersecurity Framework 2.0

| Dim | Finding |
|---|---|
| 1–2. Purpose | Voluntary, outcome-based framework (not a management system, not certifiable) structured as Functions → Categories → Subcategories, with Organizational Profiles and Implementation Tiers. `[primary, nist.gov/cyberframework]` |
| 3–4. Industries / size | **Explicitly broadened in 2.0 beyond critical infrastructure** to organisations regardless of type or size. No cost gate, since there is no audit. |
| 5. Owner | No mandated titles. GV.RR-02 requires roles, responsibilities, and authorities be *"established, communicated, understood, and enforced."* `[primary]` |
| 6–8. Evidence / audit | **No certification, no accredited auditor, no mandatory evidence list.** Self-assessment via Current Profile vs Target Profile gap analysis, with four Implementation Tiers (Partial / Risk Informed / Repeatable / Adaptive). Any vendor marketing "NIST CSF certification" is not describing a NIST scheme. |
| 9–10. Cost | Framework is free. Implementation cost `[unsourced]`. No compliance status to lose; indirect exposure only where referenced by contract or cyber-insurance underwriting. |
| 11. Pain points | GOVERN is new (Feb 2024) so programs built on CSF 1.1's five functions lack mapped governance evidence; outcome language (*"is understood," "is managed"*) makes completeness subjective; no accreditation means inconsistent self-assessment rigour. |
| 12–13. Software / automation | Vanta, Drata, Secureframe, Isora GRC, CyberSaint, ServiceNow GRC, Archer. Continuous Current-Profile generation from telemetry; policy-review tracking against GV.PO-02; official OLIR cross-mappings to ISO 27001 and SP 800-53. |
| 17. Decision traceability | **Structurally weak, and instructively so.** CSF states desired outcomes without mandating a decision-log artefact, evidentiary citation, or approval workflow. |
| **E-spine** | **1 REQUIRED** — only E8, via ID.AM-01 *"Inventories of hardware managed by the organization are maintained."* `[primary, CSF 2.0 Core export]` |
| **18. Memory Seed** | The clearest illustration of where a decision substrate has *nothing to attach to*. CSF asks for outcomes; there is no required record to hold. Candidate **false opportunity**. |
| **19. SWOT** | **S**: none specific. **W**: no mandated artefact. **O**: GV.PO-02's "reviewed, updated" is the one revision hook. **T**: effort here would produce no buyer urgency. |

**Status verified 2026-08-01:** CSF 2.0, NIST.CSWP.29, published 2024-02-26. **Six Functions —
GOVERN (GV) is present** and is new in 2.0; CSF 1.1 had five. Subcategory text in this report is
`[primary]`, extracted from NIST's own machine-readable Core export at
`csrc.nist.gov/extensions/nudp/services/json/csf/download`.

### Family C — AI Governance

#### 5.7 ISO/IEC 42001 — AI Management System

| Dim | Finding |
|---|---|
| 1–2. Purpose | Requirements for an AI Management System (AIMS) — certifiable, Annex SL, parallel to 27001. Fills for AI the gap 27001 filled for security: externally verifiable proof rather than self-attested policy. |
| 3–5. Industries / size / owner | Cross-sector: SaaS, financial services, healthcare, cloud/AI infrastructure. Executive sponsor increasingly a **Chief AI Officer** — an emerging title analogous to the post-GDPR DPO, not yet standard. `[secondary]` Annex A.3.2 requires AI roles and responsibilities be defined. |
| 6–7. Evidence / documentation | Mandatory documents per convergent secondary compilers: AIMS scope (4.3), AI policy (5.2), objectives (6.2), risk assessment methodology (6.1.2), risk treatment plan (6.1.3), **Statement of Applicability**, plus retained records for risk results (8.2), treatment results (8.3), **impact assessment results (6.1.4/8.4)**, competence (7.2), internal audit, management review. Annex A: **38 controls across 9 groups**, key families A.5 (impact assessment), A.6 (lifecycle), A.7 (data), A.8 (information for interested parties). `[secondary]` |
| 8. Certification | Certifiable. CBs must be accredited under **ISO/IEC 42006:2025** (published 2025-07-07) `[primary, IEC webstore]`, which supplements 17021-1 with AI-specific competence and audit-time requirements. Named accredited CBs include Schellman (first ANAB-accredited), BSI (triple ANAB/UKAS/RvA, March 2026), SGS, A-LIGN, Coalfire. `[secondary, CB press releases]` Auditor capacity is a bottleneck — reported six-month lead times. `[secondary]` |
| 9. Cost | `[estimate, all vendor-sourced with direct commercial interest]` Small ~$15,000–40,000; mid-market ~$180,000–320,000; large (500+) ~$350,000–650,000. CB audit fees $7,000–25,000 initial, $3,500–9,000/yr surveillance. Vanta's own published ISO 42001 module pricing: $7,500–10,000/yr on top of base subscription `[secondary, vanta.com, vendor's own figure]`. |
| 10. Non-compliance cost | **Not directly enforceable by any regulator.** Entirely opportunity cost — lost market access where RFPs require the certificate. `[unsourced]` for any dollar figure. |
| 11. Pain points | Immature auditor capacity and inconsistent rigour; ambiguity in defining AI-system scope for the SoA; duplication with 27001/SOC 2; the A.5 impact-assessment burden is new muscle; **widespread buyer misunderstanding that certification implies AI Act conformity**. |
| 12. Software | Vanta, Credo AI, OneTrust, Drata, Fairly AI, Holistic AI, Modulos, Saidot, Trustible, FairNow (acquired by AuditBoard), IBM watsonx.governance, ServiceNow, Collibra. `[secondary]` |
| 13. Automation | Evidence collection for A.7 data-provenance controls; **continuous AI-system inventory (A.6) as a living register rather than a point-in-time document**; single-control-to-many-framework crosswalks; impact-assessment templating; SoA drift detection when AI systems ship without governance review. |
| 14. AI relevance | Governs the **management system wrapping** the whole AI lifecycle — policy, risk methodology, accountability — not the AI engineering itself. |
| 15. Engineering | A.6 (lifecycle) and A.7 (data) require engineering teams to produce and retain technical documentation, data lineage, and event logs as **first-class deliverables**, a meaningful new documentation load on ML teams. |
| 16. Knowledge management | Clause 7.5 + A.6.2.3 (design/development documentation) + A.6.2.7 (technical documentation) effectively mandate a structured, retained, version-controlled knowledge base of AI design decisions. Arguably the standard's most KM-relevant feature. |
| 17. Decision traceability | Mandatory retained records (7.5) + impact-assessment documentation (A.5.2/A.5.3) + **event logging (A.6.2.8)** + management-review sign-off (9.3) create a structurally REQUIRED decision trail. |
| **E-spine** | E1 R · E2 R · E3 I · E4 R · E5 R · E6 R (A.6.2.8) · E7 R (9.3) · E8 R — **7 REQUIRED** |
| **18. Memory Seed** | The highest-affinity certifiable standard in the entire landscape. "Documentation of AI-system design and development" with retained rationale, lifecycle change records, and data provenance is a description of what Memory Seed already stores. The caveat is that the buyer is a governance function and the evidence is auditor-mediated. |
| **19. SWOT** | **S**: design-decision rationale + supersession + provenance are native. **W**: E7 approval and A.7 data-provenance surfaces are absent. **O**: newest certifiable standard, no incumbent has won it, auditor capacity is scarce. **T**: Credo AI/Vanta are building here now; 42001's market-access value is undercut by prEN 18286. |

**Critical status finding:** ISO/IEC 42001 certification carries **no legal presumption of EU AI Act
conformity**. CEN-CENELEC's JTC 21 found 42001's goals and definitions misaligned with the AI Act's
quality-management requirement and wrote a bespoke standard, **prEN 18286**, instead — with an Annex D
crosswalk letting 42001 holders reuse existing controls. Presumption of conformity under Art. 40
attaches only once prEN 18286 is cited in the Official Journal, which has not happened.
`[secondary — CSA research note 2026-04-28, Schellman; both sell AI-governance services]`
Note also that "EN ISO/IEC 42001:2026" in reseller catalogues is a **CEN regional-adoption draft, not a
new ISO edition**. Companion standards: **ISO/IEC 42005:2025** (AI system impact assessment, published
2025-05-28) and **ISO/IEC 22989:2022** (terminology) `[primary, IEC webstore]`.

#### 5.8 NIST AI Risk Management Framework 1.0

| Dim | Finding |
|---|---|
| 1–2. Purpose | *"Offer a resource to the organizations designing, developing, deploying, or using AI systems to help manage the many risks of AI"* — voluntary, rights-preserving, sector-agnostic. `[primary, NIST AI 100-1, p.2]` Directed by the National AI Initiative Act of 2020. |
| 3–4. Industries / size | Explicitly non-sector-specific. Explicitly scale-flexible: SMEs *"may face different challenges than large organizations, depending on their capabilities and resources."* `[primary, §1.2.4]` Free and non-certifiable, so inherently more accessible than 42001. |
| 5. Owner | Names governance **tiers** rather than titles: governing authorities, senior leadership, management. GOVERN 2.3: *"Executive leadership of the organization takes responsibility for decisions about risks associated with AI system development and deployment."* `[primary]` |
| 6–8. Evidence / audit | **Explicitly voluntary and non-certifiable.** No NIST-run or endorsed certification, no accredited auditors, no certificate. Self-assessment via **Current Profile vs Target Profile** gap analysis. The Playbook supplies suggested, non-mandatory actions. |
| 9–10. Cost | Framework free. `[unsourced]` for AI-RMF-isolated implementation cost — vendor figures conflate it with multi-framework GRC platforms. Zero direct legal exposure. |
| 11. Pain points | No certification means no forcing function; 4 functions / ~19 categories / 70+ subcategories with no prescribed sequencing beyond GOVERN-first; the framework itself concedes *"Use of the AI RMF alone will not lead to these changes or provide the appropriate incentives"* `[primary, §1.2.4]`; predates the GenAI wave, requiring the bolt-on AI 600-1 profile. |
| 13. Automation | Current/Target Profile gap analysis is inherently structured data; AI-system inventory (GOVERN 1.6) via model registries; official NIST crosswalks to ISO/IEC 5338, 22989, 38507, 24028, 42001, 42005. |
| 16. Knowledge management | §4 lists as an expected benefit *"better information sharing within and across organizations about risks, decision-making processes, responsibilities, common pitfalls, TEVV practices."* `[primary]` Close to an explicit organisational-KM objective. |
| 17. Decision traceability | GOVERN + MAP form the backbone: MAP 1.1 (context documented), MANAGE 1.1 (explicit go/no-go), GOVERN 1.6 (inventory). Weaker on who/when/approved-by than 42001. |
| **E-spine** | E1 R (MANAGE 1.1) · E2 I · E3 ? · E4 R (GOVERN 4.2) · E5 R (MEASURE 2.1) · E6 R (MANAGE 4.1) · E7 I · E8 R (GOVERN 1.6) — **5 REQUIRED** |
| **18. Memory Seed** | **The single most important structural contrast in this report.** ISO 42001 mandates *retained records*; AI RMF mandates *documented outcomes without prescribing record fields* — no required timestamp, no named approver of record, no retention schedule. That gap between "you must document this" and "here is what a document must contain" is exactly the space a decision-record substrate occupies. |
| **19. SWOT** | **S**: supplies the record schema AI RMF deliberately omits. **W**: no approval field; AI RMF has no audit to sell into. **O**: free + widely adopted = large surface, low friction. **T**: no forcing function means no budget. |

**Status verified 2026-08-01:** AI RMF 1.0 (NIST AI 100-1, January 2023), with the **Generative AI
Profile (NIST AI 600-1, July 2024)**. NIST's own page states **"The AI RMF 1.0 is being revised"** — no
version 2.0 published `[primary, nist.gov/itl/ai-risk-management-framework]`. Reported 2026 activity (a
critical-infrastructure profile concept note, April 2026; a public-facing AI documentation draft, July
2026) is `[secondary, unverified against a primary NIST page]`.

#### 5.9 EU AI Act — Regulation (EU) 2024/1689

**Read the status first.** A binding amending act is in force: **Regulation (EU) 2026/1744 of 8 July
2026, "Digital Omnibus on AI,"** published in the OJ 24 July 2026, in force **27 July 2026** — five days
before this report. `[primary, EUR-Lex, verified directly]`

| Obligation | Legal basis | Status as of 2026-08-01 |
|---|---|---|
| Prohibited practices (Art. 5) + AI literacy (Art. 4) | Art. 113 | **In force since 2 Feb 2025** |
| GPAI model obligations (Arts. 53–55) | Art. 113 | **In force since 2 Aug 2025**; Commission enforcement powers activate 2 Aug 2026 |
| Transparency (Art. 50) | Unchanged by Omnibus | **Applies from 2 Aug 2026 — tomorrow** |
| High-risk Annex III (stand-alone) | **Deferred by Reg. 2026/1744** | Not applicable until **2 Dec 2027** (was 2 Aug 2026) |
| High-risk Annex I (product-embedded) | **Deferred by Reg. 2026/1744** | Not applicable until **2 Aug 2028** (was 2 Aug 2027) |
| New CSAM / non-consensual intimate content prohibitions | Reg. 2026/1744 | From 2 Dec 2026 |

| Dim | Finding |
|---|---|
| 3. Actors | Precise role taxonomy in Art. 3: **provider** (develops and places on market under own name), **deployer** (uses under its authority, excluding personal non-professional use), importer, distributor. Extraterritorial where output is used in the EU (Art. 2). `[primary]` |
| 4. Size | Applies regardless of size. SME mitigations: simplified technical documentation (Art. 11(1) + Annex IV proportionality), sandbox priority (Art. 62), and the **inverted fine cap** (Art. 99(6)). |
| 5. Owner | No statutory title, but implies an AI governance lead, a QMS owner (Art. 17), and a FRIA owner (Art. 27) for certain deployers. |
| 6. Required evidence | Technical documentation file (Art. 11 / Annex IV); automatically generated logs (Art. 12); EU declaration of conformity and CE marking (Arts. 47–48); QMS documentation and evidence of operation (Art. 17); post-market monitoring records and incident reports (Arts. 72–73); deployer FRIA (Art. 27). |
| 7. Required documentation | **Annex IV is the core.** §2(b) requires *"the general logic of the AI system and of the algorithms; the key design choices including the rationale and assumptions made."* §2(f) requires description of pre-determined changes. §2(g) requires *"test logs and all test reports dated and signed by the responsible persons."* §6 requires *"relevant changes made by the provider to the system through its lifecycle."* Art. 12 requires lifecycle traceability logging. Art. 17 requires a documented QMS. **Art. 18 requires 10-year retention.** `[primary]` |
| 8. Conformity assessment | Most high-risk: provider **self-assessment** via internal control (Annex VI). Certain biometric categories: **notified body** assessment (Annex VII). CE marking on conformity. National market surveillance authorities enforce; the **AI Office** has exclusive competence over GPAI providers. |
| 9. Implementation cost | `[estimate]` Publicly circulating figures originate almost entirely from parties with a stake — either industry associations lobbying for the deferral that was ultimately granted, or GRC vendors selling the remedy. No Commission-published aggregate figure located. `[unsourced]` for an authoritative estimate. |
| 10. Non-compliance cost | `[primary, Art. 99]` **€35,000,000 / 7%** (prohibited practices); **€15,000,000 / 3%** (other listed obligations); **€7,500,000 / 1%** (incorrect or misleading information) — whichever is *higher*. **Art. 99(6): for SMEs and start-ups, whichever is *lower*.** |
| 11. Pain points | **No harmonised standard has been cited in the OJ**, so the Art. 40 presumption-of-conformity route does not exist yet; slow national authority designation; Annex III boundary ambiguity; GPAI compute-threshold contestation; GDPR/DSA/sectoral-law interplay. |
| 16. Knowledge management | Annex IV + Art. 12 constitute, structurally, a **mandated knowledge-management and decision-record system** — design rationale, assumptions, and lifecycle change history captured and retained for the system's life plus ten years. |
| 17. Decision traceability | **The most traceability-dense regulatory text of any framework in scope.** |
| **E-spine** | **8/8 REQUIRED**, all with Article or Annex citations. |
| **18. Memory Seed** | Annex IV §2(b) + §2(g) + §6 read almost as a specification for a decision record: rationale for design choices, dated and attributed test evidence, lifecycle change history. If any single framework justifies a decision-governance product thesis, it is this one. |
| **19. SWOT** | **S**: D/R/A + `evolves`/`replaces` + timestamps map directly onto Annex IV. **W**: no signature/approval field for §2(g) *"signed by the responsible persons"*; no dataset or metric surfaces. **O**: 10-year retention creates a durable-record requirement that wikis handle badly. **T**: **the deadline just moved 16 months**, deflating near-term urgency; and the record must be a formal technical file, not a session log. |

**Harmonised standards status:** CEN-CENELEC JTC 21 works under mandate M/593 (deadline revised to
31 Aug 2025, then slipping); October 2025 "exceptional measures" target key standards — prEN 18228 (risk
management, Art. 9) and prEN 18284 (data quality, Art. 10) — for Q4 2026 `[secondary, cencenelec.eu, the
standards body's own news page]`. **GPAI Code of Practice** published 10 July 2025, voluntary; signatories
get reduced administrative burden, non-signatories must show compliance by *"alternative adequate means"*
(Art. 53(4)) `[primary, Commission]`.

#### 5.10 OECD AI Principles

| Dim | Finding |
|---|---|
| 1–2. Purpose | OECD/LEGAL/0449, the first intergovernmental AI standard: promote AI that is innovative and trustworthy and respects human rights and democratic values. Adopted 22 May 2019, **revised 3 May 2024** for generative AI and foundation models. **47 adherents.** `[primary]` |
| 3. Actors | Non-binding, addressed to **governments** as policy guidance; secondarily to "AI actors" as behavioural expectations. No provider/deployer taxonomy. |
| 6–8. Evidence / audit | **None.** Soft law. Monitored via the OECD.AI Policy Observatory; no fines, no certification. |
| 9–10. Cost | **Not applicable** — no compliance regime and no penalty regime exist. This is a structural fact, not a research gap. |
| Content | Five values-based principles: inclusive growth; human-centred values and fairness; **transparency and explainability**; robustness, security and safety; **accountability**. Plus five policy recommendations. Supplies the widely-adopted definition of "AI system." `[primary]` |
| Relationships | Underpins the **G7 Hiroshima Process** International Code of Conduct, which uses the OECD's definition and principles as its base; OECD.AI operationalises monitoring for both. `[primary]` |
| **E-spine** | **0 REQUIRED.** Aspirational throughout — by design. Accountability implies decisions are identifiable; transparency implies rationale should be explicable; neither requires a record. |
| **18–19. Memory Seed** | Zero evidentiary demand. Its value to this programme is as the **conceptual origin** of what the AI Act later operationalised — useful for framing, useless as a market. Candidate **false opportunity**. |

### Family D — Software Assurance

#### 5.11 SOC 2 — AICPA Trust Services Criteria

| Dim | Finding |
|---|---|
| 1–2. Purpose | An **attestation**, not a certification: a licensed CPA firm examines and reports on controls relevant to Security, Availability, Processing Integrity, Confidentiality, and/or Privacy. Removes the need for every enterprise customer to audit a vendor independently. `[primary, AICPA]` |
| 3–4. Industries / size | B2B SaaS selling to US enterprise; data centres, MSPs, fintech infrastructure. Disproportionately pursued by startups because it is cheaper and faster than ISO 27001 or FedRAMP. |
| 5. Owner | Not prescribed by AICPA. Convention: CISO or VP Engineering owns the program; a compliance/GRC manager runs evidence collection; department heads own controls. `[secondary]` |
| 6. Required evidence | Access-review tickets and offboarding records (CC6); MFA and least-privilege configuration (CC6.1); **change tickets showing authorization → testing → approval → deployment (CC8.1)**; vulnerability scans and remediation (CC7); risk register (CC3); incident tickets and postmortems (CC7.3–7.5); vendor due diligence (CC9.2); **network/data-flow diagrams** and terminated-employee asset retrieval, both added as 2022 points of focus. `[secondary, EY]` |
| 7. Required documentation | **System description** per the 2018 Description Criteria (DC section 200) with 2022 revised implementation guidance; **management's written assertion**; the policy set. Reports governed by AT-C 105 / 205 under SSAE 18/21. `[primary, AICPA]` |
| 8. Audit process | **Type I** = design at a point in time. **Type II** = design *and* operating effectiveness over an observation window, typically 3–12 months (AICPA mandates a period, not a length; enterprises usually require 6 or 12). Only a licensed CPA firm may issue the report — there is no accreditation body analogous to a 3PAO. |
| 9. Cost | `[estimate, vendor-sourced]` Compliance-automation vendors (Vanta, Drata, Secureframe, Sprinto — **all of which monetise SOC 2 readiness**) publish first-year totals of roughly $20,000–80,000+. **No AICPA cost figure exists**; fees are negotiated per firm. Treat every point figure in circulation as lead generation. |
| 10. Non-compliance cost | **No statutory penalty. AICPA does not fine anyone.** Cost is entirely commercial: lost enterprise deals, failed vendor-risk questionnaires, and contract/misrepresentation exposure if a report proves inaccurate. |
| 11. Pain points | **Evidence collection is the dominant complaint** — continuously capturing proof for every control, every period, across IdP, ticketing, cloud consoles, and HRIS. Maintaining evidence freshness across a 6–12 month Type II window. Auditor inconsistency. |
| 12. Software | Vanta, Drata, Secureframe, Sprinto, AuditBoard, Hyperproof. |
| 13. Automation | **Already mature**: continuous evidence collection via read-only API integrations; control-monitoring dashboards flagging drift in real time; policy templates; auditor-collaboration portals. **Still manual**: the CPA judgment itself; risk-assessment narrative and materiality judgments (CC3); vendor due-diligence write-ups. |
| 14. AI relevance | **The current TSC contains no AI-specific criteria.** AI risks must be mapped onto generic criteria (CC6 access, C1 confidentiality, PI1 processing integrity). No dedicated AI trust-services category and no exposure draft located. |
| 17. Decision traceability | CC8.1 is the hook — every production change should show who proposed it, why, who approved it, when, and what it affected. |
| **E-spine** | E1 R (CC8.1) · E2 I · E3 I · E4 I · E5 I · E6 I · E7 R (CC8.1 explicitly includes *"approves"*) · E8 I — **2 REQUIRED** |
| **18. Memory Seed** | Instructive caution. SOC 2 *feels* like the obvious wedge — it is the most commonly pursued framework by exactly the software companies Memory Seed serves — but the TSC states outcomes, not evidence requirements. **When a vendor says "SOC 2 requires X evidence," that traces to auditor practice or tooling defaults, not AICPA text.** The evidence-automation market is also the most mature and best-funded in this landscape. |
| **19. SWOT** | **S**: CC8.1's who/why/approved/when maps to DRAFT labels. **W**: no approval field, which is the one thing CC8.1 explicitly names. **O**: CC3 risk-assessment narrative is still manual and judgment-heavy. **T**: Vanta/Drata/Secureframe own this buyer completely and would ship this as a feature. |

**Status note:** AICPA has publicly flagged concern in 2026 about *"quick-turn SOC engagements"* and
undisclosed business arrangements between CPA firms and SOC compliance-automation vendors, warning that
such arrangements can compromise auditor independence `[primary, AICPA SOC landing page]`. This is a
live integrity issue in the market a decision-evidence product would enter.

#### 5.12 FedRAMP

| Dim | Finding |
|---|---|
| 1–2. Purpose | Government-wide standardised approach to security assessment, authorisation, and continuous monitoring of cloud services for US federal agencies — "authorize once, use many times." `[primary, fedramp.gov]` |
| 3–4. Industries / size | Cloud service providers selling to US federal agencies. Historically skewed large given 18–24 month legacy timelines; **20x is explicitly positioned to open the program to smaller cloud-native vendors** via 90–180 day paths. `[secondary]` |
| 6–7. Evidence / documentation | **System Security Plan (SSP)**; **POA&M**; Security Assessment Plan and Report (3PAO-produced); continuous monitoring plan. Monthly vulnerability scans, POA&M updates, and inventory uploads. Security Impact Analysis submitted to the AO **at least 30 days before** a planned significant change. Under 20x, **OSCAL machine-readable submissions replace narrative SSPs**. `[primary]` |
| 8. Authorisation | **The JAB no longer exists.** Dissolved; JAB P-ATO intake closed August 2024. Replaced by the **FedRAMP Board** (seven members from DHS, DoD, VA, Air Force, CISA, FDIC, GSA) under the FY23 NDAA, which sets policy rather than granting individual ATOs. `[primary, GSA newsroom]` Legacy path: Agency ATO via sponsoring agency AO on a 3PAO assessment against Rev5 baselines. New path: **FedRAMP 20x**, launched March 2025, now in **Phase 3 (wide-scale adoption)**, Classes A/B/C active, Class D (High) planned FY27. **531 authorised services, 28 of them 20x-certified.** New Rev5 certifications stop being accepted **11 June 2027**. `[primary, fedramp.gov/20x, retrieved 2026-08-01]` |
| 9–10. Cost | `[estimate, vendor-sourced]` Legacy Moderate authorisation commonly cited in the hundreds of thousands to low millions, driven by 3PAO fees and remediation labour. No GSA-published figure. Cost of non-compliance is a **pure market gate**: no authorisation, no federal sales at all. |
| 11. Pain points | Legacy SSP narrative burden (the exact problem OSCAL targets); **monthly** ConMon cadence that never stops post-authorisation, unlike SOC 2's periodic window; transition ambiguity while Rev5 and 20x run in parallel; 3PAO capacity. |
| 13. Automation | **The 20x program is itself a government-led automation initiative** — the opportunity *is* the reform, not a gap vendors are filling around a static framework. Contrast with SOC 2, where automation is vendor-led around static AICPA criteria. Still manual: 3PAO judgment (by design), Security Impact Analysis narrative, AO risk-acceptance decisions. |
| 16. Knowledge management | The SSP is a canonical, control-indexed knowledge artefact, and **OSCAL is explicitly designed to make that knowledge machine-queryable rather than locked in prose** — directly relevant to any graph representation of governance state. |
| 17. Decision traceability | CA-6 (authorisation) and CA-5 (POA&M) create an explicit dated chain of who accepted risk, what remediation was promised, and by when. CM-3 requires determining and documenting configuration-controlled change types; CM-4 requires analysing changes *"to determine potential security and privacy impacts prior to change implementation."* `[primary, SP 800-53 Rev 5]` |
| **E-spine** | **8/8 REQUIRED.** NIST control language is drafted procedurally — *document, retain, update, assign, authorize* — so nearly every cell has quotable text. |
| **18. Memory Seed** | Structurally the best-fitting framework after the AI Act, and the worst-fitting commercially. OSCAL means the federal government is already standardising machine-readable governance records — which is either strong validation of the thesis or a signal that this niche is being solved by mandate. |
| **19. SWOT** | **S**: CM-3/CM-4 change rationale and CA-5 POA&M revision chains map well. **W**: no OSCAL surface; no risk-acceptance/approval field. **O**: OSCAL proves buyers now want machine-readable governance evidence. **T**: extremely long sales cycles, federal-only, and 20x is a moving target until Consolidated Rules settle. |

**Unverified item, flagged rather than asserted:** secondary reporting (Winvale) dates FedRAMP Ready's
retirement to 28 July 2026, but the primary rules page returned 404. Do not rely on this date.

#### 5.13 Architecture Decision Record conventions

**There is no governing body.** ADR is a convention family — Nygard's 2011 article, MADR, Joel Parker
Henderson's repository, adr-tools, Y-statements — each with an independent author or maintainer group.
Dimensions 8 and 10 are **not applicable**: no audit regime, no certification, no penalties.

| Dim | Finding |
|---|---|
| 1–2. Purpose | Capture significant technical decisions as short, immutable, timestamped records stored near the code, so the *reasoning* survives turnover. Nygard: *"One of the hardest things to track during the life of a project is the motivation behind certain decisions."* `[primary]` |
| 5. Owner | No formal role. MADR carries a `decision-makers` front-matter field so the accountable party is named **per record** rather than as a standing role. Azure guidance assigns stewardship to the solution architect. `[primary]` |
| 11. Pain points | **Adoption decay is empirically documented**: an MSR study of 900+ GitHub repositories found roughly **50% of ADR-using repositories contain only 1–5 records total**, suggesting trial-and-abandon is the modal outcome `[secondary, Buchgeher et al., IEEE Access 2023]`. Also: records decoupled from code drift stale; "written and never read" is universally complained about but the readership claim is `[unsourced]`. **Counter-evidence**: a 2024 ECSA action-research study found ADRs measurably improved knowledge transfer *where the operating model, not just the artifact, was adopted* `[secondary]`. |
| 12. Software | adr-tools (npryce), MADR templates, Log4brains (in low-maintenance mode), adr-manager, Structurizr, the Backstage ADR plugin, Confluence templates, git-adr. |
| 13. Automation | CI checks requiring an ADR for architecturally significant PRs; **LLM-assisted ADR generation from PR/commit diffs and LLM-based violation detection against existing ADRs are an active 2025–26 research area** (arXiv 2504.08207, 2604.03826, 2602.07609 — preprints, not peer-reviewed). |
| 17. Decision traceability | **The central dimension.** AWS: *"When the team accepts an ADR, it becomes immutable… the team proposes a new ADR that supersedes the previous one."* Azure: *"The ADR serves as an append-only log. Don't go back and edit accepted records."* `[primary]` This append-only supersession model is the traceability backbone — **but it is convention, enforced by nothing except team discipline.** |

**Field-by-field spine comparison** — the most useful artefact in this section, carried into Report 5:

| Q | Nygard (2011) | MADR 4.0.0 | ISO/IEC/IEEE 42010:2022 |
|---|---|---|---|
| E1 what | REQUIRED — `Decision` | REQUIRED — `Decision Outcome` | REQUIRED (conceptual) |
| E2 who | **NOT PRESENT** | REQUIRED — `decision-makers` | OPTIONAL |
| E3 when | **NOT PRESENT** | REQUIRED — `date` | NOT PRESENT |
| E4 why | REQUIRED — `Context` | REQUIRED — `Context and Problem Statement` | **REQUIRED — rationale is a first-class concept** |
| E5 evidence | OPTIONAL (implicit in `Context`) | OPTIONAL — `Decision Drivers`, `Considered Options`, `Pros and Cons` | OPTIONAL |
| E6 changed | OPTIONAL — `Status` = superseded, no link field | REQUIRED — `status`, cross-link by convention | OPTIONAL |
| E7 approved | **NOT PRESENT** | OPTIONAL — `consulted`, `informed` (RACI-style) | OPTIONAL |
| E8 affected | OPTIONAL — `Consequences` | OPTIONAL — `Consequences`, `More Information` | **REQUIRED (structurally)** — traceable to affected views/entities |

| **18. Memory Seed** | ADRs are the closest existing convention to what Memory Seed does, which makes this simultaneously the strongest validation and the strongest competitive warning. The empirical adoption-decay finding is the important one: **the problem is not that teams lack a template, it is that they stop using it.** A substrate that captures decisions as a byproduct of work rather than as a separate authoring ritual addresses the actual failure mode. |
| **19. SWOT** | **S**: append-only supersession is a Constitution invariant, not a convention — enforced by `links check`. **W**: no approval field, matching Nygard's gap. **O**: ISO/IEC/IEEE 42010's E8 requirement (traceability to affected entities) is under-served by both lightweight templates. **T**: MADR is free, adequate for most teams, and "just use Markdown files" is a real competitor. |

**Status verified 2026-08-01:** MADR **4.0.0**, released 2024-09-17 `[primary, GitHub releases]` —
notable field changes in 4.0: "Validation" renamed `Confirmation`, "Deciders" renamed
`Decision Maker(s)`. **ISO/IEC/IEEE 42010:2022** is the current 2nd edition, replacing the 2011 first
edition. ThoughtWorks Radar last placed Lightweight ADRs at **Adopt in May 2018** and they are **not on
the current (2025) Radar editions** — retired from tracking rather than demoted `[primary]`.

#### 5.14 OpenTelemetry

Governed by the **CNCF** via its Governance and Technical Committees. Not a compliance standard — no
certification of adopting organisations exists. Dimensions 8 and 10 are **not applicable**, though for a
different reason than ADR: OTel has real governance, just no audit regime.

| Dim | Finding |
|---|---|
| 1–2. Purpose | A single vendor-neutral standard (API, SDK, OTLP protocol, semantic conventions) for generating and exporting telemetry, eliminating per-vendor instrumentation lock-in. Formed from the OpenTracing + OpenCensus merger. `[primary, CNCF]` |
| 11. Pain points | Uneven per-language signal maturity; **semantic-convention churn** — HTTP conventions changed meaning between v1.20.0 and stable v1.23.0, requiring an opt-in migration flag (`OTEL_SEMCONV_STABILITY_OPT_IN`) so adopters could phase attribute names rather than break dashboards `[primary]`; GenAI and messaging conventions remain at Development status. |
| 16. Knowledge management | Semantic conventions are, in effect, a **controlled vocabulary** for describing system behaviour consistently across teams and tools — a KM artefact in the taxonomy sense, not the rationale sense. |
| 17. Decision traceability | **Indirect and narrow.** OTel records *system behaviour*, not *human decisions*. Its relevance is as a plausible **E5 (evidence) source** feeding other frameworks' decision records — "this decision's consequences were validated by observing X in production traces." |
| **E-spine** | **Not applicable.** OTel has no decision, rationale, or approval fields. Span timestamps and resource attributes could serve as raw E3/E8 evidence inside some other process. |
| **18–19. Memory Seed** | The honest read: OTel is an **integration target and an evidence source, not a governance overlap**. Its real lesson for Memory Seed is the semantic-convention model itself — a versioned controlled vocabulary with an explicit, opt-in migration path for breaking changes, which is directly relevant to how `topics.yaml` and the link-edge grammar evolve. |

**Status verified 2026-08-01:** Specification **1.59.0** (2026-07-10). **CNCF Graduated 2026-05-11**.
Per-signal stability from NIST-equivalent authority — the project's own status page: traces Stable;
metrics API Stable / SDK mixed; logs Stable; baggage Stable; **profiles Development**. `[primary]`
Practitioner blogs describing profiles as "release candidate" or "stable" **contradict the official
status page**; the status page is authoritative.

### Family E — Privacy

#### 5.15 EU GDPR — Regulation (EU) 2016/679

| Dim | Finding |
|---|---|
| 4. Size | The **Art. 30(5) derogation** (fewer than 250 employees) is far narrower than commonly believed: it falls away if processing is not occasional, is likely to risk rights and freedoms, or includes special-category data. Routine HR and employee health data typically disqualifies it, so **most SMEs maintain records anyway.** `[primary]` |
| 5. Owner | **DPO mandatory** under Art. 37(1) where processing is by a public authority; or core activities involve large-scale regular systematic monitoring; or large-scale special-category/criminal-offence data. Otherwise privacy counsel and business-unit data owners; ultimate accountability sits with the controller and is formally undelegable under Art. 5(2). |
| 6–7. Evidence / documentation | Art. 30 records; DPIAs (Art. 35); legal-basis documentation (Art. 6/9); DSR logs (Arts. 12–22); breach register (Art. 33(5)); processor contracts (Art. 28); transfer mechanisms (Ch. V); Art. 32 technical measures. |
| **The key clause** | **Art. 5(2) accountability**: the controller *"shall be responsible for, and be able to demonstrate compliance with"* the principles. This is a **documented-reasoning obligation, not a documented-outcome one.** `[primary]` Reinforced by Art. 35(7)(b), which requires a DPIA to contain *"an assessment of the necessity and proportionality of the processing operations in relation to the purposes"* — reasoning, in the statutory text. |
| 8. Enforcement | Independent supervisory authorities (Art. 51) with Art. 58 powers including audit orders; **one-stop-shop** (Art. 56) via a lead authority; **EDPB consistency mechanism** (Arts. 63–65) with binding decisions. |
| 9. Cost | `[estimate/unsourced]` Figures come from privacy-tech vendors and consultancies with a commercial interest in reporting high burden. No authoritative government figure exists. |
| 10. Non-compliance cost | `[primary, Art. 83]` **€20m / 4%** (principles, data-subject rights, transfers); **€10m / 2%** (controller/processor obligations including Arts. 25, 28, 30, 33–34). Largest to date: **Meta Platforms Ireland — €1.2 billion**, Irish DPC following EDPB Binding Decision 1/2023, for Chapter V transfer violations `[primary, EDPB]`. |
| 14. AI relevance | Art. 22 governs solely-automated significant decisions; DPIAs commonly required for AI profiling; **EDPB Opinion 28/2024** (17 Dec 2024) addresses AI model anonymity, legitimate interest for training, and — significantly — the downstream effect of unlawful training-data processing, potentially requiring retraining or deletion `[primary]`. GDPR applies **in parallel** to the AI Act; the AI Act does not disapply it. |
| 16–17. KM / traceability | **The single most explicit documented-*reasoning* obligation in the landscape.** Art. 5(2) requires the controller to reconstruct and demonstrate the *why* behind processing decisions on demand. |
| **E-spine** | E1 R (30(1)(b), 35(7)(a)) · E2 R · E3 R (33(1) 72-hour clock) · E4 **R (5(2), 35(7)(b))** · E5 R (35(7)(c)) · E6 I (24(1), 35(11)) · E7 R (35(2) DPO advice, 36 prior consultation) · E8 R (30(1)(c)–(g)) — **7 REQUIRED** |
| **18. Memory Seed** | Art. 5(2) is philosophically the closest any law comes to Memory Seed's own thesis: *files are authority for what is true now, memory is authority for why.* But the record in question is a processing record owned by privacy counsel, not an engineering decision record — the affinity is conceptual, and the buyer is different. |
| **19. SWOT** | **S**: reason-with-decision is structurally native; legitimate-interest and DPIA balancing tests are exactly "record the reasoning." **W**: no approval field for Art. 35(2)/36; no data-subject or processing-purpose model. **O**: Art. 25 data protection **by design** is an engineering-time obligation currently served by no engineering-side tool. **T**: OneTrust/TrustArc own this buyer; and this is legal work, where being wrong is expensive. |

**Status verified 2026-08-01:** GDPR unchanged as adopted law. The **Digital Omnibus** proposal of
19 Nov 2025 — which would raise the Art. 30(5) threshold from 250 to **750** employees — remains
**PROPOSED, NOT ADOPTED**, still in Parliament/Council negotiation. The EDPB/EDPS joint opinion of
9 July 2025 questioned the 750 figure's justification. `[primary, EDPB]` **Do not treat it as law.**

#### 5.16 UK Data Protection Act 2018 / UK GDPR

| Dim | Finding |
|---|---|
| Structure | UK GDPR (retained EU law) + DPA 2018 (law-enforcement and intelligence processing, derogations), **as amended by the Data (Use and Access) Act 2025**. |
| **Key divergence** | DUAA Schedule 6 **replaced UK GDPR Art. 22 with new Arts. 22A–22D**, in force since **5 February 2026** (SI 2026/82). The default flips from *prohibited-unless-exception* to **permitted-subject-to-safeguards** for significant automated decisions on non-special-category data. Art. 22C safeguards: pre-decision transparency, right to human review, right to contest. Special-category automated decisions still require explicit consent or a substantial-public-interest condition. **This is a genuine, live divergence from EU GDPR, whose Art. 22 is unchanged.** `[secondary — multiple consistent law-firm sources; the consolidated legislation.gov.uk text of Arts. 22A–D was not independently pulled]` |
| Art. 30 | UK retains the **250-employee** threshold; the EU's proposed 750 has no UK counterpart. |
| Enforcement | ICO, transitioning to an **Information Commission** (corporate body) under DUAA Part 5. **No one-stop-shop or EDPB mechanism** post-Brexit — enforcement is unilateral. Appeals: First-tier Tribunal → Upper Tribunal → Court of Appeal. |
| Penalties | £17.5m / 4% upper tier; £8.7m / 2% lower `[secondary]`. Named actions: **23andMe — £2.31m** (5 June 2025, genetic data, credential-stuffing breach) `[primary, ICO penalty notice]`; **Clearview AI — £7,552,800** (jurisdiction upheld by Upper Tribunal 7 Oct 2025, merits remitted) `[primary, ICO]`; **MediaLab/Imgur — £247,590** (Feb 2026, children's privacy) `[primary, ICO]`. |
| 13. Automation | A UK-specific opening: **Art. 22C safeguards documentation is a brand-new (Feb 2026) obligation with no legacy tooling built around it** — transparency-notice generation, human-review request tracking, contest-outcome logging. |
| **E-spine** | As EU GDPR (7 REQUIRED), **plus** Art. 22A–D adding required identification of significant automated decisions, human-review evidence, and pre-decision timing. |
| **18–19. Memory Seed** | The Art. 22C human-review record is the most interesting privacy-side hook in either jurisdiction: a per-decision record of what was decided, whether a human reviewed it, and the outcome of any contest. **S**: decision-level granularity is native. **W**: no human-in-the-loop or contest-status model. **O**: no incumbent tooling yet. **T**: this is a narrow, jurisdiction-specific obligation, and dual UK/EU divergence is a compliance-team problem, not an engineering one. |

**UK adequacy:** the Commission **adopted renewal decisions 19 December 2025**, extending UK adequacy to
**27 December 2031** — a six-year renewal with a sunset clause, the UK remaining the only adequacy partner
subject to one, with Commission power to suspend if standards diverge `[primary, European Commission]`.
Given the Art. 22 divergence above, that suspension power is not merely theoretical.

#### 5.17 HIPAA

| Dim | Finding |
|---|---|
| 3. Scope | **Covered entity** = health plan, health care clearinghouse, or health care provider transmitting health information electronically in a covered transaction (45 CFR §160.103). **Business associate** = performs functions for a covered entity involving PHI; directly liable for the Security Rule since HITECH/Omnibus. `[primary]` |
| 4. Thresholds | **No revenue or size threshold** — applicability turns entirely on function, reaching solo practitioners through national systems and all their vendors and subcontractors. |
| 5. Owner | HIPAA **requires two named roles**: a **Privacy Official** (§164.530(a)(1)(i)) and a **Security Official** (§164.308(a)(2), a *required* not addressable specification). They may be the same person; the function is mandatory. `[primary]` |
| 7. Required documentation | §164.308 administrative safeguards (risk analysis, risk management, sanctions, activity review, training, incident procedures, contingency plan, evaluation); §164.312 technical safeguards; **§164.316 policies, procedures, and documentation with the six-year retention rule**; §§164.404–414 breach notification. |
| **The key clause** | **§164.306(d)(3)(ii)(B)** — where an *addressable* implementation specification is not implemented, the entity must *document why it would not be reasonable and appropriate*, and implement an equivalent alternative measure if reasonable and appropriate. `[primary]` **This is the most explicit decision-rationale requirement in any framework studied**: a decision, its recorded justification, and its alternative — required by regulation. Paired with §164.316(b)(2)(i): retain *"for 6 years from the date of its creation or the date when it last was in effect, whichever is later."* `[primary]` And §164.316(b)(2)(iii): review periodically and update in response to environmental or operational changes. |
| 8. Enforcement | OCR complaint investigations, compliance reviews, and a periodic audit program. Outcomes: technical assistance → Corrective Action Plan + Resolution Agreement (monitored 1–3 years) → Civil Money Penalty after an ALJ hearing. Criminal referrals to DOJ under 42 U.S.C. §1320d-6. |
| 10. Non-compliance cost | **Current inflation-adjusted tiers, effective 2026-01-28** `[primary, 45 CFR §102.3, FR Doc. 2026-01688]`: Tier (i) unknowing $145–$73,011; (ii) reasonable cause $1,461–$73,011; (iii) willful neglect corrected $14,602–$73,011; (iv) willful neglect uncorrected $73,011–$2,190,294. Calendar-year cap $2,190,294. **However**, OCR has since 2019 exercised enforcement discretion applying lower annual caps ($25,000/$100,000/$250,000 for tiers i–iii) — a policy position, not the regulatory cap `[secondary]`. |
| 14. AI relevance | **No HIPAA-specific AI regulation exists.** Clinical AI is governed only through the general Security/Privacy Rule lens — any tool creating, receiving, maintaining, or transmitting ePHI is a business associate or an in-scope internal system. A notable contrast with California's ADMT regime. |
| 16–17. KM / traceability | §164.316(b) mandates written policies plus a written record of required actions and assessments, retained six years, reviewed and updated — an explicit KM and version-control obligation. |
| **E-spine** | E1 R (306(d)(3)) · E2 I · E3 R (316(b)(2)(i)) · E4 **R (306(d)(3)(ii)(B)(1))** · E5 R (308(a)(1)(ii)(A) risk analysis) · E6 R (316(b)(2)(iii)) · E7 I · E8 R — **6 REQUIRED** |
| **18. Memory Seed** | The addressable-specification decision log is, structurally, an ADR: a decision not to do the default thing, the reason, and what was done instead — retained six years and reviewed on change. If Report 3 needs one concrete, citable, non-speculative regulatory demand that Memory Seed's existing shape already satisfies, this is the strongest candidate in the entire landscape. |
| **19. SWOT** | **S**: D/R/A is almost literally the §164.306(d)(3) shape; append-only + `evolves` matches the 6-year retain-and-review rule. **W**: no approval field; healthcare buyers demand BAAs and vendor assurance a local-first OSS tool does not obviously provide. **O**: the pending Security Rule NPRM would *eliminate the addressable category* — see below. **T**: healthcare sales cycles; the market is served by dedicated HIPAA compliance vendors. |

**Status verified 2026-08-01:** the **HIPAA Security Rule NPRM remains PROPOSED, not final.** Published
6 January 2025, comment period closed 7 March 2025 with ~4,745 comments. HHS signalled possible
finalisation around May 2026; that date passed. Per secondary reporting on the Unified Agenda (RIN
0945-AA22), anticipated final action has moved to **July 2027** `[secondary]`. **The 2013 Omnibus-era
Security Rule, including the required/addressable structure at §164.306(d), remains in force.** Note the
strategic implication: the NPRM proposes eliminating the addressable category, which would remove the
very clause that makes HIPAA the strongest decision-rationale mandate in this report.

#### 5.18 CCPA as amended by CPRA

| Dim | Finding |
|---|---|
| 3–4. Thresholds | For-profit businesses doing business in California meeting **any one** of: >$25m gross annual revenue; buying/selling/sharing PI of 100,000+ California consumers or households; or ≥50% of revenue from selling/sharing PI. `[primary, California AG]` |
| 5. Owner | **No statutorily required officer**, unlike HIPAA. Convention: CPO, DPO, or privacy counsel. The CPPA is the state's dedicated regulator, separate from any internal role. |
| 7. Required documentation | Cal. Civ. Code §1798.100 et seq.; **11 CCR §§7150–7157** (risk assessments — triggers, required content, CPPA submission and attestation); **ADMT regulations** (one source cites §§7200–7222, another §§7220–7222 — **this discrepancy was not resolved** `[secondary, unresolved]`); **§§7120–7124** (cybersecurity audits). |
| 8. Enforcement | Dual: the California AG (with local DAs) and the CPPA (administrative). **CPRA eliminated the mandatory 30-day cure period**; cure is now discretionary. A narrow 30-day cure survives only for the limited private right of action for data breaches under §1798.150. `[primary, California AG]` |
| 10. Non-compliance cost | $2,663 per violation; $7,988 per intentional violation or one involving a minor under 16 (adjusted, effective 2025-01-01) `[secondary, CPPA announcement]`. Private right of action: up to $750 per consumer per incident `[primary, AG]`. **Largest to date: General Motors — $12.75 million**, announced 2026-05-08 by AG Bonta with county DAs and CPPA support, over sale of location and driving data to brokers, **subject to court approval** `[primary, oag.ca.gov]`. Also Disney $2.75m (Feb 2026), Healthline $1.55m (Jul 2025), Honda $632,500, Ford $375,703. |
| 14. AI relevance — **ADMT** | **The deepest AI intersection of any privacy law in scope.** Businesses using automated decision-making technology for a "significant decision" (credit, employment, housing, insurance, education) must: give **pre-use notice**; provide on request a **meaningful explanation including the factors that influenced the decision**; and offer an **opt-out or human-review alternative**. A risk assessment must be completed **before deploying** qualifying ADMT, and from 2028 attested to the CPPA **under penalty of perjury**. Procedurally more prescriptive than HIPAA's silence on AI. `[secondary, convergent across White & Case, Skadden, Alston & Bird, Wiley, Coblentz]` |
| 15. Engineering | Any team building scoring, ranking, screening, or eligibility features for a covered business must build the ADMT notice/explanation/opt-out UX **and the underlying explainability and logging infrastructure** as compliance-critical, with risk-assessment documentation as a **design-time gate, not an after-the-fact audit artefact**. |
| **E-spine** | E1 R · E2 I · E3 I · E4 R · E5 R · E6 I · E7 I · E8 R — **4 REQUIRED** `[secondary — the operative regulatory text was not verified verbatim]` |
| **18. Memory Seed** | "Risk assessment completed before deployment, identifying the processing, its purpose, the anticipated benefit, the identified risk, and the mitigation" is a decision record with rationale and evidence, gated at design time and attested later. The 2027–2030 phased calendar means this obligation is arriving, not arrived. |
| **19. SWOT** | **S**: design-time decision capture with rationale is native. **W**: no attestation, consumer, or ADMT-explanation model. **O**: brand-new obligation, no legacy tooling, phased dates give lead time. **T**: California-only; the buyer is privacy counsel; and OneTrust et al. will build ADMT modules. |

**Status verified 2026-08-01:** the ADMT / risk-assessment / cybersecurity-audit regulations are **FINAL**
— approved by the California Office of Administrative Law **23 September 2025**, operative **1 January
2026**, with phased compliance: **ADMT from 2027-01-01**; initial risk assessments for continuing
pre-2026 processing by **2027-12-31**; CPPA attestation from **2028-04-01** then annually; cybersecurity
audits phased **2028-04-01** (>$100m revenue), **2029-04-01** ($50–100m), **2030-04-01** (<$50m).
`[secondary, convergent across five named law firms]` An automated extraction from the CPPA's own
approved text returned internally inconsistent 2025 dates that predate the regulation's own approval;
those were discarded as extraction artefacts.

### Family F — Engineering Governance

#### 5.19 ITIL

| Dim | Finding |
|---|---|
| **Critical distinction** | **ITIL certifies people, not organisations.** PeopleCert administers individual exams (Foundation → Specialist → Strategic Leader). There is **no ITIL-certified organisation status**. A company claiming to be "ITIL-certified" either means its staff hold individual certificates, or it holds **ISO/IEC 20000** — a genuine org-level ITSM certification from accredited CBs, not from PeopleCert. `[primary]` |
| 3–4. Industries / size | Financial services, telecom, government, healthcare, retail, MSPs. Skews mid-to-large because it presumes distinct roles (service desk, change authority, problem manager) that only exist at scale. `[estimate]` |
| 9–10. Cost | `[estimate, training-provider sourced]` Individual Foundation training + exam commonly $500–1,500 per person. Org-wide cost is dominated by ITSM tool licensing, not ITIL itself. No statutory penalty; indirect cost is outages from poor change control and contractual SLA breach. |
| 11. Pain points | The v3-era over-centralisation criticism — *"every change had to go to the CAB"* — which ITIL 4 explicitly addressed via the decentralised Change Authority concept; perceived bureaucracy for smaller orgs; the certification-vs-competency gap inherent in a person-certification model. |
| 12. Software | ServiceNow, BMC Helix, Ivanti Neurons, Jira Service Management, Freshservice. |
| 16. Knowledge management | **ITIL 4 has an explicit Knowledge Management practice** — *"maintain and improve the effective, efficient and convenient use of information and knowledge across the organization"* — with named information-quality attributes: available, accurate, reliable, relevant, complete, timely, compliant. It is among the practices most commonly prioritised alongside incident, change, and problem management. `[secondary, itsm.tools summary of official practice guides]` **This is the most direct KM mandate of any framework in the report.** |
| 17. Decision traceability | **Change enablement is ITIL's decision-traceability backbone**: every significant change requires a **Change Record** (who requested, what, why, risk assessment) authorised by a **Change Authority** — a named person, team, board, or automated policy, explicitly decentralised in ITIL 4. |
| **E-spine** | E1 R · E2 R · E3 I · E4 R · E5 I · E6 R · E7 R · E8 R (CMDB linkage) — **6 REQUIRED** |
| **18. Memory Seed** | The explicit KM practice plus the change record is the strongest combination in this family. But ITSM is a ServiceNow-shaped market with a service-desk buyer, and the change record already lives in the ITSM tool. |
| **19. SWOT** | **S**: change record = decision + reason + affected scope, natively. **W**: **no change-authority/approval field** — the one thing ITIL most insists on. **O**: ITIL v5's AI-enabled framing (Feb 2026) is a re-evaluation moment. **T**: ServiceNow owns this; ITIL has no org-level audit to sell evidence into. |

**Status verified 2026-08-01:** ITIL is owned by **PeopleCert**, which completed its acquisition of AXELOS
on 21 June 2021 (£380m, from the Cabinet Office/Capita joint venture) `[primary]`. **ITIL Version 5
launched 12 February 2026** in a phased rollout, positioned around AI-enabled contexts and a unified
Product and Service Lifecycle Model `[primary, PeopleCert]`.

#### 5.20 COBIT

| Dim | Finding |
|---|---|
| 1–2. Purpose | Framework for the **governance and management of enterprise I&T**, separating governance (Evaluate/Direct/Monitor — board level) from management (Plan/Build/Run/Monitor — operational). `[primary, ISACA]` |
| 3–4. Industries / size | Strongest in regulated sectors needing demonstrable IT governance: financial services, insurance, government, healthcare, and anywhere SOX-style IT general controls matter. **Large-enterprise by construction** — it presumes a governance layer distinct from management. ISACA publishes a dedicated **SME focus-area guide** precisely because the base framework is enterprise-scaled. `[primary]` |
| 6–8. Evidence / assessment | **No org-level COBIT certification.** Certification is individual (COBIT Foundation, COBIT Design & Implementation). Organisationally, assessment uses the **Goals Cascade + Design Factors** methodology and a capability assessment (ISO/IEC 15504-style levels 0–5 per objective), typically self- or consultant-led. **No ISACA-issued organisational rating** exists, unlike CMMI. `[primary + secondary]` |
| 7. Documentation | COBIT 2019 publication set: Framework (Introduction & Methodology; Governance & Management Objectives), **Design Guide**, **Implementation Guide**, plus focus-area guides (DevOps, Information Security, IT Risk, SME, NIST CSF mapping). `[primary]` |
| 9–10. Cost | `[estimate, training-provider sourced]` Foundation training ~$1,000–3,000 per person. Enterprise governance-system design cost `[unsourced]`, consultancy-dependent. No statutory penalty. |
| 11. Pain points | ISACA's own commentary cautions that *"RACI charts are not a substitute for accountability"* — implying a documented failure mode where COBIT artefacts become a checkbox. The 40-objective scope is hard to right-size for mid-market, which the SME focus-area guide implicitly concedes. |
| 15. Engineering | A dedicated **"COBIT Focus Area: DevOps Using COBIT 2019"** publication bridges governance objectives to engineering practice. `[primary]` |
| 16. Knowledge management | **Indirect** — COBIT governs decision *rights* about IT assets rather than prescribing a KM practice (unlike ITIL). |
| 17. Decision traceability | The **RACI matrix embedded in every governance and management objective** is purpose-built for decision-rights traceability, shipped by ISACA as a structured Excel toolkit. The **EDM domain** is definitionally about the board directing and monitoring management decisions. |
| **E-spine** | E1 I · E2 R (RACI Accountable) · E3 — · E4 I · E5 I · E6 — · E7 R (RACI Accountable = approver) · E8 I — **2 REQUIRED** |
| **18. Memory Seed** | COBIT answers **E2 and E7 better than almost anything else** — decision rights and accountability are its entire subject — while answering E1/E4/E6 barely at all. It is the mirror image of Memory Seed's own profile, which is strong on what/why/changed and weak on who-approved. That complementarity is analytically interesting and commercially unpromising: the buyer is the board, the artefact is a RACI chart, and the delivery vehicle is a consultancy engagement. |
| **19. SWOT** | **S**: none strong. **W**: no RACI or decision-rights model at all. **O**: the DevOps focus area is the only engineering-adjacent surface. **T**: Big-4 consultancy-mediated; enterprise-only; no audit to supply evidence to. |

#### 5.21 CMMI

| Dim | Finding |
|---|---|
| 1–2. Purpose | Process-improvement and capability-benchmarking model, originally built so US DoD acquisition could objectively evaluate contractor process capability before award. |
| 3. Industries | Defence/aerospace (historic core), IT services and outsourcing (especially offshore delivery organisations proving maturity to Western clients), automotive. V3.0 expanded to eight domains: Development, Services, Supplier Management, Safety, Security, plus new **Data, People, Virtual**. `[primary, ISACA]` |
| 4. Size | Large/enterprise. Appraisals require a formal team and multi-week engagements with published organisational-unit scope — only large delivery organisations with dedicated process groups typically justify it. `[estimate]` |
| 6. Required evidence | **The most evidence-hungry framework in the report.** Benchmark appraisals require direct-artefact and affirmation evidence for every in-scope practice area across multiple sampled projects: project plans, risk registers, measurement repositories, **decision records with documented alternatives and evaluation criteria**, tailoring records, defect logs, training records, CM logs, plus practitioner and management interviews. `[secondary — the appraisal MDD is paywalled]` |
| 8. Appraisal | Governed by **ISACA** via the **CMMI Institute**. **CMMI V3.0** released 6 April 2023; V2.2 retired June 2024; only V3.0 appraisals accepted since 1 Jan 2024. The historic **SCAMPI** naming is superseded by: **Benchmark Appraisal** (formal rating, **valid 3 years**), **Sustainment Appraisal** (reduced scope, extends a rating, max 3 consecutive), **Evaluation Appraisal** (unrated, internal), **Action Plan Reappraisal**. Led by a certified **Lead Appraiser**. Results published in **PARS**. Dual **Maturity Level (1–5, staged)** and **Capability Level (per practice area, continuous)** structure retained; **31 practice areas — 17 core + 14 domain-specific**. `[secondary — cmmiinstitute.com returned 403]` |
| 9–10. Cost | `[estimate, consultancy-sourced]` Implementation plus Benchmark appraisal commonly reported in the tens of thousands to low hundreds of thousands USD, all from firms selling appraisal-preparation services. **No statutory penalty**; the real cost is **contract ineligibility**, historically in US defence acquisition where maturity ratings gate RFP eligibility. Current 2026 applicability `[estimate]` — not re-verified against a live DoD acquisition policy. |
| 11. Pain points | The heaviest documentation burden of the three engineering-governance frameworks. The phrase *"appraisal theatre"* — optimising to pass rather than to improve — is widely circulated but **could not be sourced to a specific citation** and is marked `[unsourced]`; the underlying documentation-burden concern is corroborated by CMMI Institute's own appraisal-preparation checklists. |
| **The key practice area** | **Decision Analysis and Resolution (DAR)** — requires establishing guidelines for which decisions need formal evaluation, **defining and recording alternatives**, **developing explicit evaluation criteria**, evaluating and selecting against those criteria, and **recording the outcome**. `[primary, ISACA's own DAR Tech Talk module]` **This is the closest thing to a mandated ADR in any institutional framework studied.** |
| 16. Knowledge management | Weak relative to ITIL — Organizational Process Focus and Organizational Training touch process-asset libraries and lessons-learned, but there is **no dedicated KM practice area**. |
| **E-spine** | E1 R (DAR) · E2 R · E3 I · E4 **R (DAR criteria + rationale)** · E5 R · E6 I · E7 R · E8 I — **5 REQUIRED** |
| **18. Memory Seed** | DAR is the single most Memory-Seed-shaped practice in the report: decision, recorded alternatives, explicit evaluation criteria, recorded outcome. That is **D / A / R / D** in DRAFT terms almost exactly. And unlike SOC 2 or CSF, the evidence is genuinely engineering-side and genuinely audited. The problem is the market: CMMI appraisals are a shrinking, defence-concentrated, consultancy-mediated business. |
| **19. SWOT** | **S**: DRAFT's `A` (Alternatives) field exists in almost no other tool and is a DAR requirement. **W**: no evaluation-criteria model; no appraisal-evidence packaging. **O**: appraisal evidence assembly is manual and painful, and V3.0's new **Data** domain is unclaimed. **T**: CMMI is a declining framework outside defence and offshore IT services; appraisal-driven demand is lumpy and consultancy-owned. |

---

## 6. Opportunity matrix

Scored on the evidence gathered above. **Evidence demand** = how much decision-rationale the framework
actually requires. **Automation gap** = how poorly incumbent tooling serves that specific requirement.
**Buyer proximity** = how close the budget holder is to an engineering organisation. **Urgency** = whether
a live deadline or enforcement action forces action.

| Framework | Evidence demand | Automation gap | Buyer proximity | Urgency | Read |
|---|---|---|---|---|---|
| **EU AI Act (Annex IV)** | Very high | High | Medium | **Reduced — deadline moved to Dec 2027** | Strongest thesis anchor; weakened timing |
| **ISO/IEC 42001** | Very high | High | Medium | Medium — market access | **Best combination in the report** |
| **CMMI DAR** | High | High | **High** | Low | Best structural fit, worst market |
| **HIPAA §164.306(d)(3)** | High | High | Low | Medium | Best single citable proof point |
| **ISO/IEC 27001 (SoA, A.8.32)** | High | Medium | Medium | Medium | Crowded by GRC incumbents |
| **ADR conventions** | Medium | **Very high** | **Very high** | **None** | Closest fit, no forcing function |
| **CCPA ADMT** | Medium | **Very high** | Medium | Rising (2027) | New, unclaimed, narrow |
| **UK GDPR Art. 22C** | Medium | **Very high** | Low | Live since Feb 2026 | New, unclaimed, very narrow |
| **FedRAMP / OSCAL** | Very high | Medium | Low | High | Validates thesis; brutal sales motion |
| **GDPR Art. 5(2) / Art. 25** | High | Medium | Low | Ongoing | Conceptually closest, wrong buyer |
| **ITIL change enablement** | Medium | Low | Medium | None | ServiceNow owns it |
| **SOC 2** | **Low (outcome-stated)** | Low | High | High | **Attractive but hollow — see §5.11** |
| **ISO 9001 (7.1.6)** | Medium | Medium | Low | Sept 2026 revision | Wrong buyer |
| **NIST AI RMF** | Medium (no fields) | **Very high** | Medium | **None** | Big surface, no budget |
| **NIST CSF 2.0** | **Very low** | n/a | Medium | None | **False opportunity** |
| **ISO 31000** | **None** | n/a | Low | None | **False opportunity** |
| **OECD AI Principles** | **None** | n/a | Low | None | **False opportunity** |
| **COBIT** | Low (E2/E7 only) | Low | Low | None | Mirror-image profile; wrong buyer |
| **ISO 56001** | Medium | High | Low | None | Greenfield, no market |
| **OpenTelemetry** | n/a | n/a | High | None | **Integration target, not a market** |

**Three candidate false opportunities identified for Report 3 to confirm or reject:** NIST CSF 2.0,
ISO 31000, and the OECD AI Principles — all have high conceptual affinity with decision governance and
**zero mandated record to attach evidence to.** SOC 2 is a fourth, subtler candidate: high apparent
attractiveness, but the TSC states outcomes rather than evidence requirements, and the automation market
is the most saturated in the landscape.

---

## 7. Status changes that post-date a May 2026 knowledge cutoff

Anyone reasoning about this landscape from memory rather than from sources will be wrong about these:

| # | Change | Date | Verification |
|---|---|---|---|
| 1 | **Reg. (EU) 2026/1744 "Digital Omnibus on AI"** defers Annex III high-risk to 2 Dec 2027, Annex I to 2 Aug 2028 | In force 2026-07-27 | `[primary, EUR-Lex]` |
| 2 | **ITIL Version 5** launched | 2026-02-12 | `[primary, PeopleCert]` |
| 3 | **OpenTelemetry graduated** to CNCF's highest maturity level | 2026-05-11 | `[primary]` |
| 4 | **CCPA ADMT/risk/cyber-audit regulations** operative, phased from 2027 | 2026-01-01 | `[secondary, convergent]` |
| 5 | **HIPAA CMP tiers** inflation-adjusted (cap $2,190,294) | 2026-01-28 | `[primary, Federal Register]` |
| 6 | **UK DUAA 2025** Part 5 in force; UK GDPR Arts. 22A–22D replace Art. 22 | 2026-02-05 | `[primary, SI 2026/82]` + `[secondary]` for article text |
| 7 | **UK EU-adequacy renewed** to 27 Dec 2031 | 2025-12-19 | `[primary, European Commission]` |
| 8 | **ISO 27001:2013 transition closed** — 2013-only certificates now invalid | 2025-10-31 | `[secondary, IAF MD 26 via CBs]` |
| 9 | **ISO 9001:2026** targeted for publication | 2026-09 | `[primary]` target, `[secondary]` FDIS status |
| 10 | **FedRAMP JAB dissolved**, FedRAMP Board established, 20x in Phase 3 | 2024–2026 | `[primary, GSA/fedramp.gov]` |

---

## 8. Glossary

| Term | Definition |
|---|---|
| **ADMT** | Automated Decision-Making Technology — California's regulatory term for systems making "significant decisions" about consumers. |
| **Annex SL** | ISO's harmonised high-level structure (clauses 4–10) shared by all modern management-system standards, enabling integration of 9001/27001/42001/56001. |
| **Annex IV** | The EU AI Act's enumeration of required technical documentation content — including design-choice rationale and lifecycle change records. |
| **AIMS** | AI Management System — the ISO/IEC 42001 equivalent of an ISMS. |
| **ATO** | Authority to Operate — a US federal agency's authorisation for a system to run. |
| **BAA** | Business Associate Agreement — HIPAA's mandatory contract between a covered entity and a vendor handling PHI. |
| **CAB** | Change Advisory Board — the ITIL v3 centralised change-approval body, decentralised into "Change Authority" in ITIL 4. |
| **CAPA** | Corrective and Preventive Action — the ISO 9001 nonconformity-response process. |
| **CB** | Certification Body — an accredited organisation that audits and issues management-system certificates. |
| **CMP** | Civil Money Penalty — HIPAA's formal fine mechanism, distinct from a settlement. |
| **ConMon** | Continuous Monitoring — FedRAMP's ongoing monthly evidence obligation post-authorisation. |
| **DAR** | Decision Analysis and Resolution — CMMI's practice area requiring recorded alternatives and evaluation criteria. |
| **DPIA** | Data Protection Impact Assessment — GDPR Art. 35 assessment required for high-risk processing. |
| **DPO** | Data Protection Officer — mandatory under GDPR Art. 37 in defined circumstances. |
| **EDM** | Evaluate, Direct, Monitor — COBIT's governance domain, distinct from its management domains. |
| **FRIA** | Fundamental Rights Impact Assessment — required of certain AI Act deployers under Art. 27. |
| **GPAI** | General-Purpose AI model — the AI Act's category for foundation models, with obligations from Aug 2025. |
| **IAF** | International Accreditation Forum — the body whose multilateral arrangement makes certificates mutually recognised. |
| **IAF MD** | IAF Mandatory Document — e.g. MD 5 (audit days), MD 26 (27001 transition), MD 29 (27006 transition). |
| **ISMS** | Information Security Management System — the thing ISO/IEC 27001 certifies. |
| **MADR** | Markdown Any Decision Records — the most widely used structured ADR template; currently v4.0.0. |
| **NPRM** | Notice of Proposed Rulemaking — a US proposed regulation, **not law until finalised**. |
| **OSCAL** | Open Security Controls Assessment Language — NIST's machine-readable format for control/assessment data, central to FedRAMP 20x. |
| **PARS** | Published Appraisal Results System — the public registry of CMMI appraisal ratings. |
| **PHI / ePHI** | Protected Health Information (electronic) — HIPAA's regulated data category. |
| **POA&M** | Plan of Action and Milestones — FedRAMP's tracked remediation commitment register. |
| **Presumption of conformity** | AI Act Art. 40 mechanism whereby applying an OJ-cited harmonised standard is presumed to satisfy the legal requirement. |
| **SoA** | Statement of Applicability — ISO/IEC 27001's per-control decision record with mandatory justification for inclusion and exclusion. |
| **SSP** | System Security Plan — FedRAMP's control-by-control implementation document. |
| **TEVV** | Test, Evaluation, Verification, and Validation — NIST AI RMF's term for AI assurance activity. |
| **3PAO** | Third-Party Assessment Organization — FedRAMP's accredited independent assessor. |
| **TSC** | Trust Services Criteria — the AICPA criteria SOC 2 reports against. |
| **Addressable (HIPAA)** | An implementation specification that may be declined **if the reason is documented** and an equivalent alternative implemented — as opposed to "required." |

---

## 9. Required reading — primary sources

Ranked by ratio of insight to effort. **Tier 1 is free, authoritative, and directly readable.**

### Tier 1 — read these first (all free)

1. **EU AI Act, Annex IV and Articles 11, 12, 17, 18, 26, 43, 72, 99** — [EUR-Lex 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng). The single most decision-record-dense legal text in existence. Read Annex IV in full; it is short.
2. **Regulation (EU) 2026/1744, "Digital Omnibus on AI"** — [EUR-Lex 2026/1744](https://eur-lex.europa.eu/eli/reg/2026/1744/oj/eng). What changed, five days ago.
3. **NIST AI RMF 1.0** — [NIST AI 100-1](https://doi.org/10.6028/NIST.AI.100-1). Free, readable, and the clearest example of outcome-stated rather than record-mandated governance. Read §5 (the four functions) and Appendix D (design attributes).
4. **NIST CSF 2.0** — [NIST.CSWP.29](https://doi.org/10.6028/NIST.CSWP.29), plus the machine-readable Core at `csrc.nist.gov/extensions/nudp/services/json/csf/download`. Read the GOVERN function.
5. **45 CFR §164.306(d) and §164.316** — the addressable-specification decision-rationale rule and the six-year retention rule. Two short sections; the highest-value citation in the report.
6. **GDPR Art. 5(2), Art. 30, Art. 35** — [EUR-Lex 2016/679](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679). Accountability as a documented-reasoning obligation.
7. **NIST SP 800-53 Rev 5, CM-3, CM-4, CA-5, CA-6** — free, public domain, and the cleanest procedural drafting of change rationale and authorisation anywhere.
8. **Michael Nygard, "Documenting Architecture Decisions" (2011)** — [cognitect.com](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions). ~800 words. The origin of the whole convention.
9. **MADR 4.0.0 template** — [github.com/adr/madr](https://github.com/adr/madr). Read the template file itself, not the docs.
10. **AWS Prescriptive Guidance on ADRs** and **Azure Well-Architected: Architecture decision record** — the two clearest statements of the append-only supersession model.

### Tier 2 — governing-body pages for status verification

11. **ISO committee pages** — [TC 176/SC 2](https://committee.iso.org/sites/tc176sc2/) (ISO 9001 revision), [TC 262](https://committee.iso.org/sites/tc262/home/projects.html) (ISO 31000 revision), [TC 279](https://committee.iso.org/sites/tc279) (innovation). **These are reachable when iso.org itself is not.**
12. **FedRAMP 20x** — [fedramp.gov/20x](https://www.fedramp.gov/20x/). The live program state and the OSCAL direction.
13. **AICPA SOC suite landing page** — [aicpa-cima.com](https://www.aicpa-cima.com/resources/landing/system-and-organization-controls-soc-suite-of-services). Note the 2026 auditor-independence warning.
14. **CPPA regulations** — [cppa.ca.gov/regulations](https://cppa.ca.gov/regulations/). The ADMT rules and their phased dates.
15. **EDPB Opinion 28/2024** on AI models — the current European position on model anonymity and training-data lawfulness.
16. **ISO/IEC/IEEE 42010:2022** — the only formal standard that treats architecture-decision *rationale* as a first-class concept.

### Tier 3 — paywalled, buy only if a specific decision depends on it

17. **ISO/IEC 42001:2023** + **ISO/IEC 42005:2025** (impact assessment) — buy if the AI-governance direction is pursued seriously. Everything in §5.7 above is `[secondary]` and should be verified before it is relied on.
18. **ISO/IEC 27001:2022** + **Amd 1:2024** — buy if the security direction is pursued. Same caveat.
19. **CMMI V3.0 model** and the appraisal Method Definition Document — buy only if DAR is being targeted specifically.

---

## 10. Ranked secondary sources

| Rank | Source | Why | For whom |
|---|---|---|---|
| 1 | **Buchgeher et al., "Using ADRs in Open Source Projects — An MSR Study on GitHub," IEEE Access 2023** | The only empirical grounding for ADR adoption claims; ~50% of ADR-using repos have 1–5 records. Use this instead of blog anecdotes. | Anyone quoting ADR adoption statistics |
| 2 | **"Architecture Decision Records in Practice: An Action Research Study," ECSA 2024** | Counter-evidence: ADRs work when the operating model, not just the artifact, is adopted. | Anyone designing an ADR rollout |
| 3 | **"Why firms lose their ISO 9001 certification" / "Recovering a lost ISO 9001 certification"**, *Total Quality Management & Business Excellence* | The only peer-reviewed, non-vendor cost/consequence data found across 21 frameworks. | Anyone needing defensible non-compliance figures |
| 4 | **csf.tools** | Non-commercial mirror of NIST SP 800-53 and CSF control text; fast, machine-parseable. | Engineers needing exact control language |
| 5 | **CEN-CENELEC JTC 21 news pages** | The standards body's own account of AI Act harmonised-standard progress — effectively primary for process status. | Anyone tracking when Art. 40 presumption becomes available |
| 6 | **CSA research note on prEN 18286 vs ISO 42001** (2026-04-28) | The clearest explanation of why 42001 certification ≠ AI Act compliance. | Anyone conflating the two |
| 7 | **artificialintelligenceact.eu** (Future of Life Institute) | Article-by-article AI Act mirror with commentary; excellent navigation. **Always cross-check numbers against EUR-Lex** — this research pass found one automated summary of the Act producing entirely wrong fine figures. | Fast navigation into the Act's structure |
| 8 | **IAF (iaf.nu)** | The actual authority on certification transition deadlines (MD 5, MD 26, MD 29). Non-commercial. | Anyone needing precise transition dates |
| 9 | **Law firm client alerts** (Freshfields, Gibson Dunn, White & Case, Skadden, Alston & Bird, DLA Piper) | Fastest credible synthesis of new rules. **All have an advisory interest in flagging urgency**; cross-check article numbers against the primary text — this pass found an unresolved CCPA section-number discrepancy between two firms. | In-house legal needing a first-pass digest |
| 10 | **ITSM.tools** | Practitioner summaries of ITIL 4 practice guides without the PeopleCert paywall. | ITSM implementers |
| 11 | **IAPP** | Near-real-time privacy enforcement and legislative tracking. | DPOs and privacy counsel |
| 12 | **CMMI PARS registry** | Authoritative check on whether a claimed CMMI rating is genuine and current. | Procurement due diligence |
| — | **Compliance-automation vendor blogs** (Vanta, Drata, Secureframe, Sprinto, Thoropass) | Useful *only* as a map of the commercial landscape. Every cost figure they publish is lead generation for the remedy they sell. Named and flagged wherever used above. | Understanding the competitive field, not sourcing facts |

---

## 11. Recommended reading order

**If the goal is to understand the decision-governance thesis** (recommended, ~6 hours):
EU AI Act Annex IV → HIPAA §164.306(d)(3) → ISO 27001's SoA concept → CMMI DAR → NIST AI RMF §5 →
NIST CSF 2.0 GOVERN → Nygard → MADR 4.0.0 template → ISO/IEC/IEEE 42010's rationale concept.
This sequence moves from the most prescriptive record mandate to the least, then to the conventions that
tried to solve the same problem voluntarily. **The contrast is the insight.**

**If the goal is AI governance specifically** (~4 hours):
OECD AI Principles → NIST AI RMF → EU AI Act (Arts. 3, 11, 12, 17, 99 + Annex IV) → Reg. 2026/1744 →
prEN 18286 vs ISO 42001 (CSA note) → CCPA ADMT regulations → EDPB Opinion 28/2024.
Chronological and causal: values → voluntary framework → binding law → amendment → the standards gap.

**If the goal is to evaluate a market wedge** (~3 hours):
§6 opportunity matrix above → SOC 2 TSC (understand why it looks better than it is) → FedRAMP 20x/OSCAL
(understand what machine-readable governance evidence looks like when a government mandates it) →
the ADR adoption-decay study (understand why the obvious answer has already failed once).

**Do not start with** ISO 31000, the OECD Principles, or NIST CSF 2.0. They are the most pleasant to read
and the least consequential for this programme.

---

## 12. Method and limitations

**Method.** Nine parallel research agents covered the 21 frameworks, each instructed to verify every date
and status against the governing body's own page rather than recall, to map dimensions 6–7 onto the
eight-question spine with clause citations, and to mark unsourceable claims rather than guess. Every
load-bearing claim was then re-verified directly: EUR-Lex for Reg. 2026/1744; the AI Act's Art. 99 and
Art. 18; ISO committee pages for the 9001 and 31000 revisions; OpenTelemetry's status page; MADR's
release history; CEN-CENELEC on prEN 18286. Three agent self-corrections were caught and confirmed.

**Limitations, stated plainly:**

1. **No ISO clause text was read.** `iso.org` returned HTTP 403 to every automated fetch across three
   independent passes. All ISO clause numbers and control text here are `[secondary]` — cross-checked
   across multiple independent compliance sources, but not verified against ISO's own text. **Buy the
   standard before relying on any ISO clause citation in this report.**
2. **Cost data is not reliable.** See §4. No neutral benchmark exists for any framework.
3. **One unresolved citation conflict**: the CCPA ADMT regulations are cited as 11 CCR §§7200–7222 by one
   law firm and §§7220–7222 by another. Not resolved.
4. **One unverified date**: FedRAMP Ready's reported retirement (28 July 2026) — primary page 404s.
5. **UK GDPR Arts. 22A–22D** are described from consistent law-firm reporting; the consolidated statutory
   text was not pulled.
6. **Dimensions 18 and 19 are first-pass observations, not findings.** They were written against Memory
   Seed's documented capabilities (`.memory-seed/index.md`, `docs/CONSTITUTION.md`, `docs/3_Spec/`) but
   have not been tested against the code. Report 3 does that.

**Two capability gaps in Memory Seed were predicted before this research and are now confirmed by it.**
Across 21 frameworks, **E7 (who approved) is REQUIRED in 11** — and Memory Seed has no approval field at
all. `user_initials` records who a session was *for*, not who chose the values or authorised the change;
Constitution v1.6 says exactly this. **E8 (systems affected) is REQUIRED in 12**, and the `F:` (Files)
label is the nearest surface — file-level, not an asset or system inventory. These two gaps are the
highest-value input this report hands to Report 2.

---

*End of Report 1. Report 2 — the Decision Governance Evidence Spine — rolls up §3 and tests the product
thesis against it.*
