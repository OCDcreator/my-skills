# Template: Debug Settings Section

Adapt this to the target plugin's settings tab style, i18n system, and existing settings persistence.

## Required Settings Fields

```ts
enableDebugLogging: boolean;
inlineSerializedDebugLogArgs: boolean;
debugLogPaths: {
  windows: string;
  macos: string;
  linux?: string;
};
```

## Required Controls

```ts
new Setting(containerEl)
  .setName('调试日志 / Debug logging')
  .setDesc('关闭时仅输出启动版本行、警告和错误；开启后输出 info/debug 级别日志。')
  .addToggle((toggle) => toggle
    .setValue(plugin.settings.enableDebugLogging)
    .onChange(async (value) => {
      plugin.settings.enableDebugLogging = value;
      plugin.applyLoggerSettings();
      await plugin.saveSettings();
    }));

new Setting(containerEl)
  .setName('内联序列化调试参数')
  .setDesc('开启后，debug 日志里的对象会转成文本，便于直接复制给开发者。')
  .addToggle((toggle) => toggle
    .setValue(plugin.settings.inlineSerializedDebugLogArgs)
    .onChange(async (value) => {
      plugin.settings.inlineSerializedDebugLogArgs = value;
      plugin.applyLoggerSettings();
      await plugin.saveSettings();
    }));

new Setting(containerEl)
  .setName('诊断操作')
  .setDesc('复制诊断报告、导出日志文件、清空最近日志缓存，或复制当前版本信息。')
  .addButton((button) => button
    .setButtonText('复制最近诊断')
    .setCta()
    .onClick(async () => {
      await plugin.copyDiagnosticReport('settings-copy');
    }))
  .addButton((button) => button
    .setButtonText('导出日志文件')
    .onClick(async () => {
      await plugin.exportDiagnosticReport('settings-export');
    }))
  .addButton((button) => button
    .setButtonText('清空日志缓存')
    .onClick(() => {
      plugin.clearDiagnosticLogs();
    }))
  .addButton((button) => button
    .setButtonText('复制版本号')
    .onClick(async () => {
      await navigator.clipboard.writeText(`${plugin.getDisplayVersion()} | BUILD_ID ${plugin.getBuildId()}`);
    }));
```

## Platform Path Control

```ts
const platformKey = getDebugPlatformKey();

new Setting(containerEl)
  .setName('日志默认路径')
  .setDesc(`保存 ${platformKey} 调试日志文件的默认文件夹。Windows 与 macOS 分别保存。`)
  .addText((text) => text
    .setPlaceholder(getDebugPathPlaceholder(platformKey))
    .setValue(plugin.settings.debugLogPaths[platformKey] ?? '')
    .onChange(async (value) => {
      plugin.settings.debugLogPaths[platformKey] = value.trim();
      await plugin.saveSettings();
    }))
  .addButton((button) => button
    .setButtonText('选择路径')
    .onClick(async () => {
      const pickedPath = await plugin.pickDiagnosticExportDirectory();
      if (!pickedPath) {
        return;
      }
      plugin.settings.debugLogPaths[platformKey] = pickedPath;
      await plugin.saveSettings();
    }));
```

## Version + Console Help

```text
当前版本：<DISPLAY_VERSION or manifest.version>
BUILD_ID：<BUILD_ID>
Windows：Ctrl + Shift + I → Console
macOS：Cmd + Option + I → Console
也可以直接复制/导出诊断报告，无需手动复制 Console。
```
