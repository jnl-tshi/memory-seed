---
memory-system-version: 2.20
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
- **Constitutional conflict** - anything contradicting an invariant in the ratified Constitution
  declared by the active `.memory-seed/index.md`. Per its governance rules, such a change "is rejected or must first amend the
  invariant - it cannot silently override it". There is no tier below Stop here: an agent may not
  decide for itself that an invariant does not apply. Either the user grants live consent for a
  change that stays inside the invariant, or the invariant is formally amended first.
- **Incidental recorded-decision conflict** - the work would contradict an established decision
  recorded in a spec or the memory corpus, and the user's instruction does NOT explicitly target
  that decision's subject. Surface the conflict and the recorded rationale before proceeding
  (Propose-and-wait): the user may be unaware of the record, and you cannot tell a deliberate
  amendment from an unaware override without asking.

- **External / irrevocable communication** - remote pushes, pull-request or issue comments, emails,
  chat messages, public posts, or other visible external actions.
- **Financial** - payments, billing, pricing, invoices, subscriptions, or financial configuration.

### Reversing a recorded decision on live instruction is NOT a Stop

When the **current conversation's live instruction explicitly requests the very change a recorded
decision rejected or reversed**, the instruction is itself the amendment authority - Constitution
Invariant #2's mechanism for ordinary recorded decisions is "extend and supersede, never rewrite",
and a live explicit instruction is how a supersession starts. Recorded decisions are evidence, not
law; only constitutional invariants get the hard Stop above. Tier: **Proceed-and-flag**, with two
mandatory parts:

1. **Flag**: name the recorded decision in the reply and carry its `R:` forward, so the user
   decides with the old rationale in view rather than without it.
2. **Record**: append a superseding entry in the same turn, with a `replaces` or `evolves` edge to
   the decision being reversed (the three-way rule in `session_logging.md` decides which). The
   reversal is the most valuable decision to record - it retires a live record; skipping the entry
   leaves the store asserting the opposite of the code.

This path requires a live instruction in the current conversation. Unattended runs working from a
plan still park recorded-decision conflicts per "live consent" below.

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

## A Clean Result Is A Claim About The Instrument

When a new measurement comes back tidy, the tidiness is evidence about the measurement before it is
evidence about the subject. Verify the instrument produced the number before reporting the number.

Three grounds to distrust a result and test the measurement first:

- **Zero variance in a column.** A verdict that never appears may be unreachable rather than
  unearned. Test it with a negative control - deliberately corrupt an input and confirm the
  instrument catches it.
- **A metric that improved without a mechanism.** If nothing plausibly caused the change, suspect
  the counter, the parser, or the plumbing.
- **A complete-looking output built from an incomplete input.** Schemas that force a value per key
  will fill every slot whether or not the upstream stage produced anything.

Recorded instances, all from 2026-08-04/05 and all initially reported as clean results:

- A capture counter keyed on the DRAFT `### Decision` heading scored prose captures as silence, and
  manufactured a dose-response dip that did not exist.
- Judge prompts passed as argv were truncated by the Windows `.CMD` shim, so 56 of 60 blind
  judgements answered a fragment - while the keyed second stage, obliged by its schema to emit one
  verdict per key, filled in all of them. The resulting table looked complete and was fabricated.
- A relevance band tuned on a 7-entry fixture banded everything `strong`; at 836 entries it still
  banded everything `strong`, including nonsense queries, and the paired instruction told agents to
  answer from `strong` results and abstain only when a signal fired that never fires.
- A negative-control harness swallowed a CLI error as an empty verdict and reported a confident
  FAIL - "null instrument" - about a judge that was in fact working.

Each was caught by a human noticing something looked too tidy, which is not a control. The check
above is the cheap substitute: **before reporting a measurement, state what would make you distrust
it, and confirm that thing is not present.**

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
