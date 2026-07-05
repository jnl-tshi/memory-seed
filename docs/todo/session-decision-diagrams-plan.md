---
memory-system-version: 2.15
tags:
  - memory-seed
  - plan
  - memory-explorer
  - session-logging
  - visualization
---

# Session Decision Diagrams Plan

> **Status:** ACTIVE — scoped 2026-07-05. **Phase 1 implemented 2026-07-05 (unreleased); revised
> same day to date-named sidecar files** for filesystem readability (see "Storage convention"
> below): the sidecar convention, `links check` validation (`orphan-diagram`/`diagram-date-mismatch`/
> `malformed-diagram`), retrieval-service surfacing (`entry_diagram_sidecars()`, opt-in
> `get_chunk(include_diagrams=True)`, Lense chunk `diagrams` metadata), and the authoring guidance in
> `session_logging.md` + `end_of_turn.md` (live + seed) are built and tested; a first real sidecar
> exists (`sessions/diagrams/2026-07-05.md`). Phases 2 (Explorer rendering) and 3 (report pack)
> remain gated as scoped below.
> **Priority:** P2 for the core convention + validation + authoring guidance (low blast radius,
> Explorer-independent); P3 for the exportable report/handover pack (paid-tier, gated on the Explorer
> split). Sequence Phase 1 first. User confirmed 2026-07-05 that decision diagrams should be included
> in the next goal-pass scope alongside Memory Trail Phase-1 retrieval-service work.
> **Source:** Conversation 2026-07-05 (JNL). Starting question: have session logs ever used Mermaid to
> capture decision logic (answer: never, in 25 files), and is that a weak-guidance symptom. Resolution:
> logic diagrams for non-technical stakeholders are a real need once the Explorer becomes a paid review
> tool (see the market-fit visual appendix), but a **no-LLM Explorer cannot derive a reasoning diagram
> from prose** — so the reasoning diagram must be authored at session-entry time, stored as a sidecar
> keyed to the entry, and kept out of the append-only prose log.
> **Scope:** A two-class diagram model for Memory Seed. **Class 1 (structural, auto-derived, uniform):**
> provenance/timeline/graph views the Explorer computes deterministically from the graph-edge contract,
> plus a new exportable static report/handover pack. **Class 2 (reasoning, authored, sporadic):**
> per-decision flow/sequence/topology diagrams the agent emits at entry time as heading blocks
> appended to `.memory-seed/sessions/diagrams/YYYY-MM-DD.md` sidecar files (one file per date,
> mirroring the session-log filename convention), validated by `links check` and rendered by the
> Explorer alongside their entry.
> **Non-goals:** No LLM/NLP in the Explorer or in `links check` (deterministic only). No requirement
> that any entry have a diagram. No mutation of existing session entries (sidecars point *to* entries,
> not the reverse). No deterministic extraction of Class-2 diagrams from prose (impossible without an
> LLM — that is the whole reason sidecars are authored at entry time). No write/curation surface in the
> Explorer. No new default dependency on core `memory-seed`.
> **Dependencies:** [`../graph-edge-contract.md`](../graph-edge-contract.md) (Class-1 substrate;
> `build_related_entry_graph()` is the canonical reader — do not fork edge parsing).
> [`memory-seed-explorer-distribution-plan.md`](memory-seed-explorer-distribution-plan.md) Phase 1 (the
> public retrieval service must surface sidecar diagrams and structured fields these views consume).
> [`memory-explorer-entry-level-ui-results-plan.md`](memory-explorer-entry-level-ui-results-plan.md)
> (the entry is the primary selectable object; diagrams attach to entries, not to section chunks).
> **Acceptance criteria:** see per-phase gates below.

## Problem

Session entries are append-only `D`/`R`/`A`/`F`/`T` decision records — mostly prose rationale. That is
correct for the current audience (agents + the technical maintainer), and the existing Working
Principle (plain text by default; Mermaid only for spatial/temporal/concurrent structure) has held so
well that **no session entry has ever embedded a diagram**. That is fine while the reader is technical.

It stops being fine when Memory Explorer becomes a paid tool for **non-technical stakeholders**
(project managers, clients, reviewers) to review developers' agent-driven work — the commercial wedge
in `docs/inbox/memory-seed-market-fit-visual-appendix.md` (Diagram 11) and the "branded reports,
exportable timelines, project handover packs" paid tier in `docs/inbox/memory-seed-market-fit-report.md`.
A wall of prose decision records is a weak product for that audience.

The naive fix — "encourage agents to embed Mermaid in the log" — fails twice: it did not move the base
rate (zero), and it would pollute the clean, diffable, append-only audit trail that *is* the product's
differentiator. The other naive fix — "have the Explorer generate diagrams from the prose at render
time" — is impossible for a **no-LLM, local-first, deterministic** Explorer: you cannot turn freeform
reasoning into a flowchart without the model that understood the reasoning.

## The two-class model

The resolution is to split diagrams by *what they depict* and *where they can be produced*.

### Class 1 — structural (auto-derived, uniform, always fresh)

Provenance graphs, supersession chains, timelines, contributor/commit linkage. These derive from
**structured fields** (`related_entries`, `supersedes`, `commits`, `session_date`, participants) via
`build_related_entry_graph()`. A no-LLM Explorer computes them deterministically at render time, so
they are **uniform** (every decision gets the same treatment) and **always current** (a
`superseded_by` badge appears automatically). Interactive versions already exist in Memory Lense
(graph, timeline). The **gap** is a static, shareable **export** of them — the actual paid handover
artifact — which does not exist yet.

### Class 2 — reasoning (authored at entry time, sporadic, frozen)

A flowchart of *why* a decision was made, a decision tree over the alternatives, a sequence across
components. This lives in the prose and cannot be machine-derived. It must be authored by the agent
(the LLM) in the same turn it writes the entry, when the decision's logic genuinely meets the existing
spatial/temporal/concurrent bar. It is stored as a **sidecar** — never inline — and it is legitimately
**frozen**: it documents the decision *as made*, so immutability is a feature, not the liability it
would be for a Class-1 roadmap view. Coverage is **sporadic by design**; Class 2 is opportunistic
enrichment, not the reliable stakeholder-value driver.

The two compose: a superseded decision keeps its frozen Class-2 flow diagram while the Explorer
overlays a live Class-1 `superseded_by` badge — accurate without editing the frozen asset.

## Phase 1 — Sidecar convention, validation, and the authoring trigger (core, Explorer-independent)

Buildable now, independent of the Explorer split. This is the part that determines whether the folder
ever fills — a storage spec alone would sit empty exactly like inline Mermaid did, so the **authoring
trigger** is in scope here, not deferred.

### Storage convention

- Location: `.memory-seed/sessions/diagrams/YYYY-MM-DD.md` — **one file per date**, mirroring the
  session-log filename convention exactly. Revised from an initial `<entry_id>.md`-per-file design:
  date-named files maximize human readability when visually traversing the raw Markdown without the
  Explorer — a user can open the day's diagrams file next to that day's session log and match by
  `entry_id` present inside it, the same way session logs already work.
- File shape: append a heading block shaped like a session entry — `## <timestamp> - <title>`,
  followed by a fenced ` ```yaml ` block naming `entry_id:` (the single authoritative link), followed
  by one or more fenced ` ```mermaid ` blocks. Multiple diagrams authored the same day append to the
  same date file, in ascending time order, exactly like session logs. Markdown-wrapped so the source
  of truth stays Markdown/text, diffable and git-native; the Explorer extracts the fenced block(s) and
  renders them client-side (no server render, no LLM).
- One link source: each block's `entry_id:` inside its ` ```yaml ` fence. The heading timestamp is a
  human-matching convenience (ideally mirroring the entry's own heading time), not a validated key.

### Validation (`check_session_links()` in `core.py`, reusing the entry-YAML scan)

Per the graph-edge contract's rule that a new artifact's validation belongs in the single validator,
add issue kinds:

- `malformed-diagram` — the filename isn't a valid `YYYY-MM-DD.md` date, no `## <timestamp> - <title>`
  + ` ```yaml ` block is found, a block's yaml has no `entry_id`, or a block has no/unbalanced
  ` ```mermaid ` fence (error; deterministic fence check only, no Mermaid semantic parsing).
- `orphan-diagram` — a block whose `entry_id` resolves to no known entry (error).
- `diagram-date-mismatch` — a block's `entry_id` resolves to a real entry, but that entry's actual
  session date differs from the diagrams filename date (error; mirrors the existing per-user
  filename↔frontmatter date check).

Sidecars are **optional**: `links check` never warns on an entry that lacks one. `doctor` keeps its
one-line summary pattern.

### Authoring trigger (the anti-empty-folder mechanism)

Add to `session_logging.md` and `end_of_turn.md` (+ seed twins): when writing a Decision entry whose
logic genuinely meets the spatial/temporal/concurrent bar (branching alternatives, a sequence/flow, a
topology), the agent **may** append a diagram block to `sessions/diagrams/YYYY-MM-DD.md` (today's
date) in the same turn, naming the `entry_id` it just generated. Same high bar as the Working
Principle — most entries still get none. This is the deliberate, gated trigger; without it the
convention stays theoretical.

### Phase 1 acceptance criteria

- `links check` validates sidecars (malformed / orphan / date-mismatch) over both session layouts and
  stays green when no sidecars exist.
- No existing session entry is modified by adding a sidecar.
- The authoring guidance is in the live + seed `session_logging.md` and `end_of_turn.md`.
- A round-trip test: an authored sidecar block for a real entry, filed under that entry's real date,
  passes `links check`; a block with a bad/dangling `entry_id` or filed under the wrong date fails
  with the specific issue kind. Multiple diagram blocks logged the same day append to and both
  resolve correctly from one shared date file.

## Phase 2 — Explorer consumption (wired to the distribution plan)

- The Phase-1 public retrieval service in
  [`memory-seed-explorer-distribution-plan.md`](memory-seed-explorer-distribution-plan.md) surfaces,
  per entry: any sidecar diagram(s) and the Class-1 structural fields.
- The Explorer reader view renders an entry's Class-2 sidecar(s) beside the entry, and overlays the
  live Class-1 provenance (`superseded_by`, inbound/outbound edges, commit links).
- Read-only; entry remains the canonical deep-link target (per the entry-level UI results plan).

### Phase 2 acceptance criteria

- Opening an entry that has a sidecar renders the diagram; opening one without a sidecar renders
  normally (no empty frame, no error).
- Class-1 overlays reflect current graph state even on entries whose frozen Class-2 diagram predates a
  later supersession.
- Retrieval parity: the sidecar surfacing goes through the shared service, not a forked reader.

## Phase 3 — Exportable report / handover pack (paid backbone, gated)

The uniform, non-technical-facing deliverable and the one genuinely new Class-1 artifact.

- A static, shareable bundle (HTML and/or PDF/Markdown+images) generated from a project's memory:
  timeline, decision graph, per-decision provenance cards, and any authored Class-2 sidecars for the
  covered entries.
- This is the paid "project handover pack / exportable timeline / branded report" tier from the
  market-fit report — positioned in the Explorer product, not core.
- Gated on the Explorer distribution (distribution-plan Phase 2) and on an explicit product decision;
  scope its acceptance criteria when that tier is greenlit.

### Phase 3 acceptance criteria (to be firmed at greenlight)

- Export is deterministic and reproducible from the Markdown source (no authoritative state in the
  export).
- The pack renders for a non-technical reader without a running server (self-contained).
- Class-1 views in the pack are current as of export time; embedded Class-2 sidecars are shown as the
  point-in-time records they are.

## Provenance

- Conversation 2026-07-05 (JNL): the Mermaid-in-logs question → the two-class realization → the
  no-LLM-can't-derive-from-prose constraint → the sidecar-at-entry-time mechanism.
- Paid handover/report framing: `docs/inbox/memory-seed-market-fit-report.md` (paid tiers) and
  `docs/inbox/memory-seed-market-fit-visual-appendix.md` (Diagram 11, Lense as commercial wedge).
- Class-1 substrate and canonical reader: [`../graph-edge-contract.md`](../graph-edge-contract.md).
- Consumers: [`memory-seed-explorer-distribution-plan.md`](memory-seed-explorer-distribution-plan.md),
  [`memory-explorer-entry-level-ui-results-plan.md`](memory-explorer-entry-level-ui-results-plan.md).
