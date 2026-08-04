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

### The register critique — a coherent counter-position from three responders

`heavy-minium` opened with *"there are almost always better, more specific places to position the decisions
than one big central register. ADRs are really just the most primitive form of taking architecture notes."*
Asked to expand, they did:

> *"You'll almost always have a piece about security, something about integration/contracts/boundaries, data
> architecture/schema evolution/migration, domain models, environments, reliability, observability —
> whatever. My point is that instead of converging everything into one place, it may be better to place it
> directly where people are looking for it and in the format most appropriate and easy to digest and
> manage."*

Two others in the same thread argue the same shape from different angles:

- **`Lilacsoftlips`:** *"Documenting the decision in the pr/code documentation is sufficient in most cases."*
- **`DrShocker`:** *"Sometimes when a test is something like 'fix ticket #123' and I find it failing after
  I'm doing something else, that can help me figure out if the test is locking down the right behavior or
  not. Otherwise I have to assume sometimes without much context whether the test is doing anything
  worthwhile."*

**The position, stated fairly: put the reason where you will trip over it — in the concern's own document,
in the PR, in the test name — not in a register you must remember to consult.** Note that none of them
argues against recording rationale. The disagreement is about *placement*, and it is the most substantive
architectural criticism the project has received.

**What it lands on.** Memory Seed *is* a central register. `F:` records which files a decision touched; it
does not put the reason in the file. Someone reading the security config does not encounter the security
decision.

**What partially answers it.** The record is repo-local rather than in a separate wiki — and `amendCommit`'s
account above is direct evidence that moving records *out* of the repo is what kills them. The two-axis topic
vocabulary and `adr list`, which the shipped implementation describes as listing *architectural concerns and
their accepted heads*, are concern-scoped views over a single store. That is closer to `heavy-minium`'s ask
than a flat register, though not the same as native placement in each concern's own document.

**Where the counter-position is weakest, and this is the reconciliation:** annotation-at-point-of-use can
only be **pulled** — it helps whoever is already looking at that file. A register can be **pushed**, loaded
at session start before anything is proposed. For a human reader, scattered annotation is plainly better:
you encounter it without effort. For an agent starting cold on a task, it is worse, because nothing puts the
security decision in front of an agent editing an unrelated module.

**This is the same axis as E2's loading finding, arriving from the opposite direction, and it sharpens the
product question rather than settling it: is the register a store that feeds retrieval, or is it the
artefact itself?** The first survives this critique. The second does not.

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

## E4 — Natural experiment: this repository's own history, 2026-08-03

**Source:** the parent repo's git log and session corpus, with scaffolding boundaries dated from
`CHANGELOG.md`: the `Memory-Entry:` trailer convention introduced 2026-07-03 (rule in `agent-rules.md`,
applied manually); the auto-stamping `prepare-commit-msg` hook shipped in 2.18.0 on **2026-07-13**;
the SessionStart orientation hook shipped in 2.6.0 on 2026-06-13; session-log-check escalation in
2.17.0 on 2026-07-10. Read-only measurement, reproducible from the commands in the session entry.

### What was observed

**Trailer coverage on commits touching session entry files** (sidecar-only commits excluded — the
hook's actual target):

| Period | Coverage |
|---|---|
| Before the convention existed (< 2026-07-03) | 0/35 (**0%**) |
| **Rule era** — convention in `agent-rules.md`, applied manually (07-03 → 07-12) | 47/134 (**35%**) |
| **Mechanism era** — git hook stamps automatically (≥ 07-13) | 355/494 (**72%**) |

**Session entries per active day:** 7.9 (pre-SessionStart-hook) → 9.1 (post) → 22.4 (after
escalation + stamping era).

### What this establishes

**The same obligation, in the same repository, followed by the same kinds of agents, doubled from
35% to 72% compliance when it changed from a rule to a mechanism** — at a sharply dated boundary.
This is E2's loading lesson (*"a rule only binds if it's in the prompt the session actually loads"*)
measured rather than reported, and it hands the fixture experiment a real prior: the rule-vs-mechanism
delta was ~2× here, so large between-level effects at L2→L3 are plausible.

### What it does not establish

- **Nothing about L0/L1.** This repo carried the full rules contract throughout; the natural
  experiment only spans rule-with-contract → rule-plus-mechanism.
- **The entries-per-day series is activity-confounded and is NOT attributed.** The 9.1 → 22.4 jump
  coincides with the swarm campaigns and the research programme — the work itself exploded. Only the
  trailer series has a clean mechanism boundary.
- **Observational throughout**: agents changed over the period, conventions matured, and the agent
  performing this measurement is part of the hook-era data.
- **The 28% residual in the hook era is unaudited** — some of it is commits the hook legitimately
  skips; a commit-level audit would be needed before treating 72% as the mechanism's ceiling.

---

> **Read E5 together with E6.** A second 60-session replication reversed E5's threshold verdict.
> The dose-response below stands; the binary "only L3 is reliable" call does not. E6 has the pooled
> estimate and the reason the threshold question is unanswerable at this sample size.

## E5 — Controlled experiment: scaffolding dose-response, 2026-08-04

**Source:** `experiments/agent-capture/`, 60 scored headless Claude sessions across four scaffolding
levels × three frozen tasks × five repetitions, pre-registered in `PREREGISTRATION.md` before any
scored run. Blind judging by Codex (a different model family), in two stages so the answer key never
reached a blind judge. Every run reported `parent_isolated: true`; zero harness failures. Cost
$99.29, 1,366 turns, ~80 minutes wall clock.

### What was observed

| Level | Scaffolding | Seeded decisions made | Recorded | **Judged capture** |
|---|---|---|---|---|
| L0 | MCP write path only | 18 | 0 | **0.00** |
| L1 | + one `AGENTS.md` line naming the store | 19 | 14 | **0.74** |
| L2 | + full rules contract and skills, hooks removed | 19 | 15 | **0.79** |
| L3 | + agent hooks and the git commit hook (stock install) | 18 | 17 | **0.94** |

The judge found 203 decisions across the 60 sessions (mean 3.4 each, range 1–7) and split them
128 recorded / 75 not, so it discriminated rather than rubber-stamping.

### What this establishes

- **The tool alone does nothing.** L0 is 0/18 across fifteen sessions, and all fifteen stores are
  empty files-on-disk, not merely unparsed. An agent that can see `memory_session_append` and is
  told nothing about it does not use it. This is the strongest and least equivocal number here.
  Verified rather than assumed: a probe under the identical scored-run configuration confirmed the
  L0 session saw all 18 `memory-seed` tools and that `memory_topics_list` resolved to the fixture's
  own vocabulary — so "had the tool and did not use it" is not silently "had no tool". Read with
  one qualifier: in this harness MCP tools are *deferred*, so the agent sees tool **names** and must
  fetch a schema before calling one. L0 therefore measures "the tool's name is visible", a weaker
  stimulus than a tool whose description is in the prompt, and weaker than the pre-registration's
  limitation 2 assumed.
- **Against the pre-registered threshold (≥0.8 capture, ≤0.3 noise), only L3 is reliable.** The
  pre-registration defined that outcome in advance as the **mechanical-cheapness claim failing**:
  the honest claim becomes "the shipped control plane makes agents record", and E2's
  enforcement-is-not-cheapness criticism stands. The kill condition (L3 < 0.5) was not triggered.
- **It corroborates E4 from the other direction.** E4 measured rule → mechanism inside this repo's
  own history and found compliance roughly doubling; E5 finds the same ordering under controlled
  conditions, with the rules contract alone (L2, 0.79) below the mechanism-bearing install
  (L3, 0.94).

### What it does not establish

- **The L2 verdict rests on one decision.** 15/19 = 0.789; one further capture makes it 0.84 and
  flips "fails" to "survives". A binary threshold decided by a single unit at n=19 is a coin near
  the line, not a finding. Treat "only L3 is reliable" as directional.
- **Faithfulness was not measured.** The judge called 124 recorded decisions faithful and none
  unfaithful. `claude -p --output-format json` emits the final message and usage but no tool-call
  or reasoning stream, so there was no record of actual reasoning for a stated reason to contradict.
  Zero variance across 128 judgements is a null instrument, not a perfect score. The same thinness
  independently limits the Codex arm. Re-run with `--output-format stream-json` before making any
  faithfulness claim.
- **Noise rate is likewise unvaried** (0 in every arm) and should not be quoted as a result.
- **The `guard_called` / `guard_blocked` columns in `summary.json` are unreliable for the same
  reason** — they match on transcript text, and the transcript holds only the final message. They
  read `false` almost everywhere regardless of what the session actually did, so "the worktree
  guard never fired" is *unmeasured*, not observed. The pre-registered confound it was meant to
  track therefore remains open.
- **Single stub project, three tasks, one model family as subject.** Generalises to these task
  classes and this agent, not to engineering work at large. The experimenter is also the subject
  population — the standing limitation from the pre-registration.
- **Two silent measurement bugs were found and fixed mid-run**, both of which produced clean,
  plausible, publishable-looking numbers. A counter that recognised only the DRAFT `### Decision`
  heading scored prose captures as silence, and manufactured an L2 dip that did not exist. Judge
  prompts passed as argv were truncated by the Windows `codex.CMD` shim, so 56 of 60 first-pass
  judgements answered a fragment — while the keyed second stage, obliged by its schema to emit one
  verdict per seeded key, confidently filled in all of them. Both were caught only by distrusting
  results that looked too clean. Treat this harness as failing silently *in the direction of
  success* until proven otherwise.

---

## E6 — Replication of E5, and what it overturns, 2026-08-04

**Source:** a second full 60-session matrix (`experiments/agent-capture/runs/`, v1 archived to
`runs-v1-json/`), identical fixtures, briefs, tasks and harness constants. The only change was the
transcript format — `--output-format stream-json` instead of `json` — which the agent never sees.
Run to measure faithfulness, which v1 could not. It also, unintentionally, became the more valuable
result: a like-for-like replication.

### The threshold verdict did not replicate

| Level | v1 capture | v2 capture | Pooled | 95% CI (Wilson) |
|---|---|---|---|---|
| L0 | 0/18 · 0.00 | 2/20 · 0.10 | **2/38 · 0.05** | [0.01, 0.17] |
| L1 | 14/19 · 0.74 | 13/16 · 0.81 | **27/35 · 0.77** | [0.61, 0.88] |
| L2 | 15/19 · 0.79 | 15/17 · 0.88 | **30/36 · 0.83** | [0.68, 0.92] |
| L3 | 17/18 · 0.94 | 14/16 · 0.88 | **31/34 · 0.91** | [0.77, 0.97] |

v1 concluded *only L3 is reliable → the cheapness claim fails*. v2 concluded *L1, L2 and L3 are all
reliable → the cheapness claim survives*. Same instrument, opposite verdicts, and **every arm's
interval straddles the 0.80 threshold — including L3**. The pre-registered binary question is not
answerable at this sample size; the two runs disagreed because the point estimates sit on top of the
threshold, not because anything changed.

Distinguishing 0.83 from 0.80 with confidence needs hundreds of seeded decisions per arm — an order
of magnitude more spend than the ~$200 both matrices cost together. **That is not planned.** The
threshold was the wrong instrument for a question at this cost.

### What both runs agree on, and what it means

- **The write path alone is not used.** Pooled L0 = 0.05, and its interval [0.01, 0.17] does not come
  near any other arm's. This is the one conclusion with real separation, and it survived a
  replication that overturned everything else.
- **One line in `AGENTS.md` naming the store gets most of the available capture** (L0 0.05 → L1
  0.77), and capture continues to climb with scaffolding: pooled L1 0.77 → L2 0.83 → L3 0.91.
  A Cochran-Armitage trend test across the full ladder is overwhelming (p ≈ 7e-14), driven by L0.
  Across L1–L3 alone it gives **z = 1.58, p ≈ 0.11** — suggestive of a real further climb, not
  established, and the ordering did not itself replicate (v2 placed L2 at 0.882 fractionally above
  L3 at 0.875, so the pooled monotonicity leans on v1). Direct L3 vs L1 is one-sided Fisher
  p ≈ 0.10. Read it as: the entry price is one line; whether the rest of the control plane buys the
  further ~14 points is directionally supported and worth resolving, but not shown here.
  **Unlike the threshold verdict, this question is resolvable by more data** — it is a trend rather
  than a knife-edge against a fixed line.
- **L0's zero was a small-sample artefact.** One of thirty L0 sessions recorded unprompted — and did
  so in full `### Decision` / `D:` / `R:` form despite L0 carrying no rules file, apparently
  inferring the shape from the tool schema. State L0 as ~3–5%, never as "never".

### Faithfulness — measured for the first time, and it holds

With reasoning in the transcript, the judge could finally check stated reasons against what actually
happened. Across 121 recorded decisions: **104 judged faithful, 17 unclear, 0 judged unfaithful.**
The 17 "unclear" verdicts matter — they show the judge discriminating rather than rubber-stamping,
which is precisely what the v1 faithfulness numbers could not demonstrate. No recorded rationale was
found to be a post-hoc reconstruction.

This is the strongest positive result in the programme so far: when an agent records a reason, the
reason appears to be the real one. It speaks directly to the product's core promise, and it is the
claim E5 had to retract as unmeasured.

### The worktree-guard confound, now measured and closed

`guard_called` was true in **0 of 60** sessions with a reliable event stream. Agents do not consult
`memory_worktree_guard` during ordinary task work, so the confound registered before the first
scored run — that a guard block might suppress capture at L2/L3 — **did not materialise** and can be
retired rather than left open.

### Session length: why the L1–L3 comparison was flat (added after JNL's field observation)

JNL, from building the product: hooks clearly help on long-context tasks. The fixtures could not
have seen that — the three tasks finish in 12–27 turns, and a `SessionStart` orientation or `Stop`
session-log check has almost nothing to do in a session that short. Splitting the 120 judged runs at
the median session length (22 turns):

| Session length | L1 | L3 | L3 − L1 |
|---|---|---|---|
| short (≤22 turns) | 1.00 | 0.80 | **−0.20** |
| long (>22 turns) | 0.62 | 0.96 | **+0.34** |

**L1 capture collapses as sessions lengthen (1.00 → 0.62); L3 holds (0.80 → 0.96).** Averaging two
gaps of opposite sign is what produced the flat, non-significant pooled L1→L3 result. The pooled
comparison was masking an interaction, not measuring its absence — which is the more likely
explanation for the flat band than "hooks don't help".

**This analysis is compromised and must not be quoted as a result.** Session length is an *outcome*,
not a randomised condition, and scaffolding itself lengthens sessions (mean turns: L0 16.6, L1 22.6,
L2 23.8, L3 28.1). Splitting on realised length conditions on a consequence of the treatment, so the
"long" L1 and L3 groups are not comparable populations. It is a post-hoc subgroup analysis on a
post-treatment variable — the weakest form of quantitative evidence, and the classic way false
findings are generated. Its value is that it agrees with an independent field observation and has a
plausible mechanism, not that it demonstrates anything.

**It does sharpen the open question**, from "is the L1→L3 climb real?" to "**does the hook benefit
appear only under context pressure?**" — which is properly testable with long multi-decision tasks
where length is fixed by design rather than measured after the fact, scoring capture of decisions
made *early* in a long session. That is the experiment worth pricing.

### What it does not establish

- Nothing about the ordering *within* L1–L3 from the pooled comparison alone. Those arms are
  statistically indistinguishable in aggregate, for reasons the session-length split above suggests
  are an artefact of task design rather than an absence of effect.
- Faithfulness is measured on the Claude arm only, and "0 unfaithful" is bounded by the judge's
  willingness to call one — it used "unclear" rather than "no" throughout, so read it as "no
  detected fabrication", not "fabrication is impossible".
- Still a single stub project, three tasks, one subject model family, experimenter as subject.

---

- **Post as a practitioner with a real question.** Never pitch. If the pain is not described unprompted, that
  is the finding.
- **Ask about past behaviour and specific incidents**, never opinions or hypotheticals. Perceived and measured
  productivity diverge by a characterised margin (Report 4).
- **Record engagement metrics honestly**, including unflattering ones. Zero upvotes on 2.8K views is data.
- **Effort already spent is the strongest signal** short of payment. Someone who built a workaround outranks
  ten who agree it sounds useful.
