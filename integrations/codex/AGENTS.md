<!-- code-story: paste this block into your repo's AGENTS.md (Codex reads it). -->

## code-story: summarize before committing

This repo uses code-story (a git hook captures the conversation behind each commit
into `.ai-context/`). Before you run `git commit`, write a concise 2–4 line summary
of *why* the change is being made (intent, key decisions, trade-offs) to:

```
.ai-context/.pending-summary
```

Then commit normally. The hook consumes that file and uses it as the commit's
summary. Do not `git add` `.pending-summary` (it is git-ignored).

To understand existing code: `git blame` a line → read the `.ai-context/*.md`
added by that commit (start with the front-matter `summary`).
