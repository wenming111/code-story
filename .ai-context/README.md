# .ai-context

This folder holds, per commit, the human<->AI conversation that produced that change.
Each `*.md` file was captured automatically at commit time by code-story and is part
of the commit that introduced it.

How an agent reads it: given a line of code, `git blame` it to a commit, then look at
the `.ai-context/*.md` file added by that commit to recover the "why".
