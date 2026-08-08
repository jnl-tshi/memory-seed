"""Join each synthesised summary to its completeness verdict and report what is ready.

Three outcomes, which map onto the approval gates:

- **complete** - both passes agree the summary accounts for the whole live chain. Ready to write
  and put to JNL as a batch.
- **incomplete** - the checker named live members the summary drops or contradicts. The concern is
  fine and the summary is not, so it goes back for one more synthesis round rather than being
  declined.
- **unjudged** - no verdict came back. Reported, never silently treated as passing.

The known-positive control matters here: `adr_documentation_lane_structure` heads on a decision
that refreshed a doc's "As of" date, so a pass that calls its ORIGINAL summary complete is broken.
That control is on the original wording, not the re-synthesis, so it is checked separately.

Usage:  python experiments/adr-campaign/adjudicate_synthesis.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    chains = {c["adr_id"]: c for c in
              json.loads((HERE / "live-chain.json").read_text(encoding="utf-8"))}
    validated = json.loads((HERE / "synthesis-validated.json").read_text(encoding="utf-8"))
    summaries = {item["adr_id"]: item for item in validated["kept"]}

    verdicts = {}
    for path in sorted(HERE.glob("complete-result-*.json")):
        for item in json.loads(path.read_text(encoding="utf-8")):
            verdicts[item["adr_id"]] = item

    ready, resend, unjudged = [], [], []
    for adr_id, summary in summaries.items():
        verdict = verdicts.get(adr_id)
        if not verdict:
            unjudged.append(adr_id)
            continue
        row = dict(summary)
        row["checker"] = verdict.get("reason", "")
        if verdict.get("verdict") == "complete":
            ready.append(row)
        else:
            row["missing"] = verdict.get("missing") or []
            row["contradicted"] = verdict.get("contradicted") or []
            resend.append(row)

    dropped = validated["drops"]
    report = {"ready": ready, "resend": resend, "unjudged": unjudged, "dropped": dropped}
    (HERE / "synthesis-adjudicated.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"{len(chains)} pending ADRs")
    print(f"  ready to propose:      {len(ready)}")
    print(f"  send back (incomplete):{len(resend)}")
    print(f"  unjudged:              {len(unjudged)}")
    print(f"  dropped at validation: {len(dropped)}")

    # Separate axis, reported alongside rather than folded in: the head is the ANCHOR now, not the
    # summary, so a head that is not the newest live member is a question for JNL rather than a
    # defect in the synthesis. An ADR can be complete and still be anchored oddly.
    anchor = sorted(c["adr_id"] for c in chains.values()
                    if c["live_chain"] and not c["head_is_newest_live"])
    ready_ids = {r["adr_id"] for r in ready}
    print(f"  head is not the newest live member: {len(anchor)}"
          f"  ({sum(1 for a in anchor if a in ready_ids)} of them otherwise ready)")
    for adr_id in anchor:
        print(f"    ANCHOR {adr_id}")
    for row in resend:
        gaps = ", ".join(row["missing"] + row["contradicted"]) or "no refs named"
        print(f"    RESEND {row['adr_id']:<38} {gaps}")
    for adr_id in unjudged:
        print(f"    UNJUDGED {adr_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
