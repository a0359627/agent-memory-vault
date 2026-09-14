#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/export_public.py 的行為測試。

這些測試存在的理由只有一個：exporter 是 private→public 的唯一入口，
它「靜默放行」的每一種方式都必須有一個會 red 的測試守著。
全部在 tempfile 目錄跑，不碰真實 HOME、不碰任何真實 vault。
"""

from __future__ import annotations

import hashlib
import io
import json
import contextlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import export_public  # noqa: E402

EXIT_OK = export_public.EXIT_OK
EXIT_FINDINGS = export_public.EXIT_FINDINGS
EXIT_CONFIG = export_public.EXIT_CONFIG


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ExportCase(unittest.TestCase):
    """每個 case 自己有一組 source／out 目錄與一份 manifest。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="export-public-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.source = self.tmp / "vault"
        self.out = self.tmp / "public"
        self.source.mkdir()
        self.out.mkdir()

    # --- helpers -------------------------------------------------------
    def write_source(self, rel: str, text: str) -> None:
        path = self.source / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def write_out(self, rel: str, text: str) -> None:
        path = self.out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def manifest(self, files, assert_absent=None) -> Path:
        data = {"version": 1, "repo": "agent-memory-vault", "files": files}
        if assert_absent:
            data["assert_absent"] = assert_absent
        path = self.tmp / "manifest.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def run_tool(self, manifest_path: Path, *extra, source=True) -> tuple[int, str]:
        argv = ["--manifest", str(manifest_path), "--out", str(self.out)]
        if source:
            argv += ["--source", str(self.source)]
        argv += list(extra)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = export_public.main(argv)
        return code, buf.getvalue()


class TestHappyPath(ExportCase):
    def test_copy_rewrite_pinned_generate_all_agree(self):
        self.write_source("AGENTS.md", "照搬的內容\n")
        self.write_source("RULES.md", "適用於 my-private-vault 的維護\n語言使用繁體中文\n")
        rewritten = "適用於 本 vault 的維護\n語言使用 zh-TW\n"
        self.write_out("template/AGENTS.md", "照搬的內容\n")
        self.write_out("template/RULES.md", rewritten)
        self.write_out("README.md", "手寫的 README\n")
        self.write_out("docs/REFERENCES.md", "生成的文獻頁\n")

        manifest = self.manifest([
            {"dest": "template/AGENTS.md", "mode": "copy", "src": "AGENTS.md",
             "sha256": sha("照搬的內容\n")},
            {"dest": "template/RULES.md", "mode": "rewrite", "src": "RULES.md",
             "sha256": sha(rewritten),
             "rules": [
                 {"pattern": "my-private-vault", "replace": "本 vault", "expect": 1},
                 {"pattern": "繁體中文", "replace": " zh-TW", "expect": 1},
             ]},
            {"dest": "README.md", "mode": "pinned", "sha256": sha("手寫的 README\n")},
            {"dest": "docs/REFERENCES.md", "mode": "generate",
             "sha256": sha("生成的文獻頁\n")},
        ])
        code, output = self.run_tool(manifest)
        self.assertEqual(code, EXIT_OK, output)
        self.assertIn("0 error", output)


class TestCopy(ExportCase):
    def test_copy_content_mismatch_fails(self):
        """copy 模式：公開樹的內容必須等於來源。差一個字就紅。"""
        self.write_source("AGENTS.md", "來源內容\n")
        self.write_out("template/AGENTS.md", "來源內容（有人偷改了）\n")
        manifest = self.manifest([
            {"dest": "template/AGENTS.md", "mode": "copy", "src": "AGENTS.md",
             "sha256": sha("來源內容\n")},
        ])
        code, output = self.run_tool(manifest)
        self.assertEqual(code, EXIT_FINDINGS, output)
        self.assertIn("template/AGENTS.md", output)

    def test_copy_missing_source_fails(self):
        self.write_out("template/AGENTS.md", "x\n")
        manifest = self.manifest([
            {"dest": "template/AGENTS.md", "mode": "copy", "src": "AGENTS.md",
             "sha256": sha("x\n")},
        ])
        code, output = self.run_tool(manifest)
        self.assertEqual(code, EXIT_FINDINGS, output)
        self.assertIn("來源不存在", output)


class TestRewriteExpect(ExportCase):
    """expect 是「刪改清單」變成可執行斷言的那一刀：命中 0 次與命中太多次都要 fail。"""

    def _manifest_with_expect(self, expect: int, out_text: str):
        self.write_out("template/RULES.md", out_text)
        return self.manifest([
            {"dest": "template/RULES.md", "mode": "rewrite", "src": "RULES.md",
             "sha256": sha(out_text),
             "rules": [{"pattern": "私有名字", "replace": "本 vault", "expect": expect}]},
        ])

    def test_expect_hit_zero_fails(self):
        """來源漂移、規則失效 → 命中 0 次。這是最危險的一種：規則還在，但什麼都沒改到。"""
        self.write_source("RULES.md", "這裡已經沒有那個詞了\n")
        manifest = self._manifest_with_expect(1, "這裡已經沒有那個詞了\n")
        code, output = self.run_tool(manifest)
        self.assertEqual(code, EXIT_FINDINGS, output)
        self.assertIn("命中 0 次", output)
        self.assertIn("expect 1 次", output)

    def test_expect_hit_more_than_declared_fails(self):
        """來源長出第三處 → 命中多於 expect。代表規則比作者以為的更寬，可能改到不該改的地方。"""
        self.write_source("RULES.md", "私有名字 A\n私有名字 B\n私有名字 C\n")
        expected = "本 vault A\n本 vault B\n本 vault C\n"
        manifest = self._manifest_with_expect(2, expected)
        code, output = self.run_tool(manifest)
        self.assertEqual(code, EXIT_FINDINGS, output)
        self.assertIn("命中 3 次", output)
        self.assertIn("expect 2 次", output)

    def test_expect_exact_hit_passes(self):
        self.write_source("RULES.md", "私有名字 A\n私有名字 B\n")
        expected = "本 vault A\n本 vault B\n"
        manifest = self._manifest_with_expect(2, expected)
        code, output = self.run_tool(manifest)
        self.assertEqual(code, EXIT_OK, output)

    def test_rewrite_output_differs_from_dest_fails(self):
        """規則都命中了，但公開樹的檔被手改過 → 仍然要紅。"""
        self.write_source("RULES.md", "私有名字\n")
        self.write_out("template/RULES.md", "本 vault\n加了一行沒人知道的話\n")
        manifest = self.manifest([
            {"dest": "template/RULES.md", "mode": "rewrite", "src": "RULES.md",
             "sha256": sha("本 vault\n"),
             "rules": [{"pattern": "私有名字", "replace": "本 vault", "expect": 1}]},
        ])
        code, output = self.run_tool(manifest)
        self.assertEqual(code, EXIT_FINDINGS, output)
        self.assertIn("不一致", output)


class TestSha256(ExportCase):
    def test_pinned_sha_mismatch_fails(self):
        """pinned 是手寫檔，沒有來源可比對，sha256 是它唯一的 gate。"""
        self.write_out("README.md", "改過的 README\n")
        manifest = self.manifest([
            {"dest": "README.md", "mode": "pinned", "sha256": sha("原本的 README\n")},
        ])
        code, output = self.run_tool(manifest, source=False)
        self.assertEqual(code, EXIT_FINDINGS, output)
        self.assertIn("sha256 與 manifest 不符", output)

    def test_generate_sha_mismatch_fails(self):
        self.write_out("docs/REFERENCES.md", "被手改的生成檔\n")
        manifest = self.manifest([
            {"dest": "docs/REFERENCES.md", "mode": "generate", "sha256": sha("生成檔\n")},
        ])
        code, output = self.run_tool(manifest, source=False)
        self.assertEqual(code, EXIT_FINDINGS, output)
        self.assertIn("sha256 與 manifest 不符", output)

    def test_rewrite_sha_pin_catches_rule_drift(self):
        """所有規則都恰好命中，但輸出不是 manifest pin 住的那份 → sha256 擋下。"""
        self.write_source("RULES.md", "私有名字\n來源新增的一行\n")
        expected_now = "本 vault\n來源新增的一行\n"
        self.write_out("template/RULES.md", expected_now)
        manifest = self.manifest([
            {"dest": "template/RULES.md", "mode": "rewrite", "src": "RULES.md",
             "sha256": sha("本 vault\n"),
             "rules": [{"pattern": "私有名字", "replace": "本 vault", "expect": 1}]},
        ])
        code, output = self.run_tool(manifest)
        self.assertEqual(code, EXIT_FINDINGS, output)
        self.assertIn("sha256", output)


class TestTree(ExportCase):
    def test_extra_file_in_public_tree_fails(self):
        """allowlist 是唯一入口：公開樹裡多一個 manifest 沒列的檔就是 ERROR。"""
        self.write_out("README.md", "手寫\n")
        self.write_out("notes/leftover.md", "不該在這裡的東西\n")
        manifest = self.manifest([
            {"dest": "README.md", "mode": "pinned", "sha256": sha("手寫\n")},
        ])
        code, output = self.run_tool(manifest, source=False)
        self.assertEqual(code, EXIT_FINDINGS, output)
        self.assertIn("notes/leftover.md", output)
        self.assertIn("manifest 沒列", output)

    def test_missing_file_in_public_tree_fails(self):
        """manifest 列了卻不存在（唯讀檢查模式）→ ERROR。"""
        self.write_out("README.md", "手寫\n")
        manifest = self.manifest([
            {"dest": "README.md", "mode": "pinned", "sha256": sha("手寫\n")},
            {"dest": "docs/gone.md", "mode": "generate", "sha256": sha("x\n")},
        ])
        code, output = self.run_tool(manifest, source=False)
        self.assertEqual(code, EXIT_FINDINGS, output)
        self.assertIn("docs/gone.md", output)

    def test_ignored_noise_does_not_break_tree_check(self):
        self.write_out("README.md", "手寫\n")
        (self.out / ".git").mkdir()
        (self.out / ".git" / "config").write_text("x", encoding="utf-8")
        (self.out / "__pycache__").mkdir()
        (self.out / "__pycache__" / "x.pyc").write_bytes(b"\x00")
        manifest = self.manifest([
            {"dest": "README.md", "mode": "pinned", "sha256": sha("手寫\n")},
        ])
        code, output = self.run_tool(manifest, source=False)
        self.assertEqual(code, EXIT_OK, output)

    def test_symlink_in_public_tree_fails(self):
        self.write_out("README.md", "手寫\n")
        (self.out / "link.md").symlink_to(self.out / "README.md")
        manifest = self.manifest([
            {"dest": "README.md", "mode": "pinned", "sha256": sha("手寫\n")},
        ])
        code, output = self.run_tool(manifest, source=False)
        self.assertEqual(code, EXIT_FINDINGS, output)
        self.assertIn("link.md", output)


class TestAssertAbsent(ExportCase):
    def test_assert_absent_hit_fails_and_never_prints_the_value(self):
        """assert_absent 命中要 fail，而且錯誤訊息只給檔名、行號與 pattern，不印命中值。"""
        secret_word = "narwhal-prod-4821"
        self.write_out("README.md", f"第一行\n部署在 {secret_word} 上\n")
        manifest = self.manifest(
            [{"dest": "README.md", "mode": "pinned",
              "sha256": sha(f"第一行\n部署在 {secret_word} 上\n")}],
            assert_absent=[r"narwhal-prod-[0-9]{4}"],
        )
        code, output = self.run_tool(manifest, source=False)
        self.assertEqual(code, EXIT_FINDINGS, output)
        self.assertIn("README.md:2", output)
        self.assertNotIn(secret_word, output)

    def test_assert_absent_checks_the_rebuilt_content_too(self):
        """來源有殘留、規則沒清乾淨時，重建結果也要被掃到——不能只靠公開樹已經寫好的那份。"""
        self.write_source("RULES.md", "私有名字\nclient-atlas 的專用規則\n")
        expected = "本 vault\nclient-atlas 的專用規則\n"
        self.write_out("template/RULES.md", expected)
        manifest = self.manifest(
            [{"dest": "template/RULES.md", "mode": "rewrite", "src": "RULES.md",
              "sha256": sha(expected),
              "rules": [{"pattern": "私有名字", "replace": "本 vault", "expect": 1}]}],
            assert_absent=[r"client-atlas"],
        )
        code, output = self.run_tool(manifest)
        self.assertEqual(code, EXIT_FINDINGS, output)
        self.assertIn("assert_absent", output)


class TestApplyIsAllOrNothing(ExportCase):
    def test_apply_writes_nothing_when_any_check_fails(self):
        """fail-before-write：一個檔錯，整批都不寫。半套的匯出比沒匯出更危險。"""
        self.write_source("ok.md", "乾淨內容\n")
        self.write_source("bad.md", "私有名字\n")
        manifest = self.manifest([
            {"dest": "template/ok.md", "mode": "copy", "src": "ok.md",
             "sha256": sha("乾淨內容\n")},
            {"dest": "template/bad.md", "mode": "rewrite", "src": "bad.md",
             "sha256": sha("本 vault\n"),
             "rules": [{"pattern": "不存在的詞", "replace": "x", "expect": 1}]},
        ])
        code, output = self.run_tool(manifest, "--apply")
        self.assertEqual(code, EXIT_FINDINGS, output)
        self.assertIn("一個檔都沒寫", output)
        self.assertFalse((self.out / "template" / "ok.md").exists(),
                         "有錯誤時連合格的檔也不能寫出去")
        self.assertFalse((self.out / "template" / "bad.md").exists())

    def test_apply_writes_everything_when_clean(self):
        self.write_source("ok.md", "乾淨內容\n")
        self.write_source("rules.md", "私有名字\n")
        manifest = self.manifest([
            {"dest": "template/ok.md", "mode": "copy", "src": "ok.md",
             "sha256": sha("乾淨內容\n")},
            {"dest": "template/rules.md", "mode": "rewrite", "src": "rules.md",
             "sha256": sha("本 vault\n"),
             "rules": [{"pattern": "私有名字", "replace": "本 vault", "expect": 1}]},
        ])
        code, output = self.run_tool(manifest, "--apply")
        self.assertEqual(code, EXIT_OK, output)
        self.assertEqual((self.out / "template" / "ok.md").read_text(encoding="utf-8"),
                         "乾淨內容\n")
        self.assertEqual((self.out / "template" / "rules.md").read_text(encoding="utf-8"),
                         "本 vault\n")
        # 寫完之後再跑一次唯讀檢查必須是綠的
        code, output = self.run_tool(manifest)
        self.assertEqual(code, EXIT_OK, output)

    def test_apply_does_not_invent_pinned_files(self):
        """--apply 只寫 copy／rewrite；手寫檔不存在時是 ERROR，不是「幫你建一個空的」。"""
        manifest = self.manifest([
            {"dest": "README.md", "mode": "pinned", "sha256": sha("手寫\n")},
        ])
        code, output = self.run_tool(manifest, "--apply", source=False)
        self.assertEqual(code, EXIT_FINDINGS, output)
        self.assertFalse((self.out / "README.md").exists())


class TestManifestValidation(ExportCase):
    def _expect_config_error(self, files, fragment, **kwargs):
        manifest = self.manifest(files, **kwargs)
        code, output = self.run_tool(manifest, source=False)
        self.assertEqual(code, EXIT_CONFIG, output)
        self.assertIn(fragment, output)

    def test_absolute_dest_rejected(self):
        self._expect_config_error(
            [{"dest": "/etc/passwd", "mode": "pinned", "sha256": sha("x")}],
            "絕對路徑")

    def test_dotdot_dest_rejected(self):
        self._expect_config_error(
            [{"dest": "../escape.md", "mode": "pinned", "sha256": sha("x")}],
            "'..'")

    def test_duplicate_dest_rejected(self):
        self._expect_config_error(
            [{"dest": "a.md", "mode": "pinned", "sha256": sha("x")},
             {"dest": "a.md", "mode": "pinned", "sha256": sha("y")}],
            "dest 重複")

    def test_unknown_mode_rejected(self):
        self._expect_config_error(
            [{"dest": "a.md", "mode": "template", "sha256": sha("x")}],
            "mode 必須是")

    def test_expect_zero_rejected(self):
        """expect 0 等於「這條規則可以不命中」，那就不是 gate 了，直接在 manifest 層拒絕。"""
        self._expect_config_error(
            [{"dest": "a.md", "mode": "rewrite", "src": "a.md", "sha256": sha("x"),
              "rules": [{"pattern": "x", "replace": "y", "expect": 0}]}],
            "expect 必須是")

    def test_missing_sha_rejected(self):
        self._expect_config_error(
            [{"dest": "a.md", "mode": "pinned"}],
            "sha256 必須是")

    def test_rewrite_without_rules_rejected(self):
        self._expect_config_error(
            [{"dest": "a.md", "mode": "rewrite", "src": "a.md", "sha256": sha("x")}],
            "必須有非空的 rules")

    def test_copy_or_rewrite_without_source_flag_is_config_error(self):
        self.write_out("template/a.md", "x\n")
        manifest = self.manifest([
            {"dest": "template/a.md", "mode": "copy", "src": "a.md", "sha256": sha("x\n")},
        ])
        code, output = self.run_tool(manifest, source=False)
        self.assertEqual(code, EXIT_CONFIG, output)
        self.assertIn("--source", output)

    def test_check_and_apply_together_rejected(self):
        manifest = self.manifest([
            {"dest": "a.md", "mode": "pinned", "sha256": sha("x")},
        ])
        code, output = self.run_tool(manifest, "--check", "--apply", source=False)
        self.assertEqual(code, EXIT_CONFIG, output)


class TestExampleManifestStaysValid(unittest.TestCase):
    """tools/public-allowlist.example.json 是文件的一部分；它必須永遠通得過 schema 檢查。"""

    def test_example_manifest_parses(self):
        example = REPO_ROOT / "tools" / "public-allowlist.example.json"
        self.assertTrue(example.is_file(), f"缺檔：{example}")
        parsed = export_public.load_manifest(example)
        self.assertTrue(parsed["entries"])
        self.assertTrue(parsed["assert_absent"])


if __name__ == "__main__":
    unittest.main()
