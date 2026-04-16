# Release Build Checklist

## Before Build

- `package.json.version` / `manifest.json.version` / `package-lock.json.version` 一致
- `releaseCodename` 已配置
- `buildInfo` 导出 `DISPLAY_VERSION`
- 日志策略为“默认安静”

## Build

- 运行 `npm run bump:patch`
- 运行 `npm run version:check`
- 运行 `npm run build`

## Deploy

- 复制 `main.js`
- 复制 `manifest.json`
- 复制 `styles.css`

## Verify

- SHA256 对比源和测试库文件
- 构建产物中存在 `APP_VERSION`
- 构建产物中存在 `RELEASE_CODENAME`
- 构建产物中存在 `BUILD_ID`
- 构建产物中存在启动版本日志模板

## Final Check

- Obsidian 中重载插件或重启
- 在控制台确认首条版本日志正确
