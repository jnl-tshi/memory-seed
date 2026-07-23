# Memory Seed Constitution

**Version:** 1.4 — **RATIFIED 2026-07-23** by JNL. Changes go through [Governance](#11-governance).
**Status:** Living document. It grows only by amendment (see [Governance](#11-governance)).
**Adopted:** 2026-07-14; amended 2026-07-16 with partitioned Markdown authority for narrowly scoped,
append-only sidecars (Invariant #6); amended 2026-07-17 with a human-gated, one-off exception for
untyped `related_entries` metadata curation (Invariant #2); amended 2026-07-19 with write-surface
parity — every write passes identical validation on any surface (Invariant #2); amended 2026-07-23
with a human-gated, one-off exception for diagram-sidecar syntax repair (Invariant #2). **Source:** distilled from demonstrated behaviour
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
   **Write-surface parity (1.3):** every write to memory passes the same validation, whatever surface
   performs it. No tool may author or integrate an entry by a path that skips the guards another
   surface enforces — chronology, ref existence, forward-only lifecycle edges, topic vocabulary, id
   collision, and DRAFT format hold identically over the CLI and MCP. This **strengthens** the
   invariant rather than relaxing it: a surface that could write without the guards was a standing way
   to add unvalidated history, which is precisely what append-only exists to prevent. A write surface
   is an [Implementation](#5-implementations) and owes no allegiance to any particular tool, but the
   guards a write passes are not implementation detail — they are how "extend, never corrupt" is kept
   true no matter who is holding the pen.
   **Narrow exception — human-gated diagram-sidecar syntax repair (1.4):** a published diagram sidecar
   whose Mermaid fails to parse — a transcription defect that stopped the record from ever rendering
   *as made* — may be repaired in place, under all of these conditions at once: it is a **one-off
   procedure, never core functionality** — no standing command, no `--allow`-style flag on `fuse` /
   `session merge-branch`, no automation or batch pass; **the maintainer approves each individual
   repair against a diff before it lands**; the change is confined to the **content inside
   ` ```mermaid ` fences** — the block's heading, its `entry_id`, the number of diagrams, and every
   byte outside the fences are unchanged, and the parent session entry's prose is never touched; and
   the repair only ever turns an **unrenderable diagram into a rendering one** — it never re-authors a
   diagram that already parsed, nor alters what a diagram depicts. If any condition fails, the
   invariant applies unchanged. The exception is scoped deliberately to *diagram* sidecars, which own
   no authoritative field and are a rendered lens over a decision; it does **not** extend to link
   sidecars, which authoritatively own typed lifecycle edges (Invariant #6) that 1.2 already walls off
   from after-the-fact editing. The exception exists because a diagram sidecar is defined as a frozen
   record of the decision *as made*, and a syntax error that stops it rendering at all defeats that
   purpose: repairing it makes the frozen record faithful to what was authored, rather than revising
   the decision. It does not license editing a diagram to say something new — that is a superseding
   entry with its own sidecar.
3. **Memory is explainable and attributable.** Every decision can be traced to who/what/when and the
   reasoning behind it. *(Cited: `Memory-Entry:` commit trailers; the decision-graph edges in
   `3_Spec/graph-edge-contract.md`; `3_Spec/memory-trace-derived-artifact-provenance-contract.md`.)*
4. **Files are the authority for what is true *now*; memory is the authority for *why*.** Neither
   substitutes for the other. *(Cited: `.memory-seed/agent-rules.md` Working Principles.)*
5. **Memory is model-independent.** No entry's meaning depends on the agent or model that wrote it; it
   serves any agent and any human. *(Cited: `agent-rules.md` `vendor_neutral: true`; the seed ships for
   Claude, Codex, Gemini, Cursor, and Copilot alike.)*
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
- **Open-core, one authoritative substrate.** The local Markdown truth is free and complete on its own; paid or
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

- **Governance-first vs. ship-first — RESOLVED (2026-07-14): resume, sequenced under the Constitution.**
  The Constitution was ratified 2026-07-14 and development **resumed the same day** — each item now answers
  the five-question test and respects Invariant #6, rather than gating all work behind further governance.
  *(This is the decision that created this document; the pause achieved its purpose.)*
- **The next-generation Trace shell** (React/Vite) and a **VS Code extension** are candidate optional-local
  surfaces (§5), not yet committed.
- **Trust taxonomy (§7) and quality metrics (§8)** are named but undefined.
- **Source-of-truth under collaboration — RESOLVED (2026-07-14):** even a future hosted/collaborative tier
  keeps Markdown authoritative; any server database is a derived projection (Invariant #6). *Still open:*
  **which** commercial tier to reach (local-pro / team-hosted / enterprise) and when — parked pending
  usage + market validation (`8_Deferred/memory-trace-commercialisation-and-monetisation-report.md`).
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
| 1.1 | 2026-07-16 | **Partitioned Markdown authority** — Invariant #6 now permits narrowly scoped append-only Markdown sidecars to own declared fields or lifecycles while entries retain rationale/evidence and all indexes, snapshots, databases, and UI views remain derived. | JNL |
| 1.2 | 2026-07-17 | **Human-gated metadata curation** — Invariant #2 now permits after-the-fact curation of an existing entry's *untyped* `related_entries` metadata, as a one-off, per-edge-approved procedure only: never core functionality, never automatic or batch, never touching prose, and never writing typed lifecycle edges into history. Raised by the Related-entries P2 plan, which was approved 2026-07-05 — before v1.0 — and whose backfill half conflicted with Invariant #2 as ratified. Rather than honour a pre-constitutional sign-off or silently override the invariant (§11 forbids both), the invariant was amended to the narrowest shape that permits the capability. | JNL |
| 1.3 | 2026-07-19 | **Write-surface parity** — Invariant #2 now requires every write to memory to pass identical validation on any surface. Prompted by a tool-surface audit that found two authoring paths of unequal strength: the CLI `session append` enforced nine guards atomically, while the MCP path (`memory_entry_id` + `memory_session_target` + a hand-written file) enforced none, so violations only surfaced later in `links check`. The read-only-MCP posture that created the gap was a 2026-07-10 session decision, not constitutional law — Invariant #2 governed *what* is written, never *which surface* writes. Rather than leave the parity rule as convention an agent could route around (as one did), it was written into the invariant it protects: the fix added a gated MCP write surface and retired the ungated pair, and the invariant now forbids any future bypass. Additive (1.x), not a changed invariant — it strengthens #2 rather than altering its meaning, following the v1.1/v1.2 precedent for narrowing/hardening under a minor bump. | JNL |
| 1.4 | 2026-07-23 | **Human-gated diagram-sidecar syntax repair** — Invariant #2 now permits repairing a published *diagram* sidecar whose Mermaid fails to parse, as a one-off, per-repair-approved procedure only: never core functionality, never a standing `fuse`/`merge-branch` flag, confined to the content inside ` ```mermaid ` fences (heading, `entry_id`, diagram count, and the parent entry's prose all unchanged), and only ever turning an unrenderable diagram into a rendering one — never re-authoring what a diagram depicts. Scoped to diagram sidecars, which own no authoritative field and are a rendered lens over a decision; explicitly **not** extended to link sidecars, which authoritatively own typed lifecycle edges (#6) that 1.2 walls off. Prompted by two published sidecars (2026-07-10, 2026-07-22) whose diagrams a `;` in sequence-message text and a `--` inside an edge label left unparseable, so Memory Trace fell back to raw source; `session merge-branch` correctly refused the in-place fix as an append-only violation (the same refusal recorded at the 2026-07-22 link-sidecar revert), leaving no sanctioned path to make a frozen record render as authored. Rather than silently override Invariant #2 (§11 forbids it) or build a standing repair capability the control plane cannot bound — it cannot parse Mermaid, so no guard can verify a diagram renders — the invariant was amended to the narrowest shape that permits the one-off repair, mirroring the v1.2 metadata-curation exception. A broader "sidecars are editable lenses" posture across all sidecar types was deliberately deferred to its own proposal. Additive (1.x): it narrows a carve-out into #2 without changing its meaning. | JNL |
