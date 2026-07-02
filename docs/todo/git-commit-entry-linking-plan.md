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

> **Status: PROPOSED, not yet decided or built.** Source: external review doc
> `Memory-Seed Logic Capture Improvement.md` (the "Version Control Reference" field in its
> proposed decision schema). Companion to
> [`related-entries-generation-plan.md`](related-entries-generation-plan.md) (same forward-edge /
> read-time-traversal design pattern) and
> [`supersession-edges-plan.md`](supersession-edges-plan.md) (shares the same validation
> dependency, see "Known Dependency" below).

## Motivation

Source code dictates the "what" of the system at any commit; session entries dictate the "why."
Today there is no link between the two. Two failure modes follow: **orphaned logic** (a decision
entry exists but you cannot find which commit realized it, so it may be stale or abandoned) and
**orphaned code** (a commit changes behavior with no recoverable rationale, because the session
entry that motivated it is buried in an unrelated day's file). Neither `related_entries` nor
`supersedes` (proposed) addresses this — both link entries to other entries, never to the commit
that implemented one.

## What Exists Today

Nothing. Session entries have no field referencing a commit hash, and commit messages have no
convention for referencing an `entry_id`. `agent-rules.md`'s Decision Mandate already requires a
DRAFT record before a durable code change, so in practice the entry is written *before* the commit
exists — meaning any commit reference on the entry has to be filled in **after** the commit lands,
within the same turn.

## Design Model

Two lightweight, additive primitives — no server, no commit hook required by default:

### 1. Commit message trailer (write path)

Agents append a standard Git trailer to the commit message referencing the entry that motivated
the change:

```text
Memory-Entry: mse_21d4kcx6g1vxt0ky
```

This is machine-parseable with `git log --grep` or `git interpret-trailers` and requires no new
tooling to *write* — it's a documented convention in `agent-rules.md` / `session_logging.md`, not
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
session — the same append-only-safe scoping `related-entries-generation-plan.md` already uses for
`link add` ("current/newest entry only... no historical rewrite"). This is not editing history; it
is completing the entry that is still being authored this turn.

## Validation

- **Hash existence (P1):** if `.git` exists at the runtime root, `links check` resolves each
  `commits:` entry against `git cat-file -e <hash>` (or an equivalent log scan) and flags an
  unresolvable hash. If no `.git` directory is present (package used outside a git repo), this
  check is skipped, not failed — matches "prefer local deterministic behavior" without assuming git
  is always available.
- **Known dependency (discovered during research):** `check_session_links()`'s existing
  `related_entries` dangling-ref scan (`memory_seed/core.py:402-409`) only runs inside the
  `if doc.layout != "per-user-day": continue` branch — it is **not** applied to legacy-flat
  `.memory-seed/sessions/YYYY-MM-DD.md` files. Verified empirically: a dangling `related_entries`
  ref in a legacy-flat file does not fail `links check` today. This repository itself uses the
  legacy-flat layout, so any new ref-validation logic (`commits:` here, `supersedes` in the
  companion plan) must not silently inherit this gap. Landing either feature should either (a) fix
  the legacy-flat scan gap as a prerequisite, or (b) explicitly document the same limitation until
  it is fixed.

## Read-Side Lookup (P1)

`memory-seed link commits <entry_id>` (read-only):

- Prints the entry's own `commits:` field, if set.
- Additionally greps `git log --all --grep="Memory-Entry: <entry_id>"` for commits that reference
  the entry via trailer, so coverage exists even when an agent forgot to backfill `commits:`
  manually. This dual-source lookup costs nothing extra to build (`git log --grep` is a single
  subprocess call) and degrades gracefully — outside a git repo it just returns the field-only
  result.

## Phasing

- **P1 (proposed first increment):** schema field + trailer convention documented in
  `agent-rules.md`/`session_logging.md`; git-presence-gated hash validation in `links check`;
  read-only `memory-seed link commits <entry_id>`.
- **P2 (deferred):** auto-populate `commits:` on the newest entry via an optional post-commit hook.
  Reminder-only by default (append a suggested `commits:` line agents confirm), never auto-writing
  YAML without review — same "hooks can't reason or obtain approval" principle already applied to
  the (deliberately unshipped) evolution-nudge hook.

## Open Decisions

1. Trailer key name: `Memory-Entry:` vs. something shorter (e.g. `Mem-Entry:`). Needs sign-off
   before documenting it as a convention.
2. Whether to fix the legacy-flat `links check` gap as part of this work or file it as its own
   prerequisite fix (see Known Dependency above) — the same question applies to
   `supersession-edges-plan.md`, so it should be decided once for both.
3. Whether `commits:` accepts short hashes or requires full 40-character SHAs (short hashes are
   friendlier to write but can become ambiguous in a large, older repo).

## Definition of Done (P1)

- Schema documented in `session_logging.md` and the commit-trailer convention documented in
  `agent-rules.md` Working Principles or an equivalent cross-cutting note.
- `links check` validates `commits:` hashes when `.git` is present; skips cleanly otherwise.
- `memory-seed link commits <entry_id>` ships read-only, with a fixture test covering both the
  field-only and trailer-grep paths.
- Concise session log entry recording the decision and the legacy-flat dependency resolution.
