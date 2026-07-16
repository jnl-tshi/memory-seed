---
memory-system-version: 2.18
spec_binding: candidate
tags:
  - memory-seed
  - spec
  - architecture
  - projection
  - performance
---

# Derived Read-Model / Projection Contract  *(draft — candidate)*

**Status:** Candidate spec (`3_Spec/draft/`) - not yet binding. Memory Trace now implements the Phase 1
Markdown-to-SQLite projection: a schema version, Git build watermark, cheap warm path, atomic build/swap,
and read-path memoisation. The contract remains a candidate because the git-rooted historical-integrity and
no-git degradation guarantees, progressive loading, and cross-consumer adoption are not yet accepted. It is
the Platform-layer contract that makes
[`CONSTITUTION.md`](../../CONSTITUTION.md) **Invariant #6** ("Markdown is the single source of truth; every
other store is a derived projection") concrete. Implementation plan:
[`2_Todo/derived-projection-implementation-plan.md`](../../2_Todo/derived-projection-implementation-plan.md).

## Purpose

Memory Trace (and any consumer) must be fast on large histories, and most of the compute — graph layout,
Trace processing, search, lineage walks — lives in a **derived store** (a local DB such as SQLite/DuckDB
with optional full-text/vector indexes). This contract fixes how that store relates to the Markdown source
of truth so performance never costs correctness.

## Model

**Markdown is the append-only log / source of truth. The DB is a materialized read-model projection over
it.** Reads are served from the projection (fast); writes land in Markdown (cheap: append a file/commit).
Authority is one-directional — **Markdown → projection, never the reverse.** (Same shape as a git index over
objects, or a search index over documents.)

## Scope

**Normative** for the settled local, single-writer case. **Out of scope (candidate):** the hosted /
collaborative multi-writer reconciliation path — that depends on the *which-commercial-tier* decision left
open in `CONSTITUTION.md` §10 and must not be speculatively specified here.

## Guarantees (normative)

- **G1 — One-directional authority.** Nothing ever reads the projection as truth or writes to it as a
  primary store. Every value in it is reconstructable from Markdown.
- **G2 — Rebuildable & disposable.** The projection can be deleted and fully rebuilt from Markdown at any
  time with no observable change to read results. It holds no state that isn't in Markdown.
- **G3 — Markdown-first writes (write-through).** A write is not durable until it is in Markdown; the
  projection is then updated *from* that write. The projection MAY buffer a write for UI responsiveness, but
  it is never the only place the write lives, and recovery is always from Markdown.
- **G4 — Atomic build & swap.** A (re)build writes to a temporary store and is swapped in atomically; a
  half-built projection is never served. A `build-in-progress` marker lets a crashed build self-heal
  (discard + rebuild) on the next start.
- **G5 — Cheap warm start (no whole-corpus scan).** Startup does **not** hash or re-read the whole corpus.
  It computes the delta since the last build from git — `git diff --name-only <watermark>..HEAD` plus
  dirty working-tree files (`git status`) — and ingests only added/changed/deleted files. The watermark is
  the git commit the projection was last built at. Cold start (no projection) does one full build.
- **G6 — Git-rooted integrity, not projection-rooted.** Whether a *historical* entry was mutated or deleted
  is answered from **git history**, never from the projection (which is disposable and would launder the
  evidence on rebuild). The signal: an entry whose file changed in a commit *after* its introducing
  `Memory-Entry:` commit beyond a pure append — or is dirty in the working tree — is an **append-only
  violation** (Invariant #2), surfaced by `links check` / `esr`. Git is also the recovery path (revert).
  Note: the warm-start delta (G5 — a *freshness* question, "what changed since the last build") and this
  integrity check (an *append-only* question, "did a historical file change after its introducing commit")
  are two **distinct** reads of git over the same files; the cheap ingest diff does not discharge the
  integrity check, which must compare each changed file against its introducing commit, not merely note that
  it appeared in the range.
- **G7 — Honest degradation without git.** With no git repository, the projection still self-heals to
  current Markdown, but the system **cannot prove the past was not altered** and must say so — it offers no
  historical-tamper guarantee in that mode. A content-hash manifest is permitted only as a warm-process
  optimization and a best-effort no-git fallback; it is **never** the durable integrity baseline (a
  disposable store cannot be its own oracle).

## Startup & load on large histories

1. Persist the projection across runs; store the build watermark (last-built git commit) with it.
2. **Warm start:** git-diff delta (G5) → ingest only the delta. O(changes), not O(corpus).
3. **Cold / very large:** build in the **background and serve progressively** (newest-first / lazy
   per-view, with a progress indicator — reuse the existing worktree-switch loader), then atomic-swap (G4)
   when complete. The UI is usable before the full projection is ready.
4. **Schema-version bump** (projection code changed) → full rebuild; otherwise reuse.

## Out-of-band edits to historical Markdown (even incorrect / accidental)

The two jobs are complementary and must not be conflated:

- **Projection — reflect.** If a historical file changed, re-project it; the projection always mirrors
  *current* Markdown (Markdown is truth). It protects nothing and holds nothing old.
- **Integrity — police.** The git-rooted check (G6) flags the mutation/deletion as an append-only violation
  and points at the offending commit / dirty file. **Recovery is git** (`git revert` / checkout) — the
  projection needs to store no prior version. Deletion of a historical entry is the same class as mutation;
  handle both through this one rule. By design (G2), a deletion leaves **no projection-visible remnant** — a
  rebuild from current Markdown simply omits it, and the integrity flag + git *are* the record; implementers
  must **not** add a tombstone table, which would reintroduce non-rebuildable state. Without git (G7), the
  projection self-heals but the violation cannot be proven — stated, not hidden.

## Already present (build on, don't greenfield)

The Memory Trace **SQLite projection** now provides the Phase 1 base: Markdown-source rebuilds, a versioned
schema, Git-watermark warm starts, atomic replacement, and read-path memoisation. **`Memory-Entry:` trailers**
bind entries to commits; **`links check` / `esr`** are the current integrity surface; **git** is the durable
ledger + recovery; **per-user session files + `session merge-branch`/fuse** are Markdown-native
write-resolution primitives. G6/G7 and progressive loading remain work to validate rather than guarantees to
claim.
