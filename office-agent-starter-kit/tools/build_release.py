#!/usr/bin/env python3
"""Validate and build a portable starter-kit ZIP."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import zipfile


EXCLUDED_DIRS = {"dist", "__pycache__", ".git", ".cache", "local-only"}
EXCLUDED_SUFFIXES = {".pyc", ".zip"}


def include(path: Path, root: Path, output: Path) -> bool:
    if path.is_symlink() or not path.is_file() or path.resolve() == output:
        return False
    relative = path.relative_to(root)
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return False
    if path.name == ".DS_Store" or path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    output = Path(args.output).resolve()
    if output.exists() and not args.replace:
        parser.error(f"output exists; use --replace after checking target: {output}")

    subprocess.run(
        [sys.executable, str(root / "tools" / "validate_kit.py")],
        cwd=root,
        check=True,
    )

    files = [path for path in sorted(root.rglob("*")) if include(path, root, output)]
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, f"{root.name}/{path.relative_to(root)}")
        manifest = [
            "Office Agent Starter Kit",
            f"Built UTC: {datetime.now(timezone.utc).isoformat()}",
            f"Files: {len(files)}",
            "Validation: passed before archive creation",
            "",
            "Start with START-HERE.md.",
        ]
        archive.writestr(f"{root.name}/KIT-MANIFEST.txt", "\n".join(manifest) + "\n")

    print(f"Created: {output}")
    print(f"Files: {len(files)} + manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
