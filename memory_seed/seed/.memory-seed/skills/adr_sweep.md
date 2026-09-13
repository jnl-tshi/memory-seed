---
memory-system-version: 2.21
governing_adr: adr_session_decision_authority
tags:
  - memory-seed
  - skill
  - adr-sweep
---

# ADR Sweep Skill

Use this skill for a corpus-wide review of living ADR coverage and freshness. The sweep is an
evidence-and-recommendation workflow: it discovers review candidates mechanically, attaches an
advisory recommendation to every potential ADR, and leaves promotion, attachment, revision, and
head movement behind a human approval gate.

## Inputs And Coverage

Run `memory-seed esr` (use `--json` when preparing review packets) and read all three ADR views:

- **ADR attachment candidates** ask which recorded decisions may belong to an ADR that carries none.
- **ADR review queue** asks whether a `refines` successor means an ADR head should be revised or
  recorded as reviewed-no-change.
- **ADR sweep candidates** ask the inverse coverage question: which same-area decision lineage has
  no ADR, or has grown beyond the membership an ADR currently claims?

The inverse check normalises decision-level `evolves` and `replaces` lineage, keeps edges whose
endpoints share a declared area, and groups connected decisions. ADR claims include founding and
revision membership plus supporting/context decisions. This is a derived projection: session
decisions remain evidence authority and ADRs remain curated authority.

## Recommendation Contract

Every discovered potential ADR must be presented with a recommendation containing an action, target
decision, rationale, and explicit advisory status. Never present a bare candidate list.

- `unclaimed-chain` (3+ decisions): recommend `review-for-adr-promotion` at the derived head. The
  basis is the count, shared area, recorded lineage, and absence of any ADR claim.
- `unclaimed-pair` (2 decisions): recommend `architectural-review-before-promotion`. A pair is useful
  evidence but too weak for automatic founding.
- `grown-chain`: recommend `review-membership-or-split`. State which ADRs claim the chain and which
  members remain unnamed; the reviewer decides whether to attach them or found a separate concern.

Recommendations do not rank hidden evidence and do not confer status. Show the chain members and
claim evidence before asking for a decision. ESR and workers never create an ADR, attach a member,
transition status, or move an authoritative head.

## Orchestration

Use the lowest level that fits the measured queue.

### Level 1 — single orchestrator (default)

For fewer than 20 unresolved candidates, one agent reviews the full queue and presents one
human-readable batch. This is the default because a small list benefits from cross-candidate
consistency more than fan-out. The orchestrator may use deterministic filters and local retrieval,
but keeps all judgment in one context.

### Level 2 — bounded read-only fan-out (conditional)

Fan out only when the unresolved queue reaches 20, or when the candidates divide into cleanly
separable topic domains that materially reduce review cost. Fan-out requires the user's request or
approval and a host that permits subagent delegation. Give each worker one concern packet or one
non-overlapping domain; workers are read-only and return evidence plus the required recommendation.
They do not edit memory, ADRs, sidecars, branches, or shared control-plane files.

One orchestrator owns reconciliation: deduplicate overlapping chains, resolve conflicting
recommendations by holding them for human review, verify refs and quoted evidence, and present the
surviving batch. Fan-out changes review capacity, never authority.

## Procedure

1. Run `memory-seed esr --json` and retain the complete ADR queues; do not inspect only the first
   candidate.
2. Re-resolve every cited decision and ADR. Drop dangling or malformed packets and report the
   mechanical failure rather than guessing.
3. Attach the recommendation contract above to every potential ADR. For existing ADR head reviews,
   recommend either authored revision or reviewed-no-change and state the evidence for that choice.
4. Present candidates grouped by type, with members, claims, recommendation, rationale, and any
   uncertainty. Ask the user to approve, edit, defer, or reject dispositions.
5. After approval, perform writes sequentially in an isolated worktree using the normal `adr
   promote`, `adr revise`, `adr transition`, or `adr reviewed` flows. Dry-run where supported and
   never bypass expected-state guards.
6. Re-run `memory-seed esr`, `memory-seed adr check`, and `memory-seed links check`. A completed
   sweep explains every remaining candidate as accepted work, deliberate deferral, or rejected
   evidence; it does not silently hide unresolved items.

## Output

The review handoff must state:

- queue counts by candidate type
- the orchestration level used and why
- each candidate's evidence and attached recommendation
- the user's disposition, when supplied
- validation results for any approved writes
