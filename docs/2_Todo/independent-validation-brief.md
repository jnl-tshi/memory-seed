---
title: "Independent Validation Brief"
date: "2026-08-05"
project: "memory-seed"
status: "open - awaiting an independent agent"
priority: "P1"
next_action: "Hand this file to an agent that has not worked on Memory Seed's experiments; it derives its own method and reports back."
related:
  - "business/research/field-evidence-log.md"
  - "docs/2_Todo/memory-index-dry-run-plan.md"
  - "docs/CONSTITUTION.md"
---

# Independent Validation Brief

**You are being asked to try to break a set of claims, not to reproduce a method.** This brief
states *what* must be established. Designing *how* is your job, and the design is the point — if
you follow someone else's procedure you inherit its blind spots, which is exactly the flaw this
exercise exists to correct.

## Why you are being asked

Every measurement behind the claims below was designed, run, and interpreted by the same agent that
also wrote the code being measured. That is a standing, acknowledged conflict: probes can be shaped,
unconsciously, to pass. Two silent measurement bugs were already caught mid-run in this programme,
both of which produced clean, plausible, publishable-looking numbers that were wrong. Assume there
is a third one nobody has found. Your independence is the instrument.

## The claims

Each is stated with the number and the sample it came from, so you can aim at it. Treat every one
as a hypothesis to attack.

**C1 — Capture.** An agent working in a project with the full Memory Seed install records its
durable decisions without being asked to. *Claimed: ~0.9 of seeded decisions recorded at full
install; ~0.05 with the MCP tools present but no routing instruction. Two matrices, 120 headless
sessions.*

**C2 — Faithfulness.** When a decision is recorded, the stated reason matches what actually drove
it. *Claimed: 0 of 121 recorded reasons judged a post-hoc reconstruction.*

**C3 — Lifecycle honesty.** A superseded record is never presented as current, and an agent asked
to reverse a recorded decision complies and records the supersession rather than refusing or
silently overwriting. *Claimed: 6/6 compliance, 4/6 recorded a lifecycle edge, 0/6 treated a
superseded record as authoritative.*

**C4 — Retrieval under question-answering.** Given a store built by ordinary work sessions, an
agent can answer questions about that project's history — including facts that were later revised,
facts established weeks earlier, and questions spanning multiple records — and abstains rather than
inventing when something was never recorded. *Claimed: 96.8% correct across 31 probes in six
categories, 0 fabrications on 8 never-stored trap questions.*

**C5 — The fixes were causal.** Two changes made on 2026-08-05 — serving retrieval results at
decision granularity, and routing durable non-decision facts to `index.md` at capture time — are
what moved C4 from 71.0 to 96.8. *Claimed: capture routing alone accounts for most of it;
long-term retention went 1/4 to 4/4.*

## What counts as a finding

All four of these are valuable. None is a failure on your part:

- **A claim survives your best attempt to break it** — say so, and say what you tried, because a
  claim's strength is the strength of the attack it withstood.
- **A claim fails** — the number is wrong, or right only under conditions the claim doesn't state.
- **A claim is unfalsifiable as written** — it cannot be tested without smuggling in an assumption.
  This is a finding about the claim, and a useful one.
- **The measure is wrong** — the claim is true and uninteresting, or it measures something other
  than what it purports to. Say that plainly; it is the most valuable outcome available.

You may also conclude that a claim cannot be evaluated within a sensible budget. Say so early
rather than producing a weak result.

## Constraints

**Do not read the existing experiment harnesses before you have written down your own design.**
`experiments/` in this repository contains prior probe sets, answer keys, judging prompts and
scoring code. Reading them first will anchor you to the design whose blind spots you are here to
find. Write your method down first; consult them afterwards if you want, and say in your report
whether you did and whether it changed anything.

**Isolate your runs.** This repository's own `.memory-seed/` store is live project memory. Nothing
you run may write to it. Fixtures must be self-contained (their own store, their own git repo),
and you should verify isolation rather than assume it — the runtime resolves its store by walking
*upward* from the working directory, with no boundary, so a fixture without its own store silently
writes into the parent's.

**Pre-register.** Write down what you expect to find and what would falsify it *before* you run
anything, and keep that file unedited. If a result lands on the wrong side of a threshold you set,
report it; do not add samples to the arm that disappointed you.

**Budget.** Aim to stay under roughly $50 of model spend. Say what you spent. If a stronger design
needs more, argue for it rather than quietly running it.

**Report honestly over favourably.** Statements about what a result does *not* establish are worth
more here than the result. If your sample is too small to support a verdict, say the number and its
uncertainty rather than the verdict.

## Environment facts (terrain, not method)

These cost real time to discover. They are facts about the machine, not hints about design:

- The product is a Python package in this repository; `python -m memory_seed.cli --help` and the
  MCP server under `memory_seed/mcp_server.py` are the two surfaces. Installing into a fresh
  project is `init_project()` / `memory-seed init`.
- Headless agent runs need permission flags to work unattended, and those flags differ per agent
  CLI. Whatever you choose, keep it identical across arms so it differences out.
- On Windows, prompts passed as command-line arguments to agent CLIs can be silently truncated by
  the `.CMD` shims; stdin is reliable. A batch of agent calls returning empty or uniform results is
  the symptom.
- An agent session's own account-level tooling (extra MCP servers, global instruction files) leaks
  into a fixture unless explicitly excluded, and changes what you are measuring.

## What to hand back

A single report containing: your method and why you chose it; your pre-registration; per-claim
verdicts with the numbers and their uncertainty; what you could not test; and anything you found
that this brief did not anticipate — especially that. Raw run artifacts should be preserved and
referenced, not pasted.

If you find that a claim is true but that the underlying thing is not worth claiming, that belongs
in the report too. The purpose is a trustworthy picture, not a favourable one.
