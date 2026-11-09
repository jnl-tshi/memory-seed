---
memory-system-version: 2.25
governing_adr: adr_runtime_discovery
tags:
  - memory-seed
  - skill
  - memory-doctor
---

# Memory Doctor Skill

Use this skill when validating a Memory Seed runtime, migration, bootstrap repair, or package seed change.

## Checks

- `AGENTS.md` exists and routes to nearest `.memory-seed/`.
- `.memory-seed/agent-rules.md` exists and defines operating-mode workflow.
- `.memory-seed/project-bootstrap.md` exists and is bootstrap/repair only.
- `.memory-seed/index.md` contains topology, active state, inheritance, and skill pointers.
- `.memory-seed/policy.md` contains behavioral constraints only.
- `.memory-seed/skills/` contains task runbooks.
- `.memory-seed/sessions/` contains dated append-only logs.
- `.memory-seed/archive/` contains archived prior control-plane snapshots when versions were replaced.
- The six managed Retrieval Profile v1 files are present at exact
  `.memory-seed/retrieval-profiles/<id>/v1.yaml` identities and pass the same strict loader used by the
  Task Packet compiler. `init`/`update` install missing versions but never overwrite an existing version;
  custom profile IDs remain project-owned. A managed profile that cannot parse, compose, or normalize makes
  the control plane unhealthy; it is not a warning-only condition.
- Every `.memory-seed/skills/*.md` runbook is registered in `skills/index.md`; an unregistered file is an orphan skill (warned, non-fatal).
- An Authority Map that declares an `Accepted ADRs` inventory links every live
  `.memory-seed/decisions/*.md` file. Deliberately thin concern-routing maps do not claim exhaustive coverage.
- Relative Markdown links in routing/control-plane Markdown resolve from their source file. Backticked paths and
  Markdown links inside `## Inputs` sections of non-hidden `CONTEXT.md` stage contracts resolve from the contract
  or project root. Vendored `_tools` and archived `_archive` trees are excluded.
- `memory-seed doctor --step-budget <tokens>` warns when an installed Retrieval Profile's effective
  `limits.max_tokens` exceeds the declared step envelope. The comparison is opt-in because projects own the budget.
- When a `.memory-seed/` runtime exists, each present entry-point file (`AGENTS.md`/`CLAUDE.md`/`GEMINI.md`/`.github/copilot-instructions.md`) routes into it — either ours (has `memory-system-version` frontmatter) or a foreign file carrying our `<!-- BEGIN memory-seed -->` block. A foreign file with no block is an orphaned runtime (warned, non-fatal); run `memory-seed update` to inject the block.
- No stale `.AGENTS/` paths are presented as the v2 target shape.
- Legacy `.AGENTS/` fallback remains tested when compatibility is required.

## Commands

```bash
memory-seed doctor
memory-seed doctor --step-budget 8000
memory-seed doctor --write-warning-baseline .memory-seed/doctor-warnings.json
memory-seed doctor --warning-baseline .memory-seed/doctor-warnings.json
memory-seed compact --days 30
python -m unittest discover -s tests
```

The warning baseline is an explicit, sorted JSON snapshot. Comparing against it keeps known warnings non-fatal,
prints resolved warnings, and exits non-zero for any new warning; recording and comparison are separate operations,
so a CI check never rewrites its own baseline.

## Output

- Pass/fail status.
- Missing or stale files.
- Version mismatches.
- Suggested repair path.
