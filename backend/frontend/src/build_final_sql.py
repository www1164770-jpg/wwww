import re

# 1. 读取你之前生成的 result.txt
try:
    with open('result.txt', 'r', encoding='utf-8') as f:
        content = f.read()
except Exception as e:
    print(f"读取 result.txt 失败: {e}")
    exit()

# 2. 使用正则表达式精准提取每一行的数据
# 匹配格式: { id: xxx, category_id: xxx, name: 'xxx', url: 'xxx', logo_url: 'xxx' }
pattern = r"id:\s*(\d+),\s*category_id:\s*(\d+),\s*name:\s*'([^']*)',\s*url:\s*'([^']*)',\s*logo_url:\s*'([^']*)'"
matches = re.findall(pattern, content)

if not matches:
    print("❌ 没有从 result.txt 中提取到任何数据，请检查 result.txt 的内容格式。")
    exit()

# 3. 生成 SQL 插入语句
sql_commands = []
sql_commands.append("/* 自动生成的网站数据插入脚本 */")
sql_commands.append("DELETE FROM websites; /* 清空旧数据 */\n")

for match in matches:
    site_id, cat_id, name, url, logo = match
    
    # 处理 SQL 注入风险（将单引号转义，防止名字里带单引号报错）
    safe_name = name.replace("'", "''")
    safe_url = url.replace("'", "''")
    
    cmd = f"INSERT INTO websites (id, category_id, name, url, logo_url) VALUES ({site_id}, {cat_id}, '{safe_name}', '{safe_url}', '{logo}');"
    sql_commands.append(cmd)

# 4. 保存为最终可执行文件
with open('insert_websites_data.sql', 'w', encoding='utf-8') as f:
    f.write("\n".join(sql_commands))

print(f"✨ 成功生成 insert_websites_data.sql！共处理了 {len(matches)} 个网站。")