import pymysql
conn = pymysql.connect(host='localhost', user='root', password='password', database='nav_site', charset='utf8mb4')
cursor = conn.cursor()
cursor.execute('DESCRIBE categories')
cols = [row[0] for row in cursor.fetchall()]
print('当前categories表字段:', cols)
if 'profession_type' not in cols:
    cursor.execute("ALTER TABLE categories ADD COLUMN profession_type VARCHAR(20) DEFAULT 'general' AFTER name")
    print('已添加 profession_type 字段')
if 'sort_order' not in cols:
    cursor.execute('ALTER TABLE categories ADD COLUMN sort_order INT DEFAULT 0 AFTER profession_type')
    print('已添加 sort_order 字段')
conn.commit()
conn.close()
print('完成')
