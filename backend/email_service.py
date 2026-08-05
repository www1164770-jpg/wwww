"""Small, provider-agnostic SMTP service used by local account security flows."""

from __future__ import annotations

import os
import smtplib
import socket
import ssl
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
for env_path in (BACKEND_DIR / ".env", PROJECT_DIR / ".env"):
    if env_path.exists():
        load_dotenv(env_path, override=False)


MAIL_ERROR_MESSAGES = {
    "MAIL_CONFIG_MISSING": "邮件服务尚未完成配置",
    "SMTP_DNS_FAILED": "无法解析邮件服务器地址",
    "SMTP_CONNECTION_TIMEOUT": "连接邮件服务器超时，请稍后重试",
    "SMTP_CONNECTION_FAILED": "邮件服务器连接失败，请稍后重试",
    "SMTP_SSL_FAILED": "邮件服务器安全连接失败",
    "SMTP_AUTH_FAILED": "QQ 邮箱 SMTP 认证失败，请检查授权码",
    "SMTP_SENDER_REJECTED": "发件邮箱被邮件服务器拒绝",
    "SMTP_RECIPIENT_REJECTED": "收件邮箱被邮件服务器拒绝",
    "SMTP_SEND_FAILED": "邮件发送失败，请稍后重试",
    "DATABASE_FAILED": "验证码服务暂不可用，请稍后重试",
    "RATE_LIMITED": "操作过于频繁，请稍后再试",
    # Backward-compatible aliases for the password-reset and older clients.
    "MAIL_NOT_CONFIGURED": "邮件服务尚未完成配置",
    "MAIL_AUTH_FAILED": "QQ 邮箱 SMTP 认证失败，请检查授权码",
    "MAIL_CONNECTION_FAILED": "邮件服务器连接失败，请稍后重试",
    "MAIL_RECIPIENT_REJECTED": "收件邮箱被邮件服务器拒绝",
    "MAIL_SENDER_REJECTED": "发件邮箱被邮件服务器拒绝",
    "MAIL_SEND_FAILED": "邮件发送失败，请稍后重试",
}


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_mail_config() -> dict:
    server = (os.getenv("MAIL_SERVER") or "smtp.qq.com").strip()
    port_text = (os.getenv("MAIL_PORT") or "465").strip()
    try:
        port = int(port_text)
    except ValueError:
        port = 465

    username = (os.getenv("MAIL_USERNAME") or "").strip()
    password = os.getenv("MAIL_PASSWORD") or ""
    default_sender = (os.getenv("MAIL_DEFAULT_SENDER") or username).strip()
    use_ssl = _as_bool(os.getenv("MAIL_USE_SSL"), default=port == 465)
    use_tls = _as_bool(os.getenv("MAIL_USE_TLS"), default=port == 587)
    timeout_text = (os.getenv("MAIL_TIMEOUT") or "15").strip()
    try:
        timeout = max(1, int(timeout_text))
    except ValueError:
        timeout = 15

    return {
        "server": server,
        "port": port,
        "username": username,
        "password": password,
        "default_sender": default_sender,
        "use_ssl": use_ssl,
        "use_tls": use_tls,
        "timeout": timeout,
    }


def validate_mail_config(config: dict | None = None) -> list[str]:
    config = config or get_mail_config()
    missing = [
        name
        for name, value in (
            ("MAIL_SERVER", config.get("server")),
            ("MAIL_PORT", config.get("port")),
            ("MAIL_USERNAME", config.get("username")),
            ("MAIL_PASSWORD", config.get("password")),
            ("MAIL_DEFAULT_SENDER", config.get("default_sender")),
        )
        if not value
    ]
    if config.get("use_ssl") and config.get("use_tls"):
        missing.append("MAIL_USE_SSL and MAIL_USE_TLS cannot both be enabled")
    return missing


def mail_config_status() -> dict:
    config = get_mail_config()
    return {
        "configured": not validate_mail_config(config),
        "server": config["server"],
        "port": config["port"],
        "ssl": config["use_ssl"],
        "tls": config["use_tls"],
        "username_present": bool(config["username"]),
        "password_present": bool(config["password"]),
    }


def _message_html(code: str) -> str:
    return f"""
    <div style="background:#f8fafc;padding:40px 20px;font-family:sans-serif">
      <div style="max-width:500px;margin:0 auto;background:#fff;border-radius:12px;padding:30px">
        <h2 style="color:#1e293b;margin-top:0">知航屿注册验证码</h2>
        <p style="color:#64748b;font-size:15px;line-height:1.6">你的注册验证码是：</p>
        <div style="background:#eff6ff;padding:15px;border-radius:10px;text-align:center;margin:25px 0">
          <span style="font-size:32px;font-weight:bold;color:#2563eb;letter-spacing:4px">{code}</span>
        </div>
        <p style="color:#94a3b8;font-size:13px;margin-bottom:0">验证码 5 分钟内有效，请勿转发给他人。如果不是你本人操作，请忽略此邮件。</p>
      </div>
    </div>
    """


def _send_message(target_email: str, subject: str, html: str) -> tuple[bool, str]:
    config = get_mail_config()
    missing = validate_mail_config(config)
    if missing:
        return False, "MAIL_CONFIG_MISSING"

    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = config["default_sender"]
    msg["To"] = target_email

    server = None
    try:
        if config["use_ssl"]:
            server = smtplib.SMTP_SSL(config["server"], config["port"], timeout=config["timeout"])
        else:
            server = smtplib.SMTP(config["server"], config["port"], timeout=config["timeout"])
            server.ehlo()
            if config["use_tls"]:
                server.starttls()
                server.ehlo()
        server.login(config["username"], config["password"])
        server.sendmail(config["default_sender"], [target_email], msg.as_string())
        return True, "OK"
    except smtplib.SMTPSenderRefused:
        return False, "SMTP_SENDER_REJECTED"
    except smtplib.SMTPRecipientsRefused:
        return False, "SMTP_RECIPIENT_REJECTED"
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP_AUTH_FAILED"
    except socket.gaierror:
        return False, "SMTP_DNS_FAILED"
    except (socket.timeout, TimeoutError):
        return False, "SMTP_CONNECTION_TIMEOUT"
    except ssl.SSLError:
        return False, "SMTP_SSL_FAILED"
    except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, ConnectionError):
        return False, "SMTP_CONNECTION_FAILED"
    except smtplib.SMTPException:
        return False, "SMTP_SEND_FAILED"
    except OSError:
        return False, "SMTP_CONNECTION_FAILED"
    finally:
        if server is not None:
            try:
                server.quit()
            except (OSError, smtplib.SMTPException):
                pass


def send_verification_email(target_email: str, code: str) -> tuple[bool, str]:
    """Send a verification code without exposing credentials or raw errors."""
    return _send_message(target_email, "知航屿注册验证码", _message_html(code))


def send_test_email(target_email: str) -> tuple[bool, str]:
    """Send a non-sensitive diagnostic email for the standalone SMTP check."""
    html = """
    <p>知航屿 SMTP 配置测试成功。</p>
    <p>这是一封普通测试邮件，不包含验证码或账号凭据。</p>
    """
    return _send_message(target_email, "知航屿 SMTP 配置测试", html)
