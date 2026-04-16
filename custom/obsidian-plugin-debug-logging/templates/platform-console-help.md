# Platform Console Help Template

Use this copy in an Obsidian plugin settings page, README, or troubleshooting modal.

## Chinese

```text
调试日志会输出在 Obsidian 开发者工具的 Console（控制台）中，可用于查看、复制日志并排查插件或界面问题。

Windows：
- 快捷键：Ctrl + Shift + I
- 菜单路径：帮助 → 开发者工具 → 打开开发者工具

macOS：
- 快捷键：Cmd + Option + I
- 菜单路径：Obsidian → 开发 → 开发者工具 → 显示 JavaScript 控制台

打开开发者工具后，切换到 Console（控制台）标签。
如果不方便手动复制 Console，请使用“复制最近诊断”或“导出日志文件”。
```

## English

```text
Debug logs are written to the Obsidian Developer Tools Console. Use them to inspect, copy, and troubleshoot plugin or UI issues.

Windows:
- Shortcut: Ctrl + Shift + I
- Menu: Help → Developer Tools → Open Developer Tools

macOS:
- Shortcut: Cmd + Option + I
- Menu: Obsidian → Developer → Developer Tools → Show JavaScript Console

After opening Developer Tools, switch to the Console tab.
If manually copying Console output is inconvenient, use "Copy recent diagnostics" or "Export log file".
```

## Default Export Path Hints

```text
Windows: %USERPROFILE%\Desktop\<PluginName>Logs
macOS: ~/Desktop/<PluginName>Logs
```

Store Windows and macOS defaults separately. Do not reuse a Windows path on macOS or a macOS path on Windows.
