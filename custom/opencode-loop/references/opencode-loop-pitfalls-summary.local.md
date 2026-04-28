# opencode-loop 踩坑痛点总结

这份总结基于一次在 macOS 上、面向 `opencodian` 仓库、完整走通 `opencode-loop` 技能的实战。重点不是功能缺失，而是 **技能文案、CLI 语义、运行时状态机、以及真实仓库工作流之间的断层**。

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
## 已完成/已缓解的旧痛点

下面第 1-15 条是上一轮总结里的痛点。你已经在新版 skill / 项目里对它们做了显式修补或明显缓解，因此这里保留为“归档 + 回归清单”，不再作为当前主矛盾。

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
