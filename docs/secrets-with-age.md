# 讓金鑰隨 repo 走，又不外洩

需求很單純：**換一台電腦，所有金鑰都能還原。**
做法的紅線也很單純：**明文永遠不進 git。**

這兩件事只靠一個東西同時成立——[age](https://github.com/FiloSottile/age)：
把秘密封成密文再進 git，解密只需要一把**不在 git 裡**的私鑰。

---

## 為什麼不直接把明文放進私有 repo

「反正是 private repo」是最常見、也最貴的誤判。git 歷史是永久的：

- 改成 public、加一個協作者、token 外流、fork、CI 的 artifact——任何一次都是**全歷史一次洩漏**；
- 事後補救不是刪檔案，是**輪替每一把 key**；
- `git-filter-repo` 之類的工具清不乾淨（fork、快取、別人已經 clone 的副本）。

所以規則是：**值不進版本庫、不進 vault、不進 agent 的回應文字。**
要隨 repo 走就先加密。規則本體在 [template/06-reference/secrets-hygiene.md](../template/06-reference/secrets-hygiene.md)。

---

## 三個地方，各放什麼

| 位置 | 放什麼 | git |
|---|---|---|
| `99-secrets-local/` | 本機明文清冊（**唯一**允許明文的地方） | gitignored，永不進 |
| `99-secrets-encrypted/` | `*.age` 密文包 ＋ `recipient.txt`（收件人**公鑰**） | 進 git，安全 |
| 你自己選的一個本機路徑 | **age 私鑰** | 永不進 git，單獨手搬 |
| `06-reference/secrets-hygiene.md` | 只記「類型／位置／Git 狀態／用途」的清冊 | 進 git；**表裡永遠沒有值** |

公鑰只能加密、不能解密，外流不等於洩漏，所以 `recipient.txt` 進 git 沒問題。
**私鑰是唯一的根信任**：遺失就等於全部密文永久解不開。

---

## 第一次設定

```bash
# ① 決定私鑰放哪（不要放在 vault 裡），並讓腳本知道
export MEMORY_VAULT_AGE_KEY=<gitignored 的私鑰路徑>   # 不放在 vault 裡；檔名建議含 age-identity，好讓封裝腳本的檔名排除也認得
mkdir -p "$(dirname "$MEMORY_VAULT_AGE_KEY")"
age-keygen -o "$MEMORY_VAULT_AGE_KEY"

# ② 把上一步印出來的 public key（age1… 開頭）寫成一行
cd ~/my-vault
cp 99-secrets-encrypted/recipient.txt.example 99-secrets-encrypted/recipient.txt
$EDITOR 99-secrets-encrypted/recipient.txt

# ③ 立刻把私鑰再存一份到密碼管理器或離線備份
```

第 ③ 步不是可選的。私鑰只存在一台機器上，等於你的備份策略是「這台電腦不會壞」。

---

## 封裝（每次改過金鑰就做一次）

```bash
cd ~/my-vault
./bin/seal-secrets.sh
git add 99-secrets-encrypted/ && git commit -m "chore: reseal secrets"
```

它做的事：

1. 檢查 `age` 有沒有裝、`recipient.txt` 裡有沒有公鑰；
2. 把 `99-secrets-local/`（排除 README 與 `.age` 自己）打包；
3. 若有設定 `VAULT_SECRETS_DIR`（你本機的 canonical 金鑰目錄），一併打包；
4. **排除並主動掃描 age 私鑰；掃到就整批不封裝**——先用檔名排除（`*age-identity*`
   與你設定的那一把），再對打包前的暫存目錄逐檔掃 age 私鑰與 PEM 私鑰區塊，
   命中就印出相對路徑並中止。私鑰進了密文包，備份自己就是後門；
5. 用**公鑰**加密成 `99-secrets-encrypted/vault-secrets.tar.gz.age`。

**封裝只需要公鑰。** 腳本預設完全不碰私鑰；只有在你有設 `MEMORY_VAULT_AGE_KEY` 時，
它才多做一步「解開來數幾個檔」的自我驗證。沒設就跳過那一步，封裝照樣完成。

兩個可選的環境變數：

| 變數 | 用途 | 沒設會怎樣 |
|---|---|---|
| `VAULT_SECRETS_DIR` | 你本機 canonical 的明文金鑰目錄 | 只封裝 vault 內的 `99-secrets-local/` |
| `MEMORY_VAULT_AGE_KEY` | age 私鑰路徑 | 跳過封裝後的自我驗證；還原時則**必填** |

---

## 還原（新機器）

```bash
# ① 舊機 → 新機：只搬這一個檔（或從密碼管理器貼回）
#    這是唯一需要手搬的東西
# ② 新機上（vault 已 clone）：
export MEMORY_VAULT_AGE_KEY=<新機上的私鑰路徑>
cd ~/my-vault && ./bin/restore-secrets.sh
```

還原腳本**不會自動覆蓋任何東西**：它把密文解到一個暫存目錄，列出解出來的檔案，
然後印出「你要的話，這樣搬」的命令讓你自己確認。用完記得刪掉那個暫存目錄。

私鑰也可以用第一個參數傳：`./bin/restore-secrets.sh <身分檔路徑>`。

> 換機的完整順序（含「先 clone active repo、再還原 skill」這個順序陷阱）寫在
> vault 的 [template/MIGRATE.md](../template/MIGRATE.md)。私鑰路徑的變數名整套統一是
> **`MEMORY_VAULT_AGE_KEY`**，本機金鑰目錄是 **`VAULT_SECRETS_DIR`**。

---

## 提交前檢查

```bash
cd ~/my-vault
git status --short 99-secrets-local/          # 應該完全沒有輸出（被 gitignore 擋住）
ls 99-secrets-encrypted/                       # 只該有 *.age、recipient.txt、README.md
git diff --cached                              # 自己看一眼
```

`.gitignore` 出廠就擋掉 `99-secrets-local/`、`.env*`、`*.key`、`*.pem`、
含 `token`／`credentials`／`client_secret` 字樣的檔名，以及 age 身分檔。
但 **gitignore 不是 gate**：它只擋你沒 force-add 的東西，而且新增一個沒想到的檔名就漏了。
真正的 gate 是掃描器。你的 vault 這一側，`bootstrap.py` 已經把 `bin/scan_sensitive.py`
放進去了，提交前跑它：

```bash
cd ~/my-vault && python3 bin/scan_sensitive.py .   # 末行要是 0 error(s)
```

`tools/publish_check.py` 與它的 pre-commit hook（`tools/install-hooks.sh`）只存在
starter repo，**不會被 bootstrap 複製到你的 vault**；要公開東西時回 starter repo 跑，
細節見 [gates.md](gates.md)。

---

## 三條不要做的事

1. **不要把私鑰放進 vault**，即使加密過。它是解開其他一切的根信任，不該和被它保護的東西住在一起。
2. **不要在 Markdown、程式、commit 訊息或 agent 的回應裡寫出值。**
   需要提到某把 key 時只寫「名稱 ＋ 用途 ＋ 放在哪個檔案路徑」。
3. **看到落單的 key 不要「順手清理」到別的檔案。**
   就地標記位置、回報，讓人決定輪替或刪除——搬家只是把洩漏面擴大，而且原處的 git 歷史還在。

輪替過一把 key 之後，回 `06-reference/secrets-hygiene.md` 更新那一列的日期與影響範圍。
**沒更新的清冊比沒有清冊更危險**，因為它會讓你以為自己知道。
