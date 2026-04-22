# OpenCode CLI 代码审查命令

## 完整命令

```bash
opencode run "对 src/utils/validator.ts 进行全面的代码审查，重点关注安全性和性能问题。请详细分析：1) 安全漏洞（如输入验证、SQL注入、XSS、路径遍历等）；2) 性能问题（如算法复杂度、内存泄漏、不必要的计算等）；3) 最佳实践建议。" -f src/utils/validator.ts --format json > code-review-result.json
```

## 命令说明

### 核心参数解析

| 参数 | 说明 |
|------|------|
| `opencode run` | 非交互模式执行命令，输出结果到 stdout |
| `"对 src/utils/validator.ts..."` | 详细的审查提示词，明确要求安全性和性能分析 |
| `-f src/utils/validator.ts` | 附加要审查的文件 |
| `--format json` | 以 JSON 格式输出结果（方便程序解析） |
| `> code-review-result.json` | 将输出重定向保存到文件 |

### 高级选项（可选）

如果需要更多控制，可以添加以下参数：

```bash
# 指定模型（使用更强的模型进行深度审查）
opencode run "..." -f src/utils/validator.ts --format json -m anthropic/claude-sonnet-4 > result.json

# 显示思考过程（了解分析逻辑）
opencode run "..." -f src/utils/validator.ts --format json --thinking > result.json

# 启用调试日志（排查问题）
opencode run "..." -f src/utils/validator.ts --format json --print-logs --log-level DEBUG 2>debug.log

# 跳过权限确认（仅用于可信的自动化环境，慎用！）
opencode run "..." -f src/utils/validator.ts --format json --dangerously-skip-permissions > result.json
```

## 输出结果说明

`--format json` 会输出原始 SSE 事件流，每行一个 JSON 对象。结果包含：

- `type`: 事件类型（如 `content`, `tool_use`, `tool_result` 等）
- `content`: 模型返回的内容
- `session_id`: 会话 ID

### 使用 jq 提取内容

如果只需要模型返回的文本内容，可以使用 `jq` 处理：

```bash
opencode run "..." -f src/utils/validator.ts --format json | \
  jq -r 'select(.type == "content") | .content[] | .text' > review-text.txt
```

### 提取完整的审查报告

```bash
opencode run "..." -f src/utils/validator.ts --format json | \
  jq -s 'map(select(.type == "content") | .content[] | .text) | join("")' > full-report.txt
```

## 实用示例

### 1. 基础审查
```bash
opencode run "审查这个文件的安全性和性能问题" -f src/utils/validator.ts --format json > result.json
```

### 2. 深度审查（带思考过程）
```bash
opencode run "对 src/utils/validator.ts 进行深度代码审查，包括安全性、性能、可维护性。给出具体的问题代码位置、修复建议和改进方案。" \
  -f src/utils/validator.ts \
  --format json \
  --thinking > result.json
```

### 3. 多文件对比审查
```bash
opencode run "对比 validator.ts 和 validator-v2.ts，分析新版本在安全性和性能上的改进" \
  -f src/utils/validator.ts \
  -f src/utils/validator-v2.ts \
  --format json > comparison.json
```

### 4. 继续会话（多轮审查）
```bash
# 第一轮：基础审查
opencode run "审查 src/utils/validator.ts 的安全性和性能" -f src/utils/validator.ts --format json > result1.json

# 获取 session ID
SESSION_ID=$(jq -r '.session_id' result1.json | head -1)

# 第二轮：继续深入分析
opencode run "针对第3个性能问题，给出具体的优化代码示例" \
  -s $SESSION_ID \
  --format json > result2.json
```

## 注意事项

1. **JSON 格式输出**：`--format json` 返回的是 SSE 事件流，需要根据 `type` 字段过滤需要的内容

2. **权限确认**：如果 opencode 需要读取文件，可能需要权限确认。在自动化环境中可以使用 `--dangerously-skip-permissions`（请确保环境可信）

3. **模型选择**：不指定模型时使用默认配置。建议使用 Claude Sonnet 4 或 GPT-4o 进行代码审查

4. **文件路径**：确保 `src/utils/validator.ts` 相对于执行命令的工作目录是正确的，或使用绝对路径

5. **输出文件**：使用 `>` 重定向时，如果文件已存在会被覆盖。如需追加使用 `>>`

## 故障排查

如果遇到问题，启用调试日志：

```bash
opencode run "..." -f src/utils/validator.ts --format json --print-logs --log-level DEBUG 2>debug.log
```

检查 `debug.log` 查看详细错误信息。
