#!/bin/bash
# 一键更新所有外部 skills submodule 并推送
cd "$(dirname "$0")"

echo ">>> 拉取 submodule 最新..."
git submodule update --remote

changed=$(git diff --stat external/)
if [ -z "$changed" ]; then
    echo ">>> 已经是最新，无需更新"
    exit 0
fi

echo ">>> 检测到更新:"
echo "$changed"
echo ""

git add external/
git commit -m "update submodules $(date +%Y-%m-%d)"
git push

echo ">>> 完成"
