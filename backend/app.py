from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import requests
import base64

app = Flask(__name__)
CORS(app) # 开启跨域，确保前端能访问

# 数据库配置
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'weiyijie748', # 确保这是你的真实密码
    'database': 'navigation_db',
    'charset': 'utf8mb4'
}

def fetch_logo_as_base64(url):
    """国内多接口轮询，抓取图标并转为 Base64 字符串"""
    domain = url.split('//')[-1].split('/')[0]
    # 国内可直连的加速接口
    api_urls = [
        f"https://api.iowen.cn/favicon/{domain}.png",
        f"https://favicon.splitbee.io/full?url={url}",
        f"https://api.uomg.com/api/get.favicon?url={url}"
    ]
    
    for api in api_urls:
        try:
            r = requests.get(api, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            if r.status_code == 200 and len(r.content) > 300:
                # 将二进制图片转为 Base64
                b64 = base64.b64encode(r.content).decode('utf-8')
                return f"data:image/png;base64,{b64}"
        except:
            continue
    return None

@app.route('/api/cache_logo', methods=['POST'])
def cache_logo():
    data = request.json
    site_id = data.get('id')
    site_url = data.get('url')

    logo_b64 = fetch_logo_as_base64(site_url)
    
    if logo_b64:
        try:
            db = pymysql.connect(**DB_CONFIG)
            cursor = db.cursor()
            # 将 Base64 存入数据库，字段类型必须是 LONGTEXT
            cursor.execute("UPDATE websites SET logo_url = %s WHERE id = %s", (logo_b64, site_id))
            db.commit()
            db.close()
            return jsonify({'status': 'success', 'logo_url': logo_b64})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    return jsonify({'status': 'error', 'message': '抓取失败'}), 500

@app.route('/api/data', methods=['GET'])
def get_data():
    db = pymysql.connect(**DB_CONFIG)
    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM categories")
    cats = cursor.fetchall()
    cursor.execute("SELECT * FROM websites")
    sites = cursor.fetchall()
    db.close()
    return jsonify({"categories": cats, "websites": sites})

if __name__ == '__main__':
    app.run(debug=True, port=5000)