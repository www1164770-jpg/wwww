"""
检查数据库中指定邮箱的用户信息
不输出密码哈希完整值,只输出是否存在和长度
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
for env_path in (BACKEND_DIR / ".env", BACKEND_DIR.parent / ".env"):
    if env_path.exists():
        load_dotenv(env_path, override=False)

sys.path.insert(0, str(BACKEND_DIR))
from models import db, User
from flask import Flask

app = Flask(__name__)
# 使用实际的数据库路径
db_path = BACKEND_DIR / "instance" / "zhihui.db"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{db_path}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

print(f"Using database: {app.config['SQLALCHEMY_DATABASE_URI']}")
print()

def check_user(email):
    with app.app_context():
        user = User.query.filter(
            func.lower(User.email) == email.lower()
        ).first()
        
        if user:
            print("USER_FOUND")
            print(f"id={user.id}")
            print(f"username={user.username or 'NULL'}")
            print(f"email={user.email}")
            print(f"password_hash_present={'true' if user.password_hash else 'false'}")
            print(f"password_hash_length={len(user.password_hash) if user.password_hash else 0}")
            print(f"role={user.role or 'NULL'}")
            print(f"status={user.status or 'NULL'}")
            print(f"login_provider={user.login_provider or 'NULL'}")
            print(f"created_at={user.created_at or 'NULL'}")
            
            # 检查 Authing 相关字段
            authing_fields = []
            if hasattr(user, 'authing_sub') and user.authing_sub:
                authing_fields.append('authing_sub')
            if hasattr(user, 'authing_id') and user.authing_id:
                authing_fields.append('authing_id')
            if hasattr(user, 'external_id') and user.external_id:
                authing_fields.append('external_id')
            
            if authing_fields:
                print(f"authing_fields_present={','.join(authing_fields)}")
            else:
                print("authing_fields_present=none")
        else:
            print("USER_NOT_FOUND")

if __name__ == "__main__":
    from sqlalchemy import func
    test_email = "3439696693@qq.com"
    check_user(test_email)
