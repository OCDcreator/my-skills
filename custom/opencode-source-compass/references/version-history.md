# Version History — OpenCode Source Compass

本文件记录 OpenCode 版本变化对技能参考文件的影响。

## 如何使用这个文件

1. 当 SDK 版本升级时，在此添加新版本的变更记录
2. 将旧版参考文件保留（重命名为带版本号的副本）
3. 需要回溯旧版本架构时，查看对应的版本记录和旧版参考文件

## 变更记录格式

```
### vX.Y.Z (日期)
- **变更类型**: 架构变更 / API 新增 / API 删除 / API 修改 / Bug 修复
- **影响范围**: 受影响的命名空间和路由
- **参考文件**: 对应的旧版参考文件名
- **变更内容**:
  - 具体变更 1
  - 具体变更 2
- **迁移指南**: (如有破坏性变更)
```

---

## v1.14.19 (2026-04-21) — 基线版本

这是技能创建时的基准版本。以下为该版本的架构快照。

### SDK 命名空间 (19 + 1 根级方法)

| 命名空间 | 方法数 |
|---|---|
| `global` | 1 |
| `project` | 2 |
| `pty` | 6 |
| `config` | 3 |
| `tool` | 2 |
| `instance` | 1 |
| `path` | 1 |
| `vcs` | 1 |
| `session` | 23 |
| `command` | 1 |
| `provider` | 2 (+2 OAuth) |
| `find` | 3 |
| `file` | 3 |
| `app` | 2 |
| `mcp` | 4 (+4 auth) |
| `lsp` | 1 |
| `formatter` | 1 |
| `tui` | 10 (+2 control) |
| `auth` | 5 |
| `event` | 1 |
| 根级方法 | 1 |
| **总计** | **78** |

### HTTP 路由文件

```
src/server/routes/
  global.ts              — /global/event, /health
  instance/
    index.ts             — /instance/dispose, /path, /vcs, /agent, /command, /lsp, /formatter, /log
    config.ts            — /config, /config/providers
    event.ts             — /event (SSE)
    experimental.ts      — /experimental/tool, /experimental/tool/ids
    file.ts              — /file, /file/content, /file/status, /find, /find/file, /find/symbol
    mcp.ts               — /mcp, /mcp/{name}/connect, /mcp/{name}/disconnect, /mcp/{name}/auth/*
    middleware.ts         — Instance 中间件 (x-opencode-directory → InstanceState)
    permission.ts        — /session/{id}/permissions/{permissionID}
    project.ts           — /project, /project/current
    provider.ts          — /provider, /provider/auth, /provider/{id}/oauth/*
    pty.ts               — /pty, /pty/{id}, /pty/{id}/connect
    question.ts          — /question (内部)
    session.ts           — /session, /session/{id}, /session/{id}/message, /session/{id}/prompt_async, ...
    sync.ts              — /sync (文件同步)
    trace.ts             — /trace (追踪)
    tui.ts               — /tui/* (终端 UI 控制)
    httpapi/             — HTTP API 子路由
```

### 核心服务文件

```
src/session/session.ts      — 会话 CRUD
src/session/prompt.ts       — 消息处理入口
src/session/llm.ts          — LLM 调用
src/session/message-v2.ts   — 消息数据模型 (Part 结构)
src/session/status.ts       — 会话状态管理
src/session/compaction.ts   — 历史压缩
src/session/revert.ts       — 消息回滚
src/session/summary.ts      — 会话摘要
src/session/todo.ts         — Todo 管理

src/provider/provider.ts    — Provider 注册表 (BUNDLED_PROVIDERS)
src/provider/sdk/           — 自定义 SDK 适配器

src/mcp/index.ts            — MCP 客户端管理
src/mcp/auth.ts             — MCP OAuth

src/bus/index.ts            — Instance 级事件总线
src/bus/global.ts           — 全局事件总线 (EventEmitter)
src/bus/bus-event.ts        — 事件定义工具

src/permission/index.ts     — 权限评估引擎
src/agent/agent.ts          — Agent 定义
src/tool/registry.ts        — 工具注册表
src/lsp/lsp.ts              — LSP 客户端
src/file/index.ts           — 文件操作
src/pty/index.ts            — PTY 管理
src/storage/                — SQLite + Drizzle
src/config/config.ts        — 配置系统
src/auth/index.ts           — 认证管理
src/project/instance.ts     — Instance 管理
src/effect/instance-state.ts — Instance 状态缓存
```

### Bus 事件类型 (40+)

完整列表见 `references/architecture-v1.14.md` 中的"事件总线事件目录"。

### SDK 自动生成

SDK 由 `@hey-api/openapi-ts` 从 OpenAPI spec 自动生成。
- 输入: OpenCode server 的 OpenAPI spec
- 输出: `packages/sdk/js/src/gen/sdk.gen.ts`
- 重建: `./packages/sdk/js/script/build.ts`

---

<!-- 以下为后续版本变更记录的模板位置 -->
