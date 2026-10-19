"""
Clean, anonymize and merge one or more short-comment runs.
清洗、匿名化、合并多次抓取的短评。

Usage (list each run's _all.csv in the order the runs were made):
    python3 clean_merge.py run_5384548_20261003_1530/douban_5384548_all.csv run_5384548_20261005_0900/douban_5384548_all.csv

Output (named after the subject ID found in the first file name; never overwrites other subjects):
  douban_<ID>_comments_long.csv    one row per run x list x comment (with scrape_run), anonymized
  douban_<ID>_comments_unique.csv  one row per comment (deduplicated by cid), with in_*/rank_* per list

Anonymization: usernames and profile links are dropped; the user ID becomes user_hash, the first
12 hex digits of SHA-256. Set DOUBAN_HASH_SALT to the same secret you used for long reviews to salt it.
Ranks: rank_* is the comment's rank the first time it appeared in that list.
Needs: pip3 install pandas
"""

import hashlib
import os
import re
import sys

import pandas as pd

LISTS = ["hot", "hot_pos", "hot_mid", "hot_neg", "latest"]
SALT = os.environ.get("DOUBAN_HASH_SALT", "")


def load(path, run_no):
    d = pd.read_csv(path, encoding="utf-8-sig", dtype={"cid": str})
    d["scrape_run"] = run_no
    d["scrape_file"] = path
    return d


def main(paths):
    if not paths:
        sys.exit(__doc__)
    m = re.search(r"douban_(\d+)_all\.csv$", os.path.basename(paths[0]))
    prefix = f"douban_{m.group(1)}_comments" if m else "douban_comments"
    df = pd.concat([load(p, i + 1) for i, p in enumerate(paths)], ignore_index=True)

    # 匿名化
    uid = df["user_url"].astype(str).str.extract(r"/people/([^/]+)/")[0].astype(str)
    df["user_hash"] = uid.map(lambda x: hashlib.sha256((SALT + x).encode()).hexdigest()[:12])
    df = df.drop(columns=["user", "user_url"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

    df.to_csv(f"{prefix}_long.csv", index=False, encoding="utf-8-sig")

    # 每条评论一行：保留最新一次抓取的文本/赞数
    base = (df.sort_values("scrape_run")
              .drop_duplicates("cid", keep="last")
              [["cid", "user_hash", "rating", "date", "votes", "location", "text"]])
    first = df.sort_values("scrape_run").drop_duplicates(["cid", "list"], keep="first")
    ranks = (first.pivot(index="cid", columns="list", values="rank")
                  .reindex(columns=LISTS).add_prefix("rank_"))
    u = base.merge(ranks, left_on="cid", right_index=True, how="left")
    for l in LISTS:
        u["in_" + l] = u["rank_" + l].notna().astype(int)
    u["n_lists"] = u[[f"in_{l}" for l in LISTS]].sum(axis=1)
    u["first_seen_run"] = u["cid"].map(df.groupby("cid")["scrape_run"].min())
    u["year"] = u["date"].dt.year
    u["sentiment"] = u["rating"].map(
        lambda r: "unrated" if pd.isna(r) else "pos" if r >= 4 else "mid" if r == 3 else "neg")
    u["nchar"] = u["text"].astype(str).str.len()
    u = u.sort_values("votes", ascending=False)
    u.to_csv(f"{prefix}_unique.csv", index=False, encoding="utf-8-sig")
    print(f"saved {prefix}_unique.csv and {prefix}_long.csv")

    print(f"读取 {len(paths)} 次抓取，共 {len(df)} 行 -> 去重后 {len(u)} 条")
    print(u["sentiment"].value_counts().to_string())
    for i in range(2, len(paths) + 1):
        print(f"第 {i} 次抓取新增：{(u['first_seen_run'] == i).sum()} 条")


if __name__ == "__main__":
    main(sys.argv[1:])
