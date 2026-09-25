# Decision-source gold-set methodology

This gold set adjudicates the frozen 50-decision Codex cohort from
`results-codex-causal-minute-fixed/alignments.json`. It evaluates the selected candidate; it does not
retune or rerank the matcher.

## Traversal rule

For each decision, review starts with the selected candidate's decision-time anchor and bounded
region, then moves backward through earlier turns and continuation files sharing the same logical
task ID. The selected winning turn is judged separately, because lexical ranking can choose a turn
immediately before the actual decision-time anchor. If the selected rollout belongs to a spawned
agent, review follows `parent_thread_id` to the parent logical task and continues backward. Parent
evidence is cut off at the child's creation time. Every rollout retains its own file identity and
source ordinals.

Only causally prior visible messages, compact tool evidence, and readable reasoning summaries may
support a label. Encrypted reasoning is never read. A `memory_session_append` call and later D/R/A/F
recitations form a post-hoc boundary and cannot establish source provenance.

## Labels

- `verified_source`: causally prior evidence establishes the complete decision. The evidence can span
  several turns.
- `partial_multi_turn`: genuine source material was found, but a substantive part of the decision or
  its adoption remains unestablished.
- `child_result`: a spawned agent produced substantive decision evidence returned to the parent, but
  the selected window is a child result rather than the originating parent discussion.
- `wrong_candidate`: the selected candidate concerns a different decision.
- `unresolved`: retained evidence is insufficient to decide.

`selected_candidate_describes_decision` refers specifically to the matcher's winning turn and is
separate from the label. It is false when traversal verifies the decision elsewhere in the same task
or lineage but the winning turn does not itself describe it. The assembled output also computes
whether any or all cited evidence falls inside the matcher's returned bounded window. This preserves
the distinction between winning-turn precision, returned-window coverage, and broader lineage
recovery.

## Mechanical gates

`assemble_gold_set.py` refuses to generate the combined outputs unless all 50 fixed decision IDs occur
exactly once, every audited rollout/turn identity exactly matches the frozen selected candidate, and
every evidence rollout is either the selected rollout or an explicitly traversed parent/child source.
This prevents a reviewer from silently auditing a nearby task, mistyping a decision identifier, or
transcribing an evidence rollout incorrectly. The final JSONL retains evidence coordinates and concise
rationales, not raw conversation text.
