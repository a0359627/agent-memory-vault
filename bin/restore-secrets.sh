#!/usr/bin/env bash
# restore-secrets.sh — 新電腦上把加密包解回明文（換機還原用）
#
# 前提：你手上要有 age 私鑰。用 MEMORY_VAULT_AGE_KEY 指定它的路徑，或當第一個參數傳進來。
#       它不在 git 裡（從舊機複製、或密碼管理器裡存的那份）。
#       沒有它 = 解不開，這是設計：唯一的根信任只有這一把。
#
# 用法：cd ~/<your-vault> && MEMORY_VAULT_AGE_KEY=<身分檔路徑> ./bin/restore-secrets.sh
#       或  cd ~/<your-vault> && ./bin/restore-secrets.sh <身分檔路徑>
#
# 環境變數：
#   MEMORY_VAULT_AGE_KEY  age 私鑰路徑（必要，或用第一個參數傳）。
#   VAULT_SECRETS_DIR   本機明文金鑰目錄；設了才會印出可直接照抄的搬檔指令，
#                       沒設就只告訴你要先 export 什麼（見下面 hint()）。
#                       與 bin/seal-secrets.sh 用同一個變數名。
set -euo pipefail
VAULT="$(cd "$(dirname "$0")/.." && pwd)"
BLOB="$VAULT/99-secrets-encrypted/vault-secrets.tar.gz.age"
ID="${1:-${MEMORY_VAULT_AGE_KEY:?請設定 MEMORY_VAULT_AGE_KEY（age 私鑰路徑），或用第一個參數指定}}"
SECRETS_DIR="${VAULT_SECRETS_DIR:-}"

command -v age >/dev/null || { echo "🔴 age 未安裝（macOS: brew install age）"; exit 1; }
[[ -f "$BLOB" ]] || { echo "🔴 找不到加密包 $BLOB"; exit 1; }
[[ -f "$ID" ]]   || { echo "🔴 找不到 age 私鑰 $ID —— 從舊機／密碼管理器取得再跑"; exit 1; }

STAGE=$(mktemp -d)
age -d -i "$ID" "$BLOB" | tar -xzf - -C "$STAGE"

echo "解出的檔案："
find "$STAGE" -type f | sed "s|$STAGE/|   |"
echo
echo "要還原到哪？（不會自動覆蓋，你確認後手動搬）"
if [[ -n "$SECRETS_DIR" ]]; then
  echo "   $SECRETS_DIR/ ← $STAGE/external-secrets/*"
fi
echo "   $VAULT/99-secrets-local/ ← $STAGE/99-secrets-local/*"
echo
echo "範例："
if [[ -n "$SECRETS_DIR" ]]; then
  echo "   mkdir -p $SECRETS_DIR && rsync -a $STAGE/external-secrets/ $SECRETS_DIR/"
else
  # 未設定時不印半成品指令：照抄一段含佔位符的 rsync 只會把檔案搬到一個叫
  # 「<你的本機金鑰目錄>」的資料夾裡。
  echo "   # 這台機器還沒設 VAULT_SECRETS_DIR，所以不印本機金鑰目錄那一行。"
  echo "   # 先 export VAULT_SECRETS_DIR=<你的本機金鑰目錄> 再重跑本腳本，"
  echo "   # 或自己把 $STAGE/external-secrets/ 底下的檔案搬到該目錄。"
fi
echo "   rsync -a $STAGE/99-secrets-local/ $VAULT/99-secrets-local/"
echo "   # 各專案的 .env 再從 99-secrets-local/ 底下複回各專案根目錄"
echo
echo "⚠️ 用完刪掉暫存：rm -rf $STAGE"
