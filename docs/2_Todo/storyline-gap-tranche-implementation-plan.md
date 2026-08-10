---
priority: P1
status: completed
next_action: "None — R5, R8, and R13 are reconciled from reviewed implementation evidence."
---

# Storyline gap tranche implementation plan

## Objective

Completed the three open findings in the living interaction-storylines review without weakening the
recorded safety contracts:

- R13: distinguish a genuine post-fuse commit failure from a timeout result returned after the merge
  commit already landed.
- R5: introduce a core, reconstructable corpus projection that can be reused across tool calls and
  checked by ESR while Markdown and sidecars remain authoritative.
- R8: add the approved read-only MCP twins that let an MCP-confined agent complete recall, sweep, and
  close workflows without crossing to the CLI.

## Global constraints

1. Source Markdown and sidecars remain authoritative. Every cache artifact is derived, disposable,
   schema-versioned, and reconstructable.
2. Any cache ambiguity, corruption, source conflict, history rewrite, incomplete delta, schema mismatch,
   or failed verification falls toward a full source reconstruction, never toward stale or partial data.
3. Cache publication is atomic. Concurrent writers coordinate with a bounded lease or fall back to an
   isolated reconstruction; no consumer observes a half-written projection.
4. The cache belongs to `memory_seed`, not `memory-trace`; core may reuse the Trace invariants without
   depending on the optional companion application.
5. Sidecars that affect a cached view are first-class freshness inputs. Raw and augmented views remain
   distinct where current behavior deliberately requires raw data.
6. ESR remains a read-only preflight. It may inspect and independently verify cache health, but it does
   not silently repair the persistent cache or use an unverified cache to certify itself.
7. A source write succeeds or fails independently of cache maintenance. The next consumer detects any
   mismatch and reconstructs from source.
8. R13 must not weaken the 30-second Git timeout, auto-abort genuine fuse refusals, discard genuine
   conflict state, or add raw-filesystem worktree cleanup.
9. New MCP writes are out of scope for R8. The read-only twins must not change the pinned MCP write-tool
   count or bypass existing governance.
10. Workers do not edit session memory, ADR ledgers, seed/control-plane files, dependency definitions,
    or lockfiles. Sol owns durable memory, integration, and final validation.

## Task 1 — Update the living gaps before implementation [COMPLETED]

Updated `docs/1_Inbox/agent-interaction-storylines-review.md` before implementation to preserve the
approved cache direction, source authority, fail-to-reconstruction rule, and ESR health boundary; the
final reconciliation now marks only the fully implemented R5, R8, and R13 findings resolved.

Allowed files:

- `docs/1_Inbox/agent-interaction-storylines-review.md`
- generated docs lane indexes only when required by `docs index`

Validation:

- `python -m memory_seed.cli docs check`
- `python -m memory_seed.cli docs index --check`
- `git diff --check`

## Task 2 — R13 merge-commit result reconciliation [COMPLETED]

Teach `session_merge_branch` to reconcile Git state after `git commit --no-edit` reports non-zero or
times out. It may classify the operation as committed only when repository evidence proves that a new
merge commit was created for this operation, includes the expected source tip, contains the expected
`Memory-Entry` trailers, and has no in-progress merge state. Proven success continues through the existing
safe source-worktree cleanup. Anything ambiguous preserves the current genuine-failure result and
inspectable merge state.

Allowed files:

- `memory_seed/core.py`
- `tests/test_session_fuse_and_merge.py`
- a new narrowly named test module only if the existing module is structurally unsuitable
- `CHANGELOG.md`

Required tests:

- A simulated timeout/non-zero result after a real merge commit is created reports committed success.
- The reconciled success path performs the existing safe cleanup classification.
- A genuine commit failure remains uncommitted and inspectable.
- A coincidental or malformed HEAD advance cannot be mistaken for this operation's merge.

## Task 3 — R5 reconstructable core corpus projection and ESR health [COMPLETED]

Build the smallest persistent core projection that eliminates repeated canonical corpus construction
without turning the cache into authority. It must support the canonical raw and sidecar-augmented corpus
views needed by `load_corpus`, key the artifact per resolved runtime/worktree, carry an explicit schema
version and complete source fingerprint, and reconstruct from source on every unprovable state. Share one
loaded snapshot through a tool invocation so ESR and append guards do not deserialize or rebuild the same
view repeatedly.

Add a read-only ESR `corpus_cache` report with at least: presence, schema status, source-current status,
health (`current|missing|stale|corrupt`), whether reconstruction is required, cached/source counts, and an
equivalence result. ESR must derive its verdict independently and fall back to live/in-memory source data
for its own integrity conclusions.

Allowed files:

- a new core cache module under `memory_seed/`
- `memory_seed/retrieval.py`
- `memory_seed/core.py` only for dependency injection/invalidation seams required by the snapshot
- `memory_seed/esr.py`
- `memory_seed/cli.py` only for an explicit cache inspection/rebuild surface when required
- focused cache, ESR, corpus-read-path, and append tests
- `CHANGELOG.md`

Required tests and measurements:

- Cold reconstruction is byte/field equivalent to the uncached canonical reader for entry, decision,
  and section granularities.
- Warm reuse performs no source reconstruction.
- Session, link-sidecar, and topic-sidecar changes invalidate the relevant views.
- Corrupt cache, schema mismatch, history rewrite, no-git mode, and concurrent rebuild contention all
  fail toward a full or isolated source reconstruction.
- ESR reports each health state without mutating the persistent artifact.
- Before/after timings and corpus-build counts are recorded for ESR and session append; optimization is
  accepted only when correctness tests stay exact.

## Task 4 — R8 approved read-only MCP twins [COMPLETED]

Add read-only MCP tools for the existing canonical operations:

- lifecycle chain view (`links chain` equivalent),
- lifecycle gap audit (`link audit` equivalent),
- ESR structured report (`esr --json` equivalent).

The tools call shared core functions rather than duplicating algorithms, carry existing evidence fields,
use stable schemas, perform no writes, and leave graph-diff snapshots plus ADR head-changing writes out of
scope.

Allowed files:

- `memory_seed/mcp_server.py`
- shared extraction functions in `memory_seed/core.py`, `memory_seed/retrieval.py`, or `memory_seed/esr.py`
  only when needed to avoid CLI/MCP duplication
- focused MCP schema/parity tests
- `README.md` and `CHANGELOG.md`

Required tests:

- MCP payloads are equivalent to their CLI/core counterparts on the same fixture.
- The registry count and exact write-tool count are intentionally updated/preserved as appropriate.
- All three tools are demonstrably read-only.

## Task 5 — Final storyline reconciliation [COMPLETED]

The living review and this plan are reconciled from implementation evidence. R5, R8, and R13 are
fully discharged; no residual R-item is implied. R1/R2 remain refuted and R12 remains stale rather
than being recast as implemented.

## Completion evidence

- **R13:** commits `2fcff569` and `f89c5e52` reconcile a failed or timed-out commit report only on
  the exact pre-commit/source-tip parent vector, final canonical `Memory-Entry` trailer equality,
  and cleared `MERGE_HEAD`. The genuine-failure path stays inspectable; proven success uses the
  existing safe cleanup. The 65 full merge/fuse tests passed; closure review: PASS.
- **R5:** commits `b6c391e4`, `0a2b2723`, `b9068bb0`, `0118a16e`, `d37aa776`, and `1baa3c7e`
  deliver the reconstructable external projection, stable runtime/worktree + HEAD key, six views,
  manifest/fingerprint, schema/integrity checks, atomic bounded-lease publication, isolated
  fallbacks, and one-invocation snapshot reuse. ESR remains independently read-only and source writes
  do not depend on cache maintenance. 342 related tests passed; closure review: PASS.
- **R8:** commits `35036ffb` and `2cab536b` add `memory_links_chain`, `memory_link_audit`, and
  `memory_esr`, using shared canonical serializers/functions. The MCP registry is 23 tools and its
  exact four mutators are unchanged. Parity, current/missing/corrupt external-cache, and read-only
  tests passed (190 focused); closure review: PASS. Graph-diff and all MCP write parity remain out of
  scope.

## Validation and known unrelated debts

- Full integrated suite: 1476 passed; frozen ADR fixture SHA drift is an unrelated validation debt,
  not an R5/R8/R13 failure.
- The Windows Git shallow-clone signal-pipe condition is the other known unrelated validation debt.
- Documentation checks, index verification, link/reference checks, and `git diff --check` are run
  for this reconciliation; indexes are regenerated only if their check requires it.
