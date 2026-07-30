---
title: "Memory Trace UX reference-model implementation plan"
date: "2026-07-30"
project: "memory-seed"
status: "active"
priority: "P1"
next_action: "Implement M1 decision reader and evidence-return path against memory-trace-ux-m0-interaction-matrix.md."
source: "JNL-supplied UX reference model (2026-07-30); existing Memory Trace plans and specifications"
---

# Memory Trace UX Reference-Model Implementation Plan

Status: **Active proposal in `2_Todo`** (2026-07-30).
Priority: **P1**, sequenced behind no prerequisite other than preserving the active Trace parity gates.
Source: JNL supplied a UX reference model that positions Memory Trace as a decision-history workbench. Its
product comparisons are design inputs, not independently validated product claims or copied product
requirements.
Scope: Reconcile and implement the remaining Memory Trace interaction changes implied by that model:
Trail history orientation; decision-first inspection and exact evidence navigation; bounded graph
perspectives; keyboard-first discovery; and a deterministic resume/attention view.
Non-goals: Rebuild GitLens, Obsidian, NotebookLM, Neo4j Bloom, Linear, or any other reference product;
add a second authoring system; make a global graph the default; hide source evidence behind generated prose;
or change canonical session, sidecar, decision, or graph-edge semantics.
Dependencies: [`../3_Spec/memory-trace-trail-search-and-graph-ux.md`](../3_Spec/memory-trace-trail-search-and-graph-ux.md),
[`memory-trace-product-and-system-architecture-blueprint.md`](memory-trace-product-and-system-architecture-blueprint.md),
[`memory-trace-next-generation-implementation-roadmap.md`](memory-trace-next-generation-implementation-roadmap.md),
[`memory-trace-graph-and-workspace-proposal-set-index.md`](memory-trace-graph-and-workspace-proposal-set-index.md),
and the renderer-neutral graph and provenance specifications.
Acceptance criteria: Each implemented increment is fixture- and accessibility-gated, preserves exact
Markdown/Git provenance and the active Trail parity contract, and exposes whether displayed information is
recorded, derived, or suggested.

## 1. Purpose and decision

Memory Trace should become easier to understand by borrowing familiar **interaction grammar**, not by
becoming a clone of another product:

| Reference role | Memory Trace interpretation | Deliberate boundary |
| --- | --- | --- |
| Git history workbench | Trail is the default chronological orientation surface; branch, worktree, fork, and merge provenance are immediately legible. | Trace is not a Git client and must not rewrite Git or memory history. |
| Developer workbench | Stable navigation, central workspace, and persistent inspector; keyboard conventions are predictable. | Layout state is a disposable local preference, never project memory. |
| Linked knowledge workspace | A selected decision has local relationships, source context, and controlled expansion. | Markdown entries and their sidecars remain authoritative; Trace is read-only. |
| Evidence reader | Claims lead to the exact source slice and back again without losing the current Trail context. | Generated summaries remain visibly distinct from source text. |
| Graph exploration tool | Start from a selected decision, topic, or query; use perspectives, legends, filters, and deliberate expansion. | No unbounded global graph or renderer-owned semantics. |
| Focused activity view | Help a returning user resume work and find deterministic follow-up conditions. | Do not turn Trace into task management, an agent controller, or an opaque recommendation feed. |

The decision is to make this model an **implementation crosswalk** for the existing Trace programme.
It does not supersede the active Trail/search/graph specification, architecture blueprint, or graph/workspace
proposal set. Where those documents already define a behaviour, this plan uses it as the contract; where the
reference model exposes a gap, this plan supplies the next testable increment.

## 2. Constitutional fit and non-negotiable guards

This proposal is conformant only under the following rules.

1. **Trace is a derived, local-first experience layer.** Markdown entries, append-only sidecars, and Git
   remain the authority. Viewport positions, layout choices, clusters, cached results, and inferred
   relationships are rebuildable projections.
2. **The decision is the primary reading target; the entry is durable context.** A decision cannot be
   detached from the entry, author, time, branch, and evidence that establish its provenance.
3. **Authority must be visible.** Every material claim is labelled as recorded (first-hand), derived
   deterministically, or suggested/reconstructed. A confidence value alone is insufficient.
4. **Evidence is navigable.** The UI links to the exact Markdown file, decision slice, heading, or source
   artefact that supports a claim. It must not silently substitute a generated summary for that source.
5. **Chronology and semantic lineage have separate visual grammars.** Git/worktree/merge lanes show where
   work happened; `replaces`, `evolves`, and related edges show what decisions mean. Neither can imply the
   other.
6. **Live history remains discoverable.** Superseded or low-ranked material may be dimmed or filtered only
   by an explicit user control; it is never deleted from canonical retrieval.
7. **The core stays model- and vendor-neutral.** Any later assistance is optional, evidence-bound, and must
   not decide or write authoritative memory by itself.

These guards directly apply Constitution invariants 1–7 and its evidence, integration, immediate-value, and
minimal-sufficient-context principles. They are acceptance gates, not visual aspirations.

## 3. Baseline and reconciliation

The active UX specification already establishes the important spine: Trail first; search navigates into Trail
neighbourhoods; a three-region workspace; shared selection; graph as specialised bounded exploration;
keyboard and accessibility parity; and exact provenance classes. The graph/workspace programme also already
requires renderer-neutral semantics and treats layout state as derived.

This plan therefore does **not** reopen those decisions. It turns the following remaining interpretation
gaps into an explicit build sequence:

| Existing contract | Implementation clarification from the reference model |
| --- | --- |
| Trail is primary and has branch/merge lanes. | Long histories need a continuously visible main/trunk spine, a clear range/minimap model, highlight-before-filter behaviour, and retained selection while filters change. |
| Inspector is a document/evidence workspace. | It needs an explicit decision reader: decision, rationale, consequences, lifecycle, evidence, then surrounding session context. |
| Graph starts local and is bounded. | Area and Activity become named perspectives that apply consistently to graph grouping, Trail filters, search suggestions, and decision badges. |
| Search navigates from ranked results to Trail. | Quick Open, structured historical query, and UI command modes must be distinguishable and show their applied criteria rather than silently translating them. |
| Shared selection spans Trail, graph, and inspector. | A selection must stay anchored through source navigation, filter changes, and local graph expansion. |

The current B0/B0b parity and accessibility/scale gates remain authoritative. Before an implementation slice
starts, its owner must update the roadmap and coverage matrix with the actual delivered baseline rather than
relying on status prose that may lag a merged branch.

## 4. Implementation sequence

### M0 — interaction contract reconciliation and fixture matrix (**delivered 2026-07-30**)

Create one implementation matrix that maps each existing behaviour and each new clarification to: its
authoritative input, API/projection field, UI surface, keyboard/a11y expectation, fixture, and acceptance
test. It must explicitly mark an item as delivered, parity-gap, proposed, or deferred.

Freeze the shared terms: **Trail**, **Graph**, **Inspector**, **Reader**, **Quick Open**, **structured
search**, **recorded**, **derived**, and **suggested**. Resolve wording conflicts in the active candidate UX
specification before implementation rather than letting individual components invent meanings.

Exit criteria:

- No M1–M5 ticket relies on an unstated data owner or renderer-specific semantic field.
- The matrix names a deterministic fixture for every provenance-state and cross-view selection claim.
- The roadmap, coverage matrix, and this plan agree on what is delivered versus only designed.

Delivery: [`memory-trace-ux-m0-interaction-matrix.md`](memory-trace-ux-m0-interaction-matrix.md)
freezes the shared terminology, named inputs, and fixture gaps. M1 is now the next actionable slice.

### M1 — decision reader and evidence return path

Build the inspector's decision-first reading mode around one stable decision identity. Present, in order:

1. decision title and recorded metadata (date, branch/worktree, author/agent context, state);
2. the decision, rationale, and consequences from its entry;
3. predecessor, successor, and typed related items;
4. evidence links with exact anchors and source provenance; and
5. the surrounding session entry and sibling decisions as context.

Opening an evidence target must preserve a return path to the originating decision and its Trail scroll
position. Raw Markdown must remain reachable. If an evidence excerpt is unavailable, the UI reports the
missing source condition rather than manufacturing a summary.

Exit criteria:

- Keyboard-only users can enter, inspect, follow evidence, and return without losing selected decision or
  Trail position.
- Every displayed lifecycle or evidence assertion identifies its source and state class.
- Reader tests cover a multi-decision entry, an external/generated event, a missing source, and a
  superseded decision.

### M2 — Trail history orientation and filtering

Complete the history-inspection behaviours that make the Trail feel familiar without reducing it to a Git
log:

- Keep the direct `main`/trunk integration spine visible across all in-range trunk entries and merge events.
- Show a stable legend that distinguishes provenance topology from semantic overlays.
- Make the default search result highlight matches in their chronological neighbourhood first; offer an
  explicit “show matches only” mode afterwards.
- Retain the selected entry/decision and announce changes when range, branch/worktree, or topic filters
  change.
- Add long-history orientation only after scale evidence: match markers and a minimap/range indicator must
  use the same canonical result window as the rows.

Exit criteria:

- Fixtures cover direct-main events newer than a merge, divergent worktrees, merge return, and a filtered
  selected decision.
- No semantic relation is rendered as a branch lane or inferred as chronology.
- Virtualisation and incremental loading retain graph-lane continuity and keyboard focus.

### M3 — bounded graph perspectives and controlled expansion

Make **Area** and **Activity** first-class perspectives, not cosmetic filters. A perspective changes the
grouping and vocabulary shown in graph navigation while preserving the same selected decision identity and
underlying edge semantics.

The default graph remains one-hop and local to a selected decision, topic, document, or search result.
Users can expand deliberately, choose relationship/node/date filters, inspect a legend, and return to the
corresponding Trail anchor. Overview/global mode remains gated on density, performance, and a usable
non-canvas equivalent.

Exit criteria:

- Perspective changes do not mutate, hide, or recategorise canonical memory; they only choose a derived
  lens.
- Each node and edge exposes type, state/authority, source, and a list/table equivalent.
- Expansion preserves selection and has an accessible non-visual route to the same neighbourhood.

### M4 — Quick Open, structured search, and commands

Separate three familiar entry points while sharing one transparent query model:

| Entry point | Purpose | Required transparency |
| --- | --- | --- |
| Quick Open | Jump to a decision, entry, topic, or artefact. | Show object type and exact target before opening. |
| Structured search | Find historical material with terms and filters such as topic, area, activity, branch, worktree, date, lifecycle, and confidence/state. | Render every applied criterion as a visible chip or query token. |
| Command palette | Invoke read-only navigation, layout, and view actions. | Do not disguise a query or AI interpretation as a command result. |

Natural-language assistance, if later added, may propose a visible structured query but must require the
user to see and edit that query before it changes scope. Chat is not the landing surface and cannot conceal
the retrieval route.

Exit criteria:

- Exact decision IDs resolve directly.
- Search result semantics follow the active search-to-Trail contract rather than opening an isolated default
  results page.
- All primary discovery actions are keyboard-operable and announced accessibly.

### M5 — deterministic resume and attention

Add a small home/resume surface only after the previous views supply the needed deterministic facts. It may
show last viewed decision, current worktree/branch, most recent session, decisions added since the last
visit, and inspection-worthy conditions such as broken evidence references, conflicting lifecycle states,
unfused worktree memory, or unvalidated suggestions.

“Needs attention” must be a stated rule with its underlying evidence, not an LLM judgement or a hidden
priority score. The view remains an optional orientation surface; Trail stays the default project-history
view.

Exit criteria:

- Every attention item exposes its deterministic rule, source, and remediation destination.
- No local layout/visit state is written into canonical project memory without an independently approved
  write contract.
- The surface is useful with no network, model provider, or hosted account.

## 5. Cross-cutting implementation rules

### Selection and navigation

All views use a shared `entry_id` plus decision locator, not a copied summary object. Navigation from graph,
search, evidence, and reader resolves through this identity and preserves enough return state to restore the
originating Trail or graph neighbourhood.

### Information-state grammar

Use text, icon/shape, and accessible label together—never colour alone:

| State | Meaning | UI treatment |
| --- | --- | --- |
| Recorded | First-hand value stored in canonical Markdown/sidecar at write time. | Canonical-source label and direct source link. |
| Derived | Deterministically calculated from canonical data or repository facts. | Calculation/source-revision label. |
| Suggested | Reconstructed or model-assisted candidate awaiting validation. | Explicit suggestion label, evidence, and no authoritative styling. |

### Performance and offline capability

Implement with bounded data windows, stable scroll anchors, rebuildable derived caches, and progressive
loading. No milestone may require a hosted service, external search provider, or model call to make the
core Trail, graph, or reader useful.

### Accessibility and test discipline

Every canvas/graph capability needs a list/table or inspectable equivalent. Preserve focus across panes;
honour reduced motion; announce dynamic search/filter changes; test dense mode at browser zoom. Visual
polish is accepted only after semantic, keyboard, and fixture parity pass.

## 6. Explicit disagreements and deferred ideas

| Reference-model idea | Disposition | Reason |
| --- | --- | --- |
| Copy a full GitLens-like graph workbench. | Narrowed. | Trail adopts understandable history conventions, but Memory Trace must remain a decision/evidence reader rather than a Git client. |
| Default to a complete global graph. | Rejected for default use. | It conflicts with bounded, explainable retrieval and has not met density/performance/a11y gates. |
| Treat workspace/pane state as shared knowledge. | Rejected. | It is a local, derived preference, not canonical project memory. |
| Use generated summaries as the primary evidence view. | Rejected. | This would weaken direct attribution and makes a derived claim look recorded. |
| Use chat as the home experience. | Rejected. | It hides retrieval choices and provenance; Trace must expose inspectable structure first. |
| Add an AI “attention” ranking. | Deferred. | Deterministic evidence rules must be proven and visible before any optional suggestion layer is considered. |
| Reuse external product names as technical dependencies. | Rejected. | The project needs vendor-neutral, local-first implementation and licensing/security review for any future dependency. |

## 7. Delivery and governance

M0 is complete. Each later milestone should become a bounded implementation ticket only after its named
fixture and acceptance gate are attached. A milestone is
not complete merely because the interface resembles a reference product: it must pass the five-question
test.

| Question | Delivery evidence |
| --- | --- |
| Capture | No milestone adds an unvalidated authoring path; canonical inputs and their owners are named. |
| Validation | Fixtures, a11y checks, scale checks, and source/identity assertions pass. |
| Retrieval | The user can find the intended decision/evidence with a transparent scope and local fallback. |
| Trust | Recorded, derived, and suggested information are distinguishable and source-linked. |
| Application | A user can return to context, compare lineage, and act on the result without losing provenance. |

When a milestone ships, update the next-generation roadmap, coverage matrix, relevant proposed specification,
and this plan's status or successor pointer in the same change. If a behaviour requires a new canonical
field or a write path, stop and create a separate authority-contract proposal first; this UX plan does not
authorize it.

## 8. Provenance

- JNL-supplied “Jakob's Law in UX” reference-model conversation, 2026-07-30. The content was used as
  product-direction input; product-specific claims have not been independently relied upon here.
- [`../3_Spec/memory-trace-trail-search-and-graph-ux.md`](../3_Spec/memory-trace-trail-search-and-graph-ux.md)
  — current proposed Trail/search/graph interaction contract.
- [`memory-trace-product-and-system-architecture-blueprint.md`](memory-trace-product-and-system-architecture-blueprint.md)
  — authoritative/semantic/projection/experience-layer boundary.
- [`memory-trace-graph-and-workspace-proposal-set-index.md`](memory-trace-graph-and-workspace-proposal-set-index.md)
  — graph/workspace constitutional and renderer-neutral requirements.
- [`../CONSTITUTION.md`](../CONSTITUTION.md) — constitutional invariants, principles, and five-question test.
