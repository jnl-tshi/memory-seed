# ADR attachment brief - founding-only ADRs (2026-08-08)

Each ADR below rests on a `founding:` control-file line and has NO session decision attached. Your
job: find which of its candidate decisions actually MADE this concern, so the ADR can rest on a
real decision instead of a line in a file.

## For each ADR

1. Read the ADR: `.memory-seed/decisions/<adr_id>.md`, the `## Current view` section. That is the
   concern you are matching against.
2. Read EVERY candidate decision. Grep its entry_id (the part before `:dN`) under
   `.memory-seed/sessions/`, then read that decision's `#### Dn` block, or its `### Decision`
   section when the entry has only one decision - a single-decision entry is addressed as `:d1`.
3. Choose the candidate that MADE or DIRECTLY SET this concern. Prefer the decision that
   established the rule over one that merely applies it.

## Verdicts

- `"primary"` - this decision made the concern. It becomes the ADR's head.
- `"supporting"` - clearly about this concern but secondary; attaches as evidence, head unchanged.
- `"none"` - no candidate made this concern. **A good and expected answer.** These ADRs were
  founded from control-file lines precisely because the deciding entry was not obvious; forcing a
  wrong one costs more than leaving the founding line in place.

## Quotes

`quote` must be 40-160 characters copied VERBATIM from the chosen decision's BODY - not its title,
which is the single most common failure here. Copy it; do not retype it. `quote_ref` names which
candidate it came from, copied exactly from the candidate list.

## Output contract

ONLY a JSON array, one object per ADR, no prose outside it:

{"adr_id": "...", "verdict": "primary"|"supporting"|"none", "ref": "<copied, or empty>",
 "quote": "...", "quote_ref": "...", "why": "one sentence", "runner_up": ""}

Never invent a ref. Every ref must appear in that ADR's own candidate list.
