#!/usr/bin/env bash
set -euo pipefail

APP_PATH="${1:-/Applications/Obsidian.app}"
PORT="${2:-9222}"
WAIT_SECONDS="${3:-20}"
VAULT_URI="${4:-}"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Obsidian app bundle not found: $APP_PATH" >&2
  exit 1
fi

osascript -e 'tell application "Obsidian" to quit' >/dev/null 2>&1 || true
sleep 2

open -na "$APP_PATH" --args "--remote-debugging-port=$PORT"

for ((i=0; i<WAIT_SECONDS; i+=1)); do
  if curl -sS --max-time 2 "http://127.0.0.1:${PORT}/json/list" >/dev/null 2>&1; then
    if [[ -n "$VAULT_URI" ]]; then
      open "$VAULT_URI" >/dev/null 2>&1 || true
    fi
    echo "CDP ready on port $PORT"
    exit 0
  fi
  sleep 1
done

echo "Timed out waiting for Obsidian CDP on port $PORT" >&2
exit 1
