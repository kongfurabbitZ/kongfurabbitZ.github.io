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

.github/workflows/verify-insights.yml在master更新时启动，等待GitHub Pages内容生效后执行scripts/verify_public_insights.py。它实际请求站点，将首页、文章目录、各篇正文、样式与RSS逐字节比对部署提交中的文件，并验证目录链接和正文身份。结果以INSIGHTS_LIVE_VERIFICATION输出到job日志；它不持有私密数据或凭据。HTTP检查与浏览器视觉验收分开记录。

## 全站视觉与栏目（2026-11-17）

沿用主页现有 Strata 风格。目录与正文由渲染器从当前 index.html 复用头像、个人介绍和社交页脚，链接转为根路径，统一加载 assets/css/main.css；assets/css/insights.css 只做阅读排版补充，不另设独立主题。修改主页个人介绍后，重新构建即可同步全部文章。

首页仅保留有真实内容的介绍、报告洞察及联系方式；不恢复模板卡片、空栏目或未接通的留言表单。后续随着真实内容增加，再逐步调整栏目与全站视觉。

## 论文研读、甘特图和标签

/insights/ 收录研读与报告，/insights/tags/ 收录全站标签。/insights/timeline/ 依照北京时间的入库日展示论文，按研究主题分行，支持日、周、月、季、年与全览。相近记录按当前尺度合并，点击卡片进入文章或选择组内论文。网页可分享当前时间范围与筛选，旧链接 month=all 和 month=YYYY-MM 仍可打开。

一篇公开论文沿用原文章字段，另外包含 reading 对象。day 为 ISO 日历日，key 为稳定的来源记录摘要，revision 为来源修订摘要，identity 为 pdf 或 bibliography。论文以具体研究主题和方法标记，报告沿用各自的标签。更新已有内容须保留原 slug、source_id、首次发布时间和记录身份。只以书目校验的历史材料采用规范文献链接摘要，不将其当作 PDF 文件摘要。

构建入口仍为 scripts/public_insights.py。查询、点图、标签、RSS 与首页都由 content/insights/ 下的全部公开稿生成；有新增或修订时应带上当前所有稿件重建。分页读取私人来源，按每篇正文独立编辑、核对书目信息，只将通过公开审阅的内容放到本站。共享主题与方法使用同一标签名。来源更新时先匹配记录摘要，再核对源身份和既有网址。核验工作流同时检查所有文章及导航，并在两种屏幕宽度实测筛选与跳转。

首页沿用既有入口文件。assets/js/main.js 会在原研究栏目加载 insights/home-fragment.html，此片段与每次发布同步重建。网络加载失败时访客仍能从首页进入静态文章目录。新建的内容页统一通过主页的联系入口联系作者。

时间轴使用本站托管的 vis-timeline 8.5.6。源码标签为 v8.5.6，官方预构建发布树为 8c5ddefcfbc51bace61758a7526d8f7e57696f10，保留原版许可。重建时从同一提交取完整 scripts 和 assets，包含 reading_catalog.TIMELINE_ASSETS 列出的样式、交互脚本及 assets/vendor/vis-timeline-8.5.6。浏览器直接读取本站文件。缺少中文系统字体时使用本站托管的 Noto Sans SC（Fontsource 5.3.1，SIL OFL 1.1）。将上游 99c8c932bbb29d808fdd82b45ae4ac65e37f57f7 的 7,946 个字符按 Unicode 划为五个 WOFF2 分区，完整保留覆盖范围。字体和许可位于 assets/vendor/noto-sans-sc/，与头像一样作为站点静态资源随版本保留。
