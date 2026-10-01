# Decision reconstruction recovery: outcome

Status (2026-10-01): **offline implementation saved on an unmerged branch;
decision detection not solved; fresh accuracy gate inconclusive.**

## What was built

A bounded, provider-independent semantic request/response boundary retains inert
drafts, validates exact evidence coordinates and quotations, checks user acceptance
and chronology, and rejects malformed or oversized responses atomically.
The offline harness freezes inputs/configuration/outputs, excludes evaluation
metadata from extractor packets, pins the actual deterministic control, masks
output review, and scores two independently reviewed runs conservatively.
It does not call a model, poll a live session, or promote memory.

Smaller implementers handled bounded changes; independent reviewers checked
specification compliance, implementation quality, and output meaning.

## Actual development results

Each version ran twice on the same five previously examined positive cases.
Inputs were only the messages already cited by known decisions. These are
gold-selected-evidence reconstruction diagnostics, not a fresh benchmark,
automatic retrieval, or discovery. The previous fourteen cases remain
regression-only; these results do not replace their historical 0/14 result.

| Prompt | Run | Complete decisions | Valid cases | Imported drafts | Field-review conflicts |
|---|---|---:|---:|---:|---:|
| v1 | A | 0/5 | 5/5 | 7 | 5 |
| v1 | B | 0/5 | 5/5 | 6 | 6 |
| v2 | A | 0/5 | 5/5 | 5 | 4 |
| v2 | B | 0/5 | 2/5 | 2 | 2 |
| Frozen rules, each version | Control | 0/5 | 5/5 | 0 | 0 |

The v2 change asked the model to preserve the entire approved bundle rather than
return fragments. It did not improve complete recovery. Run B's other three
responses used unknown field-evidence keys and were rejected; they were neither
silently repaired nor counted as successes. Conflicts refer to field judgments,
not recovered decisions. No false acceptance or wrong actor was observed among
valid reviewed outputs; this tiny, positive-only diagnostic proves neither
precision nor safety.

Trial 1's masking was weakened by fixed arm ordering and repeated per-arm hashes.
That limitation is retained, not retroactively erased. Trial 2 used shuffled
opaque items, common evidence representation and a key-free reviewer export.
Both trials used frozen gpt-6-sol/high extraction configurations through the
existing Codex service, not local inference. Two reviewers judged each trial
independently.

## Why it still fails

An independent source-adequacy audit judged only one of the five reference
decisions fully recoverable from the supplied snippets. Other references lacked
material acceptance, rationale, scope, or later results. Extracted drafts also
omitted supported conditions and portions of approved plans; the one fully
recoverable case was still incomplete. Better retrieval alone, or more fluent
paraphrasing of insufficient evidence, cannot establish complete recovery.

The bounded experiment stops here: two development versions without complete
recovery improvement. Do not add another prompt revision under this protocol.
Before a separately scoped experiment, obtain adequate evidence windows and
independently reviewed source labels. The fresh gate still requires at least
30 supported unseen positives and 30 real hard negatives, actual root lineage
and complete exposure records. Existing data cannot certify this; see
[RECOVERY-README.md](RECOVERY-README.md#freshness-blocker-found-on-2026-10-01).

## Validation and review

- Passed after the final code fixes: 45 semantic/recovery tests; diff whitespace check.
- Full suite: 2,211 passed, four failed, one skipped. This is a **failed** full run.
- Three failures were Windows parallel subtest-report serialization; those tests
  passed serially with 26 subtests. The fourth was dependency progress on stderr:
  it reproduced on unchanged main, then passed on this branch with process-only
  HF_HUB_DISABLE_PROGRESS_BARS=1. No unrelated code or global settings changed.
- Final review's metadata-leakage and control-provenance findings were fixed.
  Its single scoped re-review found a new compatibility regression:
  recovery.py's _SAFE_MARKER_FIELDS omits rollout_id although SemanticState
  supports rollout/turn/ordinal marker coordinates. This must be fixed and
  covered by a positive regression test before landing.
- The subagent-driven-development workflow's one-final-fix-wave limit is reached.
  The residual finding is accepted as load-bearing for the advertised marker
  interface, not dismissed. Further code changes require user direction.

Branch: codex/feature/decision-recovery, based on
08d10e426fdbde3011c846441d72f529afa83de8. No merge, push, deployment, provider API,
training, OAuth, live polling integration, or automatic promotion occurred.
The historical parser and incremental control remain unchanged.

## Evidence retention

[recovery-results.json](recovery-results.json) contains the raw-free score
projection, dataset digests, private score-file hashes and validation status.
Private frozen sources, actual responses, reviews and scores remain outside Git
under the owner's temporary decision-recovery-20261001 directory; revision-2
holds the second trial. Temporary storage is not a durable backup. Preserve it
before cleanup if an exact replay is needed. No raw conversation evidence is
included in this report or committed.
