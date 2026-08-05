"""
检查 MySQL 数据库中指定邮箱的用户信息
不输出密码哈希完整值,只输出是否存在和长度
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pymysql

BACKEND_DIR = Path(__file__).resolve().parent
for env_path in (BACKEND_DIR / ".env", BACKEND_DIR.parent / ".env"):
    if env_path.exists():
        load_dotenv(env_path, override=False)

# 从环境变量读取 MySQL 配置
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "nav_site"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

print(f"Connecting to MySQL: {DB_CONFIG['user']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
print()

try:
    conn = pymysql.connect(**DB_CONFIG)
    print("✓ MySQL connection successful")
    print()
    
    test_email = "3439696693@qq.com"
    
    with conn.cursor() as cursor:
        # 检查用户是否存在
        cursor.execute(
            "SELECT id, username, email, role, status, login_provider, created_at, "
            "LENGTH(password_hash) as pwd_hash_len "
            "FROM users WHERE email = %s",
            (test_email,)
        )
        user = cursor.fetchone()
        
        if user:
            print("USER_FOUND")
            print(f"  id: {user['id']}")
            print(f"  username: {user['username'] or 'NULL'}")
            print(f"  email: {user['email']}")
            print(f"  password_hash_present: {'true' if user['pwd_hash_len'] else 'false'}")
            print(f"  password_hash_length: {user['pwd_hash_len'] or 0}")
            print(f"  role: {user['role'] or 'NULL'}")
            print(f"  status: {user['status'] or 'NULL'}")
            print(f"  login_provider: {user['login_provider'] or 'NULL'}")
            print(f"  created_at: {user['created_at'] or 'NULL'}")
        else:
            print("USER_NOT_FOUND")
            print(f"No user found with email: {test_email}")
    
    conn.close()
    
except pymysql.Error as e:
    print(f"✗ MySQL Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
