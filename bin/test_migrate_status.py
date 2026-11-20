#!/usr/bin/env python3
"""Fixture tests for the one-time status split. Everything runs in a temporary tree."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
TOOL = HERE / 'migrate_status.py'

PAGES = {
    'proj-live': '---\ntitle: live\ntype: project\nstatus: production\nupdated: 2026-01-10\n---\n\nbody stays\n\nstatus: production\n',
    'proj-moved': '---\ntype: project\nstatus: pilot\nsuperseded-by: proj-live\n---\nold\n',
    'review-q1': '---\ntype: review\nstatus: frozen\n---\nslice\n',
    'proj-frozen': '---\ntype: project\nstatus: frozen\n---\nstill described accurately\n',
    'skill-draft': '---\ntype: skill-card\nstatus: draft\n---\ncard\n',
    'skill-old': '---\ntype: skill-card\nstatus: deprecated\n---\ncard\n',
    'already': '---\ntype: reference\nstatus: current\n---\nfine\n',
    'split': '---\ntype: project\nstatus: stale\nsubject_status: production\n---\nfine\n',
    'template': '---\ntype: project\nstatus: <discovery | planning>\n---\nunfilled\n',
    'odd': '---\ntype: project\nstatus: experimental\n---\nx\n',
    'plain': '# no frontmatter\n\nstatus: production\n',
}


class MigrateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for folder in ('03-wiki', '01-profile', 'bin'):
            (self.root / folder).mkdir()
        (self.root / 'bin/status-vocab.json').write_text((HERE / 'status-vocab.json').read_text())
        for name, text in PAGES.items():
            self.page(name).write_text(text)

    def page(self, name):
        return self.root / '03-wiki' / f'{name}.md'

    def put(self, name, data):
        self.page(name).write_bytes(data if isinstance(data, bytes) else data.encode())

    def run_tool(self, *args):
        result = subprocess.run([sys.executable, str(TOOL), '--vault-root', str(self.root), *args],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def read(self, name):
        return self.page(name).read_text()

    def test_dry_run_is_the_default_and_writes_nothing(self):
        report = self.run_tool()
        self.assertTrue(report['mode'].startswith('dry-run'))
        self.assertEqual(report['pages_to_change'], 7)
        for name, text in PAGES.items():
            self.assertEqual(self.read(name), text, name)

    def test_dry_run_lists_every_change_including_the_key_rename(self):
        changes = self.run_tool()['changes_by_page']
        self.assertEqual(changes['proj-moved.md'], ['superseded-by -> superseded_by',
                                                    'status pilot -> superseded, subject_status pilot'])
        self.assertEqual(changes['proj-live.md'], ['status production -> current, subject_status production'])

    def test_apply_splits_the_axes_and_keeps_bodies(self):
        report = self.run_tool('--apply')
        self.assertEqual(report['mode'], 'apply')
        self.assertEqual(self.read('proj-live'),
                         '---\ntitle: live\ntype: project\nstatus: current\nsubject_status: production\n'
                         'updated: 2026-01-10\n---\n\nbody stays\n\nstatus: production\n')
        self.assertIn('status: superseded\nsubject_status: pilot\nsuperseded_by: proj-live', self.read('proj-moved'))
        self.assertIn('status: historical\nsubject_status: frozen', self.read('review-q1'))
        self.assertIn('status: current\nsubject_status: frozen', self.read('proj-frozen'))
        self.assertIn('status: watchlist\nsubject_status: draft', self.read('skill-draft'))
        self.assertIn('status: stale\nsubject_status: deprecated', self.read('skill-old'))
        for untouched in ('already', 'split', 'template', 'plain'):
            self.assertEqual(self.read(untouched), PAGES[untouched], untouched)

    def test_values_outside_the_vocabulary_are_moved_and_reported(self):
        report = self.run_tool('--apply')
        self.assertIn('status: current\nsubject_status: experimental', self.read('odd'))
        self.assertEqual(report['subject_values_not_in_vocabulary'], ['experimental'])

    def test_second_run_is_a_no_op(self):
        self.run_tool('--apply')
        after = {name: self.read(name) for name in PAGES}
        report = self.run_tool('--apply')
        self.assertEqual(report['pages_to_change'], 0)
        self.assertEqual({name: self.read(name) for name in PAGES}, after)

    def test_missing_vocabulary_is_a_configuration_error(self):
        (self.root / 'bin/status-vocab.json').unlink()
        result = subprocess.run([sys.executable, str(TOOL), '--vault-root', str(self.root)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 3)

    # --- regressions: inputs that used to change the body or get misread ------------------------

    def test_frontmatter_closed_with_dots_never_reaches_into_the_body(self):
        # The block ends at `...`; the `---` further down is a horizontal rule and what precedes it is body.
        text = '---\ntitle: a\n...\n\nstatus: draft\n\n---\n\ntext\n'
        self.put('dots', text)
        self.put('dots-with-status', '---\nstatus: pilot\n...\nbody line\n---\nmore\n')
        self.run_tool('--apply')
        self.assertEqual(self.read('dots'), text)
        self.assertEqual(self.read('dots-with-status'),
                         '---\nstatus: current\nsubject_status: pilot\n...\nbody line\n---\nmore\n')

    def test_line_endings_are_preserved_byte_for_byte(self):
        self.put('crlf', b'---\r\nstatus: production\r\n---\r\nbody\r\nline two\r\n')
        self.put('mixed', b'---\nstatus: production\n---\nline1\r\nline2\r\n')
        self.put('no-final-newline', b'---\nstatus: pilot\n---\nends without newline')
        self.run_tool('--apply')
        self.assertEqual(self.page('crlf').read_bytes(),
                         b'---\r\nstatus: current\r\nsubject_status: production\r\n---\r\nbody\r\nline two\r\n')
        self.assertEqual(self.page('mixed').read_bytes(),
                         b'---\nstatus: current\nsubject_status: production\n---\nline1\r\nline2\r\n')
        self.assertEqual(self.page('no-final-newline').read_bytes(),
                         b'---\nstatus: current\nsubject_status: pilot\n---\nends without newline')

    def test_quotes_and_inline_comments_are_read_as_yaml_would_read_them(self):
        quoted_lifecycle = '---\nstatus: "current"\n---\nx\n'
        commented_lifecycle = '---\nstatus: stale # reviewed in spring\n---\nx\n'
        self.put('quoted-lifecycle', quoted_lifecycle)
        self.put('commented-lifecycle', commented_lifecycle)
        self.put('quoted-old', '---\ntype: "skill-card"\nstatus: "draft"\n---\nx\n')
        self.put('commented-old', '---\nstatus: production # live since spring\n---\nx\n')
        self.put('quoted-link', '---\nstatus: pilot\nsuperseded_by: "[[proj-live]]"\n---\nx\n')
        self.run_tool('--apply')
        self.assertEqual(self.read('quoted-lifecycle'), quoted_lifecycle)
        self.assertEqual(self.read('commented-lifecycle'), commented_lifecycle)
        self.assertEqual(self.read('quoted-old'),
                         '---\ntype: "skill-card"\nstatus: watchlist\nsubject_status: "draft"\n---\nx\n')
        self.assertEqual(self.read('commented-old'),
                         '---\nstatus: current\nsubject_status: production # live since spring\n---\nx\n')
        self.assertIn('status: superseded\nsubject_status: pilot\n', self.read('quoted-link'))

    def test_nested_and_repeated_status_lines_are_left_alone(self):
        nested = '---\nname: n\nmetadata:\n  status: production\n---\nx\n'
        self.put('nested', nested)
        self.put('twice', '---\nstatus: pilot\nstatus: production\n---\nx\n')
        self.run_tool('--apply')
        self.assertEqual(self.read('nested'), nested)
        self.assertEqual(self.read('twice'), '---\nstatus: current\nsubject_status: pilot\nstatus: production\n---\nx\n')
        self.assertEqual(self.run_tool('--apply')['pages_to_change'], 0)

    def test_a_page_that_is_not_utf8_is_skipped_and_the_rest_still_migrate(self):
        self.put('latin', b'---\nstatus: production\n---\ncaf\xe9\n')
        before = self.page('latin').read_bytes()
        report = self.run_tool('--apply')
        self.assertEqual(report['skipped'], [{'file': 'latin.md', 'reason': 'not UTF-8'}])
        self.assertEqual(self.page('latin').read_bytes(), before)
        self.assertIn('subject_status: production', self.read('proj-live'))

    @unittest.skipUnless(hasattr(os, 'symlink'), 'needs symlinks')
    def test_a_symlinked_page_is_not_written_through(self):
        outside = self.root / 'outside.md'
        outside.write_text('---\nstatus: production\n---\nelsewhere\n')
        self.page('linked').symlink_to(outside)
        report = self.run_tool('--apply')
        self.assertIn({'file': 'linked.md', 'reason': 'symlink; not writing through it'}, report['skipped'])
        self.assertEqual(outside.read_text(), '---\nstatus: production\n---\nelsewhere\n')


if __name__ == '__main__':
    unittest.main()
