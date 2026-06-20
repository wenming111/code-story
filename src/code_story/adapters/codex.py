"""Codex adapter.

Transcripts: ~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-<ts>-<id>.jsonl
Each line: {timestamp, type, payload}. Types seen: session_meta, turn_context,
response_item, event_msg, compacted. cwd/model live in session_meta + turn_context;
human/agent text lives in response_item payloads of type 'message'.
"""

import json
import os
from typing import List

from .base import Adapter, Event, clean_text, parse_ts


def _payload_text(payload) -> str:
    content = payload.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for blk in content:
        if isinstance(blk, dict) and blk.get("type") in ("input_text", "output_text", "text"):
            parts.append(blk.get("text", ""))
    return "\n".join(p for p in parts if p)


class CodexAdapter(Adapter):
    name = "codex"

    def discover(self, repo_root: str) -> List[str]:
        base = os.path.expanduser("~/.codex/sessions")
        if not os.path.isdir(base):
            return []
        files = []
        for root, _dirs, names in os.walk(base):
            for fn in names:
                if fn.startswith("rollout-") and fn.endswith(".jsonl"):
                    files.append(os.path.join(root, fn))
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
                    if "payload" in o and "type" in o:
                        return True
                    checked += 1
                    if checked >= 50:
                        break
        except OSError:
            return False
        return False

    def parse_file(self, path: str) -> List[Event]:
        events: List[Event] = []
        cwd = ""
        model = ""
        sid = os.path.basename(path)
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
                typ = o.get("type")
                payload = o.get("payload")
                if not isinstance(payload, dict):
                    continue
                ts = parse_ts(o.get("timestamp"))
                if typ == "session_meta":
                    cwd = payload.get("cwd", cwd)
                    sid = payload.get("id", sid)
                    model = payload.get("model", model)
                    continue
                if typ == "turn_context":
                    cwd = payload.get("cwd", cwd)
                    model = payload.get("model", model)
                    continue
                if typ != "response_item":
                    continue
                if payload.get("type") != "message":
                    continue
                role = payload.get("role")
                if role == "user":
                    norm = "human"
                elif role == "assistant":
                    norm = "agent"
                else:
                    continue  # drop developer/system
                text = clean_text(_payload_text(payload))
                if not text:
                    continue
                events.append(Event(ts=ts, role=norm, text=text, source=self.name,
                                    model=model, session_id=sid, cwd=cwd))
        return events
