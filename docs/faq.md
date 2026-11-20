# FAQ

---

### 這跟 agent 平台內建的記憶功能有什麼不同？

不同層，不是替代品。平台記憶是**短期指標與單次 correction**，由平台自動寫入、格式由平台決定、
不進你的版本控制。這個 vault 是 **canonical**：git-backed、有 diff、可 review、換機器帶得走。

一條規則就夠：**永久偏好的 canonical 永遠在 `01-profile/`**，平台記憶只放短期修正和「指回 canonical」的指標。
兩份會分岔的永久偏好遲早不一致，而且沒人會收到通知。分工細節見
[walkthrough-first-ingest.md](walkthrough-first-ingest.md) 最後一節。

---

### 我不用 Obsidian，可以嗎？

可以。Obsidian 在這裡只是**可選的唯讀圖譜檢視器**。沒有它，
從 `03-wiki/index.md` 點連結一樣能逛完整個庫——那頁本來就是為了「沒有圖譜也能走」而寫的。
`.obsidian/` 設定隨 template 走，你想用的時候 Open folder as vault 就行。

---

### Windows 可以用嗎？

**走 WSL。** `bin/` 裡是 bash 腳本，`skill_sync.py link` 建的是符號連結，
這兩件事在 Windows 原生環境不成立。與其給你一個沒測過的相容層，不如講清楚：
支援 macOS 與 Linux；Windows 請在 WSL 裡跑，路徑也用 WSL 這一側的。

---

### 需要 `pip install` 什麼嗎？

不需要。全部是 Python 3 標準庫與 bash，**零第三方依賴**。下限是 Python 3.11——CI 只跑 3.11，所以低於這個版本不會有任何 gate 幫你擋住破功，別當成有被測過。
這是刻意的：一個要活五年的記憶庫，不該因為某個套件停止維護就打不開。

---

### `office-agent-starter-kit/` 是什麼？我該用嗎？

它是**給 Codex 讀者的辦公室 agent 教學包**：六支 skill、練習、虛構 fixtures、
以及一支結構驗證器。路徑慣例是 `.agents/skills/`，跟 `skills/` 那八支**不一樣**，
**不要**用 `tools/install_skills.py` 去裝它裡面的東西。

- 你用 Codex：它是完整的一堂課，從 `START-HERE.md` 開始。
  裡面的 `create_skill.py` 與 `validate_skill.py` 也可以直接拿來當你寫新 skill 的鷹架。
- 你用 Claude Code：當**閱讀材料**看，特別是「Prompt／規則檔／Skill／工具各做什麼」那一節。
  要真的裝 skill，用 `skills/` 那八支。

---

### 我用 Codex，不是 Claude Code，這套還成立嗎？

成立。`AGENTS.md` 與 `CLAUDE.md` 都只負責載入同一份 `AGENT-RULES.md`，規範只有一份。
bootstrap 時加 `--platform codex`，`bin/skill-sources.json` 的
來源與 runtime 路徑就會指向 Codex 這一側；安裝 skill 時也加 `--platform codex`。

兩邊都用的話可以 bootstrap `--platform both`，但要知道它的 `shared_source` 仍然是
Claude 側（`~/.claude/skills`）——**正本在那裡，Codex 側是鏡像**。所以 `both` 的 vault
安裝 skill 請用 `--platform claude`；`--platform codex` 搭 `--register` 會因為
「來源清單宣告的位置 ≠ 安裝目的地」而被安裝器擋下，這是刻意的，免得 `skill_sync` 之後找不到正本。

---

### `bootstrap.py` 會動我的 `~/.claude` 嗎？

**不會。** 它只寫 `<target>`（以及 `--with-sample` 的 `<target>-sample`），
不碰 `~/.claude`、`~/.codex`、`~/.agents`，不下載任何東西。
要裝 skill 到 home 是另一個明確的動作（`tools/install_skills.py --apply`），而且預設只預覽。

---

### 第一次跑 `check-routing.sh` 有一堆 warning，是壞了嗎？

沒有。warning 分兩類，處理方式不同：

- **起始狀態**：還沒同步過 skill 鏡像（沒有 `snapshot.json`、`shared_skills` 是空的）、還沒有 `STATUS.md`。
  剛 bootstrap 的 vault 就只有這兩條。先 `python3 bin/skill_sync.py link --apply`、
  再 `./08-skill-base/sync-to-vault.sh --apply`，**然後**才 check；`STATUS.md` 跑一次 `./bin/scan-state.sh` 就有。
- **代謝類**：詞彙外的 `status`、`current` 頁沒有日期、`revisit_when` 過期、skill 卡缺 `verified_at`、
  來源資料夾沒被真連結指到。全新的 vault 一條都沒有，出現了就是某一頁該有人看——當場修，或留給每週整併。
  從 0.1.x 升上來的 vault 第一次會冒出一批，處理順序見 [upgrading.md](upgrading.md) 第 4 步。

**只有 `errors` 非空才會 exit 1。** 每一條的意思見 [gates.md](gates.md)。

---

### 我用 0.1.x 建的 vault 怎麼升級？

不要重跑 bootstrap，它拒絕非空目錄。照 [upgrading.md](upgrading.md) 把新的 `bin/` 與規範段落帶過去，
再用 `bin/migrate_status.py` 拆舊的 `status`（預設乾跑）。資料夾結構沒有變。

---

### 為什麼 `status` 要拆成兩個欄位？

因為它在回答兩個問題。`status` 只講「這一頁的理解還算不算數」，`subject_status` 講「頁面描述的專案或 skill 做到哪」。
擠在同一欄時，「專案已封存、但這張卡仍然正確」和「這張卡已經不可信」寫起來一模一樣，工具也分不出來。
完整的理由在 [concepts.md](concepts.md) 第 4 節。

---

### warning 會不會擋我 commit？

不會。bootstrap 不替你的 vault 裝任何 hook，`check-routing.sh` 也只在有 error 時 exit 1。
代謝 gate 刻意只發 warning：它判斷不了一頁對不對，只能讓該看的東西被看見。
唯一會變紅的新項目是被 `.gitignore` 擋掉的 wiki 頁——那不是判斷題，那一頁就是進不了 git。

---

### 每週整併一定要排程嗎？

不一定。用平台的排程功能或固定一個時段手動跑都行；庫還小、也沒有多個 session 同時在寫時，改成每月一次也可以。
要緊的是**寫下你選的頻率**，不要留白：沒有節奏的「過期」與「遺忘」只是政策頁上的字。
流程在 vault 的 `03-wiki/vault-consolidation.md`。

---

### 兩個 agent（或兩個 session）同時寫同一個庫會怎樣？

最常撞的是 `log.md` 的檔尾。規則是：一個任務只有一個整合者；寫入前先看有沒有別人還沒提交的修改，
有的話不要疊上去，log 條目改寫成 `03-wiki/log-append-YYYY-MM-DD.md`，由下一輪整併的
`python3 bin/consolidate.py --apply` 依日期原文併回。其餘幾條見 [concepts.md](concepts.md) 第 6 節。

---

### `install_skills.py` 會覆蓋我現有的 skill 嗎？

不會，一次也不會。遇到同名目錄就**跳過並警告**。
要換版本請自己先把舊的移走——這是刻意設計成「絕不自作主張」的，
因為被悄悄覆蓋掉的自訂 skill 是你事後最難發現的損失。

---

### 為什麼 `memory_source` 預設是 `null`？

因為打開它而不加 allowlist，同步器會把這台機器上**每一個**專案的記憶都吸進你的 vault，
連同那些由專案絕對路徑編成的目錄 id。要打開就同時設 `memory_projects` 白名單；
有幾個專案的記憶絕對不能收，再加 `memory_exclusions`。做法見 [skills-and-sync.md](skills-and-sync.md)。

---

### 範例 vault 可以刪嗎？

可以，而且它本來就不在你的主 vault 裡。`--with-sample` 會把它複製到 `<target>-sample/`，
逛完整個刪掉即可，不影響任何東西。

---

### 我已經有一個舊知識庫，要整包搬進來嗎？

**不要。** 舊庫當**歷史證據**用：可以追溯、可以按需萃取，但不再寫新東西進去，
也不再當成 current——特別是動態的事實（版本、價格、API、狀態、路徑）一律回當前環境重驗。

做兩件事：把它加進 `bin/deprecated-paths.json`，讓 `check_vault.py` 幫你擋住「還在指向舊位置」的 skill；
再用 [docs/templates/legacy-kb-bridge.md](templates/legacy-kb-bridge.md) 寫一張橋接卡，
寫清楚它**仍可作什麼、不可再怎麼用**。

---

### `log.md` 只能追加，那我發現寫錯了怎麼辦？

append-only 的意思是**不改寫歷史**，不是「寫完就不能修正」。
狀態改變時做兩件事，兩件都不動歷史：另寫一則 `supersede` 追加在**檔尾**，再回到原本那則加一行指向新的那則。
歷史那一段原樣保留（見 `template/03-wiki/log.md` 末兩行）。

**現況本身不住在 log 裡。** log 是流水，只回答「什麼時候發生了什麼」；「現在到底怎麼算」的 canonical 位置是該主題自己的頁
——project card 的「現行有效的決策」區、或對應的 wiki 頁。把現況只寫在 log 而不更新那一頁，下一個人（或 agent）會讀到過期的理解，
**過期的狀態描述冒充現況，比完全沒寫還糟**。

---

### CI 在 fork PR 上跳過識別字檢查，這不是漏洞嗎？

是刻意的取捨，而且寫在 [gates.md](gates.md) 裡。GitHub 不把 repository secret 給 fork 的 PR，
若堅持 fail-closed，**每一個外部貢獻的 CI 都會紅**，而規則又要求 PR 必過 CI——兩條規則互斥。

所以：fork PR 跑 `--no-blocklist`（L1、L3、所有測試照跑，只跳過 L2），並印一則 notice；
**維護者合併前必須在 same-repo 分支或本機補跑一次完整 gate。**
把它寫下來，是因為一個「大家都忘了為什麼」的例外，遲早會被當成「本來就不用跑」。

---

### 掃描器能保證我不會洩漏東西嗎？

**不能。** 它抓不到同音、別稱、暱稱、縮寫、拼寫變體，更抓不到「每句都乾淨、合起來只可能是你」
的可組合推論。
allowlist 是第一道、識別字 HMAC 是第二道、**人眼全文讀是第三道**。三道都做。
細節見 [gates.md](gates.md) 的「L2 的已知限制」與「gate 擋不住的事」。

---

### 我可以拿去商用／改寫／不署名嗎？

整個 repo 是 MIT，可以。唯一要注意的是第三方內容：
`skills/` 裡有三支源自上游的 MIT 專案（一支原文照搬、兩支是衍生作品），
逐項對照與版權行寫在 [THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md)，
散布時請一併保留。

---

### 我想要英文版／其他語言？

範本與文件目前是繁體中文。bootstrap 的 `--lang` 會替換 vault 內的語言宣告
（也就是「agent 用什麼語言跟你講話」），但**不會翻譯範本內容**。
要換語言就自己改 `template/` 的那幾份——它們本來就是要被你改掉的。

---

### 還有問題？

先看 [concepts.md](concepts.md)（為什麼這樣設計）與 [design-notes.md](design-notes.md)（為什麼刻意不那樣設計）。
每個設計借自哪裡、刻意不借什麼，在 [REFERENCES.md](REFERENCES.md)。
