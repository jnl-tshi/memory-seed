"""Validate screening picks: closed-list refs, grounded quotes, real verdicts.

Same drop-never-repair contract as the drafting validator. Three checks, each of which caught a
real failure in this campaign:

1. **The ref must appear in that ADR's candidate list** in ATTACHMENT-REVIEW.md. Workers invent
   refs when asked to recall them; the closed list is the fix, and this is what enforces it.
2. **The quote must be a verbatim substring of the cited decision's BODY.** Quoting the decision's
   title instead of its body passes a naive substring check against the whole entry but proves
   nothing about the decision, so titles are excluded from the haystack.

   **Length is REPORTED, never a drop.** A 40-120 char window is good guidance - a failed quote
   typically matches its opening clause and drifts in the tail, which is what line wrapping does to
   a long transcription - but enforcing it as a gate is a formatting rule doing correctness work.
   It buried a valid `adr_entry_id_scheme` pick over 27 characters here, and the same anti-pattern
   buried 3 verbatim edges (141/141/38 chars) in the 2026-08-07 link swarm, where one entry was
   about to be marked "examined and found nothing to link" as a result. Grounding decides.
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

# Advisory window: quotes outside it are REPORTED, never dropped. See the module docstring.
SOFT_MIN, SOFT_MAX = 40, 120


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
    picks, drops, kept, outliers = [], [], [], []
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
            if not quote.strip():
                drop("no quote supplied")
                continue
            if norm(quote) not in body_only:
                where = "matches only the title" if title and norm(quote) in title else "not found"
                drop(f"quote {where} in the cited decision")
                continue
            # Grounded. Length is advisory - report the outlier, keep the pick.
            if not SOFT_MIN <= len(quote) <= SOFT_MAX:
                outliers.append({"adr_id": adr, "ref": ref, "chars": len(quote)})
            picks.append(item)
            kept.append(item)

    (HERE / "screening-validated.json").write_text(
        json.dumps({"picks": picks, "kept": kept, "drops": drops,
                    "length_outliers": outliers}, indent=1), encoding="utf-8"
    )
    none_n = sum(1 for k in kept if k["verdict"] == "none")
    print(f"screened: {len(kept) + len(drops)}")
    print(f"  grounded picks:   {len(picks)}")
    print(f"  honest 'none':    {none_n}")
    print(f"  dropped:          {len(drops)}")
    print(f"  length outliers (kept, reported): {len(outliers)}")
    for o in outliers:
        print(f"    OUTLIER {o['adr_id']:<32} {o['ref']:<24} {o['chars']} chars")
    for d in drops:
        print(f"    DROP {d['adr_id']:<32} {d['reason'][:88]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
