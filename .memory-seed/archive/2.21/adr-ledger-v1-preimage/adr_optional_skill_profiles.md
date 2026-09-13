---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_optional_skill_profiles
title: Optional external-tool skills ship in a profile, never core
topics:
  - skill-architecture
  - control-plane
created_at: 2026-08-09T08:41:26Z
user_initials: JNL
agent_type: claude
source: write-time
---

# Optional external-tool skills ship in a profile, never core

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

A skill that wraps an external tool ships in a named install profile, not in CORE_SKILL_NAMES. Registration is a checklist: the profile, SKILL_DESCRIPTIONS, pyproject package-data, and the seed-file install-list test.

### Why

A bare init must not install a runbook for tooling most projects lack. CORE_SKILL_NAMES is reserved for universal memory-workflow skills; code_search.md and graphify_analysis.md both wrap external tools (Semble, the Graphify CLI) and belong to the coding profile. The registration checklist is one concern because missing any step leaves a skill that exists but never installs - which is how superpowers_integration.md was silently unregistered.

### How it evolved

Founded from the 2026-08-04 decision that completed graphify_analysis.md's registration and found superpowers_integration.md missing by the same route.

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-09T08:41:26Z

```json
{
  "decision_ref": "mse_y7d6qtjgqdfhtmaj:d2",
  "event_id": "adre_e5aadaa764d24872315b",
  "source": "write-time",
  "update_entry_id": "mse_y7d6qtjgqdfhtmaj"
}
```

#### Decision

A skill that wraps an external tool ships in a named install profile, not in CORE_SKILL_NAMES. Registration is a checklist: the profile, SKILL_DESCRIPTIONS, pyproject package-data, and the seed-file install-list test.

#### Why

A bare init must not install a runbook for tooling most projects lack. CORE_SKILL_NAMES is reserved for universal memory-workflow skills; code_search.md and graphify_analysis.md both wrap external tools (Semble, the Graphify CLI) and belong to the coding profile. The registration checklist is one concern because missing any step leaves a skill that exists but never installs - which is how superpowers_integration.md was silently unregistered.

#### Evolution

Founded from the 2026-08-04 decision that completed graphify_analysis.md's registration and found superpowers_integration.md missing by the same route.
