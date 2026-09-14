---
name: package-office-handoff
description: 將工作資料夾或 repo 整理成去機敏、可閱讀、可執行、可驗證的交接 ZIP；當使用者要交接專案、打包給同事或另一個 agent、建立操作地圖、runbook 與未完成清單時使用。一般備份或公開發布不使用。
---

# Package Office Handoff

交付目標不是「檔案很多」，而是接手者只讀入口檔，就知道有什麼、目前到哪裡、怎麼驗證、哪些不能碰。

## 1. 先界定接收者與範圍

確認：

- 接收者是同事、外包、客戶或另一個 agent；
- 他需要唯讀理解、能在本機執行，或能修改；
- 包含哪些產物與程式；
- 不包含哪些客戶資料、員工個資、憑證與 live state；
- 交接時點與 owner。

完成判準：有明確的 include／exclude 清單與接收者權限。

## 2. 盤點真實狀態

狀態分開記：

- `decided`：已拍板；
- `implemented`：已在某個工作副本完成；
- `committed`：已進 commit；
- `merged`：已合併到指定分支；
- `deployed`：已部署；
- `verified`：已在目標環境驗證。

工作在 worktree 或 feature branch 完成時，記錄實際路徑、分支與 merge 狀態。不能用「主工作區乾淨」推論工作不存在。

完成判準：每項功能都有狀態、證據、入口與下一步。

## 3. 建立入口與操作地圖

根目錄 `AGENTS.md` 至少包含：

1. 交付目標與 owner；
2. 功能／狀態／入口表；
3. 資料夾地圖；
4. 最小啟動與驗證步驟；
5. 未完成、已知限制與安全紅線；
6. 憑證如何由接收者自行設定，但不包含值。

格式讀 [`references/handoff-checklist.md`](references/handoff-checklist.md)。

完成判準：未看過專案的人能只從 `AGENTS.md` 找到第一個可驗證動作。

## 4. 掃描機敏資料

執行：

```bash
python3 .agents/skills/package-office-handoff/scripts/scan_sensitive.py <source-dir>
```

任何 secret 命中都停止打包。Email、電話等個資警告要逐項判斷是否有交付必要；預設排除。

完成判準：secret 錯誤為 0，PII 警告已逐項處理並記錄理由。

## 5. 建立 ZIP

```bash
python3 .agents/skills/package-office-handoff/scripts/build_handoff_zip.py \
  <source-dir> <output.zip>
```

預設排除 `.git`、`node_modules`、`.env`、token、資料庫、cache、`local-only` 等 live state。真正需要的設定以 `.env.example` 或設定說明取代。

完成判準：ZIP 成功建立，內含 manifest、入口檔與必要產物，不含被排除資料。

## 6. 解壓後驗證

在新的暫存資料夾解壓：

- 列出檔案；
- 重新跑機敏掃描；
- 依入口檔完成最小啟動或唯讀 smoke test；
- 檢查內部連結與相對路徑；
- 回報已驗證與尚未驗證的部分。

完成判準：驗證發生在解壓後的交接包，不是原工作資料夾；狀態沒有被誇大。
