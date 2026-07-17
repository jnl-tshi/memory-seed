---
title: "Memory quality v0 — first real-corpus baseline"
date: "2026-07-17"
project: "memory-seed"
kind: report
measured_at_revision: "bc9b1740bee1d9e797aebd942d2fe9401c9408af"
related:
  - "docs/2_Todo/memory-quality-metrics-v0-proposal.md"
  - "docs/CONSTITUTION.md"
---

# Memory quality v0 — first real-corpus baseline

Evidence, not a scorecard. The v0 proposal requires a baseline **before** any target is proposed
(*"No target thresholds before the baseline is measured"*), and Constitution §8 (Memory quality) is still
a **[candidate]** clause. This is the measurement that lets a later proposal argue about targets from
data instead of intuition. Nothing here gates anything.

Reproduce with `memory-seed quality report [--json]` at the revision below. The report is read-only and
deterministic apart from `generated_at`.

- **Corpus revision:** `bc9b1740bee1d9e797aebd942d2fe9401c9408af`
- **Measured:** 2026-07-17
- **Schema:** v1

## Results

| Metric | Status | Value | Population | Excluded |
|---|---|---|---|---|
| `unlinked_entry_rate` | measured | 95/431 (22.0%) | 431 | 0 |
| `draft_reason_coverage` | measured | 403/403 (100.0%) | 403 | 28 |
| `generated_claim_citation_coverage` | unavailable | — | 0 | 0 |
| `provenance_coverage` | unavailable | — | 0 | 0 |
| `ranking_ab_regression_rate` | not_applicable | — | 0 | 0 |

### Unlinked entries — 22.0% (95/431)

Unlinked by age band: **0–30d: 15 · 31–90d: 80 · 90d+: 0**.

Read this as an investigation queue, not a defect count — a genuinely standalone entry is legitimately
unlinked. The distribution is the interesting part: the bulk (80) sits in the 31–90d band while only 15
are recent. That is consistent with lifecycle-link discipline tightening over time (write-time
`supersedes`/`evolves` authoring, `link suggest`, the `link audit` sidecar scaffold) rather than with a
corpus that is decaying. **Do not act on this number yet** — the v0 gate is "review usefulness before
proposing targets".

### DRAFT reason coverage — 100% (403/403), 28 excluded

Every entry that records a decision pairs each `D:` with a non-empty `R:`. This is expected rather than
flattering: the DRAFT lint refuses malformed decision records at `session append` time, `links check`
audits the same rule corpus-wide, and six historical entries were reformatted when it shipped. The
metric therefore confirms the write-time gate is holding; it is not independent evidence that reasons
are *good* — it measures structure only.

The 28 excluded entries record no decision (summaries, notes, legacy pre-DRAFT entries). They are
excluded from the denominator rather than counted as failures, and remain visible in `excluded`.

### The three unmeasured metrics — deliberately not 100%

This is the honesty rule the v0 proposal is built around: *"`not_applicable` is never rendered as
perfect coverage."* Two distinct states are reported:

- **`unavailable`** — `generated_claim_citation_coverage` and `provenance_coverage` depend on the
  provenance/authority taxonomy (**BG1**, not implemented). The input does not exist yet.
- **`not_applicable`** — `ranking_ab_regression_rate`'s population is the query cases of a *completed*
  `ranking-ab` run; none was supplied. Run `memory-seed ranking-ab --signal <name>` per signal. The
  quality report never reimplements A/B scoring.

The distinction matters: "we have no way to look" and "we looked and found nothing" are different
claims, and collapsing them is how a metric starts lying.

## What this baseline does not establish

- It sets **no targets**. Per the promotion gate, do not promote Constitution §8 from `[candidate]`
  merely because the command now exists.
- It makes **no claim that entry count or edge density proves product value** (an explicit non-goal).
- It feeds **no ranking, filtering, automation, or agent instruction**.

## Next

Review whether these numbers are useful and repeatable. Only then propose targets, ESR surfacing, or
further metrics — and BG1 first, since it is what would move two metrics off `unavailable`.
