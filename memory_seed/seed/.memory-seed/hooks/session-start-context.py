"""SessionStart hook: inject current project state deterministically.

Fires once when a session begins. Reads the newest relevant session log directly
(by filename date) and injects its content so the agent knows the current state
without any follow-up read. With a configured user, the hook orients on that
user's newest per-user session file and lists same-day co-contributor files.
Without a configured user, it preserves the legacy flat-file behavior.
"""

import json
import os
import re
import sys
from pathlib import Path

# Cap on how much of the most recent entry body to inject, so a long entry
# cannot blow up session context. Headings (one line each) are always included.
LATEST_ENTRY_CHAR_CAP = 1500
RESERVED_USERS = {"index", "readme", "policy"}

agent = "claude"
for arg in sys.argv[1:]:
    if arg.startswith("--user="):
        continue
    if arg.startswith("--"):
        agent = arg[2:]

sessions = Path(".memory-seed/sessions")
if not sessions.exists():
    sys.exit(0)

date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
flat_date_re = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")
user_re = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
entry_re = re.compile(r"^## \d{4}-\d{2}-\d{2} \d{2}:\d{2}\b")


def valid_user(value):
    return bool(value and user_re.match(value) and value not in RESERVED_USERS)


def configured_user():
    explicit = None
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg.startswith("--user="):
            explicit = arg.split("=", 1)[1]
        elif arg == "--user" and i + 1 < len(args):
            explicit = args[i + 1]
    if valid_user(explicit):
        return explicit
    env_user = os.environ.get("MEMORY_SEED_USER")
    if valid_user(env_user):
        return env_user
    local = Path(".memory-seed/local.yaml")
    if local.exists():
        try:
            for line in local.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("user:"):
                    value = stripped.split(":", 1)[1].strip().strip("'\"")
                    if valid_user(value):
                        return value
        except (OSError, UnicodeDecodeError):
            return None
    return None


def heading_count(path):
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if entry_re.match(line))


def session_docs():
    docs = []
    for path in sessions.iterdir():
        if path.is_file() and flat_date_re.match(path.name):
            docs.append({
                "path": path,
                "date": path.stem,
                "user": None,
                "rel": f".memory-seed/sessions/{path.name}",
            })
            continue
        if not path.is_dir() or not date_re.match(path.name):
            continue
        for child in path.iterdir():
            if not child.is_file() or child.suffix != ".md":
                continue
            user = child.stem
            if not valid_user(user):
                continue
            docs.append({
                "path": child,
                "date": path.name,
                "user": user,
                "rel": f".memory-seed/sessions/{path.name}/{child.name}",
            })
    return sorted(docs, key=lambda doc: (doc["date"], doc["user"] or "", doc["path"].stat().st_mtime))


def extract_latest_entry(text):
    lines = text.splitlines()
    heading_idx = [i for i, ln in enumerate(lines) if entry_re.match(ln)]
    headings = [lines[i][3:].strip() for i in heading_idx]
    if heading_idx:
        latest_entry = "\n".join(lines[heading_idx[-1]:]).strip()
    else:
        latest_entry = text.strip()
    if len(latest_entry) > LATEST_ENTRY_CHAR_CAP:
        latest_entry = (
            latest_entry[:LATEST_ENTRY_CHAR_CAP].rstrip()
            + "\n... [truncated - read the file for the rest]"
        )
    return headings, latest_entry


docs = session_docs()
user = configured_user()
if user:
    candidates = [doc for doc in docs if doc["user"] == user]
else:
    candidates = [doc for doc in docs if doc["user"] is None]

if not candidates:
    sys.exit(0)

newest = candidates[-1]
prior = candidates[-2] if len(candidates) > 1 else None

text = newest["path"].read_text(encoding="utf-8")
headings, latest_entry = extract_latest_entry(text)

parts = [
    "CURRENT PROJECT STATE - injected at session start from the newest session "
    "log (read directly by date, not via search).",
    "",
    f"Newest session file: {newest['rel']} "
    f"({len(headings)} entr{'y' if len(headings) == 1 else 'ies'}).",
]
if headings:
    parts.append("")
    parts.append("Entry headings (oldest first, newest last):")
    parts.extend(f"- {h}" for h in headings)
parts.append("")
parts.append("Most recent entry (verbatim):")
parts.append("")
parts.append(latest_entry)

if user:
    contributors = [
        doc for doc in docs
        if doc["date"] == newest["date"] and doc["user"] is not None and doc["user"] != user
    ]
    if contributors:
        parts.append("")
        parts.append(f"Co-contributor session files for {newest['date']}:")
        for doc in contributors:
            count = heading_count(doc["path"])
            parts.append(f"- {doc['rel']} ({count} entr{'y' if count == 1 else 'ies'})")

if prior is not None:
    parts.append("")
    parts.append(
        f"Prior session file: {prior['rel']} "
        "(read it directly if you need more history)."
    )
parts.append("")
parts.append(
    "Recency vs. topical retrieval: the above is the latest recorded work. To "
    "answer 'what is the latest / current state', read the newest "
    ".memory-seed/sessions files directly by date - do NOT use memory_search "
    "to find the most recent work, because semantic/lexical ranking can bury the "
    "newest entry beneath older topically-similar ones. Use memory_search only for "
    "topical questions ('why was X decided', 'what do we know about Y')."
)

context = "\n".join(parts)

if agent == "cursor":
    # Cursor sessionStart: additional_context (snake_case) injects into context.
    print(json.dumps({"additional_context": context}))
elif agent == "gemini":
    # Gemini CLI SessionStart: hookSpecificOutput.additionalContext.
    print(json.dumps({"hookSpecificOutput": {"additionalContext": context}}))
elif agent == "codex":
    # Codex CLI SessionStart: hookSpecificOutput.additionalContext.
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }))
else:
    # Claude Code SessionStart: hookSpecificOutput.additionalContext.
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }))
