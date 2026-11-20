"""Public navigation and reading timeline, derived entirely from the published articles."""
from collections import Counter
from html import escape
import json
from urllib.parse import urlencode


def article_url(article):
    return "/insights/" + article["slug"] + "/"


def tag_url(tag):
    return "/insights/?" + urlencode({"tag": tag})


def display_tag(tag):
    return tag.removeprefix("主题·").removeprefix("方法·")


def tag_links(article):
    return "".join(f'<a class="tag" href="{escape(tag_url(tag))}">{escape(display_tag(tag))}</a>' for tag in article["tags"])


def groups(articles):
    counts = Counter()
    representatives = {}
    for article in articles:
        counts.update({display_tag(tag) for tag in article["tags"]})
        for tag in article["tags"]:
            label = display_tag(tag)
            # A report may use the same name without the Notion topic/method prefix.
            if label not in representatives or (label == representatives[label] and tag != label):
                representatives[label] = tag
    groups = {"研究主题": [], "研究方法": [], "其他标签": []}
    for label, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])):
        tag = representatives[label]
        group = "研究主题" if tag.startswith("主题·") else "研究方法" if tag.startswith("方法·") else "其他标签"
        groups[group].append((tag, count))
    return {name: tags for name, tags in groups.items() if tags}


def select_tags(articles, field="tag"):
    options = ['<option value="">全部标签</option>']
    for group, tags in groups(articles).items():
        options.append(f'<optgroup label="{group}">')
        options.extend(f'<option value="{escape(tag, quote=True)}">{escape(display_tag(tag))}（{count}）</option>' for tag, count in tags)
        options.append('</optgroup>')
    return f'<label>标签<select name="{field}">' + "".join(options) + '</select></label>'


def tag_directory(articles):
    sections = []
    for group, tags in groups(articles).items():
        links = "".join(f'<a href="{escape(tag_url(tag))}">{escape(display_tag(tag))} <small>{n}</small></a>' for tag, n in tags)
        sections.append(f'<section class="tag-group"><h2>{group}</h2><div>{links}</div></section>')
    return '<h1>按标签浏览</h1><p class="intro">选择标签，阅读同一主题下的论文与报告。</p>' + "".join(sections)


def filters(articles):
    kind = '<label>内容类型<select name="kind"><option value="">全部内容</option><option value="paper">论文研读</option><option value="report">报告洞察</option></select></label>'
    return f'<form class="catalog-controls" data-filters>{kind}{select_tags(articles)}<label>关键词<input name="q" type="search" placeholder="搜索标题、方法或关键词"></label><button type="reset">清除筛选</button></form>'


def attributes(article):
    fields = {"kind": "paper" if "reading" in article else "report", "tags": json.dumps(article["tags"], ensure_ascii=False), "search": " ".join([article["title"], article["description"], *article["tags"]])}
    if "reading" in article:
        fields["day"] = article["reading"]["day"]
    return " ".join(f'data-{k}="{escape(v, quote=True)}"' for k, v in fields.items())


TIMELINE_VENDOR = "assets/vendor/vis-timeline-8.5.6"
TIMELINE_ASSETS = (
    "assets/css/reading-timeline.css", "assets/js/reading-timeline.js",
    *(TIMELINE_VENDOR + "/" + name for name in (
        "vis-timeline-graph2d.min.css", "vis-timeline-graph2d.min.js",
        "LICENSE.md", "LICENSE.MIT.txt", "LICENSE.Apache-2.0.txt")),
)


def render_timeline(articles, site):
    papers = sorted((a for a in articles if "reading" in a),
                    key=lambda a: (a["reading"]["day"], a["title"]), reverse=True)
    topics = set()
    rows = []
    for article in papers:
        day = article["reading"]["day"]
        topic = next((display_tag(t) for t in article["tags"] if t.startswith("主题·")), "其他研读")
        topics.add(topic)
        rows.append(f'<li class="paper-record" {attributes(article)} data-topic="{escape(topic, quote=True)}">'
                    f'<time datetime="{day}">{day.replace("-", ".")}</time><a href="{article_url(article)}">{escape(article["title"])}</a>'
                    f'<span class="record-topic">{escape(topic)}</span><span class="record-arrow" aria-hidden="true">↗</span></li>')
    months = sorted({a["reading"]["day"][:7] for a in papers}, reverse=True)
    options = "".join(f'<option value="{m}">{m[:4]} 年 {int(m[5:])} 月</option>' for m in months)
    scales = (("day", "日"), ("week", "周"), ("month", "月"), ("quarter", "季"), ("year", "年"), ("all", "全部"))
    buttons = "".join(f'<button type="button" data-scale="{value}" aria-pressed="false">{label}</button>' for value, label in scales)
    path = site + "/insights/timeline/"
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>论文研读时间轴 · 兔子的蓝天</title><meta name="description" content="按主题与周期浏览博文的论文研读，点击记录进入公开分析。">
<link rel="canonical" href="{path}"><meta property="og:title" content="论文研读时间轴 · 兔子的蓝天"><meta property="og:url" content="{path}">
<link rel="stylesheet" href="/{TIMELINE_VENDOR}/vis-timeline-graph2d.min.css"><link rel="stylesheet" href="/assets/css/reading-timeline.css">
<script defer src="/{TIMELINE_VENDOR}/vis-timeline-graph2d.min.js"></script><script defer src="/assets/js/reading-timeline.js"></script>
</head><body><a class="skip-link" href="#content">跳到时间轴</a>
<header class="masthead"><div class="wrap mast-row"><a class="brand" href="/"><img src="/images/avatar.jpg" width="32" height="32" alt="">兔子的蓝天</a>
<nav aria-label="主导航"><a href="/insights/">全部文章</a><a href="/insights/timeline/" aria-current="page">研读甘特图</a><a href="/insights/tags/">标签目录</a></nav></div></header>
<main id="content" class="wrap">
<header class="page-heading"><div><h1>论文研读时间轴</h1><p><strong>{len(papers)}</strong> 篇论文研读<span class="separator">/</span><strong>{len(topics)}</strong> 个研究主题<span class="separator">/</span>按北京时间记录入库日</p></div>
<section class="overview js-control" aria-label="每月研读篇数"><div class="overview-title"><span>月度研读分布</span><span data-overview-dates></span></div><div class="month-bars" data-overview></div></section></header>
<section class="map js-control" aria-label="可缩放的研读甘特图">
<div class="map-head"><div class="period-nav"><button class="direction" data-step="-1" aria-label="上一周期">‹</button><h2 data-period>研读日历</h2><button class="direction" data-step="1" aria-label="下一周期">›</button></div>
<div class="scale-switch" role="group" aria-label="时间尺度">{buttons}</div></div>
<form class="filters" data-map-filters role="search"><label class="search-field"><span>搜索论文</span><input type="search" name="q" placeholder="输入题名、方法或关键词"></label>
{select_tags(papers)}<label>跳到月份<select name="jump"><option value="">选择有研读的月份</option>{options}</select></label>
<button class="latest" type="button" data-latest>最近研读</button></form>
<div class="plot" tabindex="0" role="region" aria-label="研读时间轴，方向键平移，加减键缩放" aria-describedby="plot-help" data-plot></div>
<div class="chart-foot"><span id="plot-help"><i aria-hidden="true"></i>拖动平移 · 双指或 Ctrl＋滚轮缩放</span><div class="zoom-tools"><button data-zoom="-1" aria-label="缩小">−</button><button data-zoom="1" aria-label="放大">＋</button></div></div>
</section>
<section class="reading-list" aria-labelledby="list-heading"><header class="list-head"><h2 id="list-heading">论文目录</h2><span data-count role="status">{len(papers)} 篇</span></header>
<p class="empty" data-empty hidden></p><ol class="paper-list">{''.join(rows)}</ol></section>
<dialog class="paper-dialog" aria-labelledby="cluster-title"><header><div><p data-cluster-topic></p><h2 id="cluster-title"></h2></div><button data-close aria-label="关闭论文列表">×</button></header>
<div class="dialog-papers" data-cluster-papers></div><button class="focus-period" data-focus-period>放大到这段时间</button></dialog>
</main><footer class="page-foot wrap"><a href="/insights/">全部文章</a><a href="/insights/feed.xml">RSS 订阅</a></footer></body></html>
'''


def home_tools(articles):
    topics = groups(articles).get("研究主题", [])[:4]
    chips = "".join(f'<a href="{escape(tag_url(t))}">{escape(display_tag(t))} <small>{n}</small></a>' for t, n in topics)
    n = sum("reading" in a for a in articles)
    return f'''<h2>研究与阅读</h2><p>{n} 篇论文研读 · {len(articles)-n} 篇报告洞察</p>
<nav class="catalog-nav"><a href="/insights/">全部文章</a><a href="/insights/timeline/">研读甘特图</a><a href="/insights/tags/">标签目录</a></nav>
<form class="catalog-controls home-filter" method="get" action="/insights/">{select_tags(articles)}<button type="submit">按标签浏览</button></form><div class="tag-shortcuts">{chips}</div>'''


def ordered_key(article):
    return (article['published'], article.get('reading', {}).get('day', article['published']), article['slug'])
