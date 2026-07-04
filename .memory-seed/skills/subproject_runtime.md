---
memory-system-version: 2.15
tags:
  - memory-seed
  - skill
  - subproject-runtime
---

# Sub-Project Runtime Creation Skill

Use this skill when creating, repairing, or reviewing a nested `.memory-seed/` runtime, inheritance choices, bootstrap target boundaries, or parent/root summary.

## When To Create A Runtime

Create a nested `.memory-seed/` runtime only when a sub-project has distinct long-lived context, policy, workflows, risks, outputs, or memory needs. Do not create a sub-project runtime just because a folder exists.

Good signals include:

- the sub-project can be opened or worked independently
- it has its own release, artifact, build, or deployment lifecycle
- it has local policies, risks, agents, or skills that differ from the root
- root session history would become noisy if all local work were logged there

Ask the user before creating a nested runtime unless they explicitly requested sub-project memory setup.

## Creation Workflow

1. Confirm the target path and that it is the intended bootstrap target boundary.
2. Initialize Memory Seed from that target path.
3. Bootstrap from local files and targeted user answers.
4. Record local inheritance choices in the sub-project `index.md`.
5. Keep active state and sessions local to the sub-project.
6. Record the nested runtime's existence and purpose in the parent or root `index.md`.
7. Record a parent/root summary only when the new runtime changes parent-visible topology, shared design, release behavior, policy inheritance, cross-project dependencies, risks, or active priorities.

Sub-project runtimes do not need their own root `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md` unless the sub-project is meant to be opened independently as a repository.

## Inheritance Choices

Default choices:

- Policy: inherit parent policy unless locally disabled.
- Skills: inherit parent skills unless locally disabled or overridden.
- Active state: local only.
- Sessions: local only.

Record deviations explicitly in the sub-project `index.md`. If parent and local rules conflict and inheritance intent is unclear, ask the user before applying the conflicting rule.

## Parent Or Root Summary

Write a parent/root summary when sub-project work changes something the parent runtime must know to route future agents correctly. Keep the summary brief and point to the sub-project runtime for local details.
