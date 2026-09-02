"""
智汇导航后端主应用模块
========================
本文件是整个后端服务的核心入口，基于 Flask 框架构建。

主要功能模块：
  1. 用户认证与授权（JWT 双 Token 机制 + GitHub OAuth 登录）
  2. 网站导航数据管理（分类、网站的增删改查 RESTful API）
  3. 全文搜索引擎集成（Meilisearch 极速搜索）
  4. 实时热度排行榜（多源热榜数据聚合）
  5. 爬虫与内容审核工作台（Hacker News 自动抓取 + 人工审核流程）
  6. 用户收藏夹管理
  7. 行业资讯 RSS 聚合
  8. 定时任务调度（APScheduler）
  9. 用户个性化配置云同步

运行方式：
  python app.py
  服务默认监听 http://0.0.0.0:5000
"""

import os  # 操作系统接口，用于读取环境变量和文件路径
import sys
from pathlib import Path
from dotenv import load_dotenv  # 从 .env 文件加载环境变量，保护敏感配置不硬编码

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(BACKEND_DIR.parent) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR.parent))

for env_path in (BACKEND_DIR / ".env", PROJECT_DIR / ".env"):
    if env_path.exists():
        load_dotenv(env_path, override=False)

from mysql_service import MySQLStartupError, ensure_mysql_ready, print_startup_failure

# A direct development-server launch must prove database readiness before
# importing and initializing the Flask application. This also runs in the
# Werkzeug child, where it is idempotent because RUNNING services are not
# started again. WSGI imports and utility subcommands remain side-effect free.
if __name__ == "__main__" and not (
    len(sys.argv) > 1 and sys.argv[1] == "smtp-check"
):
    try:
        ensure_mysql_ready()
    except (MySQLStartupError, RuntimeError) as error:
        print_startup_failure(error)
        raise SystemExit(1)

from background_config import (
    BACKGROUND_MAX_FILE_BYTES,
    BACKGROUND_MAX_REQUEST_BYTES,
    BACKGROUND_UPLOAD_ROOT,
)
from flask import Flask, jsonify, request, redirect, url_for, g  # Flask 核心：应用实例、JSON响应、请求对象、重定向
from flask_cors import CORS  # 跨域资源共享扩展，允许前端跨域调用后端接口
import requests  # HTTP 客户端库，用于调用第三方 API 和爬取外部数据
import time  # 时间工具，用于时间戳记录和延迟控制
from models import db, User, UserProfile, Category, Tag, Website, SiteTag, SiteOccupation, Favorite, Comment, UserBehavior, UserBehaviorEvent, RecommendationObservationSnapshot, RecommendationLog, ClickLog  # 导入 SQLAlchemy 数据库实例及所有数据模型
import questionnaire_models  # noqa: F401  Register foundation models on the shared metadata.
from sqlalchemy import func  # SQLAlchemy 聚合函数（如 COUNT、SUM），用于统计查询
import json  # JSON 序列化/反序列化，用于存储复杂配置字段
import re  # 正则表达式，用于 URL 格式校验等文本处理
from urllib.parse import quote_plus, urlparse  # URL 解析工具，用于验证 URL 合法性
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt, get_jwt_identity, verify_jwt_in_request  # JWT 认证扩展：Token 管理器、创建/验证 Token 的工具函数
from flask_bcrypt import Bcrypt  # 密码哈希扩展，使用 bcrypt 算法安全存储用户密码
from authlib.integrations.flask_client import OAuth  # OAuth 2.0 客户端，用于 GitHub 第三方登录
import meilisearch  # Meilisearch 搜索引擎客户端，提供毫秒级全文搜索能力
from flask_apscheduler import APScheduler  # 定时任务调度器，用于定时执行爬虫等后台任务
from spider import auto_fetch_hacker_news  # 自定义爬虫模块，自动抓取 Hacker News 热门站点
from functools import wraps  # 装饰器工具，用于保留被装饰函数的元信息
from sqlalchemy import text  # SQLAlchemy 原生 SQL 执行工具，用于执行复杂的原始 SQL 语句
import feedparser  # RSS/Atom Feed 解析库，用于抓取和解析行业资讯订阅源
import redis
import pymysql
from dbutils.pooled_db import TooManyConnectionsError
import random
import hmac
import secrets
import logging
import traceback
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from concurrent.futures import ThreadPoolExecutor
from email_service import MAIL_ERROR_MESSAGES, send_verification_email, validate_mail_config
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from recommend_service import rank_sites
from v1_routes import register_v1_routes
from questionnaire_admin_read_routes import register_questionnaire_admin_read_routes
from backend.crawler.review.routes import register_review_routes
from password_reset import register_password_reset_routes
from personalization import register_personalization_routes

# 导入连接池模块
from db_pool import (
    DATABASE_RETRY_DELAYS,
    MYSQL_CHARSET,
    get_connection as pool_get_connection,
    get_database_config,
    is_transient_mysql_error,
    validate_database_config,
)

# 导入扩展模块
import app_extensions

# ✨ 关键点：启动时加载 .env 文件中的机密信息

app = Flask(__name__)  # 创建 Flask 应用实例，__name__ 用于确定资源文件的根路径
app.json.ensure_ascii = False
app.config["MAX_CONTENT_LENGTH"] = BACKGROUND_MAX_REQUEST_BYTES
app.config["BACKGROUND_MAX_FILE_BYTES"] = BACKGROUND_MAX_FILE_BYTES
app.config["BACKGROUND_UPLOAD_ROOT"] = BACKGROUND_UPLOAD_ROOT
DEFAULT_DEV_SECRET = "dev-secret-key-change-me"


def get_secret_config():
    """Return application secrets and fail fast for unsafe production settings."""
    environment_values = [
        (os.getenv(name) or "").strip().lower()
        for name in ("APP_ENV", "FLASK_ENV", "ENV", "VERCEL_ENV")
    ]
    runtime_env = next((value for value in environment_values if value), "")
    is_production = "production" in environment_values

    flask_secret = os.getenv("FLASK_SECRET_KEY")
    jwt_secret = os.getenv("JWT_SECRET_KEY")

    if is_production:
        if not flask_secret or not jwt_secret:
            raise RuntimeError(
                "Production requires explicit FLASK_SECRET_KEY and JWT_SECRET_KEY"
            )
        if DEFAULT_DEV_SECRET in (flask_secret, jwt_secret):
            raise RuntimeError("Production secrets must not use the development default")
        if flask_secret == jwt_secret:
            raise RuntimeError("FLASK_SECRET_KEY and JWT_SECRET_KEY must be different in production")
        return {
            "flask_secret": flask_secret,
            "jwt_secret": jwt_secret,
            "runtime_env": runtime_env,
        }

    flask_secret = flask_secret or os.getenv("SECRET_KEY") or jwt_secret or DEFAULT_DEV_SECRET
    jwt_secret = jwt_secret or flask_secret or DEFAULT_DEV_SECRET
    return {
        "flask_secret": flask_secret,
        "jwt_secret": jwt_secret,
        "runtime_env": runtime_env,
    }


secret_config = get_secret_config()
app.secret_key = secret_config["flask_secret"]
REDIS_URL = (os.getenv("REDIS_URL") or "redis://localhost:6379/0").strip()


def get_limiter_storage_uri():
    """Return limiter storage without connecting to Redis during import."""
    configured = (os.getenv("RATELIMIT_STORAGE_URI") or "").strip()
    if configured:
        return configured
    if not should_swallow_limiter_errors():
        return REDIS_URL
    return "memory://"


def should_swallow_limiter_errors():
    """Keep development usable without silently bypassing production limits."""
    environments = {
        (os.getenv(name) or "").strip().lower()
        for name in ("APP_ENV", "FLASK_ENV", "ENV", "VERCEL_ENV")
    }
    return "production" not in environments


def should_enable_limiter():
    """Enable distributed limits in production or when explicitly configured."""
    return not should_swallow_limiter_errors() or bool(
        (os.getenv("RATELIMIT_STORAGE_URI") or "").strip()
    )

def table_columns(cursor, table_name):
    cursor.execute(f"SHOW COLUMNS FROM {table_name}")
    return {row["Field"] for row in cursor.fetchall()}


def get_frontend_url():
    configured_url = (os.getenv("FRONTEND_URL") or "").strip()
    return (configured_url or "http://localhost:5173").rstrip("/")


def get_outbound_proxies():
    """Return an optional proxy configured for outbound HTTP requests."""
    proxy_url = os.getenv("OUTBOUND_PROXY_URL", "").strip()
    if not proxy_url:
        return None
    return {"http": proxy_url, "https": proxy_url}


def auth_session_data(user, access_token, refresh_token):
    user_info = {
        "id": user.get("id"),
        "username": user.get("username"),
        "email": user.get("email"),
        "avatar": user.get("avatar") or user.get("avatar_url"),
    }
    role = user.get("role") or "user"
    questionnaire_completed = bool(
        user.get("questionnaire_completed") or user.get("has_survey")
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_info": user_info,
        "user_role": role,
        "questionnaire_completed": questionnaire_completed,
    }


def admin_role_required(fn):
    """Require a valid JWT and a database-backed administrator role."""

    @wraps(fn)
    @jwt_required()
    def decorator(*args, **kwargs):
        username = get_jwt_identity()
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT role FROM users WHERE username=%s", (username,))
                user = cursor.fetchone()
        finally:
            conn.close()

        if not user or user.get("role") not in ("admin", "super_admin"):
            return jsonify({"code": 403, "msg": "权限不足，仅管理员可访问"}), 403
        return fn(*args, **kwargs)

    return decorator


limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["5000 per day", "1000 per hour"],
    storage_uri=get_limiter_storage_uri(),
    swallow_errors=should_swallow_limiter_errors(),
    enabled=should_enable_limiter(),
)

redis_client = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)
executor = ThreadPoolExecutor(max_workers=10)
login_failures = {}

LOGIN_FAILURE_WINDOW_SECONDS = 300
LOGIN_FAILURE_LIMIT = 5
LOGIN_LOCK_SECONDS = 60
AUTH_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
AUTH_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{4,50}$")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
REGISTRATION_CODE_TTL_SECONDS = 300
REGISTRATION_CODE_RESEND_SECONDS = 60
REGISTRATION_CODE_HOURLY_LIMIT = 5
REGISTRATION_CODE_MAX_ATTEMPTS = 5
REGISTRATION_CODE_PURPOSE = "register"


def normalize_auth_email(value):
    return str(value or "").strip().lower()


def login_request_id():
    """Return a safe correlation id without reflecting arbitrary headers."""
    existing = getattr(g, "request_id", None)
    if existing:
        return existing
    supplied = (request.headers.get("X-Request-ID") or "").strip()
    g.request_id = supplied if REQUEST_ID_PATTERN.fullmatch(supplied) else secrets.token_hex(8)
    return g.request_id


@app.before_request
def assign_request_id():
    login_request_id()


@app.after_request
def add_request_id_header(response):
    response.headers.setdefault("X-Request-ID", login_request_id())
    return response


def is_database_unavailable(error):
    """Errors that mean MySQL cannot currently serve this request."""
    return is_transient_mysql_error(error) or isinstance(
        error,
        (
            pymysql.err.InterfaceError,
            TooManyConnectionsError,
            OSError,
            TimeoutError,
        ),
    )


def password_hash_is_valid(password_hash, password):
    """Verify only supported hashes; never fall back to plaintext passwords."""
    if not password_hash:
        return False
    try:
        return check_password_hash(password_hash, password)
    except (TypeError, ValueError):
        # A small number of historical accounts used Flask-Bcrypt. Retain
        # compatibility for its hashes while keeping registration on Werkzeug.
        try:
            return bcrypt.check_password_hash(password_hash, password)
        except (TypeError, ValueError):
            return False


def is_valid_auth_email(value):
    return bool(AUTH_EMAIL_PATTERN.fullmatch(value))


def registration_error(code, message, status):
    return jsonify({"success": False, "code": code, "message": message, "msg": message}), status


def _registration_code_digest(email, code):
    secret = str(app.config.get("SECRET_KEY") or app.secret_key or "").encode("utf-8")
    payload = f"{REGISTRATION_CODE_PURPOSE}:{email}:{code}".encode("utf-8")
    return hmac.new(secret, payload, "sha256").hexdigest()


def ensure_registration_code_table(conn):
    conn.cursor().execute(
        """
        CREATE TABLE IF NOT EXISTS email_verification_codes (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            email VARCHAR(120) NOT NULL,
            purpose VARCHAR(32) NOT NULL,
            code_hash CHAR(64) NOT NULL,
            expires_at DATETIME NOT NULL,
            sent_at DATETIME NOT NULL,
            attempt_count TINYINT UNSIGNED NOT NULL DEFAULT 0,
            used_at DATETIME NULL,
            request_ip VARCHAR(64) NULL,
            PRIMARY KEY (id),
            UNIQUE KEY uq_email_verification_purpose (email, purpose),
            KEY idx_email_verification_expiry (expires_at),
            KEY idx_email_verification_ip_sent (request_ip, sent_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    conn.commit()


def _datetime_value(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _rollback_and_close(conn):
    if conn is None:
        return
    try:
        conn.rollback()
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass


def _verify_registration_code(conn, email, verification_code):
    now = datetime.utcnow()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, code_hash, expires_at, attempt_count, used_at
            FROM email_verification_codes
            WHERE email=%s AND purpose=%s
            ORDER BY sent_at DESC, id DESC
            LIMIT 1
            FOR UPDATE
            """,
            (email, REGISTRATION_CODE_PURPOSE),
        )
        record = cursor.fetchone()
        if not record:
            return False, "CODE_NOT_FOUND", "请先获取邮箱验证码"

        expires_at = _datetime_value(record.get("expires_at"))
        attempts = int(record.get("attempt_count") or 0)
        if record.get("used_at"):
            return False, "CODE_ALREADY_USED", "验证码已使用，请重新获取"
        if expires_at is None or expires_at <= now:
            return False, "CODE_EXPIRED", "验证码已过期，请重新获取"
        if attempts >= REGISTRATION_CODE_MAX_ATTEMPTS:
            return False, "CODE_TOO_MANY_ATTEMPTS", "验证码错误次数过多，请重新获取"
        if hmac.compare_digest(
            str(record.get("code_hash") or ""),
            _registration_code_digest(email, verification_code),
        ):
            return True, None, None

        attempts = attempts + 1
        cursor.execute(
            "UPDATE email_verification_codes SET attempt_count=%s WHERE id=%s",
            (attempts, record["id"]),
        )
        conn.commit()
        if attempts >= REGISTRATION_CODE_MAX_ATTEMPTS:
            return False, "CODE_TOO_MANY_ATTEMPTS", "验证码错误次数过多，请重新获取"
        return False, "CODE_INVALID", "验证码错误"


DB_CONFIG = {
    **get_database_config(),
    "cursorclass": pymysql.cursors.DictCursor,
}


def get_db_connection():
    return pool_get_connection()


def get_runtime_env():
    env = (
        os.getenv("APP_ENV")
        or os.getenv("FLASK_ENV")
        or os.getenv("VERCEL_ENV")
        or ""
    ).lower()
    return "production" if env == "production" else "development"


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "code": 200,
        "message": "success",
        "data": {
            "status": "ok",
            "service": "zhihui-navigation",
            "env": get_runtime_env(),
        },
    }), 200


@app.route("/api/health/db", methods=["GET"])
def database_health_check():
    request_id = login_request_id()
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return jsonify({
            "code": 200,
            "message": "database connected",
            "data": {"database": "ok"},
        }), 200
    except Exception as error:
        app.logger.exception(
            "database health check unavailable request_id=%s error_type=%s",
            request_id,
            type(error).__name__,
        )
        return jsonify({
            "code": "DATABASE_UNAVAILABLE",
            "message": "database unavailable",
            "data": {"database": "unavailable"},
        }), 503
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass





@app.route("/api/health/database", methods=["GET"])
def database_availability_check():
    """Return only availability state; never expose database configuration."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return jsonify({"ok": True, "database": "available"}), 200
    except Exception as error:
        app.logger.warning(
            "database unavailable route=%s error_type=%s",
            request.path,
            type(error).__name__,
        )
        return jsonify({"ok": False, "database": "unavailable"}), 503
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def login_rate_key(account):
    ip = get_remote_address() or request.remote_addr or "unknown"
    normalized_account = (account or "").strip().lower() or "unknown"
    return f"{ip}:{normalized_account}"


def get_login_retry_after(key):
    record = login_failures.get(key)
    if not record:
        return 0

    now = time.time()
    lock_until = record.get("lock_until", 0)
    if lock_until > now:
        return int(lock_until - now) + 1

    if now - record.get("first_failed_at", now) > LOGIN_FAILURE_WINDOW_SECONDS:
        login_failures.pop(key, None)

    return 0


def record_login_failure(key):
    now = time.time()
    record = login_failures.get(key)
    if not record or now - record.get("first_failed_at", now) > LOGIN_FAILURE_WINDOW_SECONDS:
        record = {"count": 0, "first_failed_at": now, "lock_until": 0}

    record["count"] += 1
    if record["count"] >= LOGIN_FAILURE_LIMIT:
        record["lock_until"] = now + LOGIN_LOCK_SECONDS
    login_failures[key] = record
    return get_login_retry_after(key)


def clear_login_failures(key):
    login_failures.pop(key, None)


@app.errorhandler(429)
def handle_rate_limit(error):
    retry_after = getattr(error, "retry_after", None) or LOGIN_LOCK_SECONDS
    return jsonify({
        "code": 429,
        "message": "请求过于频繁，请稍后再试",
        "msg": "请求过于频繁，请稍后再试",
        "retry_after": int(retry_after),
    }), 429

def async_save_click(item_id):
    """异步将点击日志写入 MySQL"""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "INSERT INTO click_log (item_id) VALUES (%s)"
            cursor.execute(sql, (item_id,))
        connection.commit()
        connection.close()
    except Exception as e:
        print(f"写入点击日志失败: {e}")


def record_unified_behavior_event(user_id, website_id, event_type, source="other", payload=None):
    """Best-effort bridge for legacy app.py routes.

    The v1 route owns the full validation API; this bridge keeps the legacy
    favorite toggle on the same event stream without allowing telemetry to
    break the user-facing mutation.
    """
    if not user_id or not website_id or event_type not in {"favorite"}:
        return False
    payload = payload if isinstance(payload, dict) else {}
    source = source if source in {
        "personalized_recommendation", "category", "search", "favorite", "history", "direct", "other",
    } else "other"
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    safe_metadata = {
        key: str(metadata[key])[:128]
        for key in ("display_batch_index", "candidate_pool_id", "position", "surface", "personalization_type")
        if metadata.get(key) is not None
    }
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_behavior_events (
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  user_id INT NULL, website_id INT NOT NULL,
                  event_type VARCHAR(32) NOT NULL, source VARCHAR(64) NOT NULL DEFAULT 'other',
                  recommendation_batch_id VARCHAR(128) NULL, questionnaire_version VARCHAR(64) NULL,
                  profile_version VARCHAR(64) NULL, session_id VARCHAR(128) NULL,
                  metadata_json JSON NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  INDEX idx_behavior_events_user_site_created (user_id, website_id, created_at),
                  INDEX idx_behavior_events_batch (recommendation_batch_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                SELECT id FROM user_behavior_events
                WHERE user_id=%s AND website_id=%s AND event_type='favorite'
                LIMIT 1
                """,
                (user_id, website_id),
            )
            if cursor.fetchone():
                return False
            cursor.execute(
                """
                INSERT INTO user_behavior_events
                  (user_id, website_id, event_type, source, recommendation_batch_id,
                   questionnaire_version, profile_version, session_id, metadata_json)
                VALUES (%s,%s,'favorite',%s,%s,%s,%s,%s,%s)
                """,
                (
                    user_id, website_id, source,
                    str(payload.get("recommendation_batch_id") or "")[:128] or None,
                    str(payload.get("questionnaire_version") or "")[:64] or None,
                    str(payload.get("profile_version") or "")[:64] or None,
                    str(payload.get("session_id") or "")[:128] or None,
                    json.dumps(safe_metadata, ensure_ascii=False) if safe_metadata else None,
                ),
            )
        conn.commit()
        return True
    except Exception:
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
        app.logger.exception("legacy favorite behavior event failed")
        return False
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass

# ================= 修改密码接口 =================
@app.route('/api/user/password', methods=['POST'])
@jwt_required()
def change_password():
    # 获取当前请求人的身份 (如果是按之前的逻辑，这里可能是 username)
    username = get_jwt_identity() 
    data = request.json
    
    old_pwd = data.get('old_password')
    new_pwd = data.get('new_password')

    if not old_pwd or not new_pwd:
        return jsonify({'code': 400, 'msg': '密码参数不完整'}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 去数据库查这个人的旧密码 Hash
            cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'code': 404, 'msg': '找不到该用户'}), 404
                
            # 校验用户输入的旧密码对不对
            if not bcrypt.check_password_hash(user['password'], old_pwd):
                return jsonify({'code': 401, 'msg': '旧密码输入错误！'}), 401
                
            # 旧密码正确，把新密码加密
            hashed_new_pwd = bcrypt.generate_password_hash(new_pwd).decode('utf-8')
            
            # 存入数据库
            cursor.execute("UPDATE users SET password = %s WHERE username = %s", (hashed_new_pwd, username))
        conn.commit()
        return jsonify({'code': 0, 'msg': '密码修改成功'})
    except Exception as e:
        return jsonify({'code': 500, 'msg': f'服务器错误: {str(e)}'}), 500
    finally:
        conn.close()

# ================= 2. 注册验证码 =================
@app.route('/api/auth/send-register-code', methods=['POST'])
@limiter.limit("5 per hour")
def send_register_code():
    data = request.get_json(silent=True) or {}
    email = normalize_auth_email(data.get("email"))
    request_id = request.headers.get("X-Request-ID") or secrets.token_hex(8)
    if not email:
        return registration_error("EMAIL_REQUIRED", "邮箱不能为空", 400)
    if not is_valid_auth_email(email):
        return registration_error("EMAIL_INVALID", "邮箱格式不正确", 400)

    _mail_missing = validate_mail_config()
    if _mail_missing:
        app.logger.warning(
            "register verification mail config missing request_id=%s",
            request_id,
        )
        return registration_error("MAIL_CONFIG_MISSING", "邮件服务尚未完成配置", 503)

    conn = None
    try:
        conn = get_db_connection()
        ensure_registration_code_table(conn)
        now = datetime.utcnow()
        request_ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "unknown").split(",")[0].strip()[:64]
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE email=%s LIMIT 1", (email,))
            if cursor.fetchone():
                _rollback_and_close(conn)
                return registration_error("EMAIL_ALREADY_REGISTERED", "该邮箱已注册", 409)

            cursor.execute(
                "SELECT sent_at FROM email_verification_codes WHERE email=%s AND purpose=%s LIMIT 1",
                (email, REGISTRATION_CODE_PURPOSE),
            )
            previous = cursor.fetchone()
            previous_sent_at = _datetime_value(previous.get("sent_at")) if previous else None
            if previous_sent_at and (now - previous_sent_at).total_seconds() < REGISTRATION_CODE_RESEND_SECONDS:
                retry_after = max(1, REGISTRATION_CODE_RESEND_SECONDS - int((now - previous_sent_at).total_seconds()))
                _rollback_and_close(conn)
                return jsonify({
                    "success": False,
                    "code": "RATE_LIMITED",
                    "message": "验证码发送过于频繁，请稍后再试",
                    "msg": "验证码发送过于频繁，请稍后再试",
                    "retry_after": retry_after,
                }), 429

            cursor.execute(
                "SELECT COUNT(*) AS total FROM email_verification_codes WHERE email=%s AND purpose=%s AND sent_at >= %s",
                (email, REGISTRATION_CODE_PURPOSE, now - timedelta(hours=1)),
            )
            if int((cursor.fetchone() or {}).get("total") or 0) >= REGISTRATION_CODE_HOURLY_LIMIT:
                _rollback_and_close(conn)
                return registration_error("RATE_LIMITED", "验证码发送次数已达上限，请稍后再试", 429)

            cursor.execute(
                "SELECT COUNT(*) AS total FROM email_verification_codes WHERE request_ip=%s AND purpose=%s AND sent_at >= %s",
                (request_ip, REGISTRATION_CODE_PURPOSE, now - timedelta(hours=1)),
            )
            if int((cursor.fetchone() or {}).get("total") or 0) >= REGISTRATION_CODE_HOURLY_LIMIT * 3:
                _rollback_and_close(conn)
                return registration_error("RATE_LIMITED", "当前网络发送次数已达上限，请稍后再试", 429)

        verification_code = f"{secrets.randbelow(1_000_000):06d}"
        sent, mail_code = send_verification_email(email, verification_code)
        if not sent:
            _rollback_and_close(conn)
            app.logger.warning(
                "register verification mail failed request_id=%s code=%s",
                request_id,
                mail_code,
            )
            message = MAIL_ERROR_MESSAGES.get(mail_code, "邮件发送失败，请稍后重试")
            return registration_error(mail_code, message, 503)

        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO email_verification_codes
                    (email, purpose, code_hash, expires_at, sent_at, attempt_count, used_at, request_ip)
                VALUES (%s, %s, %s, %s, %s, 0, NULL, %s)
                ON DUPLICATE KEY UPDATE
                    code_hash=VALUES(code_hash), expires_at=VALUES(expires_at), sent_at=VALUES(sent_at),
                    attempt_count=0, used_at=NULL, request_ip=VALUES(request_ip)
                """,
                (
                    email,
                    REGISTRATION_CODE_PURPOSE,
                    _registration_code_digest(email, verification_code),
                    now + timedelta(seconds=REGISTRATION_CODE_TTL_SECONDS),
                    now,
                    request_ip,
                ),
            )
        conn.commit()
        return jsonify({"success": True, "code": 0, "message": "验证码已发送", "msg": "验证码已发送"})
    except Exception as error:
        _rollback_and_close(conn)
        app.logger.exception(
            "register verification persistence failed request_id=%s error_type=%s",
            request_id,
            type(error).__name__,
        )
        return registration_error("DATABASE_FAILED", "验证码服务暂不可用，请稍后重试", 503)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# ================= 3. 用户注册 =================
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    username = str(data.get('username') or '').strip()
    email = normalize_auth_email(data.get('email'))
    password = data.get('password')
    verification_code = str(
        data.get("verification_code")
        or data.get("verificationCode")
        or data.get("email_code")
        or ""
    ).strip()

    if not username:
        return registration_error("USERNAME_REQUIRED", "请输入用户名", 400)
    if not AUTH_USERNAME_PATTERN.fullmatch(username):
        return registration_error(
            "USERNAME_INVALID", "用户名需为 4-50 位字母、数字或下划线", 400
        )
    if not email:
        return registration_error("EMAIL_REQUIRED", "邮箱不能为空", 400)
    if not is_valid_auth_email(email):
        return registration_error("EMAIL_INVALID", "邮箱格式不正确", 400)
    if not password:
        return registration_error("PASSWORD_REQUIRED", "请输入密码", 400)
    if len(password) < 8:
        return registration_error("PASSWORD_TOO_SHORT", "密码长度不足，至少需要 8 位", 400)
    if not verification_code:
        return registration_error("CODE_REQUIRED", "请输入邮箱验证码", 400)

    conn = None
    try:
        conn = get_db_connection()
        ensure_registration_code_table(conn)
        app.logger.info(
            "Registration step username_present=%s email_present=%s",
            bool(username),
            bool(email),
        )
        valid, error_code, error_message = _verify_registration_code(conn, email, verification_code)
        if not valid:
            _rollback_and_close(conn)
            return registration_error(error_code, error_message, 400)

        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username=%s LIMIT 1", (username,))
            if cursor.fetchone():
                _rollback_and_close(conn)
                return registration_error("USERNAME_EXISTS", "该用户名已被使用", 409)
            cursor.execute("SELECT id FROM users WHERE email=%s LIMIT 1", (email,))
            if cursor.fetchone():
                _rollback_and_close(conn)
                return registration_error("EMAIL_ALREADY_REGISTERED", "该邮箱已注册", 409)

            hashed_pw = generate_password_hash(password)
            cursor.execute(
                """INSERT INTO users
                       (username, email, password_hash, role, status, login_provider, created_at)
                   VALUES (%s, %s, %s, 'user', 'active', 'local', %s)""",
                (username, email, hashed_pw, datetime.utcnow()),
            )
            cursor.execute(
                """UPDATE email_verification_codes SET used_at=%s
                   WHERE email=%s AND purpose=%s AND used_at IS NULL""",
                (datetime.utcnow(), email, REGISTRATION_CODE_PURPOSE),
            )
        conn.commit()
    except pymysql.err.IntegrityError as error:
        _rollback_and_close(conn)
        error_text = str(error).lower()
        if "username" in error_text:
            return registration_error("USERNAME_EXISTS", "该用户名已被使用", 409)
        if "email" in error_text:
            return registration_error("EMAIL_ALREADY_REGISTERED", "该邮箱已注册", 409)
        app.logger.warning("Local registration integrity error")
        return registration_error("DATABASE_ERROR", "账号创建失败，请稍后重试", 500)
    except Exception as error:
        _rollback_and_close(conn)
        app.logger.exception("Local registration failed error_type=%s", type(error).__name__)
        return registration_error("DATABASE_ERROR", "账号创建失败，请稍后重试", 500)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    return jsonify({
        'success': True,
        'code': 'REGISTER_SUCCESS',
        'msg': '注册成功',
        'message': '注册成功',
    }), 201

# ================= 3. 用户登录 =================
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    account = str(data.get('account') or data.get('email') or data.get('username') or '').strip()
    password = str(data.get('password') or '')
    request_id = login_request_id()
    failure_key = login_rate_key(account)
    retry_after = get_login_retry_after(failure_key)

    if retry_after > 0:
        return jsonify({
            'code': 429,
            'message': '请求过于频繁，请稍后再试',
            'msg': '请求过于频繁，请稍后再试',
            'retry_after': retry_after,
        }), 429

    if not account or password is None or password == '':
        return jsonify({
            'success': False,
            'code': 'CREDENTIALS_REQUIRED',
            'message': '请输入账号和密码',
            'msg': '请输入账号和密码',
        }), 400

    conn = None
    try:
        for database_attempt in range(4):
            try:
                conn = get_db_connection()
                with conn.cursor() as cursor:
                    cursor.execute(
                        """SELECT * FROM users
                           WHERE username = %s OR LOWER(email) = LOWER(%s)
                           LIMIT 1""",
                        (account, account),
                    )
                    user = cursor.fetchone()
                break
            except Exception as error:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
                    conn = None
                if not is_transient_mysql_error(error) or database_attempt >= 3:
                    raise
                delay = DATABASE_RETRY_DELAYS[database_attempt]
                app.logger.warning(
                    "login transient database failure; reconnecting request_id=%s attempt=%s",
                    request_id,
                    database_attempt + 1,
                )
                if delay:
                    time.sleep(delay)
    except Exception as error:
        if is_database_unavailable(error):
            app.logger.exception(
                "login database unavailable request_id=%s route=%s error_type=%s",
                request_id,
                request.path,
                type(error).__name__,
            )
            return jsonify({
                'success': False,
                'code': 'AUTH_DATABASE_UNAVAILABLE',
                'message': '数据库服务暂时不可用，请稍后重试',
                'msg': '数据库服务暂时不可用，请稍后重试',
            }), 503
        app.logger.exception(
            "login unexpected failure request_id=%s route=%s error_type=%s",
            request_id,
            request.path,
            type(error).__name__,
        )
        return jsonify({
            'success': False,
            'code': 'AUTH_SERVICE_ERROR',
            'message': '登录服务发生内部错误',
            'msg': '登录服务发生内部错误',
        }), 500
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


    # Older installations may predate the soft-delete migration.  Checking
    # the optional column after SELECT * keeps login compatible without
    # turning a missing `deleted_at` column into an HTTP 500.
    if user and user.get('deleted_at') is not None:
        user = None

    disabled_statuses = {'disabled', 'inactive', 'banned', 'blocked', 'deleted'}
    if user and str(user.get('status') or 'active').lower() in disabled_statuses:
        app.logger.info("Local login rejected reason=ACCOUNT_DISABLED request_id=%s", request_id)
        return jsonify({
            'success': False,
            'code': 'ACCOUNT_DISABLED',
            'message': '账号不可用',
            'msg': '账号不可用',
        }), 403

    if user and password_hash_is_valid(user.get('password_hash'), password):
        clear_login_failures(failure_key)
        session_claims = {"session_version": int(user.get("session_version") or 0)}
        access_token = create_access_token(
            identity=user['username'], additional_claims=session_claims
        )
        refresh_token = create_refresh_token(
            identity=user['username'], additional_claims=session_claims
        )
        session_data = auth_session_data(user, access_token, refresh_token)
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': session_data,
            **session_data,
        })

    app.logger.info("Local login rejected reason=%s", "PASSWORD_INVALID" if user else "USER_NOT_FOUND")
    retry_after = record_login_failure(failure_key)
    if retry_after > 0:
        return jsonify({
            'code': 429,
            'message': '请求过于频繁，请稍后再试',
            'msg': '请求过于频繁，请稍后再试',
            'retry_after': retry_after,
        }), 429

    return jsonify({
        'success': False,
        'code': 'INVALID_CREDENTIALS',
        'message': '账号或密码错误',
        'msg': '账号或密码错误',
    }), 401


@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def current_auth_user():
    identity = get_jwt_identity()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE username=%s OR email=%s LIMIT 1",
                (identity, identity),
            )
            user = cursor.fetchone()
    finally:
        conn.close()

    if not user or user.get('deleted_at'):
        return jsonify({'code': 401, 'msg': '当前用户不存在或已失效'}), 401

    session_data = auth_session_data(user, None, None)
    session_data.pop('access_token', None)
    session_data.pop('refresh_token', None)
    return jsonify({
        'code': 0,
        'msg': 'success',
        'data': session_data,
        **session_data,
    })

# ================= 4. 注销账户 (逻辑删除 + 7天冷静期) =================
@app.route('/api/user/delete-account', methods=['POST'])
@jwt_required()
def delete_account():
    username = get_jwt_identity()
    password = request.json.get('password')
    
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if not check_password_hash(user['password_hash'], password):
            return jsonify({'code': 401, 'msg': '密码验证失败'})
            
        # 逻辑删除：打上时间戳
        cursor.execute("UPDATE users SET deleted_at = %s WHERE username = %s", (datetime.now(), username))
    conn.commit()
    conn.close()
    
    return jsonify({'code': 0, 'msg': '账号已进入 7 天注销冷静期'})

# ================= 核心计算函数：计算点击增长率 =================
def calculate_and_cache_growth_rate():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 核心 SQL: 聚合今日和昨日的点击数据
            # 注意：如果你的网站表不叫 websites，请将下方的 websites 改为实际表名
            sql = """
                SELECT 
                    log.item_id,
                    i.name as title,
                    i.logo_url as cover_url,
                    SUM(CASE WHEN DATE(log.clicked_at) = CURDATE() THEN 1 ELSE 0 END) AS today_clicks,
                    SUM(CASE WHEN DATE(log.clicked_at) = DATE_SUB(CURDATE(), INTERVAL 1 DAY) THEN 1 ELSE 0 END) AS yesterday_clicks
                FROM click_log log
                JOIN websites i ON log.item_id = i.id
                WHERE log.clicked_at >= DATE_SUB(CURDATE(), INTERVAL 1 DAY)
                GROUP BY log.item_id
            """
            cursor.execute(sql)
            results = cursor.fetchall()
        conn.close()

        leaderboard = []
        for row in results:
            today = row['today_clicks']
            yesterday = row['yesterday_clicks']
            
            if today == 0: continue # 今日无点击不参与排行

            if yesterday == 0 and today > 0:
                growth_rate = 100.0
            else:
                growth_rate = ((today - yesterday) / yesterday) * 100.0

            leaderboard.append({
                'id': row['item_id'],
                'title': row['title'],
                'cover_url': row['cover_url'],
                'today_clicks': int(today),
                'growth_rate': round(growth_rate, 1)
            })

        # 按涨幅降序排列，取 Top 50
        leaderboard.sort(key=lambda x: (x['growth_rate'], x['today_clicks']), reverse=True)
        top_50 = leaderboard[:50]

        # 尝试存入 Redis，如果 Redis 没开就跳过，直接返回数据
        try:
            redis_client.setex("leaderboard:growth_rate", 300, json.dumps(top_50))
        except Exception as redis_e:
            pass 

        return top_50
    except Exception as e:
        print(f"计算排行榜严重异常: {e}")
        return []

def is_production_environment():
    environment_values = {
        (os.getenv(name) or "").strip().lower()
        for name in ("APP_ENV", "FLASK_ENV", "ENV", "VERCEL_ENV")
    }
    return "production" in environment_values


def get_cors_origins():
    """Return configured origins, or local Vite defaults in development."""
    configured_origins = [
        *os.getenv("CORS_ALLOWED_ORIGINS", "").split(","),
        os.getenv("FRONTEND_URL", ""),
    ]
    origins = {
        origin.strip().rstrip("/")
        for origin in configured_origins
        if origin.strip().rstrip("/") and origin.strip().rstrip("/") != "*"
    }
    if not is_production_environment():
        origins.update(LOCAL_VITE_ORIGINS)
    return sorted(origins)


# 允许跨域请求
# flask-cors 6.x does not match a bracketed IPv6 Origin reliably. Vite may
# bind to ::1 on Windows, so make the supported local Vite origins explicit.
LOCAL_VITE_ORIGINS = frozenset(
    {
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://[::1]:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://[::1]:5174",
    }
)

def configure_cors(application, origins=None):
    """Configure exact CORS origins and the Flask-CORS IPv6 compatibility hook."""
    allowed_origins = frozenset(origins if origins is not None else get_cors_origins())
    CORS(application, origins=sorted(allowed_origins), supports_credentials=True)

    @application.after_request
    def allow_ipv6_cors_origin(response):
        origin = request.headers.get("Origin")
        if origin not in allowed_origins or not origin.startswith(("http://[", "https://[")):
            return response

        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        if "Origin" not in response.headers.get("Vary", ""):
            response.headers.add("Vary", "Origin")
        if request.method == "OPTIONS":
            response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS, POST, PUT, PATCH, DELETE"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        return response

    return allowed_origins


# Flask-CORS handles ordinary origins. The compatibility hook in configure_cors
# completes only bracketed IPv6 origins, which Flask-CORS 6.x does not match.
CORS_ORIGINS = configure_cors(app)

# ===== 生产级日志配置 =====
app = app_extensions.setup_logging(app)

# ===== 全局异常处理器注册 =====
app = app_extensions.register_error_handlers(app)

# ===== 数据库连接配置 =====
# 从环境变量读取数据库连接参数；用户和数据库名缺失时在首次连接前明确报错。
db_user = DB_CONFIG['user'] or ''
db_pass = DB_CONFIG['password']
db_host = DB_CONFIG['host']
db_port = DB_CONFIG['port']
db_name = DB_CONFIG['database'] or ''
db_charset = MYSQL_CHARSET       # 数据库字符集

# 配置数据库连接 URL (MySQL)
# 格式：mysql+pymysql://用户名:密码@主机:端口/数据库名?字符集
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{quote_plus(db_user)}:{quote_plus(db_pass)}@{db_host}:{db_port}/{db_name}?charset={db_charset}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 关闭对象修改追踪，节省内存，避免不必要的警告
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 280,
    'pool_size': 5,
    'max_overflow': 5,
    'pool_timeout': 30,
}

# ===== JWT Token 配置 =====
app.config['SECRET_KEY'] = app.secret_key
app.config['JWT_SECRET_KEY'] = secret_config['jwt_secret']  # JWT 签名密钥，生产环境必须使用强随机字符串
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)   # Access Token 1小时过期，用于日常接口鉴权
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)  # Refresh Token 30天过期，用于无感刷新 Access Token
# Admin APIs authenticate only from Authorization: Bearer.  Do not silently
# accept ambient browser cookies; this keeps the crawler write endpoints out
# of the cookie-CSRF threat model unless deployment deliberately changes it.
app.config['JWT_TOKEN_LOCATION'] = ['headers']

class UserFavorite(db.Model):
    """
    用户收藏夹数据模型

    记录用户收藏的网站，支持多用户各自维护独立的收藏列表。
    与 users 表通过外键关联，website_id 使用 BigInteger 以兼容前端
    用 Date.now() 生成的毫秒级时间戳作为临时 ID 的场景。
    """
    __tablename__ = 'user_favorites'  # 对应数据库中的表名
    id = db.Column(db.Integer, primary_key=True)  # 收藏记录的自增主键
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 关联的用户 ID（外键）
    website_id = db.Column(db.BigInteger, nullable=False) # 使用 BigInteger 容纳 Date.now()
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
db.init_app(app)   # 将 SQLAlchemy 数据库实例与 Flask 应用绑定
jwt = JWTManager(app)   # 初始化 JWT 管理器，处理 Token 的签发与验证


@jwt.unauthorized_loader
def handle_missing_jwt(reason):
    return jsonify(
        {
            "success": False,
            "code": "AUTH_REQUIRED",
            "error_code": "AUTH_REQUIRED",
            "legacy_code": 401,
            "message": "请先登录",
            "msg": "请先登录",
            "data": {},
        }
    ), 401


@jwt.invalid_token_loader
def handle_invalid_jwt(reason):
    return jsonify(
        {
            "success": False,
            "code": "AUTH_INVALID",
            "error_code": "AUTH_INVALID",
            "legacy_code": 401,
            "message": "登录凭证无效，请重新登录",
            "msg": "登录凭证无效，请重新登录",
            "data": {},
        }
    ), 401


@jwt.expired_token_loader
def handle_expired_jwt(jwt_header, jwt_payload):
    return jsonify(
        {
            "success": False,
            "code": "AUTH_EXPIRED",
            "error_code": "AUTH_EXPIRED",
            "legacy_code": 401,
            "message": "登录状态已过期，请重新登录",
            "msg": "登录状态已过期，请重新登录",
            "data": {},
        }
    ), 401


@jwt.token_in_blocklist_loader
def handle_session_version(jwt_header, jwt_payload):
    """Reject access and refresh tokens issued before a password reset."""
    # Tokens issued before this migration have no claim and are version zero.
    # They remain valid until their owner resets a password and increments the
    # persisted version.
    token_version = int(jwt_payload.get("session_version") or 0)

    identity = jwt_payload.get("sub")
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM users LIKE 'session_version'")
            if not cursor.fetchone():
                # Legacy databases predate session versioning. Tokens issued by
                # those databases remain valid until the migration is applied.
                return False
            cursor.execute(
                "SELECT session_version FROM users WHERE username=%s LIMIT 1",
                (identity,),
            )
            user = cursor.fetchone()
        return not user or int(user.get("session_version") or 0) != token_version
    except Exception as error:
        app.logger.error(
            "JWT session validation failed error_type=%s", type(error).__name__
        )
        return True
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


@jwt.revoked_token_loader
def handle_revoked_jwt(jwt_header, jwt_payload):
    return jsonify(
        {
            "success": False,
            "code": "AUTH_REVOKED",
            "error_code": "AUTH_REVOKED",
            "message": "登录状态已失效，请重新登录",
            "msg": "登录状态已失效，请重新登录",
            "data": {},
        }
    ), 401


bcrypt = Bcrypt(app)    # 初始化 bcrypt 密码哈希工具，用于安全存储用户密码

def is_valid_url(url):
    """
    校验 URL 格式是否合法。

    使用 urllib.parse.urlparse 解析 URL，检查是否同时包含
    协议（scheme，如 http/https）和域名（netloc）两个必要部分。

    参数：
        url (str): 待校验的 URL 字符串

    返回：
        bool: URL 格式合法返回 True，否则返回 False
    """
    try:
        result = urlparse(url)  # 解析 URL 为各组成部分
        return all([result.scheme, result.netloc])  # 必须同时有协议和域名才算合法
    except ValueError:
        return False  # 解析异常时视为非法 URL

# ===== Meilisearch 搜索引擎初始化 =====
# 1. 连接 Docker 里的引擎
MEILI_HOST = os.getenv('MEILI_HOST', 'http://127.0.0.1:7700')
MEILI_MASTER_KEY = os.getenv('MEILI_MASTER_KEY')
meili_client = meilisearch.Client(MEILI_HOST, MEILI_MASTER_KEY)  # Meilisearch 主密钥从环境变量读取
meili_index = meili_client.index('websites')  # 获取名为 'websites' 的搜索索引（相当于数据库中的一张表）

# 2. 【核心】配置智能排序规则 (建议放在 app 启动处执行一次)
def setup_search_engine():
    """
    初始化 Meilisearch 搜索引擎的索引配置。

    设置可搜索字段和排序规则，确保搜索结果既准确又按热度排序。
    此函数建议在应用启动时调用一次，后续无需重复执行。
    """
    # 设定可以搜哪些字段
    meili_index.update_searchable_attributes(['name', 'url'])  # 只对网站名称和 URL 建立全文索引
    # 设定排序规则：先看匹配度，再看点击量(clicks)倒序
    meili_index.update_ranking_rules([
        "words", "typo", "proximity", "attribute", "sort", "exactness"
    ])
    meili_index.update_sortable_attributes(['clicks'])  # 允许按点击量字段排序


def sync_search_data():
    """
    将 MySQL 中的网站数据全量同步到 Meilisearch 搜索引擎。

    接口路径：POST /api/admin/sync-search
    请求方法：POST
    功能描述：读取数据库中所有网站记录，批量写入 Meilisearch 索引，
              使搜索引擎数据与数据库保持一致。适合在数据库大批量更新后手动触发。
    参数：无
    返回：
        200 - 同步成功，包含同步数量
        500 - 同步失败
    """
    from models import Website # 确保你有这个模型
    sites = Website.query.all()  # 查询数据库中所有网站记录
    
    documents = []  # 准备要写入搜索引擎的文档列表
    for s in sites:
        documents.append({
            "id": s.id,          # 文档唯一标识，与数据库主键对应
            "name": s.name,      # 网站名称，用于全文搜索
            "url": s.url,        # 网站地址，用于全文搜索
            "clicks": s.clicks or 0  # 点击量，用于热度排序（None 时默认为 0）
        })
    
    meili_index.add_documents(documents)  # 批量写入 Meilisearch（已存在则更新，不存在则新增）
    return jsonify({"message": f"成功同步 {len(documents)} 个网站到搜索引擎！"})

# --- 无感刷新 Token 接口 ---
@app.route('/api/refresh', methods=['POST', 'OPTIONS'])
def refresh():
    """
    无感刷新 Access Token 接口。

    接口路径：POST /api/refresh
    请求方法：POST（OPTIONS 用于跨域预检）
    功能描述：使用有效的 Refresh Token 换取新的 Access Token，
              实现用户登录状态的无感续期，无需重新输入密码。
    请求头：Authorization: Bearer <refresh_token>
    返回：
        200 - 新的 access_token
        401 - Refresh Token 无效或已过期
    """
    if request.method == 'OPTIONS':
        return jsonify({"message": "OK"}), 200  # 直接放行跨域预检请求
    
    # 注意这里：验证的是 refresh_token
    verify_jwt_in_request(refresh=True)  # 明确指定验证 Refresh Token 而非 Access Token
    
    # 获取当前用户 ID，签发新的 access_token
    current_user = get_jwt_identity()  # 从 Refresh Token 中提取用户身份标识
    current_claims = get_jwt()
    new_token = create_access_token(
        identity=current_user,
        additional_claims={
            "session_version": int(current_claims.get("session_version") or 0)
        },
    )  # 签发新的 Access Token
    
    return jsonify(access_token=new_token), 200

@app.route('/api/nav-data', methods=['GET'])
def get_nav_data():
    """
    获取导航页完整数据（分类 + 网站列表）。

    接口路径：GET /api/nav-data
    请求方法：GET
    功能描述：从数据库查询所有分类及其下属网站，按前端所需的嵌套结构返回。
    参数：无
    返回：
        200 - 分类列表，每个分类包含 id、name 和 sites 数组
              sites 数组中每个元素包含 id、category_id、name、url、logo_url、clicks
    """
    # 直接查库，并按照你的前端所需格式组装
    categories = Category.query.all()  # 查询所有分类
    result = []  # 最终返回的数据列表
    for cat in categories:
        cat_data = {
            "id": cat.id,       # 分类 ID
            "name": cat.name,   # 分类名称
            "sites": []         # 该分类下的网站列表（初始为空，下方循环填充）
        }
        # 假设 Category 和 Website 有一对多关联 (backref='category')
        for site in cat.websites:  # 遍历该分类下的所有网站（利用 ORM 关联关系）
            cat_data["sites"].append({
                "id": site.id,                    # 网站 ID
                "category_id": site.category_id,  # 所属分类 ID
                "name": site.name,                # 网站名称
                "url": site.url,                  # 网站地址
                "logo_url": site.logo_url,        # 网站图标 URL
                "clicks": site.clicks             # 累计点击量
            })
        result.append(cat_data)
        
    return jsonify(result), 200

# ===== 定时任务配置 =====
# 配置并启动定时任务
scheduler = APScheduler()       # 创建 APScheduler 调度器实例
scheduler.init_app(app)         # 将调度器与 Flask 应用绑定

# 设定触发器：每天凌晨 3:00 自动执行一次
@scheduler.task('cron', id='do_hn_spider', hour=3, minute=0)
def scheduled_spider_task():
    """
    定时爬虫任务（每天凌晨 3:00 自动触发）。

    功能描述：在服务器低峰期自动调用 Hacker News 爬虫，
              将新发现的热门站点写入待审核队列，供管理员次日审核。
    触发方式：cron 定时，每天 03:00 执行
    """
    auto_fetch_hacker_news()  # 调用爬虫函数，抓取 HN 热门站点

# ================= 4. 垂直资讯流聚合 (RSS 穿透防火墙版) =================
@app.route('/api/news', methods=['GET'])
def get_industry_news():
    """
    获取行业资讯列表（RSS 聚合接口）。

    接口路径：GET /api/news
    请求方法：GET
    功能描述：根据职业方向参数，从 V2EX 对应的 RSS 订阅源抓取最新文章，
              通过本地代理穿透网络限制，返回最新的 8 条资讯。
    参数：
        prof (str, 可选): 职业方向筛选，可选值：
            - 'frontend' 前端开发（程序员节点）
            - 'product'  产品经理（创意节点）
            - 'ui'       UI 设计（设计节点）
            - 'all'      全部（默认，V2EX 首页）
    返回：
        200 - 资讯列表，每条包含 title（标题）、link（链接）、source（来源）
        500 - 抓取失败，包含错误信息
    """
    prof = request.args.get('prof', 'all')  # 获取职业方向参数，默认为 'all'
    
    # RSS 订阅源映射表：职业方向 -> V2EX 对应节点的 RSS 地址
    rss_map = {
        'frontend': 'https://v2ex.com/feed/programmer.xml',  # 程序员节点
        'product': 'https://v2ex.com/feed/create.xml',       # 创意/产品节点
        'ui': 'https://v2ex.com/feed/design.xml',            # 设计节点
        'all': 'https://v2ex.com/index.xml'                  # V2EX 全站首页
    }
    
    url = rss_map.get(prof, rss_map['all'])  # 根据参数选择对应的 RSS 地址，未知参数则回退到全站
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        # 不使用代理，直接请求（若需代理请自行开启系统代理）
        try:
            response = requests.get(url, headers=headers, timeout=8)
            response.raise_for_status()
            xml_data = response.text
        except Exception:
            # 外部 RSS 请求失败时，直接返回空列表而不是 500，避免前端报错
            return jsonify([]), 200
        
        feed = feedparser.parse(xml_data)
        
        news_list = []
        entries = getattr(feed, 'entries', []) or []
        for entry in entries[:8]:
            news_list.append({
                'title': getattr(entry, 'title', ''),
                'link': getattr(entry, 'link', ''),
                'source': getattr(getattr(feed, 'feed', None), 'title', '行业快讯') if getattr(feed, 'feed', None) else '行业快讯'
            })
            
        return jsonify(news_list), 200
    except Exception as e:
        return jsonify([]), 200
# ================= 爬虫手动测试接口 =================
@app.route('/api/admin/run-spider', methods=['POST'])
@admin_role_required
def trigger_spider_manually():
    """
    手动触发 Hacker News 爬虫接口（管理员专用）。

    接口路径：POST /api/admin/run-spider
    请求方法：POST
    功能描述：同步执行 Hacker News 爬虫，将抓取到的新站点写入待审核队列。
              注意：此接口为同步调用，爬虫执行期间会阻塞响应。
              生产环境建议改为异步队列（如 Celery）处理。
    参数：无
    返回：
        200 - 爬虫执行完毕的提示信息
    """
    # 为了演示直接同步调用。在生产环境中，耗时爬虫建议扔给 Celery 等异步队列
    auto_fetch_hacker_news(app)  # 传入 app 实例以便在爬虫内部使用应用上下文
    return jsonify({"message": "✅ 爬虫执行完毕！快去前端的【审核工作台】看看有没有新货吧！"})

# ================= 1. 模拟数据库 (保持不变) =================
# 内存中的分类数据，作为静态备用数据（真实数据从 MySQL 读取）
categories_db = [
    # 字段说明：id - 分类唯一标识，name - 分类显示名称
    {"id": 1, "name": "常用推荐"},
    {"id": 2, "name": "开发社区"},
    {"id": 3, "name": "摸鱼娱乐"},
    {"id": 4, "name": "实用工具"},
    {"id": 5, "name": "AI 神器"}
]

# 内存中的网站数据，作为静态备用数据（真实数据从 MySQL 读取）
# 字段说明：
#   id          - 网站唯一标识
#   category_id - 所属分类 ID（对应 categories_db 中的 id）
#   name        - 网站显示名称
#   url         - 网站访问地址
#   logo_url    - 网站图标地址（空字符串表示待抓取）
#   clicks      - 累计点击量（用于热度排序）
websites_db = [
    # ===== 分类 1：常用推荐 =====
    {"id": 101, "category_id": 1, "name": "哔哩哔哩", "url": "https://www.bilibili.com", "logo_url": "", "clicks": 1250},
    {"id": 102, "category_id": 1, "name": "知乎", "url": "https://www.zhihu.com", "logo_url": "", "clicks": 856},
    {"id": 103, "category_id": 1, "name": "微博", "url": "https://weibo.com", "logo_url": "", "clicks": 720},
    {"id": 104, "category_id": 1, "name": "淘宝", "url": "https://www.taobao.com", "logo_url": "", "clicks": 1100},
    {"id": 105, "category_id": 1, "name": "京东", "url": "https://www.jd.com", "logo_url": "", "clicks": 980},
    {"id": 106, "category_id": 1, "name": "百度", "url": "https://www.baidu.com", "logo_url": "", "clicks": 2000},
    {"id": 107, "category_id": 1, "name": "腾讯视频", "url": "https://v.qq.com", "logo_url": "", "clicks": 650},
    {"id": 108, "category_id": 1, "name": "爱奇艺", "url": "https://www.iqiyi.com", "logo_url": "", "clicks": 600},
    {"id": 109, "category_id": 1, "name": "优酷", "url": "https://www.youku.com", "logo_url": "", "clicks": 480},
    {"id": 110, "category_id": 1, "name": "网易云音乐", "url": "https://music.163.com", "logo_url": "", "clicks": 870},
    {"id": 111, "category_id": 1, "name": "QQ音乐", "url": "https://y.qq.com", "logo_url": "", "clicks": 760},
    {"id": 112, "category_id": 1, "name": "天猫", "url": "https://www.tmall.com", "logo_url": "", "clicks": 890},
    {"id": 113, "category_id": 1, "name": "拼多多", "url": "https://www.pinduoduo.com", "logo_url": "", "clicks": 950},
    {"id": 114, "category_id": 1, "name": "12306", "url": "https://www.12306.cn", "logo_url": "", "clicks": 430},
    {"id": 115, "category_id": 1, "name": "高德地图", "url": "https://www.amap.com", "logo_url": "", "clicks": 560},

    # ===== 分类 2：开发社区 =====
    {"id": 201, "category_id": 2, "name": "GitHub", "url": "https://github.com", "logo_url": "", "clicks": 980},
    {"id": 202, "category_id": 2, "name": "GitLab", "url": "https://gitlab.com", "logo_url": "", "clicks": 420},
    {"id": 203, "category_id": 2, "name": "Gitee", "url": "https://gitee.com", "logo_url": "", "clicks": 380},
    {"id": 204, "category_id": 2, "name": "掘金", "url": "https://juejin.cn", "logo_url": "", "clicks": 430},
    {"id": 205, "category_id": 2, "name": "CSDN", "url": "https://www.csdn.net", "logo_url": "", "clicks": 560},
    {"id": 206, "category_id": 2, "name": "博客园", "url": "https://www.cnblogs.com", "logo_url": "", "clicks": 310},
    {"id": 207, "category_id": 2, "name": "Stack Overflow", "url": "https://stackoverflow.com", "logo_url": "", "clicks": 670},
    {"id": 208, "category_id": 2, "name": "MDN Web Docs", "url": "https://developer.mozilla.org", "logo_url": "", "clicks": 590},
    {"id": 209, "category_id": 2, "name": "npm", "url": "https://www.npmjs.com", "logo_url": "", "clicks": 480},
    {"id": 210, "category_id": 2, "name": "Docker Hub", "url": "https://hub.docker.com", "logo_url": "", "clicks": 350},
    {"id": 211, "category_id": 2, "name": "LeetCode", "url": "https://leetcode.cn", "logo_url": "", "clicks": 720},
    {"id": 212, "category_id": 2, "name": "牛客网", "url": "https://www.nowcoder.com", "logo_url": "", "clicks": 540},
    {"id": 213, "category_id": 2, "name": "V2EX", "url": "https://www.v2ex.com", "logo_url": "", "clicks": 390},
    {"id": 214, "category_id": 2, "name": "SegmentFault", "url": "https://segmentfault.com", "logo_url": "", "clicks": 280},
    {"id": 215, "category_id": 2, "name": "Vercel", "url": "https://vercel.com", "logo_url": "", "clicks": 460},

    # ===== 分类 3：摸鱼娱乐 =====
    {"id": 301, "category_id": 3, "name": "抖音", "url": "https://www.douyin.com", "logo_url": "", "clicks": 520},
    {"id": 302, "category_id": 3, "name": "小红书", "url": "https://www.xiaohongshu.com", "logo_url": "", "clicks": 480},
    {"id": 303, "category_id": 3, "name": "微信读书", "url": "https://weread.qq.com", "logo_url": "", "clicks": 320},
    {"id": 304, "category_id": 3, "name": "豆瓣", "url": "https://www.douban.com", "logo_url": "", "clicks": 410},
    {"id": 305, "category_id": 3, "name": "虎扑", "url": "https://www.hupu.com", "logo_url": "", "clicks": 290},
    {"id": 306, "category_id": 3, "name": "NGA玩家社区", "url": "https://nga.178.com", "logo_url": "", "clicks": 260},
    {"id": 307, "category_id": 3, "name": "Steam", "url": "https://store.steampowered.com", "logo_url": "", "clicks": 680},
    {"id": 308, "category_id": 3, "name": "Epic Games", "url": "https://www.epicgames.com", "logo_url": "", "clicks": 350},
    {"id": 309, "category_id": 3, "name": "网易游戏", "url": "https://game.163.com", "logo_url": "", "clicks": 420},
    {"id": 310, "category_id": 3, "name": "腾讯游戏", "url": "https://game.qq.com", "logo_url": "", "clicks": 510},
    {"id": 311, "category_id": 3, "name": "漫画柜", "url": "https://www.manhuagui.com", "logo_url": "", "clicks": 230},
    {"id": 312, "category_id": 3, "name": "哔哩哔哩漫画", "url": "https://manga.bilibili.com", "logo_url": "", "clicks": 280},
    {"id": 313, "category_id": 3, "name": "网易新闻", "url": "https://news.163.com", "logo_url": "", "clicks": 370},
    {"id": 314, "category_id": 3, "name": "今日头条", "url": "https://www.toutiao.com", "logo_url": "", "clicks": 440},
    {"id": 315, "category_id": 3, "name": "虎嗅", "url": "https://www.huxiu.com", "logo_url": "", "clicks": 310},

    # ===== 分类 4：实用工具 =====
    {"id": 401, "category_id": 4, "name": "ProcessOn", "url": "https://www.processon.com", "logo_url": "", "clicks": 380},
    {"id": 402, "category_id": 4, "name": "Excalidraw", "url": "https://excalidraw.com", "logo_url": "", "clicks": 290},
    {"id": 403, "category_id": 4, "name": "TinyPNG", "url": "https://tinypng.com", "logo_url": "", "clicks": 450},
    {"id": 404, "category_id": 4, "name": "Squoosh", "url": "https://squoosh.app", "logo_url": "", "clicks": 220},
    {"id": 405, "category_id": 4, "name": "Carbon", "url": "https://carbon.now.sh", "logo_url": "", "clicks": 310},
    {"id": 406, "category_id": 4, "name": "Regex101", "url": "https://regex101.com", "logo_url": "", "clicks": 340},
    {"id": 407, "category_id": 4, "name": "JSON格式化", "url": "https://jsonformatter.curiousconcept.com", "logo_url": "", "clicks": 280},
    {"id": 408, "category_id": 4, "name": "Can I Use", "url": "https://caniuse.com", "logo_url": "", "clicks": 390},
    {"id": 409, "category_id": 4, "name": "Notion", "url": "https://www.notion.so", "logo_url": "", "clicks": 620},
    {"id": 410, "category_id": 4, "name": "飞书", "url": "https://www.feishu.cn", "logo_url": "", "clicks": 540},
    {"id": 411, "category_id": 4, "name": "腾讯文档", "url": "https://docs.qq.com", "logo_url": "", "clicks": 480},
    {"id": 412, "category_id": 4, "name": "石墨文档", "url": "https://shimo.im", "logo_url": "", "clicks": 320},
    {"id": 413, "category_id": 4, "name": "百度翻译", "url": "https://fanyi.baidu.com", "logo_url": "", "clicks": 560},
    {"id": 414, "category_id": 4, "name": "DeepL翻译", "url": "https://www.deepl.com", "logo_url": "", "clicks": 490},
    {"id": 415, "category_id": 4, "name": "Cloudflare", "url": "https://www.cloudflare.com", "logo_url": "", "clicks": 270},
    {"id": 416, "category_id": 4, "name": "iLovePDF", "url": "https://www.ilovepdf.com", "logo_url": "", "clicks": 350},
    {"id": 417, "category_id": 4, "name": "Convertio", "url": "https://convertio.co", "logo_url": "", "clicks": 300},
    {"id": 418, "category_id": 4, "name": "Unsplash", "url": "https://unsplash.com", "logo_url": "", "clicks": 410},

    # ===== 分类 5：AI 神器 =====
    {"id": 501, "category_id": 5, "name": "ChatGPT", "url": "https://chat.openai.com", "logo_url": "", "clicks": 760},
    {"id": 502, "category_id": 5, "name": "Claude", "url": "https://claude.ai", "logo_url": "", "clicks": 580},
    {"id": 503, "category_id": 5, "name": "Gemini", "url": "https://gemini.google.com", "logo_url": "", "clicks": 490},
    {"id": 504, "category_id": 5, "name": "文心一言", "url": "https://yiyan.baidu.com", "logo_url": "", "clicks": 420},
    {"id": 505, "category_id": 5, "name": "通义千问", "url": "https://tongyi.aliyun.com", "logo_url": "", "clicks": 380},
    {"id": 506, "category_id": 5, "name": "讯飞星火", "url": "https://xinghuo.xfyun.cn", "logo_url": "", "clicks": 310},
    {"id": 507, "category_id": 5, "name": "Kimi", "url": "https://kimi.moonshot.cn", "logo_url": "", "clicks": 450},
    {"id": 508, "category_id": 5, "name": "豆包", "url": "https://www.doubao.com", "logo_url": "", "clicks": 390},
    {"id": 509, "category_id": 5, "name": "Midjourney", "url": "https://www.midjourney.com", "logo_url": "", "clicks": 520},
    {"id": 510, "category_id": 5, "name": "Stable Diffusion", "url": "https://stability.ai", "logo_url": "", "clicks": 340},
    {"id": 511, "category_id": 5, "name": "Runway", "url": "https://runwayml.com", "logo_url": "", "clicks": 280},
    {"id": 512, "category_id": 5, "name": "Suno AI", "url": "https://suno.ai", "logo_url": "", "clicks": 360},
    {"id": 513, "category_id": 5, "name": "GitHub Copilot", "url": "https://github.com/features/copilot", "logo_url": "", "clicks": 470},
    {"id": 514, "category_id": 5, "name": "Cursor", "url": "https://www.cursor.com", "logo_url": "", "clicks": 530},
    {"id": 515, "category_id": 5, "name": "Perplexity", "url": "https://www.perplexity.ai", "logo_url": "", "clicks": 410},
    {"id": 516, "category_id": 5, "name": "Hugging Face", "url": "https://huggingface.co", "logo_url": "", "clicks": 350},
    {"id": 517, "category_id": 5, "name": "DeepSeek", "url": "https://www.deepseek.com", "logo_url": "", "clicks": 620},
    {"id": 518, "category_id": 5, "name": "智谱清言", "url": "https://chatglm.cn", "logo_url": "", "clicks": 290},
]

@app.route('/go/<int:item_id>')
def redirect_to_item(item_id):
    # (粘贴上一轮提供的 redirect_to_item 函数内部代码)
    ...

# ================= 3. 排行榜 API 接口 =================
@app.route('/api/ranking/growth', methods=['GET'])
def get_growth_ranking():
    try:
        # 1. 优先尝试从 Redis 缓存读取
        try:
            cached_data = redis_client.get("leaderboard:growth_rate")
            if cached_data:
                # 必须要有 return，把数据打包发给前端
                return jsonify({"code": 0, "data": json.loads(cached_data)})
        except Exception as redis_e:
            print(f"Redis 缓存读取失败，准备直接查数据库: {redis_e}")

        # 2. 如果缓存没有，或者 Redis 没开，就现场计算一次
        fresh_data = calculate_and_cache_growth_rate()
        
        # 必须要有 return，把新鲜出炉的数据发给前端
        return jsonify({"code": 0, "data": fresh_data})

    except Exception as e:
        print(f"排行榜接口发生严重崩溃: {e}")
        # 3. 终极兜底：就算天塌下来，也要给前端返回一个空数组，绝对不能不写 return！
        return jsonify({"code": 0, "data": []})
    
# ================= 🔒 受保护的管理后台路由示例 =================

@app.route('/api/admin/dashboard', methods=['GET'])
@admin_role_required
@jwt_required() # ✨ 这个装饰器要求请求头必须带 Authorization: Bearer <access_token>
def admin_dashboard():
    week_ago = datetime.utcnow() - timedelta(days=7)
    total_users = User.query.filter(User.deleted_at.is_(None)).count()
    new_users = User.query.filter(
        User.deleted_at.is_(None),
        User.created_at >= week_ago,
    ).count()
    total_sites = Website.query.filter(Website.status != "deleted").count()
    total_categories = Category.query.filter(Category.status != "deleted").count()
    total_tags = Tag.query.count()
    total_clicks = (
        db.session.query(func.coalesce(func.sum(Website.click_count), 0)).scalar()
        or 0
    )
    total_favorites = (
        db.session.query(func.coalesce(func.sum(Website.favorite_count), 0)).scalar()
        or 0
    )

    click_ranking = [
        {
            "id": site.id,
            "name": site.name,
            "click_count": site.click_count or site.clicks or 0,
        }
        for site in Website.query.filter(Website.status != "deleted")
        .order_by(Website.click_count.desc())
        .limit(8)
        .all()
    ]
    favorite_ranking = [
        {
            "id": site.id,
            "name": site.name,
            "favorite_count": site.favorite_count or 0,
        }
        for site in Website.query.filter(Website.status != "deleted")
        .order_by(Website.favorite_count.desc())
        .limit(8)
        .all()
    ]
    occupation_distribution = [
        {"occupation": row[0] or "未填写", "count": row[1]}
        for row in db.session.query(UserProfile.occupation, func.count(UserProfile.id))
        .group_by(UserProfile.occupation)
        .order_by(func.count(UserProfile.id).desc())
        .limit(8)
        .all()
    ]
    category_visit_ranking = [
        {
            "id": row[0],
            "name": row[1] or "未分类",
            "visit_count": int(row[2] or 0),
        }
        for row in db.session.query(
            Category.id,
            Category.name,
            func.coalesce(func.sum(Website.click_count), 0),
        )
        .outerjoin(Website, Website.category_id == Category.id)
        .filter(Category.status != "deleted")
        .group_by(Category.id, Category.name)
        .order_by(func.coalesce(func.sum(Website.click_count), 0).desc())
        .limit(8)
        .all()
    ]

    return jsonify(
        {
            "code": 0,
            "msg": "success",
            "data": {
                "stats": {
                    "users": total_users,
                    "new_users": new_users,
                    "sites": total_sites,
                    "categories": total_categories,
                    "tags": total_tags,
                    "total_clicks": int(total_clicks),
                    "total_favorites": int(total_favorites),
                },
                "click_ranking": click_ranking,
                "favorite_ranking": favorite_ranking,
                "occupation_distribution": occupation_distribution,
                "category_visit_ranking": category_visit_ranking,
            },
        }
    ), 200
    """
    管理后台首页数据接口（需要 JWT 认证）。

    接口路径：GET /api/admin/dashboard
    请求方法：GET
    功能描述：验证 JWT Access Token 后，返回当前登录管理员的欢迎信息和后台统计数据。
    请求头：Authorization: Bearer <access_token>
    返回：
        200 - 欢迎信息和后台数据
        401 - 未提供 Token 或 Token 无效
    """
    # 只有合法用户能走到这一步
    current_user_id = get_jwt_identity()          # 从 Token 中提取用户 ID
    user = User.query.get(current_user_id)         # 根据 ID 查询用户详情
    
    return jsonify({
        "message": f"欢迎尊贵的管理员 {user.username}！",
        "secret_data": "这是只有登录用户才能看到的后台数据统计。"
    }), 200
# ================= 2. 基础 API 路由 (保持不变) =================

@app.route('/api/data', methods=['GET'])
def get_data():
    """
    获取内存中的静态导航数据（备用接口）。

    接口路径：GET /api/data
    请求方法：GET
    功能描述：直接返回内存中预置的 categories_db 和 websites_db 静态数据，
              不查询数据库，适合在数据库不可用时作为降级方案。
    参数：无
    返回：
        200 - 包含 categories（分类列表）和 websites（网站列表）的 JSON 对象
    """
    return jsonify({"categories": categories_db, "websites": websites_db})

# ================= 1. 自动抓取 Hacker News 热门站点 (SQLAlchemy 版) =================
@app.route('/api/admin/crawl_hn', methods=['POST'])
@admin_role_required
def crawl_hacker_news():
    """
    手动触发 Hacker News 热门站点抓取接口（管理员专用）。

    接口路径：POST /api/admin/crawl_hn
    请求方法：POST
    功能描述：调用 Hacker News Firebase API 获取当前最热的 30 篇文章，
              提取其中包含外链 URL 的文章，去重后写入 pending_sites 待审核表。
              已存在于正式表或待审核表中的 URL 会被跳过，避免重复录入。
    参数：无
    返回：
        200 - 抓取完成，包含新发现的站点数量
        500 - 抓取过程中发生异常
    """
    try:
        request_options = {"proxies": get_outbound_proxies(), "timeout": 10}
        # 获取 HN 最热的 30 篇文章 ID
        top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        story_ids = requests.get(top_stories_url, **request_options).json()[:30]  # 只取前 30 条热门文章 ID
        
        added_count = 0  # 记录本次新增的待审核站点数量
        
        for story_id in story_ids:
            story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
            story_info = requests.get(story_url, **request_options).json()  # 获取文章详情
            
            if story_info and 'url' in story_info:  # 只处理包含外链的文章（排除纯讨论帖）
                url = story_info['url']
                title = story_info.get('title', '未知站点')
                
                # 查重 1：检查待审核表
                is_in_pending = db.session.execute(text("SELECT id FROM pending_sites WHERE url = :url"), {'url': url}).fetchone()
                
                # ✨ 完美融合：直接用你现成的 Website 模型去正式表里查重！
                is_in_sites = Website.query.filter_by(url=url).first()
                
                if not is_in_pending and not is_in_sites:  # 两张表都没有才写入
                    # 写入待审核库
                    db.session.execute(
                        text("INSERT INTO pending_sites (name, url, description, source) VALUES (:name, :url, :desc, :source)"),
                        {'name': title, 'url': url, 'desc': title, 'source': 'Hacker News'}
                    )
                    added_count += 1
        
        db.session.commit()  # 批量提交所有插入操作
        return jsonify({'message': f'抓取完成！成功发现 {added_count} 个新站点待审核。'}), 200
    except Exception as e:
        db.session.rollback()  # 发生异常时回滚事务，保证数据一致性
        return jsonify({'error': str(e)}), 500

# ================= 2. 获取待审核站点列表 =================
@app.route('/api/admin/pending_sites', methods=['GET'])
@admin_role_required
def get_pending_sites():
    """
    获取待审核站点列表接口（管理员专用）。

    接口路径：GET /api/admin/pending_sites
    请求方法：GET
    功能描述：查询 pending_sites 表中状态为 'pending' 的站点，
              按创建时间倒序排列，供管理员在审核工作台中逐一审核。
    参数：无
    返回：
        200 - 待审核站点列表，每条包含 id、name、url、description、source
        500 - 数据库查询异常
    """
    try:
        result = db.session.execute(text("SELECT id, name, url, description, source FROM pending_sites WHERE status = 'pending' ORDER BY created_at DESC"))
        sites = []  # 存储格式化后的站点列表
        for row in result:
            sites.append({
                'id': row[0],           # 待审核记录 ID
                'name': row[1],         # 站点名称
                'url': row[2],          # 站点地址
                'description': row[3],  # 站点描述
                'source': row[4]        # 数据来源（如 'Hacker News'）
            })
        return jsonify(sites), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================= 3. 审核操作 (通过 或 拒绝) =================
@app.route('/api/admin/review_site', methods=['POST'])
@admin_role_required
def review_site():
    """
    审核待审核站点接口（管理员专用）。

    接口路径：POST /api/admin/review_site
    请求方法：POST
    功能描述：对待审核站点执行通过或拒绝操作。
              - 通过（approve）：将站点从 pending_sites 迁移到正式 websites 表，并更新待审核状态为 'approved'
              - 拒绝（reject）：仅将待审核状态更新为 'rejected'，不写入正式表
    请求体（JSON）：
        id          (int): 待审核站点的 ID
        action      (str): 操作类型，'approve' 通过 或 'reject' 拒绝
        category_id (int, 可选): 通过时指定的分类 ID，默认为 1（常用推荐）
    返回：
        200 - 审核操作成功
        500 - 数据库操作异常
    """
    data = request.json
    site_id = data.get('id')           # 待审核站点 ID
    action = data.get('action')        # 审核操作：'approve' 或 'reject'
    category_id = data.get('category_id', 1)  # 通过时的目标分类，默认归入"常用推荐"
    
    try:
        if action == 'approve':
            # 1. 查出待审核数据
            site_row = db.session.execute(text("SELECT name, url, description FROM pending_sites WHERE id = :id"), {'id': site_id}).fetchone()
            if site_row:
                # ✨ 完美融合：直接实例化你的 Website 模型，让它按照你的规则生成数据！
                new_site = Website(name=site_row[0], url=site_row[1], category_id=category_id)  # 创建正式网站记录
                db.session.add(new_site)
                
                # 更新待审核表状态
                db.session.execute(text("UPDATE pending_sites SET status = 'approved' WHERE id = :id"), {'id': site_id})
        
        elif action == 'reject':
            db.session.execute(text("UPDATE pending_sites SET status = 'rejected' WHERE id = :id"), {'id': site_id})  # 标记为已拒绝
            
        db.session.commit()  # 提交事务
        return jsonify({'message': '审核操作成功'}), 200
    except Exception as e:
        db.session.rollback()  # 异常时回滚，保证数据一致性
        return jsonify({'error': str(e)}), 500
# backend/app.py
# ✨ 1. 全网基础热度（保持不变）
# 各网站的基础热度权重，基于全网真实流量数据预估
# 用于在实时热度为 0 时提供兜底排序依据，防止冷启动时排行榜为空
BASE_HOTNESS = {
    # 常用推荐
    "百度": 200000, "哔哩哔哩": 50000, "知乎": 30000, "微博": 45000,
    "淘宝": 80000, "京东": 70000, "腾讯视频": 35000, "爱奇艺": 32000,
    "优酷": 20000, "网易云音乐": 40000, "QQ音乐": 38000, "天猫": 65000,
    "拼多多": 55000, "12306": 18000, "高德地图": 22000,
    # 开发社区
    "GitHub": 25000, "GitLab": 8000, "Gitee": 7000, "掘金": 10000,
    "CSDN": 15000, "博客园": 6000, "Stack Overflow": 18000, "MDN Web Docs": 12000,
    "npm": 9000, "Docker Hub": 7500, "LeetCode": 20000, "牛客网": 14000,
    "V2EX": 8500, "SegmentFault": 5000, "Vercel": 9500,
    # 摸鱼娱乐
    "抖音": 80000, "小红书": 42000, "微信读书": 15000, "豆瓣": 18000,
    "虎扑": 12000, "NGA玩家社区": 10000, "Steam": 28000, "Epic Games": 14000,
    "网易游戏": 17000, "腾讯游戏": 22000, "漫画柜": 8000, "哔哩哔哩漫画": 9000,
    "网易新闻": 16000, "今日头条": 35000, "虎嗅": 11000,
    # 实用工具
    "Notion": 25000, "飞书": 20000, "腾讯文档": 18000, "石墨文档": 10000,
    "百度翻译": 22000, "DeepL翻译": 19000, "TinyPNG": 12000, "Can I Use": 9000,
    "Regex101": 8000, "Carbon": 7000, "ProcessOn": 11000, "Unsplash": 13000,
    # AI 神器
    "ChatGPT": 60000, "Claude": 35000, "Gemini": 28000, "文心一言": 20000,
    "通义千问": 18000, "讯飞星火": 14000, "Kimi": 22000, "豆包": 19000,
    "Midjourney": 26000, "DeepSeek": 30000, "GitHub Copilot": 21000,
    "Cursor": 24000, "Perplexity": 16000, "Hugging Face": 13000,
    "Suno AI": 12000, "Runway": 10000, "智谱清言": 9000, "Stable Diffusion": 11000,
}

# ===== 热度缓存：存储上一次抓取的各网站热度，用于计算涨跌率 =====
_hotness_cache = {}       # 格式：{网站名: 上次热度分数}，用于计算热度涨跌幅
_hotness_cache_time = {}  # 格式：{网站名: 上次更新时间戳}，用于判断缓存是否过期


def fetch_online_hotness():
    """
    从多个公开热榜 API 抓取各网站的实时热度分数。

    数据来源（共 7 个）：
      1. 微博实时热搜 - 累加热搜词条热度值
      2. 知乎热榜     - 累加热榜条目热度（万热度单位转换）
      3. 百度实时热搜 - 累加热搜词条热度分
      4. 今日头条热榜 - 累加热榜条目热度值
      5. GitHub Trending - 今日 Star 增量（×10 放大）
      6. 哔哩哔哩热门 - 累加热门视频播放量
      7. 抖音热榜     - 累加热搜词条热度值

    返回：
        dict: {网站名(str): 实时热度分数(int)}，
              未能成功抓取的网站不会出现在返回字典中
    """
    global _hotness_cache
    # 1. 获取当前数据库中所有真实的网站 name (或 ID)
    current_site_names = {site.name for site in Website.query.all()}
    
    # 2. 清理：只保留存在于当前数据库中的网站热度数据
    _hotness_cache = {name: data for name, data in _hotness_cache.items() if name in current_site_names}  # 过滤已删除的网站缓存
    hotness = {}  # 本次抓取的热度结果字典
    hdrs = {
        # 模拟浏览器 User-Agent，避免被反爬机制拦截
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
    }
    # 源1：微博实时热搜
    try:
        r = requests.get('https://weibo.com/ajax/side/hotSearch',
            headers={**hdrs, 'Referer': 'https://weibo.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', {}).get('realtime', [])
            hotness['微博'] = sum(int(x.get('num', 0)) for x in items[:50])  # 累加前 50 条热搜词条的热度值
    except Exception:
        pass  # 抓取失败时静默跳过，不影响其他数据源
    # 源2：知乎热榜
    try:
        r = requests.get('https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50',
            headers={**hdrs, 'Referer': 'https://www.zhihu.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', [])
            total = 0
            for item in items:
                raw = item.get('detail_text', '0').replace('万热度', '').replace('万', '')  # 去除"万热度"单位文字
                try:
                    total += int(float(raw) * 10000)  # 将"万"单位转换为实际数值
                except Exception:
                    total += 5000  # 解析失败时使用默认值 5000
            hotness['知乎'] = total
    except Exception:
        pass
    # 源3：百度实时热搜
    try:
        r = requests.get('https://top.baidu.com/api/board?platform=wise&tab=realtime',
            headers={**hdrs, 'Referer': 'https://top.baidu.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', {}).get('cards', [{}])[0].get('content', [])
            hotness['百度'] = sum(int(x.get('hotScore', 0)) for x in items[:30])  # 累加前 30 条热搜的热度分
    except Exception:
        pass
    # 源4：今日头条热榜
    try:
        r = requests.get('https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc',
            headers={**hdrs, 'Referer': 'https://www.toutiao.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', [])
            hotness['今日头条'] = sum(int(x.get('HotValue', 0)) for x in items[:30])  # 累加前 30 条热榜的热度值
    except Exception:
        pass
    # 源5：GitHub Trending 今日 Star 增量
    try:
        r = requests.get('https://api.gitterapp.com/repositories?since=daily',
            headers=hdrs, timeout=6)
        if r.status_code == 200:
            repos = r.json()
            hotness['GitHub'] = sum(int(x.get('stars', 0)) for x in repos[:25]) * 10  # Star 数 ×10 放大，与其他平台热度量级对齐
    except Exception:
        pass
    # 源6：哔哩哔哩热门视频播放量
    try:
        r = requests.get('https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all',
            headers={**hdrs, 'Referer': 'https://www.bilibili.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', {}).get('list', [])
            hotness['哔哩哔哩'] = sum(int(x.get('stat', {}).get('view', 0)) for x in items[:20])  # 累加前 20 个热门视频的播放量
    except Exception:
        pass
    # 源7：抖音热榜
    try:
        r = requests.get('https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/',
            headers={**hdrs, 'Referer': 'https://www.douyin.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('word_list', [])
            hotness['抖音'] = sum(int(x.get('hot_value', 0)) for x in items[:30])  # 累加前 30 条热搜词的热度值
    except Exception:
        pass
    return hotness  # 返回本次成功抓取的所有网站热度数据

# ================= 1. 发送安全验证码 (存入 Redis, 有效期5分钟) =================

@app.route('/api/security/send-email-code', methods=['POST'])
@jwt_required()
@limiter.limit("2 per minute") # 防止被别人恶意刷邮箱轰炸
def send_bind_email_code():
    email = request.json.get('email')
    if not email: return jsonify({'code': 400, 'msg': '邮箱不能为空'}), 400
    
    code = str(random.randint(100000, 999999))
    redis_client.setex(f"bind_email_code:{email}", 300, code) # Redis：300秒(5分钟)自动过期
    
    # 调用真实的 SMTP 发送逻辑
    is_success, error_msg = send_verification_email(email, code)
    if is_success:
        return jsonify({'code': 0, 'msg': '验证码已发送'})
    else:
        return jsonify({'code': 500, 'msg': f'邮件发送失败：{error_msg}'}), 500

@app.route('/api/security/send-sms-code', methods=['POST'])
@jwt_required()
@limiter.limit("1 per minute")
def send_bind_sms_code():
    phone = request.json.get('phone')
    if not phone: return jsonify({'code': 400, 'msg': '手机号不能为空'}), 400
    
    code = str(random.randint(100000, 999999))
    redis_client.setex(f"bind_phone_code:{phone}", 300, code) # Redis 存储
    
    # ⚠️ [真实短信 SDK 接入占位] 
    # 此处应接入阿里云(Dysmsapi)或腾讯云(SmsClient) SDK。示例逻辑如下：
    # client = AcsClient('你的AccessKey', '你的Secret', 'cn-hangzhou')
    # request = CommonRequest()
    # request.set_domain('dysmsapi.aliyuncs.com')
    # request.set_action_name('SendSms')
    # request.add_query_param('PhoneNumbers', phone)
    # request.add_query_param('SignName', "智汇导航")
    # request.add_query_param('TemplateCode', "SMS_123456789")
    # request.add_query_param('TemplateParam', f'{{"code":"{code}"}}')
    # response = client.do_action_with_exception(request)
    
    print(f"\n🚀 [国内短信服务模拟] 接收手机号: {phone} | 验证码: {code}\n")
    return jsonify({'code': 0, 'msg': '短信验证码已发送'})


# ================= 2. 严格校验验证码并绑定入库 =================

@app.route('/api/security/bind-email', methods=['POST'])
@jwt_required()
def submit_bind_email():
    username = get_jwt_identity() # 取出请求者的身份
    data = request.json
    email, code = data.get('email'), data.get('code')
    
    # 1. 查 Redis 对比验证码 (同时校验是否过期)
    saved_code = redis_client.get(f"bind_email_code:{email}")
    if not saved_code or saved_code != code:
        return jsonify({'code': 400, 'msg': '验证码错误或已过期(超5分钟)'}), 400

    # 2. 校验成功，写入 MySQL 更新资料
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET email = %s WHERE username = %s", (email, username))
        conn.commit()
        
        # 3. 销毁已使用过的验证码（防重放攻击）
        redis_client.delete(f"bind_email_code:{email}") 
        
        return jsonify({'code': 0, 'msg': '邮箱换绑成功'})
    except Exception as e:
        return jsonify({'code': 500, 'msg': '数据库写入失败'}), 500
    finally:
        conn.close()

@app.route('/api/security/bind-phone', methods=['POST'])
@jwt_required()
def submit_bind_phone():
    username = get_jwt_identity()
    data = request.json
    phone, code = data.get('phone'), data.get('code')
    
    saved_code = redis_client.get(f"bind_phone_code:{phone}")
    if not saved_code or saved_code != code:
        return jsonify({'code': 400, 'msg': '验证码错误或已过期(超5分钟)'}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET phone = %s WHERE username = %s", (phone, username))
        conn.commit()
        redis_client.delete(f"bind_phone_code:{phone}") 
        return jsonify({'code': 0, 'msg': '手机号绑定成功'})
    finally:
        conn.close()

# ================= 1. 上传/更新配置到云端 =================
@app.route('/api/user/sync', methods=['POST'])
@jwt_required()
def sync_user_settings():
    """
    同步用户个性化配置到云端接口（需要 JWT 认证）。

    接口路径：POST /api/user/sync
    请求方法：POST
    功能描述：将用户在前端修改的个性化配置（深色模式、壁纸、搜索引擎等）
              持久化保存到数据库，实现多设备配置同步。
              如果用户不存在则自动创建（兼容手机号模拟登录场景）。
    请求头：Authorization: Bearer <access_token>
    请求体（JSON，所有字段均为可选）：
        username         (str):  用户名（必填，用于查找用户）
        dark_mode        (bool): 是否启用深色模式
        custom_wallpaper (str):  自定义壁纸 URL
        current_engine   (str):  当前默认搜索引擎
        selected_engines (list): 已选择的搜索引擎列表（存储为 JSON 字符串）
        avatar_url       (str):  用户头像 URL
    返回：
        200 - 配置同步成功
        401 - 未提供用户名
    """
    data = request.json
    username = data.get('username')  # 从请求体获取用户名
    
    if not username:
        return jsonify({"error": "未登录"}), 401

    # 查找用户，如果没有就顺手创建一个（兼容你目前的手机号模拟登录逻辑）
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username)  # 用户不存在时自动创建
        db.session.add(user)

    # 同步各项配置（只更新请求体中包含的字段，未传的字段保持原值）
    if 'dark_mode' in data:
        user.dark_mode = data['dark_mode']           # 深色模式开关
    if 'custom_wallpaper' in data:
        user.custom_wallpaper = data['custom_wallpaper']  # 自定义壁纸
    if 'current_engine' in data:
        user.current_engine = data['current_engine']  # 当前搜索引擎
    if 'selected_engines' in data:
        user.selected_engines = json.dumps(data['selected_engines']) # 列表转为字符串存储
    if 'avatar_url' in data:
        user.avatar_url = data['avatar_url']          # 用户头像

    db.session.commit()  # 提交所有配置更新
    return jsonify({"success": True, "message": "配置已同步到云端 ☁️"})

# ================= 2. 登录时拉取云端配置 =================
@app.route('/api/user/settings', methods=['GET'])
def get_user_settings():
    """
    获取用户个性化配置接口。

    接口路径：GET /api/user/settings
    请求方法：GET
    功能描述：根据用户名从数据库读取用户的个性化配置，
              用于用户登录后恢复其在其他设备上保存的偏好设置。
    参数：
        username (str, 查询参数): 用户名，必填
    返回：
        200 - 用户配置对象，包含 dark_mode、custom_wallpaper、
              current_engine、selected_engines、avatar_url
        400 - 缺少用户名参数
        404 - 用户不存在
    """
    username = request.args.get('username')  # 从 URL 查询参数获取用户名
    
    if not username:
        return jsonify({"error": "缺少用户名"}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "找不到用户"}), 404

    return jsonify({
        "dark_mode": user.dark_mode,                                                          # 深色模式状态
        "custom_wallpaper": user.custom_wallpaper,                                            # 自定义壁纸 URL
        "current_engine": user.current_engine,                                                # 当前搜索引擎
        "selected_engines": json.loads(user.selected_engines) if user.selected_engines else None,  # JSON 字符串反序列化为列表
        "avatar_url": user.avatar_url                                                         # 用户头像 URL
    })

@app.route('/api/ranking', methods=['GET'])
def get_ranking():
    """
    获取网站实时热度排行榜接口。

    接口路径：GET /api/ranking
    请求方法：GET
    功能描述：从多个公开热榜 API 抓取实时热度数据，结合数据库中的网站列表，
              计算每个网站的热度分数、涨跌量和涨跌率，返回综合排名前 10 的网站。
              排序规则：先按涨跌率绝对值（热度变化最大的排前面），再按综合热度分排序。
    参数：无
    返回：
        200 - 排行榜列表（最多 10 条），每条包含：
              id          - 网站 ID
              name        - 网站名称
              url         - 网站地址
              clicks      - 当前实时热度分数
              delta       - 与上次相比的热度变化量
              growth_rate - 热度涨跌率（百分比）
              sort_score  - 综合排序分（实时热度 + 基础热度权重）
        500 - 抓取或计算过程中发生异常
    """
    global _hotness_cache, _hotness_cache_time
    try:
        current = fetch_online_hotness()  # 抓取本次实时热度数据
        ranking_data = []                 # 存储排行榜数据
        all_sites_db = Website.query.all()  # 查询数据库中所有网站
        for site in all_sites_db:
            name = site.name
            cur_score = current.get(name, 0)   # 本次抓取的热度分，未抓到则为 0
            last_score = _hotness_cache.get(name, 0)  # 上次缓存的热度分，首次为 0
            if last_score > 0 and cur_score > 0:
                rate = round((cur_score - last_score) / last_score * 100, 1)  # 计算涨跌率（百分比，保留1位小数）
            elif cur_score > 0 and last_score == 0:
                rate = 100.0  # 首次出现热度数据，视为 100% 增长
            else:
                rate = 0.0    # 无热度数据时涨跌率为 0
            delta = cur_score - last_score  # 热度变化绝对值
            base = BASE_HOTNESS.get(name, 0)  # 从基础热度表获取该网站的权重
            sort_score = cur_score + base // 100  # 综合排序分 = 实时热度 + 基础热度的 1%（避免基础热度过度影响排名）
            ranking_data.append({
                'id': site.id,
                'name': name,
                'url': site.url,
                'clicks': cur_score,       # 当前实时热度分数
                'delta': delta,            # 热度变化量
                'growth_rate': rate,       # 涨跌率（%）
                'sort_score': sort_score,  # 综合排序分
            })
        for name, score in current.items():
            _hotness_cache[name] = score           # 更新热度缓存
            _hotness_cache_time[name] = time.time()  # 记录缓存更新时间
        ranking_data.sort(key=lambda x: (abs(x['growth_rate']), x['sort_score']), reverse=True)  # 先按涨跌率绝对值降序，再按综合分降序
        return jsonify(ranking_data[:10])  # 只返回前 10 名
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# --- 1. 用户发布内容 (存为草稿或提交审核) ---
@app.route('/api/articles', methods=['POST'])
@jwt_required()
def publish_article():
    user_id = get_jwt_identity() # 假设 token 里存的是 user_id
    data = request.json
    
    # 状态控制：前端传 'draft' 则是草稿，传 'pending' 则进入审核池
    status = data.get('status', 'draft') 
    
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO articles (user_id, title, cover_url, content, category, tags, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, data['title'], data['cover_url'], data['content'], 
              data['category'], json.dumps(data['tags']), status))
    conn.commit()
    conn.close()
    return jsonify({'code': 0, 'msg': '操作成功'})

# --- 2. 管理员审核接口 ---
@app.route('/api/admin/articles/<int:article_id>/review', methods=['POST'])
@admin_role_required
def review_article(article_id):
    # 此处应有管理员权限校验...
    data = request.json
    action = data.get('action') # 'approve' 或 'reject'
    reason = data.get('reason', '')

    status = 'approved' if action == 'approve' else 'rejected'
    
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("UPDATE articles SET status = %s, reject_reason = %s WHERE id = %s", 
                       (status, reason, article_id))
    conn.commit()
    conn.close()
    return jsonify({'code': 0, 'msg': '审核完毕'})

import redis
redis_client = redis.StrictRedis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)

# --- 3. 点赞/取消点赞 (Redis 方案) ---
@app.route('/api/articles/<int:article_id>/like', methods=['POST'])
@jwt_required()
def toggle_like(article_id):
    user_id = get_jwt_identity()
    redis_key = f"article:{article_id}:likes"
    
    # 检查用户是否在点赞集合中
    is_liked = redis_client.sismember(redis_key, user_id)
    
    if is_liked:
        redis_client.srem(redis_key, user_id) # 取消点赞
        # 异步更新到 MySQL (省略异步代码，此处同步演示)
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM article_likes WHERE article_id=%s AND user_id=%s", (article_id, user_id))
            cursor.execute("UPDATE articles SET likes_count = likes_count - 1 WHERE id = %s", (article_id,))
        conn.commit()
        liked_state = False
    else:
        redis_client.sadd(redis_key, user_id) # 加入点赞
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("INSERT IGNORE INTO article_likes (article_id, user_id) VALUES (%s, %s)", (article_id, user_id))
            cursor.execute("UPDATE articles SET likes_count = likes_count + 1 WHERE id = %s", (article_id,))
        conn.commit()
        liked_state = True
        
    likes_count = redis_client.scard(redis_key) # 获取最新点赞数
    return jsonify({'code': 0, 'data': {'liked': liked_state, 'count': likes_count}})

# --- 4. 获取文章详情 (含安全渲染数据与浏览量自增) ---
@app.route('/api/articles/<int:article_id>', methods=['GET'])
def get_article_detail(article_id):
    # Redis 浏览量自增
    views_key = f"article:{article_id}:views"
    redis_client.incr(views_key)
    
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM articles WHERE id = %s AND status = 'approved'", (article_id,))
        article = cursor.fetchone()
    conn.close()
    
    if not article:
        return jsonify({'code': 404, 'msg': '文章不存在或还在审核中'})
        
    # 合并 Redis 中的实时数据
    article['views'] = int(redis_client.get(views_key) or article['views'])
    return jsonify({'code': 0, 'data': article})

# ================= 记录真实点击 (升级版) =================
@app.route('/api/click', methods=['POST'])
def handle_click():
    # 获取前端传来的网站 ID
    data = request.get_json()
    site_id = data.get('id')
    
    if not site_id:
        return jsonify({'code': 400, 'msg': '缺少网站 ID'}), 400
        
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 1. (兼容旧版) 更新原本 websites 表的总点击量
            cursor.execute("UPDATE websites SET clicks = clicks + 1 WHERE id = %s", (site_id,))
            
            # 2. ✨ (核心新增) 往排行榜专用的 click_log 表里插入一条带时间戳的记录
            cursor.execute("INSERT INTO click_log (item_id) VALUES (%s)", (site_id,))
            
        conn.commit()
        conn.close()
        
        return jsonify({'code': 0, 'msg': '点击已成功记录入库'})
    except Exception as e:
        print(f"记录点击严重报错: {e}")
        return jsonify({'code': 500, 'msg': '服务器内部错误'}), 500

# ---------------------------------------------------------
# 💡 鉴权辅助函数：从前端请求的 Header 中提取当前登录的用户
# （如果你项目中用了 flask_jwt_extended，这里可以直接用 get_jwt_identity()）
# ---------------------------------------------------------
def get_current_username():
    """解析前端传来的 Authorization: Bearer <token>"""
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        # 这里为了演示通用性，假设 token 里直接存了用户名
        # 实际开发中，请使用你的 JWT 解码逻辑： jwt.decode(token, SECRET_KEY)
        return token 
    # 如果没 token，默认返回测试账号（防止前端直接崩溃）
    return "用户_1234"


# =========================================================
# 🚀 1. 获取个人主页数据概览 (发帖数、获赞数等)
# =========================================================
@app.route('/api/user/stats', methods=['GET'])
def get_user_stats():
    username = request.args.get('username') or get_current_username()
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 统计该用户的发帖总数
            cursor.execute("SELECT COUNT(*) AS posts FROM user_contents WHERE username = %s AND status = 'published'", (username,))
            posts_count = cursor.fetchone()['posts']
            
            # 统计总获赞数和浏览量
            cursor.execute("SELECT SUM(views) as total_views, SUM(likes) as total_likes FROM user_contents WHERE username = %s", (username,))
            sum_data = cursor.fetchone()
            
            # 真实商业项目中，粉丝数可能存在 follower 表中，这里先做个安全回退
            total_views = int(sum_data['total_views'] or 0) + int(sum_data['total_likes'] or 0)
            
        conn.close()
        
        return jsonify({
            'code': 0,
            'data': {
                'views': total_views,
                'followers': 0, # 这里可以改成连表查询真实的粉丝数
                'posts': posts_count
            }
        })
    except Exception as e:
        print(f"Stats API 报错: {e}")
        return jsonify({'code': 500, 'msg': '数据库查询失败'}), 500


# =========================================================
# 🚀 2. 获取账号安全 - 登录设备列表
# =========================================================
@app.route('/api/user/devices', methods=['GET'])
def get_user_devices():
    username = get_current_username()
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 查出该用户最近登录的设备
            cursor.execute("SELECT * FROM user_devices WHERE username = %s ORDER BY last_login_time DESC LIMIT 10", (username,))
            devices = cursor.fetchall()
            
            # 格式化时间，以适配前端
            for dev in devices:
                # 转换 datetime 为字符串
                dev['time'] = dev['last_login_time'].strftime('%Y-%m-%d %H:%M') 
                dev['isCurrent'] = bool(dev['is_current'])
                
        conn.close()
        return jsonify({'code': 0, 'data': devices})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e)}), 500


# =========================================================
# 🚀 3. 获取我的内容管理列表 (支持按状态过滤)
# =========================================================
@app.route('/api/user/contents', methods=['GET'])
def get_user_contents():
    username = get_current_username()
    # 接收前端传来的状态：published(已发布) / reviewing(审核中) / draft(草稿)
    status = request.args.get('status', 'published') 
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, title, views, likes, created_at 
                FROM user_contents 
                WHERE username = %s AND status = %s 
                ORDER BY created_at DESC
            """, (username, status))
            contents = cursor.fetchall()
            
            # 格式化日期给前端展示
            for item in contents:
                item['time'] = item['created_at'].strftime('%Y-%m-%d %H:%M')
                
        conn.close()
        return jsonify({'code': 0, 'data': contents})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e)}), 500


# =========================================================
# 4. 浏览历史（复用 user_behaviors 的 visit 事件）
# =========================================================
def get_history_user():
    """Resolve the JWT identity to the real user row used by history queries."""
    identity = get_jwt_identity()
    identity_text = str(identity or "").strip()
    if not identity_text:
        return None

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, username FROM users WHERE username=%s OR email=%s LIMIT 1",
                (identity_text, identity_text),
            )
            user = cursor.fetchone()
            if not user and identity_text.isdigit():
                cursor.execute(
                    "SELECT id, username FROM users WHERE id=%s LIMIT 1",
                    (int(identity_text),),
                )
                user = cursor.fetchone()
            return user
    finally:
        conn.close()


def serialize_history_row(row):
    visited_at = row.get('visited_at') or row.get('created_at')
    if hasattr(visited_at, 'isoformat'):
        visited_at = visited_at.isoformat()
    return {
        'id': row.get('id'),
        'site_id': row.get('site_id'),
        'name': row.get('name') or '未命名网站',
        'url': row.get('url') or '',
        'logo_url': row.get('logo_url') or '',
        'description': row.get('summary') or row.get('description') or '',
        'category': row.get('category_name') or '',
        'source': row.get('source') or 'unknown',
        'visited_at': visited_at,
    }


@app.route('/api/user/history', methods=['GET'])
@jwt_required()
def get_user_history():
    user = get_history_user()
    if not user:
        return jsonify({'code': 404, 'msg': '用户不存在'}), 404

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT ub.id, ub.site_id, ub.keyword AS source,
                       ub.created_at AS visited_at, w.name, w.url, w.logo_url,
                       w.summary, w.description, c.name AS category_name
                FROM user_behaviors ub
                JOIN websites w ON w.id = ub.site_id
                LEFT JOIN categories c ON c.id = w.category_id
                WHERE ub.user_id = %s AND ub.behavior_type = 'visit'
                ORDER BY ub.created_at DESC
                LIMIT 100
                """,
                (user['id'],),
            )
            items = [serialize_history_row(row) for row in cursor.fetchall()]
        if app.debug:
            app.logger.info('Browsing history loaded user_id=%s count=%s', user['id'], len(items))
        return jsonify({'code': 0, 'data': {'items': items, 'total': len(items)}})
    except Exception:
        app.logger.exception('Browsing history query failed user_id=%s', user['id'])
        return jsonify({'code': 500, 'msg': '浏览历史加载失败'}), 500
    finally:
        conn.close()


@app.route('/api/user/history', methods=['POST'])
@jwt_required()
def record_user_history():
    user = get_history_user()
    if not user:
        return jsonify({'code': 404, 'msg': '用户不存在'}), 404

    data = request.get_json(silent=True) or {}
    raw_site_id = data.get('site_id') or data.get('siteId') or data.get('id')
    site_id = int(raw_site_id) if str(raw_site_id or '').isdigit() else None
    raw_url = str(data.get('url') or '').strip()
    source = str(data.get('source') or 'unknown').strip()[:64] or 'unknown'

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            site = None
            if site_id:
                cursor.execute(
                    "SELECT id FROM websites WHERE id=%s LIMIT 1",
                    (site_id,),
                )
                site = cursor.fetchone()
            if not site and raw_url:
                normalized_url = raw_url.rstrip('/')
                cursor.execute(
                    """
                    SELECT id FROM websites
                    WHERE LOWER(TRIM(TRAILING '/' FROM url)) = LOWER(%s)
                    LIMIT 1
                    """,
                    (normalized_url,),
                )
                site = cursor.fetchone()
            if not site:
                return jsonify({'code': 404, 'msg': '网站未收录'}), 404

            site_id = site['id']
            cursor.execute(
                """
                SELECT id FROM user_behaviors
                WHERE user_id=%s AND site_id=%s AND behavior_type='visit'
                  AND created_at >= DATE_SUB(NOW(), INTERVAL 30 SECOND)
                ORDER BY created_at DESC LIMIT 1
                """,
                (user['id'], site_id),
            )
            duplicate = cursor.fetchone()
            if duplicate:
                history_id = duplicate['id']
                cursor.execute(
                    "UPDATE user_behaviors SET keyword=%s, created_at=NOW() WHERE id=%s",
                    (source, history_id),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO user_behaviors (user_id, site_id, behavior_type, keyword, created_at)
                    VALUES (%s, %s, 'visit', %s, NOW())
                    """,
                    (user['id'], site_id, source),
                )
                history_id = cursor.lastrowid
            conn.commit()

            cursor.execute(
                """
                SELECT ub.id, ub.site_id, ub.keyword AS source,
                       ub.created_at AS visited_at, w.name, w.url, w.logo_url,
                       w.summary, w.description, c.name AS category_name
                FROM user_behaviors ub
                JOIN websites w ON w.id = ub.site_id
                LEFT JOIN categories c ON c.id = w.category_id
                WHERE ub.id=%s AND ub.user_id=%s
                """,
                (history_id, user['id']),
            )
            item = serialize_history_row(cursor.fetchone() or {})
        if app.debug:
            app.logger.info(
                'Browsing history saved user_id=%s site_id=%s source=%s deduplicated=%s',
                user['id'], site_id, source, bool(duplicate),
            )
        return jsonify({'code': 0, 'data': item})
    except Exception:
        conn.rollback()
        app.logger.exception('Browsing history save failed user_id=%s site_id=%s', user['id'], site_id)
        return jsonify({'code': 500, 'msg': '浏览历史保存失败'}), 500
    finally:
        conn.close()


# =========================================================
# 🚀 5. 功能接口：删除单条内容 & 清空互动足迹
# =========================================================
@app.route('/api/user/contents/delete', methods=['POST'])
def delete_user_content():
    username = get_current_username()
    content_id = request.json.get('id')
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM user_contents WHERE id = %s AND username = %s", (content_id, username))
        conn.commit()
        conn.close()
        return jsonify({'code': 0, 'msg': '删除成功'})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e)}), 500


@app.route('/api/user/history/clear', methods=['POST'])
@jwt_required()
def clear_user_history():
    user = get_history_user()
    if not user:
        return jsonify({'code': 404, 'msg': '用户不存在'}), 404
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM user_behaviors WHERE user_id=%s AND behavior_type='visit'",
                (user['id'],),
            )
        conn.commit()
        conn.close()
        return jsonify({'code': 0, 'msg': '浏览历史已清空'})
    except Exception:
        app.logger.exception('Browsing history clear failed user_id=%s', user['id'])
        return jsonify({'code': 500, 'msg': '清空浏览历史失败'}), 500


@app.route('/api/user/history/<int:history_id>', methods=['DELETE'])
@jwt_required()
def delete_user_history(history_id):
    user = get_history_user()
    if not user:
        return jsonify({'code': 404, 'msg': '用户不存在'}), 404
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM user_behaviors
                WHERE id=%s AND user_id=%s AND behavior_type='visit'
                """,
                (history_id, user['id']),
            )
            deleted = cursor.rowcount
        conn.commit()
        if not deleted:
            return jsonify({'code': 404, 'msg': '记录不存在'}), 404
        return jsonify({'code': 0, 'msg': '删除成功'})
    except Exception:
        conn.rollback()
        app.logger.exception(
            'Browsing history delete failed user_id=%s history_id=%s',
            user['id'], history_id,
        )
        return jsonify({'code': 500, 'msg': '删除浏览历史失败'}), 500
    finally:
        conn.close()

@app.route('/api/cache_logo', methods=['POST'])
def cache_logo():
    """
    缓存网站图标 URL 接口。

    接口路径：POST /api/cache_logo
    请求方法：POST
    功能描述：根据网站 URL 自动生成 Google Favicon 服务的图标地址，
              并更新内存中 websites_db 对应网站的 logo_url 字段。
              注意：此接口只更新内存数据，不持久化到数据库。
    请求体（JSON）：
        id  (int): 网站 ID（对应 websites_db 中的 id）
        url (str): 网站地址，用于提取域名
    返回：
        200 - 成功，包含生成的 logo_url
        200 - 失败（URL 无效），包含错误信息
    """
    data = request.json
    site_id = data.get('id')   # 目标网站 ID
    url = data.get('url')      # 网站地址
    if url:
        domain = url.split('//')[-1].split('/')[0].replace('www.', '')  # 从 URL 中提取纯域名（去掉 www. 前缀）
        logo_url = f"https://www.google.com/s2/favicons?sz=128&domain={domain}"  # 构造 Google Favicon 服务 URL（128px 高清图标）
        for site in websites_db:
            if site['id'] == site_id:
                site['logo_url'] = logo_url  # 更新内存中对应网站的图标地址
                break
        return jsonify({"status": "success", "logo_url": logo_url})
    return jsonify({"status": "error", "message": "无效的 URL"})

# --- 1. 获取收藏列表 API ---
# 加上 OPTIONS 方法，让浏览器的跨域预检顺利通过
def get_favorites():
    """
    获取当前用户的收藏网站 ID 列表接口（需要 JWT 认证）。

    接口路径：GET /api/favorites
    请求方法：GET（OPTIONS 用于跨域预检）
    功能描述：返回当前登录用户收藏的所有网站 ID 列表，
              前端据此在导航页上标记已收藏的网站。
    请求头：Authorization: Bearer <access_token>
    返回：
        200 - 收藏的网站 ID 数组（如 [101, 205, 507]）
        401 - Token 无效或未提供
    """
    # 如果是跨域预检请求，直接放行
    if request.method == 'OPTIONS':
        return jsonify({"message": "OK"}), 200
        
    # 验证 Token
    verify_jwt_in_request()  # 验证 Access Token 合法性
    user_id = get_jwt_identity()  # 从 Token 中提取当前用户 ID
    favorites = UserFavorite.query.filter_by(user_id=user_id).all()  # 查询该用户的所有收藏记录
    fav_ids = [fav.website_id for fav in favorites]  # 提取收藏的网站 ID 列表
    return jsonify(fav_ids), 200

# --- 2. 切换收藏状态 API ---
@app.route('/api/favorites', methods=['POST', 'OPTIONS'])
def toggle_favorite():
    """
    切换网站收藏状态接口（需要 JWT 认证）。

    接口路径：POST /api/favorites
    请求方法：POST（OPTIONS 用于跨域预检）
    功能描述：对指定网站执行收藏/取消收藏的切换操作。
              如果该网站已被收藏则取消收藏，否则添加收藏（Toggle 逻辑）。
    请求头：Authorization: Bearer <access_token>
    请求体（JSON）：
        website_id (int): 要切换收藏状态的网站 ID
    返回：
        200 - 取消收藏成功
        201 - 添加收藏成功
        400 - 缺少 website_id 参数
        401 - Token 无效或未提供
    """
    if request.method == 'OPTIONS':
        return jsonify({"message": "OK"}), 200  # 直接放行跨域预检请求
        
    verify_jwt_in_request()  # 验证 Access Token
    user_id = get_jwt_identity()  # 获取当前用户 ID
    data = request.get_json()
    website_id = data.get('website_id')  # 获取目标网站 ID

    if not website_id:
        return jsonify({"error": "缺少 website_id"}), 400

    existing_fav = UserFavorite.query.filter_by(user_id=user_id, website_id=website_id).first()  # 查询是否已收藏
    
    if existing_fav:
        db.session.delete(existing_fav)  # 已收藏则删除记录（取消收藏）
        db.session.commit()
        return jsonify({"status": "removed", "message": "已取消收藏"}), 200
    else:
        new_fav = UserFavorite(user_id=user_id, website_id=website_id)  # 未收藏则创建新收藏记录
        db.session.add(new_fav)
        db.session.commit()
        record_unified_behavior_event(
            user_id,
            website_id,
            "favorite",
            str(data.get("source") or "favorite").strip().lower(),
            data,
        )
        return jsonify({"status": "added", "message": "收藏成功"}), 201

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    智能导航助手聊天接口（模拟数据版）。

    接口路径：POST /api/chat
    请求方法：POST
    功能描述：接收用户的自然语言消息，根据关键词匹配返回相应的网站推荐建议。
              当前为模拟实现，根据消息中的关键词（设计/摸鱼/游戏/代码/开发/前端）
              返回预设的推荐回复。生产环境可接入真实 AI 大模型 API。
    请求体（JSON）：
        message (str): 用户输入的消息内容
    返回：
        200 - 包含 reply 字段的 JSON 对象，reply 为助手的回复文本
    """
    data = request.json
    user_message = data.get('message', '')  # 获取用户消息，默认为空字符串
    time.sleep(1)   # 模拟 AI 思考延迟，提升用户体验感
    reply = "收到！但我现在还是个模拟数据。你可以试着在输入框里包含“设计”、“摸鱼”或“代码”等关键词。"
    if "设计" in user_message:
        reply = "找设计灵感吗？强烈推荐你去看看 Dribbble、Behance 或者站酷！"
    elif "摸鱼" in user_message or "游戏" in user_message:
        reply = "偷偷告诉你，工作累了可以去刷刷 B站 或者 抖音 放松一下~"
    elif "代码" in user_message or "开发" in user_message or "前端" in user_message:
        reply = "推荐多看 GitHub 的开源项目，遇到 Bug 直接上 StackOverflow 搜！"
    return jsonify({"reply": reply})


# ================= 2. 管理员权限校验装饰器 =================
def admin_required():
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            username = get_jwt_identity()
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
            conn.close()
            if not user or user.get('role') not in ('admin', 'super_admin'):
                return jsonify({'code': 403, 'msg': '权限不足，仅管理员可访问'}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper


# ================= 3. 后台数据大盘 API =================
@app.route('/api/admin/stats', methods=['GET'])
@admin_required()
def get_admin_stats():
    today = datetime.date.today().strftime('%Y-%m-%d')
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # 今日新增用户
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE DATE(created_at) = %s", (today,))
        new_users = cursor.fetchone()['count']
        # 待审核文章
        cursor.execute("SELECT COUNT(*) as count FROM articles WHERE status = 'pending'")
        pending_articles = cursor.fetchone()['count']
        # 总阅读量
        cursor.execute("SELECT SUM(views) as total_views FROM articles")
        total_views = cursor.fetchone()['total_views'] or 0
    conn.close()
    
    return jsonify({'code': 0, 'data': {
        'new_users_today': new_users,
        'pending_articles': pending_articles,
        'total_views': int(total_views)
    }})


# ================= 4. 处理举报 & DMCA =================
@app.route('/api/report', methods=['POST'])
@jwt_required()
def submit_report():
    """前端用户提交举报"""
    user_id = get_jwt_identity() # 此处简化为 username，实际建议用 id
    data = request.json
    
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("INSERT INTO reports (user_id, target_type, target_id, reason) VALUES (%s, %s, %s, %s)",
                       (user_id, data['type'], data['target_id'], data['reason']))
    conn.commit()
    conn.close()
    return jsonify({'code': 0, 'msg': '举报已提交，我们会尽快处理'})

@app.route('/api/dmca', methods=['POST'])
@limiter.limit("3 per day") # 防止恶意提交表单
def submit_dmca():
    """提交 DMCA 版权申诉 (无需登录)"""
    data = request.json
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO dmca_complaints (complainant_name, contact_email, target_url, description) 
            VALUES (%s, %s, %s, %s)
        """, (data['name'], data['email'], data['url'], data['desc']))
    conn.commit()
    conn.close()
    return jsonify({'code': 0, 'msg': '版权投诉已收到，法务团队将在 3 个工作日内联系您'})

# (文章审核、封禁用户的 CRUD API 逻辑与之前类似，此处省略重复的 UPDATE 语句，重点在于 @admin_required 保护)

# ================= 1. 配置 OAuth =================
# 注意：在本地测试时，必须允许 HTTP 传输 OAuth token
os.environ['AUTHLIB_INSECURE_TRANSPORT'] = '1'

oauth = OAuth(app)
github = oauth.register(
    name='github',
    client_id=os.getenv('GITHUB_CLIENT_ID', ''),
    client_secret=os.getenv('GITHUB_CLIENT_SECRET', ''),
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

# ================= 2. 触发登录路由 =================
@app.route('/api/login/github')
def login_github():
    # 生成回调地址，告诉 GitHub 授权完跳回哪里
    redirect_uri = url_for('github_callback', _external=True)
    return github.authorize_redirect(redirect_uri)
# ================= 3. GitHub 回调 (✨ 安全升级版) =================
@app.route('/api/github/callback', methods=['GET'])
def github_callback():
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "缺少授权码 (code)"}), 400

    # ✨ 从系统的环境变量中安全读取，取代原来的明文密码
    CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
    CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')

    if not CLIENT_ID or not CLIENT_SECRET:
        return jsonify({"error": "服务器未配置 GitHub 密钥，请检查 .env 文件！"}), 500

    # 用 code 换取 Access Token
    token_response = requests.post(
        'https://github.com/login/oauth/access_token',
        data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'code': code
        },
        headers={'Accept': 'application/json'}
    )
    
    token_json = token_response.json()
    access_token = token_json.get('access_token')

    if not access_token:
         return jsonify({"error": "获取 Access Token 失败", "details": token_json}), 400

    # 获取用户信息
    user_response = requests.get(
        'https://api.github.com/user',
        headers={'Authorization': f'token {access_token}'}
    )
    user_data = user_response.json()

    username = user_data.get('login', 'GitHub用户')
    avatar = user_data.get('avatar_url', '')

    query = urlencode({"login": "success", "username": username, "avatar": avatar})
    frontend_url = f"{get_frontend_url()}/?{query}"
    print(f"🎉 GitHub 登录成功！用户: {username}")
    return redirect(frontend_url)


@app.route('/api/admin/audit-site/<int:site_id>', methods=['POST'])
@admin_role_required
def audit_site(site_id):
    from models import db, Website
    site = Website.query.get_or_404(site_id)
    
    action = request.json.get('action') # 'approve' 或 'reject'
    
    if action == 'approve':
        # 1. 更新 MySQL 数据库
        site.status = 'approved'
        db.session.commit()
        
        # 2. ✨ 核心联动：同步推送到 Meilisearch 极速搜索引擎 ✨
        try:
            index = meili_index
            
            # 组装成搜索引擎需要的格式
            document = {
                "id": str(site.id),
                "name": site.name,
                "url": site.url,
                "description": site.description,
                "clicks": site.clicks or 0
            }
            # 推送！
            index.add_documents([document])
            print(f"🌍 [引擎同步] 成功将 {site.name} 推送至 Meilisearch!")
            
        except Exception as e:
            print(f"⚠️ [引擎报错] Meilisearch 同步失败: {e}")
            
        return jsonify({"message": "已批准上线，并秒级同步至搜索引擎！"})
        
    elif action == 'reject':
        db.session.delete(site)
        db.session.commit()
        return jsonify({"message": "已残忍拒绝并销毁！"})
        
    return jsonify({"error": "未知操作"}), 400
# ================= 网站资源 RESTful API =================

# 1. 获取列表 (GET) - 支持分页、分类筛选、搜索
@app.route('/api/websites', methods=['GET'])
def get_websites():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category_id = request.args.get('category', type=int)
    search = request.args.get('search', type=str)

    query = Website.query

    if category_id:
        query = query.filter_by(category_id=category_id)
    if search:
        query = query.filter(Website.name.ilike(f'%{search}%'))

    # 使用 SQLAlchemy 自带的分页 (基于 LIMIT 和 OFFSET)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "data": [{
            "id": s.id, "name": s.name, "url": s.url, 
            "category_id": s.category_id, "clicks": s.clicks
        } for s in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page
    })

# 2. 新增网站 (POST)
@app.route('/api/websites', methods=['POST'])
@admin_role_required
def create_website():
    data = request.json
    name = data.get('name')
    url = data.get('url')
    category_id = data.get('category') 

    # 字段校验
    if not name or not url:
        return jsonify({"error": "name和url为必填项"}), 400
    if not is_valid_url(url):
        return jsonify({"error": "URL格式不正确，需包含http/https"}), 400

    new_site = Website(name=name, url=url, category_id=category_id)
    db.session.add(new_site)
    db.session.commit()
    return jsonify({"message": "创建成功", "id": new_site.id}), 201

# 3. 获取单个详情 (GET)
@app.route('/api/websites/<int:id>', methods=['GET'])
def get_website(id):
    site = Website.query.get(id)
    if not site:
        return jsonify({"error": "网站不存在"}), 404
    return jsonify({"id": site.id, "name": site.name, "url": site.url, "category_id": site.category_id})

# 4. 更新网站 (PUT)
@app.route('/api/websites/<int:id>', methods=['PUT'])
@admin_role_required
def update_website(id):
    site = Website.query.get(id)
    if not site:
        return jsonify({"error": "网站不存在"}), 404
        
    data = request.json
    if 'name' in data: 
        site.name = data['name']
    if 'url' in data:
        if not is_valid_url(data['url']):
            return jsonify({"error": "URL格式不正确"}), 400
        site.url = data['url']
    if 'category_id' in data: 
        site.category_id = data['category_id']

    db.session.commit()
    return jsonify({"message": "更新成功"})

# 5. 删除网站 (DELETE)
@app.route('/api/websites/<int:id>', methods=['DELETE'])
@admin_role_required
def delete_website(id):
    site = Website.query.get(id)
    if not site:
        return jsonify({"message": "该网站不存在，无法删除"}), 404
        
    db.session.delete(site)
    db.session.commit()
    return jsonify({"message": "删除成功"})

# =====================================================================
# 注册所有扩展模块（统一在此处注册，确保 app 实例已完全初始化）
# =====================================================================
try:
    register_v1_routes(app, get_db_connection)
    register_personalization_routes(app, get_db_connection)
    register_questionnaire_admin_read_routes(app, get_db_connection)
    register_review_routes(app, admin_required)
    print("V1 routes registered successfully")
except Exception as e:
    print(f"Failed to register v1 routes: {e}")
    raise
app_extensions.register_redis_sync_scheduler(app, scheduler, redis_client)
register_password_reset_routes(app, limiter)
app_extensions.register_token_refresh_route(app)
app_extensions.register_content_filter_routes(app)
app_extensions.register_notification_routes(app, db)
app_extensions.register_hot_ranking_routes(app, redis_client)
app_extensions.register_admin_user_routes(app, db)
app_extensions.register_stats_overview_routes(app, db)
app_extensions.register_content_audit_routes(app, db)
app_extensions.register_survey_routes(app, db)
app.logger.info('✅ 所有扩展模块注册完成')


def should_initialize_database(debug, run_main=None):
    """Only initialize in the serving process when Werkzeug reloads."""
    if not debug:
        return True
    if run_main is None:
        run_main = os.getenv('WERKZEUG_RUN_MAIN')
    return str(run_main).lower() == 'true'


def initialize_database():
    """Create missing tables once and surface initialization failures."""
    validate_database_config(DB_CONFIG)
    with app.app_context():
        db.create_all()


def parse_backend_port():
    backend_value = os.getenv("BACKEND_PORT")
    if backend_value is not None and backend_value.strip():
        variable_name = "BACKEND_PORT"
        raw_value = backend_value.strip()
    else:
        variable_name = "PORT"
        raw_value = (os.getenv("PORT") or "5000").strip() or "5000"

    try:
        port = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(
            f"{variable_name} must be an integer between 1 and 65535"
        ) from exc
    if not 1 <= port <= 65535:
        raise RuntimeError(
            f"{variable_name} must be an integer between 1 and 65535"
        )
    return port


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "smtp-check":
        from smtp_check import main as smtp_check_main

        raise SystemExit(smtp_check_main(sys.argv[2:]))

    debug_mode = os.getenv("FLASK_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
    use_reloader = debug_mode
    bind_host = (os.getenv("BACKEND_HOST") or "0.0.0.0").strip()
    bind_port = parse_backend_port()
    serving_process = should_initialize_database(debug_mode)
    if serving_process:
        initialize_database()
        with app.app_context():
            # 启动时自动同步所有分类和网站到数据库
            try:
                from init_db import all_categories, all_sites, get_logo_url
                conn = pool_get_connection()
                cur = conn.cursor()

                # 同步分类
                for cat in all_categories:
                    cat_id, profession, name, sort = cat
                    cur.execute(
                        "INSERT INTO categories (id,name,profession_type,sort_order) VALUES (%s,%s,%s,%s) "
                        "ON DUPLICATE KEY UPDATE name=%s, profession_type=%s, sort_order=%s",
                        (cat_id, name, profession, sort, name, profession, sort)
                    )

                # 同步网站（跳过已存在的）
                new_count = 0
                for site in all_sites:
                    cur.execute("SELECT id FROM websites WHERE name=%s AND category_id=%s",
                                (site['name'], site['cat']))
                    if not cur.fetchone():
                        logo = get_logo_url(site['url'])
                        cur.execute(
                            "INSERT INTO websites (category_id,name,url,logo_url,summary,description) VALUES (%s,%s,%s,%s,%s,%s)",
                            (
                                site['cat'],
                                site['name'],
                                site['url'],
                                logo,
                                site.get('summary', ''),
                                site.get('description', ''),
                            )
                        )
                        new_count += 1

                conn.commit()
                conn.close()
                if new_count > 0:
                    print(f"Startup data sync added {new_count} websites")
                else:
                    print(f"Startup data is current: {len(all_sites)} websites")
            except Exception as e:
                print(f"Startup data sync failed (continuing): {e}")
        scheduler.start()

    print(f"[后端] Flask 服务启动（{bind_host}:{bind_port}）")
    app.run(
        host=bind_host,
        port=bind_port,
        debug=debug_mode,
        use_reloader=use_reloader,
    )
