# ADR attachment brief v2 - founding-only ADRs (2026-08-08)

Each ADR below rests on a `founding:` control-file line and has NO session decision attached. Your
job: find which of its candidate decisions actually MADE this concern.

**Everything you need is in the payload.** Each candidate carries its decision BODY inline. Read
the payload first; open `.memory-seed/sessions/` only when a candidate looks right and you want to
confirm it in context. The first run of this brief burned 30+ file reads per worker because the
bodies were missing - they are not missing now.

## For each ADR

1. Read `title` and `concern` - that is the concern you are matching against.
2. Read every candidate's `body`.
3. Choose the candidate that MADE or DIRECTLY SET this concern. Prefer the decision that
   established the rule over one that merely applies it.

## Verdicts

- `"primary"` - this decision made the concern. It becomes the ADR's head.
- `"supporting"` - clearly about this concern but secondary; attaches as evidence, head unchanged.
- `"none"` - no candidate made this concern. **A good and expected answer.** Some of these concerns
  predate the session log entirely, so the deciding decision genuinely does not exist. Forcing a
  wrong one is worse than leaving the founding line in place: it puts a false claim at the head of
  an authority record. Answer `none` whenever the fit is merely topical.

Be strict. "Related to the same area" is not "made this concern".

## Quotes

`quote` must be 40-160 characters copied VERBATIM from the chosen candidate's `body` field in the
payload. Copy it; do not retype it, and do not quote the `title` - title-quoting is the single most
common failure in this campaign, and it is checked.

## Output contract

ONLY a JSON array, one object per ADR, no prose outside it:

{"adr_id": "...", "verdict": "primary"|"supporting"|"none", "ref": "<copied, or empty>",
 "quote": "...", "quote_ref": "...", "why": "one sentence", "runner_up": ""}

Never invent a ref. Every ref must be copied from that ADR's own candidate list.
`claimed_by` on a candidate lists ADRs already citing it - that is information, not a bar.
