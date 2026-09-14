#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_status_vocabulary.py — 範本教的詞彙與腳本認得的詞彙必須是同一套。

為什麼需要這一支
----------------
`bin/scan-state.sh` 讀 project card 的 `status`／`management_scope`／`intent` 決定怎麼
標活動量測。這三個欄位的**允許值**寫在 `docs/templates/project-card.md`，讀者照範本填。
一旦兩邊分岔，失敗是靜默的：卡片看起來填對了，快照卻把一個刻意凍結的專案評成
「⚫️ stale」——一份看起來正常、語意卻錯的報表，比沒有報表更貴。

判準分兩個方向：
1. 範本列得出來的每個值，腳本要嘛真的比對它，要嘛落在下面這張「已知會走預設分支」
   的清單裡（清單本身就是「我們決定它不需要特別處理」的紀錄）。
2. 腳本拿 `status` 去比對的每個值，範本要嘛列得出來，要嘛落在相容清單裡。

兩個方向都要，否則任何一邊新增詞彙都會悄悄變成單邊的方言。
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CARD = REPO_ROOT / "docs" / "templates" / "project-card.md"
SCRIPT = REPO_ROOT / "bin" / "scan-state.sh"

# 範本列得出來、但腳本刻意不特別處理的值：它們一律照檔案活動分級，
# 這就是「定義好的行為」。要讓某個值不再走預設分支，改腳本並把它從這裡拿掉。
MEASURED_BY_ACTIVITY = {"discovery", "planning", "pilot", "parked"}

# 腳本為了相容而接受、但不屬於卡片 `status:` 正式詞彙的值：
# `observe-only` 的正式位置是 `management_scope:`；`archive` 是索引頁
# （`template/03-wiki/projects.md`）那一套詞彙的寫法，卡片這邊寫 `archived`。
STATUS_COMPAT = {"observe-only", "archive"}

FIELD_RE = r"^%s: <([^>]*)>"


def template_values(field: str) -> set[str]:
    text = CARD.read_text(encoding="utf-8")
    match = re.search(FIELD_RE % field, text, re.MULTILINE)
    assert match, f"範本裡找不到 `{field}:` 那一行"
    raw = match.group(1).split("，")[0]
    return {part.strip() for part in raw.split("|") if part.strip()}


def script_status_comparisons() -> set[str]:
    text = SCRIPT.read_text(encoding="utf-8")
    return set(re.findall(r'"\$claimed"\s*==\s*"([a-z-]+)"', text))


class TestStatusVocabulary(unittest.TestCase):
    def test_every_template_status_has_defined_behaviour(self) -> None:
        listed = template_values("status")
        self.assertTrue(listed, "範本沒有列出任何 status 值")
        compared = script_status_comparisons()
        undefined = sorted(v for v in listed
                           if v not in compared and v not in MEASURED_BY_ACTIVITY)
        self.assertEqual(
            undefined, [],
            "範本列了這些 status，但 bin/scan-state.sh 既沒比對、也沒登記成"
            f"「照活動分級」：{undefined}",
        )

    def test_script_does_not_invent_status_words(self) -> None:
        listed = template_values("status") | STATUS_COMPAT
        stray = sorted(v for v in script_status_comparisons() if v not in listed)
        self.assertEqual(
            stray, [],
            f"bin/scan-state.sh 比對了範本沒教的 status 值：{stray}",
        )

    def test_template_documents_the_two_scan_state_fields(self) -> None:
        text = CARD.read_text(encoding="utf-8")
        for field in ("management_scope", "intent"):
            self.assertIn(f"{field}:", text,
                          f"範本的 frontmatter 沒有 `{field}:`，但腳本會讀它")
        self.assertEqual(template_values("management_scope"), {"owner", "observe-only"})
        self.assertEqual(template_values("intent"), {"active", "frozen", "retire"})

    def test_script_reads_the_documented_fields(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        for field in ("management_scope", "intent"):
            self.assertIn(f'fm "$page" {field}', text)


if __name__ == "__main__":
    unittest.main()
