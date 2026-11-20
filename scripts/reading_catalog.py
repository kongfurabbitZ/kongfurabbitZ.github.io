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


def filters(articles, timeline=False):
    kind = '' if timeline else '<label>内容类型<select name="kind"><option value="">全部内容</option><option value="paper">论文研读</option><option value="report">报告洞察</option></select></label>'
    months = ""
    if timeline:
        available = sorted({a['reading']['day'][:7] for a in articles}, reverse=True)
        options = "".join(f'<option value="{m}">{m[:4]} 年 {int(m[5:])} 月</option>' for m in available)
        months = '<label>时间范围<select name="month"><option value="all">全部月份</option>' + options + '</select></label>'
    return f'<form class="catalog-controls" data-filters>{months}{kind}{select_tags(articles)}<label>关键词<input name="q" type="search" placeholder="搜索标题、方法或关键词"></label><button type="reset">清除筛选</button></form>'


def attributes(article):
    fields = {"kind": "paper" if "reading" in article else "report", "tags": json.dumps(article["tags"], ensure_ascii=False), "search": " ".join([article["title"], article["description"], *article["tags"]])}
    if "reading" in article:
        fields["day"] = article["reading"]["day"]
    return " ".join(f'data-{k}="{escape(v, quote=True)}"' for k, v in fields.items())


def render_timeline(articles):
    papers = sorted((a for a in articles if 'reading' in a), key=lambda a: (a['reading']['day'], a['title']), reverse=True)
    rows = []
    for a in papers:
        day = a['reading']['day']
        label = escape(a['title'])
        topic = next((display_tag(t) for t in a['tags'] if t.startswith('主题·')), '')
        rows.append(f'<li class="gantt-row" data-item {attributes(a)}><a class="gantt-name" href="{article_url(a)}">{label}<small><time datetime="{day}">{day}</time> · {escape(topic)}</small></a><div class="gantt-track"><a class="gantt-dot" title="{day} · {label}" aria-label="{day}，阅读《{label}》" href="{article_url(a)}"></a></div></li>')
    return f'''<div data-catalog="timeline"><h1>论文研读甘特图</h1><p class="intro">按研读笔记的入库日回看阅读历程。每个圆点代表一篇论文，日期按北京时间显示。点击标题或圆点即可阅读。</p>
{filters(papers, timeline=True)}<p data-count role="status" class="catalog-count">{len(papers)} 篇论文</p><div class="gantt"><div class="gantt-axis"><span>研读记录</span><div data-axis></div></div><ol class="gantt-rows">{''.join(rows)}</ol></div><p data-empty hidden>这个范围内没有匹配的研读记录。</p></div>'''


def home_tools(articles):
    topics = groups(articles).get("研究主题", [])[:4]
    chips = "".join(f'<a href="{escape(tag_url(t))}">{escape(display_tag(t))} <small>{n}</small></a>' for t, n in topics)
    n = sum("reading" in a for a in articles)
    return f'''<h2>研究与阅读</h2><p>{n} 篇论文研读 · {len(articles)-n} 篇报告洞察</p>
<nav class="catalog-nav"><a href="/insights/">全部文章</a><a href="/insights/timeline/">研读甘特图</a><a href="/insights/tags/">标签目录</a></nav>
<form class="catalog-controls home-filter" method="get" action="/insights/">{select_tags(articles)}<button type="submit">按标签浏览</button></form><div class="tag-shortcuts">{chips}</div>'''


def ordered_key(article):
    return (article['published'], article.get('reading', {}).get('day', article['published']), article['slug'])
