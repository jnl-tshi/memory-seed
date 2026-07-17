---
memory-system-version: 2.18
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
- **Constitutional / architectural conflict** - anything contradicting a ratified invariant in
  `docs/CONSTITUTION.md`, or an established architectural decision recorded in a spec or the memory
  corpus. Per Constitution §11, such a change "is rejected or must first amend the invariant - it
  cannot silently override it". There is no tier below Stop here: an agent may not decide for itself
  that an invariant does not apply. Either the user grants live consent for a change that stays
  inside the invariant, or the invariant is formally amended first.
- **External / irrevocable communication** - remote pushes, pull-request or issue comments, emails,
  chat messages, public posts, or other visible external actions.
- **Financial** - payments, billing, pricing, invoices, subscriptions, or financial configuration.

### "In the current context" means live consent

**A recorded prior approval is not live consent.** A proposal's sign-off, a plan's `status:` or
`next_action:` field, an approving session entry, or a task the user queued days ago authorizes the
*work* - none of them authorize a STOP-category action taken later, unattended, on the user's behalf.

This matters most in **long-horizon and autonomous runs**, where the agent works from a plan rather
than a conversation and an approval is easy to read as broader than it was. The pull there is always
toward "this was approved, so I may proceed" - which is exactly how a locked file gets edited or an
invariant gets bent with nobody watching.

The test: *if the user is not present to say no right now, they have not said yes right now.*

When an unattended run reaches a STOP-category action, park the work, record the exact question, and
move on to other items - do not infer consent from the plan that scheduled the task. A prior approval
**is** sufficient for anything that is not a STOP category; this rule narrows nothing else. It only
stops stale approval standing in for a decision the user still owns.

## Procedure

1. Identify the action, affected files/systems, reversibility, and whether the user already
   authorized this class of work.
2. If it is a STOP category, ask *when* that authorization was given. Live in this conversation ->
   proceed. Recorded in a plan, proposal, or older session -> that is not consent for this action;
   park it.
3. Pick the lowest-risk tier that accurately describes the action.
4. For Proceed-and-flag, state the assumption and validation without stopping momentum.
5. For Propose-and-wait, provide one concrete plan with tradeoffs and wait.
6. For Stop, do not perform the action. Explain the STOP category and ask for explicit approval or a
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
