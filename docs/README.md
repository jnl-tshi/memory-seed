# Memory Seed docs — lifecycle map

> **Above the lanes:** [`CONSTITUTION.md`](CONSTITUTION.md) is the project's governing document — vision,
> invariants, principles, trust model. Specs and plans conform to it, not the other way round. **Ratified
> v1.0 (2026-07-14), amended to v1.1 (2026-07-16), v1.2 (2026-07-17) and v1.3 (2026-07-19).** v1.1 permits
> partitioned authority across append-only Markdown entries and narrowly scoped Markdown sidecars while every
> index and snapshot remains derived; v1.3 requires every write to memory to pass identical validation on any
> surface. B0b Trail parity remains the current product gate.

This is the front door to `docs/`. **The folder a document lives in *is* its lifecycle state** — you can
see the state of everything by browsing the tree, without opening files. YAML frontmatter only carries
what a folder can't (priority, next action, blocked-by, pointers). Each lane's `README.md` renders its
contents as a table so you never have to scan YAML.

Design + rationale: [`2_Todo/document-lifecycle-system-plan.md`](2_Todo/document-lifecycle-system-plan.md).
This front door and the lane folders are **Phase 1** of that plan. **Phase 2 is complete (2026-07-17)**:
the legacy `2_Todo/completed/` archive is retired into `5_Completed/`, `memory-seed docs check` enforces
links/pointers/bindings (also via `esr` and CI), and `memory-seed docs index` generates each lane's
README table and the front-door counts below — only marker-scoped regions are ever regenerated.

## Lanes

**Flow lanes** — a document moves through these:

| Folder | Holds |
|---|---|
| [`1_Inbox/`](1_Inbox/) | raw, untriaged captures |
| [`2_Todo/`](2_Todo/) | active + approved work (blocked items stay here, flagged in YAML) |
| [`5_Completed/`](5_Completed/) | shipped / applied work |
| [`6_Rejected/`](6_Rejected/) | dead-end proposals, kept for the *why-not* (never deleted) |
| [`7_Superseded/`](7_Superseded/) | replaced documents (each carries a `superseded_by` pointer) |
| [`8_Deferred/`](8_Deferred/) | parked / long-horizon ideas |

**Type lanes** — durable references, entered when relevant (not a later "stage"):

| Folder | Holds |
|---|---|
| [`3_Spec/`](3_Spec/) | **live, normative** contracts. `3_Spec/draft/` = candidates (not yet binding); `3_Spec/deprecated/` = retired, kept |
| [`4_Reference/`](4_Reference/) | source material. `4_Reference/archived/` = sources whose actionable items were extracted |

> The numbers give a stable sort, not a strict order: `3_Spec`/`4_Reference` keep their numbers for path
> stability (many docs, tests, and links reference those paths). Read the lane names, not the digits.

## How a document moves

- **Inbox → Todo:** the user approves a captured idea; add `priority` + `next_action`.
- **Todo → 5/6/7/8:** on completion, move to the lane that states the outcome — `5_Completed` (shipped),
  `6_Rejected` (declined — keep it, don't `git rm`), `7_Superseded` (replaced, set `superseded_by`), or
  `8_Deferred` (parked). Blocked stays in Todo with `blocked_by`.
- **Spec:** a contract starts in `3_Spec/draft/` (candidate) and moves to `3_Spec/` when adopted as
  normative; retired contracts go to `3_Spec/deprecated/` with `deprecated_by`.
- **Reference:** a source becomes `4_Reference/archived/` once its actionable items are pulled into a
  plan/spec (`extracted_into`).

## Naming

`<topic>-<kind>.md` where `<kind>` ∈ `proposal | plan | spec | contract | report | evaluation`. Session
work and agent-namespaced branches/worktrees follow the policy shipped in
[`5_Completed/agent-worktree-and-branch-hygiene-plan.md`](5_Completed/agent-worktree-and-branch-hygiene-plan.md).

## Current Memory Trace status

The B0a shell, renderer-neutral fixture contract, and complete renderer evidence harness are implemented.
JNL selected Cytoscape 3.34.0 on 2026-07-16, and the React `/next` workspace now carries the accepted
graph, search, selection, and Inspector behaviour over the renderer-neutral projection. React diagram
rendering shipped 2026-07-20 (the Arc-2d flowchart/sequence-diagram engine ported to `arc2d.ts` +
`DiagramView.tsx`). React Trail parity, the Trail transition, evidence-backed topology/file/evolution
modes, and final accessibility/scale acceptance remain open. The vanilla SVG graph and Trail remain the
fallback until explicit B0b parity sign-off.

## Side-folder allowlist

Non-lane folders that are legitimate, with a reason:

This table must stay in sync with `SIDE_FOLDER_ALLOWLIST` in `memory_seed/docs_check.py` — the code is
what enforces it; anything here that the code does not list is a hard `off-allowlist-folder` error.

| Path | Reason | Action |
|---|---|---|
| `5_Completed/agent-templates/` | persona template sources | keep (nested reference) |
| `4_Reference/memory-trace-phase0-baseline/` | captured baseline artifacts | keep |
| `4_Reference/archived/` | sources whose actionable items were extracted; each carries `extracted_into` | keep |
| `3_Spec/draft/` | candidate contracts, not yet binding (`spec_binding: draft` or `candidate`) | keep |
| `3_Spec/deprecated/` | retired contracts kept for provenance (`spec_binding: deprecated`) | keep |
| `4_Reference/trace-humanised-dashboard-references/` | generated Trace design mockups cited by the Living Archive proposal; raw captures archived 2026-07-20 | keep |

> The two `1_Inbox/memory-seed-*-proposals/` entries were removed 2026-07-20 when both sets were retired
> to `7_Superseded/`. Superseded documents sit flat in their lane, so no replacement entry is needed.
> `1_Inbox/trace-humanised-dashboard-references/` moved to `4_Reference/` the same day, once its
> mockups were confirmed fully triaged (extracted themes recorded, actively cited by a `2_Todo/`
> proposal) rather than awaiting further design decisions — Inbox holds untriaged captures, not
> reference material for already-scoped work.

> `2_Todo/completed/` was retired 2026-07-17: its 43 documents and the nested `agent-templates/` moved to
> `5_Completed/`, so the folder-is-the-state rule now holds with no legacy archive beside it.

> `2_Todo/Claude/` and `2_Todo/codex/` (the per-agent proposal-synergy reviews) were reconciled 2026-07-14:
> both were spent 2.13-era snapshots, moved to `7_Superseded/`, and the empty folders removed.

Anything not on this list should be a lane or listed here; `memory-seed docs check` enforces it.

## Current state (generated by `memory-seed docs index`)

Every terminal document sits in a lane (the Phase 2 bulk migration retired `2_Todo/completed/` on
2026-07-17), so the folder-is-the-state rule holds with no legacy archive beside it. Constitution v1.1
records the append-only Markdown sidecar authority boundary; v1.2 the human-gated one-off exception for
untyped `related_entries` curation. The counts below are generated — hand-edits inside the markers are
overwritten on the next `docs index` run.

<!-- docs-index:begin -->
Counts (Markdown files directly in each lane, lane `README.md` excluded): 1_Inbox 0 · 2_Todo 24 · 3_Spec 8 · 4_Reference 16 · 5_Completed 60 · 6_Rejected 0 · 7_Superseded 28 · 8_Deferred 4

Top open items (P0/P1 in `2_Todo/`):
- **P1** [derived-projection-implementation-plan.md](2_Todo/derived-projection-implementation-plan.md) — Phase 1 SHIPPED 2026-07-15 (warm start + atomic swap + perf). Remaining fast-follow (deferred, low-urgency) = incremental ingest, gated on …
- **P1** [memory-provenance-and-authority-taxonomy-proposal.md](2_Todo/memory-provenance-and-authority-taxonomy-proposal.md) — Steps 5–6 (GATED on the participant/role model + a user go): implement actionability as a policy result with reason codes; add fail-closed …
- **P1** [memory-quality-metrics-v0-proposal.md](2_Todo/memory-quality-metrics-v0-proposal.md) — JNL reviews docs/4_Reference/memory-quality-v0-baseline.md. Only then propose targets, ESR surfacing, further metrics, or §8 graduation.
- **P1** [memory-seed-semantic-record-and-signal-foundation-plan.md](2_Todo/memory-seed-semantic-record-and-signal-foundation-plan.md) — Prove the append-only ADR sidecar contract on three existing decisions after B0b Trail parity and the BG1 provenance crosswalk.
- **P1** [memory-trace-graph-and-workspace-proposal-set-index.md](2_Todo/memory-trace-graph-and-workspace-proposal-set-index.md) — —
- **P1** [memory-trace-graph-visualisation-and-temporal-topology-proposal.md](2_Todo/memory-trace-graph-visualisation-and-temporal-topology-proposal.md) — —
- **P1** [memory-trace-structural-graph-enrichment-provider-proposal.md](2_Todo/memory-trace-structural-graph-enrichment-provider-proposal.md) — —
- **P1** [memory-trace-three-region-workspace-and-dockable-inspector-proposal.md](2_Todo/memory-trace-three-region-workspace-and-dockable-inspector-proposal.md) — —
<!-- docs-index:end -->
