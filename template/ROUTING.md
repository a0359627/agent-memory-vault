---
title: ROUTING — 東西該寫到哪（路徑的唯一真相來源）
type: routing
updated: {{TODAY}}
---

# ROUTING — 東西該寫到哪

> **這是知識路由的唯一副本。** Skill、腳本、`CLAUDE.md`、`AGENTS.md`
> 可以指向這裡，不要各自維護另一套歸屬規則。回歸測試：`bin/check-routing.sh`。

## 你的 vault 與（可選的）其他來源

| 角色 | 路徑 | 收什麼 | 規則 |
|---|---|---|---|
| **個人第二大腦（預設）** | `~/{{VAULT_NAME}}` | 跨專案理解、偏好、陷阱、skill 卡 | canonical 跨專案理解 |

還有第二個來源時才加列，並在這裡寫清楚它「不收什麼」。兩個常見的例子（用到才取消註解）：

<!-- | 單一客戶專用 vault | `~/<client>-vault` | 只有該客戶的研究與策略 | 該目錄不混入個人第二大腦 | -->
<!-- | 已退役的舊知識庫 | `~/<old-kb>` | 舊流程、skill、參考樣本 | source-only；不再寫新知識、不當 current | -->

「寫回知識庫」「沉澱一下」一律進第一個 vault。

## 三層真相

1. **會跑的真相**：active project repo 的 code、設定、manifest、測試與驗收紀錄。
2. **跨案理解**：本 vault 的跨案方法頁、project card、profile 與 review。
3. **歷史證據**：已退役的舊知識庫（若有）。可以追溯，但動態 model、價格、API、狀態與路徑一律重驗。

因此，新知識不是把整份 repo 搬進 vault：可執行細節留在專案 repo；跨案仍成立的判準才萃取進本 vault。

## {{VAULT_NAME}} 內部路由

| 這是什麼 | 寫到哪 | 規則 |
|---|---|---|
| 不可變原文 | `02-raw/<主題>/` | 永不編輯原文；需要時才 ingest，不整包搬舊庫 |
| 專案真實進度 | `03-wiki/proj-<name>.md` | 寫證據日期、commit／artifact／人類驗收層級；`source:` 指 active repo |
| 跨案方法 | `03-wiki/<領域>-knowledge.md` | 只收已代謝的判準、Gate、失敗模式與來源 |
| skill 卡 | `03-wiki/skill-<name>.md` | 卡片只導航；本體依下節路由 |
| 端到端流程 | `03-wiki/pipe-*.md`、`pipeline-*.md` | 跨案判準在 vault；可跑命令與版本在 active repo |
| 主題星圖 | `03-wiki/cluster-*.md` | 只寫連結，不複製成員頁事實 |
| 時間切片 | `03-wiki/review-*.md`、`worklog-*.md` | 寫完凍結；後續用新 review 取代，不回改歷史 |
| 未知／爭議 | `03-wiki/open-questions.md` | 只收會妨礙未來協助的問題 |
| skill 草稿 | `05-skills-drafts/<name>/SKILL.md` | 通過實戰後移至 active 位置並刪草稿，不留分歧全文 |
| 活檔鏡像 | `08-skill-base/` | 只由同步腳本寫，不手改 |
| Secret 值 | `99-secrets-local/` | gitignored，永不進 Git；版本庫只記位置 |
| 專案活動快照 | `STATUS.md` | 只由 `bin/scan-state.sh` 生成；不是 production 驗證 |

更新 `03-wiki/` 後要更新 `index.md`、append `log.md`，並依 [[memory-metabolism]] 標記
`current`／`superseded`／`contested`／`stale`。

## Skill 本體、平台入口與鏡像

機器可讀的來源清單是 `bin/skill-sources.json`，路由分類以本頁為準。

| 角色 | 位置與管理方式 |
|---|---|
| 跨平台共用 skill 活檔 | `~/.claude/skills/`；保留既有位置，這裡修改正文與資產 |
| Codex 共用 skill 入口 | `~/.agents/skills/`；清單中列名的 skill 連到共用活檔，不另存改名版本 |
| Codex 專用／repo skill | 來源清單指定的 `~/.codex/skills/` 項目或 active repo；不把工具自帶 `.system` 當自訂本體 |
| plugin／工具附帶能力 | 由平台或 plugin 管理；記錄用途與選用邊界，不手改 cache、不混入個人 skill 快照 |

共用 skill 新增或移除時，更新來源清單，執行 `python3 bin/skill_sync.py link` 預覽；
用 `--apply` 安裝入口，舊副本會先移到本機備份。`./08-skill-base/sync-to-vault.sh --apply`
將活檔與列名的平台全域入口建立可還原快照。
快照會展開外部 symlink，保存 hash；恢復時按來源還原並重建共用入口。

## 相似 skill 的選用

先遵循使用者指定的 skill／plugin，再依目前平台能力挑一個主流程。相似名稱不代表可以直接刪除。

| 任務 | 主流程與補充關係 |
|---|---|
| 建立／修改 skill | 當前平台的 skill-creator 處理格式；forge-skill 補本地路由與重用判準，writing-great-skills 是按需參考 |
| 專案接手／收尾 | project-memory 維護該 repo；只有跨案知識才交給 obsidian-vault，避免兩者都寫同一件事 |
| 研究 | 一般查證直接用可用查詢工具；verified-research 適用會影響實作的外部事實 |

## 記憶與偏好

`01-profile/` 是結構化偏好的 canonical。平台自有的專案記憶（例如 `~/.claude/projects/<proj>/memory/`）
只放短期 correction 或指標，不複製一份會分岔的永久偏好。

回 [[index]] · [[memory-metabolism]]
