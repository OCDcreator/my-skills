---
name: obsidian-plugin-i18n
description: Use when the user wants to translate/localize an Obsidian plugin into Chinese (or another language) — extract all user-facing strings from a plugin's main.js, translate them, optionally pop up a native GUI review window for human to approve/edit translations, then either rewrite main.js in place or export an i18n translation table. Trigger on phrasings like "汉化插件", "翻译这个插件", "plugin i18n", "把 XX 插件变中文", "审核译文", "extract translatable strings from plugin", or when a plugin path is given with a translation request. Also use for re-running translation after a plugin updates.
---

# Obsidian 插件汉化（i18n）

把任意 Obsidian 插件的界面字符串提取出来、翻译成目标语言（默认简体中文），并产出可直接使用的汉化成品。

## 工作原理（先理解，再动手）

Obsidian 插件是**压缩/混淆后的单个 `main.js`**。用户可见的字符串都通过 Obsidian API 的固定方法暴露，例如：

```js
setName("Auto backup")           // 设置项标题
setDesc("Backup every X minutes")// 设置项描述
setText("Save")                  // 按钮文字
setPlaceholder("Search...")      // 输入框占位符
new Notice("Saved!")             // 通知
addCommand({ name: "Commit" })   // 命令名
```

这些方法的调用模式是稳定的、可正则匹配的——这是整个提取的基石。i18n 插件（polyipseity 生态外的 eondrcode/obsidian-i18n）用的就是同一思路：正则抓调用 → 翻译 → 改写。

**关键事实**：绝大多数 Obsidian 插件没有内置 i18n 框架，字符串是硬编码英文。汉化 = 找到这些硬编码字符串并替换。少数插件（自带 `lang/` 目录）已有 i18n，那种优先改语言文件，见下方"特殊情况"。

## 标准流程

### 第 0 步：定位与探查

拿到插件路径后，先读清楚再动手：

1. 读 `manifest.json` 确认插件 id / name / version
2. 看 `main.js` 行数（`wc -l`）。**压缩文件（行数少、文件大）提取无影响**——脚本全文扫描，实测能正确处理。但**改写时压缩代码引号密集，需格外小心转义**，务必 `node --check` 校验（详见 references/extraction.md）
3. 检查是否有 `lang/` 目录或 `locale/` 目录 —— 若有，插件自带 i18n，走"特殊情况"分支
4. 用 `grep -oE` 统计各类调用数量，估算工作量（< 200 条轻松，> 500 条建议分批）

### 第 1 步：提取待翻译字符串

**提取规则（已验证有效，覆盖 Obsidian 核心 API）**：

```
setText("...")            setDesc("...")           setName("...")
setPlaceholder("...")     setTooltip("...")        setButtonText("...")
setHint("...")            setTitle("...")          appendText("...")
addHeading("...")         renderMarkdown("...")
new Notice("...")         new Error("...")

# 对象字面量字段（命令/设置定义）
name: "..."               description: "..."       text: "..."
placeholder: "..."        tooltip: "..."           title: "..."
```

完整正则清单和提取脚本见 `references/extraction.md`。**优先用 `scripts/extract.js`** —— 它封装了所有正则、处理了引号转义、输出结构化 JSON，比手敲 grep 可靠得多。

提取出的每条记录长这样：

```json
{
  "match": "setName(\"Auto backup interval\")",
  "method": "setName",
  "original": "Auto backup interval",
  "location": "charOffset 12345"
}
```

### 第 2 步：清洗与过滤

提取后必做（这步决定质量）：

- **范围原则（先定范围再清洗）**：只翻【用户在界面能看到的英文 UI 文案】——设置项标题/描述、按钮、命令名、placeholder、tooltip。**必须跳过**：①非英文（zh-cn.json 可能混入作者内置的德/法/西/葡/日/韩/俄等多语言样本，逐条判断）②代码标识符、模型 ID（如 `claude-sonnet-4-5`）、URL、颜色码、CLI 命令名（小写连字符如 `add-dir`）③内部 i18n key（如 `settings.xxx.xxx`，是程序内部键不是给用户看的）。拿不准某条是否用户可见 → 列入"待确认"问用户，不要硬翻。 <!-- 2026-06-29 strengthen: LESSON#5 -->
- **剔除非英文 / 已是目标语言的字符串**（比如插件可能部分已汉化）
- **剔除纯变量 / 代码表达式**：`setText(e)`、`setText(this.config.x)` 不是待翻译文本
- **保留模板占位符**：`${n}`、`{{date}}`、`%s`、`{0}` 必须原样带入译文，**绝不能翻译或删除**
- **剔除过短的噪音**：单个字母、纯标点、纯数字（除非是 `setPlaceholder(String(...))` 这类要整体跳过）
- **合并同义重复**：同一字符串出现多次只翻译一次，复用译文

### 第 3 步：翻译

两种模式，**默认 agent 直译**：

**模式 A — agent 直接翻译**（默认，零配置）
逐条给出译文。规则：
- 简洁、符合 Obsidian / 软件界面中文习惯（"Save" → "保存"，不是"拯救"）
- 保留占位符和标点结构
- 命令名、按钮文字用动词；描述用说明句
- 上下文很重要：`name` 在 `addCommand` 里是命令名，在 `addSetting` 里是设置标题，译文语气不同

**模式 B — 调用翻译 API**（用户要求时，或量大时）
用户指定 API（OpenAI / DeepL / 百度等）。批量发送时：
- 把字符串分组打包（每批 ≤ 50 条或 ≤ 4KB）
- prompt 要求"只返回译文，逐行对应"
- 拿到结果后按顺序回填，校验条数一致
- 具体调用模板见 `references/translation-api.md`

### 第 3.5 步：GUI 人工审核（推荐，可选）

翻译完之后、产出成品之前，**强烈建议**让人在原生窗口里审核一遍。提取的字符串难免有误匹配（尤其 `field:name`），译文也需要人工校对——这一步能极大提升最终质量。

**做法**：把翻译结果转成审核台输入格式，调用桥接脚本弹窗：

```bash
# 1. 把 extract.js 的产物 + 翻译结果，组装成 review_in.json
#    （每条要含 original / translation / method / defaultEnabled）
# 2. 调用桥接脚本——会弹出 EUI-NEO 原生窗口
node scripts/review_bridge.js <review_in.json> [review_out.json]
```

桥接脚本会：
1. 启动 `bin/review_gui.exe`（自动）
2. 弹出原生窗口，显示每条：[勾选框] [方法] [英文原文] [译文输入框]
3. **阻塞等待**人在窗口里操作（勾选要/不要、改译文）
4. 人点"应用并导出"→ 窗口自动关闭 → 脚本读到 `review_out.json` 退出
5. stdout 输出 JSON 摘要：`{status, enabled, entries:[{id,original,translation}]}`

**审核台窗口效果**（对标 obsidian-i18n 插件的逐行审核）：
```
┌─ i18n Review Console ──────────────────────────────┐
│ plugin@version  ·  N strings  ·  X enabled         │
├────────────────────────────────────────────────────┤
│ ☑ [setName] Auto backup       [自动备份      ]      │
│ ☑ [setDesc] Every X minutes   [每 X 分钟    ]      │
│ ☐ [field:name] open-in-new-tab[             ] ←跳过 │
│ ...（可滚动）                                       │
├────────────────────────────────────────────────────┤
│  [全选] [全不选]              [应用并导出]          │
└────────────────────────────────────────────────────┘
```

**拿到审核结果后**：
- `enabled: true` 的条目 → 进入成品产出（用其 `translation`）
- `enabled: false` 的条目 → 跳过（人判定为误匹配/不需要翻）
- `status: "cancelled"`（人没点导出就关窗）→ 中止，不产出

详见 `references/gui-review-design.md`。

**关于 review_gui.exe 的来源**：
- 首次使用需编译：运行 `review_gui/build_review_gui.bat`（需 VS 2022 MSVC 14.44+ + Git + CMake）
- 编译后 `bin/review_gui.exe` 是静态链接的独立程序，**别人拿到 skill 即可直接用，无需编译器**
- 若 exe 不存在，回退到"纯文本审核"：把清单打印出来让人口述修改

### 第 4 步：产出成品

**默认产出两份，让用户选用**：

#### 成品 1：翻译清单（中间产物，必产）
导出 `lang/<lang>-translation.json`：

```json
{
  "plugin": "obsidian-git",
  "version": "2.x",
  "sourceLanguage": "en",
  "targetLanguage": "zh-cn",
  "extractedAt": "2026-06-28",
  "count": 149,
  "entries": [
    { "match": "setName(\"Auto backup\")", "original": "Auto backup", "translation": "自动备份" }
  ]
}
```

用途：人工复核、版本对比、增量更新（插件升级后只翻新增的）。

#### 成品 2a：改写后的 main.js（默认推荐）
直接在 main.js 里把英文字符串替换成译文，产出 `main.zh-cn.js`（**不要覆盖原文件**）。

替换规则（**严格遵守，否则会破坏代码**）：
- 只替换字符串**字面量的内容**，不动引号、不动方法名、不动周边代码
- `setName("Auto backup")` → `setName("自动备份")`，引号和括号原样保留
- 模板字符串里的 `${...}` 表达式**逐字保留**
- 替换前对原 `main.js` 做备份（`.bak`）
- 替换后用 `node --check main.zh-cn.js` 验证语法没坏

用户确认无误后，再覆盖到 `main.js`。

#### 成品 2b：i18n 插件导入包
若用户用 eondrcode/obsidian-i18n 插件，导出它兼容的格式（`dict` 映射）：

```json
{
  "dict": {
    "setName(\"Auto backup\")": "自动备份",
    "setDesc(\"Backup every X minutes\")": "每 X 分钟备份一次"
  }
}
```

### 第 5 步：验证与交付

- 改写版：`node --check` 语法校验 + 抽查 5 条替换是否正确
- 告知用户：需重启 Obsidian 才能生效；插件更新后需重跑（或用清单做增量）
- 报告统计：提取 N 条、过滤掉 M 条、翻译 K 条、跳过 L 条（含原因）

## 特殊情况

### 路线 A/B：i18n 插件协作（重点）

许多仓库装了 **eondrcode/obsidian-i18n** 插件，它会扫描插件、按 AST 提取字符串、
生成 `lang/zh-cn.json`（结构 `{manifest, description, dict}`，dict 的 key 是调用片段
如 `setName("...")`，未翻译时 value==key）。i18n 插件还能读 zh-cn.json 回写 main.js
（"应用译文"按钮，且可一键还原）。

**这种情况下技能和 i18n 插件分工协作，靠 `lang/zh-cn.json` 文件桥接，零耦合**：
i18n 插件负责提取+回写（它跑在 Obsidian 内），技能负责翻译（它跑在终端用 LLM，插件自己做不到）。

**第 0.5 步（必做）：检测 i18n 环境 + 用 AskUserQuestion 让用户选路线**

检测两项：
1. 仓库 `.obsidian/plugins/i18n/` 是否存在（装了 i18n 插件）
2. 目标插件 `lang/zh-cn.json` 是否存在且 `dict` 非空（已被 i18n 插件提取过）

然后 AskUserQuestion 给用户两选一：

| 路线 | 做法 | 适用 |
|------|------|------|
| **A：用 i18n 插件提取**（推荐，若已装） | 让用户在 Obsidian 里对目标插件点 i18n 插件的"提取"，生成/刷新 `lang/zh-cn.json`，agent 读它继续。提取质量最高（AST 级，比正则准）。回写也交给 i18n 插件（agent 只填 zh-cn.json，不碰 main.js）。 | 仓库装了 i18n 插件 |
| **B：全自动** | agent 直接跑 `scripts/extract.js` 自己提取，不依赖 i18n 插件。产出 `lang/<lang>-translation.json` + 改写 `main.zh-cn.js`（兜底，不覆盖原文件）。 | 没装 i18n 插件，或想独立产出 |

**路线 A 的完整流程**（这是和 i18n 插件协作的核心）：

1. 用户在 Obsidian 对目标插件点 i18n 插件"提取" → 生成 `lang/zh-cn.json`
2. agent 读 `zh-cn.json`，从 `dict` 抽出所有 key（**未翻译 = value==key**；若 value 已是中文或非英文，视为已翻，跳过）
3. 跑翻译记忆库 diff（见下方"翻译记忆库"）：复用旧译文 + 只翻新增
4. LLM 翻译需翻条目，把每条转成 `{key, translation, enabled:true}` 喂审核台（可选）
5. 跑 `node scripts/apply-to-i18n.js <翻译结果.json> <zh-cn.json路径>`：把译文填进 dict 的 value（保留 manifest/description 段，自动备份原文件）
6. 跑 `node scripts/memory.js save <pluginId> <version> <翻译结果.json>`：更新记忆库
7. 告诉用户：**去 Obsidian 点 i18n 插件的"应用译文"**，即回写 main.js 生效（可"还原"撤销）

**apply-to-i18n.js 的翻译结果 JSON 格式**：
```json
{
  "plugin": "claudian", "targetLanguage": "zh-cn",
  "entries": [
    {"key": "setName(\"Auto backup\")", "translation": "自动备份", "enabled": true},
    {"key": "setDesc(\"...\")", "translation": "...", "enabled": false}
  ]
}
```
`translation` 字段填**纯目标语言译文**（字符串字面量的新内容，不含外壳）。apply 脚本会自动把它
重新包装进 key 的外壳里作为 value。

`enabled:false` 的条目 apply 时跳过（保持 value==key 原样）；空译文或 ==原文字面量 的也跳过。

### ⚠️ 路线 A 的关键安全规则（崩溃教训，必读）

i18n 应用译文时是**整段替换**：拿 dict 的 key（调用片段如 `Notice("...")`）去 main.js 匹配整段，
替换成 value。所以 **value 必须保留 key 的外壳**（方法名、括号、引号、模板变量 `${...}`），
只换里面的字符串内容。

- ✗ 致命错误：key=`Notice("Failed to save")` value=`保存失败`
  → i18n 替换后变成 `new X.保存失败;`，`Notice(` 和 `)` 丢了，**main.js 语法崩，插件无法加载**
- ✓ 正确：key=`Notice("Failed to save")` value=`Notice("保存失败")`
  → 替换后 `new X.Notice("保存失败")`，合法

`apply-to-i18n.js` 已内置这个外壳保留逻辑（`rewrap` 函数）：自动提取 key 里的第一个字符串字面量，
换成译文，保留其余部分。模板串 `` `...${var}...` `` 里的 `${var}` 会原样保留在译文里。
key 里找不到字符串字面量的条目会被跳过（noLiteral），不会生成破坏性 value。

### 翻译后必须验证（防止把插件搞崩，必做）

apply 之后、让用户点"应用译文"之前，**必须先验证 main.js 不会被改坏**：

1. **node --check 预检**：在 main.js 副本上模拟 i18n 整段替换，再 `node --check`：
   ```bash
   cp main.js /tmp/main_sim.js
   # 用 node 把 zh-cn.json 里 value!=key 的条目逐个 replace 进副本
   node -e "const fs=require('fs');const d=JSON.parse(fs.readFileSync('<zh-cn.json>','utf-8'));let s=fs.readFileSync('<副本>','utf-8');for(const[k,v]of Object.entries(d.dict)){if(v!==k)s=s.split(k).join(v)}fs.writeFileSync('<副本>',s)"
   node --check /tmp/main_sim.js && echo "✓ 语法安全" || echo "✗ 会崩，必须回查译文"
   ```
   `node --check` 报错 → 立刻定位是哪条 value 破坏了语法（报错行号附近），修正后重跑。
2. **应用后自检（用 autodebug 技能）**：用户在 Obsidian 点"应用译文"后，调
   `obsidian-plugin-autodebug` 技能抓控制台错误：
   - `obsidian dev:errors`（抓最近错误）+ `obsidian dev:console limit=100`
   - 若 claudian 报 `SyntaxError` / 加载失败 → 译文有问题，让用户用 i18n"还原"撤销，
     再回查 node --check 漏掉的条目（多半是模板串 `${var}` 占位符被误删/误改）
   - autodebug 技能能自动 reload + 截图 + DOM 检查，定位更准

这两个环节是路线 A 的安全网。**绝不在没跑 node --check 的情况下让用户应用译文**。

**路线 B**（无 i18n 插件）：走标准流程第 1-4 步（extract.js 提取 → 翻译 → 改写 main.zh-cn.js），
改写后同样必须 `node --check main.zh-cn.js` 校验。记忆库 key 用 `original` 字段。

### 翻译记忆库（增量复用，跨次翻译省力）

插件更新后，绝大多数字符串没变，重复翻译是浪费。技能用**集中式记忆库**复用旧译文：
存 `~/.agents/skills/obsidian-plugin-i18n/memory/<pluginId>@<version>.json`，
按插件 id + 版本隔离。流程：

1. 提取后，把当前 key 列表写成 `{pluginId, keys:[...]}`（路线 A：zh-cn.json 的 dict key；路线 B：extract.js 的 original）
2. 跑 `node scripts/memory.js diff <pluginId> <version> <keysFile>`，得到三类：
   - **reuse**：记忆库有且当前还在 → 直接用旧译文，**不重译**
   - **need**：当前有但记忆库没有 → 送 LLM 翻译
   - **stale**：记忆库有但当前消失（插件删了该字符串）→ 标记留存，不删（下次可能回来）
3. 只把 need 条目送翻译，reuse 直接合并
4. 翻译完跑 `node scripts/memory.js save <pluginId> <version> <translationsFile>` 更新记忆库

   **⚠️ save 的输入语义**：`<translationsFile>` 必须是【当前全部已翻译条目】（从 zh-cn.json 导出所有 `value!=key` 的条目），**不是"本次新增"**。因为 save 用"当前列表 vs 记忆库"区分 active/stale —— 只传本次新增会把之前翻过的误判为 stale。正确做法：`save` 前先从 zh-cn.json 导出完整译文列表传入。 <!-- 2026-06-29 add_new: LESSON#4 -->

记忆库按 key 原样索引（不区分 `Notice(...)` / `name: "..."` 形态）。首次翻译记忆库为空 → 全量翻；之后每次只翻 diff 出的 need，这是技能相对 i18n 插件（每次全量）的核心效率优势。

### 压缩成单行的 main.js
`wc -l` 显示 ≤ 50 行但文件很大 → 是压缩文件。提取脚本已处理，但**改写时要格外小心引号转义**（压缩代码里引号嵌套复杂）。务必 `node --check` 校验。

### 字符串里含 HTML / Markdown
`renderMarkdown("# Title")`、`setDesc("<b>Note</b>")` 这类，翻译时保留标签/语法，只译文字部分。

### 增量更新（插件升级后）
用**翻译记忆库**（见上方"翻译记忆库"节）：提取新版的 key 列表后跑 `memory.js diff`，
自动分出 reuse（复用旧译文）/ need（新增需翻）/ stale（失效标记留存），
只翻 need。无需手工比对清单。

## 何时读 references / 用脚本

- `references/extraction.md` —— 开始提取前读，看完整正则清单和压缩文件处理技巧
- `references/translation-api.md` —— 用户要求调 API 时读，看 OpenAI/DeepL/百度的调用模板
- `scripts/extract.js` —— 提取脚本（路线 B），`node scripts/extract.js <main.js路径>`
- `scripts/memory.js` —— 翻译记忆库（增量复用），`load/diff/save` 三个子命令
- `scripts/apply-to-i18n.js` —— 路线 A 专用：把译文填进 i18n 插件的 `lang/zh-cn.json`

## 不做什么

- 不做运行时拦截 / DOM 替换 —— 那需要 Obsidian 运行环境，skill 在终端里没有
- 不翻译代码逻辑、注释、变量名
- 不猜译 —— 拿不准的字符串列入"待确认"让用户定，而不是硬翻
- 不覆盖原始 main.js —— 永远先产 `.zh-cn.js` 或备份后再改
