# 推荐方案

对于个人长期维护 fork，建议把角色固定下来：

- `origin`：你的 fork，负责日常推送和备份
- `upstream`：原作者仓库，只作为同步来源
- `main`：你 fork 里的稳定集成分支，只负责吸收上游更新和汇总已完成改动
- `feat/*`、`fix/*`：你平时开发功能或修复问题的短生命周期分支

核心原则是：**不要长期直接在 `main` 上开发**。你的定制修改放在功能分支里完成，确认稳定后再合并回 `main`。这样 `main` 始终代表“我这份 fork 当前认可的稳定基线”。

# Remote 设置

如果你现在只有 `origin`，补上 `upstream`：

```bash
git remote -v
git remote add upstream https://github.com/原作者/原仓库.git
git fetch upstream
```

之后保持这个分工：

- `origin/main`：你自己的稳定主线
- `upstream/main`：原作者持续更新的主线

# 分支策略

推荐给个人开发者的默认路线：

1. `main` 只做两件事：同步 `upstream/main`、接收你已经完成的功能分支
2. 新工作一律从最新 `main` 拉出：`feat/xxx` 或 `fix/xxx`
3. 原作者更新后，先更新 `main`
4. 你的功能分支如果需要最新基线，再从更新后的 `main` 获取变更

不要把“在功能分支上直接对 `upstream/main` 做操作”当成默认工作流。先更新 `main`，再更新功能分支，会更清晰也更稳。

# 日常命令

## 1. 开始一个新功能

先确保本地主线是最新稳定基线：

```bash
git switch main
git pull origin main
git switch -c feat/my-change
```

开发完成后提交：

```bash
git add .
git commit -m "feat: add my custom change"
git push -u origin feat/my-change
```

## 2. 定期同步原作者更新

同步前先确认工作区干净：

```bash
git status
```

如果有未提交改动，先 `commit` 或 `stash`，不要带着脏工作区同步上游。

然后在 `main` 上同步：

```bash
git switch main
git fetch upstream
git pull origin main
git merge upstream/main
git push origin main
```

这是推荐默认方案。

## 3. 让正在开发的功能分支跟上最新主线

先把 `main` 更新完，再切回你的功能分支：

```bash
git switch feat/my-change
```

这时有两种做法。

### 做法 A：`rebase main`

适合只有你自己在用、想保持历史整洁：

```bash
git rebase main
```

如果有冲突：

```bash
git status
git add <已解决的文件>
git rebase --continue
```

如果这个分支之前已经推到 `origin`，通常还要：

```bash
git push --force-with-lease origin feat/my-change
```

### 做法 B：`merge main`

适合你更看重稳妥，或者这个分支已经共享给别人：

```bash
git merge main
```

如果有冲突：

```bash
git status
git add <已解决的文件>
git commit
```

## 4. 把完成的功能并回主线

当功能分支验证完成后，再合并回 `main`：

```bash
git switch main
git merge feat/my-change
git push origin main
```

如果你不再需要这个分支：

```bash
git branch -d feat/my-change
git push origin --delete feat/my-change
```

# 为什么这里推荐 `main` 用 `merge`

默认建议在 `main` 上执行：

```bash
git merge upstream/main
```

原因是：

- `main` 是长期稳定集成分支，默认不要改写历史
- 你以后回看提交时，能明确看出哪一次是在“同步上游”
- 对已经推送过、长期使用的 fork 来说，风险比 rebase 更低

只有在你非常明确地接受“改写历史 + 必要时强推”，并且这个 `main` 只有你自己使用时，才考虑 rebase `main`。对大多数个人长期维护 fork 的场景，不建议把它作为默认方案。

# 简化判断

可以直接记这张规则：

- `main` 跟进 `upstream/main`：默认用 `merge`
- 个人功能分支，未共享，想要干净历史：优先 `rebase main`
- 功能分支已共享，或者你不想改历史：用 `merge main`

# 风险提醒

- 不要长期直接在 `main` 上开发
- 不要在未提交改动时同步上游
- 不要把 `rebase upstream/main` 当成所有功能分支的默认更新方式
- 可以对个人功能分支用 `git push --force-with-lease`，但**不要对 `main` force push**

如果你想要最省心的一套日常习惯，可以直接记成一句话：**`main` 负责跟上游同步，开发永远在 `feat/*`，功能分支需要最新代码时再从 `main` 更新自己。**
