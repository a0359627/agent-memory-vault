# Skills Drafts — 新 skill 的孵化區

新的 skill 在這裡草擬、迭代，**穩定後才晉升**。

## 慣例
- 一個 skill 一個子資料夾：`05-skills-drafts/<skill-name>/SKILL.md`（+ notes / 範例）。
- `SKILL.md` 用標準 Agent Skills 格式（YAML frontmatter：`name`、`description` 觸發語）。
- 旁邊放一份 `notes.md` 記實跑觀察：跑過幾次、哪次沒觸發、哪次輸出要大改。
  晉升與否靠這份 notes，不靠印象。

## 晉升路徑（單向）
1. 在這裡草擬、實測跑通。
2. 穩定後擇一：
   - 通用能力 → 搬到共用活檔位置（例如 `~/.claude/skills/<name>/`），再跑 `08-skill-base/sync-to-vault.sh`。
   - 只對特定專案成立 → 搬到該 active project repo，由 code／manifest／測試一起版控。
3. 晉升後**刪掉這裡的草稿**，避免兩份分歧版本；在 `03-wiki/log.md` 追加一則 `promote`。

若你有舊知識庫，明確標記它**不再是晉升目的地**：舊庫只能當歷史證據，不接收新 skill。
