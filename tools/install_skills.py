#!/usr/bin/env python3
"""Install starter skills into the home skill directory. Preview by default.

絕不覆蓋既有同名目錄：同名就跳過並警告，要換版本請自己先改名或刪掉。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_DEST = {'claude': '~/.claude/skills', 'codex': '~/.agents/skills'}
IGNORE = shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store', '.git')
NAME_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


class InstallError(Exception):
    pass


def available_skills(source: Path) -> list[str]:
    if not source.is_dir():
        raise InstallError(f'找不到 skill 來源目錄：{source}')
    return sorted(p.name for p in source.iterdir()
                  if p.is_dir() and (p / 'SKILL.md').is_file())


def home_path(value: str) -> Path:
    return Path(value).expanduser()


def registry_source(registry_path: Path) -> str:
    data = json.loads(registry_path.read_text(encoding='utf-8'))
    if 'shared_source' not in data:
        raise InstallError(f'{registry_path} 沒有 shared_source 欄位')
    return data['shared_source']


def register(registry_path: Path, names: list[str]) -> list[str]:
    data = json.loads(registry_path.read_text(encoding='utf-8'))
    current = list(data.get('shared_skills', []))
    added = [n for n in names if n not in current]
    if added:
        data['shared_skills'] = sorted(current + added)
        registry_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n',
                                 encoding='utf-8')
    return added


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='把 skills/<name>/ 安裝到你的 home skill 目錄。',
        epilog='範例：python3 tools/install_skills.py grill-me --apply '
               '--register ~/my-vault/bin/skill-sources.json')
    parser.add_argument('names', nargs='*', help='要安裝的 skill；不給就是全部')
    parser.add_argument('--apply', action='store_true', help='真的複製；不給只印預覽')
    parser.add_argument('--dest', default=None, help='安裝目的地；預設依 --platform')
    parser.add_argument('--platform', choices=sorted(PLATFORM_DEST), default='claude',
                        help='claude → ~/.claude/skills；codex → ~/.agents/skills')
    parser.add_argument('--register', default=None, metavar='SKILL_SOURCES_JSON',
                        help='把安裝好的名字加進這份 bin/skill-sources.json 的 shared_skills')
    parser.add_argument('--source', default=None, help='skill 來源目錄；預設為本 repo 的 skills/')
    return parser.parse_args(argv)


def install(args: argparse.Namespace) -> int:
    source = Path(args.source).expanduser().resolve() if args.source else REPO_ROOT / 'skills'
    dest = home_path(args.dest) if args.dest else home_path(PLATFORM_DEST[args.platform])
    dest = dest.resolve() if dest.exists() else dest

    catalogue = available_skills(source)
    if not catalogue:
        raise InstallError(f'{source} 裡沒有任何含 SKILL.md 的目錄')
    names = args.names or catalogue
    unknown = [n for n in names if n not in catalogue]
    if unknown:
        raise InstallError(f'沒有這些 skill：{", ".join(unknown)}；可用的是 {", ".join(catalogue)}')
    bad = [n for n in names if not NAME_RE.fullmatch(n)]
    if bad:
        raise InstallError(f'skill 名稱只允許小寫與連字號：{", ".join(bad)}')

    registry_path = None
    if args.register:
        registry_path = Path(args.register).expanduser().resolve()
        if not registry_path.is_file():
            raise InstallError(f'找不到來源清單：{registry_path}')
        declared = home_path(registry_source(registry_path))
        declared_resolved = declared.resolve() if declared.exists() else declared
        if declared_resolved != dest:
            raise InstallError(
                f'--register 的 shared_source 是 {declared}，但安裝目的地是 {dest}；'
                '兩者必須一致，否則 skill_sync 會找不到正本。')

    print(f'來源：{source}')
    print(f'目的地：{dest}{"" if args.apply else "（預覽，沒有任何寫入）"}')
    installed, present, failed = [], [], []
    for name in names:
        target = dest / name
        if target.exists() or target.is_symlink():
            print(f'  skip   {name}  （目的地已有同名項目，不覆蓋）')
            present.append(name)
            continue
        if not args.apply:
            print(f'  would  {name}')
            installed.append(name)
            continue
        try:
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source / name, target, ignore=IGNORE)
        except OSError as exc:
            print(f'  FAIL   {name}  （{exc}）', file=sys.stderr)
            failed.append(name)
            continue
        print(f'  install {name}')
        installed.append(name)

    if registry_path is not None:
        candidates = sorted(set(installed) | set(present))
        if args.apply:
            added = register(registry_path, candidates)
            print(f'registry：{registry_path} 新增 {len(added)} 個 → {", ".join(added) or "（無）"}')
        else:
            print(f'registry：--apply 時會把 {", ".join(candidates)} 補進 {registry_path}')

    print(f'小計：{len(installed)} 個{"已安裝" if args.apply else "待安裝"}，'
          f'{len(present)} 個因同名而跳過，{len(failed)} 個失敗')
    if not args.apply:
        print('要真的安裝請加 --apply。')
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return install(args)
    except InstallError as exc:
        print(f'錯誤：{exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
