# Memory Seed Constitution

**Version:** 1.14 — **RATIFIED 2026-09-16** by JNL. Changes go through [Governance](#11-governance).
**Status:** Living document. Its substance changes only by amendment; the version also increments for
evolution-class corrections, so the log below is a complete version history (see
[Governance](#11-governance)).
**Adopted:** 2026-07-14; amended 2026-07-16 with partitioned Markdown authority for narrowly scoped,
append-only sidecars (Invariant #6); amended 2026-07-17 with a human-gated, one-off exception for
untyped `related_entries` metadata curation (Invariant #2); amended 2026-07-19 with write-surface
parity — every write passes identical validation on any surface (Invariant #2); amended 2026-07-23
with a human-gated, one-off exception for diagram-sidecar syntax repair (Invariant #2), **retired
2026-07-26** once an append path made it unnecessary; amended 2026-07-26 adding the *minimal but
sufficient context* principle (§3, `[candidate]`); amended 2026-08-06 with stable clause anchors;
amended 2026-08-11 to make a declared ratified Constitution formally govern lower control-plane
documents; **corrected** 2026-08-13 (1.9, evolution-class — not an amendment) to record the shipped
quality instrumentation in §8; amended 2026-09-05 to make the governed path the path of least
resistance through inspectable outcome-level composition (§3); amended 2026-09-06 with the bounded
temporary reflection-board lifecycle (Invariant #2); amended 2026-09-14 so DRAFTS decisions cite
material source artifacts and retrieval lexical matching is capitalization-safe (§4); evolved 2026-09-16
so typed DRAFTS records distinguish decisions from documentation while sharing one searchable structure (§4). **Source:** distilled from demonstrated behaviour
across the codebase,
`3_Spec/`, `.memory-seed/agent-rules.md`, and the session-memory corpus — not invented. Framework from the
[architectural-discovery proposal](5_Completed/memory-seed-architectural-discovery-proposal.md).

> **How to read this.** Higher layers constrain lower ones and change more slowly:
> **Vision → Invariants → Principles → Policies → Implementations.** An *implementation* may change
> tomorrow; an *invariant* should hold for years. Each clause is either **cited** (a file that already
> demonstrates it) or tagged **[candidate]** (aspirational — not yet established; do not treat as settled).

---

## 1. Vision

Memory Seed is **the local-first, model-independent memory substrate that preserves a project's reasoning
— its decisions, evidence, and context — so humans and AI agents can continue work without repeating
prior investigation.** It is infrastructure that many clients consume, not an application. *(Source: the
discovery proposal's strategic-position statement; `../business/market/memory-seed-market-fit-report.md`.)*

It is **not** another documentation tool, Git client, or knowledge graph. Its differentiation lives above
the Git-history layer: decision and reasoning provenance. *(Ref: `../business/market/memory-seed-gitlens-competitor-report.md`.)*

---

## 2. Invariants — expected to hold for years

The sacred properties. Changing one is a [constitutional amendment](#11-governance).

<!-- constitution-ref: constitution:v1#ownership -->
1. **Users own their memory.** It lives as plain files in the user's repository; the **core** runs with no
   server, database, or network. Optional layers may add a cache, index, database, or hosted service for
   performance or collaboration — the core never depends on them. *(Cited: Markdown+YAML storage with no DB;
   `memory-seed situate`/`esr` and the core CLI/MCP are network-free; `memory-seed` installs
   web-framework-free; the `memory-seed[trace]` optional extra is the pattern.)*
<!-- constitution-ref: constitution:v1#append-only -->
2. **The past is append-only — extend and supersede, never rewrite or delete.** History is evidence;
   corrections are new entries that point back. *(Cited: append-only session logs; `links check`
   forward-only/acyclic guards; supersede-don't-delete in `.memory-seed/skills/proposal_lifecycle.md` and
   the memory graph.)*
   <!-- constitution-ref: constitution:v1#metadata-curation -->
   **Narrow exception — human-gated metadata curation (1.2):** an existing entry's **untyped
   `related_entries` metadata** may be curated after the fact, under all of these conditions at once:
   it is a **one-off procedure, never core functionality** — no standing command, no automation, no
   batch pass; **each individual edge is approved by the user at the moment it is added**; only the
   entry's YAML metadata is touched, **never its prose**; and **typed lifecycle edges
   (`supersedes`/`evolves`/`continuity`) are never written into history** — those go through the
   evolution-edges seeding pass, which records them in *new* entries and rewrites nothing. If any
   condition fails, the invariant applies unchanged. The exception exists because an untyped "these two
   relate" pointer is a navigational aid rather than a claim about what was decided or why; it does not
   license editing the record of a decision.
   <!-- constitution-ref: constitution:v1#write-surface-parity -->
   **Write-surface parity (1.3):** every write to memory passes the same validation, whatever surface
   performs it. No tool may author or integrate an entry by a path that skips the guards another
   surface enforces — chronology, ref existence, forward-only lifecycle edges, topic vocabulary, id
   collision, and DRAFT format hold identically over the CLI and MCP. This **strengthens** the
   invariant rather than relaxing it: a surface that could write without the guards was a standing way
   to add unvalidated history, which is precisely what append-only exists to prevent. A write surface
   is an [Implementation](#5-implementations) and owes no allegiance to any particular tool, but the
   guards a write passes are not implementation detail — they are how "extend, never corrupt" is kept
   true no matter who is holding the pen.
   **Retired exception — diagram-sidecar syntax repair (added 1.4, retired 1.5):** the v1.4 carve-out
   permitting in-place repair of a published diagram sidecar whose Mermaid failed to parse is
   **withdrawn**. It existed only because there was no append path: diagram blocks were keyed by
   `entry_id` alone, so a second block for an entry blocked the fuse and editing the published one was
   the sole route to a diagram that renders. Diagram blocks now key on `(entry_id, heading timestamp)`
   like link sidecars, so a repair is an **appended block that supersedes** while the original stays
   readable as what was authored — which is what this invariant asks for in the first place. The
   exception is therefore unnecessary rather than merely unused, and a carve-out that no longer buys a
   capability is a standing invitation to edit history. Invariant #2 applies to diagram sidecars
   without exception. *(The 1.4 row stays in the amendment log: the exception was real while it
   existed, and one repair landed under it.)*
   <!-- constitution-ref: constitution:v1#adr-ledger-v2-migration -->
   **Narrow, one-time exception — ADR-ledger v2 canonicalization (1.10):** the historical ADR corpus
   may be rewritten **once**, solely to replace the v1 mixed `Why`/`Evolution` prose with the v2
   `Decision`/`Reason`/`Impact` shape. Before any source byte changes, the procedure must archive a
   byte-for-byte copy of every ADR and emit a SHA-256 manifest containing path, byte count, and digest.
   It must preserve every event ID, timestamp, JSON-envelope value, decision reference, and lifecycle
   reference. An absent impact may be reconstructed only from a directly cited historical source and
   must say so; otherwise it must remain explicitly `not-recorded`. The conversion is corpus-locked:
   it verifies the known preimage digests, refuses unfamiliar input and any second run, and is neither a
   general rewrite facility nor a standing CLI/MCP command. On successful completion this exception is
   exhausted; all future ADR history is append-only under the invariant.
   <!-- constitution-ref: constitution:v1#temporary-reflection-expiry -->
   **Narrow standing exception — temporary reflection-board expiry (1.12):** reflection blocks explicitly
   created inside a declared plan-scoped reflection board are temporary coordination material, not durable
   Memory Seed decisions or ordinary retrieval history. They may be removed only as complete reflection
   chains through the governed reflection lifecycle. A chain cannot expire until its implementation has been
   independently validated where validation is required, the orchestrator has synthesized the relevant
   implementer, reviewer, and orchestrator reflections, and a successful chain-level close records the
   disposition and complete receipt coverage. The project-configurable retention period defaults to seven days
   and starts from that chain's `closed_at` time. When it elapses, the next sanctioned cleanup automatically
   removes that chain; it never performs a general board wipe. Before any
   removal, a compact receipt for every chain member must already exist in ordinary append-only session
   memory: promoted chains embed their receipts with the decision or decisions that absorbed them, while
   unpromoted chains receive an expiry disposition in the ESR closeout entry. Early removal of an unpromoted
   chain requires the user's live approval and a durable approval/disposition record. An unresolved divergent
   head prevents chain close and therefore prevents ordinary expiry until it is resolved or explicitly disposed.
   The exception never permits rewriting or deleting ordinary sessions, decisions, ADRs, policies, or other
   durable memory; Git may retain historical blobs, so active-tree expiry is not privacy-grade erasure.
<!-- constitution-ref: constitution:v1#explainability -->
3. **Memory is explainable and attributable.** Every decision can be traced to who/what/when and the
   reasoning behind it. *(Cited: `Memory-Entry:` commit trailers; the decision-graph edges in
   `3_Spec/graph-edge-contract.md`; `3_Spec/memory-trace-derived-artifact-provenance-contract.md`.)*
<!-- constitution-ref: constitution:v1#authority -->
4. **Files are the authority for what is true *now*; memory is the authority for *why*.** Neither
   substitutes for the other. *(Cited: `.memory-seed/agent-rules.md` Working Principles.)*
   <!-- constitution-ref: constitution:v1#provenance -->
   **Provenance is first-hand vs reconstructed, not human vs machine (1.6):** a value recorded when
   the work was done — by whoever or whatever did it — is **first-hand**; a value derived afterwards
   by reading the finished record is **reconstructed**. Both are legitimate; they are not equal
   evidence, and which one a value is must be **declared on the record, never inferred from where it
   is stored**. This is a clarification, not a new rule: the corpus's own metadata is written by
   agents (`user_initials` records who a session was *for*, not who chose the values), so language
   describing stored fields as what "the author" or "a human" knew has been describing write-time
   authorship all along. Measured support for treating them as unequal: a cold sweep reconstructing
   topics from finished prose scored 0.583 and 0.613 macro-recall against the first-hand values
   (topic-swarm pilot, 2026-07-26). A reconstructed value is therefore sound as a **gap-filler where
   nothing was recorded**, and weak as a replacement for a first-hand one.
<!-- constitution-ref: constitution:v1#model-independence -->
5. **Memory is model-independent.** No entry's meaning depends on the agent or model that wrote it; it
   serves any agent and any human. *(Cited: `agent-rules.md` `vendor_neutral: true`; the seed ships for
   Claude, Codex, Gemini, Cursor, and Copilot alike.)*
<!-- constitution-ref: constitution:v1#markdown-authority -->
6. **Markdown is the authoritative memory substrate — human-readable, durable, and authoritative
   *everywhere*.** Authority may be partitioned across append-only primary entries and narrowly scoped
   Markdown sidecars, but every authoritative field or lifecycle has exactly one declared owner. Every other
   store — cache, index, database, embedding, computed snapshot, or hosted backend — is a **derived
   projection**: fully rebuildable from the authoritative Markdown, never authoritative, and never required
   for the core to run. This holds even under hosted or collaborative use — concurrent writes resolve *into*
   Markdown, and a server database is only ever an accelerator over it, never a second source of truth. A
   person can always read and edit the source directly with no service; derived layers need not be
   human-readable.
   Narrow sidecars may own explicit promotion or lifecycle facts while referenced entries own narrative
   rationale and evidence. *(Cited: the rebuildable SQLite cache outside the repo; per-user session files +
   `session merge-branch`/fuse; lifecycle and diagram sidecars; Constitution 1.1 amendment. "Markdown today,
   another durable format tomorrow" — the format may change; the source-of-truth role may not.)*
<!-- constitution-ref: constitution:v1#retrieval-transparency -->
7. **Retrieval never hides live history to flatter a ranking.** A superseded entry is down-ranked, never
   removed from results. *(Cited: `SUPERSEDED_RANK_DAMPING` down-rank-only rule in `graph-edge-contract.md`;
   `exclude_superseded` is a separate opt-in filter, never the default.)*

---

## 3. Principles — design guidance

How we decide. Amending these is heavier than a normal proposal but lighter than an invariant.

<!-- constitution-ref: constitution:v1#evidence-first -->
- **Evidence before opinion.** Ground decisions in what the code and corpus demonstrate; retrieve prior
  reasoning before re-deciding. *(Cited: `agent-rules.md` "retrieve the why"; this document's own method.)*
<!-- constitution-ref: constitution:v1#expose-before-rank -->
- **Expose before you rank.** A new signal is shown as inspectable metadata and proven on real data before
  it changes default retrieval order. *(Cited: `graph-edge-contract.md` "Standing rules".)*
<!-- constitution-ref: constitution:v1#single-source -->
- **Integrate, don't duplicate.** One canonical reader/service per concern; new surfaces consume it rather
  than fork logic. *(Cited: the single `build_related_entry_graph` reader + shared retrieval service; the
  "integrate with GitLens, don't rebuild it" stance.)*
<!-- constitution-ref: constitution:v1#immediate-value -->
- **Immediate value before future value.** Ship the smallest useful increment on the proven path before the
  ambitious rebuild. *(Cited: vanilla-first Trace with the versioned `/api/v1` contract held for the future
  React client; retired gate `3_Spec/deprecated/memory-trace-vanilla-parity-checklist.md`.)*
<!-- constitution-ref: constitution:v1#prove-automation -->
- **Prove risky automation on a small case; don't remove guards you don't understand.** *(Cited:
  `agent-rules.md` Working Principles; `.memory-seed/skills/risk_signaling.md`.)*
<!-- constitution-ref: constitution:v1#trust-first -->
- **Trust before automation.** Establish that memory is trustworthy before acting on it automatically.
  **[candidate]** — partly aspirational; the content-trust taxonomy that would make it operational is not
  yet built (see [Open Questions](#10-open-questions--unresolved-tensions)).
<!-- constitution-ref: constitution:v1#minimal-context -->
- **Minimal but sufficient context.** Retrieval aims to provide the smallest context that preserves the
  ability to decide — maximise information per token; material that does not change the answer is
  omission, not loss. **[candidate]** — aspirational; no retrieval surface enforces or measures this yet.
  Identified as a genuine gap by the inbox crosswalk (row A6-5) and independently re-derived by the
  information-theoretic disposition (`4_Reference/information-theoretic-evolution-disposition.md`,
  2026-07-25); graduates to cited when the constrained-context gold set exists to measure it against.
  *Provenance note:* first written into §3 on 2026-07-25 **without** an amendment, which §11 requires
  for a core principle. Ratified retroactively as part of v1.5 rather than left as an unratified clause
  — a principle nobody approved is exactly the kind of silent override §11 forbids.
<!-- constitution-ref: constitution:v1#path-of-least-resistance -->
- **Make the correct path the easiest path.** Memory Seed composes mechanically determined steps behind
  outcome-level operations so humans and agents do not spend attention or model tokens reconstructing
  deterministic workflows. It stops where relevance, authority, risk, scope, or intent requires judgment,
  and every composed operation preserves the same validation, provenance, explainability, and human control
  as its underlying steps. The result exposes what was selected, what was omitted, why execution continued
  or stopped, and which governing guards were applied. *(Cited: `1_Inbox/agent-interaction-storylines-review.md`;
  `8_Deferred/agent-skill-workflow-architecture-proposal.md`; `mse_d1h4mf4z40epm8jz:d1` and `:d2`.)*
<!-- constitution-ref: constitution:v1#open-core -->
- **Open-core, one authoritative substrate.** The local Markdown truth is free and complete on its own; paid or
  hosted tiers add convenience, scale, and collaboration *on top of* it — never a second, authoritative
  store. **[direction — decided 2026-07-14; no paid tier exists yet.]**

---

## 4. Policies — expected to evolve

The current, deliberately-changeable *rules* through which the invariants are realised. Changing these is
ordinary proposal work.

<!-- constitution-ref: constitution:v1#folder-lifecycle -->
- **The folder a document lives in is its lifecycle state** (`docs/README.md` front door).
<!-- constitution-ref: constitution:v1#edge-kinds -->
- **Four independent, never-merged edge kinds**; forward-only and acyclic (`graph-edge-contract.md`).
<!-- constitution-ref: constitution:v1#link-corrections -->
- **Link-edge corrections are append-only.** A published `replaces`/`evolves`/`related_entries` edge is
  downgraded or removed only through a **new-block `retracts:` correction** (the fuse refuses in-place
  edits to a published link sidecar), realizing Invariant #2 for lifecycle edges — the sanctioned path
  the v1.4 amendment noted was absent (`3_Spec/draft/link-retraction.md`). Machine-suggested edges (the
  optional link-judgment swarm) carry an advisory `edge_confidence` and are human-gated before any write.
<!-- constitution-ref: constitution:v1#draft-format -->
- **Typed DRAFTS session-entry format** and append-only chronology (`session_logging.md`). The `D`
  denotes either a **Decision** or **Documentation** record under `### Records`; every record states
  its `Scope`, while a Decision additionally states its `Disposition` and its own `R:`. Documentation
  records capture small work and evidence without acquiring lifecycle or ADR authority: they may be
  searched, addressed, topic-tagged, and related, but cannot own `replaces`/`evolves` or become an ADR
  member/head. `A/F/T/S` remain optional when applicable; `S:` names a materially informing
  repository-relative source artifact. Historical untyped and singular decision records remain valid,
  readable as decisions, and append-only.
<!-- constitution-ref: constitution:v1#lexical-normalization -->
- **Lexical matching is capitalization-safe.** Retrieval normalizes query text, preferred keywords,
  and indexed lexical fields with Unicode NFKC plus case folding before matching. Optional preferred
  keywords may add a bounded positive ranking signal, but never exclude otherwise matching history.
<!-- constitution-ref: constitution:v1#topic-vocabulary -->
- **Controlled topic vocabulary** in `.memory-seed/topics.yaml`; **seed/live twin parity** for shipped
  skills; **schema, API (`/api/v1`), and CLI surfaces** are versioned and may grow.
<!-- constitution-ref: constitution:v1#integration-mode -->
- **`integration_mode`** (local-merge vs PR); agent-namespaced branches/worktrees.

---

## 5. Implementations — freely replaceable technology

No allegiance is owed to any of these; they serve the layers above, and every non-core store sits
downstream of Invariant #6 (derived, rebuildable). Grouped by distance from the core:

- **Core (always present):** Markdown + YAML files · Git as the commit substrate · MCP over stdio ·
  Python 3.11+ / setuptools · Mermaid/D2 for diagrams.
- **Derived accelerators** (optional, read-side, rebuildable from the Markdown): a SQLite cache today;
  candidates — **DuckDB** for analytical Trace/graph processing, **SQLite FTS5** for full-text, and a
  **vector index** (sqlite-vec / pgvector / hnswlib) for semantic search.
- **Optional-local capability** (adds features, still offline, degrades to the core): Model2Vec embeddings;
  the supported **React/Vite** Memory Trace client; a **VS Code extension** (memory beside the code — a candidate
  high-leverage adoption surface); a desktop shell; pluggable local AI providers.
- **Hosted / collaborative** (paid tier — still Markdown-authoritative per Invariant #6): a team-sync /
  managed backend and cross-project memory — candidate directions, not adopted.

---

## 6. The four-layer model

```
Vision          — why Memory Seed exists
Constitution    — invariants, principles, trust, memory model   (this document)
Platform        — storage, retrieval, graph, APIs, MCP, CLI
Experience      — Memory Trace, editor/GitHub integrations, future clients
```

Lower layers must not redefine higher ones. The **Experience** layer (any UI or integration) may never
override a constitutional invariant.

---

## 7. Trust model **[candidate]**

Memory should classify *what kind of knowledge* an entry carries — authoritative policy, historical
context, evidence, hypothesis, instruction, observation, or generated summary — because retrieval and agent
safety depend on it. Today only typed DRAFTS records (Decision or Documentation, Scope, decision
Disposition/Reason, Alternatives/Files/Tests/Sources) and
`memory_hygiene`/`risk_signaling` exist; a first-class content-trust taxonomy is proposed, not built.
*(Ref: `4_Reference/memory-seed-rectification-priorities-report.md`.)*

## 8. Memory quality **[candidate]**

"Good memory" means: retrievable, explainable, attributable, current-without-losing-history, and low in
stale/orphan/contradiction rate. The Constitution defines *what* quality is; implementations decide *how*
to measure it. Today `links check`, `topics check`, `esr`, and the read-only `memory-seed quality report`
are the partial instrumentation. Of the named metrics, orphan-rate and evidence/decision coverage are
measured — as `unlinked_entry_rate` and structural `draft_reason_coverage` — while stale-rate remains
unmeasured by deliberate v0 scope. Two further metrics declare themselves `unavailable` and one
`not_applicable`, each with a stated reason. This clause remains **[candidate]**: graduation is gated on
the step-6 usefulness review in
[`2_Todo/memory-quality-metrics-v0-proposal.md`](2_Todo/memory-quality-metrics-v0-proposal.md), which is
a decision to be made, not further implementation to be done.
*(Ref: [`2_Todo/memory-quality-metrics-v0-proposal.md`](2_Todo/memory-quality-metrics-v0-proposal.md);
[`4_Reference/memory-quality-v0-baseline.md`](4_Reference/memory-quality-v0-baseline.md);
`../business/wedges/memory-seed-strategic-synthesis-report.md`.)*

## 9. The five-question test

Every proposal must improve at least one of — and say which:

**Capture · Validation · Retrieval · Trust · Application.**

If it improves none, it must justify why it belongs in Memory Seed at all.

---

## 10. Open questions & unresolved tensions

The live record of what is *not* settled (this is the honest half of "discovery" — kept, not hidden):

- **Governance-first vs. ship-first — RESOLVED (2026-07-14): resume, sequenced under the Constitution.**
  The Constitution was ratified 2026-07-14 and development **resumed the same day** — each item now answers
  the five-question test and respects Invariant #6, rather than gating all work behind further governance.
  *(This is the decision that created this document; the pause achieved its purpose.)*
- **The next-generation Trace shell — RESOLVED (2026-08-11):** React/Vite is the sole supported
  Memory Trace frontend. A **VS Code extension** remains a candidate optional-local surface (§5).
- **Trust taxonomy (§7) and quality metrics (§8)** are named but undefined.
- **Source-of-truth under collaboration — RESOLVED (2026-07-14):** even a future hosted/collaborative tier
  keeps Markdown authoritative; any server database is a derived projection (Invariant #6). *Still open:*
  **which** commercial tier to reach (local-pro / team-hosted / enterprise) and when — parked pending
  usage + market validation (`8_Deferred/memory-trace-commercialisation-and-monetisation-report.md`).
- **Where the Constitution sits relative to the locked control plane — RESOLVED (2026-08-11):** a
  ratified Constitution explicitly declared by the active runtime index formally governs the lower
  control plane. A draft, candidate, or undisclosed Constitution remains evidence only.

---

## 11. Governance

This document is **versioned and living**. Two change classes:

- **Evolution** — a change *within* existing invariants and principles (a new policy, implementation, or
  feature). Handled by the normal proposal/`0_NEXT_STEPS` flow; no amendment needed.
- **Constitutional amendment** — a change to the **Vision, an Invariant, a core Principle, or the Trust
  model**. Requires higher scrutiny: an explicit proposal, the maintainer's ratification, and a new row in
  the log below. Amendments bump the version (`1.x` for additive, `2.0` for a changed invariant).

**Versioning covers both classes.** An amendment always bumps the version. An **evolution-class
correction to this document's own text** — a clause whose factual claim has decayed relative to shipped
behaviour — also bumps the minor version and earns a log row marked as such, so the version is a complete
history of what this document has said rather than a history of amendments alone. The distinction is
preserved *in* the row, not by omitting it: a reader must be able to tell whether a version changed what
the Constitution requires or only what it accurately reports. An evolution row still records the
maintainer's acceptance, but needs no proposal cycle. A correction may never be used to change a
requirement — if the text and the code disagree about what *should* be true rather than what *is* true,
that is an amendment, and the lower layer does not get to win by having shipped first.

A proposal that conflicts with a live invariant is rejected or must first amend the invariant — it cannot
silently override it. "[candidate]" clauses graduate to cited/established only when a shipped artifact
demonstrates them.

<!-- constitution-ref: constitution:v1#control-plane-precedence -->
A runtime that declares this Constitution ratified applies the following authority order:
**Constitution → current concern-owning control file → accepted ADR head → session evidence → derived
projection**. The index is a thin router, policy states executable constraints, and ADRs own durable
decision rationale and evolution. Lower layers may operationalize higher ones but may not contradict
or silently redefine them. Projects without a declared ratified Constitution remain valid and begin
their authority chain at the concern-owning control file.

### Version log

Amendment rows change what the Constitution *requires*. Correction rows change only what it *reports*,
and say so.

| Version | Date | Change | Ratified by |
|---|---|---|---|
| 1.14 | 2026-09-16 | **Evolution: typed DRAFTS decisions and documentation.** Expands `D` to mean Decision or Documentation record under one `### Records` structure. Every new record carries Scope; decisions additionally require Disposition and their own Reason. Documentation records make small work and evidence searchable without granting lifecycle or ADR authority. Historical untyped/singular records remain decisions and are not rewritten. | JNL (approved the design-discovery plan and directed implementation live, 2026-09-16) |
| 1.13 | 2026-09-14 | **DRAFTS source attribution and capitalization-safe lexical retrieval.** Renames the current decision-record mnemonic from DRAFT to DRAFTS; adds `S:` for a materially informing repository artifact, with mechanical validation whenever supplied while preserving historical DRAFT records unchanged; and requires Unicode NFKC plus case-fold normalization across lexical query/index text. Optional preferred keywords are a bounded positive ranking aid, never a filter. | JNL (approved the implementation plan and directed implementation live, 2026-09-14) |
| 1.12 | 2026-09-06 | **Amendment: bounded temporary reflection-board expiry.** Reflection blocks created inside a declared plan-scoped board are temporary coordination material rather than durable memory. After required validation and orchestrator synthesis, complete chains close independently with durable receipt coverage; their user-configurable retention period, seven days by default, starts from chain close. Elapsed closed chains expire automatically and individually, never as a board wipe; early removal of an unpromoted chain requires live user approval and a durable disposition. Ordinary sessions, decisions, ADRs, policy, and other durable memory remain append-only. | JNL (ratified live 2026-09-06) |
| 1.11 | 2026-09-05 | **Make the correct path the easiest path.** Adds a permanent §3 principle requiring Memory Seed to compose mechanically determined continuations behind outcome-level operations, stop at genuine judgment or authority boundaries, preserve all underlying validation/provenance/human control, and expose selections, omissions, guards, and stopping reasons. This turns the storyline and workflow-architecture direction into a constitutional design constraint without authorizing opaque automation. | JNL (ratified in live discussion, 2026-09-05) |
| 1.10 | 2026-08-31 | **Amendment: one-time Canonical ADR Ledger v2 migration.** Authorizes only the corpus-locked conversion from the ambiguous `Decision`/`Why`/`Evolution` and `Reason` event prose to a uniform `Decision`/`Reason`/`Impact` ledger. It requires a preimage archive and SHA-256 manifest before rewrite; preserves event IDs, timestamps, envelopes, and references; requires declared impact provenance with direct evidence for reconstructions; and forbids a reusable rewrite command. Once run, the exception is exhausted and Invariant #2 again applies without qualification. | JNL |
| 1.9 | 2026-08-13 | **Correction (evolution-class — not an amendment): §8 records the shipped quality instrumentation.** §8 claimed that named quality metrics "are not yet tracked" and listed only `links check`, `topics check`, and `esr` as the partial instrumentation. That was true when written and had since decayed: `memory-seed quality report` shipped 2026-07-17 and measures `unlinked_entry_rate` (180/901 at this revision) and structural `draft_reason_coverage` (857/857, 44 excluded), with `generated_claim_citation_coverage`, `provenance_coverage`, and `ranking_ab_regression_rate` declaring `unavailable`/`not_applicable` and a reason each. Two of the three named metrics — orphan-rate and evidence/decision coverage — therefore have measured proxies; stale-rate does not, and its absence is deliberate v0 scope, not an oversight. §8 **remains `[candidate]`**: graduation is separately gated on the step-6 usefulness review in `2_Todo/memory-quality-metrics-v0-proposal.md`, whose `next_action` names §8 graduation explicitly, so the correction records shipped fact without touching that hold. Nothing this document requires has changed. §11 gains the versioning rule that makes an evolution-class bump legible rather than indistinguishable from an amendment. Found while comparing this project against an external report and noticing that two review passes had read current capability out of §8 — a *why* document — instead of out of the code, which Invariant #4 assigns as the authority for what is true now. | JNL (accepted 2026-08-13; version bump requested so the log tracks document versions, not amendments alone) |
| 1.8 | 2026-08-11 | **Formal control-plane precedence** — a ratified Constitution declared by the active runtime index now governs lower control files; the index routes, policy states concise executable constraints, accepted ADR heads own durable decision rationale/evolution, sessions retain evidence, and projections remain derived. Draft or undeclared Constitutions do not govern, preserving Constitution-optional bootstrap for other projects. | JNL |
| 1.7 | 2026-08-06 | **Per-clause anchor markers** — every invariant (and its live sub-clauses), principle, and §4 policy clause gains an HTML-comment `constitution-ref` anchor (`constitution:v1#slug`, 24 in all). Structural only: zero content changed, verified by a markers-stripped byte comparison against v1.6. Added so ADR constitution bindings and the ESR ADR↔Constitution audit resolve against declared anchors rather than prose numbering (the ADR contract extension of the same date validates refs against these markers). Slugs are semantic, not positional, so renumbering never breaks a binding. | Claude, under JNL's delegated ratification (live instruction, 2026-08-06: "ratify for me and get me to the end goal and then i will iterate") |
| 1.0 | 2026-07-14 | **Initial Constitution ratified** — the 7 invariants, principles, policies, four-layer model, five-question test, trust/quality candidates, and governance; includes the same-day derived-layer / optional-tier refinement (Invariants #1 & #6, §5, open-core principle). | JNL |
| 1.1 | 2026-07-16 | **Partitioned Markdown authority** — Invariant #6 now permits narrowly scoped append-only Markdown sidecars to own declared fields or lifecycles while entries retain rationale/evidence and all indexes, snapshots, databases, and UI views remain derived. | JNL |
| 1.2 | 2026-07-17 | **Human-gated metadata curation** — Invariant #2 now permits after-the-fact curation of an existing entry's *untyped* `related_entries` metadata, as a one-off, per-edge-approved procedure only: never core functionality, never automatic or batch, never touching prose, and never writing typed lifecycle edges into history. Raised by the Related-entries P2 plan, which was approved 2026-07-05 — before v1.0 — and whose backfill half conflicted with Invariant #2 as ratified. Rather than honour a pre-constitutional sign-off or silently override the invariant (§11 forbids both), the invariant was amended to the narrowest shape that permits the capability. | JNL |
| 1.3 | 2026-07-19 | **Write-surface parity** — Invariant #2 now requires every write to memory to pass identical validation on any surface. Prompted by a tool-surface audit that found two authoring paths of unequal strength: the CLI `session append` enforced nine guards atomically, while the MCP path (`memory_entry_id` + `memory_session_target` + a hand-written file) enforced none, so violations only surfaced later in `links check`. The read-only-MCP posture that created the gap was a 2026-07-10 session decision, not constitutional law — Invariant #2 governed *what* is written, never *which surface* writes. Rather than leave the parity rule as convention an agent could route around (as one did), it was written into the invariant it protects: the fix added a gated MCP write surface and retired the ungated pair, and the invariant now forbids any future bypass. Additive (1.x), not a changed invariant — it strengthens #2 rather than altering its meaning, following the v1.1/v1.2 precedent for narrowing/hardening under a minor bump. | JNL |
| 1.6 | 2026-07-26 | **Provenance is first-hand vs reconstructed** — Invariant #4 gains a clarifying clause: a value recorded when the work was done is *first-hand*, one derived afterwards by reading the finished record is *reconstructed*, both are legitimate but not equal evidence, and which one a value is must be **declared on the record rather than inferred from where it is stored**. Prompted by JNL observing that this repository's links and topics are written by agents at write time as well as derived by sweeps afterwards, so the contract's "what the author knew" language had been describing *write-time authorship* while reading as *human authorship* — and `user_initials` records who a session was for, not who chose the values. Storing provenance positionally (entry YAML = authored, sidecar = inferred) is the fragile second derivation this clarifies away, and it is what the accepted `write-time-sidecar-consolidation-proposal.md` replaces with a declared `source` field. Measured support for the inequality: a cold sweep scored 0.583/0.613 macro-recall against first-hand values (topic-swarm pilot), making reconstruction sound as a gap-filler and weak as a replacement. Clarifying, not restricting — no capability is added or removed, which is why it is 1.x and touches no other invariant. | JNL |
| 1.5 | 2026-07-26 | **Diagram-repair exception retired; *minimal but sufficient context* added.** Two clauses, approved together. (a) The v1.4 in-place diagram-repair carve-out on Invariant #2 is **withdrawn**. It existed solely because diagram blocks were keyed by `entry_id` alone, so a second block blocked the fuse and editing the published one was the only route to a diagram that renders; blocks now key on `(entry_id, heading timestamp)` like link sidecars, so a repair is an appended block that supersedes while the original stays readable. The capability the exception bought now exists *within* the invariant, so the carve-out is unnecessary rather than dormant — and a carve-out that buys nothing is a standing invitation to edit history. Hardening, hence 1.x, following the v1.1–v1.4 precedent for narrowing under a minor bump; the 1.4 row stays, since the exception was real while it existed and one repair landed under it. (b) §3 gains **minimal but sufficient context** as a `[candidate]` principle: retrieval provides the smallest context that preserves the ability to decide. Identified as a genuine gap by the inbox crosswalk (A6-5) and independently re-derived by the information-theoretic disposition. It was written into §3 on 2026-07-25 *without* an amendment, which §11 requires for a core principle; ratifying it here corrects that rather than leaving an unratified clause standing. | JNL |
| 1.4 | 2026-07-23 | **Human-gated diagram-sidecar syntax repair** — Invariant #2 now permits repairing a published *diagram* sidecar whose Mermaid fails to parse, as a one-off, per-repair-approved procedure only: never core functionality, never a standing `fuse`/`merge-branch` flag, confined to the content inside ` ```mermaid ` fences (heading, `entry_id`, diagram count, and the parent entry's prose all unchanged), and only ever turning an unrenderable diagram into a rendering one — never re-authoring what a diagram depicts. Scoped to diagram sidecars, which own no authoritative field and are a rendered lens over a decision; explicitly **not** extended to link sidecars, which authoritatively own typed lifecycle edges (#6) that 1.2 walls off. Prompted by two published sidecars (2026-07-10, 2026-07-22) whose diagrams a `;` in sequence-message text and a `--` inside an edge label left unparseable, so Memory Trace fell back to raw source; `session merge-branch` correctly refused the in-place fix as an append-only violation (the same refusal recorded at the 2026-07-22 link-sidecar revert), leaving no sanctioned path to make a frozen record render as authored. Rather than silently override Invariant #2 (§11 forbids it) or build a standing repair capability the control plane cannot bound — it cannot parse Mermaid, so no guard can verify a diagram renders — the invariant was amended to the narrowest shape that permits the one-off repair, mirroring the v1.2 metadata-curation exception. A broader "sidecars are editable lenses" posture across all sidecar types was deliberately deferred to its own proposal. Additive (1.x): it narrows a carve-out into #2 without changing its meaning. | JNL |
