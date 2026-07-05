---
title: "Proposal: Named STOP-Trigger Taxonomy"
date: "2026-07-05"
project: "memory-seed"
related_to: "docs/inbox/memory-trail-competitor-analysis.md"
author_context: "Prepared for Jean Nathan Tshibuyi"
format: "Markdown research proposal"
---

# Proposal: Named STOP-Trigger Taxonomy

> **Origin:** flagged as a genuinely good idea (not a threat) in
> [`memory-trail-competitor-analysis.md`](memory-trail-competitor-analysis.md) — the `frmoretto/memory-trail`
> skill defines a fixed taxonomy (Security, Destructive, Irreversible, Financial) that forces a hard
> stop: explain the risk, present 2–3 options, wait for a human choice. This document researches the
> idea, adapts the categories to Memory Seed's own control-plane conventions, and proposes where it
> would live if promoted to `docs/todo/`. This is **inbox research**, not an active plan — no
> status/priority/acceptance-criteria block yet.
>
> **Companion document:** [`confidence-signaling-protocol-proposal.md`](confidence-signaling-protocol-proposal.md).
> That proposal's top tier ("Stop") *is* this taxonomy — this document defines the categories in full;
> that one defines the graded behavior around them.

## Problem

Memory Seed already has one escalation list — `agent_collaboration.md`'s Conflict Escalation section —
but it is scoped narrowly to *multi-agent file-ownership conflicts* (shared control-plane files,
dependency lockfiles, session/memory files, seed templates, generated artifacts, binary files). It
does not cover the broader class of single-agent actions that warrant a hard stop regardless of who
else is working: force-pushing, dropping a database table, publishing a release, sending an external
message. Right now that broader judgment lives only in prose scattered across this session's own
host-specific guidance ("NEVER run destructive git commands... unless explicitly requested," "actions
visible to others... consider whether it could be sensitive") rather than in Memory Seed's own
portable, cross-agent control plane.

## Prior Art

- **The source idea**: Security / Destructive / Irreversible / Financial, each triggering "🔴 UNCLEAR →
  explain risk → present 2–3 options → wait."
- **Industry practice**: a three-tier auto-approve/notify/**block** model is the established shape for
  this kind of gate, with the "block" tier reserved for irreversible or high-stakes actions —
  deleting data, sending money, executing code with side effects
  ([Permit.io](https://www.permit.io/blog/human-in-the-loop-for-ai-agents-best-practices-frameworks-use-cases-and-demo)).
  Practical guidance converges on showing, at the gate, what the action is, why it's being taken, what
  will change, and how to undo it
  ([Galileo](https://galileo.ai/blog/human-in-the-loop-agent-oversight)).
- **This repo's own precedent**: this session's own governing instructions already enumerate two of the
  same categories almost verbatim — destructive/hard-to-reverse operations (`rm -rf`, `git reset
  --hard`, force-push, dropping tables) and actions visible to others or affecting shared state
  (pushing code, PRs, messages, third-party posts). Those examples are Claude-Code-specific; this
  proposal generalizes them into a named, portable taxonomy any agent reading `AGENTS.md` can follow.
- **`security_triage.md`** (existing skill) is the deep-dive *review procedure* once a change is
  already flagged as security-relevant. It doesn't define when to stop in the first place — this
  taxonomy is the trigger; `security_triage.md` is what runs after the Security category fires.

## Proposed Taxonomy

Six named categories. Each names concrete Memory-Seed-relevant examples so the guidance is
recognizable, not abstract:

| Category | Examples in this repo's context |
|---|---|
| **Destructive** | `rm -rf`, `git clean -f`, `git branch -D`, dropping a database table, deleting files/branches, overwriting uncommitted changes |
| **Irreversible** | `git push --force` (esp. to a shared branch), `git reset --hard`, schema/format migrations, renaming a published artifact, cutting a release/tag, publishing to PyPI |
| **Security / trust boundary** | credentials, auth logic, encryption, permissions changes, installing a new third-party dependency with network access — hand off to `security_triage.md` once flagged |
| **Shared / control-plane state** | editing `AGENTS.md`, `.memory-seed/agent-rules.md`, `.memory-seed/policy.md`, skill registry files, session/memory files outside the agent's assignment, seed templates under `memory_seed/seed/`, dependency lockfiles — this category is exactly `agent_collaboration.md`'s existing Conflict Escalation list, generalized beyond the multi-agent context |
| **External / irrevocable communication** | `git push` to a remote, opening/closing/commenting on PRs or issues, sending messages (Slack/email), posting to third-party services, publishing a release |
| **Financial** | payment code, pricing logic, billing configuration — less central to Memory Seed's own control-plane domain, but retained since the taxonomy is meant to travel into whatever project consumes Memory Seed, not just this repo |

**Firing rule:** any action matching a category routes to the confidence protocol's Stop tier
(see the companion proposal) regardless of how routine the surrounding task otherwise feels. The
response, in order: (1) name the category and the specific risk in one line, (2) present 2–3 concrete
options including a safe/reversible one, (3) wait for the human's choice — do not proceed on a
default guess.

## How This Composes With Existing Mechanisms (Non-Goals)

- **Not a replacement for Conflict Escalation.** The Shared/Control-plane category above *is*
  Conflict Escalation's list, restated as one category among six, so a single agent working alone gets
  the same discipline a multi-agent orchestrator already has. If this is promoted, Conflict Escalation
  should cross-reference this taxonomy rather than duplicate the file list a second time.
- **Not a replacement for `security_triage.md`.** Security firing this taxonomy is the *trigger*;
  `security_triage.md`'s procedure is what an agent runs once triage is warranted.
- **Not a new automated gate or hook.** Like the rest of Memory Seed's agent guidance, this is
  advisory — an agent recognizes the category and changes its own behavior. It does not require a
  pre-commit hook, CI check, or code-level enforcement, and should not be framed as one.
- **Not a mutation-tracking or governance system.** This taxonomy is about *pausing before acting*, not
  about auditing after the fact — it has no overlap with, and does not gate, the existing
  `related_entries`/`supersedes`/`commits` graph or `links check`.
- **Does not reopen already-settled repo conventions.** Memory Seed's existing git-safety rules (never
  skip hooks, never force-push to main without asking, always create new commits over amends unless
  requested) already enforce several of these categories in practice; this taxonomy names them as a
  general pattern so the same discipline is legible and portable to a different repo or a different
  host agent, not a rewrite of what already works here.

## Where This Would Live (If Promoted)

- Same lazy-loaded skill as the confidence-signaling protocol (tentatively
  `.memory-seed/skills/risk_signaling.md`), or a dedicated `stop_triggers.md` if the combine-vs-split
  question resolves toward splitting — see the companion proposal's open question.
- A cross-reference line added to `agent_collaboration.md`'s Conflict Escalation section, stating that
  its file list is the Shared/Control-plane category of this taxonomy, so the two lists never drift
  independently.
- A cross-reference line added to `security_triage.md`'s "Use this skill when" trigger, noting that a
  Security-category STOP is one path into that skill.

## Open Questions For Promotion

- **Should categories be extensible per-project**, e.g. a `.memory-seed/project.yaml` list of
  project-specific STOP categories (a consuming project's own "financial" or "regulated data"
  triggers)? Worth scoping only if a real need surfaces — avoid speculative extensibility per the
  existing decision-ladder principle ("does it need to exist").
- **How does this interact with worker packets** in `agent_collaboration.md` — should a STOP fired by
  a worker always escalate to the orchestrator (per `conflict_owner`), or can a sufficiently-scoped
  worker packet pre-authorize a specific STOP category for its narrow task? Recommend defaulting to
  "always escalate" and revisiting only if that proves too restrictive in practice.
- **Worked examples.** Same as the companion proposal — a short table of 1–2 concrete recognized-vs-
  not-recognized examples per category would make this actionable rather than abstract; scope at
  implementation time.

## Sources

- [`memory-trail-competitor-analysis.md`](memory-trail-competitor-analysis.md) (this repo, 2026-07-05)
- [Permit.io: Human-in-the-Loop for AI Agents](https://www.permit.io/blog/human-in-the-loop-for-ai-agents-best-practices-frameworks-use-cases-and-demo)
- [Galileo: How to Build Human-in-the-Loop Oversight for AI Agents](https://galileo.ai/blog/human-in-the-loop-agent-oversight)
- [DEV Community: Human-in-the-Loop — When AI Agents Should Stop and Ask](https://dev.to/gantz/human-in-the-loop-when-ai-agents-should-stop-and-ask-30gc)
