"""Common normalized schema shared by all source adapters."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List


@dataclass
class Event:
    """One normalized conversation event (a human turn or an agent text turn)."""

    ts: float                       # epoch seconds (UTC)
    role: str                       # 'human' | 'agent'
    text: str                       # the message text (already stripped of tool noise)
    files: List[str] = field(default_factory=list)  # file paths this turn touched
    source: str = ""               # 'claude-code' | 'codex' | ...
    model: str = ""
    session_id: str = ""
    cwd: str = ""


class Adapter:
    """Base class. Subclasses implement discovery + parsing for one tool."""

    name = "base"

    def discover(self, repo_root: str) -> List[str]:
        """Return candidate transcript file paths for this repo."""
        raise NotImplementedError

    def can_parse(self, path: str) -> bool:
        """Cheap sniff: does this file look like this adapter's format?"""
        raise NotImplementedError

    def parse_file(self, path: str) -> List[Event]:
        """Parse one transcript file into normalized Events (text-only, tool noise dropped)."""
        raise NotImplementedError


def parse_ts(value) -> float:
    """Parse an ISO-8601 string (or epoch number) into epoch seconds. Returns 0.0 on failure."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        # Heuristic: treat very large numbers as milliseconds.
        return float(value) / 1000.0 if value > 1e12 else float(value)
    s = str(value).strip()
    if not s:
        return 0.0
    # Python 3.9's fromisoformat doesn't accept a trailing 'Z'.
    s = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except ValueError:
            continue
    return 0.0


_SYS_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)
_MAX_TEXT = 16000  # truncate oversized pasted blobs


def clean_text(text: str) -> str:
    """Strip injected system-reminder blocks and truncate oversized blobs."""
    if not text:
        return ""
    text = _SYS_REMINDER.sub("", text).strip()
    if len(text) > _MAX_TEXT:
        text = text[:_MAX_TEXT] + "\n\n[... truncated by code-story ...]"
    return text


def under(path: str, root: str) -> bool:
    """True if path is root or inside root."""
    if not path or not root:
        return False
    path = path.rstrip("/")
    root = root.rstrip("/")
    return path == root or path.startswith(root + "/")
