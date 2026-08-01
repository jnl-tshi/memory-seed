# Governance & standards research programme

A seven-report research programme commissioned 2026-08-01, deliberately sequenced so each report
consumes the evidence of the previous one and no conclusion is reached before the evidence supporting
it exists.

**Status: supporting provenance.** These are dated research passes, not living dossiers. Conclusions
that survive belong in the canonical dossiers under [`market/`](../market/) and
[`wedges/`](../wedges/); these reports are the evidence trail behind them.

## Reports

| # | Report | Question it answers | Status |
|---|---|---|---|
| 1 | [Standards & regulatory landscape](standards-and-regulatory-landscape-report.md) | What do 21 governance frameworks exist to solve, and what evidence do they demand? | Complete |
| 2 | [Decision governance evidence spine](decision-governance-evidence-spine-report.md) | Do those frameworks converge on a common evidence model, and how much of it does Memory Seed already capture? | Complete |
| 3 | [Strategic fit](memory-seed-strategic-fit-report.md) | Where does Memory Seed naturally provide value, and who else occupies that ground? | Complete |
| 4 | [Benchmarking & economic value](memory-seed-benchmarking-and-economic-value-report.md) | What would actually be measured to test these claims? | Complete |
| 5 | [ADR standards](architecture-decision-record-standards-report.md) | How should Memory Seed align with existing decision-record conventions? | Complete |
| 6 | [Ideal customer profile](memory-seed-ideal-customer-profile-report.md) | Which market is worth entering first? | Complete |
| 7 | [Strategic roadmap](memory-seed-strategic-roadmap-report.md) | What should Memory Seed become, and what should it avoid? | Complete |

## Reading order

**If you read one thing: [Report 7 §4](memory-seed-strategic-roadmap-report.md), the ninety-day plan.**
It is the only section that asks for action rather than attention, and its central recommendation is that
the research phase is over.

Otherwise read **1 → 2 → 3 → 7**, treating 4, 5 and 6 as reference. The argument is cumulative, and later
reports overturn earlier ones on evidence the earlier ones did not have — Report 3 demotes Report 2's
top-ranked gap, and Report 6 records that Report 3 missed an entire competitor category.

**The most reusable artefact** is Report 1 §3, the evidence-spine crosswalk: 21 governance frameworks
mapped onto eight decision-evidence questions with clause citations.

## Conventions

Every non-obvious claim carries a provenance tag, following Constitution Invariant #4 — provenance is
declared on the record, never inferred from where it sits:

| Tag | Meaning |
|---|---|
| `[primary]` | The governing body's or vendor's own document, with URL and retrieval date |
| `[secondary]` | A named third party, with its commercial interest noted where it has one |
| `[estimate]` | A range whose basis is stated in the same sentence |
| `[unsourced]` | Could not be sourced — stated as unknown rather than guessed |

**Cost figures are the weakest content in the programme and are marked as such.** No governing body
publishes implementation costs; the available figures come from parties selling the remedy. Penalty
figures are the exception — those are quoted from statute.

## Standing caveats

These apply to every report and are repeated in each one rather than assumed:

- **No demand evidence exists.** No buyer, auditor, or user has been interviewed at any point. Every
  claim about what would satisfy a framework is derived from framework text; every claim about what
  someone would pay for is inference from vendor behaviour.
- **ISO clause citations are `[secondary]` throughout.** `iso.org` returned HTTP 403 to every automated
  fetch across three independent passes. Buy the standard before relying on any ISO clause citation.
- **"No competitor does X" is ambiguous** between an unserved need and absent demand. The programme
  cannot distinguish them.

## Provenance

Commissioned by JNL, 2026-08-01. Research performed against primary sources with dates verified at
retrieval rather than recalled — ten framework status changes were found that post-date a May 2026
model cutoff, including an EU AI Act amending regulation that entered into force five days before
Report 1 was written.
