# Post-write advisory curator: offline contract trial

Date: 2026-10-03. Run: `python -X utf8 -m hosted.evaluation.advisory_trial`.

This is a synthetic, scripted contract trial of `hosted/curator/advisory.py`, **not** a model-quality
evaluation or a hosted-service pilot. Each case begins with an already accepted first-hand write
receipt. The reviewer first sees the accepted claim, current topic candidates, and existing decision
candidates. It sees no dialogue unless it names an unresolved source question; any later call receives
only the next newly disclosed dialogue batch. Advice is returned for review and never applied to a
record, topic, or link. The submission declares first-hand provenance; each suggestion declares
reconstructed provenance. Accepted-claim and existing-record quotes can ground ordinary advice without
opening raw history.

| Measure | Result | Meaning |
|---|---:|---|
| Synthetic cases | 9 | Clean; missing/stale topic; missing/stale link; scope conflict; misleading suggestion; invalid citation; window limit |
| Useful suggestions | 5 | Matched hand-authored fixture labels |
| False suggestions | 1 | A misleading billing topic with a structurally valid parser quote |
| Missed fixture suggestions | 0 | Scripted reviewer, not a generalization claim |
| Incomplete at bound | 1 | Source at turn 0 was outside the twenty-preceding-turn cap from turn 25 |
| Invalid citations accepted / rejected | 0 / 1 | Deliberately forged quote was rejected; tool-only citation rejection is separately unit-tested |
| Record-only / source-check cases | 6 / 2 | The forged-citation control was rejected at record comparison |
| Review calls | 22 | Record comparison plus source batches only when requested; no model calls |
| Local delay | Not a service measure | Scripted in-process execution omits queue and provider time |
| Model tokens | 0 input / 0 output | No model was used; this is not a production token estimate |

The deliberately false suggestion demonstrates the boundary: a valid citation proves that a quote
exists in a cited source, **not** that it supports a topic or link. Semantic suggestion precision,
candidate-decision retrieval recall, cross-project topic freshness, and conflict-flag accuracy remain
unmeasured. The trial does not prove
authentication, owner-only access, persistence, retries, approval delivery, or production latency.

Next bounded evaluation: freeze independently reviewed, root-disjoint first-hand decision cases;
compare a real secondary reviewer against no-suggestion and deterministic baselines, with field-level
labels, exact source links, false-suggestion counts, latency, and measured token use. Keep the
retrospective discovery corpus separate from this post-write evaluation.
