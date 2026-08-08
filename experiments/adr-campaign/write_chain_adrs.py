"""Validate the chain-founding drafts and write the survivors as `proposed` ADRs.

Grounding decides, length never does - the rule that cost three real edges in the 2026-08-07 link
swarm when a 40-120 window was enforced as a gate. Quotes outside the advisory window are reported
and kept; a quote that is not a verbatim span of the decision it cites is dropped.

Every ref must be copied from the chain's own member list. Workers invent identifiers they are
asked to recall, so the closed list is the fix and this is what enforces it.

Usage:  python experiments/adr-campaign/write_chain_adrs.py [--commit]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from memory_seed.adr import (  # noqa: E402
    ADR_ID_RE,
    ConstitutionRef,
    _constitution_anchors,
    check_adrs,
    iter_adrs,
    promote_decision,
)
from memory_seed.retrieval import get_chunk  # noqa: E402
from memory_seed.topics import load_topic_index  # noqa: E402

SOFT_MIN, SOFT_MAX = 40, 160
CAPS = {"title": 130, "decision": 700, "why": 700, "evolution": 450}


def norm(text: str) -> str:
    return " ".join(text.split())


def main() -> int:
    commit = "--commit" in sys.argv
    chains = {}
    for source in ("found-payload.json", "pair-payload.json"):
        path = HERE / source
        if path.exists():
            chains.update({c["suggested_head"]: c for c in
                           json.loads(path.read_text(encoding="utf-8"))})
    anchors = _constitution_anchors(REPO)
    canonical = {v for v in load_topic_index(REPO).resolution().values()}
    existing = {r.adr_id for r in iter_adrs(REPO)}

    survivors, drops, outliers = [], [], []
    seen_ids: set[str] = set()
    for path in sorted(HERE.glob("chain-draft-*.json")):
        for item in json.loads(path.read_text(encoding="utf-8")):
            adr_id, head = item.get("adr_id", "?"), item.get("head", "")

            def drop(reason: str) -> None:
                drops.append({"adr_id": adr_id, "reason": reason, "batch": path.name})

            chain = chains.get(head)
            if chain is None:
                drop(f"head {head!r} is not a chain head we asked about")
                continue
            legal = {m["ref"] for m in chain["members"]}
            if not ADR_ID_RE.fullmatch(adr_id) or adr_id in existing or adr_id in seen_ids:
                drop("adr_id malformed, colliding, or duplicated across workers")
                continue
            over = [k for k, cap in CAPS.items() if len(item.get(k, "")) > cap]
            if over:
                drop(f"over length cap: {over}")
                continue
            if not item.get("decision", "").strip() or not item.get("why", "").strip():
                drop("empty decision or why")
                continue
            topics = list(item.get("topics") or [])[:3]
            if any(t not in canonical for t in topics):
                drop(f"non-canonical topic among {topics}")
                continue
            refs = item.get("constitution_refs") or []
            if not any(r.get("role") == "governing" for r in refs):
                drop("no governing constitution ref")
                continue
            bad = [r for r in refs if r.get("ref") not in anchors
                   or r.get("role") not in {"governing", "supporting"}]
            if bad:
                drop(f"unresolvable or invalid constitution refs: {bad}")
                continue
            quote, quote_ref = item.get("quote", ""), item.get("quote_ref", "")
            if quote_ref not in legal:
                drop(f"quote_ref {quote_ref!r} is not a member of this chain")
                continue
            try:
                body = norm(get_chunk(quote_ref, REPO).get("text") or "")
            except Exception as exc:
                drop(f"quote_ref does not resolve: {exc}")
                continue
            if not quote.strip() or norm(quote) not in body:
                drop("quote is not a verbatim span of the decision it cites")
                continue
            # Grounded. Length is advisory - report, never drop.
            if not SOFT_MIN <= len(quote) <= SOFT_MAX:
                outliers.append({"adr_id": adr_id, "chars": len(quote)})
            seen_ids.add(adr_id)
            item["_chain"] = chain
            item["topics"] = topics
            survivors.append(item)

    print(f"drafted: {len(survivors) + len(drops)} | grounded: {len(survivors)} | dropped: {len(drops)}")
    for o in outliers:
        print(f"  OUTLIER (kept) {o['adr_id']:<40} quote {o['chars']} chars")
    for d in drops:
        print(f"  DROP {d['adr_id']:<40} {d['reason'][:80]}")

    failed = 0
    for i, item in enumerate(survivors):
        chain = item["_chain"]
        head = item["head"]
        supporting = tuple(m["ref"] for m in chain["members"] if m["ref"] != head)
        entry, ordinal = head.split(":")
        kwargs = dict(
            adr_id=item["adr_id"], source_entry_id=entry, source_decision=ordinal,
            title=item["title"], topics=tuple(item["topics"]),
            user_initials="JNL", agent_type="claude", source="derived",
            decision=item["decision"], why=item["why"], evolution=item["evolution"],
            supporting_decisions=supporting,
            constitution_refs=tuple(
                ConstitutionRef(r["ref"], r["role"]) for r in item["constitution_refs"]
            ),
            timestamp=f"2026-08-08T03:{i:02d}:00Z",
        )
        dry = promote_decision(REPO, dry_run=True, **kwargs)
        status = "OK " if dry.ok else "REFUSED"
        print(f"  {status} {item['adr_id']:<44} head={head} +{len(supporting)}")
        if not dry.ok:
            failed += 1
            for issue in dry.issues[:2]:
                print(f"        {issue}")
            continue
        if commit:
            real = promote_decision(REPO, **kwargs)
            if not real.ok:
                failed += 1
                print(f"        WRITE FAILED {real.issues[:2]}")
    if commit:
        ok, issues = check_adrs(REPO)
        print("adr check:", ok, issues[:4])
    print(f"\n{'written' if commit else 'dry-run'}: {len(survivors) - failed} of {len(survivors)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
