#!/usr/bin/env bash
# seal-secrets.sh — 把所有秘密加密成一個「可進 git」的密文包
#
# 需求是：全部金鑰都能隨 repo 還原。明文進 git 是永久洩漏
# （git 歷史刪不掉、rotation 才是唯一補救），所以改成 age 加密後再進 git。
# 密文（.age）進 git 是安全的；解密只需一把 age 私鑰，那把私鑰**不進 git**——
# 放在只有你知道的本機路徑（或密碼管理器），換電腦時單獨手搬。
#
# 封裝只需要「公鑰」（recipient），所以本腳本預設完全不碰私鑰。
#
# 環境變數（都是可選的）：
#   VAULT_SECRETS_DIR   本機明文金鑰目錄。未設定就只封裝 vault 內的 99-secrets-local/。
#   MEMORY_VAULT_AGE_KEY  age 私鑰路徑。只用在封裝後「解開來數幾個檔」的自我驗證；
#                       未設定就跳過那一步，封裝本身照常完成。
#
# 用法：cd ~/<your-vault> && ./bin/seal-secrets.sh
set -euo pipefail
VAULT="$(cd "$(dirname "$0")/.." && pwd)"
ENC="$VAULT/99-secrets-encrypted"
SECRETS_DIR="${VAULT_SECRETS_DIR:-}"
IDENTITY="${MEMORY_VAULT_AGE_KEY:-}"

command -v age >/dev/null || { echo "🔴 age 未安裝（macOS: brew install age）"; exit 1; }
[[ -f "$ENC/recipient.txt" ]] || { echo "🔴 找不到 $ENC/recipient.txt（內容放一行 age 公鑰）"; exit 1; }
PUB=$(grep -oE 'age1[0-9a-z]+' "$ENC/recipient.txt" | head -n1 || true)
[[ -n "$PUB" ]] || { echo "🔴 $ENC/recipient.txt 裡找不到 age 公鑰"; exit 1; }

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/external-secrets" "$STAGE/99-secrets-local"

# 私鑰永遠不進密文包——否則備份自己就是後門。
# 第一層是檔名排除（便宜，但只認得這個命名慣例）。真正的保險是下面的內容掃描：
# MEMORY_VAULT_AGE_KEY 沒設時這裡只剩 glob，而私鑰的檔名是你自己取的。
EXCLUDES=(--exclude='*age-identity*')
[[ -n "$IDENTITY" ]] && EXCLUDES+=(--exclude="$(basename "$IDENTITY")")

# ① 本機 canonical 金鑰目錄（可選）
if [[ -n "$SECRETS_DIR" && -d "$SECRETS_DIR" ]]; then
  rsync -a "${EXCLUDES[@]}" "$SECRETS_DIR/" "$STAGE/external-secrets/"
fi

# ② vault 的明文秘密區（不含 README 與 .age 自己）
if [[ -d "$VAULT/99-secrets-local" ]]; then
  rsync -a --exclude='README.md' --exclude='*.age' \
    "$VAULT/99-secrets-local/" "$STAGE/99-secrets-local/"
fi

# 第二層：內容判定，fail-closed。檔名排除漏掉的私鑰在這裡被抓住，而且是「整批不封裝」
# 而不是「悄悄排除後繼續」——悄悄排除會讓你以為備份完整，換機時才發現少東西。
if LEAKED=$(grep -rlE 'AGE-SECRET-KEY-1|-----BEGIN [A-Z ]*PRIVATE KEY-----' "$STAGE" 2>/dev/null); then
  echo "🔴 封裝中止：下列檔案含私鑰，密文包不可以帶著能解開自己的鑰匙"
  printf '%s\n' "$LEAKED" | sed "s#^$STAGE/#  #"
  echo "  把它們移出 VAULT_SECRETS_DIR／99-secrets-local/ 之後再跑一次。"
  exit 1
fi

mkdir -p "$ENC"
tar -czf - -C "$STAGE" . | age -r "$PUB" -o "$ENC/vault-secrets.tar.gz.age"

if [[ -n "$IDENTITY" && -f "$IDENTITY" ]]; then
  n=$(age -d -i "$IDENTITY" "$ENC/vault-secrets.tar.gz.age" 2>/dev/null | tar -tzf - | grep -c '[^/]$' || echo '?')
  echo "✓ 已封裝 → $ENC/vault-secrets.tar.gz.age（解開實測 $n 個秘密檔，密文可 commit）"
else
  echo "✓ 已封裝 → $ENC/vault-secrets.tar.gz.age（密文可 commit）"
  echo "  未設定 MEMORY_VAULT_AGE_KEY，略過「解開來數幾個檔」的自我驗證。"
fi
echo "  提醒：git add 99-secrets-encrypted/ 再 commit。明文 99-secrets-local/ 仍被 gitignore。"
