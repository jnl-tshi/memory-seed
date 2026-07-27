---
priority: P2
next_action: JNL to approve or reject the four candidate children, and to decide the redundant-tag question that the measurement exposed. Nothing may be written to topics.yaml before that.
---

# Proposal: children for `memory-trace`, and what the measurement says instead

Status: **PROPOSAL — 2026-07-27.** The first run of proposal mode
(`scripts/propose_topic_children.py`), triggered by the concentration measurement as
[vocabulary-proposal-mode-proposal.md](vocabulary-proposal-mode-proposal.md) requires. No vocabulary
change has been made; `topics.yaml` is untouched.

## Why this slug is open

`measure_topic_concentration.py`, 2026-07-27:

| slug | entries | share | rollup |
|---|---|---|---|
| **memory-trace** | 202 | **43.9%** | 202 |
| memory-seed | 116 | 25.2% | 116 |
| graph | 108 | 23.5% | 111 |
| ui-design | 100 | 21.7% | 100 |

`memory-trace` is on nearly half of every topiced entry, and it has **no children at all**. It is the
work queue's first item and the reason the sweep has nothing useful to ask.

## The finding that changes the shape of the answer

**43% of the entries carrying `memory-trace` already carry a finer AREA slug.** 86 of 202:

| also carries | entries |
|---|---|
| `graph` | 63 |
| `memory-seed` | 9 |
| `mermaid` | 6 |
| `control-plane` | 3 |
| `session-logging` | 3 |
| `session-layout` | 2 |
| `process-management`, `continuity` | 1 each |

For those entries `memory-trace` is not under-specified, it is **redundant** — a blanket "this is the
Trace app" tag sitting beside the slug that already says which part. No child can fix that, because the
specificity is already recorded. The remedy is to stop the parent claiming them, which is a
**retraction**, not a vocabulary addition.

Only the other **116** entries (57%) have `memory-trace` as their only area tag. Those are the entries a
child could legitimately claim, and they are what the candidates below are measured against.

## Candidates

Axis `area`, matching the parent — a child never crosses axes. Counts are entries where `memory-trace`
is the only area tag.

| candidate | entries | % of corpus | verdict |
|---|---|---|---|
| **`trail`** — the chronological timeline: decision rows, lanes, brackets, group anchors | 40 | 8.7% | **clears** |
| **`trace-shell`** — the app frame: settings, panes, docking, typography, theme, find bar | 14 | 3.0% | **clears** |
| **`trace-cache`** — startup, incremental derivation, freshness, generation, rebuild | 12 | 2.6% | **clears** |
| **`trace-harness`** — Storybook, Playwright, e2e, a11y gates, renderer evidence | 10 | 2.2% | **clears** |
| `inspector` — the entry reader pane | 7 | 1.5% | under floor (8) |
| `diagram-view` — the Mermaid viewer | 4 | 0.9% | under floor (8) |
| `trace-api` — versioned contract, projection payloads | 3 | 0.7% | under floor (8) |

`trail` is a strong candidate on its own evidence: at 40 entries it is larger than eleven of the
vocabulary's existing roots.

Deliberately **not** proposed: a `graph-view` child. 63 of these entries already carry the `graph`
root, so the seam is covered — minting a Trace-flavoured duplicate of an existing area slug would be
the unearned depth the promotion rule exists to refuse.

## The scorer's verdict: REJECT

```
  trail            40   8.7%   ok        trace-cache    12   2.6%   ok
  trace-shell      14   3.0%   ok        trace-harness  10   2.2%   ok
  inspector         7   1.5%   UNDER FLOOR (8)
  diagram-view      4   0.9%   UNDER FLOOR (8)
  trace-api         3   0.7%   UNDER FLOOR (8)
  (residual on the parent)   112   24.3%

REJECT:
  - three candidates below the floor of 8
  - parent still 24.3% after the split, target is <=20%
```

The four qualifying children take `memory-trace` from 43.9% to **24.3%** — a large improvement that
still misses the target, and it misses it *because of the 86 redundant tags*, not because the children
are wrong. The arithmetic is worth stating plainly:

- children alone: 202 → 112 entries, **24.3%**
- children **and** retracting the 86 redundant parent tags: 202 → 40 entries, **8.7%**

Splitting solves about half the problem. The other half is a tag that should never have been on those
entries beside a finer one.

## What is being asked

1. **Approve or reject the four children** — `trail`, `trace-shell`, `trace-cache`, `trace-harness`.
   Approval means adding four `parent: memory-trace` slugs to `topics.yaml`, which is a governance
   change to deploy-once state and cannot be made by an agent.
2. **Decide the redundant-tag question.** Should `memory-trace` come off an entry that already carries a
   finer area slug? This is the larger half of the concentration and it needs a mechanism that does not
   exist: links have `retracts:`, topics do not. Under the standing rule that swarm output may only
   override write-time data through a reviewed retraction, there is currently no legal way to remove a
   topic an author wrote.
3. The three under-floor candidates should be **declined for now** and revisited if their areas grow —
   the floor is what stops the vocabulary acquiring depth it has not earned.

## Notes for whoever picks this up

- The three sub-floor candidates are real distinctions, just not yet load-bearing ones. `inspector` at 7
  is one entry short and will likely qualify on its own within a week of inspector work.
- Clustering here was keyword-led over entry titles and then reviewed, not a swarm fan-out. That is
  weaker evidence than reading the bodies, and it is why this document reports counts and quotes rather
  than asserting the split is correct. A swarm pass over the 116 would firm up the boundaries —
  particularly the 26 that matched nothing.
- Re-run any number in this document with:
  `python scripts/propose_topic_children.py gather memory-trace`
  `python scripts/propose_topic_children.py score memory-trace <split.json>`
