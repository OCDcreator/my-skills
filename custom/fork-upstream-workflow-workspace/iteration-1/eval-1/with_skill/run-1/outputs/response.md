最稳妥的做法是：把 `main` 当成你 fork 的稳定集成分支，先在 `main` 上吸收 `upstream/main`，默认用 `merge`，不要直接去改写已经长期使用的 `main` 历史。

先把角色分清：
- `origin`：你的 fork，可以推送
- `upstream`：原作者仓库，只作为同步来源
- `main`：你自己的稳定主线
- `feat/*` / `fix/*`：平时开发分支

如果你现在的情况是“我的 fork 的 `main` 上已经有自己的提交，`upstream/main` 也继续前进了，而且我不想丢自己的修改，也不想把历史搞乱”，默认推荐这条路线：

```bash
git status
git switch main
git fetch upstream
git pull origin main
git merge upstream/main
git push origin main
```

这样做的核心含义是：
- 你的个人提交会继续保留在 `main` 历史里
- 上游的新提交会以一次明确的合并进入你的 `main`
- 不需要重写已有提交，风险最低
- 以后回看历史时，也能一眼看出“这里是一次同步上游”

为什么这里默认推荐 `merge` 而不是 `rebase`：
- 你的 `main` 已经有自己的提交了，说明它不再是“纯镜像上游”的分支，而是你 fork 的长期基线
- 对这种长期使用、很可能已经推送到 `origin` 的 `main`，`merge` 更稳妥，因为不会改写历史
- `rebase` 虽然能让历史更直，但会重写 `main` 上已有提交；如果之后还要推回 `origin`，通常就涉及强推，这正是你现在想避免的

如果合并时出现冲突，说明上游修改和你的自定义修改落在了同一块地方。此时不要慌，按这个顺序处理：

```bash
git status
git add <已解决的文件>
git commit
git push origin main
```

最重要的原则是：冲突是在“保留你自己的修改”和“吸收上游更新”之间做人工整合，不是丢掉其中一边。

不要把下面这些做法当默认方案：
- 直接对已经公开使用的 `main` 做 `rebase upstream/main`
- 为了让历史更直，对 `main` 执行 `push --force`
- 带着未提交改动就开始同步上游

如果你后面还有自己的开发分支，正确顺序也是：先更新 `main`，再让功能分支跟进更新后的 `main`。功能分支这时可以再按情况决定用 `rebase main` 还是 `merge main`，但 `main` 本身优先保持稳，不要乱改历史。

一句话总结：对于“fork 的 `main` 已经有个人提交，又要稳妥跟进 `upstream/main`”这个场景，**最稳的默认方案就是：在干净工作区里切到 `main`，`fetch upstream` 后执行 `merge upstream/main`，解决冲突后再推回 `origin/main`。**
