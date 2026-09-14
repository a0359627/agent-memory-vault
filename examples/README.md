# examples/ — 三組看得到的對照組

`template/` 告訴你一個 vault 的**骨架**長什麼樣；這裡告訴你它**長好之後**長什麼樣。
三組範例全部虛構——人、客戶、案子、事故都是編的——但形狀是真的：
欄位、狀態詞、取代關係、以及「什麼證據支持什麼結論」的寫法。

> 這個資料夾不會被 `bootstrap.py` 寫進你的 vault。
> 加 `--with-sample` 時，只有 `sample-vault/` 會被複製到 `<target>-sample/`，
> 跟你的主 vault 分開放。

## 三組範例

| 目錄 | 是什麼 | 什麼時候看 |
|---|---|---|
| [sample-vault/](sample-vault/README.md) | 一個用了六週的完整 vault（小明工作室，虛構） | 動自己的知識庫之前。先看終點，再決定起點 |
| [first-skill/](first-skill/weekly-status/SKILL.md) | 一支寫完並測過的第一支 skill | 要抽第一支 skill 時 |
| [memory-nodes/](memory-nodes/MEMORY.md) | 平台端 auto-memory 的節點格式 | 搞不清楚「記憶」和「vault」差在哪時 |

## 1. `sample-vault/` — 長好之後長什麼樣

一個一人工作室用了六週的知識庫：兩個客戶、兩個專案、一支已晉升的 skill、
一支還在孵化的草稿、四條被咬出來的陷阱，以及一次誤寄事故。

入口是 [sample-vault/03-wiki/log.md](sample-vault/03-wiki/log.md)：
八則紀錄剛好是八種 type（`init`／`ingest`／`update`／`promote`／`draft`／`answer`／`review`／`supersede`），
而且其餘每一頁都能在那裡找到它是哪一則寫出來的。**從 log 讀起，不要從資料夾讀起。**

（其中 `draft` 與 `answer` 是這個範例 vault **自訂**的。`template/03-wiki/log.md` 的基本表是七個
type，自訂可以，但要像範例那樣在 log 檔頭寫明是自訂的——照抄範例的形狀之前先看那一段。）

裡面刻意示範三組對照：

- **未晉升 vs 已晉升**：一支只在單一客戶驗證過的草稿，對照一支兩客戶各三週、換人可重現的活檔。
  兩張卡的差別就是抽取門檻長什麼樣。
- **現行 vs 被取代**：一張 project card 頁頂是現行有效段，底下整段舊設計標 `superseded` 留著。
  歷史不刪，但也不准冒充現況。
- **做完了 vs 上線了 vs 驗收了**：一份 review 把口語的「上線了」拆成
  committed／deployed／client accepted 三欄證據，其中一欄整個月都是空的。

導讀見 [sample-vault/README.md](sample-vault/README.md)。

## 2. `first-skill/` — 一支夠用的第一支 skill

[weekly-status/SKILL.md](first-skill/weekly-status/SKILL.md) 是
[walkthrough-first-skill](../docs/walkthrough-first-skill.md) 走完之後的完成態。
它刻意很小：沒有 scripts、沒有 references、沒有 assets，只回答六個問題——
何時啟用、要什麼輸入、按什麼順序、什麼不能猜、何時停下來問人、什麼算完成。

[weekly-status/TESTS.md](first-skill/weekly-status/TESTS.md) 才是重點：
五類 prompt（直接觸發／間接觸發／不應觸發／輸入不完整／危險邊界）各跑一次，
第一輪有兩個 `fail`，修完再跑第二輪。**一支沒測過的 skill 只是一段比較長的 prompt。**

## 3. `memory-nodes/` — 那不是同一種記憶

如果你用的 agent 平台本身有記憶功能，你會有兩層東西都叫「記憶」，很容易混。
[memory-nodes/MEMORY.md](memory-nodes/MEMORY.md) 用一張表把分工講清楚，
四個節點（user／project／feedback／reference）示範每一型該寫什麼：

- **vault** 保存有來源、有範圍、可被取代的理解，有版控，是 canonical。
- **平台記憶**保存「這句話是什麼意思」的短期指標與 correction，過時就改掉。
- 兩邊衝突時，以 vault 為準。同一件事兩邊都寫，就一定會分歧。

## 怎麼用這些範例

1. 照 [walkthrough-first-ingest](../docs/walkthrough-first-ingest.md)：**先逛一遍 `sample-vault/`，
   再用你自己的第一份來源做一次。** 逛過終點的人比較不會把 `02-raw/` 當垃圾桶。
2. 要動手建自己的：[quickstart](../docs/quickstart.md)。
3. 要裝 starter skills：見 [skills/README.md](../skills/README.md) 與 `tools/install_skills.py`。

## 最後一句

範例的內容沒有一個字值得複製。值得複製的是：
**每一句高影響的話，旁邊都寫著它從哪裡來、範圍到哪、什麼條件下要重問。**
