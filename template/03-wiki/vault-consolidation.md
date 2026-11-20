---
title: 定期整併 — 每週一次的知識庫整理流程
type: operating-procedure
status: current
updated: {{TODAY}}
scope: 只限本 vault；不含其他 repo、部署或對外動作
revisit_when: 跑滿 4 次後檢討範圍與「可直接合併」的清單
tags: [memory, governance, consolidation]
---

# 定期整併

**一句話**：每週一次，把散落的 log 碎片併回、修掉壞連結，並檢查最近變動的頁面是否還對得上事實；
機械性修正直接做，需要判斷的只提案。

判準在 [[memory-metabolism]]，這一頁只寫怎麼跑。沒有這個節奏，「過期」與「遺忘」只是寫在政策頁上的字。

## 什麼時候跑

- 每週一次。用你的 agent 平台的排程功能，或固定一個時段手動跑；排程任務的內容只要一句
  「照 `03-wiki/vault-consolidation.md` 跑一輪」，流程以本頁為準。
- 排程沒跑到就補跑一次，不必追趕漏掉的每一週：報告會從上一輪的 log 標記起算。
- 知識庫還很小、也沒有多個 session 同時在寫時，改成每月一次也可以。寫下你選的頻率，不要留白。

## 邊界

- 在從遠端預設分支新開的 worktree 或分支裡改；不碰主工作區的未提交修改。
- 別人的分支與開著的 PR 只列出，不合併、不改、不刪。
- 不 force push；不讀 `99-secrets-local/`。
- 不動其他 repo、不部署、不發信、不改權限。

## 步驟

### 1. 準備

```bash
git fetch origin                  # 有遠端才需要
python3 bin/consolidate.py        # 唯讀報告：這次該看哪裡
./bin/check-routing.sh            # 唯讀：記下改動前的 error 與 warning
```

報告的每一欄都是「去哪裡看」，不是「什麼是真的」：

| 欄位 | 告訴你什麼 |
|---|---|
| `pending_fragments` | 有哪些 `log-append-*.md` 等著併回 |
| `injected_layer` | 每個 session 一開始就載入的指令檔共幾行；超過 200 行會標 `over_budget`（200 是軟預算，寫在 `bin/consolidate.py` 開頭，可以改） |
| `most_changed`／`largest_project_cards` | 上次整併以來改最多的頁、最長的專案卡 |
| `stale_open_questions` | Active 區超過 60 天沒動的問題 |
| `unmerged_remote_branches` | 遠端還沒併回的分支 |
| `frontmatter_warnings`／`source_link_warnings` | 代謝 gate 目前的 warning |

### 2. 機械整併（可直接合併）

只有這三類：

1. `python3 bin/consolidate.py --apply`：把 `03-wiki/log-append-*.md` 的條目依日期併進 `log.md` 並移除碎片。
2. 修壞連結，替孤兒頁或 `02-raw/` 資料夾補連結，**限目標唯一且明確時**。
3. 在 `log.md` 追加一則 `## [YYYY-MM-DD] lint | 定期整併`，寫做了什麼。下次報告靠這個標題判斷起算日。

合併條件，全部成立才合併，否則留著並回報：

- `./bin/check-routing.sh` 沒有比改動前多出任何 error 或 warning。
- `python3 -B -m unittest discover -s bin -p 'test_*.py'` 全過（`-B` 是為了不在 `bin/` 留下 `__pycache__`）。
- diff 只包含上面三類改動。

### 3. 語意檢查（只提案）

範圍只限報告列出的：上次整併以來改過的頁、`revisit_when` 過期的頁、變動最多的專案卡、每輪載入層。
不重讀整個知識庫。

| 看什麼 | 發現時的提案 |
|---|---|
| 頁面主張對不上 raw、active repo 或使用者原話 | 依 [[memory-metabolism]] 標 `stale`／`contested`／`superseded` |
| 兩頁講同一件事 | 合併成一頁，舊頁標 `superseded_by` |
| 專案卡在重播 active repo 查得到的進度 | 瘦身成現行結論加指標 |
| 每輪載入層超過 200 行 | 把細節下移到 wiki，原處留連結 |
| [[open-questions]] 的 Active 超過 60 天沒動 | 移到 Answered 或 Stale，或補上新的 Seen |
| `08-skill-base/` 鏡像漂移 | 跑 `./08-skill-base/sync-to-vault.sh` 預覽，列出會新增的來源 |

有實際改動的提案放在另一個分支，**不合併**，等 {{OWNER}} 決定。沒有改動的只寫在回報裡。

### 4. 回報

沒有待決事項時一句話：併了什麼、合併到哪個提交。有待決時用 [AGENT-RULES](../AGENT-RULES.md)
工程紀律第 8 條的回報形狀，每個待決附建議、影響、證據、風險。

## 不算機械的事

以下一律走提案，不直接合併：改 `AGENT-RULES.md`／`ROUTING.md` 的語意、改 `01-profile/`、刪頁、
改任何頁的 `status`、套用鏡像同步、搬動或改寫既有 log 條目。

## 沒事就不做

沒有碎片、沒有可修的連結、沒有提案時，不開分支、不寫 log，回報一句「本週無需整併」。

回 [[index]] · [[memory-metabolism]] · [[log]]
