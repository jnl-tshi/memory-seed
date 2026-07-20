---
title: Test-suite protection-value audit
status: active
priority: P2
next_action: Audit test_memory_seed.py module by module (Keep/Consolidate/Replace/Move/Delete), starting with the MemorySeedTests class.
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
migration cases are folded into `MemorySeedTests`.

## Phase 1 — done, 2026-07-20

- Applied `@pytest.mark.integration` to the 92 tests measuring ≥0.5s (chosen by measured duration, not
  by "touches git" — many git-backed tests are fast and stayed in the default loop). Registered the
  marker in `pyproject.toml`. Fast loop (`pytest -m "not integration"`): 543 tests, 29s (was 135s, 4.6x).
  Default `pytest` unchanged — still runs all 635. Purely additive diff (164 insertions, 0 deletions).
  `Memory-Entry: mse_fh4sp1twn0w662jb`.
- Installed `pytest-cov`, measured coverage by component (table above).
- Established a 3-run flakiness baseline: 0 failures.

## Phase 2 — the actual cull (not started)

Work one module at a time. For each: state the behaviours it protects, map every test to one, mark
duplicates, consolidate, replace incident-specific cases with invariants where a systemic rule exists,
delete obsolete/implementation-detail tests, re-run, commit separately. Surface every
Keep/Consolidate/Replace/Move/Delete candidate with a protection-value score before removing anything —
no unilateral deletion.

Cull order (highest test count / runtime / duplication / maintenance pain first, contracts and
invariants last):

1. `MemorySeedTests` (179 of the 287 tests in `test_memory_seed.py`) — the largest, most mixed class.
   Natural byproduct: split into per-concern files as tests are read and classified (not as separate
   up-front busywork).
2. `CliHelpTests` (28 tests) — given the coverage finding above, likely needs *expansion* on real
   command paths as much as consolidation of help-text checks.
3. `McpMergeTests`, `HookMergeTests`, `SessionLogOrderingHookTests`, `RetrievalCheckPathTests`,
   `SessionStartContextHookTests`, `AgentSelectionTests` — remaining classes in the monolith.
4. Remaining files, smallest/fastest/highest-signal last (`test_session_schema.py`,
   `test_docs_check.py`, contract-shape tests).

### Deferred, scoped, not started

- **Dedupe the 4 independently hand-rolled `_git()` harness helpers** (`test_git_hooks.py`,
  `test_memory_seed.py`, `test_mcp_session_integrate.py`, `test_worktree_gc.py`). They differ in
  `check=True` vs `check=False` and a `timeout=60` — do this when inside those files for the cull, with
  full context on why each differs, not as a blind text merge.
- **Split `test_memory_seed.py`'s 8 classes into per-concern files** — folded into Phase 2 item 1 above.
