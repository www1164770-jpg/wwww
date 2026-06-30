import os
import smtplib
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("MAIL_SERVER", "smtp.qq.com")
SMTP_PORT = int(os.getenv("MAIL_PORT", "465"))
SENDER_EMAIL = os.getenv("MAIL_USERNAME", "")
AUTH_CODE = os.getenv("MAIL_PASSWORD", "")


def send_verification_email(target_email, code):
    if not SENDER_EMAIL or not AUTH_CODE:
        return False, "Mail credentials are not configured"

    try:
        mail_content = f"""
        <div style="background-color:#f8fafc; padding:40px 20px; font-family:sans-serif;">
            <div style="max-width:500px; margin:0 auto; background-color:#ffffff; border-radius:12px; padding:30px;">
                <h2 style="color:#1e293b; margin-top:0;">Account verification</h2>
                <p style="color:#64748b; font-size:15px; line-height:1.6;">
                    Your verification code is:
                </p>
                <div style="background-color:#eff6ff; padding:15px; border-radius:10px; text-align:center; margin:25px 0;">
                    <span style="font-size:32px; font-weight:bold; color:#2563eb; letter-spacing:4px;">{code}</span>
                </div>
                <p style="color:#94a3b8; font-size:13px; margin-bottom:0;">
                    This code expires in 5 minutes. Ignore this email if you did not request it.
                </p>
            </div>
        </div>
        """

        msg = MIMEText(mail_content, "html", "utf-8")
        msg["Subject"] = "Verification code"
        msg["From"] = f"Navigation Team <{SENDER_EMAIL}>"
        msg["To"] = target_email

        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, AUTH_CODE)
        server.sendmail(SENDER_EMAIL, [target_email], msg.as_string())
        server.quit()
        return True, "sent"
    except Exception as exc:
        return False, str(exc)
