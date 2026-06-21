---
name: code-story-commit
description: Before running `git commit` in a code-story-enabled repo (one that has a .ai-context/ directory), write a concise "why" summary so it is stored with the commit. Trigger whenever you are about to commit changes in such a repo.
---

# code-story: write a summary before committing

code-story stores, per commit, the human↔AI conversation that produced it (a git
hook does this automatically). Your job is to contribute a high-quality summary.

If the repo has a `.ai-context/` directory, then **before you run `git commit`**:

1. Write a concise **2–4 line summary of *why*** this change is being made —
   intent, key decisions, trade-offs. Not a restatement of the diff. Write it to:
   ```
   .ai-context/.pending-summary
   ```
2. Then commit as usual.

The git hook consumes `.pending-summary` (read + delete), uses it as the commit's
summary, and records `summary_by: agent`. If you skip it, the hook falls back to a
weaker heuristic (last human message + files) — so always write it.

Do **not** `git add` `.pending-summary`; it is git-ignored and consumed by the hook.

> In Claude Code, a PreToolUse hook will block the commit until this file exists,
> as a safety net. Writing it proactively avoids the block.
