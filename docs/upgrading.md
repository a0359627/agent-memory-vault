# 從 0.1.x 升級到 0.2.0

0.2.0 改的是**記憶怎麼被維護**，不是資料夾結構：你的 `02-raw/`、`03-wiki/`、`01-profile/` 都留在原地。
這頁給已經用 0.1.x 的 `bootstrap.py` 建過 vault 的人；剛開始用的人直接照 [quickstart](quickstart.md) 走，不必讀這頁。

`bootstrap.py` 不會覆蓋既有 vault（它拒絕非空目錄），所以升級是你自己把檔案帶過去。
八個步驟裡會改到你內容的只有第 3 步，而且它預設是乾跑。

---

## 這一版改了什麼（先看這張表決定要不要升）

| 改了什麼 | 為什麼 | 你會感覺到什麼 |
|---|---|---|
| frontmatter 的 `status` 拆成兩軸 | 專案狀態與「這一頁還算不算數」擠在同一欄，值會無限增生，工具也分不出兩者 | 舊卡片的 `status: production` 會被提醒搬到 `subject_status` |
| 代謝規範變成會響的 gate | 只寫在政策頁的欄位沒有人填 | `./bin/check-routing.sh` 多出幾類 warning |
| 每週整併流程與 `bin/consolidate.py` | 「過期」與「遺忘」沒有排程就不會發生 | 多一頁 `vault-consolidation`、多一支工具 |
| log 碎片 | 多個 session 同時追加 `log.md` 會在檔尾互撞 | `log.md` 被別人改過時改寫 `log-append-*.md` |
| skill 晉升門檻與 `verified_at` | 門檻太鬆會長出一堆沒人用的 skill；沒人驗的舊 skill 會很有把握地做錯 | skill 卡多兩個欄位 |
| 工程紀律從六條變八條，移進 `AGENT-RULES.md` | 規則要跟著 vault 走，不是只寫在 starter 的文件裡 | agent 開工時會讀到 |
| 記憶鏡像可以按專案排除 | secret 掃描只認得金鑰的形狀，認不出個人資料 | `bin/skill-sources.json` 多一個可選欄位 |

不升也不會壞：0.1.x 的 vault 可以繼續用舊的 `bin/`。但新舊不要混搭——
新的 `check_vault.py` 需要 `status-vocab.json`，新的 `consolidate.py` 需要新的 `check_vault.py`。

---

## 步驟

以下假設 starter 在 `~/agent-memory-vault`、你的 vault 在 `~/my-vault`。先確定 vault 的工作樹是乾淨的，
這樣每一步的 diff 都看得清楚：

```bash
cd ~/agent-memory-vault && git pull
cd ~/my-vault && git status --short        # 應該是空的；不是的話先 commit
```

### 1. 更新 `bin/`

```bash
cd ~/my-vault
for f in check_vault.py skill_sync.py scan-state.sh status-vocab.json \
         consolidate.py migrate_status.py \
         test_check_vault.py test_consolidate.py test_migrate_status.py \
         test_scan_state.py test_skill_sync.py; do
  cp ~/agent-memory-vault/bin/"$f" bin/"$f"
done
git diff --stat bin/
```

**不要**複製 `skill-sources.json` 與 `deprecated-paths.json`：那兩份是你的設定，不是工具。
如果你改過 `bin/` 裡的工具，先看 `git diff` 再決定怎麼合。

`status-vocab.json` 這一次是新檔，直接複製。但第 3 步可能會請你把自己的狀態字加進去——加過之後它就是你的設定了：
**之後再升級時先 `diff`、再合併，不要整檔覆蓋**，否則你加的字會消失，warning 會回來。

### 2. 帶入新的規範頁

`03-wiki/vault-consolidation.md` 是全新的頁，直接複製後用編輯器的取代功能把兩個佔位符換掉
（範本裡以雙大括號包著的字樣）：

| 佔位符 | 換成 |
|---|---|
| `TODAY` | 今天的日期，`YYYY-MM-DD` |
| `OWNER` | 你的稱呼 |

佔位符沒換掉不會有任何檢查提醒你，換完自己搜一次雙大括號。

```bash
cp ~/agent-memory-vault/template/03-wiki/vault-consolidation.md 03-wiki/
```

其餘幾份你多半已經改成自己的版本了，所以**不要整檔覆蓋**，對照著把新段落搬進去：

| 檔案 | 要搬的段落 |
|---|---|
| `AGENT-RULES.md` | 「任務範圍與協作」新增的三條；讀寫規範的第 4 條後半、第 7、8 條；整節「共用工程紀律」 |
| `ROUTING.md` | 內部路由表的「skill 草稿」「log 碎片」兩列；表格下方講兩軸與 gate 的那一段；「記憶與偏好」新增的兩段 |
| `03-wiki/memory-metabolism.md` | 欄位清單的 `historical` 與 `subject_status`；「索引原則」一節；提到整併節奏的那一段 |
| `01-profile/03-known-traps.md` | 條目格式的「強制層級」；通則第 5–9 條 |
| `03-wiki/index.md` | 在「方法與規範」加一行連到 `vault-consolidation`（不加的話它會是孤兒頁） |
| `03-wiki/log.md` | 檔頭關於 log 碎片的那一段 |
| `01-profile/README.md` | 「什麼只能當 candidate」那一節的最後一段。舊版教人寫 `status: candidate`，新的 gate 不認這個值 |
| `05-skills-drafts/README.md` | 整節「晉升門檻」，以及晉升路徑第 3 步新增的欄位 |

`ROUTING.md` 還有兩處小的：講 origin `exclude` 的那一句，與檔尾連到 `vault-consolidation` 的連結。
`03-wiki/memory-metabolism.md` 另有一段講平台專案記憶的 `observed_at`／`revisit_when`。
下面這幾份只有說明文字不同，不搬也不會壞：`03-wiki/projects.md`、`03-wiki/skills.md`、`ONBOARDING.md`、
`08-skill-base/README.md`、`.obsidian/app.json`（新的預設把 `08-skill-base/` 排除在圖譜之外）。

**從來沒改過某一份範本的話，整檔覆蓋比對照著搬省事**：複製過去，再把 `OWNER`、`LANG`、`VAULT_NAME`、`TODAY`
四個佔位符換回你的值（你原本的值在舊檔裡，`git diff` 看得到）。

用 `diff` 看最省事，例如：

```bash
diff ~/agent-memory-vault/template/AGENT-RULES.md AGENT-RULES.md
```

範本那一側會有佔位符，那是正常的。

這一步做完先 commit，下一步的 diff 才會只剩遷移造成的變動：

```bash
git add -A && git commit -m "Upgrade vault tooling and rule pages to starter 0.2.0"
```

### 3. 把舊的 `status` 拆成兩軸

```bash
python3 bin/migrate_status.py              # 乾跑：只印計畫，不寫任何檔
```

讀那份計畫。它會把 `03-wiki/` 與 `01-profile/` 裡每一頁的舊 `status` 原樣搬到 `subject_status`，
再依下表填新的 `status`：

| 舊的情況 | 新的 `status` |
|---|---|
| 頁面有 `superseded_by` | `superseded` |
| `type` 是 review／worklog，舊值是 `frozen`／`archived` | `historical` |
| 舊值是 `draft`、`candidate` | `watchlist` |
| 舊值是 `deprecated` | `stale` |
| 其他（`production`、`pilot`、`active`…） | `current` |

計畫看起來對，再套用：

```bash
python3 bin/migrate_status.py --apply
git diff --stat -- 03-wiki 01-profile      # 每個檔只動 frontmatter
```

每個被改的檔會多一行 `subject_status`、改一行 `status`；原本把欄位寫成 `superseded-by` 的頁，
鍵名會順便改成 `superseded_by`。乾跑報告的 `changes_by_page` 逐頁列出這些變動；
`skipped` 列出被跳過的頁（不是 UTF-8，或是符號連結），那幾頁要自己處理。

報告裡的 `subject_values_not_in_vocabulary` 是你自己用過、但詞彙表不認得的狀態字。
兩條路：加進 `bin/status-vocab.json` 的 `subject_status.allowed`，或改成既有的字。

**這一步是機械搬遷，不是判斷。** 它會把所有舊的專案卡都標成 `current`，包括你其實早就不信的那幾張。
搬完之後自己掃一遍：內容不可信的改 `stale`，被別頁取代的改 `superseded` 並填 `superseded_by`。

舊的狀態值不管頁面是什麼型別都會被原樣搬到 `subject_status`，因為工具不替你丟資訊。
概念頁、參考頁這類不是在描述專案或 skill 的頁，那一行 `subject_status` 沒有意義，可以直接刪掉。

skill 卡多看一眼：舊值是 `active` 的卡會變成 `status: current`、`subject_status: active`，接著 gate 會要你補 `verified_at`；
舊值是 `draft` 的卡會變成 `status: watchlist`、`subject_status: draft`，之後晉升時這兩個欄位都要手動改
（`current`／`active`），並補上 `promoted_from`。欄位說明見 [skill 卡範本](templates/skill-card.md)。

### 4. 看 gate 現在說什麼

```bash
./bin/check-routing.sh
python3 -B -m unittest discover -s bin -p 'test_*.py'
```

error 要修。warning 第一次會有一批，常見的四種：

- **`status current without any of updated/observed_at/verified_at`**：補一個日期。
  不知道內容多舊就寫你最後一次確認它的日期；確認不了，它大概該是 `stale`。
- **`current skill card without verified_at`**：打開那支 skill 看一眼，還適用就補上今天的日期。
  範本的 `type` 是 `skill-card`，舊卡寫 `skill` 也認得。
- **`not linked from 03-wiki or 01-profile`**：某個 `02-raw/` 資料夾沒被任何頁面用真連結指到。
  去消化它的那一頁，把反引號路徑改成連結。算數的寫法有兩種：指向資料夾裡某一個檔的雙括號連結
  （例如連到 `<主題>/SOURCE`），或指向資料夾或其中檔案的 Markdown 連結（`[來源](../02-raw/<主題>/)`）。
  指向資料夾本身的雙括號連結不算——那種連結在圖譜工具裡指不到任何頁面。
- **`status "candidate" is not a memory lifecycle value`**：舊範本教過這個寫法。整頁都還是候選就改成 `watchlist`。

每一條 warning 的意思與處理方式見 [gates.md](gates.md)。不必一次清完；它們不擋 commit。

### 5. （可選）記憶鏡像的排除清單

只有把 `bin/skill-sources.json` 的 `memory_source` 打開過的人需要看這一步。
0.1.x 只有 allowlist（`memory_projects`）。現在多一個相反方向的 `memory_exclusions`：

```json
"memory_exclusions": {
  "<專案 id>": "<為什麼不收>"
}
```

列在這裡的專案在讀取任何內容之前就被跳過，決策會記進 `snapshot.json`。
理由欄寫類別就好，不要把要保護的內容寫進去——這份檔案本身會進 git。
它跟 allowlist 怎麼分工、有哪些限制，見 [skills-and-sync.md](skills-and-sync.md) 第五節。

### 6. 更新已經裝過的 starter skill

這一版改了三支 skill 的正文：`obsidian-vault`（多了 `references/status-review.md`，以及真連結與 log 碎片的規則）、
`forge-skill`（晉升門檻）、`agent-handoff-pack`（臨時憑據的交付方式）。
`tools/install_skills.py` 遇到同名目錄一律跳過，所以你手上的會停在舊版，沒有任何工具會提醒你。

```bash
diff -r ~/agent-memory-vault/skills/obsidian-vault ~/.claude/skills/obsidian-vault   # Codex 讀者換成 ~/.agents/skills/
```

你沒改過就整個目錄換掉；改過就對照著合併。三支都看過之後重新同步鏡像：

```bash
./08-skill-base/sync-to-vault.sh --apply && ./bin/check-routing.sh
```

沒裝過這三支的人跳過這一步。

### 7. 排一個每週的整併

照 `03-wiki/vault-consolidation.md` 設定：用你平台的排程功能，或固定一個時段手動跑。
第一次手動跑一輪，確認 `python3 bin/consolidate.py` 的報告讀得懂。

### 8. 收尾

```bash
git add -A && git commit -m "Upgrade vault tooling and rules to starter 0.2.0"
```

在 `03-wiki/log.md` 追加一則 `update`，寫這次升級改了哪些檔、遷移了幾頁、還剩幾條 warning。

---

## 回復

每一步都是一般的檔案修改，`git` 就是回復機制：還沒 commit 用 `git checkout -- <檔案>`，
commit 之後用 `git revert`。`migrate_status.py` 只動 frontmatter，回復後不會留下任何東西。

## 相容性

- `bin/scan-state.sh` 讀 `subject_status`，沒有才退回讀舊的 `status`：遷移前後都能跑。
- `bin/check_vault.py` 找不到 `bin/status-vocab.json` 時會跳過代謝 gate 並發一條 warning，其餘檢查照常。
- `snapshot.json` 的格式沒有變。只有用了 `memory_exclusions` 時才會多一個 `excluded_memory_projects` 欄位。
- `STATUS.md` 的全表多了一欄「記憶狀態」。它是生成檔，重跑 `./bin/scan-state.sh` 即可。
  還沒遷移的單軸卡片在那一欄會顯示「未拆軸」。
