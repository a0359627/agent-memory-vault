#!/usr/bin/env bash
# 端到端 smoke：在兩個拋棄式 HOME 走完 建立 → 安裝 skill → 鏡像 → 換機還原 → 檢查。
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

green() { printf '\n[%s/5] %s ✓\n' "$1" "$2"; }

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

echo
echo "SMOKE OK"
