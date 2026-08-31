"""Memory-index dry-run (docs/2_Todo/memory-index-dry-run-plan.md).

Approximates the Verging Labs Agentic Memory Index privately against Memory Seed, using their
mechanics: the agent gets the shipped install and its own instructions, works through simulated
multi-week sessions (seeding), then fresh sessions are quizzed against the store. Cross-model
blind-ish judging: the judge sees question + expected + answer, never the category of the run or
the store; verdict buckets copied from the published index.

Phases (run separately so each can be inspected before the next spends):
  python dryrun.py seed     sequential seeding sessions in ONE workspace (store accumulates)
  python dryrun.py quiz     parallel quiz sessions, each on a fresh COPY of the seeded workspace
                            (quiz sessions cannot pollute each other's store)
  python dryrun.py judge    codex judges every answer against the key (stdin prompts, schema out)
  python dryrun.py score    verdict table by category + blended score

Timeline compression is a stated limitation: all entries carry today's timestamps, so
long_term_retention approximates "early fact among many", not calendar age.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "experiments" / "agent-capture"))

import run as harness  # noqa: E402  (build_command, transcript_name)

RUNS = HERE / "runs"
WORKSPACE = RUNS / "workspace"
# Independent-replication corpus: a distinct fixture (durstr, not strutil) so no fixture-specific
# quirk from the first corpus can leak into this one. See docs/2_Todo/memory-index-dry-run-plan.md,
# open decision #13.
TEMPLATE = REPO_ROOT / "experiments" / "agent-capture" / "templates" / "claude-L3-durstr"
FACTS = json.loads((HERE / "facts.json").read_text(encoding="utf-8"))
QUESTIONS_PER_QUIZ = 3

CODEX = shutil.which("codex") or shutil.which("codex.cmd")

JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdicts"],
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "verdict", "note"],
                "properties": {
                    "id": {"type": "string"},
                    "verdict": {
                        "enum": [
                            "correct",
                            "not_addressed",
                            "incorrect",
                            "outdated",
                            "fabricated",
                        ]
                    },
                    "note": {"type": "string"},
                },
            },
        }
    },
}


def rmtree_force(path: Path) -> None:
    def _onerror(func, target, _exc):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    shutil.rmtree(path, onerror=_onerror)


def run_claude(cwd: Path, brief: str, timeout: int = 900, extra: list[str] | None = None) -> dict:
    args = argparse.Namespace(model=None, effort=None, extra_arg=list(extra or []))
    command = harness.build_command("claude", cwd, brief, args)
    completed = subprocess.run(
        command, cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )
    result_text = ""
    for line in completed.stdout.splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "result":
            result_text = obj.get("result") or ""
    tools: list[str] = []
    for line in completed.stdout.splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = obj.get("message") or {}
        for block in message.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name"):
                tools.append(block["name"])
    return {
        "exit": completed.returncode,
        "result": result_text,
        "stdout": completed.stdout,
        "tools": tools,
    }


def phase_seed() -> None:
    if WORKSPACE.exists():
        raise SystemExit(f"{WORKSPACE} exists - delete it to re-seed (the store accumulates)")
    if not TEMPLATE.is_dir():
        raise SystemExit("claude-L3 template missing - run generate_fixtures.py first")
    RUNS.mkdir(exist_ok=True)
    shutil.copytree(TEMPLATE, WORKSPACE)
    log = []
    for spec in FACTS["seeding_briefs"]:
        started = _dt.datetime.now().isoformat(timespec="seconds")
        out = run_claude(WORKSPACE, spec["brief"])
        entries = sum(
            1
            for p in (WORKSPACE / ".memory-seed" / "sessions").rglob("*.md")
            if "topics" not in p.parts and "links" not in p.parts
            for line in [p.read_text(encoding="utf-8")]
            for _ in []
        )
        store_files = [
            p
            for p in (WORKSPACE / ".memory-seed" / "sessions").rglob("*.md")
            if "topics" not in p.parts and "links" not in p.parts
        ]
        entry_count = sum(
            p.read_text(encoding="utf-8").count("\n## ") + p.read_text(encoding="utf-8").startswith("## ")
            for p in store_files
        )
        log.append({"id": spec["id"], "exit": out["exit"], "started": started,
                    "entries_total": int(entry_count), "final": out["result"][:300]})
        print(f"{spec['id']} exit={out['exit']} entries_total={entry_count}", flush=True)
    (RUNS / "seed-log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    print("seeded:", WORKSPACE)


def quiz_batches() -> list[list[dict]]:
    questions = FACTS["questions"]
    real = [q for q in questions if q["category"] != "false_memory"]
    traps = [q for q in questions if q["category"] == "false_memory"]
    batches: list[list[dict]] = []
    index = 0
    while index < len(real):
        batches.append(real[index : index + QUESTIONS_PER_QUIZ])
        index += QUESTIONS_PER_QUIZ
    # distribute exactly one trap per batch from the front; extras get their own batches
    for pos, trap in enumerate(traps):
        if pos < len(batches):
            batches[pos].append(trap)
        else:
            batches.append([trap])
    return batches


QUIZ_PREAMBLE = (
    "You are answering questions about this project's history for a teammate. Answer ONLY from "
    "this project's recorded memory (use the memory-seed tools and files under .memory-seed/, "
    "plus committed project files). Do NOT guess: if something was never recorded, say exactly "
    "that it is not recorded. Checking whether something is true by reading the source code or a "
    "config file directly is not the same as it being a recorded decision - if you had to inspect "
    "a file to answer rather than recall a decision, that means it was NOT recorded; report it as "
    "not recorded rather than asserting what you found. Do not modify any files and do not append "
    "any session entries - this is a read-only consultation. Answer each question in 1-3 "
    "sentences, numbered.\n\n"
)


def strip_index_facts(copy_dir: Path) -> bool:
    """Blank `## Active State` in the copy's index.md, leaving the rest of the file intact.

    The retrieval-only arm. Every seeded answer lives in that one section - the maintainer roster,
    benchmark ownership, the 1.2us baseline, the release cadence - and nothing outside it leaks a
    fact, which was checked term by term before this was written.

    The file is kept rather than deleted on purpose: `AGENTS.md` treats a missing index.md as "seeded
    but not bootstrapped" and sends the agent into bootstrap mode, which would have it try to REBUILD
    the index instead of answering questions. Blanking one section leaves a normally-bootstrapped
    project whose durable facts simply are not written down anywhere except the session entries.
    """
    index = copy_dir / ".memory-seed" / "index.md"
    if not index.exists():
        return False
    lines = index.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    skipping = False
    for line in lines:
        if line.startswith("## Active State"):
            out.append(line)
            out.append("")
            out.append("- Not recorded here. Consult the session memory for current state.")
            out.append("")
            skipping = True
            continue
        if skipping:
            if line.startswith("## "):
                skipping = False
            else:
                continue
        out.append(line)
    index.write_text("\n".join(out) + "\n", encoding="utf-8")
    return True


QUIZ_PREAMBLE_RETRIEVAL_ONLY = (
    "You are answering questions about this project's history for a teammate.\n\n"
    "IMPORTANT - how you may look things up. Use ONLY the memory-seed MCP tools: `memory_search` "
    "to find relevant decisions and `memory_get_chunk` to read one in full. Do NOT open, read, "
    "grep or list any file under `.memory-seed/` - not the session logs, not index.md, not the "
    "skills. This run measures whether retrieval alone surfaces what you need, so reading the "
    "store directly would silently answer a different question. Committed project files outside "
    "`.memory-seed/` (README, source) remain fair game.\n\n"
    "Do NOT guess: if something was never recorded, say exactly that it is not recorded. Do not "
    "modify any files and do not append any session entries - this is a read-only consultation. "
    "Answer each question in 1-3 sentences, numbered.\n\n"
)


def phase_quiz(jobs: int = 3, no_index_facts: bool = False, retrieval_only: bool = False) -> None:
    if not WORKSPACE.exists():
        raise SystemExit("no seeded workspace - run the seed phase first")
    batches = quiz_batches()
    answers_dir = RUNS / "answers"
    answers_dir.mkdir(exist_ok=True)

    def one(batch_index: int, batch: list[dict]) -> dict:
        copy_dir = RUNS / f"quiz-{batch_index:02d}"
        if copy_dir.exists():
            rmtree_force(copy_dir)
        shutil.copytree(WORKSPACE, copy_dir)
        if no_index_facts:
            strip_index_facts(copy_dir)
        brief = QUIZ_PREAMBLE + "\n".join(
            f"{n+1}. {q['question']}" for n, q in enumerate(batch)
        )
        # Instruction alone did not hold: told explicitly not to read files under .memory-seed/,
        # all 8 batches did anyway - 16 Grep and 13 Read calls against 19 memory_search. So the
        # retrieval-only arm denies the tools rather than asking. `tools_used` records what was
        # actually called, because an instruction whose compliance nobody measures is a wish.
        out = run_claude(
            copy_dir,
            brief,
            extra=["--disallowedTools", "Read", "Grep", "Glob", "LS", "Bash"] if retrieval_only else None,
        )
        payload = {
            "batch": batch_index,
            "exit": out["exit"],
            "question_ids": [q["id"] for q in batch],
            "questions": [q["question"] for q in batch],
            "answer_text": out["result"],
            "tools_used": out.get("tools", []),
        }
        (answers_dir / f"batch-{batch_index:02d}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        rmtree_force(copy_dir)
        return payload

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(one, i, b): i for i, b in enumerate(batches)}
        for future in as_completed(futures):
            result = future.result()
            print(f"quiz batch {result['batch']} exit={result['exit']} "
                  f"ids={','.join(result['question_ids'])}", flush=True)
    print("answers in", answers_dir)


def phase_judge() -> None:
    if not CODEX:
        raise SystemExit("codex CLI not found")
    by_id = {q["id"]: q for q in FACTS["questions"]}
    answers_dir = RUNS / "answers"
    items = []
    for path in sorted(answers_dir.glob("batch-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for qid in payload["question_ids"]:
            items.append({
                "id": qid,
                "question": by_id[qid]["question"],
                "expected": by_id[qid]["expected"],
                "answer_text": payload["answer_text"],
            })

    verdicts = []
    chunk = 6
    for start in range(0, len(items), chunk):
        group = items[start : start + chunk]
        prompt = (
            "Judge each question below. You get the question, the EXPECTED answer (ground "
            "truth), and the responding agent's full numbered reply text (find the answer to "
            "this question inside it).\n\nVerdicts:\n"
            "- correct: the reply's answer to this question matches the expected answer in "
            "substance (wording may differ)\n"
            "- not_addressed: the reply does not answer this question, or says the information "
            "is not recorded WHEN the expected answer is ABSTAIN counts as correct instead\n"
            "- incorrect: answers with wrong information (not matching expected)\n"
            "- outdated: gives a superseded/old value where expected asks for the current one\n"
            "- fabricated: expected is ABSTAIN but the reply asserts specific invented "
            "information as fact\n\n"
            "IMPORTANT: when expected is 'ABSTAIN - never discussed or recorded', a reply that "
            "says it is not recorded/unknown is CORRECT; a reply inventing specifics is "
            "FABRICATED; a hedged reply that still asserts a specific invented value is "
            "FABRICATED.\n\nReturn one verdict per id.\n\n"
            + json.dumps(group, ensure_ascii=False, indent=1)
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            schema_file = tmp_path / "schema.json"
            schema_file.write_text(json.dumps(JUDGE_SCHEMA), encoding="utf-8")
            out_file = tmp_path / "out.json"
            escaped = str(tmp_path).replace("\\", "\\\\")
            completed = subprocess.run(
                [CODEX, "exec", "-C", str(tmp_path), "-s", "read-only",
                 "--skip-git-repo-check",
                 "-c", "features.apps=false",
                 "-c", f'projects={{ "{escaped}" = {{ trust_level = "trusted" }} }}',
                 "-c", 'approval_policy="never"',
                 "--output-schema", str(schema_file), "-o", str(out_file), "-"],
                input=prompt, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=600,
            )
            if completed.returncode != 0 or not out_file.exists():
                raise SystemExit(f"judge failed on chunk {start}: {completed.stderr[-400:]}")
            verdicts.extend(json.loads(out_file.read_text(encoding="utf-8"))["verdicts"])
        print(f"judged {min(start + chunk, len(items))}/{len(items)}", flush=True)

    (RUNS / "verdicts.json").write_text(
        json.dumps(verdicts, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("verdicts written")


def phase_score() -> None:
    by_id = {q["id"]: q for q in FACTS["questions"]}
    verdicts = json.loads((RUNS / "verdicts.json").read_text(encoding="utf-8"))
    from collections import defaultdict

    table: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for verdict in verdicts:
        category = by_id[verdict["id"]]["category"]
        table[category][verdict["verdict"]] += 1
        table[category]["n"] += 1

    print(f"{'category':20} {'n':>3} {'correct':>8} {'not_addr':>9} {'incorrect':>10} "
          f"{'outdated':>9} {'fabricated':>11}")
    total_correct = total_n = fabricated = 0
    for category in ("direct_recall", "updated_facts", "thread_growth", "synthesis",
                     "long_term_retention", "false_memory"):
        row = table[category]
        print(f"{category:20} {row['n']:>3} {row['correct']:>8} {row['not_addressed']:>9} "
              f"{row['incorrect']:>10} {row['outdated']:>9} {row['fabricated']:>11}")
        total_correct += row["correct"]
        total_n += row["n"]
        fabricated += row["fabricated"]
    blended = 100.0 * total_correct / total_n if total_n else 0.0
    print(f"\nblended: {total_correct}/{total_n} = {blended:.1f}")
    print(f"fabrications: {fabricated}")
    print("kill condition (do not submit below Zep 75.1):",
          "CLEAR" if blended >= 75.1 else "TRIGGERED")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("seed", "quiz", "judge", "score"))
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--retrieval-only", action="store_true",
                        help="instruct agents to use ONLY memory_search/memory_get_chunk; tool use is recorded so compliance is checked, not trusted")
    parser.add_argument("--no-index-facts", action="store_true",
                        help="quiz with index.md's Active State blanked, so memory_search "
                             "is the only route to an answer")
    args = parser.parse_args()
    {"seed": phase_seed, "quiz": lambda: phase_quiz(args.jobs, args.no_index_facts, args.retrieval_only),
     "judge": phase_judge, "score": phase_score}[args.phase]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
