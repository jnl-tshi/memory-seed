---
title: "Decision Governance Evidence Spine Report"
date: "2026-08-01"
project: "memory-seed"
kind: "report"
next_action: "source-only"
author_context: "Prepared for Jean Nathan Tshibuyi (JNL). Report 2 of a seven-report research programme."
---

# Decision Governance Evidence Spine Report

**Report 2 of 7.** Tests one hypothesis: *governance frameworks converge on a common set of decision-evidence
requirements, and Memory Seed already answers a large proportion of them.*

**Verdict: the convergence is real and stronger than expected. The coverage claim is half right, and the half
that is wrong is the half that matters commercially.**

---

## Inputs and method

| Input | Role |
|---|---|
| [Report 1](standards-and-regulatory-landscape-report.md) §3 | The 21-framework spine crosswalk this report rolls up |
| `memory_seed/core.py`, `memory_seed/cli.py`, `memory_seed/topics.py` | Verified capture surface — every coverage claim below cites `file:line` |
| `memory-trace/memory_trace/evidence.py` | Evidence Pack surface |
| [`3_Spec/graph-edge-contract.md`](../../docs/3_Spec/graph-edge-contract.md) | Normative edge semantics |
| [`3_Spec/draft/adr-lifecycle-sidecar-contract.md`](../../docs/3_Spec/draft/adr-lifecycle-sidecar-contract.md) | **DRAFT — NOT IMPLEMENTED.** Cited as intent, never as capability |
| [`CONSTITUTION.md`](../../docs/CONSTITUTION.md) v1.6 | Invariant #4 on provenance; §9 five-question test |
| `.memory-seed/skills/session_logging.md` | DRAFT label contract |

**Coverage claims are verified against code, not specs.** Constitution Invariant #4: files are authority for
what is true now. Where a capability exists only in a draft spec, this report says so explicitly and scores it
as absent.

### What this report does not establish

- **It does not claim compliance with anything.** A field that answers an evidence question is not a control,
  and a record is not an audit.
- **It does not assess market, buyer, or competitor.** That is Report 3 and Report 6.
- **It does not propose features.** It identifies gaps; whether to close them is Report 7's call.
- **The coverage percentages in §5 are a field-shape metric, not a compliance score.** See the warning there.

---

## 1. The eight questions, and why these eight

The spine was fixed before research began, from JNL's own framing, and applied unchanged to all 21 frameworks:

| ID | Question | What it is really asking |
|---|---|---|
| E1 | What decision was made? | Is there an identifiable decision object at all? |
| E2 | Who made it? | Attribution — can a decision be traced to an actor? |
| E3 | When was it made? | Temporal ordering and evidentiary dating |
| E4 | Why was it made? | Rationale — the reasoning, not the outcome |
| E5 | What evidence supported it? | The evidentiary basis the reasoning rested on |
| E6 | What changed later? | Revision, supersession, lifecycle |
| E7 | Who approved it? | Authorisation — distinct from authorship |
| E8 | What was affected? | Scope — systems, assets, processes touched |

The instrument survived contact with the evidence. Every one of the 21 frameworks was expressible in it; none
required a ninth question. Two frameworks (OpenTelemetry, and ISO 27002 at document level) were N/A rather than
ill-fitting, which is a different result and is reported as such.

**E2 and E7 are separate questions and the distinction is load-bearing.** Authorship is who decided;
authorisation is who let it in. Frameworks that care about segregation of duties — SOC 2 CC8.1, FedRAMP CA-6,
ISO 27001 7.5.2, ITIL's Change Authority — care about the second, specifically because it is not the first.
This distinction is the single most consequential finding in the report.

---

## 2. Convergence — how strong is it really?

Aggregating Report 1 §3 across the 19 frameworks with a decision-record surface (excluding OpenTelemetry and
ISO 27002-at-document-level):

| Question | REQUIRED | IMPLIED | NOT REQUIRED / UNKNOWN | **Demand rank** |
|---|---|---|---|---|
| **E1** what decision | **13** | 6 | 0 | 1 |
| **E4** why | **12** | 7 | 0 | 2 |
| **E8** what affected | **11** | 6 | 2 | 3= |
| **E6** what changed | **11** | 7 | 1 | 3= |
| **E7** who approved | **10** | 7 | 2 | 5 |
| **E2** who made it | **9** | 10 | 0 | 6 |
| **E5** what evidence | **9** | 8 | 2 | 7 |
| **E3** when | **7** | 8 | 4 | 8 |

**Three findings.**

**(a) The convergence hypothesis is confirmed, and E4 is the surprise.** Every framework with a decision-record
surface demands E1 either explicitly or implicitly — no exceptions. **E4 (why) is REQUIRED in 12 of 19, second
only to the existence of the decision itself, and ahead of who, when, and who-approved.** Governance frameworks
are not primarily asking organisations to record *what they did*. They are asking them to record *why* —
because the outcome is usually observable from the system itself, and the reasoning is not.

This is the strongest available evidence for the product thesis, and it is worth stating in the frameworks'
own words:

- **EU AI Act, Annex IV §2(b):** *"the key design choices including the rationale and assumptions made"*
- **GDPR Art. 35(7)(b):** *"an assessment of the necessity and proportionality of the processing operations in
  relation to the purposes"*
- **HIPAA §164.306(d)(3)(ii)(B)(1):** document *why it would not be reasonable and appropriate* to implement
- **ISO 27001 6.1.3(d):** the Statement of Applicability's justification for inclusion *and exclusion*
- **CMMI DAR:** recorded alternatives evaluated against explicitly recorded criteria

Five independent bodies, three legal systems, four decades of drafting, all converging on: *record the reason.*

**(b) But E3 (when) ranks last, which discredits the naive reading.** If frameworks simply wanted a complete
audit record they would demand timestamps universally — timestamps are trivially cheap. They do not. What they
demand is the expensive, judgment-bearing content: what, why, what changed, what was affected, who authorised.
**The convergence is on the parts that cannot be automatically derived from a system's own behaviour.** That
is a much more interesting result for a decision-memory product than "everyone wants an audit log," and it is
the reason telemetry (OpenTelemetry) does not compete here: telemetry answers when and what-happened cheaply,
and cannot answer why at all.

**(c) The split is drafting style, not rigour.** Report 1 established this and the rollup confirms it:
frameworks that mandate a *record* score 6–8 REQUIRED; frameworks that state *outcomes* score 0–2. The
underlying evidence appetite is similar; what differs is whether the drafters wrote a schema. **A framework
scoring low on this spine is not a framework that does not care — it is a framework that left the record
design to the implementer.** Those are the frameworks where a substrate has the most to offer and the least
purchase, a tension Report 3 must resolve.

---

## 3. What Memory Seed actually captures

Verified against the code on branch `claude/standards-regulatory-research-853c9c` at `0c5734d`.

### E1 — What decision was made · **STRONG**

`D:` is a mandatory DRAFT label. Enforcement is real, not conventional: `entry_body_format_issues()`
(`memory_seed/core.py:1671-1708`) refuses the write when the body is malformed, and `session_append_entry()`
(`core.py:3550-3551`) calls it before writing. Decisions are individually addressable as `(entry_id, dN)`,
derived from heading structure by `_entry_decision_ordinals()` (`core.py:1711-1730`), with a singular
`### Decision` reading as `d1` by convention — which makes the scheme total rather than partial across all
876 addressable decisions in the corpus.

### E2 — Who made it · **PARTIAL, and weaker than it looks**

`user_initials` and `agent_type` are both required CLI arguments (`cli.py:359-360`). But **Constitution v1.6
states explicitly that `user_initials` records who a session was *for*, not who chose the values** — every YAML
value in this corpus is agent-chosen. `agent_type` names the model, not a person. And `agent_name` was
*removed* from the schema on 2026-08-01 (entry `mse_t1g005w0mwd6srnj`) as duplicative.

So the field answers "which session did this come from," which is attribution of the record, not of the
decision. For frameworks that accept organisational attribution (most), this suffices. For frameworks that ask
who *individually* decided, it does not.

### E3 — When was it made · **STRONG, and stronger than most frameworks require**

The heading timestamp is machine-stamped, never author-supplied by default; the writer refuses to append out
of chronological order; an explicit `--timestamp` is reserved for sanctioned backfill and earns a
`clock_drift_warning`. Append-only chronology is enforced corpus-wide by `check_session_links()`
(`core.py:1976`+). Only 7 of 19 frameworks require E3 at all — this is over-delivery.

### E4 — Why was it made · **STRONG — the strongest column, against the highest-demand question**

`R:` is mandatory and **enforced in code**: `core.py:1704-1705` flags a `D:` with no `R:`, always. The write is
refused. `A:` (alternatives) is optional but present in the grammar, and `session_logging.md:167` instructs
that a failed or incompatible approach be logged under `A:` *even when not asked*.

**This is the finding to build on.** The most-demanded governance evidence question after "what was decided"
is answered by a mandatory, write-time-enforced field. No general-purpose documentation tool — Confluence,
Notion, Jira, GitHub — has a mandatory rationale field. MADR has a rationale *section* but nothing enforces it.

### E5 — What evidence supported it · **PARTIAL**

`T:` (tests/validation) and `F:` (files) are optional free text. `commits:` links SHAs (`core.py:2131`), and
the `Memory-Entry:` trailer provides the inverse link automatically via the seeded `prepare-commit-msg` hook.
Evidence Packs (`memory-trace/memory_trace/evidence.py:43-218`) assemble a deterministic, fingerprinted,
content-hashed bundle — entries, chunks, graph edges, contradictions, `missing_evidence[]`, and a
`pack_fingerprint`, all read-only and rebuildable.

The Evidence Pack is genuinely strong and under-appreciated. But the underlying evidence *fields* are optional
and unstructured, so a pack can only be as good as what was voluntarily recorded.

### E6 — What changed later · **STRONG — arguably best-in-class**

Four typed edge kinds, never merged (`graph-edge-contract.md`). `replaces` (retirement) and `evolves`
(freshness) are forward-only and acyclic by construction, validated independently per kind, with computed
inverses that are **never written** — a stored `replaced_by:` is rejected as `authored-inverse-field`.
Corrections go through append-only `retracts:` blocks (`core.py:931-940, 2732-2777`); the fuse refuses in-place
edits to published sidecars. Supersession down-ranks and never hides (Constitution Invariant #7).

Compare this to what the frameworks actually ask for. ISO 27001 7.5.3 wants version control. The AI Act Annex
IV §6 wants a lifecycle change record. MADR has a `status` string and cross-links *by convention*. **Memory
Seed's model is more rigorous than any of them** — typed, validated, acyclic, with an append-only correction
path.

### E7 — Who approved it · **ABSENT**

Searched definitively across `memory_seed/`, `memory-trace/`, and `.memory-seed/`: there is **no
`approved_by`, `reviewer`, `sign_off`, or equivalent key in any YAML block parsed anywhere in the system.**

The only matches are the `--user-approved` CLI flag (`cli.py:296,307,334,350`; `core.py:5384,5444-5462`;
`mcp_server.py:437,775`) — an *operational* authorisation token gating a branch-merge or integrate operation.
It authorises an action and **leaves no record on the decision**. Human approval is real in Memory Seed's
workflow — the link swarm and the draft ADR promotion path both require it — but it is a gate that forgets.

The project's own draft contract states the requirement and does not meet it. From
`adr-lifecycle-sidecar-contract.md`: *"Provenance records where the judgment came from; approval records who
let it in. Those are two different questions and the file answers both."* The block shape it specifies carries
`update_entry_id`, `expected_previous_status`, and `source:` — and no approver. The answer to "who let it in"
is reachable only by inference from `user_initials`, which the same document says means something else.

**E7 is REQUIRED in 10 of 19 frameworks.** This is the single largest gap in the system.

### E8 — What was affected · **PARTIAL / WEAK**

`F:` is free-text prose guidance to write backtick-quoted repo-relative file paths, because that is what
machine extraction reads for file-overlap ranking (`session_logging.md:239-243`). It is a lexical convention,
not a structured inventory. Searched: no `affected_systems`, `affected_components`, `asset_inventory`, or
equivalent field exists anywhere.

Frameworks asking E8 are not asking for file paths. ISO 27001 A.5.9 wants an information-asset inventory.
NIST CSF ID.AM-01 wants a hardware inventory. FedRAMP wants a system boundary. NIST AI RMF GOVERN 1.6 wants an
AI-system inventory. ISO 42001 A.6 wants an AI-system lifecycle register. **E8 is REQUIRED in 11 of 19 — the
joint-third most demanded question — and Memory Seed answers it with a filename convention.**

### Beyond the spine — four further absences that frameworks demand

| Capability | Status | Which framework needs it |
|---|---|---|
| **Decision status** (proposed/accepted/rejected/superseded) | **ABSENT.** The only `status:` in the codebase is `TopicRecord.status` (`topics.py:35`) — the lifecycle of a *vocabulary slug*. Decision state is expressed only indirectly through edges. The ADR sidecar contract that would add it is **DRAFT, NOT IMPLEMENTED** | Every ADR convention; ISO 42001 9.3; the AI Act's conformity lifecycle |
| **Evaluation criteria** (the criteria alternatives were judged *by*, distinct from the alternatives) | **ABSENT.** `A:` records alternatives with prose reasons; no structured criteria field exists | **CMMI DAR requires exactly this** — recorded alternatives evaluated against explicitly recorded criteria |
| **Retention period / review date** | **ABSENT.** No `retention`, `expiry`, or `review_date` field | AI Act Art. 18 (10 years); HIPAA §164.316(b)(2)(i) (6 years) and (b)(2)(iii) (periodic review) |
| **Confidence on a decision** | **ABSENT** on decisions. `edge_confidence` exists but is per-*edge*, in link sidecars (`core.py:986-1009`) | NIST AI RMF MANAGE 1.1 go/no-go determinations |

---

## 4. Coverage scorecard

| Question | Coverage | Basis | Demand rank |
|---|---|---|---|
| E1 what decision | **Strong** | `D:` mandatory, enforced `core.py:1704-1708`; `(entry_id, dN)` identity | 1 |
| E4 why | **Strong** | `R:` mandatory, enforced; `A:` for alternatives | 2 |
| E6 what changed | **Strong** | Typed forward-only acyclic edges + `retracts:` | 3= |
| E3 when | **Strong** | Machine-stamped, chronology-enforced | 8 |
| E2 who | **Partial** | Records the session, not the decider (Constitution v1.6) | 6 |
| E5 evidence | **Partial** | `T:`/`F:`/`commits:` optional; Evidence Packs deterministic | 7 |
| E8 affected | **Partial/weak** | `F:` file paths only; no asset or system inventory | 3= |
| E7 approved | **ABSENT** | No field exists anywhere; `--user-approved` gates an action, records nothing | 5 |

**4 strong · 3 partial · 1 absent.**

The uncomfortable alignment: Memory Seed is strongest on E3 (demand rank 8, least demanded) and absent on E7
(demand rank 5). It is strong on the two highest-demand questions, which is the good news — and weak or absent
on two of the next three, which is not.

### Per-framework field-shape coverage

Scoring each framework's REQUIRED cells only, with Strong = 1.0, Partial = 0.5, Absent = 0.

> **Read this table correctly or not at all.** It measures *whether a field of the right shape exists*.
> It does **not** measure compliance, control effectiveness, scope adequacy, or auditor acceptance. A high
> score means "the record could carry this," not "this framework is satisfied." §6 explains why the real
> number is lower than every figure here.

| Framework | REQUIRED cells | Field-shape coverage |
|---|---|---|
| MADR 4.0.0 | 5 | **90%** |
| HIPAA | 6 | **83%** |
| NIST AI RMF | 5 | **80%** |
| CCPA / CPRA | 4 | 75% |
| EU AI Act | 8 | **69%** |
| FedRAMP / SP 800-53 | 8 | 69% |
| ISO/IEC 27001 | 6 | 67% |
| ITIL change enablement | 6 | 67% |
| ISO/IEC 42001 | 7 | 64% |
| GDPR / UK GDPR | 7 | 64% |
| ISO 9001 | 4 | 63% |
| CMMI DAR | 5 | 60% |
| SOC 2 | 2 | 50% |
| NIST CSF 2.0 | 1 | 50% |

**Two observations that matter more than the numbers.**

The **AI Act and FedRAMP both sit at 69% and both lose the same 31%** — E7 entirely, plus half of E2, E5, and
E8. The gaps are not scattered; they are the same four fields every time. **One coherent capability addition —
approval, affected-systems, structured evidence, individual attribution — would lift nearly every framework in
this table simultaneously.** That is an unusually clean product signal.

**SOC 2 scores 50% for a revealing reason:** it has only two REQUIRED cells, and one of them is E7. The
framework most likely to be pursued by Memory Seed's natural users is the one whose small explicit demand set
is half-composed of the single thing Memory Seed cannot do.

---

## 5. The thesis, tested

**JNL's hypothesis:** *if Memory Seed already captures a large proportion of the evidence requirements common
across governance frameworks, it becomes a decision-governance platform supplying evidence to many frameworks
through one underlying model.*

### Evidence for

1. **The convergence is real.** All 19 frameworks with a decision surface fit the same eight questions. None
   needed a ninth. The premise holds.
2. **The highest-demand question is Memory Seed's strongest field.** E4 (why) is REQUIRED in 12 of 19 and is
   mandatory-and-enforced in code. This is rare — enforcement, not just provision.
3. **E6 is genuinely best-in-class.** Typed, validated, forward-only, acyclic, append-only with a sanctioned
   correction path. More rigorous than what any framework specifies.
4. **The gaps are shared, not scattered** (§4). Four fields unlock most of the table at once.
5. **The Evidence Pack already exists** — deterministic, fingerprinted, rebuildable, with explicit
   `missing_evidence[]` and `contradictions[]`. The assembly-and-export problem is partly solved.
6. **The architecture is right for the job.** Append-only history, declared provenance, derived projections,
   and "retrieval never hides live history" (Invariant #7) are exactly the properties an evidence substrate
   needs, and they are constitutional rather than incidental.

### Evidence against

1. **E7 is absent and REQUIRED in 10 of 19.** Not weak — absent. Every framework with segregation-of-duties
   expectations fails on this alone.
2. **E8 is answered with a filename convention** against 11 frameworks wanting an asset or system inventory.
3. **No decision status, no evaluation criteria, no retention model.** These are not exotic: CMMI DAR needs
   criteria, the AI Act needs 10-year retention, every ADR convention needs status.
4. **The ADR lifecycle contract that would supply status and promotion is DRAFT, NOT IMPLEMENTED.** Reasoning
   from it as a capability would be a category error.
5. **The Evidence Pack has no export path.** `EvidencePack = dict[str, Any]` (`evidence.py:40`); callers
   serialise it themselves. No auditor-facing artefact exists.

### The objection that outranks all of the above

**Memory Seed captures a different population of decisions than governance frameworks ask about.**

The frameworks want evidence about *organisational* decisions: risk treatment choices, control selection,
processing purposes, AI system design choices, change authorisations. Memory Seed captures *engineering
session* decisions: a scroll band, a lint message, a test rename.

This is not an outside criticism — it is the project's own position. From
`adr-lifecycle-sidecar-contract.md`: the corpus holds 876 addressable decisions and *"It should not hold 876
ADRs. Most session decisions are tactical… and stay entirely in their entry."*

The two populations overlap but are not the same set, and **the overlap is not currently marked.** The ADR
sidecar exists precisely to mark it, and it is not built. Until something distinguishes the governing decisions
from the tactical ones, an evidence pack over the corpus is not governance evidence — it is a work log that
contains some.

### Verdict

> **The convergence hypothesis is confirmed. The coverage claim is true about record *shape* and false about
> record *scope*.**
>
> Memory Seed's field model already answers four of the eight governance evidence questions structurally,
> three partially, and one not at all — a genuinely strong result, particularly on the highest-demand question.
> But a substrate that captures the right *shape* over the wrong *population*, with no approval record, no
> affected-systems model, and no way to mark which decisions govern, is **not a decision-governance platform
> today.**
>
> It is a **decision-record substrate with unusually strong rationale and lifecycle semantics** — which is a
> credible foundation for that platform, and a false description of the present state. The thesis should be
> carried into Report 3 as a *direction with four named preconditions*, not as an established position.

---

## 6. What would falsify this

Stated so the next reports can test rather than assume:

| Claim | What would falsify it |
|---|---|
| The eight questions are the right instrument | A framework, or a buyer's actual evidence request, that needs a ninth. Report 5 (ADR) and Report 6 (ICP) are the tests |
| E4 enforcement is a differentiator | Finding that Confluence/Notion/Jira/Backstage templates achieve comparable rationale capture in practice. **Report 3 must check this directly** — a template field is not enforcement, but adoption may not care |
| The four gaps are the binding constraint | A buyer interview in which E7/E8 never come up, and something else (export, integration, UI) blocks instead |
| The population objection is decisive | Evidence that auditors accept a filtered engineering decision log as governance evidence. This is an empirical question about auditor behaviour, and nobody in this programme has asked one |
| Field-shape coverage predicts value | It almost certainly does not on its own. §4's caveat is the honest position; Report 4 must define what actually gets measured |

---

## 7. What this hands to Report 3

**Four named preconditions**, in the order the evidence ranks them:

1. **E7 — a recorded approval.** Absent, REQUIRED in 10 of 19, and the project's own draft contract already
   states the requirement without meeting it. Highest-value single addition.
2. **Marking which decisions govern.** Without it, no evidence pack is governance evidence. The draft ADR
   sidecar is the designed answer and is unbuilt.
3. **E8 — affected systems beyond file paths.** REQUIRED in 11 of 19.
4. **An export path for Evidence Packs.** The hard part is built; the artefact has no door out.

**Three framings to carry forward:**

- **Lead with rationale, not with compliance.** E4 is the most-demanded question and Memory Seed's strongest
  field. "We enforce the why" is a defensible claim today; "we support ISO 42001" is not.
- **The gaps are shared.** One coherent capability set lifts most frameworks at once — unusual leverage,
  and the strongest argument for a single underlying model over per-framework features.
- **Treat the coverage table as a hypothesis generator, not a scoreboard.** Report 1 flagged NIST CSF 2.0,
  ISO 31000, and the OECD Principles as candidate false opportunities; SOC 2 now joins them for a sharper
  reason — its two-cell demand set is half E7.

---

## 8. Limitations

1. **Coverage scoring is a judgment, applied consistently.** Strong/Partial/Absent was assigned by one reader
   against code. The Absent calls are definitive (searched, negative, `file:line` cited); the Strong/Partial
   boundary is arguable — particularly E5, where a case exists for Weak.
2. **The REQUIRED counts inherit Report 1's limitations**, including that all ISO clause citations are
   `[secondary]` because `iso.org` returned 403 throughout.
3. **No auditor, assessor, or buyer was consulted.** Every claim about what would satisfy a framework is
   derived from framework text, not from anyone who has ever accepted or rejected evidence.
4. **Field-shape coverage ignores scope, quality, and completeness.** A mandatory `R:` field guarantees a
   reason exists, not that it is a good one.
5. **One search-based negative is weak evidence:** `memory_search` found no recorded reasoning for or against
   an approval field. The absence of E7 appears to be an unexamined gap rather than a considered rejection —
   but "no entry found" is not proof none exists.

---

*End of Report 2. Report 3 — Memory Seed Strategic Fit — tests the four preconditions against the competitive
field and the gap analysis JNL asked for.*
