"""Secret redaction. Runs over assembled conversation text before it is written.

Targeted patterns only -- deliberately conservative to avoid clobbering benign
content (e.g. git SHAs, localhost URLs). Tune as needed.
"""

import re

_PLACEHOLDER = "[REDACTED]"

# (pattern, group_to_replace) -- group 0 means replace the whole match.
_PATTERNS = [
    # Private key blocks
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL), 0),
    # AWS access key id
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), 0),
    # GitHub / generic tokens with known prefixes
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b"), 0),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), 0),
    # JWT
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"), 0),
    # key = "value" style secrets (replace only the value, keep the key for context)
    (re.compile(
        r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|"
        r"secret[_-]?key|auth[_-]?token|bearer)\b(\s*[:=]\s*|\s+)(['\"]?)([^\s'\"]{6,})(['\"]?)"
    ), "kv"),
]


def redact(text: str) -> str:
    if not text:
        return text
    for pat, mode in _PATTERNS:
        if mode == 0:
            text = pat.sub(_PLACEHOLDER, text)
        elif mode == "kv":
            text = pat.sub(lambda m: m.group(1) + m.group(2) + m.group(3) + _PLACEHOLDER + m.group(5), text)
    return text
