# Re-grounding brief - replacement ADR heads (2026-08-08)

A refutation pass rejected the first pick for each ADR below and named a replacement (or, for the
last item, the pick was right but its quote was not verbatim). Your job is to decide whether the
proposed decision really founds the concern, and if so, to quote it correctly.

## For each item

1. Read `concern`, then `proposed.body`, then `refuter_reason`.
2. Ask whether `proposed.body` INSTITUTES the concern - sets the rule - rather than proposing,
   applying, extending or renaming it.
3. If yes, copy a quote of 40-160 characters VERBATIM from `proposed.body`. Copy it; do not retype
   it and do not quote `proposed.title`. Character-for-character, including backticks and
   punctuation. A paraphrase fails the check and the pick is discarded.
4. If no, verdict `reject`. That is a fine answer - the concern may predate the session log.

## Output contract

ONLY a JSON array, one object per item, no prose outside it:

{"adr_id": "...", "verdict": "accept"|"reject", "ref": "<proposed.ref, or empty on reject>",
 "quote": "...", "why": "one sentence"}
