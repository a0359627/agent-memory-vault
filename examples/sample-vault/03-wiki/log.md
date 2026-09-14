# Ingest Log

> Append-only。格式 `## [YYYY-MM-DD] <type> | <標題>`，保持可 grep。
> 新的一則寫在檔尾；狀態後來改變時不就地改寫，另寫一則 `supersede` 並回到原則加一行指向它。

這份是**範例 vault 的劇本**。八則紀錄涵蓋八種 type，而且這個 vault 裡的每一頁，
都能在下面找到「它是哪一則寫出來的」。想知道一個知識庫怎麼長出來的，從這裡往下讀就好。

> 型別詞彙的注意事項：`template/03-wiki/log.md` 的基本表列了七個 type
> （`init`／`ingest`／`update`／`promote`／`review`／`supersede`／`lint`）。
> 這個範例 vault 另外自訂了兩個——`draft`（草稿進孵化區但**不**晉升）與
> `answer`（open question 有了答案）——因為工作室常做這兩件事，混進 `update` 就 grep 不出來。
> 自訂 type 可以，但要像這樣寫明它是自訂的，而且**加了就不要再改**：
> 型別詞彙一改，整份 log 的可 grep 性就沒了。

## [2026-01-04] init | vault 建立

建立三層（`02-raw/` 不可變來源、`03-wiki/` 彙編、根目錄規範）＋ PARA 資料夾。
寫了 [[00-who]]、[[01-preferences]]、[[02-environment]] 三頁 profile，以及
[[index]]／[[log]]／[[open-questions]]／[[projects]]／[[skills]] 五張骨架。
來源：工作室原本散在兩本筆記本與客戶資料夾裡的慣例，這次只是把它們寫成可執行的句子。
此時 [[03-known-traps]] 還是空的——陷阱要被咬過才有資格寫進去。

## [2026-01-06] ingest | 甲咖啡館品牌改版的需求簡報

把 1/5 的客戶會議草記（[[2026-01-05]]）與客戶當天寄來的需求簡報原文一起歸檔：
原文進 `02-raw/client-brief-2026-01/`（[[02-raw/client-brief-2026-01/SOURCE]] 記出處與收件日，[[02-raw/client-brief-2026-01/brief]] 保存全文，兩份都不再編輯），
結論與推論進 [[ref-client-brief-2026-01]]。同時開了 [[proj-brand-site-relaunch]] 這張 project card，
並建 [[cluster-client-work]] 當客戶線的星狀中心，掛進 [[projects]] 與 [[index]]。
檢查：本次新增頁的 wikilink 逐一核對目標存在，壞連結 0。

## [2026-01-20] update | 週報從手寫改成腳本產草稿

更新 [[proj-weekly-report-bot]]：原本每週手抄客戶進度，改成用腳本讀工時試算表產出草稿。
這一週也第一次往 [[03-known-traps]] 寫東西——第 1 條（試算表空白欄不是 0，會讓工時少算）
與第 2 條（圖片檔名的全形空白上線後 404）都是這次做出來的坑，各附症狀與驗證方法。
狀態仍是 `pilot`：腳本跑得出草稿，但寄出這一段還是手動，也還沒有客戶對「用機器產的週報」表示過意見。

## [2026-02-03] promote | weekly-client-report 由草稿晉升為共用 skill

晉升條件成立：同一套流程在甲咖啡館與乙書室兩個客戶各跑滿三週，輸出格式沒有再改過，
而且第三個人（小華）照著草稿也產得出一樣的結果。依 `05-skills-drafts/README.md` 的單向路徑，
草稿搬到活檔位置（本範例用 `skills-promoted/weekly-client-report/`）並刪掉孵化區那份，
新增導航卡 [[skill-weekly-client-report]]，[[skills]] 的 Active 區加一列。

## [2026-02-05] draft | client-feedback-triage 進孵化區，不晉升

客戶回饋分類的做法只在甲咖啡館一個客戶身上成立過，抽取門檻**不成立**，因此只寫成草稿
`05-skills-drafts/client-feedback-triage/`（[[05-skills-drafts/client-feedback-triage/SKILL]] ＋ [[05-skills-drafts/client-feedback-triage/notes]] 兩次實跑觀察），
並建 status 為 `draft` 的卡 [[skill-client-feedback-triage]] 說明它現在能用到哪。
同時在 [[open-questions]] 開了 `draft-promotion-threshold`：一支 skill 要幾個客戶驗證過才算通用。
另補 [[03-known-traps]] 第 4 條（客戶寄來的「最終版」PDF 沒有版本號，2026-02-04 咬到）。

## [2026-02-10] answer | 客戶口頭回饋不構成 authority

[[open-questions]] 的 `client-feedback-authority` 移到 Answered，Authority 記
`user-confirmed`（小明明示）：口頭回饋只能成為候選，要有文字確認（信件或工單）才算定案依據。
連帶在 [[01-preferences]] 寫成一條可執行的 `current` 規則，並回頭補上
[[ref-client-brief-2026-01]] 的 `authority` 欄——那份簡報是客戶自己寄來的文字，本來就過關。

## [2026-02-14] review | 第一個月回顧（寫完凍結）

[[review-2026-02-14-first-month]]：逐案列 evidence 與誠實狀態，並把平常口語的「上線了」
拆成 committed／deployed／client accepted 三種不同證據。結論之一是
[[proj-weekly-report-bot]] 的寄送路徑沒有人工核准點，列為風險但當週沒有動它。
Review 頁寫完即 `frozen`，後續變化另寫新頁，不回頭改這一頁。

## [2026-02-20] supersede | 週報產生器改為「只產草稿、人核准才寄」

2026-02-18 用 `--preview` 跑週報，結果信真的寄到兩個客戶手上——那個旗標從來不是乾跑。
[[proj-weekly-report-bot]] 頁頂換成新的「現行有效」段，舊的自動寄送設計整段標 `superseded`
並雙向指向新段；[[03-known-traps]] 補第 3 條（附事故日期與可貼上的修法）。
這也回頭印證 [[review-2026-02-14-first-month]] 六天前列的那條風險：列進 review 不等於已經修掉。
