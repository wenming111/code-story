---
name: code-story-read
description: Recover WHY a line, commit, or PR exists by reading the conversation code-story stored with each commit. Trigger when investigating, debugging, reviewing, or refactoring unfamiliar code and you need the original intent behind it.
---

# code-story: read the conversation behind code

In a code-story-enabled repo (has a `.ai-context/` directory), each commit carries
the human↔AI conversation that produced it under `.ai-context/*.md`. Use it to
understand *why* code is the way it is.

## From a line of code

1. `git blame -L <start>,<end> <file>` → the commit that introduced the line.
2. `git show <commit> --name-only` → find the `.ai-context/*.md` added by that commit.
3. Read it **progressively**: the front-matter `summary` first (often enough); open
   the conversation body only if you need detail.

## Escalate to PR level only if needed

If the commit-level summary isn't enough, or you need the bigger picture:

1. Find the commit's PR (e.g. via `git log` merge commits, or the host's API).
2. Aggregate the `.ai-context/*.md` files across the PR's commit range
   (`git log <base>..<head> --name-only`) into one overall narrative.

Default to commit-level; only go to PR level when the commit context is
insufficient.

## Notes

- Records are conversation **text only** — tool output, thinking, and secrets are
  stripped at capture time. `summary_by: agent` means the summary was authored by
  the agent; `heuristic` means it was auto-derived.
- Commits with no `.ai-context/*.md` were made without code-story (sparse coverage
  is expected) — fall back to the diff and commit message.
