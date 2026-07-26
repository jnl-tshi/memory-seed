"""Adjudicate the `topic_swarm` pilot — did Leg A measure accuracy, or agreement?

The pilot in ``.memory-seed/skills/topic_swarm.md`` §4 scored the swarm's topics
against the **authored** topics as if authored were ground truth. But in this repo
the author of a topic slug is itself an agent at write time, so a disagreement
between the swarm and the author is two annotators disagreeing, not one of them
being wrong. Nobody adjudicated who was actually right. This script owns the
mechanical half of that adjudication, and of the separate question the pilot could
not ask at all — what the swarm does on entries that received NO topics at write
time, where there is no authored set to recall and Leg A is undefined.

  sheet       pool the authored and swarm roll-ups into ONE shuffled, unlabelled
              candidate list per entry, with the decision bodies, for blind marking
  join        join a marker's y/n verdicts back to the key: who proposed what,
              and who the adjudicator upheld
  rescore     recompute Leg A macro-recall against the ADJUDICATED denominator,
              swarm verdicts and pass line untouched
  topicless   draw a seeded sample from the entries with zero authored topics and
              emit the same blind, decision-body-only payloads the pilot uses
  validate    mechanical validation (skill §3) of a topicless fan-out, then the
              per-entry roll-up a backfill would actually propose

Three properties carry over from ``topic_swarm_pilot.py`` deliberately:

* **Blind means blind.** ``sheet`` writes the candidate slugs shuffled and with no
  provenance; the key naming which predictor proposed each row is written to a
  separate file the marker never reads. ``topicless`` hands workers the decision
  body only, exactly as ``draw`` does.
* **Dropped, never repaired.** ``validate`` re-implements nothing: it applies the
  same vocabulary / cap / duplicate / quote-grounding rules, and a failing slug is
  discarded rather than fixed up.
* **Seeds are recorded.** Every draw and every shuffle takes a seed written into
  the output, so a reviewer can regenerate the sample and see it was not picked.

``rescore`` reports three denominators because they bound the answer differently:

  (a) upper bound   drop only the author-ONLY slugs the adjudicator rejected.
                    Those are by construction slugs the swarm did not propose, so
                    removing them strictly RAISES recall. If (a) stays under the
                    pass line, the original verdict survives adjudication.
  (b) adjudicated   drop every authored slug the adjudicator rejected.
  (c) pooled        ground truth is every upheld candidate, including swarm-only
                    ones. A CEILING, not an estimate: the pool contains only slugs
                    one of the two predictors already proposed.

Usage:
  python scripts/topic_swarm_adjudication.py sheet     <repo> <pilot_dir> <verdicts> <dest>
  python scripts/topic_swarm_adjudication.py join      <dest>
  python scripts/topic_swarm_adjudication.py rescore   <repo> <pilot_dir> <verdicts> <dest>
  python scripts/topic_swarm_adjudication.py topicless <repo> <out_dir> --seed N --sample K
  python scripts/topic_swarm_adjudication.py validate  <repo> <out_dir>
"""

from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

MAX_PER_DECISION = 3
MAX_BARE = 4
SHEET_SHUFFLE_SEED = 4242

AREA = {
    "memory-seed", "memory-trace", "graph", "retrieval", "session-fuse", "session-layout",
    "session-logging", "mcp-tools", "hooks", "mermaid", "control-plane", "process-management",
}
ACTIVITY = {
    "ui-design", "bugfix", "documentation", "proposal-lifecycle", "release", "git-workflow",
    "agent-collaboration", "tooling-evaluation",
}


def _harness(repo: Path):
    sys.path.insert(0, str(repo))
    sys.path.insert(0, str(repo / "scripts"))
    import topic_swarm_pilot

    return topic_swarm_pilot


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


# --------------------------------------------------------------------------- sheet


def cmd_sheet(repo: Path, pilot: Path, verdicts: Path, dest: Path) -> int:
    harness = _harness(repo)
    surviving, *_rest, entries, decs_of = harness._validate(repo, pilot, verdicts)
    answers = json.loads((pilot / "answers.json").read_text(encoding="utf-8"))

    rollup: dict[str, set[str]] = defaultdict(set)
    for (eid, _ordinal), kept in surviving.items():
        rollup[eid].update(item["slug"] for item in kept)

    (dest / "blind").mkdir(parents=True, exist_ok=True)
    (dest / "private").mkdir(parents=True, exist_ok=True)

    lines = [
        "# BLIND adjudication sheet",
        "",
        "For each entry: read the decision bodies, then mark every candidate slug `y`",
        "(warranted for this entry) or `n`. Candidates pool both predictors and are",
        "shuffled; which predictor proposed a row is held out of this file.",
        "",
    ]
    key: dict[str, dict] = {}
    rng = random.Random(SHEET_SHUFFLE_SEED)
    n = 0
    for eid in sorted(answers):
        authored = set(answers[eid]["authored_canonical"])
        swarm = rollup.get(eid, set())
        pooled = sorted(authored | swarm)
        rng.shuffle(pooled)
        lines.append(f"## {eid} [{answers[eid]['stratum']}]")
        lines.append("")
        for decision in decs_of(entries[eid].text):
            lines.append(f"### decision {decision.ordinal} — {decision.name or '(singular)'}")
            lines.append("")
            lines.append(decision.text.strip())
            lines.append("")
        lines.append("| # | mark | candidate slug |")
        lines.append("|---|---|---|")
        for slug in pooled:
            n += 1
            lines.append(f"| {n} | | `{slug}` |")
            sources = [s for s, present in
                       (("author", slug in authored), ("swarm", slug in swarm)) if present]
            key[str(n)] = {"entry_id": eid, "slug": slug, "sources": sources}
        lines.append("")

    (dest / "blind" / "sheet.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (dest / "private" / "key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")

    both = sum(1 for v in key.values() if len(v["sources"]) == 2)
    only_a = sum(1 for v in key.values() if v["sources"] == ["author"])
    only_s = sum(1 for v in key.values() if v["sources"] == ["swarm"])
    print(f"pooled candidates: {n} (agreed {both}, author-only {only_a}, swarm-only {only_s})")
    print(f"disagreements: {only_a + only_s}; author-only {only_a} are the recall misses Leg A punished")
    print(f"sheet -> {dest / 'blind' / 'sheet.md'} (hand this out; withhold private/)")
    return 0


# ---------------------------------------------------------------------------- join


def cmd_join(dest: Path) -> int:
    key = json.loads((dest / "private" / "key.json").read_text(encoding="utf-8"))
    marks = json.loads((dest / "blind" / "marks.json").read_text(encoding="utf-8"))
    unmarked = [k for k in key if k not in marks]
    if unmarked:
        print(f"UNMARKED ROWS (scores below are incomplete): {unmarked}")

    cell: Counter[str] = Counter()
    for k, meta in key.items():
        cell[f"{'+'.join(meta['sources'])}/{marks.get(k, {}).get('mark', '?')}"] += 1

    print("\ncontingency (proposer -> adjudicator):")
    for src, label in (
        ("author+swarm", "AGREED (both proposed)"),
        ("author", "AUTHOR-ONLY (recall miss)"),
        ("swarm", "SWARM-ONLY (scored spurious)"),
    ):
        y, no = cell[f"{src}/y"], cell[f"{src}/n"]
        total = y + no
        pct = f"{y / total:.0%}" if total else "-"
        print(f"  {label:<30}n={total:<4}upheld={y:<4}rejected={no:<4}({pct} upheld)")

    for src, label in (("author", "AUTHOR-ONLY"), ("swarm", "SWARM-ONLY")):
        print(f"\n--- {label} rows ---")
        for k, meta in sorted(key.items(), key=lambda kv: int(kv[0])):
            if meta["sources"] == [src]:
                m = marks.get(k, {})
                print(f"  [{m.get('mark', '?')}] {meta['entry_id']} {meta['slug']:<22}{m.get('reason', '')}")

    rejected: dict[str, list[str]] = defaultdict(list)
    for k, meta in key.items():
        if "author" in meta["sources"] and marks.get(k, {}).get("mark") == "n":
            rejected[meta["entry_id"]].append(meta["slug"])
    (dest / "private" / "rejected_authored.json").write_text(
        json.dumps(rejected, indent=2), encoding="utf-8")
    print(f"\nauthored slugs rejected: {sum(len(v) for v in rejected.values())} "
          f"across {len(rejected)} entries -> private/rejected_authored.json")
    return 0


# ------------------------------------------------------------------------- rescore


def cmd_rescore(repo: Path, pilot: Path, verdicts: Path, dest: Path) -> int:
    harness = _harness(repo)
    surviving, _d, _det, _raw, resolution, _canon, entries, _decs = harness._validate(
        repo, pilot, verdicts)
    answers = json.loads((pilot / "answers.json").read_text(encoding="utf-8"))
    draw = json.loads((pilot / "draw.json").read_text(encoding="utf-8"))
    key = json.loads((dest / "private" / "key.json").read_text(encoding="utf-8"))
    marks = json.loads((dest / "blind" / "marks.json").read_text(encoding="utf-8"))

    predicted: dict[str, set[str]] = defaultdict(set)
    for (eid, _ordinal), kept in surviving.items():
        predicted[eid].update(item["slug"] for item in kept)

    verdict_of = {
        (meta["entry_id"], meta["slug"]): (meta["sources"], marks[k]["mark"])
        for k, meta in key.items() if k in marks
    }
    truths: dict[str, dict[str, set[str]]] = {k: {} for k in
                                              ("original", "a_upper", "b_adjudicated", "c_pooled")}
    for eid, meta in answers.items():
        authored = set(meta["authored_canonical"])
        truths["original"][eid] = set(authored)
        truths["a_upper"][eid] = {
            s for s in authored
            if verdict_of.get((eid, s), ([], "y")) != (["author"], "n")
        }
        truths["b_adjudicated"][eid] = {
            s for s in authored if verdict_of.get((eid, s), ([], "y"))[1] == "y"
        }
        truths["c_pooled"][eid] = {
            s for (e, s), (_src, m) in verdict_of.items() if e == eid and m == "y"
        }

    freq: Counter[str] = Counter()
    for chunk in entries.values():
        freq.update(resolution.get(t, t) for t in (chunk.topics or ()))
    ranked = [s for s, _ in freq.most_common()]

    def macro_recall(truth: dict[str, set[str]], predict) -> tuple[float, int]:
        scores = [len(t & predict(e)) / len(t) for e, t in truth.items() if t]
        return (sum(scores) / len(scores) if scores else 0.0), len(scores)

    print(f"seed {draw['seed']}; {len(answers)} entries; swarm verdicts identical in every row.\n")
    header = f"{'ground truth':<20}{'slugs':>7}{'scored':>8}{'top-4':>8}{'LEG A':>9}   verdict"
    print(header)
    print("-" * len(header))
    for name, truth in truths.items():
        slugs = sum(len(v) for v in truth.values())
        base, _ = macro_recall(truth, lambda e: set(ranked[:4]))
        recall, scored = macro_recall(truth, lambda e: predicted.get(e, set()))
        verdict = ("PROCEED" if recall >= harness.LEG_A_PROCEED
                   else "ABORT" if recall < harness.LEG_A_ABORT else "RE-PROMPT BAND")
        print(f"{name:<20}{slugs:>7}{scored:>8}{base:>8.3f}{recall:>9.3f}   {verdict}")
        if scored < len(answers):
            forced = recall * scored / len(answers)
            print(f"{'':<20}{'':>7}{'':>8}{'':>8}{forced:>9.3f}   "
                  f"(entries whose whole authored set was rejected forced back in at 0.00)")
    print(f"\npass line: ABORT < {harness.LEG_A_ABORT} / PROCEED >= {harness.LEG_A_PROCEED}")
    print("(a) is an upper bound; (c) is a ceiling, not an estimate. See the module docstring.")
    return 0


# ----------------------------------------------------------------------- topicless


def _strip_metadata(text: str) -> str:
    stripped = re.sub(r"^\s*```+\s*yaml\b.*?```+\s*", "", text, count=1, flags=re.S)
    if stripped == text:
        stripped = re.sub(r"^\s*---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.S)
    return stripped.strip()


def cmd_topicless(repo: Path, out: Path, seed: int, sample: int) -> int:
    harness = _harness(repo)
    decs_of, entries, index = harness._load(repo)

    pool = sorted(eid for eid, chunk in entries.items() if not chunk.topics)
    chosen = sorted(random.Random(seed).sample(pool, sample))

    out.mkdir(parents=True, exist_ok=True)
    (out / "tasks").mkdir(exist_ok=True)
    (out / "vocabulary.md").write_text(
        "\n".join(["# Controlled topic vocabulary — canonical slugs only", ""]
                  + [f"- `{r.slug}` — {r.label}: {r.description}"
                     for r in sorted(index.topics, key=lambda r: r.slug)]) + "\n",
        encoding="utf-8")

    tasks: list[dict] = []
    composition = Counter()
    for eid in chosen:
        decisions = decs_of(entries[eid].text)
        composition["bare" if not decisions else "single" if len(decisions) == 1 else "multi"] += 1
        if not decisions:
            tasks.append({"task_id": f"{eid}_bare", "entry_id": eid, "ordinal": None,
                          "decision_name": "", "decision_body": _strip_metadata(entries[eid].text)})
        else:
            tasks.extend({"task_id": f"{eid}_{d.ordinal}", "entry_id": eid, "ordinal": d.ordinal,
                          "decision_name": d.name, "decision_body": d.text} for d in decisions)
    for task in tasks:
        (out / "tasks" / f"{task['task_id']}.json").write_text(
            json.dumps(task, indent=2, ensure_ascii=False), encoding="utf-8")

    (out / "draw.json").write_text(json.dumps({
        "seed": seed, "population": "entries with ZERO authored topics",
        "pool_size": len(pool), "sample_size": sample, "chosen": chosen,
        "composition": dict(composition), "judgment_units": len(tasks),
    }, indent=2), encoding="utf-8")
    print(f"seed={seed}; pool={len(pool)} topicless entries; drew {sample} {dict(composition)}")
    print(f"{len(tasks)} judgment units -> {out / 'tasks'}")
    return 0


def cmd_validate(repo: Path, out: Path) -> int:
    harness = _harness(repo)
    decs_of, entries, index = harness._load(repo)
    canonical = {r.slug for r in index.topics}
    aliases = {a for r in index.topics for a in r.aliases}

    tasks = {}
    for path in sorted((out / "tasks").glob("*.json")):
        task = json.loads(path.read_text(encoding="utf-8"))
        tasks[task["task_id"]] = task

    surviving: dict[str, list[dict]] = {}
    drops: Counter[str] = Counter()
    detail: list[str] = []
    raw = 0
    for task_id, task in tasks.items():
        path = out / "verdicts" / f"{task_id}.json"
        if not path.exists():
            drops["verdict-missing"] += 1
            detail.append(f"{task_id}: no verdict file")
            continue
        try:
            block = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            drops["unparseable-verdict"] += 1
            continue
        items = block.get("slugs") or []
        raw += len(items)
        body = _norm(task["decision_body"])
        ceiling = MAX_BARE if task["ordinal"] is None else MAX_PER_DECISION
        names = [str(i.get("slug", "")) for i in items]
        if len(names) > ceiling:
            drops["over-cap-block-dropped"] += len(items)
            continue
        if len(set(names)) != len(names):
            drops["malformed-duplicate-slug-block-dropped"] += len(items)
            continue
        kept = []
        for item in items:
            slug, quote = str(item.get("slug", "")), str(item.get("quote", ""))
            if slug not in canonical:
                drops["non-canonical-topic-slug" if slug in aliases else "unknown-slug"] += 1
                detail.append(f"{task_id}: '{slug}' not canonical")
                continue
            if not quote or _norm(quote) not in body:
                drops["quote-not-grounded"] += 1
                detail.append(f"{task_id}: quote for '{slug}' not in body")
                continue
            kept.append({"slug": slug, "quote": quote, "why": str(item.get("why", ""))})
        if kept:
            surviving[task_id] = kept

    draw = json.loads((out / "draw.json").read_text(encoding="utf-8"))
    print(f"seed {draw['seed']}; {draw['sample_size']} topicless entries, "
          f"{draw['judgment_units']} units; composition {draw['composition']}")
    print(f"raw slugs {raw}; surviving blocks {len(surviving)}; "
          f"surviving slugs {sum(len(v) for v in surviving.values())}")
    print("\ndrop histogram (dropped, never repaired):")
    print("  (none)" if not drops else "")
    for kind, count in drops.most_common():
        print(f"  {kind:<42}{count}")

    shape: Counter[str] = Counter()
    for kept in surviving.values():
        slugs = {i["slug"] for i in kept}
        shape[f"{len(slugs & AREA)} area + {len(slugs & ACTIVITY)} activity"] += 1
    print("\noutput shape (surviving blocks):")
    for kind, count in shape.most_common():
        print(f"  {kind:<24}{count}")

    rollup: dict[str, set[str]] = defaultdict(set)
    for task_id, kept in surviving.items():
        rollup[tasks[task_id]["entry_id"]].update(i["slug"] for i in kept)
    print("\nper-entry roll-up (what a backfill would propose):")
    for eid in draw["chosen"]:
        count = len(decs_of(entries[eid].text))
        kind = "bare" if not count else "single" if count == 1 else f"multi x{count}"
        print(f"  {eid} [{kind}] -> {sorted(rollup.get(eid, []))}")

    (out / "surviving.json").write_text(
        json.dumps(surviving, indent=2, ensure_ascii=False), encoding="utf-8")
    if detail:
        (out / "drops.txt").write_text("\n".join(detail) + "\n", encoding="utf-8")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    command = argv[1]
    if command == "sheet":
        return cmd_sheet(Path(argv[2]).resolve(), Path(argv[3]), Path(argv[4]), Path(argv[5]))
    if command == "join":
        return cmd_join(Path(argv[2]))
    if command == "rescore":
        return cmd_rescore(Path(argv[2]).resolve(), Path(argv[3]), Path(argv[4]), Path(argv[5]))
    if command == "topicless":
        seed = int(argv[argv.index("--seed") + 1])
        sample = int(argv[argv.index("--sample") + 1])
        return cmd_topicless(Path(argv[2]).resolve(), Path(argv[3]), seed, sample)
    if command == "validate":
        return cmd_validate(Path(argv[2]).resolve(), Path(argv[3]))
    print(f"unknown command {command!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
