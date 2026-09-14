# 第三方授權聲明（Third-Party Notices）

本 repo 整體以 MIT 授權發布，版權見根目錄 [`LICENSE`](LICENSE)。
以下列出本 repo 內**源自第三方**的內容、其授權、以及我們做了什麼修改。

---

## mattpocock/skills

| 項目 | 內容 |
|---|---|
| 專案 | `mattpocock/skills` — Skills for Real Engineers |
| 來源 | https://github.com/mattpocock/skills |
| 版本 | commit `ed37663cc5fbef691ddfecd080dff42f7e7e350d` |
| 授權 | MIT License — Copyright (c) 2026 Matt Pocock |
| 授權全文 | [`skills/writing-great-skills/LICENSE`](skills/writing-great-skills/LICENSE)（另複製於 [`skills/grill-me/NOTICE.md`](skills/grill-me/NOTICE.md) 與 [`skills/diagnosing-bugs/NOTICE.md`](skills/diagnosing-bugs/NOTICE.md)） |

上游授權為 MIT，允許使用、修改與再散布，條件是保留版權聲明與授權條文。本 repo 依該條件保留上游 LICENSE 全文，並在此逐項標示修改狀態。

**2026-09-14 已對 pinned commit 逐 byte 核對上游 LICENSE 全文，一致。**該全文的 sha256 被 pin 在 `tools/publish_check.py` 的 `UPSTREAM_LICENSE_SHA256`，之後任何人改動這份 LICENSE（改年份、重打條文、截掉免責段）都會讓閘門紅——只檢查「有沒有作者名字」擋不住這些。

### 逐項對照

「上游對應」是**在 pinned commit 上真的存在的完整路徑**（上游把 skill 分在 `skills/engineering/`
與 `skills/productivity/` 兩個分類底下）。寫成扁平檔名的話，任何人拿這張表去對照都會得到 404，
而這張表存在的唯一理由就是讓第三方能自己驗「逐字未改」「已重寫」這兩句話。

| 本 repo 檔案 | 上游對應 | 狀態 | 修改內容 |
|---|---|---|---|
| `skills/writing-great-skills/SKILL.md` | `skills/productivity/writing-great-skills/SKILL.md` | **照搬，但有加料** | 正文（`A skill exists to wrangle determinism…` 以下全部）逐字未改。**檔頭新增一段繁體中文前言**，說明為什麼收錄、以及 `disable-model-invocation: true` 的用意。**frontmatter 未改**——`disable-model-invocation: true` 是**上游原有**的欄位，不是本 repo 加的（2026-09-14 對 pinned commit 的原文逐行核對）。 |
| `skills/writing-great-skills/GLOSSARY.md` | `skills/productivity/writing-great-skills/GLOSSARY.md` | **照搬** | 全檔逐字未改。 |
| `skills/grill-me/SKILL.md` | `skills/productivity/grilling/SKILL.md` | **衍生作品** | 已重寫：改用繁體中文、換掉整組對齊檢查點、改寫提問紀律與完成判準、加入授權與範圍的規則。保留的是上游的核心主張——動手前先一次一題對齊，每題附建議答案。 |
| `skills/diagnosing-bugs/SKILL.md` | `skills/engineering/diagnosing-bugs/SKILL.md` | **衍生作品** | 已重寫：改用繁體中文、六階段的內文重寫、探針範例換成本 repo 情境、階段 6 接上本 repo 的陷阱庫慣例。保留的是上游的核心主張——先建一個「會 red」的緊迴圈，再開始猜原因。 |

兩支衍生作品在檔尾各自標明了源流與 MIT 衍生身分，並各自帶一份 `NOTICE.md`（含上游版權聲明與 MIT 全文）。
這是必要的：`tools/install_skills.py` 一次只複製**一個 skill 資料夾**，指向本檔的註腳在安裝目的地並不存在，
而 MIT 要求版權與授權條文隨每一份副本走。`tools/publish_check.py` 會把「本表點名的每個 skill 目錄都要有
可獨立散布的 notice」驗成閘門，不是叮嚀。

### 沒有隨本 repo 散布的部分

上游 repo 的其餘檔案（`README.md`、`CONTEXT.md`，以及未被本 repo 採用的其他 skill）**未隨本 repo 散布**。想看完整原文請直接到上游 repo 取得。

本 repo 為什麼只採用這三支、其餘為什麼沒採用，理由記在 `docs/REFERENCES.md §B`。

---

## 其他

除上述之外，本 repo 不含第三方程式碼或文件：

- 所有工具（`tools/`、`bin/`、`tests/`）為本 repo 原創，只使用 Python 3.11 標準庫與 bash，**沒有任何第三方套件相依**，因此沒有需要隨附的相依套件授權。
- `office-agent-starter-kit/` 是本 repo 原創的教學包，與整個 repo 同樣以 MIT 發布；因為它會被打包成獨立 ZIP 交給收件者，那一層自帶一份 `LICENSE` 副本（內容與根目錄相同），`office-agent-starter-kit/tools/validate_kit.py` 把「這份 LICENSE 必須在」驗成閘門。
- `docs/REFERENCES.md` 中引用的外部文獻、規範與文章，是**引用與轉述**，不是複製——該頁只保留題名、URL 與一句借用重點，未收錄任何受著作權保護的正文。
