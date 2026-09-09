---
title: SkillOpt fit analysis
status: proposal
---

# Fit analysis: Microsoft Research SkillOpt

## Decision

Run a small, offline, review-only pilot; do not enable automatic skill adoption or make SkillOpt the source of truth for this repository's operating rules.

## Why it fits

SkillOpt treats a natural-language skill document as optimisable agent state. Its proposed workflow—replay experience, draft a skill update, validate it, then stage it for review—aligns with this repository's append-only session history, lazy-loaded skills, ESR, and explicit human approval.

The most useful contribution is not automatic editing. It is a disciplined candidate-generation loop: extract repeated execution failures from session evidence, propose a narrowly scoped skill change, validate against held-out tasks, and keep a rollbackable prior version.

## Constraints and gaps

- The repository's `.memory-seed/skills/` files are governed runbooks, not disposable prompts. Auto-adoption would conflict with the locked-control-plane and explicit-approval rules.
- SkillOpt's public material labels Sleep as preview and says real backends may receive truncated session excerpts, current skill/memory content, preferences, and generated responses. Repository session files may be publishable, but they still require review/redaction before any external provider use.
- Reported aggregate results are directional evidence, not a replacement for this project's own evaluation: raw per-run artifacts and repeated-seed confidence intervals are not generally available.
- A general optimiser can overfit one agent/model or one task class. This project needs cross-agent and cross-workflow checks before accepting a reusable rule.

## Recommended pilot

1. Select one non-critical, bounded skill with repeated evidence of missed execution (not `agent-rules.md`, policy, or session schema).
2. Prepare 10–20 historical task trajectories with sensitive paths/content redacted; reserve at least five as a held-out gate.
3. Run proposal generation offline or with a provider approved for the redacted data boundary.
4. Require a human review that compares the candidate against the current skill's ownership, trigger, and safety constraints.
5. Validate on the held-out tasks plus the repository's existing checks; accept only if it improves the measured workflow with no safety/policy regression.
6. Commit the adopted change normally, retaining the prior skill in Git history. Keep `auto_adopt` disabled.

## Success criteria

- A proposal identifies a real, repeated failure rather than restating generic advice.
- The accepted edit is smaller and more precise than the evidence it summarizes.
- Held-out completion improves or stays equal, with no new control-plane violations.
- The pilot's external-data boundary and human reviewer decision are recorded in the session entry.

## Recommendation

**Proceed with a constrained pilot, not production integration.** SkillOpt's validation-gated, explicit-adoption posture is compatible with Memory Seed only when Memory Seed remains authoritative and its existing human gates remain intact. The earliest viable use is an analyst tool that drafts proposals; automatic skill mutation should remain out of scope.

## Sources

- [SkillOpt technical blog](https://microsoft.github.io/SkillOpt/blog/gating-reflection-safe-updates/) — update gates, reflection/consolidation, preview data boundary, and staged adoption.
- [SkillOpt project](https://microsoft.github.io/SkillOpt/) — project and implementation context.
