#!/usr/bin/env python3
"""code-story PreToolUse hook (Claude Code only).

Enforces the ② agent-summary path: when the agent is about to `git commit` in a
code-story-enabled repo, require that it first wrote a "why" summary to
.ai-context/.pending-summary. If missing, block the commit (exit 2) with a
message telling the agent to write it and retry. Otherwise allow.

Manual/terminal commits are unaffected (Claude hooks only run inside Claude Code);
they fall back to the heuristic summary in the git pre-commit hook.
"""

import json
import os
import re
import subprocess
import sys

AI_DIR = ".ai-context"


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # never get in the way on malformed input

    if (data.get("tool_name") or data.get("toolName")) != "Bash":
        return 0
    cmd = ((data.get("tool_input") or data.get("toolInput") or {}).get("command")) or ""
    # Only care about actual commits.
    if not re.search(r"\bgit\b[^\n]*\bcommit\b", cmd):
        return 0
    # Amend rewrites an existing commit (its summary already exists) -- don't block.
    if "--amend" in cmd:
        return 0

    cwd = data.get("cwd") or os.getcwd()
    try:
        root = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
    except Exception:
        return 0
    if not root or not os.path.isdir(os.path.join(root, AI_DIR)):
        return 0  # repo not code-story-enabled

    if os.path.isfile(os.path.join(root, AI_DIR, ".pending-summary")):
        return 0  # agent already provided a summary

    sys.stderr.write(
        "code-story: before committing, write a concise 2-4 line summary of WHY "
        "this change is being made (intent, key decisions, trade-offs) to "
        ".ai-context/.pending-summary, then run the commit again. It becomes this "
        "commit's summary (summary_by: agent); without it a weaker heuristic is used. "
        "Do not `git add` that file.\n"
    )
    return 2  # block this tool call; the model sees the message and retries


if __name__ == "__main__":
    sys.exit(main())
