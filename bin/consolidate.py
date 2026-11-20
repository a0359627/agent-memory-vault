#!/usr/bin/env python3
"""Helper for the periodic consolidation pass (see 03-wiki/vault-consolidation.md).

Default: a read-only report of where a pass should look. It reads the vault, git metadata and the line
counts of the instruction files every session loads; it writes nothing.
--apply: merge 03-wiki/log-append-*.md into log.md and remove the merged fragments. Nothing else is
written; every other change in a pass is made, reviewed and committed by whoever runs it.

What "merge" guarantees, because a log is the one file nobody rereads to notice a loss:
  * an entry counts as already merged only when both its heading and its body are in the log;
    two entries that share a heading but say different things are both kept
  * the body goes in as written (only blank lines at its edges are trimmed)
  * a fragment with text before its first entry is left alone and reported, not silently shortened
  * entries land in date order; one older than everything in the log goes before the first entry

Why fragments exist: when several sessions (or several agents) are working at once, they all want to append
to the same log.md, and the tail of that file is where their edits collide. A session that finds log.md
already modified writes its entry to a new file `03-wiki/log-append-YYYY-MM-DD[-suffix].md` instead; this
tool later puts each entry back in date order, verbatim, with a note of where it came from.
"""
import argparse
from collections import Counter
from datetime import date, timedelta
import json
from pathlib import Path
import re
import subprocess
import sys

# A .pyc embeds the absolute path of whoever compiled it; see the note in check_vault.py.
sys.dont_write_bytecode = True

from check_vault import frontmatter_check, load_vocab, source_link_check, wiki_check  # noqa: E402

ENTRY = re.compile(r'^## \[(\d{4}-\d{2}-\d{2})\] .+$', re.M)
PASS_MARK = '定期整併'          # a pass logs itself as "## [date] lint | 定期整併…"
ORIGIN_NOTE = re.compile(r'\n*（原載碎片 `[^`\n]+`，\d{4}-\d{2}-\d{2} 原文併入。）\s*$')
INJECTED_BUDGET_LINES = 200     # this repo's own soft budget: every session pays for these lines, and a wrong one reaches every session
STALE_QUESTION_DAYS = 60
# Instruction files a session reads before it reads anything you asked for. Vault-relative first,
# then the per-user global entries of the platforms this starter knows about.
VAULT_ENTRIES = ('CLAUDE.md', 'AGENTS.md', 'AGENT-RULES.md')
USER_ENTRIES = ('.claude/CLAUDE.md', '.codex/AGENTS.md')


def trim_blank_lines(text):
    """Drop blank lines at both edges and nothing else: leading indentation is content (a code block)."""
    lines = text.split('\n')
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return '\n'.join(lines)


def entries(text):
    """Split log-style text into (date, heading, body) for each '## [YYYY-MM-DD] …' section."""
    found = list(ENTRY.finditer(text))
    return [(m.group(1), m.group(0),
             trim_blank_lines(text[m.end():(found[i + 1].start() if i + 1 < len(found) else len(text))]))
            for i, m in enumerate(found)]


def fragment_preamble(text):
    """Lines a fragment carries before its first entry, minus what is safe to drop (frontmatter, an H1 title)."""
    first = ENTRY.search(text)
    lines = (text[:first.start()] if first else text).split('\n')
    if lines and lines[0].strip() == '---':
        close = next((i for i in range(1, len(lines)) if lines[i].strip() in ('---', '...')), None)
        if close is not None:
            lines = lines[close + 1:]
    return [line for line in lines if line.strip() and not re.match(r'^# \S', line)]


def read_normalised(path):
    """Return (text with \n newlines, whether the file used \r\n) so a CRLF log is written back as CRLF."""
    with open(path, encoding='utf-8', newline='') as handle:
        raw = handle.read()
    return raw.replace('\r\n', '\n'), '\r\n' in raw


def merge_fragments(root, apply=False, today=None):
    """Put every fragment entry back into log.md in date order. Returns the plan; writes only with apply=True."""
    today = today or date.today()
    log_path = root / '03-wiki/log.md'
    fragments = sorted((root / '03-wiki').glob('log-append-*.md')) if (root / '03-wiki').is_dir() else []

    def keep_all(reason):
        return [{'fragment': frag.name, 'action': f'kept: {reason}'} for frag in fragments]

    if not log_path.is_file():
        return keep_all('03-wiki/log.md not found')
    if log_path.is_symlink():
        return keep_all('03-wiki/log.md is a symlink; not writing through it')
    try:
        log, crlf = read_normalised(log_path)
    except UnicodeDecodeError:
        return keep_all('03-wiki/log.md is not UTF-8')
    # (heading, body) pairs already in the log; the note a previous merge appended is not part of the body.
    known = {(heading, ORIGIN_NOTE.sub('', body)) for _, heading, body in entries(log)}
    plan, done = [], []
    for frag in fragments:
        if frag.is_symlink():
            plan.append({'fragment': frag.name, 'action': 'kept: fragment is a symlink'})
            continue
        try:
            text = frag.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            plan.append({'fragment': frag.name, 'action': 'kept: fragment is not UTF-8'})
            continue
        items = entries(text)
        if not items:
            plan.append({'fragment': frag.name, 'action': 'kept: no "## [YYYY-MM-DD]" entry found'})
            continue
        if fragment_preamble(text):
            plan.append({'fragment': frag.name,
                         'action': 'kept: text before the first entry would be lost; move it into an entry or delete it'})
            continue
        merged, already = [], []
        for when, heading, body in items:
            if (heading, body) in known:
                already.append(heading)
                continue
            note = f'（原載碎片 `{frag.name}`，{today.isoformat()} 原文併入。）'
            block = heading + '\n\n' + (body + '\n\n' if body else '') + note + '\n\n'
            older = [m for m in ENTRY.finditer(log) if m.group(1) <= when]
            if older:
                nxt = ENTRY.search(log, older[-1].end())
                at = nxt.start() if nxt else len(log)
            else:
                # Older than everything in the log: it belongs before the first entry, not at the end,
                # or the entries merged after it would be placed relative to the wrong neighbour.
                first = ENTRY.search(log)
                at = first.start() if first else len(log)
            head = log[:at]
            if head and not head.endswith('\n\n'):
                head = head.rstrip('\n') + '\n\n'
            log = head + block + log[at:]
            known.add((heading, body))
            merged.append(heading)
        plan.append({'fragment': frag.name, 'action': 'merge', 'merged': merged, 'already_in_log': already})
        done.append(frag)
    if apply and done:
        # Rewrite the log only when an entry actually went in: a fragment that held nothing new is
        # removed without touching a byte of log.md.
        if any(item.get('merged') for item in plan):
            log = log.rstrip('\n') + '\n'
            with open(log_path, 'w', encoding='utf-8', newline='') as handle:
                handle.write(log.replace('\n', '\r\n') if crlf else log)
        for frag in done:
            frag.unlink()
    return plan


def git(root, *args):
    try:
        return subprocess.run(['git', '-C', str(root), *args], text=True, capture_output=True, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return ''


def last_pass(root):
    log_path = root / '03-wiki/log.md'
    if not log_path.is_file():
        return None
    marks = [when for when, heading, _ in entries(log_path.read_text()) if PASS_MARK in heading]
    return max(marks) if marks else None


def injected_layer(root, user_root):
    """Line counts of the instruction files every session loads. Reads the files, reports numbers only."""
    files = {name: root / name for name in VAULT_ENTRIES}
    files.update({'~/' + name: user_root / name for name in USER_ENTRIES})
    registry_path = root / 'bin/skill-sources.json'
    registry = json.loads(registry_path.read_text()) if registry_path.is_file() else {}
    if registry.get('memory_source') and registry.get('primary_memory_project'):
        source = registry['memory_source']
        memory_root = (user_root / source[2:]) if source.startswith('~/') else Path(source)
        files['platform memory index'] = memory_root / registry['primary_memory_project'] / 'memory/MEMORY.md'
    lines = {name: len(p.read_text().splitlines()) for name, p in files.items() if p.is_file()}
    total = sum(lines.values())
    return {'lines': lines, 'total_lines': total, 'budget_lines': INJECTED_BUDGET_LINES,
            'over_budget': total > INJECTED_BUDGET_LINES}


def stale_questions(root, today):
    path = root / '03-wiki/open-questions.md'
    if not path.is_file():
        return []
    active = path.read_text().split('## Active', 1)[-1].split('\n## ', 1)[0]
    out = []
    for block in re.split(r'^### ', active, flags=re.M)[1:]:
        seen = re.search(r'Seen：(\d{4}-\d{2}-\d{2})', block)
        if seen and (today - date.fromisoformat(seen.group(1))).days > STALE_QUESTION_DAYS:
            out.append({'id': block.split('：', 1)[0].strip(), 'seen': seen.group(1)})
    return out


def default_branch(root):
    head = git(root, 'symbolic-ref', '--quiet', '--short', 'refs/remotes/origin/HEAD').strip()
    if head:
        return head
    for candidate in ('origin/main', 'origin/master'):
        if git(root, 'rev-parse', '--verify', '--quiet', candidate).strip():
            return candidate
    return None


def unmerged_branches(root):
    base = default_branch(root)
    if not base:
        return []
    out = []
    for line in git(root, 'for-each-ref', '--format=%(refname:short) %(committerdate:short)',
                    'refs/remotes/origin').splitlines():
        ref, _, when = line.partition(' ')
        if ref in (base, 'origin') or ref.endswith('/HEAD'):
            continue
        ahead = git(root, 'rev-list', '--count', f'{base}..{ref}').strip()
        if ahead not in ('', '0'):
            out.append({'branch': ref, 'ahead': int(ahead), 'last_commit': when})
    return out


def report(root, user_root, since=None, today=None):
    today = today or date.today()
    since = since or last_pass(root) or (today - timedelta(days=14)).isoformat()
    churn = Counter(line for line in git(root, 'log', f'--since={since}', '--format=', '--name-only', '--',
                                         '03-wiki', '01-profile').splitlines() if line.endswith('.md'))
    cards = sorted(((len(p.read_text()), p.name) for p in (root / '03-wiki').glob('proj-*.md')), reverse=True)[:5]
    nav = wiki_check(root)
    vocab = load_vocab(root)
    return {
        'since': since,
        'pending_fragments': merge_fragments(root, today=today),
        'injected_layer': injected_layer(root, user_root),
        'changed_pages': len(churn),
        'most_changed': [{'page': name, 'commits': n} for name, n in churn.most_common(8)],
        'largest_project_cards': [{'page': name, 'chars': size, 'commits_since': churn.get(f'03-wiki/{name}', 0)}
                                  for size, name in cards],
        'stale_open_questions': stale_questions(root, today),
        'unmerged_remote_branches': unmerged_branches(root),
        'broken_wikilinks': nav['broken_wikilinks'],
        'orphan_wiki_pages': nav['orphan_wiki_pages'],
        'frontmatter_warnings': (frontmatter_check(root, vocab, today) if vocab
                                 else ['bin/status-vocab.json missing; frontmatter gate skipped']),
        'source_link_warnings': source_link_check(root),
        'scope': 'where to look, not what is true; semantic judgments belong to the pass and its reviewer',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--vault-root', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--user-root', type=Path, default=Path.home())
    parser.add_argument('--since', help='YYYY-MM-DD; default is the last logged pass, else 14 days ago')
    parser.add_argument('--apply', action='store_true', help='merge log fragments into log.md and remove them')
    args = parser.parse_args()
    root = args.vault_root.resolve()
    if args.apply:
        out = {'merged_fragments': merge_fragments(root, apply=True)}
    else:
        out = report(root, args.user_root, args.since)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
