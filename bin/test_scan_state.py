#!/usr/bin/env python3
"""Exercise the generated status report in an isolated vault, without network."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest


def git_env():
    """Git must behave the same for everyone who runs this: no global config (signing, hooks, ignores)."""
    env = dict(os.environ)
    env.update({'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'})
    return env


def run_scan(root, *args):
    script = root / 'bin/scan-state.sh'
    script.parent.mkdir(exist_ok=True)
    shutil.copy2(Path(__file__).with_name('scan-state.sh'), script)
    subprocess.run(['bash', str(script), *args], check=True, capture_output=True, timeout=60, env=git_env())
    return (root / 'STATUS.md').read_text()


def table_rows(report):
    return {line.split('|')[1].strip(): line for line in report.splitlines()
            if line.startswith('| ') and len(line.split('|')) == 10}


class StatusAxesTest(unittest.TestCase):
    def test_subject_status_drives_the_activity_warning_and_lifecycle_is_shown_beside_it(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / '03-wiki').mkdir()
            source = root / 'old-source'
            source.mkdir()
            artifact = source / 'evidence.md'
            artifact.write_text('old evidence')
            old = time.time() - 45 * 86400
            os.utime(artifact, (old, old))
            # Files a running app keeps rewriting must not make an idle project look alive.
            (source / 'runtime.db-shm').write_text('recent runtime sidecar')
            (source / '.env').write_text('NOT_A_REAL_VALUE=fixture')
            for name, fields in {
                'live': 'status: current\nsubject_status: production',
                'slice': 'status: historical\nsubject_status: parked',
                'legacy': 'status: production',
                'frozen': 'status: current\nsubject_status: frozen',
            }.items():
                (root / f'03-wiki/proj-{name}.md').write_text(f'---\n{fields}\nsource: {source}\n---\n')
            (root / '03-wiki' / 'proj-research.md').write_text(
                '---\nstatus: current\nsubject_status: planning\nsource: 尚無 repo；筆記都在 vault 裡\n---\n')
            (root / '03-wiki' / 'proj-gone.md').write_text(
                f'---\nstatus: current\nsubject_status: pilot\nsource: {root / "no-such-dir"}\n---\n')
            rows = table_rows(run_scan(root))
            self.assertIn('| current | production |', rows['live'])
            self.assertIn('⚠️', rows['live'])
            self.assertIn('🟠 dormant', rows['live'])
            self.assertIn('| historical | parked |', rows['slice'])
            self.assertNotIn('⚠️', rows['slice'])
            # A 0.1.x card that still has one axis keeps working: its status is read as the project label,
            # and the lifecycle column says the card has not been split yet.
            self.assertIn('| 未拆軸 | production |', rows['legacy'])
            self.assertIn('⚠️', rows['legacy'])
            self.assertIn('frozen（人工定）', rows['frozen'])
            self.assertIn('未設本機 source', rows['research'])
            self.assertNotIn('路徑不存在', rows['research'])
            self.assertIn('路徑不存在', rows['gone'])

    def test_fetch_failure_is_partial_and_a_repo_without_origin_is_not_a_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / '03-wiki').mkdir()
            for name in ('originless', 'broken'):
                source = root / name
                subprocess.run(['git', 'init', '-q', str(source)], check=True, capture_output=True, env=git_env())
                subprocess.run(['git', '-C', str(source), '-c', 'user.name=Fixture',
                                '-c', 'user.email=fixture@example.com', '-c', 'commit.gpgsign=false', 'commit',
                                '-qm', 'fixture', '--allow-empty'], check=True, capture_output=True, env=git_env())
                (root / f'03-wiki/proj-{name}.md').write_text(
                    f'---\nstatus: current\nsubject_status: pilot\nsource: {source}\n---\n')
                if name == 'broken':
                    subprocess.run(['git', '-C', str(source), 'remote', 'add', 'origin',
                                    str(root / 'nonexistent-local-origin')], check=True, capture_output=True,
                                   env=git_env())
            report = run_scan(root, '--fetch')
            self.assertIn('remote_refs_refreshed: partial', report)
            failures = [line for line in report.splitlines() if 'fetch 失敗；' in line]
            self.assertEqual(len(failures), 1, failures)
            self.assertIn('| broken |', failures[0])

    def test_a_two_axis_card_without_a_project_state_does_not_borrow_its_lifecycle(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / '03-wiki').mkdir()
            source = root / 'src'
            source.mkdir()
            (source / 'a.md').write_text('x')
            (root / '03-wiki' / 'proj-plain.md').write_text(f'---\nstatus: current\nsource: {source}\n---\n')
            (root / '03-wiki' / 'proj-pipe.md').write_text(
                f'---\nstatus: current\nsubject_status: pilot | maybe\nsource: {source}\n---\n')
            rows = table_rows(run_scan(root))
            self.assertIn('| current | — |', rows['plain'])
            # A `|` inside a value must not add a column: the row still splits into the same number of cells.
            self.assertIn('| current | pilot ／ maybe |', rows['pipe'])
            self.assertEqual(set(rows), {'專案', 'plain', 'pipe'})   # header row plus one row per card

    def test_without_fetch_the_header_says_so(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / '03-wiki').mkdir()
            report = run_scan(root)
            self.assertIn('remote_refs_refreshed: false', report)
            self.assertIn('| 專案 | 記憶狀態 | 專案標籤 |', report)


if __name__ == '__main__':
    unittest.main()
