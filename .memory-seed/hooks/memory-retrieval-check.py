import json
import shutil
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Window between retrieval reminders, so this fires about once per working
# session rather than on every prompt.
REMIND_AFTER_HOURS = 8

agent = "claude"
for arg in sys.argv[1:]:
    if arg.startswith("--"):
        agent = arg[2:]

d = Path(".memory-seed")
if not d.exists():
    sys.exit(0)

stamp = d / ".retrieval-reminder-stamp"
cutoff = datetime.now() - timedelta(hours=REMIND_AFTER_HOURS)
if stamp.exists() and datetime.fromtimestamp(stamp.stat().st_mtime) > cutoff:
    sys.exit(0)

# Record that we are reminding now, so we do not repeat until the window passes.
try:
    stamp.touch()
except OSError:
    pass

_draft = (
    "Record durable decisions using DRAFT labels: "
    "D (Decision, required), R (Reason, required), "
    "A (Alternatives, optional), F (Files, optional), T (Tests, optional)."
)

if shutil.which("memory-seed-mcp") is not None:
    reminder = (
        "MEMORY RETRIEVAL REMINDER: Before substantive work, retrieve relevant "
        "prior context. For topical recall (\"why was X decided\", \"what do we "
        "know about Y\"), call the memory_search MCP tool. To establish the "
        "current/latest state, read the newest .memory-seed/sessions/*.md file "
        "directly by date (the SessionStart hook injects this) rather than "
        "memory_search, whose ranking can bury the newest entry beneath older "
        f"topically-similar ones. {_draft}"
    )
else:
    reminder = (
        "MEMORY RETRIEVAL REMINDER: memory-seed-mcp is not on PATH — the "
        "memory_search tool is unavailable. To fix: run "
        "`uv tool install memory-seed` (or `pip install memory-seed`), then "
        "restart your editor. For now, read the newest "
        f".memory-seed/sessions/*.md files directly by date before substantive work. {_draft}"
    )

if agent == "codex":
    # Codex CLI UserPromptSubmit: systemMessage shown in UI.
    # Project .codex/config.toml MCP servers load only for trusted directories.
    codex_reminder = (
        reminder + " (Codex loads the project memory_search MCP server from "
        ".codex/config.toml only if this directory is trusted.)"
    )
    print(json.dumps({"systemMessage": codex_reminder, "continue": True}))
elif agent == "cursor":
    # Cursor sessionStart: additional_context (snake_case) injects into the
    # conversation's initial system context. beforeSubmitPrompt cannot inject.
    print(json.dumps({"additional_context": reminder}))
elif agent == "gemini":
    # Gemini CLI BeforeAgent: hookSpecificOutput.additionalContext injects context.
    print(json.dumps({"hookSpecificOutput": {"additionalContext": reminder}}))
else:
    # Claude Code UserPromptSubmit: additionalContext is the valid field
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": reminder,
        }
    }))
