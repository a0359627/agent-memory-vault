#!/usr/bin/env python3
"""build_identifier_blocklist.py — 明文識別字清單 ＋ key → bin/identifier-blocklist.hmac。

明文清單與 key **都不進 repo**；產出的 .hmac 進 repo，但因為是 HMAC 而非無鹽
sha256，拿到檔案的人無法用字典撞出「作者的清單裡有誰」。

清單格式（每行）：
    <category>\t<token>
'#' 開頭是註解，空行略過。

正規化與掃描器（tools/publish_check.py）共用同一條規則：
    NFKC → lowercase → 去除所有空白
key_bytes = open(key_file).read().strip().encode('utf-8')

收錄門檻：正規化後 ASCII token 長度 < 6、CJK token 長度 < 2 一律不收
（太短會在正常文字裡誤報，且掃描器本來就不產生這麼短的候選）。

多詞 token（例如兩個字的人名）以正規化後的「去空白整串」收錄；掃描器會把
相鄰的 ASCII 連續段接起來當候選，所以文字裡寫成「Firstname Lastname」也擋得住。
**不**拆成單詞收錄——拆出來的通用字會在正常英文散文裡誤報（實測會打到
第三方 skill 的英文說明），那種誤報只會逼人放寬 gate。

補收有三種，數量都會印出來，但永遠不印明文：

1. 長度 > 6 的 CJK token 的所有長度 6 滑動視窗（掃描器最長只取 6-gram，不補就漏）。
2. **掃描器產得出來的形狀**：掃描器的 ASCII 候選一定從英數字開始，所以主目錄路徑
   片段那種「開頭是斜線、結尾是連字號」的 token，原樣收錄永遠不會命中。
   補收去掉頭尾非英數字元後的形狀。
3. **分隔符號互換／去除的形狀**：正規化只做 NFKC→lowercase→去空白，**不**統一
   `-`／`_`／`.`，所以 `foo-bar-baz` 與 `FOO_BAR_BAZ` 是兩個完全不同的 HMAC——
   差一個分隔符號就能繞過 L2，而且「剛好沒命中」看起來跟「閘門判斷過」一模一樣。
   清單這一側把四種形狀（全 `-`／全 `_`／全 `.`／完全去掉）都收進來。

收錄完還會做一次**可達性自檢**：把 token 原文當成一行餵進掃描器的候選產生器，
任何一個收錄形狀都產不出來就拒絕生成——否則清單看起來有那一項，實際上是死的，
而 canary 只會在剛好沒有別的命中時才發現（見 docs/gates.md）。

用法：
    build_identifier_blocklist.py --tokens <txt> --key-file <key> --out <hmac> \\
        [--require-categories person,company,domain,cloud,home_fragment,private_repo]
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import sys
import unicodedata
from pathlib import Path

# 必須在 import 兄弟模組**之前**。CPython 把「編譯當時的來源絕對路徑」寫進 .pyc 的
# co_filename，所以每個 __pycache__ 都帶著維護者的家目錄與使用者名稱；而 bin/gate.sh
# 有一步會把工作樹裡的 build 產物擋成紅燈。文件叫讀者直接跑這一支，所以它要自己關掉，
# 不能靠呼叫端記得設環境變數。（office kit 的 validate_kit.py 是同樣做法。）
sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_check import iter_candidates  # noqa: E402  掃描器與產生器必須共用同一份候選規則

ASCII_MIN_LEN = 6
CJK_MIN_LEN = 2
CJK_WINDOW = 6

DEFAULT_REQUIRED = "person,company,domain,cloud,home_fragment,private_repo"

HEADER = (
    "# identifier blocklist — HMAC-SHA256(key, normalized_token)\n"
    "# 由 tools/build_identifier_blocklist.py 產生；明文清單與 key 都不在本 repo。\n"
    "# 正規化：NFKC → lowercase → 去除所有空白。\n"
    "# 掃描方式與已知限制見 docs/gates.md（同音、拼音、縮寫抓不到）。\n"
)


def normalize_token(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).lower()
    return "".join(ch for ch in folded if not ch.isspace())


def has_cjk(text: str) -> bool:
    return any("㐀" <= ch <= "鿿" for ch in text)


def passes_threshold(token: str) -> bool:
    if not token:
        return False
    minimum = CJK_MIN_LEN if has_cjk(token) else ASCII_MIN_LEN
    return len(token) >= minimum


def parse_tokens(path: Path) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" not in line:
            raise SystemExit(f"第 {number} 行沒有 TAB 分隔的 <category>\\t<token>")
        category, token = line.split("\t", 1)
        category = category.strip()
        token = token.strip()
        if not category or not token:
            raise SystemExit(f"第 {number} 行的類別或 token 是空的")
        entries.append((category, token))
    return entries


def scanner_trim(token: str) -> str:
    """去掉掃描器候選不可能帶著的頭尾符號（開頭的斜線、結尾的連字號等）。"""
    start, end = 0, len(token)
    while start < end and not token[start].isalnum():
        start += 1
    while end > start and not token[end - 1].isalnum():
        end -= 1
    return token[start:end]


SEPARATOR_CHARS = "-_."


def separator_variants(token: str) -> list[str]:
    """分隔符號互換／去除後的形狀（見模組說明第 3 點）。"""
    if not any(ch in token for ch in SEPARATOR_CHARS):
        return []
    shapes = []
    for replacement in ("-", "_", ".", ""):
        shape = "".join(replacement if ch in SEPARATOR_CHARS else ch for ch in token)
        if shape != token:
            shapes.append(shape)
    return shapes


def expansions(token: str) -> list[str]:
    """token 本體之外的補收項目（見模組說明）。"""
    extra: list[str] = []
    normalized_whole = normalize_token(token)
    if has_cjk(normalized_whole) and len(normalized_whole) > CJK_WINDOW:
        for start in range(0, len(normalized_whole) - CJK_WINDOW + 1):
            extra.append(normalized_whole[start : start + CJK_WINDOW])
    trimmed = scanner_trim(normalized_whole)
    if trimmed and trimmed != normalized_whole:
        extra.append(trimmed)
    for base in (normalized_whole, trimmed):
        if base:
            extra.extend(separator_variants(base))
    return extra


def reachable_forms(token: str) -> set[str]:
    """掃描器把 token 原文當成一行時，產得出來的所有正規化候選。"""
    return {normalize_token(candidate) for candidate in iter_candidates(token)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="build_identifier_blocklist.py")
    parser.add_argument("--tokens", required=True, help="明文清單（category<TAB>token）")
    parser.add_argument("--key-file", required=True, help="HMAC key 檔（不進 repo）")
    parser.add_argument("--out", required=True, help="輸出的 .hmac 路徑")
    parser.add_argument(
        "--require-categories",
        default=DEFAULT_REQUIRED,
        help=f"必須非空的類別，逗號分隔（預設 {DEFAULT_REQUIRED}）",
    )
    args = parser.parse_args(argv)

    tokens_path = Path(args.tokens).expanduser()
    key_path = Path(args.key_file).expanduser()
    out_path = Path(args.out).expanduser()

    if not tokens_path.is_file():
        print(f"ERROR: 找不到明文清單 {tokens_path}", file=sys.stderr)
        return 1
    if not key_path.is_file():
        print(f"ERROR: 找不到 key 檔 {key_path}", file=sys.stderr)
        return 1

    key = key_path.read_text(encoding="utf-8").strip().encode("utf-8")
    if not key:
        print("ERROR: key 檔是空的", file=sys.stderr)
        return 1

    entries = parse_tokens(tokens_path)
    if not entries:
        print("ERROR: 明文清單沒有任何項目", file=sys.stderr)
        return 1

    accepted: dict[str, set[str]] = {}
    digests: set[str] = set()
    skipped_short = 0
    extra_count = 0

    def add(token: str) -> bool:
        if not passes_threshold(token):
            return False
        digests.add(hmac.new(key, token.encode("utf-8"), hashlib.sha256).hexdigest())
        return True

    unreachable: list[str] = []

    for category, token in entries:
        normalized = normalize_token(token)
        kept: list[str] = []
        if add(normalized):
            accepted.setdefault(category, set()).add(normalized)
            kept.append(normalized)
        else:
            skipped_short += 1
        for piece in expansions(token):
            if piece != normalized and add(piece):
                extra_count += 1
                kept.append(piece)
        if kept:
            produced = reachable_forms(token)
            if not any(form in produced for form in kept):
                unreachable.append(category)

    if unreachable:
        print(
            "ERROR: 下列類別有 token 的任何收錄形狀掃描器都產不出候選，拒絕生成："
            + "、".join(sorted(set(unreachable)))
            + "（清單會看起來有那一項，實際上永遠不會命中）",
            file=sys.stderr,
        )
        return 1

    required = [name.strip() for name in args.require_categories.split(",") if name.strip()]
    missing = [name for name in required if not accepted.get(name)]
    if missing:
        print(
            "ERROR: 下列必要類別在門檻後沒有任何項目，拒絕生成："
            + "、".join(missing),
            file=sys.stderr,
        )
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"{digest}\n" for digest in sorted(digests))
    out_path.write_text(HEADER + body, encoding="utf-8")

    print(f"讀入 {len(entries)} 個 token，涵蓋 {len(accepted)} 個類別")
    print(f"低於門檻略過 {skipped_short} 個（ASCII <{ASCII_MIN_LEN}／CJK <{CJK_MIN_LEN}）")
    print(f"補收 {extra_count} 個部件／視窗／修剪形狀")
    print(f"寫出 {len(digests)} 條 HMAC → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
