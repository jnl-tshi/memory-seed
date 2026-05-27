import json
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

reminder = (
    "MEMORY RETRIEVAL REMINDER: Before substantive work, retrieve relevant "
    "prior context. Call the memory_search MCP tool, or if MCP is "
    "unavailable read the two most recent .memory-seed/sessions/*.md files. "
    "Do this before editing code or making decisions so you build on past "
    "work instead of repeating it."
)

if agent == "codex":
    # Codex CLI UserPromptSubmit: systemMessage shown in UI
    print(json.dumps({"systemMessage": reminder, "continue": True}))
elif agent == "cursor":
    # Cursor sessionStart: additional_context (snake_case) injects into the
    # conversation's initial system context. beforeSubmitPrompt cannot inject.
    print(json.dumps({"additional_context": reminder}))
elif agent == "gemini":
    # Gemini CLI UserPromptSubmit: additionalContext injected into model context
    print(json.dumps({"additionalContext": reminder}))
else:
    # Claude Code UserPromptSubmit: additionalContext is the valid field
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": reminder,
        }
    }))
