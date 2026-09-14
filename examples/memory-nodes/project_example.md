---
name: weekly-report-bot
description: 「跑一下週報」＝週報產生器產出草稿到 drafts/，不寄送；試算表空白欄是 unknown 不是 0
metadata:
  node_type: memory
  type: project
  modified: 2026-02-20
---

週報產生器是工作室的內部小工具：讀客戶工時試算表匯出的 CSV，
產出每個客戶一份 Markdown 草稿到本機 `drafts/`，檔名含週次。

**scope：** 只在週報產生器這個工具的語境成立。同樣的話用在其他腳本上不適用。

**source：** vault 的 `03-wiki/proj-weekly-report-bot.md`「現行有效」段（2026-02-20 起）。

**Why:** 「跑一下週報」這句話有歧義——它可能是「產草稿」也可能是「寄給客戶」。
2026-02-18 那次誤寄之後，這個歧義變成有代價的，所以把它的意思釘死在這裡。

**How to apply:**
- 「跑一下週報」＝**只產草稿**。跑完印出草稿路徑就結束，不寄、不問要不要寄。
- 使用者說「寄出去」時，仍然先把草稿內容貼出來讓人看過，再由**人自己**寄。
- 解析 CSV 時空白欄一律是 `unknown`，不是 0。草稿第一行要印 `unknown` 的筆數；
  筆數大於 0 就停下來問人。
- `--dry-run` 是真的唯讀（不載入憑證）。**舊的 `--preview` 不是**——
  看到任何地方還在用它，直接指出來。

相關：[[user_example]]、[[feedback_example]]
