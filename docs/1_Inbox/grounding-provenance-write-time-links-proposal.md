---
memory-system-version: 2.18
tags:
  - memory-seed
  - proposal
  - retrieval
  - graph
  - lifecycle
  - session-logging
---

# Grounding-provenance → write-time lifecycle links (turn the retrieval you already do into link candidates)

Status: **PROPOSED** (2026-07-14). Inbox.
Priority: P2 — graph/retrieval quality. Raises native lifecycle-link density at the point of entry write,
targeting the sparse decision-lineage edges (`supersedes`/`evolves`) that structural candidacy is worst at.
Source: User 2026-07-14 — "can the ground-in-both-repo-and-memory procedure be used to improve the amount
of native lifecycle links created at point of entry write?"

## Problem — the two loops don't talk, so the highest-signal candidates are thrown away

Two established loops run every substantive turn, but they are disconnected:

1. **Retrieval loop** (`.memory-seed/skills/history_retrieval.md`): before a non-obvious change, the agent
   `memory_search`es "why was X / what was tried" and fetches the consequential entries with
   `memory_get_chunk`. This surfaces the prior entries most relevant to what is about to be done — a
   requirement, not a nicety (agent-rules Working Principles + the seeded retrieval discipline).
2. **Link-authoring loop** (`session_logging.md` step 7): after harvesting decisions, classify
   replace→`supersedes` / extend→`evolves` / related→`related_entries`; `memory_link_suggest` "surfaces
   candidates with **shared-file evidence**."

The entries the agent *consulted to ground the work* — the highest-signal link candidates, because it
literally used them — are discarded after grounding. At write time the candidate tool starts over from
**structural file/topic overlap**, a lower-signal proxy. The expensive retrieval is already done; the
system just throws away its most valuable by-product, then re-derives a weaker substitute.

## Why this specifically lifts the *sparse* edges

Link candidacy today draws on a single axis — **repo condition** (shared files/topics). The grounding
retrieval is the missing **memory axis** (consulted decision-lineage). The asymmetry is the whole point:

- **File/topic overlap** answers "touched the same file / same subject" → adequate for `related`, **weak
  for `supersedes`/`evolves`**.
- **`supersedes`/`evolves` are decision-lineage edges** — "this replaces / extends a prior *decision*."
  That is exactly what the agent retrieves when it asks "has this been decided before?" So the consulted
  set is the natural source for the two edge types that are hardest to catch structurally and the most
  under-created natively.

Making link-authoring "based on both repo **and** memory" — the same two-source discipline already applied
to the work itself — closes the gap where native links leak most.

## Current behavior (grounded)

- `memory_link_suggest` (MCP, read-only): ranks older entries to link from a target (default: the newest
  entry) by **shared-file evidence**, returning a paste-ready `related_entries` list. It never consults
  what the session actually retrieved.
- `history_retrieval.md`: mandates pre-work `memory_search`/`memory_get_chunk` but its output is used only
  to inform the *work*, never carried into the *entry* the work produces.
- `link audit` (+ the promoted `lifecycle-link-authoring-assist` `--apply` scaffold): candidates are older
  entries sharing ≥1 `F:` file OR ≥1 topic — again structural, and **retroactive** (end-of-session), not
  at point of write.
- Net: no channel feeds *"the entries I consulted"* into *"the edges I author"*.

## Why it's this way (do not regress)

- Classification — **supersedes vs evolves vs related** — is deliberate *author judgment*, never inferred
  (`graph-edge-contract.md`). This proposal only **surfaces candidates**; it must never auto-create an edge.
- Entries are **append-only**; this concerns the native YAML of the entry being written, not retroactive
  sidecar edits.
- Over-linking is a known hazard (the standing "don't record co-occurrence noise, only genuine lifecycle
  relationships" discipline). A high-recall candidate source must be paired with a hard author gate.

## Proposal

### 1. Guidance-only (cheapest, no code) — connect the two skills

Amend `history_retrieval.md` and `session_logging.md` (+ seed twins; both are control-plane, edit on
approval) so the loops explicitly join: *"The entries you retrieved to ground this work are your first
lifecycle-link candidates. When you author the entry, classify each consulted entry as
`supersedes`/`evolves`/`related` or discard — before falling back to `memory_link_suggest`'s file-overlap
candidates. Consulted entries are especially the source for `supersedes`/`evolves`; be conservative with
`related`."* Zero new surface, immediate lift, matches the control-plane guidance style.

### 2. Tooling — let the agent pass its consulted set (stateless, Invariant #6-clean)

Give `memory_link_suggest` an optional `consulted: [entry_id, ...]` parameter: the agent passes the ids it
fetched while grounding, and the tool **blends** them into its ranked candidates, **labeled by
provenance** ("consulted" vs "shares files") and ordered consulted-first. No server-side session state is
introduced — the agent stays authoritative over its own consult-set, so nothing new is stored, cached, or
made rebuildable (Invariant #6 holds trivially). The paste-ready `related_entries` block stays a
suggestion the author still classifies/prunes.

### 3. (Optional, P3) Capture the consult-set automatically

If manual passing proves lossy, have the runtime record each session's returned/fetched `chunk_id`s to an
**ephemeral, rebuildable, disposable** per-day working-set (outside the repo, never authoritative — a
derived projection, discardable at any time), which `memory_link_suggest`/`session append` read. Deferred
until 1–2 prove the ergonomics; only build if recall-based passing leaks.

## Non-goals

- No auto-classification and no writing a live `supersedes:`/`evolves:` value without the author.
- No new authoritative store; the consult-set is either agent-supplied (layer 2) or an ephemeral derived
  projection (layer 3), never source of truth.
- Not a replacement for `memory_link_suggest`'s file-overlap candidacy — it **adds** the memory axis
  alongside it.
- Does not touch ranking of `memory_search` results (that is the successor-surfacing / ranking-ab track).

## Acceptance criteria

- `history_retrieval.md` + `session_logging.md` (+ seed twins) state that consulted entries are the first
  lifecycle-link candidates and are the primary source for `supersedes`/`evolves`; parity tests pass.
- `memory_link_suggest` accepts `consulted: [ids]`, returns candidates labeled by provenance
  (consulted vs shares-files), consulted-first, with a paste-ready `related_entries` block; passing an
  empty/absent list reproduces today's behavior byte-for-byte.
- A measurable-lift check: on a fixture where the "written" entry's true lineage parent shares **no** file
  with it (a pure decision-lineage edge), file-overlap candidacy misses it and consulted-set candidacy
  surfaces it.
- No path auto-creates an edge; the author still classifies. Guard against `related_entries` inflation is
  stated in the guidance.

## Dependencies

- `.memory-seed/skills/history_retrieval.md`, `.memory-seed/skills/session_logging.md` (+ seed twins).
- `memory_seed/mcp_server.py` (`memory_link_suggest`) and its retrieval/link plumbing.
- `docs/3_Spec/graph-edge-contract.md` (the never-auto-classify constraint this must respect).

## Relationship to existing coverage (checked — complementary, not a duplicate)

- `docs/2_Todo/lifecycle-link-authoring-assist-proposal.md` — the **retroactive / end-of-session /
  file-topic** sidecar-scaffold backstop. This proposal is the **native / write-time / consult-sourced**
  upstream channel. They compose: consult-sourced links raise the write-time baseline (cheapest, freshest
  context); the `--apply` sweep catches whatever slipped. Could be folded into that plan as its write-time
  channel, but is a distinct mechanism (retrieval capture, not sidecar authoring) — kept standalone.
- `memory_link_suggest` (shipped) — extended here with the `consulted:` axis, not replaced.
- `docs/2_Todo/supersession-successor-surfacing-proposal.md` / `real-corpus-ranking-validation-gate-proposal.md`
  — those improve *retrieval ranking* of lifecycle edges; this improves *creation* of them. Different half
  of the same graph-quality goal.
