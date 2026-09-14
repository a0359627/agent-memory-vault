# 共用 Agent 協作與知識庫規範

> 維護來源：本檔。Codex 的 AGENTS.md 與 Claude 的 CLAUDE.md 是載入入口。
> 路徑歸屬以 [ROUTING.md](ROUTING.md) 為準。

## 任務範圍與協作

- 使用者目前的目的、明示限制與既有授權優先於舊 skill 範例；遵循平台更高層指令與實際工具權限。
- 「評估／只看／先不要改」維持唯讀；已授權的可逆工作持續完成。可查證的事實自行查，
  只對會影響方向、重大成本或外部承諾的必要未知請使用者決定，不重問同一份授權。
- 一個任務指定一個主要整合者。其他 agent 的工作要有範圍、基準版本與交付物；
  寫入前查看既有修改、分支及 worktree，不覆蓋他人未完成的工作。
- 回報區分實作、測試、提交、合併、部署與人工接受。API 200、成功 render 或測試通過只能證明對應層級。
- 非瑣碎任務按需讀 [使用者背景](01-profile/00-who.md) 與 [合作偏好](01-profile/01-preferences.md)；
  安裝／除錯才讀 [環境快照](01-profile/02-environment.md) 及相關 [陷阱](01-profile/03-known-traps.md)。
  跨專案定位依 [ROUTING](ROUTING.md)。動態事實回當前環境或 active repo 重驗。

## 權威與記憶

- 本 vault 保存跨案理解、來源與判準；程式、設定、manifest、production DB 與單案驗收留在各 active repo／正式系統。
- 領域專用知識頁依 [ROUTING](ROUTING.md) 決定：ROUTING → 該領域的跨案方法頁 → project card → active repo。
- 個人偏好的 canonical 是 `01-profile/`。單案回饋保留來源與範圍；推論先為 candidate，
  不因頻率、沉默或一次評語升為永久偏好。平台自有記憶的寫入需遵守平台授權。
- 共用 skill、平台入口與鏡像的維護位置由 [ROUTING](ROUTING.md) 和來源清單 `bin/skill-sources.json` 定義。
  自動選用 skill 時依任務與平台選一個適合的主流程，領域或品牌規則按需補充。

## 本 vault 的讀寫規範

以下適用於本 vault 的維護。Obsidian 是唯讀圖譜檢視器；agent 直接操作磁碟。

| 位置 | 角色與寫入規則 |
|---|---|
| `02-raw/` | 不可變來源；保存原文，後續只讀，不覆寫歷史 |
| `03-wiki/` | 彙編、概念、project／skill 導覽卡與索引 |
| `01-profile/` | 有來源、範圍的個人脈絡；機器資訊另標觀察時間 |
| `04-projects/` | 有期限的交付；執行 repo 的文件不搬來冒充當前狀態 |
| `05-skills-drafts/` | 尚待驗證的 skill；轉正式後保留取代關係，避免分歧全文 |
| `08-skill-base/` | 活檔的可遷移鏡像，只由同步工具產生；腳本與 README 是維護檔 |

每次知識維護先讀 [memory-metabolism](03-wiki/memory-metabolism.md) 及 [open-questions](03-wiki/open-questions.md)。
沒有新增 durable knowledge 時允許 no-op；讀取或評估本身不授權新增記憶。

1. 先分辨來源、想法、當次進度與跨案判準，查既有 canonical 頁後再寫。
2. 原文進 `02-raw/`；摘要、推論、關聯與現行結論進 `03-wiki/`。單案的執行證據先在 active repo 成立。
3. 高影響主張附來源、時間、scope、authority 及適用狀態。舊主張以 supersedes／superseded_by 保留取代關係，
   歷史 review／worklog 保持原樣；過期理解在現行入口標明，不靜默覆寫歷史。
4. wiki 使用雙括號 wikilink 與必要的標準 Markdown 連結；更新受影響的索引，在 log 追加
   `## [YYYY-MM-DD] ingest | 標題` 或相應動作。skill 卡只導航，避免複製整份 skill。
5. open questions 只追蹤會影響未來協助的未知；有新答案或條件改變時移到 Answered／Stale。
6. 交付前檢查本次連結、來源／鏡像一致性及未標明的矛盾。整理重複資料前保留來源與可回復版本。

## 機敏資料

- API key、token、密碼、私鑰不進可提交的 Markdown、程式或回應；原文包含 secret 時也不可複製到摘要。
- `99-secrets-local/` 是唯一的本地明文清冊例外，受 gitignore 保護；值只以 disk-to-disk 方式處理，
  不經模型 context。canonical 明文清冊放 gitignored 的本機位置，MIGRATE.md 只記去哪找。
- age 密文備份與明文分開，私鑰不入 Git。提交前確認 staged files 與 `99-secrets-local/` 的忽略狀態。
- 本輪授權不延伸到其他 repo 的部署、發信、付款、帳號權限或公開發布。

語言使用 {{LANG}}，給具體建議並說明原因。
