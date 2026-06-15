# my-skills

个人 AI 技能集合，统一管理自有技能、外部社区技能和设计参考源。

## 目录结构

```
my-skills/
├── custom/                                    # 自有技能
│   ├── codex-autopilot-scaffold/              # Codex 风格无人值守流程脚手架
│   ├── design-reference-router/               # 品牌/产品风格参考路由技能
│   ├── fnos-fpk-dev/                          # 飞牛 fnOS FPK 开发
│   ├── fork-upstream-workflow/                # fork 仓库个人维护与同步上游工作流
│   ├── kimi-code-review/                      # 让其他 Agent 调用 Kimi Code CLI 进行代码审查
│   ├── knowledge-to-print-html/               # 知识点整理为适合打印 PDF 的 HTML 讲义
│   ├── lean-ctx-opencode-plugin/              # lean-ctx 在多 Agent 中的项目级部署
│   ├── liquid-glass-compose/                  # Apple Liquid Glass UI
│   ├── math-to-obsidian-note/                 # 数学题目/答案/知识点整理为 Obsidian Markdown 笔记
│   ├── module-doc-guard-kit/                  # 模块文档覆盖与 diff 硬约束通用包
│   ├── obsidian-plugin-autodebug/              # Obsidian 插件全自动调试开发循环
│   ├── obsidian-plugin-debug-logging/          # Obsidian 插件调试日志治理
│   ├── obsidian-plugin-release-manager/       # Obsidian 插件版本号与测试库部署
│   ├── open-source-projects/                  # 本地 open-source-project 索引查询
│   ├── opencode-cli-handbook/                 # OpenCode CLI 速查手册（agent 非交互调用）
│   ├── opencode-loop/                         # OpenCode Loop 无人值守编码
│   ├── opencode-mcp-delegate/                 # OpenCode MCP 分发与会话协同
│   ├── opencode-plugin-builder/               # OpenCode 插件开发完整指南（API + 模板 + 踩坑）
│   ├── opencode-provider-config/              # OpenCode 模型配置
│   ├── opencode-source-compass/               # OpenCode 源码架构导航与 SDK 兼容诊断
│   ├── pdf-toc-bookmarker/                    # 扫描 PDF 目录页生成可点击书签
│   ├── project-level-tools/                   # 项目级 GitNexus + lean-ctx 配置教程
│   ├── rewrite-doc2x-markdown/                # Doc2X OCR Markdown 重写为高质量 canonical transcript
│   ├── scan-pdf-to-print-html/                # 扫描型 PDF 保真转录为 A4 HTML/PDF
│   ├── searxng/                               # SearXNG 联网搜索
│   ├── skill-catalog-maintainer/              # 技能目录/README/AGENTS 维护
│   ├── skill-router/                          # 任务先路由到 my-skills 中合适技能
│   ├── sub/                                   # OpenClash / sub-web / subconverter / wallrule 链路排障
│   ├── ssh/                                    # SSH/SCP 远程操作（Mac/Windows/Unraid/路由器/飞牛）
│   ├── syncthing/                             # Syncthing 同步排障、保留名与 .stignore 规则
│   └── x-reader/                              # 内容转录与分析（含子技能）
│       ├── analyzer/                          #   多维内容分析与 actionable insights
│       ├── browser-fetch/                     #   浏览器渲染抓取兜底
│       ├── douyin/                            #   抖音短视频转写与总结
│       └── video/                             #   视频/播客转录与结构化总结
├── external/                                  # 外部来源（技能 + 设计参考）
│   ├── anthropics-skills/                     # Anthropic 官方技能
│   ├── awesome-claude-skills/                 # ComposioHQ 社区技能
│   ├── baoyu-skills/                          # 宝玉中文技能
│   ├── claude-plugins-official/               # Anthropic 插件技能
│   ├── axton-obsidian-visual-skills/          # Obsidian 可视化技能
│   ├── deep-research-skills/                  # Deep Research 结构化调研技能（Claude/OpenCode/Codex）
│   ├── kepano-obsidian-skills/                # Obsidian 官方 CLI/Canvas 技能
│   ├── taste-skill/                           # 高级前端设计技能（多风格）
│   ├── html-ppt-skill/                        # HTML PPT 演示文稿生成技能
│   ├── ui-ux-pro-max-skill/                   # UI/UX Pro Max 设计智能工具包（7 技能）
│   ├── startup-pressure-test/                  # CodeX 创业想法压力测试技能
│   ├── mattpocock-skills/                      # Matt Pocock 工程技能集（grill-me / tdd / 架构优化等）
│   └── awesome-design-md/                     # 品牌/产品风格参考索引（getdesign.md 按需读取）
├── automation/                                # repo-local Codex autopilot 控制器与配置
├── docs/                                      # autopilot 状态、历史计划和规格文档
├── scripts/                                   # 仓库结构校验与目录生成脚本
├── SKILLS.md                                  # 自动生成的 source-aware 技能索引
├── update.sh / update.ps1                     # 同步外部技能与设计参考源
├── pull.sh / pull.ps1                         # 拉取远端覆盖本地
└── push.sh / push.ps1                         # 提交推送
```

## 自有技能 (custom/)

<!-- BEGIN GENERATED CUSTOM_SKILLS -->
| 技能 | 说明 |
|------|------|
| [codex-autopilot-scaffold](custom/codex-autopilot-scaffold/) | Use when a user wants to add, refresh, or operate a repo-local unattended Codex autopilot scaffold in a repository, especially queue-driven refactor/quality/bugfix work, review-gated rounds, Windows/macOS bootstrap, health checks, remote Mac rollout, or preserving lane docs during scaffold upgrad... |
| [design-reference-router](custom/design-reference-router/) | Use when the user wants a page or UI to follow a real product or brand style, mentions DESIGN.md, getdesign.md, or awesome-design-md, or asks for a non-generic design that should start from concrete reference sites before implementation. |
| [fnos-fpk-dev](custom/fnos-fpk-dev/) | 飞牛 fnOS FPK 应用包开发指南。涵盖目录结构、manifest 配置、生命周期脚本、用户向导、权限管理、resource 资源声明和桌面图标配置。Use when developing fnOS FPK packages, creating fnOS apps, writing cmd scripts, configuring wizard/manifest/privilege/resource, desktop icons, ui/config, or when the user mentions 飞牛、fnOS、fpk。 |
| [fork-upstream-workflow](custom/fork-upstream-workflow/) | Use when the user is maintaining a personal Git fork and needs to keep their own changes while following updates from the original repository. Trigger for requests about `origin` vs `upstream`, syncing a fork with the original author, managing `main` plus feature branches, choosing merge vs rebas... |
| [kimi-code-review](custom/kimi-code-review/) | Enable external AI agents and automated systems to invoke Kimi Code CLI for code review, quality analysis, and automated auditing. Use when (1) another agent or CI pipeline needs to delegate code review to Kimi Code CLI programmatically, (2) an external system wants to leverage Kimi Code CLI revi... |
| [knowledge-to-print-html](custom/knowledge-to-print-html/) | Use when the user wants notes, keywords, drafts, lesson content, or research findings turned into a print-ready HTML/PDF teaching handout. Trigger aggressively for requests like “知识点整理成讲义”, “把这些笔记整理成讲义”, “可打印 HTML”, “打印成 PDF”, “教学页”, “复习手册”, “make it printable”, “knowledge handout”, “teaching han... |
| [lean-ctx-deploy](custom/lean-ctx-opencode-plugin/) | Guide for deploying lean-ctx token optimization into AI coding agents. Covers three integration modes — MCP server mode (Claude Code, Kiro, OpenCode, Cursor), CLI-redirect plugin mode (OpenCode), and Hybrid mode with shell hooks (Codex) — with project-level setup, cross-platform debugging (Window... |
| [liquid-glass-compose](custom/liquid-glass-compose/) | Implement Apple-style Liquid Glass / glassmorphism UI effects in Kotlin Compose Multiplatform projects using the `io.github.fletchmckee.liquid:liquid` library. Use this skill whenever the user asks to create frosted glass, glassmorphism, liquid glass, blur glass, translucent navigation bars, glas... |
| [math-to-obsidian-note](custom/math-to-obsidian-note/) | Convert uploaded math-related images or text into a polished Obsidian Markdown note under the user's math vault. Use when the user provides math problems, answers, solution steps, exam screenshots, handwritten notes, diagrams, formulas, or knowledge points and wants them organized as a Markdown d... |
| [module-doc-guard-kit](custom/module-doc-guard-kit/) | Use when a repo needs per-module documentation under docs/modules, hard CI/local checks that fail on source-doc drift, or a reusable package so another agent can keep module docs synchronized when files are added, changed, renamed, or deleted. Trigger on 模块文档, module docs, docs/modules, doc cover... |
| [obsidian-plugin-autodebug](custom/obsidian-plugin-autodebug/) | Use when Obsidian plugin work turns into debugging, smoke testing, or release validation. Triggers include white screens after reload, slow startup, stale UI after deploy, fresh-vault install failures, console/DevTools capture, screenshots, DOM/CSS assertions, locale/i18n checks, watch-on-save lo... |
| [obsidian-plugin-debug-logging](custom/obsidian-plugin-debug-logging/) | Use this when developing or retrofitting an Obsidian plugin and the user mentions 调试日志, debug logging, 控制台日志, console logs, diagnostic report, 诊断报告, 日志开关, 日志分级, 默认静默, 模块日志开关, 子模块调试开关, 高频日志刷新频率, 故障排查, 最近日志缓存, 日志导出, 环境快照, BUILD_ID, version/build logs, or wants a maintainable logging/diagnostics sys... |
| [obsidian-plugin-release-manager](custom/obsidian-plugin-release-manager/) | Create or retrofit a complete release-management workflow for Obsidian plugins. Use this whenever the user mentions Obsidian plugin versioning, manifest/package version sync, release codename, display version, BUILD_ID, release build automation, test vault deployment, or wants an existing Obsidia... |
| [open-source-projects](custom/open-source-projects/) | 本地开源项目索引。当用户提到任何开源项目名称（中英文均可）、询问项目在哪里、 想看某个项目、问项目是做什么的、提到 repo/repository/项目/仓库/open-source-project、 问"我收藏了什么项目"、或者用户提到任何可能在 open-source-project 目录下的项目时， 都必须使用这个 skill。永远不要全盘搜索文件系统来猜测项目位置， 而是先查数据库。 |
| [opencode-cli-handbook](custom/opencode-cli-handbook/) | OpenCode CLI 速查手册 —— 让任意 agent 快速掌握 opencode 命令行的调用方式， 用于代码审查、代码辅助、调试诊断、会话管理、模型切换等自动化场景。 触发场景（满足任一即应加载此技能）： - agent 需要通过命令行调用 opencode 来完成代码审查、代码生成、bug 修复 - 用户说"用 opencode run"、"opencode CLI"、"opencode 命令行"、"非交互模式" - 需要在脚本/CI/子 agent 中调用 opencode（不需要 TUI） - 用户问"opencode 怎么跑一条命令"、"怎么用 opencode 审查代... |
| [opencode-loop](custom/opencode-loop/) | Use when the user wants opencode-loop unattended or self-running multi-iteration coding over a target project: run build-verify-fix cycles, optimize/refactor repos, fix test/lint/type failures, bootstrap projects, or watch a live human dashboard for long runs. Trigger on phrases like 无人值守, 自动循环,... |
| [opencode-mcp-delegate](custom/opencode-mcp-delegate/) | Use when an AI coding agent (Codex, Claude Code, etc.) needs to delegate coding or review tasks to OpenCode via the opencode-mcp MCP server. Trigger on requests to use opencode MCP tools, run long background jobs, continue OpenCode sessions, or avoid direct bash `opencode run`. Prefer workflow to... |
| [opencode-plugin-builder](custom/opencode-plugin-builder/) | Guide LLMs through writing, testing, and configuring OpenCode plugins using the @opencode-ai/plugin TypeScript API. Use when the user wants to create, modify, or debug an OpenCode plugin (.ts/.js), register custom tools via the tool() helper, hook into OpenCode lifecycle events (tool.execute.befo... |
| [opencode-provider-config](custom/opencode-provider-config/) | Configure complete model parameters (context window, output tokens, capabilities, cost) for custom providers in OpenCode via cc-Switch. Use this skill whenever the user mentions configuring a new provider in OpenCode or cc-Switch, when a custom model lacks context window information, when the use... |
| [opencode-source-compass](custom/opencode-source-compass/) | OpenCode 源码架构导航与版本兼容性诊断技能。 为接入 OpenCode SDK 的插件/应用提供源码快速定位、故障诊断路径和版本差异检测。 触发场景（只要有以下任何一条就应该加载此技能）： - 用户提到 OpenCode SDK、opencode-ai、OpencodeClient、createOpencodeClient - 用户在开发接入 OpenCode 的插件（Obsidian 插件、VSCode 插件、Web 应用等） - 用户遇到 OpenCode SDK 调用错误、HTTP 请求失败、SSE 事件问题 - 用户提到 opencode serve、opencode s... |
| [pdf-toc-bookmarker](custom/pdf-toc-bookmarker/) | Create a new PDF with clickable bookmarks/outline from scanned or image-only table-of-contents pages. Use when Codex needs to add PDF bookmarks from TOC screenshots/pages, especially for scanned Chinese books where local OCR is unreliable. Requires the user to provide a PDF file path, the TOC pag... |
| [piclist-upload](custom/piclist-upload/) | Use when uploading images to the user's personal image host (pic.ltreen.tech, a Lsky Pro+ bed on fnOS reached via frp), migrating images embedded in Markdown/HTML files (remote CDN links like noedgeai/unsplash/imgur, or local paths) to that bed through the local PicList client, getting image URLs... |
| [project-level-tools](custom/project-level-tools/) | Use when the user wants GitNexus and/or lean-ctx configured for one repository instead of globally, including project-level MCP setup, repo-local Codex hooks, trusted-project setup, local templates, or Windows/macOS per-project tool isolation. |
| [rewrite-doc2x-markdown](custom/rewrite-doc2x-markdown/) | Use when Doc2X OCR markdown, Doc2X export.md, page-transcript.raw.md, or source-transcript.md is messy, too long, poorly structured, or must be rewritten into a high-quality canonical Markdown transcript before downstream use. Also use when the user provides a PDF file alongside or instead of Mar... |
| [scan-pdf-to-print-html](custom/scan-pdf-to-print-html/) | Use when scanned or image-only PDFs need Doc2X OCR into a faithful, auditable page transcript and then A4 HTML/PDF, OR when an already-clean markdown file must become a printable A4 HTML/PDF handout. Best for textbooks, notes, worksheets, formulas, tables, diagrams, and question pages where conte... |
| [searxng](custom/searxng/) | Search the internet using your self-hosted SearXNG instance. Use this when you need to search for current information, news, documentation, or any web content. Triggers: "search for", "look up", "find information about", "what is", "how to" when web search is needed. |
| [skill-catalog-maintainer](custom/skill-catalog-maintainer/) | Use when working in a skills repository and the user asks to understand, catalog, compare, audit, add, remove, rename, or maintain skills and their metadata, or to update `SKILLS.md`, `README.md`, `AGENTS.md`, `update.sh`, or `update.ps1` after skill changes. |
| [skill-evolution](custom/skill-evolution/) | Use after finishing a task with ANY custom skill where you gave corrections, rework, or "do this differently" feedback, and want to fold those corrections back into the skill so the same mistake is not repeated. Invoke manually at the end of a session — it reads the session's user messages, extra... |
| [skill-router](custom/skill-router/) | Use when the immediate job is to decide which skills should be loaded from the `my-skills` repository before doing real work, especially if the user asks for skill recommendations, says to search their skill repo, references `my-skills`, or invokes a path-based skill prompt to bootstrap another t... |
| [ssh](custom/ssh/) | Use when the user mentions SSH, SCP, remote shell, "SSH 连接", "连 mac", "连 unraid", "连路由器", "连飞牛", "远程执行", "远程命令", "scp 传文件", "连服务器", or any device connection via OpenSSH. Triggers on connecting to any known device (Mac, Windows, Unraid, router, NAS) or general SSH/SCP operations. Includes device i... |
| [sub](custom/sub/) | Diagnose and maintain the local OpenClash subscription-conversion chain built from OpenClash, `sub-web`, `subconverter`, and the `wallrule` preset on this machine. Use when requests mention OpenClash, 订阅转换, `sub-web`, `subconverter`, `wallrule`, 自定义模板, `25500`, `25502`, `IPRoyal`, `dialer-proxy`,... |
| [syncthing](custom/syncthing/) | Use when diagnosing Syncthing sync failures: stuck syncing, out of sync, 0% completion between Windows and macOS, folder errors, `.stignore` ignore rule surprises, Windows reserved names such as aux/con/prn/nul/com/lpt, delete-dir not-empty loops, permission denied, or device connection problems. |
| [x-reader](custom/x-reader/) | Use when user shares media URLs, Douyin/抖音, web pages, blocked or JavaScript-rendered URLs, direct audio/video links, or requests transcription, digest, summary, browser extraction, or content analysis. |
| [x-reader/analyzer](custom/x-reader/analyzer/) | Multi-dimensional content analysis with actionable insights. Triggers when user sends content (URL, text, or transcript) with analysis intent - commands like '/analyze [URL]', 'Analyze this article', 'What are the key takeaways?', or auto-triggered after video/podcast transcription. Outputs struc... |
| [x-reader/browser-fetch](custom/x-reader/browser-fetch/) | Use when a web URL cannot be read by normal fetch tools, appears blocked by Cloudflare/reCAPTCHA/bot detection, needs JavaScript rendering, login state, browser interaction, or a stealth browser fallback before analysis. |
| [x-reader/douyin](custom/x-reader/douyin/) | Use when user sends Douyin or 抖音 share text, v.douyin.com links, douyin.com video links, or asks to transcribe, summarize, digest, download, or save a Douyin short video. |
| [x-reader/video](custom/x-reader/video/) | Video and podcast transcription with structured summaries. Auto-triggered when a media URL is detected (YouTube, Bilibili, X/Twitter, Xiaoyuzhou, Apple Podcasts, or direct mp3/mp4/m3u8 links). Extracts subtitles or transcribes via Whisper, then outputs formatted digest with key points and timesta... |
<!-- END GENERATED CUSTOM_SKILLS -->

## 外部技能来源 (external/)

<!-- BEGIN GENERATED EXTERNAL_SKILL_SOURCES -->
| 本地目录 | 源仓库 | 说明 |
|----------|--------|------|
| `external/anthropics-skills/` | [anthropics/skills](https://github.com/anthropics/skills.git) | 17 个技能（core：高质量官方/精选源） |
| `external/anysearch-skill/` | [anysearch-ai/anysearch-skill](https://github.com/anysearch-ai/anysearch-skill.git) | 0 个技能 |
| `external/awesome-claude-skills/` | [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills.git) | 863 个技能（bulk：完整索引见 docs/full-catalog.md） |
| `external/axton-obsidian-visual-skills/` | [axtonliu/axton-obsidian-visual-skills](https://github.com/axtonliu/axton-obsidian-visual-skills.git) | 3 个技能 |
| `external/baoyu-skills/` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills.git) | 21 个技能 |
| `external/claude-plugins-official/` | [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official.git) | 22 个技能（core：高质量官方/精选源） |
| `external/deep-research-skills/` | [Weizhena/Deep-Research-skills](https://github.com/Weizhena/Deep-Research-skills.git) | 20 个技能 |
| `external/doc2x-cli-skills/` | [noedgeai/doc2x-cli-skills](https://github.com/noedgeai/doc2x-cli-skills.git) | 1 个技能 |
| `external/doc2x-mcp/` | [NoEdgeAI/doc2x-mcp](https://github.com/NoEdgeAI/doc2x-mcp.git) | 1 个技能 |
| `external/html-ppt-skill/` | [lewislulu/html-ppt-skill](https://github.com/lewislulu/html-ppt-skill.git) | 0 个技能 |
| `external/kepano-obsidian-skills/` | [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills.git) | 5 个技能（core：高质量官方/精选源） |
| `external/last30days-skill/` | [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill.git) | 1 个技能（core：高质量官方/精选源） |
| `external/last30days-skill-cn/` | [Jesseovo/last30days-skill-cn](https://github.com/Jesseovo/last30days-skill-cn.git) | 1 个技能 |
| `external/mattpocock-skills/` | [mattpocock/skills](https://github.com/mattpocock/skills.git) | 29 个技能（core：高质量官方/精选源） |
| `external/startup-pressure-test/` | [Kappaemme-git/codex-startup-pressure-test-skill](https://github.com/Kappaemme-git/codex-startup-pressure-test-skill.git) | 1 个技能 |
| `external/taste-skill/` | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill.git) | 13 个技能 |
| `external/ui-ux-pro-max-skill/` | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git) | 7 个技能 |
<!-- END GENERATED EXTERNAL_SKILL_SOURCES -->

## 外部设计参考来源 (external/)

<!-- BEGIN GENERATED EXTERNAL_REFERENCE_SOURCES -->
| 本地目录 | 源仓库 | 说明 |
|----------|--------|------|
| `external/agent-reach/` | [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach.git) | 设计参考索引 |
| `external/awesome-design-md/` | [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md.git) | 设计参考索引 |
<!-- END GENERATED EXTERNAL_REFERENCE_SOURCES -->

## 一键脚本

| 脚本 | 说明 |
|------|------|
| `update.sh` / `update.ps1` | 同步 `external/` 下的外部技能与设计参考源 → 自动 commit & push |
| `pull.sh` / `pull.ps1` | 拉取远端仓库覆盖本地 |
| `push.sh` / `push.ps1` | 提交所有变更并推送到远端 |
| `scripts/generate_skills_catalog.py` | 从实际 `SKILL.md` 和 `update.sh` source metadata 生成 `SKILLS.md` |
| `scripts/verify_structure.py` | 校验 README/SKILLS 索引、脚本同构、excluded 外部示例技能和根目录技能漂移 |

### 使用方式

- **macOS / Linux**: 运行 `.sh` 脚本
- **Windows**: 运行 `.ps1` 文件（需安装 Git）
