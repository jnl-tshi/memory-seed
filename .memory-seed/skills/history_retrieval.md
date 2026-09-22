---
memory-system-version: 2.22
governing_adr: adr_semantic_provider
tags:
  - memory-seed
  - skill
  - history-retrieval
---

# History Retrieval And Conflict Resolution Skill

Use this skill when prior decisions, reason, unresolved risks, architecture, policy, bootstrap behavior, release history, or "why was this done" matters.

## Recency vs. Topical Retrieval

Pick the retrieval method by question type. They are not interchangeable.

- Current state / "what is the latest": use the SessionStart/`situate` route for the newest applicable
  session file — direct whole-file reading at or below 12,000 characters, or the source-linked economy-
  worker briefing above it. Do not use `memory_search` for latest-state questions because semantic and
  lexical ranking optimize for topical similarity, not recency; reopen exact entries when their reasoning
  will support a consequential decision.
- Topical / "why was X decided" / "what do we know about Y": use `memory_search`, then fetch consequential results with `memory_get_chunk`.

## When To Search

**Retrieve proactively before a consequential review, recommendation, design, or change decision on non-obvious behavior — do not wait for a question to force it.** This includes conclusions that something is redundant, obsolete, removable, replaceable, or ready to consolidate. Ask "has this been decided, retained, or tried before?", search for the why, and fetch the relevant full entry before concluding, so you inherit rejected alternatives, constraints, deferred items, and landmines instead of re-deriving a settled decision or re-tripping a documented one.

Call `memory_search` before relying on the visible conversation alone when the task asks about or depends on:

- a past design decision, architecture choice, policy change, bootstrap choice, release, migration, or unresolved risk
- why a file, workflow, or memory structure behaves a certain way
- whether a current request conflicts with older session history
- sub-project boundaries, inherited policy, or prior agent handoff context

Skip MCP history lookup for small, obvious edits where current source files and the active `index.md` / `policy.md` are enough.

**Carry the retrieval forward.** The entries you fetch to ground a change are not just context for the work — they are the highest-signal lifecycle-link candidates for the entry you are about to write. Keep the ids you actually consulted and hand them to `memory_link_suggest`'s `consulted` axis at authoring time (see Authoring-Support Tools), so link candidacy is based on **both** the current repo (shared files) and memory (what you consulted) — the same two-source discipline you apply to the work itself.

### Why vs. Current State — Division Of Labor

Files are the authority for what is true *now* (current source, `index.md`, `policy.md`); memory is the authority for *why* (the reasoning, tradeoffs, and rejected paths behind that state). Read files for current state; retrieve memory for the reasoning — never substitute one for the other. A file tells you what the code does now, not which alternatives were rejected or which constraint a terse guard protects; that reasoning lives only in session memory.

## Retrieval Tool Mechanics

Use the retrieval tools on the MCP server for history lookup:

- `memory_search`: ranks session-memory entries or sections.
- `memory_get_chunk`: fetches the full text for one returned `chunk_id`.

Default search payload:

```json
{
  "query": "short natural-language description of what you need to know",
  "cwd": ".",
  "top_k": 5,
  "granularity": "entry"
}
```

Use `cwd` as the project or sub-project path you are operating in. The runtime resolver uses the nearest `.memory-seed/` directory from that path.

Use `granularity: "entry"` by default. It returns one coherent chunk for each `##` session entry, and `chunk_id` is normally the entry YAML `entry_id`, such as `mse_0123456789abcdef` (legacy `ms-db2d715c`-style ids also occur in older history).

Use `granularity: "section"` only when entries are long, multi-topic, or the task needs narrower targeting. Section chunk ids append a heading path to the parent entry id, such as `mse_0123456789abcdef#decisions/d1-use-draft-for-compact-decision-records`.

Useful optional search fields:

```json
{
  "preferred_keywords": ["React", "framework", "frontend"],
  "semantic_enabled": true,
  "recency_enabled": true,
  "recency_floor": 0.15
}
```

For topical or "why was this chosen?" searches, derive 2-5 preferred keywords from the user's wording
and already-known domain context, and include them in the first `memory_search` call whenever that
produces meaningful discriminators. Prefer the named subject and its obvious domain terms; for example,
"Why was React chosen?" supports `React`, `framework`, and `frontend`. Intent terms such as `decision`,
`rationale`, and `alternatives` may clarify the natural-language query, but do not blindly expand the
preference list: a small focused set is stronger than a bag of generic words.

Do not guess unknown document types, artifact names, or hidden rationale merely to populate the field.
The React example does not require knowing that an architecture proposal exists: retrieve the React
decision first, then follow its `source_refs`. Omit `preferred_keywords` for exact identifiers or paths,
or when no useful discriminator is available. If the first results are poor, refine the preferences once
from evidence in those results instead of repeatedly appending terms.

`preferred_keywords` is a positive lexical nudge toward known terms. Values are Unicode-normalized and
case-folded, so capitalization cannot cause misses. The bonus is bounded and cannot make a zero-match
result relevant; inspect `matched_preferred_keywords` and `preference_bonus` in the result. This field is
optional and never excludes results.

Recency is anchored to the current date read from the system clock at call time. There is no date-override field; the tool never trusts a caller-supplied "today".

Search results include `chunk_id`, `entry_id`, `source`, structured DRAFTS `source_refs`, `line_range`, `heading_path`, `excerpt`, matched fields, score fields, entry metadata, and `granularity`. Keys that would be empty are omitted, except the lifecycle and attention fields, where empty is a claim rather than an absence.

`excerpt` is sized to answer one question - *is this the result I want?* A **decision** result carries its whole DRAFTS block. Anything else is a window around the terms that made it rank, with the entry's metadata block excluded because every field in it is already a key on the same result. A window that had to cut says so: a leading `...` where the head was elided, and `[preview - call memory_get_chunk for the full entry]` where the tail was. An excerpt carrying neither mark is the complete text.

Fetch any result that may affect implementation, policy, bootstrap behavior, release behavior, or memory structure:

```json
{
  "chunk_id": "ms-db2d715c",
  "cwd": "."
}
```

Use the fetched chunk text, not just the excerpt, when making or evaluating a consequential decision.

## Authoring-Support Tools

These MCP tools close the *authoring* loop — find what to link, then write the entry — the counterpart to the search/fetch retrieval loop above. Finding what to link stays read-only (`memory_link_suggest`, `memory_link_show`); authoring the entry now goes through `memory_session_append`, which **writes** it through the structural guards. Agents no longer hand-append their own session files.

- `memory_link_suggest`: rank older entries to link from a target entry (default: the newest entry, i.e. "the one I just wrote"). Returns a `target` summary, ranked `suggestions`, and a paste-ready `related_entries` list. Use it when filling an entry's `related_entries` instead of guessing or re-searching. Optional `entry_id` targets a specific entry; `top_k` bounds the candidates. Pass `consulted: [ids]` — the entries you fetched while grounding this work (above) — to add the **memory axis** of candidacy: those sort first (flagged `consulted`) and are the natural source for the `replaces`/`evolves` decision-lineage edges that shared-file evidence misses. Candidates only; you still classify.

```json
{
  "cwd": ".",
  "entry_id": "mse_...",
  "top_k": 5
}
```

- `memory_link_show`: show one entry's graph node — stored `outbound` edges, computed `inbound` backlinks, `replaces`/`replaced_by`, `importance_score`, and `commit_reference_count`. Use it to traverse the related-entry graph structurally instead of re-running a topical search.
- `memory_session_append`: append a session entry with every structural guard enforced — chronology, ref existence (fabricated ids refused), forward-only `replaces`/`evolves` edges, controlled topic vocabulary, id collision, DRAFTS body format, and the same content-bound ADR review preflight as CLI `session append`. This is the **only** sanctioned way to author an entry; do not hand-write session files. The server stamps the heading timestamp from its own clock — omit `timestamp` in normal use (an explicit far-off value earns a drift warning). Refusals come back as `{ok: false, written: false, issues: [...]}`, each independently fixable. Required: `title`, `body`, `user_initials`, `agent_type`; common options are `decisions`, `branch`, `consulted`, and `dry_run`. When a decision has no related or lifecycle link, every passing dry-run and real-write response carries `link_suggestions`; ids supplied in `consulted` sort first, but no edge is auto-written. A `dry_run` runs every guard and returns the `entry_id`, timestamp, target path, and `rendered` — the exact entry block a real call would append, so the final output is inspectable **before writing**. To commit to the previewed bytes, pass the previewed `timestamp` back on the real call: the id hashes the timestamp, so a fresh server stamp that ticks to the next minute mints a different id than the one inspected.

```json
{
  "cwd": ".",
  "title": "Switch cache key to content hash",
  "body": "### Decision\n\n- D: ...\n- R: ...",
  "user_initials": "JNL",
  "agent_type": "claude",
  "dry_run": true
}
```

## Fallback

If MCP tools are unavailable, read recent and relevant `.memory-seed/sessions/YYYY-MM/YYYY-MM-DD.md` and `.memory-seed/sessions/YYYY-MM/YYYY-MM-DD/<user>.md` files directly, with legacy flat/day paths still readable. Start with the last two session documents, then search older dated files by keyword if needed.

## The Relevance Band Is UNCALIBRATED - Do Not Treat It As Evidence

`memory_search` attaches `relevance` (strong/weak/none) and `no_match_above_threshold`. **Measured
2026-08-05 on the 836-entry corpus, these do not discriminate**: pure-nonsense queries ("recipe for
sourdough starter hydration", "premier league transfer window rules") return eight results banded
`strong`, and `no_match_above_threshold` fired for **zero** of twelve queries - real and nonsense
alike. Neither the absolute score nor the top-versus-pack gap separated them, with semantic ranking
on or off. The thresholds were set against a 7-entry fixture where everything banded `strong` and
the answer happened to be present, which hid the saturation.

Until they are recalibrated with evidence:

- **A `strong` band is not a claim that the result answers your question.** Read the served DRAFT
  block and judge relevance yourself from its content.
- **Do not treat `no_match_above_threshold: false` as evidence that something was recorded.** It is
  currently false always. Abstain when the served content does not answer the question, regardless
  of the band.
- Decision-granular results carry the whole DRAFTS block, so the material you need to make that
  judgement is already in the payload - which is what makes judging from content, rather than from
  a score, practical.

The honest posture is unchanged from before the band existed: **ungrounded denial is an error, and
so is a confident answer from content that does not support it.** The band was intended to make
abstention tool-reported rather than guessed; it does not yet do that, and saying so here is
cheaper than an agent trusting it.


## Authority And Conflict Resolution

Current files are the active authority: `.memory-seed/index.md`, `.memory-seed/policy.md`, active `.memory-seed/skills/*.md`, and source/config files for implementation truth. Session history is evidence and reason, not automatic authority.

When history conflicts with current authority files, resolve by timeline only when all clear supersession criteria are met:

- the replacing source is a newer dated session entry or current authority file
- it states an explicit decision boundary
- it names the affected files, behavior, policy, or design area
- no later reversal or unresolved disagreement is found

If the conflict remains ambiguous or unresolved, ask the user before changing durable design, policy, bootstrap behavior, memory structure, release behavior, or similarly consequential workflow.
