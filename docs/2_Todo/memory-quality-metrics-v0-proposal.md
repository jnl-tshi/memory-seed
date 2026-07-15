---
title: "Memory Quality Metrics v0 Proposal"
date: "2026-07-15"
project: "memory-seed"
status: "promoted-to-todo"
priority: "P1"
next_action: "Define a versioned read-only report schema, fixture populations, and a real-corpus baseline using the shipped ranking-ab result model, with no targets or behavioural effects."
related:
  - "docs/CONSTITUTION.md"
  - "docs/5_Completed/real-corpus-ranking-validation-gate-proposal.md"
  - "docs/3_Spec/memory-trace-derived-artifact-provenance-contract.md"
  - "docs/4_Reference/memory-seed-strategic-synthesis-report.md"
---

# Memory Quality Metrics v0 Proposal

Status: **PROMOTED to `2_Todo`** 2026-07-15; active read-only measurement proposal.
Priority: P1 after the shipped `ranking-ab` gate, before any quality label changes ranking or agent behaviour.
Source: JNL-approved constitutional hardening on 2026-07-15, extracting the measurable subset of Constitution section 8 and the strategic-synthesis report.
Next action: Specify deterministic metric populations and JSON fixtures, then record a real-corpus baseline before setting targets.

## Scope

Add one deterministic, local, read-only quality report over the current Markdown corpus and validated
derived artefacts. Each metric must declare its eligible population, numerator, denominator, exclusions,
and `not_applicable` behaviour.

## Non-goals

- No composite quality score.
- No telemetry, hosted upload, leaderboard, or cross-project comparison.
- No target thresholds before the baseline is measured.
- No automatic repair, deletion, mutation, ranking, or agent action.
- No claim that entry count, edge density, or activity volume proves product value.
- No undefined "stale memory" metric in v0.

## Dependencies

- the shipped `ranking-ab` output contract for ranking-regression cases;
- the canonical graph reader for inbound/outbound edge counts;
- the DRAFT entry parser and structural validation;
- [`memory-trace-derived-artifact-provenance-contract.md`](../3_Spec/memory-trace-derived-artifact-provenance-contract.md) for material-claim citations;
- the provenance/authority taxonomy for non-authored record coverage.

## Constitutional fit

Five-question contribution: **Validation + Trust + Retrieval**.

- Validation gains reproducible corpus health and coverage evidence.
- Trust gains honest denominators, exclusions, and `not_applicable` states.
- Retrieval gains an explicit regression rate from real-corpus A/B cases.

The report is a rebuildable projection over Markdown and validated artefacts. It never hides history,
changes ranking, or becomes authoritative project memory.

## Metrics v0

### 1. Unlinked entry rate

- **Population:** parseable session entries.
- **Counted:** entries with no inbound or outbound `related_entries`, `supersedes`, or `evolves` edge after sidecar folding.
- **Excluded:** none, but report counts by age band and entry format so old legacy entries are visible rather than silently normalised.
- **Interpretation:** an investigation queue, not proof that the entry is bad. A valid standalone entry may remain unlinked.

### 2. DRAFT reason coverage

- **Population:** entries using a `### Decision` or `### Decisions` DRAFT shape.
- **Counted:** decision records with every `D:` paired to a non-empty `R:` under the structural rules.
- **Excluded:** small-work entries that make no decision and legacy entries that predate DRAFT.
- **Interpretation:** format/evidence coverage only; it does not judge whether a reason is persuasive.

### 3. Generated-claim citation coverage

- **Population:** material claims in artefacts that conform to the derived-artifact provenance contract.
- **Counted:** material claims with one or more valid evidence references and freshness metadata.
- **Excluded:** presentation-only labels and artefacts outside the contract.
- **No population:** report `not_applicable`, never 100 percent.

### 4. Provenance coverage

- **Population:** non-authored graph/API records and generated artefacts in versioned fixtures or the current projection.
- **Counted:** records with `provenance_class`, `authority_class`, source identity, and revision/freshness where applicable.
- **Excluded:** authored memory whose source is the entry itself.
- **No population:** report `not_applicable`.

### 5. Ranking A/B regression rate

- **Population:** named query cases in a completed `ranking-ab` run.
- **Counted:** cases where enabling the candidate signal worsens the expected target or regresses a text-only/no-hit control.
- **Reported with:** total cases, improved, unchanged, regressed, and unscorable counts; never a percentage without those counts.
- **Interpretation:** a release gate for that signal, not a general retrieval-quality score.

## Output contract

Proposed surface:

```text
memory-seed quality report [--json]
```

The human report explains populations and exclusions. The versioned JSON shape includes:

```text
schema_version
corpus_revision
generated_at
metrics[].id
metrics[].status
metrics[].population
metrics[].numerator
metrics[].denominator
metrics[].excluded
metrics[].notes
```

`status` is `measured`, `not_applicable`, or `unavailable`. The report is deterministic for the same corpus,
revision, fixtures, and tool version apart from `generated_at`.

## Implementation sequence

1. Freeze the metric definitions and fixture populations.
2. Add a read-only report model and JSON schema.
3. Snapshot-test zero, legacy, mixed, and fully linked corpora.
4. Consume `ranking-ab` results without reimplementing its scoring logic.
5. Measure this repository and record the baseline as evaluation evidence under `docs/4_Reference/`.
6. Review usefulness before proposing targets, ESR surfacing, or additional metrics.

## Acceptance criteria

- Every metric declares population, numerator, denominator, exclusions, and no-population behaviour.
- Re-running against the same revision and fixtures yields the same measured values.
- Legacy and ineligible records remain visible in exclusions rather than disappearing.
- `not_applicable` is never rendered as perfect coverage.
- The command performs no writes and requires no network.
- No metric feeds ranking, filtering, automation, entitlement, or agent instructions in v0.
- Ranking metrics reuse `ranking-ab` output and include text-only/no-hit controls.
- Baseline evidence is recorded before targets or release gates beyond the existing ranking A/B gate are proposed.

## Promotion gate

Memory quality remains a Constitution section 8 candidate. After the v0 report ships and produces useful,
repeatable evidence, propose whether section 8 should graduate and which individual metrics deserve durable
targets. Do not promote the metric set merely because the command exists.
