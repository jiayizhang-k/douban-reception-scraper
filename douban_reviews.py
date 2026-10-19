"""
Douban long reviews (长评：影评 / 剧评) with a real, logged-in browser (Playwright).

Two steps:
  1. lists: page through each ranked list and record every review's rank, title, stars, votes, excerpt
  2. full : open each review page and save the full text

Lists:
  hot     最受欢迎            sort=hotest
  r5..r1  按评星查看 5–1 星    rating=5 … rating=1
  latest  最新发布的          sort=time

Usage (in Terminal, in the folder that holds douban_profile/). The subject ID is the number
in the URL movie.douban.com/subject/<ID>/ :
  python3 douban_reviews.py --subject 5384548 test           test: page 1 of each list + 2 full texts
  caffeinate -i python3 douban_reviews.py --subject 5384548  full run: lists -> full texts -> CSV
  caffeinate -i python3 douban_reviews.py --subject 5384548 lists      lists only
  caffeinate -i python3 douban_reviews.py --subject 5384548 full       full texts not yet downloaded
  caffeinate -i python3 douban_reviews.py --subject 5384548 full 300   only the next 300 full texts
  python3 douban_reviews.py --subject 5384548 build          offline: rebuild the CSVs from saved pages

Stop any time with Ctrl+C; running the same command again resumes (saved pages are never re-fetched).

Output folder reviews_<ID>/:
  list_html/, review_html/   the raw pages (gzip), so the data can be re-parsed offline
  reviews_lists_long.csv     one row per list x review (with rank)
  reviews_unique.csv         one row per review: ranks in each list + full text

Needs: pip3 install -r requirements.txt
"""

import csv
import gzip
import hashlib
import os
import random
import re
import sys
import time

from bs4 import BeautifulSoup

SUBJECT_ID = BASE = OUT = LIST_DIR = REV_DIR = None   # set by configure() from --subject

# Optional: set DOUBAN_HASH_SALT (any secret string) before running to salt the user-ID hashes.
# Leave it unset to reproduce earlier unsalted hashes. Use the same salt for short comments.
SALT = os.environ.get("DOUBAN_HASH_SALT", "")


def configure(subject_id):
    global SUBJECT_ID, BASE, OUT, LIST_DIR, REV_DIR
    SUBJECT_ID = subject_id
    BASE = f"https://movie.douban.com/subject/{SUBJECT_ID}/reviews"
    OUT = f"reviews_{SUBJECT_ID}"
    LIST_DIR = os.path.join(OUT, "list_html")
    REV_DIR = os.path.join(OUT, "review_html")

LISTS = {
    "hot":    "sort=hotest",
    "r5":     "rating=5",
    "r4":     "rating=4",
    "r3":     "rating=3",
    "r2":     "rating=2",
    "r1":     "rating=1",
    "latest": "sort=time",
}

MAX_PAGES = 150            # 每个榜单最多翻多少页（20 篇/页）
LIST_DELAY = (5, 9)        # 列表页之间等待秒数
REVIEW_DELAY = (4, 8)      # 全文页之间等待秒数
BREAK_EVERY = 100          # 每抓多少篇全文休息一次
BREAK_LEN = (60, 120)      # 休息秒数


# ---------- 小工具 ----------

def gz_write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(text)


def gz_read(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return f.read()


def list_path(name, p):
    return os.path.join(LIST_DIR, f"{name}_{p:03d}.html.gz")


def review_path(rid):
    return os.path.join(REV_DIR, f"{rid}.html.gz")


def num(s):
    m = re.search(r"\d+", s or "")
    return int(m.group()) if m else 0


def star(tag):
    if not tag:
        return ""
    m = re.search(r"allstar(\d)0", " ".join(tag.get("class", [])))
    return int(m.group(1)) if m else ""


def uid_hash(href):
    m = re.search(r"/people/([^/]+)/", href or "")
    return hashlib.sha256((SALT + m.group(1)).encode()).hexdigest()[:12] if m else ""


# ---------- 解析 ----------

def parse_list(html):
    """列表页 -> [{rid, title, author_hash, rating, date, useful, useless, replies, spoiler, excerpt}]"""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for it in soup.select(".review-item"):
        a = it.select_one("h2 a[href*='/review/']") or it.select_one("a[href*='/review/']")
        m = re.search(r"/review/(\d+)", a.get("href", "")) if a else None
        if not m:
            continue
        hd = it.select_one("header") or it
        user_a = hd.select_one("a.name") or hd.select_one("a[href*='/people/']")
        meta = hd.select_one(".main-meta")

        short = it.select_one(".short-content")
        spoiler = bool(it.select_one(".spoiler-tip"))
        excerpt = ""
        if short:
            for t in short.select(".spoiler-tip, .unfold"):
                t.decompose()
            excerpt = re.sub(r"\(\s*\)\s*$", "", short.get_text(" ", strip=True)).strip()

        up = it.select_one("[id^='r-useful_count']") or it.select_one(".action .up")
        down = it.select_one("[id^='r-useless_count']") or it.select_one(".action .down")
        reply = it.select_one("a.reply")

        out.append({
            "rid": m.group(1),
            "title": a.get_text(strip=True),
            "author_hash": uid_hash(user_a.get("href") if user_a else ""),
            "rating": star(hd.select_one("[class*=allstar]")),
            "date": meta.get_text(strip=True) if meta else "",
            "useful": num(up.get_text() if up else ""),
            "useless": num(down.get_text() if down else ""),
            "replies": num(reply.get_text() if reply else ""),
            "spoiler": int(spoiler),
            "excerpt": excerpt,
        })
    return out


def parse_review(html):
    """剧评全文页 -> {title, text, date, rating, useful, useless, ip_location, author_hash}"""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one("[property='v:summary']") or soup.select_one("#content h1")
    content = soup.select_one(".review-content") or soup.select_one("#link-report")
    hd = soup.select_one(".main-hd") or soup
    date = hd.select_one(".main-meta") or hd.select_one("[property='v:dtreviewed']")
    user_a = hd.select_one("a[href*='/people/']")
    useful = soup.select_one("[class*=useful_count]")
    useless = soup.select_one("[class*=useless_count]")

    ip = ""
    ip_tag = hd.select_one("[class*=ip-location], [class*=ip_location]")
    if ip_tag:
        ip = ip_tag.get_text(strip=True)
    else:
        m = re.search(r"IP属地[:：]?\s*([一-龥A-Za-z]+)", hd.get_text(" "))
        ip = m.group(1) if m else ""
    ip = re.sub(r"^IP属地[:：]?\s*", "", ip)

    text = content.get_text("\n", strip=True) if content else ""
    return {
        "title": title.get_text(strip=True) if title else "",
        "text": text,
        "date": date.get_text(strip=True) if date else "",
        "rating": star(hd.select_one("[class*=allstar]")),
        "useful": num(useful.get_text() if useful else ""),
        "useless": num(useless.get_text() if useless else ""),
        "ip_location": ip,
        "author_hash": uid_hash(user_a.get("href") if user_a else ""),
    }


def list_rows():
    """读取所有已下载的列表页，按榜单顺序返回（含排名）。"""
    rows = []
    for name in LISTS:
        seen = set()
        for p in range(MAX_PAGES):
            path = list_path(name, p)
            if not os.path.exists(path):
                break
            for x in parse_list(gz_read(path)):
                if x["rid"] in seen:
                    continue
                seen.add(x["rid"])
                rows.append({"list": name, "page": p + 1, "rank": len(seen), **x})
    return rows


# ---------- 浏览器 ----------

def blocked(page):
    u = page.url
    return "sec.douban.com" in u or "/misc/sorry" in u or "accounts.douban.com" in u


def fetch(page, url, label):
    resp = None
    for attempt in range(5):
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            break
        except Exception as e:
            print(f"[{label}] 网络出错（{str(e).splitlines()[0][:80]}），30 秒后重试…")
            time.sleep(30)
    else:
        input(f"[{label}] 连续失败。请检查网络、确认电脑没有睡眠，然后按回车继续…")
        resp = page.goto(url, wait_until="domcontentloaded", timeout=60000)

    while blocked(page):
        input(f"[{label}] 豆瓣要求验证或登录。请在浏览器里完成后按回车继续…")
        resp = page.goto(url, wait_until="domcontentloaded", timeout=60000)
    return page.content(), (resp.status if resp else None)


def open_browser(pw):
    ctx = pw.chromium.launch_persistent_context(
        "douban_profile", headless=False, locale="zh-CN")
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://www.douban.com/")
    input("确认浏览器里已登录豆瓣（右上角有你的账号），然后回到这里按回车…")
    return ctx, page


# ---------- 第一步：榜单 ----------

def scrape_lists(page, names=None, max_pages=MAX_PAGES):
    for name in names or LISTS:
        seen = set()
        for p in range(max_pages):
            path = list_path(name, p)
            cached = os.path.exists(path)
            if cached:
                html = gz_read(path)
            else:
                url = f"{BASE}?start={p*20}&{LISTS[name]}"
                html, status = fetch(page, url, name)
            items = parse_list(html)
            new = [x for x in items if x["rid"] not in seen]
            if not new:
                print(f"[{name}] page {p+1}: 没有更多剧评，结束（共 {len(seen)} 篇）\n")
                break
            if not cached:
                gz_write(path, html)
            seen.update(x["rid"] for x in new)
            if not cached:
                print(f"[{name}] page {p+1}: +{len(new)} (total {len(seen)})")
                time.sleep(random.uniform(*LIST_DELAY))
        else:
            print(f"[{name}] 已到 {max_pages} 页上限（共 {len(seen)} 篇）\n")


# ---------- 第二步：全文 ----------

def scrape_full(page, limit=None):
    order, seen = [], set()
    for r in list_rows():                      # 先 hot 的顺序，再补其他榜单
        if r["rid"] not in seen:
            seen.add(r["rid"])
            order.append(r["rid"])
    todo = [rid for rid in order if not os.path.exists(review_path(rid))]
    print(f"榜单里共 {len(order)} 篇，已下载全文 {len(order) - len(todo)} 篇，待下载 {len(todo)} 篇")
    if limit:
        todo = todo[:limit]
        print(f"本次只下载 {len(todo)} 篇")
    if not todo:
        return

    empty_streak = 0
    for i, rid in enumerate(todo, 1):
        html, status = fetch(page, f"https://movie.douban.com/review/{rid}/", rid)
        rec = parse_review(html)
        if rec["text"] or status == 404:
            gz_write(review_path(rid), html)
            empty_streak = 0
            tag = "（已删除）" if status == 404 else f"{len(rec['text'])} 字"
            print(f"[{i}/{len(todo)}] {rid} {tag} {rec['title'][:24]}")
        else:
            empty_streak += 1
            print(f"[{i}/{len(todo)}] {rid} 没解析到正文（status {status}），跳过，下次再试")
            if empty_streak >= 3:
                input("连续 3 篇都没有正文，可能被限制或掉线了。请看一下浏览器，处理好后按回车继续…")
                empty_streak = 0
        time.sleep(random.uniform(*REVIEW_DELAY))
        if i % BREAK_EVERY == 0 and i < len(todo):
            s = random.uniform(*BREAK_LEN)
            print(f"—— 已抓 {i} 篇，休息 {s:.0f} 秒 ——")
            time.sleep(s)


# ---------- 生成 CSV ----------

def build():
    rows = list_rows()
    if not rows:
        print("还没有下载任何列表页。")
        return
    os.makedirs(OUT, exist_ok=True)

    long_cols = ["list", "page", "rank", "rid", "title", "author_hash", "rating", "date",
                 "useful", "useless", "replies", "spoiler", "excerpt"]
    with open(os.path.join(OUT, "reviews_lists_long.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=long_cols)
        w.writeheader()
        w.writerows(rows)

    uniq = {}
    for r in rows:
        u = uniq.setdefault(r["rid"], {k: r[k] for k in long_cols[3:]})
        u["rank_" + r["list"]] = r["rank"]

    n_full = n_deleted = 0
    for rid, u in uniq.items():
        u["url"] = f"https://movie.douban.com/review/{rid}/"
        u["n_lists"] = sum(1 for n in LISTS if u.get("rank_" + n))
        path = review_path(rid)
        full = parse_review(gz_read(path)) if os.path.exists(path) else None
        if full and full["text"]:
            n_full += 1
            u["has_full"] = 1
            u["text"] = full["text"]
            u["ip_location"] = full["ip_location"]
            u["useful"] = full["useful"] or u["useful"]
            u["useless"] = full["useless"] or u["useless"]
        else:
            u["has_full"] = 0
            u["text"] = ""
            u["ip_location"] = ""
            if full:
                n_deleted += 1
        u["nchar"] = len(u["text"])

    cols = (["rid", "url", "title", "author_hash", "rating", "date", "useful", "useless",
             "replies", "spoiler"] + [f"rank_{n}" for n in LISTS] +
            ["n_lists", "has_full", "nchar", "ip_location", "text", "excerpt"])
    big = 10 ** 9
    ordered = sorted(uniq.values(), key=lambda u: tuple(u.get("rank_" + n) or big for n in LISTS))
    with open(os.path.join(OUT, "reviews_unique.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(ordered)

    print("各榜单篇数：")
    for n in LISTS:
        c = sum(1 for r in rows if r["list"] == n)
        if c:
            print(f"  {n:7s} {c}")
    print(f"去重后共 {len(uniq)} 篇；已有全文 {n_full} 篇；已删除 {n_deleted} 篇；"
          f"缺全文 {len(uniq) - n_full - n_deleted} 篇")
    print(f"已保存：{OUT}/reviews_unique.csv 和 {OUT}/reviews_lists_long.csv")


# ---------- 测试 ----------

def test(page):
    print("== 每个榜单抓第 1 页 ==")
    for name in LISTS:
        scrape_lists(page, [name], max_pages=1)
        items = parse_list(gz_read(list_path(name, 0))) if os.path.exists(list_path(name, 0)) else []
        if items:
            ratings = sorted({x["rating"] for x in items if x["rating"] != ""})
            dates = sorted(x["date"] for x in items if x["date"])
            print(f"  {name:7s} {len(items)} 篇 | 星级 {ratings} | 日期 {dates[0][:10]} ~ {dates[-1][:10]}"
                  f" | 第 1 篇：{items[0]['title'][:20]}（有用 {items[0]['useful']}）\n")
        else:
            print(f"  {name:7s} 没解析到剧评！\n")

    print("== 抓 2 篇全文 ==")
    hot = parse_list(gz_read(list_path("hot", 0))) if os.path.exists(list_path("hot", 0)) else []
    for x in hot[:2]:
        path = review_path(x["rid"])
        if not os.path.exists(path):
            html, _ = fetch(page, f"https://movie.douban.com/review/{x['rid']}/", x["rid"])
            gz_write(path, html)
            time.sleep(random.uniform(*REVIEW_DELAY))
        r = parse_review(gz_read(path))
        print(f"  {x['rid']} 《{r['title']}》 {r['rating']}星 {r['date']} 有用 {r['useful']} "
              f"IP {r['ip_location'] or '-'} | {len(r['text'])} 字")
        print(f"    开头：{r['text'][:80]}…\n")
    print("Check the output above (titles, stars, dates, text). If it looks right, run:\n"
          f"  caffeinate -i python3 douban_reviews.py --subject {SUBJECT_ID}")


# ---------- 入口 ----------

def main():
    args = sys.argv[1:]
    if "--subject" not in args:
        sys.exit(__doc__)
    i = args.index("--subject")
    sid = args[i + 1] if i + 1 < len(args) else ""
    if not sid.isdigit():
        sys.exit(f"--subject should be a number (the ID in movie.douban.com/subject/<ID>/), got {sid!r}")
    configure(sid)
    args = args[:i] + args[i + 2:]
    cmd = args[0] if args else "all"
    if cmd == "build":
        build()
        return
    if cmd not in ("all", "test", "lists", "full"):
        sys.exit(__doc__)
    limit = int(args[1]) if cmd == "full" and len(args) > 1 else None

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        ctx, page = open_browser(pw)
        try:
            if cmd == "test":
                test(page)
            if cmd in ("all", "lists"):
                scrape_lists(page)
            if cmd in ("all", "full"):
                scrape_full(page, limit)
        except KeyboardInterrupt:
            print("\n已中断。已下载的部分都保存了，再运行同一条命令会接着抓。")
        finally:
            try:
                ctx.close()
            except Exception:
                pass   # Ctrl+C 时浏览器可能已经先关了，忽略
    if cmd != "test":
        build()


if __name__ == "__main__":
    main()
