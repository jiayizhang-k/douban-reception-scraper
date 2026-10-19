"""
Douban short comments (短评) with a real, logged-in browser (Playwright).
豆瓣短评抓取：用真实 Chrome 窗口翻页，豆瓣看到的是一个正常登录的用户。

First-time setup (run once in Terminal):
    pip3 install -r requirements.txt
    python3 -m playwright install chromium

Run (in Terminal, not Jupyter). The subject ID is the number in the film's or show's URL,
movie.douban.com/subject/<ID>/ :
    caffeinate -i python3 douban_playwright.py --subject 5384548
(caffeinate keeps a Mac awake; leave it out on Windows/Linux.)

Only some lists, or re-run lists into an existing folder:
    python3 douban_playwright.py --subject 5384548 hot_neg latest
    python3 douban_playwright.py --subject 5384548 hot_neg --dir run_5384548_20261003_1802

The first run opens a browser window: log in to Douban by hand, then press Enter in Terminal.
The login is kept in douban_profile/ (never share or commit that folder).
Each run saves to a new folder run_<ID>_<date>_<time>/, so earlier data is never overwritten.

Needs douban_comments.py in the same folder (it provides the page parser).
"""

import csv
import glob
import os
import sys
import random
import time
from datetime import datetime

from playwright.sync_api import sync_playwright

from douban_comments import parse_page

SUBJECT_ID = None        # set from --subject
MAX_PAGES = 30          # 每个榜单最多翻多少页
DELAY = (5, 9)          # 每页之间随机等待秒数

MODES = {
    "latest":  "sort=time",
    "hot":     "sort=new_score",
    "hot_pos": "sort=new_score&percent_type=h",
    "hot_mid": "sort=new_score&percent_type=m",
    "hot_neg": "sort=new_score&percent_type=l",
}

FIELDS = ["cid", "user", "user_url", "rating", "date",
          "votes", "location", "text", "list", "rank"]


def safe_goto(page, url, mode):
    """网络断开（如电脑睡眠）时不崩溃：自动重试，多次失败后等你按回车。"""
    for attempt in range(5):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            return
        except Exception as e:
            print(f"[{mode}] 网络出错（{str(e).splitlines()[0][:80]}），30 秒后重试…")
            time.sleep(30)
    input(f"[{mode}] 连续失败。请检查网络、确认电脑没有睡眠，然后按回车继续…")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)


def scrape_mode(page, mode, query):
    rows, seen = [], set()
    for p in range(MAX_PAGES):
        url = (f"https://movie.douban.com/subject/{SUBJECT_ID}/comments"
               f"?start={p*20}&limit=20&status=P&{query}")
        safe_goto(page, url, mode)

        # 遇到验证页：暂停，让你在浏览器里手动完成
        if "sec.douban.com" in page.url:
            input(f"[{mode}] 豆瓣要求验证。请在浏览器里完成后按回车继续…")
            page.goto(url, wait_until="domcontentloaded")

        items = parse_page(page.content())
        new = [x for x in items if x["cid"] not in seen]
        if not new:
            print(f"[{mode}] page {p+1}: 没有更多评论，结束")
            break
        for x in new:
            seen.add(x["cid"])
            x["list"] = mode
            x["rank"] = len(rows) + 1
            rows.append(x)
        print(f"[{mode}] page {p+1}: +{len(new)} (total {len(rows)})")
        time.sleep(random.uniform(*DELAY))
    return rows


def main():
    global SUBJECT_ID
    args = sys.argv[1:]
    if "--subject" not in args:
        sys.exit("Please give the Douban subject ID, e.g.  python3 douban_playwright.py --subject 5384548\n"
                 "请用 --subject 指定豆瓣编号（网址 movie.douban.com/subject/ 后面的数字）")
    i = args.index("--subject")
    SUBJECT_ID = args[i + 1] if i + 1 < len(args) else ""
    args = args[:i] + args[i + 2:]
    if not SUBJECT_ID.isdigit():
        sys.exit(f"--subject should be a number, got {SUBJECT_ID!r}")
    outdir = None
    if "--dir" in args:
        i = args.index("--dir")
        outdir = args[i + 1]
        args = args[:i] + args[i + 2:]
    modes = args or list(MODES)
    bad = [m for m in modes if m not in MODES]
    if bad:
        sys.exit(f"不认识的榜单：{bad}，可选：{list(MODES)}")

    outdir = outdir or f"run_{SUBJECT_ID}_" + datetime.now().strftime("%Y%m%d_%H%M")
    os.makedirs(outdir, exist_ok=True)

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            "douban_profile", headless=False, locale="zh-CN")
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        page.goto("https://www.douban.com/")
        input("如果还没登录，请在弹出的浏览器里登录豆瓣，然后回到这里按回车…")
        print(f"本次结果保存在文件夹：{outdir}（不会覆盖旧文件）\n")

        for n, mode in enumerate(modes):
            rows = scrape_mode(page, mode, MODES[mode])
            fname = os.path.join(outdir, f"douban_{SUBJECT_ID}_{mode}.csv")
            with open(fname, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=FIELDS)
                w.writeheader()
                w.writerows(rows)
            print(f"saved {len(rows)} -> {fname}\n")
            if n < len(modes) - 1:
                time.sleep(random.uniform(30, 60))   # 榜单之间多歇一会
        ctx.close()

    # 用文件夹里所有单个榜单的 CSV 重新合成 _all.csv（中途断过也没关系）
    all_rows = []
    for m in MODES:
        fname = os.path.join(outdir, f"douban_{SUBJECT_ID}_{m}.csv")
        if os.path.exists(fname):
            with open(fname, encoding="utf-8-sig") as f:
                all_rows.extend(csv.DictReader(f))
    with open(os.path.join(outdir, f"douban_{SUBJECT_ID}_all.csv"), "w",
              newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(all_rows)
    have = [m for m in MODES if os.path.exists(
        os.path.join(outdir, f"douban_{SUBJECT_ID}_{m}.csv"))]
    print(f"全部完成：{len(all_rows)} 行，包含榜单 {have}")


if __name__ == "__main__":
    main()
