# OpenCode 命令行代码审查指南

## 审查 TypeScript 函数的安全性和性能

### 方法一：交互式审查（推荐）

```bash
opencode review src/utils/validator.ts
```

然后在交互式提示中输入：
```
请审查这个文件的安全性和性能问题，并以 JSON 格式输出结果
```

### 方法二：直接命令（如果支持）

```bash
opencode review src/utils/validator.ts --format json --check security,performance
```

## 输出保存方法

### 选项 1：命令行重定向

```bash
opencode review src/utils/validator.ts --format json > review-results.json
```

### 选项 2：在交互式审查后保存

1. 运行审查命令获取 JSON 输出
2. 手动复制 JSON 内容到文件：

```bash
# 创建输出文件
echo "[]" > review-results.json

# 使用你喜欢的编辑器打开并粘贴结果
notepad review-results.json
# 或
code review-results.json
```

## 完整工作流程示例

```bash
# 1. 进入项目目录
cd C:\Users\lt\Desktop\Write\open-source-project\AI-tools-agents

# 2. 运行代码审查
opencode review src/utils/validator.ts

# 在交互式提示中输入：
# "请审查这个文件的安全性和性能问题，重点关注：
# - SQL 注入风险
# - XSS 漏洞
# - 类型安全
# - 内存泄漏
# - 性能瓶颈
# - 代码效率
# 请以 JSON 格式输出结果，包含以下字段：
# {
#   'file': '文件路径',
#   'security_issues': [],
#   'performance_issues': [],
#   'recommendations': []
# }"

# 3. 将 JSON 输出保存到文件
opencode review src/utils/validator.ts --format json > code-review-results.json
```

## 预期的 JSON 输出格式

```json
{
  "file": "src/utils/validator.ts",
  "timestamp": "2025-01-15T10:30:00Z",
  "security_issues": [
    {
      "severity": "high|medium|low",
      "type": "issue_type",
      "description": "问题描述",
      "line": 42,
      "suggestion": "修复建议"
    }
  ],
  "performance_issues": [
    {
      "severity": "high|medium|low",
      "type": "issue_type",
      "description": "问题描述",
      "line": 56,
      "suggestion": "优化建议"
    }
  ],
  "recommendations": [
    "改进建议 1",
    "改进建议 2"
  ]
}
```

## 其他有用的选项

```bash
# 查看帮助
opencode review --help

# 指定审查的详细程度
opencode review src/utils/validator.ts --verbose

# 只检查安全性
opencode review src/utils/validator.ts --check security

# 只检查性能
opencode review src/utils/validator.ts --check performance

# 指定输出文件路径
opencode review src/utils/validator.ts --output ./outputs/review.json
```

## 注意事项

1. **检查 opencode 版本**：确保你使用的是支持代码审查功能的版本
2. **文件路径**：确保 `src/utils/validator.ts` 文件存在于当前目录
3. **权限**：确保有写入输出文件的权限
4. **JSON 格式**：如果命令不支持直接 JSON 输出，可以在交互式提示中明确要求 JSON 格式

## 验证命令可用性

```bash
# 查看 opencode 可用命令
opencode --help

# 查看审查命令的详细选项
opencode review --help
```

## 故障排除

如果遇到问题：

1. **命令不存在**：检查 opencode 是否正确安装
2. **JSON 输出不支持**：使用交互式方式，然后在提示中要求 JSON 格式
3. **文件未找到**：检查文件路径是否正确
4. **权限错误**：确保有写入输出文件的权限
