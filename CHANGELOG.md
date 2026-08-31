# Changelog

All notable changes to Memory Seed are summarized here.

## Unreleased

### Changed (breaking)

- [2026-08-31] **Ephemeral Evidence Packs now use one typed identity contract.** Pack and resolver version
  2 replace the generic per-item `ref` field with `id`; path-selected ADRs emit `kind: adr` and their
  frontmatter `adr_id`, decision slices emit `kind: decision` and their canonical decision ID, `source`
  remains the canonical Markdown location, and `content_digest` verifies the selected content. Evidence
  Packs are inline, non-authoritative results, so v1 consumers re-resolve the Retrieval Specification
  rather than migrating stored packs; v2 validation rejects v1 packs.

### Changed

- [2026-08-13] **Bootstrap-generated runtime indexes are now tree-first.** Every new project index
  must put a purpose-annotated repository tree and an expanded `.memory-seed/` tree immediately after
  its purpose. A small path/purpose/read-when table may clarify non-obvious entry points, but cannot
  replace the visual trees or grow into an exhaustive file inventory.

- [2026-08-13] **SessionStart now routes whole-session context by measured size instead of injecting five
  capped entries.** `situate` reports the latest applicable session's character/byte/entry counts and
  selects direct reading at or below 12,000 characters or an ≤800-token, source-linked economy-worker
  briefing above it. The hook consumes that shared report, remains model-free, and keeps policy,
  Constitution, roadmap, and release checks lazy until the task requires them.

## 2.20.0 - 2026-08-12

Landed dates in this section come from the corresponding `.memory-seed/sessions/` records; Git
history is used only as a cross-check.

### Changed (breaking)

- [2026-08-11] **Memory Trace now has one supported frontend.** The React/TypeScript client is served at `/`;
  `/next` redirects existing bookmarks to it. The retired vanilla `static/index.html`,
  `static/app.js`, and `static/styles.css`, `--open-both`, their Node-VM golden/capture
  harnesses, and the Python tests that inspected implementation strings were removed. The
  independent renderer benchmark and unversioned compatibility APIs remain.
- [2026-08-09] **`session append` no longer accepts entry-level lifecycle links.** `--related` / `--replaces` /
  `--evolves` (and the matching `related_entries` / `replaces` / `evolves` arguments to
  `session_append_entry`) are refused; declare the edge on the decision that owns it via
  `--decisions-file` / MCP `decisions[].links`, which is where its evidence and evolution type now
  live. A raw ref in an entry's YAML tells a human reading the Markdown nothing, and Invariant #6
  already assigns lifecycle facts to sidecars and narrative rationale to entries. **Published
  entries are unaffected** — the 772 refs already in entry YAML are read exactly as before,
  forever; only new writes are closed off. The arguments stay on `session_append_entry` for one
  release as the refusal surface, so a direct Python caller gets a message naming the replacement
  rather than a `TypeError`.

### Added

- [2026-08-11] **Bootstrap now turns durable choices into an explicit ADR authority chain.** It
  classifies future-session constraints, creates proposed founding ADRs before a session corpus
  exists, accepts only user-confirmed choices after the first session records them, and generates a
  thin index authority map plus policy links instead of duplicating rationale. Constitutions remain
  optional and govern only when the active index declares them ratified.
- [2026-08-11] **`adr promote` exposes the founding and binding contract already supported by the
  ledger.** CLI callers may choose either `--entry-id` + `--decision` or `--founding-source` +
  `--founding-quote`, and may repeat `--constitution-ref ref=role` and `--supporting-decision`.
  Existing session-decision promotion remains compatible, and ADR head-changing writes remain
  intentionally CLI-only.
- [2026-08-10] **Read-only MCP twins complete the chain, sweep, and ESR workflow.**
  `memory_links_chain(ref, cwd)`, `memory_link_audit(entry_id?, session_date?, top_k?,
  semantic_enabled?, cwd)`, and `memory_esr(session_date?, cwd)` return the exact canonical
  structured results from `links chain --json`, `link audit --json`, and `esr --json`.
  They share the chain reader, audit serializer, and ESR report rather than reimplementing them;
  audit deliberately has no apply/scaffold mode and ESR preserves its read-only cache inspection.
  The MCP registry grows by three read tools while the four-tool write set is unchanged.
- [2026-08-10] **The canonical corpus now has a reconstructable core projection cache.** Raw and sidecar-augmented
  entry, section, and decision views are persisted outside the repository under a stable
  runtime/worktree key while session Markdown, link/topic sidecars, and project configuration remain
  authoritative. Exact source fingerprints, Git HEAD watermarks, schema/integrity checks, owner-token
  leases, and atomic publication make every uncertain state fall back to a full or isolated source
  reconstruction. ESR independently rebuilds the live corpus and reports cache health without
  repairing or mutating the artifact; ESR and append tool calls reuse one invocation snapshot instead
  of repeatedly reconstructing the same canonical view.
- [2026-08-10] **Memory is now an explicit prerequisite for consequential conclusions.** The universal rules and
  history-retrieval trigger cover reviews, audits, recommendations, and claims that behavior is
  redundant, obsolete, removable, replaceable, or ready to consolidate. Decision Harvest carries
  every consequential fetched entry to an explicit `replaces` / typed `evolves` / `related` /
  authoring-only `no-edge` disposition, with byte-identical live and seed control files.
- [2026-08-10] **Append review and no-change recording have CLI/MCP parity.** CLI `session append` now runs the
  same content-bound ADR review preflight as `memory_session_append`, returning the full contexts and
  receipt before a zero-byte refusal and accepting the retry through `--adr-review-receipt`.
  `memory-seed adr reviewed --adr-id <id> --entry <entry-id> --reason <text>` and MCP twin
  `memory_adr_reviewed` append the same evidence-backed `reviewed-no-change` event without moving the
  ADR head or manufacturing a session entry.
- [2026-08-10] **Unlinked append decisions receive a memory-aware nudge.** Passing MCP dry runs and real writes
  return the same `link_suggestions` payload when a decision has no lifecycle or related link;
  optional `consulted` entry ids sort first, no edge is auto-written, and the response requires an
  explicit replaces/evolves/related/no-edge classification.

- [2026-08-10] **`links graph-diff` snapshots and gates the effective evolves graph.** `--snapshot <path>` writes
  `effective_graph_snapshot()` (the same effective corpus every graph reader uses) to JSON;
  `--against <path>` rebuilds it and diffs. Exit 1 iff the entry-level `evolves` edge set changed —
  a per-node addition/removal or either evolves aggregate — naming every changed node; `refines`
  typing deltas are always reported but never gate, so a retract-and-retype campaign passes by
  design. Promotes an assertion that had only ever lived in throwaway campaign scripts, despite
  catching two silent corruptions (the 807-edge vanishing, a +3 edge resurrection) that `links
  check` read as OK.
- [2026-08-10] **`link retract` writes the append-only correction.** `memory-seed link retract <kind> <ref>
  --from <entry_id> [--retype <kind-or-evolution-type>] [--note] [--date-pin] [--dry-run]` and its
  MCP twin `memory_link_retract` — the first MCP link-write tool — append the `retracts:` block that
  fixes `untyped-evolves`, `unknown-evolution-type` and `multiple-refines-successors`, which until
  now was hand-formatted Markdown every time. A comma ref (`mse_x:d1,d3`) fans out to one retract
  line per ordinal (a retract names exactly one edge) while the re-authored line keeps the comma
  form. Every guard runs before a byte is written and they report together: unparseable ref, unknown
  source entry, an edge the corpus never declared, a retraction that would pre-date its declaration,
  a `--date-pin` that is not the declaration date, and a `refines` retype whose successor slot
  another entry holds (named in the message). The CLI re-runs `links check` after the write.

- [2026-08-09] **Retractions reach entry-YAML edges.** A link sidecar's `retracts:` now removes an edge authored
  in the entry's own YAML, not only edges declared in sidecar lists — previously a silent no-op
  covering 232 of the 807 evolution-type backfill edges. Scoped strictly to the retracting block's
  own `entry_id`, and mirroring the surviving-projection rule so a retract-and-retype keeps its
  typed replacement.
- [2026-08-09] **The evolution-type backfill is applied.** Every effective untyped `evolves` edge is typed via
  retract-and-retype sidecar blocks: 109 `refines` / 692 `builds-on` across 471 entries, under the
  two-run agreement rule (`refines` only where both independent judgment runs said so). Six edges
  the snapshot carried but hand audits had already retracted were left dead rather than
  resurrected. Gated on a graph assertion — effective edge set byte-identical before and after;
  nodes carrying a `refines` successor went 1 → 105.
- [2026-08-09] **The `refines` lineage walk is decision-keyed.** `build_refines_spine` / `RefinesSpine` in
  `semantic_cache` key successors and predecessors by `(entry_id, ordinal)` — an ADR head is
  `mse_x:dN`, and the one-successor cap is a per-decision contract. `head()` walks to the terminus;
  `chain_through()` returns the ordered root → head chain. A missing ordinal on a single-decision
  entry normalises to `d1`.
- [2026-08-09] **Chains are artifacts, and a chain takes one link — at its head.** `links chain <ref>` renders
  the refines chain a decision belongs to (root, ordered members, head, length, owning ADRs),
  derived entirely from the edges. `session append` refuses a decision whose `evolves` names two
  members of one chain, with the fix in the message; `links check` raises the same shape as the
  `redundant-chain-edge` warning on published history. Cross-chain multi-evolves (a merge) stays
  fully legal.
- [2026-08-09] **Link-audit candidates know their chain position.** `link audit` annotates every candidate from
  the decision-keyed spine: interior chain members arrive marked **related-only** (`refines` slot
  taken, chain lives at `current_form`), replaced decisions never arrive at all — their terminal
  replacement substitutes, marked `substitute_for`. Carried on all five projections and taught to
  the swarm in `link_swarm.md`.
- [2026-08-09] **Untyped `evolves` is now a `links check` error.** With the backfill landed, an EFFECTIVE
  `evolves` edge carrying no type raises `untyped-evolves` at error severity, with no cutoff.
  Judged over the effective graph, so retracted untyped originals in published files do not fire;
  any instance is closable append-only via retract-and-retype.
- [2026-08-09] **`esr` reports an ADR review queue.** When the decision an ADR is headed by has an agreed
  `refines` successor, the concern's current form has moved and the ADR has not — a mechanical
  fact, reported the way `needs-diagram-review` reports a diagram invalidated by evolution. The
  walk runs to the chain's terminus, not one hop, and non-head decisions attached to the ADR are
  listed separately as secondary. **Flag only:** nothing here moves a head, and each line asks for
  an authored revision or a recorded reviewed-no-change. On the control-plane corpus (57 ADRs, 109
  agreed `refines` edges) this is six lines — a queue that gets read, not a firehose.

- [2026-08-09] **Typed evolution: `refines` and `builds-on`.** An `evolves` ref may carry its kind as a trailing
  `(refines)` / `(builds-on)`, and the decisions envelope requires one on every new `evolves` edge.
  `refines` is the next form of a decision and is capped at **one successor per target**;
  `builds-on` is later work resting on a decision that stays valid, and is unlimited. That cap is
  what makes a lineage walkable as a line: following `evolves` to its terminus currently returns up
  to 25 unrelated heads, because one edge name has been carrying both relations. Enforced at
  `session append` and, corpus-wide, by the new `multiple-refines-successors` error in
  `links check` — two branches can each author a `refines` without either being refused, so write
  time cannot be the only guard. An unrecognised word raises `unknown-evolution-type`. Edges
  written before this grammar are *unclassified*, never "neither".
- [2026-08-09] **Write-time link evidence.** A `replaces` or `evolves` item in the decisions envelope requires
  `why` — one line for why the edge was drawn — rendered into the link sidecar's `edge_evidence:`
  list, keyed by the exact ref token. `related_entries` needs none. The author knows the reason
  exactly once, at authoring, and append-only makes it unrecoverable afterwards.

### Fixed

- [2026-08-11] **Re-filing an ADR diagram review now clears its stale review tick.** Historical
  append-only diagram blocks remain syntax- and reference-validated, but only the newest block for
  an ADR is compared with the current authoritative decision date. Previously every old block kept
  emitting `needs-diagram-review`, so the documented re-file action could never satisfy the check.
- [2026-08-10] **`session merge-branch` no longer reports a completed merge as a failed commit after a Git
  timeout/non-zero result.** It now reconciles only a fully evidenced merge: a changed two-parent
  HEAD with the recorded base and exact source tip, every planned `Memory-Entry` trailer, and no
  remaining merge state. Proven success follows the existing safe source-worktree cleanup; every
  ambiguous or genuine failure remains inspectable.
- [2026-08-10] **`esr --json` dropped both ADR queues, and the review-queue section named no runnable
  command.** `EsrReport.to_dict()` omitted `adr_attachment_candidates` and `adr_head_reviews` -
  now top-level keys, so `esr --json` automation can see them. The `## ADR review queue`
  preamble now names both answer paths concretely: the `adr revise` / `adr transition` command
  pair for a revision, and the MCP `memory_session_append` no-change review gate (the CLI has no
  equivalent) for reviewed-no-change.
- [2026-08-10] **`dangling-retract` no longer fires on entry-YAML edges.** `links check` counted an edge as
  "declared" only when a link *sidecar* declared it, so retracting an edge authored in the entry's
  own YAML — which the reader has honoured since 2026-08-09 — was reported as a retraction of
  nothing. Latent rather than observed: this corpus currently carries no such retract (its 179
  issues are byte-identical before and after), but the refusal reproduces on a two-file fixture and
  would have blocked every entry-YAML correction the new `link retract` writes. Both surfaces now
  feed the declaration bookkeeping, with first-declaration-wins dates. Widening what counts as
  declared can only remove false refusals: a retract naming an edge that exists nowhere is still an
  error.

- [2026-08-09] **The mandatory ADR review gate could be bypassed by a link shape it did not recognise.**
  `adr.lifecycle_targets` and the lifecycle-assertion builder both read only bare ref strings, so a
  structured link item read as "no lifecycle target" and the gate silently did not fire. Both now
  accept either shape.

- [2026-08-05] **Decision-level retrieval is the default memory unit** (`granularity="decision"`). `memory_search`
  now returns one result per recorded decision, keyed by the canonical `mse_<entry>:dN` identity that
  topics, lifecycle edges, ADRs and Trace already use, and each result carries that decision's
  **whole DRAFT block** rather than a 280-character preview. Entries without `#### Dn` headings keep
  the whole-entry unit, which preserves the 2026-05-26 rule that a decision must never be separated
  from its rationale - a `Dn` block satisfies it by construction. Measured cost: ~1,800 tokens per
  eight-result search against ~560 for entry granularity, on an 836-entry corpus.
- [2026-08-04] **Attention signal: retrieval events are logged and exposed read-only.** `memory_get_chunk`
  fetches score into a decayed per-entry `attention_score` (30-day half-life) alongside
  `fetch_count` and `last_fetch` on every search result and chunk payload; `memory_search`
  impressions are logged at weight zero so the ranker cannot feed on its own output. Both state
  files are gitignored and self-registering. Default ranking is unchanged and the flip stays behind
  `memory-seed ranking-ab --signal attention`.
- [2026-08-04] **File-touch decision surfacing** (`.memory-seed/hooks/file-touch-decisions.py`). A Claude
  PostToolUse hook: editing a file named in a decision's `F:` refs injects that decision mid-turn,
  names its supersession successors, and states the duty to record a `replaces`/`evolves` edge if
  the change contradicts it. Fail-open, rate-limited per session and file.
- [2026-08-05] **Durable non-decision facts route to `index.md` at capture time.** The Decision Harvest gained a
  step for facts that have no `R:` to give - roles, codenames, cadences, budgets - which previously
  fell through every capture path; a turn that establishes only facts and changes no code now
  records. One claim per Active State bullet, filed by its own predicate.

### Changed

- [2026-08-07] **`sidecar-unclassified-stub` is resolved by a later sibling block.** The warning was decided per
  block, but append-only forbids editing a stub to record its own answer — the verdict always
  arrives as a later sibling block, so the warning could never be cleared. It is now an entry-level
  question decided after every block is read: a stub survives only when no later block for that
  entry authors an edge or declares `edge_status: not_applicable`. Ordering is `(heading timestamp,
  block index)`, the same later-and-more-specific precedence `edge_status` already used, so a
  resolution written *before* a stub correctly leaves it standing. On this repo's corpus the count
  fell 71 → 67 immediately: four 2026-07-21 stubs had been answered long ago and had been warning
  falsely ever since. A subsequent link-swarm campaign over the remaining 67 took it to 9.
- [2026-08-07] **`link audit --apply` sorts a non-chronological sidecar instead of refusing it.** A link sidecar
  is filed under its SOURCE entry's session date, but a later enrichment pass stamps its blocks with
  the authoring wall clock (block identity is `(entry_id, heading timestamp)`, so a second block for
  one entry needs a distinct stamp). Those two rules together make a re-visited file legitimately
  non-chronological, and `apply_link_gap_stubs` used to raise `blocks are not chronological` — which
  permanently closed that date to further scaffolding. It now re-sorts the block region on write, the
  same stable sort `_write_chronological_link_sidecar_file` already used for the fuse; block content
  is untouched, so the reorder stays inside the append-only contract. Four dates in this repo's own
  corpus (`2026-07-03`, `-05`, `-12`, `-17`) were stuck this way and have been re-sorted.
  `link_swarm.md` step 5 and the sidecar spec now state both rules explicitly — "the day's sidecar"
  read as *today's*, which would have failed `links check` with `link-sidecar-date-mismatch`.
- [2026-08-04] **Reversing a recorded decision on a live instruction is no longer a STOP.**
  `.memory-seed/skills/risk_signaling.md` splits its former "Constitutional / architectural
  conflict" category: ratified invariants keep the hard Stop, while an explicit live instruction to
  reverse a *recorded decision* is Proceed-and-flag with two mandatory parts - carry the old
  rationale forward in the reply, and record a superseding entry with a `replaces`/`evolves` edge in
  the same turn. Constitution §11's rejection sentence covers invariants; Invariant #2's "extend and
  supersede" is the mechanism for ordinary decisions. Unattended plan-driven runs still park.

### Fixed

- [2026-08-05] `memory-seed ranking-ab` no longer reports a vacuous PASS for a signal whose evidence base is
  empty. Signals may declare `requires_affected_hits`; the `attention` signal does, so an empty
  retrieval log now refuses with a stated reason and a non-zero exit instead of certifying nothing.
- [2026-08-05] The retrieval relevance band (`relevance`, `no_match_above_threshold`) is labelled
  **uncalibrated**: measured on the 836-entry corpus it does not discriminate - nonsense queries
  band `strong` and the no-match signal never fires. `search_memory` now returns
  `relevance_calibrated: False` and the retrieval guidance tells agents to judge relevance from the
  served content rather than the band.

### Added

- [2026-08-04] **Graphify structural-analysis skill ships in the coding profile** (`graphify_analysis.md`).
  The skill had been registered in both trigger registries and `SEED_FILES` without a profile,
  description, or package-data entry, so `init` never installed it and wheels would not have
  shipped it. It now installs with `--profile coding` alongside `code_search.md`, covering
  architecture, dependency-impact, call-path, and community-level structural questions.
- [2026-08-04] **ESR orphan-worktree residue detection.** The read-only Worktrees section now compares Git's
  registered worktrees with physical checkout directories beneath the Claude, Codex, Gemini, and
  Cursor worktree namespaces, including when ESR runs from a secondary checkout. Deregistered
  directories are surfaced as `ORPHAN RESIDUE CANDIDATE`; the End Of Turn runbook adds a fail-closed
  audit, recovery, consent, Windows long-path cleanup, and verification pass so partial Git removal
  cannot silently accumulate multi-gigabyte checkouts again.
- [2026-07-27] **Stale-console-script guard** (`package_provenance()` in `core.py`). When a `memory_seed/` source
  tree exists at or above the working directory and the imported package resolves **outside** it, the
  CLI refuses with exit code 2 and prints both resolved paths, both versions, and the working
  invocation; `version` and `help` stay runnable because they are how the mismatch gets diagnosed, and
  `MEMORY_SEED_ALLOW_FOREIGN_PACKAGE=1` permits a deliberate cross-version run. The MCP server warns on
  stderr instead of refusing, so a stale launch never takes the harness's server down. This closes a
  confirmed silent-corruption path: in a git worktree `uv run --no-sync` leaves `.venv` empty, so no
  console script exists there and `memory-seed` resolves through PATH to an older global build — whose
  `docs check` reported phantom lane errors for folders this tree allowlists and whose `docs index`
  regenerated `docs/README.md` from stale code, dropping a lane count, a regression attributable to
  nothing in the diff. The predicate is silent under an editable install, so `verify.yml` (already on
  `python -m memory_seed.cli`) is unaffected. A *pre-guard* global build cannot check itself; refresh
  the global install so the next stale invocation is loud.
- [2026-07-26] **Decision-level topic judgment swarm** (`topic_swarm` skill, 2026-07-26). The sibling of `link_swarm`
  for the third sidecar family: a suggest-only, mechanically validated, human-approved backfill of
  `<slug>:dN` topics across the whole corpus, including entries that already carry authored entry-level
  topics (those have no per-decision attribution). The judgment unit is the **addressable** decision
  ordinal from `entry_body_decisions()` — not the `- D:` bullet count, which disagrees on 10 entries and
  would emit `dangling-topic-decision` errors. The campaign is gated behind a two-leg measured pilot
  with a stated pass/fail line: rolled-up macro-recall against blind-judged authored topics, plus
  human-adjudicated per-decision attribution that must beat free inheritance. Registered under the
  `curation` skill profile. No swarm has been run; zero topic sidecars exist. Specs:
  `docs/3_Spec/draft/decision-level-topic-sidecars.md`, `docs/2_Todo/decision-level-topics-proposal.md`.
- [2026-07-25] **Lifecycle-link judgment swarm** (`link_swarm` skill, 2026-07-25). An optional, network-using fan-out
  of small models judges `link audit` gaps at decision granularity — the automated judgment layer above
  the mechanical sweep. It only suggests: a mechanical validator (quote-grounding, ordinal existence,
  forward-only) and a human scope approval gate every write, and stored edges are ordinary `:dN` edges
  with no dependency on the model that suggested them (Invariants #1, #5). A campaign judged all 1,108
  file-overlap never-linked pairs and landed 696 decision-level edges. Spec:
  `docs/3_Spec/draft/link-audit-decision-judgment-swarm-proposal.md`.
- [2026-07-25] **Structured `edge_confidence` link-sidecar field.** Each machine-suggested edge carries
  `{ref, confidence, tier}` per authored ref; `links check` tolerates it as an unknown sibling key (no
  parser change). The Trace graph payload exposes `confidence` on `GraphEdge`/`RendererGraphEdge`
  (`/api/v1`), and the graph + Trail **fade low-confidence edges** so an unverified suggestion never
  reads as settled fact. Spec: `docs/3_Spec/draft/edge-confidence-metadata.md`.
- [2026-07-25] **Append-only link retraction (`retracts:`).** Downgrade or remove a published lifecycle edge through a
  new-block `retracts: <kind> <ref> [(date)]` correction (the fuse refuses in-place edits to published
  link sidecars); the reader subtracts it and `links check` validates `malformed-retract`,
  `dangling-retract`, and `retract-before-declaration`. A downgrade is a retract of the old kind plus a
  fresh edge of the new kind — the sanctioned append-only correction path (Invariant #2). Spec:
  `docs/3_Spec/draft/link-retraction.md`.

### Changed

- [2026-08-01] **Session-entry persona-name metadata retired.** New entries carry `agent_type` but no longer accept or
  write `agent_name`; the CLI, MCP schema, retrieval payloads, Memory Trace contracts, and active
  control-plane documentation use the reduced shape. Historical append-only entries remain untouched
  and readable. The dependent end-of-turn persona-usage heuristic was retired with its lossy signal.

- [2026-07-25] **`related_entries` may carry decision-level refs (`:dN`)** (JNL's direction
  2026-07-25). The decision-ref grammar, previously scoped to
  `replaces`/`evolves`, now generalizes to `related` too: `related_entries:
  - mse_x:d2` (or `- d1 -> mse_x:d2`) draws a `related` edge terminating on the
  target's decision row, validated like a lifecycle decision ref (ordinal
  existence, forward-only, `:d1`-on-single-decision rejected as redundant) and
  never projected up to an entry-level related edge. Unlike lifecycle edges it
  is **allowed, not mandated** — a bare related ref to a multi-decision target
  stays valid, keeping related casual for hand-authoring while letting the
  link-swarm emit decision-level related in one pass. Read side: the sidecar
  reader, `semantic_cache` extractor, `retrieval.related_of`, and the Trail's
  `_decision_edges_for_rows` all carry `related` in the `decision_edges`
  channel (canonical kind `related`; the entry-level list key stays
  `related_entries`).

- [2026-07-24] **BREAKING (write path): decision granularity is mandated on lifecycle
  edges** (grammar v2, JNL's direction 2026-07-24). `session append` /
  `memory_session_append` name a decision on an edge end exactly when the
  entry it belongs to has more than one decision: a target with **2+
  decisions** must be written `<entry_id>:dN` (comma form `mse_x:d1,d4`
  expands to one edge per ordinal); a **single- or no-decision target takes
  the bare id** — its `:d1` and its bare id denote the same edge, so `:d1` on
  a single-decision target is *rejected* as redundant. Symmetrically, an entry
  whose own body carries 2+ decisions must prefix each ref with its authoring
  decision as `dN -> <ref>`; a single-decision writer omits the prefix. `links
  check` validates both ends' ordinals everywhere (new error
  `dangling-source-decision`, in entry YAML and link-sidecar blocks alike) and
  adds post-cutoff advisories (`unaddressed-target-decision` for a bare
  multi-decision target, `redundant-decision-ref` for `:d1` on a
  single-decision target, `unattributed-source-decision` for a missing arrow)
  that warn - never error, since append-only makes a published ref
  unrepairable - on entries stamped after 2026-07-24 09:00. Read side:
  `MemoryChunk.decision_edges` and the sidecar `decision_edges` channel carry
  `(kind, source_ordinal, target, target_ordinal)`; the Trail draws each edge
  from the authoring decision's
  row to the target decision's row and no longer double-draws the entry-level
  twin of an arrow-narrowed edge. This lands step 3 (source decisions) of the
  decision-refs draft, in per-item arrow form rather than the drafted
  block-level `source_decision:` field. Published pre-mandate entries are
  untouched and stay quiet.

- [2026-07-24] **BREAKING (vocabulary): `supersedes` is renamed `replaces` across Seed and
  Trace** (JNL's direction, 2026-07-24: one term everywhere - the Trace UI
  already said "replaces" while the data layer said "supersedes"). The entry
  and link-sidecar field is `replaces:`; computed inverses are `replaced_by`;
  the search filter is `exclude_replaced`; ranking constants and the
  `superseding_head` boost family rename accordingly; `/api/v1` renames the
  `supersedes` edge-type enum value and the `superseded_by`-derived payload
  fields to their `replace*` spellings (contract regenerated, same shape
  otherwise - the `authority_class` rename precedent). The docs lifecycle
  lane `7_Superseded/` is now `7_Replaced/` with `replaced_by:`/`replaced_on:`
  frontmatter. **Compatibility:** every reader and validator accepts the
  legacy spellings forever - `supersedes:` field keys, the `--supersedes`
  CLI flag, `supersedes`/`exclude_superseded` MCP arguments, the
  `supersedes` edge-type request value, and `7_Superseded/` +
  `superseded_by:` docs - so corpora and repos written by <=2.19 keep
  working unchanged; writers and displays emit only the new spellings.

- [2026-07-22] **`situate` reports which checkout you are actually in.** A new `## Location`
  section, printed first, classifies the caller's cwd through the existing
  `worktree_guard` and names the checkout as the primary/root tree or an
  agent-owned worktree. It exists because worktree identity is routinely
  *declared* rather than measured: a harness banner, a task packet, or a bare
  `.../worktrees/<session>` directory can each assert an isolated worktree that
  was never created, and git then resolves every command up to the primary
  checkout while the agent writes into shared state believing it is isolated.
  No new detection logic was added - `worktree guard` already classified this
  correctly; it was simply never run at orientation, only before writes.
  `orientation.md` and the `/situate` shims now tell agents to believe the
  measured Location over any declaration, and to create an isolated worktree
  before writing when the checkout is shared; `agent_collaboration.md` extends
  the same rule to *after* a create (a `git worktree add` can half-fail, and
  trusting the create is the same error as trusting the banner, one step later).
  `session-start-context.py` carries the same note at **SessionStart**, which is
  the only surface that fires whether or not an agent orients: it names the
  primary checkout and points at the worktree workflow, and stays silent inside
  a real linked worktree (`--git-dir` and `--git-common-dir` differ there) so a
  correctly-isolated session is never nagged. Stdlib-only and fail-open.

- [2026-07-21] **Memory Trace incremental startup.** A changed project (new commit, merge,
  or dirty session file) no longer triggers a full projection rebuild that
  spawned one git subprocess per historical item (~44s / 990 processes on a
  570-entry corpus). Fork points, commit parents and first-parent changed
  paths now persist per commit sha in the disposable SQLite projection
  (schema v2) and are harvested via single bulk `git log` passes;
  `ensure_current` reconciles forward moves incrementally (reparsing only
  changed session documents) and falls back to a full rebuild on rewritten
  history, a moved trunk that is not a fast-forward, or any failed git read.
  The file-entry index (File graph mode) is now built lazily on first use
  instead of at startup. Full rebuild: ~1.5s / 7 subprocesses on the same
  corpus; a new `python -m memory_trace.bench` harness reports per-stage
  timings and subprocess counts. The React client fetches Graph data only
  when Graph view is opened and the full-corpus Trail payload exactly once.
  `extract_memory_chunks` gained an additive `paths=` filter so incremental
  consumers can reparse specific session documents.

- [2026-07-19] **Gated MCP write surface (Constitution 1.3).** MCP could not write session
  files, so agents authored entries by hand with `memory_entry_id` +
  `memory_session_target` — an id and a target path — which enforced none of the
  guards `session append` does; violations only surfaced later in `links check`.
  Those two tools are **removed** and replaced by **`memory_session_append`**,
  which wraps `session_append_entry` so every MCP write passes the same nine
  guards (chronology, ref existence, forward-only edges, topic vocabulary, id
  collision, DRAFT format) and returns refusals as `{ok: false, issues}`. The
  server stamps the timestamp from its own clock (drift warning on far-off
  explicit values, carried over from the retired id tool). A new **`dry_run`**
  on both the tool and `session append` runs every guard and returns the id,
  timestamp, target path and the rendered entry block — the final output,
  inspectable before committing to the write — the pre-flight the removed
  pair used to provide. Constitution Invariant #2 gains **write-surface parity**:
  every write passes identical validation on any surface.

### Added

- [2026-07-24] **First-message operating-mode gate.** `orientation.md` (+ seed twin) gains a
  routine that runs once the user's intent is known — the layer neither
  SessionStart nor `situate` can supply, since both fire before the user has said
  anything. It sets the session variables in order (`checkout_posture` →
  `integration_mode`/`merge_trigger` → `write_intent` → `risk_tier`/
  `orchestration_level` → `worktree_decision` → `skills_to_load`), grouped by
  **enforcement class** so it stays honest about which of them flip a real
  switch: tooling-enforced (the worktree guard and the `merge_trigger` gate
  actually refuse), config-toggled (persona registry, trigger registry), and
  advisory (judgments no code can compute). Read-only work exits after step 3,
  which is what keeps a mandatory step from decaying into noise. Nothing is
  persisted — no new state file, per the derived-projection invariant.
  `agent-rules.md` routes to it in one line rather than carrying the schema: the
  startup contract sits at its 260-line cap, and `skill_architecture.md` puts
  procedural detail in skills. `session_logging.md` now records that on-branch
  logging is what `merge_trigger: manual` buys.

- [2026-07-24] **`merge_trigger` switch — hold branch landings for an explicit user
  go-ahead.** A new `.memory-seed/project.yaml` scalar (`read_merge_trigger`,
  fail-open to `automatic` so legacy/unconfigured projects are unchanged) decides
  whether the agent auto-advances a task branch to its integration handoff at a
  stable stopping point, or holds. Under `manual`, `session merge-branch`,
  `session open-pr` and the lower-level `session fuse --apply` all refuse a real
  advance without `--user-approved` (an agent is contractually barred from
  supplying it on its own initiative; a preview/dry run is never gated), and MCP
  `memory_session_integrate` declines outright, mirroring its `pr` decline — the
  unattended path cannot represent user authorization. Gating the fuse primitive
  closes the bypass where a raw `git merge --no-ff --no-commit` plus a fuse would
  land a branch around the handoff commands entirely.
  `automatic` stays bounded to local, reversible advancement (never pushes, never
  merges a PR). `situate`/`esr` surface the trigger. Handoff-only: the actual PR
  merge in `pr` mode is always the human reviewer's.

- [2026-07-19] **`memory_session_integrate`** MCP tool: merges a task branch and fuses its
  branch-local session memory into the trunk in chronological order, applying
  autonomously (no in-progress-merge precondition). Aborts and restores a clean
  tree on a non-session conflict rather than stranding a half-merged repo, and
  declines when the project's `integration_mode` is `pr` (which pushes).
- [2026-07-19] Session-file ordering is now stable across the fuse and reorder paths: both
  break same-minute timestamp ties by input order (existing entries keep their
  positions, incoming ones append after), so a fuse can no longer silently
  re-position trunk history it never touched. Previously the two paths disagreed
  and each could undo the other.
- [2026-07-18] New **`entry-future-timestamp` warning** in `links check` / `esr`: an entry
  whose `## YYYY-MM-DD HH:MM` heading is more than 10 minutes ahead of the wall
  clock at check time is flagged (heading timestamps are authored inputs and
  nothing validated temporal sanity, so an agent once stamped entries hours into
  the future). Advisory only, never blocking — append-only forbids restamping
  published entries, so historical corpora with known drifted stamps stay valid.
- [2026-07-19] New **`malformed-entry-yaml` error** in `links check` / `esr`, a sibling to the
  existing `malformed-entry-format`: an entry whose YAML metadata fence is opened
  but never closed. The unterminated fence swallows the following text and leaves
  the entry unparseable to the fuse, so this is an error, not a warning.
- [2026-07-19] Two new canonical topics, **`security`** and **`performance`**, bringing
  `.memory-seed/topics.yaml` from 21 to **23** slugs. Existing entries are
  unaffected; the vocabulary gate accepts the new slugs immediately.
- [2026-07-19] **`.gitattributes` now marks `.memory-seed/sessions/**` `-merge`.** Session
  entries share line-identical `topics:`/`related_entries:` scaffolding, so git's
  line-based three-way merge anchored on those shared lines and could splice one
  entry's body into another while stranding a YAML fence — a silent corruption
  rather than a conflict. Concurrent session-file edits now conflict wholesale by
  design, leaving `session merge-branch` / `memory_session_integrate` (which
  rebuild the file from parsed entry records) as the only correct integration
  path. The tools themselves are unaffected: they already reset branch-touched
  session files to base content before fusing.
- [2026-07-17] Memory Trace `/next` React workspace: the Inspector now renders a full entry
  reader — markdown-rendered body (frontmatter code block, headings, bullets,
  inline code/bold), search-match subsection highlighting at parity with the
  legacy reader, an evidence strip (commit + `path:line`), and navigable
  linked-memories and related-activity cards.
- [2026-07-17] Memory Trace Inspector surfaces the BG1 provenance/authority taxonomy: an
  entry's `Authority` and `Provenance` classes display as distinct rows (never a
  merged trust score), with `Provider`/revision and a `stale` flag when present,
  and a muted advisory band for provider/generated authority (BG1 step 4).
- [2026-07-18] Memory Trace `/next` adds a **Trail** presentation mode: a git-graph decision
  timeline over `/api/v1/trail` — day-grouped newest-first rows in branch lanes,
  a rendered rail (main spine, rounded-elbow fork/merge connectors, clickable
  trunk merge dots), row-click selection into the Inspector, and client-side
  windowing. The layout model is a pure, invariant-checked port of the vanilla
  Trail. Full vanilla parity landed in the same cycle: the two-rule related
  model (row brackets + evolves chain brackets + commit siblings), two-stage
  muted selection, continuity lanes, decision-diagram badges (`has_diagram` is
  now declared on the v1 `GraphNode` — additive), a humanist light/dark theme
  with resizable panes and a stable deterministic graph, and a left-pane
  selection-context panel (typed lifecycle links, commit siblings, similar
  entries). Lifecycle-edge arrows (`supersedes`/`evolves`/`related`) route through
  the relationship zone with pair precedence and soft variants — `supersedes`
  always shown, `evolves`/`related` on selection. A relationship legend and
  search-as-a-function (a client-side substring filter over the visible window
  that dims non-matching rows and shows a live match count) complete the
  readable Trail.

### Changed

- [2026-07-18] Worktree switching reuses shared history: merge fork points (the dominant
  rebuild cost — one `git merge-base` subprocess per trailer merge) memoize
  process-wide by commit sha, since every checkout shares the object database;
  switching worktrees now only computes the target's own divergence, and
  unchanged worktrees warm-start from their persisted projection instead of
  rebuilding.
- [2026-07-18] Memory Trace `/api/v1` is now worktree-scoped: every v1 endpoint accepts an
  additive `worktree` query parameter and a typed `/api/v1/worktrees` endpoint
  enumerates the repository's checkouts; the `/next` React workspace gains a
  worktree picker that switches the whole app between corpora.
- [2026-07-19] The MCP write path owns the clock: omit `timestamp` and the server stamps from
  its machine clock, returning the value for verbatim write-back. Explicitly
  supplied timestamps remain allowed for sanctioned backfill but earn a
  `clock_drift_warning` when far from the server clock — agents must never
  estimate entry times by hand. Introduced on `memory_entry_id` and carried over
  to `memory_session_append` when that tool replaced it later in this same
  unreleased tranche; echo a `dry_run`'s returned `timestamp` into the real call
  so the previewed and written entry ids agree across a minute boundary.
- [2026-07-17] CI now gates on `docs index --check`, so a stale generated docs index fails
  verification instead of drifting silently.

### Fixed

- [2026-07-26] **`session append` no longer records a foreign branch.** `branch:` captures the HEAD of the working
  tree that owns the memory dir, so when `resolve_runtime`'s walk-up escaped the caller's own checkout —
  an **untracked `.memory-seed` seen from a git worktree**, or a submodule whose superproject owns the
  memory dir — the entry was written into the enclosing tree's `.memory-seed` *and* stamped with that
  tree's branch. Neither HEAD is the right answer there (the session is on one branch; the entry file
  commits on another), so the field is now **omitted**, extending the existing detached-HEAD /
  not-a-repository omission rule rather than adding new machinery. Both write surfaces get it (Invariant
  #2). Repositories that commit `.memory-seed` — which is what makes worktree isolation work in the first
  place — are unaffected: their worktrees resolve to their own memory dir and their own HEAD, and
  continue to record it. Two agents sharing *one* checkout remain undecidable from git and still need
  explicit `--branch`/`--no-branch`; see `docs/2_Todo/branch-field-provenance.md`.
- [2026-07-18] Memory Trace graph/projection overview (no focus entry, no date filter): the
  node slice is now chosen by connectivity — deterministic greedy expansion from
  high-degree seeds with newest-first tie-breaks — instead of truncating in
  corpus order. The old positional cut kept the oldest entries, which largely
  predate lifecycle links and authored topics, so `GET /api/v1/graph/projection`
  with a limit below the corpus size returned an edgeless slice and the React
  "All dates" overview rendered a disconnected map.

### Removed

- [2026-07-20] **`memory-seed[lense]` extra and the `memory-seed lense` CLI command.** Both were a deprecated
  compatibility alias kept for one release window while the product renamed from Memory Lense to
  Memory Trace (shipped 2.13.0, deprecated since 2.16.0). The window has elapsed; install
  `memory-seed[trace]` and run `memory-trace` instead.

## 2.19.0 - 2026-07-17

- **`memory-seed docs index` + `docs check` wired into `esr` and CI** — document-lifecycle Phases 2–3
  complete. `docs index` generates each lane's `README.md` table (document · priority · blocked-by ·
  next-action, Todo sorted by priority) and a front-door counts + top-open-items roll-up. Generation is
  **marker-scoped**: only the region between `<!-- docs-index:begin/end -->` is ever rewritten, so
  hand-written lane prose survives regeneration byte-for-byte; a missing README is created, a marker-less
  one gets the block appended. Deterministic and idempotent, so `docs index --check` is a real staleness
  gate (exit 1, writes nothing) — the "stale generated index" rule the check spec asked for. `docs check`
  now also runs as an `esr` section ("Docs lifecycle" — errors surface there while links check alone still
  owns the esr exit code) and as a `verify.yml` CI step, where errors do fail the build.
- **OpenSSF credibility, in-repo slice.** `SECURITY.md` lands the vulnerability-disclosure policy
  (GitHub private reporting), a short threat model, and a "Verifying a release" section covering the
  PEP 740/Sigstore attestations Trusted Publishing already emits (SLSA Build L3-shaped provenance,
  claimed conservatively and confirmed per release). `CONTRIBUTING.md` documents how changes land —
  including, honestly, that review on a solo-maintained project is self-review plus the automated gate.
  New CodeQL (python + javascript-typescript, push/PR/weekly) and Scorecard (publishing to the API,
  SARIF to code scanning) workflows. `verify.yml` and `publish.yml` are hardened: **every third-party
  action pinned to a full commit SHA resolved from its upstream tag** (same versions, immutable refs) and
  least-privilege tokens throughout (`contents: read` default; per-job `id-token: write` for OIDC
  publish, `security-events: write` for SARIF). Expected Scorecard results — including which checks are
  deliberately capped by the project's solo shape — are recorded in
  `docs/4_Reference/openssf-scorecard-notes.md`. User-side settings (private-reporting toggle, branch
  protection/G2, bestpractices.dev registration) remain open and documented.
- **One entry-boundary grammar everywhere.** `core.py` defined `_ENTRY_HEADING_RE` twice: a strict
  timestamped pattern (used by append/format checks) that a later broad `^##` redefinition silently
  shadowed for reorder and the branch-fuse flows. The result: `session append` accepted an entry body
  containing an `## Summary` heading, but `session merge-branch` split that same body into a phantom
  ID-less entry and blocked the merge. There is now exactly one definition — an entry heading is a
  timestamped `## YYYY-MM-DD HH:MM - title` line and nothing else; a plain `##` heading inside a body is
  body content in every flow. `session reorder` consequently no longer refuses files with stray `##`
  headings (that refusal guarded the ambiguity the unification removes) — the heading now travels with
  its entry, and regression tests pin the fuse, reorder, and travels-with-entry behaviours.
- **⚠️ Breaking (`/api/v1`): `RendererGraphNode.authority_class` is now a closed enum, and its value
  `canonical_memory` was renamed to `authored`.** The field shipped as a free-form string validated only
  as "non-empty", which let it emit `canonical_memory` — a value from no declared vocabulary, exactly the
  drift the BG1 provenance/authority taxonomy exists to prevent. It is now a typed `AuthorityClass` enum
  (`authored`, `computed_canonical`, `git_derived`, `provider_extracted`, `provider_resolved`,
  `provider_inferred`, `generated`), enforced by an `AUTHORITY_CLASSES` frozenset the same way
  `provenance_class` already was, and published as a real enum in the OpenAPI/TypeScript contract instead
  of `"type": "string"`. **Blast radius was verified nil before the break:** no code branches on the
  value and the React client does not read the field; the OpenAPI fixture, TypeScript types, bounded
  graph fixture, and bundled renderer-benchmark were all regenerated. This unblocks BG1 steps 3–6.
- **Session entries are appended at the milestone, not at the merge.** `session_logging.md` gained a
  "When To Append" rule (+ seed twin, so every agent inherits it): the multi-decision shape is for
  decisions settled in *one deliberation*; if substantive work happened between two decisions —
  implementing, reviewing, testing, discovering — they are separate milestones and get separate entries,
  even on one branch in one subsystem. The Decision Harvest previously keyed only on *subsystem*
  ("choices belonging to one coherent task" → one entry), which actively endorsed batching a whole
  branch's milestones into one summary entry. It now keys on elapsed work too. `links check` reports a
  new **`entry-decision-density` warning** at 3+ decisions per entry (corpus norm is ~1.0–1.5), routed
  through a separate advisory path (`entry_body_advisories`) so it can **never** block `session append`
  or fail a check — a genuine three-decision deliberation is legitimate, and only a human can tell the
  difference.
- **`memory-seed docs check`** — read-only enforcement for the `docs/` lifecycle lanes, the check half of
  the document-lifecycle Phase 2 tooling. Validates that every relative link resolves, that lifecycle
  pointers (`superseded_by`, `extracted_into`) aim at real files, that a spec's `spec_binding` agrees with
  the folder it sits in, and that nested folders are on the side-folder allowlist. Severity is deliberate:
  **errors** are broken facts (a dead link, a dangling pointer, a draft claiming to be live), while
  **warnings** are merely incomplete (missing `priority`/`next_action`/`superseded_by`) — backfilling that
  YAML is separate open work, and failing on it would keep the check red for a known-unfinished task. On
  its first run it caught three real defects: two specs with prose in `spec_binding` and one with a
  filename there; all three are fixed, and the descriptive text moved to a `role:` field. The 2026-07-17
  lane migration had to hand-roll a throwaway link checker because this did not exist — that gap is what
  this closes. (`docs index` remains the other half of Phase 2.)
- **Legacy `docs/2_Todo/completed/` retired** — its 43 documents and the nested `agent-templates/` moved to
  `docs/5_Completed/`, so the folder-is-the-state rule now holds with no legacy archive beside the lanes.
  Every inbound reference was repaired by resolving each link to its real target, taking `docs/` from 20
  broken relative links to **0** (the pre-existing breaks were depth errors left by the previous move into
  `completed/`). Session logs keep their original paths — they are append-only history — and the move is
  recorded as a `continuity:` migration event instead.
- **`memory-seed worktree classify [--apply]`** — Track E Phase 1. Without `--apply` it is the read-only
  dry-run classifier. Classifies every registered worktree as `root`, `active`, `dirty`,
  `unmerged`, `locked`, `foreign`, `unknown`, or `removable`, and shows the evidence behind every verdict.
  **Read-only: it removes nothing**, and `--apply` does not exist yet — removal is destructive and lands as
  its own increment. A worktree is `removable` only when every safety question answers yes at once; being
  *merged* never implies a clean working tree, and anything unanswerable (unreadable `git status`, detached
  HEAD, indeterminate merge status) fails closed to `unknown`, which refuses removal. Worktrees in another
  agent's namespace report `foreign` — clean and merged, but not yours to remove. Branch deletion stays a
  separate, approval-gated concern. Distinct from the existing `worktree guard`/`status`, which inspect only
  the current worktree for the namespace guard. **`--apply` (destructive, shipped under live user
  consent) removes what a *fresh* classification calls removable** — reclassifying at apply time so a
  stale verdict is never trusted, via `git worktree remove` with bounded retry on a lock and no
  raw-filesystem fallback; branches are never touched, and a refused removal leaves the worktree intact.
  Exercised end-to-end against a throwaway worktree; the retry-on-lock path is unit-tested by injection.
- **`memory-seed quality report [--json]`** — memory-quality metrics v0: a deterministic, local,
  read-only measurement over the Markdown corpus, and the measurable subset of Constitution §8 (still a
  `[candidate]` clause this report exists to produce evidence for). Every metric declares its population,
  numerator, denominator, and exclusions. A metric with no eligible population reports `not_applicable`
  and one whose input does not exist reports `unavailable` — **never 100% coverage**, which would read as
  perfect when it means "nothing to measure". v0 measures unlinked-entry rate (by age band) and DRAFT
  reason coverage; citation and provenance coverage report `unavailable` pending the BG1 taxonomy, and
  ranking-A/B regression reports `not_applicable` until a completed `ranking-ab` run is supplied (it never
  reimplements that scoring). No composite score, no targets, no telemetry; nothing feeds ranking,
  filtering, or automation. The first real-corpus baseline is recorded in
  `docs/4_Reference/memory-quality-v0-baseline.md`.
- **`memory-seed link add <target> [--from <entry_id>]`** writes an explicit `related_entries` edge from
  the current/newest entry to an older one — the append-only-safe half of Related-entries P2. It creates
  the `related_entries:` key when absent, appends without reordering existing links, is idempotent
  (re-adding reports a no-op and rewrites nothing), touches only the entry's YAML and never its prose, and
  re-runs `links check` after the write. Forward-only by construction: the target must be older than the
  source, so an edge can never point forward in time or form a cycle. Unknown ids, self-links, and
  forward edges are refused before any write. **Editing a non-newest entry is refused** — that is
  historical curation, which Constitution Invariant #2 (the past is append-only) forbids; the plan's
  `link backfill` counterpart is deliberately not implemented and needs an explicit constitutional ruling
  first.
- **Memory Trace tolerates concurrent cache rebuilds.** Two local server processes projecting the same
  workspace no longer produce a Windows file-lock 500. Each rebuild takes a short-lived OS-level writer
  lease per primary cache path; a waiting process rechecks the winner's snapshot once the lease frees, and
  if the lease stays unavailable past a bounded wait it builds an isolated temporary projection rather than
  contending for the shared cache. The observed failure was an `os.replace` denial during concurrent
  rebuild, not a Markdown or UI data error — Markdown stays authoritative, and both the shared SQLite cache
  and any emergency temporary projection remain disposable derived state (Invariant #6).
- **`memory-trace --open-both`** opens the vanilla `/` and React `/next` renderer views as two browser tabs
  against a single server, so the two can be compared side by side during B0b parity work. Mutually
  exclusive with `--no-open`; available on `memory-seed lense` too. `scripts/launch-memory-trace.ps1` wraps
  the same flow for Windows.
- **Supersession successors now surface directly in retrieval.** `memory_search` results carry the
  lineage terminal `superseding_head`, and the default-on successor boost is bounded to affected
  supersession lineages. The additive field shipped before ranking changed; fixtures and the full-corpus
  `ranking-ab` gate then proved every replacement beats its retired predecessors while an unaffected
  control remains unchanged.
- Added deterministic `memory-seed topics suggest --from <file>` topic recommendations. Suggestions are
  read-only, vocabulary-aware, stably ranked, and do not mutate the project-owned topic index.
- **Memory Trace deterministic Evidence Pack Phase 1.** `memory_trace.evidence` now builds stable timeline
  evidence packs from bounded date, entry, topic, user, agent, and graph-neighbourhood selections, with
  normalized provenance, selection/pack fingerprints, and a committed snapshot fixture. It invokes no
  model, writes no memory, and remains a non-authoritative derived artifact.
- **Memory Trace Trail continuity axis.** Authored `continuity:` rename, migration, and removal events now
  render as derived lineage lanes in the Trail and versioned API without inventing graph edges or changing
  Markdown authority.
- `memory-seed link audit --date <date> --apply` now creates idempotent, chronologically ordered
  `classify_pending: true` sidecar stubs with candidate evidence left in comments. It never writes a live
  edge or auto-classifies a relationship; `links check` warns on unresolved stubs and ESR reports their
  count for explicit human review.
- Added `memory-seed ranking-ab --signal <name> [--query <q> ...] [--json]`, a deterministic
  full-corpus off/on gate for ranking changes. Supersession checks now derive live lineage queries,
  require each replacement to out-rank the decision it retires, require an actual unaffected-query
  control to remain identical, and fail closed on empty or incomplete evidence.
- **SessionStart orientation now begins at `AGENTS.md` and supplies a five-entry context window.** Claude,
  Codex, Gemini, and Cursor are directed to locate, read, and follow the nearest applicable `AGENTS.md`,
  then receive the five newest applicable session entries across recent files instead of every heading plus
  only the latest body. Empty/new projects still receive the startup directive; long entries are capped and
  name their source path for a full read. Copilot's static `sessionStart` prompt carries the same instructions.
- **Memory Trace derived-projection Phase 1 (warm start):** the SQLite cache is now a formalized read-model
  with a **git-watermark warm start**. `ensure_current` proves freshness in O(changes) — HEAD unmoved and
  the git-dirty session files unchanged → serve as-is, with **no whole-corpus scan** and no rebuild
  (measured: ~6.2 s full rebuild → ~78 ms warm start on a real repo). Any real change (commit, uncommitted
  edit, or a `PROJECTION_SCHEMA_VERSION` bump) rebuilds; every git ambiguity fails toward a rebuild; without
  git it degrades to the prior mtime scan. The rebuild stays byte-identical and atomically swapped. Nothing
  in the cache is authoritative — it is fully rebuildable from Markdown (Constitution Invariant #6). The
  freshness check is memoized over a short window so a burst of reads (one UI interaction) runs it once, not
  per read — entry switching stays snappy despite git's per-call subprocess cost.
- **Memory Trace read-path perf (Phase 1 fast-follows).** Two further refinements on the warm-start
  foundation: the deserialized chunk list is memoized in `TraceCache` (keyed to the rebuild), taking
  `chunk()` from ~132 ms to ~12.5 ms (JSON deserialization was the dominant per-read cost); and the diagram
  + link sidecars are now first-class in the freshness signal (git-captured) with a memoized derived
  bundle (augmented entries + related graph + diagram map), taking `chunk()` to ~3.9 ms — ~34× vs. the
  pre-Phase-1 read. Nothing here is authoritative; all of it rebuilds from Markdown (Invariant #6).
- **Memory Trace Trail: commit-accurate merge rendering.** The `Memory-Entry:` trailer parser now scans
  every trailer line from the commit body (not git's blank-line-terminated `%(trailers)`), so daisy-chained
  merges that were mis-drawn as parallel lanes now render as the real merge topology. Retroactively repairs
  live history without a re-commit.
- **Memory Trace Trail: manual Refresh button** in the topbar — re-reads memory on demand, keeps active
  filters, and auto-extends the date window to the latest entry.
- **Memory Trace Trail: the "To" date defaults to today** (not the newest entry's date), via a shared
  `defaultDateTo` helper across seed/chip/clear/refresh so a just-written entry is always in view.
- **Memory Trace Trail: selecting an entry reveals its links.** The visible window grows to include the
  selected entry's linked neighbours, so `supersedes`/`evolves`/`related` edges to off-window targets draw
  instead of silently dangling.
- `memory_link_suggest` (and the underlying `suggest_related_entries`) gained an optional
  `consulted: [ids]` axis: entry ids you retrieved while grounding the work are flagged `consulted` and
  sorted ahead of shared-file candidates — the *memory* axis of link candidacy, the natural source for the
  `supersedes`/`evolves` decision-lineage edges that file overlap misses. Additive and read-only; an
  empty/omitted `consulted` leaves ordering byte-for-byte identical. The `history_retrieval` and
  `session_logging` skills now connect the pre-work retrieval loop to write-time link authoring.
- Renamed the internal Memory Trace backend module `memory_trace/lense.py` → `memory_trace/service.py`
  and its `LenseCache` / `LenseService` classes → `TraceCache` / `TraceService`, dropping the misleading
  legacy "Lense" name from the internals. Purely internal: the public `memory-seed lense` compatibility
  command and the `memory-seed[lense]` extra are unchanged. Regenerated the `/api/v1` OpenAPI + TypeScript
  contract fixtures.
- Session entries now have a deterministic **DRAFT-format lint**
  (`core.entry_body_format_issues` / `check_entry_format`): `session append` refuses to write a
  malformed decision record (bare `D:`/`R:` labels that are not `- ` list items, DRAFT prose with no
  `### Decision`/`### Summary` heading, several decisions crammed under a singular `### Decision`, or a
  `D:` with no `R:`), and `links check` reports the same corpus-wide as `malformed-entry-format`
  (surfaced by `esr`, merge-blocking once CI runs it). The check is structural only - it never judges
  whether a turn should be one decision or several. Ships in core, so every project inherits it; six
  historical malformed entries were reformatted. (Follow-ons: blocking git commit hook, `session
  append` decision-scaffolding flags, and a read-only `memory_entry_format_preview` MCP tool.)
- **Configurable integration mode completed.** A project-local `integration_mode` (`local-merge` | `pr`)
  setting in `project.yaml` is read fail-open with a `local-merge` default and surfaced by ESR. The live
  and seeded agent contracts obey it; mode-aware `session integrate` and `session open-pr` implement local
  merge or normal push/PR preparation; bootstrap can suggest a mode but requires human confirmation.
  See `docs/5_Completed/configurable-integration-mode-plan.md`.
- **Freshness-aware `memory_search` ranking (supersession dampener, on by default).** A replaced
  decision no longer out-ranks its live replacement: entries with a non-empty `superseded_by` (drawn
  from the sidecar-augmented graph, so sidecar-authored supersessions count too) are multiplicatively
  down-ranked (`SUPERSEDED_RANK_DAMPING = 0.25`) in `final_score`, and each result now carries
  `evolved_head` so an evolves lineage's current fuller form is reachable without burying the
  still-valid original. Down-rank only - never a hard exclude (`exclude_superseded` stays the separate
  opt-in filter) and never hidden: a retired entry stays fully retrievable, just lower. Shipped
  default-off with fixtures, then turned **on by default** in `search_memory` + the MCP `memory_search`
  tool after a real-corpus A/B on both live supersession lineages proved the replacement surfaces above
  every retired predecessor while queries with no superseded hit in-window stay byte-identical;
  `supersession_damping=false` opts out. From
  `docs/5_Completed/freshness-aware-memory-ranking-proposal.md`.
- **Retrieve the *why* before changing non-obvious code**, now a portable control-plane discipline:
  `agent-rules.md` Working Principles, `skills/history_retrieval.md`, and the developer persona (all
  with seed twins, so every project inherits it) direct every agent to `memory_search` the prior
  reasoning - rejected alternatives, constraints, deferred items, landmines - before a design/change
  decision on non-obvious behavior, keeping files the authority for what is true *now* and memory the
  authority for *why*. From `docs/2_Todo/proactive-history-retrieval-discipline-proposal.md`.

- Memory Trace UI polish: switching worktrees now plays a subway-map loading animation (the Trail is
  a train line, so a switch is a short journey - stations light up at the real load milestones as the
  train slides between them) instead of freezing the previous view; and the decision-diagram badge
  now opens a large centred, zoomable/pannable viewer (wheel-zoom toward the cursor, drag-pan,
  minus/Fit/plus controls, close on ×/backdrop/Escape) rather than a cramped 420px popover, with
  reader diagrams clickable into the same viewer. While there, the built-in Arc 2d flowchart renderer
  learned to honour mermaid `<br/>` line breaks and size nodes to fit, so labels no longer overflow.

- The commit-accurate Trail merge geometry is now served on the versioned `/api/v1/*` surface as
  well as the legacy one: `/api/v1/graph` and `/api/v1/trail` carry `merges` (trailer-stamped merge
  events) and `branches` (per-branch merge/fork/estimated), and `/api/v1/chunks/{id}` carries
  `merged_by`. New `MergeEvent` / `BranchInfo` / `ForkPoint` response models formalize the shapes;
  `merged_by` reuses `CommitInfo`. The promotion is purely additive (existing v1 clients ignore the
  new keys), lands after the vanilla implementation survived a full release cycle, and inherits
  sidecar-sourced lifecycle edges automatically (they were already ordinary graph edges). The
  committed `openapi.v1.json` and generated `types.ts` fixtures are regenerated to match.
- Memory Trace now renders the authored controlled-vocabulary `topics:` field as first-class UI
  (topic-neighbourhoods plan, Phase 4 Trace half). Its single `_topics()` chokepoint prefers an
  entry's indexed topics and falls back to the hashtag/heading-derived display axes only for
  entries that predate the field - never mixing the two - so the topics facet, the reader's new
  clickable topic chips, the graph's `topic` chronological chains, and the topic filter all speak
  the controlled vocabulary once an entry adopts it. The topic filter is now vocabulary-aware:
  it expands the requested slug through `topics.yaml` (canonical + aliases, fail-open) so filtering
  by a canonical topic matches alias-stored entries and vice versa. Both the legacy `/api/*` and the
  versioned `/api/v1/*` surfaces inherit this through the shared service.
- MCP now exposes read-only topic-management tools for the controlled vocabulary:
  `memory_topics_list`, `memory_topic_inspect`, and `memory_topics_check`. Agents can list the
  project topic index, resolve canonical slugs/aliases with entry usage, and mirror
  `memory-seed topics check` validation without gaining a write surface for project-curated
  `.memory-seed/topics.yaml`.
- Added an agent worktree namespace guard: `memory-seed worktree guard --agent <agent>
  --write-intent` and the read-only `memory_worktree_guard` MCP tool classify the current checkout
  as an owned worktree, foreign worktree, root checkout, unmanaged worktree, or non-worktree. Codex,
  Claude, Gemini, and Cursor get default `.agent/worktrees/` namespaces, root writes require an
  explicit override, and `agent_collaboration.md` now requires the guard before branch/worktree
  edits.
- `session fuse` now blocks changed branch session/diagram files that cannot decode as UTF-8,
  naming the offending path instead of silently skipping it. Base-side decode failures remain
  non-blocking for already-present and sidecar-parent lookup degradation.
- Memory Trace surfaces authored Class-2 decision-diagram sidecars in the Trail and Graph views, not
  just the reader (session-decision-diagrams plan; user-chosen "badge + popover" design). A small
  diamond badge marks Trail rows and Graph nodes whose entry carries a sidecar, driven by a new cheap
  `has_diagram` boolean on graph nodes; clicking the badge floats the diagram in a popover rendered
  by the same built-in Arc 2d renderer as the reader, lazy-fetching the source from the chunk
  endpoint so the graph payload stays lean. The popover closes on the × button, an outside click,
  Escape, or re-clicking the badge. `has_diagram` ships on the legacy `/api/*` surface only for now
  (the v1 `GraphNode` model strips it) until the badge UI is polished.
- MCP graph sidecar-edge parity: `memory_search`, `memory_get_chunk`, and `memory_link_show`
  now read the same effective lifecycle-edge set as Trail/Trace by applying
  union(entry YAML, link sidecar) before graph construction or payload formatting.
  Sidecar-only `supersedes`/`evolves` edges now surface through MCP outbound and inverse
  freshness fields, while YAML-only behavior remains unchanged when no sidecars exist.
- `memory-seed link show` now reflects the same sidecar-augmented effective graph: it unions
  entry-YAML edges with link-sidecar edges before building the graph, so late-authored
  `supersedes`/`evolves`/`related_entries` (and their computed inverses and importance) appear in the
  CLI readout instead of only in retrieval/MCP/Trace. Regression-tested; caller-augments matches the
  other consumers.
- Hardened Memory-Entry trailer hook management: `memory-seed hooks status [--json]`
  reports missing/stale/broken/current/foreign `prepare-commit-msg` state, `memory-seed
  hooks repair` refreshes only missing or Memory Seed-managed hooks, `doctor` warns
  when the core trailer hook is not current, and Windows installs now use an
  absolute-Python shim to avoid Git-for-Windows shell startup failures. Foreign
  hooks are reported and never overwritten.

## 2.18.0 - 2026-07-13

- Memory Trace now ships as part of the main `memory-seed` package behind the optional
  `trace` extra (`pip install "memory-seed[trace]"`) instead of a separate PyPI
  distribution. The root package installs the `memory-trace` command, includes the
  `memory_trace` package/static assets, keeps `memory-seed[lense]` as a temporary alias,
  and removes the obsolete standalone `memory-trace` publish workflow/project metadata.
  Plain `pip install memory-seed` remains web-framework-free.
- `session merge-branch` now stamps one `Memory-Entry: <entry_id>` trailer per fused entry on the
  merge commit it creates (below git's prepared merge message), making the forward commit<->entry
  link authoritative at integration time - `link commits` and `find_trailer_commits` resolve fused
  entries to their integration point with no manual step. Only well-formed ids are stamped (a
  malformed id never poisons the trailer channel), entries already on the base commit are never
  claimed, and there is no cap. The CLI reports the stamped count; a stamping failure never aborts
  an otherwise-clean merge. `agent_collaboration.md` and `session_logging.md` (live + seed) note
  the automatic trailer; ordinary commits are covered by the `prepare-commit-msg` hook below.
- Implemented indexed topics P1 (topic-neighbourhoods plan, Phases 0-3): meaningful session
  entries carry 1-3 `topics:` slugs resolved against the new deploy-once project-local
  `.memory-seed/topics.yaml` vocabulary (canonical slugs + aliases, slug rule
  `^[a-z0-9][a-z0-9_-]{0,63}$`, `update` never overwrites project curation; seeded projects get a
  minimal generic starter). `MemoryChunk.topics` parses the stored field; retrieval dicts expose
  it; `memory_search` gains an opt-in alias-expanded `topics` pre-ranking filter (fail-open, no
  effect when unused). New `memory-seed topics list` and `memory-seed topics check` commands
  validate the vocabulary and entry usage (unknown/malformed/duplicate/collision errors;
  deprecated-use and >3-count warnings; unused-topic info) - deliberately separate from
  `links check`, since topics are membership, not a graph edge kind. `session_logging.md`
  (live + seed) documents the field and the read-the-index-first authoring rule. This repo's own
  vocabulary was derived from the 62 slugs already in use (user-approved 19-canonical
  consolidation with every observed slug preserved as canonical or alias). Trace rendering of
  indexed topics and MCP topic-management tools stay deferred (plan Phase 4).
- Memory Trace UI pass: the Trail (git-graph-style timeline over session entries) is the primary
  tab and default view, retiring the Timeline tab; search acts as a function over the active view
  (matching rows keep full presence with a marker, everything else dims) instead of a separate
  results page; relationship routes (`replaces`/`evolves`/`related`) render in a dedicated dotted
  zone left of the branch lanes with same-branch context shown as row brackets.
- Versioned `/api/v1/*` API alongside the legacy `/api/*` surface: Pydantic response models, a
  committed OpenAPI schema and generated TypeScript types as contract fixtures, plus Phase-0
  regression harnesses (deterministic synthetic corpus generator and a Trail lane/edge golden
  fixture) targeting the future React client.
- Memory Trace worktree switcher: one running server can display each on-device git worktree's
  branch-specific memory. `/api/worktrees` enumerates checkouts (from `git worktree list`, the
  only paths ever served); every legacy data endpoint gains an optional `worktree` param backed by
  lazily built per-worktree services; a header dropdown (hidden for single-checkout repos) switches
  the whole UI, defaulting to the launch checkout.
- Commit-accurate Trail merges: fork/merge connectors are driven by the `Memory-Entry:` trailers
  on trunk merge commits (one first-parent `git log` pass plus `merge-base` fork points, cached
  beside the diff-derived authoring map) instead of a positional heuristic. Merge anchors
  interpolate to commit-time positions between entries (back-to-back merges spread apart), trunk
  merge rings are hoverable and click-select the merged work, the reader splits "Authored in" from
  "Merged to main by", a branch whose newest entry is unmerged dangles open, and pre-trailer-era
  branches keep the old heuristic flagged "estimated" on hover. A dashed, dimmed phantom trunk
  extends main's lane above its newest displayed entry so branches merging into main up top have a
  visible trunk to land on without asserting a live current main. Legacy `/api/*` + vanilla UI
  only for now; the `/api/v1` contract is deliberately untouched.
- Trail lane readability: the first four lanes each cycle a pack of three bright colors across
  daisy-chained branches (12 unique colors; deeper lanes pin to their pack's middle color), lane
  allocation orders branches by entry time (older/compact inner, newer outer), and each row's
  time/title indentation follows the lane silhouette (date-separator rows included).
- Lifecycle-edge link sidecars: `supersedes`/`evolves`/`related_entries` edges can be authored
  AFTER an entry in append-only `sessions/links/YYYY-MM/YYYY-MM-DD.md` sidecars (mirroring the
  decision-diagram sidecar mechanism) instead of reopening written entries. The Trail merges
  sidecar and entry-YAML edges at read time; `links check` validates sidecar refs through the same
  dangling and forward-only guards (`orphan-link-sidecar`, `link-sidecar-date-mismatch`,
  `malformed-link-sidecar`) attributed to the source entry's timestamp. New `memory-seed link
  audit [--for ID] [--date YYYY-MM-DD]` finds entry pairs sharing `F:` files or topics with no
  recorded edge - file overlap qualifies a pair even without a shared topic and surfaces
  already-related pairs as lifecycle upgrade candidates; IDF weighting keeps hub files from
  dominating. `end_of_turn.md` gains a Lifecycle Link Sweep step (audit today's entries, classify
  retire-vs-refine, record in the sidecar with user approval).
- Canonical entry-id generation is now one call away on both agent surfaces: `memory-seed session
  entry-id` (CLI) and `memory_entry_id` (MCP) wrap the deterministic sha256 generator so ids stop
  being hand-rolled (hand-rolled ids are irreproducible and drift outside the canonical Crockford
  alphabet). `links check` ref extraction (entry YAML and sidecars) now uses the wider trailer-id
  pattern so refs to real non-Crockford ids are validated instead of silently skipped.
- `memory-seed session append`: entry authoring with structure enforced - target resolution,
  now-timestamp (refusing out-of-order appends loudly; conflicts are fixed consciously, never
  silently bumped), canonical id, YAML shape, ref validation (fabricated and forward-pointing ids
  refused), controlled-topic resolution, and branch auto-capture, while title/classification/body
  prose pass through verbatim. `memory-seed session reorder --date` repairs a misordered day as a
  pure block permutation (entry bytes untouched; dry-run default).
- `memory-seed esr`: one read-only end-of-turn preflight covering links check, topics check, the
  session-scoped link audit, per-worktree posture (merged+clean checkouts marked as stale-sweep
  candidates), and live-vs-seed skill twin drift (control-plane dev repo only). Every section
  prints even when clean; exit code reflects only hard integrity failures.
- Memory-Entry trailers stamp automatically on ordinary commits: a repo-tracked
  `prepare-commit-msg` hook (`.memory-seed/hooks/prepare-commit-msg.py`, seeded) appends
  deduplicated trailers for staged session entries and never blocks a commit. `memory-seed hooks
  install` writes the sh shim into the git common dir (covering all worktrees); `init` installs it
  by default when a repository exists.
- Memory Trace serving: index.html's asset `?v=` tags are rewritten per request with a content
  hash of `app.js`+`styles.css` (no manual cache-bust bump to forget; asset edits take effect
  without restart), and `--static-root` / `MEMORY_TRACE_STATIC_ROOT` serves another checkout's UI
  assets for verifying a worktree's changes without copying files. The Trail golden fixture is
  regenerated browserlessly via `tests/fixtures/regen_trail_golden.py` (node vm harness over the
  real `app.js`; byte-identical across runs).

## 2.17.0 - 2026-07-10

- Recorded two shipped-but-unchangelogged features found by the 2026-07-10 goal-run review:
  (1) **Memory Trace Phase-2 extraction** - the review UI moved into the `memory-trace/`
  source package (the `memory_trace` package, `memory-trace` command, and static assets; core
  sheds mandatory `fastapi`/`uvicorn`; `memory-seed[lense]` and `memory-seed lense` are
  deprecation shims), with Arc 2 UI work (reader subsection highlighting, Trail view with branch
  lineage + supersedes edges, client-side Mermaid rendering with source fallback).
  (2) **Skill profiles and CLI skill management** - fresh projects install core skills by default,
  optional profiles can be selected during `init`, ignored optional skills stay ignored on
  `update`, and `memory-seed skills list|ignored|add|remove` rewires skill files and registry
  entries.
- Fixed the fuse/merge-branch chronological rewriter butting each session-entry heading against
  the previous entry's last line: `_write_chronological_session_file` and
  `_write_chronological_diagram_file` now join entries with a blank line, restoring the
  hand-appended log's separation. Files previously rewritten cramped are normalized the next time
  a fuse touches them; a regression test pins the one-blank-line contract.
- Added typed evolution edges and artifact lineage (evolution-edges plan): entries can declare
  `evolves:` - "extends that decision, which remains valid" - with a computed, read-time-only
  `evolved_by` inverse that never dampens `importance_score` and never feeds `exclude_superseded`
  (the semantic line vs. `supersedes`); `links check` gains per-kind forward-only guards
  (`dangling/self/postdates/cycle` for evolves), the `authored-inverse-field` guard (a stored
  `superseded_by:`/`evolved_by:` key is now a named integrity error - append-only enforcement),
  and `malformed-continuity`. The new structured `continuity:` field records artifact renames,
  migrations, and removals (`kind`/`from`/`to`; `to` forbidden on removal) as historical labels;
  recorded renames feed a transitive alias table in `link suggest`/`memory_link_suggest`, which
  now also applies a rarity-weighted `F:` file-overlap boost with per-suggestion shared-file
  evidence (boost-only: hub files count ~nothing, absent `F:` is never penalized). Every
  `memory_search` result now carries computed `superseded_by`/`evolved_by` so consumers see
  retired/evolved status at retrieval time without extra calls - additive fields, ranking and
  order untouched. Decision Harvest (live + seed skills) gains the lifecycle prompts: does a
  harvested decision replace/remove/evolve an earlier entry, and did the turn rename, relocate,
  or remove any artifact.
- Added `memory-seed session merge-branch --branch <branch> [--dry-run]`: one-step task-branch
  integration that wraps the previously manual dance (fuse dry-run, `git merge --no-ff
  --no-commit`, `session fuse --apply`, commit) so session entries always land in timestamp order
  without a separate fuse step to forget - added after two real incidents where skipping that step
  let raw git line-merges land entries out of chronological order. Fails closed: fuse issues abort
  before any merge state exists; non-session conflicts leave the merge in progress for manual
  resolution (never `merge --abort`); branch-touched session paths are reset to base content before
  the fuse apply, which defeats both conflict markers and silent out-of-order auto-merges; requires
  a clean working tree and names the dirty paths when refusing. `agent_collaboration.md` (live +
  seed) now routes integration through `session merge-branch` first, keeping `session fuse` as the
  lower-level primitive for manually inspected merges. No new MCP tool: MCP stays read-only for
  this workflow.
- Hardened the `session-log-check.py` Stop hook against reminders going unaddressed: a gitignored
  `.memory-seed/.session-log-check-state` (fail-open on corruption) tracks consecutive stale checks
  with no new session entry appearing in between, escalating from the base reminder to explicit
  "repeated" wording (naming the count, citing `agent-rules.md`'s discipline-failure framing) instead
  of repeating identically forever; a new entry resets the counter. The 15-minute staleness check
  itself is unchanged and was already anchored to the last logged entry's own timestamp rather than
  to hook-invocation frequency. Reminder language was also tightened: leads with the imperative,
  names concrete triggers (file changes, `git push`/`merge`/`rebase`/delete, any decision), and
  states D/R as required on every entry instead of framing DRAFT labels as decision-only.
- Fixed two `session fuse` bugs that made it unusable on this repo's own branches. (1) The git
  subprocess helpers (`_git_text`, `_git_show_text`, `find_trailer_commits`) now decode output as
  strict UTF-8 and catch `UnicodeDecodeError`, instead of defaulting to the Windows locale (cp1252)
  and crashing / silently truncating on non-ASCII session content. (2) Branch-side validation is now
  scoped to the files the branch actually changed (three-dot `git diff <base>...<branch>`), so
  unchanged base-tree files — including legacy pre-schema logs that carry no `entry_id` — no longer
  block the fuse; base-side enumeration stays full for already-present and sidecar-parent lookups.
- Added three read-only authoring-support MCP tools so the LLM's write-side loop matches its
  retrieval loop: `memory_link_suggest` (rank older entries to link, returning paste-ready
  `related_entries`), `memory_link_show` (one entry's related-entry graph node — outbound/inbound
  edges, supersession, importance, linked-commit count), and `memory_session_target` (resolve the
  session-log append target without ever creating the file). They wrap the existing
  `suggest_related_entries`/`build_related_entry_graph`/`session_target` functions, are routed through
  `history_retrieval.md`, and keep all session writing on the CLI/direct-file path. The CLI `session`
  group help was relabeled to cover its write-capable `fuse` subcommand, and the two `migrate`
  subcommands now cross-reference each other.
- Added a warning-only `memory-seed branch status [--json]` command that reports current Git
  branch/worktree posture and recommends a task branch plus `git merge --no-ff` when distinct
  feature or proposal work is happening directly on the integration branch. No hard block — small
  fixes, release prep, and emergency repairs may still proceed on the integration branch.
- Tightened session-log closeout: `session_logging.md`/`end_of_turn.md` now route through an
  explicit **Decision Harvest** step before choosing the entry shape (single DRAFT vs. multi-decision
  D1/D2), so durable choices made in a turn are captured individually rather than compressed into one
  broad record. Decision-diagram sidecar guidance changed from an optional consideration to a
  **positive trigger** for branch/merge topology, old-to-new layout migrations, schema/compatibility
  flows, multi-agent concurrency, command lifecycle flows, and retrieval/data pipeline decisions.
- Added the Phase 1 UTF-8 text contract: `.editorconfig`, `.gitattributes`, `memory_seed.text_files`
  helpers for UTF-8/LF/NFC text and Unicode-preserving JSON, README documentation, MCP
  Unicode-preserving JSON output, and regression tests for non-ASCII round trips.
- Completed encoding hardening: `memory-seed encoding check` reports invalid UTF-8, UTF-8 BOMs,
  CRLF line endings, non-NFC text, likely mojibake, and implicit text-mode Python I/O. The new
  `memory-seed encoding repair [--dry-run]` command atomically repairs safe BOM/newline/NFC drift
  after writing timestamped backups, while invalid UTF-8 and likely mojibake remain blocked for
  manual review. `doctor` now summarizes encoding findings non-fatally.
- Added safe process-management and upgrade commands for both packages: `memory-seed processes`,
  `memory-seed shutdown`, and `memory-seed upgrade`, plus matching delegated commands for
  `memory-trace`. Shutdown is confirmation-gated by default, supports `--dry-run`, `--yes`, and JSON
  output, excludes the current control command, and only targets processes whose executable path or
  command line clearly belongs to the package. `upgrade` blocks on failed shutdown and can run
  `uv`, `pipx`, or `pip` upgrades via `--manager`.
- Made agent integration selection a first-class `init` step: interactive init now presents an
  opt-out agent prompt with all supported agents selected by default, `--agents none` installs only
  the shared runtime, `--no-agent-prompt` skips the prompt, and init/`agents list` report both
  installed and ignored agents.
- Aligned `proposal_lifecycle.md` with the repository's numbered docs taxonomy
  (`docs/1_Inbox`, `docs/2_Todo`, `docs/3_Spec`, `docs/4_Reference`) while preserving the generic
  bootstrap taxonomy (`docs/inbox`, `docs/todo`, `docs/reference`) for newly initialized projects.
- Slimmed `agent-rules.md` further into a startup contract and added optional
  `skill_architecture.md` under the new `governance` skill profile. The new skill owns guidance for
  skill/profile boundaries, concise trigger-registry entries, and seed/live parity; `agent-rules.md`
  now points to it before agents move procedural guidance between rules, policy, and skills.
- Switched new session writes to month-grouped targets:
  `.memory-seed/sessions/YYYY-MM/YYYY-MM-DD.md`,
  `.memory-seed/sessions/YYYY-MM/YYYY-MM-DD/<user>.md`, and grouped diagram sidecars under
  `.memory-seed/sessions/diagrams/YYYY-MM/YYYY-MM-DD.md`. Core discovery, retrieval, MCP/Trace
  parsing, `compact`, hooks, and `links check` continue reading legacy flat/day layouts. Added the
  explicit `memory-seed migrate sessions-month-layout [--dry-run]` command to reorganize old files
  with backups; no migration runs automatically during init/update/hooks/MCP/Trace startup.
- Added branch-session fuse hardening for multi-agent integration: `memory-seed session fuse --branch
  <branch>` previews branch-local session entries and diagram sidecars, while `--apply` is gated to
  an in-progress `git merge --no-ff --no-commit`. Existing entries/sidecars are immutable, imported
  entries must carry matching `branch:` metadata, sidecars require a parent entry already on base or
  accepted in the same fuse, and MCP now exposes read-only `memory_branch_status` and
  `memory_session_fuse_preview` tools routed through `agent_collaboration.md`.

## 2.16.0 - 2026-07-05

- **Public retrieval service (`memory_seed/retrieval.py`), Memory Trace distribution plan Phase 1:**
  the MCP-coupled search orchestration and result-dict contract moved verbatim out of
  `mcp_server.py` into an MCP-independent public service (`search_memory`, `get_chunk`,
  `resolve_semantic_provider`, `format_search_results`, `ranked_to_dict`, `chunk_to_dict`). The MCP
  server is now a thin JSON-RPC wrapper with a byte-identical tool contract (parity tests assert
  `call_tool` == service output); Memory Trace consumes the same service. This is the frozen
  surface the companion UI package imports.
- **Entry-level result rollup:** `EntryRollup` / `rollup_entry_matches()` / `rollup_entry_results()`
  in the retrieval service collapse ranked entry+section matches into one visible entry-level result
  (entry chunk preferred as representative, matching sections preserved as highlight metadata,
  `score_source` = `entry`|`section-rollup`, `best_match_chunk_id`). Memory Trace entry-granularity search
  consumes the shared grouping; a strong subsection match can now drive an entry's score without
  appearing as a separate selectable record. `granularity=section|all` and the MCP contract are
  unchanged. Memory Trace UI copy says "entry"/"session entry" and renders "Matched section" chips.
- **Session decision diagram sidecars, Phase 1:** optional authored reasoning diagrams appended to
  `.memory-seed/sessions/diagrams/YYYY-MM-DD.md` — one dated file per day, mirroring the session-log
  filename convention for filesystem readability; each diagram is a `## <timestamp> - <title>` heading
  block naming `entry_id` in a fenced yaml block, followed by fenced ```` ```mermaid ```` block(s).
  `links check` validates them (`malformed-diagram`, `orphan-diagram`, `diagram-date-mismatch`;
  deterministic checks only, sidecars always optional).
  `retrieval.entry_diagram_sidecars()` surfaces per-entry sidecar metadata; `get_chunk` grows an
  opt-in `include_diagrams` flag the MCP tool never passes; Memory Trace's chunk view carries a `diagrams`
  metadata list. Authoring guidance shipped in `session_logging.md` + `end_of_turn.md` (live + seed).
- Recorded the intermediate Memory Trail name availability check in `memory-trail-renaming-plan.md`:
  `memory-seed-trail` is unregistered on PyPI, but `memory-trail` is a live same-niche product —
  the later product-naming decision settles on Memory Trace as the package/product and Trail as an
  internal evolution view.
- Added `docs/3_Spec/graph-edge-contract.md`: the single reference for how decision-graph edges
  (`related_entries`, `supersedes`, `commits`) and derived metrics (`inbound_relation_count`,
  `importance_score`, `connectivity`, `commit_reference_count`) are defined, computed, and read across
  CLI, MCP, Memory Trace, and `links check`. Codifies the standing rules: read the canonical graph,
  keep git out of the hot path, expose before you rank, one name one meaning.
- Exposed `commit_reference_count` on `memory-seed link show` and `memory_get_chunk`: the count of
  distinct commits linking to an entry (its `commits:` field ∪ `Memory-Entry:` trailer, deduped by
  SHA). Computed caller-side via `commit_reference_ids()` so the graph reader stays git-free.
  Deliberately a standalone read-only field, **not** folded into `importance_score` (that would make
  the score git-context-dependent and inconsistent across surfaces); composing it into a score is a
  later evidence-gated ranking experiment.
- Memory Trace graph nodes now carry `importance_score`, and a "Size:" toggle sizes nodes by either
  link `connectivity` (default) or `importance_score`. The preference persists in local storage; the
  toggle is client-side (no reload).
- Added `proposal_lifecycle.md` to the seeded skill set and trigger registry. It formalizes proposal
  movement through inbox -> todo -> completed/reference lanes, including status blocks,
  completed-proposal movement rules, and roadmap/audit update surfaces.
- Added `risk_signaling.md` to the seeded skill set and trigger registry. It defines qualitative
  Proceed / Proceed-and-flag / Propose-and-wait / Stop action tiers plus STOP categories for
  destructive, irreversible, security/trust-boundary, shared/control-plane, external-communication,
  and financial actions. Cross-referenced from `agent_collaboration.md` and `security_triage.md`;
  guidance-only, with no new session schema or automated gate.
- Added a Dependency Strategy to `agent_collaboration.md` (+ seed twin): three dependency tiers
  (`none`/`isolated`/`dependency-changing`), four new task-packet fields (`dependency_tier`,
  `dependency_setup`, `dependency_definition_policy`, `dependency_shared_cache_policy`), dependency
  definition files/lockfiles named as orchestrator-owned shared files, shared-cache-vs-shared-environment
  guidance, and an optional tmux-as-control-room note. Documentation-only; no CLI scaffold. Plan moved
  to `docs/2_Todo/completed/worktree-dependency-strategy-plan.md`.
- Added `docx_render_windows.md` to the seeded skill set and trigger registry: Windows-safe DOCX
  render fallback covering the LibreOffice `UserInstallation` profile-URI hang, a bounded two-step
  DOCX→PDF→PNG render pattern, stale-process cleanup, Word field/TOC refresh before render QA,
  page-level visual inspection rules, and a single-writer render / read-only validator collaboration
  boundary. Cross-referenced from `office_document_editing.md`.
- Kept `MEMORY_SEED_LENSE_CACHE_ROOT` working as a compatibility alias for Lense cache placement;
  `MEMORY_SEED_CACHE_DIR` remains the preferred generic cache variable.

## 2.15.0 - 2026-07-04

- Added an opt-in `exclude_superseded` filter to `memory_search` (default `false`). When set, entries
  with a non-empty computed `superseded_by` are dropped from that query's results only — an opt-in
  narrowing like `date_from`/`date_to`, never a default and never a hard exclusion otherwise, so
  superseded entries stay fully retrievable by default (deprioritized via `importance_score`, not
  hidden). Backend-only; no CLI or UI default. From `docs/2_Todo/completed/exclude-superseded-filter-plan.md`.
- Exposed `importance_score` (ranking P1b): `inbound_relation_count` dampened by a fixed multiplier
  (`SUPERSEDED_IMPORTANCE_DAMPING = 0.25`) when the entry has any inbound `supersedes` edge —
  computed on `RelatedEntryNode`, shown by `memory-seed link show` (flagged when dampened) and
  returned in `memory_get_chunk` metadata. This completes the supersession harmony contract: a
  well-cited but retired decision ranks below a live, moderately-cited one, while staying fully
  retrievable (never hidden). Supersession edges never inflate the underlying count — the dampener
  is a post-hoc override. Read-only; default `memory_search` ranking is untouched. From
  `docs/2_Todo/completed/interaction-frequency-ranking-plan.md` (P1b) and `docs/2_Todo/completed/supersession-edges-plan.md`
  (harmony contract).
- Exposed `inbound_relation_count` (ranking P1a): the count of inbound `related_entries` backlinks an
  entry has accumulated (how many other entries reference it), shown by `memory-seed link show` and
  returned in `memory_get_chunk` metadata. Read-only — default `memory_search` ranking is untouched,
  per the exposure-before-ranking-changes policy. This is the directional importance-signal precursor.
- Renamed the Trace graph-node `related_degree` field to `connectivity`. Its computation is
  unchanged (combined inbound+outbound `related_entries` edges, used for node sizing) — the rename
  resolves a collision with the new inbound-only `inbound_relation_count` above, since the two count
  genuinely different things. The two-field split is documented in
  `docs/2_Todo/completed/interaction-frequency-ranking-plan.md`.
- Added git commit <-> decision entry linking (P1): a `Memory-Entry: <entry_id>` commit-message
  trailer convention (documented as a Working Principles bullet in `agent-rules.md` + seed twin)
  plus an optional `commits:` entry-YAML field of full 40-character SHAs, backfillable only while
  the entry is still the newest one (same-turn scoping, no historical edits). New read-only
  `memory-seed link commits <entry_id>` prints both sources: the stored field and a
  `git log --all --grep` trailer scan. `links check` rejects short/malformed hashes always
  (`malformed-commit-hash`) and unknown hashes when a `.git` repository is present
  (`unknown-commit`); outside a git repo, existence checks skip cleanly. From
  `docs/2_Todo/completed/git-commit-entry-linking-plan.md`.
- Added typed supersession edges (P1): an optional `supersedes:` list in entry YAML marks earlier
  decisions an entry replaces, kept strictly separate from `related_entries`. The read-time inverse
  (`superseded_by`) is computed in `build_related_entry_graph()` the same way inbound backlinks are,
  and exposed via `memory-seed link show` and `memory_get_chunk` (search results carry the stored
  `supersedes` field). `links check` validates the new edge: dangling refs (`dangling-supersedes`),
  self-references (`self-supersedes`), forward-only violations where the target postdates the
  referencing entry (`supersedes-postdates`), and same-minute cycles via a DFS (`supersedes-cycle`).
  Superseded entries stay fully retrievable — supersession deprioritizes, never hides. Schema
  documented in `skills/session_logging.md` (+ seed twin). From `docs/2_Todo/completed/supersession-edges-plan.md`.

## 2.14.0 - 2026-07-03

- Session-log layout now gates on the `participants:` registry, not just a configured user. `session_target()` only switches to per-user files (`sessions/YYYY-MM-DD/<user>.md`) once `.memory-seed/project.yaml` lists 2 or more participants; with 0 or 1, it stays on the shared flat file even with a local user configured, since per-user files exist to avoid concurrent-author conflicts that don't arise until there's a second author. An explicit `--user <slug>` CLI override still bypasses the gate. The SessionStart hook's own user resolution mirrors this so it keeps reading the same file `session_target()` writes to.
- Added a one-time identity-setup offer to the SessionStart hook: if no local identity is configured (no `MEMORY_SEED_USER`, no `.memory-seed/local.yaml`), it suggests `memory-seed user set <slug>` plus a `participants:` entry, then never repeats (tracked by a gitignored `.memory-seed/.identity-offer-stamp`). Skippable; most projects are solo and don't need it.
- `memory-seed doctor` now warns (non-fatal) when a configured local user's slug has no matching `participants:` entry in `.memory-seed/project.yaml`, so `user_initials` stays resolvable for multi-user tooling.
- Documented the identity/layout model in `agent-rules.md` and `skills/session_logging.md`.
- Fixed `memory-seed links check` silently skipping entry-level `related_entries` validation for legacy-flat session files. The dangling-ref scan was scoped inside a `per-user-day`-only branch; a dangling `related_entries` ref in a `sessions/YYYY-MM-DD.md` file passed with no warning. The entry-level scan (each entry's fenced `` ```yaml `` block, same shape in both layouts) now runs unconditionally, while the genuinely per-user-file-specific checks (frontmatter, `hash_id`, user-slug) remain scoped to per-user files.
- Added two Working Principles to `agent-rules.md`: a decision-ladder-before-adding-code check with a habit of noting deferrals, and a reminder not to strip terse validation/ownership guards without understanding what they protect against. Also added regression tests for two previously-uncovered guards (`_valid_session_date` and the MCP ownership-preservation check in the `.mcp.json`/`.cursor`/`.gemini` merge functions) so a future simplification pass has a test that fails if either is removed.
- Added a third Working Principles bullet to `agent-rules.md`: default to plain text, reserve Mermaid for genuinely spatial/temporal/concurrent structure, keep blocks small, and check both syntax and semantic freshness (a stale roadmap diagram is as misleading as a broken one). From `docs/2_Todo/completed/mermaid-usage-guidance-plan.md`.
- Added a failed-approaches rule to `skills/session_logging.md`'s Reason Rules: an approach that was attempted and failed (or proved incompatible) during a session must be logged under `A` even when not asked — one line stating what was tried and why it failed, as empirical evidence for future sessions. From `docs/2_Todo/completed/failed-approaches-logging-plan.md`.
- Added the named "Fan-Out Recipe: Explore / Plan / Implement / Validate" to `skills/agent_collaboration.md`: a 9-gate pipeline (Scope through Final Handoff) with a bounded review-to-rework loop capped at 2 iterations, preflight identity verification for both writers and read-only explorers, and orchestrator-only shared-file writes. The task packet gained `base_sha`, `expected_pwd`, `integration_artifact`, `capability_tier`, `shared_file_policy`, `conflict_owner`, `preflight`, and `review_loop` fields, plus vendor-neutral capability-tier guidance (planning and review both warrant the top tier). From `docs/2_Todo/completed/agent-fanout-workflow-plan.md`.

## 2.13.0 - 2026-07-01

- Added `memory-seed lense`, an optional local FastAPI/Uvicorn browser UI for
  searching, filtering, reading, graphing, and timeline-scanning Memory Seed
  session history. Install with `pip install "memory-seed[lense]"`; without the
  extra the command prints the install hint.
- Included the Memory Lense static UI assets in the package distribution.
- Added the universal `agent_collaboration.md` skill for Git-first subagent, branch,
  worktree, merge-conflict, and multi-developer agent workflows.
- Extracted detailed control-plane procedures from `agent-rules.md` into seeded lazy
  skills: `history_retrieval.md`, `session_logging.md`, `end_of_turn.md`,
  `memory_hygiene.md`, and `subproject_runtime.md`. `agent-rules.md` now keeps
  startup-safe summaries and explicit skill pointers, and seeded ESR commands point
  to the `end_of_turn.md` checklist.
- Fixed the packaged seed inventory so every `SeedFile` source is included in
  wheel/sdist package data, including `/esr` command files, lifecycle hooks,
  document skills, and the new lazy skills.
- Added `memory-seed link suggest [--for <entry_id>] [--top-k N]` - a read-only command that ranks
  **older** session entries to link from a target entry (default: the newest entry), excludes the
  target and its already-linked entries, and prints a copy-pasteable `related_entries:` snippet. It
  reuses the existing ranker with recency disabled so similarity drives the order.
- Added `memory-seed link show <entry_id>` - prints an entry's stored outbound `related_entries`
  edges plus its computed inbound backlinks, so the related-entry graph is **bidirectional at read
  time** without ever editing a historical entry.
- Added `build_related_entry_graph()` in `semantic_cache.py`, the canonical bidirectional
  related-entry graph (outbound as stored; inbound computed only from resolvable refs) for MCP and
  future UI consumers. Scope + decisions in `docs/2_Todo/completed/related-entries-generation-plan.md`.

## 2.12.0 - 2026-06-15

First batch of multi-user Phase 3 increments from the reviewed 3.0 plan.

- **Added session-memory integrity validation** (`memory-seed links check`) — the first increment of the 3.0 multi-user roadmap (Phase 3). It scans both legacy-flat (`sessions/YYYY-MM-DD.md`) and per-user (`sessions/YYYY-MM-DD/<user>.md`) layouts and reports: duplicate `entry_id`s (the 32-bit-ID collision risk), duplicate file `hash_id`s, dangling `related_entries`/`related_memories` references, and per-user-file frontmatter problems (filename↔frontmatter `user` or `session_date` mismatch, missing/malformed `hash_id`, unsupported `schema_version`, invalid user slug). Each issue names the source file and the offending value; the command **exits non-zero** on any issue so it works as a CI gate. It validates entry-level `related_entries` inside session-entry YAML as well as file-frontmatter related refs, resolving both legacy `ms-` IDs and new `mse_` IDs.
- `memory-seed doctor` now surfaces a one-line, non-fatal summary when integrity issues exist, pointing at `links check` for the full report (it does not change doctor's pass/fail).
- New generated session `entry_id` values now use deterministic 80-bit `mse_` IDs encoded as 16 lower-case Base32 characters. Existing `ms-` entry IDs remain valid and are never rewritten.
- `memory_search` / `memory_get_chunk` now expose `session_date`, `path`, per-user `user`, `file_hash_id`, and entry-level `related_entries`; `memory_search` accepts `user`, `date_from`, and `date_to` filters applied before ranking.
- `.memory-seed/project.yaml` now supports a `participants:` registry alongside the existing `agents:` selection. `read_project_participants()` parses valid participant entries fail-open, and agent-selection reads/writes preserve the participant block.
- Added `memory-seed migrate sessions-layout`, a conservative migration command that splits legacy flat `sessions/YYYY-MM-DD.md` files into `sessions/YYYY-MM-DD/<user>.md` files using `.memory-seed/project.yaml` participant initials, supports `--dry-run`, preserves entry IDs, backs up migrated sources, removes migrated flat files to avoid dual-read duplicate IDs, and blocks ambiguous or unsafe merges.
- Documented the optional entry-level `related_entries` field in the `agent-rules.md` session-log schema so agents can author the graph edges that `memory_search` and `links check` already read and validate.
- Bumped control-plane version from `2.11` to `2.12`.

## 2.11.0 - 2026-06-15

- **Generalized the end-of-session routine (ESR) and shipped it as a seeded command.** The "End Of Turn" routine in `agent-rules.md` now also runs a **consolidation review** (promote durable, reusable facts from the session logs into `index.md`/`policy.md` via the `memory_consolidation` skill) and a **baseline-promotion check** (flag any approved adaptation general enough to reuse beyond this project, recorded in `.memory-seed/plans/`, create-if-needed). Both are vendor-neutral and benefit every agent.
- The routine now ships as a seeded **`/esr`** command for agents with a verified repo-level command mechanism: Claude (`.claude/commands/esr.md`, version-tracked) and Gemini (`.gemini/commands/esr.toml`, deploy-once since TOML can't carry a version marker). Previously `/esr` existed only as a repo-local Claude convenience. Codex, Cursor, and any other agent run the same routine directly from `agent-rules.md` — that's where the canonical, vendor-neutral routine lives. The command is agent-selective (a Claude-only install gets only the Claude command, etc.).
- **No blocking end-of-turn hook.** A throttled `Stop` nudge hook was specced but deliberately not shipped: evolution needs reasoning and explicit user approval, which a hook cannot do; the command plus the routine cover it without nagging on every turn.
- Bumped control-plane version from `2.10` to `2.11`.

## 2.10.0 - 2026-06-14

- Added opt-in user-aware session targets. `memory-seed user set/show/clear` manages a gitignored `.memory-seed/local.yaml`; `MEMORY_SEED_USER` and `memory-seed session target --user <slug>` can override it.
- Added `memory-seed session target [--create]`. Without a configured user it keeps the legacy flat target (`.memory-seed/sessions/YYYY-MM-DD.md`); with a configured user it targets `.memory-seed/sessions/YYYY-MM-DD/<user>.md` and `--create` initializes per-user frontmatter with `schema_version: 2`, `session_date`, immutable `hash_id`, `user`, and `created_at`.
- Made session hooks user-aware while preserving legacy behavior. `session-log-check.py` checks only the active user's file, and `session-start-context.py` injects the active user's newest entry plus same-day co-contributor file counts.
- Bumped control-plane version from `2.9` to `2.10`.

## 2.9.0 - 2026-06-14

- Added read-only dual discovery for multi-user session logs. `memory_search`, `memory_get_chunk`, and `memory-seed compact` now read both legacy flat files (`.memory-seed/sessions/YYYY-MM-DD.md`) and per-day/per-user files (`.memory-seed/sessions/YYYY-MM-DD/<user>.md`, e.g. `2026-06-21/jean.md`).
- Preserved legacy write behavior and hooks. This release does not move existing logs, change where agents append new session entries, or resolve active users; SessionStart and session-log reminder hooks remain flat-layout until a later phase.
- Hardened fallback MCP chunk IDs for entries without `entry_id`: generated IDs now use the date-qualified source path, preventing collisions between same-named per-user files on different dates.
- Bumped control-plane version from `2.8` to `2.9`.

## 2.8.0 - 2026-06-14

- **Non-destructive routing into pre-existing entry-point files.** The four routing files Memory Seed manages — `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` — share their names with files other tools own (e.g. HyperFrames also uses `AGENTS.md`/`CLAUDE.md`). `init` and `update` now decide per file by ownership: a file that doesn't exist is written in full (unchanged); a file carrying our `memory-system-version` frontmatter is version-gated and archived+replaced (unchanged); a **foreign** file (no frontmatter) has a marker-delimited routing block — `<!-- BEGIN memory-seed -->…<!-- END memory-seed -->` pointing into `.memory-seed/` — **injected at the end, never overwriting the host's content** (even under `init --force`). On later updates the block is re-synced *in place* (the "second merge"), gated on content-equality so an unchanged stanza causes no churn. This mirrors the existing JSON-config merge philosophy (`_merge_grouped_hook`, the Copilot prompt-hook marker).
- **Behavior change:** a versionless entry-point file is now *merged* rather than *overwritten*. This retires the legacy "unversioned → archive under `unknown-*` + clobber" upgrade path. The fail-safe direction: when ownership can't be proven from frontmatter, append a block rather than destroy a file that is most likely host-owned or hand-edited.
- Added a `doctor` route-presence backstop (non-fatal `warnings` channel): if a `.memory-seed/` runtime exists but a present entry-point file is foreign and carries no routing block, it is flagged as an orphaned runtime ("`AGENTS.md` does not route into the `.memory-seed/` runtime — run `memory-seed update`"). Foreign routing files are no longer reported as version mismatches (the host owns the file; Memory Seed only manages its injected block).
- Bumped control-plane version from `2.7` to `2.8`. Existing projects running `memory-seed update` get the routing-merge behavior; a project whose `AGENTS.md`/`CLAUDE.md` is owned by another tool keeps that content and gains the routing block.

## 2.7.0 - 2026-06-14

- Promoted three **baseline seed additions**. Two new universal skill runbooks ship with `init`: `document_ingestion.md` (reading `.docx`/`.pdf`/`.pptx`/`.xlsx`/`.csv`/images as Markdown via markitdown, with per-format routing and fidelity caveats) and `office_document_editing.md` (field-safe surgical editing of Office documents that contain citations, captions, cross-references, or a TOC). Both get trigger-registry entries in `skills/index.md`. A new **Working Principles** section in `agent-rules.md` adds three cross-cutting rules: POC-gate a risky automated method before scaling it, state the verification split (what the agent can verify vs. what only the user can), and read share-aware copies of locked files.
- Added an **orphan & dead-artifact sweep** to the end-of-session routine. The "End Of Turn" section of `agent-rules.md` (and its seed twin, mirrored in this repo's `/esr` command) now includes a diff-scoped step: for everything the session added, confirm it is referenced somewhere (imported / registered / linked / routed) or remove it; for everything deleted or renamed, search for and resolve dangling references; flag scratch debris (temp files, commented-out code, half-removed features, stray untracked dirs, `*.bak`). The step is language-agnostic and never installs tools — if the project already declares a dead-code tool (vulture/ruff, knip, ArchUnit, cppcheck) the agent may run it, otherwise it just notes one is available. The sweep reliably catches orphan *files and features*; whole-codebase *dead code* remains a periodic tool job, stated explicitly so the routine does not over-promise.
- Added a deterministic **orphan-skill check** to `memory-seed doctor` (non-fatal `warnings` channel): any `.memory-seed/skills/*.md` runbook not registered in `skills/index.md` is flagged so it gets a trigger entry or is removed. This is the automatable backstop to the agent-performed sweep; it has deterministic ground truth and no false positives. (A session-log dangling-reference scan was deliberately *not* added — logs legitimately cite renamed, deleted, or example paths.)
- Bumped control-plane version from `2.6` to `2.7`. Existing projects running `memory-seed update` receive the updated `agent-rules.md` and `memory_doctor.md` skill.

## 2.6.0 - 2026-06-13

- Added **agent-selective install**. `memory-seed init` now accepts `--agents claude,codex` (and prompts interactively on a terminal) to install only the chosen agents' files — keeping repos clean (e.g. no `GEMINI.md` for a Claude+Codex user). `AGENTS.md`, the `.memory-seed/` runtime, and `.agents/` personas are always installed; only agent-specific routing files and per-agent hook/MCP configs are gated. The choice is persisted in `.memory-seed/project.yaml` (`agents:` list), which `doctor` and `update` respect (a deselected agent is never flagged missing or re-added). A project with no `project.yaml` behaves exactly as before (all agents). Added `memory-seed agents list|add|remove <agent>`; `remove` strips only Memory Seed's own entries (foreign config preserved) and backs up everything it touches. `codex` and `cursor` get no routing file — they read `AGENTS.md` natively.
- Added a **SessionStart orientation hook** (`session-start-context.py`). It reads the newest dated `.memory-seed/sessions/*.md` file directly and injects its path, all entry headings, and the most recent entry's body at session start, so agents establish current state by recency rather than semantic search (which ranks by topical similarity and can bury or omit the newest entry). Wired to Claude/Codex `SessionStart`, Gemini `SessionStart`, and Cursor `sessionStart` via `init`/`update`.
- Added **GitHub Copilot** as a supported agent. Copilot CLI: repo-local `.github/mcp.json` (`mcpServers` key, `type: stdio`) for `memory_search`/`memory_get_chunk`, plus a `sessionStart` **prompt** hook in `.github/hooks/memory-seed.json` (Copilot command hooks cannot inject context at sessionStart, and its `userPromptSubmitted`/`agentStop`/`sessionEnd` events do not support `additionalContext`, so it receives no per-turn reminders). VS Code Copilot: `.vscode/mcp.json` (`servers` key) + a thin `.github/copilot-instructions.md` router. The Copilot coding agent (github.com) reads `AGENTS.md` already; its MCP lives in repo/org settings (manual).
- **Fixed dead Gemini hook wiring.** Earlier versions wired Gemini's session-log and retrieval hooks to `Stop`/`UserPromptSubmit`, events Gemini does not expose, so they never fired. They now target `AfterAgent` (turn-end) and `BeforeAgent` (prompt-submit); `memory-seed update` strips the stale entries. The `--gemini` hook output now uses `hookSpecificOutput.additionalContext` as Gemini requires.
- Reconciled the per-prompt retrieval reminder (`memory-retrieval-check.py`) with the recency rule: it now points at `memory_search` for **topical** recall and defers "what's the latest" to the SessionStart/newest-file path, matching the new "Recency vs. Topical Retrieval" section in `agent-rules.md`.
- Bumped control-plane version from `2.5` to `2.6`. Existing projects running `memory-seed update` receive the new SessionStart hook, the Copilot wiring, the Gemini hook migration, and the reconciled reminder.

## 2.5.0 - 2026-06-04

- Added `.agents/` persona library. `memory-seed init` now ships six vendor-neutral agent persona templates (developer, content-creator, researcher, sales-rep, solo-founder, copywriter) under `.agents/`. Each persona file defines an identity, memory protocol pointing at `.memory-seed/`, operating rules, session discipline, skill routing, and an append-only `## Project Adaptations` section for traceable persona evolution. Persona files are runtime-local (deploy-once; `memory-seed update` never overwrites them) so project-specific customisations survive upgrades.
- Added `agent_name` field to session log entries. A new optional YAML field (`agent_name: <persona-slug>`) sits alongside the existing `agent_type` (LLM model/vendor) in every session entry. `memory_search` parses and returns it, enabling per-persona history queries. Old entries without the field are unaffected.
- Expanded `project-bootstrap.md` Step 9 — persona activation is now a five-sub-step guided flow: persona selection, personalization (entity name via pop-culture pick or user input; user name inferred from `git config`; business name inferred from project files with placeholders replaced in-file), skill routing (mapped skills table filled per persona role; gap detection with draft → approval → write for missing skills), `_registry.yaml` write with resolved metadata, and automatic onboarding of any unregistered `.agents/*.md` files dropped in after init.
- Expanded `agent-rules.md` Operating Mode Start with Step 9: if `.agents/_registry.yaml` exists, read it, load all active persona files, apply rules alongside `agent-rules.md` and `policy.md`, and record `agent_name` in all session entries. Expanded end-of-turn with Step 8: skill evolution — if a repeating workflow gap emerged, propose a draft skill file for user approval, then write it to `.memory-seed/skills/`, add a `persona:` trigger entry to `skills/index.md`, and update the persona's `### Role-Specific Skills` section.
- Added `copywriter-conversion.md` skill to the seed. Ships as a first-class universal skill with framework-selection decision table (AIDA, PAS, BAB, FAB, 4Ps, JTBD keyed to audience awareness level), developer-tool objection map, and format templates for README hero, landing page, Product Hunt tagline, email subject line, and GitHub description. Trigger entry in `skills/index.md` includes a `persona: copywriter` field; agents respect this and skip the skill when the copywriter persona is not active.
- Added `skills/index.md` trigger entries now support an optional `persona:` field scoping a skill to a specific active persona. Agents skip persona-scoped skills when the named persona is not active.
- Added bidirectional Didion ↔ Hopkins handoff protocol. A `## VII. Handoff Protocol` section in both the content-creator and copywriter persona templates defines a structured Copy Brief (Didion → Hopkins) and Repurposing Note (Hopkins → Didion) appended to the session log for the other persona to consume at startup. Neither persona reviews the other's work before publishing; Stark (solo-founder) holds the shipping decision.
- Added ESR slash command. `.claude/commands/esr.md` registers `/esr` in Claude Code, triggering the full end-of-session routine (session log write, `index.md`/`policy.md` review, persona evolution check, skill evolution check, unregistered persona detection) without requiring the user to describe it each time.
- Bumped control-plane version from `2.4` to `2.5`. Existing projects running `memory-seed update` will receive the updated `agent-rules.md`, `project-bootstrap.md`, and all skill files. The new `.agents/` templates and `copywriter-conversion.md` skill are added to projects that do not yet have them.

## 2.4.0 - 2026-06-04

- Added Codex CLI to MCP auto-registration. `memory-seed init` and `update` now write the `memory-seed-mcp` stdio server into a project-scoped `.codex/config.toml` (`[mcp_servers.memory-seed]`), bringing Codex to parity with Claude Code, Cursor, and Gemini. The merge is a zero-dependency text upsert (stdlib `tomllib` only inspects state; writes are line-based) so existing `.codex/config.toml` content and comments are preserved. Codex loads project MCP config only for **trusted** directories, so the trust step is surfaced in the README, the `--codex` retrieval-hook reminder, and a new `doctor` warning.
- Fixed Claude Code MCP registration: the server is now written to a project-root `.mcp.json` (the location Claude Code actually reads) instead of `.claude/settings.json > mcpServers`, which Claude Code silently ignored across 2.2.0–2.3.0. `memory-seed update` migrates existing projects by writing `.mcp.json` and stripping the dead `settings.json` block (ours-only; a foreign server squatting the key is left untouched).
- Added a non-fatal `warnings` channel to `doctor` / `DoctorResult`. It classifies the Codex MCP entry as `absent`, `current`, `foreign`, `stale-fixable`, or `stale-manual`, and warns when Codex hooks are installed without a working MCP registration — including when a hand-written non-standard TOML form is outdated and cannot be auto-migrated, so the no-op is never silent.
- Reframed the session-log format in `agent-rules.md` so the single-decision **DRAFT** record is the baseline shape, with the bare summary (simpler) and multi-decision (richer) shapes presented as explicit down/up routes. D/R are marked `(mandatory)` and A/F/T `(optional)`.
- Bumped control-plane version from `2.3` to `2.4` so existing projects running `memory-seed update` receive the reframed `agent-rules.md` and the Codex hook/MCP changes.

## 2.3.0 - 2026-05-29

- Made `memory-seed update` forward-only: it now skips a control-plane file when the project's local `memory-system-version` is the current version **or newer**, instead of only when it is exactly equal. Previously the equality check was symmetric, so a stale installed tool (older control-plane version) running `update` against a project on a newer control plane would silently overwrite the newer files with its older bundled seed — a downgrade. Version comparison is numeric, so multi-digit versions order correctly (`2.10` > `2.9`).
- Reframed the session-log append rule in `agent-rules.md` to be vendor-neutral. It now states the invariant ("append each entry at the physical end of the file; never insert above an existing entry") and the anchor hazard, with the mitigation that applies to any agent (confirm the actual last line before appending; never reuse a remembered anchor). `>>` / `open(f, 'a')` is demoted from a mandate to an optional technique for shell-capable agents, with a UTF-8 encoding caveat (some shells, e.g. PowerShell `>>`, default to other encodings, which would corrupt a UTF-8 log). The previous wording mandated a shell-specific mechanism inside a contract meant for any file-reading agent — and its heredoc example was unsafe on Windows. The `session-log-check.py` order-warning was reframed to match.
- Restored the two-step skill-registry wording in the `AGENTS.md` operating-mode read order ("Read `skills/index.md` as the deterministic skill trigger registry" / "Load full files only when the trigger registry matches"). It had been condensed to a single line that dropped the registry concept, diverging from `agent-rules.md`, `skills/index.md`, and `project-bootstrap.md`, which all describe the same two-step lazy-load contract.
- Bumped control-plane version from `2.2` to `2.3` so existing projects running `memory-seed update` receive the reframed append rule and the restored `AGENTS.md` wording.

## 2.2.3 - 2026-05-29

- Hardened session-log append discipline in `agent-rules.md`: added an explicit rule to use `>>` shell redirection or Python append mode (`open(f, 'a')`) when writing session entries, instead of editor replace/insert operations. Replace/insert requires an anchor line; if a prior edit already added content after that anchor, the entry lands mid-file. Append mode writes to the physical end unconditionally.
- Updated the session-log order-warning in `session-log-check.py` to include a concrete repair instruction: use `>>` or Python append mode to move an out-of-order entry to the end with the current clock time.
- Bumped control-plane version from `2.1` to `2.2`. Existing projects running `memory-seed update` will receive the updated `agent-rules.md`.

## 2.2.2 - 2026-05-29

- Fixed MCP server auto-registration to use `uvx --from memory-seed memory-seed-mcp --stdio` instead of the bare `memory-seed-mcp --stdio` command. The bare command requires `~/.local/bin` to be on the agent's PATH, which Claude Code and other agents do not inherit. Using `uvx --from memory-seed` resolves the script through uv, which is on system PATH, and works on any machine regardless of how or where the package is installed.

## 2.2.1 - 2026-05-29

- Bumped the reusable control-plane version from `2.0` to `2.1`. Existing projects running `memory-seed update` will now receive the updated `agent-rules.md` (DRAFT format improvements from 2.2.0) and `project-bootstrap.md`.

## 2.2.0 - 2026-05-29

- `memory-seed init` and `update` now register the `memory-seed-mcp --stdio` server in each vendor's MCP config: `.claude/settings.json` (Claude Code), `.cursor/mcp.json` (Cursor), and `.gemini/settings.json` (Gemini CLI). The `memory_search` and `memory_get_chunk` tools are now available to the agent without manual configuration.
- The memory-retrieval hook (`memory-retrieval-check.py`) now detects whether `memory-seed-mcp` is on PATH at prompt time. If the binary is missing (e.g. after a `uvx memory-seed init` ephemeral run), the hook surfaces a clear install instruction (`uv tool install memory-seed`) instead of directing the agent to call a tool that isn't available.
- All vendor config merge functions are now upsert (update-or-insert) instead of add-only. If a hook command or MCP entry changes between package versions, `memory-seed update` replaces the stale entry in place rather than appending a duplicate alongside it. Hook entries are identified by script filename (stable across version bumps); MCP entries are identified by command name.
- Consolidated the four direct session-log hook functions into thin wrappers over the shared `_merge_grouped_hook` / `_merge_cursor_event_hook` helpers, so there is one upsert implementation per schema shape.
- Promoted the DRAFT decision-record format definition in `agent-rules.md`: the "Reason Rules" section (naming and defining DRAFT) now precedes the "Entry Shapes" worked examples, so agents read the format definition before encountering it in use.
- Clarified that T (Tests/validation) may appear inline as `- T:` or as a separate `### Validation` section — both are accepted.
- Embedded DRAFT label reminder in the session-log staleness hook and the memory-retrieval hook so agents see the format at session start and at the moment of writing. Labels are now consistently tagged: `D (Decision, required), R (Reason, required), A (Alternatives, optional), F (Files, optional), T (Tests, optional)`.

## 2.1.3 - 2026-05-27

- Renamed the decision-record term "rationale" to "reason" across the reusable control-plane docs (`agent-rules.md`, `project-bootstrap.md`, `skills/memory_consolidation.md`). The DRAFT mnemonic is unchanged — `R` now stands for Reason — making the slot plainer and easier to recall.
- Documented the agent lifecycle hooks in the README: a new "Agent Hooks" section covering the session-log and memory-retrieval reminders installed for Claude Code, Codex, Gemini, and Cursor, plus `.memory-seed/hooks/` in the seed and runtime file trees.

## 2.1.2 - 2026-05-27

- Enforced append-only session-log chronology in `agent-rules.md`: entries are appended at the end with the current clock time, never backdated or reordered, so file order always matches timestamp order.
- Extended the session-log Stop hook (`session-log-check.py`) to warn when the day's entries are out of ascending time order, independent of the staleness check.
- Added a memory-retrieval hook (`memory-retrieval-check.py`) installed for all agents — Claude Code and Codex/Gemini via `UserPromptSubmit`, Cursor via `sessionStart` — reminding the agent to retrieve prior context (`memory_search` or recent session files) before substantive work. Gated by an 8-hour marker file so it fires about once per working session.
- Made MCP recency clock-sourced: `memory_search` now reads the current date from the system clock at call time and no longer accepts a caller-supplied `today` override (removed from the tool schema), so a stale agent-supplied date can no longer skew recency.

## 2.1.1 - 2026-05-27

- Fixed the Claude Code `Stop` hook output in `session-log-check.py`: now emits `{"systemMessage": ...}` instead of `hookSpecificOutput` with `hookEventName: "Stop"`, which failed Claude Code's hook output schema validation (`hookSpecificOutput` is only valid for `PreToolUse`, `UserPromptSubmit`, `PostToolUse`, and `PostToolBatch`).
- Added a `memory-seed help` command that prints the full command reference plus a "Keeping Memory Seed current" note distinguishing package upgrade from project seed-file update. Running `memory-seed` with no command now prints help instead of erroring.
- Documented the distinction between upgrading the package (`uv tool upgrade` / `pip install --upgrade`) and propagating seed files into a project (`memory-seed update`) in a new README "Updating" section; clarified that `update` sources files from the installed package, not PyPI.

## 2.1.0 - 2026-05-27

- Added multi-agent session log hooks: `memory-seed init` now installs `Stop`/after-response hooks for Claude Code (`.claude/settings.json`), Codex CLI (`.codex/hooks.json`), Cursor (`.cursor/hooks.json`), and Gemini CLI (`.gemini/settings.json`). Hooks remind the active agent to write a session log entry if none has been updated in the last 15 minutes.
- Added `memory_seed/seed/.memory-seed/hooks/session-log-check.py` — cross-platform Python hook script with `--codex`, `--cursor`, and `--gemini` flags for agent-specific output formats.
- Agent hook configs are handled as JSON merge targets (not seed file copies) so existing agent configuration is preserved on init and update.
- Strengthened `agent-rules.md` "End Of Turn" section: all agents (Claude, Codex, Gemini, Cursor) are now explicitly required to write session log entries before the current turn ends, not deferred or batched.
- Fixed `doctor()` to skip version-check for non-Markdown seed files.
- Added `.memory-seed/skills/index.md` as a deterministic skill trigger registry for universal lazy-loaded skills.
- Updated MCP memory retrieval to default to entry-level chunks using session YAML `entry_id`, with optional section granularity for narrower searches.
- Added control-plane guidance for sub-project runtime creation and parent/root coordination summaries without mirroring sub-project logs.
- Expanded operating-mode guidance for MCP history retrieval, unresolved history/current-file conflicts, public memory hygiene, and v2 guardrails.
- Clarified `uvx` one-off usage versus persistent `uv tool install`, project dependencies, and virtual-environment installs.

## 2.0.0 - 2026-05-25

- Promoted `.memory-seed/` as the canonical runtime directory with `agent-rules.md`, `project-bootstrap.md`, `index.md`, `policy.md`, lazy-loaded `skills/`, dated `sessions/`, and `archive/`.
- Added nearest-runtime discovery so nested sub-project folders can own isolated local memory state.
- Kept `.AGENTS/` as a code-level legacy fallback for older projects, but removed it from the v2 seed layout.
- Updated compact and MCP session extraction to use the discovered runtime boundary.
- Added default skill runbooks for security triage, data architecture, and local compilation.

## 1.6.1 - 2026-05-19

- Documented `uvx --from memory-seed` as the default way to run CLI and MCP commands without a global install.
- Clarified the difference between the Python package version and reusable control-plane version.
- Clarified that `memory-seed init` copies only Markdown seed files into target projects, not MCP server code or Python modules.

## 1.6.0 - 2026-05-19

- Added the local semantic cache core for heading-aware Markdown memory chunking, deterministic lexical ranking, optional embedding integration, and recency scoring.
- Added the lightweight stdio MCP server with `memory_search` and `memory_get_chunk` tools.
- Added `memory-seed-mcp-validate` for human-validatable search and fetch testing.
- Added support for timestamped session headings while keeping date-only session filenames.

## 1.5.3 - 2026-05-18

- Marked the project as beta maturity in package metadata.

## 1.5.2 - 2026-05-18

- Updated GitHub Actions workflow actions for Node.js 24 compatibility.

## 1.5.1 - 2026-05-18

- Prepared a patch release after the `1.5.0` PyPI release was already published.

## 1.5.0 - 2026-05-18

- Added the `memory-seed compact` command for summarizing recent session logs.
- Documented consolidation behavior and agent-led promotion of durable facts.

## Earlier

- Added reusable seed installation and update commands.
- Added project bootstrap instructions for generating `.AGENTS/index.md`, `.AGENTS/context.md`, `.AGENTS/style.md`, and dated session logs.
- Added doctor/version checks for reusable control-plane files.
