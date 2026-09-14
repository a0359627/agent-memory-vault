#!/usr/bin/env python3
"""Create a working memory vault from template/ and bin/.

唯一會寫入的地方是 <target>（以及 --with-sample 的 <target>-sample）。
不碰 ~/.claude、~/.codex、~/.agents，不下載任何東西，只用標準庫。
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import date

REPO_ROOT = Path(__file__).resolve().parents[1]

# 佔位符的左右括號分開拼，好讓 publish_check 的「佔位符只准在 template/」規則保持嚴格。
OPEN, CLOSE = '{' * 2, '}' * 2

# bin/ 內屬於 starter 發布流程、不進讀者 vault 的檔案。
BIN_EXCLUDE = {'identifier-blocklist.hmac', 'gate.sh'}
COPY_SKIP_NAMES = {'__pycache__', '.DS_Store', '.git'}

PLATFORMS = {
    # platform: (shared_source, shared_runtime, origin_id, extra_origins)
    'claude': ('~/.claude/skills', '~/.agents/skills', 'claude-skills', []),
    'codex': ('~/.agents/skills', '~/.codex/skills', 'agent-skills', []),
    'both': ('~/.claude/skills', '~/.agents/skills', 'claude-skills',
             [{'id': 'codex-skills', 'source': '~/.codex/skills'}]),
}

SECRETS_LOCAL_README = """# 99-secrets-local（本機明文清冊；永不進 git）

這個資料夾被 `.gitignore` 擋住，是唯一允許放明文憑證清冊的位置。

規則：

1. 只記「哪裡找得到」與「用途」，能不記值就不記值。
2. 真的要記值時，這裡是唯一位置；任何 wiki 頁、skill、commit 訊息都不准複製。
3. 換機時這個資料夾用離線方式搬，不靠 git，也不靠雲端同步。
4. 想連同 repo 一起搬，改用 `99-secrets-encrypted/`（age 密文），私鑰永遠單獨手搬。

建議表頭：

| 類型 | 位置 | Git 狀態 | 用途 |
|---|---|---|---|
"""


class BootstrapError(Exception):
    pass


def step(number: int, total: int, message: str) -> None:
    print(f'[{number}/{total}] {message}')


def is_text(data: bytes) -> bool:
    return b'\x00' not in data[:4096]


def iter_files(root: Path):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in COPY_SKIP_NAMES]
        for name in files:
            if name in COPY_SKIP_NAMES:
                continue
            yield Path(base) / name


def copy_tree(src: Path, dst: Path, exclude: set[str] | None = None) -> tuple[list[str], list[str]]:
    """Copy src into dst, never overwriting. Returns (written, skipped) relative paths."""
    exclude = exclude or set()
    written, skipped = [], []
    for path in sorted(iter_files(src)):
        relative = path.relative_to(src)
        if relative.parts[0] in exclude or path.name in exclude:
            continue
        target = dst / relative
        if target.exists() or target.is_symlink():
            skipped.append(relative.as_posix())
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)  # keeps the executable bit on *.sh
        written.append(relative.as_posix())
    # .gitkeep-only directories are covered above; empty dirs carry no meaning here.
    return written, skipped


def substitute(root: Path, values: dict[str, str]) -> int:
    changed = 0
    for path in iter_files(root):
        data = path.read_bytes()
        if not is_text(data):
            continue
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            continue
        new = text
        for key, value in values.items():
            new = new.replace(OPEN + key + CLOSE, value)
        if new != text:
            path.write_text(new, encoding='utf-8')
            changed += 1
    return changed


def leftover_placeholders(roots: list[Path]) -> list[str]:
    found = []
    for root in roots:
        if not root.exists():
            continue
        for path in iter_files(root):
            data = path.read_bytes()
            if not is_text(data):
                continue
            try:
                text = data.decode('utf-8')
            except UnicodeDecodeError:
                continue
            for number, line in enumerate(text.splitlines(), 1):
                if OPEN in line:
                    found.append(f'{path}:{number}')
    return found


def memory_project_id(target: Path) -> str:
    """Claude Code 的慣例：專案絕對路徑把 / 換成 -。"""
    return str(target.resolve()).replace('/', '-')


# 注意：`bin/skill-sources.json` 的 `primary_memory_project` 在骨架裡是 null，不是字面佔位符。
# 原始規格寫的是佔位符，但那個檔在 `bin/` 而不是 `template/`，而 publish_check 的 L3 規定
# 「雙大括號只准出現在 template/ 底下」——寫成字面佔位符會讓 gate 紅。值改由本函式依目標
# vault 的絕對路徑算出來填。下一個維護者請不要「照規格改回去」。
def write_registry(target: Path, platform: str) -> Path:
    registry_path = target / 'bin' / 'skill-sources.json'
    if not registry_path.is_file():
        raise BootstrapError(f'缺少來源清單骨架：{registry_path}')
    registry = json.loads(registry_path.read_text(encoding='utf-8'))
    source, runtime, origin_id, extra = PLATFORMS[platform]
    registry['shared_source'] = source
    registry['shared_runtime'] = runtime
    registry['origins'] = [{'id': origin_id, 'source': source}] + [dict(item) for item in extra]
    registry['primary_memory_project'] = memory_project_id(target)
    if registry.get('memory_source') is None:
        note = registry.get('notes', '').rstrip()
        extra_note = ('memory_source 為 null：primary_memory_project 已依本 vault 路徑填好，'
                      '但記憶快照尚未啟用；要啟用再把 memory_source 設成平台的專案記憶根目錄。')
        if extra_note not in note:
            registry['notes'] = (note + ' ' if note else '') + extra_note
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n',
                             encoding='utf-8')
    return registry_path


def write_log_entry(target: Path, today: str, vault_name: str) -> None:
    log = target / '03-wiki' / 'log.md'
    if not log.is_file():
        raise BootstrapError(f'缺少 ingest log 骨架：{log}')
    text = log.read_text(encoding='utf-8')
    heading = f'## [{today}] init | vault 建立'
    if heading in text:
        return
    entry = (f'{heading}\n'
             f'用 tools/bootstrap.py 建立 `{vault_name}`：三層（02-raw／03-wiki／01-profile）＋ PARA 目錄、'
             f'共用規則入口（AGENT-RULES.md）、來源清單（bin/skill-sources.json）、'
             f'gitignored 的 99-secrets-local/。尚未有任何來源與判準——第一筆 ingest 由你寫。\n')
    text = text.rstrip('\n') + '\n\n' + entry
    log.write_text(text, encoding='utf-8')


def write_secrets_local(target: Path) -> None:
    path = target / '99-secrets-local' / 'README.md'
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SECRETS_LOCAL_README, encoding='utf-8')


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=str(cwd), capture_output=True, text=True)


def git_available() -> bool:
    return shutil.which('git') is not None


def git_init_and_commit(target: Path, owner: str, vault_name: str) -> None:
    if not git_available():
        raise BootstrapError('找不到 git；請安裝 git 或改用 --no-git')
    if (target / '.git').exists():
        raise BootstrapError('目標已經是 git repo；請用 --no-git，或自己 commit')
    for command in (['git', 'init', '-q'],
                    ['git', 'symbolic-ref', 'HEAD', 'refs/heads/main'],
                    ['git', 'add', '-A']):
        result = run(command, target)
        if result.returncode != 0:
            raise BootstrapError(f'{" ".join(command)} 失敗：{result.stderr.strip()}')
    identity = []
    if not run(['git', 'config', 'user.email'], target).stdout.strip():
        identity = ['-c', f'user.name={owner}', '-c', 'user.email=vault@example.com']
        print('      note: git 沒有設定身分，本次 commit 用 vault@example.com；'
              '請之後用 git config 改成你自己的。')
    result = run(['git'] + identity + ['commit', '-q', '-m', f'init: {vault_name} 記憶庫建立'], target)
    if result.returncode != 0:
        raise BootstrapError(f'git commit 失敗：{(result.stderr or result.stdout).strip()}')


def commit_in_place(target: Path, vault_name: str) -> None:
    if not git_available() or not (target / '.git').is_dir():
        print('      note: 沒有 git repo，略過 commit')
        return
    run(['git', 'add', '-A'], target)
    if not run(['git', 'diff', '--cached', '--quiet'], target).returncode:
        print('      note: 沒有新檔案要 commit')
        return
    identity = []
    if not run(['git', 'config', 'user.email'], target).stdout.strip():
        identity = ['-c', 'user.name=vault owner', '-c', 'user.email=vault@example.com']
    result = run(['git'] + identity + ['commit', '-q', '-m', f'init: {vault_name} 記憶庫建立'], target)
    if result.returncode != 0:
        raise BootstrapError(f'git commit 失敗：{(result.stderr or result.stdout).strip()}')


def check_vault(target: Path) -> None:
    script = target / 'bin' / 'check_vault.py'
    if not script.is_file():
        raise BootstrapError(f'缺少 {script}')
    result = run([sys.executable, str(script), '--skip-snapshot'], target)
    sys.stdout.write(result.stdout)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise BootstrapError('check_vault.py --skip-snapshot 未通過')


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='用 template/ 與 bin/ 建立一個可用的記憶庫。',
        epilog='範例：python3 tools/bootstrap.py ~/my-vault --owner "你的稱呼" --with-sample')
    parser.add_argument('target', help='要建立 vault 的目錄；`.` 代表就地把這份 starter 變成 vault')
    parser.add_argument('--owner', default='vault 擁有者', help='佔位符 OWNER 的值')
    parser.add_argument('--lang', default='zh-TW', help='佔位符 LANG 的值')
    parser.add_argument('--vault-name', default=None, help='佔位符 VAULT_NAME；預設為目標目錄名')
    parser.add_argument('--with-sample', action='store_true',
                        help='另外把 examples/sample-vault/ 複製到 <target>-sample/')
    parser.add_argument('--no-git', action='store_true', help='不做 git init 與首個 commit')
    parser.add_argument('--force', action='store_true',
                        help='允許非空目錄：只補缺少的檔案，永遠不覆蓋、不刪除')
    parser.add_argument('--platform', choices=sorted(PLATFORMS), default='claude',
                        help='決定 bin/skill-sources.json 的 skill 來源與 runtime 路徑')
    return parser.parse_args(argv)


def bootstrap(args: argparse.Namespace) -> int:
    for required in ('template', 'bin'):
        if not (REPO_ROOT / required).is_dir():
            raise BootstrapError(f'starter 不完整：缺少 {REPO_ROOT / required}')

    in_place = args.target == '.' or Path(args.target).resolve() == REPO_ROOT
    target = REPO_ROOT if in_place else Path(args.target).expanduser().resolve()
    force = args.force or in_place
    existed = target.exists()

    if not in_place and REPO_ROOT in target.parents:
        raise BootstrapError('目標不能放在 starter repo 裡面；請選 repo 之外的目錄')
    if existed and not target.is_dir():
        raise BootstrapError(f'目標不是目錄：{target}')
    if existed and any(target.iterdir()) and not force:
        raise BootstrapError(f'目標非空：{target}（確定要補進既有目錄就加 --force；'
                             'force 只補缺、不覆蓋也不刪除）')

    vault_name = args.vault_name or target.name
    today = date.today().isoformat()
    sample_target = target.parent / f'{target.name}-sample'
    created_root = not existed
    created_sample = args.with_sample and not sample_target.exists()
    total = 9 if args.with_sample else 8

    try:
        target.mkdir(parents=True, exist_ok=True)
        if in_place:
            print(f'* in-place 模式：把 {target} 這份 starter 變成 vault；'
                  '同名的既有檔案一律保留不覆蓋。')

        step(1, total, f'複製 bin/ → {target / "bin"}（不含 {", ".join(sorted(BIN_EXCLUDE))}）')
        written, skipped = copy_tree(REPO_ROOT / 'bin', target / 'bin', exclude=BIN_EXCLUDE)
        print(f'      {len(written)} 個檔案；略過既有 {len(skipped)} 個')

        step(2, total, f'複製 template/ → {target}')
        written, skipped = copy_tree(REPO_ROOT / 'template', target)
        print(f'      {len(written)} 個檔案；略過既有 {len(skipped)} 個')
        if skipped:
            for name in skipped[:8]:
                print(f'      略過（已存在）：{name}')

        step(3, total, '替換佔位符')
        values = {'OWNER': args.owner, 'LANG': args.lang, 'VAULT_NAME': vault_name,
                  'TODAY': today, 'PRIMARY_MEMORY_PROJECT': memory_project_id(target)}
        print(f'      改寫 {substitute(target, values)} 個檔案')

        step(4, total, '確認沒有殘留的佔位符')
        leftover = leftover_placeholders([target])
        if leftover:
            for item in leftover[:10]:
                print(f'      殘留：{item}')
            raise BootstrapError('還有未替換的佔位符，停在這裡不留半成品')

        step(5, total, '寫入 bin/skill-sources.json')
        write_registry(target, args.platform)
        print(f'      platform={args.platform}；primary_memory_project={memory_project_id(target)}')

        step(6, total, '建立 99-secrets-local/README.md（被 .gitignore 擋住）與首則 log')
        write_secrets_local(target)
        write_log_entry(target, today, vault_name)

        step(7, total, 'git init 與第一個 commit' if not args.no_git else 'git（已用 --no-git 略過）')
        if args.no_git:
            print('      略過')
        elif in_place:
            commit_in_place(target, vault_name)
        else:
            git_init_and_commit(target, args.owner, vault_name)

        if args.with_sample:
            step(8, total, f'複製 examples/sample-vault/ → {sample_target}')
            source = REPO_ROOT / 'examples' / 'sample-vault'
            if not source.is_dir():
                raise BootstrapError(f'缺少 {source}')
            if sample_target.exists() and any(sample_target.iterdir()) and not force:
                raise BootstrapError(f'{sample_target} 非空；加 --force 只補缺')
            sample_target.mkdir(parents=True, exist_ok=True)
            written, skipped = copy_tree(source, sample_target)
            leftover = leftover_placeholders([sample_target])
            if leftover:
                raise BootstrapError(f'sample 有佔位符殘留：{leftover[0]}')
            print(f'      {len(written)} 個檔案；範例 vault 獨立於主 vault，也不做 git init')

        step(total, total, '跑 bin/check_vault.py --skip-snapshot')
        check_vault(target)
    except BaseException:
        if created_root and target.exists():
            shutil.rmtree(target, ignore_errors=True)
            print(f'已清掉半成品：{target}', file=sys.stderr)
        if created_sample and sample_target.exists():
            shutil.rmtree(sample_target, ignore_errors=True)
        raise

    print()
    print(f'完成：{target}')
    print('下一步：')
    print(f'  1. 讀 {target / "README.md"} 與 {target / "AGENT-RULES.md"}')
    print(f'  2. 填 {target / "01-profile" / "00-who.md"}')
    print(f'  3. 把第一份來源放進 {target / "02-raw"}，結論寫進 03-wiki/，並在 03-wiki/log.md 補一筆')
    if args.with_sample:
        print(f'  0. 想先看成品長什麼樣：{sample_target}')
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return bootstrap(args)
    except BootstrapError as exc:
        print(f'錯誤：{exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
