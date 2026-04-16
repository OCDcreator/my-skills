# Versioning Pattern for Obsidian Plugins

## Goal

把插件版本拆成三层：

1. **semver**：给 Obsidian 和包管理器识别
2. **display version**：给用户界面和控制台展示
3. **BUILD_ID**：给一次具体构建做唯一标识

## Recommended Fields

### `package.json`

- `version`
- `releaseCodename`

示例：

```json
{
  "version": "1.0.3",
  "releaseCodename": "Reed"
}
```

### `manifest.json`

仅保留纯 semver：

```json
{
  "version": "1.0.3"
}
```

## Why `manifest.version` Must Stay Pure Semver

Obsidian 插件系统和很多工具默认假设版本号可比较。  
像 `Reed v1.0.3` 这样的展示版本适合 UI，不适合放进 `manifest.version`。

所以应采用：

- `manifest.version = 1.0.3`
- `DISPLAY_VERSION = Reed v1.0.3`

## Runtime Exports

推荐提供：

```ts
export const APP_VERSION = __APP_VERSION__;
export const BUILD_ID = __BUILD_ID__;
export const RELEASE_CODENAME = __RELEASE_CODENAME__;
export const DISPLAY_VERSION = `${RELEASE_CODENAME} v${APP_VERSION}`;
```

## BUILD_ID

推荐格式：

```text
1.0.3+2026-04-16T08:11:29.213Z
```

建议生成方式：

- 构建时读取 `package.json.version`
- 拼接当前 ISO 时间戳

## Command Responsibilities

- `version:check`：校验 `package.json` / `manifest.json` / `package-lock.json`
- `bump:*`：只做 semver 迭代
- `build`：只构建
- `build:release`：做一次完整可发布构建

## Display Surfaces

`DISPLAY_VERSION` 至少应出现在：

- 插件启动首行日志
- 设置页版本信息
- 调试诊断报告

如果仓库已有“关于”页，也应优先在那里显示。
