# MIGRATE — 換新電腦完整還原指南

> 目標：在一台全新的機器上，從零還原 {{OWNER}} 的完整工作環境。
> 照順序做，每步都有驗證點。平台：macOS／Linux；Windows 走 WSL。

## 1. 基礎工具

```bash
# 套件管理器、git、gh、gitleaks、age、你的編輯器與 agent CLI
# 例（macOS / Homebrew）：
# brew install gh git gitleaks age
```

填上你這台機器實際需要的清單；版本先查目前官方文件，不要照抄舊筆記。

## 2. Git 託管服務認證 + clone 本 vault

```bash
gh auth login                 # 帳號 <your-account>，要 repo scope
gh repo clone <your-account>/{{VAULT_NAME}} ~/{{VAULT_NAME}}
```

## 3. 預覽 skill 快照（active repo 先完成第 4 節，再套用）

```bash
cd ~/{{VAULT_NAME}} && ./08-skill-base/restore-from-vault.sh
```

上面的命令只讀預覽並驗證 hash。先依第 4 節 clone 需要的 repo，避免 skill 還原先建立同名非空目錄而阻礙 clone。
接著執行 `./08-skill-base/restore-from-vault.sh --apply`：還原來源清單中的 skills 與列名的平台入口。
既有檔案會先備份，未列名 skill 保留。數量以 `snapshot.json` 與工具輸出為準。
這不還原 plugin、runtime、權限或平台自有記憶。詳見 [快照說明](08-skill-base/README.md)。

**驗證**：在 `~/{{VAULT_NAME}}` 開你的 agent，它應該透過 `CLAUDE.md`／`AGENTS.md` 讀到
`AGENT-RULES.md`、`ROUTING.md` 與任務相關的 `01-profile/`。

## 4. Active repos

```bash
# 按需 clone；以 03-wiki/projects.md 與各 project card 的 source 為準：
# gh repo clone <your-account>/<repo> ~/<repo>
```

## 5. Secrets（加密後隨 git 還原，只手搬一把私鑰）

全部金鑰（各專案 `.env`、本機明文清冊、服務帳號 JSON、後台帳密）以 age 加密成
`99-secrets-encrypted/` 底下的密文包**隨 git 一起還原**。你只需要單獨手搬**一把 age 私鑰**——
那是唯一的根信任，不在 git 裡。

```bash
# ① 舊機 → 新機：只搬這一個檔（或存密碼管理器再貼回）
#    路徑由環境變數 MEMORY_VAULT_AGE_KEY 指定，不寫死在版本庫裡
scp "$MEMORY_VAULT_AGE_KEY" 新機:"$(dirname "$MEMORY_VAULT_AGE_KEY")"/

# ② 新機（vault 已 clone）：解密還原
export MEMORY_VAULT_AGE_KEY=<新機上的私鑰路徑>
cd ~/{{VAULT_NAME}} && ./bin/restore-secrets.sh
```

⚠️ **私鑰遺失 = 全部金鑰永久解不開。** 除了留在舊機，務必再存一份到密碼管理器或離線備份。
改過任何金鑰後，在舊機跑 `./bin/seal-secrets.sh` 重新封裝再 commit。

> 為什麼不直接把明文放 git：git 歷史永久，明文一旦 commit，改 public／加協作者／token 外流
> 就是全歷史一次洩漏，`git-filter-repo` 也救不乾淨。密文進 git 則安全（見
> [06-reference/secrets-hygiene.md](06-reference/secrets-hygiene.md)）。

## 6. Obsidian（可選，圖譜檢視）

開 Obsidian → Open folder as vault → 選 `~/{{VAULT_NAME}}`。它在這裡只是唯讀圖譜檢視器。

## 7. 不用搬的東西

| 東西 | 為什麼 |
|---|---|
| plugin 形式的 skill | 由目前平台的 plugin 管理器重新安裝／啟用；不複製舊 cache，實際可用性須確認 |
| agent CLI 的 `settings.json` | 機器特定，新機重設 |
| plugin／marketplace 快取 | 自動重抓 |
| 大型二進位輸出 | 不在 git；備份走外接碟或物件儲存（見各專案） |

## 8. 環境陷阱備忘

新機裝好後先讀 [01-profile/02-environment.md](01-profile/02-environment.md) 與 [01-profile/03-known-traps.md](01-profile/03-known-traps.md)——
歷史陷阱只在相應版本與條件下適用；先查目前版本，再用小型 probe 驗證。

---

給接手的人：讀完本檔後接著讀 [ONBOARDING.md](ONBOARDING.md)。
