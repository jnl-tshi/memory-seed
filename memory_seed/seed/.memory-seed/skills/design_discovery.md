---
memory-system-version: 2.20
tags:
  - memory-seed
  - skill
  - design-discovery
---

# Design Discovery Skill

Use this skill before making a consequential new product, architectural, data, safety, or workflow
choice, even when the resulting code change is small.

## Purpose

Make the choice inspectable before implementation commits the project to it. Discovery is evidence for
the existing plan and Task Packet path; it is not a parallel execution controller, task queue, or
authority system.

Routine work stays lightweight when it directly follows an already assessed decision whose scope,
constraints, and evidence still cover the work. Do not load this skill merely to repeat that assessment.
If the work creates a new consequential choice, changes the assessed scope, or makes the earlier evidence
stale, load it regardless of code size.

## Discovery Record

Capture a concise, proportionate record in the existing planning or decision surface. It must identify:

1. **Decision and scope** — the choice to make, affected users or systems, constraints, and the decision
   that is already settled versus what is genuinely open.
2. **Capability and reuse inventory** — existing code, skills, services, configuration, and supported
   workflows that may solve the need before a new mechanism is introduced. Record what was inspected and
   what is unavailable or unsuitable.
3. **Relevant authority and evidence** — current concern-owning files, applicable Constitution clauses,
   accepted ADR heads, and evidence from the codebase or prior work. Preserve the authority order:
   Constitution, current concern-owning control file, accepted ADR head, session evidence, then derived
   projection.
4. **Realistic alternatives** — viable approaches, including reuse or no change when credible. For each,
   name the material benefits, gaps, compatibility limits, cost, and operational or maintenance burden.
   Do not pad the record with straw alternatives.
5. **Selected option** — the chosen approach, its reason, unresolved assumptions, and the observable
   outcome that would show it is working.
6. **Trial decision** — whether to proceed directly, run a bounded trial, or stop for approval. Match the
   trial to uncertainty, reversibility, and blast radius; a reversible choice with direct evidence may
   proceed, while material uncertainty needs a time- or scope-bounded trial.

## Procedure

1. State the choice and check whether an already assessed decision covers it. If it does, use that
   decision and continue with routine implementation; do not create heavyweight discovery work.
2. Read the relevant current authority and retrieve prior rationale when it could change the option set.
   Treat search results and summaries as candidate evidence, not replacement authority.
3. Inventory capabilities and reuse paths before proposing a new component, policy, workflow, or data
   structure.
4. Compare only realistic alternatives. Make gaps, costs, and constraints explicit enough for a reviewer
   to understand why the selected option is proportionate.
5. Select an option and decide the smallest justified trial. Escalate for the existing risk, approval, or
   authority guard when the choice cannot safely proceed.
6. Carry the discovery record into the existing plan and Task Packet path: identify the selected option,
   evidence and authority consulted, scope, trial decision, assumptions, and invalidation conditions.
   The existing plan compiler and execution controls remain the only execution path.

## Handoff And Verification

- A plan derived from discovery should retain the selected option, evidence references, constraints,
  acceptance observables, and replan conditions.
- A Task Packet should receive that same assessed context when its existing compiler supports it; do not
  invent a second packet format or dispatch mechanism here.
- Verify the trial at the decision's actual risk level. Record whether evidence passed, failed, was
  unavailable, or requires a later review rather than treating an unrun check as support.

## Do Not Load When

- Routine, already assessed work follows a decision whose scope and evidence remain current.
- The task only executes an approved, detailed plan and introduces no consequential new choice.
- A narrow mechanical edit has no product, architecture, data, safety, or workflow decision to make.
