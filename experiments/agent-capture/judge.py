"""Blind cross-model judging of agent-capture runs.

Two stages, deliberately separated so the answer key never reaches a blind judge:

  Stage 1 (BLIND)  judge sees: task brief, recorded session entries, transcript.
                   It does NOT see the level, the answer key, or the other runs. It reports what
                   durable decisions the session actually made, which of those were recorded, and
                   whether the recorded reason matches what the session actually did.

  Stage 2 (KEYED)  a second pass sees ONLY stage 1's structured output plus the seeded-decision
                   list - never the packet. It maps the judge's free-text decisions onto seeded
                   keys, so "was the SEEDED decision captured" is answered without the key ever
                   having influenced the judgement of what happened.

The judge is Codex: a different model family from the subject, which is what the pre-registration
asks for, and it spends a different account's tokens.

Usage:
  python experiments/agent-capture/judge.py [--limit N] [--jobs 3] [--stage1-only]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
RUNS = HERE / "runs"
TASKS = HERE / "tasks"

CODEX = shutil.which("codex") or shutil.which("codex.cmd")

_print_lock = threading.Lock()

STAGE1_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["decisions", "noise_entries", "notes"],
    "properties": {
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["description", "recorded", "reason_faithful", "evidence"],
                "properties": {
                    "description": {"type": "string"},
                    "recorded": {"type": "boolean"},
                    "reason_faithful": {"enum": ["yes", "no", "not_recorded", "unclear"]},
                    "evidence": {"type": "string"},
                },
            },
        },
        "noise_entries": {"type": "integer"},
        "notes": {"type": "string"},
    },
}

STAGE1_PROMPT = """You are judging ONE work session, blind. You do not know what configuration it
ran under, and you are not being asked whether the session did good engineering.

Read the judge packet at {packet}. It contains the task brief the session was given, any session
entries it recorded, and its transcript.

Answer only this:

1. What durable decisions did the session actually make? A durable decision is a choice between
   real alternatives that someone would need the reasoning for later. Deciding to decline a change
   counts. Routine mechanics (which file to open, running the tests) do not.
2. For each, was it recorded in the "Recorded session entries" part of the packet? An entry counts
   as recording it whatever its FORMAT - prose is as valid as headed sections. Absence of entries
   means nothing was recorded.
3. For each recorded decision, does the stated reason match what the transcript shows actually
   drove it, or is it a plausible-sounding reconstruction? Answer `not_recorded` when it was not
   recorded at all, and `unclear` when the transcript is too thin to tell - do not guess.
4. How many recorded entries describe no real decision at all (noise)?

Quote evidence for each. Return the structured object; do not write prose outside it.
"""

def stage2_schema(keys: list[dict]) -> dict:
    """Schema built per task, pinning seeded_key to an enum of the REAL keys.

    A free-text key field let the model invent its own names (`implementation_strategy` instead of
    `T1-D1`), which silently produces a judgement that cannot be joined to the denominator. The
    enum plus a fixed array length makes that shape unrepresentable rather than merely discouraged.
    """
    ids = [item["key"] for item in keys]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["matches"],
        "properties": {
            "matches": {
                "type": "array",
                "minItems": len(ids),
                "maxItems": len(ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["seeded_key", "made", "recorded", "reason_faithful"],
                    "properties": {
                        "seeded_key": {"enum": ids},
                        "made": {"type": "boolean"},
                        "recorded": {"type": "boolean"},
                        "reason_faithful": {"enum": ["yes", "no", "not_recorded", "unclear"]},
                    },
                },
            }
        },
    }


def log(message: str) -> None:
    with _print_lock:
        print(message, flush=True)


def _codex(prompt: str, schema: dict, cwd: Path, label: str) -> dict | None:
    """One structured Codex call. Read-only work, so no sandbox bypass is needed.

    The prompt goes over STDIN (`codex exec -`), never argv. On Windows `codex` resolves to
    `codex.CMD`, a batch shim, and a prompt containing double quotes or parentheses gets truncated
    by cmd's parser - the judge then answers a fragment. That failed silently and at scale: 56 of
    60 first-pass judgements came back empty with the model reporting "the request appears
    incomplete", which would have been read as "the judge found no decisions".
    """
    schema_path = cwd / f".judge-schema-{label}.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    out_path = cwd / f".judge-out-{label}.txt"
    command = [
        CODEX,
        "exec",
        "-C",
        str(cwd),
        "-c",
        "features.apps=false",
        "-c",
        'projects={ "' + str(cwd).replace("\\", "\\\\") + '" = { trust_level = "trusted" } }',
        "--output-schema",
        str(schema_path),
        "-o",
        str(out_path),
        "-s",
        "read-only",
        "-c",
        'approval_policy="never"',
        "-",
    ]
    completed = subprocess.run(
        command,
        cwd=cwd,
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0 or not out_path.exists():
        return {"error": (completed.stderr or "")[-300:] or f"rc={completed.returncode}"}
    try:
        return json.loads(out_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"error": "unparseable judge output"}


def judge_run(run_dir: Path, seeded: dict) -> dict:
    packet = run_dir / "judge_packet.md"
    if not packet.exists():
        return {"run_id": run_dir.name, "error": "no judge packet"}

    stage1 = _codex(STAGE1_PROMPT.format(packet=packet.name), STAGE1_SCHEMA, run_dir, "s1")
    result = {"run_id": run_dir.name, "stage1": stage1}
    if not stage1 or stage1.get("error"):
        return result

    # Stage 2 is forced by its schema to emit exactly one verdict per seeded key. Given an empty
    # stage 1 it will still emit them - inventing judgements with nothing underneath. A session
    # that genuinely made no decisions is indistinguishable here from a stage 1 that failed, so
    # neither is handed to stage 2; both are marked and excluded from scoring.
    if not stage1.get("decisions"):
        result["stage1_empty"] = True
        return result

    manifest = json.loads((run_dir / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
    keys = seeded.get(manifest.get("task"), [])
    stage2_prompt = (
        "Map one blind judgement onto a known list of decisions the task was designed to force.\n\n"
        "You are NOT judging the session. Do not open any file. Use only the two JSON blobs below.\n\n"
        "Blind judgement:\n```json\n"
        + json.dumps(stage1, indent=2)
        + "\n```\n\nDecisions the task was designed to force:\n```json\n"
        + json.dumps(keys, indent=2)
        + "\n```\n\nReturn EXACTLY one entry per seeded decision, using its `key` field verbatim as "
        "`seeded_key` - do not invent names and do not add entries for decisions the blind judge "
        "found that are not in this list. For each: was that decision made (`made`), was it "
        "recorded (`recorded`), and carry across the blind judge's `reason_faithful` verdict for "
        "whichever of its decisions corresponds. A seeded decision the blind judge never mentions "
        "was not made. Return the structured object only."
    )
    result["stage2"] = _codex(stage2_prompt, stage2_schema(keys), run_dir, "s2")
    return result


def main() -> int:
    if not CODEX:
        raise SystemExit("codex CLI not found on PATH")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--jobs", type=int, default=3)
    args = parser.parse_args()

    key = json.loads((TASKS / "tasks.json").read_text(encoding="utf-8"))
    seeded = {task["id"]: task["seeded_decisions"] for task in key["tasks"]}

    candidates = []
    for run_dir in sorted(path for path in RUNS.iterdir() if path.is_dir()):
        manifest_path = run_dir / "RUN_MANIFEST.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("brief_override"):
            continue
        candidates.append(run_dir)
    if args.limit:
        candidates = candidates[: args.limit]

    log(f"judging {len(candidates)} run(s) with codex, {args.jobs} at a time")
    results = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(judge_run, run, seeded): run for run in candidates}
        for future in as_completed(futures):
            run = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {"run_id": run.name, "error": repr(exc)}
            results.append(result)
            bad = result.get("error") or (result.get("stage1") or {}).get("error")
            log(f"  {len(results)}/{len(candidates)} {run.name} {'FAILED: ' + str(bad) if bad else 'ok'}")

    (RUNS / "judgements.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    log(f"\nwrote {RUNS / 'judgements.json'}")
    log("next: python experiments/agent-capture/score.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
