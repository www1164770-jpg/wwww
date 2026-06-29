import pymysql

conn = pymysql.connect(host='localhost', user='root', password='password', database='nav_site', charset='utf8mb4')
cursor = conn.cursor()

# 检查并补全 users 表
cursor.execute("SHOW TABLES")
tables = [row[0] for row in cursor.fetchall()]
print('当前数据库中的表:', tables)

# 创建 users 表（如果不存在）
if 'users' not in tables:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            avatar_url VARCHAR(255),
            email VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            dark_mode TINYINT(1) DEFAULT 0,
            custom_wallpaper TEXT,
            current_engine VARCHAR(20) DEFAULT 'bing',
            selected_engines TEXT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    print('[OK] users 表已创建')

# 创建 click_logs 表（如果不存在）
if 'click_logs' not in tables:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS click_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            website_id INT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (website_id) REFERENCES websites(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    print('[OK] click_logs 表已创建')

# 检查 websites 表字段
cursor.execute('DESCRIBE websites')
web_cols = [row[0] for row in cursor.fetchall()]
print('websites 表当前字段:', web_cols)

# 补全缺失字段
web_fields = {
    'clicks': "INT DEFAULT 0",
    'description': "VARCHAR(500) NULL",
    'status': "VARCHAR(20) DEFAULT 'approved'",
    'source': "VARCHAR(50) DEFAULT 'admin'",
    'url': "VARCHAR(500) NOT NULL",
    'logo_url': "VARCHAR(500) NULL"
}
for field, sqltype in web_fields.items():
    if field not in web_cols:
        cursor.execute(f"ALTER TABLE websites ADD COLUMN {field} {sqltype}")
        print(f'[OK] websites 已添加字段 {field}')

# 检查 users 表字段
cursor.execute('DESCRIBE users')
user_cols = [row[0] for row in cursor.fetchall()]
print('users 表当前字段:', user_cols)

user_fields = {
    'avatar_url': "VARCHAR(255) NULL",
    'email': "VARCHAR(120) UNIQUE NOT NULL",
    'password_hash': "VARCHAR(255) NOT NULL",
    'created_at': "DATETIME DEFAULT CURRENT_TIMESTAMP",
    'dark_mode': "TINYINT(1) DEFAULT 0",
    'custom_wallpaper': "TEXT NULL",
    'current_engine': "VARCHAR(20) DEFAULT 'bing'",
    'selected_engines': "TEXT NULL"
}
for field, sqltype in user_fields.items():
    if field not in user_cols:
        cursor.execute(f"ALTER TABLE users ADD COLUMN {field} {sqltype}")
        print(f'[OK] users 已添加字段 {field}')

# 检查 categories 表字段
cursor.execute('DESCRIBE categories')
cat_cols = [row[0] for row in cursor.fetchall()]
print('categories 表当前字段:', cat_cols)

cat_fields = {
    'profession_type': "VARCHAR(20) DEFAULT 'general'",
    'sort_order': "INT DEFAULT 0"
}
for field, sqltype in cat_fields.items():
    if field not in cat_cols:
        cursor.execute(f"ALTER TABLE categories ADD COLUMN {field} {sqltype}")
        print(f'[OK] categories 已添加字段 {field}')

conn.commit()
conn.close()
print('全部修复完成')
