import os
import smtplib
from email.mime.text import MIMEText


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def is_mail_requested():
    return _env_bool('MAIL_ENABLED', False)


def get_mail_config_status():
    required = {
        'SMTP_SERVER': os.getenv('SMTP_SERVER', '').strip(),
        'SMTP_USER': os.getenv('SMTP_USER', '').strip(),
        'SMTP_AUTH_CODE': os.getenv('SMTP_AUTH_CODE', '').strip(),
    }
    missing = [key for key, value in required.items() if not value]
    return {
        'enabled': is_mail_requested(),
        'missing': missing,
        'server': required['SMTP_SERVER'],
        'user': required['SMTP_USER'],
        'port': int(os.getenv('SMTP_PORT', '465') or 465),
        'use_ssl': _env_bool('SMTP_USE_SSL', True),
        'from_name': os.getenv('MAIL_FROM_NAME', '智汇导航').strip() or '智汇导航',
    }


def can_send_real_mail():
    status = get_mail_config_status()
    return status['enabled'] and not status['missing']


def send_verification_email(target_email, code):
    status = get_mail_config_status()
    if not status['enabled']:
        return False, '邮件服务未启用'
    if status['missing']:
        return False, '邮件配置缺失：' + '、'.join(status['missing'])

    sender = status['user']
    mail_content = f"""
    <div style="background-color:#f8fafc; padding:40px 20px; font-family:sans-serif;">
      <div style="max-width:500px; margin:0 auto; background-color:#ffffff; border-radius:16px; padding:30px; box-shadow:0 10px 25px rgba(0,0,0,0.05);">
        <h2 style="color:#1e293b; margin-top:0;">智汇导航 - 账号安全验证</h2>
        <p style="color:#64748b; font-size:15px; line-height:1.6;">
          您好，感谢您注册智汇导航。您的验证码是：
        </p>
        <div style="background-color:#eff6ff; padding:15px; border-radius:12px; text-align:center; margin:25px 0;">
          <span style="font-size:32px; font-weight:bold; color:#3b82f6; letter-spacing:4px;">{code}</span>
        </div>
        <p style="color:#94a3b8; font-size:13px; margin-bottom:0;">
          * 验证码有效期为 5 分钟。如果这不是你的操作，请忽略此邮件。
        </p>
      </div>
    </div>
    """

    msg = MIMEText(mail_content, 'html', 'utf-8')
    msg['Subject'] = '【智汇导航】您的注册验证码'
    msg['From'] = f"{status['from_name']} <{sender}>"
    msg['To'] = target_email

    server = None
    try:
        if status['use_ssl']:
            server = smtplib.SMTP_SSL(status['server'], status['port'], timeout=15)
        else:
            server = smtplib.SMTP(status['server'], status['port'], timeout=15)
            server.starttls()
        server.login(sender, os.getenv('SMTP_AUTH_CODE', '').strip())
        server.sendmail(sender, [target_email], msg.as_string())
        return True, '发送成功'
    except Exception as exc:
        print(f"邮件发送失败详细报错: {exc}")
        return False, str(exc)
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass
