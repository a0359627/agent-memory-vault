# Changelog

格式參考 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)，版號遵循 [語意化版本](https://semver.org/lang/zh-TW/)。

日期為該版本定版日；`Unreleased` 區塊記錄已合併但尚未發版的變更。

## [Unreleased]

（尚無）

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

[Unreleased]: https://github.com/a0359627/agent-memory-vault/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/a0359627/agent-memory-vault/releases/tag/v0.1.0
