import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Paths a git-diff fingerprint must never count as "unlogged work": the act of writing a session
# entry (or its topic/link/diagram sidecars) is itself a git change, and counting it would make
# the hook fire on its own output - a session that just logged would immediately be told to log
# again. The hook's own bookkeeping dotfiles are excluded for the same reason (state, not content).
FINGERPRINT_EXCLUDE_PREFIXES = (".memory-seed/sessions/",)
FINGERPRINT_EXCLUDE_EXACT = {
    ".memory-seed/.session-log-check-state",
    ".memory-seed/.retrieval-log.jsonl",
    ".memory-seed/.file-touch-stamp",
}

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


def _excluded(path_text):
    return path_text in FINGERPRINT_EXCLUDE_EXACT or any(
        path_text.startswith(prefix) for prefix in FINGERPRINT_EXCLUDE_PREFIXES
    )


def _run_git(args):
    try:
        completed = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def diff_fingerprint():
    """Content hash of everything git considers changed, outside the session log itself.

    Deliberately NOT a file-path list: re-editing a file that was already dirty at the last
    baseline must still register as new work, which only a content hash (not a path set) can
    tell apart from "still the same unlogged edit sitting there." Deliberately NOT the raw `git
    diff` text either - that omits untracked (never-added) files entirely, which is exactly the
    shape of a freshly created file like RELEASE.md in the replication run this exists to catch.

    Returns None (fail-open - the caller must skip this check, not treat it as "nothing changed")
    when git is unavailable, this is not a repository, or output cannot be parsed - a hook must
    never turn an environment quirk into a false "you have unlogged work" reminder.
    """
    status = _run_git(["status", "--porcelain", "--untracked-files=all"])
    if status is None:
        return None
    parts = []
    for line in status.splitlines():
        if len(line) < 4:
            continue
        code, path_text = line[:2], line[3:]
        # A rename shows as "R  old -> new"; the new path is what matters going forward.
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1]
        path_text = path_text.strip('"')
        if _excluded(path_text):
            continue
        if "D" in code:
            parts.append(f"{path_text}:DELETED")
            continue
        try:
            digest = hashlib.sha256(Path(path_text).read_bytes()).hexdigest()
        except OSError:
            # Vanished between `git status` and the read, or unreadable - skip rather than fail
            # the whole fingerprint over one file the hook cannot see clearly anyway.
            continue
        parts.append(f"{path_text}:{digest}")
    if not parts:
        return ""
    return hashlib.sha256("\n".join(sorted(parts)).encode("utf-8")).hexdigest()


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
#
# The 15-minute clock has a blind spot the git-diff check below exists to close: a fast
# automated run (a headless seeding session, a scripted batch) can edit real files, decide the
# work doesn't warrant a session entry, and exit - all well inside 15 real minutes. Measured
# directly: a 2026-08-27 replication run made unlogged file changes in 6 of 10 sessions across a
# 13-minute total run, so the staleness clock could not have fired even once regardless of
# whether every check ran correctly.
fingerprint = diff_fingerprint()

state_path = Path(".memory-seed/.session-log-check-state")
state = _load_state(state_path)
entry_advanced = not (state.get("target") == target_label and state.get("last_seen_entry") == latest_str)
if entry_advanced:
    # A new entry appeared (or this is the first check, or the day rolled over): whatever is
    # dirty right now is assumed covered by it. The baseline is the state AFTER logging, not the
    # state at session start - only NEW changes past this point should ever be flagged, per the
    # "trigger off the previous baseline, not the accumulation of differences" rule.
    consecutive_misses = 0
    baseline_fingerprint = fingerprint
else:
    consecutive_misses = state.get("consecutive_misses", 0)
    if not isinstance(consecutive_misses, int):
        consecutive_misses = 0
    baseline_fingerprint = state.get("baseline_diff_fingerprint")

# fingerprint is None when git is unavailable (fail-open: never flag on an environment quirk).
# "" means the tree has nothing dirty outside the session log. Anything else is compared against
# the baseline - re-editing a file already dirty at the baseline still changes its content hash,
# so it counts as new work rather than being silently absorbed into "already known about."
dirty_since_baseline = fingerprint is not None and fingerprint != "" and fingerprint != baseline_fingerprint

if is_stale or dirty_since_baseline:
    consecutive_misses += 1
    if consecutive_misses >= 2:
        messages.append(
            f"SESSION LOG REMINDER (repeated - {consecutive_misses} checks in a row with no "
            f"new entry): a prior reminder for {target_label} already fired and nothing new has "
            f"been logged since. Deferring or batching session log writes is a discipline "
            f"failure, and so is treating outstanding changes as someone else's turn to log - "
            f"whichever turn is running when this fires owns it, and having already written the "
            f"change into the affected file is not a substitute for logging it. Stop and append "
            f"an entry now covering everything done since the last logged entry - a small-work "
            f"entry if there's no real decision, this is especially important if the turn ran "
            f"`git push`, `git merge`, deleted or moved files, or made any decision worth "
            f"remembering."
        )
    elif dirty_since_baseline:
        messages.append(
            f"SESSION LOG REMINDER: there are changes since the last entry in {target_label} "
            f"that no entry covers yet - detected from git, independent of elapsed time, so a "
            f"fast turn cannot slip past it the way it can slip past a 15-minute clock. Append "
            f"one now, before this turn ends - not deferred, not batched, and not skipped "
            f"because the changes predate this turn: whichever turn is running when this fires "
            f"is responsible for logging them, and having already written the change into the "
            f"affected file is not a substitute - the file is what's true now, the entry is why "
            f"and when. If there's no real decision, use the small-work template "
            f"(Summary/Validation/Follow-up); otherwise D and R are required, A/F/T optional."
        )
    else:
        messages.append(
            f"SESSION LOG REMINDER: no entry has been logged in {target_label} in the last 15 "
            f"minutes. Append one now, before this turn ends - not deferred, not batched, and "
            f"not skipped because the outstanding work predates this turn: whichever turn is "
            f"running when this fires is responsible for logging it, and having already written "
            f"the change into the affected file is not a substitute - the file is what's true "
            f"now, the entry is why and when. This applies whenever the turn changed files, ran "
            f"a git operation (push, merge, rebase, delete), or made a decision, however small. "
            f"If there's no real decision, use the small-work template "
            f"(Summary/Validation/Follow-up); otherwise D (Decision) and R (Reason) are required "
            f"on every entry, with A (Alternatives), F (Files), T (Tests) optional."
        )
else:
    consecutive_misses = 0

_save_state(
    state_path,
    {
        "target": target_label,
        "last_seen_entry": latest_str,
        "consecutive_misses": consecutive_misses,
        "baseline_diff_fingerprint": baseline_fingerprint,
    },
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
    # Claude Code Stop hook: `systemMessage` is user-facing UI text only and is
    # never added to the model's context - a Stop hook only reaches the model
    # (and can make it keep going instead of stopping) via `decision: "block"`
    # with `reason` as the text fed back. Verified against
    # memory-retrieval-check.py's UserPromptSubmit branch below, which already
    # gets this right for its own event type.
    print(json.dumps({"decision": "block", "reason": reminder}))
