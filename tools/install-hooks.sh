#!/usr/bin/env bash
# install-hooks.sh — 把 tools/hooks/ 底下的 hook 裝進這個 repo 的 hooks 目錄。
#
# 用法：
#   ./tools/install-hooks.sh          # 安裝；已存在且內容不同時拒絕覆蓋
#   ./tools/install-hooks.sh --force  # 覆蓋既有 hook（會先備份成 <name>.bak）
#
# 只寫入本 repo 的 .git/hooks（或 core.hooksPath 指到的目錄），不碰全域設定。
set -euo pipefail

force=0
for arg in "$@"; do
  case "$arg" in
    --force) force=1 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "未知參數：$arg" >&2; exit 2 ;;
  esac
done

repo_root=$(git rev-parse --show-toplevel)
source_dir="$repo_root/tools/hooks"

if [ ! -d "$source_dir" ]; then
  echo "找不到 $source_dir" >&2
  exit 2
fi

hooks_path=$(git config --get core.hooksPath || true)
if [ -n "$hooks_path" ]; then
  case "$hooks_path" in
    /*) target_dir="$hooks_path" ;;
    *) target_dir="$repo_root/$hooks_path" ;;
  esac
else
  target_dir="$(git rev-parse --git-common-dir)/hooks"
  case "$target_dir" in
    /*) ;;
    *) target_dir="$repo_root/$target_dir" ;;
  esac
fi

mkdir -p "$target_dir"

installed=0
conflicts=0
for hook in "$source_dir"/*; do
  [ -f "$hook" ] || continue
  name=$(basename "$hook")
  target="$target_dir/$name"
  if [ -e "$target" ]; then
    if cmp -s "$hook" "$target"; then
      echo "已是最新：$target"
      continue
    fi
    if [ "$force" -ne 1 ]; then
      echo "已存在且內容不同，未覆蓋：$target（要覆蓋請加 --force）" >&2
      conflicts=$((conflicts + 1))
      continue
    fi
    cp "$target" "$target.bak"
    echo "備份既有 hook → $target.bak"
  fi
  cp "$hook" "$target"
  chmod +x "$target"
  echo "已安裝：$target"
  installed=$((installed + 1))
done

echo "完成（新裝或更新 $installed 個 hook）。"
echo "驗證：在 repo 內 git add 一個檔案後跑 git commit，pre-commit 會先跑 publish_check --staged。"

if [ "$conflicts" -gt 0 ]; then
  echo "有 $conflicts 個 hook 沒裝成（既有內容不同）——這個 repo 現在沒有完整的 pre-commit 防線。" >&2
  exit 1
fi
