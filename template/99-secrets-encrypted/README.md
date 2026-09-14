# 99-secrets-encrypted — 只放密文與收件公鑰

這個資料夾**可以進 git**，因為裡面只有兩種東西：

- `*.age`：age 加密後的密文包（由 `bin/seal-secrets.sh` 產生）。
- `recipient.txt`：收件人**公鑰**。公鑰只能加密、不能解密，外流不等於洩漏。

**私鑰永遠不在這裡，也永遠不在 git 裡。** 它是唯一的根信任，單獨手搬，
路徑由環境變數 `MEMORY_VAULT_AGE_KEY` 指定；遺失就等於全部密文永久解不開，
所以另外存一份到密碼管理器或離線備份。

## 第一次設定

```bash
export MEMORY_VAULT_AGE_KEY=<gitignored 的私鑰路徑>   # 先設好；沒設的話下一行會寫到空路徑
age-keygen -o "$MEMORY_VAULT_AGE_KEY"          # 產生私鑰到 gitignored 的位置
# 把輸出的 public key 貼進 recipient.txt（一行，age1… 開頭）
cp 99-secrets-encrypted/recipient.txt.example 99-secrets-encrypted/recipient.txt
```

之後改過任何金鑰，回到 vault 根目錄跑 `./bin/seal-secrets.sh` 重新封裝再 commit；
換機還原見根目錄的 `MIGRATE.md`。

commit 前確認這裡只有 `*.age`、`recipient.txt` 與本 README，沒有任何明文。
