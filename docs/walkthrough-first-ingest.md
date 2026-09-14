# Walkthrough 1 — 第一次把一份來源沉澱進來

這條路走完大約 30 分鐘，分兩半：**先逛一個已經填滿的範例 vault**（看終點長什麼樣），
**再拿你自己的一份來源做一次**（自己走到終點）。

前置：已經照 [quickstart.md](quickstart.md) 建好 `~/my-vault`，並用 `--with-sample`
產生了 `~/my-vault-sample/`。沒加也沒關係，範例 vault 就在這個 starter 的 `examples/sample-vault/`。

---

## 第一半：沿著別人的 log 逛一遍

打開範例 vault 的 `03-wiki/log.md`。它是一份劇本——八則紀錄，
從 `init`（建庫）一路走到最後的 `supersede`（新結論取代舊結論），
中間經過 ingest（新來源進來）、update（既有頁被修訂）、promote（草稿升成正式能力）與 review（時間切片盤點）。

**逛法**：一則一則往下讀，每讀一則就去點它提到的那幾頁。你在找的是這五件事：

1. **原文與結論是分開的。** `02-raw/` 底下那份來源你可以逐字看見，
   而「所以我們決定怎麼做」寫在 `03-wiki/` 的彙編頁——兩者互相指得到，但不互相取代。
2. **每個高影響主張都說得出自己的身世。** 頁面的 frontmatter 有 `status`、`source`、`scope`、`authority`。
   看一眼 `scope`：範例裡有一條偏好明確寫著「只適用單一客戶，不外推」——這一行就是它不會變成全域規則的原因。
3. **舊結論沒有被刪掉。** 找到那張標了 `superseded` 的段落，看它怎麼指向新的那一段。
   歷史留著，但現行有效的那份放在頁面最上面。
4. **未知有自己的位置。** `03-wiki/open-questions.md` 分 Active／Answered／Stale 三段；
   看一則從 Active 移到 Answered 的，它多了 `Authority` 與適用範圍——**答案沒寫範圍就會被外推。**
5. **「上線了」被拆開講。** 範例的 review 頁把成果分成 committed／deployed／客戶接受三種狀態，
   兩欄並排：一欄證據，一欄誠實狀態。這是整個 vault 最值錢的一頁排版。

逛完再回頭看 `03-wiki/index.md`：它不是目錄，是六條「什麼情境 → 先讀哪一頁」的入口。

> 逛的時候刻意不要看 `05-skills-drafts/` 那支草稿，它是下一條 walkthrough 的主角。

---

## 第二半：拿你自己的一份來源做一次

挑一份**你這週真的看過、而且以後還會用到**的東西：一篇技術文章、一份會議逐字稿、
一個外部 repo 的 README、客戶寄來的需求說明。不要挑「以後可能會有用」的——那種東西沉澱下來只會變垃圾。

在 `~/my-vault` 開你的 agent，說：

```text
我要把這份來源沉澱進 vault。請先讀 AGENT-RULES.md、ROUTING.md 與
03-wiki/memory-metabolism.md，再依 ingest 流程處理，最後告訴我你改了哪幾個檔、
以及哪些結論你標成了 candidate 而不是 current。
```

（裝了 `obsidian-vault` 這支 skill 的話，說「把這份寫回我的知識庫」就會走同一條流程。）

然後**盯著它做這六個變化**。少一個就是這次 ingest 沒做完：

| # | 應該出現的變化 | 怎麼確認 |
|---|---|---|
| 1 | `02-raw/<主題>/` 多了原文 ＋ 一張出處卡 `SOURCE.md` | 出處卡要有來源、抓取版本、授權、抓取日、「為何留」。格式見 [template/02-raw/README.md](../template/02-raw/README.md) |
| 2 | `03-wiki/` 多了（或更新了）一張彙編頁 | 裡面是摘要、推論與關聯，**不是原文複製**；frontmatter 有 `status`／`source`／`scope`／`authority` |
| 3 | 受影響的既有頁被標了狀態 | 若這份來源推翻了舊結論，雙向標 `supersedes`／`superseded_by`；矛盾但都可信就標 `contested`，兩邊都留 |
| 4 | `03-wiki/index.md` 多一列 | 新頁要能從入口點得到，否則它就是孤兒；`./bin/check-routing.sh` 會抓出來 |
| 5 | `03-wiki/log.md` 追加一則 | 格式 `## [YYYY-MM-DD] ingest \| 標題`，內文三到六行：改了哪幾頁、依據什麼來源、做了什麼檢查 |
| 6 | `03-wiki/open-questions.md` 有動靜 | 新的未知進 Active，或某則因為這份來源可以移到 Answered／Stale |

第 6 個常常是「沒有變化」——那也要說出來。**沒有新增 durable knowledge 時，允許 no-op**；
讀完一份來源不等於必須產生一頁筆記。假裝有收穫比沒收穫更貴。

最後跑一次：

```bash
cd ~/my-vault && ./bin/check-routing.sh
```

看 `errors` 裡的壞連結與 `warnings` 裡的 orphan 提示。這是你的第二個綠燈。

---

## 三種常見錯法

### 錯法一：在 `02-raw/` 裡下結論、或順手「整理一下」原文

原文一旦被編輯，你就永遠回答不了「我當初到底是根據什麼做這個決定的」。
半年後你會想知道的不是「我現在怎麼理解」，而是「我當時看到的是什麼」。

**症狀**：`02-raw/` 底下出現條列式重點、出現「所以我們決定…」、出現後來補上的更正。
**修法**：原文照貼不動；所有摘要、推論與現行結論寫到 `03-wiki/` 的彙編頁，並在出處卡寫清楚彼此的關係。
轉檔產生的東西（簡報轉 Markdown、影片轉逐字稿）是 **derived 不是原文**——
放在 `derived-<工具>/` 子資料夾，記下 canonical 原檔在哪與重轉指令，原檔更新就重轉覆蓋，不要手改。

### 錯法二：把 agent 的推論直接寫進 `01-profile/`

`01-profile/` 會被每個非瑣碎任務讀到。寫進去一條，就是改變未來所有 session 的行為。

**症狀**：出現「使用者似乎偏好…」「通常會…」這類沒有來源的句子；
或者一次趕工時說的「這次先這樣」被寫成了永久偏好。
**修法**：agent 從行為推測的東西一律先標 `status: candidate` 加生效日，或先放進 open questions。
**頻率不是同意，沉默不是核准。** 單案才成立的偏好一定要寫 scope，沒寫 scope 它就會被外推。

### 錯法三：只往檔尾追加，不回頭把過期的狀態標作廢

`log.md` 是 append-only，但那句話的意思是**「不改寫歷史」**，不是「寫完就不用管了」。

**症狀**：某張 project card 或 wiki 頁還留著三天前的狀態描述（「目前全部還在測試中」），
而實際上兩天前就已經改了。下一個讀那一頁的人——或 agent——會先撞到那句過期的話，然後照它行動。
**過期的狀態描述冒充現況，比完全沒寫還糟。**
**修法**：狀態改變時，另寫一則 `supersede` 追加在 `log.md` 的**檔尾**，回到原本那則加一行指向新的那則，
再把現況更新到它真正該住的地方——該主題自己的頁（project card 的「現行有效的決策」區）。
log 的歷史那一段原樣保留。

---

## vault 和平台自己的記憶，誰管什麼

Claude Code 有自己的專案記憶（`~/.claude/projects/<project-id>/memory/`），
Codex 也有它自己的一套。它們跟這個 vault**不是競爭關係，是分工**：

| | 放什麼 | 特性 |
|---|---|---|
| **這個 vault** | canonical：跨專案理解、確認過的偏好、陷阱、project card、來源 | git-backed、有 diff、可 review、換機器帶得走 |
| **平台 auto-memory** | 短期指標與單次 correction：「這個 session 學到的小修正」「canonical 在哪」 | 平台自動寫入、格式由平台定、容易累積、不進你的版本控制 |
| **`project-memory` skill** | 單一 repo 的決策、驗收證據、陷阱與下一步 | 寫在那個 repo 裡，跟著 code 一起版控 |

一條規則就夠：**永久偏好的 canonical 永遠在 `01-profile/`。**
平台記憶只放「短期 correction ＋ 指回 canonical 的指標」，不複製一份會分岔的永久偏好——
兩份偏好遲早會不一致，而且沒有人會收到通知。

反過來也一樣：`bin/skill-sources.json` 的 `memory_source` 出廠值是 `null`，
**這個 starter 預設不把任何平台記憶目錄同步進 vault。** 要打開之前先讀
[skills-and-sync.md](skills-and-sync.md)——不加限制的記憶來源會把這台機器上**每個**專案的記憶
都吸進你的 vault，連同那些目錄名稱裡的絕對路徑。

---

## 走完之後

- 再做兩三次，讓 log 長出節奏感。
- 然後走 [walkthrough-first-skill.md](walkthrough-first-skill.md)：把一段你已經重複做過的工作抽成 skill。
- 想知道每個設計為什麼長這樣，回 [concepts.md](concepts.md)。
