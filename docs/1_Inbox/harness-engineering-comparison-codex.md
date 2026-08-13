# Harness engineering (OpenAI) vs. Memory Seed — Codex line

Status: Evaluated comparative analysis (2026-08-13). The candidate list has been checked against
current repository capabilities, but no candidate is accepted work. The document remains in Inbox
pending a lifecycle decision.

**Authorship.** This is the **Codex-revised** line of the comparison, retained for side-by-side reading.
Claude drafted the original (`mse_j3ermf8frke6j6rn`); a Codex review then corrected the chronology and
provenance claims and added §4d (`mse_h0mp9jj6yfzaf7wk`). It is therefore joint work whose most recent
editorial judgment is Codex's, not a document Codex wrote from scratch. This revision also evaluates
the parallel [Claude line](harness-engineering-comparison-claude.md), accepting, qualifying, or
rejecting its departures in §7 rather than silently blending them. Neither line supersedes the other.

Source: Ryan Lopopolo, *Harness engineering: leveraging Codex in an agent-first world*, OpenAI,
2026-02-11 — <https://openai.com/index/harness-engineering/>. Compared against this repository at
control plane 2.20 and [Constitution](../CONSTITUTION.md) v1.8. All characterisations of the article
are paraphrase.

---

## 1. What the article reports

A team at OpenAI built an internal product over five months with **zero manually-written lines of
code** — every line (application logic, tests, CI, documentation, observability, internal tooling)
authored by Codex. Reported figures: first commit late August 2025; roughly one million lines of code;
about 1,500 pull requests; three engineers initially, seven now; ~3.5 PRs per engineer per day, with
throughput *rising* as the team grew; about a tenth of the time hand-writing would have taken.

Those magnitudes are self-reported in a vendor article about its own product. The article supplies no
repository, counting definition, counterfactual method, or independent verification for the
million-line and one-tenth-time estimates. The practices below are concrete enough to compare; the
magnitudes are context, not evaluation evidence.

Their thesis: when engineers stop writing code, the engineering work becomes **designing the
environment the agent works inside** — the harness. Their named practices:

| # | Practice | Substance |
|---|---|---|
| 1 | Engineer as environment-designer | When the agent fails, ask which capability is missing rather than retrying harder. Humans never patch code by hand; they fix the harness, and have the agent write that fix too. |
| 2 | Application legibility | App bootable per git worktree; Chrome DevTools Protocol wired into the agent runtime; per-worktree ephemeral observability stack; agents query logs with LogQL and metrics with PromQL. Prompts asserting a latency budget on named user journeys become tractable. |
| 3 | Repository as system of record | A short (~100-line) `AGENTS.md` acting as a **table of contents** into a structured `docs/` tree: design docs with an index and a core-beliefs file, exec plans (active / completed / tech-debt), generated schema, product specs, references, plus top-level `DESIGN`, `FRONTEND`, `PLANS`, `PRODUCT_SENSE`, `QUALITY_SCORE`, `RELIABILITY`, and `SECURITY` documents. |
| 4 | Agent legibility as the goal | If the agent cannot reach it in-context, it does not exist. Chat threads and external docs are illegible; repo-local versioned artifacts are all the system sees. Bias toward "boring", in-repo-modelable dependencies; sometimes reimplement a small library subset rather than tolerate opaque upstream behaviour. |
| 5 | Enforced architecture and taste | Fixed per-domain layering (Types → Config → Repo → Service → Runtime → UI), forward-only dependency edges, cross-cutting concerns admitted only through a single Providers interface. Enforced by Codex-written custom linters and structural tests. Lint error messages carry remediation instructions written *for agent context*. Enforce invariants; do not prescribe implementations. |
| 6 | Inverted merge philosophy | Minimal blocking merge gates, short-lived PRs, flakes handled by re-running rather than blocking. Corrections are cheap; waiting is expensive. Explicitly framed as irresponsible at low throughput. |
| 7 | Agent-to-agent review | Codex reviews its own change locally, requests further agent reviews locally and in the cloud, and iterates until reviewers are satisfied. Human review is optional; agents often squash-merge their own PRs. |
| 8 | Escalating autonomy | From a single prompt: validate repository state, reproduce a bug, record a video of the failure, implement a fix, drive the application to validate it, record a second video, open the PR, answer feedback, remediate build failures, escalate only on judgment calls, merge. |
| 9 | Entropy and garbage collection | Agents replicate existing patterns including poor ones. Spending Fridays cleaning up did not scale. Replaced by written-down "golden principles" plus recurring background Codex tasks that scan for deviations, update quality grades, and open small auto-mergeable refactor PRs — debt paid down continuously. |
| 10 | Doc-gardening | A recurring agent scans for documentation that no longer reflects real code behaviour and opens fix-up PRs; linters and CI validate that the knowledge base is current, cross-linked, and structurally correct. |

Their stated open questions: how architectural coherence holds over *years* in a fully
agent-generated system; where human judgment adds the most leverage and how to encode it so it
compounds; how the picture shifts as models improve. They also caution that the autonomy in row 8
depends on their specific repository investment and should not be assumed to generalise.

---

## 2. The framing that makes the comparison legible

These are not the same kind of artifact, and grading one against the other as a scorecard produces
nonsense. Two separate axes:

- **Axis A — Memory Seed as a harness.** This repository is itself agent-driven and has a harness:
  `AGENTS.md` routing, lazy skills, hooks, worktree=session / branch=task, `doctor`, `links check`,
  `docs check`, ESR. Here the article is directly comparable, practice for practice.
- **Axis B — Memory Seed as a product.** OpenAI *hand-rolled*, for one repository, the thing Memory
  Seed productises for any repository: a thin routing entry point over a structured,
  mechanically-validated, repo-local knowledge base that agents read instead of reading humans' heads.

**The strongest finding is on Axis B: credible corroboration of the problem, not market validation.**
The article predates this repository by three months, so Memory Seed has no priority claim and the
corpus cannot establish whether its design was influenced by the article or the surrounding discourse.
What survives is observable convergence: a well-resourced team judged a short router, structured
repository-local knowledge, checked-in plans and decision logs, and mechanical freshness enforcement
worth building for its own use.

That is evidence that the problem is salient and expensive enough to attract engineering investment. It
is not evidence of product demand, willingness to adopt Memory Seed, or independent invention. It is
also a competitive signal: capable teams can hand-roll the current-state portion with ordinary files,
linters, and agents. Memory Seed's defensible differentiation is therefore narrower — portable
brownfield adoption plus typed, retrievable, provenance-preserving rationale — and still needs external
user evidence.

---

## 3. Convergence

| Their practice | Memory Seed equivalent |
|---|---|
| `AGENTS.md` as table of contents, not encyclopedia | [`AGENTS.md`](../../AGENTS.md) is a thin router into `.memory-seed/`; `skills/index.md` is a deterministic trigger registry; `index.md` is tree-first. Same anti-monolith argument, implemented here after the article's February 2026 publication. |
| Progressive disclosure from a small stable entry point | "Do not read skills preemptively. Skills are lazy-loaded execution runbooks." Plus the measured whole-session context route (direct read at or below 12,000 characters, economy-worker compression above). |
| Context is scarce; too much guidance becomes non-guidance | Constitution §3 *minimal but sufficient context* — the smallest context that preserves the ability to decide. Still `[candidate]`, but written down. |
| Structured `docs/` tree as system of record | The `docs/` lifecycle taxonomy, where the folder a document lives in *is* its lifecycle state. Theirs has active/completed too, but only for exec plans. |
| Exec plans as first-class checked-in artifacts with decision logs | DRAFT session entries (D/R/A/F/T), living ADRs under `.memory-seed/decisions/`, plans under `docs/2_Todo/`. Finer-grained here: decision identity is `(entry_id, dN)`. |
| Core-beliefs file defining agent-first operating principles | [`docs/CONSTITUTION.md`](../CONSTITUTION.md) — seven invariants, principles, policies, four-layer model, five-question test, amendment log with a named ratifier. Substantially more formal. |
| Golden principles enforced continuously, not in cleanup bursts | `agent-rules.md` + `policy.md` + the skills registry, plus ESR at end of turn. Same capture-taste-once, enforce-continuously logic. |
| Doc-gardening agent and knowledge-base linters | `links check`, `topics check`, `encoding check`, `docs check`, `docs index --check`, `doctor` (orphan-skill and orphaned-runtime warnings), the ESR orphan/artifact sweep. |
| Lint messages that inject remediation into agent context | Same instinct: `session merge-branch` refusals name the missing capability and the fix command; the topic-family fuse gap reports as an actionable refusal rather than a bare failure. |
| Enforce invariants centrally, allow autonomy locally | The Constitution's layer model — invariants constrain; implementations are freely replaceable and owe no allegiance. |
| Forward-only, mechanically-validated dependency edges | Forward-only, acyclic lifecycle edges across four never-merged edge kinds, validated by `links check`. The same shape of constraint, applied to memory rather than code. |
| Agent-legible over human-stylistic | `vendor_neutral: true`, Invariant #5 model-independence, plain Markdown throughout. |
| Repo-local versioned artifacts are all the agent can see | Invariants #1 (plain files, no server, database, or network in the core) and #6 (Markdown authoritative; everything else a rebuildable projection). The strongest convergence in the comparison — their "if it isn't in the repo it doesn't exist" is this project's invariant, reached from the opposite direction. |
| Isolated per-task worktree | worktree=session, branch=task, `<agent>/<kind>/<topic>` namespacing, with a `doctor`/ESR sweep for deregistered worktree residue. |

---

## 4. Divergence

### 4a. Current-state knowledge base vs. separated now/why — the real fork

Their knowledge base is a **current-state** artifact. The doc-gardening agent finds documentation that
no longer reflects real code behaviour and opens PRs to fix it; stale content is corrected or removed.
That is coherent for their goal — the agent reads the repository and must not be misled. The article
does not describe whether a corrected document's prior rationale remains queryable, so it cannot
support the stronger claim that their reasoning is necessarily lost.

Memory Seed splits the axis instead. Invariant #4: files are the authority for what is true *now*,
memory is the authority for *why*. Invariant #2: append-only, corrections are new entries pointing
back. Invariant #7: retrieval down-ranks a superseded entry, never removes it.

Their critique of a monolithic instruction file is that it becomes what Lopopolo calls "a graveyard of
stale rules." Their remedy is current-state gardening. Memory Seed's alternative is to mark the graves:
supersede, down-rank, and keep the old rationale readable so an agent can ask what was tried and why it
was dropped.

OpenAI also keeps checked-in execution plans with progress and decision logs, a completed-plan lane,
and documentation/design history. That is a real *why* store, not an absence. The defensible divergence
is that the article does not describe Memory Seed's typed decision identity, append-only correction,
lifecycle graph, authority hierarchy, or retrieval semantics. Whether the lighter mechanism is
insufficient is a multi-year prediction, not a failure demonstrated by the five-month report.

### 4b. Merge philosophy is inverted, and both are correct

| Theirs | Here |
|---|---|
| Minimal blocking merge gates | Fails closed nearly everywhere |
| Flakes re-run rather than block | `session merge-branch` aborts the whole merge on a fuse issue and auto-runs `git merge --abort` |
| Agents squash-merge their own PRs | Write-surface parity (Invariant #2, v1.3): every surface passes identical guards — chronology, ref existence, forward-only edges, topic vocabulary, id collision, DRAFT body |
| Human review optional | Mandatory ADR review for lineage-linked evolution; human approval gates every machine-suggested lifecycle edge |
| Corrections are cheap, waiting is expensive | Machine edges never move heads without an authored chain or a named approval |

Both are internally consistent because the cost of a bad write differs by an order of magnitude. A bad
merge in a product repository is a revert. A bad write into an append-only evidence corpus cannot be
reverted by design — the only correction is another append, and the wrong claim stays legible forever.
Their throughput argument does not transfer to this substrate.

Where it *does* transfer: to the ordinary code and documentation in this repository, which are not the
corpus. Their posture — auto-mergeable, sub-minute-reviewable, continuously-opened cleanup PRs — is the
right treatment for the drift class this repository currently carries rather than pays down.

### 4c. Application legibility exists here, but not as an integrated runtime harness

OpenAI's implementation combines capabilities this project does not yet combine:

- the application bootable **per worktree**, so an agent drives its own isolated instance
- Chrome DevTools Protocol in the agent runtime, with skills for DOM snapshots, screenshots, navigation
- an ephemeral per-worktree observability stack, torn down with the task
- agents querying logs and metrics directly, making budget assertions on startup time or span latency
  checkable from a prompt
- video recorded before and after a fix, attached as evidence

Memory Trace is not human-only. The repository already has a rendered-UI debugging skill requiring a
real browser or browser automation, `memory-trace --static-root` for worktree frontend verification,
and browser fixtures, screenshots, and rendered checks. What it lacks is an isolated, per-worktree
*whole application* plus agent-queryable logs, metrics, traces, and prompt-checkable runtime budgets.
That integrated feedback loop is the transferable gap.

The stale-global-CLI and phantom-worktree incidents are a separate **environment provenance** class.
DevTools, LogQL, and PromQL would not prove which checkout or executable was loaded; Memory Seed's
package-provenance refusal and worktree guard address that class. Runtime observability and tooling
provenance should not be presented as one missing capability.

The earlier quality-metrics bridge was also stale. `memory-seed quality report --json` already provides
an agent-queryable projection: unlinked-entry rate and DRAFT reason coverage are measured, while
generated-claim citation coverage, provenance coverage, and ranking regression report explicit
`unavailable` or `not_applicable` states. The remaining question is whether the existing report is useful
enough to set targets or extend — a decision already owned by
[`memory-quality-metrics-v0-proposal.md`](../2_Todo/memory-quality-metrics-v0-proposal.md), not a new
harness-engineering candidate.

### 4d. Progressive disclosure is designed in, but its fixed routing cost remains heavy

Memory Seed follows the article's map-not-manual structure, but an agent does not stop at the 76-line
router. The measurement has two useful boundaries:

| Boundary | Files | Lines | Characters |
|---|---|---:|---:|
| Unconditional orientation before intent-specific routing | `AGENTS.md`, `agent-rules.md`, `skills/orientation.md` | 452 | **30,443** |
| Mandatory by the first substantive turn, once intent is known | + complete `skills/index.md` | 776 | **45,544** |

Claude is right that calling all 45,544 characters "before task-specific context" was imprecise: the
registry is loaded only once intent is known. But it is still a fixed cost of every substantive session,
not selectively retrieved task guidance. The 12,000-character threshold controls only the latest-session
portion and does not reduce either routing stack.

This is not the monolithic-`AGENTS.md` failure: ownership is separated, skills remain lazy-loaded, and
the route is mechanically explicit. The question is whether a compiled packet can preserve every safety
decision while carrying only measured checkout facts, a compact authority map, and matching registry
entries. That is an evaluation extension of the existing context-derivation work, not permission to
replace source reads on intuition.

### 4e. Smaller divergences

- **They generated the harness from an empty repository; Memory Seed's is designed then seeded.** Their
  `AGENTS.md` was itself written by Codex. This project's is a versioned seed file with a four-way
  ownership branch and archive-before-replace. Different problem: they harness one repository, this
  ships a harness into arbitrary ones, including repositories with a pre-existing foreign `AGENTS.md`.
- **Reimplement over depend.** They favour reimplementing small library subsets so the agent can model
  the whole thing in-repo. This project lands in the same place from a different constraint —
  `model2vec>=0.8.1` is the package's only required dependency and plain `memory-seed` ships no web framework
  — driven by local-first invariants rather than agent legibility.
- **Scale.** Seven engineers and a large agent-generated codebase against a solo maintainer. Their central claim
  — human attention is the one scarce resource — applies *harder* solo, not less. That is a fair
  argument that some gates here are tighter than the staffing warrants, and the honest counterweight to
  §4b.
- **Agent-to-agent review loops.** They push nearly all review agent-to-agent and iterate until
  reviewers are satisfied. This repository has swarms (link, topic) and subagent fan-out, but those are
  *judgment* layers over mechanical sweeps, always human-gated. The reviewed-until-clean loop as a
  standing integration workflow is not present.

---

## 5. Candidate disposition after repository and Claude-line review

Still not accepted work. This table distinguishes new opportunities from existing owners.

| Candidate | Disposition |
|---|---|
| Quality instrumentation / graded quality map | **Already owned and partly shipped.** Extend `memory-seed quality report` only after the existing proposal's user usefulness review. Do not create a parallel metric family or composite grade. |
| Recurring background cleanup | **Potential operating practice, not yet a product plan.** Limit it to named non-corpus target classes, dry-run first, and never auto-edit session entries or sidecars. |
| Per-worktree Memory Trace observability | **Genuine bounded gap.** Evaluate a whole-app worktree launch plus queryable logs/metrics and rendered evidence. Keep tooling provenance under its existing guards. |
| Agent-oriented refusal messages | **Audit before proposing work.** The convention is already partly implemented; first measure which mechanical refusals still lack cause, ownership, or an exact recovery command. |
| Compiled minimal startup packet | **Existing evaluation extension.** Test the 30,443/45,544-character boundaries through the context-derivation work and require safety-equivalent task outcomes before replacing reads. |

Explicitly **not** a candidate: minimal merge gates and self-merging agents for anything touching the
memory corpus. That is the one place where the throughput logic inverts, and the guards there are
load-bearing rather than pedantic.

---

## 6. Verdict

Different artifacts, same scaffolding thesis. OpenAI's report credibly corroborates the problem and the
value of a repo-local harness, but it does not establish independent convergence, market demand, or the
reported productivity magnitudes. It simultaneously demonstrates a build-vs-buy threat: the
current-state knowledge layer is hand-rollable by a capable team.

Memory Seed's stronger claim is narrower: portable brownfield installation plus typed, retrievable,
append-only rationale and provenance. Its genuine deficits are a heavy fixed routing cost and the lack
of OpenAI's integrated per-worktree application-observability loop. Its quality instrumentation and
browser-verification capability are partial rather than absent. The most useful exchange is therefore
not "copy their harness"; it is to measure those two remaining gaps without duplicating shipped work.

---

## 7. Gap analysis against the Claude line

| Claude-line contribution | Codex evaluation |
|---|---|
| Discount the self-reported scale and speed figures | **Accepted.** The practices are evidence; the magnitudes are unsupported context. |
| Reopen chronology and influence | **Mostly agreed, but it misstates the prior Codex position.** The Codex line already said article silence cannot prove independence. Both lines now agree that priority is unavailable and influence is unknown. |
| Reframe the article as evidence of demand | **Qualified.** It is evidence of problem salience and internal willingness to build, not external adoption or willingness to pay for Memory Seed. |
| Add the competitive/build-vs-buy reading | **Accepted.** This is Claude's strongest new strategic contribution and narrows the differentiation claim usefully. |
| Weaken the now/why claim | **Accepted.** OpenAI has decision logs and design history; the difference is formal retrieval and preservation, not presence versus absence. |
| Separate stale-CLI provenance from runtime observability | **Accepted.** These are different failure classes with different controls. |
| Say runtime legibility is wholly absent | **Rejected.** Browser automation, rendered verification, screenshots, fixtures, and worktree static serving exist. The integrated full-app telemetry loop is absent. |
| Replace 45,544 with 30,443 characters | **Qualified.** 30,443 is unconditional before intent-specific routing; 45,544 is still mandatory by the first substantive turn. Both boundaries matter. |
| Retain the claim that quality metrics are untracked | **Rejected; missed by both earlier lines.** A queryable v0 quality report already ships, with two measured and three explicitly unmeasured metrics. |
