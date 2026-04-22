---
name: opencode-cli-handbook
description: |
  OpenCode CLI 速查手册 —— 让任意 agent 快速掌握 opencode 命令行的调用方式，
  用于代码审查、代码辅助、调试诊断、会话管理、模型切换等自动化场景。

  触发场景（满足任一即应加载此技能）：
  - agent 需要通过命令行调用 opencode 来完成代码审查、代码生成、bug 修复
  - 用户说"用 opencode run"、"opencode CLI"、"opencode 命令行"、"非交互模式"
  - 需要在脚本/CI/子 agent 中调用 opencode（不需要 TUI）
  - 用户问"opencode 怎么跑一条命令"、"怎么用 opencode 审查代码"
  - 需要 attach 到远程 opencode server 执行任务
  - 需要查看/管理 opencode 的 session、provider、model、MCP、agent
  - 需要用 opencode debug 诊断配置、技能、路径等问题
  - 需要 opencode serve 启动 headless 服务器供 SDK 调用
---

# OpenCode CLI Handbook

> **版本基准**: v1.14.20

这个技能帮你快速查阅 OpenCode CLI 的所有命令、参数和使用模式。
你不需要理解源码 —— 只需要知道**该敲什么命令**。

## 核心概念

OpenCode 有两种运行模式：
- **TUI 模式**（默认）：启动交互式终端 UI，适合人类使用
- **`run` 模式**：非交互式执行，输出结果到 stdout，**agent 应该使用这种模式**

## 一、非交互执行（agent 最常用）

### `opencode run` — 一次性执行命令

这是 agent 调用 opencode 的主要方式。它会启动一个后台 opencode server，
发送消息，流式输出结果，然后自动关闭。

```bash
# 基础用法：发送消息并获取回复
opencode run "解释这段代码的作用"

# 审查代码（附带文件）
opencode run "审查这个文件的安全性和性能问题" -f src/api/auth.ts

# 审查多个文件
opencode run "对比这两个实现哪个更好" -f old_impl.ts -f new_impl.ts

# 指定模型
opencode run "优化这个函数" -m anthropic/claude-sonnet-4 -f utils.ts

# JSON 输出（方便程序解析）
opencode run "列出这个项目的架构问题" --format json

# 继续上一次会话（保持上下文）
opencode run "继续修复，关注第3个问题" -c

# 继续特定会话
opencode run "补充单元测试" -s ses_abc123

# Fork 一个会话（不影响原会话）
opencode run "试试另一种方案" -s ses_abc123 --fork

# 跳过权限确认（自动化场景，慎用）
opencode run "自动修复所有 lint 错误" --dangerously-skip-permissions

# 指定工作目录
opencode run "分析项目依赖" --dir /path/to/project

# 设置会话标题
opencode run "重构认证模块" --title "auth-refactor"

# 显示 thinking 过程
opencode run "为什么这里要用 mutex？" --thinking
```

### `run` 完整参数表

| 参数 | 短写 | 类型 | 说明 |
|---|---|---|---|
| `message` | — | `[message..]` 位置参数 | 要发送的消息内容（可多个，空格拼接） |
| `--format` | — | `default\|json` | 输出格式。`json` 返回原始 JSON 事件流，方便程序解析 |
| `--model` | `-m` | `provider/model` | 指定模型，如 `anthropic/claude-sonnet-4`、`openai/gpt-4o` |
| `--agent` | — | `string` | 指定 agent（如 `build`、`code-reviewer`） |
| `--file` | `-f` | `array` | 附带文件路径（可多次使用） |
| `--continue` | `-c` | `boolean` | 继续最近的会话 |
| `--session` | `-s` | `string` | 继续指定的会话 ID |
| `--fork` | — | `boolean` | Fork 会话（需配合 `-c` 或 `-s` 使用） |
| `--share` | — | `boolean` | 完成后分享会话 |
| `--title` | — | `string` | 设置会话标题 |
| `--attach` | — | `string` | 附加到运行中的 server（如 `http://localhost:4096`） |
| `--password` | `-p` | `string` | Basic auth 密码 |
| `--dir` | — | `string` | 工作目录 |
| `--port` | — | `number` | 本地 server 端口（默认随机） |
| `--variant` | — | `string` | 模型变体（reasoning effort: `high`、`max`、`minimal`） |
| `--thinking` | — | `boolean` | 显示 thinking 块 |
| `--command` | — | `string` | 用 message 作为参数，用此参数指定命令 |
| `--dangerously-skip-permissions` | — | `boolean` | 自动批准非显式拒绝的权限（**危险！**仅 CI/自动化用） |
| `--pure` | — | `boolean` | 不加载外部插件 |
| `--print-logs` | — | `boolean` | 将日志输出到 stderr |
| `--log-level` | — | `string` | 日志级别：`DEBUG`、`INFO`、`WARN`、`ERROR` |

### Stdin/Pipe 输入

`opencode run` 会自动检测 stdin，如果不是 TTY 就读取内容附加到消息后面：

```bash
# 管道传入
echo "fix the bug" | opencode run

# 从文件传入
cat prompt.txt | opencode run

# 配合其他命令
git diff | opencode run "review these changes"
```

### `--file` 数组选项的 `--` 分隔符

`-f` / `--file` 是数组选项（可多次使用），`[message..]` 也是可变位置参数。
两者都是"吃后面参数"的类型，容易互相干扰。在脚本中建议用 `--` 隔开：

```bash
# ✅ 推荐（脚本/自动化）：选项在前，-- 在 prompt 前
opencode run -f src/main.ts -f src/utils.ts -- "审查这两个文件"

# ✅ 也可以正常工作（交互式简单用法）
opencode run "审查这个文件" -f src/main.ts

# ❌ 错误：-- 放在前面会让 -f 被当成普通文本而非选项
opencode run -- "审查这个文件" -f src/main.ts
```

`--` 的含义是"此后的内容不再解析为选项"。所以它必须放在**所有选项之后、prompt 之前**。

### Agent 场景速查

#### 代码审查
```bash
# 审查单个文件
opencode run "对这个文件做全面的代码审查，包括安全性、性能、可维护性" -f src/api/handler.ts --format json

# 审查 PR 变更
opencode run "审查最近的 git 变更，指出潜在问题" --format json

# 审查特定 commit
opencode run "审查 commit abc1234 的变更质量和潜在问题" --format json
```

#### 代码辅助
```bash
# 解释代码
opencode run "解释 src/auth/jwt.ts 的完整工作流程" -f src/auth/jwt.ts

# 生成代码
opencode run "为 UserService 类生成 CRUD 方法的单元测试" -f src/services/UserService.ts

# 重构建议
opencode run "分析这个模块的耦合度，给出重构方案" -f src/modules/payment.ts
```

#### Bug 修复
```bash
# 诊断问题
opencode run "这个函数在高并发下会出现什么问题？给出修复方案" -f src/cache/manager.ts

# 继续修复（保持上下文）
opencode run "修复所有 type error" -c
```

#### 远程附加（连接已有 server）
```bash
# 附加到远程 server 执行任务
opencode run "检查服务状态" --attach http://192.168.1.100:4096 --password mypass

# 在远程 server 上审查代码
opencode run "审查 src/ 下的所有文件" --attach http://localhost:4096 --dir /remote/project
```

## 二、服务器模式

### `opencode serve` — 启动 headless server

启动 HTTP API 服务器，不打开 TUI。供 SDK 或远程调用使用。

```bash
# 默认启动（随机端口）
opencode serve

# 指定端口和主机
opencode serve --port 4096 --hostname 127.0.0.1

# 允许远程访问
opencode serve --port 4096 --hostname 0.0.0.0

# 启用 mDNS 服务发现
opencode serve --mdns

# 添加 CORS 允许域名
opencode serve --port 4096 --cors http://localhost:3000 --cors http://myapp.com
```

### `opencode web` — 启动 server 并打开 Web UI

```bash
opencode web    # 启动 server 并打开浏览器
```

### `opencode attach <url>` — 附加到运行中的 server

```bash
opencode attach http://localhost:4096    # 连接已有 server 的 TUI
```

## 三、会话管理

```bash
# 列出所有会话
opencode session list

# 列出最近 10 个会话（JSON 格式）
opencode session list -n 10 --format json

# 删除会话
opencode session delete ses_abc123

# 导出会话为 JSON
opencode export ses_abc123

# 导出时脱敏
opencode export ses_abc123 --sanitize

# 导入会话
opencode import session_data.json
opencode import https://example.com/session.json
```

## 四、模型和 Provider

```bash
# 列出所有可用模型
opencode models

# 列出特定 provider 的模型
opencode models anthropic

# 详细信息（包含成本等元数据）
opencode models --verbose

# 刷新模型缓存
opencode models --refresh

# 列出 providers 和凭证
opencode providers list

# 登录 provider
opencode providers login

# 登出
opencode providers logout
```

## 五、Agent 管理

```bash
# 列出所有 agent
opencode agent list

# 创建自定义 agent（可指定所有参数以实现非交互）
opencode agent create --path ./agents --description "Code reviewer agent" --mode primary --tools bash,read,write,edit,glob,grep --model anthropic/claude-sonnet-4
```

### `agent create` 参数

| 参数 | 类型 | 说明 |
|---|---|---|
| `--path` | `string` | 生成 agent 文件的目录路径 |
| `--description` | `string` | Agent 功能描述 |
| `--mode` | `all\|primary\|subagent` | Agent 模式 |
| `--tools` | `string` | 逗号分隔的工具列表 |
| `--model` | `-m` `string` | 使用的模型 |

## 六、MCP 管理

```bash
# 添加 MCP server
opencode mcp add

# 列出所有 MCP server 及状态
opencode mcp list

# OAuth 认证
opencode mcp auth [name]

# 列出支持 OAuth 的 MCP server
opencode mcp auth list

# 登出 OAuth
opencode mcp logout [name]

# 调试 MCP 连接
opencode mcp debug <name>
```

## 七、调试与诊断

```bash
# 查看已解析的完整配置
opencode debug config

# 列出所有可用技能
opencode debug skill

# 查看全局路径（数据、配置、缓存、状态）
opencode debug paths

# 查看所有已知项目
opencode debug scrap

# 查看 agent 配置详情
opencode debug agent build

# 直接执行 agent 工具（用于测试）
opencode debug agent build --tool bash --params '{"command":"echo hello"}'

# LSP 调试
opencode debug lsp

# ripgrep 调试工具
opencode debug rg files --query "*.ts" --limit 20
opencode debug rg search "TODO" --glob "*.ts"
opencode debug rg tree --limit 50

# 文件系统调试工具
opencode debug file list src/
opencode debug file read src/main.ts
opencode debug file status
opencode debug file search "config"
opencode debug file tree

# 快照调试
opencode debug snapshot track
opencode debug snapshot patch <hash>
opencode debug snapshot diff <hash>
```

## 八、统计

```bash
# 查看总 token 使用量和成本
opencode stats

# 最近 7 天的统计
opencode stats --days 7

# 显示模型级统计（前 5 个模型）
opencode stats --models 5

# 按项目过滤
opencode stats --project my-project

# 显示 top 10 工具使用统计
opencode stats --tools 10
```

## 九、数据库

```bash
# 进入交互式 SQLite shell
opencode db

# 执行 SQL 查询
opencode db "SELECT * FROM session LIMIT 10"

# JSON 格式输出
opencode db "SELECT id, title FROM session" --format json

# 查看数据库路径
opencode db path

# 迁移 JSON 数据到 SQLite
opencode db migrate
```

## 十、GitHub 集成

```bash
# 安装 GitHub agent
opencode github install

# 运行 GitHub agent
opencode github run

# 拉取 PR 并启动 opencode
opencode pr 123
```

## 十一、插件管理

```bash
# 安装插件
opencode plugin @opencode/plugin-example

# 全局安装
opencode plugin @opencode/plugin-example --global

# 强制替换已有版本
opencode plugin @opencode/plugin-example --force
```

## 十二、其他命令

```bash
# 默认命令：启动 TUI（交互式终端 UI，适合人类使用）
opencode                # 在当前目录启动
opencode /path/to/project  # 在指定目录启动
opencode -c             # 继续上次会话
opencode -m anthropic/claude-sonnet-4  # 指定模型启动

# 生成 shell 补全脚本
opencode completion

# 升级 opencode
opencode upgrade
opencode upgrade 1.15.0    # 升级到指定版本

# 卸载 opencode
opencode uninstall

# 查看 ACP server
opencode acp

# 纯净模式（不加载插件）— 可用于任何命令
opencode run "hello" --pure
```

## 全局选项

以下选项适用于**大多数命令**（少数命令如 `session list`、`export` 等仅支持基础选项）：

| 选项 | 说明 | 适用范围 |
|---|---|---|
| `--help` / `-h` | 显示帮助 | 所有命令 |
| `--version` / `-v` | 显示版本号 | 所有命令 |
| `--print-logs` | 将日志输出到 stderr | 所有命令 |
| `--log-level` | 日志级别：`DEBUG`、`INFO`、`WARN`、`ERROR` | 所有命令 |
| `--pure` | 不加载外部插件 | 所有命令 |

以下选项仅适用于 `run`、`serve`、`web`、`attach`、TUI 等部分命令：

| 选项 | 说明 | 主要命令 |
|---|---|---|
| `--port` | 指定端口 | `serve`、`web`、`run` |
| `--hostname` | 指定主机名（默认 `127.0.0.1`） | `serve`、`web` |
| `--mdns` | 启用 mDNS 服务发现 | `serve`、`web` |
| `--mdns-domain` | 自定义 mDNS 域名 | `serve`、`web` |
| `--cors` | CORS 允许域名 | `serve`、`web` |
| `-m` / `--model` | 指定模型 `provider/model` | `run`、TUI |
| `-c` / `--continue` | 继续上次会话 | `run`、`attach`、TUI |
| `-s` / `--session` | 继续指定会话 | `run`、`attach`、TUI |
| `--fork` | Fork 会话 | `run`、`attach`、TUI |
| `--prompt` | 使用指定 prompt | TUI |
| `--agent` | 指定 agent | `run`、TUI |

## 实用技巧

### 1. `--format json` 是自动化的关键
`json` 模式输出原始 SSE 事件流，每行一个 JSON 对象。程序可以用 `jq` 或 JSON parser 提取需要的内容。

### 2. 会话连续性
用 `-c` 继续上次会话，或 `-s <id>` 继续指定会话。这让多轮对话成为可能：
```bash
# 第一轮
opencode run "分析这个项目的测试覆盖率" --format json > result1.json
# 第二轮（继续同一会话，注意从结果中获取 session ID）
opencode run "为覆盖率低于 50% 的模块生成测试" -s <session-id> --format json
```

### 3. 文件附加
`-f` 可以多次使用来附加多个文件。OpenCode 会将文件内容作为上下文发送给模型。

### 4. 安全注意事项
- `--dangerously-skip-permissions` 会自动批准未被显式拒绝（deny）的权限请求，但不等于"批准所有"——被 `deny` 规则拦截的操作仍然会被阻止。仅在可信的 CI/自动化环境中使用
- `--format json` 只改变输出格式为 JSON，不会绕过权限提示；如果需要无交互运行，需要配合 `--dangerously-skip-permissions`

### 5. 模型选择
- 不指定模型时使用 opencode.json 中的默认模型
- `-m provider/model` 格式选择特定模型
- `--variant` 调整推理力度（部分 provider 支持）

### 6. 调试输出
遇到问题时：
```bash
opencode run "test" --print-logs --log-level DEBUG 2>debug.log
```

## 命令速查表

| 场景 | 命令 |
|---|---|
| 一次性执行 | `opencode run "消息"` |
| 附带文件 | `opencode run "消息" -f file.ts` |
| 指定模型 | `opencode run "消息" -m provider/model` |
| JSON 输出 | `opencode run "消息" --format json` |
| 继续会话 | `opencode run "消息" -c` |
| 连接远程 | `opencode run "消息" --attach http://host:port` |
| 启动 server | `opencode serve --port 4096` |
| 查看配置 | `opencode debug config` |
| 查看模型 | `opencode models` |
| 查看统计 | `opencode stats` |
| 列出会话 | `opencode session list` |
| 导出会话 | `opencode export <id>` |
| 查看技能 | `opencode debug skill` |
| 查看路径 | `opencode debug paths` |
