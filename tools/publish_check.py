#!/usr/bin/env python3
"""publish_check.py — 發布前三層掃描（零第三方依賴）。

三層各自獨立失敗，沒有任何一層可以被靜默跳過：

  L1  secret 樣式（金鑰、token、私鑰、賦值型密碼）
  L2  識別字封鎖（HMAC-SHA256 清單；明文清單與 key 都不在 repo）
  L3  結構與形狀（symlink、.env、二進位、絕對家目錄路徑、email、電話、
      UUID、IPv4、雲端與 session 殘留、佔位符位置、連結是否斷鏈、授權檔）

用法：
    publish_check.py <root> [選項]        # root 可以是目錄或單一檔案
    git log --all -p | publish_check.py --stdin
    git remote -v    | publish_check.py --remotes

離開碼：
    0  乾淨
    2  有發現（ERROR）
    3  設定錯誤（例如 .hmac 存在但拿不到 key → fail-closed）

錯誤訊息只給 `<LEVEL> <path>:<line> <kind>`，永不印命中值；
本機持有 key 時可用 --reveal 印出明文，方便自己修。
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

# --------------------------------------------------------------------------
# 常數
# --------------------------------------------------------------------------

BLOCKLIST_RELPATH = "bin/identifier-blocklist.hmac"
KEY_ENV = "IDENTIFIER_BLOCKLIST_KEY_FILE"
BLOCKLIST_ENV = "IDENTIFIER_BLOCKLIST_FILE"

MAX_FILE_BYTES = 200 * 1024
BINARY_SNIFF_BYTES = 8192

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    ".cache",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
}
SKIP_FILENAMES = {".DS_Store"}

# 目前沒有任何二進位檔／超大檔允許進 repo；要放行必須改這裡並說明理由。
BINARY_ALLOWLIST: set[str] = set()
LARGE_ALLOWLIST: set[str] = set()

PLACEHOLDER_TOKENS = ("example", "your-", "your_", "changeme", "change-me", "redacted")
PLACEHOLDER_BRACKETS = (re.compile(r"<[^<>\n]{0,64}>"), re.compile(r"\{\{[^}\n]{0,64}\}\}"))

ALLOWED_EMAIL_DOMAINS = ("example.com", "example.org", "users.noreply.github.com")
ALLOWED_IPS = {"127.0.0.1", "0.0.0.0"}
HOME_PATH_PLACEHOLDERS = {
    "you",
    "user",
    "users",
    "username",
    "youruser",
    "your-user",
    "your-name",
    "me",
    "someone",
    "example",
}

# --------------------------------------------------------------------------
# L1：secret 樣式
# --------------------------------------------------------------------------

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}")),
    ("openai-project-key", re.compile(r"\bsk-proj-[A-Za-z0-9_-]{20,}")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("openai-style-key", re.compile(r"\bsk-[A-Za-z0-9]{20,}")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google-oauth-secret", re.compile(r"\bGOCSPX-[A-Za-z0-9_-]{10,}")),
    ("age-secret-key", re.compile(r"\bAGE-SECRET-KEY-[0-9A-Z]{10,}")),
    ("private-key-block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "assigned-secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|client[_-]?secret)"
            r"\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{12,}"
        ),
    ),
]


def is_placeholder_match(line: str, match: re.Match[str]) -> bool:
    """佔位符白名單——只看**命中的那一段**，不是整行。

    早期版本是整行判定：同一行任何位置出現 `example`／`your-`／`<…>`，整行的 L1 就被跳過。
    那等於「在 key 旁邊寫一句註解」就能關掉這一行的掃描（`KEY=AIza…  # <see docs>`），
    而寫註解正是人在貼 key 時最常做的事。所以改成：命中片段自己含佔位符字樣，
    或命中片段整個被角括號／雙大括號包住，才算佔位符。
    """
    hit = match.group(0).lower()
    if any(token in hit for token in PLACEHOLDER_TOKENS):
        return True
    for pattern in PLACEHOLDER_BRACKETS:
        for bracket in pattern.finditer(line):
            if bracket.start() <= match.start() and match.end() <= bracket.end():
                return True
    return False


def scan_l1(line: str) -> list[str]:
    kinds = []
    for kind, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(line):
            if is_placeholder_match(line, match):
                continue
            kinds.append(kind)
            break
    return kinds


# --------------------------------------------------------------------------
# L2：識別字封鎖（HMAC）
# --------------------------------------------------------------------------

ASCII_RUN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._@+/-]*")
ASCII_SUBSEG = re.compile(r"[A-Za-z0-9]+")
CJK_RUN = re.compile(r"[\u3400-\u9fff]+")
# 路徑片段（家目錄那一類）在真實文字裡總是長路徑的一部分，所以 "/" 也要能當視窗連接符，
# 否則 home_fragment 這個必要類別只在「整條路徑剛好單獨成段」時才命中，等於形同虛設。
WINDOW_SEPARATORS = set("-_./")

ASCII_MIN_LEN = 6
CJK_MIN_LEN = 2
CJK_MAX_LEN = 6


def normalize_token(text: str) -> str:
    """NFKC → lowercase → 去除所有空白。清單產生器與掃描器必須一致。"""
    folded = unicodedata.normalize("NFKC", text).lower()
    return "".join(ch for ch in folded if not ch.isspace())


def iter_candidates(line: str):
    """吐出這一行所有待比對的候選字串（見 docs/gates.md 的規格）。

    (a) ASCII 連續段：整段、每個英數子段、以 - _ . / 相連的 2–4 個子段視窗；
    (b) 以空白相連的 2–4 個 ASCII 連續段（正規化會把空白去掉，
        所以「兩個字的人名／公司名」要靠這一種才擋得住）；
    (c) CJK 連續段的所有長度 2–6 n-gram。
    """
    runs = [(m.start(), m.end(), m.group(0)) for m in ASCII_RUN.finditer(line)]
    for index, (_, _, run) in enumerate(runs):
        yield run
        segments = [(m.start(), m.end()) for m in ASCII_SUBSEG.finditer(run)]
        for position, (start, end) in enumerate(segments):
            yield run[start:end]
            for size in (2, 3, 4):
                last = position + size - 1
                if last >= len(segments):
                    break
                window = run[start : segments[last][1]]
                gap = "".join(ch for ch in window if not ch.isalnum())
                if gap and set(gap) <= WINDOW_SEPARATORS:
                    yield window
        joined = run
        for following in range(index + 1, min(index + 4, len(runs))):
            between = line[runs[following - 1][1] : runs[following][0]]
            if not between or not between.isspace():
                break
            joined += runs[following][2]
            yield joined
    for match in CJK_RUN.finditer(line):
        run = match.group(0)
        for size in range(CJK_MIN_LEN, CJK_MAX_LEN + 1):
            for start in range(0, len(run) - size + 1):
                yield run[start : start + size]


class Blocklist:
    """bin/identifier-blocklist.hmac ＋ key → 可比對的封鎖集合。"""

    def __init__(self, digests: set[str], key: bytes) -> None:
        self.digests = digests
        self.key = key
        self._cache: dict[str, str | None] = {}

    def digest(self, token: str) -> str:
        return hmac.new(self.key, token.encode("utf-8"), hashlib.sha256).hexdigest()

    def match(self, candidate: str) -> str | None:
        """命中則回傳 hmac，否則 None。"""
        cached = self._cache.get(candidate)
        if cached is not None or candidate in self._cache:
            return cached
        normalized = normalize_token(candidate)
        result: str | None = None
        if normalized:
            has_cjk = CJK_RUN.search(normalized) is not None
            long_enough = len(normalized) >= (CJK_MIN_LEN if has_cjk else ASCII_MIN_LEN)
            if long_enough:
                digest = self.digest(normalized)
                if digest in self.digests:
                    result = digest
        self._cache[candidate] = result
        return result

    def scan_line(self, line: str) -> list[tuple[str, str]]:
        """回傳 (hmac, 命中的原文候選) 清單，同一行去重。"""
        hits: dict[str, str] = {}
        for candidate in iter_candidates(line):
            digest = self.match(candidate)
            if digest and digest not in hits:
                hits[digest] = candidate
        return list(hits.items())


class ConfigError(Exception):
    """設定錯誤 → exit 3。"""


def load_blocklist(path: Path) -> Blocklist:
    key_file = os.environ.get(KEY_ENV, "").strip()
    if not key_file:
        raise ConfigError(
            f"{path} 存在，但環境變數 {KEY_ENV} 未設定（fail-closed：不會靜默跳過 L2）"
        )
    key_path = Path(key_file).expanduser()
    try:
        raw = key_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"無法讀取 {KEY_ENV} 指向的檔案：{exc}") from exc
    key = raw.strip().encode("utf-8")
    if not key:
        raise ConfigError(f"{KEY_ENV} 指向的檔案是空的")
    digests: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        digests.add(stripped.lower())
    if not digests:
        raise ConfigError(f"{path} 沒有任何 HMAC 項目")
    return Blocklist(digests, key)


# --------------------------------------------------------------------------
# L3：結構與形狀
# --------------------------------------------------------------------------

# 注意：本檔自己也會被掃描，所以下列樣式刻意寫成「不會命中自己」的形式。
HOME_PATH_RE = re.compile(r"(?:/Users/|/home/)([A-Za-z0-9._-]+)")
WINDOWS_HOME_RE = re.compile(r"C:\\{1,2}Users\\{1,2}([A-Za-z0-9._-]+)")
EXPORTED_PROJECT_RE = re.compile(
    r"(?<![A-Za-z0-9])-(?:Users|home)-[A-Za-z0-9._]+-[A-Za-z0-9._-]+"
)
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
TW_MOBILE_RE = re.compile(r"(?<!\d)09\d{8}(?!\d)")
UUID4_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)
IPV4_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:\.\d{1,3}){3})(?![\w.])")
SESSION_ID_RE = re.compile(r"originSessionId\s*:")
GCS_URI_RE = re.compile(r"\bgs:/{2}[A-Za-z0-9._-]+")
INTERNAL_HOST_RE = re.compile(r"[A-Za-z0-9-]+[.]internal\b")
GCP_PROJECT_NUMBER_RE = re.compile(r"\bprojects/\d{4,}")
SET_ENV_VARS_RE = re.compile(r"--set-env[-]vars")
# 只抓「沒被替換掉的 bootstrap 佔位符」；GitHub Actions 的 ${…} 運算式不算
# （workflow 一定要用它，把它當違規只會逼人關掉這條規則）。
MUSTACHE_RE = re.compile(r"(?<!\$)\{\{")
FRONTMATTER_SOURCE_RE = re.compile(r"^source\s*:\s*['\"]?(~?/[^\s'\"]+)")

WIKILINK_RE = re.compile(r"\[\[([^\]\[|#]+)(?:#[^\]\[|]*)?(?:\|[^\]\[]*)?\]\]")
MDLINK_RE = re.compile(r"\]\(\s*<?([^)<>\s]+)>?(?:\s+\"[^\"]*\")?\s*\)")
URL_SCHEME_RE = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//|#)")


def ipv4_is_real(text: str) -> bool:
    parts = text.split(".")
    if len(parts) != 4:
        return False
    try:
        numbers = [int(part) for part in parts]
    except ValueError:
        return False
    if any(number > 255 for number in numbers):
        return False
    if any(len(part) > 1 and part.startswith("0") for part in parts):
        return False
    return text not in ALLOWED_IPS


def email_is_allowed(address: str) -> bool:
    domain = address.rsplit("@", 1)[-1].lower()
    return any(domain == allowed or domain.endswith("." + allowed) for allowed in ALLOWED_EMAIL_DOMAINS)


def scan_l3_line(line: str, relpath: str, in_template: bool) -> list[str]:
    kinds: list[str] = []
    for match in HOME_PATH_RE.finditer(line):
        if match.group(1).lower() not in HOME_PATH_PLACEHOLDERS:
            kinds.append("absolute-home-path")
            break
    for match in WINDOWS_HOME_RE.finditer(line):
        if match.group(1).lower() not in HOME_PATH_PLACEHOLDERS:
            kinds.append("absolute-home-path")
            break
    if EXPORTED_PROJECT_RE.search(line):
        kinds.append("exported-project-id")
    for match in EMAIL_RE.finditer(line):
        if not email_is_allowed(match.group(0)):
            kinds.append("email-address")
            break
    if TW_MOBILE_RE.search(line):
        kinds.append("phone-number")
    if UUID4_RE.search(line):
        kinds.append("uuid-v4")
    for match in IPV4_RE.finditer(line):
        if ipv4_is_real(match.group(1)):
            kinds.append("ipv4-address")
            break
    if SESSION_ID_RE.search(line):
        kinds.append("session-id")
    if GCS_URI_RE.search(line):
        kinds.append("gcs-uri")
    if INTERNAL_HOST_RE.search(line):
        kinds.append("internal-hostname")
    if GCP_PROJECT_NUMBER_RE.search(line):
        kinds.append("cloud-project-number")
    if SET_ENV_VARS_RE.search(line):
        kinds.append("deploy-env-flag")
    if not in_template and MUSTACHE_RE.search(line):
        kinds.append("placeholder-outside-template")
    return kinds


# --------------------------------------------------------------------------
# 發現與報告
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    layer: str  # L1 / L2 / L3
    level: str  # ERROR / WARN
    path: str
    line: int
    kind: str


@dataclass
class Document:
    """一份待掃描的內容（來自工作目錄、staged blob 或 stdin）。"""

    relpath: str
    text: str
    in_template: bool
    resolve_dir: Path | None  # 相對連結的解析基準
    vault_root: Path | None  # wikilink 的解析基準（None＝當相對路徑處理）


# --------------------------------------------------------------------------
# 檔案走訪
# --------------------------------------------------------------------------


def is_binary(data: bytes) -> bool:
    return b"\x00" in data[:BINARY_SNIFF_BYTES]


def iter_files(root: Path):
    """走訪整棵樹；不跟隨 symlink（symlink 本身會被回報為 L3 錯誤）。"""
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        here = Path(current)
        dirnames[:] = sorted(name for name in dirnames if name not in SKIP_DIRS)
        for name in list(dirnames):
            path = here / name
            if path.is_symlink():
                dirnames.remove(name)
                yield path
        for name in sorted(filenames):
            if name in SKIP_FILENAMES:
                continue
            yield here / name


def area_of(relpath: str) -> str:
    parts = Path(relpath).parts
    if parts and parts[0] == "template":
        return "template"
    if len(parts) >= 2 and parts[0] == "examples" and parts[1] == "sample-vault":
        return "sample-vault"
    return "repo"


def vault_root_for(root: Path, relpath: str) -> Path | None:
    area = area_of(relpath)
    if area == "template":
        return root / "template"
    if area == "sample-vault":
        return root / "examples" / "sample-vault"
    return None


# --------------------------------------------------------------------------
# 連結檢查
# --------------------------------------------------------------------------


def strip_fenced_blocks(text: str) -> list[tuple[int, str]]:
    """回傳 (行號, 內容)，圍欄程式碼區塊內的行以空字串代替（不檢查連結）。"""
    output: list[tuple[int, str]] = []
    fence: str | None = None
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if fence is None and (stripped.startswith("```") or stripped.startswith("~~~")):
            fence = stripped[:3]
            output.append((number, ""))
            continue
        if fence is not None:
            if stripped.startswith(fence):
                fence = None
            output.append((number, ""))
            continue
        output.append((number, line))
    return output


def wikilink_exists(vault_root: Path, target: str) -> bool:
    target = target.strip()
    if not target:
        return False
    candidate = vault_root / target
    if candidate.exists() or candidate.with_suffix(".md").exists():
        return True
    stem = Path(target).stem.lower()
    for path in vault_root.rglob("*.md"):
        if path.stem.lower() == stem:
            return True
    return False


def relative_link_exists(base: Path, target: str) -> bool:
    cleaned = unquote(target.split("#", 1)[0].strip())
    if not cleaned:
        return True
    try:
        candidate = (base / cleaned).resolve()
    except (OSError, ValueError):
        return False
    if candidate.exists():
        return True
    return candidate.with_suffix(".md").exists()


def check_links(document: Document) -> list[Finding]:
    if not document.relpath.lower().endswith(".md"):
        return []
    findings: list[Finding] = []
    for number, line in strip_fenced_blocks(document.text):
        if not line:
            continue
        for match in WIKILINK_RE.finditer(line):
            target = match.group(1)
            if document.vault_root is not None:
                ok = wikilink_exists(document.vault_root, target)
            elif document.resolve_dir is not None:
                ok = relative_link_exists(document.resolve_dir, target)
            else:
                ok = True
            if not ok:
                findings.append(Finding("L3", "ERROR", document.relpath, number, "broken-wikilink"))
        for match in MDLINK_RE.finditer(line):
            target = match.group(1)
            if URL_SCHEME_RE.match(target) or target.startswith("/"):
                continue
            if document.resolve_dir is None:
                continue
            if not relative_link_exists(document.resolve_dir, target):
                findings.append(Finding("L3", "ERROR", document.relpath, number, "broken-link"))
    return findings


def check_frontmatter_source(document: Document) -> list[Finding]:
    if not document.relpath.lower().endswith(".md"):
        return []
    lines = document.text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    findings: list[Finding] = []
    for number, line in enumerate(lines[1:], 2):
        if line.strip() == "---":
            break
        if FRONTMATTER_SOURCE_RE.match(line.strip()):
            findings.append(
                Finding("L3", "ERROR", document.relpath, number, "frontmatter-absolute-source")
            )
    return findings


# --------------------------------------------------------------------------
# 掃描主體
# --------------------------------------------------------------------------


def scan_document(document: Document, blocklist: Blocklist | None, reveal: bool) -> list[Finding]:
    findings: list[Finding] = []
    for number, line in enumerate(document.text.splitlines(), 1):
        for kind in scan_l1(line):
            findings.append(Finding("L1", "ERROR", document.relpath, number, kind))
        if blocklist is not None:
            for digest, plaintext in blocklist.scan_line(line):
                label = f"identifier[{plaintext}]" if reveal else f"identifier[{digest[:8]}]"
                findings.append(Finding("L2", "ERROR", document.relpath, number, label))
        for kind in scan_l3_line(line, document.relpath, document.in_template):
            findings.append(Finding("L3", "ERROR", document.relpath, number, kind))
    findings.extend(check_frontmatter_source(document))
    findings.extend(check_links(document))
    return findings


# 上游 MIT 全文的 sha256，於 2026-09-14 對 pinned commit
# （`THIRD-PARTY-NOTICES.md` 記的那一個）逐 byte 取回後計算。
# 只檢查「有沒有 Matt Pocock 這幾個字」是擋不住的：年份被改、條文被重打、
# 免責段落被截掉，字串檢查全都看不到——而 MIT 的義務正是「保留版權聲明與授權條文」。
UPSTREAM_LICENSE_SHA256 = "0e7ac423bf2c6e223b7c5b156f8cf72da49d748e56a1641402c31f22ad07dbb5"


# 一支 skill 的散布單位是**它自己的資料夾**：`tools/install_skills.py` 用 copytree
# 一次只複製一個目錄，所以「見本 repo 根目錄的 THIRD-PARTY-NOTICES.md」這種註腳在
# 安裝目的地根本不存在。MIT 要求版權與授權條文隨每一份副本走，因此逐項對照表裡點名的
# 每個 skill 目錄都必須自帶一份可獨立散布的 notice。
THIRD_PARTY_NOTICES = "THIRD-PARTY-NOTICES.md"
NOTICE_FILENAMES = ("LICENSE", "LICENSE.md", "NOTICE.md")
NOTICED_SKILL_RE = re.compile(r"skills/([a-z0-9][a-z0-9-]*)/")


def _pinned_license_findings(root: Path) -> list[Finding]:
    skill_dir = root / "skills" / "writing-great-skills"
    if not skill_dir.is_dir():
        return []
    license_path = skill_dir / "LICENSE"
    relpath = "skills/writing-great-skills/LICENSE"
    if not license_path.is_file():
        return [Finding("L3", "ERROR", relpath, 0, "third-party-license-missing")]
    raw = license_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != UPSTREAM_LICENSE_SHA256:
        return [Finding("L3", "ERROR", relpath, 0, "third-party-license-modified")]
    if "Matt Pocock" not in raw.decode("utf-8", errors="replace"):
        return [Finding("L3", "ERROR", relpath, 0, "third-party-license-attribution-missing")]
    return []


def _redistributable_notice_findings(root: Path) -> list[Finding]:
    notices = root / THIRD_PARTY_NOTICES
    if not notices.is_file() or not (root / "skills").is_dir():
        return []
    text = notices.read_text(encoding="utf-8", errors="replace")
    findings: list[Finding] = []
    for name in sorted({match.group(1) for match in NOTICED_SKILL_RE.finditer(text)}):
        skill_dir = root / "skills" / name
        if not skill_dir.is_dir():
            continue
        for filename in NOTICE_FILENAMES:
            candidate = skill_dir / filename
            if not candidate.is_file():
                continue
            body = candidate.read_text(encoding="utf-8", errors="replace")
            if "Copyright (c)" not in body or "MIT License" not in body:
                findings.append(Finding("L3", "ERROR", f"skills/{name}/{filename}", 0,
                                        "third-party-notice-incomplete"))
            break
        else:
            findings.append(Finding("L3", "ERROR", f"skills/{name}", 0,
                                    "third-party-notice-missing"))
    return findings


def license_findings(root: Path) -> list[Finding]:
    return _pinned_license_findings(root) + _redistributable_notice_findings(root)


def scan_tree(root: Path, blocklist: Blocklist | None, reveal: bool) -> list[Finding]:
    findings: list[Finding] = []
    if root.is_file():
        paths = [root]
        base = root.parent
    else:
        paths = list(iter_files(root))
        base = root
    for path in paths:
        relpath = path.name if root.is_file() else str(path.relative_to(root))
        if path.is_symlink():
            findings.append(Finding("L3", "ERROR", relpath, 0, "symlink"))
            continue
        name = path.name
        if name.startswith(".env") and name != ".env.example":
            findings.append(Finding("L3", "ERROR", relpath, 0, "live-env-file"))
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > MAX_FILE_BYTES and relpath not in LARGE_ALLOWLIST:
            findings.append(Finding("L3", "ERROR", relpath, 0, "oversized-file"))
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if is_binary(data):
            if relpath not in BINARY_ALLOWLIST:
                findings.append(Finding("L3", "ERROR", relpath, 0, "binary-file"))
            continue
        document = Document(
            relpath=relpath,
            text=data.decode("utf-8", errors="replace"),
            in_template=area_of(relpath) == "template",
            resolve_dir=path.parent,
            vault_root=None if root.is_file() else vault_root_for(base, relpath),
        )
        findings.extend(scan_document(document, blocklist, reveal))
    if root.is_dir():
        findings.extend(license_findings(root))
    return findings


def git_output(root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ConfigError(f"git {' '.join(args)} 失敗：{result.stderr.strip()}")
    return result.stdout


def scan_staged(root: Path, blocklist: Blocklist | None, reveal: bool) -> list[Finding]:
    names = git_output(root, ["diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"])
    paths = [name for name in names.split("\0") if name]
    findings: list[Finding] = []
    for relpath in paths:
        entry = git_output(root, ["ls-files", "-s", "--", relpath]).strip()
        if entry.startswith("120000"):
            findings.append(Finding("L3", "ERROR", relpath, 0, "symlink"))
            continue
        name = Path(relpath).name
        if name.startswith(".env") and name != ".env.example":
            findings.append(Finding("L3", "ERROR", relpath, 0, "live-env-file"))
            continue
        blob = subprocess.run(
            ["git", "-C", str(root), "show", f":{relpath}"],
            capture_output=True,
            check=False,
        )
        if blob.returncode != 0:
            continue
        data = blob.stdout
        if len(data) > MAX_FILE_BYTES and relpath not in LARGE_ALLOWLIST:
            findings.append(Finding("L3", "ERROR", relpath, 0, "oversized-file"))
            continue
        if is_binary(data):
            if relpath not in BINARY_ALLOWLIST:
                findings.append(Finding("L3", "ERROR", relpath, 0, "binary-file"))
            continue
        document = Document(
            relpath=relpath,
            text=data.decode("utf-8", errors="replace"),
            in_template=area_of(relpath) == "template",
            resolve_dir=(root / relpath).parent,
            vault_root=vault_root_for(root, relpath),
        )
        findings.extend(scan_document(document, blocklist, reveal))
    return findings


def scan_stdin(blocklist: Blocklist | None, reveal: bool) -> list[Finding]:
    """git log --all -p 串流：L1＋L2＋email（含 commit 作者行）。"""
    findings: list[Finding] = []
    for number, raw in enumerate(sys.stdin.buffer.read().decode("utf-8", errors="replace").splitlines(), 1):
        for kind in scan_l1(raw):
            findings.append(Finding("L1", "ERROR", "<stdin>", number, kind))
        if blocklist is not None:
            for digest, plaintext in blocklist.scan_line(raw):
                label = f"identifier[{plaintext}]" if reveal else f"identifier[{digest[:8]}]"
                findings.append(Finding("L2", "ERROR", "<stdin>", number, label))
        for match in EMAIL_RE.finditer(raw):
            if not email_is_allowed(match.group(0)):
                findings.append(Finding("L3", "ERROR", "<stdin>", number, "email-address"))
                break
    return findings


def scan_remotes(blocklist: Blocklist | None, reveal: bool) -> list[Finding]:
    findings: list[Finding] = []
    for number, raw in enumerate(sys.stdin.read().splitlines(), 1):
        if not raw.strip():
            continue
        if blocklist is None:
            continue
        for digest, plaintext in blocklist.scan_line(raw):
            label = f"identifier[{plaintext}]" if reveal else f"identifier[{digest[:8]}]"
            findings.append(Finding("L2", "ERROR", "<remote>", number, label))
    return findings


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def resolve_blocklist_path(root: Path, override: str | None) -> Path:
    if override:
        return Path(override).expanduser()
    env_value = os.environ.get(BLOCKLIST_ENV, "").strip()
    if env_value:
        return Path(env_value).expanduser()
    if root.is_dir():
        return root / BLOCKLIST_RELPATH
    # 掃描單一檔案（例如 gate --full 的 canary）時，以目前工作目錄的 repo 為準。
    return Path.cwd() / BLOCKLIST_RELPATH


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="publish_check.py",
        description="發布前三層掃描：L1 secret／L2 識別字 HMAC／L3 結構與形狀。",
    )
    parser.add_argument("root", nargs="?", default=".", help="要掃描的目錄或檔案（預設 .）")
    parser.add_argument("--staged", action="store_true", help="只掃 git 暫存區的檔案")
    parser.add_argument("--stdin", action="store_true", help="從 stdin 讀 git log -p 串流")
    parser.add_argument("--remotes", action="store_true", help="從 stdin 讀 git remote -v")
    parser.add_argument("--reveal", action="store_true", help="本機持有 key 時印出 L2 命中的明文")
    parser.add_argument("--no-blocklist", action="store_true", help="明確跳過 L2（fork PR 用）")
    parser.add_argument("--blocklist", default=None, help="指定 .hmac 路徑（預設 <root>/bin/…）")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    modes = sum(1 for flag in (args.staged, args.stdin, args.remotes) if flag)
    if modes > 1:
        print("CONFIG ERROR: --staged／--stdin／--remotes 一次只能用一個", file=sys.stderr)
        return 3

    root = Path(args.root).expanduser()
    if not args.stdin and not args.remotes and not root.exists():
        print(f"CONFIG ERROR: 找不到 {root}", file=sys.stderr)
        return 3
    root = root.resolve()

    notices: list[str] = []
    blocklist: Blocklist | None = None
    blocklist_path = resolve_blocklist_path(root, args.blocklist)
    if args.no_blocklist:
        notices.append("NOTICE L2 skipped (--no-blocklist)")
    elif blocklist_path.is_file():
        try:
            blocklist = load_blocklist(blocklist_path)
        except ConfigError as exc:
            print(f"CONFIG ERROR: {exc}", file=sys.stderr)
            return 3
        notices.append(f"NOTICE L2 key loaded ({len(blocklist.digests)} entries)")
    else:
        notices.append(f"WARN {BLOCKLIST_RELPATH}:0 blocklist-absent-l2-skipped")

    try:
        if args.stdin:
            findings = scan_stdin(blocklist, args.reveal)
        elif args.remotes:
            findings = scan_remotes(blocklist, args.reveal)
        elif args.staged:
            findings = scan_staged(root, blocklist, args.reveal)
        else:
            findings = scan_tree(root, blocklist, args.reveal)
    except ConfigError as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 3

    for notice in notices:
        print(notice)
    for finding in sorted(findings, key=lambda item: (item.path, item.line, item.layer, item.kind)):
        print(f"{finding.level} {finding.path}:{finding.line} {finding.kind}")

    counts = {"L1": 0, "L2": 0, "L3": 0}
    for finding in findings:
        if finding.level == "ERROR":
            counts[finding.layer] += 1
    print(f"L1 {counts['L1']} / L2 {counts['L2']} / L3 {counts['L3']}")
    return 2 if any(counts.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
