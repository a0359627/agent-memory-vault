#!/usr/bin/env python3
"""Fixture tests for consolidate.py. Everything runs in a temporary tree."""
from datetime import date
import json
from pathlib import Path
import sys
import tempfile
import unittest

# A .pyc embeds the absolute path of whoever compiled it; see the note in check_vault.py.
sys.dont_write_bytecode = True

from consolidate import entries, injected_layer, merge_fragments, report, stale_questions  # noqa: E402

TODAY = date(2031, 11, 10)
LOG = '''# Ingest Log

## [2031-11-04] ingest | 順序不照日期的一則

body top

## [2031-03-01] init | vault 建立

body init

## [2031-11-04] update | 第一批

body a

## [2031-11-06] update | 第二批

body b

'''


def fragment(*sections):
    return '---\ntitle: frag\ntype: log-append\n---\n\n# log-append\n\n' + '\n\n'.join(sections) + '\n'


class MergeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / '03-wiki').mkdir()
        self.log = self.root / '03-wiki/log.md'
        self.log.write_text(LOG)

    def frag(self, name, *sections):
        path = self.root / '03-wiki' / name
        path.write_text(fragment(*sections))
        return path

    def headings(self):
        return [heading for _, heading, _ in entries(self.log.read_text())]

    def test_report_mode_writes_nothing(self):
        path = self.frag('log-append-2031-11-04.md', '## [2031-11-04] update | 另一個 session\n\n內容')
        plan = merge_fragments(self.root, today=TODAY)
        self.assertEqual(plan[0]['merged'], ['## [2031-11-04] update | 另一個 session'])
        self.assertEqual(self.log.read_text(), LOG)
        self.assertTrue(path.exists())

    def test_entry_lands_after_last_entry_not_newer_than_it(self):
        self.frag('log-append-2031-11-04.md', '## [2031-11-04] update | 另一個 session\n\n內容')
        merge_fragments(self.root, apply=True, today=TODAY)
        got = self.headings()
        self.assertEqual(got.index('## [2031-11-04] update | 另一個 session'),
                         got.index('## [2031-11-04] update | 第一批') + 1)
        self.assertEqual(got[-1], '## [2031-11-06] update | 第二批')

    def test_newest_entry_is_appended_and_body_and_origin_are_kept(self):
        path = self.frag('log-append-2031-11-09-x.md', '## [2031-11-09] ingest | 新的\n\n第一段\n\n第二段')
        merge_fragments(self.root, apply=True, today=TODAY)
        text = self.log.read_text()
        self.assertEqual(self.headings()[-1], '## [2031-11-09] ingest | 新的')
        self.assertIn('第一段\n\n第二段\n\n（原載碎片 `log-append-2031-11-09-x.md`，2031-11-10 原文併入。）', text)
        self.assertTrue(text.startswith(LOG.rstrip('\n')))
        self.assertFalse(path.exists())

    def test_entry_older_than_everything_goes_before_the_first_entry(self):
        self.frag('log-append-2031-01-01.md', '## [2031-01-01] ingest | 很舊\n\nx')
        merge_fragments(self.root, apply=True, today=TODAY)
        self.assertEqual(self.headings()[0], '## [2031-01-01] ingest | 很舊')
        self.assertTrue(self.log.read_text().startswith('# Ingest Log\n\n## [2031-01-01] ingest | 很舊\n'))

    def test_a_later_fragment_is_still_placed_by_date_after_an_old_one_went_in(self):
        self.log.write_text('# Log\n\n## [2031-01-05] ingest | A\n\nA\n\n## [2031-01-10] ingest | B\n\nB\n')
        (self.root / '03-wiki/log-append-1.md').write_text('## [2030-12-01] ingest | Old\n\no\n')
        (self.root / '03-wiki/log-append-2.md').write_text('## [2031-01-07] ingest | C\n\nc\n')
        merge_fragments(self.root, apply=True, today=TODAY)
        self.assertEqual(self.headings(), ['## [2030-12-01] ingest | Old', '## [2031-01-05] ingest | A',
                                           '## [2031-01-07] ingest | C', '## [2031-01-10] ingest | B'])

    def test_same_heading_with_a_different_body_is_merged_not_dropped(self):
        self.log.write_text('# Log\n\n## [2031-01-05] ingest | A\n\nlog body A\n')
        x = self.root / '03-wiki/log-append-x.md'
        x.write_text('## [2031-01-05] ingest | A\n\nONLY-HERE body\n')
        (self.root / '03-wiki/log-append-y.md').write_text(
            '## [2031-01-08] lint | 每週檢查\n\nfirst\n\n## [2031-01-08] lint | 每週檢查\n\nsecond\n')
        (self.root / '03-wiki/log-append-z.md').write_text('## [2031-01-08] lint | 每週檢查\n\nthird\n')
        plan = merge_fragments(self.root, apply=True, today=TODAY)
        text = self.log.read_text()
        for body in ('log body A', 'ONLY-HERE body', 'first', 'second', 'third'):
            self.assertIn(body, text)
        self.assertEqual([item['already_in_log'] for item in plan], [[], [], []])
        self.assertFalse(x.exists())

    def test_text_before_the_first_entry_keeps_the_fragment(self):
        path = self.root / '03-wiki/log-append-p.md'
        path.write_text('---\ntitle: f\n---\n\nImportant note that belongs to no entry\n\n'
                        '## [2031-11-07] ingest | C\n\nc\n')
        plan = merge_fragments(self.root, apply=True, today=TODAY)
        self.assertTrue(plan[0]['action'].startswith('kept: text before the first entry'))
        self.assertTrue(path.exists())
        self.assertEqual(self.log.read_text(), LOG)

    def test_frontmatter_and_a_title_before_the_first_entry_are_not_content(self):
        path = self.frag('log-append-2031-11-07.md', '## [2031-11-07] ingest | C\n\nc')
        plan = merge_fragments(self.root, apply=True, today=TODAY)
        self.assertEqual(plan[0]['merged'], ['## [2031-11-07] ingest | C'])
        self.assertFalse(path.exists())

    def test_body_goes_in_as_written(self):
        body = '    indented code stays indented\n\n- item\n\n\ttab'
        self.frag('log-append-2031-11-09.md', '## [2031-11-09] ingest | 原文\n\n' + body)
        merge_fragments(self.root, apply=True, today=TODAY)
        self.assertIn('## [2031-11-09] ingest | 原文\n\n' + body + '\n\n（原載碎片', self.log.read_text())

    def test_merging_the_same_fragment_again_adds_nothing(self):
        section = '## [2031-11-09] ingest | 新的\n\n內容'
        self.frag('log-append-2031-11-09.md', section)
        merge_fragments(self.root, apply=True, today=TODAY)
        once = self.log.read_text()
        self.frag('log-append-2031-11-09.md', section)     # e.g. restored from another branch
        plan = merge_fragments(self.root, apply=True, today=TODAY)
        self.assertEqual(plan[0]['merged'], [])
        self.assertEqual(self.log.read_text(), once)

    def test_a_crlf_log_stays_crlf(self):
        self.log.write_bytes(b'# Log\r\n\r\n## [2031-01-05] ingest | A\r\n\r\nA\r\n')
        (self.root / '03-wiki/log-append-1.md').write_text('## [2031-01-07] ingest | C\n\nc\n')
        merge_fragments(self.root, apply=True, today=TODAY)
        data = self.log.read_bytes()
        self.assertIn(b'## [2031-01-07] ingest | C\r\n\r\nc\r\n', data)
        self.assertNotIn(b'\n', data.replace(b'\r\n', b''))

    def test_missing_log_keeps_every_fragment(self):
        self.log.unlink()
        path = self.frag('log-append-2031-11-09.md', '## [2031-11-09] ingest | 新的\n\n內容')
        plan = merge_fragments(self.root, apply=True, today=TODAY)
        self.assertEqual(plan, [{'fragment': path.name, 'action': 'kept: 03-wiki/log.md not found'}])
        self.assertTrue(path.exists())

    def test_two_fragments_same_day_keep_file_order(self):
        self.frag('log-append-2031-11-06-a.md', '## [2031-11-06] ingest | 甲\n\nx')
        self.frag('log-append-2031-11-06-b.md', '## [2031-11-06] ingest | 乙\n\nx')
        merge_fragments(self.root, apply=True, today=TODAY)
        self.assertEqual(self.headings()[-3:], ['## [2031-11-06] update | 第二批',
                                                '## [2031-11-06] ingest | 甲', '## [2031-11-06] ingest | 乙'])

    def test_rerun_does_not_duplicate_an_entry_already_in_log(self):
        self.frag('log-append-2031-11-06.md', '## [2031-11-06] update | 第二批\n\nbody b')
        plan = merge_fragments(self.root, apply=True, today=TODAY)
        self.assertEqual(plan[0]['merged'], [])
        self.assertEqual(plan[0]['already_in_log'], ['## [2031-11-06] update | 第二批'])
        self.assertEqual(self.log.read_text(), LOG)

    def test_fragment_without_entries_is_kept(self):
        path = self.frag('log-append-2031-11-08.md', '只有散文，沒有條目標題')
        plan = merge_fragments(self.root, apply=True, today=TODAY)
        self.assertTrue(plan[0]['action'].startswith('kept'))
        self.assertTrue(path.exists())
        self.assertEqual(self.log.read_text(), LOG)


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.vault, self.user = self.root / 'vault', self.root / 'user'
        for folder in ('03-wiki', '01-profile', 'bin'):
            (self.vault / folder).mkdir(parents=True)
        self.user.mkdir()
        here = Path(__file__).resolve().parent
        (self.vault / 'bin/status-vocab.json').write_text((here / 'status-vocab.json').read_text())
        (self.vault / 'bin/skill-sources.json').write_text(json.dumps({'memory_source': None}))
        (self.vault / '03-wiki/log.md').write_text(LOG + '## [2031-11-03] lint | 定期整併\n\n上一輪\n')
        (self.vault / '03-wiki/open-questions.md').write_text(
            '# Q\n\n## Active\n\n### old-one：舊題\n\n- Seen：2031-08-12\n\n### new-one：新題\n\n- Seen：2031-11-01\n\n'
            '### template-one：範例\n\n- Seen：YYYY-MM-DD\n\n'
            '## Answered\n\n### done-one：已答\n\n- Seen：2031-01-01\n')
        (self.vault / '03-wiki' / 'proj-a.md').write_text('---\ntype: project\nstatus: production\n---\n[[missing]]\n')

    def test_only_old_active_questions_are_listed(self):
        self.assertEqual(stale_questions(self.vault, TODAY), [{'id': 'old-one', 'seen': '2031-08-12'}])

    def test_injected_layer_counts_lines_and_flags_the_budget(self):
        (self.vault / 'AGENT-RULES.md').write_text('rule\n' * 150)
        (self.vault / 'CLAUDE.md').write_text('entry\n' * 5)
        (self.user / '.claude').mkdir()
        (self.user / '.claude/CLAUDE.md').write_text('global\n' * 60)
        layer = injected_layer(self.vault, self.user)
        self.assertEqual(layer['lines'], {'CLAUDE.md': 5, 'AGENT-RULES.md': 150, '~/.claude/CLAUDE.md': 60})
        self.assertEqual(layer['total_lines'], 215)
        self.assertTrue(layer['over_budget'])

    def test_report_is_read_only_and_starts_from_the_last_logged_pass(self):
        before = {p: p.read_bytes() for p in self.vault.rglob('*') if p.is_file()}
        out = report(self.vault, self.user, today=TODAY)
        self.assertEqual(out['since'], '2031-11-03')
        self.assertEqual(out['broken_wikilinks'], ['proj-a.md: missing'])
        self.assertTrue(any('proj-a.md: status "production"' in w for w in out['frontmatter_warnings']))
        self.assertEqual(out['stale_open_questions'], [{'id': 'old-one', 'seen': '2031-08-12'}])
        self.assertEqual({p: p.read_bytes() for p in self.vault.rglob('*') if p.is_file()}, before)

    def test_report_without_vocabulary_says_the_gate_was_skipped(self):
        (self.vault / 'bin/status-vocab.json').unlink()
        out = report(self.vault, self.user, today=TODAY)
        self.assertEqual(out['frontmatter_warnings'], ['bin/status-vocab.json missing; frontmatter gate skipped'])


if __name__ == '__main__':
    unittest.main()
