#!/usr/bin/env bash
# 發布閘門。任一步非 0 即停。
#
#   bin/gate.sh [--public]            CI 也能跑：只用 repo 內就有的東西
#   bin/gate.sh --full                本機發布前跑：另外比對私有母本與毒物 canary
#   bin/gate.sh --public --no-blocklist
#                                     沒有 HMAC key 時（例如 fork 的 PR）跳過 L2
#
# --full 需要兩個環境變數：
#   PRIVATE_DIR  私有側設定（manifest.json、plan/references-private.md、
#                plan/references-rules.py、canary-samples.txt）
#   VAULT_DIR    私有 vault（canary 的毒物樣本來源；要掃哪幾份由私有側的
#                canary-samples.txt 指定，公開檔不寫任何私有路徑）
# 以及指向 HMAC key 檔的 IDENTIFIER_BLOCKLIST_KEY_FILE。
set -euo pipefail

# gate 自己會跑好幾支 Python；不關掉 bytecode，跑完就長出一堆 __pycache__，
# 而 .pyc 內嵌編譯當時的絕對路徑（含使用者名稱）。下面有一步會把它們擋成紅燈，
# 所以這裡先讓 gate 不要製造自己要擋的東西。
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MODE="public"
PC_FLAGS=""
# 門檻是常數，不是可調參數。做成環境變數的話，canary 一紅就會有人用 CANARY_MIN=2
# 把它調到剛好綠——那就等於沒有 canary。要改門檻請改這一行並說明理由。
CANARY_MIN=3

for arg in "$@"; do
  case "$arg" in
    --public) MODE="public" ;;
    --full) MODE="full" ;;
    --no-blocklist) PC_FLAGS="--no-blocklist" ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

# --full 是「發布前的最後一道」，跳過 L2 的 --full 是假綠：canary 會全部變 0 命中，
# export/references 也證明不了識別字有被擋。直接拒絕這個組合。
if [ "$MODE" = "full" ] && [ "$PC_FLAGS" = "--no-blocklist" ]; then
  echo "--full 不接受 --no-blocklist：跳過 L2 的完整 gate 沒有意義" >&2
  exit 2
fi

STEP=0
step() {
  STEP=$((STEP + 1))
  printf '\n=== [%02d] %s\n' "$STEP" "$1"
}

in_git_repo() {
  [ -d "$ROOT/.git" ] && git rev-parse --is-inside-work-tree >/dev/null 2>&1
}

# 只取 publish_check 末行 `L1 n / L2 n / L3 n` 的 L2 數字；找不到就回空字串。
l2_hits() {
  { python3 tools/publish_check.py $PC_FLAGS "$1" 2>&1 || true; } \
    | tail -1 | sed -n 's/.*L2 \([0-9][0-9]*\).*/\1/p'
}

canary() {
  local sample="$1" tmp hits
  [ -f "$sample" ] || { echo "canary 樣本不存在：$sample" >&2; return 1; }
  tmp="$(mktemp -d)"
  # publish_check 是在「被掃的那棵樹」裡找 bin/identifier-blocklist.hmac；
  # 不一起搬過去，L2 會走「清單不存在→WARN 跳過」而靜默變成 0 命中。
  if ! (cp "$sample" "$tmp/sample.md" \
        && mkdir -p "$tmp/bin" \
        && cp "$ROOT/bin/identifier-blocklist.hmac" "$tmp/bin/identifier-blocklist.hmac"); then
    rm -rf "$tmp"
    echo "canary 失敗：備不出樣本或缺少 bin/identifier-blocklist.hmac（$sample）" >&2
    return 1
  fi
  hits="$(l2_hits "$tmp")"
  rm -rf "$tmp"
  if [ -z "$hits" ]; then
    echo "canary 失敗：publish_check 沒有回報 L2 計數（$sample）" >&2
    return 1
  fi
  if [ "$hits" -lt "$CANARY_MIN" ]; then
    echo "canary 失敗：$sample 只命中 $hits 個識別字，門檻是 $CANARY_MIN" >&2
    echo "（代表禁用識別字清單漏了東西，掃描器對真實毒物無效）" >&2
    return 1
  fi
  echo "  canary OK：$(basename "$sample") 命中 $hits"
}

run_public() {
  step "publish_check：L1 secret / L2 識別字 / L3 結構"
  python3 tools/publish_check.py $PC_FLAGS .

  step "scan_sensitive：第二套獨立實作"
  # 末行是 `Summary: N error(s), M warning(s)`。這裡刻意錨成 `(^|[^0-9])0 error`：
  # 沒錨定的 `0 error` 會被 `10 error(s)`、`20 error(s)` 滿足。今天有 pipefail 兜著
  # 不會出事，但一個「寫錯卻剛好被別人擋住」的斷言，遲早會變成唯一的那道檢查。
  python3 bin/scan_sensitive.py . | tail -1 | grep -qE '(^|[^0-9])0 error'

  step "兩份 scan_sensitive.py 必須一字不差"
  cmp bin/scan_sensitive.py \
    office-agent-starter-kit/.agents/skills/package-office-handoff/scripts/scan_sensitive.py

  step "單元測試"
  python3 -m unittest discover -s tests -p 'test_*.py'

  step "skill 同步工具自測"
  python3 bin/test_skill_sync.py

  step "office kit 結構驗證"
  python3 office-agent-starter-kit/tools/validate_kit.py

  step "smoke：bootstrap → install_skills → sync → restore → check（全在暫時 HOME）"
  HOME="$(mktemp -d)" tests/smoke.sh

  step "docs/REFERENCES.md 是生成物且不含私有標記"
  python3 tools/build_references.py --out docs/REFERENCES.md --check

  if in_git_repo; then
    step "bin/identifier-blocklist.hmac 必須真的被 git 追蹤"
    if git check-ignore -q bin/identifier-blocklist.hmac; then
      echo "bin/identifier-blocklist.hmac 被 .gitignore 擋住了；L2 會靜默失效" >&2
      exit 1
    fi
    git ls-files --error-unmatch bin/identifier-blocklist.hmac >/dev/null

    if [ "$(git rev-list --count --all)" -ge 1 ]; then
      step "掃整個 git 歷史（需要 fetch-depth: 0）"
      git log --all -p | python3 tools/publish_check.py $PC_FLAGS --stdin
    else
      step "git 歷史：沒有 commit，略過"
    fi

    step "掃 git remote URL"
    git remote -v | python3 tools/publish_check.py $PC_FLAGS --remotes
  else
    step "不在 git repo 內：略過歷史、remote 與 .hmac 追蹤檢查"
  fi

  step "零 symlink"
  if find . -path ./.git -prune -o -type l -print | grep -q .; then
    echo "repo 內不允許 symlink：" >&2
    find . -path ./.git -prune -o -type l -print >&2
    exit 1
  fi

  # CPython 把「編譯當時的來源絕對路徑」寫進 .pyc 的 co_filename，所以每個 .pyc 都帶著
  # 維護者的家目錄與使用者名稱。三層掃描器都把 __pycache__ 當雜訊跳過，.gitignore 只擋
  # git add——tar／zip／rsync 整棵樹照樣把它交出去。所以在這裡擋成紅燈，不是靠自律。
  step "零 build 產物（__pycache__／.pyc）"
  if find . -path ./.git -prune -o \( -name '__pycache__' -o -name '*.pyc' \) -print | grep -q .; then
    echo "工作樹有 __pycache__／.pyc；它們內嵌編譯來源的絕對路徑，先刪掉再跑：" >&2
    find . -path ./.git -prune -o \( -name '__pycache__' -o -name '*.pyc' \) -print >&2
    exit 1
  fi
}

run_full() {
  : "${PRIVATE_DIR:?--full 需要 PRIVATE_DIR（私有側設定目錄）}"
  : "${VAULT_DIR:?--full 需要 VAULT_DIR（私有 vault 根目錄）}"
  [ -f "$PRIVATE_DIR/manifest.json" ] || { echo "找不到 $PRIVATE_DIR/manifest.json" >&2; exit 1; }
  [ -d "$VAULT_DIR" ] || { echo "找不到 $VAULT_DIR" >&2; exit 1; }

  step "export_public --check：逐檔比對 manifest（expect／sha256／樹）"
  python3 tools/export_public.py --manifest "$PRIVATE_DIR/manifest.json" \
    --source "$VAULT_DIR" --out . --check

  step "build_references --check：與私有母本重生成比對"
  [ -f "$PRIVATE_DIR/plan/references-rules.py" ] || {
    echo "找不到 $PRIVATE_DIR/plan/references-rules.py（改寫規則表在私有側）" >&2; exit 1; }
  python3 tools/build_references.py --source "$PRIVATE_DIR/plan/references-private.md" \
    --rules "$PRIVATE_DIR/plan/references-rules.py" \
    --out docs/REFERENCES.md --check

  step "canary：掃描器對已知毒物必須報紅（每檔 L2 ≥ $CANARY_MIN）"
  # 樣本清單本身住在私有側（`$PRIVATE_DIR/canary-samples.txt`，一行一個相對 glob，
  # `#` 開頭是註解）。公開檔裡不寫任何一條私有 vault 的具體路徑：那種清單等於公告
  # 「這幾頁每一頁都至少藏著 N 個識別字」，是沒有值、卻替人指路的那一類洩漏。
  local list="${CANARY_LIST:-$PRIVATE_DIR/canary-samples.txt}"
  [ -f "$list" ] || {
    echo "找不到 canary 樣本清單：$list（一行一個相對 $VAULT_DIR 的 glob）" >&2; exit 1; }
  local found=0 pattern sample
  # 用 fd 3 讀清單：canary 內會跑 python3，佔用 stdin 會把迴圈吃掉半份。
  while IFS= read -r pattern <&3 || [ -n "$pattern" ]; do
    case "$pattern" in ''|'#'*) continue ;; esac
    for sample in "$VAULT_DIR"/$pattern; do
      [ -f "$sample" ] || continue
      canary "$sample"
      found=$((found + 1))
    done
  done 3< "$list"
  if [ "$found" -eq 0 ]; then
    echo "canary 失敗：$list 沒有展開出任何存在的樣本" >&2
    exit 1
  fi
}

run_public
if [ "$MODE" = "full" ]; then
  run_full
fi

printf '\nGATE OK (%s)\n' "$MODE"
