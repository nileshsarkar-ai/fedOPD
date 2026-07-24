#!/usr/bin/env python3
"""UserPromptSubmit hook: inject CLAUDE.md + the tail of WORKLOG.md every turn.

WORKLOG.md grows without bound, so only the last WORKLOG_LINES lines are injected —
enough to pick up where the last turn left off without paying for the whole history.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]   # .claude/hooks/x.py -> repo root
WORKLOG_LINES = 200

parts = []

claude_md = ROOT / "CLAUDE.md"
if claude_md.exists():
    parts.append("<CLAUDE.md>\n" + claude_md.read_text() + "\n</CLAUDE.md>")

worklog = ROOT / "WORKLOG.md"
if worklog.exists():
    lines = worklog.read_text().splitlines()
    tail = "\n".join(lines[-WORKLOG_LINES:])
    note = "" if len(lines) <= WORKLOG_LINES else f" (last {WORKLOG_LINES} of {len(lines)} lines)"
    parts.append(f"<WORKLOG.md{note}>\n{tail}\n</WORKLOG.md>")

parts.append(
    "Project rules are above. Follow them, and append this turn's entry to WORKLOG.md "
    "before ending the turn."
)

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": "\n\n".join(parts),
    },
    "suppressOutput": True,
}))
