#!/usr/bin/env bash
set -euo pipefail

PLUGIN_ID=""
TEST_VAULT_PLUGIN_DIR=""
VAULT_NAME=""
OBSIDIAN_COMMAND=""
DEPLOY_FROM="dist"
OUTPUT_DIR=".obsidian-debug"
BUILD_COMMAND="npm run build"
WATCH_SECONDS=20
POLL_INTERVAL_MS=1000
CONSOLE_LIMIT=200
DOM_SELECTOR=".workspace-leaf.mod-active"
DOM_TEXT=0
HOT_RELOAD_MODE="controlled"
HOT_RELOAD_SETTLE_MS=0
USE_CDP=0
CDP_HOST="127.0.0.1"
CDP_PORT=9222
CDP_TARGET_TITLE_CONTAINS=""
CDP_RELOAD_DELAY_MS=800
CDP_EVAL_AFTER_RELOAD=""
SCENARIO_NAME=""
SCENARIO_PATH=""
SCENARIO_COMMAND_ID=""
SURFACE_PROFILE_PATH=""
SCENARIO_SLEEP_MS=2000
ASSERTIONS_PATH=""
COMPARE_DIAGNOSIS_PATH=""
SKIP_BOOTSTRAP=0
BOOTSTRAP_ALLOW_RESTART=1
BOOTSTRAP_POLL_INTERVAL_MS=1000
BOOTSTRAP_DISCOVERY_TIMEOUT_MS=12000
BOOTSTRAP_RELOAD_WAIT_MS=1500
BOOTSTRAP_RESTART_WAIT_MS=8000
BOOTSTRAP_ENABLE_WAIT_MS=1000
SKIP_BUILD=0
SKIP_DEPLOY=0
SKIP_RELOAD=0
SKIP_SCREENSHOT=0
SKIP_DOM=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plugin-id) PLUGIN_ID="$2"; shift 2 ;;
    --test-vault-plugin-dir) TEST_VAULT_PLUGIN_DIR="$2"; shift 2 ;;
    --vault-name) VAULT_NAME="$2"; shift 2 ;;
    --obsidian-command) OBSIDIAN_COMMAND="$2"; shift 2 ;;
    --deploy-from) DEPLOY_FROM="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --build-command) BUILD_COMMAND="$2"; shift 2 ;;
    --watch-seconds) WATCH_SECONDS="$2"; shift 2 ;;
    --poll-interval-ms) POLL_INTERVAL_MS="$2"; shift 2 ;;
    --console-limit) CONSOLE_LIMIT="$2"; shift 2 ;;
    --dom-selector) DOM_SELECTOR="$2"; shift 2 ;;
    --hot-reload-mode) HOT_RELOAD_MODE="$2"; shift 2 ;;
    --hot-reload-settle-ms) HOT_RELOAD_SETTLE_MS="$2"; shift 2 ;;
    --cdp-host) CDP_HOST="$2"; shift 2 ;;
    --cdp-port) CDP_PORT="$2"; shift 2 ;;
    --cdp-target-title-contains) CDP_TARGET_TITLE_CONTAINS="$2"; shift 2 ;;
    --cdp-reload-delay-ms) CDP_RELOAD_DELAY_MS="$2"; shift 2 ;;
    --cdp-eval-after-reload) CDP_EVAL_AFTER_RELOAD="$2"; shift 2 ;;
    --scenario-name) SCENARIO_NAME="$2"; shift 2 ;;
    --scenario-path) SCENARIO_PATH="$2"; shift 2 ;;
    --scenario-command-id) SCENARIO_COMMAND_ID="$2"; shift 2 ;;
    --surface-profile) SURFACE_PROFILE_PATH="$2"; shift 2 ;;
    --scenario-sleep-ms) SCENARIO_SLEEP_MS="$2"; shift 2 ;;
    --assertions) ASSERTIONS_PATH="$2"; shift 2 ;;
    --compare-diagnosis) COMPARE_DIAGNOSIS_PATH="$2"; shift 2 ;;
    --skip-bootstrap) SKIP_BOOTSTRAP=1; shift ;;
    --bootstrap-allow-restart) BOOTSTRAP_ALLOW_RESTART="$2"; shift 2 ;;
    --bootstrap-poll-interval-ms) BOOTSTRAP_POLL_INTERVAL_MS="$2"; shift 2 ;;
    --bootstrap-discovery-timeout-ms) BOOTSTRAP_DISCOVERY_TIMEOUT_MS="$2"; shift 2 ;;
    --bootstrap-reload-wait-ms) BOOTSTRAP_RELOAD_WAIT_MS="$2"; shift 2 ;;
    --bootstrap-restart-wait-ms) BOOTSTRAP_RESTART_WAIT_MS="$2"; shift 2 ;;
    --bootstrap-enable-wait-ms) BOOTSTRAP_ENABLE_WAIT_MS="$2"; shift 2 ;;
    --dom-text) DOM_TEXT=1; shift ;;
    --use-cdp) USE_CDP=1; shift ;;
    --skip-build) SKIP_BUILD=1; shift ;;
    --skip-deploy) SKIP_DEPLOY=1; shift ;;
    --skip-reload) SKIP_RELOAD=1; shift ;;
    --skip-screenshot) SKIP_SCREENSHOT=1; shift ;;
    --skip-dom) SKIP_DOM=1; shift ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$PLUGIN_ID" ]]; then
  echo "--plugin-id is required" >&2
  exit 1
fi

if [[ -z "$TEST_VAULT_PLUGIN_DIR" ]]; then
  echo "--test-vault-plugin-dir is required" >&2
  exit 1
fi

if [[ "$HOT_RELOAD_MODE" != "controlled" && "$HOT_RELOAD_MODE" != "coexist" ]]; then
  echo "--hot-reload-mode must be controlled or coexist" >&2
  exit 1
fi

if [[ "$HOT_RELOAD_SETTLE_MS" -lt 0 ]]; then
  echo "--hot-reload-settle-ms must be 0 or greater" >&2
  exit 1
fi

timestamp() {
  date +"%Y-%m-%dT%H:%M:%S%z"
}

write_section() {
  echo
  echo "== $1 =="
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_AVAILABLE=0
OBS_CMD=""

if command -v obsidian >/dev/null 2>&1; then
  CLI_AVAILABLE=1
  OBS_CMD="$(command -v obsidian)"
elif [[ -n "$OBSIDIAN_COMMAND" ]] && command -v "$OBSIDIAN_COMMAND" >/dev/null 2>&1; then
  CLI_AVAILABLE=1
  OBS_CMD="$OBSIDIAN_COMMAND"
elif [[ -n "$OBSIDIAN_COMMAND" ]]; then
  OBS_CMD="$OBSIDIAN_COMMAND"
elif [[ -x "/Applications/Obsidian.app/Contents/MacOS/Obsidian" ]]; then
  OBS_CMD="/Applications/Obsidian.app/Contents/MacOS/Obsidian"
else
  echo "Unable to locate Obsidian command. Pass --obsidian-command explicitly." >&2
  exit 1
fi

if [[ "$CLI_AVAILABLE" -eq 0 && "$USE_CDP" -eq 0 ]]; then
  echo "Obsidian CLI is unavailable on this machine. Re-run with --use-cdp or install a CLI wrapper." >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"
BUILD_LOG_PATH="$OUTPUT_DIR/build.log"
DEPLOY_REPORT_PATH="$OUTPUT_DIR/deploy-report.json"
CONSOLE_LOG_PATH="$OUTPUT_DIR/console-watch.log"
ERRORS_LOG_PATH="$OUTPUT_DIR/errors.log"
SCREENSHOT_PATH="$OUTPUT_DIR/screenshot.png"
if [[ "$DOM_TEXT" -eq 1 ]]; then
  DOM_PATH="$OUTPUT_DIR/dom.txt"
else
  DOM_PATH="$OUTPUT_DIR/dom.html"
fi
SUMMARY_PATH="$OUTPUT_DIR/summary.json"
DIAGNOSIS_PATH="$OUTPUT_DIR/diagnosis.json"
SCENARIO_REPORT_PATH="$OUTPUT_DIR/scenario-report.json"
COMPARISON_PATH="$OUTPUT_DIR/comparison.json"
BOOTSTRAP_REPORT_PATH="$OUTPUT_DIR/bootstrap-report.json"
CDP_TRACE_PATH="$OUTPUT_DIR/cdp-reload-trace.log"
CDP_SUMMARY_PATH="$CDP_TRACE_PATH.summary.json"
VAULT_LOG_CAPTURE_PATH="$OUTPUT_DIR/vault-log-capture.json"
RESOLVED_VAULT_LOG_CAPTURE_PATH=""
VERSION_PATH="$OUTPUT_DIR/obsidian-version.txt"

obsidian_cli() {
  local quiet=0
  if [[ "${1:-}" == "--quiet" ]]; then
    quiet=1
    shift
  fi

  local command="$1"
  shift || true
  local args=()
  if [[ -n "$VAULT_NAME" ]]; then
    args+=("vault=$VAULT_NAME")
  fi
  args+=("$command")
  while [[ $# -gt 0 ]]; do
    args+=("$1")
    shift
  done

  if [[ "$quiet" -eq 0 ]]; then
    echo "$OBS_CMD ${args[*]}" >&2
  fi
  "$OBS_CMD" "${args[@]}"
}

copy_file_with_hash() {
  local source_file="$1"
  local target_file="$2"
  cp "$source_file" "$target_file"
  local sha
  sha="$(shasum -a 256 "$target_file" | awk '{print $1}')"
  printf '%s' "$sha"
}

append_console_delta() {
  local previous_snapshot_path="$1"
  local current_snapshot_path="$2"
  local output_path="$3"
  local delta_path="$4"

  awk '
    NR == FNR {
      previous[FNR] = $0
      previous_count = FNR
      next
    }
    {
      current[FNR] = $0
      current_count = FNR
    }
    END {
      shared_prefix = 1
      while (shared_prefix <= previous_count && shared_prefix <= current_count && previous[shared_prefix] == current[shared_prefix]) {
        shared_prefix++
      }
      for (line_number = shared_prefix; line_number <= current_count; line_number++) {
        print current[line_number]
      }
    }
  ' "$previous_snapshot_path" "$current_snapshot_path" > "$delta_path"

  while IFS= read -r line; do
    if [[ -z "${line//[[:space:]]/}" ]]; then
      continue
    fi
    printf '%s %s\n' "$(timestamp)" "$line" >> "$output_path"
  done < "$delta_path"

  cp "$current_snapshot_path" "$previous_snapshot_path"
}

append_error_delta() {
  local previous_snapshot_path="$1"
  local current_snapshot_path="$2"
  local output_path="$3"

  local current_snapshot
  local previous_snapshot
  current_snapshot="$(tr -d '\r' < "$current_snapshot_path" | sed '/^[[:space:]]*$/d')"
  previous_snapshot="$(tr -d '\r' < "$previous_snapshot_path" | sed '/^[[:space:]]*$/d')"

  cp "$current_snapshot_path" "$previous_snapshot_path"

  if [[ -z "$current_snapshot" || "$current_snapshot" == "$previous_snapshot" || "$current_snapshot" == "No errors captured." ]]; then
    return
  fi

  {
    echo "$(timestamp)"
    printf '%s\n\n' "$current_snapshot"
  } >> "$output_path"
}

json_path_or_null() {
  local path="$1"

  if [[ -n "$path" && -e "$path" ]]; then
    printf '"%s"' "$path"
  else
    printf 'null'
  fi
}

json_string_or_null() {
  local value="$1"

  if [[ -n "$value" ]]; then
    printf '"%s"' "$value"
  else
    printf 'null'
  fi
}

json_bool() {
  local value="${1:-0}"

  if [[ "$value" -eq 1 ]]; then
    printf 'true'
  else
    printf 'false'
  fi
}

wait_milliseconds() {
  local duration_ms="${1:-0}"

  if [[ "$duration_ms" -le 0 ]]; then
    return
  fi

  sleep "$(awk "BEGIN { print ${duration_ms} / 1000 }")"
}

run_cli_scenario_if_requested() {
  local inferred_scenario_name="$SCENARIO_NAME"
  if [[ -z "$inferred_scenario_name" && -n "$SCENARIO_COMMAND_ID" ]]; then
    inferred_scenario_name="open-plugin-view"
  fi

  if [[ "$CLI_AVAILABLE" -ne 1 ]]; then
    return
  fi

  if [[ -z "$inferred_scenario_name" && -z "$SCENARIO_PATH" ]]; then
    return
  fi

  write_section "Scenario"
  scenario_args=(
    "$SCRIPT_DIR/obsidian_debug_scenario_runner.mjs"
    --obsidian-command "$OBS_CMD"
    --plugin-id "$PLUGIN_ID"
    --vault-name "$VAULT_NAME"
    --scenario-sleep-ms "$SCENARIO_SLEEP_MS"
    --output "$SCENARIO_REPORT_PATH"
  )

  if [[ -n "$inferred_scenario_name" ]]; then
    scenario_args+=(--scenario-name "$inferred_scenario_name")
  fi
  if [[ -n "$SCENARIO_PATH" ]]; then
    scenario_args+=(--scenario-path "$SCENARIO_PATH")
  fi
  if [[ -n "$SCENARIO_COMMAND_ID" ]]; then
    scenario_args+=(--scenario-command-id "$SCENARIO_COMMAND_ID")
  fi
  if [[ -n "$SURFACE_PROFILE_PATH" ]]; then
    scenario_args+=(--surface-profile "$SURFACE_PROFILE_PATH")
  fi
  if [[ -n "$CDP_HOST" ]]; then
    scenario_args+=(--cdp-host "$CDP_HOST")
  fi
  if [[ "$CDP_PORT" -gt 0 ]]; then
    scenario_args+=(--cdp-port "$CDP_PORT")
  fi
  if [[ -n "$CDP_TARGET_TITLE_CONTAINS" ]]; then
    scenario_args+=(--cdp-target-title-contains "$CDP_TARGET_TITLE_CONTAINS")
  fi

  node "${scenario_args[@]}"
}

write_diagnosis() {
  diagnosis_args=(
    "$SCRIPT_DIR/obsidian_debug_analyze.mjs"
    --summary "$SUMMARY_PATH"
    --output "$DIAGNOSIS_PATH"
  )
  if [[ -n "$ASSERTIONS_PATH" ]]; then
    diagnosis_args+=(--assertions "$ASSERTIONS_PATH")
  fi
  if [[ -n "$DOM_SELECTOR" ]]; then
    diagnosis_args+=(--dom-selector "$DOM_SELECTOR")
  fi
  node "${diagnosis_args[@]}"
}

write_logstravaganza_capture() {
  if [[ -z "$TEST_VAULT_PLUGIN_DIR" ]]; then
    return
  fi

  log_capture_args=(
    "$SCRIPT_DIR/obsidian_debug_logstravaganza_capture.mjs"
    --test-vault-plugin-dir "$TEST_VAULT_PLUGIN_DIR"
    --output "$VAULT_LOG_CAPTURE_PATH"
  )

  write_section "Vault Log Capture"
  if node "${log_capture_args[@]}"; then
    if [[ -f "$VAULT_LOG_CAPTURE_PATH" ]]; then
      RESOLVED_VAULT_LOG_CAPTURE_PATH="$VAULT_LOG_CAPTURE_PATH"
    fi
  else
    echo "Logstravaganza capture failed; continuing with CLI/CDP logs only." >&2
  fi
}

write_comparison() {
  if [[ -z "$COMPARE_DIAGNOSIS_PATH" ]]; then
    return
  fi

  comparison_args=(
    "$SCRIPT_DIR/obsidian_debug_compare.mjs"
    --baseline "$COMPARE_DIAGNOSIS_PATH"
    --candidate "$DIAGNOSIS_PATH"
    --output "$COMPARISON_PATH"
  )
  node "${comparison_args[@]}"
}

run_bootstrap_if_needed() {
  if [[ "$SKIP_BOOTSTRAP" -eq 1 || "$CLI_AVAILABLE" -ne 1 ]]; then
    return
  fi

  write_section "Bootstrap Plugin"
  bootstrap_args=(
    "$SCRIPT_DIR/obsidian_debug_bootstrap_plugin.mjs"
    --plugin-id "$PLUGIN_ID"
    --test-vault-plugin-dir "$TEST_VAULT_PLUGIN_DIR"
    --obsidian-command "$OBS_CMD"
    --poll-interval-ms "$BOOTSTRAP_POLL_INTERVAL_MS"
    --discovery-timeout-ms "$BOOTSTRAP_DISCOVERY_TIMEOUT_MS"
    --reload-wait-ms "$BOOTSTRAP_RELOAD_WAIT_MS"
    --restart-wait-ms "$BOOTSTRAP_RESTART_WAIT_MS"
    --enable-wait-ms "$BOOTSTRAP_ENABLE_WAIT_MS"
    --allow-restart "$BOOTSTRAP_ALLOW_RESTART"
    --enable-plugin true
    --output "$BOOTSTRAP_REPORT_PATH"
  )
  if [[ -n "$VAULT_NAME" ]]; then
    bootstrap_args+=(--vault-name "$VAULT_NAME")
  fi

  node "${bootstrap_args[@]}"
}

write_section "Preflight"
if [[ "$CLI_AVAILABLE" -eq 1 ]]; then
  obsidian_cli --quiet version > "$VERSION_PATH" 2>&1 || true
else
  printf 'CLI unavailable; using CDP-only path via %s\n' "$OBS_CMD" > "$VERSION_PATH"
fi

if [[ "$SKIP_BUILD" -eq 0 ]]; then
  write_section "Build"
  echo "$BUILD_COMMAND"
  bash -lc "$BUILD_COMMAND" 2>&1 | tee "$BUILD_LOG_PATH"
fi

if [[ "$SKIP_DEPLOY" -eq 0 ]]; then
  write_section "Deploy"
  if [[ ! -d "$DEPLOY_FROM" ]]; then
    echo "Deploy source does not exist: $DEPLOY_FROM" >&2
    exit 1
  fi

  mkdir -p "$TEST_VAULT_PLUGIN_DIR"
  declare -a report_entries=()
  for file_name in main.js manifest.json styles.css; do
    source_file="$DEPLOY_FROM/$file_name"
    if [[ ! -f "$source_file" ]]; then
      if [[ "$file_name" == "main.js" || "$file_name" == "manifest.json" ]]; then
        echo "Required deploy artifact missing: $source_file" >&2
        exit 1
      fi
      continue
    fi

    target_file="$TEST_VAULT_PLUGIN_DIR/$file_name"
    sha="$(copy_file_with_hash "$source_file" "$target_file")"
    report_entries+=("{\"file\":\"$file_name\",\"source\":\"$source_file\",\"target\":\"$target_file\",\"sha256\":\"$sha\",\"matched\":true}")
  done

  if [[ -d "$DEPLOY_FROM/assets" ]]; then
    rm -rf "$TEST_VAULT_PLUGIN_DIR/assets"
    cp -R "$DEPLOY_FROM/assets" "$TEST_VAULT_PLUGIN_DIR/assets"
    report_entries+=("{\"file\":\"assets/\",\"source\":\"$DEPLOY_FROM/assets\",\"target\":\"$TEST_VAULT_PLUGIN_DIR/assets\",\"sha256\":null,\"matched\":true}")
  fi

  {
    echo "["
    for ((i=0; i<${#report_entries[@]}; i+=1)); do
      printf '  %s' "${report_entries[$i]}"
      if [[ $i -lt $((${#report_entries[@]} - 1)) ]]; then
        printf ','
      fi
      printf '\n'
    done
    echo "]"
  } > "$DEPLOY_REPORT_PATH"
fi

run_bootstrap_if_needed

HOT_RELOAD_PRE_CLEAR_SETTLE_APPLIED=0
HOT_RELOAD_POST_CLEAR_WAIT_APPLIED=0
HOT_RELOAD_EXPLICIT_RELOAD_PERFORMED=0
HOT_RELOAD_RELOAD_CHANNEL="none"

if [[ "$HOT_RELOAD_MODE" == "controlled" && "$SKIP_RELOAD" -eq 0 && "$HOT_RELOAD_SETTLE_MS" -gt 0 ]]; then
  write_section "Hot Reload Settle"
  echo "Waiting ${HOT_RELOAD_SETTLE_MS}ms before clearing buffers for a controlled explicit reload."
  wait_milliseconds "$HOT_RELOAD_SETTLE_MS"
  HOT_RELOAD_PRE_CLEAR_SETTLE_APPLIED=1
fi

write_section "Clear Buffers"
if [[ "$CLI_AVAILABLE" -eq 1 ]]; then
  obsidian_cli dev:debug on >/dev/null 2>&1 || true
  obsidian_cli dev:console clear >/dev/null 2>&1 || true
  obsidian_cli dev:errors clear >/dev/null 2>&1 || true
fi

if [[ "$USE_CDP" -eq 1 && "$SKIP_RELOAD" -eq 0 ]]; then
  write_section "CDP Reload Trace"
  cdp_reload_args=(
    "$SCRIPT_DIR/obsidian_cdp_reload_and_trace.mjs"
    --plugin-id "$PLUGIN_ID"
    --host "$CDP_HOST"
    --port "$CDP_PORT"
    --duration-seconds "$WATCH_SECONDS"
    --reload-delay-ms "$CDP_RELOAD_DELAY_MS"
    --output "$CDP_TRACE_PATH"
    --summary "$CDP_SUMMARY_PATH"
  )
  if [[ -n "$CDP_TARGET_TITLE_CONTAINS" ]]; then
    cdp_reload_args+=(--target-title-contains "$CDP_TARGET_TITLE_CONTAINS")
  fi
  if [[ -n "$CDP_EVAL_AFTER_RELOAD" ]]; then
    cdp_reload_args+=(--eval-after-reload "$CDP_EVAL_AFTER_RELOAD")
  fi
  if [[ "$HOT_RELOAD_MODE" == "coexist" ]]; then
    cdp_reload_args+=(--skip-reload)
    HOT_RELOAD_RELOAD_CHANNEL="cdp-observe"
  else
    HOT_RELOAD_EXPLICIT_RELOAD_PERFORMED=1
    HOT_RELOAD_RELOAD_CHANNEL="cdp"
  fi
  node "${cdp_reload_args[@]}"
elif [[ "$SKIP_RELOAD" -eq 0 ]]; then
  if [[ "$HOT_RELOAD_MODE" == "coexist" ]]; then
    write_section "Hot Reload Coexist"
    echo "Skipping explicit plugin reload and relying on background Hot Reload-friendly capture."
    HOT_RELOAD_RELOAD_CHANNEL="coexist-skip"
  else
    write_section "Reload Plugin"
    obsidian_cli plugin:reload "id=$PLUGIN_ID" >/dev/null
    HOT_RELOAD_EXPLICIT_RELOAD_PERFORMED=1
    HOT_RELOAD_RELOAD_CHANNEL="cli"
  fi
fi

if [[ "$HOT_RELOAD_MODE" == "coexist" && "$SKIP_RELOAD" -eq 0 && "$HOT_RELOAD_SETTLE_MS" -gt 0 ]]; then
  write_section "Hot Reload Coexist"
  echo "Waiting ${HOT_RELOAD_SETTLE_MS}ms for background Hot Reload activity before running scenarios."
  wait_milliseconds "$HOT_RELOAD_SETTLE_MS"
  HOT_RELOAD_POST_CLEAR_WAIT_APPLIED=1
fi

run_cli_scenario_if_requested

if [[ "$USE_CDP" -eq 0 ]]; then
  write_section "Watch Console"
  : > "$CONSOLE_LOG_PATH"
  : > "$ERRORS_LOG_PATH"
  console_previous_snapshot_path="$OUTPUT_DIR/.console-previous.log"
  console_current_snapshot_path="$OUTPUT_DIR/.console-current.log"
  console_delta_snapshot_path="$OUTPUT_DIR/.console-delta.log"
  errors_previous_snapshot_path="$OUTPUT_DIR/.errors-previous.log"
  errors_current_snapshot_path="$OUTPUT_DIR/.errors-current.log"
  : > "$console_previous_snapshot_path"
  : > "$errors_previous_snapshot_path"
  end_epoch=$(( $(date +%s) + WATCH_SECONDS ))
  while [[ $(date +%s) -lt $end_epoch ]]; do
    obsidian_cli --quiet dev:console "limit=$CONSOLE_LIMIT" > "$console_current_snapshot_path" 2>&1 || true
    append_console_delta "$console_previous_snapshot_path" "$console_current_snapshot_path" "$CONSOLE_LOG_PATH" "$console_delta_snapshot_path"

    obsidian_cli --quiet dev:errors > "$errors_current_snapshot_path" 2>&1 || true
    append_error_delta "$errors_previous_snapshot_path" "$errors_current_snapshot_path" "$ERRORS_LOG_PATH"
    sleep "$(awk "BEGIN { print ${POLL_INTERVAL_MS} / 1000 }")"
  done
  rm -f "$console_previous_snapshot_path" "$console_current_snapshot_path" "$console_delta_snapshot_path" "$errors_previous_snapshot_path" "$errors_current_snapshot_path"
  if [[ ! -s "$ERRORS_LOG_PATH" ]]; then
    printf '%s No errors captured during watch window.\n' "$(timestamp)" > "$ERRORS_LOG_PATH"
  fi
else
  if [[ "$CLI_AVAILABLE" -eq 1 ]]; then
    obsidian_cli --quiet dev:errors > "$ERRORS_LOG_PATH" 2>&1 || true
  else
    printf 'No separate CLI errors log in CDP-only mode. Inspect %s\n' "$CDP_TRACE_PATH" > "$ERRORS_LOG_PATH"
  fi
fi

if [[ "$SKIP_SCREENSHOT" -eq 0 ]]; then
  write_section "Screenshot"
  if [[ "$CLI_AVAILABLE" -eq 1 ]]; then
    obsidian_cli --quiet dev:screenshot "path=$SCREENSHOT_PATH" > "$OUTPUT_DIR/screenshot-command.txt" 2>&1 || true
  elif [[ "$USE_CDP" -eq 1 ]]; then
    cdp_capture_args=(
      "$SCRIPT_DIR/obsidian_cdp_capture_ui.mjs"
      --host "$CDP_HOST"
      --port "$CDP_PORT"
      --selector "$DOM_SELECTOR"
      --screenshot-output "$SCREENSHOT_PATH"
      --summary "$OUTPUT_DIR/cdp-capture-ui.summary.json"
    )
    if [[ -n "$CDP_TARGET_TITLE_CONTAINS" ]]; then
      cdp_capture_args+=(--target-title-contains "$CDP_TARGET_TITLE_CONTAINS")
    fi
    node "${cdp_capture_args[@]}"
  fi
fi

if [[ "$SKIP_DOM" -eq 0 ]]; then
  write_section "DOM"
  if [[ "$CLI_AVAILABLE" -eq 1 ]]; then
    dom_args=("selector=$DOM_SELECTOR" "all")
    if [[ "$DOM_TEXT" -eq 1 ]]; then
      dom_args+=("text")
    fi
    obsidian_cli --quiet dev:dom "${dom_args[@]}" > "$DOM_PATH" 2>&1 || true
  elif [[ "$USE_CDP" -eq 1 ]]; then
    if [[ "$DOM_TEXT" -eq 1 ]]; then
      cdp_dom_args=(
        "$SCRIPT_DIR/obsidian_cdp_capture_ui.mjs"
        --host "$CDP_HOST"
        --port "$CDP_PORT"
        --selector "$DOM_SELECTOR"
        --text-output "$DOM_PATH"
        --summary "$OUTPUT_DIR/cdp-capture-ui.summary.json"
      )
    else
      cdp_dom_args=(
        "$SCRIPT_DIR/obsidian_cdp_capture_ui.mjs"
        --host "$CDP_HOST"
        --port "$CDP_PORT"
        --selector "$DOM_SELECTOR"
        --html-output "$DOM_PATH"
        --summary "$OUTPUT_DIR/cdp-capture-ui.summary.json"
      )
    fi
    if [[ -n "$CDP_TARGET_TITLE_CONTAINS" ]]; then
      cdp_dom_args+=(--target-title-contains "$CDP_TARGET_TITLE_CONTAINS")
    fi
    node "${cdp_dom_args[@]}"
  fi
fi

write_logstravaganza_capture

TRACE_CAPTURE_MODE="console-watch"
TRACE_CAPTURE_REQUESTED=1
TRACE_CAPTURE_SKIPPED=0
TRACE_CAPTURE_SKIP_REASON=""
if [[ "$USE_CDP" -eq 1 ]]; then
  TRACE_CAPTURE_MODE="cdp-trace"
  if [[ "$SKIP_RELOAD" -eq 1 ]]; then
    TRACE_CAPTURE_REQUESTED=0
    TRACE_CAPTURE_SKIPPED=1
    TRACE_CAPTURE_SKIP_REASON="reload-skipped"
  fi
elif [[ "$WATCH_SECONDS" -le 0 ]]; then
  TRACE_CAPTURE_REQUESTED=0
  TRACE_CAPTURE_SKIPPED=1
  TRACE_CAPTURE_SKIP_REASON="watch-window-disabled"
fi

HOT_RELOAD_MAY_INFLUENCE=0
HOT_RELOAD_TIMINGS_TRUST="deterministic"
HOT_RELOAD_DETAIL="Controlled mode issued an explicit reload without a Hot Reload settle delay."
if [[ "$SKIP_RELOAD" -eq 1 ]]; then
  HOT_RELOAD_TIMINGS_TRUST="reload-skipped"
  HOT_RELOAD_DETAIL="Reload was skipped, so startup timings do not reflect a coordinated reload."
elif [[ "$HOT_RELOAD_MODE" == "coexist" ]]; then
  HOT_RELOAD_MAY_INFLUENCE=1
  HOT_RELOAD_TIMINGS_TRUST="hot-reload-influenced"
  HOT_RELOAD_DETAIL="Coexist mode avoided an explicit reload, so captured timings and logs may reflect background Hot Reload activity."
elif [[ "$HOT_RELOAD_PRE_CLEAR_SETTLE_APPLIED" -eq 1 ]]; then
  HOT_RELOAD_DETAIL="Controlled mode waited ${HOT_RELOAD_SETTLE_MS}ms before clearing buffers and issuing an explicit reload."
fi

cat > "$SUMMARY_PATH" <<EOF
{
  "timestamp": "$(timestamp)",
  "repoDir": "$(pwd -P)",
  "pluginId": "$PLUGIN_ID",
  "vaultName": "$VAULT_NAME",
  "obsidianCommand": "$OBS_CMD",
  "testVaultPluginDir": "$TEST_VAULT_PLUGIN_DIR",
  "outputDir": "$OUTPUT_DIR",
  "buildLog": $( [[ "$SKIP_BUILD" -eq 0 ]] && json_path_or_null "$BUILD_LOG_PATH" || printf 'null' ),
  "deployReport": $( [[ "$SKIP_DEPLOY" -eq 0 ]] && json_path_or_null "$DEPLOY_REPORT_PATH" || printf 'null' ),
  "bootstrapReport": $( [[ "$SKIP_BOOTSTRAP" -eq 0 ]] && json_path_or_null "$BOOTSTRAP_REPORT_PATH" || printf 'null' ),
  "scenarioReport": $( json_path_or_null "$SCENARIO_REPORT_PATH" ),
  "assertionsPath": $( [[ -n "$ASSERTIONS_PATH" ]] && printf '"%s"' "$ASSERTIONS_PATH" || printf 'null' ),
  "comparisonReport": $( [[ -n "$COMPARE_DIAGNOSIS_PATH" ]] && printf '"%s"' "$COMPARISON_PATH" || printf 'null' ),
  "consoleLog": $( [[ "$USE_CDP" -eq 1 ]] && printf 'null' || json_path_or_null "$CONSOLE_LOG_PATH" ),
  "errorsLog": $( json_path_or_null "$ERRORS_LOG_PATH" ),
  "useCdp": $( [[ "$USE_CDP" -eq 1 ]] && printf 'true' || printf 'false' ),
  "cdpTrace": $( [[ "$USE_CDP" -eq 1 && "$SKIP_RELOAD" -eq 0 ]] && json_path_or_null "$CDP_TRACE_PATH" || printf 'null' ),
  "cdpSummary": $( [[ "$USE_CDP" -eq 1 && "$SKIP_RELOAD" -eq 0 ]] && json_path_or_null "$CDP_SUMMARY_PATH" || printf 'null' ),
  "vaultLogCapture": $( json_path_or_null "$RESOLVED_VAULT_LOG_CAPTURE_PATH" ),
  "screenshot": $( [[ "$SKIP_SCREENSHOT" -eq 1 ]] && printf 'null' || json_path_or_null "$SCREENSHOT_PATH" ),
  "dom": $( [[ "$SKIP_DOM" -eq 1 ]] && printf 'null' || json_path_or_null "$DOM_PATH" ),
  "watchSeconds": $WATCH_SECONDS,
  "consoleLimit": $CONSOLE_LIMIT,
  "hotReload": {
    "mode": "$HOT_RELOAD_MODE",
    "settleMs": $HOT_RELOAD_SETTLE_MS,
    "preClearSettleApplied": $( json_bool "$HOT_RELOAD_PRE_CLEAR_SETTLE_APPLIED" ),
    "postClearWaitApplied": $( json_bool "$HOT_RELOAD_POST_CLEAR_WAIT_APPLIED" ),
    "explicitReloadRequested": $( [[ "$SKIP_RELOAD" -eq 0 && "$HOT_RELOAD_MODE" != "coexist" ]] && printf 'true' || printf 'false' ),
    "explicitReloadPerformed": $( json_bool "$HOT_RELOAD_EXPLICIT_RELOAD_PERFORMED" ),
    "reloadChannel": $( json_string_or_null "$HOT_RELOAD_RELOAD_CHANNEL" ),
    "mayInfluenceTimings": $( json_bool "$HOT_RELOAD_MAY_INFLUENCE" ),
    "timingsTrust": $( json_string_or_null "$HOT_RELOAD_TIMINGS_TRUST" ),
    "detail": $( json_string_or_null "$HOT_RELOAD_DETAIL" )
  },
  "capturePlan": {
    "trace": {
      "mode": "$TRACE_CAPTURE_MODE",
      "requested": $( json_bool "$TRACE_CAPTURE_REQUESTED" ),
      "intentionallySkipped": $( json_bool "$TRACE_CAPTURE_SKIPPED" ),
      "skipReason": $( json_string_or_null "$TRACE_CAPTURE_SKIP_REASON" )
    },
    "screenshot": {
      "requested": $( [[ "$SKIP_SCREENSHOT" -eq 1 ]] && printf 'false' || printf 'true' ),
      "intentionallySkipped": $( [[ "$SKIP_SCREENSHOT" -eq 1 ]] && printf 'true' || printf 'false' ),
      "skipReason": $( [[ "$SKIP_SCREENSHOT" -eq 1 ]] && json_string_or_null "skip-screenshot-flag" || printf 'null' )
    },
    "dom": {
      "requested": $( [[ "$SKIP_DOM" -eq 1 ]] && printf 'false' || printf 'true' ),
      "intentionallySkipped": $( [[ "$SKIP_DOM" -eq 1 ]] && printf 'true' || printf 'false' ),
      "skipReason": $( [[ "$SKIP_DOM" -eq 1 ]] && json_string_or_null "skip-dom-flag" || printf 'null' )
    },
    "vaultLogs": {
      "mode": "logstravaganza-ndjson",
      "requested": $( [[ -n "$TEST_VAULT_PLUGIN_DIR" ]] && printf 'true' || printf 'false' ),
      "intentionallySkipped": false,
      "skipReason": null
    }
  }
}
EOF

write_section "Diagnosis"
write_diagnosis

if [[ -n "$COMPARE_DIAGNOSIS_PATH" ]]; then
  write_section "Comparison"
  write_comparison
fi

write_section "Done"
echo "Summary: $SUMMARY_PATH"
