"""Shared public Reflection Board operations; persistence belongs to the ledger kernel."""
from pathlib import Path
import subprocess
from typing import Any, Mapping

from . import reflection_ledger as ledger


_FIELDS = {
    "trust_init": {"cwd", "apply"},
    "commit_admission": {"cwd"},
    "board_view": {"cwd"},
    "ledger_view": {"cwd", "workstream_id"},
    "ledger_check": {"cwd", "workstream_id"},
    "ledger_init": {"cwd", "retention_days", "apply", "expected_head"},
    "ledger_append": {"cwd", "workstream_id", "role", "chain_id", "relationship", "parents",
        "no_related_thread", "conclusion", "reasoning", "source", "confidence", "to_phase", "apply",
        "expected_head", "expected_ledger_digest"},
    "ledger_close": {"cwd", "workstream_id", "chain_id", "receipts", "apply",
        "expected_head", "expected_ledger_digest"},
    "ledger_rebind": {"cwd", "workstream_id", "source", "reason", "apply"},
    "ledger_prepare": {"cwd", "workstream_id", "apply"},
    "ledger_finalize": {"cwd", "workstream_id", "source", "reason", "apply"},
    "ledger_expire": {"cwd", "workstream_id", "chain_id", "apply"},
}
_REQUIRED = {
    "trust_init": (), "commit_admission": (),
    "board_view": (), "ledger_view": ("workstream_id",), "ledger_check": ("workstream_id",),
    "ledger_init": (), "ledger_append": ("workstream_id", "role", "conclusion", "reasoning", "source"),
    "ledger_close": ("workstream_id", "chain_id"),
    "ledger_rebind": ("workstream_id", "source", "reason"),
    "ledger_prepare": ("workstream_id",),
    "ledger_finalize": ("workstream_id", "source", "reason"),
    "ledger_expire": ("workstream_id", "chain_id"),
}

_DORMANT_ALLOWED = {"commit_admission", "board_view", "ledger_view", "ledger_check"}


def _reflection_board_dormant(root: Path) -> bool:
    """Read the project-level reversible Reflection Board pause setting."""
    path = root / ".memory-seed" / "project.yaml"
    if not path.is_file():
        return False
    return any(line.strip() == "reflection_board: dormant" for line in path.read_text(encoding="utf-8").splitlines())


def _validate(operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
    if operation not in _FIELDS:
        raise ValueError("unknown reflection operation")
    if not isinstance(arguments, dict):
        raise ValueError("reflection arguments must be an object")
    unknown = sorted(set(arguments) - _FIELDS[operation])
    if unknown:
        raise ValueError("unsupported reflection argument(s): " + ", ".join(unknown))
    for key in _REQUIRED[operation]:
        if key not in arguments:
            raise ValueError(f"{key} is required")
    for key, value in arguments.items():
        if key in {"apply", "no_related_thread"}:
            if type(value) is not bool:
                raise ValueError(f"{key} must be a boolean")
        elif key == "retention_days":
            if type(value) is not int or value not in (7, 14, 30):
                raise ValueError("retention_days must be an integer: 7, 14, or 30")
        elif key == "parents":
            if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
                raise ValueError("parents must be an array of record IDs")
        elif key == "receipts":
            if not isinstance(value, list):
                raise ValueError("receipts must be an array of ordinary session mappings")
            for item in value:
                allowed = {"session_path", "entry_id", "decision_id", "disposition", "record_id"}
                if (not isinstance(item, dict) or set(item) - allowed
                        or not (allowed - {"record_id"}) <= set(item)
                        or any(not isinstance(text, str) or not text.strip() for text in item.values())):
                    raise ValueError("each receipt requires session_path, entry_id, decision_id, disposition and optional record_id")
        elif not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a non-empty string")
    return dict(arguments)


def _context(cwd: str) -> tuple[Path, str]:
    root = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    if root.returncode:
        raise ValueError("reflection operations require a Git repository")
    path = Path(root.stdout.strip()).resolve()
    branch = subprocess.run(["git", "-C", str(path), "symbolic-ref", "--quiet", "HEAD"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False).stdout.strip()
    if not branch:
        raise ValueError("reflection operations require an attached local branch")
    return path, branch


def _anchors(args, *, head, digest=None):
    for key, actual, code in (("expected_head", head, "stale_head"),
                               ("expected_ledger_digest", digest, "stale_ledger_digest")):
        if key in args and args[key] != actual:
            raise ledger.ReflectionValidationError(code, "reflection operation",
                "preview identity changed; reload and re-judge", expected=args[key], actual=actual)


def _board(root, branch):
    view = ledger.workstream_board_view(root, trusted_ref=branch)
    items = []
    for item in view.items:
        value = {"path": item.path, "status": item.status, "raw_digest": item.raw_digest,
            "workstream_id": item.workstream_id, "working_branch": item.working_branch,
            "effective_branch": item.effective_branch,
            "diagnostic": item.diagnostic.as_dict() if item.diagnostic else None}
        if item.status == "valid":
            loaded = ledger.load_trusted_workstream_ledger(root, trusted_ref=branch, ledger_path=item.path)
            value["chains"] = ledger.workstream_closed_receipt_status(loaded)
            value["missing_receipts"] = [receipt for chain in value["chains"] for receipt in chain["missing_receipts"]]
            if value["missing_receipts"]:
                value["status"] = "closed_receipts_pending"
        items.append(value)
    return {"ok": view.exit_code == 0, "branch": branch.removeprefix("refs/heads/"), "items": items}


def _close(root, branch, args, loaded):
    chain = args["chain_id"]
    records = [record for record in loaded.ledger.records if record.chain_id == chain]
    if not records:
        raise ValueError("chain_id must identify an existing chain")
    member_ids = {record.record_id for record in records}
    if any(locator.get("record_id", records[0].record_id) not in member_ids for locator in args.get("receipts", [])):
        raise ValueError("receipt record_id is not a member of this chain")
    if records[-1].to_phase == "closed":
        status = next(item for item in ledger.workstream_closed_receipt_status(loaded) if item["chain_id"] == chain)
        required = []
        missing_ids = {item.get("record_id") for item in status["missing_receipts"] if item["kind"] == "member"}
        for locator in args.get("receipts", []):
            drafts = ledger.plan_workstream_chain_receipts(loaded, chain_id=chain,
                **{key: value for key, value in locator.items() if key != "record_id"})
            required.extend(ledger.workstream_receipt_mapping(item) for item in drafts
                            if item.record_id in missing_ids and locator.get("record_id", item.record_id) == item.record_id)
        if args.get("receipts") and any(item["kind"] == "closure" for item in status["missing_receipts"]):
            required.append(ledger.workstream_closure_mapping(records[-1],
                **{key: args["receipts"][-1][key] for key in ("session_path", "entry_id", "decision_id")}))
        return {"ok": True, "operation": "close", "applied": False, "workstream_id": args["workstream_id"],
                "head": loaded.head, "ledger_blob": loaded.ledger_blob,
                "pre_ledger_digest": ledger.workstream_ledger_digest(loaded.raw), "required_receipts": required, **status}
    integration = ledger.GitWorkstreamIntegrationVerifier(loaded)
    witness = integration.witness()
    if loaded.ledger.effective_branch != branch.removeprefix("refs/heads/"):
        raise ValueError("only the effective integration branch may close")
    if records[-1].to_phase != "orchestrate" or len(ledger.workstream_chain_heads(loaded.ledger, chain)) != 1:
        raise ValueError("close requires an orchestrate-phase chain with one resolved head")
    required, covered = {}, []
    for locator in args.get("receipts", []):
        chosen = locator.get("record_id")
        drafts = ledger.plan_workstream_chain_receipts(loaded, chain_id=chain,
            **{key: value for key, value in locator.items() if key != "record_id"})
        if chosen is not None and chosen not in {item.record_id for item in drafts}:
            raise ValueError("receipt record_id is not a member of this chain")
        for draft in drafts:
            if chosen is not None and draft.record_id != chosen:
                continue
            mapping = ledger.workstream_receipt_mapping(draft)
            if draft.record_id in required and required[draft.record_id] != mapping:
                raise ValueError("conflicting receipt mappings for one chain member")
            required[draft.record_id] = mapping
    missing = []
    for record in records:
        mapping = required.get(record.record_id)
        if mapping is None:
            mapping = {"workstream_id": args["workstream_id"], "chain_id": chain, "record_id": record.record_id,
                "detail_digest": record.detail_digest, "receipt_id": ledger.workstream_receipt_id(
                    loaded.ledger.header.id_salt, args["workstream_id"], chain, record.detail_digest),
                "session_path": None, "entry_id": None, "decision_id": None, "disposition": None,
                "receipt_digest": None}
            required[record.record_id] = mapping
            missing.append(mapping)
        else:
            admitted = ledger.committed_workstream_receipt(loaded, mapping)
            if admitted is None:
                missing.append(mapping)
            else:
                covered.append(admitted)
    payload = {"ok": True, "operation": "close", "applied": False, "workstream_id": args["workstream_id"],
        "chain_id": chain, "head": loaded.head, "ledger_blob": loaded.ledger_blob,
        "pre_ledger_digest": ledger.workstream_ledger_digest(loaded.raw),
        "history_fingerprint": loaded.history_fingerprint, "integration_commit": witness.integration_commit,
        "required_receipts": list(required.values()), "missing_receipts": missing,
        "status": "receipts_pending" if missing else "ready_to_close"}
    if missing:
        if args.get("apply", False):
            payload.update(ok=False, error={"code": "receipt", "path": loaded.ledger_path,
                "message": "every existing chain member needs an exact committed receipt", "details": {"missing": missing}})
        return payload
    verifier = ledger.GitWorkstreamReceiptVerifier(loaded, witness.integration_commit)
    preview = ledger.preview_workstream_close_commit(root, trusted_ref=branch,
        workstream_id=args["workstream_id"], chain_id=chain, receipts=covered, receipt_verifier=verifier,
        integration_witness=witness, integration_verifier=integration,
        conclusion=f"Closed reflection chain {chain}", reasoning="Resolved chain with complete durable session receipt coverage.",
        source="ordinary session receipts", confidence="high")
    payload.update(record_id=preview.record_id, post_ledger_digest=preview.post_ledger_digest)
    if args.get("apply", False):
        result = ledger.apply_workstream_commit(root, preview)
        current = ledger.load_trusted_workstream_ledger(root, trusted_ref=branch, ledger_path=loaded.ledger_path)
        status = next(item for item in ledger.workstream_closed_receipt_status(current) if item["chain_id"] == chain)
        payload.update(applied=True, head=result.new_head, **status)
        # Reuse the caller's final ordinary-session destination to draft the
        # two new mappings. They are written by the normal session writer.
        locator = args["receipts"][-1]
        drafts = ledger.plan_workstream_chain_receipts(current, chain_id=chain,
            **{key: value for key, value in locator.items() if key != "record_id"})
        payload["required_receipts"] = [ledger.workstream_receipt_mapping(item) for item in drafts if item.record_id == result.record_id]
        payload["required_receipts"].append(ledger.workstream_closure_mapping(result.ledger.records[-1],
            **{key: locator[key] for key in ("session_path", "entry_id", "decision_id")}))
    return payload


def run_reflection_operation(operation: str, arguments: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Validate, resolve, dispatch and project identically for CLI, MCP and ESR."""
    cwd = "."
    try:
        args = _validate(operation, {} if arguments is None else arguments)
        cwd = args.get("cwd", ".")
        if operation == "commit_admission":
            return {"ok": True, **ledger.reflection_commit_admission(cwd)}
        root, branch = _context(cwd)
        if _reflection_board_dormant(root) and operation not in _DORMANT_ALLOWED:
            return {"ok": False, "error": {"code": "reflection_board_dormant", "path": ".memory-seed/project.yaml",
                "message": "Reflection Board is dormant for this project; read-only inspection remains available", "details": {}}}
        if operation == "trust_init":
            return {"ok": True, **ledger.reflection_trust_init(root, apply=args.get("apply", False))}
        if operation == "board_view":
            return _board(root, branch)
        if operation == "ledger_prepare":
            return {"ok": True, **ledger.prepare_workstream_rebind(root,
                workstream_id=args["workstream_id"], apply=args.get("apply", False))}
        if operation in {"ledger_rebind", "ledger_finalize"}:
            preview, merge_event, handoff_path, handoff_bytes = ledger.preview_integrated_workstream_rebind(
                root, workstream_id=args["workstream_id"], source=args["source"], reason=args["reason"],
                pr=operation == "ledger_finalize")
            result = ledger.apply_integrated_workstream_rebind(root, preview,
                handoff_path=handoff_path, handoff_bytes=handoff_bytes) if args.get("apply", False) else None
            return {"ok": True, "operation": operation.removeprefix("ledger_"),
                "applied": result is not None, "workstream_id": args["workstream_id"],
                "head": result.new_head if result else preview.expected_head, "integration_commit": merge_event,
                "record_id": result.record_id if result else preview.record_id,
                "pre_ledger_digest": preview.pre_ledger_digest, "post_ledger_digest": preview.post_ledger_digest}
        loaded = None
        if operation != "ledger_init":
            loaded = ledger.load_trusted_workstream_ledger(root, trusted_ref=branch,
                ledger_path=ledger.workstream_ledger_path(args["workstream_id"]))
            _anchors(args, head=loaded.head, digest=ledger.workstream_ledger_digest(loaded.raw))
        if operation in {"ledger_view", "ledger_check"}:
            chains = ledger.workstream_closed_receipt_status(loaded)
            return {"ok": True, "workstream_id": loaded.ledger.header.workstream_id, "head": loaded.head,
                "ledger_blob": loaded.ledger_blob, "validation": loaded.validation,
                "ledger": ledger.render_workstream_ledger(loaded.ledger), "chains": chains,
                "status": "closed_receipts_pending" if any(item["missing_receipts"] for item in chains) else "valid"}
        if operation == "ledger_close":
            return _close(root, branch, args, loaded)
        if operation == "ledger_expire":
            preview = ledger.preview_workstream_expiry_commit(root, trusted_ref=branch,
                workstream_id=args["workstream_id"], chain_id=args["chain_id"])
            result = ledger.apply_workstream_commit(root, preview) if args.get("apply", False) else None
            return {"ok": True, "operation": "expire", "applied": result is not None,
                "workstream_id": args["workstream_id"], "chain_id": args["chain_id"],
                "head": result.new_head if result else preview.expected_head,
                "pre_ledger_digest": preview.pre_ledger_digest, "post_ledger_digest": preview.post_ledger_digest,
                "disclosure": ledger.EXPIRY_DISCLOSURE, "git_blobs_remain": True, "privacy_grade_erasure": False}
        if operation == "ledger_init":
            preview = ledger.preview_workstream_init_commit(root, trusted_ref=branch, retention_days=args.get("retention_days", 7))
        else:
            request = ledger.WorkstreamAppendRequest(args["role"], args.get("chain_id"), args.get("relationship", "refines"),
                tuple(args.get("parents", [])), args.get("no_related_thread", False), args["conclusion"], args["reasoning"],
                args["source"], args.get("confidence", "high"), to_phase=args.get("to_phase"))
            preview = ledger.preview_workstream_append_commit(root, trusted_ref=branch, workstream_id=args["workstream_id"], request=request)
        _anchors(args, head=preview.expected_head, digest=preview.pre_ledger_digest)
        result = ledger.apply_workstream_commit(root, preview) if args.get("apply", False) else None
        return {"ok": True, "applied": result is not None, "operation": preview.operation,
            "workstream_id": Path(preview.ledger_path).parent.name,
            "head": result.new_head if result else preview.expected_head,
            "record_id": result.record_id if result else preview.record_id,
            "pre_ledger_digest": preview.pre_ledger_digest,
            "post_ledger_digest": result.post_ledger_digest if result else preview.post_ledger_digest}
    except ledger.ReflectionValidationError as exc:
        return {"ok": False, "error": exc.diagnostic.as_dict()}
    except (ValueError, OSError, TypeError) as exc:
        return {"ok": False, "error": {"code": "invalid_arguments", "path": str(cwd), "message": str(exc), "details": {}}}
