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


def participant_count():
    path = Path(".memory-seed/project.yaml")
    if not path.exists():
        return 0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return 0
    count = 0
    in_participants = False
    for raw in lines:
        line = raw.rstrip()
        if re.match(r"^participants\s*:", line):
            in_participants = True
            continue
        if not in_participants:
            continue
        if line and not line[0].isspace():
            break
        if re.match(r"^\s*-\s*slug\s*:", line):
            count += 1
    return count


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
    two_or_more_participants = participant_count() >= 2
    env_user = os.environ.get("MEMORY_SEED_USER")
    if valid_user(env_user):
        return env_user if two_or_more_participants else None
    local = Path(".memory-seed/local.yaml")
    if local.exists():
        try:
            for line in local.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("user:"):
                    value = stripped.split(":", 1)[1].strip().strip("'\"")
                    if valid_user(value):
                        return value if two_or_more_participants else None
        except (OSError, UnicodeDecodeError):
            return None
    return None


def _load_state(path):
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _save_state(path, state):
    try:
        path.write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        pass


user = configured_user()
if user:
    today_file = d / today[:7] / today / f"{user}.md"
    target_label = f".memory-seed/sessions/{today[:7]}/{today}/{user}.md"
else:
    today_file = d / today[:7] / f"{today}.md"
    target_label = f".memory-seed/sessions/{today[:7]}/{today}.md"

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

is_stale = latest is None or latest < cutoff
latest_str = latest.strftime("%Y-%m-%d %H:%M") if latest else None

# Escalation state: the staleness check above is anchored to the last logged
# entry's own timestamp, so it is immune to turn frequency - it fires once
# 15 real minutes have passed since that entry, no matter how many turns ran
# in between. What it cannot detect is whether a fired reminder was actually
# acted on. The state file remembers the latest entry timestamp we last saw
# and how many consecutive stale checks have passed with no new entry
# appearing in between, so a miss that survives one reminder gets a louder,
# harder-to-miss second one instead of repeating identically forever.
state_path = Path(".memory-seed/.session-log-check-state")
state = _load_state(state_path)
if state.get("target") == target_label and state.get("last_seen_entry") == latest_str:
    consecutive_misses = state.get("consecutive_misses", 0)
    if not isinstance(consecutive_misses, int):
        consecutive_misses = 0
else:
    consecutive_misses = 0

if is_stale:
    consecutive_misses += 1
    if consecutive_misses >= 2:
        messages.append(
            f"SESSION LOG REMINDER (repeated - {consecutive_misses} checks in a row with no "
            f"new entry): a prior reminder for {target_label} already fired and nothing new has "
            f"been logged since. Deferring or batching session log writes is a discipline "
            f"failure. Stop and append an entry now covering everything done since the last "
            f"logged entry - this is especially important if the turn ran `git push`, `git "
            f"merge`, deleted or moved files, or made any decision worth remembering."
        )
    else:
        messages.append(
            f"SESSION LOG REMINDER: no entry has been logged in {target_label} in the last 15 "
            f"minutes. Append one now, before this turn ends - not deferred, not batched. This "
            f"applies whenever the turn changed files, ran a git operation (push, merge, "
            f"rebase, delete), or made a decision, however small. D (Decision) and R (Reason) "
            f"are required on every entry; A (Alternatives), F (Files), T (Tests) are optional."
        )
else:
    consecutive_misses = 0

_save_state(
    state_path,
    {"target": target_label, "last_seen_entry": latest_str, "consecutive_misses": consecutive_misses},
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
