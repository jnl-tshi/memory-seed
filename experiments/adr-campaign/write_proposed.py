"""Phase-5: write validator-surviving drafts as `proposed` ADRs. Sequential, dry-run first.

Every campaign ADR is FOUNDED from its control-file line (JNL's decision 6: the index/policy line
is an acceptable founding source), with the worker's session-decision finds attached as
supporting_decisions. `source: derived` throughout - this is reconstruction, Constitution 1.6.
Timestamps are pinned per record so dry-run and commit render identical bytes.

Rejected-status concerns (decided-and-rejected history) are promoted then transitioned to
`rejected` - the record of why not.

Usage:
  python experiments/adr-campaign/write_proposed.py [--commit]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from memory_seed.adr import ConstitutionRef, check_adrs, promote_decision, transition_adr  # noqa: E402

BASE_TS = "2026-08-06T17:{m:02d}:00Z"


def main() -> int:
    commit = "--commit" in sys.argv
    data = json.loads((HERE / "validated.json").read_text(encoding="utf-8"))
    written, failed = [], []
    for i, item in enumerate(data["survivors"]):
        assigned = item["_assigned"]
        stamp = BASE_TS.format(m=i % 60)
        # Found on the source the worker actually quoted, not merely the first assigned one -
        # several concerns cite both index.md and policy.md, and the founding line must be the
        # one the grounding quote came from.
        founding = next(
            (s for s in assigned["sources"] if s.split("#")[0] == item["source_file"]),
            assigned["sources"][0],
        )
        refs = tuple(ConstitutionRef(r["ref"], r["role"]) for r in item["constitution_refs"])
        kwargs = dict(
            adr_id=item["adr_id"], title=item["title"],
            topics=tuple(item.get("topics", [])),
            user_initials="JNL", agent_type="claude", source="derived",
            decision=item["decision"], why=item["why"], evolution=item["evolution"],
            supporting_decisions=tuple(s["ref"] for s in item.get("supporting", [])),
            constitution_refs=refs,
            founding_source=founding,
            founding_quote=item["source_quote"],
            timestamp=stamp,
        )
        dry = promote_decision(REPO, dry_run=True, **kwargs)
        if not dry.ok:
            failed.append((item["adr_id"], dry.issues))
            print(f"REFUSED {item['adr_id']}: {dry.issues[:2]}")
            continue
        if commit:
            real = promote_decision(REPO, **kwargs)
            if not real.ok:
                failed.append((item["adr_id"], real.issues))
                continue
            if assigned.get("status") == "rejected":
                stamp2 = stamp.replace("T17:", "T18:")
                # Founding transitions carry no update_entry_id: the campaign's session entry does
                # not exist yet at write time, and manufacturing one would be false provenance.
                rej = transition_adr(
                    REPO, adr_id=item["adr_id"], status="rejected",
                    update_entry_id=None,  # type: ignore[arg-type] - validated as founding
                    source="derived", reason=item["why"][:300], timestamp=stamp2,
                )
                if not rej.ok:
                    failed.append((item["adr_id"], rej.issues))
                    continue
        written.append(item["adr_id"])
    print(f"\n{'written' if commit else 'dry-run ok'}: {len(written)}  refused: {len(failed)}")
    if commit:
        ok, issues = check_adrs(REPO)
        print("adr check:", ok, issues[:5])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
