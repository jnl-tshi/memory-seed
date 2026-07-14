# Memory Seed Constitution

**Version:** 1.0 — **RATIFICATION DRAFT** (awaiting the maintainer's ratification; amend freely first)
**Status:** Living document. It starts tight and grows only by amendment (see [Governance](#11-governance)).
**Adopted:** 2026-07-14 (draft). **Source:** distilled from demonstrated behaviour across the codebase,
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

1. **Users own their memory.** It lives as plain files in the user's repository; the core needs no server,
   no database, and no network. *(Cited: Markdown+YAML storage with no DB; `memory-seed situate`/`esr` and
   the core CLI/MCP are network-free; `memory-seed` installs web-framework-free.)*
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
6. **Memory is human-readable and durable.** A person can read and edit it directly, with no tool. *(Cited:
   Markdown + YAML, folder-as-state, generated human indexes. Implementation note: "Markdown today, another
   durable format tomorrow" — the format may change; readability may not.)*
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

No allegiance is owed to any of these; they serve the layers above.

Markdown + YAML files · a rebuildable SQLite cache (outside the repo) · Git as the commit substrate · MCP
over stdio · Model2Vec embeddings (optional) · the vanilla-JS Memory Trace UI (a React/Vite shell is
*planned*, not adopted) · Mermaid/D2 for diagrams · Python 3.11+ / setuptools packaging.

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

- **Governance-first vs. ship-first.** Development of `0_NEXT_STEPS` Tracks A/B is **paused** while this
  Constitution is drafted and ratified. Open: do we resume A/B after ratification, or gate future work on
  the Constitution first? *(This is the decision that created this document.)*
- **The next-generation Trace shell** (React/Vite) is a strategic bet, not yet committed.
- **Trust taxonomy (§7) and quality metrics (§8)** are named but undefined.
- **Commercial / hosted direction** is parked (`8_Deferred/`), pending demonstrated local value.
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
| 1.0-draft | 2026-07-14 | Initial ratification draft. | _pending_ |
