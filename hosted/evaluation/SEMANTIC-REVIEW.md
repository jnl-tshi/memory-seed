# Prospective decision comparison

Status: approved comparison principle, not completed corpus adjudication.

Extract first, freeze the draft and source coordinates, then disclose the known decision
to an independent reviewer. The extractor must not receive the finished record, its title,
or selected option as a retrieval query. Gold coordinates may schedule an explicitly labelled
oracle-marker diagnostic; that experiment cannot establish unmarked discovery recall.

Review meaning, not shared words. Record `equivalent`, `different`, or `insufficient_evidence`
for each field, with exact source coordinates and a short explanation:

| Field | What must agree |
|---|---|
| Issue | The same question or problem is being decided. |
| Chosen action | The same option or commitment is selected, with the same polarity. |
| Scope | The same component, people, environment, or applicability boundary is covered. |
| Acceptance and actor | The choice is actually accepted by the attributed deciding actor, not merely proposed. |
| Conditions | Stated prerequisites, exceptions, timing, and modality survive extraction. |
| Reasons | Reasons explicitly given in the source are preserved without inventing motives. |

Different wording may be equivalent. For example, “process only newly added messages” and
“parse the delta while retaining earlier components” may agree if the same extraction scope
and acceptance are evidenced. “Reparse the expanded window” is a different action even if
it shares most words. “Use SQLite” is not equivalent to “consider SQLite.”

Do not resolve an unclear pronoun or infer acceptance by reading the gold decision back into
the draft. A reviewer who cannot establish the meaning from source evidence records
`insufficient_evidence`. Missing issue, action, scope, or acceptance prevents a complete match.
An unstated reason is not an extraction failure; omission of a stated material condition is.

Keep each case's split and source lineage. Develop rules only on development cases; preserve
the clean held-out cases as descriptive evaluation, with their existing provisional labels.
Report retrieval coverage, draft completeness, field-level agreement, false acceptance, and
unresolved cases separately. Do not report a semantic success percentage until these judgments
exist. The current diagnostic emits `semantic_equivalence: null` intentionally.

Clarifications may refine the original draft only before implementation and intervening
decisions. A later change needs a new draft linked as evolving or replacing; semantic similarity
does not authorize rewriting the old decision. All outputs remain inert until curator verification.
