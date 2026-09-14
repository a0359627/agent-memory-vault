#!/usr/bin/env bash
# 驗證快照後預覽；加 --apply 才還原，既有衝突檔會先備份。
set -euo pipefail
VAULT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$VAULT/bin/skill_sync.py" restore "$@"
