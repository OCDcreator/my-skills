#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || {
  echo "无法进入脚本所在目录。"
  exit 1
}

REPO_DIR="$(pwd)"
STATUS="SUCCESS"
DETAIL="已成功提交并推送到远端。"
BRANCH="main"
REMOTE_URL=""
COMMIT_TS=""
COMMIT_MSG=""
COMMIT_DONE=0

line() {
  echo "============================================================"
}

pause_before_exit() {
  if [ -t 0 ]; then
    echo "按回车结束..."
    read -r _
  fi
}

finish() {
  echo
  line
  case "$STATUS" in
    SUCCESS) echo "结果：推送成功" ;;
    NO_CHANGES) echo "结果：没有变更，不需要推送" ;;
    *) echo "结果：执行失败" ;;
  esac
  echo "说明：$DETAIL"
  line
  echo

  echo "当前分支："
  git branch --show-current 2>/dev/null || true
  echo

  echo "最近 5 条提交："
  git log --oneline --decorate -n 5 2>/dev/null || true
  echo

  line
  echo "如果你不确定下一步怎么做，可以直接复制下面这些命令："
  line
  echo
  echo "[看仓库状态]"
  echo "git -C \"$REPO_DIR\" status --short --branch"
  echo
  echo "[看远端地址]"
  echo "git -C \"$REPO_DIR\" remote -v"
  echo
  echo "[看最近提交]"
  echo "git -C \"$REPO_DIR\" log --oneline --decorate -n 5"
  echo
  echo "[重新推送当前分支]"
  echo "git -C \"$REPO_DIR\" push origin $BRANCH"
  echo
  echo "[先拉最新再推]"
  echo "git -C \"$REPO_DIR\" pull --rebase origin $BRANCH"
  echo "git -C \"$REPO_DIR\" push origin $BRANCH"
  echo
  echo "[检查 Git 身份信息]"
  echo "git -C \"$REPO_DIR\" config user.name"
  echo "git -C \"$REPO_DIR\" config user.email"
  echo
  echo "[设置 Git 身份信息]"
  echo "git -C \"$REPO_DIR\" config user.name \"你的名字\""
  echo "git -C \"$REPO_DIR\" config user.email \"你的邮箱\""
  echo
  echo "[检查 GitHub SSH 登录]"
  echo "ssh -T git@github.com"
  echo

  if [ "$STATUS" = "ERROR" ]; then
    line
    echo "这次失败时，最常见的排查顺序："
    echo "1. 先复制执行：git -C \"$REPO_DIR\" status --short --branch"
    echo "2. 再复制执行：git -C \"$REPO_DIR\" remote -v"
    echo "3. 如果提示远端有新提交，执行："
    echo "   git -C \"$REPO_DIR\" pull --rebase origin $BRANCH"
    echo "   git -C \"$REPO_DIR\" push origin $BRANCH"
    echo "4. 如果提示权限或公钥问题，执行：ssh -T git@github.com"
    echo "5. 如果提示作者身份未知，执行上面的 user.name / user.email 设置命令"
    echo
    if [ "$COMMIT_DONE" -eq 1 ]; then
      echo "补充说明：本地提交已经创建成功，只是还没有推送到远端。"
      echo "你通常只需要修复权限或冲突问题后，再执行："
      echo "git -C \"$REPO_DIR\" push origin $BRANCH"
      echo
    fi
  fi

  line
  pause_before_exit
}

line
echo "my-skills 一键推送助手"
echo
echo "这个窗口会直接告诉你："
echo "1. 当前做到哪一步"
echo "2. 如果失败，最常见的原因是什么"
echo "3. 你下一步可以直接复制什么命令"
echo
echo "当前仓库目录："
echo "$REPO_DIR"
line
echo

echo "[步骤 1/5] 检查 Git 是否可用..."
if ! command -v git >/dev/null 2>&1; then
  STATUS="ERROR"
  DETAIL="没有找到 Git。请先安装 Git，再重新运行这个脚本。"
  finish
  exit 1
fi
echo "[OK] 已找到 Git"
echo

echo "[步骤 2/5] 检查当前目录是不是 Git 仓库..."
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  STATUS="ERROR"
  DETAIL="当前目录不是 Git 仓库，所以无法提交或推送。"
  finish
  exit 1
fi
BRANCH="$(git branch --show-current 2>/dev/null || true)"
REMOTE_URL="$(git remote get-url origin 2>/dev/null || true)"
[ -n "$BRANCH" ] || BRANCH="main"
if [ -z "$REMOTE_URL" ]; then
  STATUS="ERROR"
  DETAIL="没有找到名为 origin 的远端仓库，所以没有可推送的目标。"
  finish
  exit 1
fi
echo "[OK] 当前分支: $BRANCH"
echo "[OK] 远端地址: $REMOTE_URL"
echo

echo "[步骤 3/5] 暂存所有变更 (git add -A)..."
if ! git add -A; then
  STATUS="ERROR"
  DETAIL="git add -A 执行失败。通常是文件权限、路径或 Git 状态异常。"
  finish
  exit 1
fi
echo "[OK] 已完成暂存"
echo

echo "[步骤 4/5] 检查这次有没有新内容需要提交..."
if git diff --cached --quiet; then
  STATUS="NO_CHANGES"
  DETAIL="没有检测到新的变更，所以这次无需提交和推送。"
  finish
  exit 0
fi
echo "[OK] 检测到有新变更，准备提交"
echo

COMMIT_TS="$(date '+%Y-%m-%d %H:%M' 2>/dev/null || true)"
[ -n "$COMMIT_TS" ] || COMMIT_TS="$(date)"
COMMIT_MSG="sync $COMMIT_TS"

echo "[步骤 5/5] 创建提交并推送到远端..."
echo "[INFO] 提交信息: $COMMIT_MSG"
if ! git commit -m "$COMMIT_MSG"; then
  STATUS="ERROR"
  DETAIL="git commit 失败。常见原因是 Git 用户名/邮箱未配置，或提交钩子报错。"
  finish
  exit 1
fi
COMMIT_DONE=1
echo "[OK] 本地提交已创建"
echo

echo "[INFO] 正在推送到 origin/$BRANCH ..."
if ! git push origin "$BRANCH"; then
  STATUS="ERROR"
  DETAIL="git push 失败。常见原因是网络、SSH 权限、远端冲突，或当前账号无推送权限。"
  finish
  exit 1
fi
echo "[OK] 已成功推送到远端"

finish
exit 0
