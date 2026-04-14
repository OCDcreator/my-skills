# my-skills

个人 AI 技能集合，统一管理自有技能和外部社区技能。

## 目录结构

```
my-skills/
├── devops/                        # 自有技能
│   └── syncthing/                 # Syncthing 同步排障
├── fnos-fpk-dev/                  # 飞牛 fnOS FPK 开发
├── liquid-glass-compose/          # Apple Liquid Glass UI
├── opencode-provider-config/      # OpenCode 模型配置
├── anthropics-skills/             # ← Anthropic 官方技能
├── awesome-claude-skills/         # ← ComposioHQ 社区技能
├── baoyu-skills/                  # ← JimLiu 宝玉技能
├── claude-plugins-official/       # ← Anthropic 插件技能
├── axton-obsidian-visual-skills/  # ← Obsidian 可视化技能
├── pull.sh / pull.bat             # 拉取远端覆盖本地
├── push.sh / push.bat             # 提交推送
└── update.sh / update.bat         # 一键同步所有外部技能源
```

## 自有技能

| 技能 | 说明 |
|------|------|
| [syncthing](devops/syncthing/) | Syncthing 同步排障与诊断 |
| [fnos-fpk-dev](fnos-fpk-dev/) | 飞牛 fnOS FPK 应用包开发指南 |
| [liquid-glass-compose](liquid-glass-compose/) | Apple Liquid Glass 风格 UI 效果（Kotlin Compose） |
| [opencode-provider-config](opencode-provider-config/) | OpenCode 自定义模型参数配置 |

## 外部技能来源

| 本地目录 | 源仓库 | 说明 |
|----------|--------|------|
| `anthropics-skills/` | [anthropics/skills](https://github.com/anthropics/skills) | Anthropic 官方技能 |
| `awesome-claude-skills/` | [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) | ComposioHQ 社区技能 |
| `baoyu-skills/` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) | 宝玉的中文技能 |
| `claude-plugins-official/` | [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | Anthropic 官方插件技能 |
| `axton-obsidian-visual-skills/` | [axtonliu/axton-obsidian-visual-skills](https://github.com/axtonliu/axton-obsidian-visual-skills) | Obsidian 可视化技能 |

## 一键脚本

| 脚本 | 说明 |
|------|------|
| `update.sh` / `update.bat` | 从 5 个外部源拉取最新技能 → 合并到本地 → 自动 commit & push |
| `pull.sh` / `pull.bat` | 拉取远端仓库覆盖本地 |
| `push.sh` / `push.bat` | 提交所有变更并推送到远端 |

### 使用方式

- **macOS / Linux**: 运行 `.sh` 脚本
- **Windows**: 双击 `.bat` 文件（需安装 Git）

### update 工作原理

1. 临时 clone 各外部仓库（`--depth 1`，只拉最新）
2. 递归扫描所有含 `SKILL.md` 的目录
3. 按来源前缀复制到本地仓库
4. 自动 git add → commit → push
5. 清理临时文件

macOS 用 `.sh`，Windows 用 `.bat`。
