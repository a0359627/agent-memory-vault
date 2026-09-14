#!/usr/bin/env python3
"""tools/bootstrap.py 的隔離測試：全部在 tempfile 目錄跑，HOME 用假的。"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = REPO_ROOT / 'tools' / 'bootstrap.py'
OPEN = '{' * 2  # 同 bootstrap.py：不留字面佔位符


def snapshot_tree(root: Path) -> dict[str, tuple[int, int]]:
    """(相對路徑 → 大小與 mtime)；用來證明某棵樹完全沒被動過。"""
    result = {}
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            path = Path(base) / name
            info = path.lstat()
            result[str(path.relative_to(root))] = (info.st_size, info.st_mtime_ns)
        for name in sorted(dirs):
            result[str((Path(base) / name).relative_to(root)) + '/'] = (0, 0)
    return result


def text_files(root: Path):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__'}]
        for name in files:
            path = Path(base) / name
            data = path.read_bytes()
            if b'\x00' in data[:4096]:
                continue
            try:
                yield path, data.decode('utf-8')
            except UnicodeDecodeError:
                continue


class BootstrapTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue((REPO_ROOT / 'template').is_dir(), 'starter 缺少 template/')
        self.assertTrue((REPO_ROOT / 'bin').is_dir(), 'starter 缺少 bin/')
        self.tmp = tempfile.TemporaryDirectory(prefix='bootstrap-test-')
        self.base = Path(self.tmp.name)
        self.home = self.base / 'fake-home'
        self.home.mkdir()
        self.addCleanup(self.tmp.cleanup)

    def env(self) -> dict[str, str]:
        environment = dict(os.environ)
        environment['HOME'] = str(self.home)
        environment['GIT_CONFIG_NOSYSTEM'] = '1'
        environment.pop('XDG_CONFIG_HOME', None)
        return environment

    def run_bootstrap(self, target: Path, *extra: str) -> subprocess.CompletedProcess:
        command = [sys.executable, str(BOOTSTRAP), str(target),
                   '--owner', 'Sample Owner', '--vault-name', 'my-vault', *extra]
        return subprocess.run(command, capture_output=True, text=True,
                              cwd=str(self.base), env=self.env())

    def git(self, target: Path, *args: str) -> str:
        result = subprocess.run(['git', *args], cwd=str(target), capture_output=True,
                                text=True, env=self.env())
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    # --- 主路徑 -------------------------------------------------------------

    def test_fresh_vault_is_complete_and_committed(self):
        target = self.base / 'my-vault'
        result = self.run_bootstrap(target)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        # 佔位符全消
        leftovers = [f'{path}:{number}'
                     for path, text in text_files(target)
                     for number, line in enumerate(text.splitlines(), 1) if OPEN in line]
        self.assertEqual(leftovers, [])

        # 值真的被填進去
        registry = json.loads((target / 'bin' / 'skill-sources.json').read_text())
        self.assertEqual(registry['primary_memory_project'],
                         str(target.resolve()).replace('/', '-'))
        self.assertEqual(registry['shared_skills'], [])
        self.assertTrue((target / '99-secrets-local' / 'README.md').is_file())
        self.assertIn('init | vault 建立', (target / '03-wiki' / 'log.md').read_text())

        # 發布用的檔案不進讀者 vault
        self.assertFalse((target / 'bin' / 'identifier-blocklist.hmac').exists())
        self.assertFalse((target / 'bin' / 'gate.sh').exists())

        # 第一個綠燈：check_vault --skip-snapshot
        check = subprocess.run([sys.executable, str(target / 'bin' / 'check_vault.py'),
                                '--skip-snapshot'], cwd=str(target), capture_output=True,
                               text=True, env=self.env())
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

        # 恰一個 commit，且分支是 main
        self.assertEqual(self.git(target, 'rev-list', '--count', 'HEAD'), '1')
        self.assertEqual(self.git(target, 'rev-parse', '--abbrev-ref', 'HEAD'), 'main')
        self.assertEqual(self.git(target, 'status', '--porcelain'), '')

    def test_shell_scripts_keep_the_executable_bit(self):
        target = self.base / 'my-vault'
        self.assertEqual(self.run_bootstrap(target, '--no-git').returncode, 0)
        scripts = sorted(target.rglob('*.sh'))
        self.assertTrue(scripts, '沒有複製到任何 .sh')
        for script in scripts:
            self.assertTrue(os.access(script, os.X_OK), f'{script} 失去執行位')

    def test_with_sample_creates_sibling_sample_vault(self):
        target = self.base / 'my-vault'
        result = self.run_bootstrap(target, '--with-sample')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        sample = self.base / 'my-vault-sample'
        self.assertTrue(sample.is_dir())
        self.assertTrue(any(sample.rglob('*.md')))
        self.assertFalse((sample / '.git').exists(), 'sample 不該自己 git init')
        leftovers = [str(path) for path, text in text_files(sample) if OPEN in text]
        self.assertEqual(leftovers, [])

    def test_no_git_leaves_no_repository(self):
        target = self.base / 'my-vault'
        self.assertEqual(self.run_bootstrap(target, '--no-git').returncode, 0)
        self.assertFalse((target / '.git').exists())

    # --- 拒絕與不破壞 -------------------------------------------------------

    def test_refuses_non_empty_target(self):
        target = self.base / 'occupied'
        target.mkdir()
        (target / 'keep.md').write_text('已經有東西了\n')
        result = self.run_bootstrap(target)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sorted(p.name for p in target.iterdir()), ['keep.md'])
        self.assertEqual((target / 'keep.md').read_text(), '已經有東西了\n')

    def test_force_only_fills_gaps_and_never_overwrites(self):
        target = self.base / 'occupied'
        target.mkdir()
        (target / 'README.md').write_text('我自己寫的\n')
        result = self.run_bootstrap(target, '--force', '--no-git')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((target / 'README.md').read_text(), '我自己寫的\n')
        self.assertTrue((target / 'AGENT-RULES.md').is_file())

    def test_writes_nothing_outside_the_target(self):
        target = self.base / 'my-vault'
        (self.home / '.claude' / 'skills').mkdir(parents=True)
        (self.home / '.claude' / 'skills' / 'mine.md').write_text('不要碰我\n')
        (self.home / '.agents').mkdir()
        before = snapshot_tree(self.home)
        result = self.run_bootstrap(target, '--with-sample')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(snapshot_tree(self.home), before, 'bootstrap 動到了 HOME')


    def test_documented_codex_install_command_succeeds(self):
        """`skills/README.md` 裡那條「裝到 Codex 並登錄」的命令必須真的跑得過。

        `install_skills.py --register` 要求來源清單宣告的 `shared_source` 等於安裝
        目的地，而 `bootstrap.py` 的預設平台是 claude——所以文件若沒寫清楚前提，
        讀者照抄第一條命令就會撞牆。這支測試把那個前提釘死：codex 建的 vault ＋
        `--platform codex` 安裝，必須 exit 0。
        """
        target = self.base / 'codex-vault'
        result = self.run_bootstrap(target, '--platform', 'codex', '--no-git')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        registry = json.loads((target / 'bin' / 'skill-sources.json').read_text())
        self.assertEqual(registry['shared_source'], '~/.agents/skills')

        install = subprocess.run(
            [sys.executable, str(REPO_ROOT / 'tools' / 'install_skills.py'),
             'obsidian-vault', '--platform', 'codex', '--apply',
             '--register', str(target / 'bin' / 'skill-sources.json')],
            capture_output=True, text=True, cwd=str(self.base), env=self.env())
        self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
        self.assertTrue((self.home / '.agents' / 'skills' / 'obsidian-vault' / 'SKILL.md').is_file())
        registry = json.loads((target / 'bin' / 'skill-sources.json').read_text())
        self.assertIn('obsidian-vault', registry['shared_skills'])

    def test_running_repo_tools_leaves_no_bytecode(self):
        """跑完 repo 自己的工具，工作樹不能長出 `__pycache__`／`*.pyc`。

        `.pyc` 的 `co_filename` 內嵌編譯當時的來源絕對路徑（含使用者名稱），
        而 `bin/gate.sh` 有一步會把工作樹裡的 build 產物擋成紅燈。會 import
        兄弟模組的工具必須自己設 `sys.dont_write_bytecode`，不能靠呼叫端記得加
        環境變數——否則讀者照文件跑一次就把 gate 弄紅。
        """
        workspace = self.base / 'bytecode-probe'
        workspace.mkdir()
        for relative in ('tools/build_identifier_blocklist.py', 'tools/publish_check.py',
                         'bin/check_vault.py', 'bin/skill_sync.py'):
            destination = workspace / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((REPO_ROOT / relative).read_bytes())
        tokens = workspace / 'tokens.txt'
        tokens.write_text('\n'.join(f'{category}\tprobe-token-{index}' for index, category in
                                    enumerate(('person', 'company', 'domain', 'cloud',
                                               'home_fragment', 'private_repo'))) + '\n',
                          encoding='utf-8')
        key = workspace / 'probe.key'
        key.write_text('probe-key\n', encoding='utf-8')

        environment = self.env()
        # 刻意**不**設 PYTHONDONTWRITEBYTECODE：要測的正是工具自己有沒有關掉。
        environment.pop('PYTHONDONTWRITEBYTECODE', None)
        result = subprocess.run(
            [sys.executable, str(workspace / 'tools' / 'build_identifier_blocklist.py'),
             '--tokens', str(tokens), '--key-file', str(key),
             '--out', str(workspace / 'out.hmac')],
            capture_output=True, text=True, cwd=str(workspace), env=environment)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        leftovers = [str(path.relative_to(workspace)) for path in workspace.rglob('*')
                     if path.name == '__pycache__' or path.suffix == '.pyc']
        self.assertEqual(leftovers, [], f'工具留下了 build 產物：{leftovers}')


if __name__ == '__main__':
    unittest.main()
