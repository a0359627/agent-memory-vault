# Sample Vault — 小明工作室（全部虛構）

> 這是一個**已經用了六週**的知識庫範例。人、客戶、案子、事故全是編的；
> 真正要看的是欄位、狀態詞與寫法紀律：一頁怎麼標來源、怎麼標範圍、怎麼被取代。
>
> 別把這裡的內容複製進你自己的 vault。要複製的是形狀，不是內容。

## 背景設定

小明是一人工作室的負責人，偶爾找小華接案支援，主要做小店家的網站與內容。
2026-01-04 建立這個 vault，到 2026-02-20 為止累積了兩個客戶（甲咖啡館、乙書室）、
兩個專案、一支已晉升的 skill、一支還在孵化的草稿，以及四條被咬出來的陷阱。

## 怎麼讀（15 分鐘）

1. **先讀 [03-wiki/log.md](03-wiki/log.md)。** 八則紀錄就是這個 vault 的劇本，
   從 `init` 到 `supersede` 各一則。其餘每一頁都能在 log 裡找到它是哪一則寫出來的。
2. **再讀 [03-wiki/index.md](03-wiki/index.md)。** 看一個長好之後的入口長什麼樣：
   六條導航路徑指向的是「現在該讀哪一頁」，不是全部檔案的清單。
3. **然後挑三組對照看：**
   - **未晉升 vs 已晉升**：[03-wiki/skill-client-feedback-triage.md](03-wiki/skill-client-feedback-triage.md)
     （只有一個客戶驗證過，`draft`）對照
     [03-wiki/skill-weekly-client-report.md](03-wiki/skill-weekly-client-report.md)（兩個客戶各三週，`active`）。
     兩張卡的差別就是抽取門檻。
   - **被取代的主張**：[03-wiki/proj-weekly-report-bot.md](03-wiki/proj-weekly-report-bot.md)
     頁頂是現行有效段，底下整段舊設計標 `superseded` 留著。歷史不刪，但也不准冒充現況。
   - **誠實的狀態**：[03-wiki/review-2026-02-14-first-month.md](03-wiki/review-2026-02-14-first-month.md)
     把口語的「上線了」拆成 committed／deployed／client accepted 三種證據。
4. **最後看原文與彙編的分工**：[02-raw/client-brief-2026-01/](02-raw/client-brief-2026-01/SOURCE.md)
   是不可變原文（收進來就不再編輯），[03-wiki/ref-client-brief-2026-01.md](03-wiki/ref-client-brief-2026-01.md)
   才是可以被新證據修訂的結論頁。

## 這裡刻意示範的六件事

| 做法 | 去哪一頁看 |
|---|---|
| 高影響主張帶 `status`／`source`／`observed_at`／`scope`／`authority`／`confidence`／`revisit_when` | [03-wiki/ref-client-brief-2026-01.md](03-wiki/ref-client-brief-2026-01.md) |
| 偏好分 `current` 與 `candidate`，範圍受限的另開一節 | [01-profile/01-preferences.md](01-profile/01-preferences.md) |
| Open question 從 Active 走到 Answered，答案要記 Authority | [03-wiki/open-questions.md](03-wiki/open-questions.md) |
| 取代不是覆寫：新段在上、舊段標 `superseded` 在下 | [03-wiki/proj-weekly-report-bot.md](03-wiki/proj-weekly-report-bot.md) |
| 陷阱寫成「症狀／根因／驗證方法／可貼上的修法」 | [01-profile/03-known-traps.md](01-profile/03-known-traps.md) |
| 草稿只在孵化區，晉升後刪草稿不留兩份分歧全文 | [05-skills-drafts/client-feedback-triage/SKILL.md](05-skills-drafts/client-feedback-triage/SKILL.md) |

## 這裡刻意**沒有**的東西

- 沒有 `AGENT-RULES.md`／`ROUTING.md`／`CLAUDE.md` 這些根目錄規範檔——那些在 `template/` 有完整版，
  這個範例只示範內容頁怎麼長。
- 沒有 `99-secrets-*`。範例不需要秘密，你的 vault 也不該把秘密的**值**寫進 Markdown。
- 沒有 `08-skill-base/` 鏡像。已晉升的那支 skill 放在 `skills-promoted/` 只是為了讓你在同一個資料夾裡
  看到它；真實 vault 的活檔位置由 `ROUTING.md` 決定。

## 你可以拿它做什麼

- 用 `python3 tools/bootstrap.py ~/my-vault --with-sample` 建自己的 vault 時，
  這份會被複製到 `~/my-vault-sample/`，跟主 vault 分開放，不會污染你的內容。
- 把 [skills-promoted/weekly-client-report/SKILL.md](skills-promoted/weekly-client-report/SKILL.md)
  當成「一支通過門檻的 skill 長什麼樣」的對照組。
- 照 repo 的 `docs/walkthrough-first-ingest.md` 先逛一遍這裡，再用你自己的第一份來源做一次。
  （這一頁被複製出來之後就離開 repo 了，所以這裡只寫路徑不給連結。）
