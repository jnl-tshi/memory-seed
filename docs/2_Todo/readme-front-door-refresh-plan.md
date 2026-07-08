---
memory-system-version: 2.16
tags:
  - memory-seed
  - proposal
  - readme
  - documentation
---

# README Front Door Refresh Plan

Status: ACTIVE - clarified; implementation not started.
Priority: P6 documentation polish after release-safety, encoding hardening, and Memory Trace release
ordering unless the user reprioritizes launch-readiness.
Source: Promoted from `docs/2_Todo/completed/README Improvements.md` on 2026-07-08. Clarified by user
decision on 2026-07-08: include screenshots/GIFs, but placeholders are acceptable when real assets
are not ready.
Scope: Refresh the root `README.md` so new users can understand, install, initialize, and trust
Memory Seed quickly.
Non-goals: No full product manual in the README. No general seeded "README architect" skill unless
the workflow repeats across projects. No promises about unpublished Memory Trace releases.
Dependencies: Current CLI surface, Memory Trace release-ordering decision, functionality audit, and
the UTF-8/encoding policy.
Acceptance criteria: See "Acceptance Criteria" below.

## Assessment

The inbox item is useful, but it should be narrowed. The README should be the front door for Memory
Seed, not a full manual and not a generic documentation skill.

The strongest ideas to keep:

- Put the value proposition and install/init path near the top.
- Optimize for time to first successful execution.
- Keep commands copy-paste-ready.
- Use visuals only when they show the actual CLI/UI state.
- Move deep architecture and roadmap material into docs.
- Include a clear security note that `.memory-seed` files should be treated as publishable.

## Blind Spots To Resolve

- Emoji headings are not a good default here. They add encoding/display risk and clash with the
  current documentation style. Use plain headings unless the user explicitly wants emoji-heavy
  marketing copy.
- The example's final "Project Documentation" link points at a Google search URL and must not be
  copied.
- Badges should only point at real, stable project surfaces. Avoid badges that imply coverage or CI
  status not actually maintained.
- The README must not present `memory-trace` publication as complete until the release-ordering plan
  has shipped.
- Screenshots/GIFs are useful but add an asset maintenance burden; decide before implementation.

## Decisions Resolved

- Include visual proof for `memory-seed init`, MCP validation, and Memory Trace where possible.
- Use placeholders for screenshots/GIFs if real assets are not ready in the implementation pass.
- Keep the README as a front door; move deeper reference detail into docs.
- Keep "README Architect" as source inspiration for now, not a seeded reusable skill.

## Proposed README Shape

1. Title, badges, and one-sentence positioning.
2. Highlights focused on local-first, Git-native, vendor-neutral, inspectable project memory.
3. Quickstart with `uvx --from memory-seed memory-seed init`.
4. Agent handoff instruction: ask the coding agent to read `AGENTS.md`.
5. Short "How it works" section covering `.memory-seed/`, hooks, MCP, and session logs.
6. Agent support table.
7. Memory Trace as optional companion UI, clearly release-state accurate.
8. Visual proof section with real assets or clearly marked placeholders.
9. Security/privacy note.
10. Links to docs, changelog, and active roadmap.

## Acceptance Criteria

- A first-time user can run the core init path from the top quarter of the README.
- Memory Trace wording matches the actual package/release state.
- Visual proof is present as real screenshots/GIFs or explicit placeholders.
- Copy-paste commands are syntax-highlighted and tested.
- The README links to `docs/2_Todo/0_NEXT_STEPS.md`, `docs/3_Spec/functionality-audit.md`, and
  relevant package docs where appropriate.
- No mojibake-prone emoji header set is introduced.
- No stale external search URL remains.
- The README remains a front door, not a full manual.
