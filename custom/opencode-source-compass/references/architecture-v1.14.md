# Architecture Deep Dive — OpenCode v1.14.19

> 源码根: `packages/opencode/`
> 分支: `dev` | 版本: v1.14.19

## 1. 整体数据流

```
┌───────────────────────────────────────────────────────────────┐
│  外部客户端 (插件 / CLI / TUI)                                  │
│  ┌─────────┐  ┌─────────┐  ┌──────────────┐                   │
│  │  SDK    │  │  CLI    │  │  ACP (Zed)   │                   │
│  │ HTTP    │  │ 直接调用 │  │  stdio       │                   │
│  └────┬────┘  └────┬────┘  └──────┬───────┘                   │
│       │            │              │                            │
└───────┼────────────┼──────────────┼────────────────────────────┘
        │            │              │
        ▼            ▼              ▼
┌───────────────────────────────────────────────────────────────┐
│  入口层                                                        │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │  HTTP Server     │  │  CLI (yargs)     │                    │
│  │  src/server/     │  │  src/cli/cmd/    │                    │
│  │  :4096           │  │                  │                    │
│  └────────┬─────────┘  └────────┬─────────┘                    │
│           │                      │                             │
│           │  middleware chain:   │                             │
│           │  Auth → Logger →     │                             │
│           │  Compression →       │                             │
│           │  CORS → InstanceMW   │                             │
│           │  → Fence             │                             │
│           │                      │                             │
└───────────┼──────────────────────┼─────────────────────────────┘
            │                      │
            ▼                      ▼
┌───────────────────────────────────────────────────────────────┐
│  Effect Service 层 (Context.Service)                           │
│                                                               │
│  所有服务通过 Effect 依赖注入，按 Instance 隔离                  │
│                                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ Session  │ │ Provider │ │   MCP    │ │   LSP    │          │
│  │ Service  │ │ Service  │ │ Service  │ │ Service  │          │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘          │
│       │            │            │            │                │
│  ┌────┴────┐ ┌─────┴────┐ ┌────┴─────┐ ┌────┴─────┐          │
│  │ Prompt  │ │ Agent    │ │   Tool   │ │    Bus   │          │
│  │ Chain   │ │ Service  │ │ Registry │ │ Service  │          │
│  └────┬────┘ └──────────┘ └──────────┘ └──────────┘          │
│       │                                                      │
│  ┌────┴────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │   LLM   │ │Storage   │ │Permission│ │  Auth    │          │
│  │ Adapter │ │(SQLite)  │ │ Evaluator│ │ Manager  │          │
│  └─────────┘ └──────────┘ └──────────┘ └──────────┘          │
│                                                               │
└───────────────────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────┐
│  基础设施层                                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ SQLite   │ │ models.dev│ │  @ai-sdk │ │  Child   │          │
│  │ (Drizzle)│ │ (模型目录)│ │  (LLM)   │ │ Process  │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
└───────────────────────────────────────────────────────────────┘
```

## 2. Instance 生命周期

Instance 是 OpenCode 的核心隔离单元。每个工作目录对应一个 Instance。

```
创建阶段:
  opencode serve / SDK 连接
    → InstanceMiddleware 拦截请求
      → 读取 x-opencode-directory header
        → InstanceState.get(directory)
          → 如果已存在 → 直接使用
          → 如果不存在 → InstanceState.make(directory)
            → 创建 Effect Scope
            → 初始化所有 Service (Session, Provider, MCP, LSP, Bus, ...)
            → 调用各 Service.init()
            → 注册到 GlobalBus

运行阶段:
  HTTP 请求 → InstanceMiddleware → 路由处理 → Service 调用
  Bus.publish(event) → PubSub 分发 → SSE /event 推送

销毁阶段:
  client.instance.dispose()
    → POST /instance/dispose
      → Effect Scope 关闭
        → 所有 Service 的 Finalizer 执行
          → Bus.publish(server.instance.disposed)
          → 关闭 PubSub
          → 停止 MCP 连接
          → 停止 LSP 进程
          → 关闭 SQLite 连接
        → InstanceState 缓存清除
```

### 关键文件

| 文件 | 职责 |
|---|---|
| `src/project/instance.ts` | Instance 定义、创建、绑定 |
| `src/effect/instance-state.ts` | InstanceState (ScopedCache, 按目录隔离) |
| `src/server/routes/instance/middleware.ts` | HTTP 中间件, 从 header 解析 directory |
| `src/project/bootstrap.ts` | 启动时初始化所有 Service |

## 3. Effect Service 依赖图

```
Bus.Service (事件总线)
  ↑ 被 22+ 个服务依赖

Session.Service (会话管理)
  → 依赖: Bus, Storage, Provider, Agent, Permission, ToolRegistry

Provider.Service (模型提供者)
  → 依赖: Bus, Storage, Config
  → 外部: models.dev API, @ai-sdk/*

MCP.Service (MCP 客户端)
  → 依赖: Bus, Config, ToolRegistry
  → 外部: stdio/HTTP MCP 传输

LSP.Service (LSP 客户端)
  → 依赖: Bus, Config
  → 外部: language server 进程

ToolRegistry (工具注册表)
  → 依赖: Bus, Config, Permission
  → 包含: bash, read, write, edit, grep, glob, lsp, webfetch, ...

Permission.Service (权限评估)
  → 依赖: Config, Bus
  → 使用: glob 匹配 allow/ask/deny 规则

Storage.Service (SQLite)
  → 依赖: 无 (底层服务)
  → 使用: Drizzle ORM

Config.Service (配置)
  → 依赖: 无
  → 读取: opencode.json, .env
```

### Effect 模式

OpenCode 使用 Effect v4 的 Context.Service 模式：

```typescript
// 标准服务定义模式
export class Service extends Context.Service<Service, Interface>()("@opencode/Bus") {}
export const layer = Layer.effect(Service, Effect.gen(function* () { ... }))
export const defaultLayer = layer.pipe(...)

// 两种运行方式:
// 1. InstanceState (按目录隔离) — 大部分核心服务
// 2. makeRuntime (全局共享) — Bus, Storage
```

### Instance.bind — ALS 上下文传递

对于原生回调（node-pty、@parcel/watcher 等），使用 `Instance.bind()` 传递 AsyncLocalStorage 上下文：

```typescript
const cb = Instance.bind((err, evts) => {
  Bus.publish(MyEvent, { ... })
})
nativeAddon.subscribe(dir, cb)
```

## 4. 事件总线事件目录

### 全局事件 (GlobalBus → `/global/event`)

| 事件类型 | 来源文件 | 触发条件 |
|---|---|---|
| `global.disposed` | `src/server/routes/global.ts` | 全局服务销毁 |
| `server.connected` | `src/server/event.ts` | SSE 客户端连接 |
| `server.instance.disposed` | `src/bus/index.ts` | Instance 销毁 |

### Instance 级事件 (Bus → `/event`)

| 事件类型 | 来源文件 | 触发条件 | Payload |
|---|---|---|---|
| **Session** | | | |
| `session.diff` | `src/session/session.ts` | 会话数据变化 | `{ id, ... }` |
| `session.error` | `src/session/session.ts` | 会话出错 | `{ id, error }` |
| `session.status` | `src/session/status.ts` | 会话状态变化 | `{ id, status }` |
| `session.idle` | `src/session/status.ts` | 会话空闲 | `{ id }` |
| `session.compacted` | `src/session/compaction.ts` | 会话压缩完成 | `{ id }` |
| **Message** | | | |
| `message.part_delta` | `src/session/message-v2.ts` | 消息 Part 流式更新 | `{ sessionID, messageID, part }` |
| **Todo** | | | |
| `todo.updated` | `src/session/todo.ts` | Todo 列表变化 | `{ sessionID, todos }` |
| **Permission** | | | |
| `permission.asked` | `src/permission/index.ts` | 需要用户授权 | `Request.zod` |
| `permission.replied` | `src/permission/index.ts` | 用户回复授权 | `Replied` |
| **Provider** | | | |
| (通过 session.diff 间接) | | | |
| **MCP** | | | |
| `mcp.tools_changed` | `src/mcp/index.ts` | MCP 工具列表变化 | `{ name }` |
| `mcp.browser_open_failed` | `src/mcp/index.ts` | OAuth 浏览器打开失败 | `{ name }` |
| **LSP** | | | |
| `lsp.updated` | `src/lsp/lsp.ts` | LSP 状态变化 | `{}` |
| `lsp.diagnostics` | `src/lsp/client.ts` | 诊断信息更新 | `{ uri, diagnostics }` |
| **File** | | | |
| `file.edited` | `src/file/index.ts` | 文件被编辑 | `{ path }` |
| `file.watcher.updated` | `src/file/watcher.ts` | 文件监控变化 | `{ path, type }` |
| **Pty** | | | |
| `pty.created` | `src/pty/index.ts` | PTY 创建 | `{ info }` |
| `pty.updated` | `src/pty/index.ts` | PTY 更新 | `{ info }` |
| `pty.exited` | `src/pty/index.ts` | PTY 退出 | `{ id, exitCode }` |
| `pty.deleted` | `src/pty/index.ts` | PTY 删除 | `{ id }` |
| **Project** | | | |
| `project.updated` | `src/project/project.ts` | 项目信息更新 | `Info.zod` |
| `project.branch_updated` | `src/project/vcs.ts` | Git 分支切换 | `{ branch }` |
| **Question** | | | |
| `question.asked` | `src/question/index.ts` | 问题提出 | `Request.zod` |
| `question.replied` | `src/question/index.ts` | 问题回复 | `Replied` |
| `question.rejected` | `src/question/index.ts` | 问题拒绝 | `Rejected` |
| **Command** | | | |
| `command.executed` | `src/command/index.ts` | 命令执行 | `{ command }` |
| **Installation** | | | |
| `installation.updated` | `src/installation/index.ts` | 安装信息更新 | `{}` |
| `installation.update_available` | `src/installation/index.ts` | 新版本可用 | `{ version }` |
| **IDE** | | | |
| `ide.installed` | `src/ide/index.ts` | IDE 插件安装完成 | `{}` |
| **Worktree** | | | |
| `worktree.ready` | `src/worktree/index.ts` | Worktree 准备就绪 | `{ path }` |
| `worktree.failed` | `src/worktree/index.ts` | Worktree 创建失败 | `{ error }` |
| **Workspace** | | | |
| `workspace.ready` | `src/control-plane/workspace.ts` | Workspace 就绪 | `{ id }` |
| `workspace.failed` | `src/control-plane/workspace.ts` | Workspace 失败 | `{ error }` |
| `workspace.restore` | `src/control-plane/workspace.ts` | Workspace 恢复 | `Restore` |
| `workspace.status` | `src/control-plane/workspace.ts` | Workspace 状态 | `ConnectionStatus` |
| **TUI** | | | |
| `tui.prompt.append` | `src/cli/cmd/tui/event.ts` | TUI 提示追加 | `{ text }` |
| `tui.command.execute` | `src/cli/cmd/tui/event.ts` | TUI 命令执行 | `{ command, args }` |
| `tui.toast.show` | `src/cli/cmd/tui/event.ts` | TUI Toast 显示 | `{ message, type }` |
| `tui.session.select` | `src/cli/cmd/tui/event.ts` | TUI 会话选择 | `{ id }` |

### 事件传递机制

```
Service 层:
  Bus.publish(EventDefinition, payload)
    → PubSub (Effect, 按 type 分发)
      → Bus.Service 内部 PubSub
        → GlobalBus.emit("event", { directory, project, workspace, payload })
          → SSE /global/event 推送

Instance 级 SSE:
  Bus.subscribe(EventDefinition) → Stream<Payload>
    → PubSub 订阅
      → src/server/routes/instance/event.ts → SSE /event 推送

全局 SSE:
  src/server/routes/global.ts → GlobalBus.on("event", ...)
    → SSE /global/event 推送
```

## 5. 会话处理链（核心路径）

这是最复杂的路径——从用户发消息到 LLM 响应的完整链路。

```
1. SDK 调用
   client.session.prompt({ id, content })
     → POST /session/{id}/message

2. 路由层 (session.ts)
   → 解析请求体
   → 调用 Prompt 服务

3. Prompt 处理 (prompt.ts)
   → 加载 Session (session.ts)
   → 获取 Provider/Model (provider.ts)
   → 构建消息历史 (message-v2.ts)
     → 包含: system prompt + user/assistant 消息
     → 可能触发: compaction (压缩长历史)
   → 获取工具列表 (registry.ts)
     → 内置工具 + MCP 工具
   → 调用 LLM (llm.ts)

4. LLM 调用 (llm.ts)
   → 选择 Provider SDK (@ai-sdk/*)
   → 流式调用
   → 每个 chunk:
     → Bus.publish(message.part_delta)
     → SSE 推送到客户端

5. 工具调用循环
   → LLM 返回 tool_call
     → Permission 评估 (permission/index.ts)
       → 如果 need approval:
         → Bus.publish(permission.asked)
         → 等待 SSE 回复: POST /session/{id}/permissions/{pid}
       → 如果 auto-approved:
         → 直接执行
     → 执行工具 (tool/*.ts)
     → 将工具结果追加到消息
     → 再次调用 LLM
   → 循环直到 LLM 不再调用工具

6. 完成
   → Bus.publish(session.idle)
   → 更新 Session 状态
   → SSE 推送最终状态
```

## 6. 错误传播链

```
SDK 调用失败:
  client.session.prompt() → HTTP Error
    → 检查 HTTP 状态码:
      400: 请求参数错误 → 检查 SDK 方法参数
      404: 路由不存在 → 版本不匹配？检查 URL
      500: 服务端错误 → 检查 OpenCode 日志

服务端错误:
  Effect Service 抛出异常
    → Effect 捕获 (Effect.catchAll / Effect.catchTag)
    → 转为 HTTP 错误响应
    → 同时: Bus.publish(session.error)

Effect 层错误模式:
  Schema.TaggedErrorClass → 类型化错误
  yield* new MyError(...) → 直接失败
  Effect.fn("Domain.method") → 命名追踪
```

## 7. 存储层

```
SQLite (via Drizzle ORM)
  位置: ~/.local/share/opencode/opencode.db (或项目 .opencode/ 下)

  主要表:
  - session: 会话元数据
  - message: 消息存储 (v2 schema)
  - part: 消息 Part (text/tool-call/tool-result)
  - auth: 认证凭据
  - config: 配置存储

  Schema 文件: src/**/*.sql.ts
  迁移: migration/ 目录
  命名: snake_case 字段名
```

## 8. 插件开发者的关键集成点

### 推荐使用的 SDK API（按优先级）

1. **核心对话**: `session.create()`, `session.prompt()`, `session.promptAsync()`, `event.subscribe()`
2. **会话管理**: `session.list()`, `session.get()`, `session.delete()`, `session.messages()`
3. **Provider/模型**: `provider.list()`, `config.providers()`
4. **文件操作**: `file.read()`, `file.list()`, `find.text()`, `find.symbols()`
5. **MCP**: `mcp.status()`, `mcp.connect()`, `mcp.add()`
6. **配置**: `config.get()`, `config.update()`
7. **权限**: `postSessionIdPermissionsPermissionId()` (响应权限请求)

### SSE 事件订阅模式

```typescript
const client = createOpencodeClient({ baseUrl: "http://127.0.0.1:4096", directory: "/path/to/project" })

// 监听 Instance 级事件
const eventStream = client.event.subscribe()
eventStream.on("data", (event) => {
  // event.type: "message.part_delta" | "session.status" | "permission.asked" | ...
  // event.properties: 事件 payload
})

// 监听全局事件
const globalStream = client.global.event()
globalStream.on("data", (event) => {
  // event.payload: Instance 事件
  // event.directory: 来源目录
})
```

### 权限响应模式

```typescript
// 当收到 permission.asked 事件
client.postSessionIdPermissionsPermissionId({
  path: { id: sessionId, permissionID: permissionId },
  body: { allow: true }  // 或 false
})
```
