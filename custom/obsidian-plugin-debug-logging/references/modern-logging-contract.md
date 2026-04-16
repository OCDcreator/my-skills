# Modern Logging Contract

这是一套适合 Obsidian 本地插件生态的默认日志治理契约。它强调低噪音、可复制诊断、可追溯构建和跨平台用户指引。

## Level Model

| Level | Console when debug off | Console when debug on | Recent buffer | Typical use |
|---|---:|---:|---:|---|
| `always` | yes | yes | yes | 启动版本行、构建身份、极少数一次性关键状态 |
| `error` | yes | yes | yes | 操作失败、异常、持久化失败、不可恢复状态 |
| `warn` | yes | yes | yes | 降级、配置风险、重试、可恢复问题 |
| `info` | no | yes | yes | 生命周期、用户动作、普通状态摘要 |
| `debug` | no | yes | yes | 详细 payload、阶段追踪、开发排障 |

`always` 不是“高级 info”。它只用于 debug 关闭时也必须可见的少量身份信息。普通生命周期消息使用 `info`。

## Destinations

### Console

- 控制台是实时查看入口。
- 默认只显示 `always/warn/error`。
- debug 开启后显示 `info/debug`。
- 保留对象参数为独立 console 参数，便于展开；可用“内联序列化”开关把 debug 对象拼成文本，便于复制。

### Recent Buffer

- 最近日志缓存是诊断报告和导出的统一来源。
- 默认使用有界 ring buffer，推荐 500 条。
- 缓存在内存中即可；不要默认持续写磁盘。
- 用户必须能从设置页清空缓存。
- 缓冲区条目至少包含：ISO 时间戳、level、scope、message。

### Diagnostic Report

- 诊断报告不是“控制台全文复制”，而是环境快照 + 最近日志。
- 报告头部固定包含 build identity 和 vault 环境，避免开发者只拿到孤立日志。
- 报告可复制到剪贴板，也可导出到用户选择的文件夹。

## Required Metadata

### Per Log Entry

- `timestamp`
- `level`
- `scope`
- `message`

### Diagnostic Header

- 插件名
- 插件 ID
- manifest semver
- display version（如果项目有）
- `BUILD_ID`
- Obsidian 平台
- desktop/mobile 状态
- vault 名称
- vault path（如果可用）
- generated timestamp
- report source，例如 `settings-copy`、`settings-export`、`startup-debug-toggle`

不要把 vault path 或版本号重复写进每条普通日志；这会造成噪音和隐私暴露。

## Build Identity

`BUILD_ID` 必须由构建系统注入，而不是运行时临时生成。格式可按项目选择：

- `1.2.3+2026-04-16T08:11:29.213Z`
- `main.202604160811`
- `feature-x.202604160811`

判断标准：

- 每次构建唯一
- 能在 bundle 中搜索到
- 能出现在启动首行
- 能出现在诊断报告
- 能用于测试库部署后确认运行版本

## Settings Contract

推荐设置结构至少包含：

```ts
interface DebugSettings {
  enableDebugLogging: boolean;
  inlineSerializedDebugLogArgs: boolean;
  debugLogPaths: {
    windows: string;
    macos: string;
    linux?: string;
  };
}
```

默认值：

```ts
{
  enableDebugLogging: false,
  inlineSerializedDebugLogArgs: false,
  debugLogPaths: {
    windows: '',
    macos: ''
  }
}
```

## Overload Control

### Deduplicate

对布局诊断、服务状态、重复连接失败、相同配置快照等日志，使用 label + stable payload key 去重：

- payload 未变化：不重复输出
- payload 变化：输出新条目
- 需要时在恢复或变化时补充 suppressed count

### Throttle

对 streaming、polling、resize、mousemove、render progress 等高频日志做节流：

- 时间阈值，例如 500ms 或 1000ms
- 内容增量阈值，例如文本增长超过 200 字符
- 阶段边界仍可立即输出，例如 start / first chunk / done / error

### Truncate

对长文本和对象做 preview：

- 默认 preview 80–200 字符
- 保留长度、类型、关键字段
- 不记录全文文档、模型完整输出、大块 base64 或二进制

### Redact

默认过滤：

- API key
- bearer token
- auth header
- password
- secret
- 私密 provider config

路径是否脱敏按项目决定；诊断报告可保留 vault path，但用户界面应提示它会被复制/导出。

## Testing Expectations

至少测试：

- debug off 时 `info/debug` 不进 console，`always/warn/error` 仍输出
- debug on 时 `info/debug` 输出
- 最近日志缓存限制条数并保留最新条目
- `clearRecentLogs()` 清空缓存
- 诊断报告包含 `BUILD_ID`、版本、vault、recent logs
- 重复 payload 抑制直到变化
- 导出文件路径按当前平台选择
