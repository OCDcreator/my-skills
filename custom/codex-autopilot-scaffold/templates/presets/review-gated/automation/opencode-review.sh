#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-}"
PRIMARY_PATH="${2:-}"
OUTPUT_PATH="${3:-}"
FOCUS_TEXT="${4:-}"
POLL_SECONDS="${AUTOPILOT_REVIEW_POLL_SECONDS:-60}"
TIMEOUT_SECONDS="${AUTOPILOT_REVIEW_TIMEOUT_SECONDS:-1800}"

if ! command -v opencode >/dev/null 2>&1; then
  echo "[review] opencode not found in PATH" >&2
  exit 1
fi

case "$MODE" in
  plan)
    if [[ -z "$PRIMARY_PATH" ]]; then
      echo "usage: bash ./automation/opencode-review.sh plan <plan-path> [output-path]" >&2
      exit 1
    fi
    if [[ -z "$OUTPUT_PATH" ]]; then
      OUTPUT_PATH="${PRIMARY_PATH%.*}.review.txt"
    fi
    PROMPT="/review-plan ${PRIMARY_PATH}"
    ;;
  code)
    if [[ -z "$PRIMARY_PATH" ]]; then
      OUTPUT_PATH="automation/runtime/review-code.txt"
    else
      OUTPUT_PATH="$PRIMARY_PATH"
    fi
    if [[ -n "$FOCUS_TEXT" ]]; then
      PROMPT="/review-code ${FOCUS_TEXT}"
    else
      PROMPT="/review-code"
    fi
    ;;
  *)
    echo "usage: bash ./automation/opencode-review.sh <plan|code> [path] [output-path] [focus]" >&2
    exit 1
    ;;
esac

mkdir -p "$(dirname "$OUTPUT_PATH")"
TEMP_OUTPUT="${OUTPUT_PATH}.tmp"
: > "$TEMP_OUTPUT"

opencode run "$PROMPT" >"$TEMP_OUTPUT" 2>&1 &
REVIEW_PID=$!
STARTED_AT="$(date +%s)"

echo "[review] mode=${MODE} pid=${REVIEW_PID}"
echo "[review] output=${OUTPUT_PATH}"
echo "[review] reviewer may be slow; polling every ${POLL_SECONDS}s for up to ${TIMEOUT_SECONDS}s"

while kill -0 "$REVIEW_PID" 2>/dev/null; do
  sleep "$POLL_SECONDS"
  if ! kill -0 "$REVIEW_PID" 2>/dev/null; then
    break
  fi
  ELAPSED="$(( $(date +%s) - STARTED_AT ))"
  echo "[review] still running after ${ELAPSED}s"
  if [[ "$TIMEOUT_SECONDS" -gt 0 && "$ELAPSED" -ge "$TIMEOUT_SECONDS" ]]; then
    kill "$REVIEW_PID" 2>/dev/null || true
    wait "$REVIEW_PID" || true
    echo "[review] timed out after ${ELAPSED}s" >&2
    exit 124
  fi
done

wait "$REVIEW_PID"
mv "$TEMP_OUTPUT" "$OUTPUT_PATH"

VERDICT="$(grep -E '^VERDICT:' "$OUTPUT_PATH" | tail -n 1 | sed 's/^VERDICT:[[:space:]]*//')"
SUMMARY="$(grep -E '^SUMMARY:' "$OUTPUT_PATH" | tail -n 1 | sed 's/^SUMMARY:[[:space:]]*//')"

{
  echo "VERDICT=${VERDICT:-UNKNOWN}"
  echo "SUMMARY=${SUMMARY:-}"
} > "${OUTPUT_PATH}.verdict.txt"

cat "$OUTPUT_PATH"
echo "[review] verdict=${VERDICT:-UNKNOWN}"
