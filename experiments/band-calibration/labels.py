"""Mechanically derived query labels for relevance-band calibration.

Nothing here is hand-labelled for relevance. Positives come from structure the store already
carries; negatives are written by hand but selected on a criterion INDEPENDENT of retrieval score,
which matters - picking negatives because they score low would guarantee the separation the
experiment is supposed to test.

Positive sources, weakest-circularity last:

  P_life   a retired decision's title should surface its live replacing head. Predates this work,
           already used by decision-retrieval-scale/measure.py, and the least circular of the three:
           the expected answer is a DIFFERENT entry from the one the query text came from.
  P_terms  a subset of content words sampled from an entry's own D: text should surface that entry.
           Partially circular - the query is drawn from the target - but it is a fair model of
           "agent half-remembers a decision and asks about it", and the subset sampling means the
           query is never the verbatim text.
  P_title  an entry's title should surface that entry. Most circular; used only as a sanity floor.
           If this fails, ranking is broken and no threshold work is meaningful.

Negatives:

  N_none   incoherent / wrong-domain questions (sourdough, quantum error correction).
  N_hard   fluent, plausible software-engineering questions about technologies this project does
           not use. These are the ones that matter: they are what an agent actually asks when the
           answer is not recorded.

A caveat that belongs in the report, not just the code: under a purely lexical ranker, a negative
defined by "the corpus does not contain these words" is close to a negative defined by "scores
low". N_hard is therefore an easier test than it looks, and any threshold that fails on it is
decisively broken, while one that passes has cleared a low bar.
"""

from __future__ import annotations

import random
import re
from pathlib import Path

# load_corpus, never extract_memory_chunks. The first version of this file used the raw extractor
# and reported "the corpus has 4 replaces edges". The augmented read shows 23 replaced_by and 290
# evolved_by - lifecycle edges are authored into link sidecars after the entry is written, and the
# raw extractor carries none of them. tests/test_corpus_read_path.py makes that mistake loud inside
# the package; experiments sit outside its scope, so here the discipline is this import.
from memory_seed.retrieval import load_corpus
from memory_seed.semantic_cache import (
    build_related_entry_graph,
    evolves_lineage_heads,
    replacing_lineage_heads,
)

# Fluent questions about technology this project does not use. Chosen by domain knowledge, then
# checked for corpus term overlap in the report - never selected by their retrieval score.
HARD_NEGATIVES = [
    "how do we configure the kubernetes ingress controller for canary rollouts",
    "what is our jwt refresh token rotation policy",
    "why did we choose postgres table partitioning over sharding",
    "how is the redis cache eviction policy configured",
    "what does the terraform module for the vpc peering look like",
    "how do we handle websocket backpressure in the gateway",
    "which grpc interceptors run on the inbound request path",
    "what is the retry budget for the payment provider webhook",
    "how are android push notification tokens refreshed",
    "what indexes back the elasticsearch product search",
    "how does the kafka consumer group rebalance on deploy",
    "what is our graphql schema stitching strategy",
    "why is the service mesh sidecar injecting latency on startup",
    "how do we rotate the s3 bucket encryption keys",
    "what triggers the autoscaling policy on the worker pool",
    "how is the oauth device flow implemented for the tv app",
    "what is the sharding key for the analytics warehouse",
    "how do we throttle outbound smtp to avoid blacklisting",
    "which browsers require the polyfill bundle",
    "how does the cdn purge propagate after a deploy",
    "what is the lock timeout on the distributed scheduler",
    "how are stripe webhook signatures verified",
    "what is the rollback plan for a failed blue green cutover",
    "how do we detect n plus one queries in the orm",
]

NONSENSE_NEGATIVES = [
    "recipe for sourdough starter hydration",
    "quantum error correction surface codes",
    "best fertiliser for tomato plants in clay soil",
    "how long to braise beef shin for stew",
    "rules for the offside trap in five a side",
    "why do cats knead blankets before sleeping",
    "what year did the treaty of westphalia get signed",
    "how do you prune an apple tree in winter",
    "which muscles does a romanian deadlift target",
    "what is the tuning for a drop d guitar",
]

_STOP = {
    "the", "and", "for", "that", "with", "this", "from", "was", "were", "not", "but", "its",
    "into", "than", "then", "they", "them", "their", "what", "when", "which", "while", "would",
    "could", "should", "have", "has", "had", "are", "our", "out", "per", "via", "any", "all",
    "one", "two", "use", "used", "using", "make", "makes", "made", "does", "did", "done",
}


def _content_words(text: str, minimum: int = 4) -> list[str]:
    words = [w for w in re.findall(r"[a-z0-9_]+", text.lower()) if len(w) >= minimum]
    return [w for w in words if w not in _STOP]


def _title_of(chunk) -> str | None:
    if chunk is None or not chunk.entry_title:
        return None
    title = chunk.entry_title.split(" - ", 1)[-1].strip()
    return title if len(title.split()) >= 3 else None


def lifecycle_positives(cwd: Path, limit: int = 200) -> list[dict]:
    """Lifecycle targets from BOTH typed edge kinds, scored by different rules.

    Read through `load_corpus`, the corpus carries 23 `replaced_by` and 290 `evolved_by`. Read raw
    it appears to carry 4 and 136, because the majority of lifecycle edges are authored into link
    sidecars after the entry is written. Both kinds are used: supersession alone would still be a
    thin guard, and this set is what protects changes to recency (recency is partly doing
    supersession's job by accident).

    The two kinds are NOT interchangeable and pooling them would manufacture failures:

      replaces  retires its target. Querying the retired title should surface the replacement, and
                the replacement should outrank the entry it retired. Both are scored.
      evolves   explicitly does NOT retire: `evolves_lineage_heads` exists to "point a reader at the
                up-to-date form without burying the still-valid original", and evolves is never
                dampened. The original outranking its head is CORRECT here, so the only thing worth
                scoring is whether the newer form also surfaces.

    Rows carry `edge_kind` so the two are always reported separately. `rival` is set only for
    `replaces`, and is the entry the expected answer is supposed to outrank.
    """
    chunks = load_corpus(cwd, "entry")
    graph = build_related_entry_graph(cwd, chunks=chunks)
    by_id = {c.entry_id: c for c in chunks if c.entry_id}
    out: list[dict] = []

    for node in graph.values():
        if not node.replaced_by:
            continue
        heads = replacing_lineage_heads(graph, node.entry_id)
        title = _title_of(by_id.get(node.entry_id))
        if not heads or title is None:
            continue
        out.append(
            {
                "query": title,
                "expected": heads[0],
                "accepted": tuple(heads),
                # The retired entry the replacement must beat. Recency currently suppresses this
                # entry by age; weakening recency is exactly what could let it climb back above.
                "rival": node.entry_id,
                "edge_kind": "replaces",
                "source": "P_life_replaces",
            }
        )
        if len(out) >= limit:
            return out

    for node in graph.values():
        if not node.evolved_by:
            continue
        heads = evolves_lineage_heads(graph, node.entry_id)
        title = _title_of(by_id.get(node.entry_id))
        if not heads or title is None:
            continue
        out.append(
            {
                "query": title,
                # The newer form is what we are testing for. The original is also a correct answer
                # and is expected to rank first - that is self-retrieval and is not scored here.
                "expected": heads[0],
                "accepted": tuple(heads),
                # The entry the query text came from. Named explicitly so a scorer can exclude it
                # rather than inferring it from position in `accepted`.
                "origin": node.entry_id,
                "rival": None,
                "edge_kind": "evolves",
                "source": "P_life_evolves",
            }
        )
        if len(out) >= limit:
            break
    return out


QUERY_LENGTHS = (3, 7, 15)


def term_positives(cwd: Path, limit: int = 200, sample: int = 7, seed: int = 20260805) -> list[dict]:
    """A subset of an entry's own decision text, as a query, should surface that entry."""
    rng = random.Random(seed)
    chunks = [c for c in load_corpus(cwd, "decision") if c.entry_id]
    rng.shuffle(chunks)
    out: list[dict] = []
    for chunk in chunks:
        words = _content_words(chunk.text)
        # Deduplicate while keeping order so a repeated term cannot fill the whole query.
        unique = list(dict.fromkeys(words))
        if len(unique) < sample + 3:
            continue
        picked = rng.sample(unique, sample)
        out.append(
            {
                "query": " ".join(picked),
                "expected": chunk.entry_id,
                "source": "P_terms",
                "n_terms": sample,
            }
        )
        if len(out) >= limit:
            break
    return out


def term_positives_by_length(
    cwd: Path, limit_per_length: int = 60, lengths: tuple[int, ...] = QUERY_LENGTHS
) -> list[dict]:
    """The same construction at several query lengths, tagged by length.

    Lexical score accumulates over matched terms and fields while cosine is a single bounded
    number, so the two components scale differently with query length. A blend tuned at one length
    is not evidence about another - which is precisely the flaw in the weight-60 sweep, whose
    queries were all 7 terms. Stratifying by length is the point of the experiment, so the label
    set has to carry the strata.
    """
    out: list[dict] = []
    for index, length in enumerate(lengths):
        # Distinct seed per length, or the shuffles align and the same entries supply every stratum,
        # which would hide a length effect behind a fixed entry sample.
        rows = term_positives(cwd, limit=limit_per_length, sample=length, seed=20260805 + index * 97)
        for row in rows:
            row["source"] = f"P_terms{length}"
        out.extend(rows)
    return out


def title_positives(cwd: Path, limit: int = 200, seed: int = 20260805) -> list[dict]:
    """An entry's title should surface that entry. Sanity floor only."""
    rng = random.Random(seed + 1)
    chunks = [c for c in load_corpus(cwd, "entry") if c.entry_id]
    rng.shuffle(chunks)
    out: list[dict] = []
    for chunk in chunks:
        if not chunk.entry_title:
            continue
        title = chunk.entry_title.split(" - ", 1)[-1].strip()
        if len(title.split()) < 4:
            continue
        out.append({"query": title, "expected": chunk.entry_id, "source": "P_title"})
        if len(out) >= limit:
            break
    return out


def negatives() -> list[dict]:
    rows = [{"query": q, "expected": None, "source": "N_hard"} for q in HARD_NEGATIVES]
    rows += [{"query": q, "expected": None, "source": "N_none"} for q in NONSENSE_NEGATIVES]
    return rows


def build(cwd: Path, per_source: int = 120) -> list[dict]:
    """The label set.

    Paraphrase positives come from `term_positives_by_length`, so `P_terms` is replaced by
    `P_terms3` / `P_terms7` / `P_terms15`. That changes the mix, so numbers from this set are NOT
    comparable to runs made before the strata existed - re-baseline rather than diffing against
    `results-lexical.json` from the first calibration run.
    """
    rows = (
        lifecycle_positives(cwd, per_source)
        + term_positives_by_length(cwd, limit_per_length=per_source // 2)
        + title_positives(cwd, per_source)
        + negatives()
    )
    return rows


def split(rows: list[dict], seed: int = 20260805) -> tuple[list[dict], list[dict]]:
    """Stratified fit/held-out halves.

    Stratified by source so the held-out half cannot end up without negatives - with only 18
    negatives a naive random split can leave one side almost blind, and a threshold scored against
    positives alone always looks excellent.
    """
    rng = random.Random(seed + 2)
    fit: list[dict] = []
    held: list[dict] = []
    by_source: dict[str, list[dict]] = {}
    for row in rows:
        by_source.setdefault(row["source"], []).append(row)
    for source in sorted(by_source):
        group = list(by_source[source])
        rng.shuffle(group)
        half = len(group) // 2
        fit.extend(group[:half])
        held.extend(group[half:])
    return fit, held
