#!/usr/bin/env bash
# 唯讀預覽為預設；加 --apply 才建立可遷移快照。
set -euo pipefail
VAULT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$VAULT/bin/skill_sync.py" snapshot "$@"
