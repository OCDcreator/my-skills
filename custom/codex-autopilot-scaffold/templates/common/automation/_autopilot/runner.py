from __future__ import annotations

import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Callable, cast


@dataclass(frozen=True)
class RunnerSupport:
    repo_root: Path
    error_type: type[Exception]
    clean_string: Callable[..., str]
    compact_text: Callable[..., str]
    progress: Callable[..., None]
    get_codex_event_summary: Callable[..., str | None]
    now_timestamp: Callable[..., str]
    write_json: Callable[..., None]
    windows_hidden_process_kwargs: Callable[..., dict[str, Any]]


def resolve_runner_executable(
    config: dict[str, Any],
    *,
    clean_string: Callable[..., str],
    error_type: type[Exception],
) -> str:
    runner_kind = clean_string(config.get("runner_kind")).lower() or "codex"
    if runner_kind != "codex":
        raise error_type(
            f"runner_kind='{runner_kind}' is not implemented by this scaffold yet. "
            "Use runner_kind='codex' or replace the runner seam deliberately."
        )

    configured_runner = clean_string(config.get("runner_command"))
    if configured_runner:
        resolved = shutil.which(configured_runner)
        if resolved:
            return resolved
        runner_path = Path(configured_runner)
        if runner_path.exists():
            return str(runner_path)
        raise error_type(f"Configured runner_command was not found: {configured_runner}")

    return shutil.which("codex.cmd") or shutil.which("codex") or "codex"


def invoke_runner_round(
    *,
    prompt_path: Path,
    schema_path: Path,
    assistant_output_path: Path,
    events_log_path: Path,
    progress_log_path: Path,
    config: dict[str, Any],
    support: RunnerSupport,
) -> int:
    prompt_text = prompt_path.read_bytes()
    runner_kind = support.clean_string(config.get("runner_kind")).lower() or "codex"
    if runner_kind != "codex":
        raise support.error_type(f"runner_kind='{runner_kind}' is not supported by this runner.")

    codex_executable = resolve_runner_executable(
        config,
        clean_string=support.clean_string,
        error_type=support.error_type,
    )
    codex_args = [
        codex_executable,
        "exec",
        "-C",
        str(support.repo_root),
        "--dangerously-bypass-approvals-and-sandbox",
        "--json",
        "--color",
        "never",
        "--output-schema",
        str(schema_path),
        "-o",
        str(assistant_output_path),
    ]

    model_name = support.clean_string(config.get("runner_model"))
    if model_name:
        codex_args.extend(["-m", model_name])

    for additional_directory in config.get("runner_additional_dirs", []):
        directory_text = support.clean_string(additional_directory)
        if directory_text:
            codex_args.extend(["--add-dir", directory_text])

    for extra_arg in config.get("runner_extra_args", []):
        extra_arg_text = support.clean_string(extra_arg)
        if extra_arg_text:
            codex_args.append(extra_arg_text)

    codex_args.append("-")

    stderr_log_path = events_log_path.with_suffix(".stderr.log")
    runner_status_path = events_log_path.with_name("runner-status.json")
    for log_path in (events_log_path, progress_log_path, stderr_log_path):
        if log_path.exists():
            log_path.unlink()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("", encoding="utf-8")

    runner_status: dict[str, Any] = {
        "runner_kind": runner_kind,
        "command": codex_args[:-1],
        "status": "launching",
        "pid": None,
        "started_at": None,
        "exec_confirmed_at": None,
        "last_output_at": None,
        "last_stdout_at": None,
        "last_stderr_at": None,
        "stdout_event_count": 0,
        "stderr_event_count": 0,
        "exit_code": None,
        "finished_at": None,
    }
    runner_status_lock = threading.Lock()

    def save_runner_status() -> None:
        with runner_status_lock:
            support.write_json(runner_status_path, dict(runner_status))

    def update_runner_status(**fields: Any) -> None:
        with runner_status_lock:
            runner_status.update(fields)
            support.write_json(runner_status_path, dict(runner_status))

    process = subprocess.Popen(
        codex_args,
        cwd=str(support.repo_root),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        **support.windows_hidden_process_kwargs(),
    )

    if not process.stdin or not process.stdout or not process.stderr:
        raise support.error_type("Failed to start codex subprocess with redirected pipes.")
    update_runner_status(
        status="spawned",
        pid=int(process.pid),
        started_at=support.now_timestamp(),
    )
    support.progress(progress_log_path, f"Spawned codex exec subprocess pid={process.pid}", channel="runner")

    stdin_pipe = cast(BinaryIO, process.stdin)
    stdout_pipe = cast(BinaryIO, process.stdout)
    stderr_pipe = cast(BinaryIO, process.stderr)

    def stdout_worker() -> None:
        with events_log_path.open("a", encoding="utf-8", newline="\n") as events_handle:
            while True:
                stdout_line = stdout_pipe.readline()
                if not stdout_line:
                    break
                decoded_line = stdout_line.decode("utf-8", errors="replace").rstrip("\r\n")
                events_handle.write(decoded_line + "\n")
                events_handle.flush()
                current_timestamp = support.now_timestamp()
                next_fields: dict[str, Any] = {
                    "stdout_event_count": int(runner_status.get("stdout_event_count") or 0) + 1,
                    "last_stdout_at": current_timestamp,
                    "last_output_at": current_timestamp,
                }
                if not runner_status.get("exec_confirmed_at"):
                    next_fields["exec_confirmed_at"] = current_timestamp
                    next_fields["status"] = "running"
                    support.progress(progress_log_path, "codex exec emitted first execution event", channel="runner")
                update_runner_status(**next_fields)
                summary = support.get_codex_event_summary(decoded_line)
                if summary:
                    support.progress(progress_log_path, summary)

    def stderr_worker() -> None:
        with stderr_log_path.open("a", encoding="utf-8", newline="\n") as stderr_handle:
            while True:
                stderr_line = stderr_pipe.readline()
                if not stderr_line:
                    break
                decoded_line = stderr_line.decode("utf-8", errors="replace").rstrip("\r\n")
                stderr_handle.write(decoded_line + "\n")
                stderr_handle.flush()
                current_timestamp = support.now_timestamp()
                next_fields = {
                    "stderr_event_count": int(runner_status.get("stderr_event_count") or 0) + 1,
                    "last_stderr_at": current_timestamp,
                    "last_output_at": current_timestamp,
                    "status": "spawned" if runner_status.get("status") == "launching" else runner_status.get("status"),
                }
                update_runner_status(**next_fields)
                if decoded_line.strip():
                    support.progress(
                        progress_log_path,
                        support.compact_text(decoded_line, max_length=220),
                        channel="stderr",
                    )

    stdout_thread = threading.Thread(target=stdout_worker, daemon=True)
    stderr_thread = threading.Thread(target=stderr_worker, daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    stdin_pipe.write(prompt_text)
    stdin_pipe.flush()
    stdin_pipe.close()

    return_code = process.wait()
    stdout_thread.join()
    stderr_thread.join()
    update_runner_status(
        exit_code=int(return_code),
        finished_at=support.now_timestamp(),
        status="exited",
    )
    return return_code
