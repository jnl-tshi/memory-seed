"""Replace each pending revision's wording with the synthesis of its live chain.

Two events per ADR, in this order:

1. `revision-rejected` on the current pending ref - retires the wording, not the decision. The
   Reason says which, so the ledger does not read as "this decision was thrown out".
2. `revision-proposed` on the SAME ref, carrying the synthesised Decision/Why/Evolution. This is
   what the 2026-08-08 contract change unlocked; before it, a rejected ref stayed closed forever
   and a summary written from bad evidence could never be corrected.

The new proposal re-declares `supporting_decisions` as the live members other than the head, so the
record itself says what its summary was synthesised from. Constitution bindings are carried forward
from the event being replaced, so no binding is lost in the swap.

Acceptance is NOT done here. These stay proposed until JNL accepts them.

Usage:  python experiments/adr-campaign/write_synthesis.py [--commit]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from memory_seed.adr import (  # noqa: E402
    ConstitutionRef,
    check_adrs,
    parse_adr,
    proposal_for,
    replay_adr,
    revise_adr,
    transition_adr,
)

UPDATE_ENTRY = "REPLACE_ME"
REJECT_REASON = (
    "Wording retired, not the decision: this summary was written from the head alone (or, for a "
    "founded concern, from the control-file line) rather than synthesised from every live chain "
    "member. Re-proposed on the same decision with that synthesis."
)


def norm(text: str) -> str:
    return " ".join((text or "").split())


def main() -> int:
    commit = "--commit" in sys.argv
    chains = {c["adr_id"]: c for c in
              json.loads((HERE / "live-chain.json").read_text(encoding="utf-8"))}
    approved = json.loads((HERE / "synthesis-approved.json").read_text(encoding="utf-8"))
    print(f"summaries to replace: {len(approved)}\n")

    failed = 0
    for index, item in enumerate(approved):
        adr_id = item["adr_id"]
        chain = chains[adr_id]
        ref = chain["head"]
        record = parse_adr(REPO / ".memory-seed" / "decisions" / f"{adr_id}.md")
        state = replay_adr(record)
        if ref not in state.pending_decisions:
            print(f"  SKIP {adr_id}: {ref} is not pending (state moved under us)")
            failed += 1
            continue
        old = proposal_for(record, ref)
        supporting = tuple(m["ref"] for m in chain["live_chain"] if m["ref"] != ref)
        bindings = tuple(ConstitutionRef(r.ref, r.role) for r in (old.constitution_refs if old else ()))

        reject = dict(
            adr_id=adr_id, status="rejected", decision_ref=ref, update_entry_id=UPDATE_ENTRY,
            source="derived", reason=REJECT_REASON,
            timestamp=f"2026-08-08T22:{index:02d}:00Z",
        )
        propose = dict(
            adr_id=adr_id, decision_ref=ref, decision=norm(item["decision"]),
            why=norm(item["why"]), evolution=norm(item["evolution"]),
            update_entry_id=UPDATE_ENTRY, source="derived", predecessors=(),
            supporting_decisions=supporting, constitution_refs=bindings,
            timestamp=f"2026-08-08T22:{index:02d}:30Z",
        )

        dry = transition_adr(REPO, dry_run=True, **reject)
        print(f"  {'OK ' if dry.ok else 'REFUSED'} reject  {adr_id:<38} {ref}")
        if not dry.ok:
            failed += 1
            for issue in dry.issues[:3]:
                print(f"        {issue}")
            continue
        if not commit:
            # The re-proposal cannot be dry-run against an unwritten rejection - the ref is still
            # live, so validation would (correctly) call it a duplicate. Report and move on.
            print(f"      propose {adr_id:<38} +{len(supporting)} supporting (checked on commit)")
            continue

        real = transition_adr(REPO, **reject)
        if not real.ok:
            failed += 1
            print(f"        REJECT FAILED {real.issues[:3]}")
            continue
        written = revise_adr(REPO, **propose)
        print(f"  {'OK ' if written.ok else 'REFUSED'} propose {adr_id:<38} +{len(supporting)} supporting")
        if not written.ok:
            failed += 1
            for issue in written.issues[:3]:
                print(f"        {issue}")

    if commit:
        ok, issues = check_adrs(REPO)
        print("\nadr check:", ok, issues[:4])
    print(f"\n{'written' if commit else 'dry-run'}: {len(approved) - failed} of {len(approved)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
