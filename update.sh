#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || {
  echo "无法进入脚本所在目录。"
  exit 1
}

REPO_DIR="$(pwd)"
TMP_DIR="$REPO_DIR/.tmp-skills"
STATUS="SUCCESS"
DETAIL="外部资源已同步，变更已提交并推送。"
BRANCH="main"
REMOTE_URL=""
COMMIT_TS=""
COMMIT_MSG=""
SOURCE_ERRORS=0
COMMIT_DONE=0

SKILL_SOURCES=(
  "anthropics-skills|https://github.com/anthropics/skills.git|main|skills"
  "awesome-claude-skills|https://github.com/ComposioHQ/awesome-claude-skills.git|master|."
  "claude-plugins-official|https://github.com/anthropics/claude-plugins-official.git|main|."
  "axton-obsidian-visual-skills|https://github.com/axtonliu/axton-obsidian-visual-skills.git|main|."
  "baoyu-skills|https://github.com/JimLiu/baoyu-skills.git|main|skills"
  "kepano-obsidian-skills|https://github.com/kepano/obsidian-skills.git|main|skills"
  "taste-skill|https://github.com/Leonxlnx/taste-skill.git|main|skills"
  "html-ppt-skill|https://github.com/lewislulu/html-ppt-skill.git|main|."
  "ui-ux-pro-max-skill|https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git|main|.claude/skills"
)

REFERENCE_SOURCES=(
  "awesome-design-md|https://github.com/VoltAgent/awesome-design-md.git|main|design-md"
)

EXCLUDE_NAMES=(
  "composio-skills"
  "template-skill"
  "example-command"
  "example-skill"
)

line() {
  echo "============================================================"
}

pause_before_exit() {
  if [ -t 0 ]; then
    echo "按回车结束..."
    read -r _
  fi
}

cleanup() {
  rm -rf "$TMP_DIR"
}

finish() {
  echo
  line
  case "$STATUS" in
    SUCCESS) echo "结果：更新并推送成功" ;;
    NO_CHANGES) echo "结果：没有新变化" ;;
    CANCELLED) echo "结果：已取消" ;;
    PARTIAL) echo "结果：部分成功，需要查看警告" ;;
    *) echo "结果：执行失败" ;;
  esac
  echo "说明：$DETAIL"
  if [ "$SOURCE_ERRORS" -ne 0 ]; then
    echo "来源警告数量：$SOURCE_ERRORS"
  fi
  line
  echo

  echo "当前仓库状态："
  git status --short --branch 2>/dev/null || true
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
  echo "[重新推送当前分支]"
  echo "git -C \"$REPO_DIR\" push origin $BRANCH"
  echo
  echo "[先拉最新再推]"
  echo "git -C \"$REPO_DIR\" pull --rebase origin $BRANCH"
  echo "git -C \"$REPO_DIR\" push origin $BRANCH"
  echo
  echo "[检查 GitHub SSH 登录]"
  echo "ssh -T git@github.com"
  echo
  echo "[重新运行当前更新脚本]"
  echo "bash \"$REPO_DIR/update.sh\""
  echo
  echo "[删除临时目录，常用于上次更新中断]"
  echo "rm -rf \"$REPO_DIR/.tmp-skills\""
  echo

  if [ "$STATUS" = "ERROR" ]; then
    line
    echo "这次失败时，最常见的排查顺序："
    echo "1. 如果 clone 失败，先确认网络能访问 GitHub"
    echo "2. 如果 push 失败，执行：ssh -T git@github.com"
    echo "3. 如果远端比本地新，执行 pull --rebase 后再 push"
    echo "4. 如果提示作者身份未知，先配置 git user.name 和 user.email"
    echo "5. 如果临时目录删不掉，关闭占用窗口后执行 rm -rf 命令"
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

trap cleanup EXIT

line
echo "my-skills 外部资源更新助手"
echo
echo "这个脚本的用途："
echo "1. 从多个 GitHub 外部技能源下载最新内容"
echo "2. 从外部参考源下载最新设计参考"
echo "3. 复制到 external 目录"
echo "4. 如果有变化，就自动提交并推送"
echo
echo "当前仓库目录："
echo "$REPO_DIR"
line
echo

echo "[重要提醒]"
echo "这个脚本会访问 GitHub，并可能修改 external 目录。"
echo "如果你只是想上传自己改的 custom 技能，请关闭窗口，改用 push.sh。"
echo
printf '确认要更新外部资源并推送吗？请输入 Y 后回车继续：'
read -r CONFIRM
if [ "$CONFIRM" != "Y" ]; then
  STATUS="CANCELLED"
  DETAIL="你没有输入 Y，脚本已取消，没有改动任何文件。"
  finish
  exit 0
fi
echo

echo "[步骤 1/7] 检查 Git 是否可用..."
if ! command -v git >/dev/null 2>&1; then
  STATUS="ERROR"
  DETAIL="没有找到 Git。请先安装 Git，再重新运行这个脚本。"
  finish
  exit 1
fi
echo "[OK] 已找到 Git"
echo

echo "[步骤 2/7] 检查当前目录是不是 Git 仓库..."
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  STATUS="ERROR"
  DETAIL="当前目录不是 Git 仓库，所以无法更新、提交或推送。"
  finish
  exit 1
fi
BRANCH="$(git branch --show-current 2>/dev/null || true)"
REMOTE_URL="$(git remote get-url origin 2>/dev/null || true)"
[ -n "$BRANCH" ] || BRANCH="main"
if [ -z "$REMOTE_URL" ]; then
  STATUS="ERROR"
  DETAIL="没有找到名为 origin 的远端仓库，所以无法推送更新结果。"
  finish
  exit 1
fi
echo "[OK] 当前分支: $BRANCH"
echo "[OK] 远端地址: $REMOTE_URL"
echo

echo "[步骤 3/7] 准备临时下载目录..."
rm -rf "$TMP_DIR"
if ! mkdir -p "$TMP_DIR"; then
  STATUS="ERROR"
  DETAIL="无法创建临时目录 .tmp-skills。可能是权限问题或文件被占用。"
  finish
  exit 1
fi
mkdir -p "$REPO_DIR/external"
echo "[OK] 临时目录已准备"
echo

echo "[步骤 4/7] 下载并复制外部来源..."
echo
echo "[技能来源]"
echo

source_index=0
for source in "${SKILL_SOURCES[@]}"; do
  source_index=$((source_index + 1))
  IFS='|' read -r prefix url branch search_root <<< "$source"

  echo "[技能 $source_index/${#SKILL_SOURCES[@]}] $prefix"
  clone_dir="$TMP_DIR/$prefix"
  rm -rf "$clone_dir"

  if ! git clone --depth 1 --branch "$branch" "$url" "$clone_dir"; then
    SOURCE_ERRORS=$((SOURCE_ERRORS + 1))
    echo "[WARN] $prefix 下载失败"
    echo
    continue
  fi
  rm -rf "$clone_dir/.git"

  search_path="$clone_dir/$search_root"
  if [ ! -d "$search_path" ]; then
    SOURCE_ERRORS=$((SOURCE_ERRORS + 1))
    echo "[WARN] $prefix 没有找到预期目录：$search_path"
    echo
    continue
  fi

  rm -rf "$REPO_DIR/external/$prefix"
  mkdir -p "$REPO_DIR/external/$prefix"
  copied=0
  while IFS= read -r skill_dir; do
    skill_dir="${skill_dir%/}"
    skill_name="$(basename "$skill_dir")"
    skip=false
    for ex in "${EXCLUDE_NAMES[@]}"; do
      if [[ "$skill_name" == "$ex"* ]]; then
        skip=true
        break
      fi
    done
    if $skip; then
      continue
    fi

    if [ "$skill_name" = "." ] || [ "$skill_dir" = "$clone_dir" ]; then
      dest="$REPO_DIR/external/$prefix"
      if cp -R "$skill_dir"/. "$dest"; then
        copied=$((copied + 1))
      fi
    else
      dest="$REPO_DIR/external/$prefix/$skill_name"
      rm -rf "$dest"
      if cp -R "$skill_dir" "$dest"; then
        copied=$((copied + 1))
      fi
    fi
  done < <(find "$search_path" -name "SKILL.md" -exec dirname {} \; | sort -u)

  echo "[OK] $prefix 已复制 $copied 个技能"
  echo
done

echo "[参考来源]"
echo

reference_index=0
for source in "${REFERENCE_SOURCES[@]}"; do
  reference_index=$((reference_index + 1))
  IFS='|' read -r prefix url branch search_root <<< "$source"

  echo "[参考 $reference_index/${#REFERENCE_SOURCES[@]}] $prefix"
  clone_dir="$TMP_DIR/$prefix"
  rm -rf "$clone_dir"

  if ! git clone --depth 1 --branch "$branch" "$url" "$clone_dir"; then
    SOURCE_ERRORS=$((SOURCE_ERRORS + 1))
    echo "[WARN] $prefix 下载失败"
    echo
    continue
  fi
  rm -rf "$clone_dir/.git"

  search_path="$clone_dir/$search_root"
  if [ ! -d "$search_path" ]; then
    SOURCE_ERRORS=$((SOURCE_ERRORS + 1))
    echo "[WARN] $prefix 没有找到预期目录：$search_path"
    echo
    continue
  fi

  rm -rf "$REPO_DIR/external/$prefix"
  mkdir -p "$REPO_DIR/external/$prefix"
  copied=0
  for ref_dir in "$search_path"/*/; do
    if [ -d "$ref_dir" ]; then
      ref_name="$(basename "$ref_dir")"
      dest="$REPO_DIR/external/$prefix/$ref_name"
      rm -rf "$dest"
      if cp -R "$ref_dir" "$dest"; then
        copied=$((copied + 1))
      fi
    fi
  done

  echo "[OK] $prefix 已复制 $copied 个参考目录"
  echo
done

echo "[步骤 5/7] 清理临时目录..."
cleanup
echo "[OK] 临时目录已清理"
echo

echo "[步骤 6/7] 检查这次更新有没有实际变化..."
if ! git add -A; then
  STATUS="ERROR"
  DETAIL="git add -A 失败。通常是文件权限、路径或 Git 状态异常。"
  finish
  exit 1
fi

if git diff --cached --quiet; then
  if [ "$SOURCE_ERRORS" -eq 0 ]; then
    STATUS="NO_CHANGES"
    DETAIL="外部资源没有新变化，所以无需提交和推送。"
  else
    STATUS="PARTIAL"
    DETAIL="部分来源下载失败，而且没有检测到可提交的新变化。"
  fi
  finish
  exit 0
fi
echo "[OK] 检测到外部来源有变化"
echo

COMMIT_TS="$(date '+%Y-%m-%d %H:%M' 2>/dev/null || true)"
[ -n "$COMMIT_TS" ] || COMMIT_TS="$(date)"
COMMIT_MSG="sync external resources $COMMIT_TS"

echo "[步骤 7/7] 提交并推送更新结果..."
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

if [ "$SOURCE_ERRORS" -eq 0 ]; then
  STATUS="SUCCESS"
  DETAIL="外部资源已同步，变更已提交并推送。"
else
  STATUS="PARTIAL"
  DETAIL="已提交并推送可用更新，但有部分来源下载失败。"
fi

finish
exit 0
