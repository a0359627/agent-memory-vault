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

記憶代謝的 gate（0.2.0 起）讀 `bin/status-vocab.json`，全部只發 warning、不擋寫入：

- frontmatter：`status` 必須是記憶生命週期詞彙、`subject_status` 必須在允許清單內；
  `superseded` 要帶找得到目標的 `superseded_by`；`revisit_when` 裡的日期過了就提醒；
  `current` 的 skill 卡要有夠新的 `verified_at`；`03-wiki/` 的 `current` 頁至少要有一個日期欄位。
- 平台專案記憶：`type: project` 的記憶檔超過期限又沒有 `revisit_when` 就提醒。
  registry 的 `memory_source` 是 null（出廠值）時整段跳過。
- 來源連結：`02-raw/`、`04-projects/`、`07-archive/` 底下每個含 Markdown 的子資料夾，
  都要被 `03-wiki/` 或 `01-profile/` 的真連結指到；反引號裡的路徑不算連結。

唯一的新 error 是 `ignored_pages`：`03-wiki/`、`01-profile/` 裡被 `.gitignore` 擋掉的頁面。
它們在你的磁碟上一切正常，卻永遠進不了 git——只看磁碟的檢查不會發現，所以這一項直接擋。
"""
import argparse
from collections import defaultdict
from datetime import date, datetime
import json
import os
from pathlib import Path
import re
import subprocess
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

# A `current` wiki page with none of these cannot show how old its content is.
DATE_FIELDS = ('updated', 'observed_at', 'verified_at')
# Both spellings exist in the wild: the card template says `skill-card`, older vaults say `skill`.
SKILL_CARD_TYPES = ('skill', 'skill-card')
# A log fragment waits for the weekly pass to merge it; nothing is supposed to link to it meanwhile.
LOG_FRAGMENT_PREFIX = 'log-append-'
# Folders whose sub-folders hold evidence that some wiki page is supposed to have digested.
SOURCE_FOLDERS = ('02-raw', '04-projects', '07-archive')


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
            'orphan_wiki_pages': [p.name for p in wiki_pages
                                  if not backlinks[p] and not p.name.startswith(LOG_FRAGMENT_PREFIX)]}


def frontmatter_lines(text):
    """Return the lines of a leading YAML frontmatter block (without the fences), or None.

    The block opens with `---` on the very first line and closes at the first line that is `---` or `...`.
    Searching for the next `---` anywhere would take a horizontal rule in the body for the closing fence
    whenever the block is closed with `...`, and then read the body as metadata.
    """
    lines = text.split('\n')
    if not lines or lines[0].rstrip('\r') != '---':
        return None
    for index in range(1, len(lines)):
        if lines[index].rstrip('\r') in ('---', '...'):
            return [line.rstrip('\r') for line in lines[1:index]]
    return None


def scalar(value):
    """Reduce a simple YAML scalar to its text: drop matching quotes, or a trailing ` # comment`."""
    value = (value or '').strip()
    if len(value) >= 2 and value[0] in '"\'':
        end = value.find(value[0], 1)
        if end > 0:
            return value[1:end]
    cut = value.find(' #')
    if cut >= 0:
        value = value[:cut].rstrip()
    return value


def parse_frontmatter(text):
    """Return (fields, raw_lines) for a simple YAML frontmatter block; fields are top-level `key: value` only."""
    lines = frontmatter_lines(text)
    if lines is None:
        return None, []
    fields = {}
    for line in lines:
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$', line)
        if m and m.group(1) not in fields:
            fields[m.group(1)] = scalar(m.group(2))
    return fields, lines


ISO_DATE = re.compile(r'(\d{4}-\d{2}-\d{2})')


def first_iso_date(value):
    m = ISO_DATE.search(value or '')
    try:
        return date.fromisoformat(m.group(1)) if m else None
    except ValueError:
        return None


def unparseable_date(value):
    """True when the value contains something shaped like a date that is not a real calendar date."""
    m = ISO_DATE.search(value or '')
    return bool(m) and first_iso_date(value) is None


def load_vocab(root):
    """Return the parsed bin/status-vocab.json, or None when the vault has not adopted it yet."""
    path = root / 'bin/status-vocab.json'
    return json.loads(path.read_text()) if path.is_file() else None


def frontmatter_check(root, vocab, today=None):
    """Memory-metabolism gate: closed status vocabularies, supersession links, overdue revisits, stale skill cards."""
    today = today or date.today()
    lifecycle = set(vocab['status']['lifecycle'])
    subject_ok = set(vocab['subject_status']['allowed'])
    max_skill_age = vocab['age_limits_days']['skill_card_verified_at']
    stems = {p.stem for p in markdown_files(root)}
    warnings = []
    pages = sorted((root / '03-wiki').glob('*.md')) + sorted((root / '01-profile').glob('*.md'))
    for p in pages:
        fields, lines = parse_frontmatter(p.read_text())
        if fields is None:
            continue
        name = p.name
        if any(line.startswith('superseded-by:') for line in lines):
            warnings.append(f'{name}: spell it superseded_by (memory-metabolism), not superseded-by')
        status = fields.get('status')
        if status is not None and status not in lifecycle:
            hints = vocab.get('derive_lifecycle_from_old_status', {})
            if status in hints.get('watchlist', ()):
                advice = 'a page that is still a candidate is status: watchlist'
            elif status in hints.get('stale', ()):
                advice = 'a page that is no longer in use is status: stale (or superseded, with superseded_by)'
            else:
                advice = ('put what the subject is doing in subject_status '
                          '(bin/migrate_status.py previews the split)')
            warnings.append(f'{name}: status "{status}" is not a memory lifecycle value; {advice}')
        subject = fields.get('subject_status')
        if subject is not None and subject not in subject_ok:
            warnings.append(f'{name}: subject_status "{subject}" not in bin/status-vocab.json')
        target = fields.get('superseded_by')
        if status == 'superseded' and not target:
            warnings.append(f'{name}: status superseded without superseded_by')
        if target:
            stem = re.sub(r'^\[\[|\]\]$', '', target).split('|')[0].split('#')[0].strip()
            if Path(stem).stem not in stems:
                warnings.append(f'{name}: superseded_by target "{target}" not found')
        due = first_iso_date(fields.get('revisit_when'))
        if unparseable_date(fields.get('revisit_when')):
            warnings.append(f'{name}: revisit_when has a date that is not a real calendar date; it will never come due')
        if due and due < today and status not in ('historical', 'superseded'):
            warnings.append(f'{name}: revisit_when {due.isoformat()} is overdue; re-verify or mark stale')
        if fields.get('type') in SKILL_CARD_TYPES and status == 'current':
            verified = first_iso_date(fields.get('verified_at'))
            if not verified:
                warnings.append(f'{name}: current skill card without verified_at')
            elif (today - verified).days > max_skill_age:
                warnings.append(f'{name}: verified_at {verified.isoformat()} older than {max_skill_age} days')
        # A page that claims to be the current understanding but carries no date at all cannot be aged by
        # anyone, including the weekly consolidation pass. Warn, do not block.
        if status == 'current' and p.parent.name == '03-wiki' and not any(fields.get(k) for k in DATE_FIELDS):
            warnings.append(f'{name}: status current without any of {"/".join(DATE_FIELDS)}; date it or metabolize it')
    return warnings


def memory_check(memory_dir, vocab, today=None):
    """Platform project-memory gate: project-type memories older than the limit need an explicit revisit_when."""
    today = today or date.today()
    limit = vocab['age_limits_days']['memory_project_without_revisit']
    warnings = []
    if not memory_dir or not memory_dir.is_dir():
        return [f'memory dir not readable: {memory_dir}']
    for p in sorted(memory_dir.glob('*.md')):
        if p.name == 'MEMORY.md':
            continue
        # Fields count only inside the frontmatter (top level or under `metadata:`); a line in the body
        # that happens to read `revisit_when: …` is prose, not a decision to revisit.
        lines = frontmatter_lines(p.read_text())
        if lines is None:
            continue
        meta = {}
        for line in lines:
            m = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$', line)
            if m and m.group(1) not in meta:
                meta[m.group(1)] = scalar(m.group(2))
        if meta.get('type') != 'project':
            continue
        if 'revisit_when' in meta:
            continue
        observed = None
        for key in ('observed_at', 'modified'):
            observed = first_iso_date(meta.get(key))
            if observed:
                break
        observed = observed or date.fromtimestamp(p.stat().st_mtime)
        age = (today - observed).days
        if age > limit:
            warnings.append(f'memory {p.name}: project memory {age} days old without revisit_when')
    return warnings


def source_link_check(root, folders=SOURCE_FOLDERS):
    """Every 02-raw/<topic>, 04-projects/<name> and 07-archive/<name> folder needs a real link from 03-wiki or 01-profile.

    Backtick paths are not links: a graph viewer draws no edge for them, so the folder shows up as an island and
    nothing tells a reader which page digested it. Warn-only.
    """
    warnings = []
    pages = sorted((root / '03-wiki').glob('*.md')) + sorted((root / '01-profile').glob('*.md'))
    candidates = []  # relative path without .md, for every page inside the source folders
    for folder in folders:
        if (root / folder).is_dir():
            candidates.extend(f.relative_to(root).as_posix()[:-3] for f in (root / folder).rglob('*.md'))
    linked_dirs = set()
    for p in pages:
        body = body_without_code(p.read_text())
        for match in re.finditer(r'\[\[([^\]]+)\]\]', body):
            target = match.group(1).split('|')[0].split('#')[0].strip()
            if target.endswith('.md'):
                target = target[:-3]
            if '/' in target:
                hits = [c for c in candidates if c == target or c.endswith('/' + target)]
            else:
                hits = [c for c in candidates if c.rsplit('/', 1)[-1] == target]
                if len(hits) > 1:
                    continue  # a bare stem shared by several folders (SOURCE, README) points at none of them
            for hit in hits:
                linked_dirs.add(tuple(hit.split('/')[:2]))
        for match in re.finditer(r'(?<!!)\[[^\]\n]*\]\(([^)\n]+)\)', body):
            # `[t](<path with spaces>)` and `[t](path "title")` are both legal; reduce them to the path.
            raw = match.group(1).strip()
            raw = raw[1:raw.index('>')] if raw.startswith('<') and '>' in raw else raw.split(' "')[0].split(" '")[0]
            target = unquote(raw.strip().split('#')[0])
            if not target or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                continue
            resolved = (p.parent / target).resolve() if not target.startswith('/') else Path(target)
            try:
                rel = resolved.relative_to(root.resolve())
            except ValueError:
                continue
            if rel.parts and rel.parts[0] in folders and len(rel.parts) >= 2:
                linked_dirs.add(rel.parts[:2])
    for folder in folders:
        base = root / folder
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_dir() or child.name.startswith('.'):
                continue
            if not any(child.rglob('*.md')):
                continue
            if (folder, child.name) not in linked_dirs:
                warnings.append(f'{folder}/{child.name}: not linked from 03-wiki or 01-profile; '
                                'link it from the page that digested it (backtick paths are not links)')
    return warnings


def ignored_pages(root):
    """Wiki/profile pages that exist on disk but .gitignore excludes: they never reach git, links break in every clone."""
    try:
        out = subprocess.run(['git', '-C', str(root), 'ls-files', '--others', '--ignored', '--exclude-standard',
                              '-z', '--', '03-wiki', '01-profile'],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return []
    if out.returncode != 0:
        return []  # not a git work tree: nothing can be ignored
    return [f'{name}: page is excluded by .gitignore and will never be committed; rename it'
            for name in out.stdout.split('\0') if name.endswith('.md')]


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

    errors.extend(ignored_pages(root))
    nav = wiki_check(root)
    errors.extend(nav['broken_wikilinks'])
    warnings.extend(nav['missing_local_links'])
    warnings.extend('Orphan wiki page, nothing links to it: ' + name for name in nav['orphan_wiki_pages'])

    try:
        vocab = load_vocab(root)
    except (ValueError, OSError) as exc:
        vocab = None
        errors.append(f'bin/status-vocab.json is not readable JSON: {exc}')
    else:
        if vocab is None:
            warnings.append('bin/status-vocab.json missing; frontmatter and memory gates skipped '
                            '(copy it from the starter to turn them on)')
    if vocab is not None:
        try:
            warnings.extend(frontmatter_check(root, vocab))
            # memory_source: null is the factory default and means "this vault does not look at platform memory".
            if store is not None and store.registry.get('memory_source'):
                memory_dir = (store.home_path(store.registry['memory_source'])
                              / (store.registry.get('primary_memory_project') or '') / 'memory')
                if not store.registry.get('primary_memory_project') or not memory_dir.is_dir():
                    memory_dir = root / '08-skill-base/claude-memory'
                warnings.extend(memory_check(memory_dir, vocab))
        except (KeyError, TypeError) as exc:
            errors.append(f'bin/status-vocab.json is missing a required key: {exc}')
    warnings.extend(source_link_check(root))

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
                      'scope': 'mechanical checks incl. metabolism gates (warn-only); semantic conflicts require review'},
                     ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
