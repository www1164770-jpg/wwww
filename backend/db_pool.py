"""
MySQL 连接池模块 (基于 DBUtils.PooledDB)
=========================================
替代原先每次请求都 connect()/close() 的原始模式，
通过连接池复用数据库连接，避免高并发下的 "Too many connections" 崩溃。

使用方式：
    from db_pool import get_connection
    conn = get_connection()
    # ... 使用 conn ...
    conn.close()  # 并非真正关闭，而是归还到连接池

配置从 backend/.env 环境变量读取。主机和端口有本地默认值，
数据库用户和数据库名必须显式配置。
"""

import logging
import os
import threading
import time
from pathlib import Path
from dotenv import load_dotenv
from dbutils.pooled_db import PooledDB
import pymysql

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

MYSQL_CHARSET = 'utf8mb4'
TRANSIENT_MYSQL_ERROR_CODES = frozenset({2003, 2006, 2013})
DATABASE_RETRY_DELAYS = (0.0, 0.5, 1.0)

logger = logging.getLogger(__name__)


def _bounded_timeout(name, default, minimum=1, maximum=30):
    """Read a MySQL timeout without allowing an accidental long stall."""
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{name} must be an integer between {minimum} and {maximum}") from exc
    if not minimum <= value <= maximum:
        raise RuntimeError(f"{name} must be an integer between {minimum} and {maximum}")
    return value


MYSQL_CONNECT_TIMEOUT = _bounded_timeout("MYSQL_CONNECT_TIMEOUT", 4)
MYSQL_READ_TIMEOUT = _bounded_timeout("MYSQL_READ_TIMEOUT", 5)
MYSQL_WRITE_TIMEOUT = _bounded_timeout("MYSQL_WRITE_TIMEOUT", 5)


def _first_nonempty_environment_value(*names, default=None):
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip():
            return value.strip()
    return default


def _database_password():
    for name in ("MYSQL_PASSWORD", "DB_PASSWORD"):
        if name in os.environ:
            return os.environ[name]
    return ""


def _database_port():
    raw_value = _first_nonempty_environment_value(
        "MYSQL_PORT", "DB_PORT", default="3306"
    )
    try:
        port = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "MYSQL_PORT or DB_PORT must be an integer between 1 and 65535"
        ) from exc
    if not 1 <= port <= 65535:
        raise RuntimeError(
            "MYSQL_PORT or DB_PORT must be an integer between 1 and 65535"
        )
    return port


def get_database_config():
    """Return database settings without opening a connection."""
    return {
        "host": _first_nonempty_environment_value(
            "MYSQL_HOST", "DB_HOST", default="127.0.0.1"
        ),
        "port": _database_port(),
        "user": _first_nonempty_environment_value("MYSQL_USER", "DB_USER"),
        "password": _database_password(),
        "database": _first_nonempty_environment_value(
            "MYSQL_DATABASE", "DB_NAME"
        ),
        "charset": MYSQL_CHARSET,
        "use_unicode": True,
    }


def validate_database_config(config=None):
    """Fail before connecting when identity or database settings are missing."""
    config = config or get_database_config()
    missing = []
    if not config.get("user"):
        missing.append("MYSQL_USER (or DB_USER)")
    if not config.get("database"):
        missing.append("MYSQL_DATABASE (or DB_NAME)")
    if missing:
        raise RuntimeError(
            "Missing database configuration in backend/.env: set "
            + ", ".join(missing)
        )
    return config


DATABASE_CONFIG = get_database_config()

# 连接池配置
POOL_CONFIG = {
    'creator': pymysql,  # 使用 pymysql 作为数据库驱动
    'maxconnections': 5,       # 保守限制连接总数，避免本地 MySQL 资源峰值
    'mincached': 0,            # 保持懒初始化，导入模块时不预建连接
    'maxcached': 5,            # 空闲连接不超过连接总上限
    'maxshared': 0,            # PyMySQL 不共享连接，显式关闭共享池
    'blocking': True,           # 连接池短暂占满时等待连接归还
    # Recycle periodically as an extra stale-socket guard; ping validates each
    # checkout below.
    'maxusage': 1000,
    'setsession': None,        # 连接创建后可执行的初始化 SQL 命令列表
    'ping': 1,                 # 取连接时检查服务端，避免复用失效连接
    'connect_timeout': MYSQL_CONNECT_TIMEOUT,
    'read_timeout': MYSQL_READ_TIMEOUT,
    'write_timeout': MYSQL_WRITE_TIMEOUT,
    **DATABASE_CONFIG,
    'cursorclass': pymysql.cursors.DictCursor,  # 返回字典格式的查询结果
    'autocommit': False,       # 关闭自动提交，由业务代码手动 commit
}

# 全局连接池实例（单例）
_pool = None
_pool_lock = threading.Lock()

def get_pool():
    """获取或创建连接池实例（懒初始化单例）"""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                validate_database_config(POOL_CONFIG)
                _pool = PooledDB(**POOL_CONFIG)
    return _pool


def mysql_error_code(error):
    """Extract a PyMySQL error number without exposing connection details."""
    seen = set()
    current = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        args = getattr(current, "args", ())
        if args and isinstance(args[0], int):
            return args[0]
        current = getattr(current, "__cause__", None) or getattr(
            current, "__context__", None
        )
    return None


def is_transient_mysql_error(error):
    """Only connection-loss errors are safe to retry automatically."""
    return mysql_error_code(error) in TRANSIENT_MYSQL_ERROR_CODES


def _discard_connection(conn):
    if conn is None:
        return
    try:
        conn.close()
    except Exception:
        pass

def get_connection(max_retries=3):
    """
    从连接池获取一个数据库连接。

    用法：
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT ...")
            conn.commit()
        finally:
            conn.close()  # 归还到连接池，并非真正关闭

    注意：调用 conn.close() 会将连接归还到池中供复用，
    不会真的断开与 MySQL 的连接。
    """
    if not isinstance(max_retries, int) or not 0 <= max_retries <= 3:
        raise ValueError("max_retries must be an integer between 0 and 3")

    conn = None
    for attempt in range(max_retries + 1):
        try:
            conn = get_pool().connection()
            # DBUtils validates ordinary checkouts via ping=1. Reconnecting here
            # also recovers a socket dropped while idle after a MySQL restart.
            conn.ping(reconnect=True)
            return conn
        except Exception as error:
            _discard_connection(conn)
            conn = None
            if not is_transient_mysql_error(error) or attempt >= max_retries:
                raise
            delay = DATABASE_RETRY_DELAYS[attempt]
            logger.warning(
                "Transient MySQL checkout failure; retrying attempt=%s error_code=%s",
                attempt + 1,
                mysql_error_code(error),
            )
            if delay:
                time.sleep(delay)

    raise RuntimeError("unreachable database retry state")
