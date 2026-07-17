---
memory-system-version: 2.13
tags:
  - memory-seed
  - plan
  - 3.0
  - git
  - related-entries
---

# Git Commit <-> Decision Entry Linking - Scope

> **Status: P1 IMPLEMENTED 2026-07-03 (unreleased).** The `Memory-Entry:` trailer convention
> (Working Principles bullet), the `commits:` schema field (session_logging.md), git-gated
> `links check` validation (malformed/unknown hashes), and read-only
> `memory-seed link commits <entry_id>` (field + trailer-scan) are built and tested. The old P2
> reminder-only post-commit hook is closed as obsolete: the later seeded `prepare-commit-msg` hook
> stamps `Memory-Entry:` trailers automatically for staged session entries, with `hooks status` and
> `hooks repair` covering installation drift. Source: external review doc
> `Memory-Seed Logic Capture Improvement.md` (the "Version Control Reference" field in its
> proposed decision schema). Companion to
> [`related-entries-generation-plan.md`](related-entries-generation-plan.md) (same forward-edge /
> read-time-traversal design pattern) and
> [`supersession-edges-plan.md`](supersession-edges-plan.md) (shared the same validation
> dependency, see "Known Dependency" below - now resolved).

## Motivation

Source code dictates the "what" of the system at any commit; session entries dictate the "why."
Today there is no link between the two. Two failure modes follow: **orphaned logic** (a decision
entry exists but you cannot find which commit realized it, so it may be stale or abandoned) and
**orphaned code** (a commit changes behavior with no recoverable rationale, because the session
entry that motivated it is buried in an unrelated day's file). Neither `related_entries` nor
`supersedes` (proposed) addresses this - both link entries to other entries, never to the commit
that implemented one.

## What Exists Today

Nothing. Session entries have no field referencing a commit hash, and commit messages have no
convention for referencing an `entry_id`. `agent-rules.md`'s Decision Mandate already requires a
DRAFT record before a durable code change, so in practice the entry is written *before* the commit
exists - meaning any commit reference on the entry has to be filled in **after** the commit lands,
within the same turn.

## Design Model

Two lightweight, additive primitives - no server, no commit hook required by default:

### 1. Commit message trailer (write path)

Agents append a standard Git trailer to the commit message referencing the entry that motivated
the change:

```text
Memory-Entry: mse_21d4kcx6g1vxt0ky
```

This is machine-parseable with `git log --grep` or `git interpret-trailers` and requires no new
tooling to *write* - it's a documented convention in `agent-rules.md` / `session_logging.md`, not
an enforced hook. Consistent with the project's "no auto-apply, reminder or convention only"
precedent (`baseline-seed-promotions.md` item 4).

### 2. Optional `commits` field on the entry (backfill, same-entry-only)

```yaml
entry_id: mse_21d4kcx6g1vxt0ky
...
commits:
  - a1b2c3d4
```

Filled in **after** the commit exists, and only ever on the current/newest entry within the same
turn, before any later session entry has been appended - the same append-only-safe scoping
`related-entries-generation-plan.md` reserves for a possible `link add` writer ("current/newest entry
only... no historical rewrite"). This is not editing history; it is completing the entry that is
still being authored this turn. Once another entry exists after it, adding `commits:` becomes a
historical edit and requires explicit user-requested correction.

## Validation

- **Hash existence (P1):** if `.git` exists at the runtime root, `links check` resolves each
  `commits:` entry against `git cat-file -e <hash>^{commit}` (or an equivalent log scan) and flags an
  unresolvable or non-commit object. If no `.git` directory is present (package used outside a git repo), this
  check is skipped, not failed - matches "prefer local deterministic behavior" without assuming git
  is always available.
- **Known dependency - resolved (2026-07-02, unreleased):** `check_session_links()`'s
  `related_entries` dangling-ref scan used to only run inside the `if doc.layout != "per-user-day":
  continue` branch, silently skipping legacy-flat `.memory-seed/sessions/YYYY-MM-DD.md` files (this
  repository's own layout). Fixed by moving the entry-level (fenced `` ```yaml `` block) scan out of
  the per-user-day gate, since `related_entries` inside an entry's YAML block has the same shape in
  both layouts. `commits:` validation can now reuse the same, now-correct gate without inheriting
  the gap.

## Read-Side Lookup (P1)

`memory-seed link commits <entry_id>` (read-only):

- Prints the entry's own `commits:` field, if set.
- Additionally greps `git log --all --grep="Memory-Entry: <entry_id>"` for commits that reference
  the entry via trailer, so coverage exists even when an agent forgot to backfill `commits:`
  manually. This dual-source lookup costs nothing extra to build (`git log --grep` is a single
  subprocess call) and degrades gracefully - outside a git repo it just returns the field-only
  result.

## Phasing

- **P1 (proposed first increment):** schema field + trailer convention documented in
  `agent-rules.md`/`session_logging.md`; git-presence-gated hash validation in `links check`;
  read-only `memory-seed link commits <entry_id>`.
- **P2 (obsolete/closed 2026-07-13):** the proposed reminder-only post-commit hook is no longer
  needed. The shipped `prepare-commit-msg` hook stamps commit messages with `Memory-Entry:` trailers
  before the commit is created, so the durable commit-to-entry link exists without reopening YAML.
  `commits:` backfill remains same-turn/newest-entry-only and explicit; the hook does not edit
  session files.

## Open Decisions

1. ~~Trailer key name: `Memory-Entry:` vs. something shorter (e.g. `Mem-Entry:`)~~ - signed off
   2026-07-03: use `Memory-Entry:`. Explicit, self-describing, and greppable.
2. ~~Whether to fix the legacy-flat `links check` gap as part of this work or file it as its own
   prerequisite fix~~ - resolved 2026-07-02 (see Known Dependency above); no longer blocking.
3. Full SHA vs. short hash for `commits:`. Recommendation: require full 40-character SHAs in the
   stored field to keep validation unambiguous; display may shorten hashes for humans.

## Definition of Done (P1)

- Schema documented in `session_logging.md` and the commit-trailer convention documented in
  `agent-rules.md` Working Principles or an equivalent cross-cutting note.
- `links check` validates `commits:` hashes as commit objects when `.git` is present; skips cleanly
  otherwise.
- `memory-seed link commits <entry_id>` ships read-only, with a fixture test covering both the
  field-only and trailer-grep paths.
- Concise session log entry recording the decision and the legacy-flat dependency resolution.
