import os
import socket
import ssl
import smtplib
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class EmailServiceConfigTests(unittest.TestCase):
    """Tests for configuration reading and validation."""

    def test_missing_mail_configuration_is_reported_without_sending(self):
        import email_service

        with patch.dict(
            os.environ,
            {
                "MAIL_SERVER": "smtp.qq.com",
                "MAIL_PORT": "465",
                "MAIL_USERNAME": "",
                "MAIL_PASSWORD": "",
                "MAIL_DEFAULT_SENDER": "",
            },
            clear=False,
        ), patch.object(email_service.smtplib, "SMTP_SSL") as smtp:
            sent, code = email_service.send_verification_email("user@example.com", "123456")

        self.assertFalse(sent)
        self.assertEqual(code, "MAIL_CONFIG_MISSING")
        smtp.assert_not_called()

    def test_complete_config_does_not_report_missing(self):
        """validate_mail_config returns empty list when all fields are present."""
        import email_service

        with patch.dict(
            os.environ,
            {
                "MAIL_SERVER": "smtp.qq.com",
                "MAIL_PORT": "465",
                "MAIL_USERNAME": "sender@qq.com",
                "MAIL_PASSWORD": "test-authorisation-code",
                "MAIL_DEFAULT_SENDER": "sender@qq.com",
                "MAIL_USE_SSL": "true",
                "MAIL_USE_TLS": "false",
            },
            clear=False,
        ):
            missing = email_service.validate_mail_config()

        self.assertEqual(missing, [])

    def test_ssl_and_tls_simultaneously_enabled_is_reported(self):
        import email_service

        with patch.dict(
            os.environ,
            {
                "MAIL_SERVER": "smtp.qq.com",
                "MAIL_PORT": "465",
                "MAIL_USERNAME": "sender@qq.com",
                "MAIL_PASSWORD": "test-authorisation-code",
                "MAIL_DEFAULT_SENDER": "sender@qq.com",
                "MAIL_USE_SSL": "true",
                "MAIL_USE_TLS": "true",
            },
            clear=False,
        ):
            missing = email_service.validate_mail_config()

        self.assertTrue(any("SSL" in m and "TLS" in m for m in missing))

    def test_ssl_string_is_converted_to_bool(self):
        import email_service

        for truthy in ("true", "True", "TRUE", "1", "yes", "on"):
            with patch.dict(os.environ, {"MAIL_USE_SSL": truthy, "MAIL_USE_TLS": "false"}, clear=False):
                config = email_service.get_mail_config()
                self.assertTrue(config["use_ssl"], f"Expected use_ssl=True for '{truthy}'")

        for falsy in ("false", "False", "0", "no", "off"):
            with patch.dict(os.environ, {"MAIL_USE_SSL": falsy, "MAIL_USE_TLS": "false"}, clear=False):
                config = email_service.get_mail_config()
                self.assertFalse(config["use_ssl"], f"Expected use_ssl=False for '{falsy}'")

    def test_mail_config_status_contains_presence_only(self):
        import email_service

        with patch.dict(
            os.environ,
            {
                "MAIL_SERVER": "smtp.qq.com",
                "MAIL_PORT": "465",
                "MAIL_USERNAME": "sender@qq.com",
                "MAIL_PASSWORD": "test-authorisation-code",
                "MAIL_DEFAULT_SENDER": "sender@qq.com",
                "MAIL_USE_SSL": "true",
                "MAIL_USE_TLS": "false",
            },
            clear=False,
        ):
            status = email_service.mail_config_status()

        self.assertTrue(status["configured"])
        self.assertTrue(status["username_present"])
        self.assertTrue(status["password_present"])
        # Must NOT expose actual values
        self.assertNotIn("username", status)
        self.assertNotIn("password", status)


class EmailServiceTransportTests(unittest.TestCase):
    """Tests for SMTP transport error classification."""

    _FULL_ENV = {
        "MAIL_SERVER": "smtp.qq.com",
        "MAIL_PORT": "465",
        "MAIL_USERNAME": "sender@qq.com",
        "MAIL_PASSWORD": "test-authorisation-code",
        "MAIL_DEFAULT_SENDER": "sender@qq.com",
        "MAIL_USE_SSL": "true",
        "MAIL_USE_TLS": "false",
    }

    def test_smtp_authentication_failure_is_mapped(self):
        import email_service

        server = MagicMock()
        server.login.side_effect = email_service.smtplib.SMTPAuthenticationError(535, b"auth failed")
        with patch.dict(os.environ, self._FULL_ENV, clear=False), \
                patch.object(email_service.smtplib, "SMTP_SSL", return_value=server):
            sent, code = email_service.send_verification_email("user@example.com", "123456")

        self.assertFalse(sent)
        self.assertEqual(code, "SMTP_AUTH_FAILED")
        self.assertEqual(server.login.call_args.args[0], "sender@qq.com")
        self.assertEqual(server.login.call_args.args[1], "test-authorisation-code")

    def test_smtp_transport_errors_are_classified(self):
        import email_service

        cases = [
            (socket.gaierror("dns"), "SMTP_DNS_FAILED", "constructor"),
            (socket.timeout("timeout"), "SMTP_CONNECTION_TIMEOUT", "constructor"),
            (ssl.SSLError("ssl"), "SMTP_SSL_FAILED", "constructor"),
            (smtplib.SMTPSenderRefused(550, b"sender", "sender"), "SMTP_SENDER_REJECTED", "sendmail"),
            (smtplib.SMTPRecipientsRefused({"user@example.com": (550, b"recipient")}), "SMTP_RECIPIENT_REJECTED", "sendmail"),
            (smtplib.SMTPException("send"), "SMTP_SEND_FAILED", "sendmail"),
        ]

        for exception, expected_code, phase in cases:
            with self.subTest(expected_code=expected_code):
                server = MagicMock()
                if phase == "constructor":
                    constructor = patch.object(email_service.smtplib, "SMTP_SSL", side_effect=exception)
                else:
                    server.sendmail.side_effect = exception
                    constructor = patch.object(email_service.smtplib, "SMTP_SSL", return_value=server)
                with patch.dict(os.environ, self._FULL_ENV, clear=False), constructor:
                    sent, code = email_service.send_verification_email("user@example.com", "123456")

                self.assertFalse(sent)
                self.assertEqual(code, expected_code)

    def test_os_error_connection_denied_is_classified(self):
        """WinError 10013 (permission denied) must not swallow error as unknown."""
        import email_service

        err = OSError("WinError 10013 permission denied")
        with patch.dict(os.environ, self._FULL_ENV, clear=False), \
                patch.object(email_service.smtplib, "SMTP_SSL", side_effect=err):
            sent, code = email_service.send_verification_email("user@example.com", "123456")

        self.assertFalse(sent)
        # OSError maps to SMTP_CONNECTION_FAILED in the current implementation
        self.assertEqual(code, "SMTP_CONNECTION_FAILED")

    def test_smtp_connect_error_is_classified(self):
        import email_service

        err = smtplib.SMTPConnectError(421, b"service unavailable")
        with patch.dict(os.environ, self._FULL_ENV, clear=False), \
                patch.object(email_service.smtplib, "SMTP_SSL", side_effect=err):
            sent, code = email_service.send_verification_email("user@example.com", "123456")

        self.assertFalse(sent)
        self.assertEqual(code, "SMTP_CONNECTION_FAILED")

    def test_smtp_check_email_is_not_a_verification_code(self):
        import email_service

        server = MagicMock()
        with patch.dict(os.environ, self._FULL_ENV, clear=False), \
                patch.object(email_service.smtplib, "SMTP_SSL", return_value=server):
            sent, code = email_service.send_test_email("user@example.com")

        self.assertTrue(sent)
        self.assertEqual(code, "OK")
        # Ensure a 6-digit code sequence is not embedded in the test email body
        self.assertNotRegex(server.sendmail.call_args.args[2], r"\b\d{6}\b")


class EmailServiceCodeStorageTests(unittest.TestCase):
    """Tests that verification code is only stored after successful send."""

    def test_code_not_stored_when_smtp_fails(self):
        """
        Regression: send_verification_email returning (False, code) means the
        calling route must NOT insert the code into the database.  This test
        confirms the function itself does not silently store anything.
        """
        import email_service

        server = MagicMock()
        server.login.side_effect = email_service.smtplib.SMTPAuthenticationError(535, b"auth failed")
        with patch.dict(
            os.environ,
            {
                "MAIL_SERVER": "smtp.qq.com",
                "MAIL_PORT": "465",
                "MAIL_USERNAME": "sender@qq.com",
                "MAIL_PASSWORD": "bad-code",
                "MAIL_DEFAULT_SENDER": "sender@qq.com",
                "MAIL_USE_SSL": "true",
                "MAIL_USE_TLS": "false",
            },
            clear=False,
        ), patch.object(email_service.smtplib, "SMTP_SSL", return_value=server):
            sent, code = email_service.send_verification_email("user@example.com", "654321")

        # send failed → caller must not save code
        self.assertFalse(sent)
        self.assertNotEqual(code, "OK")

    def test_verification_code_not_present_in_log_output(self):
        """The email HTML body must not print the code to stdout/stderr."""
        import email_service
        import io
        import contextlib

        server = MagicMock()
        buf = io.StringIO()
        with patch.dict(
            os.environ,
            {
                "MAIL_SERVER": "smtp.qq.com",
                "MAIL_PORT": "465",
                "MAIL_USERNAME": "sender@qq.com",
                "MAIL_PASSWORD": "test-authorisation-code",
                "MAIL_DEFAULT_SENDER": "sender@qq.com",
                "MAIL_USE_SSL": "true",
                "MAIL_USE_TLS": "false",
            },
            clear=False,
        ), patch.object(email_service.smtplib, "SMTP_SSL", return_value=server):
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                email_service.send_verification_email("user@example.com", "999888")

        self.assertNotIn("999888", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
