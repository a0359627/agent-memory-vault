# Skills 與同步 — 從一個想法到換一台機器也還在

這頁講整條鏈：**抽取門檻 → 草稿 → 活檔 → registry → 鏡像 → 還原。**
第一次要動手做，走 [walkthrough-first-skill.md](walkthrough-first-skill.md)；這頁是它的參考手冊。

---

## 一、鏈上每一段負責什麼

```text
「這段工作值得抽嗎」      ← 兩條硬線：會再用到 ＋ 有判斷含量
      │
      ▼
05-skills-drafts/<name>/  ← 孵化區。SKILL.md ＋ notes.md（實跑觀察）
      │  穩定之後單向晉升，並刪掉草稿
      ▼
共用活檔 ~/.claude/skills/<name>/     或     active repo 內
      │        （唯一可以手改正文的地方）
      ▼
bin/skill-sources.json    ← registry：機器可讀的來源清單
      │
      ├─► skill_sync.py link     → 在另一個平台的目錄建入口連結
      │
      ▼
08-skill-base/            ← 鏡像＋snapshot.json（只由工具寫，永不手改）
      │
      ▼
restore-from-vault.sh     ← 新機器上還原回活檔位置
```

**一個原則貫穿全鏈：正文只有一份。** 活檔是正文，鏡像是快照，另一個平台的目錄是連結。
任何時候出現「同一支 skill 兩份正文」，你就已經在等著改錯那一份。

---

## 二、抽取門檻（兩條都中才抽）

1. **會再用到**（下個月、下個客戶、下個專案還會做一次）；
2. **有判斷含量**（有取捨、有判準、有容易踩的坑）。

只有第 1 條 → 寫成腳本。只有第 2 條 → 這次好好想一次就好。
第三個問題決定它住哪：跨專案的進共用活檔，單一 repo 的留在那個 repo。

**哪些類型的 skill 值得你自己長出來**（只講類型，因為內容一定綁你的脈絡）：

- **對齊型**：開工前把模糊需求逼成規格的拷問流程。
- **診斷型**：某個技術棧反覆出現的「看起來成功、其實壞了」，連同它的驗證斷言。
- **交接型**：把一份成果打包給別人（或別人的 agent）接手，含「可以給的門 vs 不可以給的鑰匙」。
- **品質判準型**：你能一眼看出好壞、但講不清楚的那種標準，寫成可檢查的條目。
- **收尾型**：某個 repo 每次結案都要記的決策、驗收證據、陷阱與下一步。

刻意**不**建議做成 skill 的：一次性的資料搬運（寫腳本）、純格式轉換（寫腳本）、
以及「把某某平台的說明書抄一遍」（會過期，而且原文就在那裡）。

---

## 三、SKILL.md 的最小規格

```markdown
---
name: <小寫、與資料夾同名>
description: <什麼時候該用它，含觸發語；這是 agent 決定要不要叫它的唯一依據>
---

# 標題
## 什麼時候用（與什麼時候不要用）
## 判準
## 完成判準（做完長什麼樣；什麼情況應該 no-op）
```

frontmatter **只放 `name` 與 `description`**——這是 Claude Code 與 Codex 都吃得下的最小交集，
也是這個 repo 的 office kit 驗證器對 skill 採用的同一條規則。
需要子資料夾時照通用慣例：`scripts/`、`references/`、`assets/`。

> 唯一的例外是 `skills/writing-great-skills/`，它多一個 Claude Code 專屬欄位讓模型不會自動觸發它。
> 為什麼保留、以及為什麼跨平台驗證器會對它警告，寫在 [skills/README.md](../skills/README.md)。

出處：REFERENCES §B。

---

## 四、registry：`bin/skill-sources.json`

| 欄位 | 意思 |
|---|---|
| `shared_source` | 共用 skill 的**活檔**目錄（正文只在這裡改） |
| `shared_runtime` | 另一個平台的入口目錄；裡面放的是指向活檔的符號連結，不是副本 |
| `shared_skills` | 你要跨平台共用的 skill 名稱陣列。空陣列＝還沒有 |
| `origins` | 要快照的 skill 來源，每筆 `{id, source}`；專案專用的 skill 用 `origin-<project>` 這類 id |
| `global_files` | 要一起快照的平台全域設定檔 |
| `memory_source` | 平台專案記憶的根目錄。**出廠值是 `null`＝不同步任何記憶**（見下一節） |
| `memory_projects` | 可選的 allowlist：只收這幾個專案 id 的記憶 |
| `primary_memory_project` | 放在鏡像根層（而非 `by-project/<id>/`）的那個專案 id |

沒登錄進 `shared_skills` 的 skill 不會進鏡像、不會被 `check-routing.sh` 檢查，
換一台機器就不見了。安裝時可以順手登錄
（本頁的 `agent-memory-vault/` 都指 clone 下來那個資料夾，指令在它的上一層執行）：

```bash
python3 agent-memory-vault/tools/install_skills.py <name> --apply \
    --register ~/my-vault/bin/skill-sources.json
```

---

## 五、`memory_source` 為什麼出廠是 `null`

因為打開它而不加 allowlist，會把**這台機器上每一個專案的記憶**都吸進你的 vault。

同步器的做法是掃 `memory_source` 底下每個專案的記憶目錄。不設 `memory_projects` 就是**全收**——
幾十個資料夾、幾百個檔案，而且那些目錄的名稱本身通常是**由專案絕對路徑編出來的 id**，
等於把你機器上的目錄結構寫進 vault，再跟著 git 走到任何你之後推送的地方。

要打開就加 allowlist：

```json
{
  "memory_source": "~/.claude/projects",
  "memory_projects": ["<只列你真的要收的專案 id>"],
  "primary_memory_project": "<放在鏡像根層的那個>"
}
```

再提醒一次分工（詳見 [walkthrough-first-ingest.md](walkthrough-first-ingest.md) 最後一節）：
**永久偏好的 canonical 在 `01-profile/`**；平台記憶只放短期 correction 與指回 canonical 的指標。
不要讓同一條偏好有兩份會分岔的版本。

---

## 六、link → sync → check → restore

全部在 vault 根目錄跑，**預設只讀預覽，加 `--apply` 才寫入**：

```bash
python3 bin/skill_sync.py link                  # 預覽要建哪些跨平台入口連結
python3 bin/skill_sync.py link --apply          # 建立；既有副本先移到備份目錄
./08-skill-base/sync-to-vault.sh                # 預覽活檔 → 鏡像的差異
./08-skill-base/sync-to-vault.sh --apply        # 寫入鏡像與 snapshot.json
./bin/check-routing.sh                          # 來源、入口、hash、連結與路由檢查
./08-skill-base/restore-from-vault.sh           # 驗 hash，預覽還原
./08-skill-base/restore-from-vault.sh --apply   # 還原列名檔案，再建立共用入口
python3 bin/test_skill_sync.py                  # 同步引擎自測（全在暫存目錄）
```

幾個重要的行為，知道了才不會嚇到：

- **鏡像只由工具寫。** `08-skill-base/` 底下的 `claude-skills/`、`snapshot.json` 都是產物；
  要改內容請改活檔再重新 sync。README 與兩支 wrapper 是維護檔，那兩個可以手改。
- **第一次跑之前鏡像不存在。** 全新的 vault 沒有 `snapshot.json`，這時 `check-routing.sh`
  的鏡像檢查只給 warning。順序是先 sync 再 check。
- **外部 symlink 會被展開成獨立檔案。** 指向某個 repo 的 skill 連結，快照時存成副本，
  還原時也還原成副本——**避免寫穿回原 repo**。要重新連回 canonical repo 請自己手動做，
  先對照那個 repo 的版本差異。
- **還原不刪東西。** 既有衝突路徑先備份，未列名的其他 skill 原封不動。
- **secret preflight。** 同步會先完整讀取與檢查來源，命中已知 secret 前綴就**整批不寫入**，
  而且只印位置不印值。這個掃描不保證識別所有機敏資料，commit 前仍請看 staged diff。
- **快照不等於環境。** 它還原檔案，不還原 plugin、runtime、平台權限或登入憑證。

換一台新機器的完整順序（clone repo 在前、還原 skill 在後，順序有意義）寫在 vault 的
[template/MIGRATE.md](../template/MIGRATE.md)；秘密的部分見 [secrets-with-age.md](secrets-with-age.md)。

---

## 七、這個 starter 附的八支

清單、分工與授權在 [skills/README.md](../skills/README.md)。安裝器預設只預覽：

```bash
python3 agent-memory-vault/tools/install_skills.py                     # 全部預覽
python3 agent-memory-vault/tools/install_skills.py grill-me --apply    # 只裝這支
```

**永遠不覆蓋既有同名目錄**——遇到同名就跳過並警告。要換版本請自己先把舊的移走。

領域型 skill（綁特定客戶、產線或內部系統的那種）刻意沒有收進來：
那類 skill 的價值幾乎都在它綁住的脈絡裡，抽掉脈絡就只剩空殼。要長出自己的那幾支，
從上面第二節的抽取門檻開始。
