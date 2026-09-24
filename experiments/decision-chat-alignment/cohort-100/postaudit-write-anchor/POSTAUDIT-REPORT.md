# Write-event re-audit of five unresolved Codex decisions

Status: **post-hoc exploratory correction**, 2026-09-24. This is not a new sealed holdout score. The original gold JSONL, frozen retriever, decision records, and raw Codex logs were not changed.

## What changed

The earlier audit used the record heading's minute as its cutoff and could select the right session but the wrong turn. This pass finds the completed record-write event in the selected logical task or its child, then checks a bounded backward lineage scope against **individual item timestamps strictly before that write**. Historical flat session paths are recognized alongside today's month-grouped paths. A child may run while its parent continues reviewing: the post-audit scope now also admits the parent's bounded turns up to the write event, not only up to the child's launch. Same-turn text at or after the write is excluded. The live task is eligible up to that cutoff; the entire session is not excluded.

Every cited source is validated by rollout, turn, raw ordinal, actor, and timestamp against the local JSONL. Generated artifacts hold coordinates and short judgments, not transcript text. This pass does not alter the production retrieval architecture or the frozen top-three → full-20 → nearby fallback evaluation.

## Result

| Record | Original label | Post-audit label | Decisive change |
| --- | --- | --- | --- |
| Sep 6, nested-runtime pod authority | Unresolved | Verified source | Parent integrity review plus child pre-write topology/ownership design and implementation. |
| Sep 6, Git-anchored sidecar append-only rule | Unresolved | Verified source | Parent identified deletion/reordering gap; child designed and implemented committed-prefix checks before writing the record. |
| Jul 7, inbox promotion/disposition | Unresolved | **Unresolved** | Right session and near-time triage discussion found, but no independent pre-write turn proving the particular set of choices. |
| Jun 30, branch/worktree/subagent architecture | Unresolved | Verified source | User's research request and assistant's combined architecture statement occur before the record write in the selected turn. |
| Sep 24, gold-set evidence methodology | Unresolved | Verified source | The same live task has earlier user and assistant turns explicitly establishing the methodology; excluding the whole task was too broad. |

The completed write event was located for all five. The Sep 6 Markdown heading is approximately **12 hours 16 minutes later** than the actual write; its two decisions share that event. The other three headings differ from their write events by roughly one minute. Thus a heading timestamp is a search clue, not a reliable creation-event clock. The write event is still not proof of when implementation finished.

The 53 new-decision rows now have a *post-hoc* count of **47 verified, 3 partial, 2 child-result-only, 1 unresolved** (previously 43, 3, 2, 5). Across the strict 100 typed decisions, this would correspond to **86 verified, 9 partial, 4 child-result-only, 1 unresolved**. These are amended source-audit counts, **not improved held-out retriever performance**: one sealed case was inspected during debugging and the rule was revised afterward. The frozen report's 82/100 verified result and measured retrieval/token metrics remain the valid original readout.

## Remaining uncertainty and next check

The July record's session is identified, but its exact promotion/disposition choices may have been inferred from inspected files or conversation material absent from this bounded visible pre-write scope. It remains unlabeled, not a negative. A blinded human should review that source, the four new citations, and whether the September child implementation actually supports every clause of each record. Prospective write-time source capture is still the better route to a trustworthy training set. Before production use, test whether a completed-write anchor is available reliably for records created through other agents and tools; this pass only covers these five cases.

## Reproduce

Run `reaudit_write_anchors.py` with the unchanged development and held-out gold JSONL, the local Codex history directory, `POSTAUDIT-SELECTIONS.json`, and explicit output paths for `WRITE-ANCHOR-RESULTS.json` and `POSTAUDIT-ADJUDICATION.json`. The script fails if a cited ordinal is absent, outside the bounded lineage scope, or not strictly before the completed write. No LLM or paid API is required. The selections file contains the manual judgments; the adjudication file contains their validated exact coordinates and counts.
