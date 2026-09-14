"""bin/gate.sh 的「不可被調鬆」性質。

gate 最危險的失效不是它報錯，是有人用一個旋鈕把它調到剛好綠。
這支測試把幾個曾經存在的旋鈕釘死：canary 門檻不可由環境變數改、
--full 不接受 --no-blocklist、scan_sensitive 的 error 計數斷言必須錨定、
canary 的樣本清單不可寫死任何私有 vault 路徑。
"""

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "bin" / "gate.sh"


class GateShHardeningTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = GATE.read_text(encoding="utf-8")

    def test_canary_threshold_is_a_constant(self) -> None:
        """CANARY_MIN 必須是寫死的 3，不得從環境變數取值。"""
        assignments = re.findall(r"^CANARY_MIN=.*$", self.source, flags=re.MULTILINE)
        self.assertEqual(assignments, ["CANARY_MIN=3"], "canary 門檻不可做成可調參數")
        self.assertNotIn(
            "${CANARY_MIN", self.source, "環境變數會讓 canary 一紅就被調鬆"
        )

    def test_no_env_switch_for_skipping_l2(self) -> None:
        """跳過 L2 只能靠明寫的 --no-blocklist，不可有隱藏的環境變數開關。"""
        self.assertNotIn("GATE_NO_BLOCKLIST", self.source)

    def test_full_refuses_no_blocklist(self) -> None:
        """--full --no-blocklist 必須直接拒絕（否則 canary 全 0 命中卻綠燈）。"""
        result = subprocess.run(
            ["bash", str(GATE), "--full", "--no-blocklist"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("--full 不接受 --no-blocklist", result.stderr)
        # 必須在跑任何檢查之前就退出，不是跑完才抱怨。
        self.assertNotIn("=== [01]", result.stdout)


    def test_error_count_assertion_is_anchored(self) -> None:
        """`0 error` 沒錨定的話，`10 error(s)` 也會滿足它。"""
        matches = re.findall(r"grep -q(E?) '([^']*0 error[^']*)'", self.source)
        self.assertTrue(matches, "找不到 scan_sensitive 的末行斷言")
        for flag, pattern in matches:
            self.assertEqual(flag, "E", f"{pattern} 需要 -E 才能錨定")
            compiled = re.compile(pattern)
            self.assertIsNotNone(compiled.search("Summary: 0 error(s), 0 warning(s)"))
            for bad in ("Summary: 10 error(s), 0 warning(s)",
                        "Summary: 20 error(s), 3 warning(s)",
                        "Summary: 100 error(s), 0 warning(s)"):
                self.assertIsNone(compiled.search(bad),
                                  f"{pattern} 會被「{bad}」滿足——等於沒有這道檢查")

    def test_canary_samples_come_from_the_private_side(self) -> None:
        """canary 要掃哪幾份由私有側的清單決定；公開檔不得寫死 vault 內的具體路徑。

        一份「這幾頁每頁都至少藏著 3 個識別字」的路徑表，沒有值，卻正好替人指路。
        """
        self.assertIn("canary-samples.txt", self.source)
        forbidden = re.findall(r'"\$VAULT_DIR"/(?!\$)\S+', self.source)
        self.assertEqual(forbidden, [],
                         f"gate.sh 直接寫出了私有 vault 的路徑：{forbidden}")


if __name__ == "__main__":
    unittest.main()
