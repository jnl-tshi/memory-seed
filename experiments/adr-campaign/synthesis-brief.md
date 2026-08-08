# Synthesis brief - ADR summaries from the live chain (2026-08-08)

Each ADR below has a **live chain**: every decision it rests on that has not been completely
replaced, ordered oldest to newest along the evolution edges. Your job is to write the ADR's
summary as a synthesis of that whole chain.

**The rule this exists to serve:** a decision sitting at the end of a chain must not be the sole
informant of the summary. The newest member is the anchor, not the answer. A summary that just
restates `head`'s decision has failed, and so has one that restates `current_summary` unchanged.

Some `current_summary` values are the wording of a control file (`index.md`, `policy.md`) rather
than of any decision. Those especially need rewriting from the chain.

## For each ADR

1. Read `title`, then every entry in `live_chain` in order. Each carries its decision body inline.
2. Note what each member CONTRIBUTED - the first usually institutes the rule, later ones extend,
   qualify, or correct it. That progression is the substance of `evolution`.
3. Write three fields:

- **`decision`** - the concern's position as it now stands, accounting for every live member. Where
  a later member qualified an earlier one, state the qualified position, not both. Max 700 chars.
- **`why`** - the reasoning that holds it up, drawn from the members' own rationale. Say what was
  rejected and why where a member records it. Max 700 chars.
- **`evolution`** - how the position got here, walking the chain oldest to newest. Name what each
  step changed. This is the field where the chain must be visible. Max 450 chars.

4. **`covered`** - list every `live_chain` ref whose substance you accounted for. Copy the refs
   exactly. A member you judged fully subsumed by a later one still counts as covered, but say so
   in `note`. Leaving a member out of `covered` is how you declare it irrelevant, and it will be
   checked.

## Hard constraints

- Never invent a ref. Every ref in `covered` must appear in that ADR's own `live_chain`.
- Do not cite anything under `replaced` - those members are retired and must not shape the summary.
- Write plain prose, not a bulleted list. No markdown headings.
- Do not copy `current_summary` verbatim. If it is genuinely already a correct synthesis of the
  whole chain, say so in `note` and still write the fields in your own words.

## Output contract

ONLY a JSON array, one object per ADR, no prose outside it:

{"adr_id": "...", "decision": "...", "why": "...", "evolution": "...",
 "covered": ["<ref>", ...], "note": "one sentence, or empty"}
