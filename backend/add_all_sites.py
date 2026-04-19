import pymysql
import requests
import base64
import time

# 1. 在这里填入你想添加的所有网站名单
# category_id 参考：1:常用, 2:开发, 3:摸鱼, 4:工具, 5:AI
all_sites = [
    {"name": "京东", "url": "https://www.jd.com", "cat": 1},
    {"name": "淘宝", "url": "https://www.taobao.com", "cat": 1},
    {"name": "掘金", "url": "https://juejin.cn", "cat": 2},
    {"name": "CSDN", "url": "https://www.csdn.net", "cat": 2},
    {"name": "LeetCode", "url": "https://leetcode.cn", "cat": 2},
    {"name": "小红书", "url": "https://www.xiaohongshu.com", "cat": 3},
    {"name": "抖音", "url": "https://www.douyin.com", "cat": 3},
    {"name": "ProcessOn", "url": "https://www.processon.com", "cat": 4},
    {"name": "Kimi", "url": "https://kimi.moonshot.cn", "cat": 5},
    {"name": "DeepSeek", "url": "https://chat.deepseek.com", "cat": 5},
    # 你可以按照这个格式继续添加几十个、上百个网站...
]

# 2. 数据库配置
db_config = {
    'host': '127.0.0.1', 'user': 'root', 'password': 'weiyijie748',
    'database': 'navigation_db', 'charset': 'utf8mb4'
}

def fetch_logo_base64(url):
    domain = url.split('//')[-1].split('/')[0]
    api = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
    try:
        r = requests.get(api, timeout=5)
        if r.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(r.content).decode()}"
    except: return None
    return None

def run():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    print("🚀 开始批量注入网站数据...")
    
    for site in all_sites:
        # 检查是否已存在
        cursor.execute("SELECT id FROM websites WHERE name=%s", (site['name'],))
        if cursor.fetchone(): 
            print(f"跳过已存在的: {site['name']}")
            continue
            
        print(f"正在获取 {site['name']} 的图标...")
        logo = fetch_logo_base64(site['url'])
        
        sql = "INSERT INTO websites (category_id, name, url, logo_url) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (site['cat'], site['name'], site['url'], logo))
        conn.commit()
    
    conn.close()
    print("✅ 全部网站已加入数据库！")

if __name__ == "__main__":
    run()