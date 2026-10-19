"""
Turn reviews_unique.csv into a single HTML page for reading the reviews in a browser (read-only;
it never changes the data). Search with highlighting, filter by year, stars and reposts, sort,
and expand any review to its full text.
把 reviews_unique.csv 变成一个可以在浏览器里阅读的网页（只读，不会改动数据）。

Usage:
    python3 make_reader.py reviews_5384548/reviews_unique.csv
    python3 make_reader.py reviews_5384548/reviews_unique.csv -o reader.html --title "《步步惊心》豆瓣剧评"
Then double-click the HTML file. Keep it private: it contains full review texts.
"""
import argparse
import csv
import json
import re

# A title marks a repost/translation only when it says so: 【转】（转）[转] 转载 转自 翻译 搬运.
# (A bare 转 would also catch original titles such as 扭转乾坤 or 斗转星移.)
REPOST = r"[【（(\[《]\s*转\s*[】）)\]》]|转载|转自|翻译|搬运"

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("csv", help="path to reviews_unique.csv")
ap.add_argument("-o", "--out", default="review_reader.html")
ap.add_argument("--title", default="豆瓣长评 · 阅读器")
a = ap.parse_args()

rows = []
with open(a.csv, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        if r.get("has_full") not in ("1", "1.0"):
            continue
        date = (r.get("date") or "")[:16]
        title = r.get("title") or ""
        rows.append({
            "id": r["rid"], "t": title, "d": date,
            "y": date[:4] if date[:4].isdigit() else "",
            "r": int(float(r["rating"])) if r.get("rating") else None,
            "u": int(float(r.get("useful") or 0)), "n": int(float(r.get("nchar") or 0)),
            "rp": bool(re.search(REPOST, title)),
            "x": r.get("text") or "", "url": r.get("url") or "",
        })

years = sorted({x["y"] for x in rows if x["y"]})
year_opts = "".join(f'<option value="{y}">{y}</option>' for y in years)
data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
title = a.title.replace("<", "&lt;").replace(">", "&gt;")

page = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#f3f2ef;--surface:#fcfbf9;--ink:#393536;--muted:#736d6b;--line:#e3e0dc;--accent:#a26f7a;--mark:#f1d5da;
--font:"PingFang SC","Hiragino Sans GB","Noto Sans SC",system-ui,sans-serif;--mono:ui-monospace,"SF Mono",Menlo,monospace}
@media (prefers-color-scheme:dark){:root{--bg:#1f1f20;--surface:#29292a;--ink:#ecebe9;--muted:#aeaaa7;--line:#3b3a3a;--accent:#d6a5ae;--mark:#5a3c42;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--font);font-size:15px;line-height:1.7;padding:20px 16px 60px}
.wrap{max-width:820px;margin:0 auto;display:grid;gap:16px}
h1{font-size:22px;margin:0;font-weight:600}
.sub{color:var(--muted);font-size:13px;margin:2px 0 0}
.bar{position:sticky;top:0;z-index:2;background:var(--bg);padding:10px 0;display:flex;flex-wrap:wrap;gap:8px;align-items:center;border-bottom:1px solid var(--line)}
.bar input[type=search]{flex:1 1 220px;min-width:0}
.bar input,.bar select{font:inherit;font-size:14px;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:6px 8px}
.bar label{font-size:13px;color:var(--muted);display:inline-flex;gap:6px;align-items:center}
.count{font-size:13px;color:var(--muted);font-family:var(--mono)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:12px 14px}
.card h2{font-size:16px;margin:0 0 4px;font-weight:600;cursor:pointer}
.meta{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:12px;color:var(--muted);font-family:var(--mono)}
.meta a{color:var(--accent)}
.snip{margin:8px 0 0;color:var(--muted);font-size:14px}
.full{margin:10px 0 0;white-space:pre-wrap;overflow-wrap:anywhere}
.toggle{font:inherit;font-size:13px;color:var(--accent);background:none;border:0;padding:0;cursor:pointer;margin-top:6px}
mark{background:var(--mark);color:inherit;border-radius:2px}
.more{font:inherit;padding:8px 16px;border-radius:6px;border:1px solid var(--line);background:var(--surface);color:var(--ink);cursor:pointer;justify-self:center}
.empty{color:var(--muted)}
</style></head><body>
<div class="wrap">
<header><h1>__TITLE__</h1>
<p class="sub">只读：在这里阅读不会改动任何数据。点标题或"展开全文"看全文；用搜索框找词。Read-only view.</p></header>
<div class="bar">
 <input type="search" id="q" placeholder="搜索标题或正文 / search titles and text">
 <select id="yr"><option value="">全部年份 all years</option>__YEARS__</select>
 <select id="rat"><option value="">全部评分 all stars</option><option value="5">5★</option><option value="4">4★</option><option value="3">3★</option><option value="2">2★</option><option value="1">1★</option><option value="0">未打分 unrated</option></select>
 <select id="sort"><option value="useful">按"有用"排序 most useful</option><option value="new">最新在前 newest</option><option value="old">最早在前 oldest</option><option value="long">最长在前 longest</option></select>
 <label><input type="checkbox" id="norp"> 排除转载/翻译 hide reposts</label>
 <span class="count" id="count"></span>
</div>
<main id="list"></main>
<button class="more" id="more" hidden>再显示 50 篇 / show 50 more</button>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
const ALL=JSON.parse(document.getElementById('data').textContent);
const $=id=>document.getElementById(id);
let shown=50, cur=[];
function stars(r){return r?('★'.repeat(r)+'☆'.repeat(5-r)):'未打分'}
function hl(el,text,q){el.textContent='';if(!q){el.textContent=text;return}
 let i=0;while(true){const j=text.indexOf(q,i);if(j<0){el.append(text.slice(i));break}
 el.append(text.slice(i,j));const m=document.createElement('mark');m.textContent=text.slice(j,j+q.length);el.append(m);i=j+q.length}}
function card(o,q){
 const c=document.createElement('article');c.className='card';
 const h=document.createElement('h2');hl(h,o.t||'（无标题）',q);
 const meta=document.createElement('div');meta.className='meta';
 for(const s of [o.d,stars(o.r),'有用 '+o.u,o.n+' 字',o.rp?'转载/翻译':'']){if(s){const sp=document.createElement('span');sp.textContent=s;meta.append(sp)}}
 if(o.url){const a=document.createElement('a');a.href=o.url;a.target='_blank';a.rel='noopener';a.textContent='豆瓣原文';meta.append(a)}
 const snip=document.createElement('p');snip.className='snip';
 let s=o.x;if(q){const j=s.indexOf(q);s=j>60?'…'+s.slice(j-60):s}
 hl(snip,s.slice(0,180)+(s.length>180?'…':''),q);
 const full=document.createElement('div');full.className='full';full.hidden=true;
 const b=document.createElement('button');b.className='toggle';b.type='button';b.textContent='展开全文';
 const toggle=()=>{if(full.hidden){hl(full,o.x,q);full.hidden=false;snip.hidden=true;b.textContent='收起'}else{full.hidden=true;snip.hidden=false;b.textContent='展开全文'}};
 b.onclick=toggle;h.onclick=toggle;
 c.append(h,meta,snip,full,b);return c}
function apply(){
 const q=$('q').value.trim(),yr=$('yr').value,rat=$('rat').value,norp=$('norp').checked,sort=$('sort').value;
 cur=ALL.filter(o=>(!yr||o.y===yr)&&(!rat||(rat==='0'?!o.r:String(o.r)===rat))&&(!norp||!o.rp)&&(!q||o.t.includes(q)||o.x.includes(q)));
 const key={useful:(a,b)=>b.u-a.u,new:(a,b)=>b.d.localeCompare(a.d),old:(a,b)=>a.d.localeCompare(b.d),long:(a,b)=>b.n-a.n}[sort];
 cur.sort(key);shown=50;render()}
function render(){
 const q=$('q').value.trim(),list=$('list');list.textContent='';
 $('count').textContent=cur.length+' 篇';
 if(!cur.length){list.innerHTML='<p class="empty">没有符合条件的长评。No matching reviews.</p>';$('more').hidden=true;return}
 const frag=document.createDocumentFragment();for(const o of cur.slice(0,shown))frag.append(card(o,q));list.append(frag);
 $('more').hidden=shown>=cur.length}
let t;$('q').addEventListener('input',()=>{clearTimeout(t);t=setTimeout(apply,250)});
for(const id of ['yr','rat','sort','norp'])$(id).addEventListener('change',apply);
$('more').onclick=()=>{shown+=50;render()};
apply();
</script></body></html>"""

with open(a.out, "w", encoding="utf-8") as f:
    f.write(page.replace("__TITLE__", title).replace("__YEARS__", year_opts).replace("__DATA__", data))
print(f"Saved {a.out}: {len(rows)} reviews. Double-click it to open in a browser.")
