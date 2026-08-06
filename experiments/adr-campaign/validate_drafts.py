"""Phase-4 mechanical validation of swarm ADR drafts. Drop-never-repair.

Every check drops the whole concern on failure and logs why. Nothing is repaired: a repaired
verdict is the orchestrator's judgement wearing the swarm's provenance. Quote grounding is the
hallucination guard that survived every prior campaign - a claim whose quote is not a verbatim
(whitespace-normalised) substring of the cited file is treated as ungrounded, whatever it says.

Usage:
  python experiments/adr-campaign/validate_drafts.py drafts-*.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from memory_seed.adr import (  # noqa: E402
    ADR_ID_RE,
    DECISION_REF_RE,
    _constitution_anchors,
    adr_membership,
    iter_adrs,
)
from memory_seed.retrieval import get_chunk, load_corpus  # noqa: E402
from memory_seed.topics import load_topic_index  # noqa: E402

CAPS = {"decision": 700, "why": 700, "evolution": 500, "title": 120}


def norm(text: str) -> str:
    return " ".join(text.split())


def main() -> int:
    assigned = {c["adr_id"]: c for c in json.loads((HERE / "concerns.json").read_text(encoding="utf-8"))["concerns"]}
    anchors = _constitution_anchors(REPO)
    canonical = {v for v in load_topic_index(REPO).resolution().values()}
    existing_ids = {r.adr_id for r in iter_adrs(REPO)}
    claimed = set()
    for record in iter_adrs(REPO):
        claimed |= adr_membership(record)
    decision_bodies: dict[str, str] = {
        c.chunk_id: norm(c.text or "") for c in load_corpus(REPO, "decision") if c.chunk_id
    }

    survivors, drops = [], []
    seen_ids = set()
    for path in sorted(HERE.glob("drafts-*.json")):
        for item in json.loads(path.read_text(encoding="utf-8")):
            adr_id = item.get("adr_id", "?")
            def drop(reason: str) -> None:
                drops.append({"adr_id": adr_id, "batch": path.name, "reason": reason})

            if item.get("skip"):
                drop(f"worker skipped: {item['skip']}")
                continue
            if adr_id not in assigned:
                drop("not an assigned concern")
                continue
            if adr_id in seen_ids:
                drop("duplicate across workers")
                continue
            if not ADR_ID_RE.fullmatch(adr_id) or adr_id in existing_ids:
                drop("bad or colliding adr_id")
                continue
            over = [k for k, cap in CAPS.items() if len(item.get(k, "")) > cap]
            if over:
                drop(f"over length cap: {over}")
                continue
            if not item.get("decision", "").strip() or not item.get("why", "").strip():
                drop("empty decision or why")
                continue
            source_file = item.get("source_file", "")
            quote = item.get("source_quote", "")
            allowed_files = {s.split("#")[0] for s in assigned[adr_id]["sources"]}
            if source_file not in allowed_files:
                drop(f"source_file {source_file!r} not among assigned sources")
                continue
            try:
                body = norm((REPO / source_file).read_text(encoding="utf-8"))
            except OSError:
                drop(f"unreadable source {source_file}")
                continue
            if len(quote) < 25 or norm(quote) not in body:
                drop("source_quote not grounded in source file")
                continue
            good_support = []
            support_ok = True
            for support in item.get("supporting", [])[:3]:
                ref, squote = support.get("ref", ""), support.get("quote", "")
                if not DECISION_REF_RE.fullmatch(ref):
                    support_ok = False
                    drop(f"supporting ref malformed: {ref}")
                    break
                sbody = decision_bodies.get(ref)
                if sbody is None:
                    try:
                        sbody = norm(get_chunk(ref, REPO).get("text") or "")
                    except Exception:
                        sbody = None
                if not sbody:
                    support_ok = False
                    drop(f"supporting ref unresolvable: {ref}")
                    break
                if len(squote) < 25 or norm(squote) not in sbody:
                    support_ok = False
                    drop(f"supporting quote not grounded in {ref}")
                    break
                if ref in claimed:
                    # A decision may legitimately belong to two ADRs, but a swarm draft claiming an
                    # already-claimed decision is a collision risk - flag by dropping to review.
                    support_ok = False
                    drop(f"supporting ref already in an existing ADR's membership: {ref}")
                    break
                good_support.append({"ref": ref, "quote": squote})
            if not support_ok:
                continue
            topics = [t for t in item.get("topics", [])[:3]]
            if any(t not in canonical for t in topics):
                drop(f"non-canonical topic among {topics}")
                continue
            refs = item.get("constitution_refs", [])
            if not refs or not any(r.get("role") == "governing" for r in refs):
                drop("no governing constitution ref")
                continue
            bad_refs = [r for r in refs if r.get("ref") not in anchors or r.get("role") not in {"governing", "supporting"}]
            if bad_refs:
                drop(f"unresolvable/invalid constitution refs: {bad_refs}")
                continue
            seen_ids.add(adr_id)
            item["supporting"] = good_support
            item["_assigned"] = assigned[adr_id]
            survivors.append(item)

    (HERE / "validated.json").write_text(json.dumps({"survivors": survivors, "drops": drops}, indent=1), encoding="utf-8")
    print(f"survivors: {len(survivors)}  drops: {len(drops)}")
    for d in drops:
        print(f"  DROP {d['adr_id']:<36} {d['reason'][:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
