"""Render normalized events into a single .ai-context markdown file."""

from datetime import datetime, timezone
from typing import List

from .adapters.base import Event


def _yaml_scalar(value) -> str:
    """Quote a scalar for YAML front-matter."""
    s = "" if value is None else str(value)
    s = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return '"' + s + '"'


def _last_human(events: List[Event]) -> str:
    """Last human turn of the increment -- closer to the intent of THIS commit
    than the first turn (which is the oldest, often unrelated, message)."""
    for ev in reversed(events):
        if ev.role == "human" and ev.text.strip():
            line = ev.text.strip().splitlines()[0]
            return line[:200]
    return ""


def build_summary(events: List[Event], staged_files: List[str]) -> str:
    intent = _last_human(events)
    parts = []
    if intent:
        parts.append(intent)
    if staged_files:
        shown = ", ".join(staged_files[:5])
        more = "" if len(staged_files) <= 5 else " (+%d)" % (len(staged_files) - 5)
        parts.append("[files: %s%s]" % (shown, more))
    return " ".join(parts) or "(no human prompt captured)"


def render(events: List[Event], meta: dict) -> str:
    """meta: source, model, session_id, parent, branch, staged_files, anchored(set of file paths)."""
    staged = meta.get("staged_files", [])
    anchored = meta.get("anchored", set())
    agent_steps = sum(1 for e in events if e.role == "agent")
    summary = build_summary(events, staged)
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = ["---"]
    lines.append("source: " + _yaml_scalar(meta.get("source", "")))
    lines.append("model: " + _yaml_scalar(meta.get("model", "")))
    lines.append("steps: %d" % agent_steps)
    lines.append("session_id: " + _yaml_scalar(meta.get("session_id", "")))
    lines.append("parent: " + _yaml_scalar(meta.get("parent", "")))
    lines.append("branch: " + _yaml_scalar(meta.get("branch", "")))
    lines.append("created_at: " + _yaml_scalar(created))
    lines.append("summary: " + _yaml_scalar(summary))
    if staged:
        lines.append("files:")
        for f in staged:
            lines.append("  - " + _yaml_scalar(f))
    lines.append("---")
    lines.append("")
    lines.append("# 对话记录 / Conversation")
    lines.append("")
    lines.append("> 由 code-story 在 commit 时自动采集。仅含人机对话文本,已去除工具输出/思考过程,并做密钥脱敏。")
    lines.append("")

    for ev in events:
        if ev.role == "human":
            lines.append("## 👤 Human")
        else:
            head = "## 🤖 Agent"
            if ev.model:
                head += " (`%s`)" % ev.model
            lines.append(head)
        touched = [f for f in ev.files if f in anchored]
        if touched:
            lines.append("")
            lines.append("*✏️ 改动了本次提交的文件: %s*" % ", ".join(touched))
        if ev.text.strip():
            lines.append("")
            lines.append(ev.text.strip())
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
