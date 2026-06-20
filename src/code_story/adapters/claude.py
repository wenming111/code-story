"""Claude Code adapter.

Transcripts: ~/.claude/projects/<encoded-cwd>/<sessionId>.jsonl
Each line is a JSON object: {type, timestamp, cwd, gitBranch, sessionId, message, isMeta, isSidechain, ...}
"""

import json
import os
import re
from typing import List

from .base import Adapter, Event, clean_text, parse_ts

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def _encode_cwd(path: str) -> str:
    """Mirror Claude Code's project-dir encoding: non-alphanumerics -> '-'."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def _blocks_text(content) -> str:
    """Extract human/agent visible text from a message.content (string or block list)."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for blk in content:
        if isinstance(blk, dict) and blk.get("type") == "text":
            parts.append(blk.get("text", ""))
    return "\n".join(p for p in parts if p)


def _is_tool_result(content) -> bool:
    if isinstance(content, list):
        for blk in content:
            if isinstance(blk, dict) and blk.get("type") == "tool_result":
                return True
    return False


def _edited_files(content) -> List[str]:
    files = []
    if isinstance(content, list):
        for blk in content:
            if isinstance(blk, dict) and blk.get("type") == "tool_use" and blk.get("name") in EDIT_TOOLS:
                inp = blk.get("input") or {}
                fp = inp.get("file_path") or inp.get("notebook_path")
                if fp:
                    files.append(fp)
    return files


class ClaudeAdapter(Adapter):
    name = "claude-code"

    def discover(self, repo_root: str) -> List[str]:
        base = os.path.expanduser("~/.claude/projects")
        if not os.path.isdir(base):
            return []
        primary = os.path.join(base, _encode_cwd(repo_root))
        dirs = [primary] if os.path.isdir(primary) else [
            os.path.join(base, d) for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))
        ]
        files = []
        for d in dirs:
            try:
                for fn in os.listdir(d):
                    if fn.endswith(".jsonl"):
                        files.append(os.path.join(d, fn))
            except OSError:
                continue
        return files

    def can_parse(self, path: str) -> bool:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                checked = 0
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        o = json.loads(line)
                    except ValueError:
                        continue
                    if "message" in o and o.get("type") in ("user", "assistant"):
                        return True
                    checked += 1
                    if checked >= 50:
                        break
        except OSError:
            return False
        return False

    def parse_file(self, path: str) -> List[Event]:
        events: List[Event] = []
        try:
            fh = open(path, "r", encoding="utf-8", errors="replace")
        except OSError:
            return events
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                if o.get("isMeta") or o.get("isSidechain"):
                    continue
                typ = o.get("type")
                if typ not in ("user", "assistant"):
                    continue
                msg = o.get("message")
                if not isinstance(msg, dict):
                    continue
                content = msg.get("content")
                ts = parse_ts(o.get("timestamp"))
                cwd = o.get("cwd", "")
                sid = o.get("sessionId", "")
                if typ == "user":
                    if _is_tool_result(content):
                        continue
                    text = clean_text(_blocks_text(content))
                    if not text:
                        continue
                    events.append(Event(ts=ts, role="human", text=text, source=self.name,
                                        session_id=sid, cwd=cwd))
                else:  # assistant
                    text = clean_text(_blocks_text(content))
                    files = _edited_files(content)
                    if not text and not files:
                        continue
                    events.append(Event(ts=ts, role="agent", text=text, files=files,
                                        source=self.name, model=msg.get("model", ""),
                                        session_id=sid, cwd=cwd))
        return events
