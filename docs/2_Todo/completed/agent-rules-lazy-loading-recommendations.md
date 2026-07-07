# Agent Rules Lazy-Loading Recommendations

Recommendations only. This document reviews the current `.memory-seed/agent-rules.md` flow and suggests what should stay always-on versus what could move into indexed lazy skills later. It does not change policy by itself.

## Current Read

`agent-rules.md` has become a combined startup contract, authority model, MCP usage guide, orchestration guide, end-of-turn routine, session schema reference, and bootstrap boundary note. That makes it comprehensive, but it also means every agent pays for details that only apply to some tasks.

## Section Recommendations

| Section | Recommendation | Reason |
|---|---|---|
| Core Principle | keep always-on | Defines the runtime model in a few lines. |
| Runtime Structure | keep always-on | Agents need the shape before using the runtime. |
| Runtime Discovery | keep always-on | This is the central routing invariant. |
| Sub-Project Runtime Creation | move to proposed future skill | Creation is occasional and procedural; keep a short summary in rules. |
| Mode Check Routine | keep always-on | Required to decide operating versus bootstrap mode. |
| Operating Mode Start | keep always-on | This is the startup contract. |
| History Retrieval And Conflict Resolution | shorten and point to existing skill | Keep recency/topical authority rules; move Tool Mechanics detail to a retrieval skill later. |
| Inheritance | keep always-on | Agents need local/parent authority rules before acting. |
| Orchestration Levels | keep always-on | Keep the level summary and point collaboration detail to `agent_collaboration.md`. |
| Token And Model Budget Policy | keep always-on | Small and broadly applicable. |
| File Ownership | keep always-on | Required before editing memory files. |
| Change Permission Model | keep always-on | Prevents accidental control-plane edits. |
| Working Principles | leave unchanged for now | Short cross-cutting rules; revisit after more skills are extracted. |
| End Of Turn | move to proposed future skill | Important but large; keep the obligation always-on, move detailed checklist to an ESR skill. |
| Consolidation Review Triggers | shorten and point to existing skill | Keep trigger list short; move detailed workflow to `memory_consolidation.md`. |
| Skill Loading | keep always-on | Defines the lazy-load mechanism. |
| Public Memory Hygiene | shorten and point to existing skill | Keep the publishable/secrets rule; move detail to a hygiene/security skill. |
| Session Log Format | move to proposed future skill | Schema examples are useful but bulky; keep a short pointer plus required fields. |
| Archive Policy | leave unchanged for now | Very short and harmless. |
| Legacy Boundary | leave unchanged for now | Very short and important for old projects. |
| Bootstrap Boundary | shorten and point to existing skill | Keep the normal-mode warning; move deeper repair guidance to `memory_doctor.md` or a bootstrap skill. |

## Recommended Future Skills

- `history_retrieval.md`: MCP retrieval mechanics, `memory_search` payloads, chunk fetching, and recency-vs-topical examples.
- `session_logging.md`: session frontmatter, entry metadata, DRAFT labels, entry shapes, append-only chronology, and examples.
- `end_of_turn.md`: ESR checklist, orphan/artifact sweep, persona/skill evolution, and baseline-promotion review.
- `memory_hygiene.md`: publishable-memory posture, secrets minimization, public/private risk distinctions, and reusable-template hygiene.
- `subproject_runtime.md`: when to create nested runtimes, inheritance decisions, parent summaries, and bootstrap boundaries.

## Suggested Target Flow

A slimmer `agent-rules.md` should read in this order:

1. Startup contract: runtime discovery, mode check, operating-mode start.
2. Authority model: current files versus session history, inheritance, change permission.
3. Orchestration summary: levels 0-3 and the pointer to `agent_collaboration.md`.
4. File ownership/change model: locked, restricted, and routine append paths.
5. Skill-loading rules: trigger registry, lazy-load rule, and key skill pointers.
6. Minimal end-of-turn obligation: append session entry, verify, and load the ESR skill for the full checklist.

## Migration Notes

- Extract one section at a time and keep exact seed/live parity tests for every moved runbook.
- Preserve current phrases that existing tests and agents rely on until replacements are registered and documented.
- Do not make `agent-rules.md` depend on a skill for startup-critical rules; skills are loaded after startup.
- Use this repository as the first migration target before promoting any extracted skill into the reusable seed.
