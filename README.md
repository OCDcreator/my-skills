# my-skills

个人 AI 技能集合，用于扩展 Hermes Agent 的能力。

## 目录结构

```
my-skills/
├── devops/                        # 自有技能
│   └── syncthing/                 # Syncthing 同步排障
├── external/                      # 外部技能（submodule）
│   ├── awesome-claude-skills/     # ComposioHQ
│   ├── baoyu-skills/              # JimLiu
│   ├── claude-plugins-official/   # Anthropic
│   ├── anthropics-skills/         # Anthropic
│   └── axton-obsidian-visual-skills/  # axtonliu
├── pull.sh / pull.bat             # 一键拉取远端覆盖本地
├── push.sh / push.bat             # 一键提交推送
├── update.sh / update.bat         # 一键更新所有外部 submodule
└── .gitmodules
```

## 自有技能

| 技能 | 说明 |
|------|------|
| [syncthing](devops/syncthing/) | Syncthing 同步排障与诊断 |

## 外部技能来源

| 仓库 | 来源 |
|------|------|
| [awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) | ComposioHQ |
| [baoyu-skills](https://github.com/JimLiu/baoyu-skills) | JimLiu |
| [claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | Anthropic |
| [anthropics-skills](https://github.com/anthropics/skills) | Anthropic |
| [axton-obsidian-visual-skills](https://github.com/axtonliu/axton-obsidian-visual-skills) | axtonliu |

## 一键脚本

| 脚本 | 说明 |
|------|------|
| `pull.sh` / `pull.bat` | 拉取远端仓库覆盖本地 + 更新 submodule |
| `push.sh` / `push.bat` | 提交所有变更并推送到远端 |
| `update.sh` / `update.bat` | 拉取所有外部 submodule 最新并推送 |

macOS 用 `.sh`，Windows 双击 `.bat`。
