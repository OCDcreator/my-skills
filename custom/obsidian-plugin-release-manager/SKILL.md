---
name: obsidian-plugin-release-manager
description: Create or retrofit a complete release-management workflow for Obsidian plugins. Use this whenever the user mentions Obsidian plugin versioning, manifest/package version sync, release codename, display version, BUILD_ID, release build automation, test vault deployment, or wants an existing Obsidian plugin repo to gain a codename + semver + deployment system. Also trigger for phrases like 测试库部署, test vault, release build, 版本号管理, 版本代号, BUILD_ID, manifest version, package version, plugin deployment, or when the user wants a new Obsidian plugin scaffold to include a ready-to-use release workflow from day one.
---

# Obsidian Plugin Release Manager

为 Obsidian 插件仓库建立一套统一、可复用、低惊喜的发布体系。目标不是只“改一个版本号”，而是把以下能力一次性接好：

- 纯 semver 的 `manifest.json.version`
- 面向用户的展示版本 `Reed vX.Y.Z`
- 构建注入的 `BUILD_ID`
- 普通 `build` 不 bump，`release build` 自动 `+1 patch`
- 测试库部署与哈希校验
- 默认安静的控制台日志策略

这个 skill 同时适用于：

1. **给现有 Obsidian 插件仓库补发布系统**
2. **给新的 Obsidian 插件脚手架直接落完整版本/部署方案**

## What To Detect First

先确认这是不是一个 Obsidian 插件仓库，再决定是“补现有系统”还是“从模板落全套”。

优先检查：

- 是否存在 `manifest.json`
- 是否存在 `package.json`
- 是否有 `main.ts` / `src/main.ts`
- 是否有 `styles.css`
- 是否有 `esbuild`、`rollup`、`vite` 之类的构建入口
- 是否已经存在 settings UI、调试日志、测试库部署脚本

如果这些关键对象都缺失，就把它当成 **新插件脚手架初始化**。  
如果大部分对象已经存在，就把它当成 **现有仓库改造**。

## Default Architecture

默认采用下面这套标准方案，不要每次重新设计一遍。

### 1. Version Contract

- `package.json.version`
- `manifest.json.version`
- `package-lock.json.version`

这三者必须保持一致。

**重要：**

- `manifest.json.version` 永远保持纯 semver，例如 `1.0.3`
- 不要把代号拼进 `manifest.version`
- 公开展示版本使用：

```ts
DISPLAY_VERSION = `${RELEASE_CODENAME} v${APP_VERSION}`;
```

默认推荐代号：

- `releaseCodename = "Reed"`

但这是可配置字段，不要写死在业务逻辑里。

### 2. Build Injection Contract

构建系统默认应注入这三个常量：

- `__APP_VERSION__`
- `__BUILD_ID__`
- `__RELEASE_CODENAME__`

生成规则：

- `APP_VERSION` 来自 `package.json.version`
- `RELEASE_CODENAME` 来自 `package.json.releaseCodename`
- `BUILD_ID = <semver>+<ISO timestamp>`

运行时代码应统一导出：

- `APP_VERSION`
- `BUILD_ID`
- `RELEASE_CODENAME`
- `DISPLAY_VERSION`

### 3. Command Contract

优先落这组脚本命名：

- `npm run version:check`
- `npm run bump:patch`
- `npm run bump:minor`
- `npm run bump:major`
- `npm run build`
- `npm run build:release`

默认语义：

- `build`：只做类型检查 + 生产构建，不 bump
- `build:release`：执行发布链路

发布链路默认顺序：

1. `bump:patch`
2. `version:check`
3. `build`
4. deploy 到 test vault
5. hash verify
6. 校验构建产物内的版本串与 `BUILD_ID`

### 4. Deployment Contract

测试库部署默认支持 **Windows + macOS**。

不要把测试库路径硬编码进业务代码。优先使用 `package.json` 中的自定义配置块，例如：

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

默认复制文件固定为：

- `main.js`
- `manifest.json`
- `styles.css`

发布后必须：

- 对比源与目标的 SHA256
- 校验构建产物中有正确的 `APP_VERSION`
- 校验构建产物中有正确的 `BUILD_ID`
- 提醒在 Obsidian 中重载插件或重启

### 5. Logging Contract

默认日志策略要安静：

- **始终输出**：启动首行版本日志
- **始终输出**：`warn` / `error`
- **仅调试开启时输出**：`info` / `debug`

启动首行建议形态：

```ts
Bookshelf Reed v1.0.3 loaded | BUILD_ID 1.0.3+2026-04-16T08:11:29.213Z
```

如果仓库已有设置页，优先补一个轻量调试分区，而不是重新设计一整套后台系统。

## Workflow

按这个顺序做，避免漏步骤。

### Route A — Retrofit Existing Plugin Repo

1. 识别现有构建系统、插件入口、manifest、package、settings UI
2. 判断已有版本管理哪些部分可复用，哪些必须补齐
3. 引入 `releaseCodename`、`BUILD_ID`、`DISPLAY_VERSION`
4. 补 `version:check` 与 bump 脚本
5. 补 `build:release`
6. 补测试库 deploy + hash verify
7. 补启动版本行和设置页版本/调试区
8. 更新仓库说明，如 `AGENTS.md` / `README.md`

### Route B — New Plugin Scaffold

1. 建立 Obsidian 插件基础结构
2. 从一开始就加 `releaseCodename`
3. 直接落 `buildInfo` / bump script / build inject / release build / deploy verify
4. 设置页直接带版本与调试区
5. 在说明文档中写清发布流程

## Adaptation Rules

优先复用已有约定，避免无意义重命名。

- 如果仓库已有 `build`，保留它的职责，只补 `build:release`
- 如果仓库已有版本脚本，优先增强而不是重写
- 如果仓库已有日志系统，优先补“静默默认 + 首行版本日志”
- 如果仓库没有 settings UI，不要为了调试按钮强行造复杂 UI；可退化为最小版本展示和日志控制

## Files To Read Next

按需读取，不要一次性全加载：

- `references/versioning-pattern.md`：版本、代号、BUILD_ID 约定
- `references/deployment-pattern.md`：测试库部署与校验流程
- `references/repo-adaptation-checklist.md`：现有仓库接入检查清单
- `templates/`：可复制模板与脚本片段

## Output Expectation

完成这类任务时，结果里应明确说明：

- 语义版本如何管理
- 展示版本如何生成
- `BUILD_ID` 如何注入
- `build` 和 `build:release` 的职责边界
- 测试库部署目标路径与校验结果
- 控制台首条版本日志是什么

不要只说“已加版本管理”，要把这几层都交代清楚。
