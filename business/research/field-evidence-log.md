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

## E2 — Direct message with `Environmental_Ask675`, 2026-08-03

**Source:** private exchange following E1, initiated as the Report 6 §7 follow-up. Asked what would have
saved them six months, and whether an out-of-the-box tool would have been used or whether they would still
have built their own.

### What was observed

> *"Honest answer: early on, yes, I'd probably have tried an out-of-the-box thing. But the reason mine works
> isn't the decision log — it's that the rules live inside the instructions each agent actually loads, and
> that the system got refined every time it failed in front of me. That co-evolution is the part I don't
> think ships in a box: the tool would need to make capturing a decision cheaper than not capturing it, at
> the moment it happens, or people stop feeding it — same reason my notes file failed. If you build that
> part well, it's useful. If it's another file format plus discipline, people already have that and it
> already fails."*

### Why this is the most important quote in the log

It contains a market answer, a design criterion, and a disqualifier in one paragraph.

1. **A tool could have won them.** *"Early on, yes, I'd probably have tried an out-of-the-box thing."* The
   build-your-own outcome was not preference; it was the absence of an option.
2. **The design criterion, stated exactly:** *"make capturing a decision cheaper than not capturing it, at
   the moment it happens."* Not easier. Not enforced. **Cheaper than the alternative of skipping it.**
3. **The disqualifier:** *"If it's another file format plus discipline, people already have that and it
   already fails."*

**Point 3 is the sharpest criticism this project has received, and it lands.** Memory Seed is, from the
outside, a file format plus discipline — with enforcement added. **Enforcement and cheapness are not the
same thing.** Enforcement means you cannot skip it; cheapness means you do not want to. A write-time gate
that refuses a malformed record makes capture *mandatory*, which is a different property and could even
read as friction.

The honest defence is that the MCP authoring path and the SessionStart hook shift the *cost* rather than
merely imposing a rule: the agent that just made the decision writes the entry, so the human is not the
bottleneck — which is precisely the mechanism this same responder described in E1. **That defence is
plausible and untested.** It is the single most important thing to test, and it is testable: does an agent
with the MCP tool available record decisions without being asked, in real sessions?

**Also recorded:** *"the system got refined every time it failed in front of me. That co-evolution is the
part I don't think ships in a box."* A packaged tool cannot deliver the learning that comes from a system
breaking in front of its author. Whether that is a permanent moat for self-built systems or an argument for
shipping a configurable skeleton is an open question.

---

## E3 — r/softwarearchitecture, 2026-08-03

**Source:** our own post, *"If you stopped writing ADRs, what actually made you stop?"*, opening with the
MSR study finding that ~50% of ADR-adopting repositories hold only one to five records.

**Engagement at capture:** ~2.7K views · 3 upvotes · 5 comments.

### What was observed

**`svhelloworld` — the finding that most challenges the product thesis:**

> *"I don't think they are terribly useful as a historical artifact. But as a design artifact to generate
> conversations, explore alternatives, get more than just the architect's voice into the architecture design
> process, I think moving ADRs through a PR process is invaluable. I never go back and revisit closed user
> stories and I don't think about them as system documentation. I feel the same way about ADRs."*

**`Lilacsoftlips`, independently agreeing:**

> *"The team has to care. I find a full adr to be kinda pointless. Design docs/reviews are ephemeral imo.
> They are almost never revisited. Documenting the decision in the pr/code documentation is sufficient in
> most cases."*

**`Clyde_Frag`, on the time horizon:**

> *"In an industry where people typically stick around at a company for 3-4 years max, it can feel like a
> pointless exercise and it's something that requires buy in from the whole team."*

**`SJrX`, the counter-case** — writes many ADRs, finds them *"useful for understanding and reasoning through
a problem"*, finished their draft ADRs on the way out of a job and reports the successor was glad of them.
Also: *"It is hard to keep up with publishing them."*

**`heavy-minium`, unelaborated:** *"There are almost always better, more specific places to position the
decisions than one big central register. ADRs are really just the most primitive form of taking architecture
notes."* Asked to expand; no answer at capture.

**`amendCommit` — the most detailed abandonment narrative collected, and the most consequential.**
Engagement at this capture: ~3.5K views · 3 upvotes · 7 comments.

> *"We had a couple of meetings about how to properly adopt coding agents… I chose to suggest ADRs as one
> way to track our decisions. The proposal was adopted.*
>
> *A few months later, my team does not care, **they refused to adopt an agent that would validate new code
> against existing ADRs**, I'm the only one to write any ADR and nobody has time for review (or any
> discussion leading to a shared vision on architecture); then my engineering manager wanted us to move ADRs
> from our repos to a common 'architecture' repo, **which puts it away from actual, runnable code, and gates
> it behind a review process nobody really owns**.*
>
> *I'm moving on and they're going to keep vibe-coding features with zero harness because improved DX is not
> 'customer centric' and is not 'respecting individual developers in their independent use of agents'."*

Three findings, in ascending order of importance.

**1. Moving the record away from the code killed it.** *"Puts it away from actual, runnable code, and gates
it behind a review process nobody really owns."* This is direct field evidence for repo-local, Git-native
storage — Memory Seed's core architectural choice — observed as the *failure* of the alternative rather than
argued from principle. It also answers `heavy-minium`'s "better places than one central register": a central
register is exactly what failed here.

**2. The agent-validates-against-ADRs mechanism was offered and refused.** Not "nobody thought of it" —
someone proposed it and the team said no. This is the first evidence that the mechanism can exist and still
lose.

**3. The stated reason is a cultural objection no report anticipated:** enforcement was rejected as failing
to respect *"individual developers in their independent use of agents."* **Constraining an agent was read as
constraining the developer.** That is a governance-versus-autonomy conflict, and it is a category-level
barrier rather than a product-level one — a competitor with better tooling would have hit the same wall.

### How this qualifies the reframe below

The reader-changed argument holds — agents do read what humans do not. But **it is not sufficient**. The
agent only reads the record if the organisation permits the agent to be constrained by it, and here a team
explicitly declined that. *"The team has to care"* has now been said twice in one thread, once by someone
who cared and left.

**Implication for Report 6's ICPs.** ICP-2 (the small AI-forward team) is harder than assumed unless the
team *already* cares — adoption cannot be driven by the one person who does. ICP-1 (the solo or
technical-founder builder) has no such problem, because the person deciding and the person adopting are the
same. This strengthens the case for entering solo-first and treating team adoption as an expansion that
requires an existing culture rather than one the tool can create.

### What this establishes

**Two independent practitioners say the value of an ADR is in the writing, not the reading.** Deliberation,
forcing alternatives into the open, getting more than the architect's voice in — those survive. The
retrievable-historical-record premise does not. `SJrX` frames the same thing positively: useful *for
reasoning through* a problem.

**Nobody in this thread cited retrieval as the payoff.** That directly attacks the assumption every report
in this programme rested on.

**The named blockers are social, not technical:** the team has to care; buy-in is required; tenure is 3–4
years so the long-horizon argument is weak; keeping up with publishing is hard. **Not one person blamed
tooling.**

### The reconciliation — and the strongest reframe available

E1 and E3 appear to contradict each other. In the agent thread, everyone wanted decisions retrievable and
built systems to make it so. In the human thread, experienced engineers say nobody ever re-reads them.

**Both are true, because the reader changed.**

Humans do not re-read decision records — two independent reports here, consistent with the MSR abandonment
data. **Agents read them every session, mechanically, without motivation or recall limits.** The value
proposition shifts from *"a future colleague will thank you"* — which this evidence suggests is false — to
*"your agent loads this before it proposes anything"*, which is a mechanical property rather than an
aspirational one.

That reframe is worth more than any framework mapping in Reports 1–5. It also explains the abandonment
literature: ADRs failed for two decades because the reader was a human who never came back. **The reader
arriving is the change, not the format.**

**Caveat, and it is a real one:** if the value is deliberation rather than retrieval, then the product's
job is partly to improve *the moment of deciding* — which is closer to `svhelloworld`'s "move it through a
PR process" than to a searchable corpus. Do not let the reframe become a reason to stop listening; both
readings should be tested.

---

## Method notes for future entries

- **Post as a practitioner with a real question.** Never pitch. If the pain is not described unprompted, that
  is the finding.
- **Ask about past behaviour and specific incidents**, never opinions or hypotheticals. Perceived and measured
  productivity diverge by a characterised margin (Report 4).
- **Record engagement metrics honestly**, including unflattering ones. Zero upvotes on 2.8K views is data.
- **Effort already spent is the strongest signal** short of payment. Someone who built a workaround outranks
  ten who agree it sounds useful.
