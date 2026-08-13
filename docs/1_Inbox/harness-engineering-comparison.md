# Harness engineering (OpenAI) vs. Memory Seed

Status: Unassessed external capture (2026-08-13). No decision is implied by its presence here; the
"What is worth taking" section is a candidate list, not an accepted plan.

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

**The strongest finding is on Axis B: external corroboration.** A seven-person team optimising for
shipping velocity describes the same cluster of needs that Memory Seed addresses — a short router,
structured repository-local knowledge, progressive disclosure, checked-in plans and decision logs, and
mechanical freshness enforcement. The article does not mention Memory Seed, but that is not evidence
that the work was independent; the defensible conclusion is convergence, not provenance. It remains
strong validation of the product premise from a credible source and is worth more to this project than
any individual technique in the post.

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
That is coherent for their goal — the agent reads the repository and must not be misled — and it is
also the standard failure mode Memory Seed exists to prevent. Once the stale document is overwritten,
the *reasoning that produced it* is gone, and the next agent re-litigates a decision that was already
made and rejected.

Memory Seed splits the axis instead. Invariant #4: files are the authority for what is true *now*,
memory is the authority for *why*. Invariant #2: append-only, corrections are new entries pointing
back. Invariant #7: retrieval down-ranks a superseded entry, never removes it.

Note that the article makes the argument *for* this position and then does not follow it through.
Their critique of the monolithic instruction file is precisely that it becomes a graveyard of stale
rules an agent cannot distinguish from live ones. Their remedy is a gardener that clears the graves.
The alternative remedy is to mark them — supersede, down-rank, keep readable — which is what lets an
agent answer "was this tried before, and why was it dropped?" On a five-month-old repository the
gardener is cheap and correct. Their own open question is what happens over *years*, and that is the
regime where the distinction begins to bite.

What they do have that partly closes the gap: exec plans carrying decision logs, checked in, with a
completed lane. That is a partial *why* store. It is not indexed, typed, graph-linked, or retrievable
the way session entries plus ADRs plus lifecycle edges are — but it is not nothing, and it suggests
they met the same need and solved it lightly.

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

### 4c. Application legibility is genuinely absent here

This is the part of their harness with no counterpart in this project:

- the application bootable **per worktree**, so an agent drives its own isolated instance
- Chrome DevTools Protocol in the agent runtime, with skills for DOM snapshots, screenshots, navigation
- an ephemeral per-worktree observability stack, torn down with the task
- agents querying logs and metrics directly, making budget assertions on startup time or span latency
  checkable from a prompt
- video recorded before and after a fix, attached as evidence

Memory Trace is a *human* review surface, not an agent-legible one, and this repository's known failure
modes are the ones instrumentation catches: the worktree preview serving worktree static over the
primary backend, the stale-CLI-binary trap in worktrees, phantom worktree working directories. All of
those are "the agent cannot see the running system" bugs.

This also bridges to Constitution §8 (memory quality) and §7 (trust model), both still `[candidate]`.
Named metrics — stale-rate, orphan-rate, evidence/decision coverage — are defined but untracked, and
the Constitution itself describes `links check` / `topics check` / `doctor` / `esr` as *partial
instrumentation*. Their model, make the metric queryable by the agent and then write prompts that
assert on it, is the missing mechanism for graduating §8 from candidate to cited.

### 4d. Progressive disclosure is designed in, but the mandatory baseline is still heavy

Memory Seed follows the article's map-not-manual structure, but an agent does not stop at the
76-line router. Before task-specific context, normal startup requires `AGENTS.md`, `agent-rules.md`,
`orientation.md`, and the complete skill trigger registry. In this checkout those four files total
**776 lines and 45,544 characters**, before the latest session file, policy, project index, applicable
skills, or source code. The 12,000-character session threshold controls only the latest-session portion.

This is not the same failure as one monolithic `AGENTS.md`: ownership is separated, skills still
lazy-load, and the route is mechanically explicit. But the token bill is paid anyway when every startup
must read the entire operating contract and registry. The article's stronger form of progressive
disclosure is therefore only partly realised here. A mechanically compiled startup packet — measured
checkout facts, a compact authority map, and only the matching skill entries — would preserve the
guards while moving more of the control plane behind demand-driven retrieval.

### 4e. Smaller divergences

- **They generated the harness from an empty repository; Memory Seed's is designed then seeded.** Their
  `AGENTS.md` was itself written by Codex. This project's is a versioned seed file with a four-way
  ownership branch and archive-before-replace. Different problem: they harness one repository, this
  ships a harness into arbitrary ones, including repositories with a pre-existing foreign `AGENTS.md`.
- **Reimplement over depend.** They favour reimplementing small library subsets so the agent can model
  the whole thing in-repo. This project lands in the same place from a different constraint —
  `model2vec` is the package's only required dependency and plain `memory-seed` ships no web framework
  — driven by local-first invariants rather than agent legibility.
- **Scale.** Seven engineers and a million lines of code against a solo maintainer. Their central claim
  — human attention is the one scarce resource — applies *harder* solo, not less. That is a fair
  argument that some gates here are tighter than the staffing warrants, and the honest counterweight to
  §4b.
- **Agent-to-agent review loops.** They push nearly all review agent-to-agent and iterate until
  reviewers are satisfied. This repository has swarms (link, topic) and subagent fan-out, but those are
  *judgment* layers over mechanical sweeps, always human-gated. The reviewed-until-clean loop as a
  standing integration workflow is not present.

---

## 5. Candidates worth considering

Not accepted work. Each is stated with the constitutional check applied.

1. **Agent-legible instrumentation for Memory Seed's own quality metrics.** Make stale-rate,
   orphan-rate, and evidence/decision coverage queryable, then assert over them the way they assert
   latency budgets. Graduates §8 from `[candidate]`. Answers the five-question test on Validation and
   Trust. A metrics surface is a derived projection under Invariant #6, so nothing objects.
2. **Recurring background cleanup with sub-minute reviewable changes.** Their garbage-collection model
   applied to the *non-corpus* parts of this repository: documentation index drift, broken doc links,
   the known encoding issues. Explicitly **not** applied to session entries or sidecars, where
   Invariant #2 governs and human gating is the settled answer.
3. **Per-worktree bootable application and ephemeral observability for Memory Trace.** Directly
   addresses the worktree preview/backend split and stale-CLI-binary traps, both of which have already
   produced wrong conclusions in this project.
4. **A graded quality map.** They grade each product domain and architectural layer and track gaps over
   time. The Constitution names this in §8 but nothing computes it. Cheap, and it makes drift visible
   before it compounds.
5. **Lint and refusal messages written for agent context as a stated convention.** Partially present in
   the `merge-branch` refusals; worth making a rule rather than a habit — every mechanical refusal names
   the missing capability and the exact command that resolves it.
6. **A compiled minimal startup packet.** Measure whether agents can receive the enforced checkout and
   integration facts, a compact authority map, and only task-matching skill routes without reading the
   current 45,544-character mandatory routing stack. Treat this as an evaluation first: the packet must
   preserve safety decisions and improve task success or context cost before replacing source reads.

Explicitly **not** a candidate: minimal merge gates and self-merging agents for anything touching the
memory corpus. That is the one place where the throughput logic inverts, and the guards there are
load-bearing rather than pedantic.

---

## 6. Verdict

Different artifacts, same thesis: the engineering work has moved out of the code and into the
scaffolding around it. OpenAI hand-built, for one repository under severe velocity pressure, much of
the repository-knowledge environment that Memory Seed generalises — strong external corroboration of
the premise, without proving independent invention. Memory Seed goes considerably further on
*why*-preservation, provenance, and append-only integrity, but its mandatory startup context is heavier
than its progressive-disclosure ideal and it has essentially nothing in the runtime-legibility class
that OpenAI built out. Those are the three main directions of exchange.
