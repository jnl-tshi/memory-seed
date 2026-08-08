"""Apply JNL's gate verdicts: replace each summary with its live-chain synthesis, then accept.

Three events per ADR, in order:

1. `revision-rejected` on the pending ref - retires the WORDING, not the decision. The Reason says
   which, so the ledger does not read as "this decision was thrown out".
2. `revision-proposed` carrying the synthesised Decision/Why/Evolution, with `supporting_decisions`
   re-declared as the live members other than the head, so the record says what it was synthesised
   from. Constitution bindings are carried forward from the event being replaced.
3. `revision-accepted`, which is the act JNL gated on.

**Gate A** keys the new proposal on the same decision the old one used - that decision is already
the newest live member of its chain.

**Gate B** keys it on the chain's NEWEST live member instead. Those five were anchored on an older
decision while a later one in the same chain had already moved the concern past it. JNL's rule:
when the most recent authoritative decision that evolves an ADR shifts, the summary regenerates.
Here both halves happen at once - the anchor moves and the regenerated summary lands with it.

Gates C and D are not touched. They stay pending with their reasons recorded in PENDING-REVIEW.md.

Usage:  python experiments/adr-campaign/apply_gates.py [--commit]
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

UPDATE_ENTRY = "mse_rfw60ctv535cbseq"

REJECT_SAME = (
    "Wording retired, not the decision. This summary restated a single decision (or, for a founded "
    "concern, the control-file line) instead of synthesising every live member of the chain. "
    "Re-proposed on the same decision with that synthesis."
)
REJECT_REANCHOR = (
    "Wording retired and the anchor moved. This revision rested on {old}, but {new} is a later "
    "decision in the same chain that had already moved the concern past it. A shift in the most "
    "recent authoritative decision triggers a regenerated summary, so both land together."
)


def norm(text: str) -> str:
    return " ".join((text or "").split())


def main() -> int:
    commit = "--commit" in sys.argv
    gates = json.loads((HERE / "gates.json").read_text(encoding="utf-8"))
    chains = {c["adr_id"]: c for c in
              json.loads((HERE / "live-chain.json").read_text(encoding="utf-8"))}
    adj = json.loads((HERE / "synthesis-adjudicated.json").read_text(encoding="utf-8"))
    summaries = {s["adr_id"]: s for s in adj["ready"]}

    plan = [(a, "A") for a in gates["A"]] + [(a, "B") for a in gates["B"]]
    print(f"ADRs to re-summarise and accept: {len(plan)}  "
          f"(Gate A {len(gates['A'])}, Gate B {len(gates['B'])})\n")

    failed = 0
    for index, (adr_id, gate) in enumerate(plan):
        chain, summary = chains[adr_id], summaries.get(adr_id)
        if summary is None:
            print(f"  SKIP {adr_id}: no accepted synthesis")
            failed += 1
            continue
        record = parse_adr(REPO / ".memory-seed" / "decisions" / f"{adr_id}.md")
        state = replay_adr(record)
        old_ref = chain["head"]
        new_ref = chain["live_chain"][-1]["ref"] if gate == "B" else old_ref
        if old_ref not in state.pending_decisions:
            print(f"  SKIP {adr_id}: {old_ref} is not pending")
            failed += 1
            continue
        old = proposal_for(record, old_ref)
        supporting = tuple(m["ref"] for m in chain["live_chain"] if m["ref"] != new_ref)
        bindings = tuple(ConstitutionRef(r.ref, r.role)
                         for r in (old.constitution_refs if old else ()))
        authoritative = state.authoritative_decision
        stamp = lambda s: f"2026-08-08T23:{index:02d}:{s:02d}Z"  # noqa: E731 - ascending per ADR

        steps = [
            ("reject", transition_adr, dict(
                adr_id=adr_id, status="rejected", decision_ref=old_ref,
                update_entry_id=UPDATE_ENTRY, source="derived",
                reason=(REJECT_SAME if gate == "A"
                        else REJECT_REANCHOR.format(old=old_ref, new=new_ref)),
                timestamp=stamp(0))),
            ("propose", revise_adr, dict(
                adr_id=adr_id, decision_ref=new_ref, decision=norm(summary["decision"]),
                why=norm(summary["why"]), evolution=norm(summary["evolution"]),
                update_entry_id=UPDATE_ENTRY, source="derived", predecessors=(),
                supporting_decisions=supporting, constitution_refs=bindings,
                timestamp=stamp(20))),
            ("accept", transition_adr, dict(
                adr_id=adr_id, status="accepted", decision_ref=new_ref,
                update_entry_id=UPDATE_ENTRY, source="derived",
                expected_authoritative_decision=authoritative,
                timestamp=stamp(40))),
        ]

        move = f"{old_ref} -> {new_ref}" if gate == "B" else new_ref
        if not commit:
            # Only the first step can be dry-run in isolation; the next two depend on it landing.
            dry = steps[0][1](REPO, dry_run=True, **steps[0][2])
            print(f"  {'OK ' if dry.ok else 'REFUSED'} [{gate}] {adr_id:<38} {move}")
            if not dry.ok:
                failed += 1
                for issue in dry.issues[:3]:
                    print(f"        {issue}")
            continue

        ok = True
        for name, fn, kwargs in steps:
            result = fn(REPO, **kwargs)
            if not result.ok:
                ok = False
                failed += 1
                print(f"  FAILED [{gate}] {adr_id} at {name}: {result.issues[:3]}")
                break
        if ok:
            print(f"  OK  [{gate}] {adr_id:<38} {move}  +{len(supporting)} supporting")

    if commit:
        good, issues = check_adrs(REPO)
        print("\nadr check:", good, issues[:4])
    print(f"\n{'applied' if commit else 'dry-run'}: {len(plan) - failed} of {len(plan)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
