**审查结果**
- 我实测了 `opencode --help`、`opencode run --help`，并补查了 `session/providers/agent/mcp/debug/stats/db/github/plugin` 等帮助；当前版本是 `1.14.20`，与 `SKILL.md:20` 一致。
- 手册里列出的顶层命令基本都是真实存在的；大多数子命令也都存在，整体不是“乱写”的。

**主要问题**
- `SKILL.md:117` 的 `--` 用法说明是反的：`opencode run -- "审查这个文件" -f ...` 会把后面的 `-f` 当普通文本；正确写法应是 `opencode run "审查这个文件" -f ...`。
- `SKILL.md:428` “全局选项（适用于所有命令）”不准确。`--port`、`--hostname`、`--mdns`、`--cors`、`-m`、`-c`、`-s`、`--fork`、`--prompt`、`--agent` 并不是所有命令都支持。
- `SKILL.md:467` / `SKILL.md:468` 的安全说明有误：`--dangerously-skip-permissions` 不是“批准所有工具调用”，而是批准未被明确拒绝的权限；`--format json` 也不会绕过权限提示，它只改变输出格式。
- `SKILL.md:80` 的 `message` 更准确应写成可变位置参数/数组（帮助里是 `[message..]`），不是单一值。
- `SKILL.md:266` 的 `agent create \` 是 Bash 续行写法；在这个仓库默认的 PowerShell 语境里不适合直接复制执行。

**缺漏**
- 最值得补的是默认 TUI 入口命令 `opencode [project]`；顶层帮助里它是默认命令，但手册没有给出明确示例。
- 次要可补：`opencode mcp auth list`、`opencode debug file status`、`opencode debug wait`。

**结论**
- 命令真实性：基本没问题。
- 参数名/类型：`run` 那张表大体对，但“全局选项”段落和少数说明不准。
- 错误示例：`SKILL.md:124` 那个带 `--` 的例子应改。
- 如果你要，我下一步可以直接帮你把 `SKILL.md` 按这些点最小化修正。