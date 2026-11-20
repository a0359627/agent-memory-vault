#!/usr/bin/env python3
"""Fixture tests for the memory-metabolism gates in check_vault.py. Everything runs in a temporary tree."""
from datetime import date
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

# A .pyc embeds the absolute path of whoever compiled it; see the note in check_vault.py.
sys.dont_write_bytecode = True

from check_vault import (frontmatter_check, ignored_pages, load_vocab, memory_check,  # noqa: E402
                         source_link_check, wiki_check)

TODAY = date(2030, 9, 17)
VOCAB = json.loads((Path(__file__).resolve().parent / 'status-vocab.json').read_text())


class GateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / '03-wiki').mkdir()
        (self.root / '01-profile').mkdir()
        (self.root / 'memory').mkdir()

    def page(self, name, **fields):
        body = '---\n' + '\n'.join(f'{k}: {v}' for k, v in fields.items()) + '\n---\n\n# ' + name + '\n'
        (self.root / '03-wiki' / f'{name}.md').write_text(body)

    def memory(self, name, mtype, **extra):
        meta = '\n'.join(f'  {k}: {v}' for k, v in extra.items())
        (self.root / 'memory' / f'{name}.md').write_text(
            f'---\nname: {name}\ndescription: x\nmetadata:\n  type: {mtype}\n{meta}\n---\n\nfact\n')

    def warnings(self):
        return frontmatter_check(self.root, VOCAB, TODAY)

    def test_clean_page_produces_no_warning(self):
        self.page('ok', type='project', status='current', subject_status='production',
                  updated='2030-09-17', revisit_when='2030-12-17 前未動工則標 stale')
        self.assertEqual(self.warnings(), [])

    def test_status_outside_vocabulary_warns(self):
        self.page('bad', type='project', status='production', updated='2030-09-17')
        self.assertTrue(any('status "production" is not a memory lifecycle value' in w for w in self.warnings()))

    def test_subject_status_outside_vocabulary_warns(self):
        self.page('bad', type='project', status='current', subject_status='bogus-value', updated='2030-09-17')
        self.assertTrue(any('subject_status "bogus-value"' in w for w in self.warnings()))

    def test_every_documented_lifecycle_value_is_accepted(self):
        for value in VOCAB['status']['lifecycle']:
            extra = {'superseded_by': 'target'} if value == 'superseded' else {}
            self.page(f'page-{value}', type='reference', status=value, updated='2030-09-17', **extra)
        self.page('target', type='reference', status='current', updated='2030-09-17')
        self.assertEqual(self.warnings(), [])

    def test_overdue_revisit_warns_but_not_for_frozen_slices(self):
        self.page('late', type='reference', status='current', updated='2030-08-01', revisit_when='2030-09-01')
        self.page('slice', type='review', status='historical', revisit_when='2030-09-01')
        self.page('condition', type='reference', status='current', updated='2030-08-01', revisit_when='上游改版時')
        ws = self.warnings()
        self.assertTrue(any(w.startswith('late.md: revisit_when 2030-09-01 is overdue') for w in ws))
        self.assertFalse(any(w.startswith(('slice.md', 'condition.md')) for w in ws))

    def test_superseded_needs_existing_target(self):
        self.page('old', type='project', status='superseded')
        self.page('old2', type='project', status='superseded', superseded_by='nowhere')
        self.page('old3', type='project', status='superseded', superseded_by='"[[new]]"'.strip('"'))
        self.page('new', type='project', status='current', updated='2030-09-17')
        ws = self.warnings()
        self.assertTrue(any('old.md: status superseded without superseded_by' in w for w in ws))
        self.assertTrue(any('old2.md: superseded_by target "nowhere" not found' in w for w in ws))
        self.assertFalse(any(w.startswith('old3.md') for w in ws))

    def test_hyphen_spelling_warns(self):
        (self.root / '03-wiki/h.md').write_text('---\ntype: pipeline\nstatus: stale\nsuperseded-by: x\n---\n')
        self.assertTrue(any('spell it superseded_by' in w for w in self.warnings()))

    def test_skill_card_verified_at_for_both_type_spellings(self):
        self.page('skill-a', type='skill', status='current', updated='2030-09-17')
        self.page('skill-b', type='skill-card', status='current', verified_at='2030-01-01')
        self.page('skill-c', type='skill-card', status='current', verified_at='2030-09-10')
        self.page('skill-d', type='skill', status='watchlist')
        ws = self.warnings()
        self.assertTrue(any('skill-a.md: current skill card without verified_at' in w for w in ws))
        self.assertTrue(any('skill-b.md: verified_at 2030-01-01 older than 180 days' in w for w in ws))
        self.assertFalse(any(w.startswith(('skill-c.md', 'skill-d.md')) for w in ws))

    def test_current_wiki_page_needs_a_date_field(self):
        self.page('undated', type='project', status='current')
        self.page('dated', type='project', status='current', updated='2030-09-17')
        self.page('observed', type='reference', status='current', observed_at='2030-09-17')
        self.page('old', type='project', status='stale')
        (self.root / '01-profile/who.md').write_text('---\nstatus: current\n---\n')
        ws = self.warnings()
        self.assertTrue(any('undated.md: status current without any of updated/observed_at/verified_at' in w
                            for w in ws))
        self.assertFalse(any(w.startswith(('dated.md', 'observed.md', 'old.md', 'who.md')) for w in ws))

    def test_pages_without_frontmatter_or_status_are_ignored(self):
        (self.root / '03-wiki/plain.md').write_text('# no frontmatter\n')
        self.page('hub', type='hub')
        self.assertEqual(self.warnings(), [])

    def test_source_dirs_need_a_real_link_pointing_at_them(self):
        raw = self.root / '02-raw'
        for topic in ('linked-topic', 'backtick-only', 'md-linked'):
            (raw / topic).mkdir(parents=True)
            (raw / topic / 'SOURCE.md').write_text('# src\n')
        (raw / 'no-markdown').mkdir()
        (raw / 'no-markdown' / 'data.csv').write_text('a,b\n')
        (self.root / '04-projects' / 'deliverable').mkdir(parents=True)
        (self.root / '04-projects' / 'deliverable' / 'PLAN.md').write_text('# plan\n')
        (self.root / '07-archive' / 'recovered').mkdir(parents=True)
        (self.root / '07-archive' / 'recovered' / 'README.md').write_text('# old\n')
        (self.root / '03-wiki' / 'digest.md').write_text(
            '---\nstatus: stale\n---\n[[linked-topic/SOURCE]] and `02-raw/backtick-only/SOURCE.md` and '
            '[plan](../02-raw/md-linked/SOURCE.md) and [site](https://example.com/02-raw/backtick-only/)\n')
        warnings = source_link_check(self.root)
        self.assertEqual(len(warnings), 3, warnings)
        self.assertTrue(any(w.startswith('02-raw/backtick-only:') for w in warnings), warnings)
        self.assertTrue(any(w.startswith('04-projects/deliverable:') for w in warnings), warnings)
        self.assertTrue(any(w.startswith('07-archive/recovered:') for w in warnings), warnings)

    def test_memory_gate(self):
        self.memory('young', 'project', observed_at='2030-09-01')
        self.memory('old-no-revisit', 'project', observed_at='2030-05-01')
        self.memory('old-with-revisit', 'project', observed_at='2030-05-01', revisit_when='2030-12-31')
        self.memory('old-feedback', 'feedback', observed_at='2030-01-01')
        (self.root / 'memory/MEMORY.md').write_text('- index\n')
        ws = memory_check(self.root / 'memory', VOCAB, TODAY)
        self.assertEqual(len(ws), 1, ws)
        self.assertIn('old-no-revisit.md: project memory 139 days old without revisit_when', ws[0])

    def test_memory_gate_missing_dir(self):
        self.assertEqual(len(memory_check(self.root / 'nope', VOCAB, TODAY)), 1)

    # --- regressions from review: legal YAML and Markdown spellings that used to be misread ---------

    def test_quoted_values_are_read_as_yaml_would_read_them(self):
        (self.root / '03-wiki/x.md').write_text('---\nstatus: "current"\nupdated: 2030-09-01\n---\n')
        (self.root / '03-wiki/y.md').write_text('---\nstatus: superseded\nsuperseded_by: "[[target]]"\n---\n')
        (self.root / '03-wiki/target.md').write_text("---\nstatus: 'current' # checked\nupdated: 2030-09-01\n---\n")
        (self.root / '03-wiki/skill-q.md').write_text('---\ntype: "skill-card"\nstatus: current\nupdated: 2030-09-01\n---\n')
        ws = self.warnings()
        self.assertEqual(ws, ['skill-q.md: current skill card without verified_at'])

    def test_frontmatter_closed_with_dots_does_not_read_the_body_as_metadata(self):
        (self.root / '03-wiki/dots.md').write_text(
            '---\nstatus: current\nupdated: 2030-09-01\n...\n\nstatus: production\n\n---\n\ntext\n')
        self.assertEqual(self.warnings(), [])

    def test_a_date_that_cannot_exist_is_reported_instead_of_ignored(self):
        self.page('typo', type='reference', status='current', updated='2030-09-01', revisit_when='2030-13-40')
        ws = self.warnings()
        self.assertEqual(len(ws), 1, ws)
        self.assertIn('typo.md: revisit_when has a date that is not a real calendar date', ws[0])

    def test_a_candidate_or_deprecated_status_gets_a_direct_hint(self):
        self.page('maybe', type='reference', status='candidate', updated='2030-09-01')
        self.page('gone', type='skill-card', status='deprecated')
        self.page('other', type='project', status='production', updated='2030-09-01')
        ws = self.warnings()
        self.assertTrue(any(w.startswith('maybe.md:') and 'status: watchlist' in w for w in ws), ws)
        self.assertTrue(any(w.startswith('gone.md:') and 'status: stale' in w for w in ws), ws)
        self.assertTrue(any(w.startswith('other.md:') and 'subject_status' in w for w in ws), ws)

    def test_angle_bracket_and_titled_links_count_as_links(self):
        raw = self.root / '02-raw'
        for topic in ('space topic', 'titled', 'image-only'):
            (raw / topic).mkdir(parents=True)
            (raw / topic / 'note.md').write_text('# src\n')
        (self.root / '03-wiki' / 'hub.md').write_text(
            '[a](<../02-raw/space topic/note.md>) and [c](../02-raw/titled/note.md "a title") and '
            '![shot](../02-raw/image-only/note.md)\n')
        warnings = source_link_check(self.root)
        self.assertEqual(len(warnings), 1, warnings)
        self.assertTrue(warnings[0].startswith('02-raw/image-only:'), warnings)

    def test_memory_fields_count_only_inside_the_frontmatter(self):
        (self.root / 'memory/body-mention.md').write_text(
            '---\nname: n\nmetadata:\n  type: "project"\n  observed_at: 2030-05-01\n---\n\n'
            '  revisit_when: this line is prose in the body\n')
        (self.root / 'memory/no-frontmatter.md').write_text('type: project\nobserved_at: 2030-01-01\n')
        ws = memory_check(self.root / 'memory', VOCAB, TODAY)
        self.assertEqual(len(ws), 1, ws)
        self.assertIn('memory body-mention.md: project memory 139 days old without revisit_when', ws[0])

    def test_a_log_fragment_waiting_to_be_merged_is_not_an_orphan(self):
        (self.root / '03-wiki/index.md').write_text('[[linked]]\n')
        (self.root / '03-wiki/linked.md').write_text('back to [[index]]\n')
        (self.root / '03-wiki/log-append-2030-09-17.md').write_text('## [2030-09-17] update | x\n\nbody\n')
        (self.root / '03-wiki/forgotten.md').write_text('# nobody links here\n')
        self.assertEqual(wiki_check(self.root)['orphan_wiki_pages'], ['forgotten.md'])

    def test_vocab_is_optional_until_the_vault_adopts_it(self):
        self.assertIsNone(load_vocab(self.root))
        (self.root / 'bin').mkdir()
        (self.root / 'bin/status-vocab.json').write_text(json.dumps(VOCAB))
        self.assertEqual(load_vocab(self.root)['status']['lifecycle'], VOCAB['status']['lifecycle'])


class IgnoredPagesTest(unittest.TestCase):
    """The one gate that is an error: a page the ignore rules keep out of git."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / '03-wiki').mkdir()
        (self.root / '01-profile').mkdir()
        # The answer must not depend on whoever runs the test: no global ignore file, and no outer
        # repository to discover when the temporary directory happens to live inside a work tree.
        isolated = {'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1',
                    'GIT_CEILING_DIRECTORIES': str(self.root.parent)}
        saved = {key: os.environ.get(key) for key in isolated}
        os.environ.update(isolated)
        self.addCleanup(lambda: [os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
                                 for k, v in saved.items()])

    def test_outside_a_git_work_tree_nothing_is_reported(self):
        (self.root / '03-wiki' / 'glossary-token-terms.md').write_text('# page\n')
        self.assertEqual(ignored_pages(self.root), [])

    def test_a_wiki_page_matching_an_ignore_pattern_is_reported(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True, capture_output=True)
        (self.root / '.gitignore').write_text('*token*\n')
        (self.root / '03-wiki' / 'glossary-token-terms.md').write_text('# an ordinary page with an unlucky name\n')
        (self.root / '03-wiki' / 'glossary-terms.md').write_text('# same page, a name the rule does not catch\n')
        (self.root / '03-wiki/token-notes.txt').write_text('not a page\n')
        found = ignored_pages(self.root)
        self.assertEqual(len(found), 1, found)
        self.assertTrue(found[0].startswith('03-wiki/glossary-token-terms.md:'), found)


if __name__ == '__main__':
    unittest.main()
