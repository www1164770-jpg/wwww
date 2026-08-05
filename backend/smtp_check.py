"""Standalone QQ SMTP configuration and delivery check.

Usage:
    cd backend
    python smtp_check.py --recipient <TEST_RECIPIENT>

Stages reported:
    1. Config read
    2. DNS resolution
    3. TCP connection
    4. SSL handshake
    5. SMTP login
    6. Test email delivery
"""

from __future__ import annotations

import argparse
import re
import smtplib
import socket
import ssl
import sys
from pathlib import Path

# ── env loading ──────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

for _env_path in (BACKEND_DIR / ".env", PROJECT_DIR / ".env"):
    if _env_path.exists():
        load_dotenv(_env_path, override=False)

# ── imports after path setup ─────────────────────────────────────────────────
from email_service import (  # noqa: E402
    MAIL_ERROR_MESSAGES,
    get_mail_config,
    validate_mail_config,
)

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


# ── stage helpers ─────────────────────────────────────────────────────────────

def _ok(stage: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"[OK]   {stage}{suffix}")


def _fail(stage: str, code: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    msg = MAIL_ERROR_MESSAGES.get(code, code)
    print(f"[FAIL] {stage}: {code} ({msg}){suffix}")


def run(recipient: str) -> int:
    # ── Stage 1: Config ───────────────────────────────────────────────────────
    config = get_mail_config()
    missing = validate_mail_config(config)
    if missing:
        _fail("1/6 Config read", "MAIL_CONFIG_MISSING", f"missing: {', '.join(missing)}")
        return 2

    _ok(
        "1/6 Config read",
        f"server={config['server']} port={config['port']} "
        f"ssl={config['use_ssl']} tls={config['use_tls']}",
    )

    server_host = config["server"]
    server_port = config["port"]
    timeout = config["timeout"]

    # ── Stage 2: DNS ──────────────────────────────────────────────────────────
    try:
        addrs = socket.getaddrinfo(server_host, server_port, proto=socket.IPPROTO_TCP)
        if not addrs:
            raise socket.gaierror("no address info")
        ip = addrs[0][4][0]
        _ok("2/6 DNS resolution", f"{server_host} -> {ip}")
    except socket.gaierror as exc:
        _fail("2/6 DNS resolution", "SMTP_DNS_FAILED", str(exc))
        return 1

    # ── Stage 3: TCP connection ───────────────────────────────────────────────
    try:
        sock = socket.create_connection((server_host, server_port), timeout=timeout)
        sock.close()
        _ok("3/6 TCP connection", f"{server_host}:{server_port}")
    except (socket.timeout, TimeoutError) as exc:
        _fail("3/6 TCP connection", "SMTP_CONNECTION_TIMEOUT", str(exc))
        return 1
    except (ConnectionRefusedError, PermissionError, OSError) as exc:
        err_code = "SMTP_CONNECTION_DENIED" if getattr(exc, "winerror", None) in (10013, 10061) else "SMTP_CONNECTION_FAILED"
        _fail("3/6 TCP connection", err_code, str(exc))
        return 1

    # ── Stage 4: SSL handshake ────────────────────────────────────────────────
    smtp_conn = None
    try:
        if config["use_ssl"]:
            smtp_conn = smtplib.SMTP_SSL(server_host, server_port, timeout=timeout)
            _ok("4/6 SSL handshake")
        else:
            smtp_conn = smtplib.SMTP(server_host, server_port, timeout=timeout)
            smtp_conn.ehlo()
            if config["use_tls"]:
                smtp_conn.starttls()
                smtp_conn.ehlo()
                _ok("4/6 STARTTLS handshake")
            else:
                _ok("4/6 SSL/TLS skipped (plain SMTP)")
    except ssl.SSLError as exc:
        _fail("4/6 SSL handshake", "SMTP_SSL_FAILED", str(exc))
        return 1
    except smtplib.SMTPConnectError as exc:
        _fail("4/6 SSL handshake", "SMTP_CONNECTION_FAILED", str(exc))
        return 1
    except Exception as exc:
        _fail("4/6 SSL handshake", "SMTP_SSL_FAILED", str(exc))
        return 1

    # ── Stage 5: SMTP login ───────────────────────────────────────────────────
    try:
        smtp_conn.login(config["username"], config["password"])
        _ok("5/6 SMTP login", f"user=***@{config['username'].split('@')[-1] if '@' in config['username'] else '?'}")
    except smtplib.SMTPAuthenticationError as exc:
        _fail("5/6 SMTP login", "SMTP_AUTH_FAILED", str(exc)[:80])
        try:
            smtp_conn.quit()
        except Exception:
            pass
        return 1
    except smtplib.SMTPSenderRefused as exc:
        _fail("5/6 SMTP login", "SMTP_SENDER_REJECTED", str(exc)[:80])
        try:
            smtp_conn.quit()
        except Exception:
            pass
        return 1
    except Exception as exc:
        _fail("5/6 SMTP login", "SMTP_SEND_FAILED", str(exc)[:80])
        try:
            smtp_conn.quit()
        except Exception:
            pass
        return 1

    # ── Stage 6: Send test email ──────────────────────────────────────────────
    try:
        smtp_conn.quit()
    except Exception:
        pass

    # Use the high-level helper from email_service for the actual send.
    from email_service import send_test_email  # noqa: E402

    sent, mail_code = send_test_email(recipient)
    if sent:
        _ok("6/6 Test email sent", f"recipient={recipient}")
        print("SMTP_CHECK_OK")
        return 0

    _fail("6/6 Test email sent", mail_code, MAIL_ERROR_MESSAGES.get(mail_code, ""))
    print(f"SMTP_CHECK_FAILED code={mail_code}")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="QQ SMTP 6-stage configuration and delivery check. Does not send a verification code."
    )
    parser.add_argument("--recipient", required=True, help="Test email recipient address")
    args = parser.parse_args(argv)
    addr = args.recipient.strip().lower()
    if not EMAIL_PATTERN.fullmatch(addr):
        parser.error("recipient must be a valid email address")
    return run(addr)


if __name__ == "__main__":
    raise SystemExit(main())
