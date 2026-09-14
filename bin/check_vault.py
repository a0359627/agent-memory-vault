#!/usr/bin/env python3
"""Read-only checks for shared rule entrypoints, skill sources and wiki navigation.

Mechanical checks cannot establish semantic agreement, production health or user acceptance.

`bin/deprecated-paths.json` 是本檔唯一的「舊路由」設定來源。它是一個 **JSON 陣列**，
預設 `[]`（＝不檢查任何舊路由）。每個元素可以是：

- 字串：要被視為已淘汰的路徑或知識庫名稱，例如 `"old-knowledge-base/"`。
- 物件：`{"path": "<必填，字串>", "negations": ["<可選>", …], "note": "<可選，人看的說明>"}`。
  `negations` 是同一行裡若出現就不算違規的字眼（用來放行「不再…」「歷史…」這類敘述），
  省略時採用預設清單 DEFAULT_NEGATIONS。`note` 不參與判斷。

規則：共用 skill 正文的任何一行只要含 `path` 而該行沒有任何 negation 字眼，就是 error。
輸出只印 skill 名稱與行號，不回印命中的字串（設定檔本身可能是私有詞彙）。
"""
import argparse
from collections import defaultdict
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import unquote

# Must precede the sibling import: a .pyc embeds the absolute source path (and therefore
# the user name) of whoever compiled it, and `./bin/check-routing.sh` runs often enough
# that a stray bin/__pycache__/ would end up inside any folder handed to someone else.
sys.dont_write_bytecode = True

from skill_sync import SkillStore  # noqa: E402


SKIP = {'.git', '.claude', '.obsidian', 'node_modules', '.venv', 'venv', '__pycache__',
        '99-secrets-local', '99-secrets-encrypted', 'tmp'}

# Absolute home paths leak the author's machine into a file meant to be shared.
HOME_PATH_MARKERS = ('/Users/', '/home/', 'C:\\Users')

DEFAULT_NEGATIONS = ('不再', '禁止', '舊版', '歷史', '已淘汰', 'deprecated', 'retired', 'no longer')


def markdown_files(root):
    result = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP]
        result.extend(Path(base) / f for f in files if f.endswith('.md'))
    return result


def body_without_code(text):
    lines, fence = [], None
    for line in text.splitlines():
        mark = re.match(r'^\s*(`{3,}|~{3,})', line)
        if mark:
            if fence is None:
                fence = mark.group(1)[0]
            elif mark.group(1)[0] == fence:
                fence = None
            lines.append('')
        elif fence:
            lines.append('')
        else:
            lines.append(re.sub(r'`+[^`\n]*`+', '', line))
    return '\n'.join(lines)


def deprecated_routes(root):
    """Load bin/deprecated-paths.json; a missing file means 'nothing is deprecated'."""
    source = root / 'bin/deprecated-paths.json'
    if not source.is_file():
        return []
    data = json.loads(source.read_text())
    if not isinstance(data, list):
        raise ValueError('bin/deprecated-paths.json must contain a JSON array')
    entries = []
    for item in data:
        if isinstance(item, str):
            item = {'path': item}
        if not isinstance(item, dict) or not isinstance(item.get('path'), str) or not item['path']:
            raise ValueError('bin/deprecated-paths.json entries need a non-empty "path"')
        negations = item.get('negations')
        if negations is None:
            negations = list(DEFAULT_NEGATIONS)
        if not isinstance(negations, list) or any(not isinstance(n, str) or not n for n in negations):
            raise ValueError('bin/deprecated-paths.json "negations" must be a list of strings')
        entries.append((item['path'], tuple(negations)))
    return entries


def wiki_check(root):
    """Resolve [[wikilinks]] and relative Markdown links in 03-wiki/ and the vault root."""
    stems = defaultdict(list)
    for p in markdown_files(root):
        stems[p.stem].append(p)
    wiki_pages = sorted((root / '03-wiki').glob('*.md'))
    pages = wiki_pages + sorted(root.glob('*.md'))
    backlinks = defaultdict(set)
    broken, local_missing = [], []
    for p in pages:
        body = body_without_code(p.read_text())
        for match in re.finditer(r'\[\[([^\]]+)\]\]', body):
            target = match.group(1).split('|')[0].split('#')[0].strip()
            if not target:
                continue
            candidates = [p.parent / target, root / target]
            resolved = []
            for q in candidates:
                for option in [q, q.with_suffix('.md')] if not q.suffix else [q]:
                    if option.exists():
                        resolved = [option.resolve()]
                        break
                if resolved:
                    break
            if not resolved and '/' not in target:
                resolved = stems.get(Path(target).stem, [])
            if not resolved:
                broken.append(f'{p.name}: {target}')
            for q in resolved:
                if q != p and q.parent == root / '03-wiki':
                    backlinks[q].add(p.name)
        for match in re.finditer(r'(?<!!)\[[^\]\n]*\]\(([^)\n]+)\)', body):
            target = unquote(match.group(1).split(' "')[0].strip('<>').split('#')[0])
            if not target or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                continue
            q = Path(target).expanduser() if target.startswith(('~', '/')) else p.parent / target
            if not q.exists():
                local_missing.append(f'{p.name}: {target}')
    return {'wiki_pages': len(wiki_pages), 'scanned_pages': len(pages),
            'broken_wikilinks': sorted(set(broken)),
            'missing_local_links': sorted(set(local_missing)),
            'orphan_wiki_pages': [p.name for p in wiki_pages if not backlinks[p]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--vault-root', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--user-root', type=Path, default=Path.home())
    parser.add_argument('--skip-snapshot', action='store_true',
                        help='Check content while a snapshot is being prepared')
    parser.add_argument('--skip-mirror', action='store_true',
                        help='Skip every skill-mirror check (links and snapshot)')
    args = parser.parse_args()
    root = args.vault_root.resolve()
    errors, warnings = [], []

    store = None
    try:
        store = SkillStore(root, args.user_root)
    except (ValueError, OSError, KeyError) as exc:
        errors.append(str(exc))

    if store is not None:
        # A fresh vault declares no shared skills and has no snapshot yet; that is a
        # starting state, not a failure. Requiring a mirror here makes the first
        # check red before the reader has run sync once.
        unseeded = not store.registry['shared_skills'] and not (root / '08-skill-base/snapshot.json').is_file()
        bucket = warnings if unseeded else errors
        try:
            if args.skip_mirror:
                warnings.append('Skill mirror checks skipped (--skip-mirror)')
            elif unseeded:
                warnings.append('No shared skills declared and no snapshot yet; '
                                'run 08-skill-base/sync-to-vault.sh --apply once before the mirror check means anything')
                if store.links():
                    warnings.append('Shared runtime links do not match the source registry')
            elif args.skip_snapshot:
                if store.links():
                    bucket.append('Shared runtime links do not match the source registry')
            else:
                store.check()
        except (ValueError, OSError, KeyError) as exc:
            bucket.append(str(exc))

    for entry in ['AGENTS.md', 'CLAUDE.md']:
        path = root / entry
        if not path.is_file():
            errors.append(f'Missing {entry}')
        elif 'AGENT-RULES.md' not in path.read_text():
            errors.append(f'{entry} does not load the shared rules')
    if not (root / 'AGENT-RULES.md').is_file():
        errors.append('Missing common rule source')

    # Known obsolete routes, limited to maintained runtime skills, not frozen evidence.
    if store is not None:
        try:
            routes = deprecated_routes(root)
        except (ValueError, OSError) as exc:
            routes = []
            errors.append(str(exc))
        for name in store.registry['shared_skills']:
            p = store.home_path(store.registry['shared_source']) / name / 'SKILL.md'
            if not p.is_file():
                errors.append(f'{name}: missing canonical SKILL.md')
                continue
            text = p.read_text()
            # No hard-coded route list lives here: an obsolete spelling that only ever
            # applied to one person's history is noise for everyone else, and a check
            # nobody can find in a config file is a check nobody can remove. Put your
            # own retired paths in bin/deprecated-paths.json instead.
            if any(marker in text for marker in HOME_PATH_MARKERS):
                errors.append(f'{name}: shared skill body contains an absolute home path')
            for number, line in enumerate(text.splitlines(), 1):
                for path_token, negations in routes:
                    # Report the location only; the configured token may itself be private.
                    if path_token in line and not any(word in line for word in negations):
                        errors.append(f'{name}:{number}: active route still points to a deprecated path')

    nav = wiki_check(root)
    errors.extend(nav['broken_wikilinks'])
    warnings.extend(nav['missing_local_links'])
    warnings.extend('Orphan wiki page, nothing links to it: ' + name for name in nav['orphan_wiki_pages'])

    status = root / 'STATUS.md'
    if not status.is_file():
        warnings.append('STATUS snapshot missing; run bin/scan-state.sh when activity status is needed')
    else:
        match = re.search(r'^generated_at:\s*(.+)$', status.read_text(), re.M)
        try:
            generated = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M') if match else None
            hours = (datetime.now() - generated).total_seconds() / 3600 if generated else None
            if hours is None or hours > 48:
                warnings.append('STATUS snapshot stale; run bin/scan-state.sh when activity status is needed')
        except ValueError:
            errors.append('Invalid STATUS generated_at')

    print(json.dumps({'errors': errors, 'warnings': warnings, 'wiki_pages': nav['wiki_pages'],
                      'linked_pages_scanned': nav['scanned_pages'],
                      'shared_skills': len(store.registry['shared_skills']) if store else 0,
                      'scope': 'mechanical checks; semantic conflicts require review'},
                     ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
