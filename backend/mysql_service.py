"""Windows MySQL service startup and readiness checks for local development."""

from __future__ import annotations

import os
import re
import socket
import subprocess
import time
from typing import Callable

from db_pool import (
    get_connection,
    get_database_config,
    is_transient_mysql_error,
    mysql_error_code,
    validate_database_config,
)


MYSQL_SERVICE_NAME = "MySQL97"
DEFAULT_READY_TIMEOUT = 30.0
POLL_INTERVAL = 0.5
_RUNNING_STATE = re.compile(r"STATE\s*:\s*4\b", re.IGNORECASE)
_ACCESS_DENIED_MARKERS = (
    "access is denied",
    "拒绝访问",
    "failed 5",
    "error 5",
    "system error 5",
    "系统错误 5",
)
_ALREADY_RUNNING_MARKERS = (
    "already running",
    "instance of the service is already running",
    "服务的实例已在运行",
    "服务已经启动",
    "1056",
)


class MySQLStartupError(RuntimeError):
    """Raised when Flask must not start because MySQL is unavailable."""


class MySQLServicePermissionError(MySQLStartupError):
    """Raised when Windows refuses permission to start MySQL97."""


def _run_sc(*arguments: str) -> subprocess.CompletedProcess:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(
        ["sc.exe", *arguments],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=10,
        creationflags=creationflags,
        check=False,
    )


def _command_output(result: subprocess.CompletedProcess) -> str:
    return f"{result.stdout or ''}\n{result.stderr or ''}".strip()


def _service_is_running(result: subprocess.CompletedProcess) -> bool:
    return result.returncode == 0 and bool(_RUNNING_STATE.search(_command_output(result)))


def _contains_marker(output: str, markers: tuple[str, ...]) -> bool:
    normalized = output.casefold()
    return any(marker.casefold() in normalized for marker in markers)


def ensure_mysql_service(deadline: float) -> None:
    """Start MySQL97 when necessary and wait until Windows reports RUNNING."""
    print(f"[数据库] 检查 {MYSQL_SERVICE_NAME}...", flush=True)
    try:
        query = _run_sc("query", MYSQL_SERVICE_NAME)
    except (OSError, subprocess.SubprocessError) as error:
        raise MySQLStartupError("无法检查 MySQL97 Windows 服务。") from error

    if _service_is_running(query):
        print(f"[数据库] {MYSQL_SERVICE_NAME} 已运行", flush=True)
        return

    print(f"[数据库] {MYSQL_SERVICE_NAME} 未运行，正在启动...", flush=True)
    try:
        started = _run_sc("start", MYSQL_SERVICE_NAME)
    except (OSError, subprocess.SubprocessError) as error:
        raise MySQLStartupError("无法启动 MySQL97 Windows 服务。") from error

    output = _command_output(started)
    if _contains_marker(output, _ACCESS_DENIED_MARKERS):
        raise MySQLServicePermissionError(
            "MySQL97 当前未运行，并且当前终端没有启动 Windows 服务的权限。\n"
            "请以管理员身份启动后端，或将 MySQL97 设置为自动启动。"
        )
    if started.returncode != 0 and not _contains_marker(output, _ALREADY_RUNNING_MARKERS):
        raise MySQLStartupError(
            f"MySQL97 启动命令失败（退出代码 {started.returncode}）。"
        )

    while time.monotonic() < deadline:
        query = _run_sc("query", MYSQL_SERVICE_NAME)
        if _service_is_running(query):
            print(f"[数据库] {MYSQL_SERVICE_NAME} 已启动", flush=True)
            return
        time.sleep(POLL_INTERVAL)
    raise MySQLStartupError("等待 MySQL97 进入 RUNNING 状态超时。")


def wait_for_mysql_port(host: str, port: int, deadline: float) -> None:
    print(f"[数据库] 等待 {host}:{port}...", flush=True)
    last_error = None
    while time.monotonic() < deadline:
        try:
            remaining = max(0.1, min(POLL_INTERVAL, deadline - time.monotonic()))
            with socket.create_connection((host, port), timeout=remaining):
                print("[数据库] MySQL 端口已就绪", flush=True)
                return
        except OSError as error:
            last_error = error
            time.sleep(min(POLL_INTERVAL, max(0.0, deadline - time.monotonic())))
    raise MySQLStartupError(f"等待 {host}:{port} TCP 端口超时。") from last_error


def wait_for_database_connection(
    deadline: float,
    connection_factory: Callable = get_connection,
) -> None:
    print("[数据库] 正在验证数据库连接...", flush=True)
    last_error = None
    while time.monotonic() < deadline:
        connection = None
        try:
            connection = connection_factory()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            print("[数据库] 数据库连接正常", flush=True)
            return
        except Exception as error:
            last_error = error
            # Authentication, unknown-database, SQL, and configuration errors
            # cannot recover by waiting and must fail fast.
            if not is_transient_mysql_error(error):
                code = mysql_error_code(error)
                suffix = f"（MySQL 错误 {code}）" if code is not None else ""
                raise MySQLStartupError(f"数据库连接验证失败{suffix}。") from error
            time.sleep(min(POLL_INTERVAL, max(0.0, deadline - time.monotonic())))
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
    code = mysql_error_code(last_error) if last_error is not None else None
    suffix = f"（最后的 MySQL 错误 {code}）" if code is not None else ""
    raise MySQLStartupError(f"等待数据库连接超时{suffix}。") from last_error


def ensure_mysql_ready(timeout: float = DEFAULT_READY_TIMEOUT) -> None:
    """Block startup until the service, TCP port, and SELECT 1 are ready."""
    config = validate_database_config(get_database_config())
    deadline = time.monotonic() + timeout
    host = config["host"]
    port = config["port"]

    if os.name == "nt" and host.casefold() in {"127.0.0.1", "localhost", "::1"}:
        ensure_mysql_service(deadline)
    wait_for_mysql_port(host, port, deadline)
    wait_for_database_connection(deadline)


def print_startup_failure(error: Exception) -> None:
    """Print a safe, actionable startup error without database secrets."""
    print("[数据库启动失败]", file=os.sys.stderr, flush=True)
    print(str(error), file=os.sys.stderr, flush=True)
