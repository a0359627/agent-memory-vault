#!/usr/bin/env python3
"""Behavioral filesystem tests: all mutations are confined to a temporary tree."""
import json
from pathlib import Path
import tempfile
import unittest

from skill_sync import SkillStore, read_tree


class SkillSyncTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.vault, self.user = self.root / 'vault', self.root / 'user'
        self.vault.mkdir()
        self.user.mkdir()
        self.registry = {
            'schema_version': 1,
            'shared_source': '~/.claude/skills', 'shared_runtime': '~/.agents/skills',
            'shared_skills': ['example', 'second'],
            'origins': [
                {'id': 'claude-skills', 'source': '~/.claude/skills'},
                {'id': 'codex-skills', 'source': '~/.codex/skills', 'include': ['repo-skill']},
                {'id': 'origin-extra-a', 'source': '~/extra-a/skills'},
                {'id': 'origin-extra-b', 'source': '~/extra-b/skills'}],
            'global_files': [
                {'mirror': 'claude-global/CLAUDE.md', 'source': '~/.claude/CLAUDE.md'},
                {'mirror': 'codex-global/AGENTS.md', 'source': '~/.codex/AGENTS.md'}],
            'memory_source': '~/.claude/projects', 'primary_memory_project': 'main'}
        self.write_registry(self.registry)
        for name in ['example', 'second']:
            self.put(self.user / f'.claude/skills/{name}/SKILL.md', 'canonical ' + name)
            self.put(self.user / f'.agents/skills/{name}/SKILL.md', 'old runtime ' + name)
        helper = self.user / '.claude/skills/example/run.sh'
        self.put(helper, '#!/bin/sh\nexit 0\n')
        helper.chmod(0o755)
        self.put(self.user / 'external/SKILL.md', 'external material')
        (self.user / '.claude/skills/external-skill').symlink_to(self.user / 'external', target_is_directory=True)
        for relative, body in {
            '.codex/skills/repo-skill/SKILL.md': 'native',
            'extra-a/skills/method.md': 'extra a',
            'extra-b/skills/method.md': 'extra b',
            '.claude/CLAUDE.md': 'Claude rules', '.codex/AGENTS.md': 'Codex rules',
            '.claude/projects/main/memory/MEMORY.md': 'main memory',
            '.claude/projects/other/memory/MEMORY.md': 'other memory'}.items():
            self.put(self.user / relative, body)
        self.store = SkillStore(self.vault, self.user)

    @staticmethod
    def put(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def write_registry(self, registry):
        self.put(self.vault / 'bin/skill-sources.json', json.dumps(registry))

    def with_registry(self, **overrides):
        """Rewrite the registry on disk and return a store that reads the new values."""
        registry = dict(self.registry)
        registry.update(overrides)
        self.write_registry(registry)
        return SkillStore(self.vault, self.user)

    def test_read_only_does_not_create_files_or_change_runtime(self):
        before = read_tree(self.root)
        self.assertEqual(len(self.store.links()), 2)
        self.store.snapshot()
        self.assertEqual(read_tree(self.root), before)
        self.assertFalse((self.user / '.local').exists())

    def test_link_preserves_original_and_reuses_live_content(self):
        self.store.links(apply=True)
        runtime = self.user / '.agents/skills/example'
        self.assertTrue(runtime.is_symlink())
        self.assertEqual((runtime / 'SKILL.md').read_text(), 'canonical example')
        original = list(self.store.backup_root.rglob('example/SKILL.md'))
        self.assertEqual(len(original), 1)
        self.assertEqual(original[0].read_text(), 'old runtime example')
        self.put(self.user / '.claude/skills/example/SKILL.md', 'new canonical')
        self.assertEqual((runtime / 'SKILL.md').read_text(), 'new canonical')
        self.assertEqual(self.store.links(), [])

    def test_portable_roundtrip_restores_all_origins_and_each_memory(self):
        self.store.links(apply=True)
        self.store.snapshot(apply=True)
        self.assertFalse(any(p.is_symlink() for p in self.store.base.rglob('*')))
        self.store.check()
        self.put(self.user / 'external/SKILL.md', 'source later changed')
        restored_user = self.root / 'restored-user'
        self.put(restored_user / '.claude/CLAUDE.md', 'existing rules')
        self.put(restored_user / '.agents/skills/unrelated/SKILL.md', 'keep me')
        self.put(restored_user / '.codex/skills/.system/system/SKILL.md', 'keep system')
        native_link = restored_user / '.codex/skills/repo-skill'
        native_link.symlink_to(self.user / 'external', target_is_directory=True)
        restored = SkillStore(self.vault, restored_user)
        before = read_tree(restored_user)
        restored.restore()
        self.assertEqual(read_tree(restored_user), before)
        restored.restore(apply=True)
        for relative, body in {
            '.claude/skills/external-skill/SKILL.md': 'external material',
            'extra-a/skills/method.md': 'extra a', 'extra-b/skills/method.md': 'extra b',
            '.claude/projects/main/memory/MEMORY.md': 'main memory',
            '.claude/projects/other/memory/MEMORY.md': 'other memory',
            '.agents/skills/unrelated/SKILL.md': 'keep me',
            '.codex/skills/.system/system/SKILL.md': 'keep system',
            '.codex/skills/repo-skill/SKILL.md': 'native'}.items():
            self.assertEqual((restored_user / relative).read_text(), body)
        self.assertEqual((self.user / 'external/SKILL.md').read_text(), 'source later changed')
        self.assertTrue((restored_user / '.agents/skills/example').is_symlink())
        self.assertEqual((restored_user / '.claude/skills/example/run.sh').stat().st_mode & 0o777, 0o755)
        self.assertIn('existing rules', [p.read_text() for p in restored.backup_root.rglob('CLAUDE.md')])

    def test_null_memory_source_skips_memory_capture(self):
        """The starter default: no memory root is read, mirrored or restored."""
        store = self.with_registry(memory_source=None)
        self.assertNotIn('claude-memory', store.mirror_roots())
        store.links(apply=True)
        store.snapshot(apply=True)
        self.assertFalse((store.base / 'claude-memory').exists())
        metadata = json.loads((store.base / 'snapshot.json').read_text())
        self.assertEqual(metadata['memory_projects'], [])
        self.assertFalse(any(key.startswith('claude-memory/') for key in metadata['files']))
        # The machine's own memory files are neither copied nor touched.
        self.assertEqual((self.user / '.claude/projects/main/memory/MEMORY.md').read_text(), 'main memory')
        self.assertEqual((self.user / '.claude/projects/other/memory/MEMORY.md').read_text(), 'other memory')

    def test_check_and_restore_pass_without_a_memory_mirror_root(self):
        """A vault that never captured memory must still verify and restore cleanly."""
        store = self.with_registry(memory_source=None)
        store.links(apply=True)
        store.snapshot(apply=True)
        self.assertFalse((store.base / 'claude-memory').exists())
        self.assertEqual(store.check(), len(store.snapshot_payload()[0]))
        target = self.root / 'memoryless-user'
        restored = SkillStore(self.vault, target)
        restored.restore(apply=True)
        self.assertEqual((target / '.claude/skills/example/SKILL.md').read_text(), 'canonical example')
        self.assertFalse((target / '.claude/projects').exists())

    def test_memory_projects_allowlist_limits_capture(self):
        store = self.with_registry(memory_projects=['main'])
        store.links(apply=True)
        store.snapshot(apply=True)
        self.assertEqual((store.base / 'claude-memory/MEMORY.md').read_text(), 'main memory')
        self.assertFalse((store.base / 'claude-memory/by-project').exists())
        metadata = json.loads((store.base / 'snapshot.json').read_text())
        self.assertEqual(metadata['memory_projects'], ['main'])
        store.check()
        with self.assertRaisesRegex(ValueError, 'memory_projects'):
            self.with_registry(memory_projects=['../escape'])

    def test_memory_exclusion_skips_a_project_before_reading_it(self):
        # The excluded project holds something the secret preflight would refuse. A snapshot that still
        # succeeds proves the project was skipped before its files were opened, not filtered afterwards.
        self.put(self.user / '.claude/projects/other/memory/note.md',
                 'ghp_' + 'A' * 36)
        store = self.with_registry(memory_exclusions={'other': '不收進這個 vault'})
        store.links(apply=True)
        store.snapshot(apply=True)
        base = self.vault / '08-skill-base'
        self.assertTrue((base / 'claude-memory/MEMORY.md').is_file())
        self.assertFalse((base / 'claude-memory/by-project/other').exists())
        metadata = json.loads((base / 'snapshot.json').read_text())
        self.assertEqual(metadata['memory_projects'], ['main'])
        self.assertEqual(metadata['excluded_memory_projects'], {'other': '不收進這個 vault'})
        self.assertGreater(store.check(), 0)

    def test_memory_exclusion_wins_over_the_allowlist(self):
        store = self.with_registry(memory_projects=['main', 'other'], memory_exclusions={'other': 'reason'})
        payload, projects = store.snapshot_payload()
        self.assertEqual(projects, ['main'])
        self.assertFalse(any('by-project/other' in key for key in payload))

    def test_snapshot_metadata_is_unchanged_when_nothing_is_excluded(self):
        self.store.links(apply=True)
        self.store.snapshot(apply=True)
        metadata = json.loads((self.vault / '08-skill-base/snapshot.json').read_text())
        self.assertNotIn('excluded_memory_projects', metadata)

    def test_invalid_memory_exclusions_are_rejected(self):
        for bad in (['other'], {'other': ''}, {'other': '   '}, {'a/b': 'reason'}, {'..': 'reason'}, {'other': 3}):
            with self.assertRaises(ValueError, msg=repr(bad)):
                self.with_registry(memory_exclusions=bad)
        with self.assertRaisesRegex(ValueError, 'primary'):
            self.with_registry(memory_exclusions={'main': 'reason'})

    def test_origin_exclude_skips_top_level_entries_owned_by_another_tool(self):
        self.put(self.user / 'extra-a/skills/platform-synced/SKILL.md', 'managed elsewhere')
        self.put(self.user / 'extra-a/skills/.trash/old/SKILL.md', 'deleted')
        origins = [dict(item) for item in self.registry['origins']]
        next(item for item in origins if item['id'] == 'origin-extra-a')['exclude'] = ['platform-synced', '.trash']
        store = self.with_registry(origins=origins)
        payload, _ = store.snapshot_payload()
        self.assertIn('origin-extra-a/method.md', payload)
        self.assertFalse(any('platform-synced' in key or '.trash' in key for key in payload))
        origins[2]['exclude'] = 'platform-synced'
        with self.assertRaisesRegex(ValueError, 'exclude'):
            self.with_registry(origins=origins)

    def test_secret_preflight_leaves_destination_unchanged(self):
        self.put(self.user / '.claude/skills/example/bad.md', 'AIza' + 'Z' * 35)
        before = read_tree(self.vault)
        with self.assertRaisesRegex(ValueError, 'Possible secret'):
            self.store.snapshot(apply=True)
        self.assertEqual(read_tree(self.vault), before)
        self.assertFalse((self.user / '.local').exists())

    def test_restore_preserves_private_modes_after_git_checkout_normalization(self):
        private = self.user / '.claude/projects/main/memory/MEMORY.md'
        private.chmod(0o600)
        self.store.snapshot(apply=True)
        mirrored = self.store.base / 'claude-memory/MEMORY.md'
        mirrored.chmod(0o644)  # A fresh Git checkout cannot encode mode 0600.
        restored_user = self.root / 'git-restored-user'
        restored = SkillStore(self.vault, restored_user)
        restored.restore(apply=True)
        target = restored_user / '.claude/projects/main/memory/MEMORY.md'
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        restored.check()

    def test_missing_source_fails_before_any_write(self):
        (self.user / 'extra-b/skills/method.md').unlink()
        (self.user / 'extra-b/skills').rmdir()
        before = read_tree(self.vault)
        with self.assertRaisesRegex(ValueError, 'Missing source'):
            self.store.snapshot(apply=True)
        self.assertEqual(read_tree(self.vault), before)

    def test_missing_declared_skill_fails_before_snapshot_write(self):
        (self.user / '.claude/skills/second/SKILL.md').unlink()
        before = read_tree(self.vault)
        with self.assertRaisesRegex(ValueError, 'Missing canonical skill'):
            self.store.snapshot(apply=True)
        self.assertEqual(read_tree(self.vault), before)

    def test_tampered_or_unmanifested_snapshot_is_rejected(self):
        self.store.snapshot(apply=True)
        target = self.store.base / 'claude-skills/example/SKILL.md'
        self.put(target, 'tampered')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.store.restore(apply=True)
        self.store.snapshot(apply=True)
        self.put(self.store.base / 'claude-memory/extra.md', 'unmanifested')
        with self.assertRaisesRegex(ValueError, 'Unmanifested'):
            self.store.restore(apply=True)

    def test_snapshot_is_idempotent_and_removes_old_managed_files(self):
        self.store.snapshot(apply=True)
        metadata = (self.store.base / 'snapshot.json').read_bytes()
        changed, _ = self.store.snapshot(apply=True)
        self.assertEqual(changed, [])
        self.assertEqual((self.store.base / 'snapshot.json').read_bytes(), metadata)
        (self.user / '.claude/projects/other/memory/MEMORY.md').unlink()
        self.store.snapshot(apply=True)
        self.assertFalse((self.store.base / 'claude-memory/by-project/other/MEMORY.md').exists())

    def test_unmanaged_parent_link_blocks_restore_without_writes(self):
        self.store.snapshot(apply=True)
        target_user = self.root / 'unsafe-user'
        target_user.mkdir()
        (target_user / '.claude').symlink_to(self.user / '.claude', target_is_directory=True)
        before = read_tree(self.user)
        with self.assertRaisesRegex(ValueError, 'Unmanaged symlink'):
            SkillStore(self.vault, target_user).restore(apply=True)
        self.assertEqual(read_tree(self.user), before)


if __name__ == '__main__':
    unittest.main()
