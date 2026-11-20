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
from urllib.parse import urlsplit, urljoin
import reading_catalog as catalog
import xml.etree.ElementTree as ET

SITE = "https://kongfurabbitz.github.io"
REPOSITORY = "kongfurabbitZ/kongfurabbitZ.github.io"
BEGIN = "<!-- REPORT_INSIGHTS:START -->"
END = "<!-- REPORT_INSIGHTS:END -->"
FIELDS = {"schema_version", "slug", "source_id", "title", "description", "published", "updated", "tags", "lead", "sections", "questions", "references"}
PRIVATE = re.compile(r"(?:https?://(?:[^/\s]*\.)?(?:notion\.(?:so|site)|app\.notion\.com)/|notion-file-block:|(?:/Volumes/|/Users/|/private/tmp/|/home/)|(?:secret_|ntn_|ghp_|github_pat_)[A-Za-z0-9_]{12,}|Bearer\s+[A-Za-z0-9._-]+)", re.I)
# Editorial installations may maintain their own local exclusions outside the public site.
rules_path = Path(__file__).resolve().parents[1] / "config" / "publication_exclusions.txt"
if rules_path.is_file():
    terms = [line.strip() for line in rules_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if terms:
        PRIVATE = re.compile(PRIVATE.pattern + "|" + "|".join(re.escape(term) for term in terms), re.I)



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
    require(isinstance(article, dict) and FIELDS <= set(article) <= FIELDS | {"reading"}, "Unknown or missing public article fields")
    require(article["schema_version"] == 1, "Unsupported article schema")
    require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", article["slug"]) is not None and len(article["slug"]) < 100, "Invalid slug")
    require(re.fullmatch(r"[a-f0-9]{64}", article["source_id"]) is not None, "Invalid source identity SHA-256")
    require(article["slug"] not in {"tags", "timeline"}, "Reserved catalog path")
    if "reading" in article:
        reading = article["reading"]
        require(isinstance(reading, dict) and set(reading) == {"day", "key", "identity", "revision"}, "Invalid paper metadata")
        require(date.fromisoformat(reading["day"]).isoformat() == reading["day"], "Invalid reading date")
        require(re.fullmatch(r"[a-f0-9]{64}", reading["key"]) is not None, "Invalid reading record key")
        require(re.fullmatch(r"[a-f0-9]{64}", reading["revision"]) is not None, "Invalid source revision")
        require(reading["identity"] in {"pdf", "bibliography"}, "Invalid source identity type")
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


CSS = """/* Extend the existing Strata theme; homepage remains the visual source. */
:root{--insight-accent:#49bf9d;--insight-ink:#787878;--insight-muted:#999;--insight-line:#efefef}
.insights-page .skip-link{position:absolute;left:1.5em;top:-5em;background:#fff;padding:.5em 1em;z-index:10}.insights-page .skip-link:focus{top:1em}
.insights-page #header .profile-name{color:rgba(255,255,255,.5);font-size:1.35em;line-height:1.75em;margin:0}
.insights-page .site-nav{display:flex;flex-wrap:wrap;gap:.75em 1.75em;font-size:.85em;margin:0 0 3em}.insights-page .site-nav a{color:var(--insight-muted)}.insights-page .site-nav a[aria-current=page]{color:var(--insight-ink);border-bottom:2px solid var(--insight-accent)}
.insights-page #main>#content{margin:0;padding:0;border:0}.insights-page #content{min-width:0}.insights-page h1{font-size:2em;line-height:1.5;margin:0 0 .65em;font-weight:400}.insights-page .intro{font-size:1.05em;line-height:1.9;color:#888;max-width:46em}
.insights-page .eyebrow,.report-insights .eyebrow{font-size:.75em;letter-spacing:.16em;color:var(--insight-muted);margin:0 0 1em}.insights-page .meta,.report-insights .meta{display:flex;flex-wrap:wrap;gap:.4em 1.25em;font-size:.8em;color:var(--insight-muted);line-height:1.8}
.insights-page .tag,.report-insights .tag{display:inline-block;font-size:.75em;line-height:1.75;color:var(--insight-muted);margin:0 .9em .3em 0}.insights-page .article-tags{margin-top:.75em}
.insights-page .insight-grid,.report-insights .insight-grid{display:grid;grid-template-columns:minmax(0,1fr);gap:2em;margin:2em 0}.insights-page .insight-card,.report-insights .insight-card{padding:0 0 2em;border:0;border-bottom:1px solid var(--insight-line);border-radius:0;background:transparent;min-width:0}.insights-page .insight-card:last-child,.report-insights .insight-card:last-child{padding-bottom:0;border-bottom:0}
.insights-page .insight-card h2,.report-insights .insight-card h3{font-size:1.35em;line-height:1.6;font-weight:400;margin:.65em 0}.insights-page .insight-card h2 a,.report-insights .insight-card h3 a{color:var(--insight-ink);border:0}.insights-page .insight-card p,.report-insights .insight-card p{font-size:.95em;line-height:1.9;margin:0 0 1em;color:#888}.insights-page .read-link,.report-insights .read-link{display:inline-block;font-size:.85em;margin-top:1em}.insights-page .insight-card[hidden]{display:none}
.insights-page .search-label{font-size:.85em;margin:2em 0 1em}.insights-page .insights-search{display:block;width:100%;max-width:30em;margin-top:.65em;padding:.6em .85em;border:1px solid #e5e5e5;border-radius:.35em;background:#f7f7f7;font:inherit;color:var(--insight-ink)}.insights-page .insights-search:focus{outline:2px solid var(--insight-accent);outline-offset:2px}
.insights-page .article-layout{margin-top:2em}.insights-page .article-body{min-width:0;color:var(--insight-ink);line-height:1.95;overflow-wrap:break-word}.insights-page .article-body .lead{font-size:1.1em;line-height:1.9;background:#f7f7f7;border-left:2px solid var(--insight-accent);border-radius:0 .35em .35em 0;padding:1em 1.3em;margin:0 0 2.5em}.insights-page .article-body section{margin:0 0 2.75em}.insights-page .article-body h2{font-size:1.35em;line-height:1.6;font-weight:400;margin:0 0 1em}.insights-page .article-body p{margin:0 0 1.5em}.insights-page .article-body li{margin-bottom:.75em}
.insights-page .article-aside{font-size:.8em;border-top:1px solid var(--insight-line);border-bottom:1px solid var(--insight-line);padding:1em 0;margin:0 0 2.5em;color:var(--insight-muted)}.insights-page .article-aside summary{cursor:pointer;color:var(--insight-ink)}.insights-page .article-aside nav{display:flex;flex-wrap:wrap;gap:.75em 1.5em;margin-top:1em}.insights-page .article-aside a{color:var(--insight-muted)}
.insights-page .table-scroll{overflow-x:auto;max-width:100%;margin:1.5em 0;border:1px solid var(--insight-line);border-radius:.35em}.insights-page .table-scroll table{margin:0;font-size:.9em}.insights-page .table-scroll th,.insights-page .table-scroll td{min-width:9em;padding:.9em 1em;vertical-align:top;line-height:1.85}.insights-page .table-scroll th{font-weight:400;background:#f7f7f7}.insights-page .table-scroll tr:last-child td{border-bottom:0}
.insights-page .references{font-size:.85em;border-top:1px solid var(--insight-line);padding-top:2em}.insights-page .references li{overflow-wrap:anywhere}.insights-page .reading-note{font-size:.8em;line-height:1.9;border-top:2px solid var(--insight-line);margin-top:3em;padding-top:2em;color:var(--insight-muted)}.insights-page a:focus-visible,.insights-page summary:focus-visible,.report-insights a:focus-visible{outline:2px solid var(--insight-accent);outline-offset:4px}
@media screen and (max-width:736px){.insights-page .site-nav{margin-bottom:2em;gap:.75em 1.25em}.insights-page h1{font-size:1.5em}.insights-page .article-body h2,.insights-page .insight-card h2,.report-insights .insight-card h3{font-size:1.2em}.insights-page .article-body .lead{font-size:1em;padding:1em}.insights-page .reading-note{margin-bottom:2em}}
@media screen and (min-width:981px) and (max-width:1280px){.insights-page #header .profile-name{font-size:1.25em}.insights-page #header .profile-name br{display:none}}@media screen and (min-width:737px) and (max-width:980px){.insights-page #header .profile-name{font-size:1.75em}}@media screen and (max-width:480px){.insights-page #header .profile-name br{display:none}}
@media print{.insights-page #header,.insights-page #footer,.insights-page .site-nav,.insights-page .article-aside,.insights-page .skip-link{display:none}.insights-page #main{margin:0;padding:0;width:100%;max-width:none}.insights-page .table-scroll{overflow:visible}}
"""


def shared_chrome(home):
    """Reuse the actual homepage identity; resolve its links from nested URLs."""
    def fragment(tag, element_id):
        found = re.search(r'<'+tag+r'\b[^>]*\bid="'+element_id+r'"[^>]*>.*?</'+tag+r'>', home, re.S)
        if not found:
            return ""
        def root_link(match):
            attr, quote, value = match.groups()
            rooted = value if urlsplit(value).scheme or value.startswith("//") else urljoin("/", value)
            return attr + "=" + quote + rooted + quote
        return re.sub(r'(href|src)=([\'"])(.*?)\2', root_link, found.group())
    profile = fragment("header", "header")
    # The page title owns h1; retain the profile's appearance without a second h1.
    profile = profile.replace("<h1>", '<p class="profile-name">').replace("</h1>", "</p>")
    footer = fragment("footer", "footer")
    footer = re.sub(r'<ul class="icons">.*?</ul>', '<ul class="icons"><li><a href="/#three">联系博文</a></li></ul>', footer, flags=re.S)
    return profile, footer


def shell(title, description, path, body, article_hash="", chrome=None):
    stamp = f'<meta name="insight-content-sha256" content="{article_hash}">' if article_hash else ""
    profile, footer = chrome or ("", "")
    links = [("/", "个人主页"), ("/insights/", "全部文章"), ("/insights/timeline/", "研读甘特图"), ("/insights/tags/", "标签目录"), ("/insights/feed.xml", "RSS 订阅")]
    navigation = "".join(f'<a href="{href}"'+(' aria-current="page"' if path == href else '')+f'>{label}</a>' for href, label in links)
    scripts = "".join(f'<script src="/assets/js/{name}.js"></script>' for name in ("jquery.min", "jquery.poptrox.min", "browser.min", "breakpoints.min", "util", "main"))
    return f'''<!doctype html>
<!-- Strata by HTML5 UP | html5up.net | CC BY 3.0 (html5up.net/license) -->
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} · 兔子的蓝天</title><meta name="description" content="{escape(description, quote=True)}">
<link rel="canonical" href="{SITE}{path}"><meta property="og:type" content="article"><meta property="og:title" content="{escape(title, quote=True)}"><meta property="og:description" content="{escape(description, quote=True)}"><meta property="og:url" content="{SITE}{path}">
{stamp}<link rel="stylesheet" href="/assets/css/main.css"><link rel="stylesheet" href="/assets/css/insights.css"><link rel="stylesheet" href="/assets/css/reading-catalog.css"><script defer src="/assets/js/reading-catalog.js"></script><link rel="alternate" type="application/rss+xml" title="报告洞察" href="/insights/feed.xml"></head>
<body class="insights-page"><a class="skip-link" href="#content">跳到正文</a>{profile}
<main id="main"><nav class="site-nav" aria-label="主导航">{navigation}</nav><section id="content">{body}</section><p class="reading-note">以研究理解变化，以实践检验判断。<br>文章为个人阅读与分析，原报告及所引研究的权利归各自作者所有。</p></main>{footer}{scripts}</body></html>
'''


def tags(article):
    return catalog.tag_links(article)


def card(article, level=2):
    kind = "论文研读" if "reading" in article else "报告洞察"
    day = article.get("reading", {}).get("day", article["published"])
    event = "研读入库" if "reading" in article else "发布"
    url = catalog.article_url(article)
    return f'''<article class="insight-card" data-item {catalog.attributes(article)}><div class="meta"><span>{kind}</span><time datetime="{day}">{event} {day}</time></div><h{level}><a href="{url}">{escape(article['title'])}</a></h{level}><p>{escape(article['description'])}</p><div>{tags(article)}</div></article>'''


def render_article(article, chrome=None):
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
    reading_stamp = ""
    if "reading" in article:
        day = article["reading"]["day"]
        reading_stamp = f'<time datetime="{day}">研读入库 {day}</time>'
    body = f'''<h1>{escape(article['title'])}</h1><p class="intro">{escape(article['description'])}</p><div class="meta"><span>博文</span>{reading_stamp}<time datetime="{article['published']}">发布于 {article['published']}</time><time datetime="{article['updated']}">更新于 {article['updated']}</time></div><div class="article-tags">{tags(article)}</div><div class="article-layout"><details class="article-aside"><summary>本文目录</summary><nav aria-label="文章目录">{''.join(toc)}<a href="#questions">值得继续追问</a><a href="#references">来源与阅读说明</a></nav></details><article class="article-body"><p class="lead">{escape(article['lead'])}</p>{''.join(sections)}<section id="questions"><h2>值得继续追问</h2><ol>{questions}</ol></section><section class="references" id="references"><h2>来源与阅读说明</h2><ol>{''.join(refs)}</ol><p>本文为独立研读与分析，出处见上。</p></section><p><a href="/insights/">← 返回全部文章</a></p></article></div>'''
    return shell(article["title"], article["description"], f"/insights/{article['slug']}/", body, digest(article), chrome=chrome)


def render_archive(articles, chrome=None):
    body = f'''<div data-catalog="archive"><h1>全部文章</h1><p class="intro">从论文的方法与实验，到行业报告的判断与证据。</p>{catalog.filters(articles)}<p data-count class="catalog-count" role="status">{len(articles)} 篇文章</p><div class="insight-grid">{''.join(card(a) for a in articles)}</div><p data-empty hidden>没有匹配的文章，试试其他标签或关键词。</p></div>'''
    return shell("全部文章", "按主题与方法浏览博文的论文研读和报告洞察。", "/insights/", body, chrome=chrome)


def render_feed(articles):
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    for key, value in (("title", "兔子的蓝天 · 论文与报告"), ("link", SITE + "/insights/"), ("description", "研究、思考与实践"), ("language", "zh-CN")):
        ET.SubElement(channel, key).text = value
    for article in articles:
        item = ET.SubElement(channel, "item")
        for key, value in (("title", article["title"]), ("link", SITE + f"/insights/{article['slug']}/"), ("guid", SITE + f"/insights/{article['slug']}/"), ("description", article["description"]), ("pubDate", date.fromisoformat(article["published"]).strftime("%a, %d %b %Y 00:00:00 +0800"))):
            ET.SubElement(item, key).text = value
    return ET.tostring(rss, encoding="unicode", xml_declaration=True) + "\n"


def build(repo, incoming):
    result = build_many(repo, [incoming])
    return result | {"slug": incoming["slug"], "url": SITE + catalog.article_url(incoming),
                     "source_id": incoming["source_id"], "content_sha256": digest(incoming)}


def build_many(repo, incoming_articles):
    repo = Path(repo).resolve()
    require((repo / "index.html").is_file(), "Read the existing homepage before preparing a publication")
    chrome = shared_chrome((repo / "index.html").read_text(encoding="utf-8"))
    articles = {}
    for path in sorted((repo / "content/insights").glob("*.json")):
        article = validate(json.loads(path.read_text(encoding="utf-8")))
        require(path.stem == article["slug"], "Article path and slug differ")
        articles[article["slug"]] = article
    for incoming in incoming_articles:
        validate(incoming)
        slug = incoming["slug"]
        old = articles.get(slug)
        if old:
            require(old["source_id"] == incoming["source_id"], "Existing slug belongs to a different source")
            require(old["published"] == incoming["published"], "Keep the original publication date")
            require(old["updated"] <= incoming["updated"], "Do not overwrite a newer article")
            if "reading" in old:
                require(incoming.get("reading", {}).get("key") == old["reading"]["key"], "Reading identity changed")
        articles[slug] = incoming
    ordered = sorted(articles.values(), key=catalog.ordered_key, reverse=True)
    require(len({a["source_id"] for a in ordered}) == len(ordered), "This source already has a public URL; use the existing slug")
    keys = [a["reading"]["key"] for a in ordered if "reading" in a]
    require(len(set(keys)) == len(keys), "This paper already has a public URL")
    output = {"assets/css/insights.css": CSS, "insights/index.html": render_archive(ordered, chrome=chrome), "insights/feed.xml": render_feed(ordered)}
    output["insights/tags/index.html"] = shell("按标签浏览", "全站主题和方法标签", "/insights/tags/", catalog.tag_directory(ordered), chrome=chrome)
    output["insights/timeline/index.html"] = shell("论文研读甘特图", "按入库日期浏览论文研读", "/insights/timeline/", catalog.render_timeline(ordered), chrome=chrome)
    for asset in ("assets/css/reading-catalog.css", "assets/js/reading-catalog.js"):
        output[asset] = (Path(__file__).resolve().parents[1] / asset).read_text(encoding="utf-8")
    for article in ordered:
        output[f"content/insights/{article['slug']}.json"] = json.dumps(article, ensure_ascii=False, indent=2) + "\n"
        output[f"insights/{article['slug']}/index.html"] = render_article(article, chrome=chrome)
    index = [{key: a[key] for key in ("slug", "source_id", "title", "description", "published", "updated", "tags")} | ({"reading": a["reading"]} if "reading" in a else {}) | {"kind": "paper" if "reading" in a else "report", "url": SITE + f"/insights/{a['slug']}/", "content_sha256": digest(a)} for a in ordered]
    output["insights/index.json"] = json.dumps({"schema_version": 1, "articles": index}, ensure_ascii=False, indent=2) + "\n"
    home_path = repo / "index.html"
    home = home_path.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in home else "\n"
    original_home = home
    section = f'''{BEGIN}
<section id="report-insights" class="report-insights">{catalog.home_tools(ordered)}<h3>最近研读</h3><div class="insight-grid">{''.join(card(a, 3) for a in sorted((a for a in ordered if "reading" in a), key=lambda a: a["reading"]["day"], reverse=True)[:3])}</div><h3>最近报告</h3><div class="insight-grid">{''.join(card(a, 3) for a in [a for a in ordered if "reading" not in a][:3])}</div><a href="/insights/feed.xml">RSS 订阅</a></section>
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
    if 'href="/assets/css/reading-catalog.css"' not in home:
        home = home.replace("</head>", '<link rel="stylesheet" href="/assets/css/reading-catalog.css" />' + newline + "</head>", 1)
    home = home.replace("从报告出发，", "从论文与报告出发，").replace("阅读报告洞察</a>", "浏览全部文章</a>")
    output["insights/home-fragment.html"] = section.split(BEGIN, 1)[1].split(END, 1)[0].strip() + "\n"
    # The original Strata page already loads main.js. Serve the library in its own
    # fragment so a research publication never republishes the personal contact block.
    existing_strata = 'src="assets/js/main.js"' in original_home and BEGIN in original_home
    output["index.html"] = original_home if existing_strata else home
    changed = []
    for name, content in output.items():
        path = (repo / name).resolve()
        require(path.is_relative_to(repo), "Output path escaped repository")
        if not path.exists() or path.read_bytes() != content.encode("utf-8"):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode("utf-8"))
            changed.append(name)
    return {"schema_version": 1, "repository": REPOSITORY, "branch": "master", "changed_paths": changed, "expected_paths": sorted(output), "article_count": len(ordered)}


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
