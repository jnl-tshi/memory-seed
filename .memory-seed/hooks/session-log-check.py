"""Turn-end delivery adapter for the canonical session checkpoint evaluator."""

import json
import re
import sys
from pathlib import Path


agent = "claude"
explicit_user = None
args = sys.argv[1:]
for index, arg in enumerate(args):
    if arg.startswith("--user="):
        explicit_user = arg.split("=", 1)[1]
    elif arg == "--user" and index + 1 < len(args):
        explicit_user = args[index + 1]
    elif arg.startswith("--"):
        agent = arg[2:]

try:
    hook_payload = json.loads(sys.stdin.read() or "{}")
except (json.JSONDecodeError, ValueError):
    hook_payload = {}

# VS Code loads both .github/hooks and .claude/settings.json. Copilot's
# lower-camel agentStop entry is for CLI/cloud only; the Claude-compatible
# workspace hook owns the editor event.
if agent == "copilot" and hook_payload.get("hook_event_name"):
    sys.exit(0)

# A blocking host sets this on its forced continuation. Pending debt remains in
# state and will be delivered on a later real turn; a clean advisory was marked
# delivered before the first block, so neither path can loop.
if hook_payload.get("stop_hook_active") or hook_payload.get("stopHookActive"):
    sys.exit(0)

# Source-tree hooks are also executed from temporary fixture projects. Locate
# the checkout package without assuming it exists after installation; installed
# copies simply use the normal import path.
for ancestor in Path(__file__).resolve().parents:
    if (ancestor / "memory_seed" / "session_checkpoint.py").is_file():
        sys.path.insert(0, str(ancestor))
        break

try:
    from memory_seed.session_checkpoint import inspect_checkpoint
except (ImportError, ModuleNotFoundError):
    # Hooks must fail open when the package is unavailable or mid-upgrade.
    sys.exit(0)

result = inspect_checkpoint(
    Path.cwd(),
    deliver_clean_advisory=True,
    explicit_user=explicit_user,
)

messages = []
if result.get("ok") and result.get("pending"):
    evidence = ", ".join(result.get("evidence_kinds") or ["Git"])
    messages.append(
        f"SESSION RECORD CHECKPOINT {result['checkpoint_id']}: {evidence} evidence changed since "
        f"the latest valid entry in {result['target']}. This checkpoint remains pending and repeats "
        "until a new valid session entry clears it. Classify it with the closed rubric: small work "
        "gets Summary/Validation; a new decision gets Decision/Reason; a changed decision gets "
        "lineage-aware records; consequential ambiguity goes to the user. Only deterministically "
        "proven mechanical work may clear without durable memory. For whitespace-only tracked edits "
        "from a clean baseline, inspect then run `memory-seed session checkpoint resolve "
        f"--checkpoint-id {result['checkpoint_id']} --proof whitespace-only`; otherwise append the "
        "session entry before ending the turn."
    )
elif result.get("ok") and result.get("clean_advisory"):
    messages.append(
        f"SESSION RECORD SELF-CHECK: 15 minutes have passed since the latest entry in "
        f"{result['target']} with no changed Git evidence. This is a one-time, non-escalating "
        "self-check only: it creates no record obligation and will not repeat for this entry. If the clean "
        "read-only work produced a meaningful decision, record it; otherwise continue without "
        "writing an entry."
    )

# Chronology remains a direct file invariant, independent of checkpoint debt.
target_text = None
target = Path(str(result.get("target") or ""))
if target.exists():
    try:
        target_text = target.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        target_text = None
if target_text is not None:
    stamps = re.findall(r"^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2})\b", target_text, re.MULTILINE)
    if any(stamps[index] < stamps[index - 1] for index in range(1, len(stamps))):
        messages.append(
            f"SESSION LOG ORDER WARNING: Entries in {result['target']} are not in ascending time "
            "order. The log is append-only. Move only the out-of-order new entry to the physical "
            "end with the current clock time; do not reorder historical entries unless the user "
            "asks for a repair."
        )

if not messages:
    sys.exit(0)

message = "\n".join(messages)
if agent == "copilot":
    print(json.dumps({"decision": "block", "reason": message}))
elif agent == "codex":
    print(json.dumps({"systemMessage": message, "continue": True}))
elif agent == "cursor":
    print(json.dumps({"agentMessage": message}))
elif agent == "gemini":
    print(json.dumps({"hookSpecificOutput": {"additionalContext": message}}))
else:
    # Claude and VS Code Stop hooks only inject model-visible text by blocking
    # once with a reason. Clean advisory consumption is persisted first.
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": message,
                "hookSpecificOutput": {
                    "hookEventName": "Stop",
                    "decision": "block",
                    "reason": message,
                },
            }
        )
    )
