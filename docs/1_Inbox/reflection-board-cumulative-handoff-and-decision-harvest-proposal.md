---
title: Reflection Board cumulative handoff and decision harvest
status: inbox-unassessed
source: "JNL design discussion, 2026-09-08"
next_action: "Assess the proposal against the current Reflection Board transaction contract before promotion to Todo."
---

# Reflection Board cumulative handoff and decision harvest

## Problem

Reflection Board v1 proves sequential, tamper-evident lifecycle mechanics, but its first real board was
thin as a reasoning artifact. The ledger is not yet a dependable cumulative handoff: later phase owners
are not mechanically given the current synthesis, mistakes and repairs are not structured, and closeout
does not yet treat the full chain as first-class evidence for drafting durable decisions.

## Proposed use gate

Use a Reflection Board only when all three statements are true:

1. the work contains a consequential choice worth preserving;
2. the choice is unresolved when the task begins; and
3. implementation or review evidence could materially change the answer.

Explicit user direction may require or waive a board. Task size, agent count, or a desire to create
more commentary is not sufficient by itself.

## Proposed record contract

Each phase appends its own evidence and a compact cumulative handoff snapshot. The objective is accurate
updating, not novelty. A phase classifies its effect on the prior position as `confirmed`, `narrowed`,
`strengthened`, `weakened`, `overturned`, `unresolved`, or `no-material-update`, with evidence.

The contribution records:

- evidence examined and findings;
- alternatives or questions still alive;
- mistakes observed, their cause, remedy, verification, and recurrence guard;
- new ideas, each with a stable board-local idea identifier and an explicit relationship to an earlier
  idea when one exists; and
- what the next phase must test.

The cumulative snapshot is a self-contained synthesis of the current position, live alternatives,
uncertainties, known mistakes and repairs, and next checks. It may honestly remain unchanged.

## Mechanical handoff

The next Task Packet should inject the latest cumulative snapshot, its parent record identity and digest,
active risks, open questions, recurrence guards, and required next checks. The receiving phase reads the
snapshot as its minimum context and consults earlier records where the packet or task requires it.

Review and closeout must reread the full chain and compare it with the final snapshot. This detects
summary drift and prevents a rolling synthesis from silently dropping an earlier constraint.

## Local-first idea lineage and retrieval

Search first within the current board and chain for explicit idea relationships, then expand through the
normal relevance lookup across the wider corpus. Board membership narrows the search space; it does not
prove that two ideas evolve from one another.

## Decision harvest

At closeout, the full board is first-class evidence for drafting the ordinary durable session decision.
The final snapshot provides the starting synthesis; earlier contributions show how the answer changed and
which alternatives were rejected. The durable decision remains authoritative. Existing member and closure
receipts preserve traceability from that decision back to every temporary board record.

## Delivery sequence

1. Repair ESR so fenced Reflection receipt evidence is not parsed as duplicate session headers.
2. Specify and validate the use gate, update-effect vocabulary, contribution fields, and cumulative snapshot.
3. Compile the latest snapshot mechanically into successor Task Packets and enforce parent/digest binding.
4. Add full-chain drift review and decision-harvest guidance with receipt coverage for every member.
5. Add board-local idea identities and local-first, corpus-second retrieval.
6. Add anti-gaming checks: evidence support, honest `no-material-update`, and independent review.
7. Mature retention and trust separately: exercise real compaction after the retention window, define
   key rotation and recovery, and keep privacy-grade deletion out of scope unless separately designed.
8. Evaluate comparable work with and without the richer board, measuring repeated mistakes, decision
   accuracy, summary drift, time/cost, and unnecessary reflection.

## Non-goals

- Replacing the trusted Reflection transaction writer or durable session decision log.
- Rewarding disagreement, verbosity, or a manufactured reasoning delta.
- Treating same-board membership as proof of idea lineage.
- Making every task use Reflection.
- Claiming privacy-grade erasure from Git-backed retention.

## Acceptance questions for assessment

- Can a phase proceed from the injected snapshot without losing a live constraint?
- Does the full-chain check detect deliberate and accidental summary drift?
- Can an implementer record a mistake and verified remedy in a form later agents actually receive?
- Can closeout draft a complete durable decision while retaining exact member receipts?
- Does controlled evaluation show fewer repeated mistakes or better decisions without disproportionate cost?

## Research position

The design is consistent in spirit with iterative reflection, feedback-driven refinement, tool-grounded
critique, and action/reasoning traces. Its evidence requirements also address published cautions that
unsupported intrinsic self-correction can make model reasoning worse. The transaction, receipt, cumulative
handoff, and retention layers are governance extensions; their benefit must be established by the proposed
controlled evaluation rather than assumed.
