"""Write the lineage map into the ADR ledgers as `revision-proposed` events.

Reads `lineage-map.json` (produced by `lineage_map.py`) and, for each UNPINNED ADR:

- **Head moved** - proposes the current decision as the new head, with the member it descends from
  recorded as a predecessor carrying its `link:<head>:<kind>:<member>` assertion.
- **Related decisions found** - proposes the member that carries the related edge as the head and
  records the related refs as `supporting_decisions`. Per the ADR contract, related references
  "provide context but never trigger lineage semantics", so they are never predecessors.

Both cases also converge the ADR off its `founding:` placeholder onto a real decision, which is
what founding sources were built to allow.

**Nothing is applied without being named.** An ADR is only written when its id is passed to
--approve. A batch mode existed briefly and was removed: applying the map wholesale moved
`adr_subproject_scoping` onto a decision about skill triggers, via a 0.75-scored machine edge.
Read `LINEAGE-REVIEW.md`, check both titles, then name the ADRs you accept.

Everything lands `proposed`. A head change is a lineage-linked evolution, which the contract
reserves for mandatory review.

Usage:  python experiments/adr-campaign/reconcile_lineage.py --approve adr_x [adr_y ...] [--commit]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from memory_seed.adr import AdrPredecessor, check_adrs, revise_adr  # noqa: E402

UPDATE_ENTRY = "mse_ex5216t2hn30s5wx"  # the published session entry recording this pass
BASE_TS = "2026-08-07T01:{m:02d}:00Z"


def plan_rows(rows: list[dict], approved: set[str]) -> list[dict]:
    plans = []
    for row in rows:
        if row["pinned"] or row["adr_id"] not in approved:
            continue
        moved = [w for w in row["walks"] if w["path"]]
        related = row["related_refs"]
        if len(moved) == 1:
            walk = moved[0]
            step = walk["path"][-1]
            chain = " -> ".join(f"{s['kind']} {s['to']}" for s in walk["path"])
            plans.append({
                "adr_id": row["adr_id"],
                "head": walk["head"],
                "predecessors": [(step["from"], step["kind"])],
                "supporting": related,
                "evolution": (
                    f"Re-anchored from the control-file founding onto the current decision by "
                    f"walking link-sidecar lineage: {walk['seed']} -> {chain}."
                ),
                "why": (
                    "The decision this concern was founded on has been carried forward by a "
                    "recorded lifecycle edge, so the ADR's head follows it rather than remaining "
                    "on the control-file placeholder."
                ),
            })
        elif related and not moved:
            # No lineage movement, but related context exists. Anchor on the member that CARRIES
            # the related edge - mechanical, not a judgement call between members.
            carrier = next(
                (w["seed"] for w in row["walks"] if w["related"]), row["members"][0] if row["members"] else None
            )
            if not carrier:
                continue
            plans.append({
                "adr_id": row["adr_id"],
                "head": carrier,
                "predecessors": [],
                "supporting": related,
                "evolution": (
                    "Re-anchored from the control-file founding onto its session decision; "
                    f"related decisions recorded as context: {', '.join(related)}."
                ),
                "why": (
                    "No lifecycle edge has carried this decision forward, so it remains current. "
                    "Related decisions are recorded as supporting context only - the contract "
                    "keeps related references out of lineage semantics."
                ),
            })
    return plans


def main() -> int:
    commit = "--commit" in sys.argv
    argv = sys.argv[1:]
    approved: set[str] = set()
    if "--approve" in argv:
        for token in argv[argv.index("--approve") + 1:]:
            if token.startswith("--"):
                break
            approved.add(token)
    if not approved:
        print("Nothing named. Read LINEAGE-REVIEW.md, then pass --approve <adr_id> [...].")
        return 0
    rows = json.loads((HERE / "lineage-map.json").read_text(encoding="utf-8"))["adrs"]
    plans = plan_rows(rows, approved)
    unknown = approved - {r["adr_id"] for r in rows}
    if unknown:
        print(f"not in the map (nothing to apply): {sorted(unknown)}")
    print(f"planned revisions: {len(plans)}")
    failed = 0
    for i, plan in enumerate(plans):
        preds = tuple(
            AdrPredecessor(ref, f"link:{plan['head']}:{kind}:{ref}")
            for ref, kind in plan["predecessors"]
        )
        kwargs = dict(
            adr_id=plan["adr_id"], decision_ref=plan["head"],
            decision=(
                f"Current authoritative decision for this concern: `{plan['head']}`. "
                "See the source decision for its full statement."
            ),
            why=plan["why"], evolution=plan["evolution"],
            update_entry_id=UPDATE_ENTRY, source="derived",
            predecessors=preds, supporting_decisions=tuple(plan["supporting"]),
            timestamp=BASE_TS.format(m=i % 60),
        )
        dry = revise_adr(REPO, dry_run=True, **kwargs)
        status = "OK " if dry.ok else "REFUSED"
        print(f"  {status} {plan['adr_id']:<34} head={plan['head']} "
              f"preds={[p.decision for p in preds]} supporting={plan['supporting']}")
        if not dry.ok:
            failed += 1
            for issue in dry.issues[:3]:
                print(f"        {issue}")
            continue
        if commit:
            real = revise_adr(REPO, **kwargs)
            if not real.ok:
                failed += 1
                print(f"        WRITE FAILED {real.issues[:2]}")
    if commit:
        ok, issues = check_adrs(REPO)
        print("adr check:", ok, issues[:4])
    print(f"\n{'written' if commit else 'dry-run'}: {len(plans) - failed} of {len(plans)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
