# 提取参考（extraction.md）

本文件详述字符串提取的正则规则、压缩文件处理、以及 `scripts/extract.js` 之外的手动技巧。**开始提取前读这里。**

## 优先用脚本

```bash
node ~/.agents/skills/obsidian-plugin-i18n/scripts/extract.js <插件main.js路径>
```

脚本已封装所有规则、引号处理、去重、过滤。除非脚本结果有问题，否则不要手敲 grep。

## 脚本覆盖的提取点

### 函数调用类（高置信度）
这些方法名是 Obsidian API 稳定的，前缀锁定后误匹配率极低：

| 方法 | 用途 | 示例 |
|---|---|---|
| `setName` | 设置项标题 | `setName("Auto backup")` |
| `setDesc` | 设置项描述 | `setDesc("Every X minutes")` |
| `setText` | 通用文字（按钮/标签） | `setText("Save")` |
| `setPlaceholder` | 输入框占位符 | `setPlaceholder("Search...")` |
| `setTooltip` | 悬浮提示 | `setTooltip("Click to save")` |
| `setButtonText` | 按钮文字 | `setButtonText("Commit")` |
| `setHint` | 设置项提示 | `setHint("Requires restart")` |
| `setTitle` | 标题/标签页名 | `setTitle("Source Control")` |
| `appendText` | 追加文字 | `appendText("...")` |
| `addHeading` | 设置区标题 | `addHeading("Git", "h2")` |
| `renderMarkdown` | 渲染的 MD 文本 | `renderMarkdown("# Note")` |
| `new Notice` | 通知消息 | `new Notice("Saved!")` |
| `new Error` | 错误消息 | `new Error("Not a git repo")` |

### 对象字段类（中置信度，需人工复核）
插件定义命令、菜单、设置时用对象字面量：

```js
addCommand({
  id: "commit",
  name: "Create commit",        // ← 命令显示名
  callback: () => {...}
})

addRibbonIcon("icon", "Source Control", () => {...})
//                   ↑ tooltip

addMenuItem({ name: "...", description: "..." })
```

字段：`name`、`description`、`placeholder`、`tooltip`。

**风险**：`name:` 在代码里非常常见（变量赋值、对象序列化），会有误匹配。脚本已过滤纯标识符（如 `name:autoSaveInterval`），但仍有噪音。**复核时重点看 field:* 类条目，剔除明显是代码而非 UI 文本的。**

## 脚本没覆盖但可能需要的

### `setButtonText` 变体与 `addOption`
某些插件用 `new Setting().addDropdown(dd => dd.addOption("key", "显示文字"))`：
```js
addOption("auto", "Automatic")   // ← "Automatic" 要翻
```
正则：`addOption\\(\\s*"[^"]+"\\s*,\\s*${STRING}`。脚本暂未含，遇到大量 dropdown 的插件时手动补。

### `setAttr` / HTML 文本
极少见，通常不用管。

## 压缩文件处理

### 判断是否压缩
```bash
wc -l main.js
```
- **正常多行（> 100 行）**：直接提取，正则按行/全文都能跑
- **压缩单行（≤ 50 行但文件 > 100KB）**：正则全文匹配没问题（脚本用 `g` flag 全文扫），但**改写时要格外小心**：
  - 压缩代码引号密集，`\\"` 转义多，字符串边界判断容易错
  - 务必改写后 `node --check main.zh-cn.js` 校验
  - 可选：用 prettier 美化后再改（`npx prettier --parser babel main.js`），改完再压回去（但不压也能用，Obsidian 不在乎格式）

### 美化（仅当改写频繁出错时）
```bash
# 备份后美化
cp main.js main.js.orig
npx prettier --parser babel main.js > main.pretty.js
# 在 main.pretty.js 上做提取+改写，改完替换
```
美化会改变字符 offset，所以**美化后再提取一次**，别用美化前的 offset。

## 写回时的转义

提取阶段脚本把 `\n` `\"` 反转义成真实字符方便阅读。写回 main.js 时必须重新转义：

| 原文（提取显示） | 写回字面量 |
|---|---|
| 换行（真实） | `\n` |
| `"` 在双引号串里 | `\"` |
| `\` | `\\` |
| 模板串里的 `${...}` | 原样保留（模板串里 `\n` 也算转义，按需处理） |

**最稳妥的写回方式**：不做字符串级手工拼接，而是用 offset 定位原始 match 片段，整体替换。脚本输出的 `match` 字段就是完整匹配片段，可直接用来 `.replace(match, 新片段)`。

## 排查提取遗漏

跑完脚本后若怀疑遗漏，用这些 grep 快速查漏：

```bash
# 查 setText 但参数像字符串的（脚本可能因引号变体漏掉）
grep -oE 'setText\("[^"]{1,80}"\)' main.js | head

# 查疑似 UI 文本的英文短语（含空格的引号串）
grep -oE '"[A-Z][a-z]+ [a-z ]+"' main.js | sort -u | head
```
