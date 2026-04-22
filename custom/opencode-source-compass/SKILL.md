---
name: opencode-source-compass
description: |
  OpenCode 源码架构导航与版本兼容性诊断技能。
  为接入 OpenCode SDK 的插件/应用提供源码快速定位、故障诊断路径和版本差异检测。

  触发场景（只要有以下任何一条就应该加载此技能）：
  - 用户提到 OpenCode SDK、opencode-ai、OpencodeClient、createOpencodeClient
  - 用户在开发接入 OpenCode 的插件（Obsidian 插件、VSCode 插件、Web 应用等）
  - 用户遇到 OpenCode SDK 调用错误、HTTP 请求失败、SSE 事件问题
  - 用户提到 opencode serve、opencode server、OpenCode HTTP API
  - 用户需要定位 OpenCode 源码中的某个功能实现（如 session、provider、mcp、lsp、agent、tool）
  - 用户提到 SDK 版本不匹配、API 不存在、响应格式变化
  - 用户说"opencode 源码在哪"、"opencode 怎么实现的"、"opencode 架构"
  - 用户在调试 OpenCode 插件集成问题、SDK 调用问题
---

# OpenCode Source Compass

> **版本基准**: v1.14.19 | SDK: 1.14.19 | 源码分支: `dev` (commit `8cc2c81d5`)

这个技能帮你（大模型）快速理解 OpenCode 源码架构，精确定位问题对应的源码文件，并检测 SDK 版本兼容性。

## 为什么需要这个技能

OpenCode 是一个大型 monorepo，包含 19 个 packages。当插件开发者遇到问题时，盲目 grep 效率极低。这个技能提供了一张"地图"——你拿到问题症状后，能直接跳到对应的路由文件和服务文件，而不是从几万个文件中搜索。

## 第一步：版本健康检查（每次使用必须先做）

在回答任何 OpenCode 相关问题之前，先执行版本检查。

### 自动检查流程

1. 确认插件代码中声明的 SDK 版本（检查 `package.json` 中 `@opencode-ai/sdk` 的版本号）
2. 确认本地安装的 OpenCode 版本：运行 `opencode --version`
3. 确认本地源码仓库版本：读取 `packages/opencode/package.json` 的 `version` 字段
4. 对比三者，如果不一致：
   - 插件 SDK < 本地 OpenCode → **警告**：插件可能缺少新 API，某些功能不可用
   - 插件 SDK > 本地 OpenCode → **严重警告**：API 调用可能失败，服务端返回 404 或新字段丢失
   - 本地源码版本 ≠ 本地 OpenCode 版本 → **提醒**：源码可能不是最新，架构信息可能过时

### 版本差异时的处理

如果发现版本差异：
- 输出明确的版本对比信息给用户
- 如果当前架构参考文件版本低于用户实际使用的版本，读取 `references/version-history.md` 检查是否有版本迁移记录
- 提醒用户可能需要更新技能文件（运行技能中的更新指令）

## 第二步：问题定位（按症状 → 源码路径）

### 架构概览（快速心智模型）

```
你的插件
  │
  │  createOpencodeClient({ baseUrl, directory })
  │
  ▼
┌─────────────────────────────────────────────────────┐
│  SDK (packages/sdk/js/src/)                         │
│  OpencodeClient → gen/sdk.gen.ts (自动生成)          │
│    .session  .provider  .mcp  .event  .config  ...  │
│    ↓ HTTP REST / SSE                                │
│  client.ts → x-opencode-directory header 注入       │
└────────────────────┬────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  HTTP Server (src/server/)                          │
│  默认 127.0.0.1:4096                                │
│                                                     │
│  中间件链: Auth → Logger → Compression → CORS →     │
│            InstanceMW(目录路由) → Fence(限流)        │
│                                                     │
│  路由注册顺序 (决定匹配优先级):                       │
│    /project → /pty → /config → /experimental →      │
│    /session → /permission → /question → /provider → │
│    /sync → /file → /event → /mcp → /tui            │
│    + /instance/dispose, /path, /vcs, /agent,        │
│      /skill, /lsp, /formatter, /command              │
└────────────────────┬────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  Effect Service 层                                  │
│  所有核心服务通过 Effect Context.Service 注入        │
│                                                     │
│  Session.Service ←→ SessionPrompt ←→ LLM            │
│  Provider.Service ←→ models.dev + @ai-sdk/*         │
│  MCP.Service ←→ stdio/HTTP 传输                     │
│  LSP.Service ←→ language server 进程管理             │
│  Agent.Service ←→ 权限模板 + 模型绑定               │
│  ToolRegistry ←→ bash/read/write/edit/grep/...      │
│  Permission ←→ glob 匹配 allow/ask/deny             │
│  Bus ←→ 事件总线 (session/message/part/mcp events)   │
│  Storage ←→ SQLite via Drizzle ORM                  │
└─────────────────────────────────────────────────────┘
```

### 故障定位速查表

用这个表直接从症状跳到源码文件。**源码路径基于 `packages/opencode/` 根目录**。

| 症状 | SDK 调用 | 路由文件 | 服务文件 |
|---|---|---|---|
| 创建会话失败 | `client.session.create()` | `src/server/routes/instance/session.ts` POST `/session` | `src/session/session.ts` → `create()` |
| 发消息没响应 | `client.session.prompt()` | `src/server/routes/instance/session.ts` POST `/session/{id}/message` | `src/session/prompt.ts` → `src/session/llm.ts` |
| 异步发消息失败 | `client.session.promptAsync()` | 同上 | `src/session/prompt.ts` → `prompt_async` 路由 |
| 消息流中断 | SSE `/event` | `src/server/routes/instance/event.ts` | `src/bus/` 事件总线 |
| Provider 不可用 | `client.provider.list()` | `src/server/routes/instance/provider.ts` | `src/provider/provider.ts` → `BUNDLED_PROVIDERS` |
| 模型列表为空 | `client.config.providers()` | `src/server/routes/instance/config.ts` | `src/provider/provider.ts` → `models.dev` |
| MCP 连接失败 | `client.mcp.connect()` | `src/server/routes/instance/mcp.ts` | `src/mcp/index.ts` → `connectLocal/connectRemote` |
| MCP OAuth 失败 | `client.mcp.auth.start()` | 同上 | `src/mcp/oauth-provider.ts` + `src/mcp/auth.ts` |
| 权限被拒绝 | 会话中的工具调用 | `src/server/routes/instance/permission.ts` | `src/permission/evaluate.ts` |
| LSP 操作失败 | 内部工具 `lsp` | `src/server/routes/instance/index.ts` GET `/lsp` | `src/lsp/lsp.ts` + `src/lsp/client.ts` |
| 文件操作失败 | `client.file.read/list()` | `src/server/routes/instance/file.ts` | `src/file/` |
| 代码搜索失败 | `client.find.text/files/symbols()` | `src/server/routes/instance/file.ts` | `src/file/` + `src/lsp/` |
| 配置读取失败 | `client.config.get()` | `src/server/routes/instance/config.ts` | `src/config/config.ts` |
| PTY 问题 | `client.pty.create/connect()` | `src/server/routes/instance/pty.ts` | `src/pty/` |
| 全局事件断开 | `client.global.event()` | `src/server/routes/global.ts` GET `/global/event` | `src/bus/global.ts` GlobalBus |
| Instance 找不到 | 所有请求返回 500 | `src/server/routes/instance/middleware.ts` | `src/project/instance.ts` Instance 绑定 |
| 认证问题 | `client.auth.set()` | `src/server/routes/instance/session.ts` Auth 路由 | `src/auth/index.ts` |
| 工具调用失败 | 会话中工具执行 | 无独立路由（通过 session prompt 链路） | `src/tool/*.ts` → `src/tool/registry.ts` |
| Agent 不可用 | `client.app.agents()` | `src/server/routes/instance/index.ts` GET `/agent` | `src/agent/agent.ts` |

### 关键源码目录索引

| 目录 | 内容 | 何时查阅 |
|---|---|---|
| `src/index.ts` | CLI 入口（yargs 命令注册） | 理解 CLI 命令如何对应到功能 |
| `src/cli/cmd/` | 所有 CLI 命令实现 | 定位 CLI 命令的具体实现 |
| `src/server/` | HTTP Server、路由、中间件 | HTTP API 问题 |
| `src/server/routes/instance/` | Instance 级路由（核心 API） | SDK 调用对应的 HTTP 端点 |
| `src/server/routes/global.ts` | 全局路由（health/event/config） | SSE 全局事件、配置 |
| `src/session/` | 会话管理（核心数据模型） | 会话 CRUD、消息流、压缩、回滚 |
| `src/session/prompt.ts` | 消息处理入口 | 发消息后的完整处理链 |
| `src/session/llm.ts` | LLM 调用封装 | AI 模型调用问题 |
| `src/session/message-v2.ts` | 消息数据模型 | 消息格式、Part 结构 |
| `src/provider/` | Provider 系统（24 家适配器） | 模型加载、API key、成本计算 |
| `src/provider/provider.ts` | Provider 注册和模型获取 | BUNDLED_PROVIDERS 映射表 |
| `src/provider/sdk/` | 自定义 SDK 适配器 | Copilot 等特殊 Provider |
| `src/agent/agent.ts` | Agent 定义和权限模板 | Agent 配置、权限规则 |
| `src/tool/` | 所有内置工具 | 工具行为、参数定义 |
| `src/tool/registry.ts` | 工具注册表 | 查看哪些工具被注册 |
| `src/mcp/` | MCP 客户端 | MCP 连接、OAuth、工具发现 |
| `src/lsp/` | LSP 客户端 | 代码智能感知 |
| `src/permission/` | 权限评估引擎 | allow/ask/deny 逻辑 |
| `src/config/` | 配置系统 | opencode.json 解析 |
| `src/auth/` | 认证管理 | API Key / OAuth 存储 |
| `src/bus/` | 事件总线 | SSE 事件发布/订阅 |
| `src/storage/` | SQLite 存储层 | 数据库迁移、Schema |
| `src/effect/` | Effect 框架集成 | 服务生命周期、状态管理 |
| `src/plugin/` | 插件系统 | 插件加载、Hook |
| `src/skill/` | Skill 系统 | Skill 发现和加载 |
| `src/share/` | 会话分享 | 分享链接生成 |
| `src/git/` | Git 集成 | diff/revert 联动 |
| `src/acp/` | ACP 协议 | Zed 编辑器集成 |
| `src/project/` | 项目/实例管理 | Instance 绑定和生命周期 |

## 第三步：SDK API → 源码完整映射

当用户提到某个 SDK 方法调用出问题时，参考 `references/api-map-v1.14.md` 获取完整的 API → HTTP 路径 → 路由文件 → 服务文件映射。

这个参考文件包含 OpencodeClient 的所有 20 个命名空间（含嵌套 OAuth/Control）共 78 个方法的完整映射（66 个顶层方法 + 12 个嵌套方法）。

**何时读取**：当你需要精确定位某个 SDK 方法的完整调用链时。

## 第四步：深入理解架构

当问题需要理解更深层的架构关系时，参考 `references/architecture-v1.14.md`。

这个参考文件包含：
- 完整的数据流图（从 SDK 到 SQLite 的每一步）
- Effect Service 依赖关系图
- 事件总线事件目录（40+ 个事件类型）
- Instance 生命周期
- 错误传播链

**何时读取**：当简单定位不够，需要理解"为什么"时。

## 第五步：版本历史查询

当用户提到"之前能用的 API 现在不行了"或"升级后出问题了"时，参考 `references/version-history.md`。

这个文件记录了每个版本的关键架构变化、API 变更、路由变化。

**何时读取**：版本升级导致的问题，或需要回溯旧版本架构时。

## 版本更新指令

当用户说"更新技能"或"同步到新版本"时，执行以下步骤：

1. 运行 `opencode --version` 获取新版本号
2. 读取当前技能中记录的版本号（本文件头部的版本基准）
3. 从 OpenCode 源码仓库重新分析变化：
   - `packages/opencode/package.json` → 版本号
   - `packages/sdk/js/src/gen/sdk.gen.ts` → SDK API 变化（对比方法列表）
   - `packages/opencode/src/server/routes/` → 路由变化
   - `packages/opencode/src/` 目录结构 → 新增/删除的模块
4. 更新流程：
   - 将当前 `references/architecture-v1.14.md` 复制为 `references/architecture-v1.XX.md`（保留旧版）
   - 将当前 `references/api-map-v1.14.md` 复制为 `references/api-map-v1.XX.md`（保留旧版）
   - 更新 `references/version-history.md` 添加版本变更记录
   - 用新版本的架构信息重写当前参考文件
   - 更新本 SKILL.md 中的版本基准号

## 关键约束

- **OpenCode 源码根目录**: `C:\Users\lt\Desktop\Write\open-source-project\AI-tools-agents\opencode\packages\opencode\`
- **SDK 源码目录**: `C:\Users\lt\Desktop\Write\open-source-project\AI-tools-agents\opencode\packages\sdk\js\`
- 所有路径都相对于各自的根目录
- 默认分支是 `dev`，不是 `main`
- SDK 是通过 OpenAPI 自动生成的（`@hey-api/openapi-ts`），API 变化意味着 Server 路由变了

## 参考文件索引

| 文件 | 内容 | 何时读取 |
|---|---|---|
| `references/api-map-v1.14.md` | SDK 每个方法的完整调用链映射 | 定位特定 SDK 调用问题时 |
| `references/architecture-v1.14.md` | 深度架构分析（数据流、服务依赖、事件目录） | 需要理解深层架构时 |
| `references/version-history.md` | 版本变更记录 | 版本升级导致的问题 |
