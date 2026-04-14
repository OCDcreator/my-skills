#!/bin/bash
# 一键拉取远端覆盖本地
cd "$(dirname "$0")"

echo ">>> 拉取远端..."
git fetch origin

echo ">>> 覆盖本地..."
git reset --hard origin/main

echo ">>> 完成"
