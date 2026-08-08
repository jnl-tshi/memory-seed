# Completeness brief - does this summary account for its whole live chain? (2026-08-08)

Another worker wrote each ADR summary below as a synthesis of that ADR's live chain. **Your job is
to find what it left out or got wrong.**

The standard is not "is this a good summary". It is: **for each member of `live_chain`, is that
member's substance present in the summary, or correctly subsumed by a later member's position?**
A summary that reads well while quietly dropping a member's qualification has failed.

## For each claim

1. Read `live_chain` in order, then `summary.decision`, `summary.why`, `summary.evolution`.
2. For EACH live member, decide one of:
   - **present** - its substance is in the summary
   - **subsumed** - a later member's position supersedes it and the summary states that later
     position; this is correct and counts as accounted for
   - **missing** - its substance is absent and nothing later covers it
   - **contradicted** - the summary states something this member's body denies
3. `evolution` must walk the chain. A summary whose `evolution` names only the newest member, or
   is a generic sentence that would fit any ADR, is **incomplete** even if `decision` is fine.

## Verdicts

- `"complete"` - every live member is present or subsumed, and `evolution` walks the chain.
- `"incomplete"` - list the offending refs in `missing` and/or `contradicted`.

Default to `incomplete` when unsure. A summary sent back costs one more pass; a summary accepted
with a member silently dropped puts a false position at the head of an authority record.

## Output contract

ONLY a JSON array, one object per ADR, no prose outside it:

{"adr_id": "...", "verdict": "complete"|"incomplete", "missing": ["<ref>", ...],
 "contradicted": ["<ref>", ...], "reason": "one or two sentences"}

Refs must be copied from that ADR's own `live_chain`. Never invent one.
