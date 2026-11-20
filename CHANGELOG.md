# Changelog

格式參考 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)，版號遵循 [語意化版本](https://semver.org/lang/zh-TW/)。

日期為該版本定版日；`Unreleased` 區塊記錄已合併但尚未發版的變更。

## [Unreleased]

（尚無）

## [0.2.0] — 2026-11-20

把記憶代謝從「寫在政策頁的規範」變成「會響的 gate 加上固定的節奏」。資料夾結構沒有變；
已經用 0.1.x 建過 vault 的人照 [docs/upgrading.md](docs/upgrading.md) 升級。

### 新增

**兩軸的頁面狀態**

- frontmatter 的 `status` 只記頁面的記憶生命週期（`current`／`superseded`／`contested`／`watchlist`／`stale`／`historical`）；
  頁面所描述的專案或 skill 自己的狀態改記在新欄位 `subject_status`。`historical` 是新值，給寫完就凍結的 review 與 worklog。
- `bin/status-vocab.json`：兩套詞彙、舊值對照表與兩個天數門檻的唯一來源。
- `bin/migrate_status.py`：把 0.1.x 的單軸 `status` 一次拆成兩軸。預設乾跑、只動 frontmatter、重跑是 no-op。

**會響的代謝 gate**（`bin/check_vault.py`，全部只發 warning）

- 詞彙外的 `status`／`subject_status`；`superseded` 缺 `superseded_by` 或目標不存在；日期已過的 `revisit_when`；
  `current` 的 skill 卡缺 `verified_at` 或超過 180 天；`03-wiki/` 的 `current` 頁沒有任何日期欄位；
  平台的專案型記憶超過 90 天又沒有 `revisit_when`；`02-raw/`、`04-projects/`、`07-archive/` 的子資料夾沒有被真連結指到。
- 一個新的 error：`03-wiki/`、`01-profile/` 裡被 `.gitignore` 擋掉的頁面。它在磁碟上一切正常，卻永遠進不了 git。

**每週整併**

- `template/03-wiki/vault-consolidation.md`：機械整併直接做、語意判斷只提案的流程。
- `bin/consolidate.py`：唯讀報告（待併的 log 碎片、每輪載入層的行數預算、變動最多的頁、過久的 open question、
  未併回的分支、當下的代謝 warning）；`--apply` 只把 `03-wiki/log-append-*.md` 依日期原文併回 `log.md`。
- log 碎片慣例：`log.md` 已被別的 session 改動時，改寫 `log-append-YYYY-MM-DD.md`，不在同一個檔尾互撞。

**規則**

- `template/AGENT-RULES.md` 新增「共用工程紀律」八條：原有六條加上錯誤升級階梯、改前估爆炸半徑，
  以及「高風險才對抗、教訓要核准、回報有形狀」。另新增三條協作規則：不必事事回報、能跑出來的事實不要問人、
  說「誰做了什麼」之前先看證據。
- skill 晉升門檻有了數字：跨 2 個 session 真用 3 次、步驟無歧義、工具在當前環境找得到。
  skill 卡新增 `verified_at`／`verification`／`promoted_from`。
- `template/01-profile/03-known-traps.md`：條目多一欄「強制層級」；通則從四條增為九條，
  新的五條談 agent 協作本身（檢查看的是什麼、撤銷授權的範圍、誰做了什麼、交接有沒有送達、掃描擋得住什麼）。
- 交接完成的定義：對方收到的第一則訊息已包含交接檔路徑與清單本文。

**同步引擎**

- `bin/skill-sources.json` 新增可選的 `memory_exclusions`（專案 id → 排除原因）：排除發生在讀取記憶內容之前，
  決策記入 `snapshot.json`。origin 新增可選的 `exclude`（頂層名稱），跳過由別的工具管理的子目錄。

**測試與文件**

- `bin/` 新增四組自測（`test_check_vault`、`test_migrate_status`、`test_scan_state`、`test_consolidate`），
  連同擴充後的 `test_skill_sync` 都會被 `bootstrap.py` 帶進讀者的 vault；`bin/gate.sh` 改為一次全跑。
- `docs/upgrading.md`：0.1.x → 0.2.0 的逐步升級指南。
- `docs/concepts.md` 新增「代謝要有引擎」一節與外部記憶分層的對照；`docs/gates.md` 補上每一條新 warning 的意思與處理方式。
- `docs/REFERENCES.md` 新增三條來源（agent 記憶分層與離線整併、認知架構的記憶分類、一套外部的 agent 工作流方法），
  各自標明借了什麼與刻意沒收什麼。

### 變更

- CI：`release/**` 分支的 push 也跑同一道 gate。維護者發布走「推 release 分支 → CI 綠 → fast-forward `main`」，不必為了取得必過檢查開 pull request（[docs/gates.md](docs/gates.md)）。
- `bin/scan-state.sh`：專案標籤改讀 `subject_status`，沒有才退回舊的 `status`；`STATUS.md` 的全表多一欄「記憶狀態」。
  `--fetch` 有失敗時 `remote_refs_refreshed` 記為 `partial`，沒有 origin 的 repo 不算失敗。
  `source:` 不是絕對路徑時顯示「未設本機 source」，不再報成路徑不存在。執行中程式持續改寫的檔案
  （`.env`、資料庫的 `-wal`／`-shm`）不再算作專案活動。
- 範本：project card 的專案狀態移到 `subject_status`；review 的 `status` 由 `frozen` 改為 `historical`；
  舊知識庫橋接卡改為 `status: current` 加 `subject_status: source-only`；skill 卡改為兩軸。
- `examples/sample-vault/` 的頁面改用兩軸寫法。
- `template/.obsidian/app.json` 預設把 `08-skill-base/` 排除在圖譜之外：鏡像是 skill 正文的副本，會在圖上長出一堆重複節點。

### 相容性

- 0.1.x 的 vault 不升級也能繼續用舊工具；新舊工具不要混搭。
- 未遷移的單軸卡片仍可被 `bin/scan-state.sh` 掃描；新的 `check_vault.py` 會對它們發 warning，不會擋。
- `snapshot.json` 格式不變；只有用了 `memory_exclusions` 才會多一個欄位。

## [0.1.0] — 2026-09-14

第一版。以白名單匯出的方式，把一個私有知識庫裡**可通用的那部分**——骨架、規範、工具與 skill——整理成可被任何人 clone 的起手式。

### 新增

**上手路徑**

- `tools/bootstrap.py`：三個命令建立一個可用的知識庫。拒絕非空目錄、替換佔位符後自我檢查、寫入第一筆 log、`git init` 與第一個 commit，最後跑一次檢查器當第一個綠燈。對知識庫以外**零寫入**：不碰任何平台的全域設定目錄、不下載任何東西。
- `template/`：讀者知識庫的骨架。三層結構（不可變原文／彙編／規範）加上按可行動性分類的資料夾、Obsidian 設定、雙入口單一規範（`AGENTS.md`／`CLAUDE.md` 只負責載入 `AGENT-RULES.md`）、`ROUTING.md` 與它的回歸測試。
- `examples/sample-vault/`：一個**完全虛構**、已經填滿的知識庫，可從 `03-wiki/log.md` 的八筆紀錄當劇本一路翻完，含「未晉升草稿 vs 已晉升 skill」對照組。以 `bootstrap.py --with-sample` 取得。
- `examples/memory-nodes/`、`examples/first-skill/`：四型記憶節點與一支寫完的 skill（含測試紀錄）的虛構範例。
- `docs/`：快速開始、兩條動手型 walkthrough（第一次 ingest、第一支 skill）、核心概念、閘門說明、把自己的知識庫公開出去的流程、參考文獻、常見問題，以及八份可直接複製的範本。

**skill**

- `skills/` 八支 starter skill：`grill-me`、`forge-skill`、`obsidian-vault`、`project-memory`、`diagnosing-bugs`、`verified-research`、`agent-handoff-pack`（直接可用）與 `writing-great-skills`（參考用）。
- `tools/install_skills.py`：預設只預覽，`--apply` 才寫檔；**永不覆蓋**既有的同名 skill；可同時登錄進知識庫的來源清單。支援 Claude Code 與 Codex 兩個目錄慣例。
- `bin/skill_sync.py` 與 `bin/test_skill_sync.py`：registry 驅動的 skill 抽取、鏡像與還原引擎，零相依、預設唯讀、寫入前有 secret 預檢與備份。
- `office-agent-starter-kit/`：給 Codex 讀者的教學包——六支辦公室 skill、五個練習、虛構 fixtures、自帶的驗證器與去機敏打包器。

**閘門與發布工具**

- `tools/publish_check.py`：三層發布掃描。L1 secret 樣式（含佔位符白名單，不誤報）、L2 識別字 HMAC 封鎖（key 不在 repo，缺 key 時 fail-closed）、L3 結構與形狀（符號連結、環境檔、絕對路徑、個資形狀、連結目標存在性、佔位符越界等）。另支援掃 git 歷史（`--stdin`）、掃遠端 URL（`--remotes`）與 staged 檔（`--staged`）。
- `tools/export_public.py`：通用白名單匯出器。每條改寫規則帶 `expect` 命中次數、每個檔案帶輸出 sha256、全域 `assert_absent`、樹比對，**任一錯誤一個檔都不寫**。
- `tools/build_identifier_blocklist.py`：把明文識別字清單轉成 HMAC 封鎖表；必要類別缺一即拒絕生成。
- `tools/build_references.py`：從私有母本生成公開版參考文獻頁，並可在 CI 無母本時單獨驗證。
- `bin/gate.sh`：一鍵閘門。`--public` 只用 repo 內就有的東西（CI 跑這個），`--full` 另外比對私有母本並以毒物 canary 反向驗證掃描器真的有在運作。任一步非 0 即停。
- `bin/check_vault.py`、`bin/check-routing.sh`：知識庫自身的健康檢查（連結、路由、鏡像一致性、共用 skill 不得含絕對家目錄路徑）。
- `tools/hooks/pre-commit` 與 `tools/install-hooks.sh`：把三層掃描裝進 commit 流程。
- `.github/workflows/gate.yml`：push 與 PR 都跑 `bin/gate.sh --public`；fork 的 PR 拿不到 secret 時印 notice 並跳過 L2，L1／L3 與全部測試照跑。
- `tests/`：七組單元測試（`bootstrap`、`export_public`、`publish_check`、`gate.sh` 的不可調鬆性質、私有頁名與祕密位置形狀的殘留、`citation_quotes`（引文必須真的在被引檔案裡）、`status_vocabulary`（範本詞彙與 `bin/scan-state.sh` 必須同一套））與一支乾淨 HOME 的端到端 smoke，全部在臨時目錄執行。

**文件**

- `README.md`、`SECURITY.md`（三條 secrets 鐵律與「只記位置不記值」）、`CONTRIBUTING.md`（白名單唯一入口、去識別守則、對抗式複核、fork PR 的 L2 政策）、`LICENSE`（MIT）、`THIRD-PARTY-NOTICES.md`。

### 已知限制

- L2 的識別字封鎖抓不到別稱、暱稱、拼音、縮寫，也抓不到「單句無害、湊起來可反推」的敘述。白名單是第一道防線，HMAC 只是第二道，人工全文讀是最後一道。詳見 `docs/gates.md`。
- 支援 macOS 與 Linux。Windows 請在 WSL 底下使用。
- 本版只收 8 支通用 skill；領域型 skill 刻意不收（理由見 `docs/design-notes.md`）。更多 starter skill、v2 的模式範例與英文版文件，預定在後續版本加入。

[Unreleased]: https://github.com/a0359627/agent-memory-vault/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/a0359627/agent-memory-vault/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/a0359627/agent-memory-vault/releases/tag/v0.1.0
