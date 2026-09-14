#!/usr/bin/env python3
"""Scan a directory for high-confidence secrets and possible PII."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".cache",
    ".venv",
    "venv",
    "dist",
    "build",
}
SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".pdf",
    ".zip",
    ".gz",
    ".age",
    ".woff",
    ".woff2",
    ".sqlite",
    ".db",
}
PLACEHOLDERS = {
    "example",
    "placeholder",
    "changeme",
    "change-me",
    "redacted",
    "your-token",
    "your_token",
    "your-key",
    "your_key",
}


@dataclass(frozen=True)
class Finding:
    level: str
    path: str
    line: int
    kind: str


SECRET_PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("openai-style-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "assigned-secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|client[_-]?secret)"
            r"\s*[:=]\s*[\"']?([A-Za-z0-9_./+=-]{12,})"
        ),
    ),
]
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d ()-]{7,}\d)(?!\d)")
ISO_TIMESTAMP_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?\b"
)
ISO_DATE_RE = re.compile(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b")


PLACEHOLDER_BRACKET_RE = re.compile(r"<[^<>\n]{0,64}>")


def is_placeholder(line: str, match: re.Match) -> bool:
    """Whitelist the matched span only -- never the whole line.

    Line-level whitelisting meant one ``<`` or the word ``example`` anywhere on a
    line disabled the scan for that line, and both are everywhere in Markdown and
    shell snippets. A real key with a comment next to it must still be an error.
    """
    hit = match.group(0).lower()
    if any(token in hit for token in PLACEHOLDERS):
        return True
    for bracket in PLACEHOLDER_BRACKET_RE.finditer(line):
        if bracket.start() <= match.start() and match.end() <= bracket.end():
            return True
    return False


def iter_text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if path.name.startswith(".env") and path.name != ".env.example":
            yield path
            continue
        try:
            with path.open("rb") as handle:
                sample = handle.read(4096)
            if b"\x00" not in sample:
                yield path
        except OSError:
            continue


def scan_tree(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_text_files(root):
        relative = str(path.relative_to(root))
        if path.name.startswith(".env") and path.name != ".env.example":
            findings.append(Finding("ERROR", relative, 1, "live-env-file"))
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for number, line in enumerate(lines, 1):
            for kind, pattern in SECRET_PATTERNS:
                match = pattern.search(line)
                if match and not is_placeholder(line, match):
                    findings.append(Finding("ERROR", relative, number, kind))
            if EMAIL_RE.search(line) and "example." not in line.lower():
                findings.append(Finding("WARN", relative, number, "possible-email"))
            phone_candidate = ISO_TIMESTAMP_RE.sub("", line)
            phone_candidate = ISO_DATE_RE.sub("", phone_candidate)
            if PHONE_RE.search(phone_candidate) and not line.lstrip().startswith(("#", "|")):
                findings.append(Finding("WARN", relative, number, "possible-phone"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        parser.error(f"not a directory: {root}")

    findings = scan_tree(root)
    for item in findings:
        print(f"{item.level}: {item.path}:{item.line} [{item.kind}]")
    errors = sum(item.level == "ERROR" for item in findings)
    warnings = sum(item.level == "WARN" for item in findings)
    print(f"Summary: {errors} error(s), {warnings} warning(s)")
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
