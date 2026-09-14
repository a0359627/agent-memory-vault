# 辦公室 Agent Skill 新手包

這個資料夾讓沒有程式背景的人，用 Codex 完成兩件事：

1. 直接使用六支常見辦公技能。
2. 把自己的重複工作整理成可測試、可交接的 Codex skill。

不需要先理解 AI 架構，也不要先裝套件。

## 第一次使用

1. 取得本包：`git clone` 本 repo 之後進入 `office-agent-starter-kit/`；若你拿到的是 release ZIP，先解壓縮。
   本包以 MIT 授權散布，條文在同一層的 `LICENSE`——你可以自由使用、修改與再散布，條件是把那份聲明一起帶著。
2. 在 Codex App、Codex CLI 或 IDE extension 開啟這個資料夾。
3. 新開一個 task，貼上：

   ```text
   請先讀 START-HERE.md，帶我完成 PRACTICE.md 的練習 1。
   一次只教一個步驟，每一步先解釋目的，再讓我操作。
   ```

Codex 會自動讀取根目錄的 `AGENTS.md`，也會從 `.agents/skills/` 找到本包的 skills。

如果 skill 沒出現在選單，重新開啟 Codex，並確認目前開啟的是這個資料夾的根目錄（有 `AGENTS.md` 的那一層）。

## 六支技能

| Skill | 用途 | 新手可以這樣說 |
|---|---|---|
| `$build-office-skill` | 把重複辦公流程做成新 skill | 「用 `$build-office-skill` 把每週進度彙整做成 skill」 |
| `$meeting-to-actions` | 會議紀錄轉決策、待辦與待確認項目 | 「把 `fixtures/meeting-notes.txt` 整理成行動清單」 |
| `$draft-office-document` | 依來源起草郵件、備忘錄與狀態報告 | 「依 `fixtures/status-source.md` 寫主管週報」 |
| `$verify-office-research` | 建立逐條有來源的研究摘要 | 「研究某項採購方案，每條主張附來源和日期」 |
| `$review-office-spreadsheet` | 唯讀檢查試算表的錯漏與異常 | 「檢查 `fixtures/expenses.csv`，先不要修改」 |
| `$package-office-handoff` | 建立去機敏的交接 ZIP | 「把這個資料夾整理成可交給同事的 ZIP」 |

`$skill-name` 是明確指定 skill。平常也可以直接描述需求，Codex 會依 skill 的 description 判斷是否使用。

## 建議學習順序

1. 先做 `PRACTICE.md` 練習 1–4，學會使用現成技能。
2. 讀 `LESSONS.md`，理解 prompt、`AGENTS.md`、skill 與外部工具的分工。
3. 做練習 5，把自己每週真的會重複一次的工作做成 skill。
4. 用正向、反向、不完整與邊界案例測試新 skill。
5. 只在測試通過後，才把 skill 複製到個人共用目錄。

## 讓 skill 在其他專案也能使用

目前 skills 是這個資料夾專用，位置在 `.agents/skills/`。確認某支 skill 穩定後，可以請 Codex：

```text
請把 .agents/skills/meeting-to-actions 安裝到我的使用者 skill 目錄。
先顯示目標路徑與會寫入的檔案，得到我確認後再複製。
```

Codex 的使用者 skill 目錄是：

- macOS／Linux：`$HOME/.agents/skills/`
- Windows：請在 WSL 底下沿用上面那條路徑。原生 Windows 的
  `%USERPROFILE%\.agents\skills\` 只適用於「單獨使用 Codex、完全不搭配本 repo 腳本」的情況——
  本 repo 的工具鏈（bash 腳本、符號連結）在原生 Windows 不成立，裝到那裡 WSL 也看不到。

## 安全界線

- 不把密碼、API key、token、身分證字號、員工名冊或客戶個資貼進教材或 skill。
- 草稿郵件不等於已寄出；試算表建議不等於已修改；研究摘要不等於已核准決策。
- 寄信、改共享檔、刪除、付款、發布與權限變更，必須由有權限的人明確核准。
- 不知道就標「未知／待確認」，不要用流暢文字補空白。

## 官方參考

- [OpenAI：Build skills](https://learn.chatgpt.com/docs/build-skills)
- [OpenAI：AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Agent Skills 規格](https://agentskills.io/specification)
