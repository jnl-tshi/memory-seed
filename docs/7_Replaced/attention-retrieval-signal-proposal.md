---
superseded_by: "../2_Todo/hosted-memory-mvp-programme.md"
superseded_on: "2026-09-19"
disposition_note: "Unique active requirements were integrated into the canonical hosted programme; local or future-only remnants are separately retained where applicable."
title: "Attention Retrieval Signal Proposal"
date: "2026-08-04"
project: "memory-seed"
status: "capture-and-exposure-shipped; ranking flip gated on real usage"
priority: "P2"
next_action: "Accumulate real MCP usage, then run `memory-seed ranking-ab --signal attention --query ...` before any default-ranking change."
related:
  - "docs/CONSTITUTION.md"
  - "docs/5_Completed/interaction-frequency-ranking-plan.md"
  - "docs/5_Completed/freshness-aware-memory-ranking-proposal.md"
  - "docs/5_Completed/real-corpus-ranking-validation-gate-proposal.md"
  - "docs/3_Spec/graph-edge-contract.md"
---

# Attention Retrieval Signal Proposal

Status: **capture + exposure SHIPPED with this proposal; default-ranking flip explicitly deferred
behind the ranking-ab gate.** Five-question test: **Retrieval, Application**.

Un-defers **P2 ("real access-frequency telemetry")** of
[interaction-frequency-ranking-plan.md](../5_Completed/interaction-frequency-ranking-plan.md) — the
recorded deferred end goal of the attention line of work, ratified for pickup by JNL on 2026-08-04.
The framing: retrieval should surface not only the most semantically relevant, most recent, and most
evolved version of a decision, but also the one that has been *looked at a lot* — the search-engine
insight applied to the decision store.

## Decision

Track which entries agents actually open through the MCP surface; expose a decayed
fetch-frequency signal read-only on every retrieval result; flip default ranking only after the
shipped real-corpus A/B gate passes on genuinely accumulated usage.

## Design (as built)

**Substrate: a small event log; interface: a derived counter.** A bare per-entry counter was
evaluated and rejected as the sole store, for four reasons: it cannot decay (no timestamps); it
cannot explain itself (Trace/M5 rulings require attention to be "a stated rule with its underlying
evidence, not a hidden priority score"); concurrent sessions lose increments on read-modify-write;
and it amplifies rich-get-richer with no way to mitigate. The counter users see
(`fetch_count`) is derived from the log.

**Fetch vs impression — the load-bearing weighting.** `memory_search` returning an entry is the
*ranker's* choice (an impression); `memory_get_chunk` on it afterwards is the *agent's* choice (a
click). Only fetches score. Impressions are logged source-tagged at weight zero — counting them
would feed the ranker its own output. This is the impression/click distinction relevance systems
converged on.

**Files** (both gitignored; self-registered in `.gitignore` on first write, mirroring the
`local.yaml` pattern):

| File | Role |
|---|---|
| `.memory-seed/.retrieval-log.jsonl` | one `{schema, ts, tool, entry_id}` line per retrieval event |
| `.memory-seed/.retrieval-attention.json` | compacted decayed summary — freely rewritable projection |

**Decay:** `score = Σ 0.5^(age_days / 30)` over fetch events (`HALF_LIFE_DAYS = 30`,
`memory_seed/attention.py`). Compaction folds the log into the summary and truncates it past
`COMPACT_THRESHOLD = 5000` lines.

**Instrumentation:** the MCP dispatch choke point (`handle_jsonrpc_message`,
`memory_seed/mcp_server.py`), fail-open by contract — telemetry must never break the tool call it
observed.

**Exposure:** `attention_score`, `fetch_count`, `last_fetch` on every `memory_search` result row
and `memory_get_chunk` payload, beside the lifecycle annotations (`evolved_head`,
`replacing_head`) — "most looked-at" and "most evolved" read side by side. Same
computed-but-not-blended contract as `importance_score`.

**Ranking hook (default OFF):** `attention_boost` on `memory_search` / `search_memory` /
`rank_session_memory`; applied in `rank_memory_chunks` as
`final_score *= 1 + ATTENTION_RANK_BOOST * log1p(decayed_score)` (log-scaled to blunt
rich-get-richer). Registered as signal `attention` in `SIGNAL_REGISTRY`, so the flip path is the
standard one: `memory-seed ranking-ab --signal attention` over real accumulated usage. The
multiplier shape is provisional until that gate.

## Constitutional position

- **Invariant #2 (append-only past) does not bind these files** — they are operational retrieval
  state, not memory content. Ratified by JNL 2026-08-04 ("retrieval is a retrieval mechanism").
  Truncation-on-compaction is deliberate.
- **Invariant #6**: the summary is a rebuildable projection of the log; nothing here is
  authoritative memory, nothing is required for the core to run, and total absence degrades to
  "no attention data".
- **Invariant #7 + §3 "Expose before you rank"**: the signal never hides anything, is surfaced
  read-only first, and default ordering is byte-for-byte unchanged until the gate passes (tested:
  `tests/test_attention.py::test_default_ranking_identical_with_boost_off`).
- **Privacy (carried from the P2 design):** events carry `entry_id`, `ts`, `tool` — never query
  text. Behavioral telemetry stays in the gitignored runtime files and is never promoted into
  `index.md` or session logs.
- **Boundary note:** `quality.py`'s standing rule ("no metric may feed ranking") governs the
  *quality metrics report*; attention is a retrieval signal under the ranking-ab regime, the same
  lane freshness and supersession damping graduated through. Stated here so the boundary is
  declared, not discovered.

## Deferred to v2 (recorded, not built)

- **Lineage attribution** — crediting fetches of a superseded entry to its `replacing_head` /
  `evolved_head`, so attention follows the living decision. Needs evidence that stale-entry
  fetches are common (the E8 veto probe informs this).
- **Impression weighting** — a small nonzero weight for search impressions, only with A/B evidence.
- **Trace `lense_view` events** — the P2 design's third source; needs the Trace cache-lifecycle
  split it describes.
- **Cross-checkout aggregation** — the log is per-checkout; worktrees fragment the signal. Accepted
  for v1: the primary checkout carries most retrieval traffic.
- **Session-start surfacing** — "most-attended decisions" in the SessionStart hook context.

> **Resolved 2026-08-05 (later the same day).** The repo's `.mcp.json` now runs
> `uv run --no-sync python -m memory_seed.mcp_server --stdio`, so this checkout dogfoods its own
> build and the log accumulates from real sessions. Verified end to end: a `memory_search` call
> through the local server created `.memory-seed/.retrieval-log.jsonl`, where the published package
> had produced nothing. Two things came out of wiring it up:
>
> - **Impressions were being double-counted.** Under decision granularity one entry supplies several
>   result rows, and the recorder logged each - a single search wrote 8 events across 6 entries.
>   Scores were unaffected (impressions weigh zero at `attention.py:184`), but the log inflated
>   toward compaction and any future impression weighting would have quietly favoured entries with
>   the most decisions. Now one impression per entry per search.
> - **The config survives `update` only because `"uv"` is absent from `_OWN_MCP_COMMANDS`.** That is
>   load-bearing behaviour resting on the absence of a string. `tests/test_mcp_local_build.py` pins
>   it, and the failure was confirmed reachable by adding `"uv"` to the set and watching the entry
>   revert to the published package.
>
> The section below is kept as the record of why the log was empty for a day.

## Observability: why the log is still empty (2026-08-05)

`.memory-seed/.retrieval-log.jsonl` does not exist in this repository, and that is expected rather
than a fault. This project's `.mcp.json` registers `uvx --from memory-seed memory-seed-mcp` - the
**published** package - so the instrumentation added on 2026-08-05 is not the code any session here
actually runs. The signal starts accumulating only after a release carries it, or under an MCP
config pinned to the local working tree (`python -m memory_seed.mcp_server` with `PYTHONPATH`, the
pattern the agent-capture fixtures use). Same class as the recorded stale-console-script hazard:
the file on disk is not necessarily the code in the loop.

Consequence for the gate: `memory-seed ranking-ab --signal attention` cannot pass here yet, and as
of 2026-08-05 it correctly **refuses** rather than reporting a vacuous PASS - see below.

## Correction, 2026-08-05: the gate could be passed on no evidence

As shipped, the signal's registry comment claimed the gate "cannot pass on an empty log". That was
false whenever `--query` was supplied: with nothing in the log, `affected` returned an empty set,
every query fell into the control bucket, both arms were byte-identical, and `ABResult.passed`
returned **True** - a pass certifying nothing. Fixed by adding `requires_affected_hits` to `Signal`
and `ABResult`: a signal whose evidence base is accumulated runtime data fails closed when that
base is empty, and the report says so in words. Covered by `tests/test_ranking_ab.py`
(`AttentionSignalGateTests`), which had zero attention coverage before this.

## Promotion gate

Default flip requires: (1) weeks of real accumulated usage in this repo's log, (2)
`memory-seed ranking-ab --signal attention --query ...` showing directional improvement with
byte-identical unaffected-query controls, (3) a fixture pair in the ranking fixtures. Until all
three, `attention_boost` stays opt-in.
