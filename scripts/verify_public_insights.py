#!/usr/bin/env python3
"""Read the deployed Pages site and compare it with one immutable public commit.

Runs on GitHub's runner after Pages deployment; no secrets or dependencies.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import time
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
    paths = [("/", "index.html"), ("/insights/", "insights/index.html"), ("/assets/css/insights.css", "assets/css/insights.css"), ("/insights/feed.xml", "insights/feed.xml"), ("/insights/index.json", "insights/index.json")]
    paths += [(f"/insights/{a['slug']}/", f"insights/{a['slug']}/index.html") for a in articles]
    pages, files = [], []
    for urlpath, source_path in paths:
        expected = fetch(raw + source_path)
        actual = fetch(site + urlpath + "?verify=" + commit)
        expected_sha = hashlib.sha256(expected).hexdigest()
        actual_sha = hashlib.sha256(actual).hexdigest()
        if expected_sha != actual_sha:
            raise ValueError("Live content differs from published commit: " + urlpath)
        evidence = f"HTTP 200; response SHA-256 {actual_sha}; exact match to {repository}@{commit}:{source_path}"
        files.append({"url": site + urlpath, "status": 200, "sha256": actual_sha, "source_path": source_path})
        if source_path.endswith(".html"):
            parser = Headings()
            parser.feed(actual.decode("utf-8"))
            page = {"url": site + urlpath, "observed": True, "title": parser.title.strip(), "evidence": evidence}
            if urlpath == "/" and "/insights/" not in parser.links:
                raise ValueError("Homepage lacks archive navigation")
            if urlpath == "/insights/":
                if any(f"/insights/{a['slug']}/" not in parser.links for a in articles):
                    raise ValueError("Archive lacks an article link")
            if urlpath not in {"/", "/insights/"}:
                a = next(a for a in articles if urlpath == f"/insights/{a['slug']}/")
                if parser.h1.strip() != a["title"]:
                    raise ValueError("Article heading differs")
                if a["content_sha256"] not in actual.decode("utf-8"):
                    raise ValueError("Article content identity is missing")
                page["article_title"] = parser.h1.strip()
            pages.append(page)
        if source_path.endswith(".xml"):
            ET.fromstring(actual)
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
    print("INSIGHTS_LIVE_VERIFICATION=" + json.dumps(result, ensure_ascii=False, separators=(",", ":")), flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("## Public report insights verified\n\n")
            handle.write(f"Commit: `{args.commit}`\n\n")
            handle.write("\n".join(f"- [✓ {p['title']}]({p['url']})" for p in result["pages"]) + "\n\nHTTP content, article identity, RSS and navigation passed. Visual inspection is tracked separately.\n")


if __name__ == "__main__":
    main()
