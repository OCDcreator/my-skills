# GUI 审核台设计方案

## 目标

复刻 obsidian-i18n 插件的"逐条审核翻译"窗口效果，但用 EUI-NEO 原生窗口承载，
让 skill 调用时自动弹出，人类在窗口里勾选/编辑译文，完成后 agent 拿到结果继续。

这是「agent ↔ 人类 GUI 交互」的通用基座，i18n 只是第一个应用。
未来任何需要人类介入审核的 skill 都能复用 review_gui.exe。

## 目标窗口效果（对标 i18n 插件 Setting 列表）

```
┌─ i18n Review Console ────────────────────────────────────┐
│ obsidian-git@2.5.0  · 149 strings  · 0/149 reviewed       │  ← 顶栏：插件信息+进度
├──────────────────────────────────────────────────────────┤
│ ┌────────────────────────────────────────────────────┐   │
│ │ ✓ [setName] Auto backup interval        [自动备份间隔]│   │  ← 每行一条
│ │   context: setting title                            │   │
│ │ ✓ [setDesc] Every X minutes             [每 X 分钟]  │   │
│ │ ✓ [new Notice] Saved successfully       [保存成功]   │   │
│ │ ☐ [field:name] open-in-new-tab          [跳过的代码] │   │  ← 取消勾选=跳过
│ │ ...                                                 │   │
│ │  (scrollView 内滚动，149 行)                         │   │
│ └────────────────────────────────────────────────────┘   │
├──────────────────────────────────────────────────────────┤
│  [全选] [全不选] [仅显示未审]        143/149  [应用并导出] │  ← 底栏：批量操作+提交
└──────────────────────────────────────────────────────────┘
```

每行 = 1 个 checkbox（启用/跳过） + 原文标签 + 译文输入框（可编辑）
人类操作：勾选/取消决定要不要这条、直接改译文框里的文字、滚动浏览
完成点「应用并导出」→ 程序写 review_out.json 后退出

## 数据契约

### 输入 review_in.json（agent 写，exe 读）

```json
{
  "plugin": "obsidian-git",
  "version": "2.5.0",
  "sourceLanguage": "en",
  "targetLanguage": "zh-cn",
  "entries": [
    {
      "id": "0",
      "method": "setName",
      "original": "Auto backup interval",
      "translation": "自动备份间隔",
      "context": "setting title",
      "defaultEnabled": true
    }
  ]
}
```

- `translation` 是 agent 预填的译文，人类可改
- `defaultEnabled` 决定 checkbox 初始状态（提取置信度高的默认勾选，field:* 类默认不勾）

### 输出 review_out.json（exe 写，agent 读）

```json
{
  "plugin": "obsidian-git",
  "version": "2.5.0",
  "targetLanguage": "zh-cn",
  "status": "applied",
  "reviewedAt": "2026-06-28",
  "entries": [
    { "id": "0", "original": "Auto backup interval", "translation": "自动备份间隔", "enabled": true },
    { "id": "3", "original": "open-in-new-tab", "translation": "", "enabled": false }
  ]
}
```

- `enabled: false` = 人类取消勾选，agent 据此跳过这条
- `translation` = 人类最终确认/修改的译文
- `status`: "applied"(正常完成) / "cancelled"(关窗放弃) / "partial"(只审了一部分)

## 进程协议

```
agent (node)                          review_gui.exe
    │                                       │
    │── write review_in.json ──────────────>│ (启动时读)
    │── spawn review_gui.exe in.json out.json
    │                                       │ (显示窗口，人操作)
    │   (阻塞等待 exe 退出)                  │
    │                                       │
    │<──── exit code 0 + review_out.json ───│ (人点导出后写文件+退出)
    │                                       │
    │── read review_out.json                │
    │── 按结果执行写回 main.js               │
```

- exe 命令行：`review_gui.exe <in.json> <out.json>`
- 退出码：0=正常导出，1=用户取消/关窗，2=输入错误
- agent 用 `child_process.spawnSync` 阻塞等待，exe 退出即拿到结果

## 技术实现（EUI-NEO）

### 组件映射
| i18n 插件(Obsidian) | EUI-NEO 组件 |
|---|---|
| setName/setDesc（行标签）| components::text |
| addTextArea（译文输入）| components::input（multiline=false）|
| addToggle（启用开关）| components::checkbox |
| 列表容器 | components::scrollView |
| 底栏按钮 | components::button |
| 进度条 | ui.rect 动态宽度 |

### 状态管理
EUI-NEO 是即时模式，每帧重绘。需要持久化人类编辑的状态：
- 维护 `std::vector<EntryState> { bool enabled; std::string editedTranslation; }`
- input 的 onChange 回调写回 EntryState
- checkbox 的 onChange 回调写回 EntryState
- compose() 每帧从 EntryState 读取当前值渲染

### 字体
中文显示需要中文字体。EUI-NEO 默认字体可能不含 CJK。
启动时检查系统字体目录加载微软雅黑（C:\Windows\Fonts\msyh.ttc），
通过 DslAppConfig.textFont() 指定。

## 文件清单

```
obsidian-plugin-i18n/
├── SKILL.md                          (集成新流程)
├── scripts/
│   ├── extract.js                    (已有)
│   └── review_bridge.js              (新：node 侧 spawn + 读写 json)
├── review_gui/
│   ├── review_gui.cpp                (新：EUI-NEO 审核台程序)
│   ├── CMakeLists.txt                (新：构建配置)
│   └── build_review_gui.bat          (新：MSVC 构建脚本)
├── bin/
│   └── review_gui.exe                (新：编译产物，分发给别人)
└── references/
    ├── extraction.md                 (已有)
    ├── translation-api.md            (已有)
    └── gui-review-design.md          (本文件)
```

## 分发策略（解决"别人能不能用"）

- review_gui.exe 编译一次，静态链接所有依赖（含 freetype/glfw/harfbuzz）
- exe 随 skill 打包，放在 bin/
- 别人装 skill = 拿到 exe + 脚本，无需 MSVC
- 运行时依赖：Windows + 支持 OpenGL 的显卡（绝大多数 PC 都满足）
- 若某机器 OpenGL 不可用：review_bridge.js 检测 exe 退出码 2，回退到终端表格模式

## 增量价值（对比 i18n 插件）

- i18n 插件：必须 Obsidian 运行 + 插件加载，每次全量
- 本方案：独立 exe，可被任何 skill 调用；复用 review_out.json 做增量更新
- review_gui.exe 是通用审核台：换个 skill（如代码审查、配置审核）也能用，只需改 in.json 格式

## v2 布局升级（移植 i18n AST 编辑器能力 + 修两个显示问题）

研读 i18n 的 AST 编辑器文档后，提炼并移植了它的核心审核能力，
同时解决了"长文本被截断"和"滚动条出现时右边距突然变大"两个问题。

### 移植自 i18n AST 编辑器的能力

1. **搜索框**（顶栏下方的工具栏）
   - 实时匹配 `method` / `original` / `translation` / `id`
   - 输入即筛，状态保存在 `AppState.searchQuery`
2. **"仅未翻译" 筛选按钮**
   - `isUntranslated()` 判定：译文为空 / 全空白 / 与原文完全相同
   - 未翻译行用淡黄底色 + 标签后缀 "· 未翻译" 高亮（i18n 风格的状态色）
   - 按钮本身用 `theme(dark, primary)` 高亮表示激活态
3. **可编辑译文框**：从单行 input 升级为 `multiline()` input，支持多行编辑

### 长文本完整显示（变高行）

旧版问题：固定 `rowH=56`，原文 `substr(0,45)+"..."` 截断。

新版方案：
- 每行高度按内容预估，不再固定（参考 `estimateWrappedLines`）
- 原文用 `text.wrap(true)` 自动换行，高度 = 行数 × `lineHeight`
- 译文用 `multiline()` input，高度 = 行数 × 行高 + 内边距
- 行高取原文/译文两列换行行数的较大值，保证两列都装得下
- `estimateCharWidth` 按 UTF-8 码点区分全角/半角，CJK 按全宽估算（EUI-NEO 的 wrap 不暴露回测结果，所以用启发式预估）

### 滚动条右边距修复（关键）

根因（`scrollview.h:60-63`）：
```
scrollable = initialContentHeight > height_
scrollWidth = scrollable ? scrollbarWidth(8) : 0
scrollGap  = scrollable ? scrollbarGap(16)  : 0
contentWidth = width - scrollWidth - scrollGap   // -24 或 -0
```
滚动条一出现，`contentW` 就缩 24px → 行内容右边突然空出 24px。

解法：在自己布局里**恒定预留 24px gutter**：
```cpp
const float gutter = 24.0f;
const float usableW = std::max(200.0f, contentW - gutter);
```
行背景、文本、输入框都用 `usableW` 而非 `contentW`。
这样不管有没有滚动条，行内容的右边界都一致。

### 列布局（绝对坐标，仿 chat.cpp composeMessages）

```
padX=14  chk(24)  leftX=48 leftW=380  inX=440 inW=usableW-440-14
│        │        │        │          │
checkbox 原文区(方法+原文wrap)        译文输入框(multiline)
```

### 布局分区（自顶向下）

```
顶栏  52px   标题 + 统计 (total/enabled/edited/待保存)
工具栏 48px  搜索框(380) + 仅未翻译按钮(180)
滚动列表 flex  变高行，每行 [左状态竖条][chk][方法label+状态pill][原文wrap][译文multiline]
底栏  56px   状态文本(左) + [全选][全不选][完成 tertiary][保存并导出 primary]
```

## v3 视觉重构（基于 Kimi code CLI 评审，多轮迭代）

工作流：用 PowerShell 截图脚本（DPI-aware）截窗口 → 发给 `kimi -p` 评审 →
按反馈迭代 → 重编 Win+Mac → 再截 → 再评，循环 5 轮。

### 评审发现的问题与修复（按优先级）

**P0 按钮主次不分（原 4 个全蓝按钮）**
- 修复：建立三级按钮体系
  - primary：`theme(dark, true)` 实心强调蓝 — 仅"保存并导出"
  - secondary：`theme(dark, false)` — "完成"
  - tertiary：`theme(dark, false)` — "全选/全不选"

**P0 状态不可见（原无任何状态指示）**
- 修复：每行 method 标签右侧加状态 pill（圆角背景+文字）
  - 就绪（中性灰）/ 未翻译（琥珀）/ 已编辑（蓝）/ 跳过（深灰）
  - 左侧 4px 状态竖条（已编辑=蓝，未翻译=琥珀）做强化

**P0 强调色滥用（checkbox+按钮全蓝）**
- 修复：checkbox 保留组件默认中性色，强调蓝只留给主按钮 + input focus 边框（EUI-NEO input 内置 focusBorder）

**P0 灰阶层级缺失**
- 修复：统一色板 `palette::` 命名空间
  - kBg(0.10,0.11,0.13) < kSurface(0.14,0.15,0.18) < kSurface2(0.19,0.20,0.25) < kElevated(0.21,0.22,0.27)
  - method 标签改中性青灰（不再蓝），避免与 primary 撞色

**P1 真实 bug：未翻译计数显示 `4.000000`**
- 根因：`const float untranslatedTotal = static_cast<int>(count_if(...))` — cast 结果赋给 float 又 to_string
- 修复：类型改 `const int`

**P1 斑马纹不明显**
- 修复：拉大 kSurface/kSurface2 对比（0.14→0.19）+ 每行加 1px border(kBorderSoft)

**P1 底栏统计被按钮挤压**
- 修复：统计文本左对齐 size(420)，按钮从右往左定位，互不重叠

**P1 末行被底栏遮挡**
- 修复：`listH = H - listY - botH - 24`（额外 24px 余量）+ 滚动内容末尾 +10px 留白

### 截图工具（DPI 关键）

高 DPI 屏（150%）截窗口必须先声明 DPI-aware，否则 GetWindowRect 返回逻辑像素、
CopyFromScreen 按物理像素截 → 只截到左上一块。脚本：`shoot_review.ps1`，
核心：`SetProcessDpiAwareness(2)` + `EnumWindows` 按 pid 找标题为 'i18n Review Console' 的窗口。

### 评审工作流命令

```bash
# 1. 截图（DPI-aware）
powershell -ExecutionPolicy Bypass -File shoot_review.ps1
# 2. 把截图+源码放进 kimi 工作目录
cp review_shot.png review_gui.cpp <kimi_cwd>/
# 3. 让 kimi 评审（它会用工具读图，模型支持 image_in）
cd <kimi_cwd> && kimi -p "读取 review_shot.png，评价 UI 不足..."
```

