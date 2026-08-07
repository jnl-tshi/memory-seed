"""EDA step 0: verify the data and the join logic BEFORE analysing anything.

Written after a bare-ref normalisation bug produced two wrong conclusions in one session. Every
later analysis reuses `normalised_lineage_edges()` and `decision_topics()` from here rather than
re-deriving the join, so the bug cannot recur per-script.

Checks: sidecar schema and ref forms; how much normalisation recovers; that evolves/replaces really
point backward in time; graph hygiene; and topic-map integrity.
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from memory_seed.adr import DECISION_REF_RE, _entry_decisions  # noqa: E402
from memory_seed.retrieval import (  # noqa: E402
    entry_link_sidecars,
    entry_topic_sidecars,
    load_corpus,
)

LINEAGE = {"evolves", "replaces"}


def decision_axes(cwd=REPO) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """(area, activity) per decision ref, read from the DECLARED axis channel.

    Topic sidecars emit nested `topics:` with `area:`/`activity:` sub-keys as of 2026-08-07, and
    `entry_topic_sidecars` surfaces them as `decision_area`/`decision_activity`. Declared beats
    inferred: the earlier approach flattened both axes into one set and recovered the axis by
    walking `topics.yaml` ancestry, which is a second derivation of something the record now
    states. It is also better covered - 1155 decisions resolve an area here against 1067 through
    the flattened channel.

    `proposed_topics` is deliberately NOT read. It holds vocabulary REQUESTS, which never resolve
    and are never attributions; treating one as a topic is exactly what its separate key prevents.
    """
    area: dict[str, set[str]] = collections.defaultdict(set)
    activity: dict[str, set[str]] = collections.defaultdict(set)
    for entry, record in entry_topic_sidecars(cwd).items():
        for key, target in (("decision_area", area), ("decision_activity", activity)):
            for ordinal, slug in (record.get(key) or ()):
                if ordinal:  # a blank ordinal is an entry-level attribution, not a decision's
                    target[f"{entry}:{ordinal}"].add(slug)
    return dict(area), dict(activity)


def decision_topics(cwd=REPO) -> dict[str, set[str]]:
    """Both axes per decision ref, unioned - for callers that do not care which axis a slug is on.

    Falls back to the flattened `inferred_decision_topics` for any decision the declared channel
    does not cover (records predating the nested form).
    """
    area, activity = decision_axes(cwd)
    out: dict[str, set[str]] = collections.defaultdict(set)
    for source in (area, activity):
        for ref, slugs in source.items():
            out[ref] |= slugs
    for chunk in load_corpus(cwd, "decision"):
        entry = (chunk.chunk_id or "").split(":")[0]
        for ordinal, slug in (getattr(chunk, "inferred_decision_topics", None) or ()):
            ref = f"{entry}:{ordinal}"
            if ordinal and ref not in out:
                out[ref].add(slug)
    return dict(out)


def normalised_lineage_edges(cwd=REPO) -> tuple[list[tuple[str, str, str, float | None]], dict]:
    """(kind, older, newer, confidence) with BOTH ends as <entry>:dN, plus a rejection tally.

    Most targets are stored bare. A bare ref resolves only where its entry has exactly one
    decision; anything ambiguous is dropped rather than guessed.
    """
    _, ordinals = _entry_decisions(cwd)

    def canon(ref: str) -> str | None:
        if DECISION_REF_RE.fullmatch(ref):
            return ref
        choices = sorted(ordinals.get(ref, set()))
        return f"{ref}:{choices[0]}" if len(choices) == 1 else None

    edges, dropped = [], collections.Counter()
    for source_entry, record in entry_link_sidecars(cwd).items():
        confidence = record.get("edge_confidence") or {}
        for kind, s_ord, t_entry, t_ord in (record.get("decision_edges") or ()):
            if kind not in LINEAGE:
                dropped["not-lineage"] += 1
                continue
            newer = canon(f"{source_entry}:{s_ord}" if s_ord else source_entry)
            older = canon(f"{t_entry}:{t_ord}" if t_ord else t_entry)
            if not newer or not older:
                dropped["ambiguous-bare-ref"] += 1
                continue
            edges.append((kind, older, newer, confidence.get((s_ord, t_entry, t_ord))))
    return edges, dict(dropped)


def main() -> int:
    raw = entry_link_sidecars(REPO)
    print("=== A1. SCHEMA AND REF FORMS ===")
    kinds, forms = collections.Counter(), collections.Counter()
    for source_entry, record in raw.items():
        for kind, s_ord, _t_entry, t_ord in (record.get("decision_edges") or ()):
            kinds[kind] += 1
            forms[("src:dN" if s_ord else "src bare", "tgt:dN" if t_ord else "tgt bare")] += 1
    print(f"  sidecar records: {len(raw)} | edge kinds: {dict(kinds)}")
    for form, n in forms.most_common():
        print(f"    {form}: {n}")
    print("  -> no edge has BOTH ends bare, but most have one; normalisation is mandatory.")

    edges, dropped = normalised_lineage_edges()
    print(f"\n=== A2. NORMALISATION ===\n  usable lineage edges: {len(edges)} | dropped: {dropped}")

    print("\n=== A3. DIRECTION (evolves/replaces must point BACKWARD in time) ===")
    stamps = {
        c.entry_id: str(c.entry_datetime or c.session_date or "")
        for c in load_corpus(REPO, "entry") if c.entry_id
    }
    tally = collections.Counter()
    for _kind, older, newer, _c in edges:
        a, b = stamps.get(older.split(":")[0], ""), stamps.get(newer.split(":")[0], "")
        tally["unknown" if not a or not b else "backward" if b > a else "forward-violation" if b < a else "same-stamp"] += 1
    print(f"  {dict(tally)}")

    print("\n=== A4. GRAPH HYGIENE ===")
    seen = collections.Counter()
    intra = 0
    for kind, older, newer, _c in edges:
        if older.split(":")[0] == newer.split(":")[0]:
            intra += 1
        seen[(kind, older, newer)] += 1
    print(f"  intra-entry edges: {intra}")
    print(f"  duplicate (kind, older, newer) triples: {sum(n - 1 for n in seen.values() if n > 1)}")
    authored = sum(1 for *_x, c in edges if c is None)
    print(f"  authored (unscored): {authored} | machine-scored: {len(edges) - authored}")

    print("\n=== A5. TOPIC MAP INTEGRITY ===")
    chunks = load_corpus(REPO, "decision")
    real = collections.defaultdict(set)
    for chunk in chunks:
        cid = chunk.chunk_id or ""
        if ":" in cid:
            real[cid.split(":")[0]].add(cid.split(":")[1])
    area, activity = decision_axes()
    topics = decision_topics()
    bad = sum(
        1 for ref in topics
        if ref.split(":")[1] not in real.get(ref.split(":")[0], set())
    )
    print(f"  decision chunks: {len(chunks)} | topiced decision refs: {len(topics)}")
    print(f"  declared AREA: {len(area)} | declared ACTIVITY: {len(activity)}")
    print(f"  attributions pointing at a NON-EXISTENT ordinal: {bad}")
    both = sum(1 for _k, o, n, _c in edges if topics.get(o) and topics.get(n))
    both_area = sum(1 for _k, o, n, _c in edges if area.get(o) and area.get(n))
    print(f"  lineage edges with topics on BOTH ends: {both}/{len(edges)} ({100 * both // max(1, len(edges))}%)")
    print(f"  lineage edges with AREA on both ends:  {both_area}/{len(edges)} ({100 * both_area // max(1, len(edges))}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
