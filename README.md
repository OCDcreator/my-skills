# my-skills

个人 AI 技能集合，统一管理自有技能、外部社区技能和设计参考源。

## 目录结构

```
my-skills/
├── custom/                                    # 自有技能
│   ├── codex-autopilot-scaffold/              # Codex 风格无人值守流程脚手架
│   ├── fnos-fpk-dev/                          # 飞牛 fnOS FPK 开发
│   ├── fork-upstream-workflow/                # fork 仓库个人维护与同步上游工作流
│   ├── liquid-glass-compose/                  # Apple Liquid Glass UI
│   ├── knowledge-to-print-html/               # 知识点整理为适合打印 PDF 的 HTML 讲义
│   ├── module-doc-guard-kit/                  # 模块文档覆盖与 diff 硬约束通用包
│   ├── obsidian-plugin-autodebug/              # Obsidian 插件全自动调试开发循环
│   ├── obsidian-plugin-debug-logging/          # Obsidian 插件调试日志治理
│   ├── obsidian-plugin-release-manager/       # Obsidian 插件版本号与测试库部署
│   ├── opencode-loop/                         # OpenCode Loop 无人值守编码
│   ├── opencode-provider-config/              # OpenCode 模型配置
│   ├── searxng/                               # SearXNG 联网搜索
│   ├── skill-catalog-maintainer/              # 技能目录/README/AGENTS 维护
│   ├── skill-router/                          # 任务先路由到 my-skills 中合适技能
│   ├── syncthing/                             # Syncthing 同步排障、保留名与 .stignore 规则
│   ├── windows-mac-ssh/                       # Windows PowerShell 通过 SSH/SCP 操作 Mac
│   ├── opencode-source-compass/               # OpenCode 源码架构导航与 SDK 版本兼容性诊断
│   ├── opencode-cli-handbook/                 # OpenCode CLI 速查手册（agent 非交互调用）
│   ├── kimi-code-review/                      # 让其他 Agent 调用 Kimi Code CLI 进行代码审查
│   ├── design-reference-router/               # 品牌/产品风格参考路由技能
│   ├── x-reader/                              # 内容转录与分析（含子技能）
│   │   ├── video/                             #   视频/播客转录与结构化总结
│   │   └── analyzer/                          #   多维内容分析与 actionable insights
│   └── fork-upstream-workflow-workspace/      # fork-upstream-workflow 评估工作区（非技能）
├── external/                                  # 外部来源（技能 + 设计参考）
│   ├── anthropics-skills/                     # Anthropic 官方技能
│   ├── awesome-claude-skills/                 # ComposioHQ 社区技能
│   ├── baoyu-skills/                          # 宝玉中文技能
│   ├── claude-plugins-official/               # Anthropic 插件技能
│   ├── axton-obsidian-visual-skills/          # Obsidian 可视化技能
│   ├── kepano-obsidian-skills/                # Obsidian 官方 CLI/Canvas 技能
│   ├── taste-skill/                            # 高级前端设计技能（多风格）
│   ├── html-ppt-skill/                          # HTML PPT 演示文稿生成技能
│   ├── ui-ux-pro-max-skill/                    # UI/UX Pro Max 设计智能工具包（7 技能）
│   └── awesome-design-md/                       # 品牌/产品风格参考索引（getdesign.md 按需读取）
├── update.sh / update.bat                     # 同步外部技能与设计参考源
├── pull.sh / pull.bat                         # 拉取远端覆盖本地
└── push.sh / push.bat                         # 提交推送
```

## 自有技能 (custom/)

| 技能 | 说明 |
|------|------|
| [codex-autopilot-scaffold](custom/codex-autopilot-scaffold/) | 把 Codex 风格 repo-local 无人值守 autopilot 脚手架注入任意项目，含 `maintainability`、`quality-gate recovery`、`bugfix/backlog` 三类 preset；支持已批准 plan/spec 种子、远端 Mac rollout 提示、版本感知和预算误杀防护 |
| [fnos-fpk-dev](custom/fnos-fpk-dev/) | 飞牛 fnOS FPK 应用包开发指南 |
| [fork-upstream-workflow](custom/fork-upstream-workflow/) | 个人 fork 仓库的 `origin` / `upstream` / `main` / `feat/*` 维护策略与同步上游工作流 |
| [knowledge-to-print-html](custom/knowledge-to-print-html/) | 把知识点、草稿和研究资料整理成适合打印 PDF 的 HTML 讲义，内置版式约束、打印验证与逐页子代理审版循环 |
| [liquid-glass-compose](custom/liquid-glass-compose/) | Apple Liquid Glass 风格 UI 效果（Kotlin Compose） |
| [module-doc-guard-kit](custom/module-doc-guard-kit/) | 为任意仓库接入 `docs/modules` 一对一模块文档、覆盖检查和 diff 硬约束，防止新增/修改/删除源码时文档不同步 |
| [obsidian-plugin-autodebug](custom/obsidian-plugin-autodebug/) | 通用 Obsidian 插件 build → deploy → clean-vault bootstrap → reload → log watch → screenshot/DOM check 全自动调试开发循环，含 Node/WebSocket/CDP doctor、watch on save、state reset、baseline、playbook、多轮 profile、断言、对比、HTML 报告、native smoke fixture 与 vault 状态恢复 |
| [obsidian-plugin-debug-logging](custom/obsidian-plugin-debug-logging/) | Obsidian 插件调试日志、诊断报告、BUILD_ID 与 Windows/macOS 日志导出治理 |
| [obsidian-plugin-release-manager](custom/obsidian-plugin-release-manager/) | Obsidian plugin 的 semver + codename、BUILD_ID、release build 自动 patch bump 与 test vault deploy |
| [opencode-loop](custom/opencode-loop/) | OpenCode Loop 命令行 / TUI 无人值守项目创建、优化与修复 |
| [opencode-provider-config](custom/opencode-provider-config/) | OpenCode 自定义模型参数配置 |
| [opencode-source-compass](custom/opencode-source-compass/) | OpenCode 源码架构导航与 SDK 版本兼容性诊断；66 个 SDK API 完整调用链映射、40+ 事件类型目录、Effect Service 依赖图、版本升级检测与迁移指引 |
| [opencode-cli-handbook](custom/opencode-cli-handbook/) | OpenCode CLI 速查手册；覆盖 `opencode run` 非交互执行（代码审查/辅助/CI 自动化）、服务器模式、会话管理、模型切换、调试诊断等全部 CLI 命令与参数 |
| [kimi-code-review](custom/kimi-code-review/) | 让其他 Agent 通过 Shell 或 ACP 调用 Kimi Code CLI 进行代码审查；内置 general/security/performance/architecture/style 五类审查模板与 `scripts/review.py` 封装脚本 |
| [searxng](custom/searxng/) | SearXNG 联网搜索（支持多引擎聚合） |
| [skill-catalog-maintainer](custom/skill-catalog-maintainer/) | 技能目录维护、来源审计、`README.md`/`AGENTS.md`/`SKILLS.md` 规则同步 |
| [skill-router](custom/skill-router/) | 先到 `my-skills` 源仓库检索候选技能，再明确指向下一步该加载哪个技能 |
| [syncthing](custom/syncthing/) | Syncthing 同步排障、Windows/macOS 保留名、`.stignore` 顺序与官方 REST API 诊断 |
| [windows-mac-ssh](custom/windows-mac-ssh/) | Windows PowerShell / Codex CLI 通过 SSH/SCP 流畅操作 Mac，重点规避引号、换行、路径、变量展开与远程 zsh 命令坑 |
| [x-reader](custom/x-reader/) | 内容转录与分析套件（含 [video](custom/x-reader/video/) 视频/播客转录、[analyzer](custom/x-reader/analyzer/) 多维内容分析） |
| [design-reference-router](custom/design-reference-router/) | 先选真实品牌/产品设计参考，再把约束交给 `frontend-design` 实现 |

## 外部技能来源 (external/)

| 本地目录 | 源仓库 | 说明 |
|----------|--------|------|
| `external/anthropics-skills/` | [anthropics/skills](https://github.com/anthropics/skills) | Anthropic 官方技能 |
| `external/awesome-claude-skills/` | [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) | ComposioHQ 社区技能 |
| `external/baoyu-skills/` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) | 宝玉的中文技能 |
| `external/claude-plugins-official/` | [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | Anthropic 官方插件技能 |
| `external/axton-obsidian-visual-skills/` | [axtonliu/axton-obsidian-visual-skills](https://github.com/axtonliu/axton-obsidian-visual-skills) | Obsidian 可视化技能 |
| `external/kepano-obsidian-skills/` | [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) | Obsidian 官方 Markdown/Bases/Canvas/CLI 技能 |
| `external/taste-skill/` | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | 高级前端设计技能（多风格、参数可调） |
| `external/html-ppt-skill/` | [lewislulu/html-ppt-skill](https://github.com/lewislulu/html-ppt-skill) | HTML PPT 演示文稿生成技能（多主题/布局/动画） |
| `external/ui-ux-pro-max-skill/` | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | UI/UX Pro Max 设计智能工具包（banner-design、brand、design、design-system、slides、ui-styling、ui-ux-pro-max 共 7 个技能） |

## 外部设计参考来源 (external/)

| 本地目录 | 源仓库 | 说明 |
|----------|--------|------|
| `external/awesome-design-md/` | [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) | 品牌/产品风格参考索引；本地保留品牌 slug 与跳转链接，详细 DESIGN.md 通过 `getdesign.md` 按需读取 |

## 一键脚本

| 脚本 | 说明 |
|------|------|
| `update.sh` / `update.bat` | 同步 `external/` 下的外部技能与设计参考源 → 自动 commit & push |
| `pull.sh` / `pull.bat` | 拉取远端仓库覆盖本地 |
| `push.sh` / `push.bat` | 提交所有变更并推送到远端 |

### 使用方式

- **macOS / Linux**: 运行 `.sh` 脚本
- **Windows**: 双击 `.bat` 文件（需安装 Git）
