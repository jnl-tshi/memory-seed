import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime, timedelta

agent = "claude"
for arg in sys.argv[1:]:
    if arg.startswith("--user="):
        continue
    if arg.startswith("--"):
        agent = arg[2:]

d = Path(".memory-seed/sessions")
if not d.exists():
    sys.exit(0)

today = datetime.now().strftime("%Y-%m-%d")
messages = []
user_re = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
reserved_users = {"index", "readme", "policy"}


def valid_user(value):
    return bool(value and user_re.match(value) and value not in reserved_users)


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


user = configured_user()
if user:
    today_file = d / today / f"{user}.md"
    target_label = f".memory-seed/sessions/{today}/{user}.md"
else:
    today_file = d / f"{today}.md"
    target_label = f".memory-seed/sessions/{today}.md"

# Read today's entry timestamps once — used by both checks below.
# File mtime is intentionally not used: a git commit touching the session
# file would defeat a mtime-based staleness check.
heading_re = re.compile(r"^## (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})\b")
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
        f"this turn, append an entry to {target_label} "
        f"now — before this turn ends. "
        f"For decisions, use DRAFT labels: "
        f"D (Decision, required), R (Reason, required), "
        f"A (Alternatives, optional), F (Files, optional), T (Tests, optional)."
    )

# Chronology check: today's entry headings must be in non-decreasing time order.
if any(stamps[i] < stamps[i - 1] for i in range(1, len(stamps))):
    messages.append(
        f"SESSION LOG ORDER WARNING: Entries in "
        f"{target_label} are not in ascending time "
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
