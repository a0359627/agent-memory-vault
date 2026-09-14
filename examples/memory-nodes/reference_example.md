---
name: skill-promotion-threshold-origin
description: 「兩客戶 × 三週 × 換人可重現」這個晉升門檻是 2026-02-03 事後歸納的，只有一個樣本，尚未定案
metadata:
  node_type: memory
  type: reference
  modified: 2026-02-05
---

工作室目前判斷一支草稿 skill 能不能晉升，用三個條件（三條都要成立）：

1. 在**兩個以上不同客戶**身上跑過；
2. 同一份流程**連續三週格式沒再改**；
3. **換一個人**照著也做得出一樣的結果。

**scope：** 只在這個工作室的 skill 晉升判斷上使用。不是通用方法論，也不要拿去評價別人的流程。

**source：** vault 的 `03-wiki/skill-weekly-client-report.md`「2026-02-03 晉升說明」段；
爭議記在 `03-wiki/open-questions.md` 的 `draft-promotion-threshold`（狀態 Active）。

**Why:** 這三條不是先想好再套用的，是 `weekly-client-report` 晉升**之後**回頭歸納的，
樣本數是一。它現在的地位是「目前的做法」，不是「已驗證的規則」——
差別在於：前者可以被下一個案例推翻，後者不行。標錯會讓人拿它去擋別人的提案。

**How to apply:**
- 有人問「這支可以晉升了嗎」，用這三條當**提問清單**，不當通過標準：
  逐條問「你的證據是什麼」，而不是逐條打勾。
- 三條不成立就留在 `05-skills-drafts/`，並在卡上寫清楚**差在哪一條**。
  對照組看 `03-wiki/skill-client-feedback-triage.md`：它只滿足一條半，卡上就是這樣寫的。
- 有第二支 skill 走完同一條路之前，**不要**把這三條寫進 `01-profile/01-preferences.md`
  當成長期偏好。一個樣本歸納出來的規則升格太快，就會變成沒人敢質疑的教條。
- 這條被推翻時，是好事：去 open-questions 把 `draft-promotion-threshold` 移到 Answered，
  並記下 Authority。

相關：[[feedback_example]]、[[user_example]]
