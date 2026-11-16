# 报告洞察发布流程

本仓库是“兔子的蓝天”的 GitHub Pages 源站。保留原个人主页，在 /insights/ 提供静态文章目录和正文；Python 标准库生成 HTML，无前端构建依赖。

## 内容与输出

- content/insights/<slug>.json：已编辑的公开稿，字段由 scripts/public_insights.py 验证。
- insights/<slug>/index.html：静态正文，固定链接可直接分享。
- insights/index.html、index.json、feed.xml：目录、机器索引与 RSS。
- index.html 中 REPORT_INSIGHTS 标记之间：最近文章入口；保留其余主页内容。
- assets/css/insights.css：文章与目录的响应式样式。

## 一篇文章的更新

先读取 master 最新版本和全部公开稿，再生成单独公开稿。原始研究文件 SHA-256 为 source_id，同一来源保持同一 slug 和首次发布日期。更新内容时调整 updated。

```sh
python3 -B scripts/public_insights.py --repo . --article /本机工作区/public_article.json --result /本机工作区/build_result.json
```

正文结构使用 sections 数组，包含 heading 与 paragraphs/bullets/table；表格指定 headers 与 rows。另有 title、description、lead、tags、published、updated、questions（3–5 项）和 references（citation 与可选 HTTPS url）。文本一律转义，不能靠正文注入 HTML 或脚本。

检查正文、目录、首页链接、移动端排版和来源，然后将本次公开稿与所有生成文件一次提交。已有文章不删除；同一来源更换 slug 或覆盖另一来源的 slug 会被拒绝。重复构建没有内容变化时不必新增提交。

## 发布与核验

沿用现有 master 的 GitHub Pages 发布方式，不另建站点、不改动仓库访问权限。提交时绑定已读取的父提交；只用快进更新，发生并发修改时重新读取并生成，禁止强推。检查 Pages 构建结果后，实际访问首页 → 报告洞察 → 正文；提交成功不能替代线上访问。

研究笔记与公开文章分开。站点只保存可公开材料，不持有 Notion 令牌，不发布私人行动、内部组织数据、本地路径、私有页面链接或默认上传原报告全文。原图需要单独确认转载依据。公开稿保留来源和证据边界。

回退通过新提交恢复上一版，不改写历史。

## 自动上线检查

.github/workflows/verify-insights.yml在GitHub Pages部署成功后执行scripts/verify_public_insights.py。它实际请求站点，将首页、文章目录、各篇正文、样式与RSS逐字节比对部署提交中的文件，并验证目录链接和正文身份。结果以INSIGHTS_LIVE_VERIFICATION输出到job日志；它不持有私密数据或凭据。HTTP检查与浏览器视觉验收分开记录。
