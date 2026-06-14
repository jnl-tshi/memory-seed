---
memory-system-version: 2.7
tags:
  - memory-seed
  - skill
  - security-triage
---

# Security Triage Skill

Use this skill when reviewing a change, report, dependency, or workflow for security impact.

## Inputs

- Files or diff under review.
- Trust boundary or data-flow description.
- Known user, credential, network, filesystem, or release exposure.

## Procedure

1. Identify assets, actors, trust boundaries, and external inputs.
2. Trace candidate risks from source to sink.
3. Classify each risk as confirmed, plausible, or not supported.
4. Prefer concrete exploit paths over generic best-practice advice.
5. Recommend minimal fixes and targeted verification.

## Output

- Findings first, ordered by severity.
- File and line references where possible.
- Clear residual risk and test gaps.
- No secrets or sensitive raw data in the memory log.
