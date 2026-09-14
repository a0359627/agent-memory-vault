# 把自己的 vault（的一部分）公開

你的記憶庫累積到某個程度，多半會有一部分值得給別人看：一套規範、幾支 skill、幾份範本。
問題是那些東西和你的客戶、專案、憑證位置、家目錄路徑混在同一棵樹裡。

這頁講怎麼安全地切出來。工具就是這個 repo 裡的 `tools/export_public.py` 與 `tools/publish_check.py`——
**它們不是只給這個 starter 用的，是給你用的。**

---

## 心法：allowlist，不是 denylist

denylist（「這些不要出去」）的失敗模式是**忘了列**，而忘了列的東西會**悄悄放行**。
allowlist（「只有這些可以出去」）的失敗模式是**忘了列**，而忘了列的東西會**缺席**——
你馬上會發現，而且損失是零。

所以整條流程的核心是一份 manifest：**公開樹裡的每一個檔案都必須在 manifest 裡，
manifest 裡的每一個目的路徑都必須存在。多一個、少一個都是 error。**

---

## 步驟

### 1. 開一個獨立的工作副本

```bash
mkdir ~/my-vault-public && cd ~/my-vault-public && git init
```

三條硬規則：

- 它**不是**你 vault 的子目錄，也不是 worktree。兩棵樹分開，不會有人不小心 `git add .` 到隔壁。
- 兩邊**永不互加 remote**。`publish_check --remotes` 會替你檢查這件事。
- **全新的 git 歷史。** 不要用 `filter-branch` 或 `filter-repo` 去切私有歷史——
  commit 訊息與被刪掉的路徑名稱本身就是私有脈絡，而且那些工具清不乾淨。

### 2. 先處理 git 作者身分（這一步最多人漏）

公開副本的**每一個 commit 的 Author 行都會被公開**。如果那是你的私人信箱，
你等於在第一個 commit 就洩漏了它——而且掃描歷史的那道 gate 會因此永遠紅，
接著就會有人把它加進白名單，然後那道 gate 從此形同虛設。

```bash
cd ~/my-vault-public
git config user.name  "<你的對外 handle>"
git config user.email "<你的-github-id>@users.noreply.github.com"
```

驗收：`git log --format='%ae %ce' | sort -u` 只應出現 noreply 網域。

### 3. 建禁用識別字清單

明文清單與 key **都不進任何 repo**。清單格式是每行 `<category><TAB><token>`：

```text
person	<你的本名，以及每一種拼法>
company	<公司／團隊名稱>
domain	<你的網域>
cloud	<雲端專案 id 或編號>
home_fragment	<家目錄路徑片段>
private_repo	<私有 repo 名稱>
```

```bash
python3 tools/build_identifier_blocklist.py \
    --tokens ~/private/identifier-blocklist.txt \
    --key-file ~/private/hmac.key \
    --out ~/my-vault-public/bin/identifier-blocklist.hmac \
    --require-categories person,company,domain,cloud,home_fragment,private_repo
```

`--require-categories` 會在**任何一個必要類別是空的**時候拒絕生成。
這就是把「記得列完整」從一句叮嚀變成一道 gate。

產出的 `.hmac` **要進 git**（不可逆，別人驗不出你清單裡有誰），
key 與明文清單留在本機，用環境變數 `IDENTIFIER_BLOCKLIST_KEY_FILE` 指向 key。

> ⚠️ 順手用 `git check-ignore -v bin/identifier-blocklist.hmac` 確認它**沒有**被 `.gitignore` 吃掉。
> 一條含萬用字元的寬鬆規則就足以讓它進不了 git，然後 L2 會在 CI 上「檔案不存在 → 跳過」——
> 整層識別字檢查靜默消失，而你看到的是綠燈。

### 4. 寫 manifest

`tools/public-allowlist.example.json` 是可以照抄的起點（裡面的識別字全是虛構的）。
每個檔案挑一種模式：

| 模式 | 用在什麼 | 驗什麼 |
|---|---|---|
| `copy` | 原封不動的檔 | 目的內容必須等於來源 |
| `rewrite` | 要刪改幾行才能出去的檔 | 每條規則必須**恰好命中 `expect` 次**；輸出還要對上 sha256 |
| `pinned` | 你在公開 repo 直接手寫的檔 | 只驗 sha256 |
| `generate` | 由別的工具產生的檔 | 只驗 sha256 |

`expect` 是這整套機制裡最重要的一個數字：

- 命中 **0 次** → 來源改過了，你的刪改規則已經失效。**這是最危險的一種**：你以為改掉了。
- 命中**多於預期** → 規則太寬，可能改到不該改的地方。

再加一組全域 `assert_absent` 正則，對每個輸出檔做最後檢查（放你的公司名、舊知識庫名、`/Users/` 之類）。

> ⚠️ **你的 manifest 永遠放在私有側。** `pattern` 欄位裝的就是你來源檔的**原文**，
> `expect` 裝的是「那句話在你的檔案裡出現幾次」——所以 manifest 本身就是一份
> 「我有哪些東西要藏、藏的是哪幾句、各幾條」的清單。公開 repo 裡能放的只有
> `tools/public-allowlist.example.json` 那種**全虛構**的範例。
>
> 同一條道理適用於任何「用私有原文當 pattern」的產生器：`assert_absent` 通常只跑在
> **產物**上，不會跑在產生器自己身上，於是被擦掉的字串會從後門整包走出去，而閘門全綠。
> 本 repo 因此把 `tools/build_references.py` 的規則表整個移到私有側
> （見 [gates.md](gates.md) 的 `--full` 說明）。

### 5. 預設就該 exclude 的東西

這些是實戰上最會出事的幾類，**先當成不會出去，要出去再個別論證**：

- `08-skill-base/snapshot.json` — 開頭就有你的家目錄根路徑，以及一堆由專案絕對路徑編成的 id。
- 平台記憶目錄的鏡像 — 同上，而且內容是你的工作脈絡。
- `99-secrets-local/`（明文）與 `99-secrets-encrypted/`（密文與收件公鑰都是你的資產）。
- 你的憑證位置清冊（不論放哪一層）— **指路型洩漏**：沒有值，但告訴所有人去哪裡找。
- `STATUS.md` — 腳本產物，含專案名稱與本機路徑。
- 填好的 `01-profile/` 全部。
- `03-wiki/` 的 `ref-*`／`proj-*`／`review-*`／`worklog-*`／`cluster-*` — 這幾類頁面天生綁著來源與對象，通常密集出現識別字，預設全部排除。
- 任何 `.env*`（`.env.example` 除外）、任何 symlink、任何二進位檔、任何大於 200 KB 的檔。

想公開「卡片的格式」而不是卡片的內容？把格式抽成範本（`docs/templates/` 那八份就是這樣來的），
內容另外寫一份**全虛構**的範例。這比「把真的那份改到看不出來」安全得多——
改寫過的真實內容仍然保留可反推的結構。

### 6. 匯出、人眼看、過閘門

```bash
cd ~/my-vault-public

# ① 只檢查，不寫任何檔
python3 <starter>/tools/export_public.py --manifest ~/private/manifest.json \
    --source ~/my-vault --out . --check

# ② 真的寫（只寫 copy 與 rewrite；先整批檢查，任一錯誤一個檔都不寫）
python3 <starter>/tools/export_public.py --manifest ~/private/manifest.json \
    --source ~/my-vault --out . --apply

# ③ 人眼看 diff —— 這一步不能跳
git diff

# ④ 過掃描器（三層都跑，含 L2 禁用識別字）
export IDENTIFIER_BLOCKLIST_KEY_FILE=<你放 HMAC key 的路徑>
python3 <starter>/tools/publish_check.py ~/my-vault-public

# ⑤ 連歷史與遠端一起掃（淺 clone 會給你假綠燈，記得完整 clone）
git -C ~/my-vault-public log --all -p | python3 <starter>/tools/publish_check.py --stdin
git -C ~/my-vault-public remote -v   | python3 <starter>/tools/publish_check.py --remotes
```

⚠️ **這四條都從 starter 的 checkout 跑，掃的是你的匯出樹。** `bin/gate.sh` 驗的是
**starter repo 自己**（它會跑 starter 的 `tests/`、office kit 驗證器、兩份 `scan_sensitive.py` 的
`cmp`⋯⋯），`bootstrap.py` 也刻意不把它複製進你的 vault——在自己的匯出樹跑它只會得到
一串「檔案不存在」。你這一側的常駐 gate 是 `bin/scan_sensitive.py`（bootstrap 有給），
要公開東西時再回 starter 跑 `tools/publish_check.py`。

`--apply` 的 fail-before-write 是刻意的：**半套的匯出比完全沒匯出更危險。**

每道 gate 在檢查什麼、紅了代表什麼，見 [gates.md](gates.md)。

### 7. 發布前的最後三件事

1. **確認第 6 步的 ④⑤ 是在「要推出去的那個 commit」上跑的**——不是在你改之前跑的那次。
   歷史與 remote 那兩條特別容易被跳過：`git log --all -p` 需要完整 clone，
   淺 clone 會給你假綠燈。
2. **找第二個 agent 做對抗式複核**：另開一個 session，**只給它識別字的類型清單（不給值）**，
   要它以「陌生讀者＋找碴」的角度逐檔回報疑似殘留與**可組合推論**的敘述。目標是 0。
3. **自己全文讀一遍。** README、範本、skill、範例、docs 全部。
   清單只抓得到已知的詞；別稱、暱稱、以及「單看都乾淨、合起來只可能是你」的敘述，只有人抓得到。

然後：先開 private repo 觀察一輪，CI 綠了、branch protection 設好了，再轉 public。
轉 public 前把第 6 步的 ④⑤ 再跑一次。

---

## 之後每一次更新

方向**永遠是單向的**：私有 → 公開。

```text
改私有 vault → 更新 manifest → export --check → export --apply → git diff 人眼看
→ gate.sh --public（或 --full）→ commit → push
```

反向只准 `bin/`、`tools/`、`docs/` 的通用改善用 `cp` 拿回去，而且要重跑私有側的檢查。
**不要在私有 vault 裡加公開 remote 做 merge。**

**收了外部 PR（或自己直接改了 `pinned` 的手寫檔）之後多一步**：那些檔案的 sha256 已經過期，
`bin/gate.sh --full` 會紅。合併後跑
`python3 tools/export_public.py --manifest <private>/manifest.json --out . --print-hashes`，
把新的 sha256 回填進私有 manifest，再跑一次 `bin/gate.sh --full`。
一道每次收 PR 都會紅的閘門，最後一定會被人用旗標繞過去——所以這一步要寫進流程，不是靠記性。

在私有 vault 留一張 project card 記著：manifest 在哪、上次匯出對應哪個 tag 與哪個私有 commit、
哪些通用改善還沒回流、以及「我哪一天全文讀過並簽核」。
不記這張卡，第二次匯出你就得重新想一遍。

---

## 最後一句

**掃描器不保證抓到所有機敏資料。**
allowlist 是第一道、識別字 HMAC 是第二道、人眼是第三道。三道都做，不要只靠任何一道。
