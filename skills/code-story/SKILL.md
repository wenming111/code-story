---
name: code-story
description: Write a "why" summary before committing in a code-story-enabled repo, and read past commit conversations to understand code. Trigger when about to `git commit` in a repo that has a .ai-context/ directory, or when investigating why a line/commit exists.
---

# code-story

code-story stores, per commit, the human↔AI conversation that produced it, inside
the same commit (under `.ai-context/`). A git hook captures the conversation
automatically; your job as the agent is to contribute a high-quality summary and
to read these records when explaining code.

## When committing (the ② agent path)

If the repo has a `.ai-context/` directory, then **before you run `git commit`**:

1. Write a concise 2–4 line summary of *why* this change is being made (intent,
   key decisions, trade-offs — not a restatement of the diff) to:
   ```
   .ai-context/.pending-summary
   ```
2. Then commit as usual.

The hook consumes `.pending-summary` (read + delete), uses it as the commit's
summary, and records `summary_by: agent`. If you don't write it, the hook falls
back to a heuristic (last human message + files) — so always prefer to write it.

Do **not** `git add` `.pending-summary`; it is git-ignored and consumed by the hook.

## When reading code (the read side)

To understand why a line or commit exists:

1. `git blame` the line → find the commit.
2. Read that commit's `.ai-context/*.md` (added by the same commit) — start with
   its front-matter `summary`, then the conversation body if you need detail.
3. For broader context, aggregate the `.ai-context/*.md` files across a PR's
   commit range (`git log <base>..<head>`).

Records are conversation text only (tool output, thinking, and secrets are
stripped at capture time).
