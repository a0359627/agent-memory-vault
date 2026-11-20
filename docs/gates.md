# Gates — 把不變條件寫成會擋人的東西

清單會被跳過，gate 不會。這頁列出這個 repo 裡每一道 gate：**它檢查什麼、你怎麼跑、它紅了代表什麼。**

兩組人用兩組 gate：

- **你的 vault 日常用的**（bootstrap 出來的 vault 裡就有）：`bin/check-routing.sh`、`bin/consolidate.py`、`bin/scan-state.sh`、`bin/scan_sensitive.py`、一次性的 `bin/migrate_status.py`，以及 `bin/test_*.py` 五組自測。
- **要把東西公開時用的**（只存在這個 starter repo）：`tools/publish_check.py`、`tools/export_public.py`、`bin/gate.sh`、pre-commit hook 與 CI。

---

## 一、vault 日常

### `./bin/check-routing.sh`（＝ `bin/check_vault.py`，唯讀）

**檢查什麼**

- `AGENTS.md`／`CLAUDE.md` 存在，而且真的載入 `AGENT-RULES.md`；`AGENT-RULES.md` 存在。
- `bin/skill-sources.json` 讀得起來；宣告的共用 skill 都有 `SKILL.md`；平台入口連結與來源清單一致；鏡像 hash 對得上。
- 共用 skill 正文**不得含絕對家目錄路徑**（`/Users/`、`/home/`、`C:\Users`）——那種寫法換一台機器就死。
- 舊路由殘留：`bin/deprecated-paths.json` 列出的已淘汰路徑若還出現在 active skill 裡就是 error。
  預設是空陣列 `[]`（不檢查）；退役一個舊知識庫時把它加進去，這條就會替你守著。
  這份 JSON 是**唯一**的舊路由設定來源——沒有另外寫死在程式裡的名單，所以被擋下來時
  一定查得到原因，不想擋就從這份檔案拿掉。
- wiki 連結：`03-wiki/` 與根目錄 `*.md` 裡的雙括號 wikilink 與相對連結目標是否存在、有沒有孤兒頁。
- **被忽略的頁面**（error）：`03-wiki/`、`01-profile/` 裡被 `.gitignore` 擋掉的 `.md`。
- **記憶代謝的 gate**（全部只發 warning），讀 `bin/status-vocab.json`：

  | 檢查 | 什麼情況會 warning |
  |---|---|
  | 生命週期詞彙 | frontmatter 的 `status` 不是 `current`／`superseded`／`contested`／`watchlist`／`stale`／`historical` |
  | 專案／skill 狀態詞彙 | `subject_status` 不在 `bin/status-vocab.json` 的允許清單 |
  | 取代關係 | `status: superseded` 卻沒有 `superseded_by`，或 `superseded_by` 指向不存在的頁；欄位寫成 `superseded-by` |
  | 重驗期限 | `revisit_when` 裡的日期已過（`historical`／`superseded` 的頁不算）；或寫了一個不存在的日期，它永遠不會到期 |
  | skill 卡保鮮 | `current` 的 skill 卡沒有 `verified_at`，或 `verified_at` 超過 180 天 |
  | 頁面年齡 | `03-wiki/` 的 `current` 頁沒有 `updated`／`observed_at`／`verified_at` 任何一個 |
  | 平台專案記憶 | `type: project` 的記憶檔超過 90 天又沒有 `revisit_when`（`memory_source` 是 `null` 時整段跳過） |
  | 來源連結 | `02-raw/`、`04-projects/`、`07-archive/` 底下含 Markdown 的子資料夾，沒有被 `03-wiki/` 或 `01-profile/` 的任何真連結指到 |

  兩個天數門檻也寫在 `bin/status-vocab.json`（`age_limits_days`），要改就改那一份。
  沒有 frontmatter、或 frontmatter 沒有 `status` 的頁（索引、hub）不在檢查範圍。
  欄位值照 YAML 的讀法：成對的引號與行尾的 ` # 註解` 不算值的一部分，所以把 `superseded_by` 的雙括號連結用引號包起來是合法寫法。
  來源連結認兩種：指向資料夾裡某個檔的雙括號連結，或指向資料夾或其中檔案的 Markdown 連結；
  指向資料夾本身的雙括號連結不算。等著被併回的 log 碎片（`log-append-*.md`）不會被報成孤兒頁。

**怎麼跑**

```bash
cd ~/my-vault && ./bin/check-routing.sh
./bin/check-routing.sh --skip-snapshot     # 正在準備快照時，只檢查內容
./bin/check-routing.sh --skip-mirror       # 完全跳過 skill 鏡像相關檢查
```

輸出是 JSON：`errors`、`warnings` 與幾個計數。**有 error 才 exit 1。**

**紅了代表什麼**

- `does not load the shared rules`：兩個入口之一沒指向 `AGENT-RULES.md`，你的 agent 這一側正在裸奔。
- `shared skill body contains an absolute home path`：那支 skill 換機就壞，改成相對寫法或指向 `ROUTING.md`。
- `active route still points to a deprecated path`：某支還在用的 skill 仍指向你已經退役的位置。
- 斷掉的 wikilink：有頁面指向不存在的頁，圖譜破了一個洞。
- `page is excluded by .gitignore`：那一頁在你的磁碟上讀得到，但 `git add` 永遠不會收它，
  所以每一份 clone、每一台新機器上，指向它的連結都是壞的。常見原因是檔名剛好含 `credentials`、`token`
  這類為了擋憑證檔而寫的字樣。**改檔名**，不要為單一頁面開 ignore 例外。
  這一項是 error 而不是 warning，因為只看磁碟的檢查永遠發現不了它：本機全綠，遠端缺頁。

**代謝 gate 黃了代表什麼**

它們是 [`memory-metabolism`](../template/03-wiki/memory-metabolism.md) 那份規範的可執行版本。
黃燈的意思是「這一頁該有人看一眼」，不是「這一頁錯了」：

- `status "…" is not a memory lifecycle value`：你把專案或 skill 的狀態寫進了 `status`。
  把它搬到 `subject_status`，`status` 改回這一頁的生命週期。舊 vault 用 `bin/migrate_status.py` 一次搬完。
  值是 `candidate`／`draft` 時訊息會直接叫你改成 `watchlist`，是 `deprecated` 時叫你改成 `stale`。
- `revisit_when … is overdue`：你當初寫下「到這一天回來重驗」。回去看內容還對不對：
  對就把日期往後挪並更新 `updated`；不對就改內容或標 `stale`。不要只挪日期。
- `current skill card without verified_at`／`older than 180 days`：確認活檔還在、觸發情境還成立，再更新日期。
- `status current without any of updated/observed_at/verified_at`：這一頁自稱現行，卻沒有人能判斷它多舊。
- `not linked from 03-wiki or 01-profile`：那個來源資料夾沒有被任何頁面消化，或者消化它的頁面
  只用反引號寫了路徑。反引號不是連結，圖譜上那個資料夾是一座孤島。

warning 不擋 commit。它們要的是每週有人看一遍——那就是整併的工作（見下方 `bin/consolidate.py` 一節）。

**黃燈不是紅燈。** 全新的 vault 還沒跑過 `sync-to-vault.sh --apply`，沒有 `snapshot.json`、
`shared_skills` 也是空的——這是**起始狀態，不是失敗**，所以鏡像檢查只給 warning。
`STATUS.md` 不存在或超過 48 小時同樣只是 warning。
第一次的建議順序是：先 `skill_sync.py link --apply` 與 `sync-to-vault.sh --apply`，**再**跑 check。

### `python3 bin/consolidate.py` — 每週整併的報告與 log 碎片併回

**預設唯讀。** 不帶參數時印一份 JSON 報告，告訴你這一輪整併該看哪裡：等著併回的 log 碎片、
每輪載入層的行數（`AGENT-RULES.md`、兩個入口檔、平台全域入口與記憶索引；超過 200 行標 `over_budget`）、
上次整併以來改最多的頁與最長的專案卡、Active 區超過 60 天沒動的 open question、遠端還沒併回的分支，
以及當下的代謝 warning。它讀檔、讀 git 中繼資料，不寫任何東西。

`--apply` 只做一件事：把 `03-wiki/log-append-*.md` 裡的條目依日期原文併進 `log.md`，註明出自哪個碎片，
然後刪掉碎片。log 是沒有人會重讀來發現少了什麼的檔案，所以這一步的保證寫得比較死：

- **標題與內文都相同才算已經併過。** 兩則標題一樣、內文不同，兩則都留。
- **內文照原樣進去**，只去掉頭尾的空行；縮排的程式碼區塊不會被壓平。
- **碎片在第一則條目之前還有文字**（frontmatter 與一行 `#` 標題除外）時，整個碎片原樣留著並在報告裡說明，
  不會悄悄少掉那一段。沒有 `## [YYYY-MM-DD]` 標題的碎片、不是 UTF-8 的碎片、符號連結也一樣留著。
- **依日期排**：比 log 裡每一則都舊的條目放在第一則之前，不是接在檔尾。
- 重跑不會重複併入；`log.md` 原本是 CRLF 就寫回 CRLF；沒有新條目時不會動 `log.md` 一個 byte。

```bash
python3 bin/consolidate.py                 # 報告：這次該看哪裡
python3 bin/consolidate.py --since 2026-01-01
python3 bin/consolidate.py --apply         # 只併 log 碎片，其他什麼都不改
```

報告說的是「去哪裡看」，不是「什麼是真的」。標 `stale`、合併兩頁、瘦身專案卡這些判斷，
照 [`vault-consolidation`](../template/03-wiki/vault-consolidation.md) 的流程提案，由人決定。

### `python3 bin/migrate_status.py` — 把舊的單軸 `status` 拆成兩軸（一次性）

給 0.1.x 建立的 vault 用。**預設是真的乾跑**：只讀檔、印出每一頁會怎麼改（`changes_by_page`），不寫任何東西；
`--apply` 才寫，而且只動 frontmatter 區塊裡的行：從結尾的 `---`（或 `...`）起，正文連同換行字元一個 byte 都不碰。
不是 UTF-8 的頁與符號連結會被跳過並列在 `skipped`。重跑是 no-op。

```bash
python3 bin/migrate_status.py              # 看計畫
python3 bin/migrate_status.py --apply      # 照計畫改
./bin/check-routing.sh                     # 改完看 warning 是否歸零
```

舊值原樣搬到 `subject_status`；`status` 依 `bin/status-vocab.json` 的對照表導出
（有 `superseded_by` → `superseded`；凍結的 review／worklog → `historical`；草稿與候選 → `watchlist`；
`deprecated` → `stale`；其餘 → `current`）。報告裡的 `subject_values_not_in_vocabulary`
列出你自己發明過的狀態字：把它們加進詞彙表，或改成既有的字。
**這是機械搬遷，不是判斷**——哪些頁其實已經不可信，要你自己之後標 `stale`。

### `bin/test_*.py` — 五組自測

全部在隔離的暫存目錄跑，**不碰你真正的家目錄**。一次全跑：

```bash
python3 -B -m unittest discover -s bin -p 'test_*.py'
```

| 檔案 | 驗什麼 |
|---|---|
| `test_skill_sync.py` | 同步引擎：唯讀預覽、備份、連結、各來源還原、缺來源與 secret 攔截、記憶專案排除、hash 異常、冪等、「不寫穿 symlink 回到原 repo」 |
| `test_check_vault.py` | 代謝 gate 的每一條 warning 與被忽略頁面的 error，各用一個最小 fixture 證明它會響、也證明合法的寫法不會響 |
| `test_migrate_status.py` | 拆軸：乾跑零寫入、正文不變、重跑 no-op、詞彙外的值會被報出來 |
| `test_scan_state.py` | 活動快照讀對了哪一軸、舊的單軸卡片照常運作、fetch 失敗標成 partial |
| `test_consolidate.py` | log 碎片併回的位置與冪等、報告模式零寫入、載入層行數預算 |

改過 `bin/` 底下任何一支之後一定要跑；紅了就別 `--apply`。

### `python3 bin/scan_sensitive.py .`

**檢查什麼**

提交前的機敏資料掃描：已知的 secret 前綴與賦值型樣式、email、絕對家目錄路徑、
以及「不該出現在可提交檔案裡」的形狀。`tools/bootstrap.py` 會把它複製進你的 vault，
所以它是**你這一側的常駐 gate**，不是只有這個 starter repo 才有。

**怎麼跑**

```bash
cd ~/my-vault && python3 bin/scan_sensitive.py .
```

末行是 `Summary: 0 error(s)` 才算過；**exit 2 代表有發現**（exit 0 乾淨）。
交接包與封裝流程（[`skills/agent-handoff-pack/SKILL.md`](../skills/agent-handoff-pack/SKILL.md) 步驟 5、
[`secrets-with-age.md`](secrets-with-age.md)）都以這一行當放行條件。

**紅了代表什麼**

有東西不該被提交。**先看命中的那一行，不要先想怎麼調鬆樣式**——
掃描器誤報的代價是多讀一行，漏報的代價是永久寫進 git 歷史。

### `./bin/scan-state.sh` → `STATUS.md`

**這是量測，不是語意。** 它掃 `03-wiki/proj-*.md` 每張 project card 的 `source:`，量檔案活動與 git 風險，
生成 `STATUS.md`。它**不**證明 production 正在跑、部署成功或客戶接受了。

生成出來的格式長這樣：

```text
---
title: STATUS — 專案活動與 VCS 快照（腳本生成）
type: generated
generated_at: YYYY-MM-DD HH:MM
generator: bin/scan-state.sh
remote_refs_refreshed: true|false
---

## 🔴 無 Git 備份或 source 非 repo      ← 有問題才出現
## ⚠️ Branch／remote drift              ← 有問題才出現
## 📅 有交期的
## 全表   | 專案 | 記憶狀態 | 專案標籤 | 活動量測 | 最近活動 | 天數 | 最近檔案 | VCS |
```

`remote_refs_refreshed` 有三個值：`false`（沒加 `--fetch`）、`true`、`partial`（有 repo fetch 失敗，
哪一個列在 drift 表裡）。「記憶狀態」是卡片的 `status`，「專案標籤」是 `subject_status`；
0.1.x 的單軸卡片沒有 `subject_status`，腳本會把它的 `status` 當成專案標籤，並在記憶狀態欄標「未拆軸」，
所以舊卡不必先遷移就能照常掃。已經是兩軸寫法、只是沒填 `subject_status` 的卡，專案標籤顯示 `—`。

活動量測的分級：7 天內 🟢 active、30 天內 🟡 slowing、90 天內 🟠 dormant、更久 ⚫️ stale；
專案標籤是 `active`／`production` 但超過 30 天沒有檔案活動時加 ⚠️。
`source:` 空白或不是絕對路徑（例如一句「尚無 repo」）顯示「未設本機 source」，寫了路徑但找不到才是「路徑不存在」。
執行中的程式會一直改寫的檔案（`.env`、資料庫與它的 `-wal`／`-shm` 檔）不算活動，否則一個沒人碰的專案會看起來很忙。

它還會讀每張卡的 `management_scope:` 與 `intent:`（兩行都可省略）：`management_scope: observe-only` 只顯示標記、不把 branch drift 算成你的待辦；`intent: frozen`／`retire`（或 `subject_status` 寫成 `frozen`／`archived`）把活動量測改成「人工定」，不會因為沒有檔案變動就被評成 🟠 dormant／⚫️ stale。欄位與允許值見 [`templates/project-card.md`](templates/project-card.md)；`tests/test_status_vocabulary.py` 守著「範本列得出來的詞，腳本都要有定義好的行為」。
`generated_at` 超過 48 小時，`check_vault.py` 會提醒你重跑——舊快照比沒有快照更會騙人。

`--fetch` 會先更新遠端 refs 再判斷 ahead／behind。沒加就只看本機，別拿它宣稱「已經推上去了」。

### 版控真相：三步查核

「這份資產安全嗎」不能用「它有 .git」回答。有 `.git` 不代表有備份。三步，缺一不可：

```bash
git -C <dir> remote -v                              # ① 有沒有 remote
gh repo list <your-handle> --limit 100              # ② 遠端全貌：這個帳號到底有哪些 repo
git -C <dir> log --all --not --remotes --oneline    # ③ 有沒有還沒推上去的 commit
```

第三步是最多人漏的：`git status` 乾淨不等於東西在雲端。
另外，**本機 main 不是真相**——遠端可能比本機新，操作前先 `git fetch`，並看一眼 `git worktree list`。

---

## 二、發布端

### `tools/publish_check.py` — 三層掃描

三層各自獨立失敗，沒有任何一層可以被靜默跳過。

| 層 | 抓什麼 |
|---|---|
| **L1 secret 樣式** | 常見金鑰前綴（雲端 API key、模型供應商 key、GitHub／Slack token、雲端 OAuth secret、age 私鑰、PEM 私鑰區塊），以及賦值型的 `api_key`／`access_token`／`refresh_token`／`password`／`client_secret`。佔位符白名單（角括號、`example`、`your-`、`changeme`、`redacted`、雙大括號）不誤報。 |
| **L2 識別字封鎖** | 你自己列的禁用識別字（本名各拼法、公司、客戶、網域、帳號、雲端專案、機器名、私有 repo 名、家目錄片段…），以 HMAC-SHA256 存成 `bin/identifier-blocklist.hmac`。**明文清單與 key 都不在 repo 裡。** |
| **L3 結構與形狀** | symlink；`.env*`（只准 `.env.example`）；二進位檔；超過 200 KB 的檔；`/Users/`、`/home/`、`C:\Users` 絕對路徑；email（只放行 `example.com`／`example.org`／`users.noreply.github.com`）；台灣手機格式；UUID v4；真實 IPv4；session id 殘留；物件儲存 URI；內部主機名；雲端專案編號；部署環境變數旗標；frontmatter 的 `source:` 指向絕對路徑；雙大括號佔位符出現在 `template/` 以外；斷掉的 wikilink 與相對連結；`skills/writing-great-skills/LICENSE` 必須存在，且其 sha256 等於 `tools/publish_check.py` 裡 pin 的上游全文雜湊（另檢查含上游版權行）——要更新它必須先確認新的上游 pinned commit，再同步更新 `UPSTREAM_LICENSE_SHA256` 與 `THIRD-PARTY-NOTICES.md`；`THIRD-PARTY-NOTICES.md` 逐項對照表列出的每個衍生 skill 目錄也都必須有可獨立散布的 `NOTICE.md`。 |

**怎麼跑**

```bash
python3 tools/publish_check.py .                       # 掃整棵樹
python3 tools/publish_check.py . --reveal              # 本機有 key 時，把 L2 命中的明文印出來
python3 tools/publish_check.py . --staged              # 只掃 git 暫存區（pre-commit 用的）
git log --all -p | python3 tools/publish_check.py --stdin     # 掃整個歷史（含 commit 作者行）
git remote -v   | python3 tools/publish_check.py --remotes    # 掃遠端 URL
python3 tools/publish_check.py . --no-blocklist        # 明確跳過 L2（見下面 fork PR 政策）
```

**輸出與離開碼**

發現只印 `<LEVEL> <path>:<line> <kind>`，**永不印命中的值**；L2 預設只印 HMAC 的前 8 碼。
最後一行固定是 `L1 <n> / L2 <n> / L3 <n>`，方便腳本取用。

| exit | 意思 |
|---|---|
| `0` | 乾淨 |
| `2` | 有發現 |
| `3` | **設定錯誤**：`bin/identifier-blocklist.hmac` 存在，但拿不到 key。這是 fail-closed，不是誤報。 |

`.hmac` 檔**不存在**（例如你自己的 vault 還沒建清單）時，L2 印一行 WARN 跳過，L1／L3 照跑。
但只要 `.hmac` 在，key 就必須在，否則整支停掉——因為「悄悄少跑一層」正是最貴的那種失敗。

### L2 的已知限制（請當第二道防線，不是第一道）

HMAC 清單只擋**你列過的字**。它抓不到：

- **同音、別稱、暱稱、縮寫、拼音、羅馬拼寫變體**——「同一個人的第七種寫法」不在清單裡就過關；
- **可組合推論的敘述**——沒有一個字命中，但三句話合起來只可能是某一家公司的某一個系統；
- **語意等價的改寫**——把專有名詞換成「我們那套內部工具」仍可能被熟人認出來。

**分隔符號曾經是一個缺口，現在補上了。** 正規化只做 NFKC → 小寫 → 去空白，**不**統一
`-`／`_`／`.`，所以 `foo-bar-baz` 與 `FOO_BAR_BAZ` 本來是兩個完全不同的 HMAC——差一個
分隔符號就繞過 L2，而「剛好沒命中」看起來跟「閘門判斷過」一模一樣。
現在 `tools/build_identifier_blocklist.py` 會替每個帶分隔符號的 token 一併收錄
四種形狀（全 `-`／全 `_`／全 `.`／完全去掉），所以改寫分隔符號不再能繞過。
**大小寫與空白本來就被正規化吃掉，但別的變形（插入字元、換順序）仍然抓不到。**

所以真正的第一道防線是 **allowlist**（只有明確列出的檔案能出去，見下一節），
第二道才是 L2，最後一道是**人眼全文讀**。三道都做，不要只靠掃描器。

**那把 HMAC key 要當長期機密看。** 公開的 `bin/identifier-blocklist.hmac` 一旦進了 git 歷史就永久存在、收不回來，
而它對**當初那把 key** 永遠有效。所以：這把 key 只用於這個用途、不與任何其他系統共用，也不隨 repo 散布。
key 沒外洩時，這份檔案是不可逆的（256-bit key，離線字典攻擊不成立）；key 外洩之後，同一份檔案會回溯性地變成
「這些字在不在清單裡」的查詢器。

**外洩的正確處置是換 key 重生成，不是只輪替 key。** 產生一把新 key、用它重跑 `tools/build_identifier_blocklist.py`、
以新 commit 取代 `bin/identifier-blocklist.hmac`。只換 key 而留著舊檔沒有用——舊檔在 git 歷史裡仍然對舊 key 有效。

**「兩套實作」能擋什麼、不能擋什麼。** `bin/scan_sensitive.py` 是 L1 的第二套實作，
但它跟 `publish_check.py` 的 L1 共用同一批樣式思路，而且 gate 用 `cmp` 強制它與 office kit 的
那一份一字不差——所以它擋得住「某一支被改壞」，擋不住「兩支對同一類輸入同時判錯」。
實際踩過一次：佔位符白名單原本是**整行**判定，於是 `KEY=<真 key>  # example value`
這一行在兩支裡同時被跳過。現在兩支都改成只看命中的那一段，`tests/test_publish_check.py`
也有回歸測試——但這個教訓要記住：兩套實作不等於兩種判斷。

另外，`.hmac` 之所以用 HMAC 而不是無鹽 sha256：無鹽 hash 可以被字典撞出「這份清單裡有 X」，
等於把你的禁用字表換個形式公開。HMAC 讓拿到檔案的人驗不出任何東西。
**key 永遠不進 repo**：本機用環境變數 `IDENTIFIER_BLOCKLIST_KEY_FILE` 指向一個 gitignored 的檔，
CI 用 repository secret 在執行時寫進暫存檔。

清單怎麼建：

```bash
python3 tools/build_identifier_blocklist.py \
    --tokens ~/private/identifier-blocklist.txt \
    --key-file ~/private/hmac.key \
    --out bin/identifier-blocklist.hmac \
    --require-categories person,company,domain,cloud,home_fragment,private_repo
```

`--require-categories` 是這道 gate 的重點：**任何一個必要類別是空的就拒絕生成**。
少了「私有 repo 名」那一類還讓你產出檔案，等於給你一個會過關的假防線。

### `tools/export_public.py` — allowlist 匯出

manifest 是唯一入口。四種模式：`copy`（內容必須等於來源）、`rewrite`（套規則，
**每條規則必須恰好命中 `expect` 次**）、`pinned`（手寫檔，只驗 sha256）、`generate`（工具產物，只驗 sha256）。
另外有全域 `assert_absent` 正則、以及樹檢查：**公開樹裡多一個檔或 manifest 裡少一個檔都是 error**。

紅了代表什麼：

- `expect` 命中 **0 次** → 來源漂移，那條刪改規則已經失效（最危險的一種：你以為改掉了）。
- `expect` 命中 **多於預期** → 規則太寬，可能改到不該改的地方。
- `sha256` 不符 → 有人在規則之外手改了輸出。
- 樹不相等 → 有東西「忘了列」卻已經躺在公開目錄裡。

`--apply` 只寫 `copy` 與 `rewrite`，而且**先整批檢查、任一錯誤一個檔都不寫**。
半套的匯出比完全沒匯出更危險。詳細流程見 [publishing-your-vault.md](publishing-your-vault.md)。

### pre-commit hook

```bash
./tools/install-hooks.sh          # 裝進本 repo 的 .git/hooks（不碰全域設定）
```

它對**暫存區的 blob**跑 `publish_check --staged`，所以 `git add -p` 只加一半也擋得住。
exit 3 時它會明講「最可能是 key 沒設好」——那是 fail-closed，把 key 路徑設好再 commit，
**不要用 `--no-verify` 繞過**。繞過一次，後面每次都會繞過。

### `bin/gate.sh` — 一鍵，任一步非 0 即停

```bash
bin/gate.sh --public                 # CI 也能跑：只用 repo 內就有的東西
bin/gate.sh --public --no-blocklist  # 沒有 HMAC key 時
PRIVATE_DIR=~/private VAULT_DIR=~/my-vault bin/gate.sh --full   # 發布前，本機跑
```

`--public` 依序跑：publish_check 三層 → `bin/scan_sensitive.py`（第二套實作，末行的 error 計數必須是 0）→
`cmp` 確認兩份 `scan_sensitive.py` 一字不差 → 單元測試 → `bin/test_*.py` 五組 vault 工具自測 →
office kit 結構驗證 → smoke（在暫時 HOME 裡跑 bootstrap → install_skills → sync → restore → check）→
`build_references.py --check` → `.hmac` 真的被 git 追蹤 → 掃整個 git 歷史 → 掃 remote URL → 零 symlink →
零 build 產物（`__pycache__`／`.pyc`）。

手動跑 `python3 -m unittest` 會留下 `__pycache__/`，之後跑 gate 前請用 `python3 -B` 跑測試，或先 `find . -name __pycache__ -type d -prune -exec rm -rf {} +`。

`--full` 在上面全部之上再加三件事，都需要私有側的東西在場：

- `export_public.py --check`：逐檔比對 manifest（expect／sha256／樹）。
- `build_references.py --check --source <私有母本> --rules <私有規則檔>`：重新生成並比對。
  改寫規則表跟母本一樣放在私有側——每條 pattern 都是母本的原文，放進公開 repo 就等於把
  要擦掉的字串印在產生器裡，而閘門只掃產物、不掃產生器。
- **canary：對已知有毒的真實檔案跑 L2，每檔命中必須 ≥ 3。**
  要掃哪幾份**由私有側的 canary 清單指定**（`$PRIVATE_DIR/canary-samples.txt`，
  一行一個相對 vault 根的 glob，`#` 開頭是註解；也可以用 `CANARY_LIST` 指到別處）。
  清單不放在公開檔裡是刻意的：一份「這幾頁每頁都至少藏著 3 個識別字」的路徑表，
  沒有值，卻正好替人指路——跟它要防的那類洩漏是同一種。
  這一步在測「掃描器對真實毒物還有效嗎」。它紅了不代表那些檔案有問題，
  代表**你的禁用識別字清單漏了東西**——沒有這一步，L2 可以在清單過期之後永遠綠燈。
  門檻 3 是寫死在 `bin/gate.sh` 裡的常數，**刻意不做成環境變數**：可調的門檻在 canary 一紅時
  就會被調成剛好綠。要改門檻請改那一行並在 commit 說明理由。
  同理，`--full` 會直接拒絕 `--no-blocklist`——跳過 L2 的完整 gate 全部 canary 都是 0 命中，
  綠的話只證明你把測試關掉了。

成功時印 `GATE OK (public)` 或 `GATE OK (full)`。

**兩個特別容易假綠的地方**：

1. `git ls-files --error-unmatch bin/identifier-blocklist.hmac` 這一步看起來多餘，其實不是。
   `.gitignore` 裡任何一條寬鬆規則（例如含 `token` 的萬用字元）都可能把 `.hmac` 吃掉；
   檔案沒進 git → CI 端走「`.hmac` 不存在 → WARN 跳過」分支 → **整層 L2 靜默消失**。
2. 掃歷史那一步需要完整的 clone。淺 clone 下 `git log --all -p` 幾乎沒東西可掃，會給你一個好看的綠燈。
   CI 因此固定 `fetch-depth: 0`。

### CI：`.github/workflows/gate.yml`

push 到 `main` 與所有 pull request 都跑 `bin/gate.sh --public`，Python 3.11，`fetch-depth: 0`。
建議在 GitHub 對 `main` 開 branch protection，把這個 job 設成必過。

**fork PR 的 L2 政策**（這是刻意的取捨，不是漏洞）：

GitHub 不會把 repository secret 給 fork 的 `pull_request` 事件。若什麼都不做，
L2 的 fail-closed 會讓**每一個外部貢獻的 CI 都紅**，而 CONTRIBUTING 又要求 PR 必過 CI——兩條規則互斥。
所以 workflow 這樣處理：

- secret **拿得到**（push、same-repo PR）→ 寫進暫存 key 檔，跑完整的 `bin/gate.sh --public`。
- secret **拿不到**（fork PR）→ 印一則 notice，改跑 `--no-blocklist`：**L1、L3、所有測試照跑，只有 L2 跳過**。

它的意思是：**fork PR 的綠燈不包含識別字檢查**。維護者合併前必須在 same-repo 分支或本機補跑一次完整 gate。
這條寫在這裡，是因為一個「大家都忘了為什麼」的例外，遲早會被當成「本來就不用跑」。

---

## 三、gate 擋不住的事

機械檢查不等於語意正確，更不等於人類接受。這幾件事沒有任何一道 gate 會替你把關：

- **掃描器不保證抓到所有機敏資料。** 上面說過的 L2 限制，加上你沒想到的那一類。
- **可組合推論。** 每個檔案單看都乾淨，合起來指向同一個人或同一家公司。這只有人讀得出來。
- **語意矛盾。** 兩頁對同一件事的狀態描述互相打架，連結全部有效，gate 全綠。
  代謝 gate 只看欄位在不在、詞彙對不對、日期過了沒；一頁標著 `current`、日期很新、內容卻是錯的，它看不出來。
- **個人資料。** secret 樣式只認得金鑰的形狀，認不出個人資料。要把平台記憶鏡像進 vault 之前，
  先用 `memory_exclusions` 把不該收的專案排除在讀取之外（見 [skills-and-sync.md](skills-and-sync.md)）。
- **人類接受。** 測試通過只證明測試通過。實作、測試、提交、合併、部署與人工接受是六件不同的事。

所以最後一道 gate 是人：**發布前把 README、`template/`、`skills/`、`examples/`、`docs/` 全文讀過一遍**，
並找第二個 session 的 agent 以「陌生讀者＋找碴」的角度複核——只給它識別字的**類型**，不給值。
