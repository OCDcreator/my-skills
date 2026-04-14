#!/bin/bash
# 一键推送所有内容到远端
cd "$(dirname "$0")"

git add -A

if git diff --cached --quiet; then
    echo ">>> 没有变更，无需推送"
    exit 0
fi

git commit -m "sync $(date +%Y-%m-%d\ %H:%M)"
git push

echo ">>> 完成"
