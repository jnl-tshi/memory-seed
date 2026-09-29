# Fresh-session handoff: P0.2 paired decision-extraction replay

User requested a fresh session on 2026-09-29. This is a continuation, not a new design exercise.
User authorized the old-versus-new corpus replay and meaning-based comparison; no tuning on held-out data.

## Ownership and landing state

- Primary repository: the repository root.
- Continue in the existing owned home at `.codex/worktrees/home`.
- Branch: codex/test/p0-2-paired-replay.
- Base/HEAD: 95514648be7dae6652d217fd8bfbcade897e19d3.
- Current replay work is UNCOMMITTED, NOT MERGED, NOT PUSHED.
- Original owner has stopped editing and running experiments for this handoff. No corpus process remains running.
- Preserve current untracked files. Do not reset, park, overwrite, or create another home for this continuation.
- Follow full primary-session AGENTS routing, policy, collaboration skill and fresh worktree verification. Reclaim only the same branch/path as appropriate.

## User's accepted contract

Start at a marker; retain parsed components; expand with newly added messages only.
A complete decision needs a clear issue, chosen action, scope and grounded acceptance.
Capture reasons/conditions when stated; unresolved references require expansion.
Clarification remains within a decision only before implementation and intervening decisions;
later changes evolve/replace it. Compare meaning, not word choices.
All outputs remain inert drafts and require curator verification.
STOP before OAuth identifier request/use, device sign-in, approval mutation or token storage.

## Current experiment

- hosted/evaluation/PAIRED-REPLAY-PLAN.md: preregistered protocol, frozen before execution.
- hosted/evaluation/paired_replay.py: local paired oracle-marker replay and cache ablation.
- hosted/evaluation/paired-results.json: successful machine results; semantic status still pending.
- tests/test_p02_paired_replay.py: six harness tests.
- A temporary compiled v2 reviewer packet and spawn prompt were used as owner-local handoff artifacts;
  they are intentionally not committed.
- hosted/evaluation/SEMANTIC-REVIEW.md: already tracked rubric.
- Production parser and incremental.py are unchanged from HEAD, intentionally frozen.
- Baseline parser commit: 1c3f2e298e95ae8c54dcc5918cbaf6d2e95e3003.
- Revised parser commit: 95514648be7dae6652d217fd8bfbcade897e19d3.
- Pinned environment: spaCy 3.8.16 / en_core_web_sm 3.8.0 at %TEMP%\p02-spacy-deps.
- Replay command: set PYTHONPATH to that dependency directory plus current worktree, then
  python -m hosted.evaluation.paired_replay --codex-home %USERPROFILE%\.codex --output hosted/evaluation/paired-results.json.
- First full run completed extraction but sandbox blocked report save. Second identical run outside sandbox saved report successfully.
- Both private replay packet directories remain in owner-local temporary storage and are intentionally
  omitted from the repository.
- Each private directory has raw-results.json plus per-case masked JSON; never commit raw evidence.
- Two independent read-only reviewers assessed the first packets. Their final results are being saved beside this handoff if available. Check the current source thread if missing; do not fabricate judgments.

## Verified machine results (first run; confirm equality with second)

67 eligible verified cases: 53 development + 14 clean descriptive held-out.
65 replayable (51 development + all 14 held-out); two development cases lack visible anchors.
Missing IDs: mse_f29hkasxxz61ghw6:d1 and mse_f82r85nq95zng55e:d1.

| Metric, 65 replayable cases | Original | Revised |
| --- | ---: | ---: |
| Cases with any draft | 65 | 5 |
| Cases with accepted-state draft | 11 | 3 |
| All accessible cited refs retrieved | 19 | 60 |
| All cited refs retrieved including inaccessible/tool refs | 15 | 51 |

Held-out fourteen: original emits14, accepted3, retrieves all cited refs5;
revised emits2, accepted2, retrieves all cited refs14. Revised complete drafts: ZERO
both overall and held-out. Original does not implement a comparable complete flag.

Cache ablation: outputs identical after excluding instrumentation in all65 replayable cases.
Delta extraction calls5669 vs reparse14339; chars2594386 vs6086846.
Do not call this runtime speedup: shared linguistic-feature memoization accelerates both arms.
Fixed cue coverage:10/65 at oracle anchor;34/65 at any cited visible event. NOT detector recall.

## Scope and caveats

Anchor is last accessible cited visible event, chosen using gold coordinates, not gold text.
No future messages are supplied; this tests anchor-time reconstruction, NOT full streaming forward waits.
Revised arm can retrieve causally earlier parent lineage. Source input hashes cover26 rollouts.
Input normalization only user/assistant visible messages; boundary inference from raw events is not implemented.
Marker hint is generic source-derived signal; accepted-state marker is a simple heuristic, not a validated hard marker.
Gold contents opened only after both parser outputs are frozen.
No negative population sample; no autonomous discovery accuracy or real precision claim is justified.
Expanded retrieval/rules differ between old/new; cache ablation isolates processing only.
Both reviewers' preliminary finding: no complete semantic match; generic issue/null scope and incorrect attribution recur.
Do not present preliminary finding as reconciled final review until reading final results.

## Tests and harness hardening

Latest targeted run: python -m pytest -q -n 0 tests/test_p02_paired_replay.py tests/test_p02_incremental.py tests/test_hosted_decision_capture.py =>36 passed.
Pinned spaCy run: python -m pytest -q -n 0 tests/test_p02_paired_replay.py =>6 passed.
Tests preceded behavior changes, initial red run retained in source thread.
After successful corpus run, added validated_gold_text: requires matching nearest entry_id and heading
before scoring frozen line slice. Six tests pass but corpus was NOT rerun after this guard-only change.
Separate read-only audit checked all85 verified formal gold rows' enclosing identity/heading: no mismatches.
Need call the new validator over replayed rows, compare gold bytes with saved packets, and document freshness.
Full suite for THIS branch has NOT run. Prior milestone result is not fresh validation:
2164 passed,3 xdist WindowsPath serialization failures,2 skipped; those3 passed serial.
Existing new test file was formerly4 tests, now6. No source parser tuning occurred.

## Remaining work, in order

1. Verify ownership/HEAD and actual files; preserve in-progress uncommitted work.
2. Collect both independent final review reports, reconcile field-level disagreements; don't tune parsers.
3. Confirm both raw replay outputs match; validate gold guard against saved gold; consider harness validity
   issues: anchor timestamp vs ordinal ordering, blind packet integrity, fixed baseline linguistic rules.
4. Produce sanitized semantic labels + report separating retrieval success, incomplete extraction,
   semantic failures and saved processing. No raw conversation prose in Git.
5. Read-only whole-branch validator through v2 Task Packet; address harness bugs only (not held-out tuning).
6. Relevant targeted tests, one background full suite, sandbox-only retry once if needed.
7. Append durable session record using sanctioned writer; update active state/next steps to truthful status.
8. Commit and land automatically only under repository local-merge policy, fresh integrated checks.
   Report committed/merged/pushed facts; do not push unless policy/request authorizes.
9. Answer whether decision extraction improved: current evidence says better retrieval and less repeated
   processing, but complete semantic extraction not demonstrated. Full live/production P0.2 remains incomplete.

## Prior accepted memory

mse_ad9xz2f1kpyygw9b:d1 records user's delta-only and semantic-comparison contract.
mse_vrq7b274s17mq6m1 records conservative prototype and honest evaluation limits.
Prior milestone f2618254 merged as95514648; primary main ahead40 origin at last check.
