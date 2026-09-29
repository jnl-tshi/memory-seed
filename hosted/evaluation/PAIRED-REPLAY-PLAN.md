# Paired decision-extraction experiment

Status: frozen before execution; approved by JNL's request to trigger the comparison.

## Question and scope

Does the revised extractor recover the meaning of known decisions better than the
original bounded-window extractor? Separately, does retained-state extraction avoid
repeated processing while preserving the output of the same rules?

Freeze the original parser at `1c3f2e298e95ae8c54dcc5918cbaf6d2e95e3003` and the
revised parser at `95514648be7dae6652d217fd8bfbcade897e19d3`. Do not tune either parser
during this experiment. Use the existing canonical corpus and partitions unchanged.
Use the pinned spaCy environment for both arms. This is local, owner-only evaluation;
no OAuth, uploads, provider API, authoritative-memory promotion, or public raw logs.

## Three distinct observations

1. **Paired oracle-marker replay:** at the last accessible visible cited source event,
   pretend a marker was emitted. Its hint and quote come from that observed message,
   not the completed record. Give both parsers the same observed current-session prefix;
   the revised parser may use causally earlier parent-lineage context. Exclude all future
   events, including later records. Score exact source-coordinate recovery and compare
   emitted draft meaning. This isolates extraction conditional on a correct source anchor;
   it does not measure autonomous discovery recall or marker-placement accuracy.
2. **Independent cue coverage:** using source-message text only, test whether a fixed
   commitment/proposal/acceptance cue fires at any adjudicated visible source event.
   Report this solely as cue coverage, not decision detection accuracy. No unlabeled
   discussion is silently treated as a negative.
3. **Delta ablation:** replay the revised parser with and without retained extraction
   components over the same retrieval stages. Require byte-identical final outputs after
   excluding processing-count instrumentation. Count extraction calls and input characters;
   do not attribute semantic gains to caching. Shared deterministic linguistic-feature
   caching may accelerate both benchmark arms; therefore wall-clock speed is not a gate.

## Scoring and review

- Publish exact denominators, missing/inaccessible source cases, source hashes, and split
  counts. Partial/unresolved gold rows and audit-only amendments do not enter verified recall.
- Distinguish candidate emission, accepted-state emission, complete draft emission, exact
  all-source coverage, and semantic equivalence. Retain failures and abstentions.
- Run machine comparisons on every eligible verified case. Conduct blind, field-level
  semantic review of every available clean held-out case, with arm names masked; use the
  existing semantic review rubric. This is descriptive AI adjudication, not human gold.
- Reviewers receive the frozen emitted fields and source evidence only after extraction;
  the gold record is never passed into the parser. Inspect all distinct candidate meanings
  in that case. No lexical-overlap score substitutes for a semantic judgment.
- Retain owner-local raw review packets outside Git. Commit only reproducible harness,
  sanitized metrics, and a limitations report. Do not claim population precision from the
  selected positive corpus; the existing synthetic negatives remain a separate control.

## Validation and ownership

Root owns harness, tests, aggregate reports and memory. Read-only reviewers own no source
files and report bounded judgments; independent paired labels are reconciled explicitly.
Use tests before harness implementation for causal cutoff, exact-coordinate scoring,
baseline pinning, blind arm preparation, and ablation accounting. Run the synthetic probe
before corpus replay. A source mutation, gold leakage, differing model versions, or unexplained
ablation output difference invalidates the affected run. Report parser limitations rather
than changing the frozen extractor to improve held-out results.
