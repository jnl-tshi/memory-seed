"""Validate screening picks: closed-list refs, grounded quotes, real verdicts.

Same drop-never-repair contract as the drafting validator. Three checks, each of which caught a
real failure in this campaign:

1. **The ref must appear in that ADR's candidate list** in ATTACHMENT-REVIEW.md. Workers invent
   refs when asked to recall them; the closed list is the fix, and this is what enforces it.
2. **The quote must be >=40 chars and a verbatim substring of the cited decision's BODY.** Quoting
   the decision's title instead of its body passes a naive substring check against the whole entry
   but proves nothing about the decision, so titles are excluded from the haystack.
3. **verdict in {primary, supporting, none}**, with ref+quote required for the first two and
   forbidden for the third.

Usage:  python experiments/adr-campaign/validate_screening.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from memory_seed.retrieval import get_chunk  # noqa: E402

MIN_QUOTE = 40


def norm(text: str) -> str:
    return " ".join(text.split())


def candidate_lists() -> dict[str, set[str]]:
    """adr_id -> the refs offered to the worker."""
    out: dict[str, set[str]] = {}
    current = None
    for line in (HERE / "ATTACHMENT-REVIEW.md").read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^## (adr_\S+)", line)
        if heading:
            current = heading.group(1)
            out[current] = set()
            continue
        ref = re.match(r"^- `([^`]+)` \(\d+ shared", line)
        if ref and current:
            out[current].add(ref.group(1))
    return out


def main() -> int:
    offered = candidate_lists()
    picks, drops, kept = [], [], []
    for path in sorted(HERE.glob("screen-*.json")):
        for item in json.loads(path.read_text(encoding="utf-8")):
            adr, verdict = item.get("adr_id", "?"), item.get("verdict", "")
            ref, quote = item.get("ref", ""), item.get("quote", "")

            def drop(reason: str) -> None:
                drops.append({"adr_id": adr, "ref": ref, "reason": reason, "batch": path.name})

            if verdict not in {"primary", "supporting", "none"}:
                drop(f"bad verdict {verdict!r}")
                continue
            if verdict == "none":
                if ref or quote:
                    drop("verdict none must carry no ref or quote")
                    continue
                kept.append(item)
                continue
            if adr not in offered:
                drop("ADR not in the attachment review")
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
            # A title quote proves nothing about the decision - exclude it from the haystack.
            body_only = body.replace(title, " ") if title else body
            if len(quote) < MIN_QUOTE:
                drop(f"quote is {len(quote)} chars, under the {MIN_QUOTE} minimum")
                continue
            if norm(quote) not in body_only:
                where = "matches only the title" if title and norm(quote) in title else "not found"
                drop(f"quote {where} in the cited decision")
                continue
            picks.append(item)
            kept.append(item)

    (HERE / "screening-validated.json").write_text(
        json.dumps({"picks": picks, "kept": kept, "drops": drops}, indent=1), encoding="utf-8"
    )
    none_n = sum(1 for k in kept if k["verdict"] == "none")
    print(f"screened: {len(kept) + len(drops)}")
    print(f"  grounded picks:   {len(picks)}")
    print(f"  honest 'none':    {none_n}")
    print(f"  dropped:          {len(drops)}")
    for d in drops:
        print(f"    DROP {d['adr_id']:<32} {d['reason'][:88]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
