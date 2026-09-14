# Ingest Log

> Append-only。格式 `## [YYYY-MM-DD] <type> | <標題>`，保持可 grep。
> 一次知識維護寫一則，標題是「這次改了什麼」，不是「我做了什麼工作」。
> 內文三到六行：改了哪幾頁、依據什麼來源、做了什麼檢查（例如壞連結數）。

`<type>` 只用下列七個：

| type | 什麼時候用 |
|---|---|
| `init` | vault 建立；每個 vault 只有一次 |
| `ingest` | 有新來源進來，寫成新的彙編頁 |
| `update` | 更新既有頁的內容或狀態 |
| `promote` | 候選升為 canonical：草稿 skill 晉升、`candidate` 偏好轉 `current` |
| `review` | 時間切片的盤點（`review-*.md`／`worklog-*.md`），寫完凍結 |
| `supersede` | 新主張取代舊主張，雙向標 `supersedes`／`superseded_by` |
| `lint` | 健檢：壞連結、孤兒頁、過期主張 |

新的一則寫在**檔尾**（append-only 指的是不改寫歷史）。
若某則描述的狀態後來改變了，不要就地改寫：另寫一則 `supersede`，並回到原則加一行指向新的那則。
