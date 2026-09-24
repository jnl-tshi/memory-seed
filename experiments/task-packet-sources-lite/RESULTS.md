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
