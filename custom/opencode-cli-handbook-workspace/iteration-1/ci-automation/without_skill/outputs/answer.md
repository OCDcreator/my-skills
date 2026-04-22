# OpenCode CI 自动化指南

## 自动修复 lint 错误并提交

在 CI 脚本中使用 OpenCode 自动修复 lint 错误并提交，可以使用以下命令：

```bash
# 基础命令（跳过确认）
opencode fix --yes

# 完整的 CI 流程示例
opencode fix --yes && git add . && git commit -m "fix: auto-fix lint errors" && git push
```

### 常用参数

- `--yes` 或 `-y`: 跳过所有权限确认，自动执行
- `--no-interactive`: 非交互模式，不询问任何问题
- `--auto-fix`: 自动修复可修复的问题

### 环境变量方式

你也可以通过环境变量控制：

```bash
export OPENCODE_AUTO_CONFIRM=true
opencode fix
```

## 查看上次 token 消耗统计

OpenCode 提供多种方式查看 token 使用情况：

### 1. 运行后立即查看

每次 OpenCode 运行结束后，会自动在终端显示统计信息：

```
✓ Task completed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Token Usage:
  Input:  12,345 tokens
  Output: 8,765 tokens
  Total:  21,110 tokens
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 2. 使用统计命令

```bash
# 查看最近一次的统计
opencode stats --last

# 查看历史统计
opencode stats --history

# 查看当前会话的统计
opencode stats --session
```

### 3. 查看统计文件

OpenCode 的统计信息通常保存在：

- **Linux/macOS**: `~/.opencode/stats.json`
- **Windows**: `%USERPROFILE%\.opencode\stats.json`

查看统计文件：

```bash
# Linux/macOS
cat ~/.opencode/stats.json | jq '.last_session'

# Windows PowerShell
Get-Content $env:USERPROFILE\.opencode\stats.json | ConvertFrom-Json | Select-Object -ExpandProperty last_session
```

### 4. 统计文件格式

`stats.json` 文件包含详细的会话历史：

```json
{
  "last_session": {
    "timestamp": "2024-04-22T10:30:00Z",
    "tokens_in": 12345,
    "tokens_out": 8765,
    "total_tokens": 21110,
    "cost": 0.12,
    "commands": [
      {
        "command": "fix",
        "tokens_in": 5000,
        "tokens_out": 3000
      }
    ]
  },
  "history": [...]
}
```

## CI 完整示例

```yaml
# GitHub Actions 示例
name: Auto Fix Lint
on: [push]

jobs:
  lint-fix:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install OpenCode
        run: npm install -g @opencode/cli
      
      - name: Auto fix lint errors
        env:
          OPENCODE_AUTO_CONFIRM: true
        run: |
          opencode fix --yes
          
      - name: Commit and push
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add .
          git diff --quiet && git diff --staged --quiet || git commit -m "fix: auto-fix lint errors"
          git push
```

## 注意事项

1. **API Key 配置**: 确保在 CI 环境中设置了 `OPENCODE_API_KEY` 环境变量
2. **权限控制**: 使用 `--yes` 时要确保操作是安全的，建议先在测试环境验证
3. **成本监控**: token 消耗会累积，建议定期查看历史统计以控制成本
4. **日志保存**: 可以将统计信息输出到文件以便后续分析

```bash
# 保存本次运行的统计
opencode fix --yes 2>&1 | tee opencode_run.log
```
