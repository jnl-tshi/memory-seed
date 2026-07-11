"""Deterministic synthetic Memory Seed corpora for Memory Trace baselines.

Phase 0 of the next-generation roadmap needs 500/1,000/10,000-entry datasets
whose shape exercises everything the Trail and Graph render: a main line,
forking/merging feature branches (including parallel branches and
daisy-chains), lifecycle edges (related/supersedes/evolves), topics, and
varied prose for search ranking. Output is a plain ``.memory-seed/sessions``
tree readable by the real cache - no Trace-specific format.

Determinism contract: same (count, seed) -> byte-identical tree. No wall
clock, no filesystem ordering dependence; every choice flows from the seeded
RNG or the entry counter. Regenerate with:

    python tests/fixtures/generate_synthetic.py <count> <output-dir> [seed]

The datasets are generated on demand rather than committed - 10k entries of
markdown is megabytes of noise in a review, and the generator IS the fixture.
"""
from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

ENTRIES_PER_DAY = 8
BASE_DATE = date(2026, 7, 1)  # newest day; history walks backwards
AGENTS = ["codex", "claude", "gemini"]
TOPICS = [
    "memory-trace", "git-workflow", "graph", "documentation", "release",
    "session-fuse", "ui-design", "mcp-tools", "bugfix", "proposal",
]
TITLE_VERBS = [
    "Implement", "Refine", "Audit", "Repair", "Extract", "Promote",
    "Retire", "Harden", "Document", "Benchmark",
]
TITLE_NOUNS = [
    "trail lane allocation", "search ranking", "commit map", "cache rebuild",
    "session fuse", "topic vocabulary", "reader layout", "graph forces",
    "encoding policy", "release workflow", "branch status", "diagram sidecars",
]
BODY_SENTENCES = [
    "Adjusted the {noun} so the {topic} path stays deterministic.",
    "Verified against the fixture corpus before landing.",
    "The previous approach conflated {noun} with presentation state.",
    "Follow-up work is tracked in the {topic} plan.",
    "Measured no regression at the target scale.",
    "Documented the decision beside the code it constrains.",
]


def _entry_id(counter: int) -> str:
    # Base32-flavoured, 16 chars, unique and stable per counter.
    alphabet = "0123456789abcdefghjkmnpqrstvwxyz"
    encoded = ""
    value = counter + 1
    while value:
        encoded = alphabet[value % 32] + encoded
        value //= 32
    return "mse_" + encoded.rjust(16, "0")


def _entry_text(*, day: date, minute_of_day: int, counter: int, branch: str,
                rng: random.Random, earlier_ids: list[str]) -> str:
    hh, mm = divmod(minute_of_day, 60)
    title = f"{rng.choice(TITLE_VERBS)} {rng.choice(TITLE_NOUNS)}"
    topic = rng.choice(TOPICS)
    agent = rng.choice(AGENTS)
    lines = [
        f"## {day.isoformat()} {hh:02d}:{mm:02d} - {title}",
        "",
        "```yaml",
        f"entry_id: {_entry_id(counter)}",
        "user_initials: SY",
        f"agent_type: {agent}",
        "project_path: .",
        "subproject_path: null",
        f"branch: {branch}",
        "topics:",
        f"  - {topic}",
    ]
    # Lifecycle edges reference only earlier ids (forward-only invariant).
    if earlier_ids and rng.random() < 0.45:
        lines.append("related_entries:")
        for ref in rng.sample(earlier_ids, k=min(len(earlier_ids), rng.randint(1, 2))):
            lines.append(f"  - {ref}")
    if earlier_ids and rng.random() < 0.08:
        lines += ["supersedes:", f"  - {rng.choice(earlier_ids)}"]
    elif earlier_ids and rng.random() < 0.10:
        lines += ["evolves:", f"  - {rng.choice(earlier_ids)}"]
    lines += ["```", "", "### Decision", ""]
    body = rng.sample(BODY_SENTENCES, k=3)
    lines += [f"- D: {body[0].format(noun=rng.choice(TITLE_NOUNS), topic=topic)}"]
    lines += [f"- R: {body[1].format(noun=rng.choice(TITLE_NOUNS), topic=topic)}"]
    lines += [f"- T: {body[2].format(noun=rng.choice(TITLE_NOUNS), topic=topic)}", ""]
    return "\n".join(lines)


def generate(count: int, out_dir: Path, seed: int = 20260711) -> Path:
    rng = random.Random(seed)
    sessions = out_dir / ".memory-seed" / "sessions"

    total_days = max(1, (count + ENTRIES_PER_DAY - 1) // ENTRIES_PER_DAY)
    counter = 0
    earlier_ids: list[str] = []
    # Branch machinery: a rotating pool of open feature branches so the Trail
    # sees parallel lanes; each branch lives for a bounded number of entries.
    open_branches: dict[str, int] = {}
    branch_serial = 0

    for day_index in range(total_days - 1, -1, -1):
        day = BASE_DATE - timedelta(days=day_index)
        day_entries = min(ENTRIES_PER_DAY, count - counter)
        if day_entries <= 0:
            break
        blocks: list[str] = []
        minute = 8 * 60  # 08:00, spaced through the working day
        for _ in range(day_entries):
            # Open a new branch sometimes (up to 3 in parallel).
            if len(open_branches) < 3 and rng.random() < 0.18:
                branch_serial += 1
                open_branches[f"feature/synth-{branch_serial:04d}"] = rng.randint(2, 5)
            if open_branches and rng.random() < 0.55:
                branch = rng.choice(sorted(open_branches))
                open_branches[branch] -= 1
                if open_branches[branch] <= 0:
                    del open_branches[branch]
            else:
                branch = "main"
            blocks.append(_entry_text(
                day=day, minute_of_day=minute, counter=counter, branch=branch,
                rng=rng, earlier_ids=earlier_ids[-40:],
            ))
            earlier_ids.append(_entry_id(counter))
            counter += 1
            minute += rng.randint(35, 75)
        target = sessions / day.strftime("%Y-%m") / f"{day.isoformat()}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        header = "\n".join([
            "---", "tags:", "  - session-log", "  - memory-seed",
            f"session_date: {day.isoformat()}", "---", "",
        ])
        target.write_text(header + "\n" + "\n".join(blocks), encoding="utf-8", newline="\n")
    return out_dir


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    count = int(argv[0])
    out_dir = Path(argv[1])
    seed = int(argv[2]) if len(argv) > 2 else 20260711
    generate(count, out_dir, seed)
    print(f"Generated {count} entries under {out_dir / '.memory-seed' / 'sessions'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
