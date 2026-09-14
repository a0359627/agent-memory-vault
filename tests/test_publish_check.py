#!/usr/bin/env python3
"""tests/test_publish_check.py — 三層掃描器與識別字清單產生器的測試。

全部在 tempfile 目錄裡跑，不碰真實 HOME、不碰本 repo 的 bin/identifier-blocklist.hmac。

注意：本檔自己也會被 `publish_check.py .` 掃到，所以所有「應該被抓到」的樣本
都用字串拼接寫成，讓樣本在測試執行時才組合出來、在原始碼裡不成形。
這不是為了繞過掃描，是為了讓測試檔本身乾淨（樣本都是虛構值）。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLISH_CHECK = REPO_ROOT / "tools" / "publish_check.py"
BUILD_BLOCKLIST = REPO_ROOT / "tools" / "build_identifier_blocklist.py"


def cat(*parts: str) -> str:
    """把樣本在執行期組起來（見模組說明）。"""
    return "".join(parts)


# --- L1 樣本（全部是虛構值） -------------------------------------------------
L1_SAMPLES = {
    "google-api-key": cat("AIza", "B" * 35),
    "openai-project-key": cat("sk-proj-", "a" * 24),
    "anthropic-key": cat("sk-ant-", "A" * 24),
    "openai-style-key": cat("sk-", "z" * 30),
    "github-token": cat("ghp_", "b" * 36),
    "slack-token": cat("xoxb-", "1" * 12, "-", "2" * 12),
    "aws-access-key": cat("AKIA", "C" * 16),
    "google-oauth-secret": cat("GOCSPX-", "d" * 20),
    "age-secret-key": cat("AGE-SECRET-KEY-", "E" * 40),
    "private-key-block": cat("-----BEGIN ", "OPENSSH ", "PRIVATE KEY-----"),
    "assigned-secret": cat("api", "_key = ", "Zq7vN2pL8xT4wR"),
}

# --- L3 樣本 ----------------------------------------------------------------
HOME_PATH = cat("/Us", "ers/alice/vault/notes.md")
WINDOWS_PATH = cat("C:", "\\Users\\alice\\vault")
EXPORTED_PROJECT = cat("-Us", "ers-alice-my-vault")
REAL_EMAIL = cat("alice.chen@", "not-a-real-host.test")  # .test 是 RFC 6761 保留 TLD，永遠不會被註冊
PHONE = cat("09", "12345678")
UUID_V4 = cat("3f2504e0-4f89-41d3-", "9a0c-0305e82c3301")
IPV4 = cat("203.", "0.113.7")
SESSION_ID = cat("originSessionId", ": 7f3a")
GCS_URI = cat("gs:", "//some-bucket/exports")
INTERNAL_HOST = cat("build-node", ".internal")
CLOUD_PROJECT = cat("projects/", "123456789012")
DEPLOY_FLAG = cat("--set-env", "-vars=MODE=live")
MUSTACHE = cat("{", "{OWNER}", "}")

# --- L2 樣本（純虛構識別字） -------------------------------------------------
FAKE_TOKENS = [
    ("person", "Peregrine Thistlewood"),
    ("company", "Flibbertigibbet Works"),
    ("domain", "wobblegoose.test"),
    ("cloud", "nimbus-quokka-4242"),
    ("home_fragment", "marzipanuser"),
    ("private_repo", "clandestine-abacus"),
    ("internal_system", "紫色河馬"),
]
FAKE_KEY = "d41d8cd98f00b204e9800998ecf8427e"


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def run_check(*args: str, env: dict[str, str] | None = None, stdin: str | None = None):
    environ = os.environ.copy()
    environ.pop("IDENTIFIER_BLOCKLIST_KEY_FILE", None)
    environ.pop("IDENTIFIER_BLOCKLIST_FILE", None)
    if env:
        environ.update(env)
    return subprocess.run(
        [sys.executable, str(PUBLISH_CHECK), *args],
        capture_output=True,
        text=True,
        input=stdin,
        env=environ,
    )


def summary(stdout: str) -> str:
    lines = [line for line in stdout.splitlines() if line.strip()]
    return lines[-1] if lines else ""


class ScannerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="publish-check-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = self.tmp / "repo"
        self.root.mkdir()

    def make_blocklist(self, tokens=FAKE_TOKENS) -> tuple[Path, dict[str, str]]:
        """在 temp 目錄產生 .hmac＋key，回傳 (hmac 路徑, 要注入的環境變數)。"""
        tokens_file = self.tmp / "tokens.txt"
        tokens_file.write_text(
            "# 虛構清單\n" + "".join(f"{category}\t{token}\n" for category, token in tokens),
            encoding="utf-8",
        )
        key_file = self.tmp / "hmac.key"
        key_file.write_text(FAKE_KEY + "\n", encoding="utf-8")
        out = self.root / "bin" / "identifier-blocklist.hmac"
        result = subprocess.run(
            [
                sys.executable,
                str(BUILD_BLOCKLIST),
                "--tokens",
                str(tokens_file),
                "--key-file",
                str(key_file),
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(out.is_file())
        return out, {"IDENTIFIER_BLOCKLIST_KEY_FILE": str(key_file)}


class TestCleanTree(ScannerTestCase):
    def test_clean_tree_exits_zero(self) -> None:
        write(self.root / "README.md", "# 乾淨的檔案\n\n沒有秘密、沒有絕對路徑。\n")
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(summary(result.stdout), "L1 0 / L2 0 / L3 0")

    def test_missing_root_is_config_error(self) -> None:
        result = run_check(str(self.root / "nope"))
        self.assertEqual(result.returncode, 3)


class TestLayerOne(ScannerTestCase):
    def test_every_secret_pattern_is_detected(self) -> None:
        body = "\n".join(f"{kind}: {sample}" for kind, sample in L1_SAMPLES.items())
        write(self.root / "leak.txt", body + "\n")
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 2)
        for kind in L1_SAMPLES:
            self.assertIn(kind, result.stdout, f"{kind} 沒有被抓到")

    def test_placeholders_do_not_false_positive(self) -> None:
        lines = [
            "api_key = <your-api-key>",
            "GOOGLE_API_KEY = 'example-value-not-a-real-key'",
            "password: changeme-please-change-me",
            "client_secret = redacted-before-publishing",
            "access_token: " + MUSTACHE,
        ]
        write(self.root / "template" / "docs.md", "\n".join(lines) + "\n")
        result = run_check(str(self.root))
        self.assertEqual(summary(result.stdout), "L1 0 / L2 0 / L3 0", result.stdout)
        self.assertEqual(result.returncode, 0)

    def test_comment_on_the_same_line_does_not_disable_l1(self) -> None:
        """真 key 旁邊寫一句註解，不能把整行的 L1 關掉。

        佔位符白名單一度是整行判定，於是 `KEY=<真 key>  # example value` 全綠——
        而「在 key 旁邊寫註解」正是人貼 key 時最常做的事。
        """
        lines = [
            f"GOOGLE_API_KEY={L1_SAMPLES['google-api-key']}  # <see docs>",
            f"export ANTHROPIC_API_KEY={L1_SAMPLES['anthropic-key']}  # example value",
        ]
        write(self.root / "notes.md", "\n".join(lines) + "\n")
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("google-api-key", result.stdout)
        self.assertIn("anthropic-key", result.stdout)

    def test_second_scanner_also_scopes_the_placeholder_whitelist(self) -> None:
        """bin/scan_sensitive.py 是第二套實作，同一個洞不能只補一邊。"""
        lines = [
            f"GOOGLE_API_KEY={L1_SAMPLES['google-api-key']}  # <see docs>",
            f"export OPENAI_API_KEY={L1_SAMPLES['openai-style-key']}  # example value",
        ]
        write(self.root / "notes.md", "\n".join(lines) + "\n")
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "bin" / "scan_sensitive.py"), str(self.root)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("google-api-key", result.stdout)


class TestLayerTwo(ScannerTestCase):
    def test_blocklist_hit_exits_two(self) -> None:
        _, env = self.make_blocklist()
        write(
            self.root / "notes.md",
            "這份筆記提到 Peregrine Thistlewood 與 wobblegoose.test。\n",
        )
        result = run_check(str(self.root), env=env)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("identifier[", result.stdout)
        self.assertNotIn("Peregrine", result.stdout)
        self.assertNotIn("wobblegoose", result.stdout)
        self.assertIn("key loaded", result.stdout)

    def test_multiword_identifier_is_caught_with_spaces(self) -> None:
        """兩個字的人名／公司名寫成有空白，也必須擋下來。"""
        _, env = self.make_blocklist()
        write(self.root / "notes.md", "感謝 Flibbertigibbet Works 提供場地。\n")
        result = run_check(str(self.root), env=env)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("identifier[", result.stdout)

    def test_generic_word_from_multiword_token_is_not_flagged(self) -> None:
        """清單裡的多詞 token 不可以被拆成通用單字，否則正常英文散文會誤報。"""
        _, env = self.make_blocklist()
        write(self.root / "prose.md", "This glossary explains how the works section is written.\n")
        result = run_check(str(self.root), env=env)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_cjk_ngram_hit(self) -> None:
        _, env = self.make_blocklist()
        write(self.root / "cjk.md", "這段文字裡面藏了紫色河馬這個內部代號。\n")
        result = run_check(str(self.root), env=env)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertTrue(summary(result.stdout).startswith("L1 0 / L2 "))

    def test_reveal_prints_plaintext_only_on_demand(self) -> None:
        _, env = self.make_blocklist()
        write(self.root / "notes.md", "owner: marzipanuser\n")
        quiet = run_check(str(self.root), env=env)
        self.assertNotIn("marzipanuser", quiet.stdout)
        loud = run_check(str(self.root), "--reveal", env=env)
        self.assertIn("marzipanuser", loud.stdout)

    def test_missing_key_is_fail_closed(self) -> None:
        self.make_blocklist()
        write(self.root / "notes.md", "一切正常\n")
        result = run_check(str(self.root))  # 不給 key
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn("CONFIG ERROR", result.stderr)

    def test_absent_blocklist_warns_and_skips(self) -> None:
        write(self.root / "notes.md", "一切正常\n")
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 0)
        self.assertIn("blocklist-absent-l2-skipped", result.stdout)

    def test_no_blocklist_flag_skips_layer(self) -> None:
        _, env = self.make_blocklist()
        write(self.root / "notes.md", "提到 Peregrine Thistlewood。\n")
        result = run_check(str(self.root), "--no-blocklist", env=env)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("--no-blocklist", result.stdout)

    def test_builder_rejects_missing_required_category(self) -> None:
        tokens_file = self.tmp / "partial.txt"
        tokens_file.write_text("person\tPeregrine Thistlewood\n", encoding="utf-8")
        key_file = self.tmp / "hmac.key"
        key_file.write_text(FAKE_KEY + "\n", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(BUILD_BLOCKLIST),
                "--tokens",
                str(tokens_file),
                "--key-file",
                str(key_file),
                "--out",
                str(self.tmp / "out.hmac"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.tmp / "out.hmac").exists())

    def test_builder_skips_short_tokens(self) -> None:
        tokens_file = self.tmp / "short.txt"
        tokens_file.write_text(
            "".join(f"{category}\t{token}\n" for category, token in FAKE_TOKENS) + "person\tabc\n",
            encoding="utf-8",
        )
        key_file = self.tmp / "hmac.key"
        key_file.write_text(FAKE_KEY + "\n", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(BUILD_BLOCKLIST),
                "--tokens",
                str(tokens_file),
                "--key-file",
                str(key_file),
                "--out",
                str(self.tmp / "out.hmac"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("低於門檻略過 1 個", result.stdout)

    def test_path_shaped_token_is_caught_despite_leading_symbol(self) -> None:
        """掃描器的候選一定從英數字開始；頭尾帶符號的 token 必須靠補收才擋得住。"""
        tokens = FAKE_TOKENS + [("home_fragment", "/marzipanhollow/quill")]
        blocklist, env = self.make_blocklist(tokens)
        self.assertTrue(blocklist.is_file())
        write(self.root / "notes.md", "備份放在 /marzipanhollow/quill/archive 裡。\n")
        result = run_check(str(self.root), env=env)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("identifier[", result.stdout)
        self.assertNotIn("marzipanhollow", result.stdout)

    def test_builder_rejects_token_the_scanner_can_never_produce(self) -> None:
        """收錄了卻永遠掃不到的 token 是死清單項目，必須在生成時就紅。"""
        tokens_file = self.tmp / "unreachable.txt"
        tokens_file.write_text(
            "".join(f"{category}\t{token}\n" for category, token in FAKE_TOKENS)
            + "person\tPeregrine|Thistlewood\n",
            encoding="utf-8",
        )
        key_file = self.tmp / "hmac.key"
        key_file.write_text(FAKE_KEY + "\n", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(BUILD_BLOCKLIST),
                "--tokens",
                str(tokens_file),
                "--key-file",
                str(key_file),
                "--out",
                str(self.tmp / "out.hmac"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertFalse((self.tmp / "out.hmac").exists())
        self.assertNotIn("Thistlewood", result.stderr)


class TestLayerThree(ScannerTestCase):
    def _scan_line(self, text: str, name: str = "notes.md"):
        write(self.root / name, text + "\n")
        return run_check(str(self.root))

    def test_shape_patterns(self) -> None:
        cases = {
            "absolute-home-path": HOME_PATH,
            "exported-project-id": EXPORTED_PROJECT,
            "email-address": REAL_EMAIL,
            "phone-number": PHONE,
            "uuid-v4": UUID_V4,
            "ipv4-address": IPV4,
            "session-id": SESSION_ID,
            "gcs-uri": GCS_URI,
            "internal-hostname": INTERNAL_HOST,
            "cloud-project-number": CLOUD_PROJECT,
            "deploy-env-flag": DEPLOY_FLAG,
        }
        for kind, sample in cases.items():
            with self.subTest(kind=kind):
                result = self._scan_line(sample)
                self.assertEqual(result.returncode, 2, f"{kind} 沒被抓到：{result.stdout}")
                self.assertIn(kind, result.stdout)

    def test_windows_home_path(self) -> None:
        result = self._scan_line(WINDOWS_PATH)
        self.assertEqual(result.returncode, 2)
        self.assertIn("absolute-home-path", result.stdout)

    def test_allowed_shapes_are_quiet(self) -> None:
        lines = [
            "寄到 someone@example.com 或 bot@users.noreply.github.com 都可以",
            "本機測試用 127.0.0.1 與 0.0.0.0",
            "家目錄寫成 /home/you/my-vault 這種佔位就不算命中",
        ]
        result = self._scan_line("\n".join(lines))
        self.assertEqual(summary(result.stdout), "L1 0 / L2 0 / L3 0", result.stdout)
        self.assertEqual(result.returncode, 0)

    def test_symlink_is_rejected(self) -> None:
        target = write(self.root / "real.md", "# 真的檔案\n")
        os.symlink(target, self.root / "link.md")
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("symlink", result.stdout)

    def test_env_file_is_rejected_but_example_is_fine(self) -> None:
        write(self.root / ".env", "MODE=live\n")
        write(self.root / ".env.example", "MODE=<your-mode>\n")
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("live-env-file", result.stdout)
        self.assertNotIn(".env.example", result.stdout)

    def test_binary_and_oversized_files_are_rejected(self) -> None:
        (self.root / "blob.bin").write_bytes(b"\x00\x01\x02binary")
        (self.root / "huge.md").write_text("x" * (201 * 1024), encoding="utf-8")
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("binary-file", result.stdout)
        self.assertIn("oversized-file", result.stdout)

    def test_mustache_outside_template_is_rejected(self) -> None:
        write(self.root / "template" / "README.md", f"# {MUSTACHE} 的記憶庫\n")
        write(self.root / "docs" / "quickstart.md", f"# {MUSTACHE} 的記憶庫\n")
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("docs/quickstart.md", result.stdout)
        self.assertIn("placeholder-outside-template", result.stdout)
        self.assertNotIn("template/README.md", result.stdout)

    def test_github_actions_expression_is_allowed(self) -> None:
        body = "      env:\n        KEY: $" + MUSTACHE.replace("{OWNER}", "{ secrets.SOME_KEY }") + "\n"
        write(self.root / ".github" / "workflows" / "gate.yml", body)
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_frontmatter_absolute_source_is_rejected(self) -> None:
        body = "---\ntitle: 範例\nsource: " + HOME_PATH + "\n---\n\n內文\n"
        write(self.root / "card.md", body)
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("frontmatter-absolute-source", result.stdout)

    def test_third_party_license_must_exist(self) -> None:
        write(self.root / "skills" / "writing-great-skills" / "SKILL.md", "# 借來的 skill\n")
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("third-party-license-missing", result.stdout)
        # 上游全文逐 byte 搬過來才算數（見 UPSTREAM_LICENSE_SHA256）。
        upstream = (REPO_ROOT / "skills" / "writing-great-skills" / "LICENSE").read_bytes()
        (self.root / "skills" / "writing-great-skills" / "LICENSE").write_bytes(upstream)
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_third_party_license_must_match_upstream_byte_for_byte(self) -> None:
        """只檢查「有沒有作者名字」擋不住改年份、重打條文、截掉免責段。"""
        write(self.root / "skills" / "writing-great-skills" / "SKILL.md", "# 借來的 skill\n")
        upstream = (REPO_ROOT / "skills" / "writing-great-skills" / "LICENSE").read_text(
            encoding="utf-8")
        tampered = upstream.replace("2026", "2025", 1)
        self.assertNotEqual(tampered, upstream)
        write(self.root / "skills" / "writing-great-skills" / "LICENSE", tampered)
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("third-party-license-modified", result.stdout)

    def test_derived_skill_named_in_notices_must_carry_its_own_notice(self) -> None:
        """安裝器一次只複製一個 skill 資料夾，所以 notice 必須跟著資料夾走。"""
        write(self.root / "skills" / "borrowed-skill" / "SKILL.md", "# 衍生作品\n")
        write(self.root / "THIRD-PARTY-NOTICES.md",
              "# 第三方授權聲明\n\n| 檔案 | 狀態 |\n|---|---|\n"
              "| `skills/borrowed-skill/SKILL.md` | 衍生作品 |\n")
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("third-party-notice-missing", result.stdout)

        # 有檔但沒有版權與授權條文，一樣不算數。
        write(self.root / "skills" / "borrowed-skill" / "NOTICE.md", "這是衍生作品。\n")
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("third-party-notice-incomplete", result.stdout)

        upstream = (REPO_ROOT / "skills" / "writing-great-skills" / "LICENSE").read_text(
            encoding="utf-8")
        write(self.root / "skills" / "borrowed-skill" / "NOTICE.md",
              "# NOTICE\n\n衍生作品；上游授權全文：\n\n```\n" + upstream + "```\n")
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout)


class TestLinks(ScannerTestCase):
    def test_broken_wikilink_in_vault_is_caught(self) -> None:
        write(self.root / "template" / "03-wiki" / "index.md", "回 [[log]] 與 [[missing-page]]\n")
        write(self.root / "template" / "03-wiki" / "log.md", "# log\n")
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("broken-wikilink", result.stdout)
        self.assertEqual(result.stdout.count("broken-wikilink"), 1)

    def test_broken_relative_link_is_caught(self) -> None:
        write(self.root / "docs" / "gates.md", "見 [守門](./missing.md) 與 [這份](./here.md)\n")
        write(self.root / "docs" / "here.md", "# 在\n")
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("broken-link", result.stdout)
        self.assertEqual(result.stdout.count("broken-link"), 1)

    def test_links_in_code_fences_are_ignored(self) -> None:
        body = "```\n見 [示範](./not-real.md) 與 [[not-real]]\n```\n"
        write(self.root / "docs" / "faq.md", body)
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_external_urls_are_ignored(self) -> None:
        write(self.root / "README.md", "見 [上游](https://example.com/a) 與 [錨點](#section)\n")
        result = run_check(str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout)


class TestStreamModes(ScannerTestCase):
    def test_stdin_rejects_non_noreply_author(self) -> None:
        stream = f"commit 1234\nAuthor: Alice <{REAL_EMAIL}>\n+ 一行改動\n"
        result = run_check(str(self.root), "--stdin", stdin=stream)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("email-address", result.stdout)

    def test_stdin_accepts_noreply_author(self) -> None:
        stream = (
            "commit 1234\n"
            "Author: handle <1234567+handle@users.noreply.github.com>\n"
            "+ 一行改動\n"
        )
        result = run_check(str(self.root), "--stdin", stdin=stream)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(summary(result.stdout), "L1 0 / L2 0 / L3 0")

    def test_stdin_catches_secret_in_history(self) -> None:
        stream = "+" + L1_SAMPLES["github-token"] + "\n"
        result = run_check(str(self.root), "--stdin", stdin=stream)
        self.assertEqual(result.returncode, 2)
        self.assertIn("github-token", result.stdout)

    def test_stdin_is_fail_closed_without_key(self) -> None:
        self.make_blocklist()  # .hmac 在，key 不在 → 不准靜默跳過 L2
        result = run_check(str(self.root), "--stdin", stdin="+ 一行改動\n")
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)

    def test_remotes_mode_uses_blocklist(self) -> None:
        blocklist, env = self.make_blocklist()
        stream = cat("origin\tgit@", "github.test:handle/clandestine-abacus.git (fetch)\n")
        result = run_check(
            "--remotes",
            env={**env, "IDENTIFIER_BLOCKLIST_FILE": str(blocklist)},
            stdin=stream,
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("identifier[", result.stdout)

    def test_remotes_mode_passes_for_public_origin(self) -> None:
        blocklist, env = self.make_blocklist()
        stream = "origin\thttps://github.test/handle/agent-memory-vault.git (push)\n"
        result = run_check(
            "--remotes",
            env={**env, "IDENTIFIER_BLOCKLIST_FILE": str(blocklist)},
            stdin=stream,
        )
        self.assertEqual(result.returncode, 0, result.stdout)


@unittest.skipIf(shutil.which("git") is None, "需要 git")
class TestStagedMode(ScannerTestCase):
    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    def setUp(self) -> None:
        super().setUp()
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "test")

    def test_staged_secret_is_caught(self) -> None:
        write(self.root / "clean.md", "# 沒事\n")
        write(self.root / "leak.md", L1_SAMPLES["aws-access-key"] + "\n")
        self.git("add", "clean.md")
        result = run_check(str(self.root), "--staged")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.git("add", "leak.md")
        result = run_check(str(self.root), "--staged")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("aws-access-key", result.stdout)


if __name__ == "__main__":
    unittest.main()
