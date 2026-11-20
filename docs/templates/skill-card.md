# 範本：skill card

放在 `03-wiki/skill-<name>.md`。**卡片只導航，不複製 skill 正文。**
正文只有一份，在活檔位置（或那個 active repo 裡）；卡片回答的是
「這支是什麼、什麼時候用、跟隔壁那支怎麼分工、它被改過什麼」。

---

```markdown
---
title: skill — <name>
type: skill-card
status: <current | watchlist | stale | superseded，草稿寫 watchlist>
subject_status: <active | draft | deprecated>
scope: <跨專案 | 只對某個 repo 成立>
updated: <YYYY-MM-DD>
verified_at: <YYYY-MM-DD，你最後一次確認活檔還在、還適用的日期；草稿可整行刪掉>
verification: <怎麼確認的：實跑了一次 | 讀過正文 | 只確認檔案存在>
promoted_from: <05-skills-drafts/<name>，不是從草稿晉升的就整行刪掉>
---

# <name>

## 一句話

<它替你做什麼。寫得讓半年後的自己看得懂。>

## 什麼時候觸發

- <情境一>
- <情境二>
- **不要**在 <相鄰但不適用的情境> 用它，那種情況請走 <另一支>。

## 本體在哪

- 活檔：<共用 skill 目錄底下的 `<name>/`，或該 active repo 的路徑>
- 登錄：`bin/skill-sources.json` 的 `shared_skills`（沒登錄就不會進鏡像）
- 路由規則見 `ROUTING.md`

## 與相鄰能力的分工

| 情境 | 用哪一支 | 為什麼不是這支 |
|---|---|---|
| <> | <> | <> |

## 判準摘要（三條以內，細節在正文）

1. <這支 skill 真正值錢的那個判斷，不是步驟>

## 實跑紀錄

| 日期 | 情境 | 結果 | 要改什麼 |
|---|---|---|---|
| <YYYY-MM-DD> | <> | <觸發了嗎、輸出可用嗎> | <> |

## <YYYY-MM-DD> 取代說明

> 正文有過重大修改時加一段，說明**改了什麼、為什麼、舊版哪裡不再成立**。
> 這一區是 append 的，舊的段落保留。

- <改動一句話>。原因：<>。影響：<誰要重新學一次>。

回 [[skills]] · [[index]]
```

---

## 填寫要點

- **卡片和正文分歧時，正文是真相。** 卡片過期了就更新卡片，不要反過來改正文遷就卡片。
- 「與相鄰能力的分工」那張表是這張卡最值錢的部分。相似名稱不代表可以刪掉其中一支，
  但也不代表兩支都要跑——寫清楚哪個情境走哪一支。
- 草稿階段的 skill 也可以有卡片：`status: watchlist`、`subject_status: draft`，本體指向 `05-skills-drafts/<name>/`。
  晉升之後改成 `status: current`、`subject_status: active`，填 `promoted_from` 與 `verified_at`、
  把本體路徑改掉，並在取代說明區記一行。
- **`verified_at` 是這張卡的保鮮期。** `current` 的 skill 卡沒有它、或它超過 180 天，
  `./bin/check-routing.sh` 會提醒你回來確認：活檔還在嗎、觸發情境還成立嗎。
  一支沒人驗過的 skill 比沒有 skill 更糟，因為它會很有把握地做錯。
  `verification` 老實寫你做到哪一層；「只確認檔案存在」也是有效資訊。
- 不再使用的 skill：卡片 `status: stale`、`subject_status: deprecated`；被另一支取代就用 `superseded` 並填 `superseded_by`。
