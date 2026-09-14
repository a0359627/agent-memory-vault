# starter skills

這裡是八支可以直接裝進你的 agent 的 skill。它們不是示範用的空殼——每一支都是從真實工作裡磨出來、再去識別化後放進來的。**目錄本身就是安裝來源**：一支 skill ＝ 一個資料夾，裡面至少一份 `SKILL.md`。

## 怎麼裝

```bash
# 先看會發生什麼（預設就是預覽，不寫任何檔案）
python3 tools/install_skills.py

# 只裝你要的幾支
python3 tools/install_skills.py grill-me project-memory --apply

# 裝到 Codex 的 skill 目錄，並登錄進 vault 的來源清單
# 前提：這個 vault 是用 `bootstrap.py --platform codex` 建的。`--register` 會要求
#       來源清單的 shared_source 與安裝目的地一致（不一致就報錯、不寫任何檔）——
#       `--platform both` 的 shared_source 仍在 Claude 側，那時請改用 `--platform claude`。
python3 tools/install_skills.py obsidian-vault --platform codex --apply \
  --register ~/my-vault/bin/skill-sources.json
```

安裝器**永遠不覆蓋既有同名目錄**：遇到已存在的就跳過並警告，要換版本請自己先移走舊的。
不想用安裝器也行——把整個資料夾複製到 `~/.claude/skills/<name>/`（Claude Code）或 `~/.agents/skills/<name>/`（Codex）就生效。

## 八支是什麼

| skill | 等級 | 一句話 |
|---|---|---|
| [`grill-me`](grill-me/SKILL.md) | 直接可用 | 動手前的對齊拷問：一次一題、每題附建議答案，對齊了才開工。 |
| [`forge-skill`](forge-skill/SKILL.md) | 直接可用 | 判斷一段工作值不值得抽成 skill，以及怎麼把它寫成可預測的那種。 |
| [`obsidian-vault`](obsidian-vault/SKILL.md) | 直接可用 | 把新來源、跨案方法與決策沉澱到知識庫的正確位置，保留來源與適用範圍。 |
| [`project-memory`](project-memory/SKILL.md) | 直接可用 | 接手與收尾時，維護單一 repo 的決策、驗收證據、陷阱與下一步。 |
| [`diagnosing-bugs`](diagnosing-bugs/SKILL.md) | 直接可用 | 難搞 bug 的紀律：先建一個「會 red」的緊迴圈，再開始猜原因。 |
| [`verified-research`](verified-research/SKILL.md) | 直接可用 | 會寫進 code 的外部事實追到一手來源；高影響的再交叉驗證。 |
| [`agent-handoff-pack`](agent-handoff-pack/SKILL.md) | 直接可用 | 把 repo 打包成「別人的 agent 讀得懂、跑得動」的交接包，且不附 live 金鑰。 |
| [`writing-great-skills`](writing-great-skills/SKILL.md) | 參考用 | 寫 skill 的詞彙與原則（英文原文）；配套詞彙表 [`GLOSSARY.md`](writing-great-skills/GLOSSARY.md)。 |

**「直接可用」** ＝ 裝上去就能用，不必先改成你的情境。
**「參考用」** ＝ 它是一份給你（和你的 agent）查的參考文本，不是會自己跳出來執行的流程。

這七支「直接可用」彼此有分工，別重疊著用：開工前對齊用 `grill-me`；要查的外部事實交給 `verified-research`；東西壞了走 `diagnosing-bugs`；收尾時單一 repo 的脈絡寫進 `project-memory`、跨專案的理解才進 `obsidian-vault`；發現某段流程值得固定下來就用 `forge-skill`；要把成果轉交出去才用 `agent-handoff-pack`。

## frontmatter 只放 name 與 description

每份 `SKILL.md` 的 frontmatter 只有 `name` 與 `description` 兩個欄位——這是兩個平台都吃得下的最小交集，也是本 repo office kit 驗證器對 skill 採用的同一條規則。`description` 一律寫「什麼時候該用它」，含觸發語，agent 才有辦法自己判斷要不要叫它。

**唯一的例外是 `writing-great-skills`**，它比其他七支多一個 `disable-model-invocation: true`（**上游原本就有這一欄**，不是本 repo 加的）。這是 Claude Code 專屬欄位，意思是「只有人可以手動叫它，模型不會自動觸發」——因為它是給你查的參考文本，讓它每回合都佔著 context 並不划算。

> ⚠️ **把這支複製到 Codex 側再跑 skill 驗證器時，那一行會被判為多餘欄位而警告——這是預期行為。** Codex 慣例（也是本 repo `office-agent-starter-kit/tools/validate_kit.py` 對 kit 內 skill 執行的那條規則）是 frontmatter 只准有 `name` 與 `description`。不要為了消掉那行警告就刪掉它——刪了以後這支參考文本會在 Claude Code 變成每回合都載入的 model-invoked skill，剛好違反它自己教的原則。Codex 側若真的要通過驗證，刪掉那一行的**副本**即可，別動這裡的正本。

## 出處與授權

整個 repo 是 MIT。八支裡有三支源自 [mattpocock/skills](https://github.com/mattpocock/skills)（同為 MIT）：

- `writing-great-skills`（`SKILL.md` 與 `GLOSSARY.md`）是**上游原文照搬**，只在檔頭多加一段繁中前言說明為什麼收錄；該資料夾內附上游 [`LICENSE`](writing-great-skills/LICENSE)。
- `grill-me` 與 `diagnosing-bugs` 是**衍生作品**，已依本 repo 的情境重寫；兩個資料夾各自帶一份 `NOTICE.md`（上游版權聲明＋MIT 全文），所以你單獨複製一支出去也符合授權條件。

逐項對照（哪支照搬、哪支衍生、改了什麼）見根目錄的 `THIRD-PARTY-NOTICES.md`；為什麼收這三支、為什麼其餘沒收，見 `docs/REFERENCES.md §B`。其餘五支為本 repo 原創。

## 這裡沒有的東西

`office-agent-starter-kit/` 裡另有六支 skill，但那是**給 Codex 讀者的教學包**（含練習、fixtures 與驗證器），路徑與 frontmatter 慣例都跟這裡不同，不要用 `install_skills.py` 去裝它們。

領域型 skill（綁特定客戶、特定產線、特定內部系統的那種）刻意沒有放進來——那類 skill 的價值幾乎都在它綁住的脈絡裡，抽掉脈絡就只剩空殼。要長出自己的那幾支，從 `forge-skill` 的抽取門檻開始，流程見 `docs/skills-and-sync.md`。
