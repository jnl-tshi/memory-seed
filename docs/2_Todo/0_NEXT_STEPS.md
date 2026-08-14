# Next Steps

Status: **ACTIVE — Constitution-aligned** (v1.0 ratified 2026-07-14; current v1.9 ratified 2026-08-13).
Updated: 2026-08-14

> ▶ **Foundation and memory-quality core shipped 2026-07-15.** The
> [derived-projection Phase 1](derived-projection-implementation-plan.md) (git-watermark warm start +
> atomic swap + three read-path perf refinements) **shipped 2026-07-15** — the plan's former "do first"
> foundation is done. Work still sequences *under* [`docs/CONSTITUTION.md`](../CONSTITUTION.md) **v1.9**
> (each item answers the five-question test — Capture / Validation / Retrieval / Trust / Application — and
> respects Invariant #6: Markdown = source of truth; every DB/cache is a derived, rebuildable projection).
> **v1.3 (2026-07-19)** amended Invariant #2 with write-surface parity: any surface that writes session
> memory must run the same validation as every other, which is what permitted — and constrains — the
> gated MCP write path below. **v1.5 (2026-07-26)** retired the v1.4 diagram-repair carve-out (an append
> path made the exception unnecessary) and ratified the *minimal but sufficient context* principle.
> **v1.6 (2026-07-26)** settled provenance as **first-hand vs reconstructed** rather than human-vs-machine
> — every YAML topic/edge in this corpus was agent-chosen, so the real distinction is who observed the
> fact directly — and is what the new topic-sidecar authority (below) is built on.
> **v1.9 (2026-08-13)** is the first *evolution-class* bump rather than an amendment: §8 was corrected to
> name the shipped `memory-seed quality report` instrumentation (it had claimed named quality metrics were
> untracked), and §11 gained a rule distinguishing a correction from an amendment — a correction bumps the
> minor version, earns a marked version-log row, and **may never change a requirement**. The §8 clause
> stays `[candidate]`: correcting a decayed sentence is deliberately *not* the same act as graduating it,
> and graduation still belongs to JNL after the quality-v0 step-6 review (open decision #7 below).
> The ranking/graph core now includes the full-corpus gate, `replacing_head` plus its bounded boost,
> and inert `link audit --apply` scaffolding. **2.20.0 released 2026-08-12** (live on PyPI). **B0a
> graph/workspace contracts and B0b formal accessibility/scale acceptance are complete. The UX
> reference-model sequence delivered M1 Decision Reader and M2 Trail orientation on 2026-07-30, then
> refined the Inspector on 2026-07-31; M3 bounded graph perspectives and controlled expansion is the
> next Memory Trace slice.** The projection's **incremental-ingest fast-follow
> SHIPPED 2026-07-21** — it was the last deferred piece of the derived-projection plan, taken because
> the profile had moved: parsing was no longer the cost, per-history-item git work was
> (44.25 s / 990 git subprocesses → 1.46 s / 7).
> **Two large tranches landed 2026-07-26/27 and 2026-07-28/29** (below, in their own dated sections): a
> two-axis (area/activity) hierarchical topic vocabulary with per-decision declared attribution replacing
> the old flat/derived topic model, and a graph-navigation/physics tranche (ontology tree navigation,
> lifecycle chains spiralling by age, soft crossing-avoidance) plus a new capability — Trace can now open
> any correctly-initialised folder from inside the app, not just switch between this repo's own worktrees.
Source: the `docs/` lifecycle lanes (folder = state — see [`../README.md`](../README.md)), `CHANGELOG.md`,
and `docs/3_Spec/`. Rebuilt 2026-07-14 from a full inbox+todo evaluation; re-baselined 2026-07-15 after the
Foundation shipped (per-doc status verified against CHANGELOG + code, not this file's prior claims).

## Current state

- **Released: v2.20.0 (2026-08-12)** — live on PyPI as both wheel and sdist; see `CHANGELOG.md`
  "## 2.20.0" for the authoritative dated list. Highlights include durable bootstrap-to-ADR
  authority, Constitution-aware control-plane precedence, the React-only Memory Trace frontend,
  memory-grounded consequential conclusions, CLI/MCP review parity, and the reconstructable corpus
  projection cache. The deprecated `memory-seed[lense]` alias and vanilla Trace client are removed.
- **Foundation SHIPPED 2026-07-15:** derived-projection Phase 1 — git-watermark warm start (O(changes)
  freshness, no whole-corpus scan; ~6.2 s rebuild → ~78 ms warm) + atomic build/swap + schema version, plus
  three read-path perf refinements (freshness memoize, chunk memoize, sidecar-first-class freshness):
  `chunk()` 132 ms → 3.9 ms. The **incremental-ingest** fast-follow — the plan's last open piece —
  **shipped 2026-07-21**; the derived-projection plan is now complete.
- **Doc lifecycle:** the folder a doc sits in *is* its state. This refresh moved the terminal docs into
  `5_Completed/` / `7_Replaced/` / `8_Deferred/`; only docs with live work remain in `2_Todo/`.
- **Wave 1 + closeout SHIPPED 2026-07-15:** `topics suggest --from`, deterministic timeline Evidence
  Packs, the Trail continuity axis, `replacing_head` plus the gated boost, all four configurable
  integration-mode phases, and lifecycle-link scaffold steps 1–3.
- **Release cadence:** 2.20.0 is **released** (2026-08-12). The next tranche accumulates under
  `CHANGELOG.md` "## Unreleased"; publishing remains a manual-approval gate at the pypi environment.
- **On `main` since the release, unreleased (2026-08-13):** two control-plane changes, both under
  `CHANGELOG.md` "## Unreleased". **Startup context is now routed by measured session length** — see
  Track C item 4. **Bootstrap-generated runtime indexes are tree-first** — a new project's `index.md`
  must lead with a purpose-annotated repository tree and an expanded `.memory-seed/` tree; a small
  path/purpose/read-when table may clarify non-obvious entry points but cannot replace the trees or grow
  into a file inventory (`mse_vengxdppa52t2yhy`). This is the presentation half of the durable
  bootstrap-to-ADR authority chain that shipped in 2.20.0.
- **Constitution v1.9 ratified 2026-08-13** — see the header block. Evolution-class correction, no
  requirement changed.
- **An evidence programme now exists and is not yet on any track** — the decision-replay pilot, the
  independent-validation brief, the adjudication queue, and the context-derivation preregistration. All
  four are gated on a JNL decision rather than on engineering; see "Evidence programme" below.

## Immediate next step — Memory Trace UX M3

> **Standing, but idle since 2026-07-31 (verified 2026-08-14).** Nothing has superseded M3 and no
> replacement was chosen — it simply has not been worked. The 2026-08-01 → 2026-08-14 stream went to the
> control plane (ADR foundation, bootstrap-to-ADR authority, tree-first indexes, startup context routing),
> the 2.20.0 cut, the harness-engineering comparison, and the evidence programme. No August session
> mentions M3. Treat this section as the next Trace slice to pick up, not as a description of work in
> flight; if the evidence programme's questions matter more than another Trace slice, that is a
> re-sequencing decision to take explicitly rather than by drift.

M0 interaction reconciliation, M1 decision reading/evidence return, and M2 Trail history orientation are
delivered. The 2026-07-31 M1 refinement keeps canonical DRAFT content lightweight: it is recorded by
definition, while recorded/derived/suggested origin treatment is reserved for sidecar or projected
information whose origin can vary. Multi-decision entries now use one equal-weight, scrollable decision
window with a D1/D2 selector.

Implement [`memory-trace-ux-reference-model-implementation-plan.md`](memory-trace-ux-reference-model-implementation-plan.md)
M3 as the next bounded slice:

1. **Delivered:** coordinated Area + Activity facets now persist across Trail and Graph, retain selection,
   use decision-level matching, and reduce choices from the active logical view. Continue M3 by evolving
   the graph presentation of those facets while preserving canonical edge semantics and the existing
   renderer-neutral projection contract.
2. Add previewed, reversible **one-hop expansion** with explicit node/edge counts and bounded growth; do
   not turn the global graph into the default view.
3. Provide a keyboard-operable, non-canvas list equivalent for every expanded neighbourhood and verify
   selection continuity, reduced-motion behaviour, and the named bounded-neighbourhood fixture.

After M3 passes its fixture and accessibility gates, continue to M4 Quick Open/structured discovery.
M5 deterministic resume/attention remains later and must expose a stated evidence rule rather than a
hidden priority score.

**Attention retrieval signal (2026-08-04, capture + exposure shipped):**
[`attention-retrieval-signal-proposal.md`](attention-retrieval-signal-proposal.md) un-defers P2 of the
interaction-frequency plan — MCP fetches (`memory_get_chunk`) are logged and exposed as decayed
`attention_score`/`fetch_count`/`last_fetch` on every retrieval result, read-only. The default-ranking
flip waits on real accumulated usage plus `memory-seed ranking-ab --signal attention` (Retrieval,
Application). Companion proposal:
[`file-touch-decision-surfacing-proposal.md`](file-touch-decision-surfacing-proposal.md) — surface
decisions whose `F:` refs match a file the agent is editing (unbuilt; E7's answer to "records die
because nothing surfaces them").

## Shipped 2026-07-28/29 — unreleased, on local main

Two back-to-back tranches: the graph became explicitly ontology-aware and physically legible, then Trace
gained a capability outside any existing roadmap phase — opening an arbitrary correctly-initialised folder.

- **The ontology becomes the graph's navigation** — the flat "Topics" chip list in the navigation pane
  became a recursive Areas/Activities tree (`TreeView.tsx`, a generic component with no topic knowledge;
  expansion state owned by the caller so switching axis doesn't forget where you were), backed by a new
  `ontology` facet keyed by axis (`{axis: [OntologyNode, ...]}`, the same shape at every depth). Selecting
  a parent implicitly selects its whole subtree.
- **The topic axis is now DECLARED per decision, not derived from `topics.yaml`** — sidecars nest
  `topics: / area: / activity:` structurally, so "one area and one activity per decision" is a shape, not
  a rule someone has to remember to check; decision rows in the graph stop inheriting their entry's rolled
  up topics and can finally show two decisions in the same entry differing by area or activity.
- **Long lifecycle chains wind into a spiral, oldest innermost** — a per-chain radial spring force (not a
  drawn shape) pulls each chain member to the radius its age earns, seeded so the winding direction is
  unambiguous; four real-unit controls (strength, minimum chain length, tightness, winding) replaced a
  single strength-only slider; terminating spurs hang off the spine instead of bending the whole spiral.
  `related` edges then became a SECOND, lower-priority chain kind (tried only over nodes a lifecycle chain
  did not already claim) — gated by a concordance check, since unlike `evolves`/`replaces`, a `related`
  chain's topology carries no promise it tracks chronology; a chain that fails the check stays a plain
  line rather than spiralling dishonestly.
- **The layout leans away from crossing edges** — a bounded, grid-bucketed soft force nudges genuinely
  crossing edges apart every tick (an explicit ideal, not a hard rule — some crossings in dense clusters
  are expected to survive). Overview paging also gained a "Show less" button mirroring "Show more."
- **Trace can open any folder from inside the app** — a new capability, not previously scoped by any
  roadmap phase. A folder-browser modal walks the server's filesystem; opening a folder runs the real
  `doctor()` check (the same one `memory-seed doctor` runs) and only registers it as a switchable project
  if it passes — "correctly initialised" means what it already means elsewhere in this codebase, not a
  lighter existence test. Opened folders join the SAME allowlist git worktrees already use, so every
  existing endpoint (facets/search/graph/trail) serves one with no further backend changes.

### Open follow-ups from this tranche

- One specific chain a session's screenshot circled still does not spiral, deliberately: its topology
  tracks chronology only ~76% of the time (measured), which the concordance gate correctly rejects — the
  gate working as designed, not an unmet request.
- Opened external folders are not persisted across a server restart and there is no "recent folders"
  list; both are straightforward additions to the new registry if wanted.
- Crossing-avoidance strength has no user-facing control and no way to disable it — deliberately kept
  internal until a concrete reason surfaces to expose it.

## Shipped 2026-07-26 (late) / 27 — unreleased, on local main

A full day-plus reworking memory-seed's topic vocabulary into a two-axis, hierarchical model with
per-decision attribution — the topic system's biggest change since it was introduced. Summarized from the
session log, not transcribed from memory.

- **Constitution v1.5/v1.6** — retired the v1.4 diagram-repair exception (an append path made it
  unnecessary) and ratified minimal-sufficient-context (v1.5); settled provenance as first-hand vs
  reconstructed rather than human-vs-machine, since every YAML topic/edge in this corpus was agent-chosen
  (v1.6). A write-time consolidation design was accepted on the same footing: topics/links move from
  entry-YAML into sidecar blocks under one owner, each carrying an explicit `source: write-time|derived`
  field. Derived data may override write-time data only through an explicit, human-reviewed `retracts:`
  — never implicitly on recency alone.
- **The swarm-driven decision-level topic BACKFILL was tried twice and explicitly ABORTED** — two pilot
  runs scored macro-recall 0.583 and 0.613 against a 0.70 gate; zero sidecars were written. A later
  adjudication pass found the scoring denominator itself was ambiguous (a stricter reading scores 0.798),
  but the abort stands on its own terms regardless — what changed was the stated reason, not the verdict.
- **The vocabulary itself was redesigned, not just re-scored**: two axes (`area`/`activity`) with declared
  `parent:` fields, write-time shape validation (one area per decision, parent-cycle detection), colour
  keyed on the root while grouping/filtering read the child, and depth earned by concentration rather than
  capped. 17 new slugs landed (`memory-seed` renamed to `seed-core` with the old name kept as an alias;
  four new area roots split out: `lifecycle-edges`, `topic-vocabulary`, `test-suite`, `docs-lifecycle`).
  Reparenting `graph` under `memory-trace` was proposed, then explicitly WITHDRAWN — measured to add 0
  true positives against 45 false ones.
- **A full decision-level attribution campaign then succeeded where the abandoned backfill failed** — by
  changing the premise: swarm output became curated evidence rather than a scored, auto-applied answer.
  1,030 decision units judged, 2,013 attributions written, 95% carrying both axes. The sidecar became
  **the topic authority**: `_topics()` now reads sidecar → authored → hashtag, in that order, instead of
  unioning sidecar and authored topics — nothing on disk is edited, and it is reversible by design.
- **Two consumer bugs were found and fixed while verifying the sidecar landed correctly**: a
  commit-message hook was stamping ~520 spurious `Memory-Entry:` trailers per sidecar-heavy commit (it
  scanned every entry a sidecar *referenced*, not just entries a commit *authored*); and decision-level
  graph edges were being drawn but silently excluded from the physics simulation (22% of drawn edges, 316
  of 1,463) — they now transfer to their row's anchor entry with de-duplication.

### Open follow-ups from this tranche

- **Topic-family fuse implementation completed on `codex/feature/topic-sidecar-fuse`.**
  `session merge-branch` now parses, plans, applies, chronologically rewrites, and reports topic-sidecar
  blocks with the same `(entry_id, heading timestamp)` identity and append-only safety checks as links
  and diagrams. Landing remains gated by the project's manual merge trigger.
- **Topics have no `retracts:` construct yet** — only links do. Needed for step 1 of the write-time
  consolidation build; not yet built as of this tranche.
- **PROPOSAL (2026-07-29): even the link family's existing fuse has a gap worth closing alongside the
  topic-family build above, not instead of it.** `session merge-branch` silently dropped a branch-side
  edit that converted an existing `classify_pending` stub into a live `evolves:` block - the merge
  reported success and stamped a trailer, but `git show --stat` on the resulting commit showed only the
  session-log entry landed, not the sidecar edit it described. `_plan_session_fuse`'s own code
  (`memory_seed/core.py`, the link-sidecar block-identity loop) appears to intend an explicit
  `existing link sidecar modified for entry_id ...` issue for exactly this case - same-(entry_id,
  timestamp) blocks with different text on each side - which should abort the fuse loudly rather than
  drop it quietly; why it didn't fire here is unconfirmed, not yet root-caused past that first layer.
  Reapplied directly to `main` as a one-off workaround (see `mse_m9kmrztj8kswee35`,
  `.memory-seed/sessions/2026-07-29.md`). The ask, scoped together with the topic-family build: (a) either
  make in-place stub-to-live-edge conversion (the sanctioned `end_of_turn.md` Lifecycle Link Sweep
  workflow) an explicitly RECOGNISED, importable fuse case for every sidecar family, or (b) guarantee the
  refusal is always LOUD, per this project's own 2026-07-21 precedent for exactly this class of
  silent-failure bug. The current synthetic regression correctly refuses the exact stub-to-live edit
  before merge, but the historical real-branch anomaly has not been reproduced or root-caused; do not
  treat the topic-family implementation as resolving that separate investigation.
- Swarm-based topic discovery for a *new* project (not this corpus) remains a design proposal only
  (`docs/2_Todo/topic-discovery-from-evidence.md`), not implemented.

## Shipped 2026-07-21/22 — unreleased, on local main

26 entries across two sessions, grouped by theme rather than transcribed. Verified against the
session log and code, not against this file's prior claims.

- **Memory Trace startup is now incremental** — the derived-projection plan's last deferred piece.
  Immutable git derivations (fork points, commit parents, changed paths) persist across rebuilds;
  reconciliation is incremental; the file-entry index is lazy. Forced rebuild 44.25 s / 990 git
  subprocesses → 1.46 s / 7. Live: warm 308 ms, one new commit 1.62 s, one merge 2.20 s.
- **B0b graph slices closed** — evolution scope, file graph mode (path → entry index derived from the
  authoring commit's parent), Overview across all dates with an honest coverage indicator — **ranked
  by connectivity until 2026-07-26, now a chronological spine** (newest `limit` entries plus depth-1
  over rendered lifecycle edges), so the Graph grows along the axis the Trail pages along; the stale
  wording here is what led one later analysis to assume the default slice was the densest window
  available when it is a time window — Obsidian-style edge filters that hide *lines* not nodes, one line per pair
  taken by the strongest relationship, and settled layout positions restored on exact-match remount.
- **Trail decision rows** — one row per `#### Dn`, the entry row anchoring as a heading with D1..DN
  as pastel subheadings, grouped by bracket, on the already-ratified `(entry_id, dN)` identity.
- **Decision diagrams are usable again** — clickable badge/figure → zoom-pan modal in the React
  client (vanilla parity), and `esr` now reports diagram coverage. The convention had produced
  nothing for five days and 131 entries with nothing anywhere reporting it.
- **Link-sidecar backlog cleared** — all 69 open `classify_pending` stubs classified (8 live edges,
  61 `not_applicable` with reasons). `link audit` now scores candidates on idf-weighted shared title
  terms: true edges surfaced 73/102 → 92/102, recall@5 44% → 59%.
- **Two silent-failure surfaces made visible** — `session merge-branch` notes when a merged branch
  carried no session entry (trunk lane + missing `Memory-Entry` trailer, both unrecoverable once
  published), and `esr` reports when semantic ranking has degraded to lexical.
- **Packaging** — `model2vec` stays required; `pip install --no-deps memory-seed` is now the
  documented lightweight install, pinned by a test asserting it remains the *only* required
  dependency.
- **Docs** — `docs/3_Spec/draft/decision-level-link-sidecar-refs.md` drafted (not implemented).

### Open threads from this tranche — sequence before they rot

These exist only in session-entry Follow-ups today. Nothing below is built.

1. ~~**Two silent-corruption paths in `_TRAILER_ENTRY_ID_RE` extraction** (P1 — data integrity).~~
   **RESOLVED 2026-07-23.** The safe per-item parser shipped in 21749f4 but seven `links check` call
   sites still scraped the region text; `_entry_level_ref_ids` now migrates all seven (session-entry
   `yaml`, per-user file frontmatter, sidecar `related_entries`). Comments no longer become edges and
   a `:dN` ref is no longer truncated; a misplaced decision ref surfaces, other non-id tokens are
   skipped as before (the ref grammar is stricter than `_ENTRY_ID_RE`, so surfacing them would flag a
   ref to a registered non-standard id). Real-corpus `links check` diff identical; three regression
   tests added; validator-only (the live graph already used the migrated retrieval path).
2. ~~**Decision-level link refs** — spec drafted and evidence-backed.~~ **RESOLVED 2026-07-24/25.**
   Grammar v2 shipped (`<entry_id>:dN`, comma multi-ordinal, `dN -> ` source arrow) across extraction,
   validation, parse, and Trace attachment; `replaces`/`evolves`/`related_entries` all carry decision
   granularity as a distinct edge set. A 2026-07-25 **link-judgment swarm** campaign then judged all
   1,108 file-overlap never-linked pairs and landed **696 decision-level edges**, each carrying a
   structured `edge_confidence` (`link_swarm` skill; specs `edge-confidence-metadata.md`). The graph and
   Trail now **fade low-confidence edges**, and published edges are corrected only via append-only
   `retracts:` blocks (`link-retraction.md`).
   *Follow-up CLOSED 2026-07-26:* the user-facing confidence control shipped — an All / ≥0.7 / ≥0.9
   threshold in the graph filter bar, reusing the tiers the sidecar already stores so it filters on the
   same boundaries the graph fades on. Defaults to All, because hiding evidence by default would let a
   viewing preference decide what the corpus appears to contain. Human-authored edges carry no
   confidence and are never hidden by it. Filtered edges are also dropped from the per-pair outranking
   input, so a hidden low-confidence edge cannot win its pair and blank the visible relationship.
   *Follow-up SUPERSEDED:* "re-run the swarm on the ~200 still-topicless entries" understated the job.
   The topic backfill is ~933 judgment units across the WHOLE corpus (659 of the 899 addressable
   decisions sit inside already-topiced entries, which carry no per-decision attribution). The
   `topic_swarm` skill owns it, with a two-leg pilot gate.
   *Follow-up ABORTED 2026-07-26 — the decision-level topic backfill will NOT be run.* Both permitted
   pilot runs are spent and neither cleared the gate: **Leg A macro-recall 0.583** (run 1) and **0.613**
   (run 2, the single allowed re-prompt, on a disjoint sample with a revised brief) against
   `PROCEED ≥ 0.70`. Per the skill a second band-or-below result aborts the backfill. **Zero topic
   sidecars were written** — `.memory-seed/sessions/topics/` does not exist.
   The measured reason is not a bad prompt. Run 1's recall loss was 63% *area*-slug misses with only 24
   of 45 units holding the two-axis shape; run 2's revision fixed that completely (45/45 units, one area
   + one activity), cut spurious slugs 38 → 27 and quote drops 5 → 2, and lifted precision 0.521 →
   0.587 — but recall moved only +0.030, which at n=20 is noise. The residual misses are genuine
   vocabulary ambiguity (`graph` is both a subsystem and a subject, so `graph`+`memory-trace`+`ui-design`
   entries lose `graph` to a defensible `memory-trace` read) plus a structural tension: one area per
   decision caps the rolled-up union at one area slug, while authors write two or three. And the margin
   over free is thin — the always-top-4 constant guess scores 0.500 on run 2's own sample, so the swarm
   bought +0.113 for 45 model calls against 933 for the campaign.
   *Reviving it requires a changed premise, not another prompt rewrite* — sharpen the `area` axis in
   `topics.yaml`, or gate on attribution directly (Leg B style) instead of roll-up recall, then re-run
   the pilot from scratch with a fresh pass line. The pipeline, validator, block grammar and harness
   (`scripts/topic_swarm_pilot.py`, brief at `scripts/topic_swarm_worker_brief.md`) are sound and
   reusable; only the verdict on spending 933 judgments is settled. Entry-level authored `topics:` and
   inheritance remain the fallback.
3. ~~**Semantic scoring for `link audit`** — measured, unbuilt.~~ **RESOLVED — stale as written
   (verified 2026-07-26).** Both halves of the item were already done and its figures are
   *superseded*, not merely reproduced. Semantic ranking shipped **2026-07-22** in `3deb9c2`
   (`SEMANTIC_OVERLAP_BOOST` in `memory_seed/retrieval.py`), and the spec's "no all-pairs semantic
   scan" paragraph was retracted **in the same tranche** — `lifecycle-edge-linking-sidecars.md`
   carries a dated `> **Retracted 2026-07-22:**` block saying exactly what this item asked for. The
   item's "recall@5 61% → 75% at weight ~120" came from a *pre-ship local scorer that silently
   diverged from `audit_link_gaps`*; the shipped sweep re-measured end-to-end through the real
   function and landed on **weight 160, recall@5 77%, recall@10 82%** (97/104 true edges surfaced).
   Quote the spec's table, not this item's numbers.

   **Re-measured 2026-07-26** on the now-637-entry corpus (133 resolvable author-declared lifecycle
   pairs, end-to-end through `audit_link_gaps`, `top_k=200`): lexical-only recall@5 **56%**,
   +semantic **74%**; recall@10 **63% → 82%**; median rank **3 → 2**. recall@10 reproduces the
   shipped figure exactly; recall@5 lands 3 points under it on a corpus grown from 544 entries.
   Embedding 637 entries costs **0.17 s**; the one-off model load is **~6 s** cold here (not 2.9 s).

   *What this pass actually fixed* — two real defects the "measured, unbuilt" framing hid, both
   violations of **expose before you rank**: the cosine was folded invisibly into a field named
   `file_overlap_score`, and a missing provider degraded to lexical **silently**. That second one is
   not cosmetic: the semantic term changes the top-5 for **610 of 629** sources, so a silent fallback
   served a different ranking with nothing on screen to say so. Now `LinkGapCandidate` carries
   `lexical_score` + `semantic_score` (raw cosine, `None` when off), `link audit` prints a
   ranking-provenance line and the per-candidate cosine, `--json` carries a `semantic` block, and
   **`--no-semantic`** ranks lexically without loading a model. Ranking stayed **default-on** rather
   than being flipped to opt-in: it is a swept, spec-documented default and reverting it would have
   discarded ~18 points of recall@5 on no evidence.

   *Also corrected:* the spec claimed "the gain is in *reachability*, not reordering". It is the
   reverse — reachability is 132/133 **either way** (cosine only adds to pairs the lexical gate
   already admitted, so it structurally cannot improve reach); the whole gain is reordering.
4. ~~**`compact_mermaid_diagrams` vs `arc2d`**~~ **RESOLVED — stale as written (verified 2026-07-26).**
   The premise "the renderer parses no `subgraph` in *both* clients" stopped being true on 2026-07-22:
   `71cea36` deleted `client/src/arc2d.ts` and `DiagramView.tsx` now renders each sidecar block through
   **real Mermaid**, so `subgraph` and the full ~30-type vocabulary render in the maintained UI (both surfaces —
   the inline reader and the zoom modal route through the same component). The skill was reversed in
   the same tranche and *already* says "author standard Mermaid", *already* carries the transitional
   caveat naming the legacy `/` subset parser, and its seed twin is byte-identical — so the "narrow the
   skill" remedy is done and **no skill edit is needed**. What is genuinely left is not a mismatch but a
   The last documented residue — the vanilla subset renderer — retired with that client after JNL's
   2026-08-11 cutover sign-off. VS Code, GitHub, and Memory Trace now all consume standard Mermaid;
   there is no fourth renderer or skill caveat left to maintain.
5. ~~**Cross-session `branch:` contamination**~~ **RESOLVED 2026-07-26 — code half fixed, policy half
   decided and adopted.**
   Investigated against a synthetic-repository matrix rather than by reasoning; full write-up and the
   options in [`branch-field-provenance.md`](branch-field-provenance.md), matrix pinned as
   `tests/test_session_append.py::BranchProvenanceTests`. Two corrections to the item as written.
   **(a) "Affects every git-derived field" is overstated:** `branch:` is the *only* git-derived field
   on an entry — `session_append_entry` makes exactly one git call (`_auto_captured_branch` in
   `memory_seed/core.py`); every other YAML key is caller-supplied, `read_local_user` is a file read,
   `generate_session_entry_id` hashes caller metadata, and `_DiagramSidecarRecord` /
   `_LinkSidecarRecord` / topic sidecars carry no branch at all. The item shrinks to one field.
   **(b) The premise does not hold for this repo:** worktree isolation turns out to be a consequence
   of **`.memory-seed` being committed**, not of worktrees. Because it is tracked here, every real
   worktree checks out its own copy, `resolve_runtime`'s walk-up stops there, and git reports that
   worktree's own HEAD — so today's parallel agents each record their branch **correctly**, and the
   escalation premise ("a second agent appending while another has a feature branch checked out")
   describes a layout this repo does not currently run. **Fixed:** the same worktree layout with
   `.memory-seed` *gitignored* silently stamped the primary's branch — a wrong durable value with no
   concurrency at all — so `branch:` is now omitted when the memory dir belongs to a different
   working tree than the caller, extending the existing detached-HEAD/not-a-repository omission rule
   by one clause. Never fires in this repo; it protects downstream PyPI users. **Still open:** two
   agents sharing *one* checkout have a genuinely identical HEAD, and an agent's session branch is
   never passed to the CLI, so no code can recover it — policy about an unknowable value, not a bug.
   **Decided (JNL, 2026-07-26): A now, D as the standing convention.** A — the existing
   `--branch`/`--no-branch` flags are now documented in `.memory-seed/skills/session_logging.md`
   (the `branch` field prose: shared-tree caveat, both flags, and why omitting beats a wrong durable
   label) and cross-referenced from the README's `session append` reference. D — the standing
   convention that a harness passes `--branch` unconditionally, sourced from the Task Packet's
   `working_branch`, lives in `agent_collaboration.md` under "Branch And Worktree Defaults";
   `agent-rules.md` was left alone because its startup budget is full and this is procedural
   guidance. B (warn on multi-worktree repos) was rejected because it would fire on every legitimate
   primary-checkout append; C (lock/marker enforcement) needs session-identity state that does not
   exist. `test_shared_checkout_concurrency_is_still_invisible` stays as the pin that the code-side
   omission rule is not a complete answer.
6. ~~**The ADR corpus table does not reconcile.**~~ **RESOLVED 2026-07-26** — re-derived from one
   classifier (`scripts/count_decision_shapes.py`), run against today's tree *and* against the git
   trees of the two days that produced the rival figures. **Current, at `0dc423b`: 636 entries**
   (186 numbered / 407 singular / 1 inline / 42 no-decision), **593 with an addressable decision**
   (186 + 407, exactly what `_entry_decision_ordinals` returns), 163 multi-decision, **876 addressable
   decisions**. Population is now stated in the ADR: the **stamped-heading** splitter
   (`_ENTRY_HEADING_RE`, what `links check` validates against), with the 25 date-only May-2026 legacy
   headings **excluded** — the looser chunk-extractor boundary gives 661, and `extract_memory_chunks`
   independently emits exactly that. The filter is **heading shape, not `entry_id` presence**: 9 stamped
   entries predate the id convention and are counted. *Cause of the mismatch:*
   the two figures counted different populations and neither said which. **580 was real** — a mid-day
   2026-07-21 count under the date-only-tolerant splitter (its 66 no-decision matches that splitter's
   67, not the stamped 42). **612 was inflated** and reproduces under neither splitter: the 07-20 tree
   measures 537 stamped / 562 tolerant, and the whole error sits in its no-decision bucket (140 vs
   42/67), consistent with a `sessions/**/*.md` sweep absorbing the 99 decision-less date headings the
   `links/`+`diagrams/` sidecars held that day. **There was no fall** — stamped totals rise
   monotonically 537 → 562 → 636; the `none` bucket (42) and legacy-heading count (25) are frozen
   across all three snapshots, which is what shows the classifier stable and the growth real. Safe to
   size decision-coverage work from these.
7. **Centrality-driven node prominence** — **DEGREE SHIPPED 2026-07-26; betweenness/PageRank open.**
   Residue 3 of the
   [information-theoretic disposition](../4_Reference/information-theoretic-evolution-disposition.md).
   Node size is now `22 + min(20, sqrt(degree) * 5)` over the **payload's** edges of every kind, not
   the related-only `connectivity` that previously drove radius — an entry whose ties are mostly
   `evolves` drew small while a chattier but less consequential one drew large. Reading the payload
   rather than the visible set keeps sizing stable when an edge filter is toggled; sqrt is because
   degree is heavy-tailed and a linear ramp flattens everything below the hubs. Verified live: 98
   nodes resolve to 9 distinct sizes over 22–36. Position is untouched.
   *Still open:* betweenness and PageRank. Unlike degree these are **global** computations, so they
   are a genuine argument for computing server-side and adding a node field, which degree was not.
   The proposal's ADR-gravity-well layout stays declined until ADR nodes exist.
8. **Decision rows in the Graph** — **SHIPPED 2026-07-26, end to end.**
   `/api/v1/graph/projection` accepts `include_decisions` (default **false**, so the entry-level
   surface is untouched) and `graph()` takes `decision_row_scope`: `"all"` for the Trail, `"linked"`
   for the Graph. Forging an entry-level line for a decision edge was tried and **reverted** —
   `test_decision_edges_never_reach_entry_level_consumers` asserts by set-equality against a
   sidecar-deleted control that the entry-level surface stays indistinguishable from a world without
   decision edges, and that guard is deliberate. Asking for rows changes **granularity**, so the edge
   lands on the decision it names instead of being widened into an entry-level claim.
   The scope split is measured, not stylistic: expanding every decision into the force layout added
   446 rows of which **276 were isolated** — worse than the 9 orphans it set out to fix. Filtering by
   entry got that to 110; filtering by **ordinal** gets it to **0**.
   **The tether question is answered, and the answer was not an edge.** Containment travels through a
   structural channel — a synthetic `dgroup:` Cytoscape **compound node** holding both the anchor and
   its rows as children — so the four-independent-never-merged-kinds contract is untouched and no
   entry-level fact is emitted. Not the anchor as parent: a compound parent is auto-positioned (this
   simulation writes every participant's position each tick) and auto-sized (the entry would lose the
   circle/fill/rim vocabulary the rest of the map reads in). Rows are **not simulation participants**;
   their position is derived from their anchor's after every paint, which is why turning rows on moves
   no anchor at all. Live on the real corpus: 112 nodes / 26 rows / 15 groups / 50 edges, 26 of 26 rows
   parented, 0 outside their group's box, row-to-anchor distance exactly `SATELLITE_RADIUS`; the
   on→off→on round trip returns 71/0/0/31 and then the identical numbers, with no stale containers.
   *Open follow-up (small, server-side):* 4 of the 26 rows carry no decision edge, because
   `only_ordinals` is built from sidecar refs **before** `_decision_edges_for_rows` knows whether the
   counterpart resolves — an off-slice counterpart mints a row whose edge is then dropped. They are now
   contained and attributable rather than floating, so this is tidiness rather than a visible defect;
   the prune belongs after `decision_row_edges` is computed, with its own test.
   This was also step 1 of the sequencing recorded in
   [decision-level-topics-proposal.md](decision-level-topics-proposal.md) ("render the decision-node
   graph using the substrate that already exists"), so that track is unblocked.

## Shipped 2026-07-18/19 — unreleased, on local main

None of this was on the roadmap when it was written; it is recorded here so the next sprint starts from
what is true rather than reconstructing it. All of it sits on local main, unpushed.

- **Gated MCP write surface + Constitution v1.3.** `memory_session_append` is now the only way to author
  an entry over MCP, inheriting all nine write-time guards, and `memory_session_integrate` wraps branch
  integration. Both **replaced and removed** `memory_entry_id` and `memory_session_target` — an id plus a
  target path was the entire bypass, and it was the path agents actually used. `dry_run` on both the tool
  and `session append` runs every guard and returns `rendered`: the byte-exact block a real write would
  append. A follow-up pinned the contract that a dry run's `timestamp` is echoed into the real call, so a
  preview at `:59` and a write at `:01` cannot silently mint a different id. Constitution **v1.3** amended
  Invariant #2 with write-surface parity — the amendment is what binds future agents, since the invariant
  never forbade the change.
- **Session-memory integrity.** New `malformed-entry-yaml` links-check error for an unclosed entry
  metadata fence — the signature a bad three-way merge leaves. It was verified by replay against the
  actual corruption: it flags exactly the damaged entry at `ae90e91` and is silent on the repaired file.
  `.gitattributes` now applies `-merge` to `.memory-seed/sessions/**` so git cannot line-merge session
  files at all; concurrent edits conflict wholesale and the structural merge is the only way through.
- **Topic vocabulary 21 → 23** — `security` and `performance` added rather than rewriting the published
  entries that already used them. The vocabulary describes the corpus; it does not constrain it
  retroactively.
- **Trail UI tranche (merged).** Deterministic hand-drawn Trail geometry, middle-third scroll discipline,
  the floating find bar, DRAFT initials rendered as words with file pills, pressure ribbons across the
  whole rail, a tabbed settings menu, collapsible entry metadata, and the full-text/find-bar consolidation
  that removed the competing results dropdown.

### Unscoped discoveries — found by doing the work

Four defects that no one reported and no plan predicted. They are recorded because the pattern matters
more than the individual fixes: each was found by measuring or testing rather than by reading code.

1. **A dark-mode contrast bug the report did not name.** The reported symptom was unreadable pressed-button
   lettering; the same rule was also near-invisible in light mode (cream on cream, 1.15:1).
2. **A self-inflicted capability regression.** Making Enter cycle local matches left the server's full-text
   search — the only thing that reads entry *bodies* — reachable only when the Trail had no local match.
   Flagged when introduced, repaired the same day.
3. **The DRAFT body lint was blind to any entry quoting code.** `_walk_entry_bodies` split the body on
   `fences[1]`, but the metadata opener is ` ```yaml ` and never equals a bare ` ``` `, so `fences[1]` was
   really a body code fence and everything above it was discarded. Found while fixing fence integrity;
   un-blinding it exposed one real violation in a published entry.
4. **82% of search results were filler.** `rank_memory_chunks` never drops zero-score chunks, so an
   entry-granularity search returns the whole corpus ranked. A dropdown hid it; cycling would have marched
   through 82 unrelated entries of a 100-result page with the counter reporting progress.

### Fixed 2026-07-20 — link sidecars were silently lost by `session merge-branch`

Branch-side edits to `.memory-seed/sessions/links/**` used to be discarded without an error.
`_changed_session_paths` diffs *all* of `.memory-seed/sessions`, so the reset loop restored sidecars to
base content — but the fuse had no classifier for `links/` paths, so it never re-imported them. The
`-merge` guard changed the failure's shape rather than causing it: a both-sides edit conflicted and was
misclassified as a *non-session* conflict, aborting the merge loudly; the one-sided case — the common
one — lost silently.

Fixed by making link sidecars a third recognized kind in the fuse, mirroring diagram sidecars exactly
(classification, ref extraction, chronological write, plan/apply wiring, CLI/MCP output). A shared
`_is_recognized_session_tree_path` helper now backs both the conflict classifier and a new
defense-in-depth guard: a branch-touched session-tree path the fuse doesn't recognize is refused with an
issue rather than silently reset, so the next unrecognized sidecar kind fails loudly instead of repeating
this bug. Five regression tests cover the one-sided loss, the two-sided conflict, refusal of an
in-place-modified (stub → live) sidecar block on a branch, and the new guard, all proven through
`session_merge_branch` end to end, not just the fuse in isolation. The trunk-only workaround for
*modifying* an existing sidecar block still holds — that's the append-only invariant, not a merge-tool
gap — and is documented precisely in `agent_collaboration.md`.

### Test-suite protection-value audit — complete 2026-07-20

JNL asked for a protection-value audit of the 635-test suite (not a headcount target): measure before
culling, classify by layer, then work module by module assigning every test Keep / Consolidate /
Replace-with-invariant / Move / Delete. Full record:
[`test-suite-protection-value-audit.md`](test-suite-protection-value-audit.md).

- **Phase 1 — measured, then marked slow tests.** 92 tests ≥0.5s got `@pytest.mark.integration`
  (chosen by measured duration, not by "touches git"); the fast loop (`pytest -m "not integration"`)
  dropped from 135s to 29s (4.6x) while the default `pytest` still runs all 635. `pytest-cov` measured
  81% full-suite coverage (70% fast-loop-only).
- **Phase 2a/2b — structural split, no content changed.** `test_memory_seed.py` (6,533 lines, 287
  tests across 8 unrelated classes in one file) was retired: 7 already-cohesive classes moved to their
  own files verbatim, and the 179-test grab-bag class was split by an AST-driven call-graph analysis
  into 5 files by actual concern (fuse/merge, links-check, project-lifecycle, session-layout-migration,
  core-misc). A shared `tests/_git_helpers.py` deduped one subprocess helper that had drifted 4 slightly
  different ways across files. Verified count-neutral both times: 635 collected before and after each
  pass.
- **Phase 2c — the content cull itself, all 635 tests read module by module.** Result: **1 Move** (2
  misclassified tests relocated to their natural file), **2 Expands** (one closed an unverified
  `session fuse` CLI print line, one closed an untested `psutil`-preference branch in
  `processes.py` — both verified non-vacuous by temporarily breaking the underlying code and confirming
  the new test failed before reverting), **0 Consolidations, 0 Deletions**. Current count: 639,
  full suite green (171.6s).
- **No Delete candidates were found anywhere in the suite.** The suite's real problem was organizational
  (one giant grab-bag file), which Phase 2a already fixed — not volume or duplication.
- **One item deferred to your call**, not actioned autonomously: see open decision #6 below.

## Open decisions — ready for your call

Engineering gates that autonomous work has pushed as far as it reasonably can; each needs one decision
before its next step. (Market/account items live under "Parked" below.)

1. **BG1 steps 5–7 — actionability policy + §7 graduation.** Step 4 (expose authority/provenance in
   Inspector Entry details) **shipped 2026-07-17 and was visually simplified 2026-07-31**. Step 5–6 add an
   `actionability` field computed by policy with machine-readable reason codes, plus fixtures proving
   generated/provider content **cannot** become actionable on its own; step 7 is the Constitution §7
   amendment that would let annotation/generated content become agent-actionable.
   *Options:* **(a)** build 5–6 now as additive/advisory — everything stays non-actionable in effect,
   fail-closed by construction *(recommended: keeps momentum, adds no trust the model doesn't already
   grant)*; **(b)** hold 5–6 until the participant/role model (B3/Phase 6) exists. Step 7 needs your
   explicit amendment approval regardless of (a)/(b).
2. ~~**Track C.2 — ESR Persona Usage Check.**~~ **RETIRED 2026-08-01** — the check originally shipped
   as propose-and-wait, but its only signal was the optional `agent_name` session field. That field and
   the dependent check have now been removed because the signal was incomplete and did not justify
   permanent entry metadata.
   Moved [`persona-usage-deactivation-esr-proposal.md`](../5_Completed/persona-usage-deactivation-esr-proposal.md)
   to `5_Completed/` as historical rationale; its optional usage-report follow-up is retired as well.
3. ~~**Track A.4 — `memory-seed[lense]` deprecation window.**~~ **RESOLVED 2026-07-20** — option (a):
   announced 2.20 as the drop and removed the alias/shim now. `pyproject.toml`'s `lense` extra and
   `cli.py`'s `lense` subcommand are gone; `README.md`, `functionality-audit.md` (bumped to 2.20), and
   `CHANGELOG.md`'s Unreleased "### Removed" section reflect it. `memory-trace-distribution-plan.md`'s
   last obligation is now discharged — see the distribution-plan note below.
4. **Track A.2 — Session decision diagrams Phase 3** (exportable report / handover pack) — sizable, needs
   a product greenlight. *Recommendation:* hold until a concrete handover-pack need surfaces (no current
   pull).
5. **OpenSSF remainder — your GitHub clicks** (only you can do these): enable private vulnerability
   reporting; add branch protection + set `integration_mode: pr` (G2); submit to bestpractices.dev
   (answers drafted on request); confirm PyPI attestations at the next cut.
6. ~~**Structural split of `test_session_fuse_and_merge.py`.**~~ **RESOLVED 2026-07-20** — JNL: "make a
   reasonable call." Split into `test_integration_mode.py` (6), `test_branch_status.py` (3),
   `test_worktree_guard.py` (4), `test_session_target.py` (8); the 6 `decision_density`/
   `future_timestamp` tests split further, 3 into `test_links_check.py` and 3 into
   `test_session_append.py` per their actual call target; one `_merge_routing_stanza` test into
   `test_core_misc.py`. `test_session_fuse_and_merge.py` itself: 69 → 41, now purely fuse/merge. Pure
   reorganization — 639 tests collected before and after, full suite unchanged at 639 passed.
7. **Quality-v0 step-6 usefulness review — the oldest open gate here, and it now blocks three things.**
   [`memory-quality-metrics-v0-proposal.md`](memory-quality-metrics-v0-proposal.md), baseline at
   [`../4_Reference/memory-quality-v0-baseline.md`](../4_Reference/memory-quality-v0-baseline.md).
   Open since 2026-07-17; this file wrongly recorded it as done until 2026-08-14 (see BG2 below), which is
   probably why it has sat. The ask is small and is *only* yours: is the baseline useful and repeatable?
   Downstream of the answer: proposing targets or ESR surfacing, Constitution **§8** graduation out of
   `[candidate]`, and the decision-quality benchmark the Inbox gap report puts first in its triage order.
   *Options:* **(a)** useful as-is, keep it, set no targets — graduate §8, unblock the benchmark
   *(recommended: it is what the command already does, and §8 is the only clause still carrying a stale
   `[candidate]`)*; **(b)** useful but not yet worth graduating — say so, and the clause stays candidate
   with a stated reason instead of by default; **(c)** not useful — retire v0 and stop the downstream
   chain. Any of the three closes it; leaving it open is the one outcome that costs something.
8. **Decision-replay — approve or decline scored execution.** See "Evidence programme" below. The pilot
   ran and was adjudicated, but the instrument is amended rather than frozen and four preconditions are
   unmet. Nothing may be run *as scored evidence* without your go.
9. **Context-derivation preregistration — approve or reject.** `experiments/context-derivation/` is
   written and waiting; it is the sanctioned way to reduce fixed startup context without guessing at
   safety-equivalence, and startup context has since changed underneath it (Track C item 4), so the
   preregistration wants a re-read before approval. *Recommendation:* rule either way rather than carrying
   it — a reject is a real outcome here.

## Evidence programme — does durable rationale actually change a later decision?

New section 2026-08-14. Four artifacts now exist that test the project's central claim from the outside,
and none of them had an owner in this file. They are grouped because they answer one question and share
one failure mode: every measurement so far was designed, run, and interpreted by the same agent that
wrote the code being measured. **None of this is engineering-blocked.** All four wait on a JNL ruling.

1. **Decision replay (pilot run 2026-08-13, adjudicated 2026-08-14).**
   `experiments/decision-replay/claude-quality-report-v0/`. A blinded two-arm replay: a fresh Claude
   session implements a real historical defect fix in standalone `A`/`B` repositories that differ *only*
   in whether dated session-memory documents are present, judged by four independent gates rather than a
   composite score. The first pilot (`20260813T204539Z`) was revealed and adjudicated with the original
   grader outputs preserved immutable. **Read the result carefully and do not quote its timing.** B was
   faster (5m07s vs 12m05s), but the pilot has **no causal power**: n=1 pair, B ran fewer validation
   steps, and **treatment uptake was zero** — the bug-specific rationale never reached active context
   because the startup packet overflowed into persisted output and was not opened. The v1 gate also
   rejected permitted behavior, so the instrument was amended prospectively to grade honest
   unreadable-input handling instead of the historical patch shape, and this run is labelled an
   *instrument pilot* rather than a result. **Four preconditions before anything is allowed to count:**
   freeze schema v2; make rationale exposure observable; prevent persisted-output overflow from hiding
   the treatment; run multiple randomized fresh sessions per arm. Gate: **open decision #8**.
2. **Independent validation brief** (P1, open since 2026-08-05) —
   [`independent-validation-brief.md`](independent-validation-brief.md). Asks an agent that has *not*
   worked on this project's experiments to try to **break** a set of claims and to derive its own method,
   precisely so it does not inherit the blind spots of the procedure it would otherwise copy. Its
   `next_action` is to hand the file to such an agent; that has not happened. This is the cheapest
   available answer to the same-author conflict named above.
3. **Adjudication queue** (P2, open since 2026-07-27) —
   [`adjudication-queue.md`](adjudication-queue.md). 22 contested rows of 77, held out from a
   two-independent-worker run; uncontested rows are deliberately absent because agreement there buys
   nothing. Bounded and finite. Every validity figure the project has quoted so far rests on a proxy —
   authored tags held up only ~50% when contested, and the file-derived gold set was shown unsound — so
   these rulings would be the first ground truth the project actually has.
4. **Context-derivation preregistration** — `experiments/context-derivation/`. Written, unapproved. Gate:
   **open decision #9**.

*Sequencing note, not a recommendation to build:* 2 and 3 are cheap and unblock interpretation of 1. The
Inbox gap report reaches a similar ordering by a different route, but it is an unassessed capture and is
recorded as such below — it is not the authority for this section.

## Live work — sequenced (Constitution-aligned)

Active work, sequenced under the Constitution (each item answers the five-question test — Capture /
Validation / Retrieval / Trust / Application — and respects Invariant #6). The foundation,
memory-quality core, B0a contracts, and B0b formal acceptance have shipped, so **the Memory Trace UX
sequence now leads with M3 bounded graph perspectives and controlled expansion**.

### Foundation — derived-projection Phase 1 ✅ SHIPPED 2026-07-15

**Made Trace fast + made Invariant #6 real.** The SQLite cache is now a formalized read-model per the
[contract](../3_Spec/draft/derived-read-model-projection-contract.md): explicit Markdown→projection ingest
with a byte-identical rebuild, a **git-watermark warm start** (O(changes) freshness — no whole-corpus scan)
and **atomic build/swap**, plus three read-path perf refinements (`chunk()` 132 ms → 3.9 ms). Plan:
[`derived-projection-implementation-plan.md`](derived-projection-implementation-plan.md). Five-question
test → **Retrieval** (fast reads) + **Application** (usable Trace on large histories).
**Incremental ingest shipped 2026-07-21:** immutable Git derivations persist across rebuilds,
reconciliation is incremental, and the file-entry index is lazy. The measured forced rebuild moved from
44.25 s / 990 Git subprocesses to 1.46 s / 7. **Phase 2** (git-rooted historical integrity, G6/G7) is the
next projection increment when that track resumes.

### Ranking & graph quality — core SHIPPED 2026-07-15 (gate → surface → capture)

The memory-quality trio from the 2026-07-13 freshness-ranking session was approved, implemented in
dependency order, and closed on 2026-07-15:

1. **`ranking-ab` + the "expose before you rank" amendment** — ✅ **SHIPPED 2026-07-15**.
   [`real-corpus-ranking-validation-gate-proposal.md`](../5_Completed/real-corpus-ranking-validation-gate-proposal.md).
   The reusable `memory-seed ranking-ab` command and graph-edge-contract rule now require a full-corpus
   off/on comparison, intended directional wins, and an unchanged no-affected-hit control before a
   default ranking flip. Five-question → **Validation + Trust**. *The gate for item 2 now exists.*
2. **`replacing_head` + lineage-bounded replacement boost** — ✅ **SHIPPED 2026-07-15**.
   [`supersession-successor-surfacing-proposal.md`](../5_Completed/supersession-successor-surfacing-proposal.md).
   Additive successor exposure shipped first; the bounded boost then passed the full-corpus A/B gate.
   Five-question → **Retrieval + Trust**.
3. **`link audit --apply` sidecar scaffold, steps 1–3** — ✅ **SHIPPED 2026-07-15**.
   [`lifecycle-link-authoring-assist-proposal.md`](lifecycle-link-authoring-assist-proposal.md).
   Scaffolds inert `classify_pending` sidecar stubs, warns on unresolved stubs, and reports them in ESR.
   It never auto-classifies or emits a live edge; human classification remains mandatory. Optional steps
   4–5 are deferred while the shipped workflow is evaluated. Five-question → **Capture**.

### Track A — remaining open tails

1. **Related-entries P2** — ✅ **RESOLVED 2026-07-17**.
   [`related-entries-p2-mutation-plan.md`](related-entries-p2-mutation-plan.md). `memory-seed link add`
   ships (newest-entry only: forward-only, idempotent, YAML-only, `links check`-gated). The historical
   backfill is **permitted but deliberately not a command** — Constitution **v1.2** amended Invariant #2
   with a one-off, per-edge-approved, metadata-only exception, which a standing command would violate by
   definition. The sanctioned hand procedure is in the plan; prefer the evolution-edges seeding pass,
   which adds edges to history by writing *new* entries and rewrites nothing.
2. **Session decision diagrams Phase 3** — [`session-decision-diagrams-plan.md`](session-decision-diagrams-plan.md).
   Phases 1–2b shipped (sidecars, validation, reader + Trail/Graph badge & zoom viewer). Phase 3
   (exportable report / handover pack) is sizable and **gated on a product greenlight**.
3. **OpenSSF credibility** — **in-repo slice SHIPPED 2026-07-17** (greenlit by JNL after the
   implementation-plan checkpoint). [`openssf-credibility-proposals.md`](openssf-credibility-proposals.md).
   Landed: `SECURITY.md` (G0), `CONTRIBUTING.md`, CodeQL + Scorecard workflows, README badges, and both
   workflows hardened (every action SHA-pinned from upstream; least-privilege tokens; OIDC preserved).
   G1 CI was already delivered by codex's `verify.yml`. Expected-score notes:
   [`../4_Reference/openssf-scorecard-notes.md`](../4_Reference/openssf-scorecard-notes.md).
   **Remaining is yours:** enable private vulnerability reporting, branch protection + `integration_mode:
   pr` (G2), the bestpractices.dev submission (answers drafted on request), and attestation confirmation
   at the next release cut.
4. ~~**Trace distribution — deprecation-window closeout**~~ **RESOLVED 2026-07-20, moved to
   `5_Completed/`** — [`memory-trace-distribution-plan.md`](../5_Completed/memory-trace-distribution-plan.md).
   Both phases shipped (Phase 1 released in 2.16.0; the optional-extra fold-in landed 2026-07-12), and its
   last remaining obligation — dropping the `memory-seed[lense]` alias and `memory-seed lense` shim after
   one release window — discharged the same day as Track A.4 above. No open obligations remain, so the
   plan moved out of `2_Todo/`.

### Track B — Memory Trace next generation (the promoted direction, 2026-07-11)

Governance (read to sequence, not build): [`memory-trace-product-and-system-architecture-blueprint.md`](memory-trace-product-and-system-architecture-blueprint.md)
(entry point) → [`memory-trace-next-generation-implementation-roadmap.md`](memory-trace-next-generation-implementation-roadmap.md)
(Phase 0–10 spine; Phases 0–1 delivered) → [`memory-trace-next-generation-coverage-matrix.md`](memory-trace-next-generation-coverage-matrix.md).

- **B1 — Evidence Pack Builder** — ✅ **PHASE 1 SHIPPED 2026-07-15**.
  [`memory-trace-ai-timeline-summarisation-plan.md`](memory-trace-ai-timeline-summarisation-plan.md).
  `build_timeline_evidence_pack()` now emits deterministic, snapshot-tested JSON over the delivered
  retrieval/graph readers with **no write path and no provider**. The plan remains active for Phase 2: a
  disabled-by-default provider interface and local-model adapter whose cited generated output remains
  non-authoritative. The canonical shape is the spec
  [`../3_Spec/memory-trace-derived-artifact-provenance-contract.md`](../3_Spec/memory-trace-derived-artifact-provenance-contract.md)
  (blueprint §4.5 and the evidence-annotations doc are forward supersets — do not build a second builder).
- **B0a — Graph/workspace contract and benchmark** — **COMPLETE 2026-07-16** *(pre-React; JNL-endorsed
  2026-07-15; proposal set promoted 2026-07-15)*. The graph received semantic, interaction, and renderer
  attention before any React rebuild, without implementing the same UI twice.
  Sits **before B2**. Coordinating index:
  [`memory-trace-graph-and-workspace-proposal-set-index.md`](memory-trace-graph-and-workspace-proposal-set-index.md).
  B0a makes the decisions and produces the evidence B2/B0b must consume:
  1. **Shell behaviour / shared-selection contract** —
     [`memory-trace-three-region-workspace-and-dockable-inspector-proposal.md`](memory-trace-three-region-workspace-and-dockable-inspector-proposal.md):
     hamburger toggles only the left pane; Trail and Graph remain centre workspace modes; inspector
     visibility/dock state is independent. Apply only vanilla-safe clarifications that will not duplicate
     the React implementation.
  2. **Renderer-neutral graph contract + fixtures** —
     [`memory-trace-graph-visualisation-and-temporal-topology-proposal.md`](memory-trace-graph-visualisation-and-temporal-topology-proposal.md):
     separate graph semantics from renderer implementation while preserving the current SVG renderer as a
     fallback. The first bounded B0a fixture contract is now implemented in
     [`../3_Spec/memory-trace-renderer-neutral-graph-projection.md`](../3_Spec/memory-trace-renderer-neutral-graph-projection.md);
     the packaged side-by-side renderer harness completed its evidence sweep; JNL selected Cytoscape.js
     3.34.0 for B0b while retaining the SVG fallback.
  3. **Renderer benchmark** — the same bounded fixture passes the evidence sweep in vis-network and
     Cytoscape.js. Cytoscape.js is the selected B0b renderer.
  4. **Topology-first graph** — stable community colour, stronger node hierarchy, typed/curved edges,
     optional mild temporal drift, bounded/community overview modes, and a bounded force-motion layer:
     Settled remains the cached default; Animate layout and Reheat on drag are explicit exploration tools,
     capped to small visible graphs and disabled by default under reduced motion. The topology model is
     fixture-proven; this motion extension is specified but not yet implemented or benchmarked in Cytoscape.
- **B2 — React/Vite shell** *(first implementation slice landed 2026-07-16)* —
  [`memory-trace-frontend-architecture-and-design-system-proposal.md`](memory-trace-frontend-architecture-and-design-system-proposal.md)
  (roadmap Phase 2). `memory-trace/client/` now builds a TypeScript React shell to packaged assets served at `/`;
  it consumes only `/api/v1/*`, lazy-loads Cytoscape.js, and needs no Node.js at runtime. The first
  three-region shell has independent navigation and persisted Inspector dock state.
  **Trail/search parity is substantially closed as of 2026-07-19**: local title/branch/id find-bar cycling
  with eased Trail scrolling, server full-text search reachable from the same bar, one counter and one
  pair of chevrons serving both modes, and the reader easing to the matched section as results are
  stepped. Genuine hits are separated from the ranker's score-0 filler client-side, so the counter reports
  matches rather than corpus size. **Storybook harness landed 2026-07-20** (`storybook@10` +
  `@storybook/react-vite`, wired to `vitest` so stories run as real tests, `@storybook/addon-a11y` set
  to a hard gate) — one component (`SettingsMenu`) fully storied as proof; full component-inventory
  coverage waits on the primitive/token extraction the design-system proposal calls for. The a11y gate's
  first run caught and fixed a real WCAG contrast violation (light-theme `--muted` token, 26 call sites).
  **Playwright e2e harness landed 2026-07-20** too: `@playwright/test`, running against the packaged
  React build served by the real `memory-trace` CLI over this repo's own 600+-entry corpus (not a mock),
  proving "packaged-wheel loading" for real. 3 of 8 required flows covered (search-to-match, next/prev
  navigation, keyboard-only Enter-to-cycle); 4 more are buildable now (selection/inspector persistence,
  graph search/focus, offline startup) and 1 (annotation creation/version resolution) can't be tested
  until B3 ships the feature. **First manual accessibility pass done 2026-07-20**, against the live
  packaged app over real data: found and fixed a systemic WCAG 2.4.7 (Focus Visible) violation — 8
  interactive element classes had `outline: none` on `:focus-visible`, relying only on a subtle
  border/background/text-color shift as the sole keyboard-focus signal (some with no visual change at
  all). Added a real outline to each, matching the pattern other elements already used correctly.
  **Accessibility/scale closeout completed 2026-07-29:** packaged-browser checks cover focus restoration,
  keyboard graph selection through the non-visual list alternative, stable colour across reloads, and
  the full-corpus performance ceiling. **Cutover completed 2026-08-11:** JNL approved React as the sole
  supported frontend; it now owns `/` and the vanilla fallback and parity-only tests are retired.
- **B0b — Native graph/workspace implementation** *(started 2026-07-16; implemented through roadmap
  Phases 3 and 5)* — the first React shell provides a lazy Cytoscape graph, bounded initial graph range,
  shared entry selection, right/bottom/auto/hidden persisted Inspector controls, and the additive
  `/api/v1/graph/projection` renderer-neutral contract. The React route now also has exact `mse_` and
  legacy `ms-` entry-ID navigation, ranked search results feeding shared Inspector selection, a recent
  seven-day default graph range with an explicit all-dates control, overview/local/topic filters, typed
  curved edges, selected-context `evolves` routes, focus/minimal/all label policy, keyboard fit/zoom/node
  cycling, and a complete-list alternative. Failed graph refreshes preserve the current view; graph mode
  renders connected context while the list retains unlinked records. **The Inspector reader shipped
  2026-07-17** — a markdown-rendered entry body (frontmatter code block, headings, bullets, inline
  code/bold), search-match subsection highlighting at parity with the vanilla reader, an evidence strip
  (commit + `path:line`), and navigable linked-memories/related-activity cards. **Decision Reader M1 and
  Trail orientation M2 shipped 2026-07-30; the Inspector was refined 2026-07-31** into lightweight entry
  segments with one equal-weight, scrollable decision window. Canonical DRAFT content carries no
  redundant Recorded badge; technical sidecar/projection origin remains available under Entry details.
  **The Trail view shipped
  2026-07-18** (first slice) — a `Trail` presentation mode over `/api/v1/trail` with a pure, testable
  `trailModel` (day-grouped newest-first rows, greedy branch-lane interval packing with the main-lane-0
  guard, commit-time `interpRow`), rendering the git-graph rail (lane segments, solid+phantom main spine,
  rounded-elbow fork/merge connectors, clickable trunk merge dots), row-click selection into the shared
  Inspector, and client-side windowing (Load older). Verified by model invariants on live 458-entry data
  (main alone in lane 0; per-lane disjoint; sane laneCount) via the `window.memoryTraceNextDebug` parity
  harness. **Slice 4a shipped 2026-07-18** — lifecycle-edge arrows: `replaces`/`evolves`/`related` edges
  route through the reserved relationship zone as dashed arrows with pair precedence (replaces > evolves >
  related), soft/pastel variants, and an adjacent-`replaces` bow; `replaces` always shows, `evolves`
  and `related` draw for the selected entry. **Slice 5a shipped 2026-07-18** — a relationship legend
  (replaces/evolves/related dashed keys) and search-as-a-function-over-the-Trail: a client-side substring
  filter over the visible window (title/branch/entry-id) dims non-matching rows and dots, marks matches
  with a dot, and shows a live match count. **Slices 4b + 5b + diagram badges shipped 2026-07-18 —
  the Trail is at full parity with the vanilla feature set**: the two-rule related model (same-branch
  related as chain-primary/secondary row brackets, adjacent same-lane evolves as chain brackets,
  commit-sibling right-edge brackets), two-stage muted/pinned selection, continuity lanes
  (rename/migration/removal glyphs in their own band), and `has_diagram` diamond badges (the field the
  service always computed is now declared on the v1 `GraphNode` — additive contract change, fixtures
  regenerated). The left pane is now a **selection context panel** (typed lifecycle links + commit
  siblings + similar entries; recent entries when nothing is selected), replacing the placeholder
  graph-slice list. **React diagram rendering shipped 2026-07-20**: the Arc-2d flowchart/sequence-diagram
  engine ported from the vanilla reader to `arc2d.ts` (pure parsing/layout, 16 unit tests) +
  `DiagramView.tsx` (React SVG renderer, JSX escapes text automatically — no HTML-string injection
  surface to manage), replacing `EntryReader.tsx`'s "in-reader rendering lands in a later slice"
  placeholder. Verified against the real packaged app on a real 16-node flowchart entry
  (`mse_v26pem9hsvsbjbge`): correct multi-rank layout, 13 nodes/17 edges rendered, matching the vanilla
  parser's own edge-syntax limitation (dotted `-.->` mermaid edges aren't recognized by either
  implementation — faithful port, not a regression). **Evolution graph mode shipped 2026-07-20**: a
  third `GraphScope` alongside the existing Overview/Local, requesting only `evolves`/`replaces` edges
  at depth 8 centered on the selected entry — a scoped lifecycle-chain view distinct from Local's full
  neighborhood, reusing the existing `/api/v1/graph/projection` `edge_types`/`depth` params with zero
  backend changes. Verified live: an entry with a real `evolves` edge renders exactly its 2-node chain;
  an entry with none renders an empty graph, no crash. **File graph mode shipped 2026-07-21**: a new
  `file_entry_index` (path → entry_ids) derived once per rebuild from each entry's authoring commit's
  *parent* — not the entry's own diff or its recorded `branch:` field, both of which are usually just
  the session file/`main`, since this project logs sessions on main after merging, not on the feature
  branch. Exposed as a `path` param on `/api/v1/graph/projection`, seeding the graph with an exact
  membership set (a new `entry_ids` path through `Service.graph()`) rather than a neighborhood
  expansion. File pills in the reader's `F:` blocks are now clickable, opening this scope directly.
  First implementation attempt used trailer/branch-name matching and returned zero nodes against real
  data — found live, root-caused (this session's own commits never carry a `Memory-Entry` trailer, and
  entries logged after merge record `branch: main`), and corrected; 8 unit tests cover both the
  merge-based and plain-commit shapes. Verified live against real multi-entry files (23 entries for
  `App.tsx`) with real relationship edges rendered between them. **Topology communities: MEASURED AND
  REJECTED, not pending** — [`adr-graph-community-detection.md`](../3_Spec/adr-graph-community-detection.md).
  This line previously read "Louvain recommended, client-side over the existing bounded projection;
  designed, not yet built", which the ADR contradicted a day later and its 2026-07-26 addendum closed
  for the client-side variant specifically. Node colour means *authored topic community*; Louvain
  cannot replace it and cannot be offered as a second colour mode either, because on the payload's
  authored-only edges the floor on community count is the connected-component count — 46 at the
  default Overview slice, 110 at full corpus — so the granularity a 16-slot legend needs is
  unreachable at any resolution, and the default slice (71 nodes, 31 authored pairs, 35 isolated) has
  nothing to detect. The deeper reason is that `_overview_slice` is a *chronological spine* (newest 60
  by date + depth-1 expansion = the 71), not a connectivity ranking, so the default payload is a time
  window whose partition would be recomputed over a different graph every "Show more". Corpus density
  rose 56% since the first measurement without moving the verdict.
  §4.3's stable-community apparatus is **not required**. The only untested route that could reopen
  this is Leiden, which needs `leidenalg`/`igraph` — a new runtime dependency, so a maintainer call.
  **B0b formal accessibility/scale acceptance completed 2026-07-29**: packaged-browser checks cover
  focus restoration and keyboard selection through the graph's non-visual list alternative; the full
  corpus scale harness reaches 707 nodes / 1,269 edges with a 1.2 s first graph paint, stable colour
  assignment across reloads, and a 250 ms interaction ceiling. The ADR is accepted.
  Keep the SVG renderer until explicit parity sign-off.
  **Navigation and layout gained ground 2026-07-28/29** (full detail in the dated "Shipped" section
  above): the flat topic-chip navigation became a recursive Areas/Activities ontology tree; long
  lifecycle chains now wind into a spiral aged oldest-innermost, with a concordance gate so a chain only
  spirals when its topology actually tracks chronology; the layout gained a soft crossing-avoidance
  force; and Trace can now open any correctly-initialised folder from inside the app, not only switch
  between this repo's own git worktrees — a capability outside B0b's original scope.
  Only after B0b acceptance may the
  [`structural-provider proposal`](memory-trace-structural-graph-enrichment-provider-proposal.md) define a
  provider-neutral contract and pilot optional `code-review-graph`; providers never own canonical decision
  semantics or alter ranking without exposure and real-corpus validation.
- **BG1 — Provenance and authority taxonomy** *(constitutional gate before actionable annotations or
  agent-influencing generated output)* —
  [`memory-provenance-and-authority-taxonomy-proposal.md`](memory-provenance-and-authority-taxonomy-proposal.md).
  Keep provenance, authority, lifecycle, and actionability as separate fields; do not create a single
  trust score. **Steps 1–4 SHIPPED** — the enum-constrained `AuthorityClass`/`ProvenanceClass` on the
  node (2.19), and Entry details expose authority + provenance without crowding the canonical entry
  reading surface (refined 2026-07-31). Steps 5–7
  (actionability policy, fail-closed fixtures, §7 graduation) are the **open-decisions gate #1** above.
- **BG2 — Memory-quality metrics v0** — **v0 SHIPPED 2026-07-17; step-6 usefulness review STILL OPEN.**
  [`memory-quality-metrics-v0-proposal.md`](memory-quality-metrics-v0-proposal.md).
  `memory-seed quality report [--json]`; first baseline at
  [`../4_Reference/memory-quality-v0-baseline.md`](../4_Reference/memory-quality-v0-baseline.md)
  (unlinked 95/431 = 22.0%; DRAFT reason coverage 403/403; BG1-dependent metrics honestly `unavailable`).
  **Corrected 2026-08-14 — this line previously read "usefulness review COMPLETE … BG2 is done" and cited
  a JNL review on 2026-07-17 that did not happen.** What the 2026-07-17 session actually recorded (D2 of
  `.memory-seed/sessions/2026-07/2026-07-17.md`) is the *opposite*: record the baseline, set the proposal
  to `blocked_by` a user usefulness review, **propose no targets**, and keep it in `2_Todo` precisely
  because what remains is a user decision. The proposal's own front matter still carries
  `status: v0-shipped-awaiting-usefulness-review` and a `next_action` naming JNL. Two independent sources
  agree with the proposal and not with this file: Constitution **§8** (v1.9, 2026-08-13) leaves its clause
  `[candidate]` with graduation gated on this review, and the Inbox gap report makes it step 1 of its
  proposed triage order. Promoted to **open decision #7** below. The BG1-dependent metrics stay
  `unavailable` until BG1 lands regardless (see the open-decisions gate for BG1).
  *Remeasured 2026-08-13 at `78342e2b`:* unlinked 180/901, DRAFT reason coverage 857/857 with 44 excluded,
  citation/provenance coverage `unavailable`, ranking-A/B regression `not_applicable`. The dated baseline
  document is the 2026-07-17 artifact and is deliberately left as measured.
- **B3 — Evidence annotations & projection** *(long-horizon, after B2/B0b and BG1)* —
  [`memory-trace-evidence-annotations-and-projection-architecture.md`](memory-trace-evidence-annotations-and-projection-architecture.md).
  Anchors, append-only annotations, SQLite projection — needs the React shell **and** a participant/role
  model first. No annotation becomes agent-actionable until BG1's authority rules are adopted.

### Track C — agent context efficiency (control-plane)

Approved + promoted 2026-07-14 from Inbox. Both P2, small, unblocked, independent of the Foundation and of
Tracks A/B — control-plane/skill/agent-rules guidance that slims how much context each agent loads. They
descend from the two-axis persona/orchestration evaluation (session `mse_y7nhd5hcpwa0qb51`):
"orchestrator/worker/reviewer" and "developer/copywriter" are *different axes*, so the real win is trimming
context, not renaming roles. Five-question test → **Application** (how agents load and apply memory);
Markdown-authoritative, so Invariant #6-clean (no derived-state surface).

1. **Worker Context Contract** — ✅ **SHIPPED 2026-07-17** under live user consent (locked-file edit).
   [`../5_Completed/worker-context-minimisation-proposal.md`](../5_Completed/worker-context-minimisation-proposal.md).
   A packeted worker loads only its Task Packet + at most one domain persona + objective-triggered skills
   (`persona:` + `context_load:` packet fields), skipping load-all-personas / full-index / newest-session
   read while **still** running `base_sha`/preflight/worktree-guard. Lives in `agent_collaboration.md`;
   `agent-rules.md` carries one clause (its 260-line startup budget is now exactly full).
2. ~~**ESR Persona Usage Check**~~ — **RETIRED 2026-08-01**.
   [`../5_Completed/persona-usage-deactivation-esr-proposal.md`](../5_Completed/persona-usage-deactivation-esr-proposal.md).
   The original check depended on incomplete persona-name recording. The session field and check were
   removed together; persona activation and approval-gated persona evolution remain unchanged.
3. **Superpowers collaboration integration** — **ACTIVE P2, started 2026-07-29**.
   [superpowers-collaboration-integration-proposal.md](superpowers-collaboration-integration-proposal.md).
   Optional direct delegation only where Superpowers has the stronger proven workflow: independent
   read-only diagnosis and approved same-session SDD. Memory Seed keeps the Worker Context safety
   envelope, owned worktrees, durable memory, \`integration_mode\`, \`merge_trigger\`, session fusion, and
   cleanup. Phase 1 ships the thin adapter and retained-boundary contracts; Phase 2 requires two real-plan
   pilots plus a compaction/resume test before broader promotion. Five-question test → **Validation,
   Trust, Application**, with Capture improved at the durable SDD return receipt.
4. **Whole-session startup context, routed by measured length** — ✅ **SHIPPED 2026-08-13, unreleased**
   (`mse_fx1gm0x6p1sts4y2`). This is Track C's thesis landing on the startup path itself. `situate`
   measures the latest applicable session file and returns a deterministic route: **direct** primary-context
   reading at or below **12,000 characters**, or a read-only **≤800-token economy-worker briefing** above
   it, which must cover the whole file, cite entry IDs/headings, report N/N coverage, flag superseded
   claims, and yield to exact source for consequential reasoning. Fallbacks are direct read and
   entry-boundary chunk/reduce. **What it replaced:** a fixed five-entry, 1,500-character-capped payload
   that could silently omit earlier work in the same session — a window, not a summary. A character
   threshold was chosen over a token one because it is deterministic and tokenizer-independent, and model
   selection stays *outside* the hook so each host picks its own smallest suitable worker and `situate`
   stays fast, offline-safe, and portable. 205 focused/compatibility tests; the 12,000/12,001 boundary is
   pinned exactly. **Note the interaction with open decision #9:** this changed the startup-cost baseline
   the context-derivation preregistration was written against.

The first two compound (fewer active personas → lighter worker *and* primary startup load) but neither
blocks the other. Both sit **below Track A's open tails** in priority — small, sequence-flexible guidance
changes.

5. **Declarative Retrieval Specification primitive (P1, M0/M1 delivered; M2–M5 planned)** —
   [`declarative-retrieval-specification-proposal.md`](declarative-retrieval-specification-proposal.md).
   Context construction becomes a versioned request resolved by Memory Seed into a deterministic Evidence
   Pack and bound to a Task Packet. The former blocker path — M0 (v1 contract/fixtures) → M1 (shared
   resolver plus MCP preview/resolve) — landed on `main` through merge `3577e9` on 2026-07-30. Profiles,
   composition, Trace, and advanced selectors remain enabling or later work and do not block first
   orchestrator/worker use.
### Track D — semantic memory and workflow evolution

Approved 2026-07-16 after full Inbox triage. These plans are dependency-ordered and do not displace B0b:

1. **Semantic record and signal foundation (P1; ADR foundation shipped 2026-08-03)** —
   [`memory-seed-semantic-record-and-signal-foundation-plan.md`](memory-seed-semantic-record-and-signal-foundation-plan.md).
   Living concern-based ADRs, mandatory MCP review, structural branch fusion, CLI/MCP/Trace surfaces, and
   three-concern dogfooding are complete. Entries retain detailed evidence; the ADR owns its curated synopsis,
   concern membership, and accepted head; status and indexes are derived. The remaining `record_kind` and
   retrieval-signal work still waits for BG1/BG2 and cannot change ranking before the real-corpus gate.
2. **Workflow evidence and review workbench (P2)** —
   [`memory-seed-workflow-evidence-and-review-workbench-plan.md`](memory-seed-workflow-evidence-and-review-workbench-plan.md).
   Reconstruct three real idea-to-outcome journeys before defining a deterministic review queue. No raw
   telemetry, universal workflow, automatic judgement, or new generic graph edges.
3. **Semantic Trace projections (P3)** —
   [`memory-trace-semantic-projections-plan.md`](memory-trace-semantic-projections-plan.md). Begin with one
   validated Decision projection over shared readers; additional projections require user evidence.

The Evidence Envelope and Capability Status were folded into the existing evidence/annotations architecture.
The seeded document lifecycle was folded into the local lifecycle plan after its Phase 2/3 proof gates.
Publishability and the generic skill/workflow router are deferred until their explicit reactivation gates.

### Track E — worktree and branch hygiene

**COMPLETE 2026-07-20**, moved to
[`5_Completed/agent-worktree-and-branch-hygiene-plan.md`](../5_Completed/agent-worktree-and-branch-hygiene-plan.md),
which combined the two former Inbox proposals. **Phase 1 COMPLETE 2026-07-17**: `memory-seed worktree
classify` (dry-run, evidence per verdict, fails closed) and `--apply` (destructive; shipped under live
consent; reclassifies at apply time, git-native with bounded retry, no raw deletion, branches untouched).
**Phase 2 COMPLETE 2026-07-20**: `agent_collaboration.md` still carried two stale `<owner>/<kind>/<topic>`
branch examples and one stale `.{agent}/worktrees/<task>` worktree example predating the
worktree=session/branch=task decision; reconciled to `<agent>/<kind>/<topic>` and worktree=session,
seed-twin synced; existing branch names remain grandfathered.

## Inbox disposition — evaluated 2026-07-16, re-triaged 2026-07-20

The 2026-07-16 pass evaluated all 14 Inbox documents: actionable work got one canonical owner in Todo,
security- or evidence-gated work went to Deferred, source indexes were archived or replaced.
Constitution v1.1 records the partitioned Markdown-authority decision.

A new drop arrived 2026-07-18 (two 7-document proposal sets, a product proposal, and a design-reference
folder) and was assessed but deliberately not promoted — see
[`INBOX-ASSESSMENT.md`](../4_Reference/INBOX-ASSESSMENT.md). Triaged 2026-07-20:

- **Living Archive / Editorial Focus product proposal → `2_Todo`; §14 answered the same day.**
  [The proposal](memory-trace-living-archive-and-editorial-focus-proposal.md) was the most mature document
  in the drop. Promoted so it is visible on the roadmap rather than buried, then partly unblocked: **the
  Community Decision Brief slice is approved to build** — deterministic, ephemeral, no provider — because
  its fields already exist as DRAFT labels and graph edges, so it needs no new capture. Briefs are
  ephemeral by default and exportable only on request, keeping generated output out of the corpus per
  Invariant #6. Adoption as the B0b visual target is gated on a task-completion test recorded inside
  [`memory-quality-metrics-v0-proposal.md`](memory-quality-metrics-v0-proposal.md), since nothing today
  measures whether a grounded decision was actually reached. **Still deferred by choice:** the Pro/BYOK
  boundary (§14.3), because that *is* the commercialisation question and this proposal cites the deferred
  report as a source; and both naming questions, until a first brief exists to name. Sections 5 and 9 stay
  parked; `8_Deferred/` is untouched.
- **Both proposal sets (14 documents) → `7_Replaced`, retired 2026-07-20.** Step 1 of the assessment's
  corrected sequence ran first as
  [a current-capability crosswalk](../4_Reference/INBOX-CAPABILITY-CROSSWALK.md): 82 claims scored against the
  owner documents and shipped code rather than the proposals' own account of the status quo. Most were
  already constitutional law or already-shipped capability the proposals understated — the Evidence Pack,
  typed `replaces`/`evolves`, blended retrieval — and five conflicted with explicit owner non-goals.
  A6 and B1 turned out to be the same document written twice. The sets were then de-numbered, renamed
  `-exploration`, and retired pointing back at the crosswalk, which is now the more accurate record.
  **Nothing was deleted and nothing was promoted.**

  The ten claimed deltas were **adversarially re-verified before retirement** — a pass told to falsify
  each rather than confirm it. Five survived clean; five were true only under a narrow reading and were
  reworded; **one was outright false** (the crosswalk asserted evidence-proportional-to-consequence was
  absent from every constitutional layer, missing a *cited* §3 principle at `CONSTITUTION.md:105-106`).
  The crosswalk was corrected before it became the supersession target.

  **Where the surviving residues went:** the constrained-context decision-quality benchmark into
  [memory-quality-metrics-v0-proposal.md](memory-quality-metrics-v0-proposal.md); record-level queryable
  absence into [the semantic-record plan](memory-seed-semantic-record-and-signal-foundation-plan.md)
  Phase 1, which also now discharges step 2 of the sequence — it already models three decisions against
  the ADR contract, so only the ambiguity-vs-cost measurement was added. Open-question and assumption
  lenses gained an owner on the same day when
  [the Living Archive proposal](memory-trace-living-archive-and-editorial-focus-proposal.md) was promoted.

  **Still ownerless — three candidates, recorded so they are not lost:**
  1. **Decision-change impact report** — propagating a decision change to the plans, specs and tasks it
     affects. `link audit` detects uncaptured structural neighbours only. Large and genuinely unowned;
     the assessment's scope-multiplication warning applies directly, so this is a candidate, not a queue
     item.
  2. **Cross-provider output conformance suite** — Invariant #5 makes model independence law, and nothing
     tests it: no fixture corpus, no threshold. Downstream of an extraction pipeline that does not exist.
  3. **Declared entry `intent` field** — genuinely uncovered (no such field; stage is inferred from
     prose), but its *value* is contested. Do not make it mandatory without evidence it beats existing
     topics, DRAFT sections, branch and `F:` evidence.

  **Steps 3–5 remain undone** and no longer gate anything: step 3's gold set is the benchmark above,
  step 4 pilots the open-questions lens under its new owner, step 5 decides promotions. The inbox was
  clear at the time — that was the stop rule. *(It is no longer clear; see the 2026-08-13 drop below.)*
- **Raw design captures → `4_Reference/archived`.** Seven mood-board screenshots were archived once their
  palette and hierarchy themes had been extracted into the folder README; the five generated mockups
  stayed alongside them, cited by live documents (see the follow-up correction directly below).
- **Follow-up correction, same day: the crosswalk, the assessment doc, and the mockups folder itself
  moved from `1_Inbox/` to `4_Reference/`.** JNL caught that all three were still sitting in Inbox despite
  being fully evaluated — the crosswalk and assessment are completed evaluation records other documents
  already cite, and the mockups folder's themes are already extracted and cited by the Living Archive
  proposal in `2_Todo/`. Per the project's own lane rule, `1_Inbox/` holds raw untriaged captures and
  `4_Reference/` holds source material — none of the three still fit the former. `2_Todo/` was considered
  and rejected: that lane is for active work carrying `priority`/`next_action`, and the actual work item
  consuming the mockups (the Living Archive proposal) already correctly lives there; the mockups
  themselves are reference material for that work, not a work item in their own right. Every citing link
  (14 `7_Replaced/` pointers, three `2_Todo/` plans, the archived-captures cross-reference, the
  `docs_check.py` allowlist + its test) was updated; `docs index`/`docs check`/`links check` all clean,
  full suite unaffected.

### 2026-08-13 drop — four live documents, UNTRIAGED (recorded 2026-08-14)

`1_Inbox/` is no longer clear. Four documents arrived on 2026-08-13 and **no triage pass has run**;
nothing below is accepted work, prioritised, or authorised to build. They are listed so the next triage
starts from what is there rather than rediscovering it.

- **Entry point: [`memory-seed-harness-gap-opportunity-report.md`](../1_Inbox/memory-seed-harness-gap-opportunity-report.md)**
  (`mse_ask8e72zq76fdm9f`) — a synthesis of the two comparison lines below into one register of ten
  opportunities (O1–O10), each dispositioned as an existing-owner extension, a bounded candidate needing
  an owner decision, a research/market question, or an explicit non-goal. Its own status line says no
  opportunity is accepted work or assigned a roadmap priority, and its §7 order is "a proposed order for
  triage, not approval". **Deliberately not threaded into "Live work" or the immediate next step.** The
  precedent is this project's own: the Constitution v1.9 decision (2026-08-13, D1) refused to cite the
  Inbox comparison as evidence because an unassessed capture has no standing in a higher-authority
  document. The same applies to the roadmap of record. Read it to *inform* the triage decision; do not
  treat it as having made one. Worth knowing before reading: it withdrew a set of claims its own inputs
  had made — including that quality instrumentation and browser verification are absent — and it names
  its own non-goals (a second quality-metric family or composite grade, volume-as-value, minimal merge
  gates for authoritative memory writes, automatic promotion of generated content, unbounded reviewer
  loops, autonomous control-plane self-modification, and any framing of Memory Seed as
  recursive-self-improvement safety).
- **[Claude line](../1_Inbox/harness-engineering-comparison-claude.md)** and
  **[Codex line](../1_Inbox/harness-engineering-comparison-codex.md)** — the same OpenAI
  harness-engineering comparison worked as two deliberately parallel, unmerged evaluations, each later
  extended with Anthropic's recursive-self-improvement report. Neither supersedes the other; the pair is
  left unresolved on purpose, and **that outstanding triage decision is why both are still in Inbox**.
  Both retain their `v1.8` Constitution pin by design — they record what they were compared against.
- **[`agent-interaction-storylines-review.md`](../1_Inbox/agent-interaction-storylines-review.md)** — a
  *living* document rather than a capture (refreshed 2026-08-13): every named agent↔Memory Seed
  storyline, its tool surface, a surface-parity matrix, and **R1–R13** redundancies with streamlining
  recommendations, plus a deletion-candidate audit. Ground-truthed against the 23 MCP tools and the CLI
  tree. R1–R13 are unowned and unassessed.

**Two of these were already partly consumed, which is worth stating so the triage does not re-litigate
them.** The harness comparison surfaced the Constitution §8 drift that v1.9 then corrected — via the
proposal and command output, not via the capture. And the decision-replay pilot in the evidence
programme above is the direct execution of the gap report's central question. Neither counts as triage
of the drop.

## Captured strategic input — `4_Reference` (2026-07-14 drop, triaged)

A strategy/research set was dropped into the inbox and triaged: the architectural-discovery proposal was
promoted and completed through Constitution v1.0; the three source reports moved to `4_Reference` (source
material, not buildable plans). They overlap the existing corpus (`memory-seed-market-fit-report.md`, the
next-gen blueprint, `agent-rules.md` Working Principles) more than they add; the useful extracted and
remaining ideas are:

- [`../../business/market/memory-seed-gitlens-competitor-report.md`](../../business/market/memory-seed-gitlens-competitor-report.md)
  — GitLens as a competitor/integration target; differentiate on decision/reasoning provenance (not
  Git-history features); "memory beside the commit/PR being viewed" tactics.
- [`../../business/wedges/memory-seed-strategic-synthesis-report.md`](../../business/wedges/memory-seed-strategic-synthesis-report.md)
  — Memory-Quality as a first-class KPI set and a named layered-maturity ladder (raw activity → … →
  institutional knowledge). The measurable, non-gameable subset is now active as
  [`memory-quality-metrics-v0-proposal.md`](memory-quality-metrics-v0-proposal.md).
- [`../4_Reference/memory-seed-rectification-priorities-report.md`](../4_Reference/memory-seed-rectification-priorities-report.md)
  — an entry-type taxonomy (Evidence/Interpretation/Decision/…), content authority, and an
  outcome-comparison benchmark (with/without Memory Seed). Provenance/authority/actionability is now active
  as [`memory-provenance-and-authority-taxonomy-proposal.md`](memory-provenance-and-authority-taxonomy-proposal.md);
  the broader entry-type taxonomy and outcome benchmark remain unpromoted. Several of the report's other
  items are already shipped/covered (two-stage capture, retrieval-over-graph, trust/security groundwork).

The GitLens integration tactic, broader entry-type taxonomy, layered-maturity model, and outcome-comparison
benchmark remain reference input rather than active work.

## Doc-lifecycle Phase 2 (housekeeping)

Tracked in [`document-lifecycle-system-plan.md`](document-lifecycle-system-plan.md) (Phase 1 — lanes +
front door — shipped). **The bulk migration shipped 2026-07-17:** all 43 `2_Todo/completed/` docs plus the
nested `agent-templates/` moved to `5_Completed/`, every inbound reference was repaired, and the folder is
retired — so no legacy archive sits beside the lanes any more. **`docs check` SHIPPED 2026-07-17** (0
errors / 29 warnings on the live tree; its first run caught three real `spec_binding` defects).
**Corrected 2026-08-14 — two of the three "remaining" items have since shipped.** `docs index` exists
with a `--check` mode, and **P3 is done both ways**: `esr` runs `check_docs` and reports `docs_checked`
(`memory_seed/esr.py`), and `.github/workflows/verify.yml` runs `docs check` *and* `docs index --check`
in CI. **Genuinely remaining: the secondary-YAML backfill only.** *(The former third item — removing an
empty `superpowers/specs/` — is dropped: no such directory exists in the working tree or in git
history.)*

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
  2.20.0 released 2026-08-12; the next tranche accumulates under `CHANGELOG.md` "## Unreleased".
- **Ranking:** keep `main` behavior stable; run ranking experiments on a branch, merge only after **both**
  fixtures **and** the shipped real-corpus A/B (`ranking-ab`) show a clear win with no text-ranking
  regression. This is the enforced "expose before you rank" gate from the trio's item 1.
- **Branches/worktrees: branch = workstream** (policy set 2026-07-15). Batch follow-on fixes/evolutions of
  the *same goal* onto one `claude/<kind>/<topic>` branch — the tell is an `evolves`/`related` edge to the
  entry just written, or the same subsystem — and merge the batch to local `main` at a **stable, tested
  stopping point** (self-gated; no per-merge approval pause). Open a new branch only for a genuinely new
  goal. Writing agents stay in their own `.<agent>/worktrees/` namespace (guard enforced).

## Continuity naming

- **Memory Seed** — core runtime, CLI, MCP, retrieval, validation, session files.
- **Memory Trace** — companion package + human review UI (`pip install "memory-seed[trace]"`, `memory-trace`).
- **Trail** — the Memory Trace view for branch/supersession/evolution.
- **Lense** — legacy compatibility name only. **Explorer** — historical working name only.
