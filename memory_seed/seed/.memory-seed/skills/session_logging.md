---
memory-system-version: 2.12
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

Keep session filenames date-only, such as `.memory-seed/sessions/2026-05-02.md`. Generate `entry_id` as a deterministic 80-bit `mse_` ID from metadata only: timestamp, title, user initials, agent type, project path, and subproject path. Legacy `ms-` IDs remain valid and must not be rewritten.

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
