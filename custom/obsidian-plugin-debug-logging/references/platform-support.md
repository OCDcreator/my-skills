# Platform Support: Windows + macOS

Obsidian 插件运行在 Electron 中。日志 core 应跨平台共享，但用户可见路径、控制台入口和导出目录必须区分 Windows 与 macOS。

## Shared Logic

这些逻辑应完全共享：

- `createLogger(scope)`
- 日志级别策略
- debug 开关
- inline serialization 开关
- 最近日志 ring buffer
- 诊断报告结构
- 导出文件命名，例如 `<plugin-id>-debug-<timestamp>.log`
- `BUILD_ID` 注入与启动首行
- 去重、节流、截断、敏感字段过滤

## Platform-Specific Logic

这些逻辑需要平台分支：

| Concern | Windows | macOS |
|---|---|---|
| platform key | `windows` | `macos` |
| default export hint | `%USERPROFILE%\\Desktop\\<PluginName>Logs` | `~/Desktop/<PluginName>Logs` |
| placeholder | `C:\\Users\\You\\Desktop\\<PluginName>Logs` | `/Users/you/Desktop/<PluginName>Logs` |
| console shortcut | `Ctrl + Shift + I` | `Cmd + Option + I` |
| console menu | `Help → Developer Tools → Open Developer Tools` | `Obsidian → Developer → Developer Tools → Show JavaScript Console` |
| path separator display | backslash common | slash common |

Linux can be added as `linux`, but do not collapse macOS into `unix` when the requirement is Windows + macOS.

## Recommended Helpers

```ts
type DebugPlatformKey = 'windows' | 'macos' | 'linux';

function getDebugPlatformKey(): DebugPlatformKey {
  if (process.platform === 'win32') {
    return 'windows';
  }
  if (process.platform === 'darwin') {
    return 'macos';
  }
  return 'linux';
}
```

If the project intentionally supports only Windows/macOS, still handle other platforms gracefully by falling back to macOS-style slash paths or asking the user to choose a directory.

## Export Directory

Preferred behavior:

1. Read saved path for current platform.
2. If empty or missing, offer a folder picker.
3. If picker is unavailable, let the user type a path.
4. If user picks a path, ask whether to save it as the default for this platform.
5. Create the directory before writing the report.
6. Return the full output path in the Obsidian `Notice`.

Do not auto-write logs forever. Export should be user initiated unless a project has an explicit support-bundle feature.

## File System Notes

- Use Node `path.join()` for actual file writes.
- Use `os.homedir()` to build default suggestions.
- Preserve native path strings in UI where possible.
- In diagnostic reports, label the path platform so copied reports are understandable across machines.
- Avoid assuming a Windows path works on macOS or vice versa; store separate defaults.

## Console Guidance Text

Settings UI should show both platforms even when the user is currently on one platform. Users often follow support instructions from another device, and developers may ask for cross-platform reproduction.

Minimum text:

- Debug logs are written to Obsidian Developer Tools Console.
- Windows: `Ctrl + Shift + I`, then Console tab.
- macOS: `Cmd + Option + I`, then Console tab.
- The diagnostic report can be copied or exported without manually opening Console.
