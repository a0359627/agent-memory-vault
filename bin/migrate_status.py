#!/usr/bin/env python3
"""Split a single overloaded frontmatter `status:` into two axes.

status         -> memory lifecycle of the page (bin/status-vocab.json: status.lifecycle)
subject_status -> the old value, kept as written: what the project or skill the page describes is doing

Vaults created by starter 0.1.x wrote project and skill states (`production`, `pilot`, `draft`, …) into
`status`. From 0.2.0 on that field only says whether the page is still the current understanding, and
`bin/check-routing.sh` warns about anything else. This tool does the one-time move.

Default is a true dry run: it reads files, prints the plan as JSON and writes nothing.
`--apply` rewrites lines inside the frontmatter block only. Everything from the closing fence on is written
back byte for byte, line endings included; a page that is not UTF-8, or is a symlink, is skipped and reported.
It also normalises the field spelling `superseded-by:` to `superseded_by:`.

How the lifecycle value is derived (first match wins; the lists live in bin/status-vocab.json):
  1. the page has `superseded_by`                                   -> superseded
  2. a frozen time slice (type review/worklog, old value frozen/…)  -> historical
  3. old value is a draft or candidate                              -> watchlist
  4. old value is deprecated                                        -> stale
  5. anything else                                                  -> current

The result is a starting point, not a judgment: read the plan before applying, and afterwards mark pages
whose content you no longer trust as stale by hand. A mechanical move cannot know that.
"""
import argparse
import json
import re
import sys
from pathlib import Path

FENCES = ('---', '...')


def bare(line):
    """A line without its line ending."""
    return line.rstrip('\r\n')


def ending(line):
    return line[len(bare(line)):]


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


def frontmatter_span(lines):
    """Index of the closing fence when `lines` opens with a frontmatter block, else None.

    The block closes at the first line that is `---` or `...`. Looking for the next `---` anywhere would
    take a horizontal rule in the body for the fence whenever the block is closed with `...`.
    """
    if not lines or bare(lines[0]) != '---':
        return None
    for index in range(1, len(lines)):
        if bare(lines[index]) in FENCES:
            return index
    return None


def field(block, key):
    """Value of a top-level `key:` inside the frontmatter block (already reduced with scalar), or None."""
    for line in block:
        m = re.match(rf'^{re.escape(key)}:(.*)$', bare(line))
        if m:
            return scalar(m.group(1))
    return None


def derive(old, block, rules):
    if field(block, rules['superseded_if_field_present']):
        return 'superseded'
    if (field(block, 'type') or '') in rules['frozen_slice_types'] and old in rules['frozen_slice_values']:
        return 'historical'
    if old in rules['watchlist']:
        return 'watchlist'
    if old in rules['stale']:
        return 'stale'
    return rules['default']


def plan_page(path, vocab):
    """Return None (nothing to do), a {'skipped': reason} record, or a plan carrying the new text."""
    if path.is_symlink():
        return {'file': path.name, 'skipped': 'symlink; not writing through it'}
    try:
        with open(path, encoding='utf-8', newline='') as handle:
            text = handle.read()
    except UnicodeDecodeError:
        return {'file': path.name, 'skipped': 'not UTF-8'}
    lines = text.splitlines(keepends=True)
    close = frontmatter_span(lines)
    if close is None:
        return None
    block = lines[1:close]
    changes = []
    for i, line in enumerate(block):
        if line.startswith('superseded-by:'):
            block[i] = 'superseded_by:' + line[len('superseded-by:'):]
            changes.append('superseded-by -> superseded_by')
    lifecycle = set(vocab['status']['lifecycle'])
    status_idx = next((i for i, line in enumerate(block) if re.match(r'^status:', line)), None)
    old = new = None
    if status_idx is not None and field(block, 'subject_status') is None:
        written = bare(block[status_idx])[len('status:'):].strip()   # exactly what the author wrote
        value = scalar(written)
        # Already a lifecycle word, blank, or an unfilled template placeholder such as `<a | b>`: leave it.
        if value and value not in lifecycle and not value.startswith('<'):
            old = value
            new = derive(value, block, vocab['derive_lifecycle_from_old_status'])
            eol = ending(block[status_idx]) or '\n'
            block[status_idx] = f'status: {new}{eol}'
            block.insert(status_idx + 1, f'subject_status: {written}{eol}')
            changes.append(f'status {old} -> {new}, subject_status {old}')
    if not changes:
        return None
    body = ''.join(lines[close:])               # the closing fence and everything after it: untouched
    new_text = lines[0] + ''.join(block) + body
    if not new_text.endswith(body) or frontmatter_span(new_text.splitlines(keepends=True)) is None:
        raise ValueError(f'{path}: refusing to write, the body would change')
    known = set(vocab['subject_status']['allowed'])
    return {'file': path.name, 'old_status': old, 'status': new, 'changes': changes,
            'subject_status_in_vocabulary': (old in known) if old else None, '_path': path, '_text': new_text}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--vault-root', type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument('--apply', action='store_true', help='write changes (default: dry run, zero side effects)')
    args = ap.parse_args()
    root = args.vault_root.resolve()
    vocab_path = root / 'bin/status-vocab.json'
    if not vocab_path.is_file():
        print(f'missing {vocab_path}; copy bin/status-vocab.json from the starter first', file=sys.stderr)
        return 3
    vocab = json.loads(vocab_path.read_text(encoding='utf-8'))
    pages = sorted((root / '03-wiki').glob('*.md')) + sorted((root / '01-profile').glob('*.md'))
    results = [r for r in (plan_page(page, vocab) for page in pages) if r]
    plans = [r for r in results if 'skipped' not in r]
    skipped = [{'file': r['file'], 'reason': r['skipped']} for r in results if 'skipped' in r]
    if args.apply:
        for p in plans:
            with open(p['_path'], 'w', encoding='utf-8', newline='') as handle:
                handle.write(p['_text'])
    mapping = {}
    for p in plans:
        if p['old_status']:
            mapping.setdefault(f"{p['old_status']} -> {p['status']}", []).append(p['file'])
    unknown = sorted({p['old_status'] for p in plans if p['subject_status_in_vocabulary'] is False})
    print(json.dumps({
        'mode': 'apply' if args.apply else 'dry-run (nothing written)',
        'pages_scanned': len(pages), 'pages_to_change': len(plans),
        'mapping': {k: {'count': len(v), 'pages': v} for k, v in sorted(mapping.items())},
        'changes_by_page': {p['file']: p['changes'] for p in plans},
        'skipped': skipped,
        'subject_values_not_in_vocabulary': unknown,
        'next': ('add those values to subject_status.allowed in bin/status-vocab.json, or rename them'
                 if unknown else 'run ./bin/check-routing.sh'),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
