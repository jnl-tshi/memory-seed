---
memory-system-version: 2.18
tags:
  - memory-seed
  - proposal
  - retrieval
  - graph
  - lifecycle
---

# Lifecycle-link authoring assist (`link audit --apply` sidecar scaffold + advisory gap warning)

Status: **PROPOSED** (2026-07-13). Inbox — spun out of a user question about the lifecycle-link update
process ("is there a hook that runs in background?").
Priority: P2 — retrieval/graph quality; removes authoring friction, touches no ranking behavior.
Source: User 2026-07-13, after confirming the update flow is deliberately manual.

## Problem

The lifecycle-link update flow is *correct* but has mechanical friction at the exact moment it matters
(session end). `memory-seed link audit` reports the gaps and prints a classification litmus, then
**writes nothing** — the author must hand-author the sidecar: the right path
(`.memory-seed/sessions/links/YYYY-MM/YYYY-MM-DD.md`), the frontmatter, a per-entry `## heading` +
```yaml``` block, the correct `entry_id`, and chronological placement. That hand-authoring is exactly
where edges get **dropped or malformed** — the same failure mode the DRAFT-format lint just closed for
session *entries*. An edge you don't record is invisible to ranking (now that supersession damping is
on by default), the Trail, and `links check`.

## Current behavior (grounded)

- `link audit [--for <id>] [--date <date>]` is **read-only**: candidates are older entries sharing
  >=1 `F:` file OR >=1 topic (deliberately no all-pairs semantic scan — efficiency design in
  `mse_8wq2vnr5tkxm3jhc`); a recorded `supersedes`/`evolves` suppresses the pair, `related_entries`
  overlap is flagged "already related — consider upgrading". It ends by printing the litmus
  (`cli.py:854`). It never touches disk.
- Retroactive edges live in a **link sidecar** (`.memory-seed/sessions/links/YYYY-MM/YYYY-MM-DD.md`),
  unioned into the effective graph at read time by `augment_chunks_with_link_sidecars`
  (`retrieval.py`), so a sidecar edge counts everywhere the YAML edge would.
- `links check` validates the union (dangling/self/postdates/cycle/authored-inverse); `esr` surfaces a
  "Lifecycle link gaps (today's entries)" preflight.

## Why it's this way (do not regress)

Classification — **supersedes vs evolves vs related** — is a deliberate *author judgment*, not
something the tool infers: `supersedes` retires (and now damps ranking), `evolves` stays valid, and
the graph-edge contract forbids outbound-supersedes from inflating importance. Entries are append-only,
so retroactive edges *must* live in sidecars. **So the fix removes mechanical friction only; it must
never auto-classify or write a live edge.**

## Proposal

1. **`link audit --date <today> --apply` — scaffold, don't decide.** Ensure the dated sidecar exists
   with correct frontmatter and, for each gap, insert a per-entry block with `entry_id:` filled and the
   candidates recorded as a **machine-detectable, inert stub** the author must resolve — never a live
   edge:
   ```yaml
   entry_id: mse_xxxx
   classify_pending: true          # replace with `supersedes:` or `evolves:` (or delete if merely related)
   # candidates (evidence):
   #   - mse_cand1   # files: app.js | topics: retrieval
   #   - mse_cand2   # topics: graph
   ```
   `classify_pending: true` is a real key the graph reader **ignores** (so a stub creates no phantom
   edge), the candidate ids sit in comments (also inert), and blocks are inserted in chronological
   order. The author swaps `classify_pending: true` for the real `supersedes:`/`evolves:` list or
   deletes the block. `--apply` refuses to emit a live edge value.
2. **`links check` gains `sidecar-unclassified-stub` (warning, not error).** Any block still carrying
   `classify_pending: true` is surfaced so it can't be silently forgotten — warning-level, because
   classification is judgment and must never block a commit or a fuse.
3. **`esr` counts open stubs** in its existing "Lifecycle link gaps" section (0 open stubs = clean).
4. **(P2, optional) advisory commit-time nudge.** Extend the `prepare-commit-msg` (or a new pre-commit)
   hook to run the today-scoped audit and print a **non-blocking** note when a commit touches the
   session log with unresolved gaps/stubs — advisory only, pointing to `link audit --apply`.
5. **(P3, optional) MCP `memory_link_record`.** A write tool so agents author sidecar edges through MCP
   rather than hand-editing files. Larger surface (first memory *write* tool) — deferred until 1–3 prove
   the ergonomics.

## Non-goals

- No auto-classification and no writing a live `supersedes:`/`evolves:` value without the author.
- No all-pairs semantic scan — keep the file/topic candidate heuristic.
- Stays append-only: sidecars only, never edits an existing entry.
- The commit nudge stays advisory; classification never blocks.

## Acceptance criteria

- `link audit --date <d> --apply` writes a schema-valid, chronologically-ordered sidecar of
  `classify_pending` stubs with commented candidate evidence; re-running is idempotent (no duplicate
  stubs for an already-classified or already-stubbed entry).
- The graph reader treats a `classify_pending` stub as **zero edges** (no phantom supersedes/evolves);
  a classified block round-trips through `augment_chunks_with_link_sidecars` exactly as a hand-authored
  one.
- `links check` reports open stubs as `sidecar-unclassified-stub` (warning); `esr` counts them.
- Fixtures: apply→stub→classify→check round trip; stub-creates-no-edge; idempotent re-apply.

## Dependencies

- `docs/3_Spec/lifecycle-edge-linking-sidecars.md` (sidecar format + read path).
- `docs/3_Spec/graph-edge-contract.md` (edge semantics; the "never auto-classify" constraint).
- `.memory-seed/skills/session_logging.md` (end-of-session sweep step points at `--apply`).
