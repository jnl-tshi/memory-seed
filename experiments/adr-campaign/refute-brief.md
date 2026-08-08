# Refutation brief - ADR attachment claims (2026-08-08)

Another worker claimed a specific decision FOUNDED each ADR below. **Your job is to refute it.**

They were shown the same 25 candidates you are, ranked by semantic similarity to the concern. A
worker handed 25 plausible-looking candidates will find something for every one of them - which is
why 25 of 29 came back positive, and why this pass exists. Assume the claim is a top-ranked
lookalike until the body proves otherwise.

## For each claim

Read `concern`, then `claim.body`. Ask, in this order:

1. **Does the body actually SET this rule?** Not "is about the same area", not "mentions the same
   file", not "is downstream of it" - does this decision INSTITUTE the concern? A decision that
   applies, extends, fixes, or renames an existing rule did not found it.
2. **If not, does one of `other_candidates` found it instead?** Name that ref.
3. **If no candidate founds it, say so.** Many of these concerns predate the session log entirely -
   they came from the control files, which is exactly why the ADR was founded on one. `refuted`
   with `better_ref: ""` is the right answer there and it is a common one.

## Verdicts

- `"stands"` - the body institutes the concern. Say which sentence does it.
- `"refuted"` - it does not. Give `better_ref` if a candidate genuinely does, otherwise `""`.

Default to `refuted` when you are unsure. A wrong head on an authority record is worse than a
control-file line that is honest about being one.

## Output contract

ONLY a JSON array, one object per claim, no prose outside it:

{"adr_id": "...", "verdict": "stands"|"refuted", "better_ref": "", "reason": "one or two sentences"}
