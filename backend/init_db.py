import pymysql
import requests
import base64
import time

DB_CONFIG = {
    'host': '127.0.0.1', 'user': 'root', 'password': 'weiyijie748',
    'database': 'navigation_db', 'charset': 'utf8mb4'
}

# 把你想加的网站全部丢进来，只要有网址就行
all_sites = [
    {"name": "京东", "url": "https://www.jd.com", "cat": 1},
    {"name": "淘宝", "url": "https://www.taobao.com", "cat": 1},
    {"name": "掘金", "url": "https://juejin.cn", "cat": 2},
    {"name": "CSDN", "url": "https://www.csdn.net", "cat": 2},
    {"name": "小红书", "url": "https://www.xiaohongshu.com", "cat": 3},
    {"name": "Kimi", "url": "https://kimi.moonshot.cn", "cat": 5},
    {"name": "DeepSeek", "url": "https://chat.deepseek.com", "cat": 5},
]

def fetch_logo(url):
    domain = url.split('//')[-1].split('/')[0]
    api_urls = [
        f"https://api.iowen.cn/favicon/{domain}.png",
        f"https://favicon.splitbee.io/full?url={url}",
        f"https://api.uomg.com/api/get.favicon?url={url}"
    ]
    for api in api_urls:
        try:
            r = requests.get(api, timeout=5)
            if r.status_code == 200 and len(r.content) > 300:
                return f"data:image/png;base64,{base64.b64encode(r.content).decode()}"
        except: continue
    return None

def run():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    for site in all_sites:
        cursor.execute("SELECT id FROM websites WHERE name=%s", (site['name'],))
        if cursor.fetchone(): continue # 已经存在的跳过
            
        print(f"正在抓取 {site['name']} ...")
        logo = fetch_logo(site['url'])
        
        sql = "INSERT INTO websites (category_id, name, url, logo_url) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (site['cat'], site['name'], site['url'], logo))
        conn.commit()
        time.sleep(0.2)
        
    conn.close()
    print("✅ 批量注入并离线化完成！")

if __name__ == "__main__":
    run()