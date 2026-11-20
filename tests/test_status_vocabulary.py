#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_status_vocabulary.py — 範本教的詞彙與腳本認得的詞彙必須是同一套。

為什麼需要這一支
----------------
`bin/scan-state.sh` 讀 project card 的 `subject_status`／`management_scope`／`intent` 決定怎麼
標活動量測。這三個欄位的**允許值**寫在 `docs/templates/project-card.md`，讀者照範本填。
一旦兩邊分岔，失敗是靜默的：卡片看起來填對了，快照卻把一個刻意凍結的專案評成
「⚫️ stale」——一份看起來正常、語意卻錯的報表，比沒有報表更貴。

判準分兩個方向：
1. 範本列得出來的每個值，腳本要嘛真的比對它，要嘛落在下面這張「已知會走預設分支」
   的清單裡（清單本身就是「我們決定它不需要特別處理」的紀錄）。
2. 腳本拿專案狀態去比對的每個值，範本要嘛列得出來，要嘛落在相容清單裡。

兩個方向都要，否則任何一邊新增詞彙都會悄悄變成單邊的方言。

0.2.0 起多了第三個要對齊的地方：`bin/status-vocab.json`。`bin/check_vault.py` 的代謝 gate 拿它
判斷 frontmatter 合不合法，所以範本教的每個值都必須在那份詞彙表裡——否則讀者照範本填完，
檢查器反而對他發 warning。`status`（記憶生命週期）與 `subject_status`（專案／skill 的狀態）
是兩套詞彙，任何一個字同時出現在兩邊都算錯（唯一的例外寫在 SHARED_BY_DESIGN）。
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = REPO_ROOT / "docs" / "templates"
CARD = TEMPLATES / "project-card.md"
SKILL_CARD = TEMPLATES / "skill-card.md"
SCRIPT = REPO_ROOT / "bin" / "scan-state.sh"
VOCAB = json.loads((REPO_ROOT / "bin" / "status-vocab.json").read_text(encoding="utf-8"))
LIFECYCLE = set(VOCAB["status"]["lifecycle"])
SUBJECT = set(VOCAB["subject_status"]["allowed"])

# 兩套詞彙理應不相交。目前沒有任何刻意共用的字；要加之前先想清楚讀者怎麼分得出來。
SHARED_BY_DESIGN: set[str] = set()

# 範本列得出來、但腳本刻意不特別處理的值：它們一律照檔案活動分級，
# 這就是「定義好的行為」。要讓某個值不再走預設分支，改腳本並把它從這裡拿掉。
MEASURED_BY_ACTIVITY = {"discovery", "planning", "pilot", "parked"}

# 腳本為了相容而接受、但不屬於卡片 `subject_status:` 正式詞彙的值：
# `observe-only` 的正式位置是 `management_scope:`；`archive` 是索引頁
# （`template/03-wiki/projects.md`）那一套詞彙的寫法，卡片這邊寫 `archived`。
STATUS_COMPAT = {"observe-only", "archive"}

FIELD_RE = r"^%s: <([^>]*)>"


def template_values(field: str, card: Path = CARD) -> set[str]:
    text = card.read_text(encoding="utf-8")
    match = re.search(FIELD_RE % field, text, re.MULTILINE)
    assert match, f"{card.name} 裡找不到 `{field}:` 那一行"
    raw = match.group(1).split("，")[0]
    return {part.strip() for part in raw.split("|") if part.strip()}


def script_status_comparisons() -> set[str]:
    text = SCRIPT.read_text(encoding="utf-8")
    return set(re.findall(r'"\$claimed"\s*==\s*"([a-z-]+)"', text))


class TestStatusVocabulary(unittest.TestCase):
    def test_every_template_status_has_defined_behaviour(self) -> None:
        listed = template_values("subject_status")
        self.assertTrue(listed, "範本沒有列出任何 subject_status 值")
        compared = script_status_comparisons()
        undefined = sorted(v for v in listed
                           if v not in compared and v not in MEASURED_BY_ACTIVITY)
        self.assertEqual(
            undefined, [],
            "範本列了這些 subject_status，但 bin/scan-state.sh 既沒比對、也沒登記成"
            f"「照活動分級」：{undefined}",
        )

    def test_script_does_not_invent_status_words(self) -> None:
        listed = template_values("subject_status") | STATUS_COMPAT
        stray = sorted(v for v in script_status_comparisons() if v not in listed)
        self.assertEqual(
            stray, [],
            f"bin/scan-state.sh 比對了範本沒教的專案狀態：{stray}",
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
        for field in ("subject_status", "status", "management_scope", "intent"):
            self.assertIn(f'fm "$page" {field}', text)


class TestVocabularyFile(unittest.TestCase):
    """範本、腳本與 `bin/status-vocab.json` 三邊必須是同一套字。"""

    def test_the_two_axes_do_not_share_words(self) -> None:
        self.assertEqual(sorted((LIFECYCLE & SUBJECT) - SHARED_BY_DESIGN), [],
                         "同一個字不能既是記憶生命週期、又是專案狀態")

    def test_card_templates_teach_exactly_the_lifecycle_the_gate_accepts(self) -> None:
        self.assertEqual(template_values("status"), LIFECYCLE,
                         "project-card 範本列的 status 必須就是整份生命週期詞彙")
        self.assertLessEqual(template_values("status", SKILL_CARD), LIFECYCLE,
                             "skill-card 範本教了檢查器不認得的 status")

    def test_every_subject_value_a_template_teaches_is_in_the_vocabulary(self) -> None:
        taught = (template_values("subject_status") | template_values("subject_status", SKILL_CARD)
                  | STATUS_COMPAT)
        self.assertEqual(sorted(taught - SUBJECT), [],
                         "範本教了這些 subject_status，但 bin/status-vocab.json 不認得")

    def test_every_frontmatter_status_in_shipped_templates_is_a_lifecycle_value(self) -> None:
        """`template/` 與 `docs/templates/` 裡每一個寫死的 `status:` 都要過得了代謝 gate。"""
        offenders = []
        for root in (REPO_ROOT / "template", TEMPLATES):
            for path in sorted(root.rglob("*.md")):
                for line in path.read_text(encoding="utf-8").splitlines():
                    match = re.match(r"^status:\s*(\S.*?)\s*$", line)
                    if not match or match.group(1).startswith("<"):
                        continue
                    if match.group(1) not in LIFECYCLE:
                        offenders.append(f"{path.relative_to(REPO_ROOT)}: status: {match.group(1)}")
        self.assertEqual(offenders, [])

    def test_scan_state_knows_the_same_lifecycle_words(self) -> None:
        """腳本用一個寫死的清單分辨「兩軸卡片」與「0.1.x 單軸卡片」；它必須就是詞彙表那六個字。"""
        text = SCRIPT.read_text(encoding="utf-8")
        match = re.search(r'^\s*((?:[a-z]+\|)+)""\) ;;$', text, re.MULTILINE)
        self.assertIsNotNone(match, "找不到 scan-state.sh 裡分辨生命週期詞彙的那一行")
        self.assertEqual(set(match.group(1).strip("|").split("|")), LIFECYCLE)

    def test_migration_table_only_derives_lifecycle_values(self) -> None:
        rules = VOCAB["derive_lifecycle_from_old_status"]
        self.assertIn(rules["default"], LIFECYCLE)
        for key in ("watchlist", "stale"):
            self.assertIn(key, LIFECYCLE)
            self.assertFalse(set(rules[key]) & LIFECYCLE,
                             f"`{key}` 那一列列了本來就是生命週期的值")


if __name__ == "__main__":
    unittest.main()
