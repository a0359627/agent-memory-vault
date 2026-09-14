#!/usr/bin/env python3
"""Registry-driven local skill links, portable snapshots and scoped restore.

Read-only by default; mutations require --apply. No network or package dependencies.

Registry (`bin/skill-sources.json`) fields that steer the memory mirror:

- ``memory_source``：agent 平台存放每個專案記憶的根目錄（例如 ``~/.claude/projects``）。
  設為 ``null`` 代表「不要快照任何記憶」——這是 starter 的預設值。此時
  ``claude-memory/`` 不會出現在鏡像根清單裡，快照與還原都完全跳過記憶。
- ``memory_projects``：可選的 allowlist（專案 id 陣列）。**不設或設為 null 代表整個
  ``memory_source`` 底下的每個專案都會被吸進 vault**——多數人不想要這個預設，因為
  專案 id 通常就是該專案的絕對路徑編碼，本身即是可識別資訊。只要填了這個陣列，
  就只有列名的專案會進快照，其餘一律跳過。
- ``primary_memory_project``：放在鏡像 ``claude-memory/`` 根層（而非 ``by-project/<id>/``）
  的那個專案 id。``memory_source`` 為 null 時不會被讀取。

Platform note: `link` 建立符號連結，因此需要 macOS／Linux（Windows 請走 WSL）。
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
from datetime import datetime, timezone
from uuid import uuid4


IGNORED_DIRS = {'.git', '.system', '__pycache__', 'node_modules', '.cache'}
MEMORY_ROOT = 'claude-memory'
SECRET = re.compile(rb'AIza[0-9A-Za-z_-]{30,}|sk-proj-[A-Za-z0-9_-]{20,}|'
                    rb'sk-[A-Za-z0-9]{32,}|'
                    rb'gh[pousr]_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{20,}|'
                    rb'-----BEGIN [A-Z ]*PRIVATE KEY-----')


def ignored(name):
    return (name in IGNORED_DIRS or name == '.DS_Store' or name.startswith('.env')
            or name.endswith(('.pyc', '.db', '.sqlite', '.sqlite3', '.key', '.pem'))
            or bool(re.match(r'(token|credentials?|client_secret|service-account).*\.json$', name)))


def read_tree(root, include=None):
    """Materialize symlinks in memory; fail on missing inputs or cycles."""
    root = Path(root)
    if not root.is_dir():
        raise ValueError(f'Missing source directory: {root}')
    result = {}

    def visit(path, relative, ancestors):
        if ignored(path.name):
            return
        real = path.resolve(strict=True)
        if real in ancestors:
            raise ValueError(f'Symlink cycle: {path}')
        if path.is_dir():
            for child in sorted(path.iterdir()):
                visit(child, relative / child.name, ancestors | {real})
        elif path.is_file():
            result[relative.as_posix()] = (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
        else:
            raise ValueError(f'Unsupported source: {path}')

    entries = [root / n for n in include] if include else sorted(root.iterdir())
    for entry in entries:
        visit(entry, Path(entry.name), {root.resolve()})
    return result


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def validate_payload(payload):
    for key, (blob, _) in payload.items():
        p = Path(key)
        if p.is_absolute() or '..' in p.parts:
            raise ValueError(f'Unsafe snapshot path: {key}')
        if SECRET.search(blob):
            # Never print matching values or lines.
            raise ValueError(f'Possible secret; no writes performed: {key}')


class SkillStore:
    def __init__(self, vault, user_root):
        self.vault = Path(vault).resolve()
        self.user_root = Path(user_root).resolve()
        self.base = self.vault / '08-skill-base'
        self.registry = json.loads((self.vault / 'bin/skill-sources.json').read_text())
        if self.registry.get('schema_version') != 1:
            raise ValueError('Unsupported source registry version')
        names = self.registry['shared_skills']
        if len(set(names)) != len(names) or any(not re.fullmatch(r'[a-z0-9-]+', n) for n in names):
            raise ValueError('Invalid or duplicate shared skill name')
        allowlist = self.registry.get('memory_projects')
        if allowlist is not None:
            if not isinstance(allowlist, list) or any(
                    not isinstance(p, str) or not p or p in ('.', '..') or '/' in p for p in allowlist):
                raise ValueError('memory_projects must be a list of plain project ids')
        self.backup_root = None

    def memory_source(self):
        """Return the memory root, or None when the registry disables memory capture."""
        value = self.registry.get('memory_source')
        return self.home_path(value) if value else None

    def home_path(self, value):
        if not value.startswith('~/') or '..' in Path(value[2:]).parts:
            raise ValueError(f'Source must be relative to the user root: {value}')
        return self.user_root / value[2:]

    def backup(self, path):
        """Move only the managed path itself, preserving symlink targets."""
        if self.backup_root is None:
            tag = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid4().hex[:8]
            self.backup_root = self.user_root / '.local/state/vault-skill-backups' / tag
            self.backup_root.mkdir(parents=True, mode=0o700)
        relative = str(path.absolute()).lstrip('/')
        target = self.backup_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(target))
        return target

    def links(self, apply=False):
        src = self.home_path(self.registry['shared_source'])
        dst = self.home_path(self.registry['shared_runtime'])
        changes = []
        for name in self.registry['shared_skills']:
            source, target = src / name, dst / name
            if not (source / 'SKILL.md').is_file():
                raise ValueError(f'Missing canonical skill: {source}')
            if target.is_symlink() and target.resolve() == source.resolve():
                continue
            changes.append((source, target))
        if apply:
            dst.mkdir(parents=True, exist_ok=True)
            for source, target in changes:
                previous = self.backup(target) if os.path.lexists(target) else None
                try:
                    # Relative links survive moving the user home as a whole.
                    target.symlink_to(os.path.relpath(source, target.parent), target_is_directory=True)
                except BaseException:
                    if previous is not None:
                        shutil.move(str(previous), str(target))
                    raise
        return [target.name for _, target in changes]

    def snapshot_payload(self):
        self.links()  # Validate every declared canonical skill before any snapshot mutation.
        payload = {}
        for item in self.registry['origins']:
            files = read_tree(self.home_path(item['source']), item.get('include'))
            payload.update({item['id'] + '/' + key: value for key, value in files.items()})
        for item in self.registry['global_files']:
            source = self.home_path(item['source'])
            payload[item['mirror']] = (source.read_bytes(), stat.S_IMODE(source.stat().st_mode))
        projects = []
        memroot = self.memory_source()
        if memroot is not None:
            if not memroot.is_dir():
                raise ValueError(f'Missing memory source directory: {memroot}')
            allowlist = self.registry.get('memory_projects')
            for memory in sorted(memroot.glob('*/memory')):
                project = memory.parent.name
                # Without an allowlist every project on this machine is captured.
                if allowlist is not None and project not in allowlist:
                    continue
                projects.append(project)
                prefix = MEMORY_ROOT + '/'
                if project != self.registry.get('primary_memory_project'):
                    prefix += 'by-project/' + project + '/'
                payload.update({prefix + key: value for key, value in read_tree(memory).items()})
        validate_payload(payload)
        return payload, projects

    def replace_file(self, target, blob, mode):
        # Never write through an existing link into an unrelated repo.
        if target.is_file() and not target.is_symlink() and target.read_bytes() == blob:
            if stat.S_IMODE(target.stat().st_mode) == mode:
                return
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix='.skill-write-', dir=target.parent)
        previous = None
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(blob)
            os.chmod(temp, mode)
            if os.path.lexists(target):
                previous = self.backup(target)
            os.replace(temp, target)
        except BaseException:
            if previous is not None and not os.path.lexists(target):
                shutil.move(str(previous), str(target))
            raise
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    def snapshot(self, apply=False):
        payload, projects = self.snapshot_payload()
        top_levels = self.mirror_roots()
        changed = []
        for top in sorted(top_levels):
            target = self.base / top
            expected = {k[len(top) + 1:]: v for k, v in payload.items() if k.startswith(top + '/')}
            actual = read_tree(target) if target.is_dir() else {}
            links = target.is_symlink() or (target.is_dir() and any(p.is_symlink() for p in target.rglob('*')))
            if expected != actual or links:
                changed.append(top)
        if apply:
            self.base.mkdir(parents=True, exist_ok=True)
            for top in changed:
                target = self.base / top
                stage = Path(tempfile.mkdtemp(prefix='.skill-stage-', dir=self.base))
                previous = None
                try:
                    for key, (blob, mode) in payload.items():
                        if not key.startswith(top + '/'):
                            continue
                        f = stage / key[len(top) + 1:]
                        f.parent.mkdir(parents=True, exist_ok=True)
                        f.write_bytes(blob)
                        f.chmod(mode)
                    if os.path.lexists(target):
                        previous = self.backup(target)
                    os.replace(stage, target)
                except BaseException:
                    if previous is not None and not os.path.lexists(target):
                        shutil.move(str(previous), str(target))
                    raise
                finally:
                    if stage.exists():
                        shutil.rmtree(stage)
            metadata = {'schema_version': 1, 'generated_at': datetime.now(timezone.utc).isoformat(),
                        'source_user_root': str(self.user_root), 'memory_projects': projects,
                        'registry_sha256': digest((self.vault / 'bin/skill-sources.json').read_bytes()),
                        'files': {k: digest(v[0]) for k, v in sorted(payload.items())},
                        'file_modes': {k: v[1] for k, v in sorted(payload.items())}}
            old = self.base / 'snapshot.json'
            previous = json.loads(old.read_text()) if old.is_file() else {}
            if not changed and all(previous.get(k) == v for k, v in metadata.items() if k != 'generated_at'):
                metadata['generated_at'] = previous['generated_at']
            self.replace_file(old, (json.dumps(metadata, indent=2) + '\n').encode(), 0o644)
        return changed, len(payload)

    def mirror_roots(self):
        roots = ({item['id'] for item in self.registry['origins']}
                 | {item['mirror'].split('/')[0] for item in self.registry['global_files']})
        # No memory source means no memory mirror root; requiring one would fail every check.
        if self.registry.get('memory_source'):
            roots.add(MEMORY_ROOT)
        return roots

    def verified_snapshot(self):
        metadata = json.loads((self.base / 'snapshot.json').read_text())
        if metadata.get('schema_version') != 1:
            raise ValueError('Unsupported snapshot version')
        if metadata.get('registry_sha256') != digest((self.vault / 'bin/skill-sources.json').read_bytes()):
            raise ValueError('Registry differs from snapshot; regenerate before restore')
        modes = metadata.get('file_modes', {})
        if set(modes) != set(metadata['files']):
            raise ValueError('Snapshot permissions missing; regenerate before restore')
        if any(type(mode) is not int or not 0 <= mode <= 0o777 for mode in modes.values()):
            raise ValueError('Invalid snapshot permissions')
        payload = {}
        for key, wanted in metadata['files'].items():
            if Path(key).is_absolute() or '..' in Path(key).parts:
                raise ValueError(f'Unsafe snapshot path: {key}')
            p = self.base / key
            if not p.is_file() or p.is_symlink() or any(parent.is_symlink() for parent in p.parents if parent != self.base):
                raise ValueError(f'Snapshot must contain independent regular files: {key}')
            blob = p.read_bytes()
            if digest(blob) != wanted:
                raise ValueError(f'Snapshot hash mismatch: {key}')
            # Git retains only executable bits; restore privacy modes from the manifest.
            payload[key] = (blob, modes[key])
        validate_payload(payload)
        shared_origin = next(item['id'] for item in self.registry['origins']
                             if item['source'] == self.registry['shared_source'])
        for name in self.registry['shared_skills']:
            if f'{shared_origin}/{name}/SKILL.md' not in payload:
                raise ValueError(f'Missing shared skill in snapshot: {name}')
        existing = set()
        for top in self.mirror_roots():
            root = self.base / top
            if not root.is_dir() or root.is_symlink():
                raise ValueError(f'Missing or linked mirror: {top}')
            for p in root.rglob('*'):
                if p.is_symlink():
                    raise ValueError(f'Symlink in portable snapshot: {p.relative_to(self.base)}')
                if p.is_file() and p.name != '.DS_Store':
                    existing.add(p.relative_to(self.base).as_posix())
        if existing != set(payload):
            raise ValueError('Unmanifested or missing snapshot files: ' + ', '.join(sorted(existing ^ set(payload))[:8]))
        return payload

    def restore(self, apply=False):
        payload = self.verified_snapshot()
        targets = {}
        global_map = {item['mirror']: self.home_path(item['source']) for item in self.registry['global_files']}
        origins = {item['id']: self.home_path(item['source']) for item in self.registry['origins']}
        memroot = self.memory_source()
        for key, content in payload.items():
            if key in global_map:
                target = global_map[key]
            elif key.startswith(MEMORY_ROOT + '/'):
                if memroot is None:
                    raise ValueError(f'Snapshot carries memory but the registry disables it: {key}')
                remainder = key[len(MEMORY_ROOT) + 1:]
                if remainder.startswith('by-project/'):
                    project, remainder = remainder[len('by-project/'):].split('/', 1)
                else:
                    project = self.registry.get('primary_memory_project')
                    if not project:
                        raise ValueError('Snapshot needs primary_memory_project to restore root memory files')
                target = memroot / project / 'memory' / remainder
            else:
                origin, remainder = key.split('/', 1)
                if origin not in origins:
                    raise ValueError(f'Unregistered restore origin: {origin}')
                target = origins[origin] / remainder
            targets[target] = content
        # A parent symlink could otherwise redirect restored data into a project.
        # Detach the top-level managed skill link, backing up the link, before restoring its files.
        linked_parents = set()
        for target in targets:
            for parent in target.parents:
                if parent == self.user_root:
                    break
                if parent.is_symlink():
                    if not any(parent == origin / parent.name for origin in origins.values()):
                        raise ValueError(f'Unmanaged symlink in restore path: {parent}')
                    linked_parents.add(parent)
        if apply:
            for parent in sorted(linked_parents):
                self.backup(parent)
            for target, (blob, mode) in targets.items():
                self.replace_file(target, blob, mode)
            self.links(apply=True)
        return len(targets)

    def check(self):
        pending = self.links()
        if pending:
            raise ValueError('Shared runtime is not linked to canonical sources: ' + ', '.join(pending))
        expected, _ = self.snapshot_payload()
        actual = self.verified_snapshot()
        if expected != actual:
            changed = sorted(k for k in expected.keys() | actual.keys() if expected.get(k) != actual.get(k))
            raise ValueError('Mirror drift: ' + ', '.join(changed[:12]))
        return len(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['link', 'snapshot', 'restore', 'check'])
    parser.add_argument('--vault-root', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--user-root', type=Path, default=Path.home())
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        store = SkillStore(args.vault_root, args.user_root)
        if args.command == 'link':
            result = {'changed_links': store.links(args.apply)}
        elif args.command == 'snapshot':
            changed, count = store.snapshot(args.apply)
            result = {'changed_mirrors': changed, 'files': count}
        elif args.command == 'restore':
            result = {'restore_files': store.restore(args.apply)}
        else:
            result = {'verified_files': store.check()}
        result['mode'] = 'apply' if args.apply and args.command != 'check' else 'read-only'
        if store.backup_root:
            result['backup'] = str(store.backup_root)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
