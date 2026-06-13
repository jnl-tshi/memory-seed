"""SessionStart hook: inject current project state deterministically.

Fires once when a session begins. Reads the newest dated session log directly
(by filename date) and injects its content — the file path, every entry heading,
and the full body of the most recent entry — so the agent knows the current state
without any follow-up read. This is deliberately NOT a "go read the file" nudge:
the orientation that semantic search loses (the newest entry can rank below older
topically-similar ones) is delivered as self-sufficient context instead.

Per-agent output uses each platform's documented SessionStart context field.
No throttle stamp: SessionStart already fires once per session. stdin is not
read, so the script is also runnable by hand for verification.
"""

import json
import re
import sys
from pathlib import Path

# Cap on how much of the most recent entry body to inject, so a long entry
# cannot blow up session context. Headings (one line each) are always included.
LATEST_ENTRY_CHAR_CAP = 1500

agent = "claude"
for arg in sys.argv[1:]:
    if arg.startswith("--"):
        agent = arg[2:]

sessions = Path(".memory-seed/sessions")
if not sessions.exists():
    sys.exit(0)

# Newest-by-date: session filenames are YYYY-MM-DD.md, so a lexical sort is a
# date sort. mtime breaks ties for same-named edge cases. Ignore .gitkeep etc.
date_re = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")
files = sorted(
    (p for p in sessions.glob("*.md") if date_re.match(p.name)),
    key=lambda p: (p.name, p.stat().st_mtime),
)
if not files:
    sys.exit(0)

newest = files[-1]
prior = files[-2] if len(files) > 1 else None

text = newest.read_text(encoding="utf-8")
lines = text.splitlines()

# Entry headings are timestamped "## YYYY-MM-DD HH:MM ..." lines; list them
# oldest->newest. The strict pattern (matching session-log-check.py) avoids
# mistaking a "## " line inside an entry body for an entry boundary.
entry_re = re.compile(r"^## \d{4}-\d{2}-\d{2} \d{2}:\d{2}\b")
heading_idx = [i for i, ln in enumerate(lines) if entry_re.match(ln)]
headings = [lines[i][3:].strip() for i in heading_idx]

# Most recent entry = from the last "## " heading to end of file.
if heading_idx:
    latest_entry = "\n".join(lines[heading_idx[-1]:]).strip()
else:
    latest_entry = text.strip()
if len(latest_entry) > LATEST_ENTRY_CHAR_CAP:
    latest_entry = (
        latest_entry[:LATEST_ENTRY_CHAR_CAP].rstrip()
        + "\n... [truncated - read the file for the rest]"
    )

parts = [
    "CURRENT PROJECT STATE - injected at session start from the newest session "
    "log (read directly by date, not via search).",
    "",
    f"Newest session file: .memory-seed/sessions/{newest.name} "
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
if prior is not None:
    parts.append("")
    parts.append(
        f"Prior session file: .memory-seed/sessions/{prior.name} "
        "(read it directly if you need more history)."
    )
parts.append("")
parts.append(
    "Recency vs. topical retrieval: the above is the latest recorded work. To "
    "answer 'what is the latest / current state', read the newest "
    ".memory-seed/sessions/*.md files directly by date - do NOT use memory_search "
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
