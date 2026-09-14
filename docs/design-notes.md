# 刻意不做的事

一個工具真正的形狀，在它拒絕了什麼。這頁列出每一條「本來可以做、但刻意沒做」的決定，
以及當時的理由。理由會過期——所以每條都標了出處，讓你能回頭判斷它現在還成不成立。

出處標「REFERENCES §X」的，在 [REFERENCES.md](REFERENCES.md) 找得到完整的借用與取捨紀錄；
標「設計判斷」的沒有外部來源，就是這個 repo 自己的取捨。

---

## 關於知識庫本身

### 不裝任何 MCP／REST 橋接

最流行的那套做法是替 Obsidian 裝 Local REST API plugin，再用 MCP 接上 agent。這裡走另一條路：
**純 git Markdown，agent 直接讀寫磁碟。** 少一層會壞的橋接，少一個持有 API key 的外掛，
少一個「plugin 更新之後整條鏈斷掉」的故障點。代價是你拿不到 plugin 生態的便利。

> 出處：REFERENCES §A（那條路被明確列為「被拒絕的那條路」）。

### Obsidian 只當唯讀圖譜檢視器

`.obsidian/` 設定隨 template 走，clone 下來就能當 vault 打開。但**沒有任何資料真相依賴 Obsidian**：
不用它的專屬語法當結構，沒裝它也能從 `03-wiki/index.md` 點連結逛完整個庫。
理由是 vault 的壽命應該比任何一個 app 長。

> 出處：REFERENCES §A。

### 沒有獨立的 Areas 資料夾

PARA 的 Projects／Resources／Archives 都在，唯獨少了 Areas。
「持續責任」被拆給 `01-profile/`（個人脈絡）與 `03-wiki/cluster-*.md`（主題星圖）——
因為三層模型要求「來源」與「解讀」分開，而 Areas 天生混著兩者。

> 出處：REFERENCES §A。

### 不宣稱符合任何知識格式規格

frontmatter 的 `status`／`authority`／`supersedes`／`revisit_when` 是自訂欄位，
沒有對齊任何外部規格的 provenance／trust／freshness 欄位，也不輸出符合規格的 bundle。
外部規格在這裡只當**驗證用的對照組**：能一格一格對上，代表設計沒歪；但不承諾相容性，
因為承諾相容就要跟著別人的版本走。

> 出處：REFERENCES §A。

### 不把外部知識工具裝成第四個知識落點

有些工具會在你的 `ROUTING.md` 認得的幾個位置之外，自己長出一個新的知識落點，
並把外部服務的原始資料與授權 token 落在你的 secret 稽核閘門**之外**。
那不是功能問題，是**邊界問題**：路由一旦有第四個落點，「東西該寫到哪」就不再有唯一答案。

> 出處：REFERENCES §A。

---

## 關於 skill

### 上游那一整組只收三支

借來的 skill 只收了三支（寫作原則、對齊拷問、除錯紀律），其餘刻意不收：
整條綁 issue tracker 的流程（個人工作流用不到）、綁特定語言生態的工具（技術棧不符）、
以及「已經有更好的替代」的那幾支。
**「看起來該裝」不是判準**；判準是「它解決的問題，我這個月真的會遇到嗎」。

> 出處：REFERENCES §B（逐支取捨表）。

### 不收領域型 skill

綁特定客戶、產線或內部系統的 skill 一支都沒有。不是因為機敏，是因為**沒有用**：
那類 skill 的價值幾乎都在它綁住的脈絡裡，抽掉脈絡剩下的只是空殼，
讀者拿到只會困惑「這到底在幹嘛」。要長出你自己的那幾支，從抽取門檻開始，
見 [skills-and-sync.md](skills-and-sync.md)。

> 設計判斷。

### 不把 skill 打包成 plugin

自訂 skill 以 standalone 資料夾存在，不打包成唯讀的 plugin bundle。
理由是活檔要能手改、能在地化裁剪、能被鏡像快照還原——plugin 三件都做不到。
plugin 提供的能力照用，只是**只記錄用途與邊界，不混進個人 skill 的快照**。

> 出處：REFERENCES §C。

### frontmatter 不加 `license:` 欄位

整個 repo 是 MIT，授權寫在 LICENSE 與 THIRD-PARTY-NOTICES.md。
SKILL.md 的 frontmatter 只留 `name` 與 `description`，因為那是兩個平台的最小交集，
而且這個 repo 的兩套驗證器**不該對同一份檔案給出不同答案**。

> 設計判斷（規格細節見 REFERENCES §B）。

### 不維護「兩個平台各一份全文」

同一支 skill 不會有 Claude 版和 Codex 版兩份正文。正文只有一份，
另一個平台的目錄放指向它的符號連結。維護兩份全文的下場是它們會慢慢分岔，
而且沒有人會收到通知。

> 出處：REFERENCES §B。

### 不另建一份術語表檔案

有一派做法是在 repo 根放一份共享術語檔降低溝通成本。這裡判定
`03-wiki/index.md` ＋ cluster 頁 ＋ `ROUTING.md` 的固定詞彙已經在做同一件事，
再開一份只會產生**第二份會分岔的術語表**。若哪天詞彙真的開始分岔，這是第一個該回頭看的設計。

> 出處：REFERENCES §C。

---

## 關於上手路徑

### 主路徑是 `bootstrap.py`，不是「clone 即 vault」

不讓你把這個 repo 直接當成自己的 vault。理由是那樣會讓**你的筆記和範本的 commit 混在同一段歷史**裡，
而且你得先手動刪掉一堆範例檔。`bootstrap.py` 產生的是一個乾淨的新 repo，第一個 commit 就只有你的東西。

範例 vault 也因此**不進主 vault**：`--with-sample` 把它複製到 `<target>-sample/`，
逛完可以整個刪掉。

> 設計判斷。

### 不附任何 skill 鏡像

`08-skill-base/` 在新 vault 裡是空的，`snapshot.json` 要等你第一次 `sync --apply` 之後才出現。
不預先塞一份，是因為鏡像是**你的機器的快照**，別人的快照對你沒有意義，
而且會讓第一次 `check` 對著一份假資料說綠燈。

> 設計判斷。

### 預設不同步任何平台記憶

`memory_source` 出廠是 `null`。打開它而不加 allowlist，會把這台機器上**每一個**專案的記憶
吸進 vault，連同那些由絕對路徑編成的目錄 id。
把炸彈預設拆掉，但也在 [skills-and-sync.md](skills-and-sync.md) 告訴你炸彈長什麼樣——
只拆不說，下一個人會再裝回去。

> 設計判斷。

---

## 關於安全與發布

### 用 allowlist，不用 denylist

denylist 忘了列會**悄悄放行**，allowlist 忘了列只會**缺席**。
兩種都會忘，但只有一種會讓你在事後才發現。

> 出處：REFERENCES §D。

### 識別字清單用 HMAC，不用無鹽雜湊

無鹽雜湊可以被字典撞出「這份清單裡有 X」——等於把禁用字表換個形式公開。
HMAC 讓拿到檔案的人**驗不出任何東西**，而 key 留在本機與 CI secret。
代價是：沒有 key 就跑不了那一層，所以設計成 fail-closed 而不是靜默跳過。

> 出處：REFERENCES §D。

### 不用歷史改寫工具切私有歷史

不用 `filter-branch`／`filter-repo` 把私有 repo「洗乾淨」再公開。
commit 訊息與被刪掉的路徑名稱**本身就是私有脈絡**，而且那些工具在 fork、快取與別人已有的 clone 面前
清不乾淨。改成全新歷史的一次性匯出，加上可重複的再匯出機制。

> 出處：REFERENCES §D。

### 外部 secret 掃描工具不列為必跑 gate

裝了就順手跑，但不納入必過的閘門。理由是**必跑的東西必須在每一台機器與 CI 上都存在**，
否則第一個沒裝的人就會學會用 `|| true` 繞過去，然後整條 gate 從此不可信。
repo 自帶兩套**不同**的掃描實作（`tools/publish_check.py` 的 L1 與 `bin/scan_sensitive.py`），而 gate 另外用 `cmp` 確保 `scan_sensitive.py` 與 office kit 的那一份沒有分岔——`cmp` 比的是同一支的兩個副本，證明的是「沒被改壞」，不是「兩種判斷」。前者擋「某一支被改壞」，擋不住「兩支同時判錯」；理由與實際踩過的案例見 `docs/gates.md`。

> 出處：REFERENCES §D。

### 只支援 macOS 與 Linux，Windows 走 WSL

`bin/` 裡有 bash 腳本，skill 入口用符號連結，這兩件事在 Windows 原生環境都不成立。
與其寫一個沒測過的相容層，不如誠實寫「走 WSL」。

> 設計判斷。

---

## 怎麼推翻這頁的任何一條

這些不是信仰。要改任何一條，做三件事：
（1）說出**當初的理由現在哪裡不成立**；（2）說出**新做法的失敗模式是什麼**；
（3）把新的不變條件寫成一道**會擋人的 gate**，而不是一句叮嚀。

三件都做得到，就改。做不到的話，你要的可能只是這次方便。
