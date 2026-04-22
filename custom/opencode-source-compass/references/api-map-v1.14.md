# API Map — OpenCode SDK v1.14.19

> SDK 源码: `packages/sdk/js/src/gen/sdk.gen.ts` (1197 行，自动生成)
> OpenCode 版本: v1.14.19 | 分支: `dev`
> 路由根: `packages/opencode/src/server/routes/instance/`
> 服务根: `packages/opencode/src/`

## 命名空间总览

OpencodeClient 包含以下 19 个命名空间和 1 个根级方法：

| # | 命名空间 | 方法数 | HTTP 前缀 | 路由文件 | 核心服务 |
|---|---|---|---|---|---|
| 1 | `global` | 1 | `/global/` | `src/server/routes/global.ts` | `src/bus/global.ts` |
| 2 | `project` | 2 | `/project` | `src/server/routes/instance/project.ts` | `src/project/project.ts` |
| 3 | `pty` | 6 | `/pty` | `src/server/routes/instance/pty.ts` | `src/pty/index.ts` |
| 4 | `config` | 3 | `/config` | `src/server/routes/instance/config.ts` | `src/config/config.ts` |
| 5 | `tool` | 2 | `/experimental/tool` | `src/server/routes/instance/experimental.ts` | `src/tool/registry.ts` |
| 6 | `instance` | 1 | `/instance` | `src/server/routes/instance/index.ts` | `src/project/instance.ts` |
| 7 | `path` | 1 | `/path` | `src/server/routes/instance/index.ts` | `src/project/` |
| 8 | `vcs` | 1 | `/vcs` | `src/server/routes/instance/index.ts` | `src/git/` |
| 9 | `session` | 23 | `/session` | `src/server/routes/instance/session.ts` | `src/session/session.ts` |
| 10 | `command` | 1 | `/command` | `src/server/routes/instance/index.ts` | `src/cli/cmd/` |
| 11 | `provider` | 2+2oauth | `/provider` | `src/server/routes/instance/provider.ts` | `src/provider/provider.ts` |
| 12 | `find` | 3 | `/find` | `src/server/routes/instance/file.ts` | `src/file/` + `src/lsp/` |
| 13 | `file` | 3 | `/file` | `src/server/routes/instance/file.ts` | `src/file/` |
| 14 | `app` | 2 | `/log`, `/agent` | `src/server/routes/instance/index.ts` | `src/agent/agent.ts` |
| 15 | `mcp` | 4+4auth | `/mcp` | `src/server/routes/instance/mcp.ts` | `src/mcp/index.ts` |
| 16 | `lsp` | 1 | `/lsp` | `src/server/routes/instance/index.ts` | `src/lsp/lsp.ts` |
| 17 | `formatter` | 1 | `/formatter` | `src/server/routes/instance/index.ts` | `src/formatter/` |
| 18 | `tui` | 10+2control | `/tui` | `src/server/routes/instance/tui.ts` | TUI 内部 |
| 19 | `auth` | 5 | `/auth`, `/mcp/.../auth` | `src/server/routes/instance/session.ts` + `mcp.ts` | `src/auth/index.ts` |
| 20 | `event` | 1 | `/event` | `src/server/routes/instance/event.ts` | `src/bus/index.ts` |
| - | 根级方法 | 1 | `/session/.../permissions` | `src/server/routes/instance/permission.ts` | `src/permission/index.ts` |

**总计**: 78 个 API 方法（66 个顶层方法 + 12 个嵌套 OAuth/Control 方法）

---

## 1. Global

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.global.event()` | GET `/global/event` (SSE) | `src/server/routes/global.ts` | `src/bus/global.ts` → GlobalBus (EventEmitter) |

**说明**: 全局 SSE 事件流，在 Instance 之前建立。所有 Instance 的事件通过 GlobalBus 转发到这个端点。

---

## 2. Project

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.project.list()` | GET `/project` | `src/server/routes/instance/project.ts` | `src/project/project.ts` |
| `client.project.current()` | GET `/project/current` | 同上 | 同上 |

---

## 3. Pty

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.pty.list()` | GET `/pty` | `src/server/routes/instance/pty.ts` | `src/pty/index.ts` → list |
| `client.pty.create()` | POST `/pty` | 同上 | 同上 → create |
| `client.pty.remove()` | DELETE `/pty/{id}` | 同上 | 同上 → remove |
| `client.pty.get()` | GET `/pty/{id}` | 同上 | 同上 → get |
| `client.pty.update()` | PUT `/pty/{id}` | 同上 | 同上 → update |
| `client.pty.connect()` | GET `/pty/{id}/connect` | 同上 | 同上 → connect (WebSocket 升级) |

**Bus 事件**: `pty.created`, `pty.updated`, `pty.exited`, `pty.deleted`

---

## 4. Config

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.config.get()` | GET `/config` | `src/server/routes/instance/config.ts` | `src/config/config.ts` |
| `client.config.update()` | PATCH `/config` | 同上 | 同上 |
| `client.config.providers()` | GET `/config/providers` | 同上 | `src/provider/provider.ts` → BUNDLED_PROVIDERS |

---

## 5. Tool

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.tool.ids()` | GET `/experimental/tool/ids` | `src/server/routes/instance/experimental.ts` | `src/tool/registry.ts` |
| `client.tool.list()` | GET `/experimental/tool` | 同上 | 同上（带 JSON Schema 参数） |

**说明**: 实验性 API。`ids()` 返回所有已注册工具 ID，`list()` 返回带 JSON Schema 的完整工具列表。

---

## 6. Instance

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.instance.dispose()` | POST `/instance/dispose` | `src/server/routes/instance/index.ts` | `src/project/instance.ts` |

**说明**: 销毁当前 Instance，释放所有 Effect 资源。触发 `server.instance.disposed` 事件。

---

## 7. Path

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.path.get()` | GET `/path` | `src/server/routes/instance/index.ts` | `src/project/` |

---

## 8. Vcs

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.vcs.get()` | GET `/vcs` | `src/server/routes/instance/index.ts` | `src/git/` + `src/project/vcs.ts` |

**Bus 事件**: `project.branch_updated`

---

## 9. Session（最大命名空间，23 个方法）

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.session.list()` | GET `/session` | `src/server/routes/instance/session.ts` | `src/session/session.ts` |
| `client.session.create()` | POST `/session` | 同上 | 同上 → `create()` |
| `client.session.status()` | GET `/session/status` | 同上 | `src/session/status.ts` |
| `client.session.delete()` | DELETE `/session/{id}` | 同上 | `src/session/session.ts` |
| `client.session.get()` | GET `/session/{id}` | 同上 | 同上 |
| `client.session.update()` | PATCH `/session/{id}` | 同上 | 同上 |
| `client.session.children()` | GET `/session/{id}/children` | 同上 | 同上 |
| `client.session.todo()` | GET `/session/{id}/todo` | 同上 | `src/session/todo.ts` |
| `client.session.init()` | POST `/session/{id}/init` | 同上 | `src/session/` (AGENTS.md 生成) |
| `client.session.fork()` | POST `/session/{id}/fork` | 同上 | `src/session/session.ts` |
| `client.session.abort()` | POST `/session/{id}/abort` | 同上 | 同上 |
| `client.session.unshare()` | DELETE `/session/{id}/share` | 同上 | `src/share/` |
| `client.session.share()` | POST `/session/{id}/share` | 同上 | 同上 |
| `client.session.diff()` | GET `/session/{id}/diff` | 同上 | `src/git/` |
| `client.session.summarize()` | POST `/session/{id}/summarize` | 同上 | `src/session/summary.ts` |
| `client.session.messages()` | GET `/session/{id}/message` | 同上 | `src/session/message-v2.ts` |
| `client.session.prompt()` | POST `/session/{id}/message` | 同上 | `src/session/prompt.ts` → `src/session/llm.ts` |
| `client.session.message()` | GET `/session/{id}/message/{messageID}` | 同上 | `src/session/message-v2.ts` |
| `client.session.promptAsync()` | POST `/session/{id}/prompt_async` | 同上 | `src/session/prompt.ts` |
| `client.session.command()` | POST `/session/{id}/command` | 同上 | `src/session/prompt.ts` (command 路由) |
| `client.session.shell()` | POST `/session/{id}/shell` | 同上 | `src/session/prompt.ts` + `src/pty/` |
| `client.session.revert()` | POST `/session/{id}/revert` | 同上 | `src/session/revert.ts` |
| `client.session.unrevert()` | POST `/session/{id}/unrevert` | 同上 | 同上 |

**Bus 事件**: `session.diff`, `session.error`, `session.status`, `session.idle`, `message.part_delta`, `todo.updated`, `session.compacted`

### prompt() 完整调用链

```
client.session.prompt({ id, ... })
  → POST /session/{id}/message
    → src/server/routes/instance/session.ts (路由处理)
      → src/session/prompt.ts → prompt()
        → src/session/session.ts → 会话加载
          → src/session/llm.ts → LLM 调用
            → src/provider/ → 模型选择
            → src/tool/registry.ts → 工具注册
            → src/bus/ → Bus.publish(message.part_delta) 流式输出
```

### promptAsync() 与 prompt() 的区别

- `prompt()` 同步等待，流式返回 SSE 事件
- `promptAsync()` 立即返回 session 对象，后台开始处理。通过 `client.event.subscribe()` 监听结果

---

## 10. Command

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.command.list()` | GET `/command` | `src/server/routes/instance/index.ts` | `src/cli/cmd/` |

---

## 11. Provider

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.provider.list()` | GET `/provider` | `src/server/routes/instance/provider.ts` | `src/provider/provider.ts` |
| `client.provider.auth()` | GET `/provider/auth` | 同上 | 同上 |
| `client.provider.oauth.authorize()` | POST `/provider/{id}/oauth/authorize` | 同上 | `src/provider/` + OAuth |
| `client.provider.oauth.callback()` | POST `/provider/{id}/oauth/callback` | 同上 | 同上 |

---

## 12. Find

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.find.text()` | GET `/find` | `src/server/routes/instance/file.ts` | `src/file/` (grep) |
| `client.find.files()` | GET `/find/file` | 同上 | `src/file/` (glob) |
| `client.find.symbols()` | GET `/find/symbol` | 同上 | `src/lsp/` (workspace symbols) |

---

## 13. File

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.file.list()` | GET `/file` | `src/server/routes/instance/file.ts` | `src/file/index.ts` |
| `client.file.read()` | GET `/file/content` | 同上 | 同上 |
| `client.file.status()` | GET `/file/status` | 同上 | 同上 |

**Bus 事件**: `file.edited`, `file.watcher.updated`

---

## 14. App

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.app.log()` | POST `/log` | `src/server/routes/instance/index.ts` | 日志系统 |
| `client.app.agents()` | GET `/agent` | 同上 | `src/agent/agent.ts` |

---

## 15. Mcp

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.mcp.status()` | GET `/mcp` | `src/server/routes/instance/mcp.ts` | `src/mcp/index.ts` |
| `client.mcp.add()` | POST `/mcp` | 同上 | 同上 |
| `client.mcp.connect()` | POST `/mcp/{name}/connect` | 同上 | 同上 → connectLocal / connectRemote |
| `client.mcp.disconnect()` | POST `/mcp/{name}/disconnect` | 同上 | 同上 |
| `client.mcp.auth.remove()` | DELETE `/mcp/{name}/auth` | 同上 | `src/mcp/auth.ts` |
| `client.mcp.auth.start()` | POST `/mcp/{name}/auth` | 同上 | 同上 |
| `client.mcp.auth.callback()` | POST `/mcp/{name}/auth/callback` | 同上 | 同上 |
| `client.mcp.auth.authenticate()` | POST `/mcp/{name}/auth/authenticate` | 同上 | 同上 |

**Bus 事件**: `mcp.tools_changed`, `mcp.browser_open_failed`

---

## 16. Lsp

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.lsp.status()` | GET `/lsp` | `src/server/routes/instance/index.ts` | `src/lsp/lsp.ts` |

**Bus 事件**: `lsp.updated`, `lsp.diagnostics`

---

## 17. Formatter

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.formatter.status()` | GET `/formatter` | `src/server/routes/instance/index.ts` | `src/formatter/` |

---

## 18. Tui

> **注意**: TUI API 主要用于终端 UI 控制，外部插件一般不需要使用。

| SDK 方法 | HTTP | 路由文件 |
|---|---|---|
| `client.tui.appendPrompt()` | POST `/tui/append-prompt` | `src/server/routes/instance/tui.ts` |
| `client.tui.openHelp()` | POST `/tui/open-help` | 同上 |
| `client.tui.openSessions()` | POST `/tui/open-sessions` | 同上 |
| `client.tui.openThemes()` | POST `/tui/open-themes` | 同上 |
| `client.tui.openModels()` | POST `/tui/open-models` | 同上 |
| `client.tui.submitPrompt()` | POST `/tui/submit-prompt` | 同上 |
| `client.tui.clearPrompt()` | POST `/tui/clear-prompt` | 同上 |
| `client.tui.executeCommand()` | POST `/tui/execute-command` | 同上 |
| `client.tui.showToast()` | POST `/tui/show-toast` | 同上 |
| `client.tui.publish()` | POST `/tui/publish` | 同上 |
| `client.tui.control.next()` | GET `/tui/control/next` | 同上 |
| `client.tui.control.response()` | POST `/tui/control/response` | 同上 |

**Bus 事件**: `tui.prompt.append`, `tui.command.execute`, `tui.toast.show`, `tui.session.select`

---

## 19. Auth

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.auth.set()` | PUT `/auth/{id}` | `src/server/routes/instance/session.ts` | `src/auth/index.ts` |
| `client.auth.remove()` | DELETE `/mcp/{name}/auth` | `src/server/routes/instance/mcp.ts` | `src/mcp/auth.ts` |
| `client.auth.start()` | POST `/mcp/{name}/auth` | 同上 | 同上 |
| `client.auth.callback()` | POST `/mcp/{name}/auth/callback` | 同上 | 同上 |
| `client.auth.authenticate()` | POST `/mcp/{name}/auth/authenticate` | 同上 | 同上 |

**说明**: `client.auth` 命名空间同时包含 Provider 认证（`set()`）和 MCP OAuth 认证（其余方法）。SDK 中 Auth 类的方法实际上是 MCP auth 的快捷方式。

---

## 20. Event

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.event.subscribe()` | GET `/event` (SSE) | `src/server/routes/instance/event.ts` | `src/bus/index.ts` → Bus.Service |

**说明**: Instance 级别的 SSE 事件流。所有 Instance 内的 Bus 事件都会转发到此端点。与 `client.global.event()` 的区别：global 是全局的（跨 Instance），event 是当前 Instance 的。

---

## 根级方法

| SDK 方法 | HTTP | 路由文件 | 服务文件 |
|---|---|---|---|
| `client.postSessionIdPermissionsPermissionId()` | POST `/session/{id}/permissions/{permissionID}` | `src/server/routes/instance/permission.ts` | `src/permission/index.ts` |

**Bus 事件**: `permission.asked`, `permission.replied`

---

## SDK 客户端注入机制

SDK 通过 `packages/sdk/js/src/client.ts` 中的 `rewrite()` 函数注入 `x-opencode-directory` header：

```typescript
// client.ts 核心逻辑
function rewrite(options) {
  const directory = options?.directory ?? client.baseUrl
  options.headers = {
    ...options.headers,
    "x-opencode-directory": directory,
  }
  // 将 directory 转为 ?directory= query param
}
```

这意味着每个 SDK 调用都自动携带 `directory` 信息，服务端通过 InstanceMiddleware 将请求路由到正确的 Instance。
