"""List every ADR revision proposed but not yet accepted, with what it would move.

`adr list` shows each concern's ACCEPTED head, so a proposal is invisible there until someone
accepts it. The ADR file shows its own pending set under `### Awaiting review`, but that is one
file at a time. This is the corpus-wide view: what is queued, and what accepting it would change.

Usage:  python experiments/adr-campaign/list_pending.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from memory_seed.adr import iter_adrs, proposal_for, replay_adr  # noqa: E402


def gist(text: str, cap: int = 88) -> str:
    sentence = " ".join(text.split()).split(". ")[0]
    return sentence if len(sentence) <= cap else sentence[: cap - 1] + "…"


def main() -> int:
    founding, fresh = [], []
    for record in sorted(iter_adrs(REPO), key=lambda r: r.adr_id):
        state = replay_adr(record)
        head = state.authoritative_decision
        for ref in state.pending_decisions:
            proposal = proposal_for(record, ref)
            row = (record.adr_id, ref, head or "", gist(proposal.decision if proposal else ""))
            (founding if head and head.startswith("founding:") else fresh).append(row)

    print(f"{len(founding) + len(fresh)} revisions awaiting acceptance\n")
    print(f"-- {len(founding)} would move a concern off its control-file line --")
    for adr_id, ref, head, text in founding:
        print(f"  {adr_id:<38} {ref:<26} was {head[len('founding:'):]}")
        print(f"      {text}")
    print(f"\n-- {len(fresh)} are ADRs with no accepted head yet --")
    for adr_id, ref, _, text in fresh:
        print(f"  {adr_id:<38} {ref}")
        print(f"      {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
