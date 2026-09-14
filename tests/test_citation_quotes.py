#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_citation_quotes.py — 引用指到本 repo 的檔案時，引號裡的話必須真的在那個檔案裡。

為什麼需要這一支
----------------
`docs/REFERENCES.md` 存在的理由是「讓第三方能自己驗」：每一列都寫著「這個概念落在本 repo 的
哪個檔案」，很多列還把那個檔案裡的一句話用引號抄出來。這種引用有兩種安靜的壞法：

1. **引文是從別的地方抄來的。** 生成 `docs/REFERENCES.md` 的規則表只映射路徑，
   不映射引號內容，所以私有母本的用語會原封不動被發布，而它在公開版根本不存在。
2. **章節被刪改後編號位移。** 引用寫 §7，公開版刪節後那一節變成 §6，引用靜默漂移。

兩種都不是 secret 樣式、不是結構異常、不在禁用識別字清單裡——三層掃描器對它們完全瞎，
`publish_check.py` 的連結檢查也只驗「檔案存不存在」，不驗「引的話在不在裡面」。

判準
----
形如 `` `<repo 內路徑>`（§n）「引文」 `` 的引用：路徑必須存在，且引文必須逐字出現在那個檔案裡。
引文不一致時，要改的通常是引用端（或私有側的規則表），不是把這條測試放寬。
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# 掃「會寫引用」的那幾類文件：根目錄說明、docs/、skills/ 的 SKILL 與說明頁。
SCAN_GLOBS = ("*.md", "docs/*.md", "docs/templates/*.md", "skills/*/*.md")

# `路徑`（可選的 §n 或「的」）「引文」
CITATION_RE = re.compile(
    r"`([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:md|sh|py|json|yml))`"
    r"(?:\s*(?:§\d+|的))?\s*「([^」]{2,60})」"
)

# 引用夠多才代表這條性質真的在守著東西；regex 壞掉時不該靜悄悄地全過。
MIN_CITATIONS = 10


def iter_docs():
    seen = set()
    for pattern in SCAN_GLOBS:
        for path in sorted(REPO_ROOT.glob(pattern)):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path


class TestCitationQuotes(unittest.TestCase):
    def test_quoted_citations_exist_in_the_cited_file(self) -> None:
        problems = []
        count = 0
        for doc in iter_docs():
            text = doc.read_text(encoding="utf-8")
            label = doc.relative_to(REPO_ROOT).as_posix()
            for match in CITATION_RE.finditer(text):
                target_name, quote = match.group(1), match.group(2)
                target = REPO_ROOT / target_name
                count += 1
                if not target.is_file():
                    problems.append(f"{label}：引用的 `{target_name}` 不存在")
                    continue
                body = target.read_text(encoding="utf-8", errors="replace")
                if quote not in body:
                    problems.append(
                        f"{label}：`{target_name}` 裡找不到引文「{quote}」")
        self.assertEqual(problems, [], "引用對不上被引的檔案：\n" + "\n".join(problems))
        self.assertGreaterEqual(
            count, MIN_CITATIONS,
            f"只找到 {count} 筆引用，少於 {MIN_CITATIONS}——先確認 CITATION_RE 還抓得到東西")


if __name__ == "__main__":
    unittest.main()
