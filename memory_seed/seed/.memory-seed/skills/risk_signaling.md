---
memory-system-version: 2.15
tags:
  - memory-seed
  - skill
  - risk-signaling
  - stop-triggers
---

# Risk Signaling Skill

Use this skill when a task may be ambiguous, destructive, irreversible, security-sensitive,
externally visible, financial, or likely to touch shared control-plane state.

## Purpose

Choose an action tier from observable risk, not numeric confidence. Use reversibility, blast radius,
authorization, shared-state impact, security exposure, and external visibility to decide whether to
act, flag an assumption, propose a plan first, or stop.

## Action Tiers

- **Proceed** - the action is routine, reversible, explicitly requested, and follows established
  project patterns.
- **Proceed-and-flag** - the action is reversible but non-trivial; proceed while naming the
  assumption, expected impact, and validation.
- **Propose-and-wait** - the action is ambiguous, underspecified, broad, or outside the user's
  explicit authorization; present a concrete plan and wait for approval.
- **Stop** - the action matches a STOP category below; explain the risk, give concrete options, and
  wait for explicit approval before acting.

## STOP Categories

Stop before taking an action in any of these categories unless the user has explicitly authorized
that exact class of action in the current context:

- **Destructive** - deletes files, branches, data, or uncommitted work.
- **Irreversible** - force-pushes, hard resets, release publication, package/name publication,
  migrations, or format changes that are hard to unwind.
- **Security / trust boundary** - credentials, authentication, authorization, permissions,
  encryption, privileged network dependencies, or user-data exposure.
- **Shared / control-plane state** - routing files, `.memory-seed/` control files, skill registry
  entries, seed templates, lockfiles, or session/memory files outside the assigned scope.
- **External / irrevocable communication** - remote pushes, pull-request or issue comments, emails,
  chat messages, public posts, or other visible external actions.
- **Financial** - payments, billing, pricing, invoices, subscriptions, or financial configuration.

## Procedure

1. Identify the action, affected files/systems, reversibility, and whether the user already
   authorized this class of work.
2. Pick the lowest-risk tier that accurately describes the action.
3. For Proceed-and-flag, state the assumption and validation without stopping momentum.
4. For Propose-and-wait, provide one concrete plan with tradeoffs and wait.
5. For Stop, do not perform the action. Explain the STOP category and ask for explicit approval or a
   safer alternative.

## Interactions With Other Skills

- Security / trust boundary STOP items should route through `security_triage.md` when analysis or
  mitigation is needed.
- Shared / control-plane STOP items in multi-agent work align with `agent_collaboration.md` conflict
  escalation; the orchestrator or human owns those writes unless a worker packet explicitly assigns
  them.
- Proposal lifecycle, release publishing, and data-architecture tasks may still proceed when already
  authorized, but the tier should be stated when the change has broad or hard-to-reverse impact.

## Output

- Chosen tier: Proceed, Proceed-and-flag, Propose-and-wait, or Stop.
- One-sentence reason tied to reversibility, blast radius, authorization, or trust boundary.
- Required approval, validation, or fallback, if any.
