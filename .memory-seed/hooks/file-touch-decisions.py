"""PostToolUse hook: surface recorded decisions whose F: refs name the file just edited.

The trigger half of docs/2_Todo/file-touch-decision-surfacing-proposal.md, built after field
evidence E8 showed the record-side alone cannot carry reversals: agents that reversed a recorded
decision on instruction recorded nothing, and end-of-turn reminders cannot reach a single-turn
headless session at all. This fires MID-turn, at the moment the decision's subject is being
changed - the only point where a headless session can still be influenced.

Deliberately conservative and fail-open: stdlib only, exact path matches only, silent on any
error - a hook failure must never block an edit. Surfaced entry ids are appended to the
retrieval log with tool "file_touch", which attention.py weighs at ZERO by design (a trigger
impression must never inflate the attention score the ranker may one day use).
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WATCHED_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
MAX_DECISIONS = 3
# No character cap: this hook asks the agent to judge whether its edit contradicts a decision, so
# it shows whole decisions. MAX_DECISIONS is what bounds the payload.
STAMP_PATH = Path(".memory-seed/.file-touch-stamp")
LOG_PATH = Path(".memory-seed/.retrieval-log.jsonl")
SESSIONS = Path(".memory-seed/sessions")

HEADING_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) - (.+)$", re.MULTILINE)
ENTRY_ID_RE = re.compile(r"^entry_id: (mse_[a-z0-9]+)\s*$", re.MULTILINE)
MSE_RE = re.compile(r"mse_[a-z0-9]+")
BACKTICK_RE = re.compile(r"`([^`\s]+)`")
LABEL_RE = re.compile(r"^\s*-\s+[A-Z]:")

agent = "claude"
for arg in sys.argv[1:]:
    if arg.startswith("--") and not arg.startswith("--user"):
        agent = arg[2:]


def norm(path_text):
    return path_text.replace("\\", "/").strip().rstrip(".,;")


def touched_path(payload):
    tool = payload.get("tool_name") or ""
    if tool not in WATCHED_TOOLS:
        return None
    raw = (payload.get("tool_input") or {}).get("file_path") or (
        payload.get("tool_input") or {}
    ).get("notebook_path")
    if not raw:
        return None
    candidate = Path(raw)
    try:
        rel = candidate.resolve().relative_to(Path.cwd().resolve())
    except (ValueError, OSError):
        if candidate.is_absolute():
            return None
        rel = candidate
    return norm(str(rel))


def entry_file_refs(body):
    """Conservative F: extraction (mirrors semantic_cache._entry_file_refs)."""
    refs = []
    lines = body.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if re.match(r"^\s*-\s+F:", line):
            block = [line]
            index += 1
            while index < len(lines):
                nxt = lines[index]
                if not nxt.strip() or LABEL_RE.match(nxt) or nxt.startswith("#"):
                    break
                if nxt.startswith((" ", "\t")):
                    block.append(nxt)
                    index += 1
                else:
                    break
            for token in BACKTICK_RE.findall("\n".join(block)):
                if "/" in token or "." in token:
                    refs.append(norm(token))
            continue
        index += 1
    return refs


def iter_entries():
    """Yield (entry_id, heading_line, body) for every entry in the session store."""
    if not SESSIONS.is_dir():
        return
    for path in sorted(SESSIONS.rglob("*.md")):
        parts = {p.lower() for p in path.parts}
        if {"topics", "diagrams"} & parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        headings = list(HEADING_RE.finditer(text))
        for pos, match in enumerate(headings):
            end = headings[pos + 1].start() if pos + 1 < len(headings) else len(text)
            body = text[match.start():end]
            id_match = ENTRY_ID_RE.search(body)
            yield (
                id_match.group(1) if id_match else None,
                match.group(0).lstrip("# ").strip(),
                body,
                "links" in parts,
            )


def replaces_map(all_entries):
    """entry_id -> ids it replaces, from entry YAML and link sidecars (legacy spelling too)."""
    replaced_by = {}
    for entry_id, _heading, body, _is_link in all_entries:
        if not entry_id:
            continue
        for key in ("replaces", "supersedes"):
            for block in re.finditer(
                rf"^{key}:\s*\n((?:\s+-\s+.+\n?)+)", body, re.MULTILINE
            ):
                for target in MSE_RE.findall(block.group(1)):
                    if target != entry_id:
                        replaced_by.setdefault(target, set()).add(entry_id)
    return replaced_by


def decision_text(body):
    """The WHOLE decision content of an entry - never an excerpt.

    This hook asks the agent to rule on whether its edit contradicts a recorded decision, so it
    must not show a fragment. Two ways the old version broke that, both silently:

    - it hard-cut at 420 characters with no ellipsis and no "read the source" pointer, so a
      mid-sentence stop was indistinguishable from the end of the decision;
    - it kept only `- D:` and `- R:` lines, dropping A/F/T even when the entry was well under the
      cap - and `A:` is precisely where a decision records "we considered reversing this", which
      is the most decision-relevant thing an agent about to reverse it could read.

    The bound that keeps this affordable is MAX_DECISIONS, which caps how many decisions are
    surfaced. Capping the middle of each one bought little and cost the evidence.
    """
    lines = [line.rstrip() for line in body.splitlines()]
    # Drop the YAML metadata fence: it is provenance, not decision content, and the old fallback
    # emitted exactly that when an entry had no D:/R: lines.
    if lines and lines[0].strip().startswith("```"):
        for index in range(1, len(lines)):
            if lines[index].strip().startswith("```"):
                lines = lines[index + 1:]
                break
    return "\n".join(lines).strip()


def load_stamp():
    try:
        return json.loads(STAMP_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def log_surfaced(entry_ids):
    if not entry_ids:
        return
    try:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            for entry_id in entry_ids:
                handle.write(
                    json.dumps(
                        {"schema": 1, "ts": now, "tool": "file_touch", "entry_id": entry_id},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
    except OSError:
        pass


def emit(message):
    if agent == "codex":
        print(json.dumps({"systemMessage": message, "continue": True}))
    elif agent == "cursor":
        print(json.dumps({"agentMessage": message}))
    elif agent == "gemini":
        print(json.dumps({"hookSpecificOutput": {"additionalContext": message}}))
    else:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": message,
                    }
                }
            )
        )


def main():
    payload = json.loads(sys.stdin.read() or "{}")
    touched = touched_path(payload)
    if not touched:
        return

    session_id = str(payload.get("session_id") or "unknown")
    stamp = load_stamp()
    seen = stamp.get(session_id) or {}
    if touched in seen:
        return

    all_entries = list(iter_entries())
    matches = []
    for entry_id, heading, body, is_link in all_entries:
        if is_link:
            continue
        refs = entry_file_refs(body)
        if touched in refs or touched.lower() in [r.lower() for r in refs]:
            matches.append((entry_id, heading, body))
    if not matches:
        return

    replaced_by = replaces_map(all_entries)
    lines = [
        f"RECORDED DECISIONS TOUCH THIS FILE ({touched}) - loaded because your edit changed a "
        "file these decisions reference:"
    ]
    surfaced = []
    for entry_id, heading, body in matches[-MAX_DECISIONS:]:
        status = ""
        if entry_id and entry_id in replaced_by:
            heads = ", ".join(sorted(replaced_by[entry_id]))
            status = f" [SUPERSEDED by {heads} - that successor is the live position, not this]"
        lines.append(f"\n### {heading}{status}")
        if entry_id:
            lines.append(f"entry_id: {entry_id}")
            surfaced.append(entry_id)
        lines.append(decision_text(body))
    lines.append(
        "\nIf your current change contradicts or retires any decision above, your session entry "
        "for this turn MUST declare a `replaces` or `evolves` edge to it (three-way rule in "
        ".memory-seed/skills/session_logging.md). A reversal without a superseding entry leaves "
        "the store asserting the opposite of the code."
    )

    seen[touched] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    stamp[session_id] = seen
    try:
        if len(stamp) > 20:  # keep the stamp bounded; oldest sessions age out
            for key in sorted(stamp)[: len(stamp) - 20]:
                del stamp[key]
        STAMP_PATH.write_text(json.dumps(stamp), encoding="utf-8")
    except OSError:
        pass
    log_surfaced(surfaced)
    emit("\n".join(lines))


try:
    main()
except Exception:
    pass
sys.exit(0)
