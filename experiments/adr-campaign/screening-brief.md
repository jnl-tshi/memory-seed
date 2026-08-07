# ADR attachment screening brief (2026-08-07)

You are SCREENING pre-found candidates, not searching. For each ADR you are given, decide which
candidate decision (if any) should be attached, and prove it with a verbatim quote.

## Your inputs

- `experiments/adr-campaign/ATTACHMENT-REVIEW.md` - find your assigned ADRs there. Each lists up
  to 5 candidate decision refs with titles.
- `.memory-seed/decisions/<adr_id>.md` - the ADR itself. Read its `## Current view` to learn what
  the concern actually IS. This is the thing you are matching against.
- `.memory-seed/sessions/` - the decision bodies. Grep the entry_id (the part before `:dN`) to find
  the entry, then read that decision's `#### Dn` block (or `### Decision` for single-decision
  entries).

## The judgement

A candidate should be attached only if it is **about the same concern** - it made, changed, or
directly implements the decision the ADR records. Do NOT attach a decision merely because it
mentions the same technology or shares a topic. Topic overlap is why these candidates were
surfaced; it is not evidence that they belong.

Classify each ADR into exactly one of:

- `"primary"` - this candidate IS the decision the concern was founded on, or directly made it.
  The strongest possible match.
- `"supporting"` - clearly about this concern but secondary: an implementation, a later
  refinement, a correction.
- `"none"` - no candidate is about this concern. **This is a perfectly good answer and you should
  use it whenever it is true.** A wrong attachment is worse than no attachment, because it makes
  the ADR claim evidence it does not have.

## Quotes

Copy 40-120 characters, verbatim, from within ONE line of the candidate decision's body. Re-read
the file and confirm it matches character-for-character before returning. A drifted quote is
treated as ungrounded and the pick is dropped.

## Output contract

Return ONLY a JSON array, one object per assigned ADR, no prose outside it:

```
[{"adr_id": "...",
  "verdict": "primary" | "supporting" | "none",
  "ref": "<entry_id>:dN or empty when verdict is none",
  "quote": "verbatim 40-120 chars, or empty when none",
  "why": "one sentence: why this decision is the same concern (or why none fit)",
  "runner_up": "<ref or empty>"}]
```

Rules: `ref` must be copied EXACTLY from the candidate list in ATTACHMENT-REVIEW.md - never
invent, abbreviate, or correct a ref. If none of the candidates fit, say `"none"` rather than
picking the least-bad one.
