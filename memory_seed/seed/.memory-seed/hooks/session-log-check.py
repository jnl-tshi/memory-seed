import json
import re
import sys
from pathlib import Path
from datetime import datetime, timedelta

agent = "claude"
for arg in sys.argv[1:]:
    if arg.startswith("--"):
        agent = arg[2:]

d = Path(".memory-seed/sessions")
if not d.exists():
    sys.exit(0)

today = datetime.now().strftime("%Y-%m-%d")
messages = []

# Staleness check: nudge a session write if nothing was logged recently.
cutoff = datetime.now() - timedelta(minutes=15)
recent = [
    f for f in d.glob("*.md")
    if datetime.fromtimestamp(f.stat().st_mtime) > cutoff
]
if not recent:
    messages.append(
        f"SESSION LOG REMINDER: No .memory-seed/sessions/ entry has been "
        f"updated in the last 15 minutes. If you completed meaningful work "
        f"this turn, append an entry to .memory-seed/sessions/{today}.md "
        f"now — before this turn ends."
    )

# Chronology check: today's entry headings must be in non-decreasing time order.
heading_re = re.compile(r"^## (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})\b")
today_file = d / f"{today}.md"
if today_file.exists():
    stamps = []
    for line in today_file.read_text(encoding="utf-8").splitlines():
        m = heading_re.match(line)
        if m:
            stamps.append(f"{m.group(1)} {m.group(2)}")
    if any(stamps[i] < stamps[i - 1] for i in range(1, len(stamps))):
        messages.append(
            f"SESSION LOG ORDER WARNING: Entries in "
            f".memory-seed/sessions/{today}.md are not in ascending time "
            f"order. The log is append-only: append new entries at the end "
            f"with the current clock time, never backdated. Do not reorder "
            f"existing entries unless the user asks for a repair."
        )

if not messages:
    sys.exit(0)

reminder = "\n".join(messages)

if agent == "codex":
    # Codex CLI: systemMessage shown in UI
    print(json.dumps({"systemMessage": reminder, "continue": True}))
elif agent == "cursor":
    # Cursor: agentMessage injected into next agent turn
    print(json.dumps({"agentMessage": reminder}))
elif agent == "gemini":
    # Gemini CLI: additionalContext injected into model context
    print(json.dumps({"additionalContext": reminder}))
else:
    # Claude Code Stop hook: systemMessage injects into model context
    print(json.dumps({"systemMessage": reminder}))
