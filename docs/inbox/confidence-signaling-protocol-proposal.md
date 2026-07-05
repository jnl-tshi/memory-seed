---
title: "Proposal: Graded Confidence-Signaling Protocol"
date: "2026-07-05"
project: "memory-seed"
related_to: "docs/inbox/memory-trail-competitor-analysis.md"
author_context: "Prepared for Jean Nathan Tshibuyi"
format: "Markdown research proposal"
---

# Proposal: Graded Confidence-Signaling Protocol

> **Origin:** flagged as a genuinely good idea (not a threat) in
> [`memory-trail-competitor-analysis.md`](memory-trail-competitor-analysis.md) — the `frmoretto/memory-trail`
> skill requires an agent to signal a graded certainty level at the start of every response, with named
> risk factors that shift the required behavior. This document researches the idea further, adapts it
> to Memory Seed's own conventions, and proposes where it would live if promoted to `docs/todo/`.
> This is **inbox research**, not an active plan — no status/priority/acceptance-criteria block yet.

## Problem

Memory Seed already asks agents to exercise judgment about risk in several scattered places:

- The Working Principles in `.memory-seed/agent-rules.md` include a POC-gate for risky automated
  methods and a verification split (state what the agent verified vs. what only the user can verify),
  but nothing that says *when to pause and ask* as a general rule.
- `.memory-seed/skills/agent_collaboration.md`'s Conflict Escalation section lists specific file
  categories that require escalation — but only in the multi-agent/orchestrator context, not for a
  single agent working alone.
- Individual host tools (e.g., Claude Code's own system-level guidance) already encode a reversibility-
  and-blast-radius judgment call — "consider the reversibility and blast radius of actions... for
  actions that are hard to reverse, affect shared systems, or could otherwise be risky, transparently
  communicate the action and ask for confirmation" — but that discipline is **specific to whichever
  host tool happens to bake it in**. `AGENTS.md`/`CLAUDE.md`/`GEMINI.md`/Copilot routing exists
  precisely because Memory Seed is meant to give *every* agent the same durable guidance regardless of
  vendor. Right now, this one is missing: an agent using Codex, Gemini CLI, or Cursor against this
  repo has no equivalent written-down discipline unless its host happens to supply one.

The gap isn't "agents never think about risk" — it's that the judgment is informal, host-dependent,
and has no consistent surfaced signal a human can scan quickly to know when to pay closer attention.

## Prior Art

- **The source idea** (`frmoretto/memory-trail`, see the competitor analysis): five levels
  (🟢 CERTAIN 95%+ / 🔵 CONFIDENT 80–94% / 🟡 PROBABLE 60–79% / 🟠 UNCERTAIN 40–59% / 🔴 UNCLEAR <40%),
  with named risk adjustments applied as literal percentage arithmetic (e.g., `DESTRUCTIVE: -15%`,
  `TESTED: +15%`) before choosing a behavior.
- **Academic/industry practice, 2026**: reversibility-tiered gating shows up as an established pattern —
  a three-tier **auto-approve / notify / block** model for human-in-the-loop agent oversight, where the
  gate sits on reversibility and blast radius rather than a numeric score
  ([Permit.io](https://www.permit.io/blog/human-in-the-loop-for-ai-agents-best-practices-frameworks-use-cases-and-demo),
  [Galileo](https://galileo.ai/blog/human-in-the-loop-agent-oversight)). Separately, current research on
  agentic confidence (["Agentic Confidence Calibration"](https://arxiv.org/pdf/2601.15778),
  ["Agentic Uncertainty Quantification"](https://arxiv.org/html/2601.15703v1)) documents that agents are
  **systematically overconfident** and that calibration failures compound across a trajectory — the
  motivating problem is real, not manufactured.
- **This repo's own precedent**: the "Executing actions with care" guidance already present in this
  session's system-level instructions is, in substance, the same pattern — reversibility and blast
  radius determine whether to proceed or confirm first. That guidance is Claude-Code-specific; this
  proposal is to write an equivalent, tool-agnostic version into Memory Seed's own control plane.

## Why Not Copy the Source Idea Directly

The competitor's numeric arithmetic (`85% + TESTED: +15% + REVERSIBLE: +10% = 100% -> CERTAIN`) is
**pseudo-quantification**. An LLM cannot reliably introspect a calibrated numeric confidence, and
percentage math applied to an uncomputed number creates false rigor — it looks precise without being
accurate, which is worse than an honest qualitative signal. The three-tier academic pattern
(auto-approve/notify/block) is more defensible precisely because it ties the gate to *observable*
properties of the action (is it reversible? does it touch shared state?) rather than an unverifiable
self-reported percentage.

## Proposed Design

A small number of **qualitative, action-tied tiers** — no arithmetic, no percentages:

| Tier | When | Behavior |
|---|---|---|
| **Proceed** | Routine, reversible, matches established repo patterns | Act; no pause. Note the action in the normal course of the response. |
| **Proceed-and-flag** | Reversible but non-trivial — meaningfully changes behavior, or touches a file class that others may care about | Act, but state the assumption plainly so the human can course-correct without being blocked. |
| **Propose-and-wait** | Genuinely ambiguous, underspecified, or outside what the user explicitly authorized | Present the plan or options; do not act until the human responds. |
| **Stop** | Matches a category in the companion
[STOP-trigger taxonomy proposal](stop-trigger-taxonomy-proposal.md) | Explain the risk, present 2–3 concrete options, and do not proceed without explicit approval — regardless of how "confident" the agent otherwise feels. |

Factors that push a judgment toward a higher tier (adapted from the source idea, kept qualitative):
reversibility, blast radius (local file vs. shared/control-plane vs. external system), destructive
potential, security/financial sensitivity, presence or absence of test coverage, and whether the
change is isolated (branch/feature-flag) or immediately live. These are the same factors this
session's own risk guidance already names — the proposal's job is to make them explicit and portable,
not to invent new ones.

**Stop is a hard floor, not just the far end of a gradient**: an action matching a STOP-trigger
category always routes to Stop regardless of how routine the rest of the task feels, exactly as
Memory Seed's own commit-safety rules already work for `--force` pushes and `--no-verify`.

## How This Composes With Existing Mechanisms (Non-Goals)

- **Not a replacement for `capability_tier`** in `agent_collaboration.md`'s Task Packet — capability
  tier is about which model/vendor strength a task warrants; this protocol is about whether to act or
  pause on a given action, independent of which tier is doing the work.
- **Not a replacement for Conflict Escalation** — that list (control-plane files, dependency files,
  session/memory files, seed templates, etc.) is a specific instance of the general "shared state"
  factor above, scoped to multi-agent orchestration. This protocol is the general single-agent-or-
  multi-agent version; Conflict Escalation stays the authoritative list for *which files* count as
  shared state.
- **Not a new session-log YAML field.** Per the graph-edge-contract's own standing rule ("one name,
  one meaning" — don't add schema surface casually), this stays pure behavioral guidance. When a
  Propose-and-wait or Stop moment is genuinely load-bearing for future readers, it belongs in the
  entry's existing `R`/`A` prose (the same way the failed-approaches-logging convention already asks
  agents to record rejected approaches under `A` unprompted) — not a new structured field.
- **Not an enforced hook.** Like the rest of `agent-rules.md` and `agent_collaboration.md`, this is
  advisory guidance an agent follows, not a code-level gate. Memory Seed's existing stance is that
  hooks are optional add-ons, not core enforcement.
- **No emoji/percentage requirement.** Plain words (Proceed / Proceed-and-flag / Propose-and-wait /
  Stop) read cleanly in any terminal or log without relying on a specific rendering environment.

## Where This Would Live (If Promoted)

- A new lazy-loaded skill, tentatively `.memory-seed/skills/risk_signaling.md` (paired with the
  companion STOP-trigger taxonomy — see that proposal's "Where This Would Live" section for the
  combine-vs-split question), registered in `skills/index.md`'s trigger registry with `required: true`
  triggers on ambiguous, destructive, irreversible, security-sensitive, or externally-visible actions.
- One short bullet added to `agent-rules.md`'s Working Principles, in the same terse, bold-lead-in
  style as the existing Mermaid and decision-ladder bullets, pointing at the skill.
- A one-line cross-reference added to `agent_collaboration.md`'s Conflict Escalation section noting
  that it is a specialization of this protocol's "shared state" factor.

## Open Questions For Promotion

- **Combine or split from the STOP-trigger taxonomy?** They are two faces of one coherent system
  (Stop-tier here *is* the STOP-trigger taxonomy). A single skill file may be simpler to load and keep
  consistent; two files may be easier to reference independently (e.g., pointing at just the STOP list
  from a security-review context). Recommend deciding this when scoping the `docs/todo/` plan.
- **Should Propose-and-wait ever be skippable for a trusted, narrowly-scoped worker packet** (e.g., a
  validator with `capability_tier: frontier` and a tightly bounded task)? Worth a short acceptance
  criterion either way rather than leaving it implicit.
- **Does this need a lightweight example bank** (2–3 worked examples per tier, mirroring the source
  idea's worked calculations but without the arithmetic) to make the guidance concrete rather than
  abstract? Likely yes, scoped at implementation time.

## Sources

- [`memory-trail-competitor-analysis.md`](memory-trail-competitor-analysis.md) (this repo, 2026-07-05)
- [Permit.io: Human-in-the-Loop for AI Agents](https://www.permit.io/blog/human-in-the-loop-for-ai-agents-best-practices-frameworks-use-cases-and-demo)
- [Galileo: How to Build Human-in-the-Loop Oversight for AI Agents](https://galileo.ai/blog/human-in-the-loop-agent-oversight)
- [Agentic Confidence Calibration (arXiv 2601.15778)](https://arxiv.org/pdf/2601.15778)
- [Agentic Uncertainty Quantification (arXiv 2601.15703)](https://arxiv.org/html/2601.15703v1)
- [Responsible AI Labs: AI Agent Safety in 2026](https://responsibleailabs.ai/knowledge-hub/articles/ai-agent-safety-2026)
