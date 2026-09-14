---
title: 2026-02-14 第一個月回顧
type: review
status: frozen
updated: 2026-02-14
scope: all-client-work-2026-01-04-to-2026-02-14
authority: repo-evidence-plus-user-decision
confidence: source-backed
---

# 2026-02-14 第一個月回顧

> 這是時間切片，**寫完凍結**。後來的變化另寫新頁，不回頭改這一頁。
> 這一頁存在的唯一理由：把平常口語的「上線了」「做好了」拆成可以查證的層級。

## 結論（三句）

1. 兩個客戶、兩個專案在跑，但**沒有任何一件事通過客戶的文字驗收**。
2. 口語裡的「上線了」在這一個月至少有三種意思，混用會讓人（包括未來的自己）高估進度。
3. 最大的風險不是做不完，是**會動到外部的動作沒有人擋在中間**。

## 逐案 evidence 與誠實狀態

| 項目 | 2026-02-14 evidence | 誠實狀態 |
|---|---|---|
| [[proj-brand-site-relaunch]] | 本機預覽截圖 4 張（2026-02-12）；客戶案 repo 有提交；靜態主機仍是舊站 | committed：是。deployed：**否**。client accepted：**否**（客戶只回了修改意見） |
| [[proj-weekly-report-bot]] | 每週實際跑；兩個客戶都收過報告 | committed：是。deployed：是（本機工具，跑起來就算）。client accepted：**未問過**——客戶收了信不等於認可格式 |
| [[skill-weekly-client-report]] | 2026-02-03 晉升；兩客戶 × 三週；小華重現一次 | 流程層級可信。但「門檻本身」只有一個樣本，見 [[open-questions]] |
| [[skill-client-feedback-triage]] | 兩次實跑紀錄 | 草稿。**不要**因為它有 SKILL.md 就當它可信 |
| 乙書室這條線 | 只有每週報告，沒有其他交付物 | 刻意不開 project card。為了湊數開空卡比沒有卡更糟 |

## 「上線了」的三種意思

這個月我至少對三件不同的事說過「上線了」，這裡把它們分開：

- **committed**：程式碼進了版控。只證明東西存在、改動可追。
- **deployed**：東西跑在客戶看得到的地方。只證明它在運作，不證明它是對的。
- **client accepted**：客戶以**文字**說了可以。這一欄整個月都是空的。

以後三者分開寫。任何一張卡的 `status` 是 `production`，都要能指出 client accepted 的那封信。

## 風險清單（寫完當下）

1. **寄送沒有人工核准點。** 週報產生器跑完會直接寄；`--preview` 旗標沒有人驗過它到底跳過什麼。
   → 本週沒有動它。
2. **沒有測試環境。** 部署等於上線（[[02-environment]]）。上線前的手動快照是唯一的回頭路。
3. **需求 authority 靠慣例。** 口頭與文字的界線這個月都是臨場判斷的，沒寫成規則。
4. **`unknown` 工時的處理沒定案。** 見 [[open-questions]] 的 `report-unknown-handling`。

## 後來發生了什麼（2026-02-20 補記，不改上文）

風險 1 在 2026-02-18 實現了：`--preview` 真的把未定稿的信寄給兩個客戶。
處置見 [[proj-weekly-report-bot]] 的現行有效段與 [[03-known-traps]] 第 3 條。
風險 3 在 2026-02-10 已經先一步解決（[[open-questions]] 的 `client-feedback-authority`）。

> 這一段是**補記**，只說明後續指向哪裡，不修改上面凍結的內容。
> 一份 review 的價值在於它記錄了「當時我們知道什麼」，改掉就沒了。

回 [[index]] · [[log]] · [[projects]]
