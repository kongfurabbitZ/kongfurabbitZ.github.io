#!/usr/bin/env python3
"""Read the deployed Pages site and compare it with one immutable public commit.

Runs on GitHub's runner after Pages deployment; no secrets or dependencies.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import base64
import gzip
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import time
import subprocess
import tempfile
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


class Headings(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.h1 = ""
        self.links = []
        self.current = None
    def handle_starttag(self, tag, attrs):
        if tag in {"title", "h1"}:
            self.current = tag
        if tag == "a":
            self.links.append(dict(attrs).get("href", ""))
    def handle_endtag(self, tag):
        if tag == self.current:
            self.current = None
    def handle_data(self, data):
        if self.current == "title":
            self.title += data
        if self.current == "h1":
            self.h1 += data


def fetch(url):
    request = Request(url, headers={"User-Agent": "Bowen-Insights-Smoke-Check/1.0", "Cache-Control": "no-cache"})
    with urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}: {url}")
        return response.read()


def verify(repository, commit, site):
    raw = f"https://raw.githubusercontent.com/{repository}/{commit}/"
    index = json.loads(fetch(raw + "insights/index.json"))
    articles = index["articles"]
    nav = {"/": "index.html", "/insights/": "insights/index.html", "/insights/timeline/": "insights/timeline/index.html", "/insights/tags/": "insights/tags/index.html"}
    by_url = {f"/insights/{a['slug']}/": a for a in articles}
    paths = list(nav.items()) + [(p, p[1:]) for p in ("/insights/home-fragment.html", "/assets/css/insights.css", "/assets/css/reading-catalog.css", "/assets/js/reading-catalog.js", "/insights/feed.xml", "/insights/index.json")]
    paths += [(u, u[1:] + "index.html") for u in by_url]

    def check(pair):
        urlpath, source_path = pair
        expected = fetch(raw + source_path)
        actual = fetch(site + urlpath + "?verify=" + commit)
        if expected != actual:
            raise ValueError("Live content differs from published commit: " + urlpath)
        actual_sha = hashlib.sha256(actual).hexdigest()
        file = {"url": site + urlpath, "status": 200, "sha256": actual_sha, "source_path": source_path}
        page = None
        if source_path == "insights/home-fragment.html":
            parser = Headings()
            parser.feed(actual.decode("utf-8"))
            if not (set(nav) - {"/"}) <= set(parser.links):
                raise ValueError("Homepage research component lacks navigation")
        elif source_path.endswith(".html"):
            parser = Headings()
            parser.feed(actual.decode("utf-8"))
            page = {"url": site + urlpath, "observed": True, "title": parser.title.strip(), "evidence": f"HTTP 200; SHA-256 {actual_sha}; exact match: {repository}@{commit}:{source_path}"}
            links = set(parser.links)
            if urlpath == "/" and "/insights/" not in links:
                raise ValueError("Homepage lacks catalog navigation")
            if urlpath == "/insights/" and not set(by_url) <= links:
                raise ValueError("Archive lacks an article link")
            if urlpath == "/insights/timeline/" and any(u not in links for u, a in by_url.items() if "reading" in a):
                raise ValueError("Timeline lacks a paper link")
            if urlpath in by_url:
                a = by_url[urlpath]
                if parser.h1.strip() != a["title"] or a["content_sha256"] not in actual.decode("utf-8"):
                    raise ValueError("Article identity differs: " + urlpath)
                page["article_title"] = parser.h1.strip()
        if source_path.endswith(".xml"):
            feed = ET.fromstring(actual)
            if {i.findtext("link") for i in feed.findall("./channel/item")} != {site + u for u in by_url}:
                raise ValueError("Incomplete RSS")
        return file, page

    # Fail quickly while Pages still serves the previous deployment, then check every article.
    results = [check(paths[0])]
    with ThreadPoolExecutor(max_workers=6) as pool:
        results.extend(pool.map(check, paths[1:]))
    files = [f for f, _ in results]
    pages = [p for _, p in results if p]
    return {"schema_version": 1, "ok": True, "repository": repository, "commit": commit, "checked_at": datetime.now(timezone.utc).isoformat(), "pages": pages, "files": files, "visual_status": "pending", "visual_note": "HTTP content and navigation verified; responsive CSS has not been visually inspected."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--site", default="https://kongfurabbitz.github.io")
    parser.add_argument("--output", required=True)
    parser.add_argument("--attempts", type=int, default=8)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository) or not re.fullmatch(r"[a-f0-9]{40}", args.commit):
        raise ValueError("Invalid immutable source identity")
    for attempt in range(args.attempts):
        try:
            result = verify(args.repository, args.commit, args.site.rstrip("/"))
            break
        except Exception as exc:
            if attempt + 1 == args.attempts:
                raise
            print(f"Attempt {attempt + 1}: site not ready ({type(exc).__name__}: {exc})", flush=True)
            time.sleep(15)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("INSIGHTS_LIVE_GZIP=" + base64.b64encode(gzip.compress(json.dumps(result, ensure_ascii=False).encode())).decode(), flush=True)
    print("INSIGHTS_LIVE_VERIFICATION=" + json.dumps(result, ensure_ascii=False, separators=(",", ":")), flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("## Public report insights verified\n\n")
            handle.write(f"Commit: `{args.commit}`\n\n")
            handle.write("\n".join(f"- [✓ {p['title']}]({p['url']})" for p in result["pages"]) + "\n\nHTTP content, article identity, RSS and navigation passed. Visual inspection is tracked separately.\n")

    if os.environ.get("GITHUB_ACTIONS") == "true":
        # Run the pinned browser smoke test against the live site after the byte comparison.
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "check_reading_ui.mjs"
            script.write_bytes(fetch(f"https://raw.githubusercontent.com/{args.repository}/{args.commit}/scripts/check_reading_ui.mjs"))
            subprocess.run(["node", str(script)], env={**os.environ, "READING_SITE": args.site}, check=True, timeout=100)


if __name__ == "__main__":
    main()
