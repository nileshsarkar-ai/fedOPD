#!/usr/bin/env python3
"""UserPromptSubmit hook: inject CLAUDE.md every turn.

WORKLOG.md is no longer injected (2026-07-27, at the owner's instruction). It is still the project
record and is still written every turn - it is read on demand rather than pushed into every prompt.
The worklog is full of numbers, and having them in context makes it easy to write one from recall
instead of from the notebook, which is the failure this project keeps hitting.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]   # .claude/hooks/x.py -> repo root

# encoding="utf-8" is required, not cosmetic: Python on Windows defaults to the system codepage
# (cp1252 here), which turns every em-dash in this file into mojibake before Claude ever sees it.
claude_md = ROOT / "CLAUDE.md"
context = ("<CLAUDE.md>\n" + claude_md.read_text(encoding="utf-8") + "\n</CLAUDE.md>\n\n"
           "Project rules are above. WORKLOG.md is NOT injected - read it with the Read tool when "
           "you need the previous turn's state. Append this turn's entry to it before ending.")

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": context,
    },
    "suppressOutput": True,
}))
