下面给你一个适合个人开发者、长期维护 fork 的方案：核心思路是把 `origin` 当成你自己的发布仓库，把 `upstream` 当成外部更新来源，把 `main` 作为“已整理、可长期保存”的主分支，再用功能分支承载每次开发。

## 一、推荐的 remote 方案

保留两个 remote：

- `origin`：你的 GitHub fork 仓库，拥有推送权限
- `upstream`：原作者仓库，只读同步来源

先确认或设置：

```bash
git remote -v
git remote add upstream https://github.com/原作者/原仓库.git
git fetch upstream
```

如果 `upstream` 已存在，就不用重复添加。

日常你会看到这样的分工：

- `origin/main`：你自己的稳定主线
- `upstream/main`：原作者最新主线

## 二、推荐的分支方案

个人开发者我建议用 3 层思路，简单且够稳：

### 1. `main`

你的长期主分支，只放：

- 已同步的上游更新
- 你已经确认要长期保留的定制修改

不要直接在 `main` 上随手开发。

### 2. `feat/*`

你的日常开发分支，例如：

- `feat/ui-tweaks`
- `feat/local-ai`
- `feat/custom-tools`

所有新改动先在这里做，完成后再合回 `main`。

### 3. 可选：`sync/upstream-YYYYMMDD`

如果你担心同步上游时冲突较多，可以临时开一个同步分支，先处理冲突、验证无误，再合回 `main``。`

这不是必须，但在上游更新频繁、你本地改动也很多时很好用。

## 三、为什么推荐这种方式

这个方案适合个人维护 fork，原因是：

- `main` 始终代表“我自己的可用版本”
- 上游同步和个人开发分开，出问题更容易定位
- 功能分支让你可以小步提交，不会把 `main` 搞乱
- 即使以后改成提 PR、发 release，这套结构也不用推翻

## 四、同步上游时，建议用 `merge` 而不是直接 `rebase`

如果你的 fork 目标是“长期保留自己的定制修改”，我更推荐：

- 上游同步到 `main` 时优先用 `merge`
- 你自己的功能分支，必要时再 `rebase main`

原因：

1. `merge upstream/main` 更符合“把上游更新并入我的主线”这个语义
2. 它不会改写你 `main` 的历史，长期维护更稳
3. 当你已经有很多本地定制提交时，反复 rebase `main` 成本会越来越高

所以建议原则是：

- `main` 跟上游：`merge`
- `feat/*` 跟 `main`：可 `rebase`

## 五、初始化后的日常命令

### 1. 首次设置 upstream

```bash
git remote add upstream https://github.com/原作者/原仓库.git
git fetch upstream
```

### 2. 确保本地主分支跟踪自己的 fork

```bash
git checkout main
git branch --set-upstream-to=origin/main main
git pull origin main
```

### 3. 从 `main` 开新功能分支

```bash
git checkout main
git pull origin main
git checkout -b feat/my-change
```

### 4. 开发完成后合回 `main`

```bash
git checkout main
git merge --no-ff feat/my-change
git push origin main
```

如果你不在意保留分支合并痕迹，也可以不用 `--no-ff`。

## 六、最常用的“同步上游”流程

这是最推荐你养成习惯的一套：

```bash
git fetch upstream
git fetch origin
git checkout main
git pull origin main
git merge upstream/main
git push origin main
```

含义是：

1. 拉取原作者最新更新
2. 拉取你自己 fork 上最新状态
3. 切到你的主分支 `main`
4. 先保证本地 `main` 和 `origin/main` 一致
5. 把 `upstream/main` 合并进来
6. 把同步后的结果推回你的 fork

## 七、如果同步时有冲突，怎么处理

执行：

```bash
git merge upstream/main
```

如果出现冲突：

```bash
git status
```

手动改完冲突文件后：

```bash
git add 冲突文件1 冲突文件2
git commit
git push origin main
```

建议处理冲突时遵循这个原则：

- 原作者修 bug / 安全更新：优先保留上游逻辑
- 你自己的产品定制：在上游基础上重新套回去
- 不要盲目整段选择 “ours” 或 “theirs”，容易把有效修改覆盖掉

## 八、功能分支如何跟进最新主线

如果你开发到一半，上游已经同步到你的 `main`，可以这样更新功能分支：

```bash
git checkout feat/my-change
git fetch origin
git rebase main
```

或者更稳一点：

```bash
git checkout feat/my-change
git merge main
```

怎么选：

- 想让功能分支历史更干净：`rebase main`
- 想少折腾历史、降低出错风险：`merge main`

对个人项目来说，两者都可以；如果你不想处理太多历史问题，优先 `merge main` 也没问题。

## 九、我最建议你的分支纪律

可以直接照着执行：

- `main` 只做两件事：同步上游、合并已完成功能
- 平时开发都在 `feat/*`
- 每次同步上游前，先 `git fetch upstream`
- 每次准备推送前，先 `git pull origin main`
- 大冲突时，先开临时同步分支，不要直接在混乱状态下硬改 `main`

## 十、一个适合长期使用的固定工作流

### 日常开发

```bash
git checkout main
git pull origin main
git checkout -b feat/some-work
```

开发中提交：

```bash
git add .
git commit -m "feat: add some work"
```

完成后：

```bash
git checkout main
git merge --no-ff feat/some-work
git push origin main
git branch -d feat/some-work
```

### 定期同步上游

```bash
git fetch upstream
git checkout main
git pull origin main
git merge upstream/main
git push origin main
```

### 功能分支跟进最新主线

```bash
git checkout feat/some-work
git rebase main
```

或：

```bash
git checkout feat/some-work
git merge main
```

## 十一、如果你想更稳，可以加一个同步专用分支

当上游变化很大时：

```bash
git fetch upstream
git checkout main
git pull origin main
git checkout -b sync/upstream-20260416
git merge upstream/main
```

在这个分支里解决冲突、测试没问题后：

```bash
git checkout main
git merge sync/upstream-20260416
git push origin main
git branch -d sync/upstream-20260416
```

这样做的好处是：同步过程和正式主线隔离，心理压力小很多。

## 十二、最后给你一个最简结论

如果你只想记住一套最实用的方案，就用这个：

- remote：`origin` 指向你的 fork，`upstream` 指向原作者仓库
- 主分支：只保留一个长期分支 `main`
- 开发分支：每次从 `main` 拉 `feat/*`
- 同步上游：在 `main` 上执行 `git merge upstream/main`
- 推送位置：永远推到 `origin`

最常用命令可以直接记成：

```bash
git fetch upstream
git checkout main
git pull origin main
git merge upstream/main
git push origin main
```

如果你愿意，我下一步可以继续给你整理一份：

1. `fork` 项目的冲突处理清单
2. 适合个人开发者的提交信息规范
3. 把上面流程做成一个可直接复制的 Git alias 配置
