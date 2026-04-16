最稳妥、也最不容易把历史搞乱的做法，是：**先保留你 fork 的 `main` 历史不改写，再把 `upstream/main` 合并进来**，而不是对已经公开使用的 `main` 做 rebase。

如果你的 `main` 上已经有自己的提交，而且这些提交可能已经推到远端，推荐用 **merge 同步 upstream**。

可以按这个顺序做：

1. 先确认远程是否齐全

```bash
git remote -v
```

理想情况是：
- `origin` 指向你自己的 fork
- `upstream` 指向原仓库

如果还没有 `upstream`：

```bash
git remote add upstream <原仓库地址>
```

2. 获取最新远程状态

```bash
git fetch origin
git fetch upstream
```

3. 切到你自己的 `main`

```bash
git checkout main
```

如果本地有未提交修改，先处理掉，避免合并时混进去：

```bash
git status
git stash push -u -m "temp before syncing upstream"
```

4. 先确保本地 `main` 和你 fork 的 `origin/main` 对齐

```bash
git pull origin main
```

如果你平时禁止 `pull` 自动合并，也可以显式写成：

```bash
git fetch origin
git merge origin/main
```

5. 把 `upstream/main` 合并进你自己的 `main`

```bash
git merge upstream/main
```

这是最稳妥的一步。它的特点是：
- 不会丢你自己 `main` 上的提交
- 不会改写已有历史
- 即使之后要回溯，也容易看清楚“什么时候同步了上游”

如果有冲突，Git 会提示你解决。解决后执行：

```bash
git add <冲突文件>
git commit
```

如果没有冲突，Git 会自动生成一个 merge commit。

6. 推回你的 fork

```bash
git push origin main
```

如果你之前用了 stash，再恢复：

```bash
git stash pop
```

最推荐的完整命令流是：

```bash
git remote -v
git fetch origin
git fetch upstream
git checkout main
git status
git pull origin main
git merge upstream/main
git push origin main
```

如果你关心“历史别太乱”，这里有个判断标准：

- **你的 `main` 已经承担长期集成作用**：用 `merge upstream/main` 最合适。
- **你的 `main` 只有你自己在用，而且你非常想要线性历史**：理论上可以 rebase 到 `upstream/main`，但这会改写你 `main` 的提交历史；如果已经推送过，就需要强推，风险更高，不算“最稳妥”。

所以在你这个场景里，结论很明确：

**不要 rebase 现有的 `main`，直接在 `main` 上 merge `upstream/main`，这是最稳、最不容易出事故的同步方式。**

如果你还想进一步把日常流程也整理好，一个更稳的习惯是：
- `main` 专门用来同步 `origin/main` 和 `upstream/main`
- 自己的功能修改平时放在 `feat/*` 分支
- 功能分支基于最新 `main` 开发，需要时对功能分支做 rebase，但尽量不要重写 `main`

这样以后 upstream 再更新，你只需要周期性：

```bash
git checkout main
git fetch upstream
git merge upstream/main
git push origin main
```

这套流程对 fork 场景最稳，出问题也最好恢复。
