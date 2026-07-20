---
memory-system-version: 2.18
tags:
  - memory-seed
  - proposal
  - personas
  - end-of-turn
---

# ESR Persona Usage Check — propose deactivating active-but-unused personas

Status: **SHIPPED 2026-07-20** — approved 2026-07-14; promoted from Inbox (`2_Todo`).
Priority: P2 — keeps the active-persona set honest so startup + worker load stay lean; approval-gated, low blast radius.
Next action: **Done** — the "Persona Usage Check" step landed in `.memory-seed/skills/end_of_turn.md`
(step 17, its own subsection) and `agent-rules.md`'s "End Of Turn" summary, both mirrored to the seed
twins. Remaining optional sub-item: the deterministic `memory-seed persona usage [--days N] [--json]`
report, sequenced as a follow-up now that the prose step exists.
Dependencies: none hard. Companion to `../5_Completed/worker-context-minimisation-proposal.md` (shared provenance; **landed 2026-07-17**).
Scope: control-plane — `end_of_turn.md`, `agent-rules.md`, seed twins; optional `persona usage` CLI report + tests. Out of scope: any auto-apply / deletion path.
Open decision for the user: this is designed **propose-and-wait** (never auto-deactivate), consistent with every other persona step. If automatic deactivation on detection is wanted instead, that changes the design — resolve before build.
Source: The two-axis persona/orchestration evaluation (`mse_y7nhd5hcpwa0qb51`). User: persona slimming is key "but needs to be well thought through — it should be part of the ESR so that active personas that aren't used get turned off."

## Problem — the active-persona set only grows

A persona in `.agents/_registry.yaml` stays `status: active` indefinitely once activated, whether or not any session ever selects it. Every active persona is load surface — at primary startup (`agent-rules.md` step 10 loads *all* active personas) and, until the companion contract lands, inside every worker too. Nothing ever retires an active-but-unused persona; there is a path **in** (bootstrap activation, unregistered-persona onboarding) but no path **out** short of the user remembering to hand-edit the registry.

This repo is the live example: four personas are active (solo-founder, developer, content-creator, copywriter), but recent session logs show `agent_name` almost always resolves to `developer` (or `null`). copywriter and content-creator may be earning their activation — or may be dead weight. There is no mechanism that ever asks.

## Current behavior (grounded)

`end_of_turn.md` already runs three persona-adjacent closeout steps, **all user-approval-gated**:

- **Persona Evolution Check** (step 13) — improve an *active* persona.
- **Skill Evolution Check** (step 14) — add a role-specific skill.
- **Unregistered persona check** (step 15) — a persona *file used but missing from the registry* → onboard it.

Step 15 handles **used-but-not-registered → activate**. There is **no inverse**: **registered-active-but-unused → deactivate**. The mechanism to act on it already exists — `_registry.yaml` supports `status: active|inactive` (researcher and sales-rep already sit `inactive`) — nothing drives the transition.

## Proposal — add a "Persona Usage Check" ESR step (the symmetric inverse of step 15)

Add to `end_of_turn.md`, the `agent-rules.md` "End Of Turn" list, and their seed twins:

- **Detect** active personas with **no `agent_name` usage across a window** (default: the last ~30 days *or* ~20 session entries, whichever is longer; configurable).
- **Propose** flipping each unused active persona to `status: inactive` in `_registry.yaml`, showing the evidence (last-seen date, usage count in window).
- **Approval-gated, propose-and-wait** — identical gate to Persona Evolution. Never auto-applies.
- **Deactivation is not deletion.** The `.agents/<slug>.md` file stays; only `status` flips; reactivation is a one-line flip back. (Mirrors the memory system's supersede-don't-delete rule.)

### The subtleties (why this "needs to be well thought through")

1. **The signal is lossy — bias conservative.** `agent_name` is recorded only when a persona is active *and* the entry logs it; many solo entries are `agent_name: null`. A null-agent entry is **neither** evidence of use **nor** of non-use. So "unused" must require a *long* window of positive absence, and the check must prefer a false *keep* over a false *deactivate*.
2. **Grace period.** Never flag a persona activated or created inside the window — a just-added persona hasn't had a chance to be used.
3. **Deactivate, never delete; reactivation is trivial.** This makes the whole step low-risk: the cost of a wrong deactivation is one flip back.
4. **Occasional-use personas.** A persona used monthly (e.g. copywriter for a launch) should survive a monthly window — hence the conservative default and configurability, not an aggressive threshold.
5. **Solo vs. team.** With one human the signal is weak; the check should degrade to a gentle "these N personas show no recorded use in the window — keep them active?" rather than a confident retirement recommendation.

### Optional deterministic backing (P2 sub-item)

A `memory-seed persona usage [--days N] [--json]` report — counts `agent_name` occurrences per active persona over the window (same pattern as the `memory-seed esr` preflight) so the ESR step reads a number instead of eyeballing logs. The ESR step works as guidance even without it; the tool just makes it deterministic and testable.

## Non-goals

- **Never auto-deactivates** and **never deletes** a persona file.
- Does not touch already-`inactive` personas.
- Does not change the Persona Evolution, Skill Evolution, or Unregistered-persona steps — it complements them as the fourth persona-lifecycle step.
- Does not decide *which* personas this repo should keep — it installs the recurring mechanism; the first run's recommendations are the user's call.

## Acceptance criteria

- `end_of_turn.md` gains a **"Persona Usage Check"** step, and `agent-rules.md` "End Of Turn" lists it; seed twins match (live/seed parity test green).
- The step is explicitly approval-gated and conservative (long window, grace period, deactivate-not-delete, lossy-signal note).
- (Optional) `memory-seed persona usage` report with tests covering the window, the `agent_name: null` case, and the grace period.

## Relationship to existing coverage (checked)

- No prior proposal or session decision covers unused-persona deactivation (memory search on persona deactivation/usage returned only the *unregistered* onboarding path and unrelated worktree/ranking work) — genuinely uncovered.
- Companion: `../5_Completed/worker-context-minimisation-proposal.md` (shipped 2026-07-17) — fewer active personas directly lightens both worker and primary startup load; the two share the `mse_y7nhd5hcpwa0qb51` provenance and the `mse_jh2n9x7p5bq4r6cd` friction.
- Frames as the mirror of `end_of_turn.md` step 15 (unregistered-persona onboarding), so it slots into an established, approval-gated pattern rather than introducing a new gate.
