"""Cursor adapter (v2 stub).

Cursor is a VS Code fork; its chat history lives in a SQLite key-value store at
~/Library/Application Support/Cursor/User/globalStorage/state.vscdb (macOS).
The schema is undocumented and changes across releases, so transcript capture is
deferred to v2. The git hook + agent-summary handshake (.pending-summary) still
work for Cursor today -- only automatic conversation-body extraction is pending.
"""

from typing import List

from .base import Adapter, Event


class CursorAdapter(Adapter):
    name = "cursor"

    def discover(self, repo_root: str) -> List[str]:
        return []  # v2: read state.vscdb (SQLite)

    def can_parse(self, path: str) -> bool:
        return False

    def parse_file(self, path: str) -> List[Event]:
        return []
