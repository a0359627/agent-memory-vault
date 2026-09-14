# {{VAULT_NAME}} — {{OWNER}} 的記憶庫

建立於 {{TODAY}}。工作語言：{{LANG}}。

## 三個原則

1. **分清楚來源、推論與人類確認。** 高影響主張要標來源、時間、範圍與狀態；沒有這些就只是候選。
2. **一個概念一份 canonical。** 舊主張以 `supersedes`／`superseded_by` 保留取代關係，不靜默覆寫歷史。
3. **值不進庫，只記位置。** 金鑰、token、密碼留在 gitignored 的本機位置；版本庫只寫「去哪裡找」。

## 三個入口

- [AGENT-RULES.md](AGENT-RULES.md) — 共用協作規範；`AGENTS.md`／`CLAUDE.md` 只負責載入它。
- [ROUTING.md](ROUTING.md) — 東西該寫到哪，路徑的唯一真相來源。
- [03-wiki/index.md](03-wiki/index.md) — 知識圖譜入口；沒開 Obsidian 時從這裡點連結逛。

第一次使用、要建第二個 vault 或要把這個 vault 公開，回 agent-memory-vault 讀 `docs/quickstart.md`。
