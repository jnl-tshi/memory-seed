# Post-write advisory curator: offline contract trial

Date: 2026-10-03. Run: `python -X utf8 -m hosted.evaluation.advisory_trial`.

This is a synthetic, scripted contract trial of `hosted/curator/advisory.py`, **not** a model-quality
evaluation or a hosted-service pilot. Each case begins with an already accepted first-hand write
receipt. The reviewer sees only newly disclosed dialogue batches; advice is returned for review and
never applied to a record, topic, or link. The submission declares first-hand provenance; each
suggestion declares reconstructed provenance.

| Measure | Result | Meaning |
|---|---:|---|
| Synthetic cases | 9 | Clean; missing/stale topic; missing/stale link; scope conflict; misleading suggestion; invalid citation; window limit |
| Useful suggestions | 5 | Matched hand-authored fixture labels |
| False suggestions | 1 | A misleading billing topic with a structurally valid parser quote |
| Missed fixture suggestions | 0 | Scripted reviewer, not a generalization claim |
| Incomplete at bound | 1 | Source at turn 0 was outside the twenty-preceding-turn cap from turn 25 |
| Invalid citations accepted / rejected | 0 / 1 | Deliberately forged quote was rejected; tool-only citation rejection is separately unit-tested |
| Review calls | 20 | One or more dialogue batches per case; no model calls |
| Local median / max delay | 0.154 / 0.702 ms | One scripted run; not hosted queue/provider latency |
| Model tokens | 0 input / 0 output | No model was used; this is not a production token estimate |

The deliberately false suggestion demonstrates the boundary: a valid citation proves that a quote
exists in a disclosed source, **not** that it supports a topic or link. Semantic suggestion precision,
cross-project topic freshness, and conflict-flag accuracy remain unmeasured. The trial does not prove
authentication, owner-only access, persistence, retries, approval delivery, or production latency.

Next bounded evaluation: freeze independently reviewed, root-disjoint first-hand decision cases;
compare a real secondary reviewer against no-suggestion and deterministic baselines, with field-level
labels, exact source links, false-suggestion counts, latency, and measured token use. Keep the
retrospective discovery corpus separate from this post-write evaluation.
