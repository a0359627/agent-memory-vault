# Office Agent Starter Kit — 專案脈絡

> 維護者用。新手入口是根目錄 `START-HERE.md`。
> 最後更新：2026-08-03。

## 目標

讓沒有程式背景的辦公室工作者在 Codex 中：

1. 使用六支安全的辦公 skill；
2. 理解 prompt、`AGENTS.md`、skill 與工具的分工；
3. 把自己的重複工作做成可測試 skill；
4. 在任何外部副作用前保留人類核准。

## 安全與交付邊界

- 不包含任何真實人員、客戶、部署資訊或 secrets；fixtures 全為虛構。
- 寄信、修改共享檔、刪除、付款、發布與權限變更只做到預覽與核准點。
- skill 使用 repo-scoped `.agents/skills/`；clone 本 repo 後開啟 `office-agent-starter-kit/`
  （或解壓 release ZIP 後開啟根目錄）即可被 Codex 掃描。
- 不要求 MCP、外部 connector 或 API key；需要 live 系統時由接收者另行授權。

## 結構

```text
START-HERE / LESSONS / PRACTICE
                 │
                 ▼
        .agents/skills/（6 支）
                 │
                 ▼
          fixtures + tools
```

## 技能分工

| Skill | 主要 contract |
|---|---|
| build-office-skill | 重複流程 → 可觸發、可測試 skill |
| meeting-to-actions | 來源 → 決策、待辦、未知 |
| draft-office-document | 核准來源 → 可審核文件草稿 |
| verify-office-research | 決策問題 → claim ledger 與來源 |
| review-office-spreadsheet | 原始表格 → 唯讀問題證據 |
| package-office-handoff | 工作資料夾 → 去機敏交接 ZIP |

## 驗證

```bash
python3 tools/validate_kit.py
python3 tools/build_release.py ../office-agent-starter-kit-YYYY-MM-DD.zip
```

每支 skill 另以官方 `skill-creator` 的 `quick_validate.py` 驗證。Release 必須解壓後重新檢查檔案清單、skill 結構與 secret scan。

前向測試涵蓋兩條高判斷流程：

- `meeting-to-actions`：能把逐字紀錄中的確認決策、提案、待辦與未知事項分開，並保留時間戳來源。
- `build-office-skill`：面對「彙整三位同事週報」的需求時，會先提出工作契約、不可推測欄位、人類核准點與最小 skill 結構，不會自行加入寄送動作。

## Sprint 紀錄

| 日期 | 狀態 | 內容 |
|---|---|---|
| 2026-08-03 | verified | 完成教材、六支 skill、fixtures、前向測試、驗證與 ZIP 建置工具 |
