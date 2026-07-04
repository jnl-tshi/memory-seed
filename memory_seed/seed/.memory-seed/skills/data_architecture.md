---
memory-system-version: 2.15
tags:
  - memory-seed
  - skill
  - data-architecture
---

# Data Architecture Skill

Use this skill when designing or changing durable data structures, storage layout, schemas, indexes, migrations, or retrieval behavior.

## Inputs

- Current data model or file layout.
- Query and update patterns.
- Migration, compatibility, and rollback constraints.
- Privacy or retention requirements.

## Procedure

1. Define the entities, ownership boundaries, and lifecycle.
2. Identify read/write paths and consistency requirements.
3. Choose the smallest structure that supports current access patterns.
4. Define migration and rollback behavior before implementation.
5. Add tests or fixtures that prove compatibility and retrieval behavior.

## Output

- Proposed structure and ownership.
- Compatibility notes.
- Migration or backfill plan.
- Verification commands and expected behavior.
