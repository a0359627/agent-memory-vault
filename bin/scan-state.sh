#!/usr/bin/env bash
# scan-state.sh — 量測 project card 的磁碟活動與 Git 風險，生成 STATUS.md。
# 這是 activity/VCS snapshot，不是 production、部署或人類驗收的語意證明。
# 用法：./bin/scan-state.sh [--fetch]
#
# 兩軸（0.2.0 起）：project card 的 `status` 是這一頁的記憶生命週期（current／stale／…），
# `subject_status` 才是專案自己的狀態（production／pilot／frozen／…）。本檔拿 `subject_status`
# 決定怎麼標活動量測；卡片還沒拆軸、只有 `status` 時退回讀它，舊卡不必先遷移就能照常掃。
#
# 可攜性：`stat` 與 `date` 的旗標在 BSD（macOS）與 GNU（Linux）兩家完全不同，
# 所以開頭先探測一次再決定用哪一套；兩家都探不到就**直接停，不寫 STATUS.md**。
# 這是刻意的 fail-closed：前一版寫死 BSD 旗標，在 GNU 上 `stat` 會靜默失敗、
# mtime 退回 0，於是每一列都變成「⚫️ stale ＋ 1970-01-01」——一份看起來正常、
# 內容全錯的快照，比沒有快照更糟。
# 本檔用 bash 3.2 相容語法撰寫（macOS 內建版本），不使用關聯陣列。
set -uo pipefail

# --- 探測 stat／date 的方言（只做一次）-------------------------------------
if stat -c '%Y' . >/dev/null 2>&1; then
  STAT_FLAG='-c'; STAT_FMT='%Y|%n'; DATE_DIALECT='gnu'
elif stat -f '%m' . >/dev/null 2>&1; then
  STAT_FLAG='-f'; STAT_FMT='%m|%N'; DATE_DIALECT='bsd'
else
  echo "scan-state.sh 需要 BSD 或 GNU 的 stat；兩者都偵測不到，不產生 STATUS.md" >&2
  exit 1
fi

# epoch → YYYY-MM-DD；失敗回空字串（呼叫端自己決定怎麼標，不自動編一個日期）。
epoch_to_date() {
  if [[ "$DATE_DIALECT" == gnu ]]; then date -d "@$1" +%Y-%m-%d 2>/dev/null
  else date -r "$1" +%Y-%m-%d 2>/dev/null; fi
}

# YYYY-MM-DD → epoch；失敗回空字串。**不要**退回「今天」：那會把每一個交期
# 都報成剩 0 天，而且沒有任何人會發現。
date_to_epoch() {
  if [[ "$DATE_DIALECT" == gnu ]]; then date -d "$1" +%s 2>/dev/null
  else date -j -f %Y-%m-%d "$1" +%s 2>/dev/null; fi
}

if [[ -z "$(epoch_to_date "$(date +%s)")" || -z "$(date_to_epoch 2026-01-01)" ]]; then
  echo "scan-state.sh：$DATE_DIALECT 版的 date 不吃預期的旗標，不產生 STATUS.md" >&2
  exit 1
fi

VAULT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$VAULT/STATUS.md"
NOW=$(date +%s)
FETCH=0
[[ "${1:-}" == "--fetch" ]] && FETCH=1

DORMANT_DAYS=30
ARCHIVE_DAYS=90

fm() {
  sed -n '2,/^---$/p' "$1" 2>/dev/null | grep -m1 "^$2:" | sed "s/^$2:[[:space:]]*//;s/^\"//;s/\"$//"
}

latest_activity() {
  local src="$1" line
  if [[ -f "$src" ]]; then
    stat "$STAT_FLAG" "$STAT_FMT" "$src" 2>/dev/null
    return
  fi
  line=$(find "$src" \
    \( -name .git -o -name .obsidian -o -name node_modules -o -name .venv -o -name venv -o -name __pycache__ -o -name .cache -o -name .pytest_cache -o -name 99-secrets-local -o -name tokens \) -prune -o \
    \( -name .DS_Store -o -name '.env' -o -name '.env.*' -o -name 'token*' -o -name '*credential*' -o -name '*.db' -o -name '*.db-*' -o -name '*.sqlite' -o -name '*.sqlite-*' -o -name '*.sqlite3' -o -name '*.sqlite3-*' \) -prune -o \
    -type f -exec stat "$STAT_FLAG" "$STAT_FMT" {} + 2>/dev/null | sort -t'|' -k1,1nr | head -n1)
  [[ -n "$line" ]] && echo "$line" || stat "$STAT_FLAG" "$STAT_FMT" "$src" 2>/dev/null
}

# bash 3.2 沒有關聯陣列；用一個以空白分隔的字串當「已 fetch 過的 repo root」集合。
fetched=""
rows=(); nobackup=(); branchrisk=(); duesoon=(); dirty=()
fetch_failures=0

for page in "$VAULT"/03-wiki/proj-*.md; do
  [[ -f "$page" ]] || continue
  name=$(basename "$page" .md); name=${name#proj-}
  src=$(fm "$page" source); src=${src/#\~/$HOME}
  lifecycle=$(fm "$page" status)
  claimed=$(fm "$page" subject_status)
  # 欄位值裡的 `|` 會把下面以 `|` 串接的列與 Markdown 表格一起切壞，先換掉。
  lifecycle=${lifecycle//|/／}; claimed=${claimed//|/／}
  if [[ -z "$claimed" ]]; then
    case "$lifecycle" in
      # 已經是兩軸寫法、只是沒填專案狀態：別把生命週期的字搬去專案欄。
      current|superseded|contested|watchlist|stale|historical|"") ;;
      # 0.1.x 的單軸卡片：`status` 裡放的其實是專案狀態，照舊讀它，並標明還沒拆軸。
      *) claimed="$lifecycle"; lifecycle="未拆軸" ;;
    esac
  fi
  management_scope=$(fm "$page" management_scope)
  intent=$(fm "$page" intent)
  due=$(fm "$page" due)

  if [[ -n "$src" && -e "$src" ]]; then
    activity=$(latest_activity "$src")
    mt=${activity%%|*}; lastfile=${activity#*|}
    # 量不到就說量不到（days=-2），不要退回 mt=0——那會產出「⚫️ stale、1970-01-01」的假資料。
    if [[ -z "$activity" || "$mt" == "$activity" || ! "$mt" =~ ^[0-9]+$ ]]; then
      days=-2; disk="—"; lastrel="—"
    else
      days=$(( (NOW - mt) / 86400 ))
      disk=$(epoch_to_date "$mt"); [[ -n "$disk" ]] || disk="—"
      [[ "$lastfile" == "$src" ]] && lastrel="$(basename "$lastfile")" || lastrel="${lastfile#$src/}"
      lastrel=${lastrel//|/／}
    fi
  else
    days=-1; disk="—"; lastrel="—"
  fi

  vcs="—"
  if [[ -n "$src" && -e "$src" ]] && git -C "$src" rev-parse --git-dir >/dev/null 2>&1; then
    root=$(git -C "$src" rev-parse --show-toplevel 2>/dev/null)
    remote=$(git -C "$root" remote get-url origin 2>/dev/null | sed 's|.*github.com[:/]||;s|\.git$||')
    # 沒有 origin 的 repo 沒有東西可 fetch：那是「無 remote」，下面會標，不算 fetch 失敗。
    if (( FETCH )) && [[ -n "$remote" ]]; then
      case " $fetched " in
        *" $root "*) ;;
        *)
          if ! git -C "$root" fetch --quiet --prune origin 2>/dev/null; then
            branchrisk+=("$name|$root|fetch 失敗；遠端 drift 未更新")
            fetch_failures=$(( fetch_failures + 1 ))
          fi
          fetched="$fetched $root"
          ;;
      esac
    fi

    ncommit=$(git -C "$root" rev-list --count HEAD 2>/dev/null || echo 0)
    cur=$(git -C "$root" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
    changes=$(git -C "$root" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    upstream=$(git -C "$root" rev-parse --abbrev-ref '@{upstream}' 2>/dev/null || true)
    ahead=0; behind=0
    if [[ -n "$upstream" ]]; then
      counts=$(git -C "$root" rev-list --left-right --count "HEAD...@{upstream}" 2>/dev/null || echo "0 0")
      ahead=${counts%%[[:space:]]*}; behind=${counts##*[[:space:]]}
    fi

    dirty_wt=0
    while IFS= read -r wt; do
      [[ -d "$wt" ]] || continue
      [[ -n "$(git -C "$wt" status --porcelain 2>/dev/null)" ]] && dirty_wt=$(( dirty_wt + 1 ))
    done < <(git -C "$root" worktree list --porcelain 2>/dev/null | sed -n 's/^worktree //p')

    if [[ "$ncommit" == "0" || -z "$ncommit" ]]; then
      vcs="🔴 零 commit"; nobackup+=("$name|$src|有 .git 但無 commit")
    elif [[ -z "$remote" ]]; then
      vcs="🔴 無 remote · $cur"; nobackup+=("$name|$src|$ncommit commits 但無 remote")
    else
      vcs="$remote · $cur · ↑$ahead ↓$behind · dirty:$changes · dirty-wt:$dirty_wt"
      if [[ "$management_scope" == "observe-only" || "$claimed" == "observe-only" ]]; then
        vcs="$vcs · observe-only"
      else
        (( ahead > 0 )) && branchrisk+=("$name|$remote|$ahead 個 commit 尚未推送")
        (( behind > 0 )) && branchrisk+=("$name|$remote|本機分支落後 upstream $behind commits")
      fi
    fi
    (( changes > 0 )) && dirty+=("$name|$changes|$dirty_wt")
  elif [[ -n "$src" && -e "$src" ]]; then
    vcs="🔴 非 git repo"; nobackup+=("$name|$src|不是 git repo")
  fi

  # `intent` 是正式欄位；`subject_status` 的 frozen／archived 是範本也列得出來的詞彙，
  # 讓它走同一個分支，範本寫得出來的字腳本就認得（見 docs/templates/project-card.md）。
  if [[ "$intent" == "frozen" || "$intent" == "retire" \
        || "$claimed" == "frozen" || "$claimed" == "archived" || "$claimed" == "archive" ]]; then
    measured="${intent:-$claimed}（人工定）"
  # `source:` 空白或不是絕對路徑（例如一句「尚無 repo」的說明）：沒有東西可量，
  # 這跟「寫了路徑但找不到」是兩件事，不要都報成路徑不存在。
  elif [[ -z "$src" || "$src" != /* ]]; then measured="— 未設本機 source"
  elif (( days == -1 )); then measured="❓ 路徑不存在"
  elif (( days < 0 )); then measured="❓ 活動量測失敗"
  elif (( days <= 7 )); then measured="🟢 active"
  elif (( days <= DORMANT_DAYS )); then measured="🟡 slowing"
  elif (( days <= ARCHIVE_DAYS )); then measured="🟠 dormant"
  else measured="⚫️ stale"
  fi

  flag=""
  if [[ "$claimed" == "production" || "$claimed" == "active" ]]; then
    (( days > DORMANT_DAYS )) && flag=" ⚠️"
  fi

  if [[ -n "$due" ]]; then
    due_epoch=$(date_to_epoch "$due")
    if [[ -n "$due_epoch" ]]; then
      duesoon+=("$due|$name|$(( (due_epoch - NOW) / 86400 ))")
    else
      duesoon+=("$due|$name|❓ 解析不了（due 要寫成 YYYY-MM-DD）")
    fi
  fi
  rows+=("$name|${lifecycle:-—}|${claimed:-—}|$measured$flag|$disk|$days|$lastrel|$vcs")
done

refresh_state=false; refresh_label="未 fetch"
if (( FETCH )); then
  refresh_state=true; refresh_label="已 fetch（限有 origin 的 repo）"
  if (( fetch_failures )); then
    refresh_state=partial; refresh_label="部分 fetch 失敗，見下表"
  fi
fi

{
  echo "---"
  echo "title: STATUS — 專案活動與 VCS 快照（腳本生成）"
  echo "type: generated"
  echo "generated_at: $(date '+%Y-%m-%d %H:%M')"
  echo "generator: bin/scan-state.sh"
  echo "remote_refs_refreshed: $refresh_state"
  echo "---"
  echo
  echo "# STATUS — 專案活動與 VCS 快照"
  echo
  echo "> **本檔只由 \`bin/scan-state.sh\` 生成。** 它量測遞迴檔案活動、branch drift、dirty entries 與 worktrees；"
  echo "> 不證明 production 正在跑、部署成功、資料完整或人類接受。這些語意真相要回 project card／runtime evidence。"
  echo "> 生成於 **$(date '+%Y-%m-%d %H:%M')**；remote refs ${refresh_label}。超過 48 小時先重跑。"
  echo

  if (( ${#nobackup[@]} )); then
    echo "## 🔴 無 Git 備份或 source 非 repo"
    echo
    echo "| 專案 | 路徑 | 問題 |"
    echo "|---|---|---|"
    for r in "${nobackup[@]}"; do IFS='|' read -r a b c <<< "$r"; echo "| $a | \`$b\` | $c |"; done
    echo
  fi

  if (( ${#branchrisk[@]} )); then
    echo "## ⚠️ Branch／remote drift"
    echo
    echo "| 專案 | repo | 問題 |"
    echo "|---|---|---|"
    for r in "${branchrisk[@]}"; do IFS='|' read -r a b c <<< "$r"; echo "| $a | \`$b\` | $c |"; done
    echo
  fi

  if (( ${#duesoon[@]} )); then
    echo "## 📅 有交期的"
    echo
    echo "| 交期 | 專案 | 剩餘天數 |"
    echo "|---|---|---|"
    printf '%s\n' "${duesoon[@]}" | sort | while IFS='|' read -r d n left; do echo "| $d | $n | $left |"; done
    echo
  fi

  echo "## 全表"
  echo
  echo "記憶狀態讀 \`status\`；專案標籤讀 \`subject_status\`。只有一個 \`status\`、裡面放的是專案狀態的舊卡片，記憶狀態欄標「未拆軸」。專案標籤是卡片上最後記下的值，不是本輪查驗的結果。"
  echo "⚠️ 只表示專案標 active／production，但 source 超過 ${DORMANT_DAYS} 天無檔案活動。"
  echo
  echo "| 專案 | 記憶狀態 | 專案標籤 | 活動量測 | 最近活動 | 天數 | 最近檔案 | VCS |"
  echo "|---|---|---|---|---|---|---|---|"
  if (( ${#rows[@]} )); then
    printf '%s\n' "${rows[@]}" | sort -t'|' -k6 -n | while IFS='|' read -r a b c d e f g h; do
      [[ "$f" == -* ]] && f="—"
      echo "| $a | $b | $c | $d | $e | $f | \`$g\` | $h |"
    done
  fi
  echo
  echo "---"
  echo
  echo "回 [[index]]"
} > "$OUT"

echo "✓ 已寫入 $OUT"
echo "  專案 ${#rows[@]} 個｜無 Git 備份/非 repo ${#nobackup[@]}｜branch/remote 風險 ${#branchrisk[@]}｜dirty project ${#dirty[@]}"
