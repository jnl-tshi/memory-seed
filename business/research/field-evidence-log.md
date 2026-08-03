---
title: "Field Evidence Log"
status: active
last_reviewed: "2026-08-03"
next_review_due: "2026-09-03"
confidence: low
kind: "report"
---

# Field evidence log

**The first real demand evidence the project has collected.** Reports 1–7 were desk research and said so
repeatedly: *no user interviewed, no purchase attempted, no retention observed.* This log records what
actual practitioners said, unprompted, and separates what it establishes from what it does not.

**Standing rule for this file:** record the observation and its source verbatim before interpreting it.
Quotes are public posts, cited by their public handle so a claim can be checked. Interpretation is marked
as such and is always separable from the evidence.

---

## E1 — r/ClaudeAI, 2026-08-03

**Source:** our own post, *"How do you stop agents re-deciding things you already decided?"*
([thread](https://www.reddit.com/r/ClaudeAI/comments/1vegd28/)), posted per the Report 6 §7 test design —
a genuine practitioner question, no product mentioned, no pitch.

**Engagement at capture:** ~2.8K views · **0 upvotes** · 24 comments · 6 distinct responders.

### What was observed

**Every responder described a hand-rolled workaround. None disputed the problem.** Six for six, unprompted.
Nobody named a commercial product — no Pieces, Unblocked, Mem0, or any tool. Everyone is building it
themselves.

**The convergent design.** `Environmental_Ask675`, who reports spending *"half my time working on my project
and half my time more or less trying to answer this question"*, described a system they built alone:

> *"Decisions are records, not notes. Every settled decision gets a structured entry: what we decided, the
> rationale, and — this is the part that solves your June problem — the alternatives we REJECTED and why.
> 'Tried X, broke on Y, do Z instead' is literally a field. Records are never deleted, only marked
> superseded-by, so the failure story survives even after the decision changes. And the agent writes the
> entry at the moment of abandonment, in the same session that abandoned it. That fixes 'I forget to update
> the file' — you were the bottleneck; make the agent that just lived the failure write it down before it
> moves on."*

**The loading lesson**, from the same responder:

> *"A rule only binds if it's in the prompt the session actually loads. I learned this the expensive way —
> rules that lived in a shared doc got ignored under pressure; the same rules pasted into the session's own
> role prompt held every time. Your `AGENTS.md` is 'how we write code here' ambient knowledge. The
> decision-search step has to be in the operating instructions of the session doing the work, or it's
> decorative."*

And the follow-up correction they added on reflection:

> *"Don't rely only on the agent remembering to search. Where you can, flip it to push — make the session's
> startup load the decisions relevant to its task before it proposes anything… Search catches the long tail;
> startup-loading catches the case you actually described, where the agent had 'no way of knowing' — it only
> had no way of knowing because nothing put the record in front of it."*

**A behavioural success signal**, same source:

> *"Re-derivations started dying at the proposal stage — the agent finds the June record and says 'this was
> tried, here's why it failed' instead of proposing it. That exact sentence, from the agent, is how you know
> it's working."*

**The ADR failure mode**, from `biohackeddad`, who had earlier said only *"ADRs can also cause issues. Trial
and error"* and was asked what those issues were:

> *"Making the AI not willing to go with your product decision because it doesn't understand the ADR."*

**A counter-pressure**, from `Kimani_AI`, who keeps an `ADDITIONAL_CONTEXT.md` during hard problems and
discards it afterwards. Asked why:

> *"When I've solved the problem I don't need the doc anymore, so removing it clears up context so lower
> token cost."*

**A dissent**, from `ellicottvilleny`: the problem is workflow discipline, not missing memory — use fresh
task-scoped sessions, version control, automated tests. *"You catch stuff by automated tests."*

**A storage-location argument**, from `MaterialHead4801`, challenging a codebase-search approach:

> *"I want those decisions recorded outside the code itself. When the project gets big enough, having to scan
> the entire codebase to find out why a database was chosen seems wasteful?"*

They separately described a controller/agent split with a per-project wiki holding decisions and *"a ledger
of successes and failures ('traps' that have caused wasted effort previously)"*, plus a `/clear` ritual that
updates docs and leaves breadcrumbs before a session ends.

### What this establishes

1. **The problem is real and self-reported unprompted.** Six of six. Report 6's Test 1 passes on its own
   stated bar — the pain was described without prompting, with concrete incidents attached.
2. **Effort already spent is present throughout**, including one responder at roughly 50% of their working
   time. That is the strongest demand signal available short of payment.
3. **The design converges independently.** Structured records, rejected alternatives as a field, never
   delete only mark superseded, write at the moment of abandonment, search before proposing. That is `D`/`R`/`A`,
   `replaces`/`evolves`, and write-time capture, arrived at by someone who has never seen this project.
4. **Nobody named a commercial tool.** Consistent with Report 3's "unoccupied" finding — though six comments
   in one subreddit is weak evidence for a negative.

### What it does not establish

- **Nothing about willingness to pay.** Not asked, correctly. Enthusiasm for a self-built workaround is not
  budget.
- **Nothing about passive capture.** Report 6's Test 2 remains entirely unrun; no responder mentioned Pieces,
  Unblocked, or any passive tool in either direction.
- **Nothing about breadth.** ~2.8K views produced **zero** upvotes. The engaged minority engaged deeply; the
  rest scrolled past without endorsing. This reads as **niche with intensity**, not a mass-market pain, and it
  argues against the upper revenue path in Report 6 §5 rather than for it.
- **Nothing generalisable.** One subreddit, one thread, self-selected responders, six people.

### What it revises

| Report | Revision |
|---|---|
| **R4** | Add the behavioural success metric — *the agent says "this was tried, here's why it failed" at proposal stage*. Observable, unambiguous, zero instrumentation. Cheaper and more direct than anything in the designed suite. Also: token cost is a live counter-pressure, someone is actively deleting context to save tokens, so token efficiency is confirmed as the right lead metric. |
| **R5** | A new ADR failure mode, absent from the academic literature: the record becomes **over-authoritative** and blocks a legitimate new decision. Staleness cuts both ways — a decision record can be wrong *and* obeyed. `evolves`/`replaces` is the answer, but the failure is worth naming. |
| **R7** | **The binding constraint is loading, not storage.** All seven reports treated the record as the product and retrieval as a feature. The field lesson is the reverse: a perfect record that is not injected at the right moment is decorative. Push (startup-load relevant decisions) beats pull (agent remembers to search). The SessionStart hook and MCP retrieval move from plumbing to headline. |

### The uncomfortable implication

The convergent design is validation *and* threat. One competent person reproduced the core model alone, in a
few months of part-time effort, without prior art. **The moat is not the data model.** If there is one, it is
in the parts they did not build: validated referential integrity on supersession, enforcement that refuses a
record without a reason, and guaranteed injection at session start.

### Follow-ups from this thread

- `Environmental_Ask675` declined a call but offered to consult in-thread. Two questions worth asking:
  *what would have saved you the six months*, and *what can your system still not do?* The first separates
  "validated design" from "buildable by anyone"; the second is worth more than any benchmark.
- `MaterialHead4801` holds the strongest opinion on where records should live and has built a per-project
  wiki. Worth a direct question about what breaks at scale.
- `biohackeddad`'s over-authoritative-ADR failure deserves a second question: how did they detect it, and
  what did they do?

---

## Method notes for future entries

- **Post as a practitioner with a real question.** Never pitch. If the pain is not described unprompted, that
  is the finding.
- **Ask about past behaviour and specific incidents**, never opinions or hypotheticals. Perceived and measured
  productivity diverge by a characterised margin (Report 4).
- **Record engagement metrics honestly**, including unflattering ones. Zero upvotes on 2.8K views is data.
- **Effort already spent is the strongest signal** short of payment. Someone who built a workaround outranks
  ten who agree it sounds useful.
