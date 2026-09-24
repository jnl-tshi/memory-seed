# Codex decision alignment: lineage and causal fact-finding

## Outcome

The original 8% confident-alignment result was not a trustworthy scoring baseline. A structural identity defect collapsed parent and spawned-agent rollouts onto shared identifiers, overwrote parent transcripts, and duplicated surviving child blocks. Repairing that defect recovered the long-running parent turns found by manual review.

The corrected deterministic matcher is promising but not yet suitable for producing classifier labels without review. On seven provisional-gold decisions it retrieves the exact source turn for five and a window containing the source for six. That is 71.4% recall at the winning turn and 85.7% recall at the returned window, far below the exploratory 98% target and based on too few gold examples to estimate that target reliably.

## Spawned-agent storage finding

Spawned agents are recorded in both places, with different information:

- The child has its own rollout JSONL containing its full messages and turn events.
- The child `session_meta.payload.source.subagent.thread_spawn` object records the parent task ID, depth, agent path, and nickname.
- The parent records the spawn call and later summary or final handoff, but not the child's full transcript.

Parent and child text must remain separate candidate sources. Lineage is useful for repository eligibility, grouped review, and provenance; concatenating child text into the parent would inflate similarity and erase source boundaries.

## Manual recovery of the 28 previous No-match decisions

Three independent economy-model passes searched 1,545–1,550 active and archived JSONL files. Their bounded result was:

| Manual status | Count | Meaning |
|---|---:|---|
| Found | 7 | Exact source evidence with rollout and turn coordinates was verified. |
| Probable | 6 | Substantive related evidence was verified but source boundaries or multi-turn synthesis need adjudication. |
| Ambiguous | 1 | Only a later copied-history wrapper was verified. |
| Unknown | 14 | The bounded manual pass did not corroborate a source; this is not evidence of absence. |

The row-level machine-readable audit is in `MANUAL-RECOVERY-AUDIT.csv`.

## Root cause

The decisive defect was identity collapse:

1. `read_session_meta()` preferred `payload.session_id` to the rollout's own identity.
2. Spawned-agent `session_id` values can point to the parent task.
3. Continuation rollout files can repeat one logical task ID while having distinct storage-file identities.
4. `blocks_by_session` was keyed by the collapsed value, so later files overwrote earlier parent blocks.
5. `align()` iterated every metadata row and reinserted the overwritten blocks for each collision.

In the reviewed snapshot, 922 repository-associated rollout files collapsed to 484 parsed identifiers. Thirty-four identifiers collided, covering 472 files; one collision contained 77 rollouts. The prior report's repeated source ordinals were an observable symptom.

The repair now distinguishes:

- rollout-file identity, derived from the final UUID in the rollout filename;
- logical task/session identity from `payload.id`;
- legacy or parent hint from `payload.session_id`;
- explicit parent lineage parsed from nested `thread_spawn` metadata.

Candidate blocks are keyed by rollout-file identity. Duplicate rollout identities and duplicate `(source path, ordinal)` coordinates fail closed.

## Ablation results

All passes reuse the exact fixed 50-decision cohort and unchanged confidence thresholds.

| Pass | High | Medium | Low | No match | High + Medium | Ambiguous windows |
|---|---:|---:|---:|---:|---:|---:|
| Original turn-aware result | 2 | 2 | 18 | 28 | 4 (8%) | 13 (26%) |
| Unique rollout identity + lineage | 11 | 20 | 19 | 0 | 31 (62%) | 22 (44%) |
| Strict pre-minute causal cutoff | 4 | 26 | 20 | 0 | 30 (60%) | 30 (60%) |
| Decision-minute cutoff, stopping at append | 6 | 25 | 19 | 0 | 31 (62%) | 29 (58%) |

The zero No-match count does not mean zero false negatives. Low-confidence and wrong-window results remain misses against a known source. The sharp increase in ambiguity is honest: once overwritten rollouts are restored, the scorer sees many more plausible competitors.

The current candidate set averages roughly 26 eligible rollouts per decision. Candidate-volume reduction at the turn/window level is not yet instrumented and must be added before this can be evaluated as a high-recall filtering stage.

## Causal and replay controls

A manual precision audit of the 31 lineage-only High/Medium winners classified 21 as valid first-hand provenance, five as valid child-result provenance, four as materially post-hoc session-record matches, and one as uncertain. Thus the provisional precision-at-one was 26/31, or 83.9%, before causal controls.

That 83.9% figure must not be transferred unchanged to the final causal-minute pass. Four current High/Medium winners changed relative to the lineage-only pass; their decisive raw text has not yet received an independent manual audit, so current-pass precision remains unknown. The causal controls have a clear anti-leakage mechanism, but their net precision effect still requires adjudication.

The raw winning windows commonly contain later D/R/A/F recitations because source discussions and Memory Seed authoring often happen in the same long turn. The matcher now:

- scores only items before the end of the recorded decision minute;
- stops earlier when an explicit `memory_session_append` call begins in that minute;
- rejects embedded action-history replay wrappers, not just wrappers whose text begins with the marker;
- excludes encrypted reasoning and never serializes readable reasoning-summary text;
- retains child-result evidence with child rollout provenance.

The minute-aware cutoff recovered the genuine same-minute Inbox source that the stricter cutoff removed, while still excluding the later append call. It changed eight winners relative to the strict-cutoff pass and restored the provisional-gold source turn.

## Remaining failure modes

- Decisions synthesized across adjacent turns are still scored as single turns; the context window is constructed only after a winner is chosen.
- Rewritten decisions can share few surface terms with their sources.
- Generic repository filenames and repeated architecture vocabulary create competitive windows.
- Child results forwarded to parents need explicit source-boundary adjudication.
- A session-record append can be the only highly specific wording even when broader genuine discussion precedes it.
- Repository membership is still mostly a hard gate. The new lineage inheritance path is implemented, but the current corpus reported no child that needed it because observed children already carried repository working-directory metadata.
- Confidence margin calculation still mixes base score and ranking-assisted winner selection and should be made internally consistent before thresholds are interpreted.
- Fourteen of the original misses remain manually Unknown; broader deterministic retrieval must not relabel them as correct without audit.

## Dataset feasibility

The process can create useful labels, but the present gold set is too small. Seven gold decisions mean one miss changes measured recall by 14.3 percentage points. A 98% target cannot be evaluated meaningfully at this size.

Positive examples should be exact, causally prior source windows with rollout, turn, ordinal, timestamp, and lineage provenance. Probable child/parent syntheses should be adjudicated before use. Post-hoc session records, copied action histories, and later decision recitations must not be positives.

Unlinked conversation remains unlabeled rather than negative. Safer negatives are reviewed same-time, same-project competitor windows that contain similar filenames or vocabulary but are demonstrably about a different decision. Split evaluation by root task/session, then by project or time tranche where possible; never split parent and child rollouts across train and test.

An initial classifier baseline still needs roughly 200–500 manually verified positives and two to four times as many reviewed hard negatives. Do not train it from the current confidence labels.

## Architecture implication

The evidence now favors continued experimentation with:

`raw conversation -> deterministic high-recall candidate detector -> curator`

The deterministic layer has demonstrated useful recovery once its candidate corpus is correct, and its errors are inspectable. It has not demonstrated the approximately 98% recall operating point, and its current candidate volume and ambiguity are high. Therefore raw conversation to curator remains the safe fallback, a lightweight classifier remains premature, and adding both rules and a classifier would introduce an unsupported second false-negative boundary.

## Next experiment

The smallest uncertainty-reducing next step is to adjudicate 30–50 exact source windows, including the 14 still-Unknown decisions and hard same-vocabulary competitors. Then evaluate:

1. recall at the winning turn and within the returned window;
2. false-negative rate;
3. candidates and retained turns per decision;
4. conversation-volume reduction;
5. precision at one;
6. replay or post-hoc contamination rate.

Only after that label set exists should the matcher add pre-ranked multi-turn windows, structured decision/rationale/identifier query fields, staged temporal widening, or a classifier.
