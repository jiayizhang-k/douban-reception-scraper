# Douban Reception Scraper · 豆瓣评论抓取

Tools for collecting the Douban (豆瓣) audience responses to one film or TV series, for research on reception and collective memory:

- **Short comments (短评)**: the five ranked lists Douban shows on the 看过 ("watched") tab
- **Long reviews (长评：影评 / 剧评)**: every publicly visible review, with full text

The scripts drive a real, logged-in Chrome window, move slowly, keep every downloaded page so the data can be rebuilt offline, resume after any interruption, and anonymize user IDs. They were written for an M.A. thesis on *Scarlet Heart* (《步步惊心》, 2011) and work for any Douban subject. [`docs/case_study_scarlet_heart.md`](docs/case_study_scarlet_heart.md) is a full worked example.

中文说明见[下方](#中文简介)。

## Why a real browser

Douban blocks most automated access:

| Approach | Result |
|---|---|
| Python `requests` from Google Colab or another cloud server | Redirected to `sec.douban.com` (anti-bot check), even with a login cookie |
| Mobile API (`m.douban.com/rexxar/api/v2/.../interests`) | About 120 popular comments at most; sort and rating parameters are ignored; a cookie gives HTTP 403 |
| `requests` from a home network, not logged in | Redirected to `sec.douban.com` |
| **Real browser (Playwright) + logged in + home or campus network + slow pace** | **Works** |

When Douban asks for a verification step, the scripts stop and wait for you to complete it in the browser. They do not try to get around it.

## What you can collect (observed October 2026, logged in)

**Short comments.** Since 2017 Douban shows only an algorithmically selected subset of short comments. Each ranked list stops at a fixed number:

| List | Script name | URL parameters | Maximum |
|---|---|---|---|
| 看过 · 热门 · 全部 (popular, all) | `hot` | `status=P&sort=new_score` | 400 |
| 看过 · 热门 · 好评 (4–5★) | `hot_pos` | `…&percent_type=h` | 400 |
| 看过 · 热门 · 一般 (3★) | `hot_mid` | `…&percent_type=m` | 400 |
| 看过 · 热门 · 差评 (1–2★) | `hot_neg` | `…&percent_type=l` | 400 |
| 看过 · 最新 (latest) | `latest` | `status=P&sort=time` | 100 |

`status=P` means 看过 ("watched"), not "positive". The 最新 list has no rating filter. Together the five lists give about 1,300 unique comments per title (1,307 for *Scarlet Heart*, out of 121,968 reported). The rating-filtered lists come back identical on repeat runs; only 最新 changes.

**Long reviews.** No cap was observed. The scripts collect every review Douban displays (2,048 of the 2,129 reported for *Scarlet Heart*; the rest are folded or hidden by the platform, more often among low-rated reviews).

## Files

| File | What it does |
|---|---|
| `douban_playwright.py` | Short comments: the five lists above, with a logged-in browser |
| `douban_comments.py` | Page parser used by `douban_playwright.py` (its own `requests` CLI is usually blocked) |
| `clean_merge.py` | Anonymizes, deduplicates and merges one or more short-comment runs |
| `douban_reviews.py` | Long reviews: seven ranked lists, then each review's full text; resumable |
| `make_reader.py` | Builds a read-only HTML page for searching and reading the long reviews |
| `docs/case_study_scarlet_heart.md` | Methods notes for the *Scarlet Heart* corpus: limits, coverage, sources |

Keep all `.py` files in the same folder.

## Setup

```bash
pip3 install -r requirements.txt
python3 -m playwright install chromium
```

On a Mac, install Python from python.org and run `Install Certificates.command` once.

**Find the subject ID.** Open the film or series on Douban. The number in the address `movie.douban.com/subject/<ID>/` is the ID (*Scarlet Heart* is `5384548`). TV series use the same `movie.douban.com` address.

## Short comments

```bash
caffeinate -i python3 douban_playwright.py --subject 5384548
```

1. A Chrome window opens. Log in to Douban by hand, then press Enter in Terminal. The login is saved in `douban_profile/`, so you only do this once.
2. The script pages through the five lists, waiting 5–9 seconds between pages and 30–60 seconds between lists (about 20–30 minutes in all).
3. If Douban asks for verification, complete it in the browser and press Enter.
4. Results go to a new folder `run_<ID>_<date>_<time>/`, so earlier runs are never overwritten.

`caffeinate -i` keeps a Mac awake; leave it out on Windows or Linux. To run only some lists, or to re-run a list into an existing folder:

```bash
python3 douban_playwright.py --subject 5384548 hot_neg latest
python3 douban_playwright.py --subject 5384548 hot_neg --dir run_5384548_20261003_1802
```

Then merge and anonymize (list each run's `_all.csv`, oldest first):

```bash
python3 clean_merge.py run_5384548_20261003_1802/douban_5384548_all.csv
```

This writes `douban_<ID>_comments_unique.csv` (one row per comment) and `douban_<ID>_comments_long.csv` (one row per run × list × comment).

## Long reviews

```bash
python3 douban_reviews.py --subject 5384548 test           # page 1 of each list + 2 full texts; check the output
caffeinate -i python3 douban_reviews.py --subject 5384548  # all lists -> all full texts -> CSV
caffeinate -i python3 douban_reviews.py --subject 5384548 full 300   # next 300 full texts only
python3 douban_reviews.py --subject 5384548 build          # offline: rebuild the CSVs from saved pages
```

Stop with Ctrl+C at any time; the same command resumes where it left off. About 2,000 reviews take roughly five hours of unattended running. Raw pages are kept (gzip) in `reviews_<ID>/list_html/` and `reviews_<ID>/review_html/`, so the parser can be changed and `build` re-run without going back online. Output: `reviews_<ID>/reviews_unique.csv` (one row per review, with full text) and `reviews_<ID>/reviews_lists_long.csv`.

To read the reviews without touching the CSV:

```bash
python3 make_reader.py reviews_5384548/reviews_unique.csv -o reader.html --title "《步步惊心》豆瓣剧评"
```

## Output fields

**Short comments** (`douban_<ID>_comments_unique.csv`): `cid` comment ID · `user_hash` · `rating` 1–5 (blank = no rating) · `date` · `votes` (有用) · `location` (province-level IP location at posting; Douban shows it only from about September 2022) · `text` · `rank_<list>` / `in_<list>` rank in and presence on each list · `n_lists` · `year` · `sentiment` (pos / mid / neg / unrated) · `nchar`.

**Long reviews** (`reviews_unique.csv`): `rid` review ID · `url` · `title` · `author_hash` · `rating` · `date` · `useful` / `useless` votes · `replies` · `spoiler` · `rank_hot`, `rank_r5` … `rank_r1`, `rank_latest` · `n_lists` · `has_full` · `nchar` · `ip_location` (currently not parsed) · `text` · `excerpt`.

`user_hash` and `author_hash` are made the same way, so one person can be matched across both datasets without being identified.

## Using this responsibly

- **Go slowly.** Keep the built-in delays, collect one title at a time, and stop if Douban starts asking for verification repeatedly.
- **Never share `douban_profile/`.** It holds your logged-in session. The `.gitignore` keeps it, and all collected data, out of the repository.
- **Anonymization.** Usernames and profile links are dropped, and user IDs are replaced with the first 12 characters of a SHA-256 hash. Because the method is public and Douban IDs are public, an unsalted hash can be matched by anyone who hashes candidate IDs. Before sharing any derived data, set a secret salt, and use the same one for both scripts: `export DOUBAN_HASH_SALT="something-only-you-know"`. Leave it unset to reproduce earlier unsalted hashes.
- **Copyright.** Review texts belong to their authors. Use them for analysis and quote short excerpts; do not redistribute the full-text corpus.
- **Spreadsheets.** Do not open and re-save the CSVs in Excel. It breaks hashes into scientific notation, reformats dates, and splits reviews longer than 32,767 characters into extra rows. Read them in R or Python, and choose "Don't Convert" if Excel asks.
- **Page changes.** Douban changes its pages from time to time. If `test` shows empty titles, stars or dates, the selectors in `parse_page`, `parse_list` or `parse_review` need updating.

## 中文简介

用真实的、已登录的 Chrome 窗口抓取某部电影或剧集的豆瓣短评（看过 · 5 个榜单，约 1,300 条）和全部可见长评（含全文）。

1. 安装：`pip3 install -r requirements.txt`，然后 `python3 -m playwright install chromium`
2. 豆瓣编号：作品页面网址 `movie.douban.com/subject/` 后面的数字
3. 短评：`caffeinate -i python3 douban_playwright.py --subject 编号`，第一次在弹出的浏览器里手动登录，回终端按回车
4. 合并、匿名化：`python3 clean_merge.py run_编号_日期_时间/douban_编号_all.csv`
5. 长评：先 `python3 douban_reviews.py --subject 编号 test` 检查，再去掉 `test` 正式运行；可随时 Ctrl+C，重跑同一命令会接着抓
6. 阅读长评：`python3 make_reader.py reviews_编号/reviews_unique.csv`

注意：慢慢抓，遇到验证就在浏览器里手动完成；不要上传或分享 `douban_profile/`（登录信息）；长评全文有版权，只用于分析和引用片段；不要用 Excel 保存 CSV。

## Author

Jiayi Zhang, University of California, Los Angeles.

## License

Code: MIT (see `LICENSE`). This license covers the code only, not any data collected with it.
