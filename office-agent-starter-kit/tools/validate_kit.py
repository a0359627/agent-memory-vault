#!/usr/bin/env python3
"""Validate starter-kit structure, skills, scripts, and secret hygiene."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
import sys

# Never leave __pycache__/*.pyc behind: a .pyc embeds the absolute path of the
# source it was compiled from, which means the maintainer's home directory and
# user name ride along in any tarball of this tree.
sys.dont_write_bytecode = True


EXPECTED_SKILLS = {
    "build-office-skill",
    "meeting-to-actions",
    "draft-office-document",
    "verify-office-research",
    "review-office-spreadsheet",
    "package-office-handoff",
}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("missing opening frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("missing closing frontmatter")
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def load_scanner(script_path: Path):
    spec = importlib.util.spec_from_file_location("handoff_scanner", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load scanner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []

    # LICENSE is in this list because the kit ships as a standalone ZIP: whoever
    # receives it has only this folder, so the statement of rights has to live
    # inside it. A gate, not a reminder — it cannot be dropped by accident again.
    for required in ("START-HERE.md", "AGENTS.md", "LESSONS.md", "PRACTICE.md", "LICENSE"):
        if not (root / required).is_file():
            errors.append(f"missing root file: {required}")

    skills_root = root / ".agents" / "skills"
    actual_skills = {path.name for path in skills_root.iterdir() if path.is_dir()}
    if actual_skills != EXPECTED_SKILLS:
        errors.append(
            f"skill set mismatch: expected {sorted(EXPECTED_SKILLS)}, got {sorted(actual_skills)}"
        )

    for skill_name in sorted(actual_skills):
        skill_dir = skills_root / skill_name
        skill_file = skill_dir / "SKILL.md"
        openai_file = skill_dir / "agents" / "openai.yaml"
        if not skill_file.is_file():
            errors.append(f"{skill_name}: missing SKILL.md")
            continue
        text = skill_file.read_text(encoding="utf-8")
        try:
            metadata = parse_frontmatter(text)
        except ValueError as exc:
            errors.append(f"{skill_name}: {exc}")
            continue
        if set(metadata) != {"name", "description"}:
            errors.append(f"{skill_name}: frontmatter must contain only name and description")
        if metadata.get("name") != skill_name or not NAME_RE.fullmatch(skill_name):
            errors.append(f"{skill_name}: invalid or mismatched name")
        if len(metadata.get("description", "")) < 30:
            errors.append(f"{skill_name}: description too short for reliable triggering")
        if "[TODO" in text or "TODO:" in text:
            errors.append(f"{skill_name}: unfinished TODO marker remains in SKILL.md")
        if len(text.splitlines()) > 500:
            errors.append(f"{skill_name}: SKILL.md exceeds 500 lines")
        if not openai_file.is_file():
            errors.append(f"{skill_name}: missing agents/openai.yaml")
        elif f"${skill_name}" not in openai_file.read_text(encoding="utf-8"):
            errors.append(f"{skill_name}: default_prompt does not mention ${skill_name}")

    for script in sorted(root.rglob("*.py")):
        # compile() in memory instead of py_compile: same syntax check, no .pyc on disk.
        try:
            compile(script.read_text(encoding="utf-8"), str(script), "exec")
        except (SyntaxError, ValueError, OSError) as exc:
            errors.append(f"python compile failed: {script.relative_to(root)}: {exc}")

    scanner_path = (
        skills_root / "package-office-handoff" / "scripts" / "scan_sensitive.py"
    )
    scanner = load_scanner(scanner_path)
    findings = scanner.scan_tree(root)
    secret_errors = [item for item in findings if item.level == "ERROR"]
    if secret_errors:
        errors.extend(
            f"secret scan: {item.path}:{item.line} [{item.kind}]"
            for item in secret_errors
        )

    symlinks = [path for path in root.rglob("*") if path.is_symlink()]
    if symlinks:
        errors.extend(f"symlink not allowed: {path.relative_to(root)}" for path in symlinks)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    warnings = [item for item in findings if item.level == "WARN"]
    print(f"OK: {len(actual_skills)} skills")
    print(f"OK: {sum(1 for _ in root.rglob('*.py'))} Python scripts compile")
    print("OK: no high-confidence secret findings")
    print(f"INFO: {len(warnings)} possible PII warning(s) for manual review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
