# CI 自动化修复 Lint 错误与 Token 统计

## 一、在 CI 脚本中自动修复 Lint 错误并提交

### 核心命令

使用 `--dangerously-skip-permissions` 参数可以跳过所有权限确认，让 opencode 自动执行所有工具调用：

```bash
# 基础用法：自动修复所有 lint 错误
opencode run "自动修复所有 lint 错误" --dangerously-skip-permissions

# 指定工作目录
opencode run "自动修复所有 lint 错误" --dangerously-skip-permissions --dir /path/to/project

# JSON 格式输出（方便脚本解析）
opencode run "自动修复所有 lint 错误" --dangerously-skip-permissions --format json

# 指定模型
opencode run "自动修复所有 lint 错误" --dangerously-skip-permissions -m anthropic/claude-sonnet-4
```

### 完整的 CI 脚本示例

#### 方案 1：直接修复并提交

```bash
#!/bin/bash

# 1. 运行 lint 检查
npm run lint

# 如果有 lint 错误，使用 opencode 自动修复
if [ $? -ne 0 ]; then
  echo "发现 lint 错误，正在自动修复..."

  # 使用 opencode 自动修复，跳过权限确认
  opencode run "修复所有 lint 错误" \
    --dangerously-skip-permissions \
    --format json \
    --title "fix-lint-errors" \
    > opencode_output.json

  # 检查 opencode 是否成功
  if [ $? -eq 0 ]; then
    # 修复后再次运行 lint 验证
    npm run lint

    if [ $? -eq 0 ]; then
      # 提交修复
      git add .
      git commit -m "fix: auto-fix lint errors via opencode"
      git push
      echo "✅ Lint 错误已自动修复并提交"
    else
      echo "❌ 自动修复失败，仍存在 lint 错误"
      exit 1
    fi
  else
    echo "❌ opencode 执行失败"
    exit 1
  fi
else
  echo "✅ 无 lint 错误"
fi
```

#### 方案 2：继续之前的会话修复

```bash
#!/bin/bash

# 第一次运行：修复 lint 错误
opencode run "运行 lint 并修复所有错误" \
  --dangerously-skip-permissions \
  --format json \
  > /tmp/opencode_first_run.json

# 从输出中提取 session ID
SESSION_ID=$(cat /tmp/opencode_first_run.json | jq -r '.session_id')

# 第二次运行：继续同一会话，提交修复
opencode run "如果所有 lint 错误已修复，请运行 git add . && git commit -m 'fix: auto-fix lint errors'" \
  --dangerously-skip-permissions \
  --session "$SESSION_ID" \
  --format json
```

#### 方案 3：GitHub Actions 示例

```yaml
name: Auto-fix Lint Errors

on:
  push:
    branches: [main, develop]

jobs:
  lint-and-fix:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Run lint
        id: lint
        run: npm run lint || echo "lint_failed=true" >> $GITHUB_OUTPUT

      - name: Auto-fix with opencode
        if: steps.lint.outputs.lint_failed == 'true'
        run: |
          opencode run "修复所有 lint 错误，确保代码符合项目规范" \
            --dangerously-skip-permissions \
            --format json \
            --dir ${{ github.workspace }}

      - name: Verify fix
        if: steps.lint.outputs.lint_failed == 'true'
        run: npm run lint

      - name: Commit and push
        if: steps.lint.outputs.lint_failed == 'true'
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add .
          git diff --quiet && git diff --staged --quiet || git commit -m "fix: auto-fix lint errors via opencode"
          git push
```

### 重要安全提示

⚠️ **`--dangerously-skip-permissions` 的风险**：
- 会自动批准所有工具调用（包括文件写入、命令执行等）
- 仅在**可信的 CI/自动化环境**中使用
- 不要在不可信的代码库或公共仓库中使用
- 建议配合 `--format json` 使用，便于日志记录和审计

## 二、查看 Token 消耗统计

### 基础命令

```bash
# 查看总体 token 使用量和成本
opencode stats

# 查看最近 7 天的统计
opencode stats --days 7

# 查看最近 30 天的统计
opencode stats --days 30
```

### 高级统计选项

```bash
# 显示模型级统计（前 5 个最常用的模型）
opencode stats --models 5

# 显示前 10 个最常用的工具
opencode stats --tools 10

# 按项目过滤统计
opencode stats --project my-project

# 组合使用：查看某项目最近 7 天的模型统计
opencode stats --days 7 --models 5 --project my-project
```

### 在 CI 中记录 Token 消耗

```bash
#!/bin/bash

# 运行任务
opencode run "执行某个任务" --format json > task_output.json

# 任务完成后查看本次消耗的 token
opencode stats --days 1 > token_stats.txt

# 提取关键信息
TOTAL_TOKENS=$(opencode stats --days 1 | grep "Total tokens" | awk '{print $3}')
TOTAL_COST=$(opencode stats --days 1 | grep "Total cost" | awk '{print $3}')

echo "本次任务消耗: $TOTAL_TOKENS tokens"
echo "本次任务成本: $TOTAL_COST"
```

### 定期统计脚本

```bash
#!/bin/bash

# 每周统计脚本
REPORT_FILE="/tmp/opencode_weekly_report_$(date +%Y%m%d).txt"

{
  echo "=== OpenCode Token 消耗周报 ==="
  echo "报告时间: $(date)"
  echo ""

  echo "【本周统计】"
  opencode stats --days 7

  echo ""
  echo "【本周最常用的 5 个模型】"
  opencode stats --days 7 --models 5

  echo ""
  echo "【本周最常用的 10 个工具】"
  opencode stats --days 7 --tools 10

  echo ""
  echo "【各项目统计】"
  # 需要根据实际情况调整项目名称
  for project in project-a project-b project-c; do
    echo "  - $project:"
    opencode stats --days 7 --project "$project" | grep -E "(Total tokens|Total cost)"
  done

} > "$REPORT_FILE"

echo "周报已生成: $REPORT_FILE"
```

### 实时监控 Token 使用

```bash
#!/bin/bash

# 在任务开始前记录初始统计
INITIAL_STATS=$(opencode stats)
echo "任务开始前的统计:"
echo "$INITIAL_STATS" | grep "Total tokens"

# 执行任务
opencode run "执行某个长时间任务" --format json

# 任务完成后对比统计
FINAL_STATS=$(opencode stats)
echo ""
echo "任务完成后的统计:"
echo "$FINAL_STATS" | grep "Total tokens"

# 计算差异（需要根据实际输出格式调整）
```

## 三、最佳实践

### 1. CI 脚本中的错误处理

```bash
#!/bin/bash

set -e  # 任何命令失败都退出

# 使用 trap 确保即使出错也能记录统计
trap 'echo "任务失败，记录当前统计..."; opencode stats --days 1' ERR

# 执行主任务
opencode run "修复 lint 错误" \
  --dangerously-skip-permissions \
  --format json \
  2>&1 | tee opencode.log

# 验证结果
if [ ${PIPESTATUS[0]} -eq 0 ]; then
  echo "✅ 任务成功"
  opencode stats --days 1 >> opencode.log
else
  echo "❌ 任务失败"
  exit 1
fi
```

### 2. 配合 Git Hooks 使用

```bash
# .git/hooks/pre-commit
#!/bin/bash

# 运行 lint
npm run lint

# 如果失败，尝试自动修复
if [ $? -ne 0 ]; then
  echo "Lint 检测到错误，尝试自动修复..."

  opencode run "修复所有 lint 错误" \
    --dangerously-skip-permissions \
    --format json > /dev/null 2>&1

  # 重新检查
  npm run lint

  if [ $? -eq 0 ]; then
    echo "✅ 已自动修复 lint 错误，请重新提交"
    git add .
    exit 1  # 让用户重新提交
  else
    echo "❌ 无法自动修复，请手动处理"
    exit 1
  fi
fi
```

### 3. 日志和审计

```bash
#!/bin/bash

# 创建日志目录
mkdir -p /var/log/opencode
LOG_FILE="/var/log/opencode/$(date +%Y%m%d_%H%M%S).log"

# 记录完整的 opencode 执行过程
{
  echo "=== 开始时间: $(date) ==="
  echo "命令: $0 $@"
  echo ""

  # 执行 opencode
  opencode run "$@" --dangerously-skip-permissions --format json

  echo ""
  echo "=== Token 统计 ==="
  opencode stats --days 1

  echo ""
  echo "=== 结束时间: $(date) ==="

} 2>&1 | tee "$LOG_FILE"

echo "日志已保存到: $LOG_FILE"
```

## 四、常见问题

### Q1: 为什么加了 `--dangerously-skip-permissions` 还会卡住？

可能原因：
1. opencode 遇到了**显式拒绝**的权限请求（此参数只会自动批准非显式拒绝的请求）
2. 网络问题导致模型请求超时
3. opencode 服务端未正常启动

解决方法：
```bash
# 添加调试日志
opencode run "修复 lint 错误" \
  --dangerously-skip-permissions \
  --print-logs \
  --log-level DEBUG \
  2>&1 | tee debug.log
```

### Q2: 如何确保 opencode 修复后代码能通过 lint？

```bash
# 循环修复直到成功
MAX_ATTEMPTS=3
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  opencode run "修复所有 lint 错误" \
    --dangerously-skip-permissions \
    --format json > /dev/null 2>&1

  npm run lint

  if [ $? -eq 0 ]; then
    echo "✅ Lint 检查通过"
    break
  fi

  ATTEMPT=$((ATTEMPT + 1))
  echo "尝试 $ATTEMPT/$MAX_ATTEMPTS..."
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
  echo "❌ 达到最大尝试次数，自动修复失败"
  exit 1
fi
```

### Q3: 如何限制 opencode 的 token 消耗？

```bash
#!/bin/bash

# 检查今日已使用的 token
TODAY_USAGE=$(opencode stats --days 1 | grep "Total tokens" | awk '{print $3}' | tr -d ',')
MAX_DAILY_TOKENS=100000

if [ "$TODAY_USAGE" -gt "$MAX_DAILY_TOKENS" ]; then
  echo "❌ 今日 token 使用已超限: $TODAY_USAGE > $MAX_DAILY_TOKENS"
  exit 1
fi

# 执行任务
opencode run "修复 lint 错误" --dangerously-skip-permissions
```

## 五、总结

### 关键参数速查

| 场景 | 命令 |
|------|------|
| 自动修复 lint | `opencode run "修复所有 lint 错误" --dangerously-skip-permissions` |
| 查看总统计 | `opencode stats` |
| 查看最近 7 天 | `opencode stats --days 7` |
| 查看模型统计 | `opencode stats --models 5` |
| 查看工具统计 | `opencode stats --tools 10` |

### 安全建议

1. ✅ 在 CI 环境中使用 `--dangerously-skip-permissions`
2. ✅ 配合 `--format json` 便于日志记录
3. ✅ 使用 `--print-logs --log-level DEBUG` 调试问题
4. ❌ 不要在开发机器上使用 `--dangerously-skip-permissions`
5. ❌ 不要在处理不可信代码时使用此参数
