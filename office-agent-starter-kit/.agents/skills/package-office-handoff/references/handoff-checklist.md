# 交接包檢查表

## 根入口

- `AGENTS.md`：目標、狀態、地圖、操作、限制、安全。
- `.env.example`：只有欄位名稱與假值。
- 必要的 runbook、資料 schema、輸出範例。
- 最新接受產物與版本說明。

## 狀態表

| 功能／產物 | 狀態 | 證據 | 入口 | 接手下一步 |
|---|---|---|---|---|

狀態只能使用：

- decided
- implemented
- committed
- merged
- deployed
- verified
- blocked
- unknown

## 必排除

- `.env`、API key、token、cookie、private key
- OAuth／service-account 憑證
- 員工、客戶、供應商個資
- 含真實資料的 SQLite／資料庫 dump
- `.git`、cache、build cache、`node_modules`
- 本機絕對路徑、暫存檔、編輯器狀態

## 驗證

- ZIP 可列出且無損壞。
- 解壓後入口檔存在。
- 機敏掃描通過。
- 最小啟動或唯讀 smoke test 通過。
- 憑證缺少時失敗訊息清楚，不假裝功能可用。
- 已部署與已驗證有獨立證據。
