from __future__ import annotations

from pathlib import Path
import re


SECRET_FILE_NAMES = {
    ".env",
    ".gr" + "okrc",
    "id_rsa",
    "id_dsa",
    "id_ed25519",
    "secrets.yml",
    "secrets.yaml",
    "appsettings.secrets.json",
}

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?([A-Za-z0-9_\-+/=]{8,}|[^\s'\"]{8,})"),
    re.compile(r"(?i)(password\s*[:=]\s*)([^\s\n]+)"),
    re.compile(r"(?i)(connection\s*string\s*[:=]\s*)([^\n]+)"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----.*?-----END [A-Z ]+PRIVATE KEY-----", re.DOTALL),
    re.compile(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", re.DOTALL),
]


def is_secret_file(path: Path) -> bool:
    name = path.name.lower()
    if name in SECRET_FILE_NAMES:
        return True
    return any(part.lower() in {"secrets", ".ssh"} for part in path.parts)


def redact_text(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: f"{match.group(1) if match.lastindex else ''}[REDACTED]", redacted)
    return redacted


def safe_text_excerpt(text: str, limit: int = 4000) -> str:
    excerpt = redact_text(text)
    if len(excerpt) <= limit:
        return excerpt
    return excerpt[:limit] + "\n...[truncated]"