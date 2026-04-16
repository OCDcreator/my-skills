---
name: fork-upstream-workflow
description: Use when the user is maintaining a personal Git fork and needs to keep their own changes while following updates from the original repository. Trigger for requests about `origin` vs `upstream`, syncing a fork with the original author, managing `main` plus feature branches, choosing merge vs rebase in a fork workflow, or Chinese requests such as 管理 fork、跟进上游、同步原作者更新、保留个人修改、设置 upstream remote.
---

# Fork Upstream Workflow

把 fork 维护成一个长期可用的个人分支体系，而不是临时拼命令。这个 skill 的重点不是背 Git 命令，而是先把角色分清，再决定命令应该落在哪个分支上。

## 这个 skill 适合什么情况

当用户处在下面这些场景时，优先使用这个 skill：

- fork 了别人的仓库，想长期保留自己的定制修改
- 想让自己的 fork 持续跟进原作者更新
- 不确定 `origin`、`upstream`、`main`、`feat/*` 该怎么分工
- 不确定同步上游时该 `merge` 还是 `rebase`
- 已经有个人提交了，但又怕同步上游时把历史搞乱

不要把这个 skill 用成通用 Git 入门教程。它专门回答“**个人 fork 怎么长期维护**”。

## 先建立角色模型

先把这四个对象讲清楚，再给命令：

- `origin`：用户自己的 fork，能推送
- `upstream`：原作者仓库，作为同步来源
- `main`：用户自己 fork 的稳定集成分支
- `feat/*` / `fix/*`：用户的短生命周期开发分支

如果用户还没有 `upstream`，先补上：

```bash
git remote add upstream https://github.com/owner/repo.git
git fetch upstream
```

## 默认工作流

优先推荐这套个人维护 fork 的默认流程：

1. `main` 只做两件事：同步上游、合并已完成功能
2. 平时开发都在 `feat/*` 或 `fix/*`
3. 跟进原作者更新时，先在 `main` 上吸收 `upstream/main`
4. 功能分支需要跟进最新主线时，再从更新后的 `main` 获取变更

这个顺序很重要，因为 `main` 代表的是“我这个 fork 当前认可的稳定基线”。功能分支应该建立在这个基线之上，而不是各自直接乱跟 `upstream/main` 打交道。

## 默认同步上游方案

如果用户没有特别强调要线性历史，或者 `main` 已经承担长期集成作用，默认推荐在 `main` 上做 `merge upstream/main`。

### 推荐步骤

先提醒用户保证工作区干净：

```bash
git status
```

如果有未提交改动，先 `commit` 或 `stash`，不要带着脏工作区同步上游。

然后：

```bash
git switch main
git fetch upstream
git pull origin main
git merge upstream/main
git push origin main
```

### 为什么默认用 `merge`

- 不改写 `main` 历史，更稳
- 适合已经推送过、已经长期使用的 fork 主分支
- 冲突出现时，用户更容易理解“这是一次上游同步”

除非用户明确说“我的 `main` 只有自己用，而且我接受改历史和强推”，否则不要把 rebase `main` 当默认建议。

## 功能分支如何跟进最新主线

先更新 `main`，再更新功能分支。优先讲这个顺序，不要直接跳到“在功能分支上对 `upstream/main` 做 rebase”。

### 推荐顺序

先更新主线：

```bash
git switch main
git fetch upstream
git pull origin main
git merge upstream/main
git push origin main
```

然后切回功能分支：

```bash
git switch feat/my-change
```

接下来根据场景选 `rebase main` 或 `merge main`。

## `merge` 还是 `rebase` 的判断

| 场景 | 推荐 | 原因 |
|------|------|------|
| `main` 跟进 `upstream/main` | `merge` | `main` 是稳定集成分支，默认不要改写历史 |
| 个人功能分支，未共享，想要干净历史 | `rebase main` | 保留线性历史，后续回看或提 PR 更清楚 |
| 功能分支已共享，或用户怕改历史 | `merge main` | 风险更低，不影响别人已有提交基线 |

### 功能分支用 `rebase`

适合只有自己在用、想保持历史整洁的分支：

```bash
git switch feat/my-change
git rebase main
```

如果中途冲突：

```bash
git status
git add <resolved-files>
git rebase --continue
```

如果分支已经推到 `origin`，通常还要：

```bash
git push --force-with-lease origin feat/my-change
```

这里要明确提醒：对功能分支可以讨论 `--force-with-lease`，但不要把这种做法迁移到 `main`。

### 功能分支用 `merge`

适合已经共享或用户更看重稳妥：

```bash
git switch feat/my-change
git merge main
```

如果有冲突：

```bash
git status
git add <resolved-files>
git commit
```

## 明确告诉用户不要做什么

如果用户的目标是长期维护 fork，默认要拦住这些高风险做法：

- 长期直接在 `main` 上开发
- 未提交改动时直接同步上游
- 把 `rebase upstream/main` 当成更新所有功能分支的默认第一反应
- 为了让历史变直，就对已经公开使用的 `main` 做强推

如果用户确实想打破这些默认规则，可以解释代价，但不要把危险做法包装成推荐方案。

## 输出结构

回答这类问题时，优先用这个结构：

1. **角色说明**：`origin` / `upstream` / `main` / `feat/*` 各干什么
2. **推荐策略**：先给个人 fork 的默认维护路线
3. **命令步骤**：给可直接复制的命令
4. **判断依据**：为什么这里是 `merge`，那里是 `rebase`
5. **风险提醒**：脏工作区、共享分支、`force-with-lease`、不要 force push `main`

## 回答风格

- 默认用用户的语言回答；中文用户优先中文
- 先给推荐路线，再给备选
- 解释为什么，而不是只列命令
- 如果用户问的是一个很窄的问题，也要补一句它在整体 fork 工作流里的位置

## 例子

**例子 1：用户问“fork 怎么长期同步上游还保留自己修改？”**

应该回答：

- `origin` 是你的 fork，`upstream` 是原仓库
- `main` 保持稳定，平时开发在 `feat/*`
- 同步上游默认在 `main` 上 `fetch upstream` + `merge upstream/main`
- 功能分支需要最新基线时，再 `rebase main` 或 `merge main`

**例子 2：用户问“我开发到一半，上游更新了，该在功能分支上 rebase upstream/main 吗？”**

应该优先回答：

- 先把 `main` 跟 `upstream/main` 同步
- 再回到功能分支决定 `rebase main` 还是 `merge main`
- 不要把“功能分支直接对 upstream/main 操作”当默认维护路线
