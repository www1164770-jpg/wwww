# email_service.py
import smtplib
from email.mime.text import MIMEText

# ================= 邮箱基础配置 =================
# ⚠️ 强烈建议：未来正式上线时，把这几个值存入 .env 文件中读取，避免泄露
SMTP_SERVER = 'smtp.qq.com'
SMTP_PORT = 465
SENDER_EMAIL = '3439696693@qq.com'       # 替换为你的真实发件邮箱
AUTH_CODE = 'bxwhjtbwkpkldbjf'            # 替换为你刚才获取的授权码

def send_verification_email(target_email, code):
    """
    发送验证码邮件的核心函数
    :param target_email: 目标用户的邮箱
    :param code: 6位验证码
    :return: (是否成功: bool, 错误信息/成功信息: str)
    """
    try:
        # 构建高颜值的 HTML 邮件正文
        mail_content = f"""
        <div style="background-color:#f8fafc; padding:40px 20px; font-family:sans-serif;">
            <div style="max-width:500px; margin:0 auto; background-color:#ffffff; border-radius:16px; padding:30px; box-shadow:0 10px 25px rgba(0,0,0,0.05);">
                <h2 style="color:#1e293b; margin-top:0;">🚀 智汇导航 - 账号安全验证</h2>
                <p style="color:#64748b; font-size:15px; line-height:1.6;">
                    您好！感谢您注册智汇导航。<br>
                    您的专属验证码是：
                </p>
                <div style="background-color:#eff6ff; padding:15px; border-radius:12px; text-align:center; margin:25px 0;">
                    <span style="font-size:32px; font-weight:bold; color:#3b82f6; letter-spacing:4px;">{code}</span>
                </div>
                <p style="color:#94a3b8; font-size:13px; margin-bottom:0;">
                    * 验证码有效期为 5 分钟。如果这不是您的操作，请直接忽略此邮件。
                </p>
            </div>
        </div>
        """
        
        # 组装邮件结构
        msg = MIMEText(mail_content, 'html', 'utf-8')
        msg['Subject'] = '【智汇导航】您的注册验证码'
        msg['From'] = f"智汇导航团队 <{SENDER_EMAIL}>"
        msg['To'] = target_email

        # 连接服务器并发送
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, AUTH_CODE)
        server.sendmail(SENDER_EMAIL, [target_email], msg.as_string())
        server.quit() 
        
        return True, "发送成功"
        
    except Exception as e:
        print(f"❌ 邮件发送失败详细报错: {str(e)}")
        return False, str(e)