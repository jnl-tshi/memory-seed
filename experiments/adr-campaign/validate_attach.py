"""Validate attachment picks for the founding-only ADRs.

Same drop-never-repair contract as `validate_screening.py`, with the closed candidate list read
from `attach-payload.json` itself rather than re-parsed out of a report - the payload IS what the
worker was shown, so there is no second copy to drift.

Three checks:

1. **Closed list.** The ref must appear in that ADR's own candidate list. Workers invent
   identifiers they are asked to recall; a verified list rendered into the payload is the fix.
2. **Grounding.** The quote must be a verbatim substring of the cited decision's BODY. The title is
   excluded from the haystack because quoting the title passes a naive substring check while
   proving nothing about the decision - the single most common failure in this campaign.
   Length is REPORTED, never a drop. Grounding decides.
3. **Verdict** in {primary, supporting, none}; ref+quote required for the first two, forbidden for
   the third. `none` is a good answer here: these ADRs rest on control-file lines precisely because
   the deciding entry was not obvious.

Usage:  python experiments/adr-campaign/validate_attach.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from memory_seed.retrieval import get_chunk  # noqa: E402

# Advisory window: quotes outside it are REPORTED, never dropped.
SOFT_MIN, SOFT_MAX = 40, 160


def norm(text: str) -> str:
    return " ".join(text.split())


ROUNDS = {
    "v1": ("attach-payload.json", "attach-result-*.json"),
    "v2": ("attach-payload-v2.json", "attach-v2-result-*.json"),
}


def candidate_lists(payload_name: str) -> dict[str, set[str]]:
    payload = json.loads((HERE / payload_name).read_text(encoding="utf-8"))
    return {item["adr_id"]: {c["ref"] for c in item["candidates"]} for item in payload}


def main() -> int:
    round_name = sys.argv[1] if len(sys.argv) > 1 else "v2"
    payload_name, result_glob = ROUNDS[round_name]
    offered = candidate_lists(payload_name)
    picks, drops, kept, outliers = [], [], [], []
    seen: set[str] = set()
    for path in sorted(HERE.glob(result_glob)):
        for item in json.loads(path.read_text(encoding="utf-8")):
            adr, verdict = item.get("adr_id", "?"), item.get("verdict", "")
            ref, quote = item.get("ref", "") or "", item.get("quote", "") or ""
            item["batch"] = path.name
            seen.add(adr)

            def drop(reason: str) -> None:
                drops.append({"adr_id": adr, "ref": ref, "reason": reason, "batch": path.name})

            if adr not in offered:
                drop("ADR not in the attachment payload")
                continue
            if verdict not in {"primary", "supporting", "none"}:
                drop(f"bad verdict {verdict!r}")
                continue
            if verdict == "none":
                if ref or quote:
                    drop("verdict none must carry no ref or quote")
                    continue
                kept.append(item)
                continue
            if ref not in offered[adr]:
                drop(f"ref not in that ADR's candidate list (offered: {sorted(offered[adr])})")
                continue
            try:
                chunk = get_chunk(ref, REPO)
            except Exception as exc:
                drop(f"ref does not resolve: {exc}")
                continue
            title = norm(chunk.get("title") or "")
            body = norm(chunk.get("text") or "")
            body_only = body.replace(title, " ") if title else body
            if not quote.strip():
                drop("no quote supplied")
                continue
            if norm(quote) not in body_only:
                where = "matches only the title" if title and norm(quote) in title else "not found"
                drop(f"quote {where} in the cited decision")
                continue
            if not SOFT_MIN <= len(quote) <= SOFT_MAX:
                outliers.append({"adr_id": adr, "ref": ref, "chars": len(quote)})
            picks.append(item)
            kept.append(item)

    missing = sorted(set(offered) - seen)
    (HERE / "attach-validated.json").write_text(
        json.dumps({"picks": picks, "kept": kept, "drops": drops,
                    "length_outliers": outliers, "unanswered": missing}, indent=1),
        encoding="utf-8",
    )
    primary = [k for k in kept if k["verdict"] == "primary"]
    supporting = [k for k in kept if k["verdict"] == "supporting"]
    none_n = sum(1 for k in kept if k["verdict"] == "none")
    print(f"answered: {len(kept) + len(drops)} of {len(offered)} ADRs")
    print(f"  grounded primary:    {len(primary)}")
    print(f"  grounded supporting: {len(supporting)}")
    print(f"  honest 'none':       {none_n}")
    print(f"  dropped:             {len(drops)}")
    print(f"  length outliers (kept, reported): {len(outliers)}")
    for o in outliers:
        print(f"    OUTLIER {o['adr_id']:<34} {o['ref']:<24} {o['chars']} chars")
    for d in drops:
        print(f"    DROP {d['adr_id']:<34} {d['reason'][:90]}")
    if missing:
        print(f"  unanswered ADRs: {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
