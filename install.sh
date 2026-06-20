#!/bin/sh
# code-story installer (v1, repo-local).
# Activates the committed hooks/ dir for THIS repo and drops the .ai-context marker.
# Does NOT touch global git config.
set -e

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$ROOT" ]; then
  echo "code-story: not inside a git repo" >&2
  exit 1
fi

# Activate the committed hooks directory for this repo.
git -C "$ROOT" config core.hooksPath hooks
chmod +x "$ROOT/hooks/pre-commit" 2>/dev/null || true

# Create the per-repo opt-in marker / read-side note if missing.
if [ ! -d "$ROOT/.ai-context" ]; then
  mkdir -p "$ROOT/.ai-context"
fi
if [ ! -f "$ROOT/.ai-context/README.md" ]; then
  cat > "$ROOT/.ai-context/README.md" <<'EOF'
# .ai-context

This folder holds, per commit, the human<->AI conversation that produced that change.
Each `*.md` file was captured automatically at commit time by code-story and is part
of the commit that introduced it.

How an agent reads it: given a line of code, `git blame` it to a commit, then look at
the `.ai-context/*.md` file added by that commit to recover the "why".
EOF
fi

echo "code-story: installed (core.hooksPath=hooks) in $ROOT"
