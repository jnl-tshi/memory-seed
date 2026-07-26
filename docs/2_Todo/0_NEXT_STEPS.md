# Next Steps

Status: **ACTIVE — Constitution-aligned** (v1.0 ratified 2026-07-14; v1.1 2026-07-16; v1.2 2026-07-17;
v1.3 2026-07-19; v1.4 2026-07-23).
Updated: 2026-07-23

> ▶ **Foundation and memory-quality core shipped 2026-07-15.** The
> [derived-projection Phase 1](derived-projection-implementation-plan.md) (git-watermark warm start +
> atomic swap + three read-path perf refinements) **shipped 2026-07-15** — the plan's former "do first"
> foundation is done. Work still sequences *under* [`docs/CONSTITUTION.md`](../CONSTITUTION.md) **v1.4**
> (each item answers the five-question test — Capture / Validation / Retrieval / Trust / Application — and
> respects Invariant #6: Markdown = source of truth; every DB/cache is a derived, rebuildable projection).
> **v1.3 (2026-07-19)** amended Invariant #2 with write-surface parity: any surface that writes session
> memory must run the same validation as every other, which is what permitted — and constrains — the
> gated MCP write path below.
> The ranking/graph core now includes the full-corpus gate, `replacing_head` plus its bounded boost,
> and inert `link audit --apply` scaffolding. **2.19.0 released 2026-07-17** (live on PyPI). **B0a
> graph/workspace contracts and renderer evidence are complete;
> B2/B0b React parity is the current lead.** The projection's **incremental-ingest fast-follow
> SHIPPED 2026-07-21** — it was the last deferred piece of the derived-projection plan, taken because
> the profile had moved: parsing was no longer the cost, per-history-item git work was
> (44.25 s / 990 git subprocesses → 1.46 s / 7).
Source: the `docs/` lifecycle lanes (folder = state — see [`../README.md`](../README.md)), `CHANGELOG.md`,
and `docs/3_Spec/`. Rebuilt 2026-07-14 from a full inbox+todo evaluation; re-baselined 2026-07-15 after the
Foundation shipped (per-doc status verified against CHANGELOG + code, not this file's prior claims).

## Current state

- **Released: v2.19.0 (2026-07-17)** — live on PyPI, both wheel + sdist; see `CHANGELOG.md`
  "## 2.19.0" for the authoritative list (highlights: memory-quality report/baseline; `link add`;
  `worktree classify --apply`; `docs check`/`docs index`; unified entry grammar + decision-density
  advisory; the breaking `/api/v1` `authority_class` enum rename; OpenSSF hardening — SHA-pinned
  actions, CodeQL, Scorecard, SECURITY/CONTRIBUTING; plus the full 2.18→2.19 tranche folded in).
  The `memory-seed[lense]` deprecated alias **shipped intact in 2.19** (removal never consented at the
  time). **Removed 2026-07-20**, targeted at the 2.20 release — see Track A.4 below.
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
- **Release cadence:** 2.19.0 is **released** (2026-07-17). The next tranche accumulates under
  `CHANGELOG.md` "## Unreleased"; publishing remains a manual-approval gate at the pypi environment.

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
   The topic backfill is ~922 judgment units across the WHOLE corpus (648 of the 888 addressable
   decisions sit inside already-topiced entries, which carry no per-decision attribution). The
   `topic_swarm` skill now owns it, with a two-leg pilot gate; nothing has been run.
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
   **real Mermaid**, so `subgraph` and the full ~30-type vocabulary render in `/next` (both surfaces —
   the inline reader and the zoom modal route through the same component). The skill was reversed in
   the same tranche and *already* says "author standard Mermaid", *already* carries the transitional
   caveat naming the legacy `/` subset parser, and its seed twin is byte-identical — so the "narrow the
   skill" remedy is done and **no skill edit is needed**. What is genuinely left is not a mismatch but a
   documented residue: the vanilla `/` UI still ships the hand-written subset renderer
   (`static/app.js`, `renderDiagramBlock`), so a `subgraph` sidecar shows stray boxes *there only*.
   That is the correct trade under Invariant #6 — the Markdown is the source of truth and VS Code,
   GitHub and `/next` all run real Mermaid, so three renderers beat accommodating a retiring fourth.
   It retires with the `/` UI itself, under the B2 parity-sign-off gate already recorded in Track B
   below ("the current vanilla `/` UI remains the supported fallback until explicit parity sign-off");
   **delete the skill's caveat paragraph when that sign-off lands.**
5. **Cross-session `branch:` contamination** — **HALF FIXED, half needs your decision (2026-07-26).**
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
   never passed to the CLI, so no code can recover it. `--branch`/`--no-branch` already exist as the
   workaround. Options A–D in the proposal; recommendation is A (document the workaround) plus D
   (harness always passes `--branch`), with B (warn on multi-worktree repos) rejected because it
   would fire on every legitimate primary-checkout append. **Your call.**
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
8. **Decision rows in the Graph** — **BACKEND SHIPPED 2026-07-26; client wiring blocked on one
   contract decision.** `/api/v1/graph/projection` accepts `include_decisions` (default **false**, so
   the entry-level surface is untouched) and `graph()` takes `decision_row_scope`: `"all"` for the
   Trail, `"linked"` for the Graph. Forging an entry-level line for a decision edge was tried and
   **reverted** — `test_decision_edges_never_reach_entry_level_consumers` asserts by set-equality
   against a sidecar-deleted control that the entry-level surface stays indistinguishable from a world
   without decision edges, and that guard is deliberate.
   The scope split is measured, not stylistic: expanding every decision into the force layout added
   446 rows of which **276 were isolated** — worse than the 9 orphans it set out to fix. Filtering by
   entry got that to 110; filtering by **ordinal** gets it to **0**.
   **Your call before a client lands:** with rows on, full-corpus orphans go 83 → 94, because ~11
   anchors whose only edges were decision-level now float while their rows carry the relationships. A
   timeline gets parent/child from adjacency; a force graph has no tether between an anchor and its
   rows, and adding one means a **fifth edge kind** — which the four-independent-never-merged-kinds
   contract makes a deliberate decision, not an implementation detail. No client shipped, because
   shipping UI now would bake in whichever answer I guessed.
8. **Decision rows in the Graph — the fix for the last 9 orphans** (P2). Nine entries whose only
   relationships are decision-level render as unconnected: an entry-granularity view has no decision
   row for `B:d2 evolves A:d1` to terminate on, so the edge has nowhere to land. Emitting an
   entry-level line instead was tried on 2026-07-26 and **reverted** —
   `test_decision_edges_never_reach_entry_level_consumers` asserts by set-equality against a
   sidecar-deleted control that the entry-level surface stays indistinguishable from a world without
   decision edges, and that guard is deliberate. The sanctioned fix is to render the decision rows
   themselves: `_expand_decision_rows` already exists and `include_decisions` is Trail-only today, so
   the Graph calling it gives those edges a real endpoint and resolves the orphans without touching
   the guard. This is also step 1 of the sequencing already recorded in
   [decision-level-topics-proposal.md](decision-level-topics-proposal.md) ("render the decision-node
   graph using the substrate that already exists"), so it unblocks that track as well.

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

1. **BG1 steps 5–7 — actionability policy + §7 graduation.** Step 4 (display authority/provenance in the
   inspector) **shipped 2026-07-17**. Step 5–6 add an
   `actionability` field computed by policy with machine-readable reason codes, plus fixtures proving
   generated/provider content **cannot** become actionable on its own; step 7 is the Constitution §7
   amendment that would let annotation/generated content become agent-actionable.
   *Options:* **(a)** build 5–6 now as additive/advisory — everything stays non-actionable in effect,
   fail-closed by construction *(recommended: keeps momentum, adds no trust the model doesn't already
   grant)*; **(b)** hold 5–6 until the participant/role model (B3/Phase 6) exists. Step 7 needs your
   explicit amendment approval regardless of (a)/(b).
2. ~~**Track C.2 — ESR Persona Usage Check.**~~ **RESOLVED 2026-07-20** — option (a): propose-and-wait,
   built. Step 17 (its own subsection) landed in `.memory-seed/skills/end_of_turn.md`, mirrored to the
   seed twin; `agent-rules.md`'s "End Of Turn" summary lists it. Conservative window (30 days or 20
   entries, whichever is longer), grace period for newly-activated personas, and the lossy-`agent_name`
   caution are all built in per the proposal's own subtleties section. Never auto-deactivates.
   Moved [`persona-usage-deactivation-esr-proposal.md`](../5_Completed/persona-usage-deactivation-esr-proposal.md)
   to `5_Completed/`; its one remaining item — an optional deterministic `memory-seed persona usage`
   CLI report — is a follow-up enhancement, not a blocker.
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

## Live work — sequenced (Constitution-aligned)

Active work, sequenced under the Constitution (each item answers the five-question test — Capture /
Validation / Retrieval / Trust / Application — and respects Invariant #6). The foundation and
memory-quality core shipped 2026-07-15, so **B0a graph/workspace work now leads**.

### Foundation — derived-projection Phase 1 ✅ SHIPPED 2026-07-15

**Made Trace fast + made Invariant #6 real.** The SQLite cache is now a formalized read-model per the
[contract](../3_Spec/draft/derived-read-model-projection-contract.md): explicit Markdown→projection ingest
with a byte-identical rebuild, a **git-watermark warm start** (O(changes) freshness — no whole-corpus scan)
and **atomic build/swap**, plus three read-path perf refinements (`chunk()` 132 ms → 3.9 ms). Plan:
[`derived-projection-implementation-plan.md`](derived-projection-implementation-plan.md). Five-question
test → **Retrieval** (fast reads) + **Application** (usable Trace on large histories).
**Remaining fast-follow (deferred, low-urgency):** *incremental ingest* — re-project only the delta files'
chunks and recompute whole-history git meta only when HEAD moved, gated behind an
`incremental == full-rebuild` equivalence test. Reads are already ~3.9 ms, and the 2026-07-18
worktree-switch profiling re-confirmed the deferral: chunk parsing is ~0.35s of a ~10.3s rebuild (~3%) at
~500 entries — the dominant 92% (per-merge `git merge-base` spawns) was fixed instead via the process-wide
fork-point memo + `ensure_current` warm starts. Incremental ingest waits until corpus scale
makes parse time material (~5k+ entries). **Phase 2** (git-rooted historical integrity, G6/G7) is the next projection increment after the
trio.

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
  (roadmap Phase 2). `memory-trace/client/` now builds a TypeScript React shell to packaged `/next` assets;
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
  **Still open:** focus restoration and screen-reader labels beyond one component's Storybook coverage,
  and graph alternatives (no non-visual equivalent for the Cytoscape canvas evaluated yet) — this was a
  first pass, not the completed audit. The current
  vanilla `/` UI remains the supported fallback until explicit
  parity sign-off.
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
  (commit + `path:line`), and navigable linked-memories/related-activity cards. **The Trail view shipped
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
  REJECTED, not pending** — [`adr-graph-community-detection.md`](../3_Spec/draft/adr-graph-community-detection.md).
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
  What remains of B0b is therefore formal accessibility/scale acceptance, plus promoting the ADR from
  `draft` to accepted.
  Keep the SVG renderer until explicit parity sign-off.
  Only after B0b acceptance may the
  [`structural-provider proposal`](memory-trace-structural-graph-enrichment-provider-proposal.md) define a
  provider-neutral contract and pilot optional `code-review-graph`; providers never own canonical decision
  semantics or alter ranking without exposure and real-corpus validation.
- **BG1 — Provenance and authority taxonomy** *(constitutional gate before actionable annotations or
  agent-influencing generated output)* —
  [`memory-provenance-and-authority-taxonomy-proposal.md`](memory-provenance-and-authority-taxonomy-proposal.md).
  Keep provenance, authority, lifecycle, and actionability as separate fields; do not create a single
  trust score. **Steps 1–4 SHIPPED** — the enum-constrained `AuthorityClass`/`ProvenanceClass` on the
  node (2.19), and the inspector now displays authority + provenance distinctly (2026-07-17). Steps 5–7
  (actionability policy, fail-closed fixtures, §7 graduation) are the **open-decisions gate #1** above.
- **BG2 — Memory-quality metrics v0** — ✅ **v0 SHIPPED 2026-07-17; usefulness review COMPLETE**
  (proposal step 6). [`memory-quality-metrics-v0-proposal.md`](memory-quality-metrics-v0-proposal.md).
  `memory-seed quality report [--json]`; first baseline at
  [`../4_Reference/memory-quality-v0-baseline.md`](../4_Reference/memory-quality-v0-baseline.md)
  (unlinked 95/431 = 22.0%; DRAFT reason coverage 403/403; BG1-dependent metrics honestly `unavailable`).
  **Review (JNL, 2026-07-17):** the baseline is useful as-is — keep it, set **no** targets. BG2 is done;
  the BG1-dependent metrics stay `unavailable` until BG1 lands (see the open-decisions gate for BG1).
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
2. **ESR Persona Usage Check** — ✅ **SHIPPED 2026-07-20**.
   [`../5_Completed/persona-usage-deactivation-esr-proposal.md`](../5_Completed/persona-usage-deactivation-esr-proposal.md).
   A new end-of-turn step, the symmetric inverse of the shipped unregistered-persona check: flags active
   personas with no recorded `agent_name` use over a conservative window and **proposes** flipping them to
   `status: inactive` (approval-gated; never auto-applies; deactivate ≠ delete). Built as propose-and-wait
   per the open-decisions gate above.

The two compound (fewer active personas → lighter worker *and* primary startup load) but neither blocks the
other. Both sit **below Track A's open tails** in priority — small, sequence-flexible guidance changes.

### Track D — semantic memory and workflow evolution

Approved 2026-07-16 after full Inbox triage. These plans are dependency-ordered and do not displace B0b:

1. **Semantic record and signal foundation (P1)** —
   [`memory-seed-semantic-record-and-signal-foundation-plan.md`](memory-seed-semantic-record-and-signal-foundation-plan.md).
   After B0b plus BG1/BG2, prove authoritative append-only Markdown ADR sidecars on three real decisions.
   Entries retain rationale/evidence; the sidecar owns promotion/lifecycle; current status and indexes are
   derived. Historical entries are not rewritten and ranking cannot change before signal exposure plus the
   real-corpus gate.
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
  step 4 pilots the open-questions lens under its new owner, step 5 decides promotions. The inbox is
  clear regardless — that is the stop rule.
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

## Captured strategic input — `4_Reference` (2026-07-14 drop, triaged)

A strategy/research set was dropped into the inbox and triaged: the architectural-discovery proposal was
promoted and completed through Constitution v1.0; the three source reports moved to `4_Reference` (source
material, not buildable plans). They overlap the existing corpus (`memory-seed-market-fit-report.md`, the
next-gen blueprint, `agent-rules.md` Working Principles) more than they add; the useful extracted and
remaining ideas are:

- [`../4_Reference/memory-seed-gitlens-competitor-report.md`](../4_Reference/memory-seed-gitlens-competitor-report.md)
  — GitLens as a competitor/integration target; differentiate on decision/reasoning provenance (not
  Git-history features); "memory beside the commit/PR being viewed" tactics.
- [`../4_Reference/memory-seed-strategic-synthesis-report.md`](../4_Reference/memory-seed-strategic-synthesis-report.md)
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
errors / 29 warnings on the live tree; its first run caught three real `spec_binding` defects). Remaining:
`docs index`, secondary-YAML backfill, and P3 (wire `docs check` into `esr` + CI). *(The former third item — removing an empty `superpowers/specs/` — is dropped: no such directory
exists in the working tree or in git history.)*

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
  2.19.0 released 2026-07-17; the next tranche accumulates under `CHANGELOG.md` "## Unreleased".
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
