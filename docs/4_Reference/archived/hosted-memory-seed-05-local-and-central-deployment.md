---
title: "Archived source — 05-local-and-central-deployment"
source_path: "docs/1_Inbox/memory-seed-hosted-proposals/05-local-and-central-deployment.md"
captured_on: "2026-09-18"
extracted_into: "docs/2_Todo/hosted-memory-mvp-programme.md"
archive_note: "Copied from the primary checkout without deleting or modifying the untracked original; superseded assumptions are preserved as source evidence."
---

# Proposal 5 — Local and Centrally Hosted Memory Seed Server

## Objective

Support both locally hosted and centrally hosted Memory Seed deployments using the same application architecture and API.

Avoid building distributed synchronization into the first release.

---

## Core Architecture

```text
Agent / Hook
     |
     v
Memory Seed API
     |
     +-------------------+
     |                   |
     v                   v
Local Server         Hosted Server
     |                   |
PostgreSQL           PostgreSQL
+ pgvector           + pgvector
     |                   |
Curator              Curator
```

The client integration should not care where the server runs.

---

## Stable API Boundary

Hooks and agents should call a stable Memory Seed API such as:

```text
POST /events
POST /search
GET  /decisions
POST /curator/jobs
```

Deployment becomes configuration:

```text
MEMORY_SEED_URL=http://localhost:8080
```

or:

```text
MEMORY_SEED_URL=https://api.memoryseed.example
```

---

## Local Deployment

Recommended initial packaging:

```text
Docker Compose
├── memory-seed-api
├── curator-worker
└── postgres + pgvector
```

A local deployment can support:

- private raw conversation logs
- local embeddings
- local curator models
- API-based curator models
- fully offline deployments later

---

## Hosted Deployment

The centrally hosted version can provide:

- managed PostgreSQL
- managed pgvector
- managed curator jobs
- managed model routing
- shared-team access
- central governance records
- backups and operational monitoring

---

## Hybrid Mode

Design for hybrid operation, but do not implement full bidirectional synchronization in the MVP.

Potential future data classes:

```text
local_only
sync_allowed
central_only
```

Example:

```text
raw conversations         -> local_only
derived decisions         -> sync_allowed
topics / edges            -> sync_allowed
team ADRs                 -> central
organisation Constitution -> central
```

---

## Migration Path

Recommended phases:

```text
Phase 1
Local OR hosted

Phase 2
Export/import

Phase 3
Selective sync

Phase 4
True hybrid federation
```

This avoids early complexity around:

- conflict resolution
- offline edits
- tenancy
- deletion semantics
- identity
- multi-master replication

---

## Success Condition

The same Memory Seed server and curator codebase can run locally or centrally, with deployment selected by configuration rather than by separate product architectures.
