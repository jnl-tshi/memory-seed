---
memory-system-version: 2.15
tags:
  - memory-seed
  - proposal
  - risk-signaling
  - stop-triggers
  - agent-guidance
---

# Risk Signaling and STOP Triggers Plan

> **Status:** IMPLEMENTED - completed 2026-07-05. The live and seeded `risk_signaling.md` skill now
> exists, is registered, and is cross-referenced from collaboration/security guidance.
> **Priority:** P1b - low-code control-plane guidance that should land before more mutation or
> automation work, especially `link add`, fanout scaffolding, package publication, or external
> communication flows.
> **Source:** [`confidence-signaling-protocol-proposal.md`](confidence-signaling-protocol-proposal.md)
> and [`stop-trigger-taxonomy-proposal.md`](stop-trigger-taxonomy-proposal.md),
> derived from the competitor-analysis follow-up in
> [`../../4_Reference/memory-trail-competitor-analysis.md`](../../4_Reference/memory-trail-competitor-analysis.md).
> **Scope:** Add vendor-neutral agent guidance for when to proceed, flag, propose-and-wait, or stop;
> define STOP categories; wire the guidance into lazy-skill routing and relevant existing skills.
> **Non-goals:** No numeric confidence percentages. No emoji protocol. No new session-entry YAML
> fields. No automated hook/gate. No project.yaml extensibility until a real downstream need appears.
> **Dependencies:** `.memory-seed/agent-rules.md`, `.memory-seed/skills/index.md`,
> `.memory-seed/skills/agent_collaboration.md`, `.memory-seed/skills/security_triage.md`, and seed
> twins under `memory_seed/seed/`.
> **Acceptance criteria:** see below.

## Decision

Create one lazy-loaded skill, `.memory-seed/skills/risk_signaling.md`, rather than two
separate skills. The confidence tier and STOP taxonomy are one operating system:

## Implemented 2026-07-05

- Added `.memory-seed/skills/risk_signaling.md` and the seed twin.
- Registered the live and seeded trigger registries for ambiguous, destructive, irreversible,
  externally visible, financial, high-blast-radius, and shared-control-plane actions.
- Added a Working Principles pointer in live and seed `agent-rules.md`.
- Cross-referenced Shared/control-plane STOP handling from `agent_collaboration.md`.
- Cross-referenced Security / trust boundary STOP handling from `security_triage.md`.
- Wired the new seed file into `SEED_FILES`, package data, and regression tests.

- **Proceed** - routine, reversible, matches established repo patterns.
- **Proceed-and-flag** - reversible but non-trivial; act and state the assumption.
- **Propose-and-wait** - ambiguous, underspecified, or outside explicit authorization.
- **Stop** - matches a STOP category; explain the risk, present concrete options, wait for explicit
  approval.

STOP categories:

- **Destructive** - deletes files, branches, data, or uncommitted work.
- **Irreversible** - force-pushes, hard resets, releases, schema/format migrations, published-name
  changes.
- **Security / trust boundary** - credentials, auth, permissions, encryption, privileged networked
  dependencies.
- **Shared / control-plane state** - routing files, `.memory-seed/` control files, skill registry,
  seed templates, lockfiles, session/memory files outside assignment.
- **External / irrevocable communication** - remote pushes, PR/issue comments, emails/messages,
  public posts, release publication.
- **Financial** - payments, billing, pricing, or financial configuration.

## Rationale

The source competitor idea was useful, but its percentage arithmetic is false precision. Memory Seed
should use observable factors - reversibility, blast radius, shared state, security exposure, and
external visibility - rather than self-reported numeric confidence. This keeps the guidance portable
across Codex, Claude, Gemini, Cursor, Copilot, and future file-reading agents.

## Implementation Outline

1. Add `.memory-seed/skills/risk_signaling.md` and the seed twin.
2. Register the skill in `.memory-seed/skills/index.md` and the seed registry with triggers for
   ambiguous, destructive, irreversible, security-sensitive, externally visible, financial, and
   shared-control-plane actions.
3. Add one Working Principles bullet in `.memory-seed/agent-rules.md` and seed twin pointing to the
   risk-signaling skill.
4. Cross-reference from `agent_collaboration.md` Conflict Escalation: its shared-file list is the
   Shared/control-plane STOP category.
5. Cross-reference from `security_triage.md`: a Security STOP is one path into security triage.
6. Add focused seed/live parity and doctor/skill-registry tests if the seed inventory changes.

## Acceptance Criteria

- The live and seeded `risk_signaling.md` skill exist and match.
- The live and seeded skill registries route the correct triggers to `risk_signaling.md`.
- Working Principles name the qualitative tiers without percentages or emoji.
- `agent_collaboration.md` and `security_triage.md` reference the relevant STOP categories without
  duplicating the full taxonomy.
- No new structured session schema field is introduced.
- Tests covering seed inventory/parity and skill registration pass.
- `memory-seed links check` and `memory-seed doctor` remain clean.

## Deferred Questions

- Whether future consuming projects need their own project-specific STOP categories.
- Whether tightly scoped worker packets may pre-authorize a specific STOP category. Default remains
  escalate to the orchestrator/human unless explicitly authorized.
- Whether a small example bank should live in the skill or a separate reference appendix.
