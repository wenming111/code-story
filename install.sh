#!/bin/sh
# code-story installer.
#
# code-story lives in one place (this directory, $CODE_STORY_HOME) and serves
# many repos. The git hook self-locates the engine, so you only point a repo's
# core.hooksPath at $CODE_STORY_HOME/hooks and drop a .ai-context/ marker.
#
# Usage:
#   ./install.sh --enable [REPO]     enable code-story in REPO (default: cwd's repo)
#   ./install.sh --global            run the hook for ALL your repos (global core.hooksPath)
#   ./install.sh --help
#
# Per-repo (recommended, safe) = --enable. Global = convenient but overrides any
# existing core.hooksPath / husky in every repo (see README caveats).
set -e

CODE_STORY_HOME="$(cd "$(dirname "$0")" && pwd)"
HOOKS_DIR="$CODE_STORY_HOME/hooks"

usage() { sed -n '2,15p' "$0"; exit "${1:-0}"; }

enable_repo() {
  TARGET="${1:-$(git rev-parse --show-toplevel 2>/dev/null)}"
  [ -n "$TARGET" ] || { echo "code-story: not inside a git repo (pass a repo path)" >&2; exit 1; }
  git -C "$TARGET" config core.hooksPath "$HOOKS_DIR"
  chmod +x "$HOOKS_DIR/pre-commit" 2>/dev/null || true
  mkdir -p "$TARGET/.ai-context"
  if [ ! -f "$TARGET/.ai-context/README.md" ]; then
    cp "$CODE_STORY_HOME/.ai-context/README.md" "$TARGET/.ai-context/README.md" 2>/dev/null || \
      printf '# .ai-context\n\nPer-commit human<->AI conversation captured by code-story.\n' > "$TARGET/.ai-context/README.md"
  fi
  echo "code-story: enabled in $TARGET (core.hooksPath=$HOOKS_DIR)"
}

install_global() {
  git config --global core.hooksPath "$HOOKS_DIR"
  chmod +x "$HOOKS_DIR/pre-commit" 2>/dev/null || true
  echo "code-story: global hook set (core.hooksPath=$HOOKS_DIR)."
  echo "  Repos still need a .ai-context/ marker to activate: ./install.sh --enable <repo>"
  echo "  WARNING: global core.hooksPath overrides per-repo .git/hooks and husky. See README."
}

case "${1:-}" in
  --enable) enable_repo "$2" ;;
  --global) install_global ;;
  --help|-h|"") usage 0 ;;
  *) echo "unknown option: $1" >&2; usage 1 ;;
esac
