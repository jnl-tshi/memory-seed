import json
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

cutoff = datetime.now() - timedelta(minutes=15)
recent = [
    f for f in d.glob("*.md")
    if datetime.fromtimestamp(f.stat().st_mtime) > cutoff
]
if not recent:
    today = datetime.now().strftime("%Y-%m-%d")
    reminder = (
        f"SESSION LOG REMINDER: No .memory-seed/sessions/ entry has been "
        f"updated in the last 15 minutes. If you completed meaningful work "
        f"this turn, append an entry to .memory-seed/sessions/{today}.md "
        f"now — before this turn ends."
    )
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
