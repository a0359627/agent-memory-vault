# Skill 與規則的可遷移快照

活檔與讀取入口由來源清單 `bin/skill-sources.json` 定義，歸屬規則見 [ROUTING](../ROUTING.md)。
共用正文在 `~/.claude/skills/`；列名的 `~/.agents/skills/` 是連結，不再維護替換平台字樣的全文。

**本 starter 不附任何鏡像。** 第一次執行 `./08-skill-base/sync-to-vault.sh --apply` 之後，
這個目錄底下才會出現 `claude-skills/` 與 `snapshot.json`。在那之前
`./bin/check-routing.sh` 的鏡像檢查只會給 warning，不是錯誤。

## 範圍

- `claude-skills/`：共用與本機 skill，含原有 references／assets。外部 symlink 展開為獨立檔案。
- `codex-skills/`：清單中的 Codex 專用／repo skill 快照；工具自帶 `.system` 不包含在內。
- `origin-<project>/`：來源清單登記的專案 skill 快照（範例）。與全域同名者保留專案 scope，不自動合併或覆蓋。
- `claude-global/`、`codex-global/`：兩個平台入口與其特有規則。
- `snapshot.json`：來源清單 hash、檔案 hash、原始權限與生成時間。只由工具產生。Git 只保存 executable bit，其餘權限由還原工具依清單恢復。

這是上述來源的檔案快照，不代表執行 repo、平台權限、plugin、runtime 或登入憑證已可用。
平台自有記憶、plugin cache、`.env` 與私鑰不在範圍內。

預設不同步任何平台記憶目錄：來源清單的 `memory_source` 出廠值是 `null`。
要打開之前先讀 agent-memory-vault 的 `docs/skills-and-sync.md`——不加限制的記憶來源會把
這台機器上**每個**專案的記憶都吸進 vault。

## 操作

以下在 vault 根目錄執行；預設只讀預覽，加 `--apply` 才寫入。第一次照這個順序跑：

```bash
python3 bin/skill_sync.py link                  # 預覽共用 skill 入口
python3 bin/skill_sync.py link --apply          # 備份舊副本，建立共用連結
./08-skill-base/sync-to-vault.sh                # 預覽快照差異
./08-skill-base/sync-to-vault.sh --apply        # 活檔 → 快照（此後 snapshot.json 才存在）
./bin/check-routing.sh                          # 來源、入口、hash、連結與路由檢查
./08-skill-base/restore-from-vault.sh           # 驗 hash，預覽還原
./08-skill-base/restore-from-vault.sh --apply   # 還原已列名檔案，再建立共用入口
```

既有衝突路徑先備份至工具輸出的備份目錄；還原不刪除未列名的其他 skill。
既有指向 repo 的頂層 skill link 先備份，快照復原成獨立副本，避免寫穿到原 repo。
repo-backed skill 要重新連回已 clone 的 canonical repo 時，先對照 project card 及版本差異。
其他專案記憶的目錄 ID 保留來源名稱；換登入名稱或 repo 路徑時須核對其平台 project ID。

同步會先完整讀取與檢查來源，缺檔或已知 secret 前綴命中時不寫入，輸出只列位置。
這個掃描不保證識別所有機敏資料；提交前仍檢視 staged diff。
私鑰與 age 備份的做法見 agent-memory-vault 的 `docs/secrets-with-age.md`。
鏡像內容只由工具更新；此 README、兩支 wrapper 與 `bin/` 是維護檔。

## 驗證

```bash
python3 bin/test_skill_sync.py
```

測試全部在隔離 temporary directory 執行，涵蓋唯讀預覽、備份、連結、各來源還原、
缺來源與 secret 攔截、hash 異常、冪等與防止寫穿 symlink。機械檢查不等於語意／業務驗收。
