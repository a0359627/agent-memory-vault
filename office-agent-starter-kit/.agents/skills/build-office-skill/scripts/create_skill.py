#!/usr/bin/env python3
"""Create a minimal repo-scoped Codex skill without overwriting files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("name", help="lowercase kebab-case skill name")
    parser.add_argument("--description", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--output-dir", default=".agents/skills")
    args = parser.parse_args()

    if not NAME_RE.fullmatch(args.name) or len(args.name) > 64:
        parser.error("name must be lowercase kebab-case and at most 64 characters")

    destination = Path(args.output_dir).resolve() / args.name
    if destination.exists():
        parser.error(f"refusing to overwrite existing path: {destination}")

    (destination / "agents").mkdir(parents=True)
    (destination / "references").mkdir()

    skill_md = f"""---
name: {args.name}
description: {args.description}
---

# {args.display_name}

## 輸入

- [列出必要輸入；缺少時要問什麼]

## 流程

1. [第一步]

   完成判準：[可檢查條件]

2. [第二步]

   完成判準：[可檢查條件]

## 輸出

- [固定輸出結構]

## 邊界

- [不能推測的資料]
- [需要人類核准的副作用]
"""
    (destination / "SKILL.md").write_text(skill_md, encoding="utf-8")

    short = f"以一致流程完成「{args.display_name}」並保留來源、未知與人類核准點"
    prompt = f"使用 ${args.name}，帶我完成{args.display_name}。"
    openai_yaml = (
        "interface:\n"
        f"  display_name: {yaml_quote(args.display_name)}\n"
        f"  short_description: {yaml_quote(short)}\n"
        f"  default_prompt: {yaml_quote(prompt)}\n"
    )
    (destination / "agents" / "openai.yaml").write_text(
        openai_yaml, encoding="utf-8"
    )

    print(f"Created {destination}")
    print("Next: replace every bracketed placeholder, then run validate_skill.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
