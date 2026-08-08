"""Write the surviving attachments as `revision-proposed` events on their ADRs.

Only picks that were grounded in a verbatim quote AND survived the refutation pass are written.
They are PROPOSED, never accepted: a machine-chosen head does not move an authority record without
JNL's acceptance, which is the standing rule these 17 are queued behind.

The concern statement itself does not change - what changes is what the concern rests on. So the
revision carries the ADR's existing derived Decision text forward verbatim, and the Why records
which session decision instituted it, with the quote that proves it and the refuter's confirmation.
Constitution bindings are carried forward from the founding event so no binding is lost.

Usage:  python experiments/adr-campaign/write_attachments.py [--commit]
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
    replay_adr,
    revise_adr,
)

UPDATE_ENTRY = "mse_kqna9hegj35dwsqj"
WHY_CAP, EVOLUTION_CAP = 700, 450


def norm(text: str) -> str:
    return " ".join(text.split())


def main() -> int:
    commit = "--commit" in sys.argv
    if "--reground" in sys.argv:
        # The replacement heads the refutation pass named, re-grounded on their own quotes.
        rows = json.loads((HERE / "reground-validated.json").read_text(encoding="utf-8"))
    else:
        rows = json.loads(
            (HERE / "attach-adjudicated.json").read_text(encoding="utf-8"))["stands"]
    print(f"attachments to propose: {len(rows)}\n")

    failed = 0
    for index, row in enumerate(rows):
        adr_id, ref = row["adr_id"], row["ref"]
        path = REPO / ".memory-seed" / "decisions" / f"{adr_id}.md"
        record = parse_adr(path)
        founding = next(
            (e for e in record.events
             if e.kind == "revision-proposed" and e.founding_source), None)
        if founding is None:
            print(f"  SKIP {adr_id}: no founding revision to carry forward")
            failed += 1
            continue

        decision = norm(founding.decision or record.title)
        why = norm(
            f'Rests on the session decision that instituted it: "{norm(row["quote"])}" '
            f'({ref}). {norm(row["why"])}'
        )[:WHY_CAP]
        evolution = norm(
            f"Founded from {founding.founding_source}; this revision moves the concern off that "
            f"control-file line onto {ref}, the decision that made it. Selected by semantic recall "
            f"over the concern text, grounded verbatim, and confirmed by an independent "
            f"refutation pass."
        )[:EVOLUTION_CAP]

        kwargs = dict(
            adr_id=adr_id,
            decision_ref=ref,
            decision=decision,
            why=why,
            evolution=evolution,
            update_entry_id=UPDATE_ENTRY,
            source="derived",
            predecessors=(),
            constitution_refs=tuple(
                ConstitutionRef(r.ref, r.role) for r in founding.constitution_refs),
            timestamp=f"2026-08-08T19:{index + (30 if '--reground' in sys.argv else 0):02d}:00Z",
        )
        dry = revise_adr(REPO, dry_run=True, **kwargs)
        print(f"  {'OK ' if dry.ok else 'REFUSED'} {adr_id:<36} -> {ref}")
        if not dry.ok:
            failed += 1
            for issue in dry.issues[:3]:
                print(f"        {issue}")
            continue
        if commit:
            real = revise_adr(REPO, **kwargs)
            if not real.ok:
                failed += 1
                print(f"        WRITE FAILED {real.issues[:3]}")

    if commit:
        ok, issues = check_adrs(REPO)
        print("\nadr check:", ok, issues[:4])
    print(f"\n{'written' if commit else 'dry-run'}: {len(rows) - failed} of {len(rows)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
