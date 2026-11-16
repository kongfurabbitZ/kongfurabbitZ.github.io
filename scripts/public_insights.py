#!/usr/bin/env python3
"""Build public report notes for Bowen's existing GitHub Pages site (stdlib only).

This file is also versioned as scripts/public_insights.py in the website repo.
It accepts an edited public article, never a whole Notion export.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
import argparse
from datetime import date
import hashlib
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

SITE = "https://kongfurabbitz.github.io"
REPOSITORY = "kongfurabbitZ/kongfurabbitZ.github.io"
BEGIN = "<!-- REPORT_INSIGHTS:START -->"
END = "<!-- REPORT_INSIGHTS:END -->"
FIELDS = {"schema_version", "slug", "source_id", "title", "description", "published", "updated", "tags", "lead", "sections", "questions", "references"}
PRIVATE = re.compile(r"(?:https?://(?:[^/\s]*\.)?(?:notion\.(?:so|site)|app\.notion\.com)/|notion-file-block:|(?:/Volumes/|/Users/|/private/tmp/|/home/)|(?:secret_|ntn_|ghp_|github_pat_)[A-Za-z0-9_]{12,}|Bearer\s+[A-Za-z0-9._-]+|产业数智化中心|长城汽车股份有限公司|个人行动明细|为什么适合我|最小下一步|REPORT_WORKSPACE|NOTION_API_TOKEN)", re.I)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def text(value, label, minimum=1, maximum=20000):
    require(isinstance(value, str) and minimum <= len(value.strip()) <= maximum, label + " must be nonempty text within bounds")
    return value


def public_url(value):
    parts = urlsplit(value)
    require(parts.scheme == "https" and parts.hostname and not parts.username and not parts.password, "Reference must be an HTTPS URL")
    require(parts.hostname.lower() not in {"localhost", "127.0.0.1", "::1"} and not parts.hostname.lower().endswith((".local", ".internal")), "Reference must be public")
    require(not PRIVATE.search(value), "Private reference is not allowed")


def validate(article):
    require(isinstance(article, dict) and set(article) == FIELDS, "Unknown or missing public article fields")
    require(article["schema_version"] == 1, "Unsupported article schema")
    require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", article["slug"]) is not None and len(article["slug"]) < 100, "Invalid slug")
    require(re.fullmatch(r"[a-f0-9]{64}", article["source_id"]) is not None, "source_id must be source PDF SHA-256")
    for key, maximum in (("title", 100), ("description", 240), ("lead", 1000)):
        text(article[key], key, maximum=maximum)
    for key in ("published", "updated"):
        require(date.fromisoformat(article[key]).isoformat() == article[key], "Invalid date")
    require(article["published"] <= article["updated"], "updated predates published")
    require(isinstance(article["tags"], list) and 1 <= len(article["tags"]) <= 8, "Use 1-8 tags")
    for tag in article["tags"]:
        text(tag, "tag", maximum=30)
    require(isinstance(article["sections"], list) and 1 <= len(article["sections"]) <= 20, "Use 1-20 sections")
    for section in article["sections"]:
        require(isinstance(section, dict) and set(section) <= {"heading", "paragraphs", "bullets", "table"} and "heading" in section, "Invalid section")
        text(section["heading"], "section heading", maximum=100)
        require(any(section.get(key) for key in ("paragraphs", "bullets", "table")), "Empty section")
        for key in ("paragraphs", "bullets"):
            if key in section:
                require(isinstance(section[key], list), key + " must be an array")
                for item in section[key]:
                    text(item, key)
        if "table" in section:
            table = section["table"]
            require(isinstance(table, dict) and set(table) == {"headers", "rows"}, "Invalid table")
            require(isinstance(table["headers"], list) and 2 <= len(table["headers"]) <= 5, "Use 2-5 table columns")
            require(isinstance(table["rows"], list) and table["rows"], "Empty table")
            for row in [table["headers"], *table["rows"]]:
                require(isinstance(row, list) and len(row) == len(table["headers"]), "Ragged table")
                for cell in row:
                    text(cell, "table cell")
    require(isinstance(article["questions"], list) and 3 <= len(article["questions"]) <= 5, "Use 3-5 discussion questions")
    for question in article["questions"]:
        text(question, "question")
    require(isinstance(article["references"], list) and article["references"], "At least one source is required")
    for ref in article["references"]:
        require(isinstance(ref, dict) and set(ref) <= {"citation", "url"} and "citation" in ref, "Invalid reference")
        text(ref["citation"], "citation")
        if ref.get("url"):
            public_url(ref["url"])
    require(not PRIVATE.search(canonical(article)), "Public draft contains a private URL, path, credential, or internal action context; edit it before publishing")
    return article


CSS = """/* Public report notes. System fonts, no external runtime dependencies. */
:root{--ink:#263e39;--muted:#5d7069;--accent:#235e4e;--line:#dbe4dd;--paper:#f7f9f5;--white:#fff;--radius:16px}
*{box-sizing:border-box}html{scroll-behavior:smooth}body.insights-page{margin:0;background:var(--paper);color:var(--ink);font:17px/1.9 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}a{color:var(--accent);text-underline-offset:4px}a:hover{text-decoration-thickness:2px}a:focus-visible,input:focus-visible{outline:3px solid #b17a23;outline-offset:5px}.skip-link{position:absolute;left:16px;top:-80px;background:white;padding:8px}.skip-link:focus{top:16px}.site-nav{max-width:1120px;margin:auto;padding:25px 32px;display:flex;gap:22px;align-items:center;flex-wrap:wrap}.site-nav .brand{font-weight:750;margin-right:auto;text-decoration:none;letter-spacing:.06em}.site-nav a{font-size:15px}.insights-main{max-width:1060px;margin:20px auto 80px;padding:0 32px}.eyebrow{font-size:12px;letter-spacing:.17em;font-weight:700;color:var(--accent);text-transform:uppercase}.insights-page h1{font-size:clamp(29px,4.2vw,46px);line-height:1.35;letter-spacing:-.025em;margin:14px 0 20px;max-width:850px}.intro{font-size:19px;color:var(--muted);max-width:760px}.meta{font-size:13px;color:var(--muted);display:flex;gap:10px 18px;flex-wrap:wrap}.tag{font-size:12px;padding:3px 10px;border:1px solid var(--line);border-radius:99px;display:inline-block;margin:0 7px 6px 0}.article-layout{display:grid;grid-template-columns:minmax(0,750px) 190px;gap:50px;margin-top:36px}.article-body{min-width:0}.article-body .lead{border-left:3px solid var(--accent);padding:18px 24px;background:#eaf0e8;border-radius:0 10px 10px 0;font-size:20px;line-height:1.8;margin:0 0 36px}.article-body section{margin:0 0 36px}.article-body h2{font-size:24px;line-height:1.5;margin:0 0 16px;color:#1d4438}.article-body p{margin:0 0 20px}.article-body ul,.article-body ol{padding-left:1.5em}.article-body li{padding-left:.2em;margin-bottom:10px}.table-scroll{overflow-x:auto;margin:22px 0;border:1px solid var(--line);border-radius:10px}table{width:100%;border-collapse:collapse;font-size:15px;background:white}th,td{padding:14px 16px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line);min-width:140px}th{background:#eaf0e8;font-weight:650}tr:last-child td{border-bottom:0}.article-aside{font-size:13px;align-self:start;position:sticky;top:24px;padding-left:18px;border-left:1px solid var(--line)}.article-aside a{display:block;margin:0 0 12px;text-decoration:none;color:var(--muted)}.references{font-size:14px;color:var(--muted);border-top:1px solid var(--line);padding-top:24px}.references li{overflow-wrap:anywhere}.insight-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px;margin-top:30px}.insight-card{padding:26px;border:1px solid var(--line);border-radius:var(--radius);background:white;display:flex;flex-direction:column}.insight-card h2,.insight-card h3{font-size:23px;line-height:1.5;margin:12px 0 14px}.insight-card h2 a,.insight-card h3 a{text-decoration:none;color:var(--ink)}.insight-card p{color:var(--muted);font-size:15px;margin:0 0 20px}.insight-card .read-link{margin-top:auto;font-size:14px;font-weight:600}.insight-card[hidden]{display:none}.search-label{display:block;font-size:14px;margin-top:26px}.insights-search{display:block;margin-top:8px;max-width:480px;width:100%;font:inherit;border:1px solid var(--line);border-radius:9px;padding:10px 14px;background:white;color:var(--ink)}.site-footer{max-width:1060px;margin:0 auto;padding:28px 32px;border-top:1px solid var(--line);font-size:13px;color:var(--muted)}.report-insights{color:#344c43}.report-insights .insight-card h3{font-size:1.2em}.report-insights .insight-card p{line-height:1.8}.report-insights .eyebrow{margin-bottom:8px}.report-insights .insight-grid{margin-bottom:24px}.report-insights .meta{color:#5d7069}
@media(max-width:800px){.article-layout{grid-template-columns:1fr;gap:0}.article-aside{display:none}.insight-grid{grid-template-columns:1fr}.insights-main{padding:0 22px;margin-top:12px}.site-nav{padding:22px}.article-body .lead{padding:18px;font-size:18px}.article-body h2{font-size:22px}.site-footer{padding:26px 22px}.insight-card{padding:22px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{.site-nav,.article-aside,.site-footer,.skip-link{display:none}.insights-page{background:white}.article-layout{display:block}.insights-main{max-width:none;padding:0}.table-scroll{overflow:visible}}
"""


def shell(title, description, path, body, article_hash=""):
    stamp = f'<meta name="insight-content-sha256" content="{article_hash}">' if article_hash else ""
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} · 兔子的蓝天</title><meta name="description" content="{escape(description, quote=True)}">
<link rel="canonical" href="{SITE}{path}"><meta property="og:type" content="article"><meta property="og:title" content="{escape(title, quote=True)}"><meta property="og:description" content="{escape(description, quote=True)}"><meta property="og:url" content="{SITE}{path}">
{stamp}<link rel="stylesheet" href="/assets/css/insights.css"><link rel="alternate" type="application/rss+xml" title="报告洞察" href="/insights/feed.xml"></head>
<body class="insights-page"><a class="skip-link" href="#content">跳到正文</a><nav class="site-nav" aria-label="主导航"><a class="brand" href="/">兔子的蓝天</a><a href="/insights/">报告洞察</a><a href="/insights/feed.xml">RSS 订阅</a><a href="https://github.com/{REPOSITORY}">GitHub</a></nav>
<main class="insights-main" id="content">{body}</main><footer class="site-footer">博文 · 以研究理解变化，以实践检验判断。<br>文章为个人阅读与分析，原报告及所引研究的权利归各自作者所有。</footer></body></html>
'''


def tags(article):
    return "".join(f'<span class="tag">{escape(tag)}</span>' for tag in article["tags"])


def card(article, level=2):
    return f'''<article class="insight-card" data-search="{escape(article['title'] + ' ' + article['description'] + ' ' + ' '.join(article['tags']), quote=True)}"><div class="meta"><time datetime="{article['published']}">{article['published']}</time><span>报告解读</span></div><h{level}><a href="/insights/{article['slug']}/">{escape(article['title'])}</a></h{level}><p>{escape(article['description'])}</p><div>{tags(article)}</div><a class="read-link" href="/insights/{article['slug']}/">阅读全文 →</a></article>'''


def render_article(article):
    sections = []
    toc = []
    for index, section in enumerate(article["sections"], 1):
        heading = escape(section["heading"])
        toc.append(f'<a href="#section-{index}">{heading}</a>')
        blocks = [f'<h2>{heading}</h2>']
        blocks += [f'<p>{escape(p)}</p>' for p in section.get("paragraphs", [])]
        if section.get("bullets"):
            blocks.append("<ul>" + "".join(f'<li>{escape(p)}</li>' for p in section["bullets"]) + "</ul>")
        if section.get("table"):
            table = section["table"]
            headers = "".join(f'<th scope="col">{escape(t)}</th>' for t in table["headers"])
            rows = "".join("<tr>" + "".join(f'<td>{escape(c)}</td>' for c in row) + "</tr>" for row in table["rows"])
            blocks.append(f'<div class="table-scroll" role="region" aria-label="{heading}" tabindex="0"><table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table></div>')
        sections.append(f'<section id="section-{index}">' + "\n".join(blocks) + '</section>')
    refs = []
    for ref in article["references"]:
        label = escape(ref["citation"])
        refs.append(f'<li><a href="{escape(ref["url"], quote=True)}" rel="noreferrer">{label}</a></li>' if ref.get("url") else f'<li>{label}</li>')
    questions = "".join(f'<li>{escape(q)}</li>' for q in article["questions"])
    body = f'''<p class="eyebrow">研究 · 思考 · 实践</p><h1>{escape(article['title'])}</h1><p class="intro">{escape(article['description'])}</p><div class="meta"><span>博文</span><time datetime="{article['published']}">发布于 {article['published']}</time><time datetime="{article['updated']}">更新于 {article['updated']}</time></div><div style="margin-top:14px">{tags(article)}</div><div class="article-layout"><article class="article-body"><p class="lead">{escape(article['lead'])}</p>{''.join(sections)}<section id="questions"><h2>值得继续追问</h2><ol>{questions}</ol></section><section class="references" id="references"><h2>来源与阅读说明</h2><ol>{''.join(refs)}</ol><p>本文是基于原报告的独立整理与分析。文中建议需结合具体情境验证；研究结论与作者推断的边界在正文中分别说明。</p></section><p><a href="/insights/">← 返回全部报告洞察</a></p></article><aside class="article-aside" aria-label="文章目录"><p>本文目录</p>{''.join(toc)}<a href="#questions">值得继续追问</a><a href="#references">来源与阅读说明</a></aside></div>'''
    return shell(article["title"], article["description"], f"/insights/{article['slug']}/", body, digest(article))


def render_archive(articles):
    search = '''<label class="search-label" for="insights-search">搜索标题、主题或关键词<input class="insights-search" id="insights-search" type="search" placeholder="例如：AI、组织、生产率" autocomplete="off"></label>'''
    script = '''<script>const search=document.querySelector('#insights-search');const cards=[...document.querySelectorAll('.insight-card')];search.addEventListener('input',()=>{const terms=search.value.trim().toLocaleLowerCase().split(/\\s+/).filter(Boolean);let count=0;cards.forEach(card=>{card.hidden=!terms.every(term=>card.dataset.search.toLocaleLowerCase().includes(term));if(!card.hidden)count++;});document.querySelector('#search-count').textContent=count+' 篇文章';});</script>'''
    body = f'''<p class="eyebrow">REPORT INSIGHTS</p><h1>报告洞察</h1><p class="intro">把长报告里的重要判断、证据边界和实践启发，整理成可以读懂、讨论和使用的文章。关注 AI、组织与数字化，也关注技术如何走进真实生活。</p>{search}<p class="meta" id="search-count" role="status" aria-live="polite">{len(articles)} 篇文章</p><div class="insight-grid">{''.join(card(a) for a in articles)}</div>{script}'''
    return shell("报告洞察", "博文的报告解读：AI、组织、数字化与实践思考。", "/insights/", body)


def render_feed(articles):
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    for key, value in (("title", "兔子的蓝天 · 报告洞察"), ("link", SITE + "/insights/"), ("description", "研究、思考与实践"), ("language", "zh-CN")):
        ET.SubElement(channel, key).text = value
    for article in articles:
        item = ET.SubElement(channel, "item")
        for key, value in (("title", article["title"]), ("link", SITE + f"/insights/{article['slug']}/"), ("guid", SITE + f"/insights/{article['slug']}/"), ("description", article["description"]), ("pubDate", date.fromisoformat(article["published"]).strftime("%a, %d %b %Y 00:00:00 +0800"))):
            ET.SubElement(item, key).text = value
    return ET.tostring(rss, encoding="unicode", xml_declaration=True) + "\n"


def build(repo, incoming):
    repo = Path(repo).resolve()
    require((repo / "index.html").is_file(), "Read the existing homepage before preparing a publication")
    incoming = validate(incoming)
    articles = {}
    for path in sorted((repo / "content/insights").glob("*.json")):
        article = validate(json.loads(path.read_text(encoding="utf-8")))
        require(path.stem == article["slug"], "Article path and slug differ")
        articles[article["slug"]] = article
    for slug, article in articles.items():
        require(article["source_id"] != incoming["source_id"] or slug == incoming["slug"], "This report already has a public URL; update that slug instead")
    if incoming["slug"] in articles:
        old = articles[incoming["slug"]]
        require(old["source_id"] == incoming["source_id"], "Existing slug belongs to a different report")
        require(old["published"] == incoming["published"], "Keep the original publication date on update")
        require(old["updated"] <= incoming["updated"], "Do not overwrite a newer article")
    articles[incoming["slug"]] = incoming
    ordered = sorted(articles.values(), key=lambda a: (a["published"], a["slug"]), reverse=True)
    output = {"assets/css/insights.css": CSS, "insights/index.html": render_archive(ordered), "insights/feed.xml": render_feed(ordered)}
    for article in ordered:
        output[f"content/insights/{article['slug']}.json"] = json.dumps(article, ensure_ascii=False, indent=2) + "\n"
        output[f"insights/{article['slug']}/index.html"] = render_article(article)
    index = [{key: a[key] for key in ("slug", "source_id", "title", "description", "published", "updated", "tags")} | {"url": SITE + f"/insights/{a['slug']}/", "content_sha256": digest(a)} for a in ordered]
    output["insights/index.json"] = json.dumps({"schema_version": 1, "articles": index}, ensure_ascii=False, indent=2) + "\n"
    home_path = repo / "index.html"
    home = home_path.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in home else "\n"
    section = f'''{BEGIN}
<section id="report-insights" class="report-insights"><p class="eyebrow">研究 · 思考 · 实践</p><h2>报告洞察</h2><p>从长报告中提炼重要判断，把证据、边界与实践启发分享给更多读者。</p><div class="insight-grid">{''.join(card(a, 3) for a in ordered[:3])}</div><ul class="actions"><li><a class="button" href="/insights/">阅读全部报告洞察</a></li><li><a href="/insights/feed.xml">RSS 订阅</a></li></ul></section>
{END}'''.replace("\n", newline)
    require(home.count(BEGIN) == home.count(END) and home.count(BEGIN) <= 1, "Homepage publication markers are malformed")
    if BEGIN in home:
        start, end = home.index(BEGIN), home.index(END) + len(END)
        home = home[:start] + section + home[end:]
    else:
        anchor = "<!-- Two -->"
        require(home.count(anchor) == 1, "Cannot safely locate homepage insertion point")
        home = home.replace(anchor, section + newline + newline + "\t\t\t\t" + anchor)
    if 'href="/assets/css/insights.css"' not in home:
        home = home.replace("</head>", '<link rel="stylesheet" href="/assets/css/insights.css" />' + newline + "\t</head>", 1)
    output["index.html"] = home
    changed = []
    for name, content in output.items():
        path = (repo / name).resolve()
        require(path.is_relative_to(repo), "Output path escaped repository")
        if not path.exists() or path.read_bytes() != content.encode("utf-8"):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode("utf-8"))
            changed.append(name)
    return {"schema_version": 1, "repository": REPOSITORY, "branch": "master", "slug": incoming["slug"], "url": SITE + f"/insights/{incoming['slug']}/", "source_id": incoming["source_id"], "content_sha256": digest(incoming), "changed_paths": changed, "expected_paths": sorted(output), "article_count": len(ordered)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--article", required=True)
    parser.add_argument("--result", required=True, help="Private workspace path; never commit publication evidence")
    args = parser.parse_args()
    result = build(Path(args.repo), json.loads(Path(args.article).read_text(encoding="utf-8")))
    Path(args.result).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
