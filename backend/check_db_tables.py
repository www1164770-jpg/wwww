"""检查数据库的表结构"""
import sqlite3
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
db_path = BACKEND_DIR / "instance" / "zhihui.db"

print(f"Checking database: {db_path}")
print(f"Database exists: {db_path.exists()}")
print()

if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 获取所有表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("Tables in database:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # 如果有 user 表，检查其结构
    table_names = [t[0] for t in tables]
    user_table = None
    if 'user' in table_names:
        user_table = 'user'
    elif 'users' in table_names:
        user_table = 'users'
    
    if user_table:
        print(f"\nStructure of '{user_table}' table:")
        cursor.execute(f"PRAGMA table_info({user_table})")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]}: {col[2]} {'NOT NULL' if col[3] else 'NULL'} {f'DEFAULT {col[4]}' if col[4] else ''}")
        
        # 检查是否有该邮箱的用户
        print(f"\nChecking for user with email 3439696693@qq.com:")
        cursor.execute(f"SELECT * FROM {user_table} WHERE email = '3439696693@qq.com'")
        user = cursor.fetchone()
        if user:
            print("USER FOUND")
            # 获取列名
            cursor.execute(f"PRAGMA table_info({user_table})")
            columns = cursor.fetchall()
            col_names = [col[1] for col in columns]
            for i, col_name in enumerate(col_names):
                if col_name == 'password_hash':
                    value = f"(length: {len(user[i]) if user[i] else 0})"
                else:
                    value = user[i]
                print(f"  {col_name}: {value}")
        else:
            print("USER NOT FOUND")
    
    conn.close()
