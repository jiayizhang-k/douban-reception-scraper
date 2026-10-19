# Douban Data Collection Notes: 《步步惊心》 *Scarlet Heart* (2011)

**Douban subject ID:** 5384548
**Collection period:** October 3–5, 2026
**Collection account:** personal Douban account, logged in
**Code:** this repository (`douban_playwright.py`, `douban_reviews.py`, `clean_merge.py`); in October 2026 the scripts had the subject ID written in, rather than the `--subject` option they take now

## 1. Corpus summary

| Data type | Douban-reported total | Collected | Coverage |
|---|---|---|---|
| Short comments (短评), 看过 tab | 121,968 | 1,307 unique | Platform-selected subset |
| Long reviews (剧评) | 2,129 | 2,048 visible (2,047 with full text) | Near-complete: 96% of reported; all publicly visible reviews |

## 2. Short comments (短评)

### 2.1 Page structure

- The comment page has three tabs: 看过 (watched), 在看 (watching), and 想看 (want to watch).
- Within each tab, comments can be sorted by 热门 (popular) or 最新 (latest). A third sort, 好友 (friends), only shows the logged-in user's own network, so it was excluded.
- Rating filters (全部 all / 好评 positive / 一般 neutral / 差评 negative) appear **only** under 热门, not under 最新.
- That leaves nine collectible lists. Five were collected for the 看过 tab. The other four (在看 and 想看 × 热门/最新) have not been collected yet.

### 2.2 Observed retrieval limits (October 2026, logged in)

| List | URL parameters | Max retrievable |
|---|---|---|
| 看过 · 热门 · 全部 | `status=P&sort=new_score` | 400 |
| 看过 · 热门 · 好评 (4–5★) | `…&percent_type=h` | 400 |
| 看过 · 热门 · 一般 (3★) | `…&percent_type=m` | 400 |
| 看过 · 热门 · 差评 (1–2★) | `…&percent_type=l` | 400 |
| 看过 · 最新 | `status=P&sort=time` | 100 |

- The limit is set by Douban's server. Requests past page 20 (`start=400`) return an empty page.
- 最新 covered only about three weeks of posts (2026-09-15 to 2026-10-04).

### 2.3 Collected data

- 1,700 rows in total, which came to 1,306 unique comments after deduplicating by comment ID. A second run added 1 more, for **1,307**.
- Sentiment breakdown (by star rating): 460 positive (4–5★), 422 neutral (3★), 414 negative (1–2★), 11 unrated.
- Overlap between lists:
  - 热门·全部 shares 299 comments with 好评, 54 with 差评, and 41 with 一般.
  - The 好评, 一般 and 差评 lists don't overlap with each other.
  - 最新 doesn't overlap with any 热门 list.
- This means the main 热门 list is about three-quarters positive.

### 2.4 Stability across runs

Run 1 was on October 3. Run 2 was on October 3, except the 差评 list, which was re-collected on October 5.

- 好评, 一般 and 差评 came back **identical** in both content and order.
- 热门·全部 had the same 400 comments, but in a different order: the average rank shift was 3.7 positions, and 6 of the top 20 moved.
- 最新 had one new comment. Only about two hours had passed between runs.
- **Takeaway:** the rating-filtered lists are effectively fixed snapshots. Only 最新 brings in new comments over time.

### 2.5 Temporal pattern (preliminary)

- 热门 and 好评 comments peak in **2016–2017** (median date around March 2017). This lines up with retrospective rewatching; many top comments compare the show with the 2016 Korean remake 《步步惊心：丽》.
- 一般 and 差评 comments cluster in **2011–2012**, during the original broadcast (median dates November 2011 and July 2012).
- In short, criticism was concentrated at the time of the original airing, while the most-praised comments came later, from viewers looking back.

### 2.6 IP location field

- This field shows the poster's province-level IP location **at the time of posting**. It is not the user's self-reported home city.
- Douban began displaying IP locations around September 2022. Comments posted earlier have no location.
- Only 201 of 1,307 comments have a location, so the field was excluded from the main analysis.

## 3. Long reviews (剧评)

### 3.1 Page structure and lists

- URL: `/subject/5384548/reviews`
- Douban reports 2,129 reviews: 946 at 5★, 691 at 4★, 234 at 3★, 57 at 2★, 45 at 1★, and the rest unrated.
- Seven lists were collected: `sort=hotest` (最受欢迎), `rating=5` through `rating=1` (按评星查看), and `sort=time` (最新发布的).

### 3.2 Observed retrieval limits

- **No 400-review cap was observed.** The page navigation lists 107 pages (2,129 ÷ 20), and collection reached the end of the list.
- Some pages show fewer than 20 reviews. Page 1 of 最受欢迎, for example, shows 18. Douban counts these reviews in the total but doesn't display them, most likely because they were folded (折叠), deleted, or hidden by moderation.
- The full text of each review was collected separately from its own page (October 5, 2026).

### 3.3 Collection results

| List | Douban-reported | Visible and collected | Share visible |
|---|---|---|---|
| 最受欢迎 (hot, all) | 2,129 | **2,048** | 96.2% |
| 5★ | 946 | 927 | 98.0% |
| 4★ | 691 | 667 | 96.5% |
| 3★ | 234 | 215 | 91.9% |
| 2★ | 57 | 53 | 93.0% |
| 1★ | 45 | 38 | 84.4% |
| Unrated (derived) | 156 | 148 | 94.9% |
| 最新发布的 (latest) | — | 239 (first 12 pages only, used as a check) | — |

- **Unique reviews:** 2,048. **With full text:** 2,047. **Deleted:** 0. **Missing full text:** 1 (retry once; otherwise exclude).
- **Completeness check:** every review in the five rating lists and in the 239 latest reviews also appears in the hot list, so the hot list contains every visible review.
- **Note on what is hidden:** the share of reviews not shown rises as ratings fall (1★: 84% visible vs. 5★: 98%). Lower-rated reviews may be folded or removed somewhat more often. The hidden reviews can't be observed, so report this as a limitation rather than a finding.

## 4. Access methods attempted

| Method | Result |
|---|---|
| Python `requests` from Google Colab | Redirected to `sec.douban.com` (anti-bot check), which is typical for data-center IPs. Same result even with a logged-in session cookie. |
| Douban mobile API (`m.douban.com/rexxar/api/v2/tv/5384548/interests`) | Returned at most about 120 popular comments. Sort and rating parameters were ignored. With a cookie, it returned HTTP 403. |
| Python `requests` from a home network, not logged in | Redirected to `sec.douban.com`. |
| **Automated real browser (Playwright), logged in, home network** | **Successful.** It waited 5–9 seconds between pages and 30–60 seconds between lists, and paused for manual verification when Douban asked. |

## 5. Platform documentation and secondary sources

### 5.1 Douban's official statement (2020)

- In late October 2020, the tech press reported that Douban no longer showed all short comments.
- In response, Douban said the change had been in place for films since **November 2017**, and for books and music since April 2020.
- Douban said: "短评区仅显示部分短评，由算法根据时间、热度等因素进行筛选" (the short-comment section displays only part of the comments, selected by an algorithm based on factors such as time and popularity).
- The stated reason: "在不影响用户体验的前提下，同时兼顾反爬虫、反水军而进行的产品考量" (a product decision balancing user experience with anti-scraping and anti-astroturfing concerns).
- As reported at the time, about 500 comments were shown per view (popular, latest, friends), roughly 1,500 in total.
- Hot comments are reported to be shown in proportion to each star rating, **with randomization** to resist manipulation. This would explain the reordering seen in the 热门 list (section 2.4).

### 5.2 Developer and user reports

- A 2020 GooSeeker forum thread reports a cap of 25 pages × 20 = 500 short comments, even when logged in. The suggested workaround is to scrape 好评, 中评 and 差评 separately, for up to 1,500. This is the same strategy used here.
- In a Douban group thread, a user asks why a film shows 395,524 comments but only about 400 can be retrieved. A reply notes that the same limit applies when browsing by hand.
- A commercial scraper (Apify) states that short comments are limited to about 540 per popular title, while long reviews return "every review the title lists" (its example: The Shawshank Redemption, 14,897 reviews).

### 5.3 Discrepancy with prior reports

- Sources from 2020 report 500 short comments per list. This collection found **400 per list, and only 100 for 最新**.
- That suggests Douban has tightened the limit since 2020. No official statement about the current limit was found, so the write-up should report the October 2026 numbers as observed.

## 6. Methodological implications

- **The two datasets are different kinds of samples.**
  - Short comments are a **platform-curated subset**, selected by Douban's algorithm from time, popularity and star rating. They show what the platform puts in front of readers, not the full range of viewer opinion.
  - Long reviews are close to a **full census of publicly visible reviews**, minus those Douban folds or hides.
- Short-comment rankings are **dated snapshots**. Report the collection date, and expect the order of 热门 to shift slightly.
- The 热门·全部 list leans heavily positive. For comparing sentiment, use the separate rating lists rather than 热门·全部.

### Draft methods paragraph

> Data were collected from Douban, China's largest review platform for film and television, for *Scarlet Heart* (《步步惊心》, Hunan TV, 2011; Douban ID 5384548) in October 2026, using an automated browser session logged into a personal account. Douban does not display all short comments: since 2017 the platform has shown only an algorithmically selected subset, filtered by time and popularity, a measure it describes as a defense against scraping and astroturfing (Tencent News 2020). At the time of collection, each ranked list returned at most 400 comments (100 for the most-recent list). To approximate the range of visible opinion, I collected the popular list overall and separately for positive (4–5★), neutral (3★), and negative (1–2★) ratings, along with the most-recent list, for a total of 1,307 unique short comments out of 121,968 reported. Long-form reviews were not subject to this limit; I collected all 2,048 publicly visible reviews (96 percent of the 2,129 reported), together with their full text. Usernames were removed and user IDs replaced with one-way hashes.

## 7. Data management and ethics

- **Anonymization:** usernames and profile links were removed. User IDs were replaced with the first 12 characters of their SHA-256 hash. The same method was applied to short comments and long reviews, so the same author can be matched across both datasets without being identified.
- **Raw pages:** the original web pages for long reviews were saved in compressed form (`reviews_5384548/list_html/`, `review_html/`), so the data can be re-processed without scraping again.
- **Copyright:** long-review texts are used for analysis only. Quote short excerpts in publications, and don't share the full-text corpus publicly.
- **File handling:** don't re-save the CSVs from Excel, which can corrupt the hashed IDs and date formats. When Excel asks, choose "Don't Convert."
- **Rate limiting:** collection used deliberate delays and paused for Douban's verification checks rather than trying to bypass them.

## 8. Sources

- 腾讯新闻. 2020. "豆瓣回应'短评机制修改'：3年前就已调整，防水军控评." https://news.qq.com/rain/a/20201105A006SI00
- 虎嗅. 2020. "豆瓣'短评机制修改'，触动了谁的神经？" https://m.huxiu.com/article/391743.html
- 观察者网·风闻. 2020. "豆瓣回应'不再显示全部短评'：是为了反水军，用户也不需要全看." https://user.guancha.cn/main/content?id=406255
- GooSeeker 集搜客论坛. 2020. "豆瓣电影短评为何只能爬500条？" https://www.gooseeker.com/doc/thread-18285-1-1.html
- 豆瓣小组. "豆瓣评论爬虫求助." https://www.douban.com/group/topic/169516272/
- 知乎. "豆瓣电影的短评为什么只能查看500条？有没有查看更多条短评的方法？" https://www.zhihu.com/question/263776298/answer/330449890
- Apify. "Douban Scraper." https://apify.com/zen-studio/douban-scraper

<!-- To verify before citing: 观察者网 and 知乎 pages could not be opened directly; the "~500 per view" figure is from press coverage, not a direct Douban quote. -->
