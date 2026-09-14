---
title: Open Questions — 會影響未來協助的未知
type: memory-index
status: current
updated: 2026-02-20
---

# Open Questions — 會影響未來協助的未知

> 只收「若不知道，會讓未來的 agent 協助失準」的未知與爭議。
> 報價、排程、程式 bug 留在工作清單，不放這裡。

## Active

### draft-promotion-threshold：一支 skill 要在幾個客戶身上成立，才算通用？

- Owner：小明
- Seen：2026-02-05
- Evidence：[[skill-client-feedback-triage]]、[[skill-weekly-client-report]]、[[log]] 的 2026-02-03 與 2026-02-05 兩則
- Notes：目前用的是「兩個客戶 × 三週 × 換人也做得出來」，但這個門檻是
  [[skill-weekly-client-report]] 晉升時**事後**歸納的，只有一個樣本。
  在有第二支 skill 走完同一條路之前，不把它寫成 [[01-preferences]] 的規則。
  決定前不假設：遇到新草稿一律先問「你打算用什麼證據說它通用」。

### report-unknown-handling：週報裡的 `unknown` 工時要不要讓客戶看到？

- Owner：小明
- Seen：2026-02-14
- Evidence：[[03-known-traps]] 第 1 條、[[proj-weekly-report-bot]]、[[review-2026-02-14-first-month]]
- Notes：現在的做法是「有 `unknown` 就不自動送出，先問人」，但沒有決定
  **問完之後**該把它寫進客戶版報告，還是只留在內部版。
  兩邊都有道理：寫進去比較誠實，但客戶可能誤以為是我們沒做事。
  這一題不決定不會出事，但每次都要重問，所以值得留在這裡。

## Answered

### client-feedback-authority：客戶的口頭回饋可以直接當定案依據嗎？

- Evidence：[[2026-01-05]] 的待確認清單、[[02-raw/client-brief-2026-01/SOURCE]] 的三份「最終版」差異、[[03-known-traps]] 第 4 條
- Answered：2026-02-10
- Authority：`user-confirmed`（小明在 2026-02-10 明確決定）
- Answer：**不可以。** 口頭回饋只能成為候選；要有文字確認（信件或工單）才算定案依據。
  沒有文字的，回信覆述一次請客戶回覆確認，並把那封回信當成來源記在對應的頁上。
  範圍：所有客戶案，包含尚未簽約的洽談。已寫成 [[01-preferences]] 的 `current` 條目。
  這一題是被 `02-raw/` 的三份同名「最終版」逼出來的——檔案不會告訴你誰說了算。

## Stale

目前無。

> 條件消失（客戶結案、系統下線、決策被取代）而失效的問題移到這裡並寫 `Why`；
> 「想不出答案」不是 stale，那還是 Active。

> 維護規則（Active → Answered → Stale 的判準）在 `template/03-wiki/memory-metabolism.md`，
> 這個範例只示範長好之後的樣子。

回 [[index]] · [[log]]
