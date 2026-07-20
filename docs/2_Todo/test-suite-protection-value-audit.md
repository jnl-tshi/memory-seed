---
title: Test-suite protection-value audit
status: active
priority: P2
next_action: Phase 2c content cull, starting with test_links_check.py (Keep/Consolidate/Replace/Move/Delete per test).
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

## Phase 2b — harness dedup (not started)

`_git()` now lives in exactly 4 files: `test_git_hooks.py`, `test_mcp_session_integrate.py`,
`test_worktree_gc.py`, `test_session_fuse_and_merge.py` (was `test_memory_seed.py` before the split).
They differ in `check=True` vs `check=False` and a `timeout=60` — needs a real behavioral comparison
per file before unifying, not a blind text merge. The three small fixture helpers noted above are a
second, lower-risk dedup candidate for the same pass.

## Phase 2c — the actual content cull (not started)

Work one module at a time, now that each is a cohesive file instead of a slice of a monolith. For each:
state the behaviours it protects, map every test to one, mark duplicates, consolidate, replace
incident-specific cases with invariants where a systemic rule exists, delete obsolete/implementation-
detail tests, re-run, commit separately. Surface every Keep/Consolidate/Replace/Move/Delete candidate
with a protection-value score before removing anything — no unilateral deletion.

Cull order (highest test count / runtime / duplication / maintenance pain first, contracts and
invariants last):

1. `test_links_check.py` (44 tests) — the largest remaining single concern; good parametrization
   candidate given the volume.
2. `test_session_fuse_and_merge.py` (69 tests) — largest file, but this is the P1-bug-catching
   machinery; expect mostly Keep, look for genuine duplication only.
3. `test_project_lifecycle.py` (39 tests).
4. `test_cli_help.py` (28 tests) — given the coverage finding above (`cli.py` at 54%), likely needs
   *expansion* on real command paths as much as consolidation of help-text checks.
5. `test_mcp_merge.py`, `test_hook_merge.py`, `test_session_log_ordering_hook.py`,
   `test_retrieval_check_path.py`, `test_session_start_hook.py`, `test_agent_selection.py`,
   `test_session_layout_migration.py`, `test_core_misc.py`.
6. Remaining files, smallest/fastest/highest-signal last (`test_session_schema.py`,
   `test_docs_check.py`, contract-shape tests).
