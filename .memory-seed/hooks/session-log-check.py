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

# Read today's entry timestamps once — used by both checks below.
# File mtime is intentionally not used: a git commit touching the session
# file would defeat a mtime-based staleness check.
heading_re = re.compile(r"^## (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})\b")
today_file = d / f"{today}.md"
stamps = []
if today_file.exists():
    for line in today_file.read_text(encoding="utf-8").splitlines():
        m = heading_re.match(line)
        if m:
            stamps.append(f"{m.group(1)} {m.group(2)}")

# Staleness check: the most recent timestamped entry heading must be within
# the last 15 minutes.
cutoff = datetime.now() - timedelta(minutes=15)
latest = None
for stamp in stamps:
    try:
        t = datetime.strptime(stamp, "%Y-%m-%d %H:%M")
        if latest is None or t > latest:
            latest = t
    except ValueError:
        pass

if latest is None or latest < cutoff:
    messages.append(
        f"SESSION LOG REMINDER: No .memory-seed/sessions/ entry has been "
        f"written in the last 15 minutes. If you completed meaningful work "
        f"this turn, append an entry to .memory-seed/sessions/{today}.md "
        f"now — before this turn ends. "
        f"For decisions, use DRAFT labels: "
        f"D (Decision, required), R (Reason, required), "
        f"A (Alternatives, optional), F (Files, optional), T (Tests, optional)."
    )

# Chronology check: today's entry headings must be in non-decreasing time order.
if any(stamps[i] < stamps[i - 1] for i in range(1, len(stamps))):
    messages.append(
        f"SESSION LOG ORDER WARNING: Entries in "
        f".memory-seed/sessions/{today}.md are not in ascending time "
        f"order. The log is append-only. To repair: move the out-of-order "
        f"entry to the physical end of the file with the current clock "
        f"time; confirm the actual last line before appending rather than "
        f"reusing a remembered anchor (append mode like >> or open(f, 'a') "
        f"avoids the problem where supported). Do not reorder existing "
        f"entries unless the user asks for a repair."
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
    # Gemini CLI AfterAgent: hookSpecificOutput.additionalContext injects context.
    print(json.dumps({"hookSpecificOutput": {"additionalContext": reminder}}))
else:
    # Claude Code Stop hook: systemMessage injects into model context
    print(json.dumps({"systemMessage": reminder}))
