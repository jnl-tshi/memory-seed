"""Harness for the `topic_swarm` skill's pilot gate — enumerate, draw, validate, score.

The pilot in ``.memory-seed/skills/topic_swarm.md`` §4 is the gate on a ~933-unit
backfill campaign, and a gate that cannot be re-run is not reproducible evidence.
This script owns every mechanical half of it so that only the model judgments and
the human adjudication happen by hand:

  scope     re-measure the skill's scope table against the live corpus (§ "Scope")
  draw      stratified, seeded sample + BLIND task payloads + a separate answer key
  score     mechanical validation (§3) then Leg A macro-recall vs the baselines (§4)
  legb      the interleaved, unlabelled swarm-vs-inheritance adjudication sheet (§4)

Three properties are deliberate, not incidental:

* **Blind means blind.** ``draw`` writes worker payloads containing the decision
  ordinal, its heading name, and its body — the exact slice ``entry_body_decisions``
  returns, which begins after the entry's YAML metadata fence. The entry title and
  the authored ``topics:`` list go only into ``answers.json``, which no worker reads.
* **Canonical slugs only in the payload.** §3 *drops* an alias rather than
  canonicalising it, so teaching workers the alias column would manufacture a low
  recall for a prompt-authoring reason instead of a judgment reason. The vocabulary
  handed out is the 23 canonical slugs with labels and descriptions.
* **Anything failing validation is dropped, never repaired,** and dropped units stay
  in the Leg A denominator. A repaired verdict is the orchestrator's judgment wearing
  the swarm's provenance.

The sample is drawn from a pool sorted by ``entry_id`` before seeding, so "fixed
seed" survives a corpus rebuild instead of inheriting filesystem iteration order.

Usage:
  python scripts/topic_swarm_pilot.py scope [repo]
  python scripts/topic_swarm_pilot.py draw  <repo> <out_dir> --seed N [--exclude ids.json]
  python scripts/topic_swarm_pilot.py score <repo> <out_dir> <verdict_dir>
  python scripts/topic_swarm_pilot.py legb  <repo> <out_dir> <verdict_dir>
"""

from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Stratification and pass line, quoted from the skill so a drift is visible here.
PILOT_MULTI = 14
PILOT_SINGLE = 6
LEG_A_PROCEED = 0.70
LEG_A_ABORT = 0.55
MAX_PER_DECISION = 3
MAX_BARE = 4


def _load(repo: Path):
    sys.path.insert(0, str(repo))
    from memory_seed.core import entry_body_decisions
    from memory_seed.semantic_cache import extract_memory_chunks
    from memory_seed.topics import load_topic_index

    index = load_topic_index(repo)
    entries = {}
    for chunk in extract_memory_chunks(str(repo)):
        if chunk.entry_id and chunk.entry_id not in entries:
            entries[chunk.entry_id] = chunk
    return entry_body_decisions, entries, index


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


# --------------------------------------------------------------------------- scope


def cmd_scope(repo: Path) -> int:
    decs_of, entries, index = _load(repo)
    canonical = {r.slug for r in index.topics}
    resolution = index.resolution()

    ordinals = zero = topiced = in_topiced = alias_users = 0
    multi_pool: list[str] = []
    single_pool: list[str] = []
    authored_freq: Counter[str] = Counter()

    for eid, chunk in entries.items():
        decisions = decs_of(chunk.text)
        ordinals += len(decisions)
        if not decisions:
            zero += 1
        authored = list(chunk.topics or ())
        if authored:
            topiced += 1
            in_topiced += len(decisions)
            if any(t not in canonical and t in resolution for t in authored):
                alias_users += 1
            authored_freq.update(resolution.get(t, t) for t in authored)
        if 2 <= len(authored) <= 4:
            (multi_pool if len(decisions) >= 2 else single_pool if decisions else []).append(eid)

    print(f"entries carrying an entry_id                 {len(entries)}")
    print(f"addressable decision ordinals                {ordinals}")
    print(f"entries with zero addressable ordinals       {zero}")
    print(f"TOTAL judgment units                         {ordinals + zero}")
    print(f"entries with authored topics                 {topiced}")
    print(f"entries with no topics                       {len(entries) - topiced}")
    print(f"ordinals inside already-topiced entries      {in_topiced}")
    print(f"topiced entries using at least one alias     {alias_users}")
    print(f"canonical topics defined                     {len(canonical)}")
    print(f"pilot pool multi-decision (>=2 ord, 2-4)     {len(multi_pool)}")
    print(f"pilot pool single-decision (1 ord, 2-4)      {len(single_pool)}")
    print("most-authored canonical slugs                " + ", ".join(
        f"{s}({n})" for s, n in authored_freq.most_common(6)
    ))
    return 0


# ---------------------------------------------------------------------------- draw


def cmd_draw(repo: Path, out: Path, seed: int, exclude: Path | None) -> int:
    decs_of, entries, index = _load(repo)
    canonical = {r.slug for r in index.topics}
    resolution = index.resolution()
    skip = set(json.loads(exclude.read_text(encoding="utf-8"))) if exclude else set()

    multi: list[str] = []
    single: list[str] = []
    for eid, chunk in sorted(entries.items()):  # sort BEFORE seeding
        if eid in skip:
            continue
        authored = list(chunk.topics or ())
        if not 2 <= len(authored) <= 4:
            continue
        n = len(decs_of(chunk.text))
        if n >= 2:
            multi.append(eid)
        elif n == 1:
            single.append(eid)

    rng = random.Random(seed)
    chosen_multi = sorted(rng.sample(multi, PILOT_MULTI))
    chosen_single = sorted(rng.sample(single, PILOT_SINGLE))

    out.mkdir(parents=True, exist_ok=True)
    (out / "tasks").mkdir(exist_ok=True)

    vocab_lines = ["# Controlled topic vocabulary — canonical slugs only", ""]
    for record in sorted(index.topics, key=lambda r: r.slug):
        vocab_lines.append(f"- `{record.slug}` — {record.label}: {record.description}")
    (out / "vocabulary.md").write_text("\n".join(vocab_lines) + "\n", encoding="utf-8")

    answers: dict[str, dict] = {}
    tasks: list[dict] = []
    for eid in chosen_multi + chosen_single:
        chunk = entries[eid]
        decisions = decs_of(chunk.text)
        answers[eid] = {
            "authored_raw": list(chunk.topics or ()),
            "authored_canonical": sorted({resolution.get(t, t) for t in (chunk.topics or ())}),
            "stratum": "multi" if len(decisions) >= 2 else "single",
            "ordinals": [d.ordinal for d in decisions],
            "decision_names": {d.ordinal: d.name for d in decisions},
        }
        for decision in decisions:
            task = {
                "task_id": f"{eid}_{decision.ordinal}",
                "entry_id": eid,
                "ordinal": decision.ordinal,
                "decision_name": decision.name,
                "decision_body": decision.text,
            }
            tasks.append(task)
            (out / "tasks" / f"{task['task_id']}.json").write_text(
                json.dumps(task, indent=2, ensure_ascii=False), encoding="utf-8"
            )

    (out / "answers.json").write_text(
        json.dumps(answers, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out / "draw.json").write_text(
        json.dumps(
            {
                "seed": seed,
                "pool_multi": len(multi),
                "pool_single": len(single),
                "excluded": sorted(skip),
                "chosen_multi": chosen_multi,
                "chosen_single": chosen_single,
                "judgment_units": len(tasks),
                "canonical_topics": sorted(canonical),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"seed={seed} pools: multi={len(multi)} single={len(single)}")
    print(f"drew {len(chosen_multi)} multi + {len(chosen_single)} single = {len(tasks)} judgment units")
    print(f"tasks -> {out / 'tasks'}   answers -> {out / 'answers.json'}")
    return 0


# ------------------------------------------------------------------ validate/score


def _validate(repo: Path, out: Path, verdicts: Path):
    """Mechanical validation per skill §3. Returns (surviving, drops, raw_count)."""
    decs_of, entries, index = _load(repo)
    canonical = {r.slug for r in index.topics}
    resolution = index.resolution()
    aliases = {a for r in index.topics for a in r.aliases}

    bodies: dict[tuple[str, str], str] = {}
    for eid in json.loads((out / "answers.json").read_text(encoding="utf-8")):
        for decision in decs_of(entries[eid].text):
            bodies[(eid, decision.ordinal)] = decision.text

    surviving: dict[tuple[str, str], list[dict]] = {}
    drops: Counter[str] = Counter()
    detail: list[str] = []
    raw = 0

    for path in sorted(verdicts.glob("*.json")):
        try:
            verdict = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            drops["unparseable-verdict"] += 1
            detail.append(f"{path.name}: unparseable")
            continue
        for block in verdict if isinstance(verdict, list) else [verdict]:
            eid = str(block.get("entry_id", ""))
            ordinal = block.get("ordinal")
            ordinal = None if ordinal in (None, "", "null") else str(ordinal)
            key = (eid, ordinal or "")
            items = block.get("slugs") or []
            raw += len(items)
            if key not in bodies:
                drops["dangling-topic-decision"] += len(items)
                detail.append(f"{eid}:{ordinal}: ordinal not addressable")
                continue
            body = _norm(bodies[key])
            ceiling = MAX_BARE if ordinal is None else MAX_PER_DECISION
            names = [str(i.get("slug", "")) if isinstance(i, dict) else str(i) for i in items]
            if len(names) > ceiling:
                drops["over-cap-block-dropped"] += len(items)
                detail.append(f"{eid}:{ordinal}: {len(names)} slugs > cap {ceiling}, block dropped")
                continue
            if len(set(names)) != len(names):
                drops["malformed-duplicate-slug-block-dropped"] += len(items)
                detail.append(f"{eid}:{ordinal}: duplicate slug in block, block dropped")
                continue
            kept: list[dict] = []
            for item in items:
                if isinstance(item, dict):
                    slug = str(item.get("slug", ""))
                    quote = str(item.get("quote", ""))
                    why = str(item.get("why", ""))
                else:
                    slug, quote, why = str(item), "", ""
                if slug not in canonical:
                    drops["non-canonical-topic-slug" if slug in aliases else "unknown-slug"] += 1
                    detail.append(f"{eid}:{ordinal}: slug '{slug}' not canonical")
                    continue
                if not quote or _norm(quote) not in body:
                    drops["quote-not-grounded"] += 1
                    detail.append(f"{eid}:{ordinal}: quote for '{slug}' not in decision body")
                    continue
                kept.append({"slug": slug, "quote": quote, "why": why})
            if kept:
                surviving[key] = kept
    return surviving, drops, detail, raw, resolution, canonical, entries, decs_of


def cmd_score(repo: Path, out: Path, verdicts: Path) -> int:
    surviving, drops, detail, raw, resolution, canonical, entries, decs_of = _validate(
        repo, out, verdicts
    )
    answers = json.loads((out / "answers.json").read_text(encoding="utf-8"))
    draw = json.loads((out / "draw.json").read_text(encoding="utf-8"))

    # Corpus-wide authored frequency for the constant-guess baselines.
    freq: Counter[str] = Counter()
    for chunk in entries.values():
        freq.update(resolution.get(t, t) for t in (chunk.topics or ()))
    ranked = [s for s, _ in freq.most_common()]

    predicted: dict[str, set[str]] = defaultdict(set)
    for (eid, _ordinal), kept in surviving.items():
        predicted[eid].update(item["slug"] for item in kept)

    def macro_recall(predict) -> float:
        scores = []
        for eid, meta in answers.items():
            authored = set(meta["authored_canonical"])
            if not authored:
                continue
            scores.append(len(authored & predict(eid)) / len(authored))
        return sum(scores) / len(scores)

    swarm_recall = macro_recall(lambda e: predicted.get(e, set()))
    precisions = [
        len(set(answers[e]["authored_canonical"]) & predicted[e]) / len(predicted[e])
        for e in answers
        if predicted.get(e)
    ]
    diag_precision = sum(precisions) / len(precisions) if precisions else 0.0

    rng = random.Random(draw["seed"])
    random_trials = []
    for _ in range(2000):
        pick = set(rng.sample(sorted(canonical), 2))
        random_trials.append(macro_recall(lambda e, p=pick: p))
    baselines = {
        "random 2 slugs from the vocabulary": sum(random_trials) / len(random_trials),
        f"always top-2 authored ({', '.join(ranked[:2])})": macro_recall(lambda e: set(ranked[:2])),
        f"always top-3 authored (+{ranked[2]})": macro_recall(lambda e: set(ranked[:3])),
        f"always top-4 authored (+{ranked[3]})": macro_recall(lambda e: set(ranked[:4])),
    }

    print(f"seed {draw['seed']}; {len(answers)} entries, {draw['judgment_units']} judgment units")
    print(f"verdict files read: {len(list(verdicts.glob('*.json')))}; raw slugs proposed: {raw}")
    print(f"surviving blocks: {len(surviving)}; surviving slugs: {sum(len(v) for v in surviving.values())}")
    print()
    print("drop histogram (dropped, never repaired):")
    if not drops:
        print("  (none)")
    for kind, count in drops.most_common():
        print(f"  {kind:<42}{count}")
    print()
    print("baselines (same corpus, same canonicalisation, same macro-average):")
    for name, value in baselines.items():
        print(f"  {name:<48}{value:.3f}")
    print()
    print(f"LEG A macro-recall of the authored set:  {swarm_recall:.3f}")
    print(f"  (precision, DIAGNOSTIC only:           {diag_precision:.3f})")
    verdict = (
        "PROCEED" if swarm_recall >= LEG_A_PROCEED
        else "ABORT" if swarm_recall < LEG_A_ABORT
        else "RE-PROMPT BAND (0.55-0.70): re-prompt once, fresh disjoint sample of 20"
    )
    print(f"  pass line {LEG_A_ABORT} / {LEG_A_PROCEED}  ->  {verdict}")
    print()
    print("per-entry recall:")
    for eid, meta in sorted(answers.items(), key=lambda kv: kv[1]["stratum"]):
        authored = set(meta["authored_canonical"])
        got = predicted.get(eid, set())
        r = len(authored & got) / len(authored) if authored else 0.0
        print(f"  {eid} [{meta['stratum']:<6}] {r:.2f}  authored={sorted(authored)} swarm={sorted(got)}")
    if detail:
        (out / "drops.txt").write_text("\n".join(detail) + "\n", encoding="utf-8")
        print(f"\ndrop detail -> {out / 'drops.txt'}")
    return 0


# ---------------------------------------------------------------------------- legb


def cmd_legb(repo: Path, out: Path, verdicts: Path) -> int:
    """Build the interleaved, unlabelled swarm-vs-inheritance adjudication sheet.

    Scoring it is the human's job (skill §4, Leg B). This writes the sheet and a
    separately-filed key so the adjudicator cannot see which predictor proposed a
    pair; nothing here computes a Leg B number.
    """
    surviving, _drops, _detail, _raw, _res, _canon, entries, decs_of = _validate(
        repo, out, verdicts
    )
    answers = json.loads((out / "answers.json").read_text(encoding="utf-8"))
    draw = json.loads((out / "draw.json").read_text(encoding="utf-8"))

    rows: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for eid in draw["chosen_multi"]:
        authored = set(answers[eid]["authored_canonical"])
        for decision in decs_of(entries[eid].text):
            for slug in authored:  # inheritance: every decision gets the whole entry set
                rows[(eid, decision.ordinal, slug)].add("inheritance")
    for (eid, ordinal), kept in surviving.items():
        if eid not in set(draw["chosen_multi"]):
            continue
        for item in kept:
            rows[(eid, ordinal, item["slug"])].add("swarm")

    ordered = sorted(rows)
    random.Random(draw["seed"] + 1).shuffle(ordered)

    sheet = [
        "# Leg B adjudication sheet — is this topic correctly attributed to THIS decision?",
        "",
        f"{len(ordered)} distinct (decision, slug) pairs across the {len(draw['chosen_multi'])} "
        "multi-decision pilot entries. Pairs proposed by the swarm and by inheritance are pooled,",
        "deduplicated, and shuffled; which predictor proposed a row is held in `legb_key.json`.",
        "Mark each row `y` (correctly attributed to that decision) or `n`.",
        "",
        "| # | mark | entry | decision | slug | decision heading |",
        "|---|---|---|---|---|---|",
    ]
    key = {}
    for i, (eid, ordinal, slug) in enumerate(ordered, 1):
        name = answers[eid]["decision_names"].get(ordinal, "") or "(singular ### Decision)"
        sheet.append(f"| {i} | | `{eid}` | {ordinal} | `{slug}` | {name} |")
        key[str(i)] = {
            "entry_id": eid,
            "ordinal": ordinal,
            "slug": slug,
            "sources": sorted(rows[(eid, ordinal, slug)]),
        }
    (out / "legb_sheet.md").write_text("\n".join(sheet) + "\n", encoding="utf-8")
    (out / "legb_key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")

    both = sum(1 for v in key.values() if len(v["sources"]) == 2)
    only_swarm = sum(1 for v in key.values() if v["sources"] == ["swarm"])
    only_inh = sum(1 for v in key.values() if v["sources"] == ["inheritance"])
    print(f"pairs to adjudicate: {len(ordered)}  (both predictors {both}, swarm only {only_swarm}, inheritance only {only_inh})")
    print(f"swarm proposed {both + only_swarm}; inheritance proposed {both + only_inh}")
    print(f"sheet -> {out / 'legb_sheet.md'}   key -> {out / 'legb_key.json'}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    command = argv[1]
    if command == "scope":
        return cmd_scope(Path(argv[2] if len(argv) > 2 else ".").resolve())
    if command == "draw":
        seed = int(argv[argv.index("--seed") + 1])
        exclude = Path(argv[argv.index("--exclude") + 1]) if "--exclude" in argv else None
        return cmd_draw(Path(argv[2]).resolve(), Path(argv[3]), seed, exclude)
    if command in {"score", "legb"}:
        fn = cmd_score if command == "score" else cmd_legb
        return fn(Path(argv[2]).resolve(), Path(argv[3]), Path(argv[4]))
    print(f"unknown command {command!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
