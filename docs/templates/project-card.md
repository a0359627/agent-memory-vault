# 範本：project card

放在 `03-wiki/proj-<name>.md`。**一個專案一張卡，卡片是導航與誠實狀態，不是專案文件。**
可執行細節（指令、設定、manifest、測試）留在 active repo；這裡只放「跨 session 還需要知道的」。

`source:` 那一行是 `bin/scan-state.sh` 量測活動與 git 風險的依據，寫錯就量不到。
`management_scope:` 與 `intent:` 也是給那支腳本看的，兩行都可以整行省略：

| 欄位 | 值 | 對 `bin/scan-state.sh` 的效果 |
|---|---|---|
| `management_scope` | `owner`（預設） | 正常回報 ahead／behind 的 branch drift |
| `management_scope` | `observe-only` | 只顯示 `observe-only`，不把 drift 當成你的待辦（別人維護的 repo） |
| `intent` | `active`（預設） | 活動量測照檔案 mtime 分級 |
| `intent` | `frozen`／`retire` | 活動量測改成「人工定」，不再因為沒有檔案變動被評成 dormant／stale |

`status:` 是**頁面自稱**，`intent:` 是**你對它的處置**——兩者分開，所以 `status: production` 但 `intent: frozen` 是合法且有意義的組合。
為了相容，`status` 寫成 `frozen`／`archived`／`archive`（索引頁那一套詞彙的寫法）／`observe-only` 時，腳本也會照同樣的分支處理。

索引頁（`03-wiki/projects.md`）列一句話摘要時用的是同一套詞彙的子集：`discovery`／`planning`／`pilot`／`production`／`observe-only`／`archive`。對照只有兩處要記：索引頁的 `archive` 就是卡片的 `archived`；索引頁的 `observe-only` 來自卡片的 `management_scope:`，不是 `status:`。

---

```markdown
---
title: <專案名稱>
type: project
status: <discovery | planning | pilot | active | production | parked | frozen | archived>
management_scope: <owner | observe-only，預設 owner，可整行刪掉>
intent: <active | frozen | retire，預設 active，可整行刪掉>
source: <指向 active repo 或主要產出的路徑>
updated: <YYYY-MM-DD>
due: <YYYY-MM-DD，沒有交期就整行刪掉>
---

# <專案名稱>

## 這是什麼（三句以內）

<要解決誰的什麼問題、目前做到哪、下一個里程碑是什麼。>

## 現行有效的決策

> 狀態改變時更新這一區，並把舊的那段移到下面的「已取代」，**不要就地改寫**。

- <YYYY-MM-DD> <決策一句話>。理由：<為什麼不是另一個選項>。

## verification — 做到哪一層

| 層級 | 狀態 | 證據 |
|---|---|---|
| 實作 | <未開始 / 進行中 / 完成> | <commit、檔案或連結> |
| 測試 | <> | <哪支測試、什麼時候跑的> |
| 提交／合併 | <> | <branch、PR> |
| 部署 | <> | <哪個環境、什麼時候> |
| 人工接受 | <> | <誰、什麼時候、依據什麼> |

**這五層是五件事。** 測試綠不等於部署了，部署了不等於對方接受了。

## last_execution_evidence

- <YYYY-MM-DD>：<最後一次真的跑起來的證據——輸出檔、log 片段的位置、或「沒有」>

## 已知陷阱

- <這個專案特有的坑；跨專案通用的請改寫進 `01-profile/03-known-traps.md`>

## 下一步

1. <具體到可以直接開始做的程度>

## 歸屬待確認（可選，沒有就整節刪掉）

> 這個專案有一部分不是你負責時，寫在這裡，避免未來的 agent 把它排進你的待辦。

- <哪一塊由誰負責>；本 vault 只**觀測**，不得因研究而修改該處。

## 已取代

- <YYYY-MM-DD> <舊決策>，已由上面 <日期> 那條取代。理由：<條件改變了什麼>。

回 [[projects]] · [[index]]
```

---

## 填寫要點

- **`status` 是頁面撰寫當下的語意標記，不是即時狀態。** 要知道哪些專案真的還活著，
  跑 `./bin/scan-state.sh` 再讀 `STATUS.md`。
- **「上線了」永遠要拆開講。** verification 那張表存在的唯一理由，
  就是防止三個月後的你把「測試通過」記成「客戶已經在用」。
- `last_execution_evidence` 寫「沒有」也是有效資訊，而且比空白誠實。
- 卡片長到要分節找東西時，代表細節該回 active repo 了。
