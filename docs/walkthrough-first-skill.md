# Walkthrough 2 — 第一次把一段工作抽成 skill

skill 不是「把 prompt 存起來」。它是**把一段你已經重複做過、而且每次都要動腦的工作，
寫成下一次可以預測地重跑的東西**。這條路走完大約 45 分鐘。

---

## 第 0 步：抽取門檻自測（兩條都中才抽）

先誠實回答兩題。**兩題都是「是」才往下走。**

1. **會再用到嗎？** 不是「這次很麻煩」，是「下個月、下一個客戶、下一個專案還會做一次」。
   只做一次的東西寫成 skill，你會多維護一個沒人叫的檔案。
2. **有判斷含量嗎？** 有取捨、有判準、有容易踩的坑嗎？
   如果它從頭到尾是固定的指令序列——寫成腳本，放進 `bin/`，然後在 skill 裡引用那支腳本就好。

兩題都「是」之後，再問第三題（這題決定它住哪，不決定要不要抽）：
**它跨專案成立，還是只對某一個 repo 成立？** 跨專案的進共用活檔，單一 repo 的留在那個 repo 裡跟 code 一起版控。

> 順便：如果你答不出「跑完之後，怎麼知道它做對了」，那你還沒準備好寫這支 skill。
> 這個問題的答案就是下面第 3 步的完成判準。

---

## 第 1 步：看一組「未晉升 vs 已晉升」的對照

範例 vault 裡刻意放了一對：

- **未晉升的那支**在 `05-skills-drafts/` 底下，旁邊有一份 `notes.md` 記著兩次實跑觀察。
  它沒有晉升，理由寫得很清楚：**只在一個客戶身上驗過**。一次成功不是判準，是樣本數 1。
- **已晉升的那支**在範例的 `skills-promoted/` 底下，是完成態：
  description 寫得出觸發時機、正文寫的是判準不是步驟、有明確的完成條件。

把兩份並排讀五分鐘。你在找的差別是這三個：

| | 草稿 | 已晉升 |
|---|---|---|
| `description` | 「幫我做週報」 | 寫清楚**什麼時候**該用它，含觸發語，讓 agent 自己判斷得出來 |
| 正文 | 一串步驟 | 判準、取捨、容易踩的坑；步驟只是骨架 |
| 結尾 | 沒有 | 完成判準（做完長什麼樣），以及**什麼情況下應該不做**（no-op） |

`notes.md` 才是晉升與否的依據——**靠紀錄，不靠印象。**

---

## 第 2 步：在孵化區寫草稿

```bash
mkdir -p ~/my-vault/05-skills-drafts/weekly-status
$EDITOR ~/my-vault/05-skills-drafts/weekly-status/SKILL.md
```

最小結構就兩樣：YAML frontmatter ＋ 正文。

```markdown
---
name: weekly-status
description: 把這週的零散進度整理成一頁對外週報。當使用者說「寫週報」「這週的進度整理一下」
  「給客戶的狀態更新」時使用。輸入是散落的筆記或 commit 訊息，輸出是一頁分層的狀態報告。
---

# 週報

## 什麼時候用（與什麼時候不要用）
...

## 判準
1. 進度分層描述：實作／測試／合併／部署／對方接受是五件事，不能混成「做好了」。
2. 沒有證據的項目一律寫「未驗證」，不補話。
...

## 完成判準
- 每一條都指得出證據（commit、連結、檔案）或明確標為未驗證。
- 對方讀完知道「這週我該做什麼決定」。
```

規則只有三條：`name` 必須小寫、必須等於資料夾名稱；`description` 要寫**何時使用**（含觸發語）；
frontmatter 只放 `name` 與 `description`——這是兩個平台都吃得下的最小交集。

旁邊開一份 `notes.md`，之後每次實跑就記一行。

**Codex 讀者可以少打一半的字**：這個 repo 的 office kit 附了現成的鷹架與驗證器，
`office-agent-starter-kit/.agents/skills/build-office-skill/scripts/` 底下的 `create_skill.py`
會替你建好骨架，`validate_skill.py` 檢查 frontmatter 是否合法。
（office kit 整包是**給 Codex 讀者的教學包**，路徑慣例是 `.agents/skills/`，
不要用 `install_skills.py` 去裝它裡面的 skill。）

---

## 第 3 步：五類測試

不要只試「它會不會動」。五類各至少一則，把 prompt 與結果記進 `notes.md`：

| # | 類型 | 你在測什麼 | 通過長什麼樣 |
|---|---|---|---|
| 1 | **正面觸發** | 明說觸發語時會不會叫它 | 叫了，而且輸出符合完成判準 |
| 2 | **側面觸發** | 只描述情境、不說名字時會不會叫它 | 叫了。沒叫＝你的 `description` 沒寫出「何時使用」 |
| 3 | **反面不觸發** | 相鄰但不該用它的情境（例如「寫一篇對外文章」而不是週報） | **沒**叫它。會誤觸＝ description 太貪心，會在不相干的任務裡吃你的 context |
| 4 | **缺輸入／邊界** | 該有的資料不在時 | 它問你，而不是硬編一份出來 |
| 5 | **完成判準與 no-op** | 輸出能不能通過你自己寫的完成判準；沒東西可做時會不會說「這次不需要」 | 兩者都做到 |

第 3 類最常被跳過，也最貴。一支會亂觸發的 skill 比沒有 skill 糟：
它每次都要佔 context，而你還得花力氣叫它閉嘴。

跑到「五類都穩定」才算可以晉升。**還沒穩定就是還在孵化，不是失敗。**

---

## 第 4 步：晉升（單向）

穩定之後擇一，然後**刪掉草稿**——不要留兩份會分岔的全文。

**A. 跨專案通用 → 搬到共用活檔位置**

```bash
mv ~/my-vault/05-skills-drafts/weekly-status ~/.claude/skills/weekly-status   # Claude Code
# Codex 的使用者 skill 目錄是 ~/.agents/skills/
```

Claude Code 讀者就這樣，沒有別的步驟：**一個資料夾＝一支 skill**。
要從這個 starter 拿現成的幾支，用安裝器（預設只預覽）。
以下（含第 5 步）的 `agent-memory-vault/` 都是 clone 下來那個資料夾的相對路徑，
指令要在它的上一層執行，或換成它的實際路徑：

```bash
python3 agent-memory-vault/tools/install_skills.py                          # 看會發生什麼
python3 agent-memory-vault/tools/install_skills.py grill-me --apply         # 真的裝
python3 agent-memory-vault/tools/install_skills.py grill-me --platform codex --apply
```

它**永遠不覆蓋既有同名目錄**，遇到同名就跳過並警告。

**B. 只對某個 repo 成立 → 搬到那個 active repo**，由 code、設定與測試一起版控。

不論走哪一條，都在 `03-wiki/log.md` 追加一則 `promote`，
並在 `03-wiki/skill-<name>.md` 建一張導航卡（**只導航，不複製整份 skill 正文**）。

---

## 第 5 步：登錄進 registry

vault 不會自己發現你裝了什麼。`bin/skill-sources.json` 是機器可讀的來源清單：

```bash
# 第 4 步已經把草稿搬進 ~/.claude/skills/weekly-status 了，所以來源就指那裡：
# 目的地已有同名目錄 → 印 skip（永不覆蓋），但名字照樣登錄進 registry。
python3 agent-memory-vault/tools/install_skills.py weekly-status --apply \
    --source ~/.claude/skills \
    --register ~/my-vault/bin/skill-sources.json
```

（不加 `--source` 的話，它只認得 starter repo `skills/` 底下那幾支，
會回「沒有這些 skill：weekly-status」。）或自己把名字加進那份 JSON 的 `shared_skills` 陣列。沒登錄的 skill 不會進鏡像，
也不會被 `check-routing.sh` 檢查——換一台機器就不見了。

這時候先別跑 `check-routing.sh`，第 6 步 `link --apply` 做完再跑，否則會看到 `Shared runtime is not linked` 的錯誤。

---

## 第 6 步：link → sync → check

在 vault 根目錄，**預設全部只讀預覽，加 `--apply` 才寫**：

```bash
cd ~/my-vault
python3 bin/skill_sync.py link                  # 預覽：要在 Codex 側建哪些入口連結
python3 bin/skill_sync.py link --apply          # 建立連結（舊副本先備份）
./08-skill-base/sync-to-vault.sh                # 預覽：活檔 → 鏡像的差異
./08-skill-base/sync-to-vault.sh --apply        # 寫入鏡像；此後 snapshot.json 才存在
./bin/check-routing.sh                          # 來源、入口、hash、連結與路由檢查
```

順序有意義：**先 sync 再 check**。還沒同步過的 vault 沒有 `snapshot.json`，
這時候跑 check，鏡像那幾項只會給 warning（那是起始狀態，不是失敗）。

同步會先完整讀取與檢查來源，**命中已知 secret 前綴就整批不寫入**，而且只印位置不印值。
這個掃描不保證識別所有機敏資料，commit 前還是自己看一眼 staged diff。

驗收：

```bash
python3 bin/test_skill_sync.py      # 同步引擎自測，全在暫存目錄跑
```

---

## 常見錯法

- **寫成步驟而不是判準。** 步驟會過期，判準不會。
  真正值錢的是「這裡有兩種做法，什麼條件下選哪一種、選錯會怎樣」。
- **description 寫「這支 skill 很厲害」。** 它是給 agent 判斷「現在要不要叫它」用的，
  不是給人看的行銷文案。寫觸發情境與觸發語。
- **晉升後留著草稿。** 兩份分歧全文，半年後你會改錯那一份。
- **在活檔裡寫絕對家目錄路徑。** 換機器就壞，`check_vault.py` 會直接報 error。
  需要指路就指向 vault 的 `ROUTING.md`，讓路由只有一份。
- **一支 skill 想涵蓋三件事。** 拆開。會誤觸的 skill 比沒有 skill 貴。

---

## 接下來

- skill 的鏡像、還原與換機流程：[skills-and-sync.md](skills-and-sync.md)
- 哪些 gate 會替你守著這些規則：[gates.md](gates.md)
- 想更系統地寫 skill：`skills/writing-great-skills/`（參考文本，人手動叫它）
