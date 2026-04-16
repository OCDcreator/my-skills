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
else
  STATUS="PARTIAL"
  DETAIL="已提交并推送可用更新，但有部分来源下载失败。"
fi

finish
exit 0
