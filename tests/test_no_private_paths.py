#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_no_private_paths.py — 工具、文件與 skill 不得指名道姓地引用私有 vault 的頁面。

為什麼需要這一支
----------------
三層掃描器對這一類是瞎的：私有頁名不是 secret 樣式（L1 不動）、不是結構異常（L3 不動），
L2 只在那個字剛好被收進禁用識別字清單時才會命中。而 `tools/build_references.py` 的
`ASSERT_ABSENT` 只跑在**產物**（`docs/REFERENCES.md`）上，從來不跑在產生器自己身上——
於是曾經發生過：被刻意擦掉的私有檔名整包留在產生器的原始碼裡，三道閘門全綠。

這支測試補那個缺口，判準是「具體 vs 慣例」：
`03-wiki/proj-<name>.md`、`03-wiki/review-*.md` 這種帶佔位符或萬用字元的**命名慣例**
是本 repo 要教的東西，完全正常；`03-wiki/proj-<某個真實名字>.md` 這種**具體頁名**
則代表有人把自己 vault 裡的某一頁寫進了公開檔。

掃描範圍涵蓋全樹，只排除 `template/` 與 `examples/` 兩棵——而且只有這兩棵：
那兩處的檔案是「讀者自己的 vault」，裡面出現 vault 相對路徑（含範例 vault 真的有的那幾頁）
本來就對。其餘每一棵都要掃，`office-agent-starter-kit/` 也在內：它既不是範本也不是範例，
而是全樹唯一一棵整包從私有專案目錄匯出的內容，最需要被這條性質鎖住。

自我匹配
--------
pattern 都寫成「原始碼文字本身不會命中自己」的形式（用 `0[0-9]` 而不是 `03`），
所以本檔自己也在掃描範圍內，不需要特例。
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SCAN_DIRS = ("tools", "bin", "docs", "skills", "tests", ".github",
             "office-agent-starter-kit")
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules"}

# 本 repo 真的有隨 `template/` 出貨的快查表頁；引用它不算指向誰的私有頁。
SHIPPED_REFERENCE_PAGES = ("secrets-hygiene",)

# 「祕密放在哪」的**形狀**描述。教材要教的通則是「位置本身就是機敏資訊」，
# 一旦為了舉例而寫出具體的路徑層級或檔案型態，那句話自己就成了指路——
# 三層掃描器對它完全瞎：不是 secret 樣式、不是結構異常、不是識別字。
#
# 規則本身**只描述通用形狀**（憑證類詞 ＋ 路徑前綴／可執行副檔名），不寫進任何一個
# 真實要素。曾經的寫法把「哪一層目錄」與「哪一種可執行檔」硬編在 regex 與反向測試裡，
# 於是規則自己就是一句完整的指路——`\uXXXX` escape 只擋得住 grep，跑一次 python 就還原了。
# 中文仍用 escape 拼出，好讓本檔的原始碼不含會命中自己的字面值
# （`test_patterns_do_not_match_their_own_source` 會替我們守著這一點）。
_CREDENTIAL_WORDS = "\u6191\u8b49|\u91d1\u9470|\u79c1\u9470|\u79d8\u5bc6|\u6e05\u518a"
_PLACED_AT = "\u5728|\u653e\u5728|\u4f4d\u65bc"  # 在／放在／位於
_PATH_PREFIX = r"(?:~/|/[A-Za-z])"           # 家目錄前綴或任何絕對路徑
_EXEC_EXT = r"\.(?:sh|bash|zsh|bat|cmd|ps1|command|exe)\b"
# 祕密存放位置的第三種形狀：**憑證類環境變數直接被賦值成一條真實路徑**。
# 這種寫法沒有動詞，所以繞得過上面那條「憑證類詞 ＋ 在／放在／位於 ＋ 路徑」的規則，
# 但它講的事情一模一樣：讀者照著就找得到那份東西放在哪一層。
# 規則同樣只描述形狀：變數名有一段是憑證類詞，值以家目錄前綴或絕對路徑開頭。
# 用佔位符（角括號、雙大括號、`$VAR`）寫的示範不會命中，教材照樣能給可讀的例子。
_CRED_ENV_WORDS = "KEY|SECRET|SECRETS|TOKEN|PASSWORD|CREDENTIAL|IDENTITY"

FORBIDDEN = [
    # 具體的私有 wiki 頁名（慣例寫法用 `*` 或角括號佔位符，不會命中）
    ("具體的私有 wiki 頁名", re.compile(r"0[0-9]-wiki/(?:ref|review|proj|worklog)-[a-z0-9]")),
    # 快查表層底下的具體頁名：那一層放的常是「哪些東西在哪裡」，點名任何一頁都是指路型洩漏
    ("私有快查表頁名",
     re.compile(r"0[0-9]-reference/(?!(?:%s)\b)[a-z0-9]" % "|".join(SHIPPED_REFERENCE_PAGES))),
    # 祕密存放位置的「路徑」描述（憑證類詞 ＋ 指向某條真實路徑）
    ("描述祕密存放位置的路徑",
     re.compile(r"(?:%s)[^\n]{0,12}(?:%s)[^\n]{0,4}%s"
                % (_CREDENTIAL_WORDS, _PLACED_AT, _PATH_PREFIX))),
    # 祕密存放位置的「檔案型態」描述（憑證類詞 ＋ 某種可執行檔）
    ("描述祕密存放位置的檔案型態",
     re.compile(r"(?:%s)[^\n]{0,12}%s" % (_CREDENTIAL_WORDS, _EXEC_EXT))),
    # 祕密存放位置的「賦值」描述（憑證類環境變數 ＋ 直接指向一條路徑）
    ("憑證類環境變數直接賦值成路徑",
     re.compile(r"(?<![A-Z0-9_])(?:[A-Z][A-Z0-9_]*_)?(?:%s)(?:_[A-Z0-9]+)*"
                r"\s*=\s*(?:~/|/[A-Za-z])" % _CRED_ENV_WORDS)),
]


def iter_text_files():
    for name in SCAN_DIRS:
        base = REPO_ROOT / name
        if base.is_dir():
            yield from _walk(base)
    for path in sorted(REPO_ROOT.glob("*.md")):
        if path.is_file():
            yield path


def _walk(base: Path):
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(REPO_ROOT).parts):
            continue
        yield path


def read_lines(path: Path):
    try:
        with path.open("rb") as handle:
            if b"\x00" in handle.read(4096):
                return []
        return path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []


class TestNoPrivateVaultPaths(unittest.TestCase):
    def test_no_concrete_private_page_names(self) -> None:
        hits = []
        for path in iter_text_files():
            relative = path.relative_to(REPO_ROOT).as_posix()
            for number, line in enumerate(read_lines(path), 1):
                for label, pattern in FORBIDDEN:
                    if pattern.search(line):
                        hits.append(f"{relative}:{number} {label}")
        self.assertEqual(
            hits, [],
            "有檔案引用了某個具體的 vault 頁名（不印命中值，自己開檔看）：\n" + "\n".join(hits),
        )

    def test_patterns_do_not_match_their_own_source(self) -> None:
        own = Path(__file__).read_text(encoding="utf-8")
        for label, pattern in FORBIDDEN:
            self.assertIsNone(pattern.search(own), f"pattern「{label}」會命中本檔自己")

    def test_patterns_still_catch_a_real_private_page(self) -> None:
        """反向測試：規則不能寬到連真的私有頁名都放過。"""
        # 形狀樣本一律憑空編：路徑與副檔名都挑本 repo 與作者都用不到的，
        # 這支測試自己不該變成任何人的尋寶圖。
        samples = ["03-wiki/" + "review-2026-0101-something.md",
                   "06-reference/" + "some-inventory-page.md",
                   # 下面兩則是形狀樣本，整句以 escape 拼出，避免本檔自我命中：
                   # 一則是「某類詞 ＋ 一條編出來的路徑」，一則是「某類詞 ＋ 一種可執行檔」。
                   "\u91d1\u9470\u6e05\u518a\u653e\u5728 /opt/nowhere/",
                   "\u6191\u8b49\u5728 setup.bat",
                   # 賦值形狀：字串拆開寫，免得本檔自己命中這條規則。
                   "export NOWHERE_AGE_" + "KEY=" + "~/nowhere/identity.txt"]
        for sample in samples:
            self.assertTrue(any(pattern.search(sample) for _, pattern in FORBIDDEN),
                            f"沒有任何規則抓到 {sample}")

    def test_shape_patterns_do_not_fire_on_category_lists(self) -> None:
        """正向測試：把「祕密位置」與「主目錄路徑」並列成類別清單不算描述形狀。"""
        benign = ("\u6191\u8b49\u4f4d\u7f6e\u3001"
                  "\u5bb6\u76ee\u9304\u8def\u5f91\u6df7\u5728\u540c\u4e00\u68f5\u6a39\u88e1")
        for label, pattern in FORBIDDEN:
            self.assertIsNone(pattern.search(benign), f"pattern「{label}」誤報了類別清單")

    def test_credential_env_rule_allows_placeholders(self) -> None:
        """正向測試：教材用佔位符寫懑證環境變數時不得誤報。"""
        benign = ["export NOWHERE_AGE_" + "KEY=<gitignored \u7684\u79c1\u9470\u8def\u5f91>",
                  "export NOWHERE_BLOCKLIST_" + "KEY_FILE=\"$RUNNER_TEMP/blocklist\"",
                  "PACKAGE_DIR=/usr/local/share",
                  "MONKEY=/tmp/not-a-credential"]
        for sample in benign:
            for label, pattern in FORBIDDEN:
                self.assertIsNone(pattern.search(sample),
                                  f"pattern「{label}」誤報了 {sample}")


if __name__ == "__main__":
    unittest.main()
