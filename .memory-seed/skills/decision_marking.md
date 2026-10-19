---
memory-system-version: 2.24
tags:
  - memory-seed
  - skill
  - decision-marking
---

# Decision Marking

Use this skill when a conversation produces a material decision signal. The marker narrows where a later
curator should inspect; it never proves a decision, writes repository files, or creates authoritative memory.

## Marker Contract

Call `memory_decision_mark` immediately after the qualifying turn with:

- `strength`: `hard` or `soft`;
- `state`: `accepted` or `proposed`;
- `origin`: `user` or `agent`;
- `trigger_class`: `explicit_commitment`, `contextual_acceptance`, `correction`, `option_selection`, or `agent_inference`;
- `issue_hint`: a short non-authoritative issue label;
- `trigger_quote`: a short exact phrase from the source turn.

The surrounding rollout supplies the session, turn, and source ordinal. Never manufacture coordinates.

## Trigger Table

| Signal | Marker | Required interpretation |
| --- | --- | --- |
| explicit commitment | hard / accepted | The user directly commits to an action or policy. |
| contextual acceptance | hard / accepted | An acceptance such as “that’s the right approach” resolves exactly one nearby proposal. |
| correction | hard / accepted | A correction closes the active choice rather than merely adding information. |
| option selection | hard / accepted | A named option or direct answer selects among visible alternatives. |
| tentative proposal | soft / proposed | A possible action is raised without explicit acceptance. |
| emerging consensus | soft / proposed | Direction is converging but authority has not committed. |
| agent inference | soft / proposed | The agent detects a likely decision without explicit user acceptance. |

Contextual acceptance is hard only when exactly one proposal is resolvable in the bounded nearby context.
Otherwise use a soft marker or no marker.

## Exclusions

Use **No marker** for brainstorming, hypotheticals, quotations, replayed history, rejected or negated choices,
status reports, tool outcomes, and an ambiguous acknowledgement such as “okay” when it could refer to more
than one proposal. Do not mark an assistant proposal as accepted without a grounded user agreement span.

## Output Discipline

- Copy the trigger quote exactly and keep it short enough for later source validation.
- Describe the issue without asserting that the marker is correct.
- Continue normal session logging for durable decisions. The marker is evidence about where to inspect only.
