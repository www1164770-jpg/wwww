import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request, redirect
from flask_cors import CORS
import requests
import time
from models import db, User, Category, Website, ClickLog
from sqlalchemy import func
from datetime import datetime, timedelta
import json
import re
from urllib.parse import urlparse
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, verify_jwt_in_request
from flask_bcrypt import Bcrypt
from authlib.integrations.flask_client import OAuth
import meilisearch
from flask_apscheduler import APScheduler
from spider import auto_fetch_hacker_news
from functools import wraps
from authing import AuthenticationClient
from sqlalchemy import text
import feedparser

# ✨ 关键点：启动时加载 .env 文件中的机密信息
load_dotenv()

app = Flask(__name__)
# 允许跨域请求
CORS(app)

# 配置数据库连接 URL (MySQL)
# 获取环境变量，如果 .env 中没有，则使用默认值
db_user = os.getenv('DB_USER', 'root')
db_pass = os.getenv('DB_PASSWORD', '')
db_host = os.getenv('DB_HOST', '127.0.0.1')
db_port = os.getenv('DB_PORT', '3306')
db_name = os.getenv('DB_NAME', 'nav_site')

# 配置数据库连接 URL (MySQL)
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'fallback-secret')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)   # Access Token 1小时过期
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)  # Refresh Token 30天过期

class UserFavorite(db.Model):
    __tablename__ = 'user_favorites'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    website_id = db.Column(db.BigInteger, nullable=False) # 使用 BigInteger 容纳 Date.now()
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

db.init_app(app)
jwt = JWTManager(app)
bcrypt = Bcrypt(app)
def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

# 1. 连接 Docker 里的引擎
meili_client = meilisearch.Client('http://127.0.0.1:7700', 'pronav_super_secret_master_key')
meili_index = meili_client.index('websites')

# 2. 【核心】配置智能排序规则 (建议放在 app 启动处执行一次)
def setup_search_engine():
    # 设定可以搜哪些字段
    meili_index.update_searchable_attributes(['name', 'url'])
    # 设定排序规则：先看匹配度，再看点击量(clicks)倒序
    meili_index.update_ranking_rules([
        "words", "typo", "proximity", "attribute", "sort", "exactness"
    ])
    meili_index.update_sortable_attributes(['clicks'])


# ================= 1. 配置 Authing 客户端 =================
# ⚠️ 这里替换为你自己的 Authing 密钥和域名
AUTHING_APP_ID = '69fdee93f62848c14ce9d3a6'
AUTHING_APP_SECRET = '381eeae3cd314fb80665a8235a03bc71'
AUTHING_APP_HOST = 'https://zhihuidh.authing.cn' 

# 初始化认证客户端
auth_client = AuthenticationClient(
    app_id=AUTHING_APP_ID,
    app_secret=AUTHING_APP_SECRET,
    app_host=AUTHING_APP_HOST
)

# ================= 2. 编写全局 Token 验证装饰器 =================
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # 1. 检查有没有带请求头
        auth_header = request.headers.get('Authorization', None)
        if not auth_header:
            return jsonify({"error": "未提供 Authorization 凭证"}), 401

        # 2. 检查 Bearer 格式
        parts = auth_header.split()
        if parts[0].lower() != 'bearer' or len(parts) != 2:
            return jsonify({"error": "请求头格式错误，应为 Bearer <token>"}), 401

        token = parts[1]

        try:
            # 3. 核心：调用 Authing 验证 Token 的合法性和时效性
            introspection_result = auth_client.introspect_token(token)

            # 4. 检查 active 字段（如果过期或伪造，active 会是 False）
            if not introspection_result.get('active'):
                return jsonify({"error": "Token 已失效或过期，请重新登录"}), 401

            # 5. 验证通过！把用户信息挂载到全局变量 g，供后续的接口随意调用
            g.current_user = introspection_result

        except Exception as e:
            return jsonify({"error": f"Token 校验失败: {str(e)}"}), 401

        return f(*args, **kwargs)
    
    return decorated


# ================= 3. 测试接口 =================

# 公开接口（谁都能访问）
@app.route('/api/public_data', methods=['GET'])
def public_data():
    return jsonify({"message": "这是公开数据"})

# 私密接口（带有 @require_auth 的保护盾）
@app.route('/api/protected/user_profile', methods=['GET'])
@require_auth
def protected_profile():
    # 走到这里，说明 Token 绝对合法，直接从 g 里面拿刚才解析出的用户信息
    user_data = g.current_user
    
    return jsonify({
        "message": "验证通过，欢迎来到私密领域！",
        "user_id": user_data.get('sub'),  # Authing 的唯一用户 ID
        "token_scopes": user_data.get('scope')
    })

# 3. 编写一键同步接口 (把 MySQL 数据搬到 Meilisearch)
@app.route('/api/admin/sync-search', methods=['POST'])
def sync_search_data():
    from models import Website # 确保你有这个模型
    sites = Website.query.all()
    
    documents = []
    for s in sites:
        documents.append({
            "id": s.id,
            "name": s.name,
            "url": s.url,
            "clicks": s.clicks or 0
        })
    
    meili_index.add_documents(documents)
    return jsonify({"message": f"成功同步 {len(documents)} 个网站到搜索引擎！"})

# --- 无感刷新 Token 接口 ---
@app.route('/api/refresh', methods=['POST', 'OPTIONS'])
def refresh():
    if request.method == 'OPTIONS':
        return jsonify({"message": "OK"}), 200
    
    # 注意这里：验证的是 refresh_token
    verify_jwt_in_request(refresh=True)
    
    # 获取当前用户 ID，签发新的 access_token
    current_user = get_jwt_identity()
    new_token = create_access_token(identity=current_user)
    
    return jsonify(access_token=new_token), 200

@app.route('/api/nav-data', methods=['GET'])
def get_nav_data():
    # 直接查库，并按照你的前端所需格式组装
    categories = Category.query.all()
    result = []
    for cat in categories:
        cat_data = {
            "id": cat.id,
            "name": cat.name,
            "sites": []
        }
        # 假设 Category 和 Website 有一对多关联 (backref='category')
        for site in cat.websites:
            cat_data["sites"].append({
                "id": site.id,
                "category_id": site.category_id,
                "name": site.name,
                "url": site.url,
                "logo_url": site.logo_url,
                "clicks": site.clicks
            })
        result.append(cat_data)
        
    return jsonify(result), 200

# 配置并启动定时任务
scheduler = APScheduler()
scheduler.init_app(app)

# 设定触发器：每天凌晨 3:00 自动执行一次
@scheduler.task('cron', id='do_hn_spider', hour=3, minute=0)
def scheduled_spider_task():
    auto_fetch_hacker_news()

# 启动调度器
scheduler.start()

# ================= 4. 垂直资讯流聚合 (RSS 穿透防火墙版) =================
@app.route('/api/news', methods=['GET'])
def get_industry_news():
    prof = request.args.get('prof', 'all')
    
    rss_map = {
        'frontend': 'https://v2ex.com/feed/programmer.xml', 
        'product': 'https://v2ex.com/feed/create.xml',       
        'ui': 'https://v2ex.com/feed/design.xml',            
        'all': 'https://v2ex.com/index.xml'                  
    }
    
    url = rss_map.get(prof, rss_map['all'])
    
    try:
        # ✨ 1. 挂上本地代理 (如果你的代理不是 7890，请改成你自己的端口)
        my_proxies = {
            'http': 'http://127.0.0.1:7890',
            'https': 'http://127.0.0.1:7890'
        }
        
        # ✨ 2. 先用 requests 强行穿透墙壁拉取 XML 文本
        import requests
        response = requests.get(url, proxies=my_proxies, timeout=10)
        xml_data = response.text
        
        # ✨ 3. 再把拉到的纯文本喂给 feedparser 进行解析
        feed = feedparser.parse(xml_data)
        
        news_list = []
        for entry in feed.entries[:8]:
            news_list.append({
                'title': entry.title,
                'link': entry.link,
                'source': feed.feed.title if hasattr(feed.feed, 'title') else '行业快讯'
            })
            
        return jsonify(news_list), 200
    except Exception as e:
        import traceback
        traceback.print_exc() # 在终端打印真实报错原因
        return jsonify({'error': str(e)}), 500
# ================= 爬虫手动测试接口 =================
@app.route('/api/admin/run-spider', methods=['POST'])
def trigger_spider_manually():
    # 为了演示直接同步调用。在生产环境中，耗时爬虫建议扔给 Celery 等异步队列
    auto_fetch_hacker_news(app)
    return jsonify({"message": "✅ 爬虫执行完毕！快去前端的【审核工作台】看看有没有新货吧！"})

# ================= 1. 模拟数据库 (保持不变) =================
categories_db = [
    {"id": 1, "name": "常用推荐"},
    {"id": 2, "name": "开发社区"},
    {"id": 3, "name": "摸鱼娱乐"},
    {"id": 4, "name": "实用工具"},
    {"id": 5, "name": "AI 神器"}
]

websites_db = [
    # ===== 分类 1：常用推荐 =====
    {"id": 101, "category_id": 1, "name": "哔哩哔哩", "url": "https://www.bilibili.com", "logo_url": "", "clicks": 1250},
    {"id": 102, "category_id": 1, "name": "知乎", "url": "https://www.zhihu.com", "logo_url": "", "clicks": 856},
    {"id": 103, "category_id": 1, "name": "微博", "url": "https://weibo.com", "logo_url": "", "clicks": 720},
    {"id": 104, "category_id": 1, "name": "淘宝", "url": "https://www.taobao.com", "logo_url": "", "clicks": 1100},
    {"id": 105, "category_id": 1, "name": "京东", "url": "https://www.jd.com", "logo_url": "", "clicks": 980},
    {"id": 106, "category_id": 1, "name": "百度", "url": "https://www.baidu.com", "logo_url": "", "clicks": 2000},
    {"id": 107, "category_id": 1, "name": "腾讯视频", "url": "https://v.qq.com", "logo_url": "", "clicks": 650},
    {"id": 108, "category_id": 1, "name": "爱奇艺", "url": "https://www.iqiyi.com", "logo_url": "", "clicks": 600},
    {"id": 109, "category_id": 1, "name": "优酷", "url": "https://www.youku.com", "logo_url": "", "clicks": 480},
    {"id": 110, "category_id": 1, "name": "网易云音乐", "url": "https://music.163.com", "logo_url": "", "clicks": 870},
    {"id": 111, "category_id": 1, "name": "QQ音乐", "url": "https://y.qq.com", "logo_url": "", "clicks": 760},
    {"id": 112, "category_id": 1, "name": "天猫", "url": "https://www.tmall.com", "logo_url": "", "clicks": 890},
    {"id": 113, "category_id": 1, "name": "拼多多", "url": "https://www.pinduoduo.com", "logo_url": "", "clicks": 950},
    {"id": 114, "category_id": 1, "name": "12306", "url": "https://www.12306.cn", "logo_url": "", "clicks": 430},
    {"id": 115, "category_id": 1, "name": "高德地图", "url": "https://www.amap.com", "logo_url": "", "clicks": 560},

    # ===== 分类 2：开发社区 =====
    {"id": 201, "category_id": 2, "name": "GitHub", "url": "https://github.com", "logo_url": "", "clicks": 980},
    {"id": 202, "category_id": 2, "name": "GitLab", "url": "https://gitlab.com", "logo_url": "", "clicks": 420},
    {"id": 203, "category_id": 2, "name": "Gitee", "url": "https://gitee.com", "logo_url": "", "clicks": 380},
    {"id": 204, "category_id": 2, "name": "掘金", "url": "https://juejin.cn", "logo_url": "", "clicks": 430},
    {"id": 205, "category_id": 2, "name": "CSDN", "url": "https://www.csdn.net", "logo_url": "", "clicks": 560},
    {"id": 206, "category_id": 2, "name": "博客园", "url": "https://www.cnblogs.com", "logo_url": "", "clicks": 310},
    {"id": 207, "category_id": 2, "name": "Stack Overflow", "url": "https://stackoverflow.com", "logo_url": "", "clicks": 670},
    {"id": 208, "category_id": 2, "name": "MDN Web Docs", "url": "https://developer.mozilla.org", "logo_url": "", "clicks": 590},
    {"id": 209, "category_id": 2, "name": "npm", "url": "https://www.npmjs.com", "logo_url": "", "clicks": 480},
    {"id": 210, "category_id": 2, "name": "Docker Hub", "url": "https://hub.docker.com", "logo_url": "", "clicks": 350},
    {"id": 211, "category_id": 2, "name": "LeetCode", "url": "https://leetcode.cn", "logo_url": "", "clicks": 720},
    {"id": 212, "category_id": 2, "name": "牛客网", "url": "https://www.nowcoder.com", "logo_url": "", "clicks": 540},
    {"id": 213, "category_id": 2, "name": "V2EX", "url": "https://www.v2ex.com", "logo_url": "", "clicks": 390},
    {"id": 214, "category_id": 2, "name": "SegmentFault", "url": "https://segmentfault.com", "logo_url": "", "clicks": 280},
    {"id": 215, "category_id": 2, "name": "Vercel", "url": "https://vercel.com", "logo_url": "", "clicks": 460},

    # ===== 分类 3：摸鱼娱乐 =====
    {"id": 301, "category_id": 3, "name": "抖音", "url": "https://www.douyin.com", "logo_url": "", "clicks": 520},
    {"id": 302, "category_id": 3, "name": "小红书", "url": "https://www.xiaohongshu.com", "logo_url": "", "clicks": 480},
    {"id": 303, "category_id": 3, "name": "微信读书", "url": "https://weread.qq.com", "logo_url": "", "clicks": 320},
    {"id": 304, "category_id": 3, "name": "豆瓣", "url": "https://www.douban.com", "logo_url": "", "clicks": 410},
    {"id": 305, "category_id": 3, "name": "虎扑", "url": "https://www.hupu.com", "logo_url": "", "clicks": 290},
    {"id": 306, "category_id": 3, "name": "NGA玩家社区", "url": "https://nga.178.com", "logo_url": "", "clicks": 260},
    {"id": 307, "category_id": 3, "name": "Steam", "url": "https://store.steampowered.com", "logo_url": "", "clicks": 680},
    {"id": 308, "category_id": 3, "name": "Epic Games", "url": "https://www.epicgames.com", "logo_url": "", "clicks": 350},
    {"id": 309, "category_id": 3, "name": "网易游戏", "url": "https://game.163.com", "logo_url": "", "clicks": 420},
    {"id": 310, "category_id": 3, "name": "腾讯游戏", "url": "https://game.qq.com", "logo_url": "", "clicks": 510},
    {"id": 311, "category_id": 3, "name": "漫画柜", "url": "https://www.manhuagui.com", "logo_url": "", "clicks": 230},
    {"id": 312, "category_id": 3, "name": "哔哩哔哩漫画", "url": "https://manga.bilibili.com", "logo_url": "", "clicks": 280},
    {"id": 313, "category_id": 3, "name": "网易新闻", "url": "https://news.163.com", "logo_url": "", "clicks": 370},
    {"id": 314, "category_id": 3, "name": "今日头条", "url": "https://www.toutiao.com", "logo_url": "", "clicks": 440},
    {"id": 315, "category_id": 3, "name": "虎嗅", "url": "https://www.huxiu.com", "logo_url": "", "clicks": 310},

    # ===== 分类 4：实用工具 =====
    {"id": 401, "category_id": 4, "name": "ProcessOn", "url": "https://www.processon.com", "logo_url": "", "clicks": 380},
    {"id": 402, "category_id": 4, "name": "Excalidraw", "url": "https://excalidraw.com", "logo_url": "", "clicks": 290},
    {"id": 403, "category_id": 4, "name": "TinyPNG", "url": "https://tinypng.com", "logo_url": "", "clicks": 450},
    {"id": 404, "category_id": 4, "name": "Squoosh", "url": "https://squoosh.app", "logo_url": "", "clicks": 220},
    {"id": 405, "category_id": 4, "name": "Carbon", "url": "https://carbon.now.sh", "logo_url": "", "clicks": 310},
    {"id": 406, "category_id": 4, "name": "Regex101", "url": "https://regex101.com", "logo_url": "", "clicks": 340},
    {"id": 407, "category_id": 4, "name": "JSON格式化", "url": "https://jsonformatter.curiousconcept.com", "logo_url": "", "clicks": 280},
    {"id": 408, "category_id": 4, "name": "Can I Use", "url": "https://caniuse.com", "logo_url": "", "clicks": 390},
    {"id": 409, "category_id": 4, "name": "Notion", "url": "https://www.notion.so", "logo_url": "", "clicks": 620},
    {"id": 410, "category_id": 4, "name": "飞书", "url": "https://www.feishu.cn", "logo_url": "", "clicks": 540},
    {"id": 411, "category_id": 4, "name": "腾讯文档", "url": "https://docs.qq.com", "logo_url": "", "clicks": 480},
    {"id": 412, "category_id": 4, "name": "石墨文档", "url": "https://shimo.im", "logo_url": "", "clicks": 320},
    {"id": 413, "category_id": 4, "name": "百度翻译", "url": "https://fanyi.baidu.com", "logo_url": "", "clicks": 560},
    {"id": 414, "category_id": 4, "name": "DeepL翻译", "url": "https://www.deepl.com", "logo_url": "", "clicks": 490},
    {"id": 415, "category_id": 4, "name": "Cloudflare", "url": "https://www.cloudflare.com", "logo_url": "", "clicks": 270},
    {"id": 416, "category_id": 4, "name": "iLovePDF", "url": "https://www.ilovepdf.com", "logo_url": "", "clicks": 350},
    {"id": 417, "category_id": 4, "name": "Convertio", "url": "https://convertio.co", "logo_url": "", "clicks": 300},
    {"id": 418, "category_id": 4, "name": "Unsplash", "url": "https://unsplash.com", "logo_url": "", "clicks": 410},

    # ===== 分类 5：AI 神器 =====
    {"id": 501, "category_id": 5, "name": "ChatGPT", "url": "https://chat.openai.com", "logo_url": "", "clicks": 760},
    {"id": 502, "category_id": 5, "name": "Claude", "url": "https://claude.ai", "logo_url": "", "clicks": 580},
    {"id": 503, "category_id": 5, "name": "Gemini", "url": "https://gemini.google.com", "logo_url": "", "clicks": 490},
    {"id": 504, "category_id": 5, "name": "文心一言", "url": "https://yiyan.baidu.com", "logo_url": "", "clicks": 420},
    {"id": 505, "category_id": 5, "name": "通义千问", "url": "https://tongyi.aliyun.com", "logo_url": "", "clicks": 380},
    {"id": 506, "category_id": 5, "name": "讯飞星火", "url": "https://xinghuo.xfyun.cn", "logo_url": "", "clicks": 310},
    {"id": 507, "category_id": 5, "name": "Kimi", "url": "https://kimi.moonshot.cn", "logo_url": "", "clicks": 450},
    {"id": 508, "category_id": 5, "name": "豆包", "url": "https://www.doubao.com", "logo_url": "", "clicks": 390},
    {"id": 509, "category_id": 5, "name": "Midjourney", "url": "https://www.midjourney.com", "logo_url": "", "clicks": 520},
    {"id": 510, "category_id": 5, "name": "Stable Diffusion", "url": "https://stability.ai", "logo_url": "", "clicks": 340},
    {"id": 511, "category_id": 5, "name": "Runway", "url": "https://runwayml.com", "logo_url": "", "clicks": 280},
    {"id": 512, "category_id": 5, "name": "Suno AI", "url": "https://suno.ai", "logo_url": "", "clicks": 360},
    {"id": 513, "category_id": 5, "name": "GitHub Copilot", "url": "https://github.com/features/copilot", "logo_url": "", "clicks": 470},
    {"id": 514, "category_id": 5, "name": "Cursor", "url": "https://www.cursor.com", "logo_url": "", "clicks": 530},
    {"id": 515, "category_id": 5, "name": "Perplexity", "url": "https://www.perplexity.ai", "logo_url": "", "clicks": 410},
    {"id": 516, "category_id": 5, "name": "Hugging Face", "url": "https://huggingface.co", "logo_url": "", "clicks": 350},
    {"id": 517, "category_id": 5, "name": "DeepSeek", "url": "https://www.deepseek.com", "logo_url": "", "clicks": 620},
    {"id": 518, "category_id": 5, "name": "智谱清言", "url": "https://chatglm.cn", "logo_url": "", "clicks": 290},
]


# ================= 🛡️ 用户认证与 JWT API =================

# 1. 注册接口
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({"error": "用户名、邮箱和密码不能为空"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "用户名已被占用"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "邮箱已被注册"}), 400

    # ✨ 核心：使用 bcrypt 哈希密码
    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username, email=email, password_hash=pw_hash)
    
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "注册成功，请登录"}), 201

# 2. 登录接口
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    # 根据邮箱查找用户
    user = User.query.filter_by(email=email).first()
    
    # ✨ 核心：校验哈希密码
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "邮箱或密码错误"}), 401

    # 生成双 Token (把 user.id 作为身份标识存入 token)
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "message": "登录成功",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    }), 200
# ================= 🔒 受保护的管理后台路由示例 =================

@app.route('/api/admin/dashboard', methods=['GET'])
@jwt_required() # ✨ 这个装饰器要求请求头必须带 Authorization: Bearer <access_token>
def admin_dashboard():
    # 只有合法用户能走到这一步
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    return jsonify({
        "message": f"欢迎尊贵的管理员 {user.username}！",
        "secret_data": "这是只有登录用户才能看到的后台数据统计。"
    }), 200
# ================= 2. 基础 API 路由 (保持不变) =================

@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify({"categories": categories_db, "websites": websites_db})

# ================= 1. 自动抓取 Hacker News 热门站点 (SQLAlchemy 版) =================
@app.route('/api/admin/crawl_hn', methods=['POST'])
def crawl_hacker_news():
    try:
        my_proxies = {
            'http': 'http://127.0.0.1:7890',
            'https': 'http://127.0.0.1:7890'
        }
        # 获取 HN 最热的 30 篇文章 ID
        top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        story_ids = requests.get(top_stories_url).json()[:30]
        
        added_count = 0
        
        for story_id in story_ids:
            story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
            story_info = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json").json()
            
            if story_info and 'url' in story_info:
                url = story_info['url']
                title = story_info.get('title', '未知站点')
                
                # 查重 1：检查待审核表
                is_in_pending = db.session.execute(text("SELECT id FROM pending_sites WHERE url = :url"), {'url': url}).fetchone()
                
                # ✨ 完美融合：直接用你现成的 Website 模型去正式表里查重！
                is_in_sites = Website.query.filter_by(url=url).first()
                
                if not is_in_pending and not is_in_sites:
                    # 写入待审核库
                    db.session.execute(
                        text("INSERT INTO pending_sites (name, url, description, source) VALUES (:name, :url, :desc, :source)"),
                        {'name': title, 'url': url, 'desc': title, 'source': 'Hacker News'}
                    )
                    added_count += 1
        
        db.session.commit()
        return jsonify({'message': f'抓取完成！成功发现 {added_count} 个新站点待审核。'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ================= 2. 获取待审核站点列表 =================
@app.route('/api/admin/pending_sites', methods=['GET'])
def get_pending_sites():
    try:
        result = db.session.execute(text("SELECT id, name, url, description, source FROM pending_sites WHERE status = 'pending' ORDER BY created_at DESC"))
        sites = []
        for row in result:
            sites.append({
                'id': row[0],
                'name': row[1],
                'url': row[2],
                'description': row[3],
                'source': row[4]
            })
        return jsonify(sites), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================= 3. 审核操作 (通过 或 拒绝) =================
@app.route('/api/admin/review_site', methods=['POST'])
def review_site():
    data = request.json
    site_id = data.get('id')
    action = data.get('action')
    category_id = data.get('category_id', 1)
    
    try:
        if action == 'approve':
            # 1. 查出待审核数据
            site_row = db.session.execute(text("SELECT name, url, description FROM pending_sites WHERE id = :id"), {'id': site_id}).fetchone()
            if site_row:
                # ✨ 完美融合：直接实例化你的 Website 模型，让它按照你的规则生成数据！
                new_site = Website(name=site_row[0], url=site_row[1], category_id=category_id)
                db.session.add(new_site)
                
                # 更新待审核表状态
                db.session.execute(text("UPDATE pending_sites SET status = 'approved' WHERE id = :id"), {'id': site_id})
        
        elif action == 'reject':
            db.session.execute(text("UPDATE pending_sites SET status = 'rejected' WHERE id = :id"), {'id': site_id})
            
        db.session.commit()
        return jsonify({'message': '审核操作成功'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
# backend/app.py
# ✨ 1. 全网基础热度（保持不变）
BASE_HOTNESS = {
    # 常用推荐
    "百度": 200000, "哔哩哔哩": 50000, "知乎": 30000, "微博": 45000,
    "淘宝": 80000, "京东": 70000, "腾讯视频": 35000, "爱奇艺": 32000,
    "优酷": 20000, "网易云音乐": 40000, "QQ音乐": 38000, "天猫": 65000,
    "拼多多": 55000, "12306": 18000, "高德地图": 22000,
    # 开发社区
    "GitHub": 25000, "GitLab": 8000, "Gitee": 7000, "掘金": 10000,
    "CSDN": 15000, "博客园": 6000, "Stack Overflow": 18000, "MDN Web Docs": 12000,
    "npm": 9000, "Docker Hub": 7500, "LeetCode": 20000, "牛客网": 14000,
    "V2EX": 8500, "SegmentFault": 5000, "Vercel": 9500,
    # 摸鱼娱乐
    "抖音": 80000, "小红书": 42000, "微信读书": 15000, "豆瓣": 18000,
    "虎扑": 12000, "NGA玩家社区": 10000, "Steam": 28000, "Epic Games": 14000,
    "网易游戏": 17000, "腾讯游戏": 22000, "漫画柜": 8000, "哔哩哔哩漫画": 9000,
    "网易新闻": 16000, "今日头条": 35000, "虎嗅": 11000,
    # 实用工具
    "Notion": 25000, "飞书": 20000, "腾讯文档": 18000, "石墨文档": 10000,
    "百度翻译": 22000, "DeepL翻译": 19000, "TinyPNG": 12000, "Can I Use": 9000,
    "Regex101": 8000, "Carbon": 7000, "ProcessOn": 11000, "Unsplash": 13000,
    # AI 神器
    "ChatGPT": 60000, "Claude": 35000, "Gemini": 28000, "文心一言": 20000,
    "通义千问": 18000, "讯飞星火": 14000, "Kimi": 22000, "豆包": 19000,
    "Midjourney": 26000, "DeepSeek": 30000, "GitHub Copilot": 21000,
    "Cursor": 24000, "Perplexity": 16000, "Hugging Face": 13000,
    "Suno AI": 12000, "Runway": 10000, "智谱清言": 9000, "Stable Diffusion": 11000,
}

# ===== 热度缓存：存储上一次抓取的各网站热度，用于计算涨跌率 =====
_hotness_cache = {}
_hotness_cache_time = {}


def fetch_online_hotness():
    global _hotness_cache
    # 1. 获取当前数据库中所有真实的网站 name (或 ID)
    current_site_names = {site.name for site in Website.query.all()}
    
    # 2. 清理：只保留存在于当前数据库中的网站热度数据
    _hotness_cache = {name: data for name, data in _hotness_cache.items() if name in current_site_names}
    """从多个公开热榜 API 抓取实时热度，返回 {网站名: 热度分数}"""
    hotness = {}
    hdrs = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
    }
    # 源1：微博实时热搜
    try:
        r = requests.get('https://weibo.com/ajax/side/hotSearch',
            headers={**hdrs, 'Referer': 'https://weibo.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', {}).get('realtime', [])
            hotness['微博'] = sum(int(x.get('num', 0)) for x in items[:50])
    except Exception:
        pass
    # 源2：知乎热榜
    try:
        r = requests.get('https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50',
            headers={**hdrs, 'Referer': 'https://www.zhihu.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', [])
            total = 0
            for item in items:
                raw = item.get('detail_text', '0').replace('万热度', '').replace('万', '')
                try:
                    total += int(float(raw) * 10000)
                except Exception:
                    total += 5000
            hotness['知乎'] = total
    except Exception:
        pass
    # 源3：百度实时热搜
    try:
        r = requests.get('https://top.baidu.com/api/board?platform=wise&tab=realtime',
            headers={**hdrs, 'Referer': 'https://top.baidu.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', {}).get('cards', [{}])[0].get('content', [])
            hotness['百度'] = sum(int(x.get('hotScore', 0)) for x in items[:30])
    except Exception:
        pass
    # 源4：今日头条热榜
    try:
        r = requests.get('https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc',
            headers={**hdrs, 'Referer': 'https://www.toutiao.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', [])
            hotness['今日头条'] = sum(int(x.get('HotValue', 0)) for x in items[:30])
    except Exception:
        pass
    # 源5：GitHub Trending 今日 Star 增量
    try:
        r = requests.get('https://api.gitterapp.com/repositories?since=daily',
            headers=hdrs, timeout=6)
        if r.status_code == 200:
            repos = r.json()
            hotness['GitHub'] = sum(int(x.get('stars', 0)) for x in repos[:25]) * 10
    except Exception:
        pass
    # 源6：哔哩哔哩热门视频播放量
    try:
        r = requests.get('https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all',
            headers={**hdrs, 'Referer': 'https://www.bilibili.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', {}).get('list', [])
            hotness['哔哩哔哩'] = sum(int(x.get('stat', {}).get('view', 0)) for x in items[:20])
    except Exception:
        pass
    # 源7：抖音热榜
    try:
        r = requests.get('https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/',
            headers={**hdrs, 'Referer': 'https://www.douyin.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('word_list', [])
            hotness['抖音'] = sum(int(x.get('hot_value', 0)) for x in items[:30])
    except Exception:
        pass
    return hotness

# ================= 1. 上传/更新配置到云端 =================
@app.route('/api/user/sync', methods=['POST'])
@jwt_required()
def sync_user_settings():
    data = request.json
    username = data.get('username')
    
    if not username:
        return jsonify({"error": "未登录"}), 401

    # 查找用户，如果没有就顺手创建一个（兼容你目前的手机号模拟登录逻辑）
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username)
        db.session.add(user)

    # 同步各项配置
    if 'dark_mode' in data:
        user.dark_mode = data['dark_mode']
    if 'custom_wallpaper' in data:
        user.custom_wallpaper = data['custom_wallpaper']
    if 'current_engine' in data:
        user.current_engine = data['current_engine']
    if 'selected_engines' in data:
        user.selected_engines = json.dumps(data['selected_engines']) # 列表转为字符串存储
    if 'avatar_url' in data:
        user.avatar_url = data['avatar_url']

    db.session.commit()
    return jsonify({"success": True, "message": "配置已同步到云端 ☁️"})

# ================= 2. 登录时拉取云端配置 =================
@app.route('/api/user/settings', methods=['GET'])
def get_user_settings():
    username = request.args.get('username')
    
    if not username:
        return jsonify({"error": "缺少用户名"}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "找不到用户"}), 404

    return jsonify({
        "dark_mode": user.dark_mode,
        "custom_wallpaper": user.custom_wallpaper,
        "current_engine": user.current_engine,
        "selected_engines": json.loads(user.selected_engines) if user.selected_engines else None,
        "avatar_url": user.avatar_url
    })

@app.route('/api/ranking', methods=['GET'])
def get_ranking():
    global _hotness_cache, _hotness_cache_time
    try:
        current = fetch_online_hotness()
        ranking_data = []
        all_sites_db = Website.query.all()
        for site in all_sites_db:
            name = site.name
            cur_score = current.get(name, 0)
            last_score = _hotness_cache.get(name, 0)
            if last_score > 0 and cur_score > 0:
                rate = round((cur_score - last_score) / last_score * 100, 1)
            elif cur_score > 0 and last_score == 0:
                rate = 100.0
            else:
                rate = 0.0
            delta = cur_score - last_score
            base = BASE_HOTNESS.get(name, 0)
            sort_score = cur_score + base // 100
            ranking_data.append({
                'id': site.id,
                'name': name,
                'url': site.url,
                'clicks': cur_score,
                'delta': delta,
                'growth_rate': rate,
                'sort_score': sort_score,
            })
        for name, score in current.items():
            _hotness_cache[name] = score
            _hotness_cache_time[name] = time.time()
        ranking_data.sort(key=lambda x: (abs(x['growth_rate']), x['sort_score']), reverse=True)
        return jsonify(ranking_data[:10])
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
@app.route('/api/click', methods=['POST'])
def record_click():
    data = request.json
    site_id = data.get('id')
    
    if not site_id:
        return jsonify({"error": "缺少网站ID"}), 400
        
    site = Website.query.get(site_id)
    if site:
        # 1. 历史总点击量依然累加
        site.clicks += 1  
        
        # 2. ✨ 新增：生成一条带有时间戳的“热搜流水”记录
        new_log = ClickLog(website_id=site.id)
        db.session.add(new_log)
        
        db.session.commit()
        return jsonify({"success": True, "new_clicks": site.clicks})
    
    return jsonify({"error": "找不到该网站"}), 404

@app.route('/api/cache_logo', methods=['POST'])
def cache_logo():
    data = request.json
    site_id = data.get('id')
    url = data.get('url')
    if url:
        domain = url.split('//')[-1].split('/')[0].replace('www.', '')
        logo_url = f"https://www.google.com/s2/favicons?sz=128&domain={domain}"
        for site in websites_db:
            if site['id'] == site_id:
                site['logo_url'] = logo_url
                break
        return jsonify({"status": "success", "logo_url": logo_url})
    return jsonify({"status": "error", "message": "无效的 URL"})

# --- 1. 获取收藏列表 API ---
# 加上 OPTIONS 方法，让浏览器的跨域预检顺利通过
@app.route('/api/favorites', methods=['GET', 'OPTIONS'])
def get_favorites():
    # 如果是跨域预检请求，直接放行
    if request.method == 'OPTIONS':
        return jsonify({"message": "OK"}), 200
        
    # 验证 Token
    verify_jwt_in_request() 
    user_id = get_jwt_identity()
    favorites = UserFavorite.query.filter_by(user_id=user_id).all()
    fav_ids = [fav.website_id for fav in favorites]
    return jsonify(fav_ids), 200

# --- 2. 切换收藏状态 API ---
@app.route('/api/favorites', methods=['POST', 'OPTIONS'])
def toggle_favorite():
    if request.method == 'OPTIONS':
        return jsonify({"message": "OK"}), 200
        
    verify_jwt_in_request()
    user_id = get_jwt_identity()
    data = request.get_json()
    website_id = data.get('website_id')

    if not website_id:
        return jsonify({"error": "缺少 website_id"}), 400

    existing_fav = UserFavorite.query.filter_by(user_id=user_id, website_id=website_id).first()
    
    if existing_fav:
        db.session.delete(existing_fav)
        db.session.commit()
        return jsonify({"status": "removed", "message": "已取消收藏"}), 200
    else:
        new_fav = UserFavorite(user_id=user_id, website_id=website_id)
        db.session.add(new_fav)
        db.session.commit()
        return jsonify({"status": "added", "message": "收藏成功"}), 201

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    time.sleep(1) 
    reply = "收到！但我现在还是个模拟数据。你可以试着在输入框里包含“设计”、“摸鱼”或“代码”等关键词。"
    if "设计" in user_message:
        reply = "找设计灵感吗？强烈推荐你去看看 Dribbble、Behance 或者站酷！"
    elif "摸鱼" in user_message or "游戏" in user_message:
        reply = "偷偷告诉你，工作累了可以去刷刷 B站 或者 抖音 放松一下~"
    elif "代码" in user_message or "开发" in user_message or "前端" in user_message:
        reply = "推荐多看 GitHub 的开源项目，遇到 Bug 直接上 StackOverflow 搜！"
    return jsonify({"reply": reply})


# ================= 1. 配置 OAuth =================
# 注意：在本地测试时，必须允许 HTTP 传输 OAuth token
os.environ['AUTHLIB_INSECURE_TRANSPORT'] = '1'

oauth = OAuth(app)
github = oauth.register(
    name='github',
    client_id='你的_GITHUB_CLIENT_ID',         # 去 GitHub Developer Settings 获取
    client_secret='你的_GITHUB_CLIENT_SECRET', # 去 GitHub Developer Settings 获取
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

# ================= 2. 触发登录路由 =================
@app.route('/api/login/github')
def login_github():
    # 生成回调地址，告诉 GitHub 授权完跳回哪里
    redirect_uri = url_for('github_callback', _external=True)
    return github.authorize_redirect(redirect_uri)
# ================= 3. GitHub 回调 (✨ 安全升级版) =================
@app.route('/api/github/callback', methods=['GET'])
def github_callback():
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "缺少授权码 (code)"}), 400

    # ✨ 从系统的环境变量中安全读取，取代原来的明文密码
    CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
    CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')

    if not CLIENT_ID or not CLIENT_SECRET:
        return jsonify({"error": "服务器未配置 GitHub 密钥，请检查 .env 文件！"}), 500

    # 用 code 换取 Access Token
    token_response = requests.post(
        'https://github.com/login/oauth/access_token',
        data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'code': code
        },
        headers={'Accept': 'application/json'}
    )
    
    token_json = token_response.json()
    access_token = token_json.get('access_token')

    if not access_token:
         return jsonify({"error": "获取 Access Token 失败", "details": token_json}), 400

    # 获取用户信息
    user_response = requests.get(
        'https://api.github.com/user',
        headers={'Authorization': f'token {access_token}'}
    )
    user_data = user_response.json()

    username = user_data.get('login', 'GitHub用户')
    avatar = user_data.get('avatar_url', '')

    frontend_url = f"http://localhost:5173/?login=success&username={username}&avatar={avatar}"
    print(f"🎉 GitHub 登录成功！用户: {username}")
    return redirect(frontend_url)


@app.route('/api/admin/audit-site/<int:site_id>', methods=['POST'])
def audit_site(site_id):
    from models import db, Website
    site = Website.query.get_or_404(site_id)
    
    action = request.json.get('action') # 'approve' 或 'reject'
    
    if action == 'approve':
        # 1. 更新 MySQL 数据库
        site.status = 'approved'
        db.session.commit()
        
        # 2. ✨ 核心联动：同步推送到 Meilisearch 极速搜索引擎 ✨
        try:
            client = meilisearch.Client('http://127.0.0.1:7700', 'pronav_super_secret_master_key')
            index = client.index('websites')
            
            # 组装成搜索引擎需要的格式
            document = {
                "id": str(site.id),
                "name": site.name,
                "url": site.url,
                "description": site.description,
                "clicks": site.clicks or 0
            }
            # 推送！
            index.add_documents([document])
            print(f"🌍 [引擎同步] 成功将 {site.name} 推送至 Meilisearch!")
            
        except Exception as e:
            print(f"⚠️ [引擎报错] Meilisearch 同步失败: {e}")
            
        return jsonify({"message": "已批准上线，并秒级同步至搜索引擎！"})
        
    elif action == 'reject':
        db.session.delete(site)
        db.session.commit()
        return jsonify({"message": "已残忍拒绝并销毁！"})
        
    return jsonify({"error": "未知操作"}), 400
# ================= 网站资源 RESTful API =================

# 1. 获取列表 (GET) - 支持分页、分类筛选、搜索
@app.route('/api/websites', methods=['GET'])
def get_websites():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category_id = request.args.get('category', type=int)
    search = request.args.get('search', type=str)

    query = Website.query

    if category_id:
        query = query.filter_by(category_id=category_id)
    if search:
        query = query.filter(Website.name.ilike(f'%{search}%'))

    # 使用 SQLAlchemy 自带的分页 (基于 LIMIT 和 OFFSET)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "data": [{
            "id": s.id, "name": s.name, "url": s.url, 
            "category_id": s.category_id, "clicks": s.clicks
        } for s in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page
    })

# 2. 新增网站 (POST)
@app.route('/api/websites', methods=['POST'])
def create_website():
    data = request.json
    name = data.get('name')
    url = data.get('url')
    category_id = data.get('category') 

    # 字段校验
    if not name or not url:
        return jsonify({"error": "name和url为必填项"}), 400
    if not is_valid_url(url):
        return jsonify({"error": "URL格式不正确，需包含http/https"}), 400

    new_site = Website(name=name, url=url, category_id=category_id)
    db.session.add(new_site)
    db.session.commit()
    return jsonify({"message": "创建成功", "id": new_site.id}), 201

# 3. 获取单个详情 (GET)
@app.route('/api/websites/<int:id>', methods=['GET'])
def get_website(id):
    site = Website.query.get(id)
    if not site:
        return jsonify({"error": "网站不存在"}), 404
    return jsonify({"id": site.id, "name": site.name, "url": site.url, "category_id": site.category_id})

# 4. 更新网站 (PUT)
@app.route('/api/websites/<int:id>', methods=['PUT'])
def update_website(id):
    site = Website.query.get(id)
    if not site:
        return jsonify({"error": "网站不存在"}), 404
        
    data = request.json
    if 'name' in data: 
        site.name = data['name']
    if 'url' in data:
        if not is_valid_url(data['url']):
            return jsonify({"error": "URL格式不正确"}), 400
        site.url = data['url']
    if 'category_id' in data: 
        site.category_id = data['category_id']

    db.session.commit()
    return jsonify({"message": "更新成功"})

# 5. 删除网站 (DELETE)
@app.route('/api/websites/<int:id>', methods=['DELETE'])
def delete_website(id):
    site = Website.query.get(id)
    if not site:
        return jsonify({"message": "该网站不存在，无法删除"}), 404
        
    db.session.delete(site)
    db.session.commit()
    return jsonify({"message": "删除成功"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # 启动时自动同步所有分类和网站到数据库
        try:
            from init_db import all_categories, all_sites, get_logo_url
            import pymysql

            env_db = {
                'host': os.getenv('DB_HOST', '127.0.0.1'),
                'user': os.getenv('DB_USER', 'root'),
                'password': os.getenv('DB_PASSWORD', ''),
                'database': os.getenv('DB_NAME', 'nav_site'),
                'charset': 'utf8mb4'
            }
            conn = pymysql.connect(**env_db)
            cur = conn.cursor()

            # 同步分类
            for cat in all_categories:
                cat_id, profession, name, sort = cat
                cur.execute(
                    "INSERT INTO categories (id,name,profession_type,sort_order) VALUES (%s,%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE name=%s, profession_type=%s, sort_order=%s",
                    (cat_id, name, profession, sort, name, profession, sort)
                )

            # 同步网站（跳过已存在的）
            new_count = 0
            for site in all_sites:
                cur.execute("SELECT id FROM websites WHERE name=%s AND category_id=%s",
                            (site['name'], site['cat']))
                if not cur.fetchone():
                    logo = get_logo_url(site['url'])
                    cur.execute(
                        "INSERT INTO websites (category_id,name,url,logo_url) VALUES (%s,%s,%s,%s)",
                        (site['cat'], site['name'], site['url'], logo)
                    )
                    new_count += 1

            conn.commit()
            conn.close()
            if new_count > 0:
                print(f"✅ 启动同步：新增 {new_count} 个网站")
            else:
                print(f"✅ 数据库已是最新，共 {len(all_sites)} 条网站数据")
        except Exception as e:
            print(f"⚠️  启动同步失败（不影响运行）: {e}")

    print("🚀 智汇导航后端服务已启动！正在监听 http://127.0.0.1:5000 ...")
    app.run(host='0.0.0.0', port=5000, debug=True)