# Existing Repo Adaptation Checklist

给现有 Obsidian 插件接入发布系统时，先做事实探测，再做改造。

## Detect First

### Plugin Identity

- `manifest.json` 是否存在
- 插件 ID 和名称是什么
- 入口文件是 `main.ts`、`src/main.ts` 还是其他结构

### Build System

- `package.json` 中有哪些 scripts
- 使用 `esbuild`、`rollup`、`vite` 还是其他方式
- 构建产物路径在哪里

### Version State

- `package.json.version`
- `manifest.json.version`
- `package-lock.json.version`
- 是否已有版本同步脚本

### UI Surfaces

- 是否已有设置页
- 是否已有调试日志开关
- 是否已有关于/版本展示区

### Deployment State

- 是否已有测试库路径约定
- 是否已有 copy/deploy 脚本
- 是否已有 hash 校验

## Reuse vs Replace

### Prefer Reuse

- 现有 `build` 命令
- 现有设置页
- 现有 logger 或诊断报告
- 现有部署脚本的路径解析逻辑

### Add Missing Pieces

- `releaseCodename`
- `BUILD_ID` 注入
- `DISPLAY_VERSION`
- `version:check`
- `bump:*`
- `build:release`
- test vault hash verify

## Retrofit Sequence

1. 补版本模型
2. 补构建注入
3. 补展示层
4. 补发布命令
5. 补部署与校验
6. 补文档与 AGENTS 规则

## Anti-Patterns

避免这些做法：

- 把代号直接写进 `manifest.version`
- 让普通 `build` 自动 bump
- 把测试库路径写死在业务逻辑源码里
- 默认刷出大量 `info/debug` 控制台日志
- 只改版本号，不做部署校验
