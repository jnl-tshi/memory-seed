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

## T7 — blocked: no packet compiles against this repository

`measure.py --repo` compiles read-only packets over the real corpus with two pinned decisions. It fails in
both profiles, before source following runs:

> `invalid_constitution_projection`: Constitution anchors must use the ratified Version's major identity

- `docs/CONSTITUTION.md` has been ratified as v2.x since 2026-09-19 (a4b51292), but all 30 of its clause anchors
  still read `constitution:v1#…`.
- `_constitution_clauses` requires the anchor prefix to match the ratified major version. So every Task
  Packet compiled against this repository has been refused since v2.0 was ratified.
- 54 ADRs, and 56 code and test references, bind `constitution:v1#…` anchors.
- The pilot fixture is unaffected; it carries its own Constitution.

This check predates the plan, and fixing it needs a decision (see the session log).


- `entry_future_timestamp_issue` (`memory_seed/core.py`) refuses a heading more than 10 minutes in the
  future. It applies at CLI and MCP append, including dry runs, and when `session fuse`, `merge-branch` or MCP
  integrate import a branch entry.
- Past stamps stay legal, which covers the dry-run echo and labelled backfill. Published history is never
  re-judged, so the corpus-wide check stays advisory.
- **Stated limit:** hand-authored entries are not detected. A session entry is plain Markdown with no
  writer-only marker, so any such check would either be forgeable or reject legitimate backfill. Instead, the
  tooling blocks the concrete Ada symptom, a future-dated stamp. Entry structure is enforced at append, and
  `links check` covers it at integration.
