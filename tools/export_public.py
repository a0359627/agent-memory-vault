#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""allowlist exporter：把一個私有 vault 依 manifest 匯出成公開 repo。

設計原則（為什麼長這樣）
------------------------
1. **allowlist 是唯一入口**：只有 manifest 列出的 dest 會存在。公開樹裡多一個檔、
   manifest 裡少一個檔，都是 ERROR——「忘了列」不會變成「悄悄放行」。
2. **每條刪改規則都要說出自己命中幾次**（`expect`）。命中 0 次代表來源漂移、規則失效；
   命中多於預期代表規則太寬，可能改到不該改的地方。兩種都 fail。
3. **sha256 pin 輸出**：`expect` 抓「沒改到」，sha256 抓「規則之外的手改」。
4. **fail-before-write**：先把整批檢查跑完，任一 ERROR 就一個檔都不寫。
   半套的匯出比完全沒匯出更危險。

四種模式
--------
copy      dest 內容必須 byte-for-byte 等於 src（可為二進位）。
rewrite   對 src 依序套用 rules，每條 pattern 必須恰好命中 expect 次；結果必須等於 dest。
pinned    手寫檔（本 repo 內作者直接寫的），只驗 dest 的 sha256 等於記錄值。
generate  由其他工具產生（例如 docs/REFERENCES.md），只驗 dest 的 sha256。

manifest 格式
-------------
{
  "version": 1,
  "repo": "agent-memory-vault",
  "assert_absent": ["regex", ...],          # 對每個 dest 的最終內容檢查，命中即 ERROR
  "files": [
    {"dest": "template/AGENTS.md", "mode": "copy",    "src": "AGENTS.md", "sha256": "..."},
    {"dest": "template/ROUTING.md","mode": "rewrite", "src": "ROUTING.md","sha256": "...",
     "rules": [{"pattern": "...", "replace": "...", "expect": 1, "flags": ["MULTILINE"]}]},
    {"dest": "README.md",          "mode": "pinned",   "sha256": "..."},
    {"dest": "docs/REFERENCES.md", "mode": "generate", "sha256": "..."}
  ]
}

`replace` 走 `re.sub` 語義（`\\1` 可回填 group；字面反斜線要自己跳脫）。
`flags` 選填，預設 `["MULTILINE"]`；可用 MULTILINE／DOTALL／IGNORECASE。

用法
----
    tools/export_public.py --manifest <json> --source <VAULT> --out <PUB>            # = --check
    tools/export_public.py --manifest <json> --source <VAULT> --out <PUB> --apply
    tools/export_public.py --manifest <json> --out <PUB> --print-hashes

exit code：0 乾淨；2 有發現（檢查失敗）；3 設定錯誤（manifest 壞、缺 --source…）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_FINDINGS = 2
EXIT_CONFIG = 3

MODES = ("copy", "rewrite", "pinned", "generate")
FROM_SOURCE = ("copy", "rewrite")  # --apply 只寫這兩種

# 走訪公開樹時忽略的東西。`.git` 是契約明訂的；另外兩個是必然 gitignored 的雜訊，
# 列在這裡是為了讓「樹檢查」不會因為跑過一次 python 就變紅。
IGNORED_DIRS = {".git", "__pycache__"}
IGNORED_FILES = {".DS_Store"}

FLAG_NAMES = {
    "MULTILINE": re.MULTILINE,
    "DOTALL": re.DOTALL,
    "IGNORECASE": re.IGNORECASE,
    "UNICODE": re.UNICODE,
    "VERBOSE": re.VERBOSE,
}

ENTRY_KEYS = {"dest", "mode", "src", "sha256", "rules", "note"}
RULE_KEYS = {"pattern", "replace", "expect", "flags", "note"}


class ConfigError(Exception):
    """manifest 本身有問題——這不是「發現機敏資料」，是「設定寫錯」。"""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_rel(path_str: str, field: str) -> Path:
    """dest／src 一律是相對路徑，且不得逃出根目錄。"""
    if not isinstance(path_str, str) or not path_str:
        raise ConfigError(f"{field} 必須是非空字串")
    p = Path(path_str)
    if p.is_absolute() or path_str.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", path_str):
        raise ConfigError(f"{field} 不得是絕對路徑：{path_str}")
    if ".." in p.parts:
        raise ConfigError(f"{field} 不得包含 '..'：{path_str}")
    return p


def parse_flags(raw, where: str) -> int:
    if raw is None:
        return re.MULTILINE
    if not isinstance(raw, list):
        raise ConfigError(f"{where}: flags 必須是陣列")
    value = 0
    for name in raw:
        if name not in FLAG_NAMES:
            raise ConfigError(f"{where}: 不認得的 flag {name!r}")
        value |= FLAG_NAMES[name]
    return value


def load_manifest(path: Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"讀不到 manifest：{exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"manifest 不是合法 JSON：{exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("manifest 最外層必須是物件")
    if data.get("version") != 1:
        raise ConfigError(f"不支援的 manifest version：{data.get('version')!r}（本工具只吃 1）")

    absent = data.get("assert_absent", [])
    if not isinstance(absent, list) or any(not isinstance(x, str) for x in absent):
        raise ConfigError("assert_absent 必須是字串陣列")
    compiled_absent = []
    for pattern in absent:
        try:
            compiled_absent.append((pattern, re.compile(pattern, re.MULTILINE)))
        except re.error as exc:
            raise ConfigError(f"assert_absent 的 regex 編不起來：{pattern!r}（{exc}）") from exc

    files = data.get("files")
    if not isinstance(files, list) or not files:
        raise ConfigError("files 必須是非空陣列")

    entries = []
    seen = set()
    for index, entry in enumerate(files):
        where = f"files[{index}]"
        if not isinstance(entry, dict):
            raise ConfigError(f"{where} 必須是物件")
        unknown = set(entry) - ENTRY_KEYS
        if unknown:
            raise ConfigError(f"{where}: 不認得的欄位 {sorted(unknown)}")
        mode = entry.get("mode")
        if mode not in MODES:
            raise ConfigError(f"{where}: mode 必須是 {MODES} 之一，不是 {mode!r}")
        dest = safe_rel(entry.get("dest"), f"{where}.dest")
        key = dest.as_posix()
        if key in seen:
            raise ConfigError(f"{where}: dest 重複：{key}")
        seen.add(key)

        sha = entry.get("sha256")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise ConfigError(f"{where}: sha256 必須是 64 位小寫 hex（用 --print-hashes 取得）")

        src = None
        if mode in FROM_SOURCE:
            if "src" not in entry:
                raise ConfigError(f"{where}: mode={mode} 必須有 src")
            src = safe_rel(entry["src"], f"{where}.src")
        elif "src" in entry:
            raise ConfigError(f"{where}: mode={mode} 不得有 src")

        rules = []
        if mode == "rewrite":
            raw_rules = entry.get("rules")
            if not isinstance(raw_rules, list) or not raw_rules:
                raise ConfigError(f"{where}: mode=rewrite 必須有非空的 rules")
            for r_index, rule in enumerate(raw_rules):
                r_where = f"{where}.rules[{r_index}]"
                if not isinstance(rule, dict):
                    raise ConfigError(f"{r_where} 必須是物件")
                unknown = set(rule) - RULE_KEYS
                if unknown:
                    raise ConfigError(f"{r_where}: 不認得的欄位 {sorted(unknown)}")
                pattern = rule.get("pattern")
                replace = rule.get("replace")
                expect = rule.get("expect")
                if not isinstance(pattern, str) or not pattern:
                    raise ConfigError(f"{r_where}: pattern 必須是非空字串")
                if not isinstance(replace, str):
                    raise ConfigError(f"{r_where}: replace 必須是字串（刪除就給空字串）")
                if not isinstance(expect, int) or isinstance(expect, bool) or expect < 1:
                    raise ConfigError(f"{r_where}: expect 必須是 >= 1 的整數")
                flags = parse_flags(rule.get("flags"), r_where)
                try:
                    compiled = re.compile(pattern, flags)
                except re.error as exc:
                    raise ConfigError(f"{r_where}: regex 編不起來（{exc}）") from exc
                rules.append({"pattern": pattern, "regex": compiled,
                              "replace": replace, "expect": expect})
        elif "rules" in entry:
            raise ConfigError(f"{where}: 只有 mode=rewrite 可以有 rules")

        entries.append({"dest": dest, "mode": mode, "src": src,
                        "sha256": sha, "rules": rules})

    return {
        "repo": data.get("repo"),
        "assert_absent": compiled_absent,
        "entries": entries,
    }


def walk_tree(root: Path):
    """列出公開樹裡真實存在的檔案（相對路徑，posix 形式）。symlink 也要列出來，
    否則「用 symlink 指到 vault 外」會整個躲過樹檢查。"""
    found = []
    for path in sorted(root.rglob("*")):
        rel_parts = path.relative_to(root).parts
        if any(part in IGNORED_DIRS for part in rel_parts):
            continue
        if path.is_dir() and not path.is_symlink():
            continue
        if path.name in IGNORED_FILES:
            continue
        found.append(path.relative_to(root).as_posix())
    return found


def apply_rules(text: str, rules, dest: str, errors: list):
    """依序套規則；每條必須恰好命中 expect 次。"""
    ok = True
    for index, rule in enumerate(rules):
        text, count = rule["regex"].subn(rule["replace"], text)
        if count != rule["expect"]:
            errors.append(
                f"ERROR {dest}: rule[{index}] 命中 {count} 次，expect {rule['expect']} 次"
                f"（pattern 前 60 字：{rule['pattern'][:60]!r}）"
            )
            ok = False
    return text, ok


def check_absent(content: bytes, label: str, absent, errors: list):
    """assert_absent 命中就報錯，但**永不印出命中值**——只印 regex 與行號。"""
    if not absent:
        return
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return  # 二進位檔不做文字斷言
    lines = text.splitlines()
    for pattern, regex in absent:
        for line_no, line in enumerate(lines, 1):
            if regex.search(line):
                errors.append(f"ERROR {label}:{line_no} assert_absent 命中（pattern: {pattern}）")
                break


def run(manifest_path: Path, source: Path | None, out: Path,
        apply: bool, print_hashes: bool) -> int:
    manifest = load_manifest(manifest_path)
    entries = manifest["entries"]
    absent = manifest["assert_absent"]

    if print_hashes:
        for entry in entries:
            dest_path = out / entry["dest"]
            if dest_path.is_file() and not dest_path.is_symlink():
                print(f"{sha256_bytes(dest_path.read_bytes())}  {entry['dest'].as_posix()}")
            else:
                print(f"{'-' * 64}  {entry['dest'].as_posix()}  (缺檔)")
        return EXIT_OK

    needs_source = any(entry["mode"] in FROM_SOURCE for entry in entries)
    if needs_source:
        if source is None:
            raise ConfigError("manifest 內有 copy／rewrite 條目，必須給 --source")
        if not source.is_dir():
            raise ConfigError(f"--source 不是目錄：{source}")
    if not out.is_dir():
        raise ConfigError(f"--out 不是目錄：{out}")

    errors: list[str] = []
    planned: list[tuple[Path, bytes]] = []  # (絕對路徑, 內容) — 全部檢查通過才寫

    for entry in entries:
        dest_rel = entry["dest"].as_posix()
        dest_path = out / entry["dest"]
        mode = entry["mode"]
        expected: bytes | None = None

        # --- 1. 算出「應該長什麼樣」 ---
        if mode in FROM_SOURCE:
            src_path = source / entry["src"]  # type: ignore[operator]
            if src_path.is_symlink() or not src_path.is_file():
                errors.append(f"ERROR {dest_rel}: 來源不存在或不是普通檔案："
                              f"{entry['src'].as_posix()}")
            elif mode == "copy":
                expected = src_path.read_bytes()
            else:
                try:
                    text = src_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    errors.append(f"ERROR {dest_rel}: mode=rewrite 的來源必須是 UTF-8 文字")
                else:
                    text, ok = apply_rules(text, entry["rules"], dest_rel, errors)
                    if ok:
                        expected = text.encode("utf-8")

        # --- 2. sha256 pin ---
        if expected is not None:
            actual_sha = sha256_bytes(expected)
            if actual_sha != entry["sha256"]:
                errors.append(
                    f"ERROR {dest_rel}: 刪改後輸出的 sha256 與 manifest 不符"
                    f"（manifest {entry['sha256'][:12]}…，實際 {actual_sha[:12]}…）"
                )
                expected = None

        # --- 3. 目的檔的狀態 ---
        if dest_path.is_symlink():
            errors.append(f"ERROR {dest_rel}: 目的檔是 symlink，公開樹不接受 symlink")
        elif dest_path.is_file():
            dest_bytes = dest_path.read_bytes()
            dest_sha = sha256_bytes(dest_bytes)
            if mode in ("pinned", "generate"):
                if dest_sha != entry["sha256"]:
                    errors.append(
                        f"ERROR {dest_rel}: mode={mode} 的 sha256 與 manifest 不符"
                        f"（manifest {entry['sha256'][:12]}…，實際 {dest_sha[:12]}…）"
                        "；手寫／生成檔改了就要更新 manifest"
                    )
            elif expected is not None and dest_bytes != expected:
                errors.append(
                    f"ERROR {dest_rel}: 目的檔與 mode={mode} 重建的結果不一致"
                    "（有人直接改了公開樹，或來源已漂移）"
                )
            check_absent(dest_bytes, dest_rel, absent, errors)
        elif mode in FROM_SOURCE:
            if not apply:
                errors.append(f"ERROR {dest_rel}: manifest 列了但公開樹沒有這個檔"
                              "（要寫出來請加 --apply）")
        else:
            errors.append(f"ERROR {dest_rel}: manifest 列了但公開樹沒有這個檔"
                          f"（mode={mode} 是手寫／由別的工具生成，本工具不會產生它）")

        if expected is not None:
            check_absent(expected, f"{dest_rel}（重建結果）", absent, errors)
            if mode in FROM_SOURCE:
                planned.append((dest_path, expected))

    # --- 4. 樹檢查：公開樹裡不得有 manifest 沒列的檔 ---
    declared = {entry["dest"].as_posix() for entry in entries}
    for rel in walk_tree(out):
        if rel not in declared:
            errors.append(f"ERROR {rel}: 公開樹裡有這個檔，但 manifest 沒列"
                          "（allowlist 是唯一入口）")

    if errors:
        for line in errors:
            print(line)
        print(f"\n{len(errors)} error(s)；fail-before-write：一個檔都沒寫。")
        return EXIT_FINDINGS

    if apply:
        written = 0
        for dest_path, content in planned:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(content)
            written += 1
        print(f"OK 0 error(s)；已寫出 {written} 個 copy／rewrite 檔，"
              f"共 {len(entries)} 條 manifest 條目。")
    else:
        print(f"OK 0 error(s)；{len(entries)} 條 manifest 條目全部一致（唯讀檢查）。")
    return EXIT_OK


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="export_public.py",
        description="依 allowlist manifest 把私有 vault 匯出成公開 repo（預設唯讀檢查）。",
    )
    parser.add_argument("--manifest", required=True, help="allowlist manifest（JSON）")
    parser.add_argument("--source", help="私有 vault 根目錄（有 copy／rewrite 條目時必填）")
    parser.add_argument("--out", required=True, help="公開 repo 工作副本根目錄")
    parser.add_argument("--check", action="store_true", help="唯讀檢查（預設行為）")
    parser.add_argument("--apply", action="store_true",
                        help="檢查全過才寫出 copy／rewrite 的檔；任一錯誤一個檔都不寫")
    parser.add_argument("--print-hashes", action="store_true",
                        help="印出每個 dest 目前的 sha256，供填 manifest 用；不做檢查")
    args = parser.parse_args(argv)

    if args.check and args.apply:
        print("ERROR --check 與 --apply 不能同時給", file=sys.stderr)
        return EXIT_CONFIG

    try:
        return run(
            manifest_path=Path(args.manifest),
            source=Path(args.source) if args.source else None,
            out=Path(args.out),
            apply=args.apply,
            print_hashes=args.print_hashes,
        )
    except ConfigError as exc:
        print(f"ERROR 設定錯誤：{exc}", file=sys.stderr)
        return EXIT_CONFIG


if __name__ == "__main__":
    sys.exit(main())
