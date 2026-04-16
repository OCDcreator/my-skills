推荐做法：**先在 `main` 上同步上游，再回到你的 `feat/ui-tweak` 分支决定用 `rebase main` 还是 `merge main`**。不要把“直接在功能分支上对 `upstream/main` 操作”当默认路线。

1. **角色分工**
- `origin`：你的 fork，可推送
- `upstream`：原作者仓库，作为同步来源
- `main`：你 fork 里的稳定基线，只负责同步上游和集成完成的功能
- `feat/ui-tweak`：你当前开发分支，平时在这里做改动

2. **默认推荐策略**
- `main` 跟进 `upstream/main` 时，默认用 `merge`
- `feat/ui-tweak` 跟进最新 `main` 时：
  - 只有你自己用、想保持线性历史：用 `rebase main`
  - 分支已经共享，或你不想改历史：用 `merge main`

3. **先更新 `main`**
先确保工作区干净：

```bash
git status
```

如果有未提交改动，先 `commit` 或 `stash`。

然后在 `main` 上同步上游：

```bash
git switch main
git fetch upstream
git pull origin main
git merge upstream/main
git push origin main
```

4. **再更新你的功能分支**
切回功能分支：

```bash
git switch feat/ui-tweak
```

如果这个分支**只有你自己在用**，推荐：

```bash
git rebase main
```

如果中途冲突：

```bash
git status
git add <已解决的文件>
git rebase --continue
```

如果这个分支之前已经推到 `origin`，rebase 后通常还要：

```bash
git push --force-with-lease origin feat/ui-tweak
```

如果这个分支**已经共享**，或者你想更稳妥，改用：

```bash
git switch feat/ui-tweak
git merge main
```

如果有冲突：

```bash
git status
git add <已解决的文件>
git commit
```

5. **判断依据**
- **为什么 `main` 上默认用 `merge upstream/main`**
  - `main` 是稳定集成分支，默认不改写历史更稳
  - 你以后回看提交时，能清楚知道这是一次“同步上游”
  - 对长期维护的 fork，更适合保守策略

- **为什么功能分支常用 `rebase main`**
  - 你的功能提交会被“平移”到最新 `main` 之后，历史更直
  - 后续自己看、或者提 PR，都更清晰
  - 前提是这个分支主要是你自己使用，能接受改写历史

- **什么时候功能分支改用 `merge main`**
  - 这个分支已经被别人拉走或协作使用
  - 你不想 force push
  - 你更重视低风险，而不是提交历史是否线性

6. **不推荐的默认做法**
- 不要直接在 `feat/ui-tweak` 上把 `upstream/main` 当同步入口
- 不要在脏工作区状态下同步上游
- 不要为了线性历史去 rebase 公开使用的 `main`
- 不要对 `main` 做 `push --force`

一句话结论：**你的场景里，默认是 `main` 上 `merge upstream/main`，然后 `feat/ui-tweak` 上优先 `rebase main`；如果功能分支已共享，就把第二步改成 `merge main`。**
