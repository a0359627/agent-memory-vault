---
name: build-office-skill
description: 建立或改良可重複的辦公室 Codex skill；當使用者要把週報、會議、文件、研究、表格、交接或其他固定流程做成 SKILL.md，或要測試既有 skill 的觸發與輸出品質時使用。
---

# Build Office Skill

把重複辦公流程做成一支可觸發、可驗證、可交接的 skill。不要把一次性需求或只有機械步驟的工作硬抽成 skill。

## 1. 通過抽取門檻

確認兩件事：

1. 這項工作會重複發生。
2. 它包含非顯而易見的判準，例如怎麼算完成、哪些資料不能猜、何時要交還人類。

只符合第一項時，優先建立模板或腳本；兩項都不符合時，直接完成一次性任務。

完成判準：能用一句話說明「這支 skill 每次替誰完成什麼重複目標」。

## 2. 先查現況

檢查目前資料夾的 `AGENTS.md`、既有 `.agents/skills/`、範例輸入、實際產物與已知問題。能從檔案查到的事自行查，只向使用者詢問會改變結果的業務決策。

完成判準：列出可重用內容、不能帶入 skill 的個資／機密，以及尚缺的關鍵決策。

## 3. 建立工作契約

定義：

- 使用者目標與 owner；
- 必要輸入與來源權威；
- 輸出格式與接受者；
- 不可推測的欄位；
- 外部寫入與人類核准點；
- 失敗、停止與 `unknown` 條件；
- 可檢查的完成證據。

涉及寄信、共享檔、刪除、付款、發布、法務或權限時，先讀
[`references/office-skill-design.md`](references/office-skill-design.md)，畫出上面那張人類視圖並讓有權限的人確認。

完成判準：使用者確認輸入、輸出、未知、人類核准點與完成判準。

## 4. 選擇最小結構

- 核心流程放 `SKILL.md`。
- 只有特定分支才需要的政策、格式、例子放 `references/`。
- 必須重複且需要確定結果的檢查或轉換才放 `scripts/`。
- 要複製到交付物的範本放 `assets/`。
- 一個 skill 只對應一個可辨識的使用者目標；不同觸發、輸入或成功判準就拆開。

需要骨架時執行：

```bash
python3 .agents/skills/build-office-skill/scripts/create_skill.py \
  weekly-status \
  --description "彙整每週進度；當使用者要寫週報、主管摘要或專案狀態更新時使用。" \
  --display-name "每週進度彙整"
```

腳本不覆寫既有資料夾。

完成判準：每個檔案都有明確用途，沒有空資料夾、TODO 或重複規則。

## 5. 寫出可預測的流程

使用命令式步驟。每個階段都以可檢查的 completion criterion 收尾。正面描述目標行為；只有真正的硬性紅線才使用禁止句，並同時寫出安全替代做法。

Frontmatter 只保留：

```yaml
---
name: lower-kebab-case
description: 主要用途；當哪些請求出現時使用，以及重要邊界。
---
```

完成判準：description 能區分應觸發與不應觸發，body 明確規定輸入、步驟、輸出、未知與停止條件。

## 6. 測試再安裝

讀 [`references/test-cases.md`](references/test-cases.md)，至少測試：

1. 直接觸發；
2. 間接觸發；
3. 不應觸發；
4. 輸入不完整；
5. 危險副作用。

再執行：

```bash
python3 .agents/skills/build-office-skill/scripts/validate_skill.py \
  .agents/skills/<skill-name>
```

先修 activation，再修 instructions。使用相同模型、工具與輸入重新測試，不用換模型掩蓋 skill 問題。

完成判準：結構驗證通過，五類測試都有實際結果，且危險副作用停在人類核准前。
