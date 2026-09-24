# Codex-only decision-to-chat alignment follow-up

Date: 2026-09-24

## Question

Does restricting the sampled Memory Seed decisions to records tagged `agent_type: codex` materially
improve retrospective alignment to local Codex conversation windows?

## Method

This run used the same matcher, temporal bounds, confidence rules, privacy exclusions, sample size,
and seed as the original experiment. The only intentional change was to filter the canonical decision
population by an exact case-insensitive `agent_type == "codex"` match before sampling.

- Unfiltered canonical decision population: 1,641.
- Codex-tagged eligible population: 533.
- Sample: 50 decisions selected uniformly without replacement after sorting by decision ID.
- Seed: `20260924`.
- Sample-ID SHA-256: `73b2dc2de7967859c9b138a6fbd56b9b10774a453bc5d3ba7b76c6c7795179a6`.
- Sample date range: 2026-05-26 through 2026-09-22.
- Repository rollouts: 917.
- Temporally eligible rollouts: 381.
- Normalized turn blocks: 404.
- Source window: winning turn plus two turns before and after.

The sample is independent of the original mixed sample; it is not a re-evaluation of the original 23
Codex rows. Comparisons therefore describe two seeded samples, not a paired test.

## Results

| Confidence | Codex-only count | Codex-only percent | Original mixed count |
|---|---:|---:|---:|
| High | 0 | 0% | 0 |
| Medium | 2 | 4% | 3 |
| Low | 21 | 42% | 10 |
| No match | 27 | 54% | 37 |

- Automatically aligned at High or Medium: **2/50 (4%)**.
- At least a weak candidate at Low or better: **23/50 (46%)**.
- Multiple plausible source sessions: **12/50 (24%)**.
- Unique Low candidates: **9/50 (18%)**.

The diagnostic failure categories were:

| Category | Count |
|---|---:|
| No sufficiently similar conversation window | 27 |
| Multiple conversations discuss similar material | 12 |
| Rewritten, synthesized, or weakly distinctive wording | 9 |

## Manual check of Medium results

Both Medium results appear to be genuine source windows:

1. `ms-c0d56306:d1` aligns to session `019e5f82-bca6-74f3-b226-422af8de505f`, turn 74. The window
   contains the user's request to distinguish persistent `uv tool install` from one-off `uvx`, the
   implementation, the matching files, and the validation recorded in the decision.
2. `mse_vexkm8da35zj856x:d1` aligns to session
   `019f0b5e-267a-7263-8c5c-0f6fb130fe4b`, turn 35. The window contains the rendered-UI debugging
   workflow proposal, explicit user approval, and the persona/skill changes recorded by the decision.

The Low rows remain candidates for owner audit, not positive labels. Twelve have a competitive second
session, and the other nine still lack enough evidence for promotion under the pre-registered rules.

## Interpretation

Restricting the decision population to Codex-authored records removes the first experiment's largest
obvious source-coverage mismatch, but it does **not** produce a useful confident-alignment rate. The
No-match rate falls from 74% to 54%, while Low candidates rise from 20% to 42%. Medium-or-better
alignment falls from 6% to 4%, and ambiguity doubles from 12% to 24%.

Because the samples are independent, the exact percentage differences should not be treated as a
controlled causal estimate. The directional result is still clear: cross-agent coverage was only one
failure mode. Timestamp looseness, repeated project vocabulary, rewritten decision prose, long-session
synthesis, and absent first-hand session IDs continue to dominate.

The outcome strengthens the earlier recommendation:

- do not train a classifier from these retrospective matches;
- do not treat Low candidates as labels;
- capture first-hand session/turn provenance prospectively;
- evaluate a deterministic high-recall candidate detector on those prospective gold spans before
  deciding whether a classifier stage adds value.

## Outputs

- `results-codex-only/alignments.json` — sanitized machine-readable results;
- `results-codex-only/alignments.csv` — compact audit table;
- `results-codex-only/review.md` — all 50 decisions and candidate coordinates;
- private raw-window audit — stored only in the explicitly named local temporary directory.

No existing Memory Seed decision or Codex rollout was modified.
