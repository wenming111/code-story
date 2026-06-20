<!-- code-story: add this as a Trae project rule (Trae > Rules), or paste into your
     repo's agent rules file that Trae reads. -->

# code-story: summarize before committing

This repo uses code-story. A git hook captures the conversation behind each commit
into `.ai-context/`.

Before running `git commit`, write a concise 2–4 line summary of *why* this change
is being made (intent, key decisions, trade-offs — not a restatement of the diff)
to `.ai-context/.pending-summary`. Then commit normally. Do not `git add` that file
(it is git-ignored and consumed by the hook).

To understand existing code: `git blame` a line → read the `.ai-context/*.md` added
by that commit, starting with its front-matter `summary`.

Note: automatic capture of Trae's own conversation body is planned (v2); the
summary you write is recorded today.
