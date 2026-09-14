#!/usr/bin/env bash
# 唯讀：共用規則、來源/鏡像、已知舊路由與 wiki 連結檢查。
set -euo pipefail
VAULT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$VAULT/bin/check_vault.py" "$@"
