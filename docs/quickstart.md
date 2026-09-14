# Quickstart — 五分鐘生出一個會代謝的記憶庫

平台：macOS／Linux。Windows 請在 WSL 裡跑（`bin/check-routing.sh` 是 bash，skill 連結用 symlink）。
需求：`python3` 3.11 以上與 `git`。**零第三方套件**，不需要 `pip install` 任何東西。

---

## 三個命令

```bash
git clone https://github.com/a0359627/agent-memory-vault
python3 agent-memory-vault/tools/bootstrap.py ~/my-vault --owner "你的稱呼" --with-sample
cd ~/my-vault && claude        # 或 codex
```

第二行做完這些事，每一步都會印出來，失敗就停、不留半成品：

1. 拒絕非空目錄（要往既有目錄補檔案請加 `--force`，它只補缺、永不覆蓋或刪除）；
2. 把 `template/` 與 `bin/` 複製過去，保留 `.sh` 的執行位；
3. 替換佔位符（雙大括號包住的 OWNER／LANG／VAULT_NAME／TODAY 那幾個），替換完還找得到殘留就報錯；
4. 依目標路徑推導平台的 memory project id，寫進 `bin/skill-sources.json`；
5. 建立被 gitignore 的 `99-secrets-local/README.md`；
6. 在 `03-wiki/log.md` 寫下第一則 `init`；
7. `git init` 加一個 commit（不想要就加 `--no-git`）；
8. `--with-sample` 時，把範例 vault 複製到 `~/my-vault-sample/`（**不進**主 vault、不 git init）；
9. 最後跑一次 `bin/check_vault.py --skip-snapshot`，這是你的第一個綠燈。

常用選項：`--lang`（預設 `zh-TW`）、`--vault-name`（預設取目錄名）、
`--platform claude|codex|both`（決定 `bin/skill-sources.json` 指向 `~/.claude/skills` 還是 `~/.agents/skills`）。

> `bootstrap.py` 對 vault 以外**零寫入**：不碰 `~/.claude`、`~/.codex`、`~/.agents`，不下載任何東西。
> 要裝 skill 是另一個明確的動作，見下面第 3 步。

---

## 不想打指令？把這段貼給你的 agent

在 clone 下來的資料夾裡開 Claude Code 或 Codex，貼這句：

```text
請讀 docs/quickstart.md，用 tools/bootstrap.py 幫我在 ~/my-vault 建立記憶庫，
完成後告訴我第一件該做的事。
```

---

## 五分鐘後你會有什麼

```text
~/my-vault/
├── AGENTS.md · CLAUDE.md      兩個平台入口，都只負責載入下面那份規範
├── AGENT-RULES.md             共用協作規範（唯一一份）
├── ROUTING.md                 東西該寫到哪：路徑的唯一真相來源
├── 00-inbox/                  還沒分類的輸入
├── 01-profile/                你是誰、怎麼跟你合作、環境、反覆咬人的陷阱
├── 02-raw/                    不可變原文（只讀，不在這裡下結論）
├── 03-wiki/                   彙編、index、log、open-questions、記憶代謝規範
├── 04-projects/               有期限的交付
├── 05-skills-drafts/          skill 孵化區（晉升後刪草稿）
├── 06-reference/ · 07-archive/  快查表／歸檔（歸檔不冒充 current）
├── 08-skill-base/             skill 活檔的可遷移鏡像（只由同步腳本寫）
└── bin/                       check_vault.py · skill_sync.py · scan-state.sh …

另有 ONBOARDING.md／MIGRATE.md／99-secrets-encrypted/／.obsidian/，第一天用不到可以先不管。
```

---

## 接下來三件事

1. **填 profile。** 打開 `01-profile/01-preferences.md`，把四條原則換成你自己的。
   這一層會被 agent 在每個非瑣碎任務前讀到，寫得含糊就等於沒寫。
2. **做一次完整的 ingest。** 照 [walkthrough-first-ingest.md](walkthrough-first-ingest.md) 走一遍——
   先逛範例 vault，再拿你自己的一份來源做一次。
3. **裝幾支 skill。** 下面的 `agent-memory-vault/` 是**你 clone 下來那個資料夾**的相對路徑，
   所以要回到 clone 的上一層執行（或換成它的實際路徑）；人還在 `~/my-vault` 裡跑會找不到檔案。

   ```bash
   python3 agent-memory-vault/tools/install_skills.py                 # 預設只預覽，不寫檔
   python3 agent-memory-vault/tools/install_skills.py grill-me obsidian-vault --apply \
       --register ~/my-vault/bin/skill-sources.json
   ```

   安裝器**永遠不覆蓋既有同名目錄**；遇到同名就跳過並警告。八支各是什麼見 [skills/README.md](../skills/README.md)。

---

## 隨時可以跑的自檢

```bash
cd ~/my-vault && ./bin/check-routing.sh          # 規則入口、skill 來源、wiki 連結
```

第一次跑（還沒同步過 skill 鏡像）鏡像檢查只會給 warning，不是錯誤。
每道閘門各在檢查什麼、紅了代表什麼，見 [gates.md](gates.md)。

---

## 還想看什麼

| 你想知道 | 讀這個 |
|---|---|
| 這套設計的骨架與三個原則 | [concepts.md](concepts.md) |
| 第一次把來源沉澱進來 | [walkthrough-first-ingest.md](walkthrough-first-ingest.md) |
| 第一次把一段工作抽成 skill | [walkthrough-first-skill.md](walkthrough-first-skill.md) |
| skill 的草稿→活檔→鏡像→還原 | [skills-and-sync.md](skills-and-sync.md) |
| 金鑰怎麼隨 repo 走又不外洩 | [secrets-with-age.md](secrets-with-age.md) |
| 有一天想把自己的 vault 公開 | [publishing-your-vault.md](publishing-your-vault.md) |
| 為什麼刻意不做某些事 | [design-notes.md](design-notes.md) ｜ [faq.md](faq.md) |
