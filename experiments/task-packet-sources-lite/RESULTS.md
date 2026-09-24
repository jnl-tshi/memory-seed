# Task Packet sources and orientation-lite measurements

Plan: [`docs/2_Todo/task-packet-sources-and-orientation-lite-plan.md`](../../docs/2_Todo/task-packet-sources-and-orientation-lite-plan.md).
Harness: [`measure.py`](measure.py).

- The harness compiles the offline pilot fixture with this repository's real `agent-rules.md` and
  `session_logging.md` substituted in, in two forms: the shipped read-only dispatch and a `worker_checkpoint`
  session-writing variant.
- Token counts are the compiler's UTF-8/4 estimates, not provider usage.
- Packet fingerprints differ between runs, because each run commits a fresh fixture whose base SHA includes
  the commit time. Token counts are stable across runs.
- The four frozen Seed Pod dispatches named in the plan were kept in an evaluator scratch area and are not in
  the repository, so the pilot fixture is the reproducible measurement set.

## T0 — baseline (repo `5eb1b5cb`, 2026-09-24)

| Packet | Serialized | `agent-rules.md` | `session_logging.md` | Baseline share | Envelope |
|---|---:|---:|---:|---:|---:|
| Read-only | 9,415 | 5,093 | — | 54.1% | 13,486 |
| Session-writing | 21,161 | 5,093 | 11,476 | 78.3% | 25,232 |

The embedded worker baselines are most of every packet. Without them, the same read-only packet would serialize
to about 4.3k tokens, and the session-writing one to about 4.6k. This confirms the plan's estimate: the
2026-09-06 baseline decision outweighs the 2026-09-05 clause-projection saving.

Raw output: [`t0.json`](t0.json).

## T7 — source following on the real corpus (repo `8858b276`, 2026-09-24)

`measure.py --repo` compiles read-only packets over this repository with two pinned real decisions,
`mse_v048edjgmvk5mqsx:d1` and `mse_nw47r0vpcj5tr2pj:d1`, under `implementation` v1 (source following off)
and v2 (on).

| Profile | Serialized | Envelope | Followed sources | Constitution projection |
|---|---:|---:|---|---|
| v1 | 17,773 | 21,844 | — | 26 ranked clauses, 4,424 tokens |
| v2 | 25,604 | 29,675 | 3 (6,586 tokens) | the same |

Followed sources:
- `.memory-seed/skills/end_of_turn.md` (2,766 tokens)
- `docs/8_Deferred/decision-storyline-retrieval-proposal.md` (1,952)
- `docs/8_Deferred/laya-local-decision-worker-proposal.md` (1,868)

Reported but not followed:
- two sources over the 4,000-token cap: `agent_collaboration.md` at 13,813 tokens, and the tournament plan at
  4,368;
- three archived reports, labelled as retired.

The `agent-rules.md` baseline is still 5,093 tokens in both, and is removed by T8.

Findings:

1. **Fixed here: no packet compiled against this repository since Constitution v2.0 (2026-09-19).** Anchors
   read `constitution:v1#…`, but the compiler requires the ratified major. JNL chose v2 names with v1 legacy
   aliases, applied as correction 2.3.
   - All 30 anchors are renamed.
   - The compiler and ADR validation resolve `vK#slug` to the current name, so the 54 historical ADR bindings
     still validate.
   - `adr promote` and `adr revise` refuse a legacy name in a new event, so bindings migrate as ADRs change.
2. **Fixed: real-corpus resolution took about 4.8 s against a 5 s deadline**, so packets over this repository
   failed by chance with `timeout`. It now takes about 1.0-1.9 s, from three changes:
   - Resolution skips the per-chunk lexical-term scan, which only search ranking reads.
   - Runtime confinement resolves only symlinks and junctions instead of every file.
   - The end-of-resolution stability check compares a stat signature instead of re-hashing the corpus.

   Corpus revisions are byte-identical to the previous implementation, and a junction escape is still refused
   (`tests/test_retrieval_deadline.py`). The harness no longer lifts the deadline: T7 passed 3 of 3 runs under
   the production 5 s limit.
3. **Open: ranked clause projection is weak on real text.** A generic dispatch selected 26 of 30 clauses. The
   saving from clause projection depends on explicit or ADR-bound refs.
4. **The 4,000-token cap cuts real sources.** Two of the five sources worth following exceeded it. Citing
   heading anchors avoids this; raising the cap is a calibration question for M3.

Raw output: [`t7.json`](t7.json).

## T3 — mechanical session-write backstop


- `entry_future_timestamp_issue` (`memory_seed/core.py`) refuses a heading more than 10 minutes in the
  future. It applies at CLI and MCP append, including dry runs, and when `session fuse`, `merge-branch` or MCP
  integrate import a branch entry.
- Past stamps stay legal, which covers the dry-run echo and labelled backfill. Published history is never
  re-judged, so the corpus-wide check stays advisory.
- **Stated limit:** hand-authored entries are not detected. A session entry is plain Markdown with no
  writer-only marker, so any such check would either be forgeable or reject legitimate backfill. Instead, the
  tooling blocks the concrete Ada symptom, a future-dated stamp. Entry structure is enforced at append, and
  `links check` covers it at integration.
