"""Database-backed password reset routes for local accounts."""

from __future__ import annotations

import hmac
import ipaddress
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from flask import jsonify, request
from werkzeug.security import generate_password_hash

from db_pool import get_connection
from email_service import (
    MAIL_ERROR_MESSAGES,
    check_mail_connection,
    parse_env_bool,
    send_password_reset_email,
    validate_mail_config,
)


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
CODE_PATTERN = re.compile(r"^\d{6}$")
PASSWORD_LETTER_PATTERN = re.compile(r"[A-Za-z]")
PASSWORD_DIGIT_PATTERN = re.compile(r"\d")

CODE_TTL_MINUTES = 10
RESEND_SECONDS = 60
HOURLY_SEND_LIMIT = 5
MAX_ATTEMPTS = 5
GENERIC_SEND_MESSAGE = "如果该邮箱已注册，验证码将发送至该邮箱"


def utcnow() -> datetime:
    """Return a naive UTC value suitable for the project's MySQL DATETIME fields."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_email(value) -> str:
    return str(value or "").strip().lower()


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_PATTERN.fullmatch(value))


def is_strong_password(value: str) -> bool:
    return (
        len(value) >= 8
        and bool(PASSWORD_LETTER_PATTERN.search(value))
        and bool(PASSWORD_DIGIT_PATTERN.search(value))
    )


def _error(code: str, message: str, status: int, **extra):
    payload = {
        "success": False,
        "code": code,
        "message": message,
        "msg": message,
        **extra,
    }
    return jsonify(payload), status


def _code_digest(app, email: str, code: str) -> str:
    secret = str(app.config.get("SECRET_KEY") or app.secret_key or "").encode("utf-8")
    payload = f"password-reset:{email}:{code}".encode("utf-8")
    return hmac.new(secret, payload, "sha256").hexdigest()


def _valid_ip(value: str | None) -> str | None:
    candidate = str(value or "").strip()
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def get_client_ip() -> str:
    """Honor X-Forwarded-For only when the deployment declares trusted proxy hops."""
    remote_ip = _valid_ip(request.remote_addr) or "unknown"
    try:
        trusted_hops = max(0, int(os.getenv("TRUSTED_PROXY_COUNT") or "0"))
    except ValueError:
        trusted_hops = 0
    if trusted_hops == 0:
        return remote_ip[:64]

    forwarded = [
        parsed
        for parsed in (
            _valid_ip(part) for part in request.headers.get("X-Forwarded-For", "").split(",")
        )
        if parsed
    ]
    chain = [*forwarded, remote_ip]
    if len(chain) <= trusted_hops:
        return remote_ip[:64]
    return chain[-(trusted_hops + 1)][:64]


def _development_code_allowed(app) -> bool:
    environments = {
        (os.getenv(name) or "").strip().lower()
        for name in ("APP_ENV", "FLASK_ENV", "ENV", "VERCEL_ENV")
    }
    is_production = "production" in environments
    is_development = bool(
        app.testing
        or app.debug
        or environments.intersection({"development", "testing", "test"})
    )
    return bool(
        not is_production
        and is_development
        and parse_env_bool(os.getenv("PASSWORD_RESET_DEV_SHOW_CODE"), False)
    )


def _mail_mode(app) -> tuple[str | None, str | None]:
    mode = (os.getenv("PASSWORD_RESET_MAIL_MODE") or "smtp").strip().lower()
    if mode == "smtp":
        return mode, None
    if mode == "console" and _development_code_allowed(app):
        return mode, None
    return None, "开发邮件模式未启用或当前环境不允许使用"


def _missing_reset_table(error: BaseException) -> bool:
    error_text = str(error).lower()
    error_code = error.args[0] if getattr(error, "args", None) else None
    return error_code == 1146 or (
        "password_reset_codes" in error_text
        and ("doesn't exist" in error_text or "does not exist" in error_text)
    )


def register_password_reset_routes(app, limiter) -> None:
    """Register the two password reset endpoints on the existing auth namespace."""

    @app.post("/api/auth/forgot-password/send-code")
    @limiter.limit("30 per hour")
    def send_password_reset_code():
        data = request.get_json(silent=True) or {}
        email = normalize_email(data.get("email"))
        request_id = request.headers.get("X-Request-ID") or secrets.token_hex(8)

        if not email:
            return _error("EMAIL_REQUIRED", "请输入邮箱地址", 400)
        if not is_valid_email(email):
            return _error("EMAIL_INVALID", "邮箱格式不正确", 400)
        mail_mode, mail_mode_error = _mail_mode(app)
        if mail_mode_error:
            app.logger.warning("password reset mail mode rejected request_id=%s", request_id)
            return _error("MAIL_MODE_INVALID", mail_mode_error, 503)
        if mail_mode == "smtp":
            if validate_mail_config():
                app.logger.warning(
                    "password reset mail config missing request_id=%s", request_id
                )
                return _error("MAIL_CONFIG_MISSING", "邮件服务尚未完成配置", 503)
            mail_ready, mail_code = check_mail_connection()
            if not mail_ready:
                app.logger.warning(
                    "password reset mail preflight failed request_id=%s code=%s",
                    request_id,
                    mail_code,
                )
                return _error(
                    mail_code,
                    MAIL_ERROR_MESSAGES.get(mail_code, "邮件服务暂时不可用"),
                    503,
                )

        conn = None
        code = None
        record_id = None
        user = None
        now = utcnow()
        try:
            conn = get_connection()
            with conn.cursor() as cursor:
                # Locking an existing user serializes requests for registered accounts.
                cursor.execute(
                    """SELECT id, username FROM users
                       WHERE LOWER(email)=LOWER(%s) AND deleted_at IS NULL
                       LIMIT 1 FOR UPDATE""",
                    (email,),
                )
                user = cursor.fetchone()

                cursor.execute(
                    """SELECT created_at FROM password_reset_codes
                       WHERE email=%s ORDER BY created_at DESC, id DESC LIMIT 1""",
                    (email,),
                )
                previous = cursor.fetchone()
                previous_at = previous.get("created_at") if previous else None
                if previous_at and (now - previous_at).total_seconds() < RESEND_SECONDS:
                    retry_after = max(
                        1, RESEND_SECONDS - int((now - previous_at).total_seconds())
                    )
                    conn.rollback()
                    return _error(
                        "RESET_CODE_RATE_LIMITED",
                        "验证码发送过于频繁，请稍后再试",
                        429,
                        retry_after=retry_after,
                    )

                cursor.execute(
                    """SELECT COUNT(*) AS total FROM password_reset_codes
                       WHERE email=%s AND created_at >= %s""",
                    (email, now - timedelta(hours=1)),
                )
                if int((cursor.fetchone() or {}).get("total") or 0) >= HOURLY_SEND_LIMIT:
                    conn.rollback()
                    return _error(
                        "RESET_CODE_HOURLY_LIMIT",
                        "验证码发送次数已达上限，请稍后再试",
                        429,
                    )

                if user:
                    cursor.execute(
                        """UPDATE password_reset_codes SET used_at=%s
                           WHERE user_id=%s AND used_at IS NULL""",
                        (now, user["id"]),
                    )
                    code = f"{secrets.randbelow(1_000_000):06d}"
                    code_hash = _code_digest(app, email, code)
                    used_at = None
                else:
                    # Persist a consumed decoy request so rate-limit behavior is uniform.
                    code_hash = _code_digest(app, email, secrets.token_hex(16))
                    used_at = now

                cursor.execute(
                    """INSERT INTO password_reset_codes
                           (user_id, email, code_hash, expires_at, used_at,
                            attempt_count, request_ip, created_at)
                       VALUES (%s, %s, %s, %s, %s, 0, %s, %s)""",
                    (
                        user["id"] if user else None,
                        email,
                        code_hash,
                        now + timedelta(minutes=CODE_TTL_MINUTES),
                        used_at,
                        get_client_ip(),
                        now,
                    ),
                )
                record_id = cursor.lastrowid
            conn.commit()

            if user and mail_mode == "smtp":
                sent, mail_code = send_password_reset_email(email, code)
                if not sent:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "UPDATE password_reset_codes SET used_at=%s WHERE id=%s",
                            (utcnow(), record_id),
                        )
                    conn.commit()
                    app.logger.warning(
                        "password reset mail failed request_id=%s code=%s",
                        request_id,
                        mail_code,
                    )
                    return _error(
                        mail_code,
                        MAIL_ERROR_MESSAGES.get(mail_code, "邮件服务暂时不可用"),
                        503,
                    )

            payload = {
                "success": True,
                "code": "RESET_CODE_ACCEPTED",
                "message": GENERIC_SEND_MESSAGE,
                "msg": GENERIC_SEND_MESSAGE,
            }
            if user and code and _development_code_allowed(app):
                payload["test_code"] = code
            return jsonify(payload), 200
        except Exception as error:
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
            if _missing_reset_table(error):
                app.logger.exception(
                    "password_reset_codes table missing; apply migration "
                    "20260806_add_password_reset_codes request_id=%s",
                    request_id,
                )
            else:
                app.logger.exception(
                    "password reset send failed request_id=%s error_type=%s",
                    request_id,
                    type(error).__name__,
                )
            return _error(
                "PASSWORD_RESET_UNAVAILABLE", "密码重置服务暂不可用，请稍后重试", 503
            )
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    @app.post("/api/auth/forgot-password/reset")
    @limiter.limit("20 per hour")
    def reset_forgotten_password():
        data = request.get_json(silent=True) or {}
        email = normalize_email(data.get("email"))
        code = str(data.get("code") or "").strip()
        new_password = str(data.get("new_password") or "")
        confirm_password = str(data.get("confirm_password") or "")

        if not email or not code or not new_password or not confirm_password:
            return _error("FIELDS_REQUIRED", "请完整填写邮箱、验证码和新密码", 400)
        if not is_valid_email(email):
            return _error("EMAIL_INVALID", "邮箱格式不正确", 400)
        if not CODE_PATTERN.fullmatch(code):
            return _error("RESET_CODE_INVALID", "验证码应为六位数字", 400)
        if not is_strong_password(new_password):
            return _error(
                "PASSWORD_WEAK", "新密码至少 8 位，并且至少包含一个字母和一个数字", 400
            )
        if new_password != confirm_password:
            return _error("PASSWORD_MISMATCH", "两次输入的密码不一致", 400)

        conn = None
        now = utcnow()
        try:
            conn = get_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    """SELECT r.id, r.user_id, r.code_hash, r.expires_at,
                              r.used_at, r.attempt_count, u.username
                       FROM password_reset_codes r
                       INNER JOIN users u ON u.id=r.user_id
                       WHERE r.email=%s AND u.deleted_at IS NULL
                       ORDER BY r.created_at DESC, r.id DESC
                       LIMIT 1 FOR UPDATE""",
                    (email,),
                )
                record = cursor.fetchone()
                if not record:
                    conn.rollback()
                    return _error(
                        "RESET_CODE_INVALID", "验证码无效，请重新获取", 400
                    )
                if record.get("used_at"):
                    conn.rollback()
                    return _error(
                        "RESET_CODE_USED", "验证码已使用，请重新获取", 400
                    )
                expires_at = record.get("expires_at")
                if not expires_at or expires_at <= now:
                    cursor.execute(
                        "UPDATE password_reset_codes SET used_at=%s WHERE id=%s",
                        (now, record["id"]),
                    )
                    conn.commit()
                    return _error(
                        "RESET_CODE_EXPIRED", "验证码已过期，请重新获取", 400
                    )

                attempts = int(record.get("attempt_count") or 0)
                if attempts >= MAX_ATTEMPTS:
                    conn.rollback()
                    return _error(
                        "RESET_CODE_LOCKED", "验证码错误次数过多，请重新获取", 400
                    )
                if not hmac.compare_digest(
                    str(record.get("code_hash") or ""),
                    _code_digest(app, email, code),
                ):
                    attempts += 1
                    used_at = now if attempts >= MAX_ATTEMPTS else None
                    cursor.execute(
                        """UPDATE password_reset_codes
                           SET attempt_count=%s, used_at=%s WHERE id=%s""",
                        (attempts, used_at, record["id"]),
                    )
                    conn.commit()
                    if attempts >= MAX_ATTEMPTS:
                        return _error(
                            "RESET_CODE_LOCKED", "验证码错误次数过多，请重新获取", 400
                        )
                    return _error("RESET_CODE_INVALID", "验证码错误", 400)

                password_hash = generate_password_hash(new_password)
                cursor.execute(
                    """UPDATE users
                       SET password_hash=%s,
                           session_version=COALESCE(session_version, 0) + 1,
                           updated_at=%s
                       WHERE id=%s""",
                    (password_hash, now, record["user_id"]),
                )
                cursor.execute(
                    """UPDATE password_reset_codes SET used_at=%s
                       WHERE user_id=%s AND used_at IS NULL""",
                    (now, record["user_id"]),
                )
            conn.commit()
            return jsonify(
                {
                    "success": True,
                    "code": "PASSWORD_RESET_SUCCESS",
                    "message": "密码重置成功，请使用新密码登录",
                    "msg": "密码重置成功，请使用新密码登录",
                }
            ), 200
        except Exception as error:
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
            app.logger.exception(
                "password reset failed error_type=%s", type(error).__name__
            )
            return _error(
                "PASSWORD_RESET_UNAVAILABLE", "密码重置服务暂不可用，请稍后重试", 503
            )
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
