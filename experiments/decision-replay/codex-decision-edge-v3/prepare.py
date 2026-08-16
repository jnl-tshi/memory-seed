"""Prepare a sealed, randomized Codex decision-edge replay run."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import random
import re
import shutil
import tempfile
import textwrap
from pathlib import Path

from common import (
    ARMS,
    BLOCK_COUNT,
    DECISIVE_PHRASE,
    CODEX_CONTRACT_PATH,
    HERE,
    RELEVANT_ENTRY_ID,
    REPO_ROOT,
    SOURCE_REVISION,
    TASK_PATH,
    assert_cross_arm_equality,
    assert_no_decisive_phrase,
    dated_session_documents,
    export_source,
    initialize_fixture,
    primary_checkout_root,
    sanitize_source,
    sha256_bytes,
    sha256_file,
    strip_dated_session_memory,
    tree_digest,
    tree_hashes,
    verify_source_relationship,
    write_json,
)

PUBLIC_TEST_COMMAND = "python RUN_TASK_TESTS.py"
SUBJECT_PROMPT = (
    "Read CODEX_EXPERIMENT_CONTRACT.md, then EXPERIMENT_CONTEXT.md, then TASK.md and implement it. "
    "Stay inside this repository and obey its experimental constraints."
)
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

BOUNDED_D2_PROJECTION = textwrap.dedent(
    f"""\
    Source: `.memory-seed/sessions/2026-07/2026-07-21.md`, entry
    `{RELEVANT_ENTRY_ID}:d2`, recorded before the withheld implementation.

    ### Summary

    - Drafted `docs/3_Spec/draft/decision-level-link-sidecar-refs.md`: link-sidecar refs that terminate on
      a specific decision rather than a whole entry. Spec only, nothing implemented.

    ### D2 - Decision edges are a distinct edge set, never projected up to entry level

    - D: A decision edge is not unioned into the entry-level `supersedes`/`evolves` lists. Consumers that do
      not model decisions ignore them entirely, exactly as they already ignore `classify_pending` stubs and
      `edge_status: not_applicable`.
    - R: {DECISIVE_PHRASE} - that overstatement is the whole
      reason the feature exists, so projecting decision edges upward at the read layer would reintroduce at
      the reader precisely what the format was designed to stop the author doing. The compatibility story is
      better this way too: existing consumers see exactly the edge set they see today, so nothing regresses
      and nothing inflates. The alternative - project up for compatibility - buys visibility in old surfaces
      at the cost of making the graph assert things no one wrote.
    - A: This is the load-bearing rule of the draft; if it is ever relaxed the feature becomes a worse version
      of what already exists.

    ### Validation

    - `memory-seed docs check`: 167 files, lifecycle OK, 14 pre-existing warnings, none on the new file.
      `docs index` already current. Back-compat verified by grep: no decision-shaped ref exists anywhere under
      `.memory-seed/sessions/links/**` as of today, so the parser change cannot silently reinterpret existing
      data.

    ### Follow-up

    - Three open questions are recorded in the draft rather than answered: whether `link audit` can suggest
      decision-level candidates at all (its evidence is file/topic overlap, both entry-scoped, so it may have
      no signal that discriminates between decisions of one entry); whether ESR should count decision edges
      separately; and whether `related_entries` is worth extending to decisions.
    - Implementation touches four points when it happens: extraction (`core.py:724`), validation
      (`core.py:1810-1826`), parse (`retrieval.py:372`), attachment (`service.py:2587`).
    """
)
PUSHED_CONTEXT_BODY = "## Bounded pre-fix historical rationale\n\n" + BOUNDED_D2_PROJECTION


def _neutral_context_body() -> str:
    """Build semantically inert padding with the pushed body's exact bytes/tokens."""

    prefix = (
        "## Neutral control material\n\n"
        "No supplemental material is supplied. The remainder is inert size padding only.\n\n"
    )
    target_bytes = len(PUSHED_CONTEXT_BODY.encode("utf-8"))
    target_tokens = len(PUSHED_CONTEXT_BODY.split())
    padding_tokens = target_tokens - len(prefix.split())
    if padding_tokens < 1:
        raise RuntimeError("pushed context is too short for neutral padding")
    minimum_padding_bytes = (padding_tokens * 2)
    remaining_bytes = target_bytes - len(prefix.encode("utf-8"))
    extra = remaining_bytes - minimum_padding_bytes
    if extra < 0:
        raise RuntimeError("neutral padding prefix cannot fit target context dimensions")
    quotient, remainder = divmod(extra, padding_tokens)
    tokens = ["x" * (1 + quotient + (index < remainder)) for index in range(padding_tokens)]
    body = prefix + " ".join(tokens) + "\n"
    if len(body.encode("utf-8")) != target_bytes or len(body.split()) != target_tokens:
        raise RuntimeError("neutral context padding did not reach exact dimensions")
    return body


NEUTRAL_CONTEXT_BODY = _neutral_context_body()


def _context_receipt(seed: int, run_id: str, subject_id: str) -> str:
    payload = f"codex-decision-edge-v3:{seed}:{run_id}:{subject_id}:receipt".encode()
    return "ctx_" + hashlib.sha256(payload).hexdigest()[:24]


def _subject_id(seed: int, run_id: str, block_number: int, slot: int) -> str:
    payload = f"codex-decision-edge-v3:{seed}:{run_id}:{block_number}:{slot}".encode()
    return "subject-" + hashlib.sha256(payload).hexdigest()[:16]


def context_document(*, pushed: bool, receipt: str) -> str:
    """Render both packet kinds through one wrapper; only the evidence body varies."""

    evidence = PUSHED_CONTEXT_BODY if pushed else NEUTRAL_CONTEXT_BODY
    header = (
        "# Experiment context\n\n"
        f"Read `{CODEX_CONTRACT_PATH.as_posix()}` first, then this file before `TASK.md`. This packet is\n"
        "experimental evidence, not authorization to edit beyond the task's stated boundary.\n\n"
        f"CONTEXT_RECEIPT: {receipt}\n\n"
        f"Candidate validation command: `{PUBLIC_TEST_COMMAND}`\n"
        "The pristine source intentionally lacks that candidate-created module; a missing-module failure\n"
        "is expected before implementation. Reference-patch behavioral qualification belongs to Task 2.\n\n"
    )
    return header + evidence.rstrip() + "\n"


def _write_context(root: Path, *, arm: str, receipt: str) -> dict[str, int | str]:
    document = context_document(pushed=arm == "relevant-rationale-pushed", receipt=receipt)
    path = root / "EXPERIMENT_CONTEXT.md"
    path.write_text(document, encoding="utf-8", newline="\n")
    return {
        "sha256": sha256_file(path),
        "bytes": len(document.encode("utf-8")),
        "whitespace_tokens": len(document.split()),
    }


def _artifact_hashes(output_root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(output_root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        relative = path.relative_to(output_root).as_posix()
        if relative == "artifact-sha256.json" or "/.git/" in f"/{relative}/":
            continue
        hashes[relative] = sha256_file(path)
    return hashes


def _validate_run_id(run_id: str) -> str:
    if not RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run_id must be 1-64 path-safe ASCII characters")
    return run_id


def prepare_study(
    output_root: Path | None,
    *,
    seed: int,
    run_id: str,
    repo_root: Path = REPO_ROOT,
    blocks: int = BLOCK_COUNT,
) -> dict[str, object]:
    """Create standalone fixtures and manifests; scored/default preparation uses eight blocks."""

    run_id = _validate_run_id(run_id)
    if isinstance(blocks, bool) or not isinstance(blocks, int) or not 1 <= blocks <= BLOCK_COUNT:
        raise ValueError(f"blocks must be an integer from 1 through {BLOCK_COUNT}")
    destination = (
        output_root.resolve()
        if output_root is not None
        else (primary_checkout_root(repo_root) / "f" / f"{run_id}-artifacts").resolve()
    )
    if destination.exists():
        raise FileExistsError(f"refusing existing output root: {destination}")
    relationship = verify_source_relationship(repo_root)
    destination.mkdir(parents=True, exist_ok=False)
    subjects_root = destination / "subjects"
    subjects_root.mkdir()
    sealed_root = destination / "sealed"
    sealed_root.mkdir()

    rng = random.Random(seed)
    task_bytes = TASK_PATH.read_bytes()
    task_sha256 = sha256_bytes(task_bytes)
    subject_records: dict[str, dict[str, object]] = {}
    treatment_delta_records: dict[str, dict[str, object]] = {}
    public_blocks: list[dict[str, object]] = []
    fixture_paths: list[Path] = []

    with tempfile.TemporaryDirectory(prefix=".sanitized-", dir=destination) as temporary:
        sanitized_root = Path(temporary) / "source"
        export_source(sanitized_root, repo_root)
        transformation = sanitize_source(sanitized_root)
        sanitized_digest = tree_digest(tree_hashes(sanitized_root))
        baseline_session_hashes = {
            path.relative_to(sanitized_root).as_posix(): sha256_file(path)
            for path in dated_session_documents(sanitized_root)
        }
        allowed_treatment_paths = sorted(
            {"EXPERIMENT_CONTEXT.md", *baseline_session_hashes.keys()}
        )

        for block_number in range(1, blocks + 1):
            block_id = f"block-{block_number:02d}"
            assignments = list(ARMS)
            rng.shuffle(assignments)
            block_subjects: list[str] = []
            for slot, arm in enumerate(assignments, start=1):
                subject_id = _subject_id(seed, run_id, block_number, slot)
                fixture = subjects_root / subject_id
                shutil.copytree(sanitized_root, fixture)
                removed_session_paths: list[str] = []
                if arm in {"no-dated-memory", "relevant-rationale-pushed"}:
                    removed_session_paths = strip_dated_session_memory(fixture)
                    if set(removed_session_paths) != set(baseline_session_hashes):
                        raise RuntimeError("stripped fixture session delta differed from the baseline set")
                else:
                    retained_hashes = {
                        path.relative_to(fixture).as_posix(): sha256_file(path)
                        for path in dated_session_documents(fixture)
                    }
                    if retained_hashes != baseline_session_hashes:
                        raise RuntimeError("historical fixture did not retain baseline session Markdown")
                (fixture / "TASK.md").write_bytes(task_bytes)
                receipt = _context_receipt(seed, run_id, subject_id)
                context_metrics = _write_context(fixture, arm=arm, receipt=receipt)
                if arm == "no-dated-memory":
                    assert_no_decisive_phrase(fixture)
                retained_session_count = len(dated_session_documents(fixture))
                fixture_commit = initialize_fixture(fixture)
                fixture_digest = tree_digest(tree_hashes(fixture))
                fixture_paths.append(fixture)
                block_subjects.append(subject_id)
                subject_records[subject_id] = {
                    "arm": arm,
                    "block_id": block_id,
                    "fixture_path": str(fixture.resolve()),
                    "fixture_commit": fixture_commit,
                    "fixture_tree_sha256": fixture_digest,
                    "context_receipt": receipt,
                    "context": context_metrics,
                    "removed_dated_session_documents": len(removed_session_paths),
                    "retained_dated_session_documents": retained_session_count,
                }
                treatment_delta_records[subject_id] = {
                    "block_id": block_id,
                    "removed_session_markdown_paths": removed_session_paths,
                    "retained_session_markdown_paths": [
                        path.relative_to(fixture).as_posix()
                        for path in dated_session_documents(fixture)
                    ],
                    "context_sha256": context_metrics["sha256"],
                }
            execution_order = list(block_subjects)
            rng.shuffle(execution_order)
            public_blocks.append(
                {"block_id": block_id, "subject_ids": block_subjects, "execution_order": execution_order}
            )

    neutral_tree_sha256 = assert_cross_arm_equality(
        fixture_paths,
        allowed_treatment_paths=allowed_treatment_paths,
    )
    context_byte_sizes = {record["context"]["bytes"] for record in subject_records.values()}
    context_token_counts = {
        record["context"]["whitespace_tokens"] for record in subject_records.values()
    }
    if len(context_byte_sizes) != 1 or len(context_token_counts) != 1:
        raise RuntimeError("context padding differs across subjects")
    public_manifest = {
        "schema_version": 1,
        "instrument": "codex-decision-edge-v3",
        "run_id": run_id,
        "source_revision": SOURCE_REVISION,
        "task_sha256": task_sha256,
        "subject_prompt_sha256": sha256_bytes(SUBJECT_PROMPT.encode("utf-8")),
        "block_count": blocks,
        "subjects_per_block": len(ARMS),
        "blocks": public_blocks,
        "subjects": {
            subject_id: {
                "block_id": record["block_id"],
                "fixture_path": record["fixture_path"],
                "fixture_commit": record["fixture_commit"],
            }
            for subject_id, record in subject_records.items()
        },
    }
    public_path = destination / "public-manifest.json"
    write_json(public_path, public_manifest)
    treatment_delta_path = sealed_root / "treatment-deltas.json"
    write_json(
        treatment_delta_path,
        {
            "schema_version": 1,
            "run_id": run_id,
            "allowed_treatment_paths": allowed_treatment_paths,
            "baseline_session_markdown_sha256": baseline_session_hashes,
            "subjects": treatment_delta_records,
        },
    )
    sealed_manifest = {
        "schema_version": 1,
        "instrument": "codex-decision-edge-v3",
        "run_id": run_id,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "seed": seed,
        "block_count": blocks,
        **relationship,
        "relevant_entry_id": RELEVANT_ENTRY_ID,
        "decisive_phrase_sha256": sha256_bytes(DECISIVE_PHRASE.encode("utf-8")),
        "sanitized_source_tree_sha256": sanitized_digest,
        "neutral_fixture_tree_sha256": neutral_tree_sha256,
        "transformation_manifest_sha256": sha256_bytes(
            (json.dumps(transformation, indent=2, sort_keys=True) + "\n").encode("utf-8")
        ),
        "context_balance": {
            "bytes": next(iter(context_byte_sizes)),
            "whitespace_tokens": next(iter(context_token_counts)),
            "byte_difference": 0,
            "whitespace_token_difference": 0,
        },
        "treatment_delta_manifest": str(treatment_delta_path.resolve()),
        "subjects": subject_records,
    }
    sealed_path = sealed_root / "condition-map.json"
    write_json(sealed_path, sealed_manifest)
    artifact_path = destination / "artifact-sha256.json"
    write_json(
        artifact_path,
        {"schema_version": 1, "run_id": run_id, "files": _artifact_hashes(destination)},
    )
    return {
        "run_id": run_id,
        "output_root": str(destination),
        "public_manifest": str(public_path),
        "sealed_mapping": str(sealed_path),
        "treatment_deltas": str(treatment_delta_path),
        "artifact_hashes": str(artifact_path),
        "fixture_count": len(fixture_paths),
        "instruction": "Dispatch only from the public manifest; do not open the sealed mapping.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True, help="explicit recorded randomization seed")
    parser.add_argument("--run-id", default=None, help="path-safe identifier; defaults to UTC timestamp")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="caller-owned new directory; default is gitignored f/<run-id>-artifacts",
    )
    args = parser.parse_args()
    run_id = args.run_id or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result = prepare_study(args.output_root, seed=args.seed, run_id=run_id)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
