---
schema_version: 2
adr_id: adr_fixture
title: Fixture authority
topics:
  - schema
created_at: 2026-01-01T10:00:00Z
user_initials: JNL
agent_type: codex
source: write-time
---

# Fixture authority

## Current view

Status: **Accepted**

Authoritative decision: `mse_0000000000000001:d1`

### Decision

Preserve authority.

### Reason

Parity requires it.

### Impact

The ADR is a curated projection.

### Constitution

- `constitution:v2.5#authority` (governing)

## Event ledger

### founded - 2026-01-01T10:00:00Z

```json
{"kind":"founded","event_id":"fixture-event","timestamp":"2026-01-01T10:00:00Z","source":"write-time","decision_ref":"mse_0000000000000001:d1","update_entry_id":"mse_0000000000000001","expected_authoritative_decision":null,"predecessors":[{"decision":"mse_0000000000000000:d1","relation_assertion":"evolves"}],"supporting_decisions":[],"matched_decisions":["mse_0000000000000001:d1"],"decision":"Preserve authority.","why":"Parity.","evolution":"Initial state.","reason":"Founding event.","replacement_adr":null,"constitution_refs":[{"ref":"constitution:v2.5#authority","role":"governing"}],"founding_source":"fixture","founding_quote":"Preserve authority.","impact":"Projection only.","impact_provenance":"first-hand","impact_evidence":"fixture","body_issues":[]}
```

