# Next Steps

Status: Forward-looking plan (release history lives in `CHANGELOG.md`; this file is the *what's next*).
Updated: 2026-07-14
Source: the `docs/` lifecycle lanes (folder = state — see [`../README.md`](../README.md)), `CHANGELOG.md`,
and `docs/3_Spec/`. Rebuilt 2026-07-14 from a full inbox+todo evaluation (per-doc status verified against
CHANGELOG + code, not this file's prior claims).

## Current state

- **Released: v2.18.0.** A large tranche is **shipped-but-unreleased on `main`** — see `CHANGELOG.md`
  "## Unreleased" for the authoritative list (highlights: DRAFT-format entry lint; `integration_mode`
  setting; freshness-aware `memory_search` ranking on by default + `evolved_head`; retrieve-the-*why*
  discipline; indexed `topics:` end-to-end incl. Trace rendering; decision-diagram badges in Trail/Graph;
  agent worktree namespace guard; MCP topic + sidecar-edge parity; hardened Memory-Entry trailer hook;
  `link show` now reflects the sidecar-augmented effective graph).
- **Doc lifecycle:** the folder a doc sits in *is* its state. This refresh moved the terminal docs into
  `5_Completed/` / `7_Superseded/` / `8_Deferred/`; only docs with live work remain in `2_Todo/`.
- **A release cut (2.19) is due** to publish the Unreleased tranche — hold for the user's go (no unprompted
  release).

## Live work — sequenced

Active/approved work with a real remaining tail. Each links its plan. **Recommended order; awaiting your
go before starting a major track.**

### Track A — close the open tails (small, finish-what-shipped)

1. **`integration_mode` Phases 2–4** — [`configurable-integration-mode-plan.md`](configurable-integration-mode-plan.md).
   P0.1 (setting + reader + `esr` surfacing) shipped; remaining: the agent contract reads/obeys the mode
   (skills/agent-rules), PR/`session integrate` tooling, and a bootstrap heuristic. *Unblocks OpenSSF.*
2. **`topics suggest --from <file>`** — [`memory-trace-topic-neighbourhoods-plan.md`](memory-trace-topic-neighbourhoods-plan.md).
   The single named item left before that plan is fully done (Phases 0–4 shipped).
3. **Evolution-edges continuity display in Trail** — [`evolution-edges-plan.md`](evolution-edges-plan.md).
   P1 + lineage-seeding shipped (2.18.0); the last sub-item of the Trace lineage pass — render
   `continuity:` chains as a Trail display axis — is unbuilt.
4. **Related-entries P2** — [`related-entries-p2-mutation-plan.md`](related-entries-p2-mutation-plan.md).
   Approved 2026-07-05, unbuilt: controlled `link add` (current-entry) + explicit historical backfill.
   Sequence after 1–3; it's a convenience increment, not a blocker.
5. **Session decision diagrams Phase 3** — [`session-decision-diagrams-plan.md`](session-decision-diagrams-plan.md).
   Phases 1–2b shipped (sidecars, validation, reader + Trail/Graph badge & zoom viewer). Phase 3
   (exportable report / handover pack) is sizable and **gated on a product greenlight**.
6. **OpenSSF credibility** — [`openssf-credibility-proposals.md`](openssf-credibility-proposals.md).
   `SECURITY.md`, a CI gate, G0–G2. Approved-not-built and **blocked on integration-mode Phases 2–3**.

### Track B — Memory Trace next generation (the promoted direction, 2026-07-11)

Governance (read to sequence, not build): [`memory-trace-product-and-system-architecture-blueprint.md`](memory-trace-product-and-system-architecture-blueprint.md)
(entry point) → [`memory-trace-next-generation-implementation-roadmap.md`](memory-trace-next-generation-implementation-roadmap.md)
(Phase 0–10 spine; Phases 0–1 delivered) → [`memory-trace-next-generation-coverage-matrix.md`](memory-trace-next-generation-coverage-matrix.md).

- **B1 — Evidence Pack Builder** *(startable now, small, backend-only)* —
  [`memory-trace-ai-timeline-summarisation-plan.md`](memory-trace-ai-timeline-summarisation-plan.md) Phase 1.
  `build_timeline_evidence_pack()`: deterministic JSON over the already-delivered retrieval/graph readers,
  snapshot-tested, **no write path, no provider**. Owns the near-term "Evidence Pack" implementation; the
  canonical shape is the spec [`../3_Spec/memory-trace-derived-artifact-provenance-contract.md`](../3_Spec/memory-trace-derived-artifact-provenance-contract.md)
  (blueprint §4.5 and the evidence-annotations doc are forward supersets — do not build a second builder).
- **B2 — React/Vite shell** *(the strategic bet — needs your greenlight)* —
  [`memory-trace-frontend-architecture-and-design-system-proposal.md`](memory-trace-frontend-architecture-and-design-system-proposal.md)
  (roadmap Phase 2). First increment before any component work: stand up the Vite/TS workspace whose
  **built** assets serve from the wheel with **zero Node at runtime** — proving the packaging spine.
  Gated by the `3_Spec` parity fixtures + vanilla fallback. The current vanilla `/api/*` + `app.js` Trail
  stays the shipped UI until parity is proven.
- **B3 — Evidence annotations & projection** *(long-horizon, after B2)* —
  [`memory-trace-evidence-annotations-and-projection-architecture.md`](memory-trace-evidence-annotations-and-projection-architecture.md).
  Anchors, append-only annotations, SQLite projection — needs the React shell **and** a participant/role
  model first.

## Captured proposals — awaiting your approval (`1_Inbox/`)

Raw, unbuilt, each a genuine gap (verified: none redundant with shipped work). Approve to promote into a
Track above.

- [`supersession-successor-surfacing-proposal.md`](../1_Inbox/supersession-successor-surfacing-proposal.md)
  — `superseding_head`, the symmetric mirror of the shipped `evolved_head` (retired→its replacement).
- [`real-corpus-ranking-validation-gate-proposal.md`](../1_Inbox/real-corpus-ranking-validation-gate-proposal.md)
  — durable `ranking-ab` tooling + a graph-edge-contract rule (the flip's A/B was run once, ad hoc).
- [`lifecycle-link-authoring-assist-proposal.md`](../1_Inbox/lifecycle-link-authoring-assist-proposal.md)
  — `link audit --apply` scaffold (audit is read-only today).
- [`worktree-gc-proposal.md`](../1_Inbox/worktree-gc-proposal.md) — a `worktree gc` command (the namespace
  guard shipped; removal/GC did not).
- [`agent-namespaced-branch-worktree-lifecycle-proposal.md`](../1_Inbox/agent-namespaced-branch-worktree-lifecycle-proposal.md)
  — session-scoped-worktree / task-owns-branch naming scheme + enforcement (practice is still mixed).

## Doc-lifecycle Phase 2 (housekeeping)

Tracked in [`document-lifecycle-system-plan.md`](document-lifecycle-system-plan.md) (Phase 1 — lanes +
front door — shipped): the `docs index` / `docs check` CLI, bulk-migrating the 43 `2_Todo/completed/`
docs into `5_Completed/`, and removing the empty `superpowers/specs/`.

## Parked — needs your judgement / market / accounts (not engineering next-steps)

- [`8_Deferred/memory-trace-commercialisation-and-monetisation-report.md`](../8_Deferred/memory-trace-commercialisation-and-monetisation-report.md)
  — pricing/tiers; needs usage + market validation before any build.
- [`8_Deferred/memory-trace-hosted-product-and-security-architecture.md`](../8_Deferred/memory-trace-hosted-product-and-security-architecture.md)
  — hosted/team tier; needs commercial + billing/auth decisions and a later security review.
- **MCP client validation** — register in a client and confirm the agent calls `memory_search` before
  answering; record client-specific setup. Command: `claude mcp add memory-seed -s user -- uvx --from
  memory-seed memory-seed-mcp --stdio`.
- **Launch assets** — real terminal screenshot/GIF (`init`, mcp-validate, a memory lookup) to replace the
  README S6 placeholders; decide the launch-note audience.
- **Optional semantic extra** — decide whether to add `memory-seed[semantic]` (Model2Vec embeddings);
  keep the default path dependency-light unless it shows clear value.
- **Community feedback** — watch agent-compatibility issues across Codex/Claude/Gemini/Copilot clients.

## Discipline

- **Releases:** never cut/publish without the user's explicit go; the PyPI push is a manual-approval gate.
- **Ranking:** keep `main` behavior stable; run ranking experiments on a branch, merge only if fixtures
  show a clear win with no text-ranking regression.
- **Branches/worktrees:** non-trivial work on `claude/<kind>/<topic>` → merge to local `main` → delete;
  writing agents stay in their own `.<agent>/worktrees/` namespace (guard enforced).

## Continuity naming

- **Memory Seed** — core runtime, CLI, MCP, retrieval, validation, session files.
- **Memory Trace** — companion package + human review UI (`pip install "memory-seed[trace]"`, `memory-trace`).
- **Trail** — the Memory Trace view for branch/supersession/evolution.
- **Lense** — legacy compatibility name only. **Explorer** — historical working name only.
