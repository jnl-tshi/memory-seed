"""Render the human review document for the pending-ADR gates.

Everything JNL needs to give a verdict, in one readable file: the proposed wording for the batch
that is ready, and a plain-language account of each ADR that is held back and why.

Usage:  python experiments/adr-campaign/build_review_doc.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "PENDING-REVIEW.md"

PLAIN_C = {
    "adr_agent_config_merge": (
        "**The decision this concern rests on has been retired.** Its one decision, `ms-7c4e1f9a:d1`, "
        "was later replaced by `ms-6a09aea8:d1`. So the ADR points at something the corpus has "
        "already superseded, and there is nothing live left to write a summary from - the synthesis "
        "worker produced one anyway, from the title alone, which is why the validator dropped it. "
        "It needs a new decision to rest on before it needs a summary."
    ),
    "adr_hook_merge_framework": (
        "**It shares the retired decision above.** `ms-7c4e1f9a:d1` is one of its four members, so it "
        "is down to three live ones. Its summary passed both checks on those three. The reason it is "
        "held is that whatever you decide about `adr_agent_config_merge` - re-head it, fold it, or "
        "drop it - changes what this one should say, so judging them apart risks two answers that "
        "contradict each other."
    ),
    "adr_branch_session_fuse": (
        "**Two problems at once.** First, the decision it proposes to rest on, "
        "`mse_9c151e4gbkkv1w5v:d1`, is already part of an ADR you have accepted - "
        "`adr_merge_branch_primitive`. Both concern `session merge-branch`, so this may be one "
        "concern recorded twice, which is exactly the pattern that produced the encoding-policy "
        "duplicate earlier today. Second, its summary was judged incomplete: it does not carry the "
        "diagram-sidecar validation point or the open design questions the decision itself records."
    ),
}


def main() -> int:
    gates = json.loads((HERE / "gates.json").read_text(encoding="utf-8"))
    chains = {c["adr_id"]: c for c in
              json.loads((HERE / "live-chain.json").read_text(encoding="utf-8"))}
    adj = json.loads((HERE / "synthesis-adjudicated.json").read_text(encoding="utf-8"))
    summaries = {s["adr_id"]: s for s in adj["ready"] + adj["resend"]}
    checker = {s["adr_id"]: s for s in adj["resend"]}

    lines: list[str] = []
    add = lines.append

    add("# Pending ADR revisions - review\n")
    add("38 revisions are proposed and unaccepted. Every summary below was rewritten from the ADR's")
    add("**live chain**: every decision the concern rests on that has not been completely replaced,")
    add("in order. A second, independent reader then checked whether each live member's substance")
    add("actually made it into the summary.\n")
    add("Each entry shows the chain it was built from, so you can check the summary against its")
    add("evidence rather than taking my word for it.\n")

    def render(adr_id: str, *, wording: bool) -> None:
        chain = chains[adr_id]
        add(f"\n### `{adr_id}`\n")
        add(f"**{chain['title']}**\n")
        add(f"- Rests on: `{chain['head']}`")
        members = " → ".join(
            f"`{m['ref']}`{' ←head' if m['is_head'] else ''}" for m in chain["live_chain"])
        add(f"- Live chain (oldest → newest): {members or '_none_'}")
        for m in chain["live_chain"]:
            add(f"  - `{m['ref']}` {m['date'][:10]} — {m['title']}")
        if chain["replaced"]:
            for r in chain["replaced"]:
                add(f"- Retired member: `{r['ref']}` replaced by {', '.join(r['replaced_by'])}")
        if not wording:
            return
        s = summaries.get(adr_id)
        if not s:
            return
        add(f"\n**Decision.** {s['decision']}\n")
        add(f"**Why.** {s['why']}\n")
        add(f"**How it evolved.** {s['evolution']}\n")

    add("\n---\n\n## Gate A — 25 ready\n")
    add("Summary rebuilt from the whole live chain, checker confirms nothing was dropped, and the")
    add("decision it rests on is the newest one in its chain. This is the proposed wording.\n")
    for adr_id in gates["A"]:
        render(adr_id, wording=True)

    add("\n---\n\n## Gate B — 5 ready, but anchored on an older decision\n")
    add("These summaries passed both checks. What is odd is *which* decision each one says it rests")
    add("on: a later decision in the same chain has already moved the concern past it.\n")
    for adr_id in gates["B"]:
        chain = chains[adr_id]
        newest = chain["live_chain"][-1]
        add(f"\n### `{adr_id}`\n")
        add(f"**{chain['title']}**\n")
        add(f"- Rests on: `{chain['head']}`")
        add(f"- Newest decision in its chain: `{newest['ref']}` ({newest['date'][:10]}) — {newest['title']}")
        s = summaries.get(adr_id)
        if s:
            add(f"\n**Decision.** {s['decision']}\n")
            add(f"**Why.** {s['why']}\n")
            add(f"**How it evolved.** {s['evolution']}\n")

    add("\n---\n\n## Gate C — 3 held on a structural problem\n")
    add("No wording can fix these; something about what the ADR points at is wrong.\n")
    for adr_id in gates["C"]:
        add(f"\n### `{adr_id}`\n")
        add(f"**{chains[adr_id]['title']}**\n")
        add(PLAIN_C[adr_id] + "\n")
        render(adr_id, wording=False)

    add("\n---\n\n## Gate D — 5 held because the summary still misses something\n")
    add("The concern is real in each case. The summary is what falls short: it leaves out a live")
    add("member's substance, or states something the chain does not support.\n")
    for adr_id in gates["D"]:
        chain = chains[adr_id]
        add(f"\n### `{adr_id}`\n")
        add(f"**{chain['title']}**\n")
        if adr_id == "adr_draft_format":
            add("**Held by me, not by the checker.** The proposed summary says multi-decision entries")
            add("use numbered `#### Dn` headings as the canonical form. Its one live decision is 744")
            add("characters long, was given to the worker in full, and says nothing of the sort - it")
            add("only defines the D/R/A/F/T labels. So the summary states a rule its evidence does not")
            add("support. The completeness checker passed it; I read the decision myself and failed it.\n")
        else:
            v = checker.get(adr_id, {})
            gaps = ", ".join(f"`{r}`" for r in v.get("missing", []) + v.get("contradicted", []))
            add(f"**What the checker found.** {v.get('checker', '')}\n")
            if gaps:
                add(f"Members not accounted for: {gaps}\n")
        render(adr_id, wording=True)

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT.name} ({len(OUT.read_text(encoding='utf-8')):,} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
