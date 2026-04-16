# Project Comparison: Obsidian Plugin Debug Logging

本参考总结两个本地 Obsidian 插件项目在调试日志管理上的现有做法。它用于指导未来项目取长补短，不要求照搬任一项目。

## `obsidian-bookshelf`

### 保留

- 默认静默：debug 关闭时只输出启动版本行、警告和错误。
- `always` 语义：启动时输出 `Bookshelf <display version> loaded | BUILD_ID <id>`，便于确认测试库实际运行版本。
- 设置页集中调试入口：调试开关、内联序列化、复制诊断、清空最近日志缓存、复制版本号。
- 诊断报告包含展示版本、release codename、manifest version、`BUILD_ID`、vault 名称和 vault 路径。
- 最近日志缓存可被诊断报告复用，且可以手动清空。
- `DISPLAY_VERSION = <releaseCodename> v<semver>` 与 manifest pure semver 分层清晰。

### 改进

- 最近日志缓存上限较小，只有 300 条；通用方案建议默认 500 条。
- 没有导出诊断日志文件，只能复制剪贴板。
- 没有 Windows/macOS 分平台日志路径或控制台指引；控制台说明偏单行。
- 无重复日志抑制、节流、payload 变化检测等过载控制。
- `always` 实际写入最近日志时落为 `info`，建议在通用契约中独立保存为 `always` level。
- 诊断报告里的 runtime 快照较轻，复杂插件需要可扩展的 subsystem diagnostics。

### 废弃或避免

- 避免把 `always` 只当作 `info` 的别名；它应是独立语义。
- 避免只依赖 clipboard；用户反馈和开发者排障通常需要文件导出路径。
- 避免所有调试信息都靠手动复制 Console；诊断报告应成为一等入口。

## `opencodian`

### 保留

- 较完整的导出能力：可以复制诊断信息，也可以生成调试日志文件。
- 设置页包含平台相关控制台说明：Windows/Linux 用 `Ctrl + Shift + I`，macOS 用 `Cmd + Option + I`。
- 支持按平台保存默认导出路径，并在路径为空或不存在时打开目录选择器。
- 最近日志缓存上限 500 条，适合更复杂插件。
- 诊断报告包含服务健康、内部状态、managed process、server diagnostics 等 runtime 快照。
- debug 开关开启时会额外输出服务状态快照。
- 部分高频/重复诊断日志已有抑制和测试，例如相同 liquid glass payload 只记录一次直到变化。
- 流式链路有 `traceId`、阶段日志、progress 节流思想，适合复杂异步插件借鉴。

### 改进

- `info` 默认始终输出，普通用户控制台容易偏吵；通用方案应让 `info` 跟随 debug 开关。
- 没有独立 `always` level；启动 `BUILD_ID` 通过 `info` 输出，导致 `info` 语义混杂。
- 诊断报告没有固定包含 `BUILD_ID` 和展示版本，排查测试库版本时不够稳。
- 平台路径使用 `unix` 合并 macOS/Linux；通用方案要求至少显式区分 `windows` 与 `macos`。
- 设置页提供复制和生成文件，但缺少“清空最近日志缓存”入口。
- 内联序列化设置只存全局 flag，不如持久化到明确设置结构更透明。

### 废弃或避免

- 避免让 `info` 在默认状态下始终可见；这会削弱 quiet-by-default。
- 避免把 macOS 仅归入泛 `unix`，因为用户文案、路径和控制台菜单都不同。
- 避免只在局部功能里做去重/节流；应提供共享 helper，减少重复实现。

## 抽象后的推荐方向

- 采用 `always | error | warn | info | debug` 五级语义。
- 控制台默认只输出 `always/warn/error`；`info/debug` 需要用户打开 debug logging。
- 所有输出进入最近日志缓存，缓存用于诊断报告和文件导出。
- 诊断报告固定包含 build identity、environment、settings、runtime、recent logs。
- 设置页提供 debug 开关、内联序列化、复制诊断、导出文件、清空缓存、复制版本信息、平台控制台指引。
- Windows/macOS 单独设计路径与文案；Linux 可扩展，但不能替代 macOS。
- 对高频/重复/大 payload 日志提供共享去重、节流、截断工具。
