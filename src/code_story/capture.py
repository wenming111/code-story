"""code-story capture: invoked by the pre-commit hook.

Pipeline: guards -> time window -> adapters -> filter/cwd -> redact -> render -> write + git add.
NEVER blocks a commit: any error exits 0.
"""

import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import List

from .adapters import ADAPTERS
from .adapters.base import Event, under
from .redact import redact
from .render import render

AI_DIR = ".ai-context"


def _git(repo_root: str, *args: str) -> str:
    try:
        out = subprocess.run(["git", "-C", repo_root, *args],
                             capture_output=True, text=True, check=False)
        return out.stdout.strip()
    except Exception:
        return ""


def _repo_root() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, check=False)
        return out.stdout.strip()
    except Exception:
        return ""


def _staged_files(repo_root: str) -> List[str]:
    out = _git(repo_root, "diff", "--cached", "--name-only")
    return [l for l in out.splitlines() if l.strip()]


def _in_special_state(repo_root: str) -> bool:
    """Skip during rebase/merge/cherry-pick/amend to avoid mis-attaching."""
    git_dir = _git(repo_root, "rev-parse", "--git-dir")
    if not git_dir:
        return False
    if not os.path.isabs(git_dir):
        git_dir = os.path.join(repo_root, git_dir)
    for marker in ("MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD", "REVERT_HEAD"):
        if os.path.exists(os.path.join(git_dir, marker)):
            return True
    return False


def _last_commit_time(repo_root: str) -> float:
    out = _git(repo_root, "log", "-1", "--format=%ct")
    try:
        return float(out)
    except ValueError:
        return 0.0


def _read_pending_summary(repo_root: str):
    """Agent-path handshake: the agent writes its summary to
    .ai-context/.pending-summary before committing. We consume (read + delete)
    it here so it applies to exactly one commit. Returns None if absent."""
    path = os.path.join(repo_root, AI_DIR, ".pending-summary")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            txt = fh.read().strip()
    except OSError:
        return None
    try:
        os.remove(path)
    except OSError:
        pass
    return txt or None


def _explicit_files() -> List[str]:
    raw = os.environ.get("CODE_STORY_SESSION_FILES", "").strip()
    if not raw:
        return []
    parts = [p.strip() for chunk in raw.split(os.pathsep) for p in chunk.split(",")]
    return [os.path.expanduser(p) for p in parts if p.strip()]


def collect_events(repo_root: str) -> List[Event]:
    explicit = _explicit_files()
    events: List[Event] = []

    if explicit:
        # Override path (dogfood): use explicit files and SKIP cwd filtering
        # (the session's cwd may not match this repo), but STILL apply the time
        # window so we capture only the increment since the last commit.
        since = _last_commit_time(repo_root)
        until = time.time()
        for path in explicit:
            if not os.path.isfile(path):
                continue
            for adapter in ADAPTERS:
                if adapter.can_parse(path):
                    for ev in adapter.parse_file(path):
                        if ev.ts and not (since <= ev.ts < until):
                            continue
                        events.append(ev)
                    break
        events.sort(key=lambda e: e.ts)
        return events

    since = _last_commit_time(repo_root)
    until = time.time()
    for adapter in ADAPTERS:
        for path in adapter.discover(repo_root):
            for ev in adapter.parse_file(path):
                if ev.ts and not (since <= ev.ts < until):
                    continue
                if ev.cwd and not under(ev.cwd, repo_root):
                    continue
                events.append(ev)
    events.sort(key=lambda e: e.ts)
    return events


def _pick(events: List[Event], key):
    """Most common non-empty value of an attribute across events."""
    counts = {}
    for e in events:
        v = key(e)
        if v:
            counts[v] = counts.get(v, 0) + 1
    return max(counts, key=counts.get) if counts else ""


def main() -> int:
    repo_root = _repo_root()
    if not repo_root:
        return 0

    if _in_special_state(repo_root):
        return 0

    staged = _staged_files(repo_root)
    # Anti-recursion: skip if the only staged changes are inside .ai-context/.
    if staged and all(f.startswith(AI_DIR + "/") or f == AI_DIR for f in staged):
        return 0

    events = collect_events(repo_root)
    pending = _read_pending_summary(repo_root)
    # Nothing to record if there's neither captured conversation nor an
    # agent-authored summary (the latter supports agents without a transcript
    # adapter yet, e.g. Cursor/Trae).
    if not events and not pending:
        return 0

    # Redact every event's text before anything is written.
    for ev in events:
        ev.text = redact(ev.text)

    # Focus: which captured file-edits intersect this commit's staged files.
    staged_set = set(staged)
    anchored = set()
    for ev in events:
        for f in ev.files:
            rel = os.path.relpath(f, repo_root) if os.path.isabs(f) else f
            if rel in staged_set:
                anchored.add(f)

    summary_override = redact(pending) if pending else None

    meta = {
        "source": _pick(events, lambda e: e.source),
        "model": _pick(events, lambda e: e.model),
        "session_id": _pick(events, lambda e: e.session_id),
        "parent": _git(repo_root, "rev-parse", "--short", "HEAD") or "",
        "branch": _git(repo_root, "rev-parse", "--abbrev-ref", "HEAD") or "",
        "staged_files": staged,
        "anchored": anchored,
        "summary_override": summary_override,
    }

    body = render(events, meta)

    ai_dir = os.path.join(repo_root, AI_DIR)
    os.makedirs(ai_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sid8 = (meta["session_id"] or "session").replace("/", "-")[:8]
    fname = "%s-%s-%s.md" % (stamp, meta["source"] or "ai", sid8)
    fpath = os.path.join(ai_dir, fname)
    with open(fpath, "w", encoding="utf-8") as fh:
        fh.write(body)

    _git(repo_root, "add", os.path.join(AI_DIR, fname))
    sys.stderr.write("[code-story] captured %d conversation events -> %s/%s\n"
                     % (len(events), AI_DIR, fname))
    return 0


def _safe_main() -> int:
    try:
        return main()
    except Exception as exc:  # never block a commit
        try:
            sys.stderr.write("[code-story] capture skipped: %r\n" % exc)
        except Exception:
            pass
        return 0


if __name__ == "__main__":
    sys.exit(_safe_main())
