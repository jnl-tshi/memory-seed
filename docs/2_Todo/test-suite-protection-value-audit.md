---
title: Test-suite protection-value audit
status: active
priority: P2
next_action: Phase 2c content cull is complete (all 635 original tests + the 18-file remainder reviewed). Awaiting JNL's review of the "Findings awaiting a review checkpoint" section below before any structural split or deletion proceeds.
blocked_by: []
---

# Test-Suite Protection-Value Audit

Status: **ACTIVE**. JNL requested an audit of the 635-test suite scoped by protection value, not
headcount: freeze uncontrolled growth, measure before culling, classify by layer, then work module by
module assigning every test one of Keep / Consolidate / Replace-with-invariant / Move / Delete.

## Rule for new tests going forward

Every new regression test must answer: **what behaviour becomes unprotected if this test does not
exist?** Check first whether a bug should be covered by an existing test, another case in a
parametrized test, a broader invariant, or a contract/integration test — before adding a new one.

## Measurements (2026-07-20)

| Measurement | Finding |
|---|---|
| Total execution time | ~135–154s across 5 consecutive full runs (635 tests) |
| Slowest tests | Top 40 are all real-git-subprocess `session_fuse`/`merge_branch`/`prepare_pr`/`open_pr` workflows |
| Tests per module | `test_memory_seed.py` = 287/635 (45%), ~105/135s (78%) of wall time, across 8 unrelated `unittest.TestCase` classes in one 6,400-line file |
| Flaky tests | **0 failures across 3 consecutive full runs** (154s/149s/147s) after the integration-marker pass. Not a rigorous flakiness study — a documented starting baseline, since no historical run data existed to derive one retroactively. Re-run this check periodically and record results here. |
| Coverage by component | `pytest-cov` installed 2026-07-20 (not yet added as a project dependency — installed locally for this audit). Full suite: **81%** (8577 stmts, 1627 missed). Fast loop only (`-m "not integration"`): **70%** — the integration tier carries ~983 statements of real, non-redundant coverage, not filler. |

### Coverage by module (full suite)

| Module | Stmts | Cover | Note |
|---|---:|---:|---|
| `cli.py` | 1237 | **54%** | Largest gap by far. `CliHelpTests` (28 tests) is mostly `--help` output checks, not command execution — e.g. every new `planned_link_sidecars` CLI print line added 2026-07-20 executes its `for` header but never its body in any test (list always empty), so the actual print text is unverified by any test. |
| `processes.py` | 471 | 67% | Second-largest gap |
| `mcp_validate.py` | 29 | 69% | Small file, meaningfully under-tested |
| `ranking_ab.py` | 236 | 79% | |
| `worktree_gc.py` | 182 | 87% | |
| `esr.py` | 198 | 85% | |
| `situate.py` | 156 | 85% | |
| `docs_check.py` | 125 | 86% | |
| `core.py` | 3836 | 86% | Healthy % but largest absolute miss count (555 lines) given file size |
| `mcp_server.py` | 197 | 86% | |
| `text_files.py` | 280 | 89% | |
| `semantic_cache.py` | 762 | 90% | |
| `topics.py` | 263 | 91% | |
| `retrieval.py` | 391 | 92% | |
| `quality.py` | 106 | 93% | |
| `docs_index.py` | 108 | 94% | |
| `__init__.py` | 2 | 100% | Trivial |

**Reading this straight:** the suite's problem is not blanket over-coverage. `cli.py` is genuinely
under-tested despite CLI-adjacent tests existing in volume — the *shape* of those tests (help-text
checks) doesn't match the *claim* their name makes (CLI coverage). That's a finding for the cull to
act on directly: some `CliHelpTests` cases may be Keep-worthy but mislabeled/incomplete, not
duplicative.

### Layer classification (by module)

| Module | Tests | Runtime (>0.05s tests) | Layer | Integration-marked |
|---|---:|---:|---|---:|
| `test_memory_seed.py` | 287 | 105.3s | mixed (8 unrelated classes) | 57/287 |
| `test_worktree_gc.py` | 18 | 11.4s | integration | 15/18 |
| `test_mcp_session_integrate.py` | 5 | 8.2s | integration | 5/5 (all) |
| `test_git_hooks.py` | 11 | 5.4s | integration | 8/11 |
| `test_mcp_server.py` | 42 | 3.7s | contract | 4/42 |
| `test_situate.py` | 7 | 1.8s | unit/integration mix | 1/7 |
| `test_esr.py` | 9 | 1.2s | unit | 1/9 |
| `test_processes.py` | 22 | 0.8s | unit | 1/22 |
| `test_quality.py` | 9 | 0.5s | unit | 0 |
| `test_text_files.py` | 10 | 0.4s | unit | 0 |
| `test_retrieval.py` | 22 | 0.4s | unit | 0 |
| `test_semantic_cache.py` | 50 | 0.3s | unit | 0 |
| `test_link_audit.py` | 20 | 0.3s | unit | 0 |
| `test_topics_suggest.py` | 12 | 0.2s | unit | 0 |
| `test_mcp_session_append.py` | 21 | 0.2s | unit | 0 |
| `test_docs_index.py` | 9 | 0.1s | unit | 0 |
| `test_session_append.py` | 12 | 0.1s | unit | 0 |
| `test_session_reorder.py` | 13 | 0.1s | unit | 0 |
| `test_docs_check.py` | 17 | 0.1s | unit | 0 |
| `test_topics.py` | 8 | <0.1s | unit | 0 |
| `test_session_schema.py` | 19 | <0.1s | unit | 0 |
| `test_ranking_ab.py` | 10 | <0.1s | unit | 0 |
| `test_mcp_validation.py` | 2 | <0.1s | unit | 0 |

No true end-to-end or compatibility/migration tier exists as a distinct concern today; session-layout
migration cases are folded into `test_session_layout_migration.py` (see Phase 2 below).

## Phase 1 — done, 2026-07-20

- Applied `@pytest.mark.integration` to the 92 tests measuring ≥0.5s (chosen by measured duration, not
  by "touches git" — many git-backed tests are fast and stayed in the default loop). Registered the
  marker in `pyproject.toml`. Fast loop (`pytest -m "not integration"`): 543 tests, 29s (was 135s, 4.6x).
  Default `pytest` unchanged — still runs all 635. Purely additive diff (164 insertions, 0 deletions).
  `Memory-Entry: mse_fh4sp1twn0w662jb`.
- Installed `pytest-cov`, measured coverage by component (table above).
- Established a 3-run flakiness baseline: 0 failures.

## Phase 2a — structural split, done 2026-07-20

`test_memory_seed.py` (6,533 lines, 287 tests across 8 unrelated classes) is retired. Split by an
AST-driven script — not by hand — so every test's exact source (including `@pytest.mark.integration`
decorators) was verified relocated exactly once before the original was deleted:

- The 7 already-cohesive classes moved to their own files verbatim: `test_hook_merge.py`,
  `test_session_log_ordering_hook.py`, `test_mcp_merge.py`, `test_retrieval_check_path.py`,
  `test_cli_help.py`, `test_session_start_hook.py`, `test_agent_selection.py`.
- `MemorySeedTests` (179 tests, the real grab-bag) was further split by concern, classified by a
  call-graph analysis of each test (which core API / helper methods it actually calls), not by name
  prefix guessing:
  - `test_session_fuse_and_merge.py` — `SessionFuseAndMergeTests`, 69 tests (fuse/merge-branch/
    prepare-pr/open-pr + the `-merge` attribute + false-anchor-conflict tests + the
    `_is_recognized_session_tree_path` unit test)
  - `test_links_check.py` — `LinksCheckTests`, 44 tests
  - `test_project_lifecycle.py` — `ProjectLifecycleTests`, 39 tests (init/update/doctor/skill/seed/
    version)
  - `test_session_layout_migration.py` — `SessionLayoutMigrationTests`, 9 tests
  - `test_core_misc.py` — `CoreMiscTests`, 18 tests (entry-format/id, commit provenance,
    `resolve_runtime`, `compact_sessions`)

**Verification, not assertion:** collected test-name sets before/after were asserted equal (179 tests,
each exactly once) prior to deleting the original; `pytest --collect-only` confirmed exactly 635 both
before and after; the full suite still reports **635 passed, 14 subtests passed**, byte-for-byte the
same tally as before the split; the fast loop still reports **543 passed, 92 deselected** (all 57
integration markers that lived in `MemorySeedTests` landed correctly — 46 in
`test_session_fuse_and_merge.py`, 7 in `test_cli_help.py`, 3 in `test_mcp_merge.py`, 1 in
`test_links_check.py`).

**Known, accepted trade-off:** three small pure-Python fixture helpers (`_per_user_session`,
`_write_participants`, `_git_repo_with_commit`) are now duplicated across 2-3 of the new files rather
than shared, since a true shared module wasn't attempted in this pass (see Phase 2b). This is
controlled, verified-identical duplication of small leaf helpers, not the kind of duplication the audit
is trying to eliminate.

## Phase 2b — harness dedup, done 2026-07-20

`_git()` lived in 4 files, each hand-rolling the same `subprocess.run(["git", "-C", ...])` call with
different `check`/`timeout` defaults: `check=True` (`test_git_hooks.py`, `test_session_fuse_and_merge.py`),
`check=False` explicit (`test_mcp_session_integrate.py`), and no `check` passed at all plus
`timeout=60` (`test_worktree_gc.py`). Read each exact implementation and every call site before
touching anything — the differences were real, not incidental drift, so a single shared default would
have silently changed behavior for at least one file.

Added `tests/_git_helpers.py` (leading underscore keeps it out of pytest's `test_*.py` collection) with
one `run_git(cwd, *args, check=False, timeout=None)`. Each file's own `_git()` now delegates to it,
passing its own historical `check`/`timeout` explicitly — every existing call site (18 + 23 + 28 + 124 =
193 of them) needed zero changes, since each file's `_git(...)` signature and behavior are unchanged
from the caller's perspective. Removed `import subprocess` from `test_mcp_session_integrate.py` and
`test_worktree_gc.py`, where it was only ever used inside `_git()`; kept it in the other two files,
which also call `subprocess.run` directly elsewhere. Fixed a stale docstring reference in
`test_mcp_session_integrate.py` pointing at the now-retired `test_memory_seed.py`.

**Not done in this pass:** the three small pure-Python fixture helpers noted above
(`_per_user_session`, `_write_participants`, `_git_repo_with_commit`) remain duplicated across 2-3
files. Lower risk than the subprocess helper was, but still needs the same read-every-caller
discipline before merging, not a blind cross-file diff.

**Verified:** the 4 files' own tests (103 tests) pass; full suite still 635 passed / 14 subtests
(unchanged); `docs check`/`links check` clean. Diff is small and net-negative: 9 insertions, 16
deletions across the 4 files plus one new 20-line shared module.

## Phase 2c — the actual content cull (in progress)

Work one module at a time, now that each is a cohesive file instead of a slice of a monolith. For each:
state the behaviours it protects, map every test to one, mark duplicates, consolidate, replace
incident-specific cases with invariants where a systemic rule exists, re-run, commit separately.

**Authorization split, agreed 2026-07-20:** Move and Consolidate proceed autonomously per file — a
green suite after either is real evidence the behaviour survived. Delete does not: a green suite after
a deletion proves nothing (the deleted test can't fail, and whatever it caught is now unguarded), so
deletion candidates are *accumulated* below with a protection-value note and surfaced together at one
checkpoint before anything is actually removed. "Reviewed this file, 0 changes, everything here is a
distinct contract" is a valid, honest outcome — the goal is not manufacturing churn to show motion.

Cull order (highest test count / runtime / duplication / maintenance pain first, contracts and
invariants last):

1. `test_links_check.py` (44 tests) — **done, 2026-07-20**, see below.
2. `test_session_fuse_and_merge.py` (69 tests) — **done, 2026-07-20**, see below.
3. `test_project_lifecycle.py` (39 tests) — **done, 2026-07-20**, see below.
4. `test_cli_help.py` (28 tests) — **done, 2026-07-20**, see below.
5. `test_mcp_merge.py`, `test_hook_merge.py`, `test_session_log_ordering_hook.py`,
   `test_retrieval_check_path.py`, `test_session_start_hook.py`, `test_agent_selection.py`,
   `test_session_layout_migration.py`, `test_core_misc.py` — **done, 2026-07-20**, see below.
6. The remaining ~18 original unit-test files — **done, 2026-07-20**, see below.

### test_links_check.py — done, 2026-07-20

Read all 44 tests against what `check_session_links` actually validates: it has ~20 distinct issue
kinds (malformed YAML/format, duplicate id/hash, dangling/postdating/self/cycle variants of
`supersedes` and `evolves` each, sidecar-specific stub/orphan/date-mismatch/malformed cases, continuity
block shapes, git-environment-dependent commit-hash checks, legacy-layout compatibility). Each test
maps to exactly one distinct issue kind or acceptance case — this is one-test-per-contract-shape
coverage for a validator, which is what a validator's test suite *should* look like, not duplication.
**Verdict: 42 Keep, 2 Move, 0 Consolidate, 0 Delete.**

- **Move (2):** `test_migrate_sessions_layout_apply_splits_entries_and_backs_up_source` and
  `test_migrate_sessions_month_layout_apply_moves_sources_and_backs_up` called
  `migrate_session_layout`/`migrate_session_month_layout` as their subject under test, using
  `check_session_links(cwd=cwd).ok` only as a closing sanity assertion — a classification artifact
  from the Phase 2a AST split (its priority order favored "calls `check_session_links`" over "calls
  `migrate_session_*`" for these two). Moved to `test_session_layout_migration.py`, which already had
  byte-identical `_write_participants`/`_write_flat_session`/`_write_old_diagram_sidecar` fixture
  helpers, so no new duplication was introduced. Their now-dead copies of those three helpers (plus the
  now-unused `migrate_session_*` imports) were removed from `test_links_check.py`. Net effect: one of
  the three Phase 2a-noted duplicated helpers (`_write_participants`) lost one of its four copies
  (test_links_check.py's), incidentally.
- **Consolidation considered and rejected:** the `supersedes`/`evolves` dangling/postdating/
  backward-accepted pairs that exist in both plain-YAML and sidecar form look like a parametrize
  candidate on first glance, but (a) YAML-edge and sidecar-edge extraction are genuinely different code
  paths in `core.py`, so merging them would reduce diagnostic precision on which path broke (the
  rubric's own "diagnostic quality" axis), and (b) the matrix isn't even square — `evolves` has no
  sidecar-dangling/postdating variants, only `supersedes` does — which is itself a signal the two axes
  aren't as parallel as they look. Left as distinct tests.
- Verified: 635 → 635 collected (count-neutral, a Move not a deletion); both touched files' full suites
  (`test_links_check.py` 42, `test_session_layout_migration.py` 11) pass, 53/53.

### test_session_fuse_and_merge.py — done, 2026-07-20

Read all 69 tests. **Verdict: 69 Keep, 0 Move, 0 Consolidate, 0 Delete.** This is the file the 2026-07-20
P1 sidecar-loss fix (this session, tasks #1-8 above) added its regression coverage to, plus the
`-merge` gitattribute proof suite and the general fuse/merge-branch/prepare-pr/open-pr machinery.
Consistently high-quality: nearly every test carries an inline comment naming the exact incident or
mechanism it guards (the `-merge` attribute quartet is a deliberate mechanism/regression/control/outcome
proof structure, not repetition; the link-sidecar tests are the literal regression proof for this
session's own P1 fix). No true duplicates found. Considered and rejected the same YAML/sidecar-pair
consolidation temptation as file 1, for the same reason (distinct extraction paths).

**Structural finding, surfaced not actioned:** despite its name, ~28 of the 69 tests are not fuse/merge
tests at all — they cover five distinct other concerns that happen to share the file's real-git fixture
harness: `integration_mode` read/suggest/write (5), `decision_density`/`future_timestamp` advisories (6,
see note below), `branch_status` (3), `worktree_guard` (4), `session_target` routing (8), plus
`update_preserves_declared_integration_mode` and `_merge_routing_stanza` (2). Checked with advisor
before acting: this is **not** the same class of change as the file-1 migrate-tests move — that
relocated 2 tests into a file that already existed with identical helpers, this would mean inventing
5-6 new files, re-opening the Phase 2a structural split JNL already approved. Recommend a targeted
further split by concern; **not done autonomously, needs a go-ahead.**

Sub-finding on the 6 `decision_density`/`future_timestamp` tests specifically: on inspection they split
further — 3 call `check_session_links(cwd=...)` and assert on its `entry-decision-density`/
`entry-future-timestamp` issue kinds (arguably belong in `test_links_check.py`, just closed), and 3 call
the underlying advisory/gate functions (`check_entry_timestamp_advisories`, `entry_body_advisories`,
`entry_body_format_issues`) directly, one of which explicitly documents the write-time gate
`session_append_entry` uses (arguably belongs in `test_session_append.py`). Not a single clean
destination, so left in place pending the same go-ahead rather than guessing.

Verified: no files changed in this file's review, so nothing to re-run — confirmed by inspection only.

### test_project_lifecycle.py — done, 2026-07-20

Read all 39 tests. **Verdict: 39 Keep, 0 Move, 0 Consolidate, 0 Delete.** Covers `init_project`/
`update_project` (foreign-vs-owned routing file handling, force/backup/archive semantics, version
comparison, idempotency, dry-run), `doctor` (missing/mismatched files, bootstrap-vs-control-plane
health), skills (profiles, add/remove, status), and control-plane packaging invariants (seed manifest,
`pyproject.toml` package-data parity, per-agent command deployment). Each test targets a genuinely
distinct edge case in what is a real, non-trivial config-management system (owned vs. foreign files,
force vs. no-force, newer-vs-older version handling) — no duplication found.

Two tests worth naming even though both are Keep: `test_repo_root_control_plane_files_match_version`
explicitly documents that it pins a regression that "happened in 2.2.3 / 2.3.0" (the version-bump sed
missing this repo's own root routing files) — a real historical-bug test that's earned its place because
the systemic fix (`doctor()`) only catches it at runtime, not at release time. `test_seed_files_use_memory_seed_runtime`
is a ~40-line exact-manifest snapshot of every seed file destination — higher maintenance cost than
most tests here (any new seed file requires updating it), but it protects the actual packaging list, so
left as Keep rather than flagged for replacement.

### test_cli_help.py — done, 2026-07-20

Read all 28 tests. **The file's own measurements-phase description turned out to overstate the
problem:** re-reading against real behaviour, only 2 of the 28 tests (`test_help_command_lists_all_commands`,
`test_no_command_prints_help`) are pure `--help`-text checks — the other 26 dispatch real subcommands
(`skills`, `init`, `branch status`, `worktree guard`/`status`, `session integrate`, `user`, `migrate`,
`session fuse`/`merge-branch`) through `cli.main()` and assert on real stdout/JSON/exit codes/file
side-effects. No duplication found across the 28; each targets a distinct command, flag combination, or
error path (interactive-prompt vs. non-interactive, TTY-mocked opt-out, unreadable-config refusal,
newer-vs-declared integration mode, etc.).

The measurements-phase note's specific example, though, held up under verification: no fixture in this
file ever produces a non-empty `planned_link_sidecars`, so the CLI's "Would import link sidecar: ..."
print line (added this session, task #6 above, across 6 call sites in `cli.py`) had never actually
executed in any test — a real coverage gap in code from earlier in this same session. **Added
`test_session_fuse_cli_dry_run_reports_link_sidecar_import`**, driving a real branch-side link sidecar
through `session fuse --branch` via the CLI. Verified the new test actually catches the gap by
temporarily replacing the print statement with `pass` — the test failed with a clear diff, confirming
it isn't a vacuous assertion; reverted before committing.

**Verdict: 28 Keep, 1 new (Expand), 0 Move, 0 Consolidate, 0 Delete.** Treated as an autonomous action
like Move/Consolidate, not gated behind the review checkpoint: a new test either passes against real
behaviour or fails, so a green suite is real evidence here, unlike a deletion.

Verified: `pytest tests/test_cli_help.py` — 29/29 passed (was 28).

### The 8 smaller Phase 2a split files — done, 2026-07-20

Read all 109 tests across `test_mcp_merge.py` (21), `test_hook_merge.py` (12),
`test_session_log_ordering_hook.py` (14), `test_retrieval_check_path.py` (2),
`test_session_start_hook.py` (16), `test_agent_selection.py` (15),
`test_session_layout_migration.py` (11, including the 2 tests moved in here from file 1),
`test_core_misc.py` (18). **Verdict: 109 Keep, 0 Move, 0 Consolidate, 0 Delete.** These were the 7
already-cohesive classes Phase 2a moved verbatim plus the concern-split leftovers, and it shows: each
file covers one real subsystem (per-agent hook/MCP JSON-merge idempotency and foreign-content
preservation, the two standalone hook scripts' stateful behaviour, agent selection/add/remove,
session-layout migration, and a grab-bag of small core-function unit tests), and every test within a
file targets a distinct case. The many superficially-similar per-agent tests in `test_mcp_merge.py`/
`test_hook_merge.py` (Claude/Cursor/Gemini/Codex/Copilot/VSCode) are not duplication — each agent has
its own JSON/TOML shape and its own merge function under test, so each earns its own regression cover.

Verified: no files changed, so nothing to re-run.

### The remaining ~18 original unit-test files — done, 2026-07-20

Read all 314 tests across `test_semantic_cache.py` (50), `test_mcp_server.py` (42),
`test_retrieval.py` (22), `test_processes.py` (22), `test_link_audit.py` (20), `test_mcp_session_append.py`
(21), `test_session_schema.py` (19), `test_docs_check.py` (17), `test_session_reorder.py` (13),
`test_topics_suggest.py` (12), `test_session_append.py` (12), `test_ranking_ab.py` (10),
`test_text_files.py` (10), `test_docs_index.py` (9), `test_esr.py` (9), `test_quality.py` (9),
`test_topics.py` (8), `test_situate.py` (7), `test_mcp_validation.py` (2). These were never touched by
the Phase 2a structural split, so — per the advisor guidance recorded above — the earlier files'
all-Keep streak was **not** treated as predictive; each was read fresh.

**Verdict: 311 Keep, 3 Expand, 0 Move, 0 Consolidate, 0 Delete.** This is a mature, carefully-written
test suite: nearly every test carries an explicit rationale (docstring or inline comment) naming the
exact behaviour or historical incident it guards, and cross-file review found no genuine duplication
anywhere in the ~635-test corpus — the file-1 and file-2 findings (the 2 migrated tests, the
structural-split recommendation) were the only real issues in the whole suite.

- **Expand (`test_processes.py`, +3 tests):** `iter_system_processes()` prefers `psutil` when
  importable, but no test exercised that branch or `_iter_psutil_processes()` itself — every existing
  test either bypassed process listing entirely (`find_managed_processes(snapshots=...)`) or mocked the
  platform-specific subprocess fallback. psutil is optional and not installed in this environment, so
  the "available" path was faked via `sys.modules`, mirroring the `memory_trace` fake already used in
  `test_cli_help.py`. Verified the new tests catch a real break (temporarily corrupted the `pid` field
  translation, confirmed the test failed, reverted) before committing. Coverage on `processes.py`: 67%
  → 71%.
- **Considered and declined an Expand:** `test_mcp_validation.py`'s coverage gap (69%, lines 65-83) is
  `mcp_validate.py`'s `main()` — thin `argparse` + a call into `build_validation_report` (already
  tested) + a `print`. No independent logic to protect; a test here would mostly exercise `argparse`
  itself. Left alone rather than chasing the percentage.
- **`test_session_schema.py`** is a deliberate living-contract file pinning specific control-plane doc
  phrases (agent-rules.md, skills, README, CHANGELOG) plus seed/live parity — per prior guidance
  (`feedback_multi_decision_entry_format`-adjacent project memory), these are intentionally fragile-by-
  design pins; additions are safe, removals/rewordings are not. Left untouched.

Verified: `pytest tests/test_processes.py` 25/25 passed; full `pytest tests` 639 passed (was 636), 14
subtests passed.

## Findings awaiting a review checkpoint (not yet actioned)

Structural-split and Delete candidates accumulate here as later files are culled, and are reviewed with
JNL as one batch before anything in this section is acted on — see the authorization split above.
**Phase 2c is now complete; this is the full and final list.**

1. **Structural split of `test_session_fuse_and_merge.py`.** ~28 of its 69 tests cover 5 concerns
   unrelated to fuse/merge (`integration_mode` read/suggest/write, `decision_density`/`future_timestamp`
   advisories, `branch_status`, `worktree_guard`, `session_target`) that share the file's real-git
   fixture harness. Recommend carving these into their own file(s), but this reopens the Phase 2a
   structural split JNL already approved, so it needs a go/no-go rather than proceeding on the same
   autonomous footing as the file-1 migrate-tests move.
   - Sub-question: the 6 `decision_density`/`future_timestamp` tests don't have one clean destination
     even within that split — 3 call `check_session_links` directly (arguably belong with
     `test_links_check.py`), 3 call the underlying advisory/gate functions used by
     `session_append_entry` (arguably belong with `test_session_append.py`). Needs a decision before
     any move happens.

**No Delete candidates were found anywhere in the 635-test suite.** Every test mapped to a distinct,
currently-protected behaviour; the only content-level issues across the whole audit were the 2
misclassified migration tests in file 1 (already moved) and the one coverage gap already closed above.
The suite's actual problem, confirmed by this full pass, was organizational (one 6,533-line grab-bag
file), not volume or duplication — which Phase 2a already fixed. 635 → 639 is the current test count
after this session's one Move and two Expands (`test_cli_help.py` +1, `test_processes.py` +3, net of no
deletions).
