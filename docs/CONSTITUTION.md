# Memory Seed Constitution

**Version:** 1.0 — **RATIFIED 2026-07-14** by JNL. Changes now go through [Governance](#11-governance).
**Status:** Living document. It grows only by amendment (see [Governance](#11-governance)).
**Adopted:** 2026-07-14 (ratified; includes the same-day derived-layer / optional-tier refinement —
Invariants #1 & #6, §5, and the open-core principle). **Source:** distilled from demonstrated behaviour
across the codebase,
`3_Spec/`, `.memory-seed/agent-rules.md`, and the session-memory corpus — not invented. Framework from the
[architectural-discovery proposal](2_Todo/memory-seed-architectural-discovery-proposal.md).

> **How to read this.** Higher layers constrain lower ones and change more slowly:
> **Vision → Invariants → Principles → Policies → Implementations.** An *implementation* may change
> tomorrow; an *invariant* should hold for years. Each clause is either **cited** (a file that already
> demonstrates it) or tagged **[candidate]** (aspirational — not yet established; do not treat as settled).

---

## 1. Vision

Memory Seed is **the local-first, model-independent memory substrate that preserves a project's reasoning
— its decisions, evidence, and context — so humans and AI agents can continue work without repeating
prior investigation.** It is infrastructure that many clients consume, not an application. *(Source: the
discovery proposal's strategic-position statement; `4_Reference/memory-seed-market-fit-report.md`.)*

It is **not** another documentation tool, Git client, or knowledge graph. Its differentiation lives above
the Git-history layer: decision and reasoning provenance. *(Ref: `4_Reference/memory-seed-gitlens-competitor-report.md`.)*

---

## 2. Invariants — expected to hold for years

The sacred properties. Changing one is a [constitutional amendment](#11-governance).

1. **Users own their memory.** It lives as plain files in the user's repository; the **core** runs with no
   server, database, or network. Optional layers may add a cache, index, database, or hosted service for
   performance or collaboration — the core never depends on them. *(Cited: Markdown+YAML storage with no DB;
   `memory-seed situate`/`esr` and the core CLI/MCP are network-free; `memory-seed` installs
   web-framework-free; the `memory-seed[trace]` optional extra is the pattern.)*
2. **The past is append-only — extend and supersede, never rewrite or delete.** History is evidence;
   corrections are new entries that point back. *(Cited: append-only session logs; `links check`
   forward-only/acyclic guards; supersede-don't-delete in `.memory-seed/skills/proposal_lifecycle.md` and
   the memory graph.)*
3. **Memory is explainable and attributable.** Every decision can be traced to who/what/when and the
   reasoning behind it. *(Cited: `Memory-Entry:` commit trailers; the decision-graph edges in
   `3_Spec/graph-edge-contract.md`; `3_Spec/memory-trace-derived-artifact-provenance-contract.md`.)*
4. **Files are the authority for what is true *now*; memory is the authority for *why*.** Neither
   substitutes for the other. *(Cited: `.memory-seed/agent-rules.md` Working Principles.)*
5. **Memory is model-independent.** No entry's meaning depends on the agent or model that wrote it; it
   serves any agent and any human. *(Cited: `agent-rules.md` `vendor_neutral: true`; the seed ships for
   Claude, Codex, Gemini, Cursor, and Copilot alike.)*
6. **Markdown is the single source of truth — human-readable, durable, and authoritative *everywhere*.**
   Every other store — cache, index, database, embedding, or hosted backend — is a **derived projection**:
   fully rebuildable from the Markdown, never authoritative, never required for the core to run. This holds
   even under hosted or collaborative use — concurrent writes resolve *into* Markdown, and a server database
   is only ever an accelerator over it, never a second source of truth. A person can always read and edit
   the source directly with no tool; derived layers need not be human-readable. *(Cited: the rebuildable
   SQLite cache outside the repo; per-user session files + `session merge-branch`/fuse as Markdown-native
   concurrent-write resolution. "Markdown today, another durable format tomorrow" — the format may change;
   the source-of-truth role may not.)*
7. **Retrieval never hides live history to flatter a ranking.** A superseded entry is down-ranked, never
   removed from results. *(Cited: `SUPERSEDED_RANK_DAMPING` down-rank-only rule in `graph-edge-contract.md`;
   `exclude_superseded` is a separate opt-in filter, never the default.)*

---

## 3. Principles — design guidance

How we decide. Amending these is heavier than a normal proposal but lighter than an invariant.

- **Evidence before opinion.** Ground decisions in what the code and corpus demonstrate; retrieve prior
  reasoning before re-deciding. *(Cited: `agent-rules.md` "retrieve the why"; this document's own method.)*
- **Expose before you rank.** A new signal is shown as inspectable metadata and proven on real data before
  it changes default retrieval order. *(Cited: `graph-edge-contract.md` "Standing rules".)*
- **Integrate, don't duplicate.** One canonical reader/service per concern; new surfaces consume it rather
  than fork logic. *(Cited: the single `build_related_entry_graph` reader + shared retrieval service; the
  "integrate with GitLens, don't rebuild it" stance.)*
- **Immediate value before future value.** Ship the smallest useful increment on the proven path before the
  ambitious rebuild. *(Cited: vanilla-first Trace with the versioned `/api/v1` contract held for the future
  React client; `3_Spec/memory-trace-vanilla-parity-checklist.md`.)*
- **Prove risky automation on a small case; don't remove guards you don't understand.** *(Cited:
  `agent-rules.md` Working Principles; `.memory-seed/skills/risk_signaling.md`.)*
- **Trust before automation.** Establish that memory is trustworthy before acting on it automatically.
  **[candidate]** — partly aspirational; the content-trust taxonomy that would make it operational is not
  yet built (see [Open Questions](#10-open-questions--unresolved-tensions)).
- **Open-core, one source of truth.** The local Markdown truth is free and complete on its own; paid or
  hosted tiers add convenience, scale, and collaboration *on top of* it — never a second, authoritative
  store. **[direction — decided 2026-07-14; no paid tier exists yet.]**

---

## 4. Policies — expected to evolve

The current, deliberately-changeable *rules* through which the invariants are realised. Changing these is
ordinary proposal work.

- **The folder a document lives in is its lifecycle state** (`docs/README.md` front door).
- **Four independent, never-merged edge kinds**; forward-only and acyclic (`graph-edge-contract.md`).
- **DRAFT session-entry format** (D/R/A/F/T) and append-only chronology (`session_logging.md`).
- **Controlled topic vocabulary** in `.memory-seed/topics.yaml`; **seed/live twin parity** for shipped
  skills; **schema, API (`/api/v1`), and CLI surfaces** are versioned and may grow.
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
  a **React/Vite** Trace shell (*planned*); a **VS Code extension** (memory beside the code — a candidate
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
safety depend on it. Today only the DRAFT labels (Decision/Reason/Alternatives/Files/Tests) and
`memory_hygiene`/`risk_signaling` exist; a first-class content-trust taxonomy is proposed, not built.
*(Ref: `4_Reference/memory-seed-rectification-priorities-report.md`.)*

## 8. Memory quality **[candidate]**

"Good memory" means: retrievable, explainable, attributable, current-without-losing-history, and low in
stale/orphan/contradiction rate. The Constitution defines *what* quality is; implementations decide *how*
to measure it. Today `links check`, `topics check`, and `esr` are the partial instrumentation; named
quality metrics (stale-rate, orphan-rate, evidence/decision coverage) are not yet tracked.
*(Ref: `4_Reference/memory-seed-strategic-synthesis-report.md`.)*

## 9. The five-question test

Every proposal must improve at least one of — and say which:

**Capture · Validation · Retrieval · Trust · Application.**

If it improves none, it must justify why it belongs in Memory Seed at all.

---

## 10. Open questions & unresolved tensions

The live record of what is *not* settled (this is the honest half of "discovery" — kept, not hidden):

- **Governance-first vs. ship-first — now the live decision.** The Constitution is ratified (2026-07-14);
  `0_NEXT_STEPS` Tracks A/B remain **paused**. The open call: resume A/B, or gate future work on the
  Constitution first? *(This is the decision that created this document.)*
- **The next-generation Trace shell** (React/Vite) and a **VS Code extension** are candidate optional-local
  surfaces (§5), not yet committed.
- **Trust taxonomy (§7) and quality metrics (§8)** are named but undefined.
- **Source-of-truth under collaboration — RESOLVED (2026-07-14):** even a future hosted/collaborative tier
  keeps Markdown authoritative; any server database is a derived projection (Invariant #6). *Still open:*
  **which** commercial tier to reach (local-pro / team-hosted / enterprise) and when — parked while
  development is paused (`8_Deferred/memory-trace-commercialisation-and-monetisation-report.md`).
- **Where the Constitution sits relative to the locked control plane.** Today it *describes*
  `agent-rules.md`; making agent-rules formally *subordinate* to this document is a future amendment, not
  assumed here.

---

## 11. Governance

This document is **versioned and living**. Two change classes:

- **Evolution** — a change *within* existing invariants and principles (a new policy, implementation, or
  feature). Handled by the normal proposal/`0_NEXT_STEPS` flow; no amendment needed.
- **Constitutional amendment** — a change to the **Vision, an Invariant, a core Principle, or the Trust
  model**. Requires higher scrutiny: an explicit proposal, the maintainer's ratification, and a new row in
  the log below. Amendments bump the version (`1.x` for additive, `2.0` for a changed invariant).

A proposal that conflicts with a live invariant is rejected or must first amend the invariant — it cannot
silently override it. "[candidate]" clauses graduate to cited/established only when a shipped artifact
demonstrates them.

### Amendment log

| Version | Date | Change | Ratified by |
|---|---|---|---|
| 1.0 | 2026-07-14 | **Initial Constitution ratified** — the 7 invariants, principles, policies, four-layer model, five-question test, trust/quality candidates, and governance; includes the same-day derived-layer / optional-tier refinement (Invariants #1 & #6, §5, open-core principle). | JNL |
