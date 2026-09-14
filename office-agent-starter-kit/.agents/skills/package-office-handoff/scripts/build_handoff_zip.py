#!/usr/bin/env python3
"""Build a conservative handoff ZIP after a secret scan."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import zipfile

from scan_sensitive import scan_tree


EXCLUDED_NAMES = {
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
    "local-only",
}
EXCLUDED_FILE_NAMES = {
    ".env",
    "token.json",
    "credentials.json",
    "client_secret.json",
}
EXCLUDED_SUFFIXES = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".pem",
    ".key",
    ".p12",
    ".age",
}


def include_file(path: Path, source: Path, output: Path) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    if path.resolve() == output:
        return False
    relative = path.relative_to(source)
    if any(part in EXCLUDED_NAMES for part in relative.parts):
        return False
    if path.name in EXCLUDED_FILE_NAMES:
        return False
    if path.name.startswith(".env") and path.name != ".env.example":
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    output = Path(args.output).resolve()
    if not source.is_dir():
        parser.error(f"not a directory: {source}")
    if output.exists() and not args.replace:
        parser.error(f"output exists; use --replace after checking target: {output}")

    findings = scan_tree(source)
    errors = [item for item in findings if item.level == "ERROR"]
    warnings = [item for item in findings if item.level == "WARN"]
    for item in findings:
        print(f"{item.level}: {item.path}:{item.line} [{item.kind}]")
    if errors:
        print("Refusing to build: secret scan has errors.")
        return 2
    if warnings:
        print("PII warnings remain. Confirm they are necessary before sharing.")

    files = [
        path
        for path in sorted(source.rglob("*"))
        if include_file(path, source, output)
    ]
    if not any(path.name == "AGENTS.md" for path in files):
        print("Refusing to build: source has no AGENTS.md entrypoint.")
        return 3

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    top = source.name
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, f"{top}/{path.relative_to(source)}")
        manifest = [
            f"Created UTC: {datetime.now(timezone.utc).isoformat()}",
            f"Source folder: {source.name}",
            f"Files: {len(files)}",
            f"Secret scan errors: {len(errors)}",
            f"PII warnings: {len(warnings)}",
            "",
            "Included files:",
            *[str(path.relative_to(source)) for path in files],
        ]
        archive.writestr(f"{top}/HANDOFF-MANIFEST.txt", "\n".join(manifest) + "\n")

    print(f"Created: {output}")
    print(f"Files: {len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
