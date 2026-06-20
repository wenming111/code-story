"""Source adapters: each maps one AI tool's local transcripts to the common Event schema."""

from .claude import ClaudeAdapter
from .codex import CodexAdapter

# Registry of all adapters. Add new sources here.
ADAPTERS = [ClaudeAdapter(), CodexAdapter()]
