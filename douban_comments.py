"""
Parser for Douban short-comment pages (/subject/<id>/comments), plus a simple requests-based CLI.

douban_playwright.py imports parse_page() from here. The requests CLI below is kept for reference:
in practice Douban redirects plain requests to sec.douban.com (an anti-bot check), especially from
cloud or data-center IPs such as Google Colab, even with a login cookie. Use douban_playwright.py.

Lists (status=P is 看过 "watched"; it does not mean "positive"):
  latest   -> sort=time
  hot      -> sort=new_score
  hot_pos  -> sort=new_score & percent_type=h   (好评, 4–5 stars)
  hot_mid  -> sort=new_score & percent_type=m   (一般, 3 stars)
  hot_neg  -> sort=new_score & percent_type=l   (差评, 1–2 stars)

Example (usually blocked; see above):
  python3 douban_comments.py 5384548 --mode latest
"""

import argparse
import csv
import random
import re
import time

import requests
from bs4 import BeautifulSoup

MODES = {
    "latest":  {"sort": "time"},
    "hot":     {"sort": "new_score"},
    "hot_pos": {"sort": "new_score", "percent_type": "h"},
    "hot_mid": {"sort": "new_score", "percent_type": "m"},
    "hot_neg": {"sort": "new_score", "percent_type": "l"},
}

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

STAR_MAP = {"allstar50": 5, "allstar40": 4, "allstar30": 3,
            "allstar20": 2, "allstar10": 1}


def parse_page(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for item in soup.select(".comment-item"):
        cid = item.get("data-cid", "")
        user_a = item.select_one(".comment-info a") or item.select_one(".comment-info > a")
        user = user_a.get_text(strip=True) if user_a else ""
        user_url = user_a.get("href", "") if user_a else ""

        rating = ""
        star = item.select_one(".comment-info span[class*=allstar], .comment-info .rating")
        if star:
            for c in star.get("class", []):
                if c in STAR_MAP:
                    rating = STAR_MAP[c]

        t = item.select_one(".comment-time")
        date = (t.get("title") or t.get_text(strip=True)) if t else ""

        v = item.select_one(".votes, .vote-count")
        votes = v.get_text(strip=True) if v else "0"

        loc = item.select_one(".comment-location")
        location = loc.get_text(strip=True) if loc else ""

        s = item.select_one(".short, .comment-content")
        text = s.get_text(" ", strip=True) if s else ""

        rows.append({"cid": cid, "user": user, "user_url": user_url,
                     "rating": rating, "date": date, "votes": votes,
                     "location": location, "text": text})
    return rows


def fetch(subject_id, mode, pages, domain, cookie, status, delay):
    base = f"https://{domain}.douban.com/subject/{subject_id}/comments"
    sess = requests.Session()
    sess.headers.update(HEADERS)
    if cookie:
        sess.headers["Cookie"] = cookie

    seen, out = set(), []
    for p in range(pages):
        params = {"start": p * 20, "limit": 20, "status": status, **MODES[mode]}
        r = sess.get(base, params=params, timeout=15)
        if "sec.douban.com" in r.url:
            print("[stop] Redirected to sec.douban.com (anti-bot check). "
                  "Use douban_playwright.py with a logged-in browser instead.")
            break
        if r.status_code != 200:
            print(f"[stop] page {p+1}: HTTP {r.status_code}")
            break
        rows = parse_page(r.text)
        if not rows:
            print(f"[stop] page {p+1}: 无更多评论（可能需要登录 cookie）")
            break
        new = [x for x in rows if x["cid"] not in seen]
        seen.update(x["cid"] for x in new)
        out.extend(new)
        print(f"page {p+1}: +{len(new)}  (total {len(out)})")
        time.sleep(delay + random.uniform(0, delay))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subject_id")
    ap.add_argument("--mode", choices=MODES, default="latest")
    ap.add_argument("--pages", type=int, default=30)
    ap.add_argument("--domain", default="movie", choices=["movie", "book"])
    ap.add_argument("--status", default="P", help="P=看过 F=想看")
    ap.add_argument("--cookie", default="")
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    rows = fetch(a.subject_id, a.mode, a.pages, a.domain, a.cookie, a.status, a.delay)
    out = a.out or f"douban_{a.subject_id}_{a.mode}.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["cid", "user", "user_url", "rating",
                                          "date", "votes", "location", "text"])
        w.writeheader()
        w.writerows(rows)
    print(f"saved {len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()
