#!/usr/bin/env python3
"""Validate the minimal structure used by this starter kit."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("frontmatter closing delimiter is missing")
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_dir")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir).resolve()
    errors: list[str] = []
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        errors.append("missing SKILL.md")
    else:
        text = skill_file.read_text(encoding="utf-8")
        try:
            metadata = parse_frontmatter(text)
            if set(metadata) != {"name", "description"}:
                errors.append("frontmatter must contain only name and description")
            name = metadata.get("name", "")
            if not NAME_RE.fullmatch(name):
                errors.append("name must use lowercase kebab-case")
            if name != skill_dir.name:
                errors.append("frontmatter name must match folder name")
            if len(metadata.get("description", "")) < 20:
                errors.append("description is too short to express triggers")
        except ValueError as exc:
            errors.append(str(exc))

        if "[TODO" in text or "TODO:" in text or "[列出" in text or "[第一步]" in text:
            errors.append("unfinished placeholders remain")
        if len(text.splitlines()) > 500:
            errors.append("SKILL.md exceeds 500 lines; use progressive disclosure")

    openai_file = skill_dir / "agents" / "openai.yaml"
    if not openai_file.is_file():
        errors.append("missing agents/openai.yaml")
    elif skill_file.is_file():
        openai_text = openai_file.read_text(encoding="utf-8")
        if f"${skill_dir.name}" not in openai_text:
            errors.append("default_prompt must mention the skill as $skill-name")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"OK: {skill_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
