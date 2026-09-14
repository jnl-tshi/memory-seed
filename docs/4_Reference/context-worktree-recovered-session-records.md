---
status: reference
source: uncommitted codex/fix/context-mode-routing worktree inspected 2026-09-14
scope: nine unique session records and their available link/topic sidecars
---

# Recovered Context Worktree Session Records

These records were unique to the dirty Context Mode worktree. They are preserved verbatim as
non-governing evidence because the guarded session fuse rejected their original provenance: the
entries declared `branch: main`, `branch: HEAD`, or no branch. Rewriting those fields would falsify
history. This reference does not insert the records into live session history or activate the behavior
they describe.

## Source: `.memory-seed/sessions/2026-09/2026-09-03.md`

````markdown
## 2026-09-03 21:20 - Evaluate project worktrees and branches

```yaml
entry_id: mse_hx7a5enfqjj5r99f
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
branch: main
```

### Summary

- Evaluated all registered local Git worktrees and branches without changing repository state.

### Validation

- `git worktree list --porcelain`, per-worktree `git status --porcelain`, branch divergence checks, and local `python -X utf8 -m memory_seed.cli esr` completed.

### Follow-up

- Preserve uncommitted work in `seed-pods` and `experiment-audit-cleanup`; obtain explicit approval before any integration or cleanup.
````


## Source: `.memory-seed/sessions/2026-09/2026-09-09.md`

````markdown
## 2026-09-09 14:20 - Evaluate Superpowers skills for Memory Seed workflow

```yaml
entry_id: mse_q65cvve98xnwzr9a
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
branch: HEAD
```

### Summary

- Reviewed the complete first-party Superpowers skill catalogue against Memory Seed's current runtime, constitutional boundaries, and existing collaboration adapter.

### Decisions

#### D1 - Treat Superpowers as a selective process source, not a competing control plane

- D: Recommend adapting the strongest universal practices (root-cause-first debugging, fresh verification evidence, and scaled design discovery); retain direct optional delegation only for independent read-only dispatch and plan-based SDD; keep Memory Seed as the authority for worktrees, durable memory, integration, and cleanup.
- R: This preserves Memory Seed's local-first, append-only, guarded workflow while importing practices that close genuine process gaps without copying an external execution system.
- A: Importing Superpowers' global bootstrap, generic worktree/branch-finish routines, or a duplicate SDD/review controller is rejected because it conflicts with established Memory Seed authority and safety boundaries.
- T: Compared all fourteen published first-party Superpowers skills with their official current documentation and the active Memory Seed collaboration contracts.
````


## Source: `.memory-seed/sessions/2026-09/2026-09-10.md`

````markdown
## 2026-09-10 08:58 - Activate existing design discovery skill in current checkout

```yaml
entry_id: mse_h7nxqbp739wmj2fv
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
branch: HEAD
```

### Summary

- User requested bringing main's design-discovery skill into this checkout and applying it to the search tuning proposal.

### Decisions

#### D1 - Restore the existing discovery runbook locally and begin scope comparison

- D: Copied main's unchanged design_discovery.md into live and seed skills and inserted its required trigger in both registries. Begin discovery on the draft by comparing consistency-only repair, repair plus bounded evaluation, and broader calibration.
- R: This older checkout lacked the registered skill. The user wants to test its performance on the plan; copying the existing runbook preserves that test without changing the skill itself. No experiment scope has been selected yet.
- F: `.memory-seed/skills/design_discovery.md`, `.memory-seed/skills/index.md`, `memory_seed/seed/.memory-seed/skills/design_discovery.md`, `memory_seed/seed/.memory-seed/skills/index.md`.
- T: Root-write guard was explicitly overridden for the user's requested current-checkout import; unrelated dirty content was preserved. Diff whitespace check passed and both triggers were found. Discovery remains open for user input.
````

````markdown
## 2026-09-10 09:09 - Refine retrieval evaluation sequence during discovery

```yaml
entry_id: mse_gmjn58kkz0v00n2m
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
branch: HEAD
```

### Summary

- Continued design discovery for the search parameter proposal; no implementation or plan-file changes this turn.

### Decisions

#### D1 - Evaluate consistency, then baseline performance, then component exclusion floors

- D: Carry the user's clarified sequence forward: establish surface consistency, measure current performance with a bounded evaluation, then evaluate whether individual component scores support reliable exclusion thresholds. Combination rules remain an experimental question.
- R: The user corrected a premature focus on filter combinations. Floors must be judged by relevant decisions lost as well as irrelevant candidates removed, using an unchanged ranker initially. Statistical intervals quantify uncertainty in measured error rates; they do not by themselves convert scores into relevance probabilities.
- A: Broad weight tuning and selecting AND/OR rules before baseline measurement are premature. Raw score thresholds may not transfer across corpus or embedding changes; failure to find a safe floor is a valid result.
- T: Re-read the draft, design-discovery skill, calibration report, and August 5 decisions explaining BM25F scale changes and recency as a tie-breaker. Proposed shadow evaluation and held-out validation; neither has run.
````

````markdown
## 2026-09-10 10:50 - Apply capability allocation workflow in current checkout

```yaml
entry_id: mse_gk3c6ps0j53k2yxk
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
branch: HEAD
```

### Summary

- Applied the user's approved capability-allocation update to this checkout's collaboration and design-discovery skills and both seed twins. The retrieval proposal and canonical commit are on codex/docs/parameter-tuning-plan.

### Decisions

#### D1 - Use explicit task capability allocation during planning

- D: Planning records worker/reviewer tier and effort, budgets, escalation and dependencies. Dispatch resolves available models and reports substitutions and observable actual selection. No compiler schema or automatic dispatch change is claimed.
- R: The user wants orchestrator-controlled sessions with different capability levels chosen as part of planning. Updating this active older checkout makes the workflow available immediately while preserving unrelated changes.
- F: `.memory-seed/skills/agent_collaboration.md`, `.memory-seed/skills/design_discovery.md`, `memory_seed/seed/.memory-seed/skills/agent_collaboration.md`, `memory_seed/seed/.memory-seed/skills/design_discovery.md`.
- T: Corresponding task-branch documentation and modified-skill parity checks passed. Session-schema suite had 30 passes and 2 existing topic_swarm parity failures. No implementation workers or retrieval experiments launched.
````

````markdown
## 2026-09-10 19:40 - Capture Decision Curator orchestration design in inbox

```yaml
entry_id: mse_k7q89ftjxrqvq5jz
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
```

### Summary

- Captured the user-approved Decision Curator architecture in an inbox discovery artifact. It establishes automatic Design Discovery, pre-merge, and post-merge curation gates, while preserving orchestrator and human approval boundaries.

### Decisions

#### D1 - Adopt a vendor-neutral Decision Curator and capture its design before implementation

- D: Record the Decision Curator architecture: a packeted curator runs automatically at named gates; it prefers a fresh same-worktree session, falls back to an inline subagent and then manual orchestration, and returns a receipt plus proposed diff for orchestrator approval. Origin: user.
- R: Planning decisions were not reliably harvested or reconciled with topics, links, ADRs, diagrams, and Git provenance. A purpose-built curation role supplies a bounded, repeatable gate without turning Context Mode or any vendor integration into Memory Seed authority.
- A: Retaining the six inactive generic personas was rejected by the user in favour of a single role with a defined workflow purpose. Automatic acceptance of ADRs or live lifecycle edges remains rejected: the curator may draft and propose, while human approval remains authoritative.
- F: docs/1_Inbox/decision-curator-orchestration-proposal.md.
- T: `python -m memory_seed.cli docs check` passed with 16 pre-existing metadata warnings; `git diff --check` passed.
````

````markdown
## 2026-09-10 19:51 - Repair legacy decision-qualified topic validation

```yaml
entry_id: mse_0f0ds66grvfe2mvg
user_initials: JN
agent_type: codex
project_path: .
subproject_path: null
```

### Summary

- Repaired `topics check` compatibility for historical entries that stored decision-qualified topics directly in immutable YAML metadata.

### Decisions

#### D1 - Validate legacy decision-qualified topics by base slug

- D: Treat only well-formed `slug:dN` values as decision-scoped authored topic references; validate their base slug and apply the topic-count target per decision.
- R: Historical entries are append-only evidence and the read path already recognizes this representation. The checker was the inconsistent component, reporting valid base slugs as unknown literals.
- A: Rewriting historical session YAML or changing the vocabulary was rejected because neither corrects the compatibility defect and both would alter durable evidence.
- F: Updated `memory_seed/topics.py` and added topic-check regression coverage.
- T: `python -m unittest tests.test_topics` passed; `python -m memory_seed.cli topics check` reports `Topic vocabulary OK` with only pre-existing count warnings.

### Follow-up

- The full unittest discovery run did not complete within the local 30-second command window; targeted coverage and the full corpus checker passed.
````

````markdown
## 2026-09-10 20:23 - Raise authored topic allowance and flag hierarchy overlap

```yaml
entry_id: mse_yb9adxp90vpkc8qb
user_initials: JN
agent_type: codex
project_path: .
subproject_path: null
```

### Summary

- Revised topic validation so four distinct authored topics are acceptable and parent-plus-descendant tags are the actionable warning.

### Decisions

#### D1 - Prefer hierarchy-specific topics over duplicate parents

- D: Raise the authored-topic warning threshold to five, retain three as the suggestion limit, and warn when one topic is an ancestor of another in the same attribution scope.
- R: Four distinct themes can be meaningful; the vocabulary hierarchy gives a deterministic definition of redundancy and names the child that preserves specificity.
- A: Lexical similarity was rejected because labels can overlap in wording without sharing taxonomy or meaning.
- F: Updated `memory_seed/topics.py`, topic tests, the live and seed session-logging contracts, and the decision-level-topic sidecar specification.
- T: `python -m unittest tests.test_topics` passed; `topics check` reports `Topic vocabulary OK`; `links check` reports session-memory integrity OK.

### Follow-up

- Historical authored metadata remains unchanged. The hierarchy warnings identify any later append-only correction candidates.
````

````markdown
## 2026-09-10 20:43 - Apply append-only hierarchy topic overrides

```yaml
entry_id: mse_35ptbbyvp0bf6sc7
user_initials: JN
agent_type: codex
project_path: .
subproject_path: null
```

### Summary

- Added append-only effective-topic overrides for every hierarchy overlap in the current corpus.

### Decisions

#### D1 - Correct effective membership through human-reviewed sidecars

- D: Preserve original session YAML as historical evidence, while a `human-amendment` topic sidecar marked `overrides_authored_topics: true` supplies the current effective topic set.
- R: Hierarchy makes the parent-to-child reduction deterministic, but append-only history forbids silently rewriting what was originally authored.
- A: Directly editing the historic YAML was rejected because it would erase the original provenance rather than record a correction.
- F: Added the override reader, checker behavior, CLI writer, regression tests, and 23 audited topic sidecar overrides.
- T: `python -m unittest tests.test_topics tests.test_topic_amend` passed; `topics check` reports `Topic vocabulary OK` with no hierarchy-overlap warnings.

### Follow-up

- `links check` is waiting on a local Git subprocess during commit-provenance inspection; it produced no validation result in this turn.
````


## Source: `.memory-seed/sessions/links/2026-09/2026-09-03.md`

````markdown
## 2026-09-03 21:20 - Evaluate project worktrees and branches

```yaml
entry_id: mse_hx7a5enfqjj5r99f
classify_pending: true
# candidates (evidence):
#   - mse_dd7zyz50qw9aqx0x
#   - mse_nzf2pfkwnehx5b70
#   - mse_kq3ba0cy9nkpqkm0
#   - mse_9c151e4gbkkv1w5v
#   - mse_yk47cyw9bbdvf52j
#   - mse_2x8yysgezex3tbys  # UNGATED - semantic rank only, no shared file/title/topic gate
#   - mse_w0jh7s6adamfkyt5  # UNGATED - semantic rank only, no shared file/title/topic gate
```
````


## Source: `.memory-seed/sessions/links/2026-09/2026-09-09.md`

````markdown
## 2026-09-09 14:20 - Evaluate Superpowers skills for Memory Seed workflow

```yaml
entry_id: mse_q65cvve98xnwzr9a
source: write-time
evolves:
  - d1 -> mse_hbcz7yz5q4yhqwsx (refines)
edge_evidence:
  - ref: "d1 -> mse_hbcz7yz5q4yhqwsx (refines)"
    why: "Extends the adapter-specific decision into a complete catalogue assessment while retaining its authority boundary."
```
````


## Source: `.memory-seed/sessions/links/2026-09/2026-09-10.md`

````markdown
## 2026-09-10 19:51 - Repair legacy decision-qualified topic validation

```yaml
entry_id: mse_0f0ds66grvfe2mvg
source: write-time
related_entries:
  - d1 -> mse_wj8p66t3v1pbpzth:d1
```
````

````markdown
## 2026-09-10 20:23 - Raise authored topic allowance and flag hierarchy overlap

```yaml
entry_id: mse_yb9adxp90vpkc8qb
source: write-time
related_entries:
  - d1 -> mse_0f0ds66grvfe2mvg
```
````

````markdown
## 2026-09-10 20:43 - Apply append-only hierarchy topic overrides

```yaml
entry_id: mse_35ptbbyvp0bf6sc7
source: write-time
related_entries:
  - d1 -> mse_yb9adxp90vpkc8qb
```
````


## Source: `.memory-seed/sessions/topics/2026-09/2026-09-09.md`

````markdown
## 2026-09-09 14:20 - Evaluate Superpowers skills for Memory Seed workflow

```yaml
entry_id: mse_q65cvve98xnwzr9a
source: write-time
topics:
  area:
    - control-plane:d1
  activity:
    - design-evaluation:d1
```
````


## Source: `.memory-seed/sessions/topics/2026-09/2026-09-10.md`

````markdown
## 2026-09-10 08:58 - Activate existing design discovery skill in current checkout

```yaml
entry_id: mse_h7nxqbp739wmj2fv
source: write-time
topics:
  area:
    - retrieval:d1
  activity:
    - testing:d1
```
````

````markdown
## 2026-09-10 09:09 - Refine retrieval evaluation sequence during discovery

```yaml
entry_id: mse_gmjn58kkz0v00n2m
source: write-time
topics:
  area:
    - retrieval:d1
  activity:
    - testing:d1
```
````

````markdown
## 2026-09-10 10:50 - Apply capability allocation workflow in current checkout

```yaml
entry_id: mse_gk3c6ps0j53k2yxk
source: write-time
topics:
  area:
    - retrieval:d1
  activity:
    - testing:d1
```
````

````markdown
## 2026-09-10 19:40 - Capture Decision Curator orchestration design in inbox

```yaml
entry_id: mse_k7q89ftjxrqvq5jz
source: write-time
topics:
  area:
    - control-plane:d1
  activity:
    - agent-collaboration:d1
```
````

````markdown
## 2026-09-10 19:51 - Repair legacy decision-qualified topic validation

```yaml
entry_id: mse_0f0ds66grvfe2mvg
source: write-time
topics:
  area:
    - topic-vocabulary:d1
  activity:
    - bugfix:d1
```
````

````markdown
## 2026-09-10 20:23 - Raise authored topic allowance and flag hierarchy overlap

```yaml
entry_id: mse_yb9adxp90vpkc8qb
source: write-time
topics:
  area:
    - topic-vocabulary:d1
  activity:
    - bugfix:d1
```
````

````markdown
## 2026-09-10 20:43 - Apply append-only hierarchy topic overrides

```yaml
entry_id: mse_35ptbbyvp0bf6sc7
source: write-time
topics:
  area:
    - topic-vocabulary:d1
  activity:
    - bugfix:d1
```
````
