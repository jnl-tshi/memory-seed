---
memory-system-version: 2.6
tags:
  - memory-seed
  - proposal
  - multi-user
  - deferred
---

# Multi-user session memory for Memory Seed (refined proposal)

> **Status: REFINED 2026-06-13 — DEFERRED to 3.0.** Do not implement yet. Start only after
> Release 2.6.0 ships and Release 2.7.0 lands. Product intent: **exploring team-capable** (the
> repo is solo-first today; this opens a multi-user door without harming solo users).
>
> This is the execution-ready spec. Its design rationale and comparative research are in
> [`multi-user-deep-research-report.md`](multi-user-deep-research-report.md). Where this doc and
> the research report differ, **this doc wins** (it folds in corrections found during review —
> notably the SQLite-cache caution and the complete reader inventory).
>
> **What this provides:** multi-user *attribution* and *Git-merge avoidance*.
> **What it does NOT provide:** privacy, permissions, encryption, or real-time concurrent editing.
> Per-user filenames are not confidentiality — `.memory-seed/` files are plain Markdown and may be
> committed; treat them as publishable unless the repo is explicitly private.

## Objective

Support multiple contributors writing session memory on the same date without colliding in one
file, using this canonical layout:

```text
.memory-seed/sessions/
  YYYY-MM-DD/
    <user>.memory.md
```

Example:

```text
.memory-seed/sessions/
  2026-06-13/
    jean.memory.md
    amina.memory.md
    theo.memory.md
```

## Decision and justification

Adopt date-first, per-user session files because they:

1. Reduce Git merge conflicts by separating contributors into different files.
2. Preserve Memory Seed's Markdown-first and local-first architecture.
3. Make authorship explicit and auditable.
4. Retain normal Git diffs, reviews, repair workflows, and portability.
5. Support graph-style relationships without a database as the source of truth.
6. Preserve the existing date-oriented session model.
7. Avoid pretending plain files provide real-time collaborative editing.

## Compatibility requirement (dual-read)

Do not replace the existing layout. Memory Seed must read **both**:

```text
.memory-seed/sessions/2026-06-13.md
.memory-seed/sessions/2026-06-13/jean.memory.md
```

Existing repositories, entry IDs, and MCP chunk IDs must keep working. New writes use the per-user
layout only once an active user is resolved (see User identity).

## Upgrade & compatibility for existing installs

The guiding principle: **upgrading the tool must never silently relocate writes or rewrite a
user's files.**

- `memory-seed update` refreshes control-plane code and re-merges hook configs, but is
  **layout-agnostic and never migrates or rewrites session data**. Upgrading the package alone
  changes nothing about where a project writes.
- **Dual-read (Phase 1) means existing flat `YYYY-MM-DD.md` files keep working with zero action.**
- The user-resolution order makes a solo/legacy project **default to flat-file behavior** unless
  the user explicitly opts in. There is no silent switch of write target.
- Per-user writes activate only after a user is resolved. Converting historical data is the
  **opt-in `migrate sessions-layout`** command (idempotent, `--dry-run`, backups, preserves
  `entry_id`, adds file `hash_id`). Nothing auto-migrates on upgrade.
- Existing flat files lack `hash_id`/`schema_version`; readers treat them as legacy (implicit v1)
  and **never write frontmatter back into them** — sessions are append-only user data, not
  seed-managed. A transient file identity may be derived in-memory for indexing but is never
  persisted into a legacy file.
- Sub-projects upgrade independently via nearest-runtime resolution.

## Required storage model

Each new per-user session file carries YAML frontmatter:

```yaml
---
schema_version: 2
session_date: 2026-06-13
hash_id: msm_7f4939f294ce4deca8e046bc7f6e519a
project_id: memory-seed
user: jean
created_at: 2026-06-13T09:12:44Z
updated_at: 2026-06-13T16:41:02Z
related_memories:
  - hash_id: msm_8af47986ee4b4dfcbeb58ee27050645f
    relation: continuation
related_entries:
  - entry_id: ms-a17f39c2
    relation: builds_on
---
```

Field standardization (resolves inconsistencies in the original draft):

- `schema_version: 2` denotes the per-user layout. Legacy flat files are implicit/unversioned (v1).
- The date field is **`session_date`** (matching the existing file-frontmatter convention) — not
  `date`.
- The body keeps today's shape: `## YYYY-MM-DD HH:MM - title` headings, a per-entry ```yaml``` block,
  and narrative bullets. This preserves current MCP search and schema-test semantics.

## Identity rules

Two identity levels.

**File-level identity — `hash_id`**

- Identifies the entire user session file.
- Immutable; generated once at file creation from an immutable seed (include a random nonce so two
  files with identical metadata never collide). Never recomputed from mutable content.
- At least 128 bits of effective space. Namespace `msm_` (e.g. `msm_` + base32-encoded SHA-256,
  truncated only after generating the full digest).

**Entry-level identity — `entry_id`**

- Identifies an individual session entry / MCP chunk.
- Existing IDs (`ms-` + 8 hex) MUST be preserved and remain resolvable. Do not replace entry IDs
  with the file-level hash. Detect duplicate entry IDs.
- **Known, deferred limitation:** the current `ms-` + 8-hex format is ~32 bits of visible space.
  The research report's birthday-bound analysis shows this is small for a large multi-user corpus
  (~1% collision near 10k entries). This feature **keeps the 32-bit format for backward
  compatibility** and does **not** rewrite historic entry IDs (see Non-goals). Widening the
  entry-ID space (e.g. an `mse_` 128-bit format with backward-compatible aliasing) is a separate,
  explicitly deferred follow-up — flagged here so it is not forgotten.

Links: `related_memories` points to file-level `hash_id` values; `related_entries` points to
entry-level `entry_id` values. Support both shorthand strings and relation-bearing objects:

```yaml
related_memories:
  - msm_8af47986ee4b4dfcbeb58ee27050645f          # shorthand
  - hash_id: msm_8af47986ee4b4dfcbeb58ee27050645f # relation-bearing
    relation: continuation
```

## User identity

Canonical user slugs match `^[a-z0-9][a-z0-9_-]{0,63}$`. The filename and frontmatter `user` must
agree (`sessions/2026-06-13/jean.memory.md` ⇒ `user: jean`).

Resolve the active user in order:

1. Explicit function/CLI argument.
2. `MEMORY_SEED_USER` environment variable.
3. Per-clone `.memory-seed/local.yaml` (gitignored; a local selection must NOT become a shared
   default that makes every clone write under the same user).
4. Legacy flat-file behavior when interacting with an existing legacy session.
5. Otherwise, emit an actionable configuration warning rather than guessing.

A shared, tracked `.memory-seed/project.yaml` may hold the `project_id`, the participant registry,
and the `user_initials → slug` map used by migration.

## Implementation architecture

Introduce **one** canonical session-discovery abstraction instead of scattering globs:

```python
@dataclass(frozen=True)
class SessionDocument:
    path: Path
    session_date: str
    user: str | None
    layout: Literal["legacy-flat", "per-user-day"]

def iter_session_documents(memory_dir: Path) -> Iterator[SessionDocument]: ...
def session_path(memory_dir: Path, date: str, user: str) -> Path: ...
```

`iter_session_documents` must recognize `sessions/YYYY-MM-DD.md` and
`sessions/YYYY-MM-DD/*.memory.md`; return deterministic ordering; ignore malformed paths safely;
distinguish legacy vs per-user; and expose date + user. `session_path` is the single path
constructor — do not rebuild session paths independently in multiple modules.

### Complete reader inventory (every current session reader must route through the abstraction)

This list is exhaustive as of 2.6.0 — the original draft and the research report omitted the
SessionStart hook because it post-dates them:

- `memory_seed/core.py` — `compact_sessions()` and `SESSION_DATE_RE` (currently flat-only).
- `memory_seed/semantic_cache.py` — MCP chunk extraction / ranking (reads each session file).
- `memory_seed/cli.py` — `compact` command output (uses the above).
- `memory_seed/mcp_validate.py` — validation report (uses search/extraction).
- `.memory-seed/hooks/session-log-check.py` — reads today's file (becomes user-aware in Phase 2).
- **`.memory-seed/hooks/session-start-context.py`** — globs `sessions/*.md` by filename date.
  Its `*.md` glob **silently misses** files under `sessions/YYYY-MM-DD/` today; it must adopt
  `iter_session_documents` and the multi-user orientation rule below.
- `doctor` session/bootstrap awareness, and the **seed twins** of every hook
  (`memory_seed/seed/.memory-seed/hooks/*`).

### SessionStart orientation semantics for multi-user

The SessionStart hook (`session-start-context.py`) must define "newest" in a multi-user tree:

1. Resolve the active user (same order as above).
2. Pick the newest `session_date` (newest date directory or newest legacy flat file).
3. Inject the **active user's** latest entry for that date **in full** (path, headings, latest
   entry body — current behavior, now scoped to that user's file).
4. Append a **one-line-per-file listing** of co-contributors' files for that same date (path +
   entry-heading count only) so cross-contributor context is visible without dominating the
   injected payload.
5. If no active user is resolved (legacy/solo), behave exactly as today against the flat file.

### Caching of entry chunks

**Out of scope for the initial implementation — and SQLite is the wrong approach for this project.**

- Markdown stays authoritative; `memory_search` keeps reparsing per call. Today there is **no
  chunk cache** to preserve or break: `semantic_cache.py` only `lru_cache`s the embedding model;
  session chunks are read fresh via `read_text`. Per-user/day sharding raises file **count**, not
  total content, so parse cost is roughly unchanged (modest extra directory-walk / file-handle
  overhead). Not a reason to add caching now.
- **If/when caching is later justified**, it must be a **local, gitignored, rebuildable, per-file
  cache keyed by mtime/content-hash**, layered transparently beneath `iter_session_documents`,
  never authoritative, always reconstructable by reparsing.
- **Do NOT use SQLite, and do NOT commit a monolithic manifest.** The research report's preferred
  `index.db` (SQLite FTS5) is rejected here: this repository lives in a **cloud-synced (OneDrive)
  path**, and the report's own Trilium citation warns that Drive/Dropbox/OneDrive sync can corrupt
  a SQLite database. A committed monolithic manifest is also a Git merge hot spot. A plain per-file
  cache avoids both problems. (Reaffirms the existing non-goals: no committed monolithic index, no
  SQLite as source of truth.)

## Implementation phases

### Phase 1 — dual-read session discovery
Add `iter_session_documents` / `session_path`; route **every** reader in the inventory above
through them (including the SessionStart hook). Update tests that assume `YYYY-MM-DD.md`, plus
README examples and seeded instructions. Preserve nearest-runtime behavior. **Do not move or
rewrite existing session files in this phase.**

### Phase 2 — user-aware writes and hooks
Make `session-log-check.py` (and its seed twin) resolve the active user and check
`sessions/<today>/<user>.memory.md`: another user's recent entry must not suppress the current
user's reminder; chronology is checked independently per user file; legacy repos keep their
fallback; unresolved identity yields a clear setup instruction. New per-user files get valid
frontmatter and an immutable `hash_id`. Apply the SessionStart orientation rule above.

### Phase 3 — graph-link validation
Validate: duplicate `hash_id`; duplicate `entry_id`; unresolved `related_memories`/
`related_entries`; malformed frontmatter; invalid user slugs; filename/frontmatter user mismatch;
filename/frontmatter date mismatch; unsupported schema versions. Output must identify the source
file and offending value.

### Phase 4 — MCP metadata
Keep existing chunk IDs working. Where it fits the existing public interface, include
`file_hash_id`, `path`, `user`, `session_date` in results, and add `user`/date filters. Recursive
Markdown parsing is acceptable; no SQLite source of truth.

### Phase 5 — migration command
`memory-seed migrate sessions-layout`: `--dry-run`; parse legacy files entry by entry; map
`user_initials` → canonical users via `project.yaml`; preserve `entry_id`; one file-level hash per
output file; preserve per-user chronological order; follow backup conventions; idempotent; report
unknown users instead of guessing; never overwrite an existing per-user file incorrectly; handle
repos with both layouts. Keep legacy reads after migration.

## Required tests

- **Discovery:** legacy flat / per-user / mixed-layout repos all discovered; deterministic
  ordering; malformed names ignored or reported; nested runtimes isolated.
- **User behavior:** Jean's path resolves to `jean.memory.md`; Amina's entry does not satisfy
  Jean's freshness check; invalid slugs rejected; filename/frontmatter ownership must agree;
  missing user config produces an actionable message.
- **Identity & relationships:** new files get unique file hashes; editing content does not change
  the hash; duplicate file hashes and duplicate entry IDs detected; valid links resolve; dangling
  links reported; existing entry IDs unchanged.
- **MCP & compaction:** both layouts appear in compact output; existing chunk IDs still fetchable;
  source paths/line ranges accurate; user/date/file-hash metadata exposed where required;
  legacy-only repos behave as before.
- **Migration:** dry-run writes nothing; entry text/IDs preserved; users split into correct files;
  repeated runs idempotent; unknown initials fail safely; backups created; mixed input handled
  without data loss.
- **SessionStart orientation:** active user's latest entry injected in full; co-contributor files
  listed as headings-only; legacy/solo path unchanged.

## Non-goals

Real-time collaborative editing; a hosted sync service; privacy / per-user access control;
encryption; SQLite as the source of truth; a committed monolithic generated index; deletion of
legacy-read support; automatic rewriting of all existing entry IDs; silent inference of ambiguous
users.

## Engineering constraints

Preserve current public behavior unless explicitly changed here. Prefer small, reviewable helpers
over duplicated path/parsing logic. Avoid new dependencies unless clearly necessary. Keep Markdown
authoritative and generated caches rebuildable + ignored. Maintain Python 3.11 compatibility.
Follow the repo's backup / update / doctor / nearest-runtime conventions. No unrelated refactors.
Update seeded files as well as runtime code where both copies exist. Run the full test suite before
completion.

## Deliverables

Implementation; tests for legacy/new/mixed layouts; updated README + seeded docs; a concise
migration note; a summary of modified files; test commands + results; any deferred work with
justification; confirmation the design stays consistent with
[`multi-user-deep-research-report.md`](multi-user-deep-research-report.md).

## Completion criteria

Multiple users can work on the same date without writing to the same file; old flat files remain
readable; the current user's hook checks only the correct file; file and entry links resolve by
immutable IDs; duplicate and dangling IDs are detected; compaction and MCP work across both
layouts; migration is safe and idempotent; the SessionStart hook handles the per-user tree;
documentation explains attribution, configuration, compatibility, upgrade behavior, caching stance,
and limitations; all existing and new tests pass.
