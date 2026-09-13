"""SessionStart hook: inject measured orientation and a length-gated context route.

The shared ``memory_seed.situate`` report owns checkout and latest-session
measurement. This hook is the automatic forcing function: it directs the host
agent through ``AGENTS.md`` and tells it whether to read the whole latest session
file directly or ask a read-only economy worker to compress that whole file.
It never invokes a model and never injects session-entry bodies.
"""

import json
import os
import sys
from pathlib import Path


def _prefer_checkout_package():
    """Use this checkout's implementation when the hook runs in the source repo."""
    starts = (Path.cwd().resolve(), Path(__file__).resolve().parent)
    seen = set()
    for start in starts:
        for candidate in (start, *start.parents):
            if candidate in seen:
                continue
            seen.add(candidate)
            if (candidate / "memory_seed" / "situate.py").is_file():
                sys.path.insert(0, str(candidate))
                return


_prefer_checkout_package()

agent = "claude"
explicit_user = None
for arg in sys.argv[1:]:
    if arg.startswith("--user="):
        explicit_user = arg.split("=", 1)[1]
        continue
    if arg.startswith("--"):
        agent = arg[2:]


def offer_identity_setup(memory_dir):
    """One-time nudge to configure a local identity; never repeats.

    Fires only when no identity is configured at all (no env var, no
    local.yaml) and the offer hasn't already been made. Writes a stamp file
    on first offer regardless of whether the user accepts, so this is a
    single ask per project, not a per-session reminder.
    """
    if os.environ.get("MEMORY_SEED_USER"):
        return None
    if (memory_dir / "local.yaml").exists():
        return None
    stamp = memory_dir / ".identity-offer-stamp"
    if stamp.exists():
        return None
    try:
        stamp.touch()
    except OSError:
        pass
    return (
        "No local Memory Seed identity is configured for this project "
        "(.memory-seed/local.yaml is absent), so session entries use a generic "
        "user_initials placeholder instead of your name. This is entirely optional "
        "and this offer will not repeat: if you'd like entries to reference you, ask "
        "for a preferred slug/initials/display name, then run `memory-seed user set "
        "<slug>` and add a participants: entry to .memory-seed/project.yaml with "
        "those initials. Not needed for solo work, and configuring it alone does not "
        "split session logs into per-user files - that only happens once a second "
        "participant is registered."
    )


def emit(text):
    if agent == "cursor":
        # Cursor sessionStart: additional_context (snake_case) injects into context.
        print(json.dumps({"additional_context": text}))
    elif agent == "gemini":
        # Gemini CLI SessionStart: hookSpecificOutput.additionalContext.
        print(json.dumps({"hookSpecificOutput": {"additionalContext": text}}))
    elif agent == "codex":
        # Codex CLI SessionStart: hookSpecificOutput.additionalContext.
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": text,
            }
        }))
    else:
        # Claude Code SessionStart: hookSpecificOutput.additionalContext.
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": text,
            }
        }))


parts = [
    "STARTUP ORIENTATION - mandatory, complete before any task action, however small the task "
    "looks. Reading `AGENTS.md` is the routing step, not the destination - follow where it "
    "routes rather than stopping once it is open.",
    "",
    "1. Locate the nearest applicable `AGENTS.md`, read it first, and follow its routing.",
    "2. Load `.memory-seed/skills/orientation.md` and apply the measured session-context route below.",
    "3. Do not use memory_search to determine current/latest state; use it only for topical history.",
]

try:
    from memory_seed.core import resolve_runtime
    from memory_seed.situate import situate_report

    runtime = resolve_runtime(Path.cwd())
    report = situate_report(Path.cwd(), explicit_user=explicit_user)
except Exception as exc:  # Hooks fail open: preserve the AGENTS-first route.
    parts.extend([
        "",
        "ORIENTATION FACTS unavailable from the shared report "
        f"({exc.__class__.__name__}). Run `memory-seed situate` from the project root, "
        "then follow `orientation.md`.",
    ])
    emit("\n".join(parts))
    sys.exit(0)

parts.extend([
    "",
    "ORIENTATION FACTS (measured, not declared)",
    f"- checkout: {report.checkout_classification or 'not-a-worktree'}"
    + (f" — {report.checkout_path}" if report.checkout_path else ""),
    f"- branch: {report.branch or 'detached'}; uncommitted: "
    f"{report.dirty if report.dirty is not None else '?'}; ahead: "
    f"{report.ahead if report.ahead is not None else '?'}",
    f"- integration_mode: {report.integration_mode}; merge_trigger: {report.merge_trigger}",
])
if report.checkout_classification == "root-checkout":
    parts.append(
        "- this is the shared PRIMARY checkout; read-only work is fine, but create and verify "
        "an agent-owned worktree before non-trivial writes."
    )

if not report.newest_session_path:
    parts.extend(["", "LATEST SESSION", "- No applicable session entries were found yet."])
else:
    parts.extend([
        "",
        "LATEST SESSION",
        f"- path: {report.newest_session_path}",
        f"- last entry: {report.newest_entry or '(no entries yet)'}",
    ])
    if report.newest_session_read_error:
        parts.append(
            f"- context_route: unavailable ({report.newest_session_read_error}); "
            "inspect the source safely and report the read failure."
        )
    else:
        parts.extend([
            f"- characters: {report.newest_session_characters}; bytes: "
            f"{report.newest_session_bytes}; entries: {report.newest_session_entries}",
            f"- compression_threshold_characters: {report.compression_threshold_characters}",
            f"- context_route: {report.context_route}",
            "",
            "SESSION CONTEXT ROUTE",
        ])
        if report.context_route == "direct":
            parts.append(
                "Read the entire latest session file in the primary context. The route is based "
                "on the whole file, not a fixed number of recent entries."
            )
        else:
            parts.extend([
                "Launch one read-only worker at the smallest available economy capability tier "
                "whose context window can hold the entire latest session file. Give it only the "
                "exact path above and this contract; do not inherit conversation, personas, the "
                "project index, policy, or skill registry.",
                "",
                "Return at most 800 tokens covering: final state after later corrections; "
                "accomplishments grouped by workstream; important decisions and recorded reasons; "
                "open follow-ups, risks, and unresolved questions; stale or superseded intermediate "
                "claims; source entry IDs/headings for consequential conclusions; and coverage as "
                "the source path plus N/N entries considered. Do not write files or infer absent facts.",
                "",
                "If no suitable worker is available, read the file directly. If the file exceeds "
                "available worker context, split only at session-entry boundaries, summarize every "
                "chunk with economy workers, and reduce those summaries to the same 800-token contract.",
                "Treat the briefing as derived orientation, not authority. Reopen exact source entries "
                "before consequential decisions that depend on their reasoning.",
            ])

    if report.session_contributors:
        parts.append("")
        parts.append(f"Co-contributor session files for {report.newest_session_date}:")
        for contributor in report.session_contributors:
            noun = "entry" if contributor.entries == 1 else "entries"
            parts.append(f"- {contributor.path} ({contributor.entries} {noun})")

identity_note = offer_identity_setup(runtime.memory_dir)
if identity_note:
    parts.extend(["", identity_note])

emit("\n".join(parts))
