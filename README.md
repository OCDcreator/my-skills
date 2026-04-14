# my-skills

个人 AI 技能集合，统一管理自有技能和外部社区技能。

## 目录结构

```
my-skills/
├── custom/                                    # 自有技能
│   ├── devops/syncthing/                      # Syncthing 同步排障
│   ├── fnos-fpk-dev/                          # 飞牛 fnOS FPK 开发
│   ├── liquid-glass-compose/                  # Apple Liquid Glass UI
│   ├── opencode-provider-config/              # OpenCode 模型配置
│   ├── searxng/                               # SearXNG 联网搜索
│   └── x-reader/                              # 视频/播客转录内容分析
├── external/                                  # 外部社区技能
│   ├── anthropics-skills/                     # Anthropic 官方技能
│   ├── awesome-claude-skills/                 # ComposioHQ 社区技能
│   ├── baoyu-skills/                          # 宝玉中文技能
│   ├── claude-plugins-official/               # Anthropic 插件技能
│   └── axton-obsidian-visual-skills/          # Obsidian 可视化技能
│   └── kepano-obsidian-skills/                 # Obsidian 官方 CLI/Canvas 技能
├── update.sh / update.bat                     # 同步外部技能源
├── pull.sh / pull.bat                         # 拉取远端覆盖本地
└── push.sh / push.bat                         # 提交推送
```

## 自有技能 (custom/)

| 技能 | 说明 |
|------|------|
| [syncthing](custom/devops/syncthing/) | Syncthing 同步排障与诊断 |
| [fnos-fpk-dev](custom/fnos-fpk-dev/) | 飞牛 fnOS FPK 应用包开发指南 |
| [liquid-glass-compose](custom/liquid-glass-compose/) | Apple Liquid Glass 风格 UI 效果（Kotlin Compose） |
| [opencode-provider-config](custom/opencode-provider-config/) | OpenCode 自定义模型参数配置 |
| [searxng](custom/searxng/) | SearXNG 联网搜索（支持多引擎聚合） |
| [x-reader](custom/x-reader/) | 视频/播客转录内容多维分析与结构化总结 |

## 外部技能来源 (external/)

| 本地目录 | 源仓库 | 说明 |
|----------|--------|------|
| `external/anthropics-skills/` | [anthropics/skills](https://github.com/anthropics/skills) | Anthropic 官方技能 |
| `external/awesome-claude-skills/` | [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) | ComposioHQ 社区技能 |
| `external/baoyu-skills/` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) | 宝玉的中文技能 |
| `external/claude-plugins-official/` | [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | Anthropic 官方插件技能 |
| `external/axton-obsidian-visual-skills/` | [axtonliu/axton-obsidian-visual-skills](https://github.com/axtonliu/axton-obsidian-visual-skills) | Obsidian 可视化技能 |
| `external/kepano-obsidian-skills/` | [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) | Obsidian 官方 Markdown/Bases/Canvas/CLI 技能 |

## 一键脚本

| 脚本 | 说明 |
|------|------|
| `update.sh` / `update.bat` | 从 5 个外部源拉取最新技能到 `external/` → 自动 commit & push |
| `pull.sh` / `pull.bat` | 拉取远端仓库覆盖本地 |
| `push.sh` / `push.bat` | 提交所有变更并推送到远端 |

### 使用方式

- **macOS / Linux**: 运行 `.sh` 脚本
- **Windows**: 双击 `.bat` 文件（需安装 Git）
