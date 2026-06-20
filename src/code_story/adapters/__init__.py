"""Source adapters: each maps one AI tool's local transcripts to the common Event schema."""

from .claude import ClaudeAdapter
from .codex import CodexAdapter
from .cursor import CursorAdapter
from .trae import TraeAdapter

# Registry of all adapters. Add new sources here.
# Claude + Codex are fully implemented; Cursor + Trae are v2 stubs (SQLite).
ADAPTERS = [ClaudeAdapter(), CodexAdapter(), CursorAdapter(), TraeAdapter()]
