---
memory-system-version: 2.3
tags:
  - memory-seed
  - skill-registry
  - trigger-registry
---

# Skill Trigger Registry

This registry is the deterministic trigger map for universal Memory Seed skills. Read it during operating-mode startup, then lazy-load only the full skill files that match the active task.

```yaml
trigger_registry_version: 1
default_behavior:
  read_this_file_at_startup: true
  lazy_load_full_skills: true
  evaluate_order: listed
  load_every_matching_required_skill: true
  smallest_sufficient_skill_set: true
  ambiguity_policy: ask_when_durable
  local_registry_precedence: nearest_runtime_first
  inherited_parent_skills: apply_when_not_disabled_or_overridden_locally

skills:
  - skill: code_search.md
    required: true
    load_when:
      - source code exploration
      - symbol lookup
      - call path or dependency tracing
      - repository structure search
      - broad grep or full-file read would otherwise be used
    do_not_load_when:
      - task only touches memory control-plane docs
      - exact file path and required lines are already known

  - skill: data_architecture.md
    required: true
    load_when:
      - changing durable data structures
      - changing indexes or ranking behavior
      - changing schemas, persistence, cache format, or retrieval contracts
      - changing semantic memory extraction or scoring
    do_not_load_when:
      - documentation-only wording change with no data contract impact

  - skill: local_compilation.md
    required: true
    load_when:
      - validating local build, test, package, or CLI behavior
      - changing dependency or packaging configuration
      - reproducing a local failure
    do_not_load_when:
      - analysis-only task with no local validation needed

  - skill: memory_consolidation.md
    required: true
    load_when:
      - reviewing compact output
      - promoting session history into durable memory
      - reconciling sessions with index.md or policy.md
      - deciding whether long session logs need summarizing
    do_not_load_when:
      - appending a normal session entry only

  - skill: memory_doctor.md
    required: true
    load_when:
      - runtime health is uncertain
      - bootstrap completion is uncertain
      - migration or archive integrity is being checked
      - seed/live sync is being changed
      - control-plane repair is needed
    do_not_load_when:
      - ordinary implementation work in a healthy runtime

  - skill: release_publishing.md
    required: true
    load_when:
      - preparing or publishing a package release
      - changing release process, tags, changelog, or packaging metadata
      - verifying release workflow state
    do_not_load_when:
      - local-only development with no release impact

  - skill: security_triage.md
    required: true
    load_when:
      - security-sensitive code or policy changes
      - secrets, credentials, auth, permissions, user data, payments, network exposure, or destructive operations are involved
      - reviewing public-memory hygiene risks
    do_not_load_when:
      - task has no security, privacy, or destructive-operation surface
```

## Deterministic Use

Evaluate skills in the listed order. Load every matching required skill, but keep the loaded set as small as the task safely allows. A skill match means the agent must read that skill before acting on the matching part of the task.

For sub-projects, use the nearest runtime's registry first. Parent registries and parent skills apply only when inherited and not disabled or overridden in the local `index.md`.

If trigger confidence is ambiguous and the decision affects durable design, policy, bootstrap behavior, release behavior, memory structure, security, privacy, or destructive operations, ask the user before proceeding.
