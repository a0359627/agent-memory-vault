#!/usr/bin/env bash
# 端到端 smoke：在兩個拋棄式 HOME 走完 建立 → 安裝 skill → 鏡像 → 換機還原 → 檢查 → 代謝工具。
#
# 永遠自己開暫存目錄，不管呼叫端的 HOME 是什麼；真實 HOME 全程零寫入。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/vault-smoke.XXXXXX")"

case "$WORK" in
  "${HOME:-/nonexistent}"/*)
    echo "拒絕執行：暫存目錄 $WORK 落在 HOME 底下" >&2
    exit 1
    ;;
esac

cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

HOME_A="$WORK/home-a"
HOME_B="$WORK/home-b"
mkdir -p "$HOME_A" "$HOME_B"
VAULT="$HOME_A/my-vault"

export HOME="$HOME_A"
export GIT_CONFIG_NOSYSTEM=1
unset XDG_CONFIG_HOME 2>/dev/null || true

green() { printf '\n[%s/6] %s ✓\n' "$1" "$2"; }

echo "工作目錄：$WORK"

python3 "$ROOT/tools/bootstrap.py" "$VAULT" \
  --owner "Sample Owner" --lang zh-TW --vault-name my-vault
green 1 "bootstrap 建立 $VAULT"

python3 "$ROOT/tools/install_skills.py" grill-me --apply \
  --register "$VAULT/bin/skill-sources.json"
test -f "$HOME_A/.claude/skills/grill-me/SKILL.md"
green 2 "install_skills --apply 把 grill-me 裝進暫存 HOME 並登記"

python3 "$VAULT/bin/skill_sync.py" link --apply
test -L "$HOME_A/.agents/skills/grill-me"
"$VAULT/08-skill-base/sync-to-vault.sh" --apply
test -f "$VAULT/08-skill-base/snapshot.json"
green 3 "link --apply 與 sync-to-vault.sh --apply 產出可遷移鏡像"

HOME="$HOME_B" "$VAULT/08-skill-base/restore-from-vault.sh" --apply --user-root "$HOME_B"
test -f "$HOME_B/.claude/skills/grill-me/SKILL.md"
green 4 "restore-from-vault.sh 還原到第二個 HOME"

python3 "$VAULT/bin/check_vault.py"
python3 "$VAULT/bin/check_vault.py" --user-root "$HOME_B"
green 5 "check_vault 在兩個 HOME 都是 0 errors"

# 全新的 vault 必須過得了自己帶的代謝 gate：範本教的寫法若與檢查器對不上，
# 讀者第一次跑檢查就會被自己剛拿到的範本警告。
export PYTHONDONTWRITEBYTECODE=1
python3 "$VAULT/bin/consolidate.py" > "$WORK/report.json"
python3 -c '
import json, sys
report = json.load(open(sys.argv[1]))
keys = ("frontmatter_warnings", "source_link_warnings", "broken_wikilinks", "orphan_wiki_pages")
problems = {key: report[key] for key in keys if report[key]}
if report["injected_layer"]["over_budget"]:
    problems["injected_layer"] = report["injected_layer"]
if problems:
    sys.exit("全新的 vault 不該有這些：" + json.dumps(problems, ensure_ascii=False))
' "$WORK/report.json"

python3 "$VAULT/bin/migrate_status.py" > "$WORK/migrate.json"
grep -q '"pages_to_change": 0' "$WORK/migrate.json"

# log 碎片：寫一個、併回、確認碎片消失，再把 log.md 還原成原樣。
before="$(cd "$VAULT" && git status --porcelain)"
printf -- '---\ntitle: frag\n---\n\n## [2099-01-01] update | smoke 碎片\n\n內容\n' \
  > "$VAULT/03-wiki/log-append-2099-01-01.md"
python3 "$VAULT/bin/consolidate.py" --apply > /dev/null
grep -q '^## \[2099-01-01\] update | smoke 碎片$' "$VAULT/03-wiki/log.md"
test ! -e "$VAULT/03-wiki/log-append-2099-01-01.md"
(cd "$VAULT" && git checkout -q -- 03-wiki/log.md && test "$(git status --porcelain)" = "$before")

(cd "$VAULT" && python3 -m unittest discover -s bin -p 'test_*.py' > "$WORK/bin-tests.log" 2>&1) \
  || { cat "$WORK/bin-tests.log" >&2; exit 1; }
green 6 "新 vault 過得了自己的代謝 gate；整併、拆軸與 bin 自測都能在 vault 內執行"

echo
echo "SMOKE OK"
