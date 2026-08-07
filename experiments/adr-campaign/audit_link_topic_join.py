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
from memory_seed.retrieval import entry_link_sidecars, load_corpus  # noqa: E402

LINEAGE = {"evolves", "replaces"}


def decision_topics(cwd=REPO) -> dict[str, set[str]]:
    """Per-decision topics from the sidecar channel, which is the authority."""
    out: dict[str, set[str]] = collections.defaultdict(set)
    for chunk in load_corpus(cwd, "decision"):
        entry = (chunk.chunk_id or "").split(":")[0]
        for ordinal, slug in (getattr(chunk, "inferred_decision_topics", None) or ()):
            out[f"{entry}:{ordinal}"].add(slug)
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
    topics = decision_topics()
    bad = sum(
        1 for ref in topics
        if ref.split(":")[1] not in real.get(ref.split(":")[0], set())
    )
    sizes = collections.Counter(len(v) for v in topics.values())
    print(f"  decision chunks: {len(chunks)} | topiced decision refs: {len(topics)}")
    print(f"  attributions pointing at a NON-EXISTENT ordinal: {bad}")
    print(f"  topics-per-decision: {dict(sorted(sizes.items()))}")
    both = sum(1 for _k, o, n, _c in edges if topics.get(o) and topics.get(n))
    print(f"  lineage edges with topics on BOTH ends: {both}/{len(edges)} ({100 * both // max(1, len(edges))}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
