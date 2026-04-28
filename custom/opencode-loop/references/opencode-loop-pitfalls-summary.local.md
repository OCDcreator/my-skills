# opencode-loop 踩坑痛点总结

> **阅读指南（2026-04-29 更新）**
>
> 本文件经过 8 轮复核。最准确的当前状态在"第八次"一节。
> "第四次"及更早的轮次中，有若干结论已被第八次明确判定为过时——这些旧段落保留作历史审计记录，但**不代表当前项目状态**。
>
> 如果旧轮次与第八次冲突，以第八次为准。

## 最新复核补充（2026-04-29，第八次）

**这一节优先级高于下面所有旧轮记录。**  
如果和下面“第四次 / 第三次 / 更早轮次”的结论冲突，以这一节为准。

这次我做了三类核对：

- 我本地直接跑关键 CLI 测试
- 我本地直接抽查 skill / README / 项目脚本实现
- 我额外起了一个 `gpt-5.5` 只读子代理做快速复核

这轮最重要的结论不是“又发现了一批新缺陷”，而是：

- **有几条之前反复出现的痛点，现在已经可以明确判定为“旧结论过时，需要纠偏”。**
- **现在真正还值得继续优化的点，已经从“大流程跑不通”收敛成“少数文档语义和运行时边界仍需统一”。**

### 这次确认已经解决，旧结论需要撤回或改写的点

#### 1. `start --profile execute --dry-run` 有副作用，这条已经不成立

我这次本地直接跑了：

- `bats tests/test_cli.bats`

结果：

- 全部通过，`15/15`
- 其中已经包含：
  - `cli start --profile execute --dry-run does not modify control.json`
  - `cli start --profile execute --dry-run does not create missing control.json`

这意味着：

- 之前“dry-run 仍会改 control.json / 仍会创建 control.json”的结论，现在应明确标记为**已解决**
- 后面旧轮次里如果还保留这类说法，都应该视为历史记录，不再代表当前状态

#### 2. `start --profile execute` 的 `desired_state=running` 自愈，现在是项目实现，不只是技能提醒

现状：

- CLI 里已经有 `ensure_execute_control_running()`
- execute profile 真启动前会把 `desired_state` 拉回 `running`

这意味着：

- 这条不再属于“用户必须记住的手工避坑”
- 它已经进入项目启动路径的显式保护

#### 3. `DEEPSEEK_API_KEY` 检测缺失，这条现在也需要纠偏

我这次本地用临时仓库实测：

- `opencode.json` 里显式配置 `deepseek`
- 环境里只给 `DEEPSEEK_API_KEY`
- 跑 `preflight --json`

结果：

- `provider_keys.detected` 能看到 `DEEPSEEK_API_KEY`
- `provider_keys.ok=true`

这意味着：

- “项目 CLI 只认 OpenAI / Anthropic / OpenAI-compatible，不认 DeepSeek”这个结论已经过时
- 更准确的现状是：
  **DeepSeek 已进入 provider catalog，但 pass/fail 语义仍取决于当前 repo 配置了哪些 provider**

#### 4. Task Master 导入任务默认 `review_required:false / tdd_required:false`，这条也已经不成立

我这次直接检查当前 `adapt_taskmaster()`：

- `review_required: true`
- `tdd_required: true`

这意味着：

- 之前把这条继续写成“默认仍然偏松”的说法，已经不准确
- 现在更准确的问题不再是“默认没开”
- 而是“默认虽然开了，但 review gate 的最终可用性仍依赖 `gate-review` hook 是否真的配置好”

#### 5. README profile 表缺 `execute`，这条已经解决

现状：

- README 的 profile 表里已经明确列出 `execute`

这意味着：

- 这条不应再作为当前残留问题继续往下传

#### 6. Kimi / kimi-code 的“主文案级不一致”已经基本关闭

现状：

- skill 主文案已经改成先探测：
  `command -v kimi-code || command -v kimi`
- README 也已经对齐这一思路

这意味着：

- 之前那种“技能主路径仍硬编码 kimi-code”的说法，现在至少不能再笼统保留
- 如果后面还要继续优化，应该更精确地描述成：
  **检查是否还有局部示例残留，而不是继续把它定性成主路径级断层**

### 这次新收敛出来、最值得继续优化的点

#### 1. `opencode.json` 的定位现在其实已经偏向“本地 runtime state”，但历史文案还有残余冲突

现状：

- `setup.sh` 会创建 `opencode.json`
- `setup.sh` 同时把 `opencode.json` 写进 `.gitignore`
- skill 当前也明确写了：
  `opencode.json` 是 runtime-generated、默认不应提交

这意味着：

- 从**当前实现 + 当前技能文案**看，项目已经更接近一个统一结论：
  **`opencode.json` 默认属于 repo 根目录里的本地运行态，而不是应提交的 repo asset**
- 真正的问题已经不再是“项目不知道怎么处理它”
- 而是这份痛点总结里仍保留了多轮历史说法，容易让下一轮优化者误以为这件事还没有定论

如果你下一轮要优化，我建议把问题表述成：

- **要么正式确认 `opencode.json` 默认就是 gitignored runtime file，并把所有旧文案统一删干净**
- **要么反过来把项目实现改掉，不再默认 gitignore 它**

现在最怕的不是“功能没做”，而是“文档仍同时保留两套世界观”。

#### 2. `dirty working tree with no active task` 这条，旧文档大概率已经落后于当前代码

现状：

- 当前 `opencode-loop.sh` 代码路径里，dirty tree + no active task 已经是：
  - `state_set_status "environment_blocked"`
  - `return 6`
- 也就是从实现语义上看，它已经更接近**阻断退出**
- 但 skill 这段说明仍然沿用旧的“spin loop / 看起来还在忙”的表述

这意味着：

- 这里当前最值得优化的，不一定是项目代码本身
- 而是**把技能和这份痛点总结里的旧表述改成和当前实现一致**

更准确的写法应该是：

- 旧问题是：runtime `opencode.json` 可能把 worktree 弄脏
- 当前实现是：发现后直接进入 `environment_blocked` 路径，而不是继续假装正常推进
- 当前仍需提醒的是：如何在长跑前避免 `opencode.json` 脏工作树，而不是继续把它描述成“还会空转”

#### 3. 现在最需要继续优化的，已经不是 execute 主流程，而是“文档历史层累积的误导”

这次回头看，最容易让下一轮优化继续打偏的，不是代码，而是这份总结文件里仍混着多轮旧结论，例如：

- 还写着 DeepSeek 不被识别
- 还写着 Task Master 默认 `review_required:false / tdd_required:false`
- 还写着 README profile 表缺 `execute`
- 还写着 dry-run 仍有副作用
- 还写着 dirty-tree 仍会 spin

这些说法如果不在文档层先纠偏，会直接误导下一轮优化方向。

### 这轮之后，最准确的总判断

- 现在已经不能把 `opencode-loop` 的主问题继续概括成“execute 主路径不稳”了。
- 更准确的状态是：
  **主路径关键坑大多已经修掉；剩下主要是 `opencode.json` 分层语义、dirty-tree 文案同步、以及历史痛点总结自身仍有过期结论。**

### 我建议你下一轮优先优化的顺序

1. 先统一 `opencode.json` 的官方定位：到底是 repo asset，还是默认 gitignored runtime state
2. 把 skill 和这份痛点总结里关于 dirty-tree 的旧“spin loop”表述，改成和当前 `environment_blocked / return 6` 语义一致
3. 把这份痛点总结里已经过时的旧问题统一标成“已解决 / 已纠偏”，不要继续让它们混在“当前残留问题”里
4. 只有在以上三条统一后，再继续追更细的 provider / hook / review 体验问题

---
> **以下为历史复核记录。如果与上方第八次结论冲突，以上方为准。**
---

## 最新复核补充（2026-04-28，第四次）

> ⚠️ **部分结论已过时**。第八次复核确认以下条目已经不成立：
> - §1 "dirty working tree + no active task 仍然会空转" → 现在是 `environment_blocked` + `return 6`（阻断退出，不空转）
> - §3 "Task Master 导入后 review_required:false / tdd_required:false" → 现在默认 `true`
> - §4 "skill 示例里仍残留 kimi-code 硬编码" → 现在已改为探测模式

这部分基于你再次优化后的新一轮真实复核，结论需要对前一版做一个关键纠偏：

- **前一版里“macOS `plan / queue / gate` 仍失败”的结论，在当前工作树里已经不成立。**
- **但并不等于全部痛点清零。现在剩下的主问题，已经收敛成更具体的运行时边界问题。**

这一轮我做了两类核对：

- 我本地直接复跑关键 Bats 测试
- `gpt-5.5` 子代理做独立审计，再和我本地结果交叉验证

### 这次确认已解决 / 需要纠偏的点

#### 1. macOS `plan / queue / gate` 兼容问题，在当前工作树里已经跑通

现状：

- 我本地直接跑了：
  - `tests/test_plan_adapters.bats`
  - `tests/test_queue_manager.bats`
  - `tests/test_gate_manager.bats`
- 这三组这次在当前工作树里全部通过

这意味着：

- 上一版里把它定性为“仍未解决”，现在需要纠偏
- 至少在**当前这份本地工作树**里，`queue_manager.sh` 那条最关键的 macOS 兼容链已经显著改善

但要注意：

- 这个结论是**基于当前工作树**，不是基于“已经提交后的历史版本”
- 我这次同时看到项目仓库仍有未提交改动：`lib/queue_manager.sh`
- 所以更准确的说法是：
  **当前工作树里的实现已经把这条线跑绿了，但这份结果仍依赖当前未提交代码状态**

#### 2. `start --profile execute` / 主循环 control state 语义现在可以算真修好了

现状：

- CLI execute profile 启动前会主动把 `desired_state` 拉回 `running`
- 主循环启动时也会再次兜底 reset
- integration 测试这轮继续通过

这意味着：

- 这块已经不是“靠技能文案提醒使用者绕坑”
- 而是项目本身在启动路径上补了自愈

#### 3. Full Auto 路由冲突、OpenSpec artifact drift、Task Master 元任务归一化，这三类老坑现在都可以归到“已明显改善”

现状：

- skill 已明确 Full Auto Pipeline 覆盖泛化 brainstorming / route selection
- OpenSpec 那段已经写清楚：`openspec new change` 后必须显式补 proposal/design/specs/tasks
- Task Master `parse-prd` 后，skill 要求 mandatory normalization；项目 adapter 也开始自动剔除可疑 meta tasks

这意味着：

- 这些不再是之前那种“代理极容易第一脚踩偏”的状态
- 至少从 skill 文案和项目适配层看，都比最初稳定很多

### 这次新确认仍未解决的点

#### 1. dirty working tree + no active task 仍然会空转

> **⚠️ 第八次复核确认：本条已过时。** 当前实现直接 `environment_blocked` + `return 6`，不再空转。保留此段仅供历史对比。

现象：

- execute 模式下，如果 worktree 是 dirty 且当前没有 active task
- 主循环会持续报：
  `Dirty working tree with no active task. Cannot start new task.`
- 但它不会立刻把这轮当成 fatal/blocking exit 收掉
- 我本地用临时仓库直接复现后，`timeout 2s` 退出码是 `124`，日志里同一轮持续重复报错

问题本质：

- 这块虽然已经能**检测并标记 blocked**
- 但还没有做到**检测后立即干净退出或停止推进 run_count**

这意味着：

- 对无人值守场景来说，这仍然是一个真实坑
- 它会让 loop 看起来“还在忙”，实际上只是在空转

#### 2. Full Auto one-script summary 里 `CHANGE` 和 `my-feature` 变量仍然漂移

现象：

- one-script summary 先定义了：
  `CHANGE="${2:-my-feature}"`
- 但后面 OpenSpec change 名、artifact 路径、proposal 路径仍然直接写死 `my-feature`

问题本质：

- 分支名和 OpenSpec change id 没有真正统一用同一个变量

这意味着：

- 用户一旦换 feature 名
- 这段示例脚本就会出现“branch 名变了，但 OpenSpec 路径没跟着变”的文档性误导

#### 3. provider / review / TDD 默认策略仍然是“部分补齐”

> **⚠️ 第八次复核确认：本条部分过时。** `adapt_taskmaster()` 现在默认 `review_required: true, tdd_required: true`。残留问题只是 review gate 的最终可用性仍依赖 `gate-review` hook 是否真的配置好。

现状：

- provider preflight 比之前强很多，execute 真启动前已经会 fail-fast
- 但 CLI provider catalog 仍主要识别：
  - `OPENAI_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `OPENAI_COMPATIBLE_API_KEY`
- Task Master 导入后的任务默认仍是：
  - `review_required: false`
  - `tdd_required: false`

这意味着：

- 项目已经从“完全松散”进步到“具备能力”
- 但还没有进步到“默认就是你偏好的强审查 / 强 TDD 路径”

#### 4. skill 示例里仍残留 `kimi-code` 硬编码

> **⚠️ 第八次复核确认：本条已基本关闭。** skill 主文案已改为 `command -v kimi-code || command -v kimi` 探测模式。仅剩局部示例可能残留，不再是主路径级问题。

现状：

- 项目 README 已经开始提示先探测 `kimi` / `kimi-code`
- 但 skill 示例里仍然残留直接写死 `kimi-code` 的地方

这意味着：

- 项目侧认知已经更新
- skill 侧示例还没有完全对齐

### 对上一版结论的修正

上一版里最核心的未解决项写成了：

- `queue_manager.sh` 的 macOS Bash 兼容问题仍在拖累 `plan / queue / gate`

这一条在**当前工作树复核结果**下应调整为：

- **已在当前工作树里明显改善，并且关键测试已跑绿**
- 但由于项目仓库当前仍有 `lib/queue_manager.sh` 未提交改动，所以更准确的状态是：
  **“当前工作树已修通，是否算正式解决还取决于这部分实现是否最终沉淀提交”**

### 当前最准确的结论

- 现在已经不能再说“这套技能和项目还停留在靠熟手救火才能跑”的早期状态了。
- execute 主路径、control state、status/doctor、OpenSpec/Task Master 文档衔接、queue/gate 主干能力，这些都已经明显进步。
- 但如果标准是“之前所有痛点是不是都解决了”，答案仍然是：**还没有完全。**

当前最值得优先继续优化的，已经收敛成下面 4 条：

1. dirty tree + no active task 时，不要空转，应该立即停止或显式退出
2. one-script summary 全量改成变量一致，不要再混用 `CHANGE` 和 `my-feature`
3. 如果目标是强审查 / 强 TDD，无论 skill 还是 adapter 默认值都要继续前推
4. skill 示例里的 Kimi 命令探测方式，和项目 README 完全对齐

## 最新复核补充（2026-04-28，第三次）

> ⚠️ **本节多段结论已被后续轮次推翻。** 保留作审计记录，不代表当前状态。

这部分是你再次优化技能和项目之后，我又做的一轮真实复核。相比前一版，这次最重要的新结论有两个：

- **provider preflight 又往前走了一步**：`execute` 真启动前，缺 provider key 现在已经会 fail-fast，不再只是 warning。
- **macOS Bash 兼容问题并没有彻底收掉**：`queue_manager.sh` 相关路径仍残留 `declare -A` 和空数组边界问题，导致 `plan adapters / queue / gate` 这条链在 macOS 上继续失败。

### 这次确认已经继续变好的点

#### 1. execute 的 provider preflight 已经从“提示”升级为“阻断”

现状：

- `cmd_start` 在 execute 且非 dry-run 时，会检查 `provider_keys.ok`
- 如果缺 provider key，会直接报错退出

这意味着：

- 这块已经不再只是“看见风险但继续跑”
- 对低经验代理来说，少了一种“明知没 provider 还硬启动”的误跑

#### 2. integration 主路径这次依然是绿的

现状：

- 我本地直接跑 `tests/test_loop_integration.bats`
- 这次整文件通过

这意味着：

- execute 主循环、session 延续、timeout、pause/resume 这些主路径至少没有重新退化

### 这次重新确认的未解决项

#### 1. `queue_manager.sh` 仍残留 Bash 4 专属写法

现象：

- 我本地跑 `tests/test_plan_adapters.bats` 时，多条失败直接报：
  - `declare: -A: invalid option`
  - `... unbound variable`
- 我本地跑 `tests/test_queue_manager.bats` 时，也有多条同类失败
- 我本地跑 `tests/test_gate_manager.bats` 时，仍能触发依赖数组相关失败

问题本质：

- 你前面确实修掉了一部分 `mapfile` 路径
- 但 `queue_manager.sh` 里围绕 queue validate / next task / adapter output validate 的关键路径，仍然残留 Bash 4 依赖

这意味着：

- 现在不能再把“macOS Bash 兼容”归类为半坑
- 它仍然是一个明确的、真实可复现的未解决项

#### 2. `plan adapters` 这条线当前不能算稳定

现象：

- `tests/test_plan_adapters.bats` 中：
  - OpenSpec adapter
  - Task Master adapter
  - manual adapter
  - adapter output validate
  这几类测试都还能被 `queue_manager.sh` 的兼容问题打断

问题本质：

- 不是技能文案问题
- 是项目底层 queue/validate 逻辑在 macOS 环境仍不稳

这意味着：

- 即使 Full Auto 文档已经更完整
- 真到 `plan --from-openspec` / `plan --from-taskmaster` 这一步，mac 上还是会继续踩坑

### 这次最准确的结论

- 当前版本已经比前几轮更强，尤其是 execute 主流程、provider preflight、status/doctor、review gate 这些方面都在继续进步。
- 但如果标准是“之前的痛点是不是都解决了”，答案仍然是：**没有**。
- 现在最核心的残留已经收敛到一条非常具体的线：
  **`queue_manager.sh` 的 macOS Bash 兼容问题，仍在拖累 plan / queue / gate 相关路径。**

### 当前最优先的剩余修复项

1. 把 `queue_manager.sh` 里剩余的 `declare -A` 依赖全部清掉
2. 修掉空依赖数组/空集合情况下的 `deps[@]` unbound variable 边界
3. 先把 `tests/test_plan_adapters.bats`、`tests/test_queue_manager.bats`、`tests/test_gate_manager.bats` 跑回绿
4. 之后再回头统一 skill 里仍残留的 `kimi-code` 硬编码示例

## 重新优化后的二次复核（2026-04-28，追加）

> ⚠️ **本节为历史审计记录。** 多个结论已被后续轮次（特别是第四次和第八次）推翻。

这部分基于你再次优化技能和项目之后，我重新做的一轮真实复核，包含：

- `gpt-5.5` 子代理独立审计
- 我本地直接抽查 skill / 项目实现
- 我本地直接跑关键 Bats 测试

这一轮和上一轮相比，结论已经明显变好了：

- 之前一些“只在技能文案里提醒、项目本身不兜底”的坑，现在项目侧开始补控制逻辑和检测了。
- `test_loop_integration.bats` 这类主路径回归，这次我本地已经整文件通过。
- 但我本地仍看到一个剩余边界失败，所以结论依然不是“全部痛点都彻底解决”。

### 这次已经明显关闭的点

#### 1. `start --profile execute` 不再依赖旧的 `desired_state`

现状：

- CLI 在 execute profile 启动前，会主动初始化或重置 `control.json.desired_state=running`
- 主循环启动时也会再次兜底重置

这意味着：

- 这个坑已经从“技能提醒但项目不自愈”，变成“项目和技能双保险”

#### 2. health / status 不再只是读 JSON 文件

现状：

- `status --json` 现在已经带真实 PID liveness 检查和 stale running warning
- `doctor --json` 也开始报告 loop / supervisor / child 的进程健康

这意味着：

- 这块已经不再只是技能层的“认知升级”
- 项目 CLI 本身开始提供更接近 ground truth 的状态信息

#### 3. `hooks test` 与真实 gate 路径的关系已经被正式产品化说明

现状：

- 普通 `hooks test` 现在会明确警告：这只是 normal hook path
- `hooks test --gate` 才测试 blocking gate semantics
- CLI 测试里也已经覆盖了 `--gate` 语义

这意味着：

- 这块虽然仍然是两条路径，但已经不再是“隐性断层”
- 至少用户和代理能被明确告知“哪条才是真实 review gate 路径”

#### 4. provider / normalization 终于开始进入 CLI 检测面

现状：

- CLI 新增了 `preflight`
- `doctor --json` 和 `start --dry-run` 会报告 provider key 缺失
- 也会检测 queue 中是否存在 suspicious meta tasks

这意味着：

- 它还不是硬阻断，但已经不再完全依赖技能文案
- 项目侧开始具备“发现问题并显式告警”的能力

#### 5. macOS `mapfile` 兼容问题这次已经部分被修掉

现状：

- 上一轮我在 `queue_manager.sh` 里看到的 `mapfile` 依赖，这次关键路径已经被改成兼容写法
- `test_loop_integration.bats` 本地这次整文件通过

这意味着：

- 之前那种“主路径直接被 Bash 版本打断”的状态已经缓解很多

### 这次仍然只是“部分解决”的点

#### 1. provider preflight 现在能检测，但还不是 fail-fast

现状：

- CLI 会 warning
- `init --mode execute` / `start` 会跑 preflight
- 但 provider key 缺失当前仍不会直接阻断执行

问题本质：

- 这是“检测到了”，还不是“系统替你拦住了”

#### 2. `parse-prd` 元自动化任务归一化现在能提示，但不会自动修

现状：

- CLI 会识别 suspicious meta task ids
- 但不会自动删除、合并、重写这些任务

问题本质：

- 这依然需要模型或操作者手动做最后一跳

#### 3. review / TDD 仍然不是 imported task 默认硬开启

现状：

- 执行路径已经支持 review gate 和 TDD gate
- 但 imported tasks 默认仍是 `review_required:false`、`tdd_required:false`

问题本质：

- 这代表“能力已存在”，但“默认治理强度”还没彻底收口

### 这次仍然保留的残余问题

#### 1. 我本地仍看到一个 gate / queue 边界失败

现象：

- 我本地直接跑 `tests/test_gate_manager.bats` 时，仍看到：
  `ed_validate_exit_request rejects when more tasks remain`
  这条用例失败

说明：

- 主路径稳定性比上一轮好很多
- 但 queue/gate 边界行为还没有完全打平

#### 2. `hooks test --gate` 与 gate command checks 的默认 timeout 口径仍不完全一致

现状：

- blocking hook 默认 timeout 还是一套
- gate command check 默认 timeout 还是另一套

说明：

- 这不一定会立刻炸，但仍然是一个值得继续统一的实现细节

### 这次最准确的结论

- 这轮重新优化之后，`opencode-loop` 已经比上一轮更接近“代理可稳定照着技能跑主流程”的状态
- 以前几个最烦的坑里，`desired_state`、status/doctor、integration 主路径、`hooks test --gate` 语义说明，这次都属于明显进步
- 但如果标准是“所有历史痛点都解决，可以完全放心长期无人值守”，那现在还不能这样下结论

### 当前最高优先级剩余项

1. 把 provider preflight 从 warning 继续推进到更硬的 execute 前约束
2. 把 Task Master meta-task normalization 从“检测/提示”推进到更强的系统约束
3. 修掉 `test_gate_manager.bats` 里剩余的 queue/gate 边界失败
4. 统一 hook blocking timeout 和 gate command timeout 的默认口径

## 最新回归复核（2026-04-28）

> ⚠️ **本节为最早一轮复核。** 大部分结论已被后续轮次推翻或明显改善。

这部分是基于你完成上一轮技能和项目优化之后，我再次按“技能文案 + 项目实现 + 本地测试”做的一轮真实复核。结论不是“之前痛点都解决了”，而是：

- 技能侧已经明显收口，很多历史断层已补上。
- 项目侧仍有几处真实回归和半修状态。
- 当前版本已经比之前稳很多，但还不算“可以完全放心地长期无人值守”。

### 本轮总体判断

- **已明显解决**：Full Auto 与通用 brainstorming/route-choice 冲突、OpenSpec artifact drift、execute 默认 15 分钟超时过短、dirty-tree handoff 文案断层、review gate 没真正接入执行路径、`.opencode-loop/` 本地态与 repo 资产分层不清。
- **部分解决**：Task Master provider preflight、`parse-prd` 后任务归一化、`start --profile execute` 与 `desired_state` 语义断层、Kimi 命令探测、health/status 判断路径。
- **仍未解决**：`hooks test` 默认路径和真实 blocking gate 路径仍不一致；provider preflight 和任务归一化仍主要依赖技能纪律，不是项目强制能力。
- **新增确认的新坑**：macOS Bash 兼容仍有真实问题；全量测试仍不绿；部分测试断言已落后于实现。

### 已确认解决的点

#### 1. Full Auto 不再容易被通用 brainstorming / route-choice 带偏

现状：

- 技能入口已经加了硬约束：触发后默认直接走 Full Auto Pipeline，不再先问 mode/route。

意义：

- 这是最关键的技能层修复之一。
- 代理更不容易再在“先设计还是先执行”上原地打转。

#### 2. OpenSpec artifact drift 已经补文档

现状：

- 技能现在明确写了：`openspec new change` 之后，还需要显式生成 `proposal/design/specs/tasks` 的 instructions，并自己写 `proposal.md` 等产物。

意义：

- 这已经把“CLI 真实行为”和“技能假设”对齐了。

#### 3. execute 默认超时不再是 15 分钟

现状：

- 项目实现和 CLI execute profile 都已经是 60 分钟级别，而不是老的 15 分钟默认。

意义：

- 对你这种持续自动跑、验证成本高的场景，这是实打实的可用性提升。

#### 4. dirty working tree handoff 已经被正面写透

现状：

- 项目 execute 模式仍会在“无 active task + worktree dirty”时阻断新任务。
- 但技能现在已经把“bootstrap 之后先 commit，再启动 execute”写成明确步骤。

意义：

- 这不代表项目自动修好了，但至少技能不再把用户带进这个坑里。

#### 5. review gate 已真正接入执行路径

现状：

- `review_required=true` 时，项目会查找名为 `gate-review` 的 `post_iteration` hook，并通过 blocking hook 解析最后一行 JSON 结果。

意义：

- 这块已经不再只是“文案承诺”，而是确实进了 gate path。

### 仍然只是“部分解决”的点

#### 1. Task Master provider preflight

现状：

- 技能已经强制要求在 `parse-prd` 前先做 provider key 检测和配置。
- 但项目 CLI / adapter 本身不会替你强制做这件事。

问题本质：

- 这仍然是“技能约束”，不是“项目能力”。

#### 2. `parse-prd` 元自动化任务归一化

现状：

- 技能已经明确要求 normalize。
- 但项目 `plan --from-taskmaster` 仍主要是直接映射 Task Master 输出，不会自动识别和重写元任务。

问题本质：

- 只要代理漏做这一步，旧坑就会回潮。

#### 3. `start --profile execute` 与 `control.json.desired_state`

现状：

- 核心脚本启动时会把 `desired_state` 拉回 `running`。
- 但 CLI wrapper 自身只是 `exec` 底层命令，技能仍然要求额外检查。

问题本质：

- 实际体验比以前好一些了，但还没完全做到“用户无脑 start 就不踩状态坑”。

#### 4. Kimi 命令探测

现状：

- 项目 README 已经开始提示 `kimi-code || kimi`。
- 但技能示例仍有硬编码 `kimi-code` 的地方。

问题本质：

- 技能和项目没有完全统一。

#### 5. health / status 判断路径

现状：

- 技能现在已经强调：`status --json` 不是 liveness ground truth，要结合 `ps`、output、`supervisor-child.log`。
- 但 CLI `status` 本身仍只是聚合 JSON，并不主动做真实进程交叉验证。

问题本质：

- 技能层认知升级了，项目层还没完全产品化。

### 仍未彻底解决的点

#### 1. `hooks test` 默认路径和真实 gate 路径仍分叉

现状：

- 普通 `hooks test` 走的是普通 hook 执行路径。
- 只有 `hooks test --gate` 才会走 blocking gate 路径。

后果：

- 用户很容易在“测试 hook”和“真实 gate 执行”之间得到不一致体验。

这说明：

- 这块还不能算彻底收口。

#### 2. provider preflight / task normalization 仍依赖模型自觉

现状：

- 现在它们更像是“技能强制动作”。
- 还不是项目自己兜底的强约束。

后果：

- 一旦代理偷懒、技能触发不完整，老问题还是会复发。

### 本轮新增确认的新坑

#### 1. macOS Bash 兼容仍有真实实现问题

现象：

- 本地跑 `tests/test_gate_manager.bats` 时，实际出现了 `mapfile: command not found`。
- 说明项目实现里仍有依赖更高 Bash 能力的代码路径。

意义：

- 这不是文档问题，而是实打实的项目问题。
- 对 mac 用户尤其关键。

#### 2. 全量测试当前仍不绿

现象：

- 我本地跑聚焦测试时，`tests/test_gate_manager.bats` 和 `tests/test_loop_integration.bats` 都能看到真实失败。

意义：

- 当前状态不能称为“项目整体已完全回稳”。

#### 3. 部分测试断言已经落后于实现

现象：

- `test_loop_integration.bats` 里至少有两处失败，核心原因不是主逻辑坏了，而是测试还在匹配旧的 continue prompt 文字。
- 现在实现已经改成绝对路径版本，因此测试没同步。

意义：

- 这类问题虽然不像运行时 bug 那么危险，但会直接让回归不绿，影响你判断系统是否真正稳定。

#### 4. README 里仍残留旧超时认知

现象：

- 项目实现和 execute profile 已经提升到 60 分钟级别，但 README 某些位置仍能看到 15 分钟旧描述。

意义：

- 这属于文档残留漂移，虽然没有旧版本那么致命，但仍会误导新使用者。

### 目前最准确的结论

- 这个新版本已经足够让一个严格代理“按技能大体跑起来”。
- 但它还没有稳定到“完全不用盯、所有历史坑都已经收掉”的程度。
- 现在剩余的最高优先级，不再是继续补技能文案，而是：
  1. 修 macOS Bash 兼容
  2. 统一 `hooks test` 和真实 gate 路径
  3. 把 provider preflight / task normalization 下沉成项目能力
  4. 修回归测试，让全量测试重新回绿

# opencode-loop 踩坑痛点总结

这份总结基于一次在 macOS 上、面向 `opencodian` 仓库、完整走通 `opencode-loop` 技能的实战。重点不是功能缺失，而是 **技能文案、CLI 语义、运行时状态机、以及真实仓库工作流之间的断层**。

## 本轮回归审计新增痛点（待继续优化）

下面这些不是“第一次跑流程时踩到的坑”，而是你完成上一轮技能/项目优化后，我又专门做了一轮 **技能文案 + 项目实现 + 测试行为** 回归审计，确认还没彻底闭环的点。

### A. `hooks test` 仍然可能卡住，hook 健康检查和真实 gate 路径不一致

现象：

- review gate 真正执行时走的是 blocking hook，里面有 `timeout 300`。
- 但 `opencode-loop hooks test` 走的是普通 `hm_run_hooks` 路径，不带同样的阻塞保护。
- 这意味着“真实 review gate 可控”与“hooks test 可能长时间挂住”可以同时成立。

后果：

- 用户会误以为 hook 系统整体不稳定。
- 技能如果仍把 `hooks test` 当成唯一健康检查，就会把一个“可用的 reviewer 命令”误判成“不可用的 reviewer 系统”。

建议：

- 项目层把 `hooks test` 和 blocking gate 的超时/重试语义尽量对齐。
- 技能层继续保留两段式验证：
  1. 先测 reviewer 命令最小 JSON 输出
  2. 再测 `hooks test`

### B. Kimi 命令名探测仍未真正产品化，示例还在硬编码 `kimi-code`

现象：

- 技能和项目 README 里的示例依然主要写 `kimi-code`。
- 但真实机器上常见情况是只有 `kimi`，没有 `kimi-code`。

后果：

- 这类 hook 例子会继续“文档看起来正确，落地直接失效”。
- 用户每次换机器、换环境，都会重复踩同一个命令名坑。

建议：

- 技能和项目文档统一改成：
  - 先 `command -v kimi-code || command -v kimi`
  - 再注入具体 hook
- 不要再默认 `kimi-code` 是稳定命令名。

### C. `start --profile execute` 仍未主动修正 `control.json.desired_state`

现象：

- `setup.sh` 确实默认把 `desired_state` 初始化成了 `running`。
- 但如果某次旧运行把它留在 `paused` 或 `stopped`，后续再执行 `opencode-loop start --profile execute`，CLI 本身不会帮你纠正。
- 也就是说，这个坑现在是“技能已提醒”，但“项目还没自愈”。

后果：

- 用户会看到“明明 start 了，但 loop 还是很快停掉”。
- 代理如果只照 `start` 跑，不做额外检查，仍会被旧状态绊倒。

建议：

- 项目层让 `start` 在 execute 启动前显式校验或重置 `desired_state=running`。
- 技能层继续保留这一步，但最好不再完全依赖模型记住。

### D. provider preflight 和 `parse-prd` 归一化，目前更多还是“技能约束”，不是“项目能力”

现象：

- 技能已经明确要求：
  - 先做 Task Master provider preflight
  - `parse-prd` 后必须做任务归一化
- 但项目 CLI 本身还不会强制探测 provider，也不会自动识别“元自动化任务并改写掉”。

后果：

- 这两件事仍然依赖代理是否严格按技能执行。
- 一旦模型偷懒、漏做，旧坑就会回潮。

建议：

- 如果你希望“技能照着跑就稳定”，这两步最好继续往项目能力里下沉。
- 至少要让 `plan --from-taskmaster` 或其上游 preflight 对这些风险给出显式告警。

### E. `setup.sh` 生成的 execute 默认 queue profile 与 queue manager 默认 profile 仍有轻微漂移

现象：

- `queue_manager` 默认 profile 包含 `integration_strategy`。
- 但 `setup.sh` 初始化 execute queue 时写进去的 profile 仍缺这个字段。

后果：

- 虽然当前多数路径还能跑，但这类 schema 轻微漂移以后很容易再演化成新的文档/实现错位。
- 这种问题最烦的地方在于：它不会立刻炸，但会持续增加心智负担。

建议：

- 把 `setup.sh` 的 execute queue 默认 profile 和 `queue_manager` 默认 profile 做成同源，避免再漂。

### F. 仍存在真实测试回归，说明“主路径变稳”不等于“整体完全收口”

现象：

- 这轮本地回归里，`tests/test_loop_integration.bats` 的 timeout 相关用例仍可复现失败。
- 这说明项目里至少还有一部分边界路径没有完全跟上最新语义。

后果：

- 用户在真实长跑里遇到的“偶发怪行为”，很可能不是错觉，而是已有测试边界还没完全收敛。

建议：

- 下一轮优化不要只补技能文案。
- 需要把这类测试失败一并视为“项目仍有残留坑”的证据，优先修到测试回绿。

## 最新新增痛点（待继续优化）

下面这些是你完成上一轮技能和项目优化之后，我继续在“新 worktree + Kimi review gate + execute 续跑”阶段踩到的新增坑。它们依然属于 **技能和项目结合面** 的问题，而不是单纯的人为操作失误。

### A. 新 worktree 创建被中断后，容易留下“半创建分支 + 无 worktree 目录”的状态

现象：

- `git worktree add ... -b autopilot/thick-owner-loop` 被旧的 `index.lock` 卡住。
- 分支已经创建出来了，但 worktree 目录没真正落好。
- 后续如果不先识别“分支已存在但 worktree 未绑定”，很容易继续乱建分支或误判失败。

后果：

- 自动化从主工作区切到新 worktree 的第一步就会进入半残状态。
- 代理如果不做恢复，后续所有“新树继续跑”都会卡在错误前提上。

建议：

- 技能增加“worktree 创建恢复”小节：
  1. 先查 `git worktree list`
  2. 再查目标分支是否已创建
  3. 若分支已存在但目录不存在，直接 `git worktree add <path> <branch>`
  4. 若有 `index.lock`，先确认没有活跃 git 进程，再清理锁

### B. 新 worktree 不会自动继承本地 `.opencode-loop` queue/runtime 语义

现象：

- 在新 worktree 里执行 `opencode-loop init --mode execute`，会先创建一份空的 manual queue。
- 它不会自动继承上一棵工作树里已经调好的 `taskmaster -> queue -> master-7/master-8` 状态。

后果：

- 一旦切到新 worktree，不显式迁移 `.opencode-loop/queue.json`、`program.md`、hooks 配置，就会丢失“继续上一轮任务”的上下文。

建议：

- 技能明确区分：
  - repo 资产可由 Git 带过去
  - `.opencode-loop` 是本地运行态，不会自动跟过去
- 增加“新 worktree 续跑”步骤：
  1. `init --mode execute`
  2. 从旧树迁移 `program.md` / `queue.json` / `hooks.json`
  3. 重置当前 task 为可重跑状态

### C. Kimi 审查命令在真实机器上可能不是 `kimi-code`

现象：

- 技能示例里长期沿用 `kimi-code`
- 这台机器上实际可用命令是 `kimi`

后果：

- 直接照技能示例挂 hook，会在本机失效。

建议：

- 技能把 Kimi 命令前置探测写死：
  - `command -v kimi-code || command -v kimi`
- 文档示例不要只写一个命令名，应该写成“先探测，再注入 hook”

### D. `gate-review` 命令本身可用，不代表 `hooks test` 路径稳定可用

现象：

- `kimi --print --final-message-only ...` 最小 JSON 输出是通的
- 但 `opencode-loop hooks test --event post_iteration --iteration 0` 会长时间挂住

后果：

- 不能把 `hooks test` 当成唯一的 hook 健康检查
- 否则会在“审查功能其实能用”的情况下，被测试命令本身拖住主任务

建议：

- 技能里把 hook 验证拆成两层：
  1. 先验证 reviewer 命令最小 JSON 输出
  2. 再把 `hooks test` 作为附加验证，而不是唯一准入门槛

### E. 只挂 `gate-review` hook 还不够，queue 任务还必须显式 `review_required=true`

现象：

- 新 worktree 里虽然已经挂上 `gate-review`
- 但如果 queue 任务本身还是 `review_required=false`，Kimi 审查不会真正参与 gate 判定

后果：

- 看起来“审查已经接上了”，实际上只是旁路 hook，不是硬 gate

建议：

- 技能在 queue enrichment 阶段直接写清楚：
  - 哪些任务必须 `review_required=true`
  - 不要等 loop 启动以后再补

### F. 新 worktree 没有依赖环境，不能假设可以立即 execute

现象：

- 新树 checkout 完是干净的，但 `node_modules` 不在
- 如果直接跑 execute，后续 verification 很容易因为依赖缺失失败

后果：

- “切到新树继续自动跑”会退化成“新树上重新踩依赖坑”

建议：

- 技能把 worktree continuation 明确成：
  1. create/add worktree
  2. 安装依赖
  3. 校验 doctor / tests baseline
  4. 再恢复 queue 和 execute

### G. 任务已经提交，但 loop 收尾失败时，可能因为 repo-visible 脏改动再次掉回 blocked 自旋

> **⚠️ 状态更新：** 当前实现中，检测到 dirty working tree + no active task 后，loop 直接进入 `environment_blocked` 状态并退出（exit code 6），不再"自旋"或"空转"。本节保留的"后果"描述已不适用于当前代码，但预防建议（确保 `opencode.json` 在 `.gitignore` 中）仍然有效。

现象：

- `master-8` 在新 worktree 里已经真实产出并提交了代码改动。
- 但 loop 没把这轮完整收尾，随后工作树里留下了 `opencode.json` 的 repo-visible 脏改动。
- 因为这时已经没有 active task 了，child loop 就开始疯狂重复：
  `Dirty working tree with no active task. Cannot start new task.`

后果：

- 用户会误以为“它还在继续跑”，其实它已经退化成空转自旋。
- 更糟的是，这种状态不是任务执行失败，而是 **任务已完成 + 收尾失败**，很容易把判断搞混。

本质：

- queue/loop 对“代码任务成功提交”与“repo-visible 运行时回写文件”之间缺少一致的收尾策略。
- `opencode.json` 这种会被 runtime 轻微改写的文件，在没有 active task 时会立刻把 loop 推回 blocked。

建议：

- 技能里新增一个“任务提交后再看一次 worktree”检查：
  1. 如果任务已 commit
  2. 立刻 `git status --porcelain`
  3. 如果只剩 `opencode.json` / 类似 runtime 配置回写，明确规定：
     - 要么自动吸纳到当前任务收尾
     - 要么自动停止 loop，要求人工确认
- 不要让 loop 在“已无 active task + 仅剩 repo-visible runtime 改动”的状态下继续重试。
## [已归档] 已完成/已缓解的旧痛点

> 以下第 1-15 条已确认解决或明显缓解。保留作回归检查清单，不作为当前主矛盾。

## 结论先说

- 这个技能现在已经能跑通，但更像是“熟悉日志和脚本的人可以救回来”的状态。
- 它距离“代理照着技能就稳定跑通”还差四个关键面：
  - `artifact drift`
  - `provider bootstrap`
  - `dirty-tree handoff`
  - `control-state semantics`

## [已缓解] 一、最高优先级痛点

### 1. [已完成] 技能入口和通用设计/澄清流程冲突

现象：

- `opencode-loop` 技能已经明确说默认走 Full Auto Pipeline，不要再问 route/mode，直接开始。
- 但在带有通用 brainstorming / 规划约束的环境里，代理还是很容易先去做设计问答。

后果：

- 用户明明要“自动跑”，代理却先做成“传统对话式设计”。
- 这会让 `opencode-loop` 技能的主路径被上层通用流程抢走。

本质：

- 技能触发后，缺少一句足够强的“覆盖通用流程”的硬约束。

建议：

- 在技能开头增加强约束：
  `opencode-loop` Full Auto Pipeline 覆盖通用 brainstorming / route-choice。
- 只有在项目路径不清楚、需求本身严重歧义时才允许先问。

### 2. [已完成] OpenSpec 当前脚手架和技能参考漂移

现象：

- 技能和 `full-auto-pipeline.md` 都默认假设 `openspec new change` 后就直接写 `proposal.md`。
- 实测新版 OpenSpec 会先生成 `README.md` 和 `.openspec.yaml`，`proposal.md` / `design.md` / `tasks.md` / `specs/**` 需要后续补建。

后果：

- 代理很容易直接去读一个并不存在的 `proposal.md`。
- 文档里的“自然下一步”和真实 CLI 产物不一致。

本质：

- 技能把 OpenSpec 当成静态文件模板系统在写，但实际已经更像“change 容器 + artifact 指令系统”。

建议：

- 把 OpenSpec 段落改成：
  1. `openspec init`
  2. `openspec new change`
  3. 立即运行 `openspec instructions proposal/specs/design/tasks --change ...`
  4. 按 artifact 指令补齐各文件
- 不要再把 `proposal.md` 当成天然存在的文件。

### 3. [已完成] Task Master provider bootstrap 是硬断点

现象：

- 参考文档只说“先配置 provider / API key”，但没有一个强制 preflight。
- 实战中 Task Master 默认指向 `anthropic` / `perplexity`。
- 当前环境实际只有 `DEEPSEEK_API_KEY`，第一次 `parse-prd` 直接失败。

后果：

- Full Auto Pipeline 会在 Layer 2 硬中断。
- 如果代理不继续追，会误以为“Task Master 不可用”。

本质：

- 技能假设 provider 已经配置好了，但这在真实本地环境里经常不成立。

建议：

- 把 provider 检测做成强制 preflight。
- 技能里要写明：
  - 先探测 `OPENAI_COMPATIBLE_API_KEY` / `DEEPSEEK_API_KEY` / `ANTHROPIC_API_KEY` / `PERPLEXITY_API_KEY`
  - 如果只有 DeepSeek，就自动执行：
    - `task-master models --set-main deepseek-chat --openai-compatible --baseURL https://api.deepseek.com/v1/`
    - `task-master models --set-fallback ...`
    - `task-master models --set-research ...`
  - 必要时临时桥接 `OPENAI_COMPATIBLE_API_KEY="$DEEPSEEK_API_KEY"`

### 4. [已完成] `parse-prd` 很容易产出“元自动化任务”

现象：

- 第一次 `parse-prd` 生成的任务，明显偏向于：
  - lane-switch 脚本
  - guardrail 脚本
  - 模板文件
  - 额外自动化层
- 反而没有直接切到 `OpenCodeService.ts` / `OpenCodianView.ts` 的稳定职责切片。

后果：

- Task Master 把“为自动化搭脚手架”当成了“真正的需求”。
- 最终 queue 会跑偏到元工程，而不是用户要的代码工作。

本质：

- PRD 对“自动化执行方式”和“真正业务目标”的边界不够强。
- 技能缺少一轮“生成后归一化”的硬步骤。

建议：

- `parse-prd` 后强制执行一轮 task normalization：
  - 对照 OpenSpec `tasks.md`
  - 把元自动化任务压缩回真实 repo 任务
  - 删除泛脚本/模板发明倾向
- 明确写进技能：Task Master 输出不是权威，OpenSpec contract 才是权威。

## [已缓解] 二、CLI / 运行时语义上的坑

### 5. [已完成] `opencode-loop plan` wrapper 健壮性不足

现象：

- 实战直接撞到 `bin/opencode-loop-plan.sh` 没执行权限。
- `opencode-loop plan` 直接 `Permission denied`。

后果：

- Full Auto Pipeline 到 Layer 3 的第一步就会炸。
- 用户很难理解“是 queue 导入坏了”还是“wrapper 权限坏了”。

本质：

- 技能默认相信 wrapper 是健康的，但本地 checkout 未必满足。

建议：

- `plan` 前先做 wrapper 自检：
  - `ls -l bin/opencode-loop-plan.sh`
  - 如果不可执行，自动 `chmod +x`
  - 或直接 fallback 到 `bash bin/opencode-loop-plan.sh ...`

### 6. [已完成] `start --profile execute` 的语义非常误导

现象：

- 技能和参考都把它写成正式启动动作。
- 但 CLI 的 `cmd_start()` 只是直接 `exec` 组装后的命令，不负责切 `control.json.desired_state=running`。
- 主循环读取到 `desired_state=stopped` 时会立刻退出。

后果：

- 表面上“启动了 execute”，实际上 child loop 秒退。
- 用户会以为 `start` 语义就是“启动+恢复”，但真实语义只是“按当前状态执行命令”。

本质：

- 技能把 `start` 写成了“高层行为”，实际 CLI 实现只是“薄启动器”。

建议：

- 技能里明确区分：
  - `start/supervisor`：只启动进程
  - `control.json.desired_state`：才是真正的运行意图开关
- 在 execute 启动前强制检查：
  - `desired_state == running`
  - 如果不是，先改 control，再启动 supervisor

### 7. [已完成] `execute` profile 实际继承了 `quick` 的 15 分钟 timeout

现象：

- CLI 默认 `PROFILE="quick"`。
- `execute` 分支只设置 `MODE="execute"`，没有覆盖 `TIMEOUT_MINUTES`。
- 所以最终 `execute` 会继承 `quick` 的 `--timeout 15`。

后果：

- 用户以为开始的是长期自动跑，实际上每轮只有 15 分钟。
- 对带 `verify`、`graphify`、重测试的大仓库非常不友好。

本质：

- `execute` profile 没有独立参数定义，只是模式切换。

建议：

- 技能里必须明确：
  - `execute profile` 当前默认 timeout 很短，不能盲信
  - 长时仓库要显式改 timeout
- 更进一步，技能可以建议：
  - 长任务优先 `next-command --kind supervisor --profile execute`
  - 再把 timeout 显式改成 60 分钟或用户要求值

### 8. [已缓解] 状态面板和真实执行流可能严重脱节

现象：

- `status --json` 还显示 `running`
- `current_task_id` 也在
- 但 `progress.txt`、`supervisor-child.log` 很久不更新
- 同时 `output-1.jsonl` 还在持续写真实思考和 tool 调用

后果：

- 只看 `status` 会误判“还在健康跑”。
- 只看 `progress.txt` 又会误判“已经卡死”。

本质：

- 运行态真相分散在多层：
  - 高层状态：`state.json` / `runtime.json`
  - loop 边界日志：`supervisor.log` / `supervisor-child.log`
  - 真正流式产出：`output-*.jsonl`
- 技能没有明确“哪一层是真实活性来源”。

建议：

- 技能把排障顺序写死：
  1. `ps`
  2. `.opencode-loop/output-*.jsonl`
  3. `supervisor-child.log`
  4. `state.json` / `runtime.json`
- 不要只教用户看 `status --json`。

## [已缓解] 三、工作树与本地状态管理的坑

### 9. [已完成] dirty working tree 和 execute handoff 极易互相打架

现象：

- execute mode 在没有 active task 时，对 dirty tree 很敏感。
- child loop 会连续报：
  `Dirty working tree with no active task. Cannot start new task.`
- Full Auto bootstrap 又会先制造一批 repo-visible 改动：
  - `openspec/`
  - `.taskmaster/`
  - `.claude/`
  - `.gemini/`
  - `opencode.json`

后果：

- “准备 execute 的过程”本身会阻止“第一轮 execute 启动”。
- 这是最反直觉、也最容易卡住的一步。

本质：

- bootstrap 产物和 code-bearing round 缺少明确 handoff。

建议：

- 给技能单独加一节：
  `Full Auto bootstrap -> first execute round handoff`
- 明确要求：
  - import queue 之后，先 commit repo-visible bootstrap 资产
  - 再确保 worktree clean
  - 再启动第一轮 execute

### 10. [已完成] `.opencode-loop/` 是本地运行态，不是 repo 资产

现象：

- `.opencode-loop/` 默认被 Git 忽略。
- `queue.json`、`control.json`、`runtime.json`、logs 都不会跟着 commit 走。

后果：

- 用户很容易误以为“我已经在 repo 里建立好了 execute 队列”。
- 实际上 repo 里留下的是 OpenSpec、Task Master 和配置资产，本地机器上才有执行队列状态。

本质：

- 技能没有把“可复现资产”和“本地运行态”讲清楚。

建议：

- 技能里明确分层：
  - repo 资产：
    - `openspec/`
    - `.taskmaster/`
    - `opencode.json`
    - 必要时 `.claude/` / `.gemini/`
  - 本地运行态：
    - `.opencode-loop/queue.json`
    - `.opencode-loop/control.json`
    - `.opencode-loop/runtime.json`
    - `.opencode-loop/output-*.jsonl`
    - `.opencode-loop/logs/`

### 11. [已缓解] 启动后 runtime 还可能回写 repo-visible 文件

现象：

- 实战里启动 execute 后，`opencode.json` 又被 runtime 补写了 `$schema`。

后果：

- 即便你在 bootstrap 后做过一次 clean commit，也可能在刚启动 execute 后再次变脏。

本质：

- 部分配置文件既像 repo 配置，又会被运行时轻微修正。

建议：

- 技能要提醒：
  - 启动 execute 后，马上再看一次 `git status`
  - 如果只出现安全可接受的配置标准化写回，决定是否作为 bootstrap 尾声再补一笔提交

## [已缓解] 四、文档层体验上的坑

### 12. [已缓解] Full Auto bootstrap 的改动量很吵

现象：

- `openspec init` 生成 `.claude/`、`.gemini/`、`.opencode/`
- `task-master init` 生成 `.taskmaster/`、`.env.example`
- `opencode-loop init` 会写 `opencode.json`

后果：

- 用户如果只是想“开始自动跑”，会被一堆脚手架改动淹没。
- 技能如果不解释这些文件为何出现，很容易引起不信任。

建议：

- 技能在 Full Auto 开头显式说：
  - 这条路径会生成多套本地自动化脚手架
  - 哪些是正常的
  - 哪些需要 commit
  - 哪些只是本地辅助

## [已完成] 五、最值得直接写进技能的优化方案

### 1. 入口硬约束

- `opencode-loop` Full Auto Pipeline 覆盖通用 brainstorming / route-choice。
- 除非路径或需求本身不清楚，否则不要先进入设计问答。

### 2. OpenSpec artifact 生成改写

- `openspec new change` 后，不要假设 `proposal.md` 已存在。
- 立即运行 artifact instructions，显式生成：
  - `proposal.md`
  - `design.md`
  - `tasks.md`
  - `specs/**`

### 3. Task Master provider preflight

- 先探测环境变量
- 自动选 provider
- 自动写 `task-master models --set-main/--set-fallback/--set-research`
- 没有可用 key 再返回 blocker

### 4. `parse-prd` 后强制任务归一化

- 对照 OpenSpec `tasks.md`
- 删掉明显元自动化任务
- 把 queue 对准真实 repo 工作切片

### 5. wrapper 自愈

- `plan` 前检查 `bin/*.sh` 执行权限
- 不行就 `chmod +x`
- 再不行就 fallback 到 `bash ...`

### 6. execute 启动前双检查

- `control.json.desired_state == running`
- Git worktree clean，或已有 active task 承接脏改动

### 7. bootstrap -> first execute handoff 专节

建议伪流程：

1. 探测 env key 和 provider
2. `openspec new change` 后显式生成 `proposal/design/specs/tasks`
3. `parse-prd` 后强制任务归一化
4. import queue
5. enrich queue
6. commit repo-visible bootstrap 资产
7. 确认 `desired_state=running`
8. 确认 worktree clean
9. 再启动第一轮 execute

## [已缓解] 六、最准确的最终判断

- 这个技能不是“不能用”，而是“默认路径还不够抗真实环境噪声”。
- 真正的痛点不在模型能力，而在 **技能文案没有把运行时语义讲透**。
- 如果不修这些断层，代理每次都可能在不同位置重复踩同一类坑。

## [已归档] 七、本次实战额外新增的坑

这是在第一版总结之后，继续实跑时新增确认的坑：

- `execute profile` 当前默认会落回 `quick timeout=15`，这对中大型仓库的 `verify/build/graphify` 明显太短。
- `status --json` 的 `running` 不足以证明 loop 健康，必须交叉核对进程树和 `output-*.jsonl`。
- `queue next` 和当前 active task 的可见性可能不同步，不能只靠 `queue next` 判断是不是已经真正开跑。
- 启动后即便外层 `progress.txt` / `supervisor-child.log` 暂时不刷新，`output-*.jsonl` 仍可能在持续写真实执行流；活性检查必须优先看 output。

### 13. [待继续优化] Queue policy gate 失败语义不清，容易让人误判“这轮到底算成功还是失败”

现象：

- 实跑中 child log 出现：
  - `Queue gate policy failed for master-7`
  - 紧接着又出现
    `Delivery: commit | Counts iteration: true | Progress: true | Error: false`

后果：

- 从自动化视角看，这一轮既像失败，又像成功。
- 用户和代理都很难判断：
  - 是应该把它当成 landed change
  - 还是应该把它当成 rejected / blocked task

本质：

- gate 失败和 iteration delivery 统计之间的语义没有清晰对齐。
- “commit 已经发生” 与 “task gate 没过” 处于冲突状态。

建议：

- 技能里要提醒：
  - `policy failed` 不是普通 warning，必须立刻查看 queue task 状态与 gate 结果
  - 不能只看 `Delivery: commit`
- 更理想的是在工具层统一语义：
  - 要么 gate fail 时不要记作成功交付
  - 要么显式标记为 “commit happened but task not accepted”

### 14. [待继续优化] 任务重试时可能触发非法状态迁移

现象：

- `master-7` 在 policy gate 失败后重试，child log 明确出现：
  `Illegal status transition for master-7: in_progress -> in_progress`

后果：

- loop 虽然继续往下跑，但 queue 状态机已经不干净。
- 这会让后续恢复、监控、以及人工接管都变得很难判断。

本质：

- task retry 路径和 queue 状态机没有完全对齐。
- 一次失败重试前，缺少稳定的状态回退或 retry 中间态。

建议：

- 技能里加入一个 execute-mode 故障条目：
  - 如果出现 `Illegal status transition ... in_progress -> in_progress`
  - 先停 loop
  - 再人工检查 queue 当前 task 的 status / gate_results / attempt_count
- 如果未来优化工具本身，最好补一个明确 retry 状态或统一 retry 前回退逻辑。

### 15. [待继续优化] 停止后状态文件可能长期滞后，显示“还在 running”

现象：

- 实战中我把 `control.json.desired_state` 改成 `stopped`，并且后面还强杀了 supervisor / child / `opencode run` 进程。
- 但 `state.json` 和 `runtime.json` 仍然保留：
  - `status: running`
  - `process_state: running`
  - 旧 `pid`

后果：

- 用户会看到一种最糟糕的状态：
  - 真实进程已经没了
  - 但 `status --json` 还显示在跑
- 这会让“是否真的停下来了”都要靠 `ps` 再核对一遍。

本质：

- 停机控制和状态回写不是强一致的。
- 强制停机尤其容易留下陈旧 runtime/state 文件。

建议：

- 技能文档必须明确：
  - `status --json` 不是停机真相来源
  - 停止后要同时核对：
    1. `control.json`
    2. `ps`
    3. `state.json` / `runtime.json`
- 如果未来优化工具本身，停机后应该主动 reconcile：
  - `state.status=stopped`
  - `runtime.process_state=stopped`
  - `last_exit_reason=user_stop|killed`
