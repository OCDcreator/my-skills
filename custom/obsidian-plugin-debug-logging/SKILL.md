---
name: obsidian-plugin-debug-logging
description: Use this when developing or retrofitting an Obsidian plugin and the user mentions 调试日志, debug logging, 控制台日志, console logs, diagnostic report, 诊断报告, 日志开关, 日志分级, 默认静默, 故障排查, 最近日志缓存, 日志导出, 环境快照, BUILD_ID, version/build logs, or wants a maintainable logging/diagnostics system. Trigger even if the user only asks to make plugin logs quieter, copy troubleshooting info, export logs, add a debug toggle, or support Windows/macOS console instructions.
---

# Obsidian Plugin Debug Logging

为 Obsidian 插件建立一套现代、低噪音、可维护的调试日志与诊断报告体系。目标不是“把 `console.log` 包一层”，而是让插件同时满足：

- 普通用户默认安静
- 开发者能快速打开详细日志
- 故障排查时能复制/导出完整诊断上下文
- Windows 与 macOS 都有清晰路径、控制台和文件导出策略
- 日志不会刷屏、泄露敏感信息或成为新的用户体验负担

## First Pass

先审计当前仓库，再决定补齐方案。不要直接套模板覆盖已有实现。

1. 阅读目标插件仓库适用的 `AGENTS.md` / `CLAUDE.md` / 项目说明。
2. 确认这是 Obsidian 插件：`manifest.json`、`package.json`、入口 `src/main.ts` 或等价文件。
3. 搜索现有实现：`createLogger`、`logger`、`console.`、`debug`、`BUILD_ID`、`diagnostic`、`诊断`、`日志`、`settings`。
4. 找到设置结构、设置页、构建注入、启动日志、导出/剪贴板能力。
5. 先写 gap analysis：保留什么、改进什么、废弃什么，再动代码。

## Standard Contract

默认推荐的日志级别固定为：

| Level | 默认输出 | 用途 |
|---|---:|---|
| `always` | 是 | 启动首行版本/`BUILD_ID`、极少数一次性关键状态 |
| `error` | 是 | 真实错误、失败原因、可行动异常 |
| `warn` | 是 | 降级、配置风险、非致命异常 |
| `info` | 否 | 生命周期、用户动作、摘要状态；debug 开启后输出 |
| `debug` | 否 | 细节 payload、流程追踪、开发排障；debug 开启后输出 |

关键原则：

- 默认静默：debug 关闭时，控制台只输出 `always`、`warn`、`error`。
- `always` 是独立语义，不要把普通 `info` 都设为 always-visible。
- 控制台和诊断报告共享同一最近日志缓存，但职责不同：控制台实时查看，诊断报告用于复制/导出和异步排障。
- 每条日志至少带 `timestamp`、`level`、`scope`、`message`。
- `DISPLAY_VERSION`、`BUILD_ID`、vault 信息放在启动首行和诊断报告头部，不要塞进每条普通日志。

完整契约见 `references/modern-logging-contract.md`。

## Implementation Workflow

### 1. Logger Core

优先建立或改造一个共享 logger 模块，通常位于：

- `src/shared/logger.ts`
- `src/utils/logger.ts`
- `src/core/logger.ts`

应支持：

- `createLogger(scope)`
- `setDebugLoggingEnabled(enabled)`
- `setInlineSerializedDebugLogArgsEnabled(enabled)`
- `getRecentLogEntries()`
- `getRecentLogText()`
- `clearRecentLogs()`
- `logOnceUntilChanged()` 或等价重复 payload 抑制
- 高频日志节流 helper

可参考 `templates/logger-contract.ts`，但要适配目标仓库的 TypeScript 风格和已有命名。

### 2. Build Identity

确认 `BUILD_ID` 是否由构建系统注入。格式可以是：

- `semver+ISO timestamp`
- `branch.YYYYMMDDHHmm`
- 其他每次构建唯一且可追溯的格式

不要强制统一格式；必须确保：

- 插件启动首行输出当前版本和 `BUILD_ID`
- 诊断报告固定包含 `BUILD_ID`
- 测试库部署或用户反馈能据此确认实际运行的构建

如果项目还没有版本/部署体系，可结合 `obsidian-plugin-release-manager` skill。

### 3. Settings Debug Entry

设置页至少提供：

- `启用调试日志` 开关
- `内联序列化调试参数` 开关
- `复制最近诊断` 按钮
- `导出诊断日志文件` 按钮
- `清空最近日志缓存` 按钮
- `复制版本号 / DISPLAY_VERSION / BUILD_ID` 按钮
- 当前版本、`BUILD_ID`、Windows/macOS 控制台打开指引

参考 `templates/debug-settings-section.md`。

### 4. Diagnostic Report

诊断报告固定包含：

- Build：插件名、插件 ID、manifest semver、展示版本、`BUILD_ID`
- Environment：Obsidian 平台、桌面/移动、vault 名称、vault 路径、生成时间、来源
- Settings：只放排障必要设置，避免复制密钥或敏感 token
- Runtime：项目特定状态，例如服务健康、文件 watcher、缓存数量、当前模式
- Recent Logs：最近日志缓存文本
- Optional subsystem diagnostics：服务、模型、文件系统、渲染、同步等项目特定快照

参考 `templates/diagnostic-report-template.md`。

### 5. Overload Control

把日志过载控制当成一等需求：

- 对相同 label + payload 的诊断日志做“直到 payload 变化才再次输出”
- 对 streaming / progress / resize / polling 日志做时间或内容增量节流
- 对大对象、长文本、文件内容、模型输出做 preview 和截断
- 不输出 API key、token、完整隐私路径、全文文档、二进制或大块 base64
- debug 开启时可以详细，但仍不能无限刷屏

## Windows + macOS

必须把 Windows 和 macOS 作为一等平台支持。

共享逻辑：

- logger core
- ring buffer
- debug 开关
- 诊断报告结构
- 导出文件命名
- `BUILD_ID` 与版本头信息

分平台逻辑：

- 默认导出目录建议
- 路径占位符与路径格式
- 目录选择器默认路径
- 控制台快捷键与菜单路径
- 诊断报告里的平台标签

推荐设置结构：

```ts
interface DebugLogPaths {
  windows: string;
  macos: string;
  linux?: string;
}
```

不要把 macOS 只当成泛 `unix`。如需支持 Linux，可额外扩展，但不能弱化 Windows/macOS。

更多平台细节见 `references/platform-support.md` 和 `templates/platform-console-help.md`。

## Project Lessons

本 skill 的本地经验来自两个 Obsidian 插件项目：

- `obsidian-bookshelf`：保留其默认静默、`always` 启动版本行、诊断复制、清空缓存、展示版本/代号做法；改进其无文件导出、无平台分流、无去重节流、缓存较小、`always` 未独立建模的问题。
- `opencodian`：保留其导出日志文件、平台控制台指引、目录选择器、服务快照、重复/高频日志抑制做法；改进其 `info` 默认始终输出、缺少独立 `always`、诊断头缺 `BUILD_ID`/展示版本、macOS/Linux 合并路径、缺清空缓存入口的问题。

详细对比见 `references/project-comparison.md`。

## Reference Files

按需读取，不要一次性全部加载：

- `references/project-comparison.md`：两个本地项目的对比结论
- `references/modern-logging-contract.md`：推荐日志治理契约
- `references/platform-support.md`：Windows/macOS 平台支持规则
- `references/adoption-checklist.md`：落地检查清单
- `templates/`：可复制/改写的 TypeScript 和设置页模板

## Expected Output

完成相关任务时，结果要明确说明：

- 当前仓库已有日志系统的优点与缺口
- 采用的级别策略和默认静默行为
- 控制台输出与诊断报告的关系
- 最近日志缓存大小、清空方式和导出方式
- 设置页新增/调整的调试入口
- `BUILD_ID`、版本号、vault 信息如何进入启动日志与诊断报告
- Windows/macOS 哪些逻辑共享、哪些分平台
- 采取了哪些防刷屏、防泄露、防过载措施
- 如何验证：单元测试、类型检查、构建、Obsidian 控制台/导出文件人工验证
