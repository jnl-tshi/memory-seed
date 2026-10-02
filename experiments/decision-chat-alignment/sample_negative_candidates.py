"""Select private historical proposal-like windows for negative-label calibration.

Selection is structural only. Every case has an unknown label and is explicitly
ineligible for the fresh accuracy gate until independently source-reviewed.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Sequence


SEED = "hard-negative-pilot-v1"
PROPOSAL_RE = re.compile(
    r"\b(?:could we|should we|what if|perhaps|maybe|option|proposal|propose|plan|instead)\b",
    re.IGNORECASE,
)


def _load_local(name: str, filename: str) -> Any:
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load {filename}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def proposal_cue(text: str) -> bool:
    return bool(PROPOSAL_RE.search(text))


def causal_window(blocks: Sequence[Any], turn_number: int, max_chars: int) -> list[dict] | None:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    selected = sorted(
        (block for block in blocks if turn_number - 20 <= block.turn_number <= turn_number),
        key=lambda block: block.turn_number,
    )
    if not selected or selected[-1].turn_number != turn_number:
        return None
    rows: list[dict] = []
    chars = 0
    for block in selected:
        messages = []
        omitted_non_dialogue_count = 0
        for item in block.items:
            if item.role not in {"user", "assistant"}:
                omitted_non_dialogue_count += 1
                continue
            if not isinstance(item.source_ordinal, int):
                return None
            chars += len(item.text)
            if chars > max_chars:
                return None  # No silent source clipping.
            messages.append({"role": item.role, "text": item.text,
                             "source_ordinal": item.source_ordinal, "timestamp": item.timestamp})
        rows.append({"turn_number": block.turn_number, "turn_id": block.turn_id,
                     "messages": messages,
                     "omitted_non_dialogue_count": omitted_non_dialogue_count})
    return rows


def choose_turn(root_id: str, blocks: Sequence[Any], max_chars: int) -> dict | None:
    candidates = []
    for block in blocks:
        user_text = "\n".join(item.text for item in block.items if item.role == "user")
        if (block.turn_number < 3 or len(user_text.strip()) < 20
                or len(user_text) > 2000 or not proposal_cue(user_text)):
            continue
        window = causal_window(blocks, block.turn_number, max_chars)
        if window is None or sum(
            any(message["role"] == "user" for message in turn["messages"])
            for turn in window
        ) < 2:
            continue
        key = hashlib.sha256(f"{SEED}:{root_id}:{block.turn_number}".encode()).hexdigest()
        candidates.append((key, block, window))
    if not candidates:
        return None
    _, block, window = min(candidates, key=lambda item: item[0])
    material = json.dumps(window, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "case_id": hashlib.sha256(f"{SEED}:{root_id}:{block.turn_number}".encode()).hexdigest()[:24],
        "root_id": root_id,
        "turn_number": block.turn_number,
        "label": "unknown",
        "exposure": "historical_or_unknown",
        "fresh_gate_eligible": False,
        "source_projection": "verbatim user/assistant messages only; non-dialogue items omitted and counted",
        "source_sha256": hashlib.sha256(material.encode("utf-8")).hexdigest(),
        "window": window,
    }


def build_pilot(snapshot: dict, count: int, max_chars: int) -> dict:
    if count <= 0:
        raise ValueError("count must be positive")
    rows = snapshot.get("rollouts")
    if not isinstance(rows, list):
        raise ValueError("invalid exposure snapshot")
    material = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    if digest != snapshot.get("summary", {}).get("rollout_rows_sha256"):
        raise ValueError("exposure snapshot digest mismatch")
    freeze = _load_local("decision_exposure_freeze", "freeze_exposure.py")
    alignment = freeze._alignment_module()
    # Root sessions only; child and continuation files do not create independent cases.
    root_rows = {}
    for row in rows:
        root_id = row.get("root_session_id")
        if (row.get("lineage_status") == "resolved" and root_id
                and row.get("session_id") == root_id and row.get("parent_thread_id") is None):
            root_rows.setdefault(root_id, []).append(row)
    cases = []
    skipped = {"changed_source": 0, "parse_error": 0, "no_candidate": 0}
    for root_id in sorted(root_rows, key=lambda value: hashlib.sha256(f"{SEED}:{value}".encode()).hexdigest()):
        # A single physical file avoids inventing turn continuity across files.
        if len(root_rows[root_id]) != 1:
            continue
        row = root_rows[root_id][0]
        path = Path(row["source_path"])
        try:
            source_hash, _, stable = freeze._file_digest(path)
            if not stable or source_hash != row["source_sha256"]:
                skipped["changed_source"] += 1
                continue
            meta = alignment.read_session_meta(path)
            if meta is None or meta.rollout_id != row["rollout_id"]:
                skipped["changed_source"] += 1
                continue
            blocks = alignment.parse_rollout(path, meta)
        except (OSError, ValueError, RuntimeError):
            skipped["parse_error"] += 1
            continue
        candidate = choose_turn(root_id, blocks, max_chars)
        if candidate is None:
            skipped["no_candidate"] += 1
            continue
        candidate["rollout_id"] = row["rollout_id"]
        candidate["source_file_sha256"] = source_hash
        cases.append(candidate)
        if len(cases) >= count:
            break
    return {
        "schema_version": 1,
        "purpose": "historical diagnostic prefilter, not gold labels or fresh-gate cases",
        "source_projection": "verbatim user/assistant messages only; omitted non-dialogue counts per turn",
        "selector_seed": SEED,
        "exposure_snapshot_sha256": digest,
        "max_window_chars": max_chars,
        "cases": cases,
        "summary": {"requested": count, "selected": len(cases), "skipped": skipped},
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exposure-snapshot", required=True, type=Path)
    parser.add_argument("--private-output", required=True, type=Path)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--max-window-chars", type=int, default=50000)
    args = parser.parse_args(argv)
    freeze = _load_local("decision_exposure_freeze", "freeze_exposure.py")
    target = freeze.validate_output_path(args.private_output)
    snapshot = json.loads(args.exposure_snapshot.read_text(encoding="utf-8"))
    pilot = build_pilot(snapshot, args.count, args.max_window_chars)
    with target.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(pilot, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
    print(json.dumps(pilot["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
