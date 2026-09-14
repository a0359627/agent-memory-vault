---
title: 客戶交付線
type: cluster
status: current
updated: 2026-02-20
---

# 客戶交付線

> 叢集頁只寫連結與一句話，**不複製成員頁的事實**。想知道某個案子現在到哪，點進去看那張卡；
> 這一頁只負責讓你在三十秒內找到該點哪一個。

## 客戶

- **甲咖啡館**：形象網站改版。需求來源見 [[ref-client-brief-2026-01]]，執行見 [[proj-brand-site-relaunch]]。
- **乙書室**：沒有獨立專案頁——目前只有每週進度報告這一條線，
  證據散在 [[skill-weekly-client-report]] 與 [[review-2026-02-14-first-month]]。
  等它有第二種交付物時才開卡；為了湊數而開的空卡比沒有卡更糟。

## 專案

- [[proj-brand-site-relaunch]] — 甲咖啡館形象網站改版 — `pilot`
- [[proj-weekly-report-bot]] — 週報產生器（內部工具，兩個客戶都在用） — `production`

## 能力

- [[skill-weekly-client-report]] — 已晉升；每週報告的產出流程與完成判準。
- [[skill-client-feedback-triage]] — 孵化中；只在甲咖啡館驗證過。

## 這條線的三個已知風險

1. **沒有測試環境**（[[02-environment]] 硬限制第一條）：部署等於給客戶看，改錯就是線上錯。
2. **外部動作的核准點是後來才補的**（[[03-known-traps]] 第 3 條）：2026-02-18 之前，
   週報的寄送沒有人擋在中間。
3. **需求的 authority 靠慣例撐了一個月**：2026-02-10 才寫成規則
   （[[open-questions]] 的 `client-feedback-authority`）。在那之前的判斷都要當成可疑的。

回 [[index]] · [[projects]]
