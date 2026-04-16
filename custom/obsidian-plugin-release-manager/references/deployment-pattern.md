# Test Vault Deployment Pattern

## Goal

让 Obsidian 插件在本地测试库中快速验证，同时避免“构建成功但实际没部署对”的假象。

## Supported Defaults

默认支持：

- Windows
- macOS

不要把测试库路径写死在业务代码中。优先放在 `package.json` 的自定义配置里。

## Recommended Config Shape

```json
{
  "obsidianRelease": {
    "testVaults": {
      "win32": "C:\\Users\\name\\Desktop\\Write\\testvault",
      "darwin": "/Users/name/Desktop/Write/testvault"
    }
  }
}
```

## Runtime Deliverables

默认部署这些文件：

- `main.js`
- `manifest.json`
- `styles.css`

## Release Flow

推荐固定顺序：

1. bump patch
2. version consistency check
3. production build
4. copy runtime deliverables to test vault plugin directory
5. SHA256 compare source vs target
6. inspect built artifact for version/build strings
7. reload plugin or restart Obsidian

## Verification

至少做两层校验：

### 1. File Hash Verification

比较源文件与测试库文件哈希，确认复制无误。

### 2. Version String Verification

构建产物中应包含：

- `APP_VERSION`
- `RELEASE_CODENAME`
- `BUILD_ID`
- 启动版本日志模板

## Console Verification

理想情况下，部署后要确认 Obsidian 控制台首条插件日志显示：

```text
<PluginName> Reed v1.0.3 loaded | BUILD_ID 1.0.3+...
```

## Quiet-by-Default Logging

发布后的默认行为应尽量安静：

- 首行版本日志始终可见
- `warn` / `error` 始终可见
- `info` / `debug` 仅在用户开启调试时输出

这样既能确认部署成功，也不会让控制台被常规日志刷屏。
