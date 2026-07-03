---
memory-system-version: 2.14
tags:
  - memory-seed
  - skill
  - session-logging
---

# Session Logging Skill

Use this skill when writing, validating, or repairing Memory Seed session entries.

## Session Log Format

Use dated files under `.memory-seed/sessions/` with file-level frontmatter:

````markdown
---
tags:
  - session-log
  - memory-seed
session_date: 2026-05-02
---

## 2026-05-02 14:35 - Switch cache key to content hash

```yaml
entry_id: mse_0123456789abcdef
user_initials: USER
agent_type: codex
agent_name: null
project_path: .
subproject_path: null
related_entries:
  - ms-db2d715c
```

### Summary

- What changed or what was checked.

### Decision

- D: State the decision that was made or implemented. (mandatory)
- R: Explain the decisive reason in 1-3 bullets. (mandatory)
- A: Alternative considered or rejected, with reason, if it mattered. (optional)
- F: Files, artifacts, or behaviors changed. (optional)
- T: Tests or validation outcome. (optional)
````

`agent_type` is the LLM model or vendor. `agent_name` is the active `.agents/` persona slug, or `null` when no persona is active. `related_entries` is an optional list of related `entry_id` values, legacy `ms-` or current `mse_`, that link this entry to prior entries. It forms the canonical graph edges surfaced by `memory_search` / `memory_get_chunk` and validated by `memory-seed links check`.

`supersedes` is an optional sibling list of `entry_id` values marking earlier decisions this entry explicitly replaces or deprecates — a typed status edge, kept separate from `related_entries` (relatedness) and never merged with it. Forward-only: reference only entries that already existed when this one was written; `links check` rejects a `supersedes` ref whose target postdates the referencing entry, a self-reference, or a cycle. A superseded entry stays fully retrievable — supersession deprioritizes, never hides. The computed inverse (`superseded_by`) is available read-time via `memory-seed link show` and `memory_get_chunk`; do not hand-write it.

`commits` is an optional list of full 40-character commit SHAs implementing this entry's decision. Backfill it only on the current/newest entry, in the same turn the commit lands — once a later entry exists, adding `commits:` becomes a historical edit requiring explicit user-requested correction. The commit side of the link is the `Memory-Entry: <entry_id>` message trailer (see Working Principles), which needs no backfill window; `memory-seed link commits <entry_id>` reads both sources. `links check` rejects short or malformed hashes always, and unknown hashes when a `.git` repository is present.

Keep session filenames date-only, such as `.memory-seed/sessions/2026-05-02.md`. Generate `entry_id` as a deterministic 80-bit `mse_` ID from metadata only: timestamp, title, user initials, agent type, project path, and subproject path. Legacy `ms-` IDs remain valid and must not be rewritten.

## Local Identity and Session Layout

Two related but separate mechanisms:

- **Identity** (`.memory-seed/local.yaml`, gitignored): the active local user, set via `memory-seed user set <slug>`. Once configured, `user_initials` in new entries should reflect that user, resolved against `.memory-seed/project.yaml`'s `participants:` registry (`slug` / `initials` / `display_name`).
- **Layout** (flat vs. per-user file): purely a function of how many participants are registered, not whether identity is configured. `session_target()` only switches to `.memory-seed/sessions/YYYY-MM-DD/<user>.md` once `participants:` lists 2 or more entries; with 0 or 1, it stays on the shared flat `.memory-seed/sessions/YYYY-MM-DD.md` file regardless of a configured user. Per-user files exist to avoid concurrent-author merge conflicts, which isn't a concern until there is a second author to conflict with. An explicit `--user <slug>` CLI override bypasses this gate (a deliberate one-shot choice).

Practical effect: configuring identity alone never fragments an existing single-author project's log. Only registering a second `participants:` entry does — at that point `memory-seed migrate sessions-layout` can split existing flat history if wanted.

**No local identity configured?** The SessionStart hook offers once, then never repeats regardless of whether the offer was accepted (tracked by a gitignored `.memory-seed/.identity-offer-stamp` file, written on first offer). This is optional and skippable — most projects are solo and don't need it. If offered, ask the user for a preferred slug/initials/display name, then run `memory-seed user set <slug>` and add a matching `participants:` entry.

**Consistency check:** `memory-seed doctor` warns (non-fatal) when a configured local user's slug has no matching `participants:` entry — that leaves `user_initials` unresolvable for multi-user tooling (`migrate sessions-layout`, `links check`) even though `session_target()` still works.

## Append-Only Chronology

The session file is strictly append-only and must stay in ascending time order.

- Append every new entry to the end of the day's file. Never insert an entry above an existing one.
- Append each entry at the physical end of the file; never insert above an existing entry.
- The entry heading timestamp is the actual current clock time at the moment you write it.
- Never reuse a time from context, memory, or an earlier message.
- Never backdate an entry to when the work happened.
- If recording work completed earlier, still stamp the heading with the current time and describe the original timing in the entry body if it matters.

## Reason Rules

DRAFT is the baseline decision-record format for session entries. A DRAFT decision record is the default whenever a turn produced a decision or durable change.

- D = Decision
- R = Reason
- A = Alternatives considered or rejected
- F = Files, artifacts, or behaviors changed
- T = Tests or validation

`D` and `R` are required for every meaningful decision. `A`, `F`, and `T` are optional when not relevant.

- Do not invent reason.
- If reason is inferred, label it `Inferred reason`.
- If reason is unknown, write `Reason not recorded`.
- Alternatives are optional unless they affected the decision or tradeoff.
- If an approach was **attempted and failed** or proved incompatible during the session, log it under `A` even when not explicitly asked to — this is empirical evidence for future sessions, not an optional nicety. State what was tried and why it failed in one line; that's enough for a future agent to skip it without re-deriving the failure.
- Use `D1`, `D2`, and similar labels only inside a multi-decision entry.
- Do not rewrite old logs solely to match the newest schema unless the user explicitly asks.

## Entry Shapes

### Meaningful decision entry

Use for one durable decision.

```markdown
### Summary

- Summarize the coherent task.

### Decision

- D: State the decision. (mandatory)
- R: Explain the decisive reason in 1-3 bullets. (mandatory)
- A: Alternative considered or rejected, with reason, if it mattered. (optional)
- F: Files, artifacts, or behaviors changed. (optional)
- T: Tests or validation outcome. (optional)
```

### Small work entry

Use for routine edits, small fixes, or verification-only work with no real decision. Do not invent reason.

```markdown
### Summary

- What changed or what was checked.

### Validation

- Command or check and outcome, if relevant.

### Follow-up

- Only include if there is residual risk or a next action.
```

### Multi-decision session entry

Use one entry when several decisions belong to one coherent task, plan, or user goal. Split entries when decisions affect unrelated subsystems, sub-projects, or goals.

```markdown
### Summary

- Summarize the coherent task.

### Decisions

#### D1 - Short decision name

- D: State the choice. (mandatory)
- R: Explain the decisive reason in 1-3 bullets. (mandatory)
- A: Alternative considered or rejected, with reason, if it mattered. (optional)
- F: Files, artifacts, or behaviors changed. (optional)
- T: Tests or validation outcome. (optional)

#### D2 - Short decision name

- D: State the choice. (mandatory)
- R: Explain the decisive reason in 1-3 bullets. (mandatory)

### Implementation

- Summarize changed behavior, not every file.

### Validation

- Commands or checks and outcomes, not full output.

### Follow-up

- Residual risks or next actions.
```
