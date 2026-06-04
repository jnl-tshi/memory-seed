---
memory-system-version: 2.5
tags:
  - memory-seed
  - skill
  - copywriter
  - copywriter-conversion
---

# Copywriter Conversion Skill

Use this skill when writing or revising any conversion-focused copy: landing pages, headlines, README heroes, Product Hunt taglines, email sequences, CTAs, or launch announcements.

## Inputs

- The asset type (landing page / README / email / tagline / GitHub description)
- The audience's awareness level (unaware / problem-aware / solution-aware / product-aware)
- Word count or character constraint (if any)
- Approved proof points (numbers, quotes, claims cleared to use)
- Voice constraints from `policy.md`

## Framework Selection

Match the framework to the audience's awareness level:

| Awareness level | Best framework | Notes |
|---|---|---|
| Unaware | AIDA | Hook first; problem reveal second |
| Problem-aware | PAS | Name the pain, amplify it, then solve |
| Transformation story | BAB | Before/After/Bridge; strong for launches |
| Solution-aware | FAB | Feature → Advantage → Benefit |
| Skeptical / cold | 4Ps | Lead with proof before the ask |
| Repositioning | JTBD | What job does the user hire this product to do? |

## Procedure

1. **Define the single action** the copy must produce. Write it down before writing a word of copy.
2. **Select the framework** from the table above. State why before proceeding.
3. **Write 10 headline candidates.** Rank them 1-10. Choose the top two.
4. **Write the hero unit:** top headline + sub-headline (one sentence) + CTA (specific verb + outcome).
5. **Extend to body copy** only after the hero unit is locked.
6. **Run the copy QA checklist:**
   - Does the headline pass the "so what?" test?
   - Is the first sentence about the reader, not the product?
   - Is the CTA a specific verb + specific outcome?
   - Is there at least one verifiable proof element?
   - Can it be cut by 20% without losing meaning?
7. **Log the also-ran headlines** in the session entry — they are future A/B test candidates.

## Developer Tool Objection Map

Pre-empt these before they surface in the copy:

| Objection | Counter in copy |
|---|---|
| "Another tool to learn" | Show the install-to-value time. One command. |
| "Vendor lock-in" | MIT license. Plain Markdown. You own the files. |
| "Performance overhead" | Local-first. No network call in the hot path. |
| "Will it work with my LLM?" | Vendor-neutral. Works with any file-reading agent. |
| "Will it break my workflow?" | Reads AGENTS.md — plugs into what you already have. |

## Format Templates

### README hero (target: < 100 words)
```
# [What it does in 8 words]

[One sentence: who it's for + the job it does]

- [Outcome 1]
- [Outcome 2]
- [Outcome 3]

[install command]
```

### Product Hunt tagline (< 60 chars)
`[What it is] for [who] that [job it does]`

### Email subject line (< 50 chars)
Variant A: `[Specific pain in 5 words]`
Variant B: `[Specific outcome in 5 words]`
Always write both. Send A first; test B after 500 sends.

### GitHub description (< 160 chars)
`[What it does] · [Key differentiator] · [Install hint or link]`

## Output

- Headline: top choice + 2 ranked alternatives
- Full copy asset in the requested format
- CTA variants (minimum 2)
- Test hypothesis: what you'd A/B test first, and what metric proves the winner
- Also-ran headlines logged for future testing
