# ONBOARDING — 給接手這個 vault 的人或 agent

> 這份文件的目的：讓**另一個人或另一個 agent**接手 `{{VAULT_NAME}}` 時，
> 表現得像 {{OWNER}} 本人就坐在旁邊——不用重新問一遍「這是誰的東西、規矩是什麼」。
> 只講「工作副本怎麼讀、怎麼寫」，不重複 `CLAUDE.md` 或 `01-profile/` 的內容，只指路。

---

## 1. 這是誰的庫、怎麼讀

這是 **{{OWNER}}** 的 canonical 第二大腦／跨專案理解層。git-backed，採三層架構
（Karpathy「LLM Wiki」模型）並加入 [[memory-metabolism]] 定義的記憶代謝：

| 層 | 資料夾 | 規則 |
|---|---|---|
| raw（不可變來源） | `02-raw/` | 貼上的原文、逐字稿、截圖。只讀不改。 |
| wiki（彙編） | `03-wiki/` | 摘要頁／概念頁／index／log，由各 agent 共同維護，互相用雙括號 wikilink 連結。 |
| schema（指令層） | `AGENT-RULES.md` | 共用規範；AGENTS.md／CLAUDE.md 只負責載入。 |

其餘資料夾是 PARA 分類：`00-inbox/`（未分類隨手丟）、`04-projects/`（有期限交付）、
`05-skills-drafts/`（skill 草稿，實戰通過後搬去 `~/.claude/skills/` 或 active project repo，
不留兩邊分歧版本）、`06-reference/`（本庫內的快查）、`07-archive/`（非活躍留作召回）、
`08-skill-base/`（skill 活檔的可遷移鏡像——**編輯永遠在活檔位置，鏡像只由 sync 腳本更新**；
換電腦照根目錄 `MIGRATE.md` 還原）。

**進入方式**：先開 `03-wiki/index.md`——它是整個知識圖譜的入口，連到各主題叢集（star hub）
與索引頁。沒有 Obsidian 圖譜可看時，就從這個檔案開始點連結逛。

**理解記憶的方式**：再讀 [[memory-metabolism]] 與 [[open-questions]]。工作軌跡先是 evidence，
AI 的整理先是 candidate；沒有足夠來源、scope 或人類確認，不得直接寫成永久偏好或可執行決策。

---

## 2. {{OWNER}} 的工作原則（濃縮自 `01-profile/`）

完整版見 `01-profile/`（canonical，git-backed，比平台自有的薄記憶指標更權威）。
接手前至少掃過這四條——每條在 `01-profile/01-preferences.md` 補成自己的版本：

1. **語言**：{{LANG}}。
2. **決策風格**：（填一句，例如「給明確建議，不要列一堆選項要他自己挑」。）
3. **做事順序**：（填一句，例如「先做能跑的最小版本再加東西」。）
4. **查證邊界**：（填一句，說明哪些事實不准憑記憶答、要查到哪裡為止。）

---

## 3. 常用入口地圖

> 這三列是範例格式；把它換成你自己的常用入口，每列都要指向真的存在的頁。

| 想找什麼 | 去哪 |
|---|---|
| 目前有哪些專案、各自什麼狀態 | [[projects]] |
| 目前有哪些 skill、分幾條線 | [[skills]] |
| 記憶如何形成、更正、取代、過期與遺忘 | [[memory-metabolism]]／[[open-questions]] |

---

## 4. 給接手 agent 的行為守則

**開工前的讀取順序**（不要跳過，順序有意義）：

1. Codex 讀 `AGENTS.md`；Claude Code 讀 `CLAUDE.md`（本目錄根，schema 層——兩者共用歸檔、記憶代謝與硬規則）
2. `AGENT-RULES.md`，再依任務讀取 profile 模組；環境與陷阱按需讀取並重驗
3. [[memory-metabolism]] 與 [[open-questions]]（避免把過時理解或 AI 推論當成事實）
4. 跟你這次任務相關的 cluster 頁（`03-wiki/cluster-*.md`）——先看星狀總覽再進單頁，
   不要一開始就鑽進單一 project 頁失去脈絡。

**Ingest 工作流**（有新來源或新想法進來時，`AGENTS.md`／`CLAUDE.md` 已定義，這裡只提醒不要漏步）：
判斷來源 vs 想法 → 來源存 `02-raw/`（不改原文）→ 在 `03-wiki/` 寫或更新彙編頁 →
依 [[memory-metabolism]] 標來源、時間、scope、authority 與狀態 → 將未決問題維護在 [[open-questions]] →
更新 `03-wiki/index.md` → append 一行到 `03-wiki/log.md`（格式 `## [YYYY-MM-DD] ingest | 標題`）。
新證據改變舊理解時要建立取代／爭議關係，不可靜默覆寫。

**Secrets 鐵律**（跨越所有任務，優先權高於「把事情做完」）：
- 任何 API key / token / 密碼的**值**絕不寫入這個 vault 的任何檔案，也絕不出現在你的
  回應文字裡。需要提及時只寫「key 的名稱 + 用途 + 放在哪個檔案路徑」。
- 彙編 raw 來源時，若原文貼了 key，**絕對不要**把它複製進任何 markdown 摘要頁。
- 看到疑似落單的 key/密碼字串，直接標記位置回報，不要嘗試「順手清理」而搬到別的檔案。

---

## 5. Secrets 放在哪（本文件只記位置，不記值）

> 表頭與一列範例；照這個格式補上你自己的項目。規則見 [06-reference/secrets-hygiene.md](06-reference/secrets-hygiene.md)。

| 東西 | 放哪 |
|---|---|
| 各專案的 API key／token | 各專案自己 gitignored 的 `.env`，runtime 才讀 |

**一句話**：值永遠不進 git、不進這個 vault、不進任何 agent 的回應文字；vault 只負責記「去哪裡找」。

---

回 [[index]]（`03-wiki/index.md`）
