"""
智汇导航后端主应用模块
========================
本文件是整个后端服务的核心入口，基于 Flask 框架构建。

主要功能模块：
  1. 用户认证与授权（JWT 双 Token 机制 + Authing 第三方认证 + GitHub OAuth 登录）
  2. 网站导航数据管理（分类、网站的增删改查 RESTful API）
  3. 全文搜索引擎集成（Meilisearch 极速搜索）
  4. 实时热度排行榜（多源热榜数据聚合）
  5. 爬虫与内容审核工作台（Hacker News 自动抓取 + 人工审核流程）
  6. 用户收藏夹管理
  7. 行业资讯 RSS 聚合
  8. 定时任务调度（APScheduler）
  9. 用户个性化配置云同步

运行方式：
  python app.py
  服务默认监听 http://0.0.0.0:5000
"""

import os  # 操作系统接口，用于读取环境变量和文件路径
from dotenv import load_dotenv  # 从 .env 文件加载环境变量，保护敏感配置不硬编码
from flask import Flask, jsonify, request, redirect, g, url_for  # Flask 核心：应用实例、JSON响应、请求对象、重定向
from flask_cors import CORS  # 跨域资源共享扩展，允许前端跨域调用后端接口
import requests  # HTTP 客户端库，用于调用第三方 API 和爬取外部数据
import time  # 时间工具，用于时间戳记录和延迟控制
from models import db, User, Category, Website, ClickLog  # 导入 SQLAlchemy 数据库实例及所有数据模型
from sqlalchemy import func, or_  # SQLAlchemy 聚合函数与条件组合工具
import json  # JSON 序列化/反序列化，用于存储复杂配置字段
import re  # 正则表达式，用于 URL 格式校验等文本处理
from urllib.parse import urlparse  # URL 解析工具，用于验证 URL 合法性
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, verify_jwt_in_request  # JWT 认证扩展：Token 管理器、创建/验证 Token 的工具函数
from flask_bcrypt import Bcrypt  # 密码哈希扩展，使用 bcrypt 算法安全存储用户密码
from authlib.integrations.flask_client import OAuth  # OAuth 2.0 客户端，用于 GitHub 第三方登录
import meilisearch  # Meilisearch 搜索引擎客户端，提供毫秒级全文搜索能力
from flask_apscheduler import APScheduler  # 定时任务调度器，用于定时执行爬虫等后台任务
from spider import auto_fetch_hacker_news  # 自定义爬虫模块，自动抓取 Hacker News 热门站点
from functools import wraps  # 装饰器工具，用于保留被装饰函数的元信息
from authing import AuthenticationClient  # Authing 身份云客户端，用于 Token 校验和用户管理
from sqlalchemy import text  # SQLAlchemy 原生 SQL 执行工具，用于执行复杂的原始 SQL 语句
import feedparser  # RSS/Atom Feed 解析库，用于抓取和解析行业资讯订阅源
import redis
import pymysql
import smtplib
import random
import logging
import traceback
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from concurrent.futures import ThreadPoolExecutor
from email_service import can_send_real_mail, get_mail_config_status, is_mail_requested, send_verification_email
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# 导入连接池模块
from db_pool import get_connection as pool_get_connection

# 导入扩展模块
import app_extensions

# ✨ 关键点：启动时加载 .env 文件中的机密信息
load_dotenv()  # 将 .env 文件中的键值对注入到系统环境变量，后续通过 os.getenv() 读取

app = Flask(__name__)  # 创建 Flask 应用实例，__name__ 用于确定资源文件的根路径

# Redis is optional in local development. If it is not running, rate limiting
# must not break every API request before it reaches the route handler.
def get_limiter_storage_uri():
    redis_uri = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    try:
        redis.StrictRedis.from_url(redis_uri, decode_responses=True).ping()
        return redis_uri
    except Exception as exc:
        print(f"Redis unavailable, using in-memory limiter storage: {exc}")
        return 'memory://'


class SafeRedis:
    def get(self, *args, **kwargs):
        return None

    def setex(self, *args, **kwargs):
        return False

    def delete(self, *args, **kwargs):
        return 0

    def incr(self, *args, **kwargs):
        return 0

    def sismember(self, *args, **kwargs):
        return False

    def sadd(self, *args, **kwargs):
        return 0

    def srem(self, *args, **kwargs):
        return 0

    def scard(self, *args, **kwargs):
        return 0

    def zrange(self, *args, **kwargs):
        return []

    def zrevrange(self, *args, **kwargs):
        return []

    def zadd(self, *args, **kwargs):
        return 0


def make_redis_client():
    redis_uri = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    try:
        client = redis.StrictRedis.from_url(redis_uri, decode_responses=True)
        client.ping()
        return client
    except Exception as exc:
        print(f"Redis unavailable, using no-op redis client: {exc}")
        return SafeRedis()


#初始化接口防刷限制器
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["5000 per day", "1000 per hour"], # 全局默认限制：每个 IP 每天最多 5000 次请求
    storage_uri=get_limiter_storage_uri()
)

# 初始化 Redis 和 线程池
redis_client = make_redis_client()
executor = ThreadPoolExecutor(max_workers=10)

# 数据库配置（请改成你自己的！）
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'weiyijie748',
    'database': 'nav_site',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    """从连接池获取一个数据库连接（推荐使用此函数替代直连）"""
    return pool_get_connection()

def async_save_click(item_id):
    """异步将点击日志写入 MySQL"""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "INSERT INTO click_log (item_id) VALUES (%s)"
            cursor.execute(sql, (item_id,))
        connection.commit()
        connection.close()
    except Exception as e:
        print(f"写入点击日志失败: {e}")

# ================= 修改密码接口 =================
@app.route('/api/user/password', methods=['POST'])
@jwt_required()
def change_password():
    # 获取当前请求人的身份 (如果是按之前的逻辑，这里可能是 username)
    username = get_jwt_identity() 
    data = request.json
    
    old_pwd = data.get('old_password')
    new_pwd = data.get('new_password')

    if not old_pwd or not new_pwd:
        return jsonify({'code': 400, 'msg': '密码参数不完整'}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. 字段名改为 password_hash
            cursor.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'code': 404, 'msg': '找不到该用户'}), 404
                
            # 2. 统一使用 werkzeug 的 check_password_hash
            if not check_password_hash(user['password_hash'], old_pwd):
                return jsonify({'code': 401, 'msg': '旧密码输入错误！'}), 401
                
            # 3. 统一使用 werkzeug 的 generate_password_hash 加密新密码
            hashed_new_pwd = generate_password_hash(new_pwd)
            
            # 4. 更新 password_hash 字段
            cursor.execute("UPDATE users SET password_hash = %s WHERE username = %s", (hashed_new_pwd, username))
        conn.commit()
        return jsonify({'code': 0, 'msg': '密码修改成功'})
    except Exception as e:
        return jsonify({'code': 500, 'msg': f'服务器错误: {str(e)}'}), 500
    finally:
        conn.close()

# ================= 1. 发送真实邮件验证码 =================
@app.route('/api/auth/send-code', methods=['POST'])
@limiter.limit("1 per minute", error_message="发送太频繁，请 1 分钟后再试")
def send_verification_code():
    payload = request.get_json(silent=True) or {}
    email = (payload.get('email') or '').strip()
    if not email:
        return jsonify({'code': 400, 'msg': '邮箱不能为空'}), 400

    code = str(random.randint(100000, 999999))
    mail_status = get_mail_config_status()
    real_mail_requested = is_mail_requested()
    real_mail_ready = can_send_real_mail()

    if real_mail_requested and mail_status['missing']:
        return jsonify({
            'code': 500,
            'msg': '邮件配置缺失：' + '、'.join(mail_status['missing'])
        }), 500

    if real_mail_requested and isinstance(redis_client, SafeRedis):
        return jsonify({'code': 500, 'msg': '真实邮件模式需要可用的 Redis 来保存验证码'}), 500

    try:
        redis_client.setex(f"verify_code:{email}", 300, code)
    except Exception as exc:
        if real_mail_requested:
            return jsonify({'code': 500, 'msg': f'验证码存储失败：{str(exc)}'}), 500
        print(f"[DEV] Redis 不可用，注册时将允许任意非空验证码。目标邮箱：{email}")

    if not real_mail_ready:
        print(f"[DEV] {email} 的注册验证码是：{code}")
        return jsonify({'code': 0, 'msg': '开发模式验证码已生成，请查看后端控制台'})

    is_success, error_message = send_verification_email(email, code)
    if is_success:
        return jsonify({'code': 0, 'msg': '验证码已发送，请查收邮箱'})

    return jsonify({'code': 500, 'msg': f'邮件发送失败：{error_message}'}), 500
    
# ================= 2. 用户注册 =================
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    username, email, password, code = data.get('username'), data.get('email'), data.get('password'), data.get('code')
    
    # 1. 校验验证码
    saved_code = redis_client.get(f"verify_code:{email}")
    if not isinstance(redis_client, SafeRedis) and (not saved_code or saved_code != code):
        return jsonify({'code': 400, 'msg': '验证码错误或已过期'})
    if isinstance(redis_client, SafeRedis) and not code:
        return jsonify({'code': 400, 'msg': '请输入验证码'})
        
    # 2. 密码加密
    hashed_pw = generate_password_hash(password)
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 唯一性由数据库 UNIQUE 约束保障，这里直接执行插入
            cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)", 
                           (username, email, hashed_pw))
        conn.commit()
        conn.close()
        # 注册成功后删除验证码
        redis_client.delete(f"verify_code:{email}")
        return jsonify({'code': 0, 'msg': '注册成功'})
    except Exception as e:
        return jsonify({'code': 400, 'msg': '用户名或邮箱已存在'})

# ================= 3. 用户登录 =================
@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute", error_message="密码尝试次数过多，请稍后再试")
def login():
    payload = request.get_json(silent=True) or {}
    account, password = payload.get('account'), payload.get('password')
    if not account or not password:
        return jsonify({'code': 400, 'msg': '账号和密码不能为空'}), 400
    
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # 支持用户名或邮箱登录，同时过滤掉已注销的账户
        cursor.execute("SELECT * FROM users WHERE (username = %s OR email = %s) AND deleted_at IS NULL", (account, account))
        user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        # 签发 JWT Token
        access_token = create_access_token(identity=user['username'])
        refresh_token = create_refresh_token(identity=user['username'])
        return jsonify({
            'code': 0,
            'msg': '登录成功',
            'token': access_token,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'data': {
                'token': access_token,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': {
                    'id': user.get('id'),
                    'username': user.get('username'),
                    'email': user.get('email'),
                    'avatar': user.get('avatar_url') or '',
                    'has_survey': user.get('has_survey') or 0,
                    'user_tags': user.get('user_tags') or user.get('interests') or ''
                }
            }
        })
        
    return jsonify({'code': 401, 'msg': '账号或密码错误'}), 401

# ================= 4. 注销账户 (逻辑删除 + 7天冷静期) =================
@app.route('/api/user/delete-account', methods=['POST'])
@jwt_required()
def delete_account():
    username = get_jwt_identity()
    password = request.json.get('password')
    
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if not check_password_hash(user['password_hash'], password):
            return jsonify({'code': 401, 'msg': '密码验证失败'})
            
        # 逻辑删除：打上时间戳
        cursor.execute("UPDATE users SET deleted_at = %s WHERE username = %s", (datetime.now(), username))
    conn.commit()
    conn.close()
    
    return jsonify({'code': 0, 'msg': '账号已进入 7 天注销冷静期'})

# ================= 核心计算函数：计算点击增长率 =================
def calculate_and_cache_growth_rate():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 核心 SQL: 聚合今日和昨日的点击数据
            # 注意：如果你的网站表不叫 websites，请将下方的 websites 改为实际表名
            sql = """
                SELECT 
                    log.item_id,
                    i.name as title,
                    i.logo_url as cover_url,
                    SUM(CASE WHEN DATE(log.clicked_at) = CURDATE() THEN 1 ELSE 0 END) AS today_clicks,
                    SUM(CASE WHEN DATE(log.clicked_at) = DATE_SUB(CURDATE(), INTERVAL 1 DAY) THEN 1 ELSE 0 END) AS yesterday_clicks
                FROM click_log log
                JOIN websites i ON log.item_id = i.id
                WHERE log.clicked_at >= DATE_SUB(CURDATE(), INTERVAL 1 DAY)
                GROUP BY log.item_id
            """
            cursor.execute(sql)
            results = cursor.fetchall()
        conn.close()

        leaderboard = []
        for row in results:
            today = row['today_clicks']
            yesterday = row['yesterday_clicks']
            
            if today == 0: continue # 今日无点击不参与排行

            if yesterday == 0 and today > 0:
                growth_rate = 100.0
            else:
                growth_rate = ((today - yesterday) / yesterday) * 100.0

            leaderboard.append({
                'id': row['item_id'],
                'title': row['title'],
                'cover_url': row['cover_url'],
                'today_clicks': int(today),
                'growth_rate': round(growth_rate, 1)
            })

        # 按涨幅降序排列，取 Top 50
        leaderboard.sort(key=lambda x: (x['growth_rate'], x['today_clicks']), reverse=True)
        top_50 = leaderboard[:50]

        # 尝试存入 Redis，如果 Redis 没开就跳过，直接返回数据
        try:
            redis_client.setex("leaderboard:growth_rate", 300, json.dumps(top_50))
        except Exception as redis_e:
            pass 

        return top_50
    except Exception as e:
        print(f"计算排行榜严重异常: {e}")
        return []

# 允许跨域请求
CORS(app)  # 开启全局跨域支持，允许前端（如 localhost:5173）访问后端接口

# ===== 生产级日志配置 =====
app = app_extensions.setup_logging(app)

# ===== 全局异常处理器注册 =====
app = app_extensions.register_error_handlers(app)

# ===== 数据库连接配置 =====
# 从环境变量读取数据库连接参数，如果 .env 中没有配置则使用默认值
db_user = os.getenv('DB_USER', 'root')          # 数据库用户名
db_pass = os.getenv('DB_PASSWORD', '')           # 数据库密码
db_host = os.getenv('DB_HOST', '127.0.0.1')     # 数据库主机地址
db_port = os.getenv('DB_PORT', '3306')           # 数据库端口（MySQL 默认 3306）
db_name = os.getenv('DB_NAME', 'nav_site')       # 数据库名称

# 配置数据库连接 URL (MySQL)
# 格式：mysql+pymysql://用户名:密码@主机:端口/数据库名?字符集
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 关闭对象修改追踪，节省内存，避免不必要的警告

# ===== JWT Token 配置 =====
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'fallback-secret')  # JWT 签名密钥，生产环境必须使用强随机字符串
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)   # Access Token 1小时过期，用于日常接口鉴权
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)  # Refresh Token 30天过期，用于无感刷新 Access Token

class UserFavorite(db.Model):
    """
    用户收藏夹数据模型

    记录用户收藏的网站，支持多用户各自维护独立的收藏列表。
    与 users 表通过外键关联，website_id 使用 BigInteger 以兼容前端
    用 Date.now() 生成的毫秒级时间戳作为临时 ID 的场景。
    """
    __tablename__ = 'user_favorites'  # 对应数据库中的表名
    id = db.Column(db.Integer, primary_key=True)  # 收藏记录的自增主键
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 关联的用户 ID（外键）
    website_id = db.Column(db.BigInteger, nullable=False) # 使用 BigInteger 容纳 Date.now()
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
db.init_app(app)   # 将 SQLAlchemy 数据库实例与 Flask 应用绑定
jwt = JWTManager(app)   # 初始化 JWT 管理器，处理 Token 的签发与验证
bcrypt = Bcrypt(app)    # 初始化 bcrypt 密码哈希工具，用于安全存储用户密码


def ok(data=None, msg='ok', status=200):
    return jsonify({'code': 0, 'msg': msg, 'data': data}), status


def fail(msg='error', code=400, status=400, data=None):
    return jsonify({'code': code, 'msg': msg, 'data': data}), status


def get_current_user_id():
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    return user.id if user else None


def site_to_dict(site, category_name=None):
    return {
        'id': site.id,
        'category_id': site.category_id,
        'category_name': category_name or (site.category.name if getattr(site, 'category', None) else ''),
        'name': site.name,
        'url': site.url,
        'logo_url': site.logo_url or '',
        'description': site.description or '',
        'clicks': site.clicks or 0,
        'status': site.status or 'approved',
        'source': site.source or 'admin',
        'quality_score': 0.8,
        'popularity_score': min((site.clicks or 0) / 1000, 1),
        'tags': [],
        'occupations': [],
    }


def add_site_metadata(items):
    """Attach tag/occupation metadata when optional MVP tables exist."""
    ids = [item['id'] for item in items]
    if not ids:
        return items

    tag_map = {site_id: [] for site_id in ids}
    occupation_map = {site_id: [] for site_id in ids}

    try:
        rows = db.session.execute(
            text("""
                SELECT st.site_id, t.name
                FROM site_tags st
                JOIN tags t ON t.id = st.tag_id
                WHERE st.site_id IN :ids
            """),
            {'ids': tuple(ids)}
        ).fetchall()
        for site_id, tag_name in rows:
            tag_map.setdefault(site_id, []).append(tag_name)
    except Exception:
        pass

    try:
        rows = db.session.execute(
            text("SELECT site_id, occupation FROM site_occupations WHERE site_id IN :ids"),
            {'ids': tuple(ids)}
        ).fetchall()
        for site_id, occupation in rows:
            occupation_map.setdefault(site_id, []).append(occupation)
    except Exception:
        pass

    for item in items:
        item['tags'] = tag_map.get(item['id'], [])
        item['occupations'] = occupation_map.get(item['id'], [])
        if item['tags']:
            item['description'] = item['description'] or '适合 ' + '、'.join(item['tags'][:3])
    return items


def log_user_behavior(action, website_id=None, keyword=None):
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_current_user_id() if get_jwt_identity() else None
    except Exception:
        user_id = None

    try:
        db.session.execute(
            text("""
                INSERT INTO user_behavior (user_id, website_id, action, keyword)
                VALUES (:user_id, :website_id, :action, :keyword)
            """),
            {
                'user_id': user_id,
                'website_id': website_id,
                'action': action,
                'keyword': keyword,
            }
        )
        db.session.commit()
    except Exception:
        db.session.rollback()

def is_valid_url(url):
    """
    校验 URL 格式是否合法。

    使用 urllib.parse.urlparse 解析 URL，检查是否同时包含
    协议（scheme，如 http/https）和域名（netloc）两个必要部分。

    参数：
        url (str): 待校验的 URL 字符串

    返回：
        bool: URL 格式合法返回 True，否则返回 False
    """
    try:
        result = urlparse(url)  # 解析 URL 为各组成部分
        return all([result.scheme, result.netloc])  # 必须同时有协议和域名才算合法
    except ValueError:
        return False  # 解析异常时视为非法 URL

# ===== Meilisearch 搜索引擎初始化 =====
# 1. 连接 Docker 里的引擎
meili_client = meilisearch.Client('http://127.0.0.1:7700', 'pronav_super_secret_master_key')  # 连接本地 Meilisearch 实例，第二个参数为主密钥
meili_index = meili_client.index('websites')  # 获取名为 'websites' 的搜索索引（相当于数据库中的一张表）

# 2. 【核心】配置智能排序规则 (建议放在 app 启动处执行一次)
def setup_search_engine():
    """
    初始化 Meilisearch 搜索引擎的索引配置。

    设置可搜索字段和排序规则，确保搜索结果既准确又按热度排序。
    此函数建议在应用启动时调用一次，后续无需重复执行。
    """
    # 设定可以搜哪些字段
    meili_index.update_searchable_attributes(['name', 'url'])  # 只对网站名称和 URL 建立全文索引
    # 设定排序规则：先看匹配度，再看点击量(clicks)倒序
    meili_index.update_ranking_rules([
        "words", "typo", "proximity", "attribute", "sort", "exactness"
    ])
    meili_index.update_sortable_attributes(['clicks'])  # 允许按点击量字段排序


# ================= 1. 配置 Authing 客户端 =================
# ⚠️ 这里替换为你自己的 Authing 密钥和域名
AUTHING_APP_ID = '69fdee93f62848c14ce9d3a6'          # Authing 应用的唯一标识符（App ID）
AUTHING_APP_SECRET = '381eeae3cd314fb80665a8235a03bc71'  # Authing 应用密钥，用于服务端 Token 校验（勿泄露）
AUTHING_APP_HOST = 'https://zhihuidh.authing.cn'     # Authing 应用的专属域名（用户池域名）

# 初始化认证客户端
auth_client = AuthenticationClient(
    app_id=AUTHING_APP_ID,
    app_secret=AUTHING_APP_SECRET,
    app_host=AUTHING_APP_HOST
)

# ================= 2. 编写全局 Token 验证装饰器 =================
def require_auth(f):
    """
    Authing Token 验证装饰器（用于保护需要登录才能访问的接口）。

    使用方式：在路由函数上方添加 @require_auth 即可启用保护。
    验证流程：
      1. 检查请求头中是否携带 Authorization 字段
      2. 验证 Bearer Token 格式是否正确
      3. 调用 Authing 服务端接口校验 Token 的合法性和有效期
      4. 验证通过后将用户信息挂载到 Flask 全局变量 g 上

    参数：
        f: 被装饰的路由函数

    返回：
        decorated: 包装后的函数，具备 Token 验证能力
    """
    @wraps(f)  # 保留原函数的 __name__、__doc__ 等元信息，避免路由注册冲突
    def decorated(*args, **kwargs):
        # 1. 检查有没有带请求头
        auth_header = request.headers.get('Authorization', None)
        if not auth_header:
            return jsonify({"error": "未提供 Authorization 凭证"}), 401

        # 2. 检查 Bearer 格式
        parts = auth_header.split()
        if parts[0].lower() != 'bearer' or len(parts) != 2:
            return jsonify({"error": "请求头格式错误，应为 Bearer <token>"}), 401

        token = parts[1]  # 提取 Token 字符串

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
    """
    公开数据接口（无需认证）。

    接口路径：GET /api/public_data
    功能描述：返回一条公开消息，用于测试接口连通性。
    参数：无
    返回：JSON 格式的公开消息
    """
    return jsonify({"message": "这是公开数据"})

# 私密接口（带有 @require_auth 的保护盾）
@app.route('/api/protected/user_profile', methods=['GET'])
@require_auth
def protected_profile():
    """
    受保护的用户信息接口（需要 Authing Token 认证）。

    接口路径：GET /api/protected/user_profile
    请求方法：GET
    功能描述：验证 Authing Token 后，返回当前登录用户的基本信息。
    请求头：Authorization: Bearer <authing_token>
    返回：
        200 - 用户 ID 和 Token 权限范围
        401 - Token 无效或未提供
    """
    # 走到这里，说明 Token 绝对合法，直接从 g 里面拿刚才解析出的用户信息
    user_data = g.current_user
    
    return jsonify({
        "message": "验证通过，欢迎来到私密领域！",
        "user_id": user_data.get('sub'),  # Authing 的唯一用户 ID
        "token_scopes": user_data.get('scope')  # Token 授权的权限范围
    })

# 3. 编写一键同步接口 (把 MySQL 数据搬到 Meilisearch)
@app.route('/api/admin/sync-search', methods=['POST'])
def sync_search_data():
    """
    将 MySQL 中的网站数据全量同步到 Meilisearch 搜索引擎。

    接口路径：POST /api/admin/sync-search
    请求方法：POST
    功能描述：读取数据库中所有网站记录，批量写入 Meilisearch 索引，
              使搜索引擎数据与数据库保持一致。适合在数据库大批量更新后手动触发。
    参数：无
    返回：
        200 - 同步成功，包含同步数量
        500 - 同步失败
    """
    from models import Website # 确保你有这个模型
    sites = Website.query.all()  # 查询数据库中所有网站记录
    
    documents = []  # 准备要写入搜索引擎的文档列表
    for s in sites:
        documents.append({
            "id": s.id,          # 文档唯一标识，与数据库主键对应
            "name": s.name,      # 网站名称，用于全文搜索
            "url": s.url,        # 网站地址，用于全文搜索
            "clicks": s.clicks or 0  # 点击量，用于热度排序（None 时默认为 0）
        })
    
    meili_index.add_documents(documents)  # 批量写入 Meilisearch（已存在则更新，不存在则新增）
    return jsonify({"message": f"成功同步 {len(documents)} 个网站到搜索引擎！"})

# --- 无感刷新 Token 接口 ---
@app.route('/api/refresh', methods=['POST', 'OPTIONS'])
def refresh():
    """
    无感刷新 Access Token 接口。

    接口路径：POST /api/refresh
    请求方法：POST（OPTIONS 用于跨域预检）
    功能描述：使用有效的 Refresh Token 换取新的 Access Token，
              实现用户登录状态的无感续期，无需重新输入密码。
    请求头：Authorization: Bearer <refresh_token>
    返回：
        200 - 新的 access_token
        401 - Refresh Token 无效或已过期
    """
    if request.method == 'OPTIONS':
        return jsonify({"message": "OK"}), 200  # 直接放行跨域预检请求
    
    # 注意这里：验证的是 refresh_token
    verify_jwt_in_request(refresh=True)  # 明确指定验证 Refresh Token 而非 Access Token
    
    # 获取当前用户 ID，签发新的 access_token
    current_user = get_jwt_identity()  # 从 Refresh Token 中提取用户身份标识
    new_token = create_access_token(identity=current_user)  # 签发新的 Access Token
    
    return jsonify(access_token=new_token), 200

@app.route('/api/nav-data', methods=['GET'])
def get_nav_data():
    """
    获取导航页完整数据（分类 + 网站列表）。

    接口路径：GET /api/nav-data
    请求方法：GET
    功能描述：从数据库查询所有分类及其下属网站，按前端所需的嵌套结构返回。
    参数：无
    返回：
        200 - 分类列表，每个分类包含 id、name 和 sites 数组
              sites 数组中每个元素包含 id、category_id、name、url、logo_url、clicks
    """
    categories = Category.query.order_by(Category.sort_order.asc(), Category.id.asc()).all()
    all_sites = Website.query.filter(Website.status != 'rejected').order_by(Website.clicks.desc(), Website.id.asc()).all()
    site_items = add_site_metadata([site_to_dict(site) for site in all_sites])
    site_by_id = {site['id']: site for site in site_items}

    category_items = []
    for cat in categories:
        category_sites = [
            site_by_id[site.id]
            for site in cat.websites
            if site.id in site_by_id and site.status != 'rejected'
        ]
        category_items.append({
            'id': cat.id,
            'name': cat.name,
            'profession_type': cat.profession_type or 'general',
            'sort_order': cat.sort_order or 0,
            'sites': category_sites,
        })

    return ok({'categories': category_items, 'sites': site_items})

# ===== 定时任务配置 =====
# 配置并启动定时任务
scheduler = APScheduler()       # 创建 APScheduler 调度器实例
scheduler.init_app(app)         # 将调度器与 Flask 应用绑定

# 设定触发器：每天凌晨 3:00 自动执行一次
@scheduler.task('cron', id='do_hn_spider', hour=3, minute=0)
def scheduled_spider_task():
    """
    定时爬虫任务（每天凌晨 3:00 自动触发）。

    功能描述：在服务器低峰期自动调用 Hacker News 爬虫，
              将新发现的热门站点写入待审核队列，供管理员次日审核。
    触发方式：cron 定时，每天 03:00 执行
    """
    auto_fetch_hacker_news()  # 调用爬虫函数，抓取 HN 热门站点

# 启动调度器
scheduler.start()  # 启动后台调度器，开始监听定时任务

# ================= 4. 垂直资讯流聚合 (RSS 穿透防火墙版) =================
@app.route('/api/news', methods=['GET'])
def get_industry_news():
    """
    获取行业资讯列表（RSS 聚合接口）。

    接口路径：GET /api/news
    请求方法：GET
    功能描述：根据职业方向参数，从 V2EX 对应的 RSS 订阅源抓取最新文章，
              通过本地代理穿透网络限制，返回最新的 8 条资讯。
    参数：
        prof (str, 可选): 职业方向筛选，可选值：
            - 'frontend' 前端开发（程序员节点）
            - 'product'  产品经理（创意节点）
            - 'ui'       UI 设计（设计节点）
            - 'all'      全部（默认，V2EX 首页）
    返回：
        200 - 资讯列表，每条包含 title（标题）、link（链接）、source（来源）
        500 - 抓取失败，包含错误信息
    """
    prof = request.args.get('prof', 'all')  # 获取职业方向参数，默认为 'all'
    
    # RSS 订阅源映射表：职业方向 -> V2EX 对应节点的 RSS 地址
    rss_map = {
        'frontend': 'https://v2ex.com/feed/programmer.xml',  # 程序员节点
        'product': 'https://v2ex.com/feed/create.xml',       # 创意/产品节点
        'ui': 'https://v2ex.com/feed/design.xml',            # 设计节点
        'all': 'https://v2ex.com/index.xml'                  # V2EX 全站首页
    }
    
    url = rss_map.get(prof, rss_map['all'])  # 根据参数选择对应的 RSS 地址，未知参数则回退到全站
    
    try:
        # ✨ 1. 挂上本地代理 (如果你的代理不是 7890，请改成你自己的端口)
        my_proxies = {
            'http': 'http://127.0.0.1:7890',   # HTTP 代理地址
            'https': 'http://127.0.0.1:7890'   # HTTPS 代理地址
        }
        
        # ✨ 2. 先用 requests 强行穿透墙壁拉取 XML 文本
        import requests

        # 找到 requests.get 这一行，在它上面加上 headers 变量
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)# 通过代理请求 RSS 地址，超时 10 秒
        xml_data = response.text  # 获取原始 XML 文本内容
        
        # ✨ 3. 再把拉到的纯文本喂给 feedparser 进行解析
        feed = feedparser.parse(xml_data)  # 解析 RSS/Atom XML 为结构化数据
        
        news_list = []  # 存储处理后的资讯列表
        for entry in feed.entries[:8]:  # 只取前 8 条，避免数据过多
            news_list.append({
                'title': entry.title,   # 文章标题
                'link': entry.link,     # 文章链接
                'source': feed.feed.title if hasattr(feed.feed, 'title') else '行业快讯'  # 来源名称，取 Feed 标题
            })
            
        return jsonify(news_list), 200
    except Exception as e:
        import traceback
        traceback.print_exc() # 在终端打印真实报错原因
        return jsonify({'error': str(e)}), 500
# ================= 爬虫手动测试接口 =================
@app.route('/api/admin/run-spider', methods=['POST'])
def trigger_spider_manually():
    """
    手动触发 Hacker News 爬虫接口（管理员专用）。

    接口路径：POST /api/admin/run-spider
    请求方法：POST
    功能描述：同步执行 Hacker News 爬虫，将抓取到的新站点写入待审核队列。
              注意：此接口为同步调用，爬虫执行期间会阻塞响应。
              生产环境建议改为异步队列（如 Celery）处理。
    参数：无
    返回：
        200 - 爬虫执行完毕的提示信息
    """
    # 为了演示直接同步调用。在生产环境中，耗时爬虫建议扔给 Celery 等异步队列
    auto_fetch_hacker_news(app)  # 传入 app 实例以便在爬虫内部使用应用上下文
    return jsonify({"message": "✅ 爬虫执行完毕！快去前端的【审核工作台】看看有没有新货吧！"})

# ================= 1. 模拟数据库 (保持不变) =================
# 内存中的分类数据，作为静态备用数据（真实数据从 MySQL 读取）
categories_db = [
    # 字段说明：id - 分类唯一标识，name - 分类显示名称
    {"id": 1, "name": "常用推荐"},
    {"id": 2, "name": "开发社区"},
    {"id": 3, "name": "摸鱼娱乐"},
    {"id": 4, "name": "实用工具"},
    {"id": 5, "name": "AI 神器"}
]

# 内存中的网站数据，作为静态备用数据（真实数据从 MySQL 读取）
# 字段说明：
#   id          - 网站唯一标识
#   category_id - 所属分类 ID（对应 categories_db 中的 id）
#   name        - 网站显示名称
#   url         - 网站访问地址
#   logo_url    - 网站图标地址（空字符串表示待抓取）
#   clicks      - 累计点击量（用于热度排序）
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

@app.route('/go/<int:item_id>')
def redirect_to_item(item_id):
    return jsonify({"msg": "重定向功能开发中"}), 200

# ================= 3. 排行榜 API 接口 =================
@app.route('/api/ranking/growth', methods=['GET'])
def get_growth_ranking():
    try:
        try:
            cached_data = redis_client.get("leaderboard:growth_rate")
            if cached_data:
                return jsonify({"code": 0, "data": json.loads(cached_data)})
        except Exception as redis_e:
            print(f"Redis cache unavailable, using database ranking: {redis_e}")

        rows = Website.query.filter(Website.status != 'rejected').order_by(Website.clicks.desc()).limit(10).all()
        fresh_data = [{
            'id': site.id,
            'name': site.name,
            'url': site.url,
            'logo_url': site.logo_url or '',
            'clicks': site.clicks or 0,
            'growth_rate': min(99, max(1, int((site.clicks or 1) % 100))),
        } for site in rows]
        return jsonify({"code": 0, "data": fresh_data})

    except Exception as e:
        print(f"Growth ranking fallback failed: {e}")
        return jsonify({"code": 0, "data": []})
    
# ================= 🔒 受保护的管理后台路由示例 =================

@app.route('/api/admin/dashboard', methods=['GET'])
@jwt_required() # ✨ 这个装饰器要求请求头必须带 Authorization: Bearer <access_token>
def admin_dashboard():
    """
    管理后台首页数据接口（需要 JWT 认证）。

    接口路径：GET /api/admin/dashboard
    请求方法：GET
    功能描述：验证 JWT Access Token 后，返回当前登录管理员的欢迎信息和后台统计数据。
    请求头：Authorization: Bearer <access_token>
    返回：
        200 - 欢迎信息和后台数据
        401 - 未提供 Token 或 Token 无效
    """
    # 只有合法用户能走到这一步
    current_user_id = get_jwt_identity()          # 从 Token 中提取用户 ID
    user = User.query.get(current_user_id)         # 根据 ID 查询用户详情
    
    return jsonify({
        "message": f"欢迎尊贵的管理员 {user.username}！",
        "secret_data": "这是只有登录用户才能看到的后台数据统计。"
    }), 200
# ================= 2. 基础 API 路由 (保持不变) =================

@app.route('/api/data', methods=['GET'])
def get_data():
    """
    获取内存中的静态导航数据（备用接口）。

    接口路径：GET /api/data
    请求方法：GET
    功能描述：直接返回内存中预置的 categories_db 和 websites_db 静态数据，
              不查询数据库，适合在数据库不可用时作为降级方案。
    参数：无
    返回：
        200 - 包含 categories（分类列表）和 websites（网站列表）的 JSON 对象
    """
    return jsonify({"categories": categories_db, "websites": websites_db})

# ================= 1. 自动抓取 Hacker News 热门站点 (SQLAlchemy 版) =================
@app.route('/api/admin/crawl_hn', methods=['POST'])
def crawl_hacker_news():
    """
    手动触发 Hacker News 热门站点抓取接口（管理员专用）。

    接口路径：POST /api/admin/crawl_hn
    请求方法：POST
    功能描述：调用 Hacker News Firebase API 获取当前最热的 30 篇文章，
              提取其中包含外链 URL 的文章，去重后写入 pending_sites 待审核表。
              已存在于正式表或待审核表中的 URL 会被跳过，避免重复录入。
    参数：无
    返回：
        200 - 抓取完成，包含新发现的站点数量
        500 - 抓取过程中发生异常
    """
    try:
        my_proxies = {
            'http': 'http://127.0.0.1:7890',   # HTTP 代理，用于访问被墙的 Firebase API
            'https': 'http://127.0.0.1:7890'   # HTTPS 代理
        }
        # 获取 HN 最热的 30 篇文章 ID
        top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        story_ids = requests.get(top_stories_url).json()[:30]  # 只取前 30 条热门文章 ID
        
        added_count = 0  # 记录本次新增的待审核站点数量
        
        for story_id in story_ids:
            story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
            story_info = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json").json()  # 获取文章详情
            
            if story_info and 'url' in story_info:  # 只处理包含外链的文章（排除纯讨论帖）
                url = story_info['url']
                title = story_info.get('title', '未知站点')
                
                # 查重 1：检查待审核表
                is_in_pending = db.session.execute(text("SELECT id FROM pending_sites WHERE url = :url"), {'url': url}).fetchone()
                
                # ✨ 完美融合：直接用你现成的 Website 模型去正式表里查重！
                is_in_sites = Website.query.filter_by(url=url).first()
                
                if not is_in_pending and not is_in_sites:  # 两张表都没有才写入
                    # 写入待审核库
                    db.session.execute(
                        text("INSERT INTO pending_sites (name, url, description, source) VALUES (:name, :url, :desc, :source)"),
                        {'name': title, 'url': url, 'desc': title, 'source': 'Hacker News'}
                    )
                    added_count += 1
        
        db.session.commit()  # 批量提交所有插入操作
        return jsonify({'message': f'抓取完成！成功发现 {added_count} 个新站点待审核。'}), 200
    except Exception as e:
        db.session.rollback()  # 发生异常时回滚事务，保证数据一致性
        return jsonify({'error': str(e)}), 500

# ================= 2. 获取待审核站点列表 =================
@app.route('/api/admin/pending_sites', methods=['GET'])
def get_pending_sites():
    """
    获取待审核站点列表接口（管理员专用）。

    接口路径：GET /api/admin/pending_sites
    请求方法：GET
    功能描述：查询 pending_sites 表中状态为 'pending' 的站点，
              按创建时间倒序排列，供管理员在审核工作台中逐一审核。
    参数：无
    返回：
        200 - 待审核站点列表，每条包含 id、name、url、description、source
        500 - 数据库查询异常
    """
    try:
        result = db.session.execute(text("SELECT id, name, url, description, source FROM pending_sites WHERE status = 'pending' ORDER BY created_at DESC"))
        sites = []  # 存储格式化后的站点列表
        for row in result:
            sites.append({
                'id': row[0],           # 待审核记录 ID
                'name': row[1],         # 站点名称
                'url': row[2],          # 站点地址
                'description': row[3],  # 站点描述
                'source': row[4]        # 数据来源（如 'Hacker News'）
            })
        return jsonify(sites), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================= 3. 审核操作 (通过 或 拒绝) =================
@app.route('/api/admin/review_site', methods=['POST'])
def review_site():
    """
    审核待审核站点接口（管理员专用）。

    接口路径：POST /api/admin/review_site
    请求方法：POST
    功能描述：对待审核站点执行通过或拒绝操作。
              - 通过（approve）：将站点从 pending_sites 迁移到正式 websites 表，并更新待审核状态为 'approved'
              - 拒绝（reject）：仅将待审核状态更新为 'rejected'，不写入正式表
    请求体（JSON）：
        id          (int): 待审核站点的 ID
        action      (str): 操作类型，'approve' 通过 或 'reject' 拒绝
        category_id (int, 可选): 通过时指定的分类 ID，默认为 1（常用推荐）
    返回：
        200 - 审核操作成功
        500 - 数据库操作异常
    """
    data = request.json
    site_id = data.get('id')           # 待审核站点 ID
    action = data.get('action')        # 审核操作：'approve' 或 'reject'
    category_id = data.get('category_id', 1)  # 通过时的目标分类，默认归入"常用推荐"
    
    try:
        if action == 'approve':
            # 1. 查出待审核数据
            site_row = db.session.execute(text("SELECT name, url, description FROM pending_sites WHERE id = :id"), {'id': site_id}).fetchone()
            if site_row:
                # ✨ 完美融合：直接实例化你的 Website 模型，让它按照你的规则生成数据！
                new_site = Website(name=site_row[0], url=site_row[1], category_id=category_id)  # 创建正式网站记录
                db.session.add(new_site)
                
                # 更新待审核表状态
                db.session.execute(text("UPDATE pending_sites SET status = 'approved' WHERE id = :id"), {'id': site_id})
        
        elif action == 'reject':
            db.session.execute(text("UPDATE pending_sites SET status = 'rejected' WHERE id = :id"), {'id': site_id})  # 标记为已拒绝
            
        db.session.commit()  # 提交事务
        return jsonify({'message': '审核操作成功'}), 200
    except Exception as e:
        db.session.rollback()  # 异常时回滚，保证数据一致性
        return jsonify({'error': str(e)}), 500
# backend/app.py
# ✨ 1. 全网基础热度（保持不变）
# 各网站的基础热度权重，基于全网真实流量数据预估
# 用于在实时热度为 0 时提供兜底排序依据，防止冷启动时排行榜为空
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
_hotness_cache = {}       # 格式：{网站名: 上次热度分数}，用于计算热度涨跌幅
_hotness_cache_time = {}  # 格式：{网站名: 上次更新时间戳}，用于判断缓存是否过期


def fetch_online_hotness():
    """
    从多个公开热榜 API 抓取各网站的实时热度分数。

    数据来源（共 7 个）：
      1. 微博实时热搜 - 累加热搜词条热度值
      2. 知乎热榜     - 累加热榜条目热度（万热度单位转换）
      3. 百度实时热搜 - 累加热搜词条热度分
      4. 今日头条热榜 - 累加热榜条目热度值
      5. GitHub Trending - 今日 Star 增量（×10 放大）
      6. 哔哩哔哩热门 - 累加热门视频播放量
      7. 抖音热榜     - 累加热搜词条热度值

    返回：
        dict: {网站名(str): 实时热度分数(int)}，
              未能成功抓取的网站不会出现在返回字典中
    """
    global _hotness_cache
    # 1. 获取当前数据库中所有真实的网站 name (或 ID)
    current_site_names = {site.name for site in Website.query.all()}
    
    # 2. 清理：只保留存在于当前数据库中的网站热度数据
    _hotness_cache = {name: data for name, data in _hotness_cache.items() if name in current_site_names}  # 过滤已删除的网站缓存
    hotness = {}  # 本次抓取的热度结果字典
    hdrs = {
        # 模拟浏览器 User-Agent，避免被反爬机制拦截
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
    }
    # 源1：微博实时热搜
    try:
        r = requests.get('https://weibo.com/ajax/side/hotSearch',
            headers={**hdrs, 'Referer': 'https://weibo.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', {}).get('realtime', [])
            hotness['微博'] = sum(int(x.get('num', 0)) for x in items[:50])  # 累加前 50 条热搜词条的热度值
    except Exception:
        pass  # 抓取失败时静默跳过，不影响其他数据源
    # 源2：知乎热榜
    try:
        r = requests.get('https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50',
            headers={**hdrs, 'Referer': 'https://www.zhihu.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', [])
            total = 0
            for item in items:
                raw = item.get('detail_text', '0').replace('万热度', '').replace('万', '')  # 去除"万热度"单位文字
                try:
                    total += int(float(raw) * 10000)  # 将"万"单位转换为实际数值
                except Exception:
                    total += 5000  # 解析失败时使用默认值 5000
            hotness['知乎'] = total
    except Exception:
        pass
    # 源3：百度实时热搜
    try:
        r = requests.get('https://top.baidu.com/api/board?platform=wise&tab=realtime',
            headers={**hdrs, 'Referer': 'https://top.baidu.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', {}).get('cards', [{}])[0].get('content', [])
            hotness['百度'] = sum(int(x.get('hotScore', 0)) for x in items[:30])  # 累加前 30 条热搜的热度分
    except Exception:
        pass
    # 源4：今日头条热榜
    try:
        r = requests.get('https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc',
            headers={**hdrs, 'Referer': 'https://www.toutiao.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', [])
            hotness['今日头条'] = sum(int(x.get('HotValue', 0)) for x in items[:30])  # 累加前 30 条热榜的热度值
    except Exception:
        pass
    # 源5：GitHub Trending 今日 Star 增量
    try:
        r = requests.get('https://api.gitterapp.com/repositories?since=daily',
            headers=hdrs, timeout=6)
        if r.status_code == 200:
            repos = r.json()
            hotness['GitHub'] = sum(int(x.get('stars', 0)) for x in repos[:25]) * 10  # Star 数 ×10 放大，与其他平台热度量级对齐
    except Exception:
        pass
    # 源6：哔哩哔哩热门视频播放量
    try:
        r = requests.get('https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all',
            headers={**hdrs, 'Referer': 'https://www.bilibili.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', {}).get('list', [])
            hotness['哔哩哔哩'] = sum(int(x.get('stat', {}).get('view', 0)) for x in items[:20])  # 累加前 20 个热门视频的播放量
    except Exception:
        pass
    # 源7：抖音热榜
    try:
        r = requests.get('https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/',
            headers={**hdrs, 'Referer': 'https://www.douyin.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('word_list', [])
            hotness['抖音'] = sum(int(x.get('hot_value', 0)) for x in items[:30])  # 累加前 30 条热搜词的热度值
    except Exception:
        pass
    return hotness  # 返回本次成功抓取的所有网站热度数据

# ================= 1. 发送安全验证码 (存入 Redis, 有效期5分钟) =================

@app.route('/api/security/send-email-code', methods=['POST'])
@jwt_required()
@limiter.limit("2 per minute") # 防止被别人恶意刷邮箱轰炸
def send_bind_email_code():
    email = request.json.get('email')
    if not email: return jsonify({'code': 400, 'msg': '邮箱不能为空'}), 400
    
    code = str(random.randint(100000, 999999))
    redis_client.setex(f"bind_email_code:{email}", 300, code) # Redis：300秒(5分钟)自动过期
    
    # 调用真实的 SMTP 发送逻辑
    is_success, error_msg = send_verification_email(email, code)
    if is_success:
        return jsonify({'code': 0, 'msg': '验证码已发送'})
    else:
        return jsonify({'code': 500, 'msg': f'邮件发送失败：{error_msg}'}), 500

@app.route('/api/security/send-sms-code', methods=['POST'])
@jwt_required()
@limiter.limit("1 per minute")
def send_bind_sms_code():
    phone = request.json.get('phone')
    if not phone: return jsonify({'code': 400, 'msg': '手机号不能为空'}), 400
    
    code = str(random.randint(100000, 999999))
    redis_client.setex(f"bind_phone_code:{phone}", 300, code) # Redis 存储
    
    # ⚠️ [真实短信 SDK 接入占位] 
    # 此处应接入阿里云(Dysmsapi)或腾讯云(SmsClient) SDK。示例逻辑如下：
    # client = AcsClient('你的AccessKey', '你的Secret', 'cn-hangzhou')
    # request = CommonRequest()
    # request.set_domain('dysmsapi.aliyuncs.com')
    # request.set_action_name('SendSms')
    # request.add_query_param('PhoneNumbers', phone)
    # request.add_query_param('SignName', "智汇导航")
    # request.add_query_param('TemplateCode', "SMS_123456789")
    # request.add_query_param('TemplateParam', f'{{"code":"{code}"}}')
    # response = client.do_action_with_exception(request)
    
    print(f"\n🚀 [国内短信服务模拟] 接收手机号: {phone} | 验证码: {code}\n")
    return jsonify({'code': 0, 'msg': '短信验证码已发送'})


# ================= 2. 严格校验验证码并绑定入库 =================

@app.route('/api/security/bind-email', methods=['POST'])
@jwt_required()
def submit_bind_email():
    username = get_jwt_identity() # 取出请求者的身份
    data = request.json
    email, code = data.get('email'), data.get('code')
    
    # 1. 查 Redis 对比验证码 (同时校验是否过期)
    saved_code = redis_client.get(f"bind_email_code:{email}")
    if not saved_code or saved_code != code:
        return jsonify({'code': 400, 'msg': '验证码错误或已过期(超5分钟)'}), 400

    # 2. 校验成功，写入 MySQL 更新资料
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET email = %s WHERE username = %s", (email, username))
        conn.commit()
        
        # 3. 销毁已使用过的验证码（防重放攻击）
        redis_client.delete(f"bind_email_code:{email}") 
        
        return jsonify({'code': 0, 'msg': '邮箱换绑成功'})
    except Exception as e:
        return jsonify({'code': 500, 'msg': '数据库写入失败'}), 500
    finally:
        conn.close()

@app.route('/api/security/bind-phone', methods=['POST'])
@jwt_required()
def submit_bind_phone():
    username = get_jwt_identity()
    data = request.json
    phone, code = data.get('phone'), data.get('code')
    
    saved_code = redis_client.get(f"bind_phone_code:{phone}")
    if not saved_code or saved_code != code:
        return jsonify({'code': 400, 'msg': '验证码错误或已过期(超5分钟)'}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET phone = %s WHERE username = %s", (phone, username))
        conn.commit()
        redis_client.delete(f"bind_phone_code:{phone}") 
        return jsonify({'code': 0, 'msg': '手机号绑定成功'})
    finally:
        conn.close()

# ================= 1. 上传/更新配置到云端 =================
@app.route('/api/user/sync', methods=['POST'])
@jwt_required()
def sync_user_settings():
    """
    同步用户个性化配置到云端接口（需要 JWT 认证）。

    接口路径：POST /api/user/sync
    请求方法：POST
    功能描述：将用户在前端修改的个性化配置（深色模式、壁纸、搜索引擎等）
              持久化保存到数据库，实现多设备配置同步。
              如果用户不存在则自动创建（兼容手机号模拟登录场景）。
    请求头：Authorization: Bearer <access_token>
    请求体（JSON，所有字段均为可选）：
        username         (str):  用户名（必填，用于查找用户）
        dark_mode        (bool): 是否启用深色模式
        custom_wallpaper (str):  自定义壁纸 URL
        current_engine   (str):  当前默认搜索引擎
        selected_engines (list): 已选择的搜索引擎列表（存储为 JSON 字符串）
        avatar_url       (str):  用户头像 URL
    返回：
        200 - 配置同步成功
        401 - 未提供用户名
    """
    data = request.json
    username = data.get('username')  # 从请求体获取用户名
    
    if not username:
        return jsonify({"error": "未登录"}), 401

    # 查找用户，如果没有就顺手创建一个（兼容你目前的手机号模拟登录逻辑）
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username)  # 用户不存在时自动创建
        db.session.add(user)

    # 同步各项配置（只更新请求体中包含的字段，未传的字段保持原值）
    if 'dark_mode' in data:
        user.dark_mode = data['dark_mode']           # 深色模式开关
    if 'custom_wallpaper' in data:
        user.custom_wallpaper = data['custom_wallpaper']  # 自定义壁纸
    if 'current_engine' in data:
        user.current_engine = data['current_engine']  # 当前搜索引擎
    if 'selected_engines' in data:
        user.selected_engines = json.dumps(data['selected_engines']) # 列表转为字符串存储
    if 'avatar_url' in data:
        user.avatar_url = data['avatar_url']          # 用户头像

    db.session.commit()  # 提交所有配置更新
    return jsonify({"success": True, "message": "配置已同步到云端 ☁️"})

# ================= 2. 登录时拉取云端配置 =================
@app.route('/api/user/settings', methods=['GET'])
def get_user_settings():
    """
    获取用户个性化配置接口。

    接口路径：GET /api/user/settings
    请求方法：GET
    功能描述：根据用户名从数据库读取用户的个性化配置，
              用于用户登录后恢复其在其他设备上保存的偏好设置。
    参数：
        username (str, 查询参数): 用户名，必填
    返回：
        200 - 用户配置对象，包含 dark_mode、custom_wallpaper、
              current_engine、selected_engines、avatar_url
        400 - 缺少用户名参数
        404 - 用户不存在
    """
    username = request.args.get('username')  # 从 URL 查询参数获取用户名
    
    if not username:
        return jsonify({"error": "缺少用户名"}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "找不到用户"}), 404

    return jsonify({
        "dark_mode": user.dark_mode,                                                          # 深色模式状态
        "custom_wallpaper": user.custom_wallpaper,                                            # 自定义壁纸 URL
        "current_engine": user.current_engine,                                                # 当前搜索引擎
        "selected_engines": json.loads(user.selected_engines) if user.selected_engines else None,  # JSON 字符串反序列化为列表
        "avatar_url": user.avatar_url                                                         # 用户头像 URL
    })

@app.route('/api/ranking', methods=['GET'])
def get_ranking():
    """
    获取网站实时热度排行榜接口。

    接口路径：GET /api/ranking
    请求方法：GET
    功能描述：从多个公开热榜 API 抓取实时热度数据，结合数据库中的网站列表，
              计算每个网站的热度分数、涨跌量和涨跌率，返回综合排名前 10 的网站。
              排序规则：先按涨跌率绝对值（热度变化最大的排前面），再按综合热度分排序。
    参数：无
    返回：
        200 - 排行榜列表（最多 10 条），每条包含：
              id          - 网站 ID
              name        - 网站名称
              url         - 网站地址
              clicks      - 当前实时热度分数
              delta       - 与上次相比的热度变化量
              growth_rate - 热度涨跌率（百分比）
              sort_score  - 综合排序分（实时热度 + 基础热度权重）
        500 - 抓取或计算过程中发生异常
    """
    global _hotness_cache, _hotness_cache_time
    try:
        current = fetch_online_hotness()  # 抓取本次实时热度数据
        ranking_data = []                 # 存储排行榜数据
        all_sites_db = Website.query.all()  # 查询数据库中所有网站
        for site in all_sites_db:
            name = site.name
            cur_score = current.get(name, 0)   # 本次抓取的热度分，未抓到则为 0
            last_score = _hotness_cache.get(name, 0)  # 上次缓存的热度分，首次为 0
            if last_score > 0 and cur_score > 0:
                rate = round((cur_score - last_score) / last_score * 100, 1)  # 计算涨跌率（百分比，保留1位小数）
            elif cur_score > 0 and last_score == 0:
                rate = 100.0  # 首次出现热度数据，视为 100% 增长
            else:
                rate = 0.0    # 无热度数据时涨跌率为 0
            delta = cur_score - last_score  # 热度变化绝对值
            base = BASE_HOTNESS.get(name, 0)  # 从基础热度表获取该网站的权重
            sort_score = cur_score + base // 100  # 综合排序分 = 实时热度 + 基础热度的 1%（避免基础热度过度影响排名）
            ranking_data.append({
                'id': site.id,
                'name': name,
                'url': site.url,
                'clicks': cur_score,       # 当前实时热度分数
                'delta': delta,            # 热度变化量
                'growth_rate': rate,       # 涨跌率（%）
                'sort_score': sort_score,  # 综合排序分
            })
        for name, score in current.items():
            _hotness_cache[name] = score           # 更新热度缓存
            _hotness_cache_time[name] = time.time()  # 记录缓存更新时间
        ranking_data.sort(key=lambda x: (abs(x['growth_rate']), x['sort_score']), reverse=True)  # 先按涨跌率绝对值降序，再按综合分降序
        return jsonify(ranking_data[:10])  # 只返回前 10 名
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# --- 1. 用户发布内容 (存为草稿或提交审核) ---
@app.route('/api/articles', methods=['POST'])
@jwt_required()
def publish_article():
    user_id = get_jwt_identity() # 假设 token 里存的是 user_id
    data = request.json
    
    # 状态控制：前端传 'draft' 则是草稿，传 'pending' 则进入审核池
    status = data.get('status', 'draft') 
    
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO articles (user_id, title, cover_url, content, category, tags, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, data['title'], data['cover_url'], data['content'], 
              data['category'], json.dumps(data['tags']), status))
    conn.commit()
    conn.close()
    return jsonify({'code': 0, 'msg': '操作成功'})

# --- 2. 管理员审核接口 ---
@app.route('/api/admin/articles/<int:article_id>/review', methods=['POST'])
@jwt_required()
def review_article(article_id):
    # 此处应有管理员权限校验...
    data = request.json
    action = data.get('action') # 'approve' 或 'reject'
    reason = data.get('reason', '')

    status = 'approved' if action == 'approve' else 'rejected'
    
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("UPDATE articles SET status = %s, reject_reason = %s WHERE id = %s", 
                       (status, reason, article_id))
    conn.commit()
    conn.close()
    return jsonify({'code': 0, 'msg': '审核完毕'})

# --- 3. 点赞/取消点赞 (Redis 方案) ---
@app.route('/api/articles/<int:article_id>/like', methods=['POST'])
@jwt_required()
def toggle_like(article_id):
    user_id = get_jwt_identity()
    redis_key = f"article:{article_id}:likes"
    
    # 检查用户是否在点赞集合中
    is_liked = redis_client.sismember(redis_key, user_id)
    
    if is_liked:
        redis_client.srem(redis_key, user_id) # 取消点赞
        # 异步更新到 MySQL (省略异步代码，此处同步演示)
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM article_likes WHERE article_id=%s AND user_id=%s", (article_id, user_id))
            cursor.execute("UPDATE articles SET likes_count = likes_count - 1 WHERE id = %s", (article_id,))
        conn.commit()
        liked_state = False
    else:
        redis_client.sadd(redis_key, user_id) # 加入点赞
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("INSERT IGNORE INTO article_likes (article_id, user_id) VALUES (%s, %s)", (article_id, user_id))
            cursor.execute("UPDATE articles SET likes_count = likes_count + 1 WHERE id = %s", (article_id,))
        conn.commit()
        liked_state = True
        
    likes_count = redis_client.scard(redis_key) # 获取最新点赞数
    return jsonify({'code': 0, 'data': {'liked': liked_state, 'count': likes_count}})

# --- 4. 获取文章详情 (含安全渲染数据与浏览量自增) ---
@app.route('/api/articles/<int:article_id>', methods=['GET'])
def get_article_detail(article_id):
    # Redis 浏览量自增
    views_key = f"article:{article_id}:views"
    redis_client.incr(views_key)
    
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM articles WHERE id = %s AND status = 'approved'", (article_id,))
        article = cursor.fetchone()
    conn.close()
    
    if not article:
        return jsonify({'code': 404, 'msg': '文章不存在或还在审核中'})
        
    # 合并 Redis 中的实时数据
    article['views'] = int(redis_client.get(views_key) or article['views'])
    return jsonify({'code': 0, 'data': article})

# ================= 记录真实点击 (升级版) =================
@app.route('/api/click', methods=['POST'])
def handle_click():
    # 获取前端传来的网站 ID
    data = request.get_json()
    site_id = data.get('id')
    
    if not site_id:
        return jsonify({'code': 400, 'msg': '缺少网站 ID'}), 400
        
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 1. (兼容旧版) 更新原本 websites 表的总点击量
            cursor.execute("UPDATE websites SET clicks = clicks + 1 WHERE id = %s", (site_id,))
            
            # 2. 兼容旧排行榜日志表；表不存在时不影响主流程
            try:
                cursor.execute("INSERT INTO click_log (item_id) VALUES (%s)", (site_id,))
            except Exception:
                pass
            
        conn.commit()
        conn.close()
        log_user_behavior('visit', website_id=site_id)
        
        return jsonify({'code': 0, 'msg': '点击已成功记录入库'})
    except Exception as e:
        print(f"记录点击严重报错: {e}")
        return jsonify({'code': 500, 'msg': '服务器内部错误'}), 500

# ---------------------------------------------------------
# 💡 鉴权辅助函数：从前端请求的 Header 中提取当前登录的用户
# （如果你项目中用了 flask_jwt_extended，这里可以直接用 get_jwt_identity()）
# ---------------------------------------------------------
def get_current_username():
    """解析前端传来的 Authorization: Bearer <token>"""
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        # 这里为了演示通用性，假设 token 里直接存了用户名
        # 实际开发中，请使用你的 JWT 解码逻辑： jwt.decode(token, SECRET_KEY)
        return token 
    # 如果没 token，默认返回测试账号（防止前端直接崩溃）
    return "用户_1234"


# =========================================================
# 🚀 1. 获取个人主页数据概览 (发帖数、获赞数等)
# =========================================================
@app.route('/api/user/stats', methods=['GET'])
def get_user_stats():
    username = request.args.get('username') or get_current_username()
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 统计该用户的发帖总数
            cursor.execute("SELECT COUNT(*) AS posts FROM user_contents WHERE username = %s AND status = 'published'", (username,))
            posts_count = cursor.fetchone()['posts']
            
            # 统计总获赞数和浏览量
            cursor.execute("SELECT SUM(views) as total_views, SUM(likes) as total_likes FROM user_contents WHERE username = %s", (username,))
            sum_data = cursor.fetchone()
            
            # 真实商业项目中，粉丝数可能存在 follower 表中，这里先做个安全回退
            total_views = int(sum_data['total_views'] or 0) + int(sum_data['total_likes'] or 0)
            
        conn.close()
        
        return jsonify({
            'code': 0,
            'data': {
                'views': total_views,
                'followers': 0, # 这里可以改成连表查询真实的粉丝数
                'posts': posts_count
            }
        })
    except Exception as e:
        print(f"Stats API 报错: {e}")
        return jsonify({'code': 500, 'msg': '数据库查询失败'}), 500


# =========================================================
# 🚀 2. 获取账号安全 - 登录设备列表
# =========================================================
@app.route('/api/user/devices', methods=['GET'])
def get_user_devices():
    username = get_current_username()
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 查出该用户最近登录的设备
            cursor.execute("SELECT * FROM user_devices WHERE username = %s ORDER BY last_login_time DESC LIMIT 10", (username,))
            devices = cursor.fetchall()
            
            # 格式化时间，以适配前端
            for dev in devices:
                # 转换 datetime 为字符串
                dev['time'] = dev['last_login_time'].strftime('%Y-%m-%d %H:%M') 
                dev['isCurrent'] = bool(dev['is_current'])
                
        conn.close()
        return jsonify({'code': 0, 'data': devices})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e)}), 500


# =========================================================
# 🚀 3. 获取我的内容管理列表 (支持按状态过滤)
# =========================================================
@app.route('/api/user/contents', methods=['GET'])
def get_user_contents():
    username = get_current_username()
    # 接收前端传来的状态：published(已发布) / reviewing(审核中) / draft(草稿)
    status = request.args.get('status', 'published') 
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, title, views, likes, created_at 
                FROM user_contents 
                WHERE username = %s AND status = %s 
                ORDER BY created_at DESC
            """, (username, status))
            contents = cursor.fetchall()
            
            # 格式化日期给前端展示
            for item in contents:
                item['time'] = item['created_at'].strftime('%Y-%m-%d %H:%M')
                
        conn.close()
        return jsonify({'code': 0, 'data': contents})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e)}), 500


# =========================================================
# 🚀 4. 获取互动足迹 (精细化：按日期进行折叠分组)
# =========================================================
@app.route('/api/user/history', methods=['GET'])
def get_user_history():
    username = get_current_username()
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, action, target_name, target_url, created_at 
                FROM user_history 
                WHERE username = %s 
                ORDER BY created_at DESC LIMIT 50
            """, (username,))
            history_records = cursor.fetchall()
            
        conn.close()
        
        # 💡 核心算法：用 Python 将平铺的数据按 "日期" 分组，满足前端 UI 的需求
        grouped_history = {}
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        for row in history_records:
            date_part = row['created_at'].strftime('%Y-%m-%d')
            time_part = row['created_at'].strftime('%H:%M')
            
            # 人性化日期显示
            if date_part == today_str:
                display_date = "今天"
            elif date_part == yesterday_str:
                display_date = "昨天"
            else:
                display_date = date_part

            if display_date not in grouped_history:
                grouped_history[display_date] = []
                
            grouped_history[display_date].append({
                'id': row['id'],
                'time': time_part,
                'action': row['action'],
                'target_name': row['target_name'],
                'url': row['target_url']
            })

        # 将字典转换为前端要求的大数组格式
        final_data = [{'date': k, 'items': v} for k, v in grouped_history.items()]
        
        return jsonify({'code': 0, 'data': final_data})
    except Exception as e:
        print(f"足迹报错: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


# =========================================================
# 🚀 5. 功能接口：删除单条内容 & 清空互动足迹
# =========================================================
@app.route('/api/user/contents/delete', methods=['POST'])
def delete_user_content():
    username = get_current_username()
    content_id = request.json.get('id')
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM user_contents WHERE id = %s AND username = %s", (content_id, username))
        conn.commit()
        conn.close()
        return jsonify({'code': 0, 'msg': '删除成功'})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e)}), 500


@app.route('/api/user/history/clear', methods=['POST'])
def clear_user_history():
    username = get_current_username()
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM user_history WHERE username = %s", (username,))
        conn.commit()
        conn.close()
        return jsonify({'code': 0, 'msg': '足迹已清空'})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e)}), 500

@app.route('/api/cache_logo', methods=['POST'])
def cache_logo():
    """
    缓存网站图标 URL 接口。

    接口路径：POST /api/cache_logo
    请求方法：POST
    功能描述：根据网站 URL 自动生成 Google Favicon 服务的图标地址，
              并更新内存中 websites_db 对应网站的 logo_url 字段。
              注意：此接口只更新内存数据，不持久化到数据库。
    请求体（JSON）：
        id  (int): 网站 ID（对应 websites_db 中的 id）
        url (str): 网站地址，用于提取域名
    返回：
        200 - 成功，包含生成的 logo_url
        200 - 失败（URL 无效），包含错误信息
    """
    data = request.json
    site_id = data.get('id')   # 目标网站 ID
    url = data.get('url')      # 网站地址
    if url:
        domain = url.split('//')[-1].split('/')[0].replace('www.', '')  # 从 URL 中提取纯域名（去掉 www. 前缀）
        logo_url = f"https://www.google.com/s2/favicons?sz=128&domain={domain}"  # 构造 Google Favicon 服务 URL（128px 高清图标）
        for site in websites_db:
            if site['id'] == site_id:
                site['logo_url'] = logo_url  # 更新内存中对应网站的图标地址
                break
        return jsonify({"status": "success", "logo_url": logo_url})
    return jsonify({"status": "error", "message": "无效的 URL"})

# --- 1. 获取收藏列表 API ---
# 加上 OPTIONS 方法，让浏览器的跨域预检顺利通过
@app.route('/api/favorites', methods=['GET', 'OPTIONS'])
def get_favorites():
    if request.method == 'OPTIONS':
        return ok()

    verify_jwt_in_request()
    user_id = get_current_user_id()
    if not user_id:
        return fail('用户不存在', 404, 404)

    favorites = UserFavorite.query.filter_by(user_id=user_id).order_by(UserFavorite.added_at.desc()).all()
    return ok([{'website_id': fav.website_id, 'added_at': fav.added_at.isoformat()} for fav in favorites])
@app.route('/api/favorites', methods=['POST', 'OPTIONS'])
def toggle_favorite():
    if request.method == 'OPTIONS':
        return ok()

    verify_jwt_in_request()
    user_id = get_current_user_id()
    if not user_id:
        return fail('用户不存在', 404, 404)

    data = request.get_json(silent=True) or {}
    website_id = data.get('website_id')
    if not website_id:
        return fail('缺少 website_id', 400, 400)

    site = Website.query.get(website_id)
    if not site:
        return fail('网站不存在', 404, 404)

    existing_fav = UserFavorite.query.filter_by(user_id=user_id, website_id=website_id).first()
    if existing_fav:
        db.session.delete(existing_fav)
        db.session.commit()
        log_user_behavior('unfavorite', website_id=website_id)
        return ok({'website_id': website_id, 'favorited': False}, '已取消收藏')

    new_fav = UserFavorite(user_id=user_id, website_id=website_id)
    db.session.add(new_fav)
    db.session.commit()
    log_user_behavior('favorite', website_id=website_id)
    return ok({'website_id': website_id, 'favorited': True}, '收藏成功', 201)


@app.route('/api/favorites/<int:website_id>', methods=['DELETE', 'OPTIONS'])
def remove_favorite(website_id):
    if request.method == 'OPTIONS':
        return ok()

    verify_jwt_in_request()
    user_id = get_current_user_id()
    if not user_id:
        return fail('用户不存在', 404, 404)

    existing_fav = UserFavorite.query.filter_by(user_id=user_id, website_id=website_id).first()
    if existing_fav:
        db.session.delete(existing_fav)
        db.session.commit()
    log_user_behavior('unfavorite', website_id=website_id)
    return ok({'website_id': website_id, 'favorited': False}, '已取消收藏')
@app.route('/api/chat', methods=['POST'])
def chat():
    """
    智能导航助手聊天接口（模拟数据版）。

    接口路径：POST /api/chat
    请求方法：POST
    功能描述：接收用户的自然语言消息，根据关键词匹配返回相应的网站推荐建议。
              当前为模拟实现，根据消息中的关键词（设计/摸鱼/游戏/代码/开发/前端）
              返回预设的推荐回复。生产环境可接入真实 AI 大模型 API。
    请求体（JSON）：
        message (str): 用户输入的消息内容
    返回：
        200 - 包含 reply 字段的 JSON 对象，reply 为助手的回复文本
    """
    data = request.json
    user_message = data.get('message', '')  # 获取用户消息，默认为空字符串
    time.sleep(1)   # 模拟 AI 思考延迟，提升用户体验感
    reply = "收到！但我现在还是个模拟数据。你可以试着在输入框里包含“设计”、“摸鱼”或“代码”等关键词。"
    if "设计" in user_message:
        reply = "找设计灵感吗？强烈推荐你去看看 Dribbble、Behance 或者站酷！"
    elif "摸鱼" in user_message or "游戏" in user_message:
        reply = "偷偷告诉你，工作累了可以去刷刷 B站 或者 抖音 放松一下~"
    elif "代码" in user_message or "开发" in user_message or "前端" in user_message:
        reply = "推荐多看 GitHub 的开源项目，遇到 Bug 直接上 StackOverflow 搜！"
    return jsonify({"reply": reply})


# ================= 1. 接口防刷配置 (Rate Limiting) =================
# 基于请求者的 IP 进行频率限制，防止恶意爆破

# 【应用防刷】给敏感接口加上限制 (在之前的路由上加装饰器)
# @app.route('/api/auth/send-code', methods=['POST'])
# @limiter.limit("1 per minute", error_message="发送太频繁，请1分钟后再试")
# def send_verification_code(): ...

# @app.route('/api/auth/login', methods=['POST'])
# @limiter.limit("5 per minute", error_message="密码尝试次数过多，请稍后再试")
# def login(): ...


# ================= 2. 管理员权限校验装饰器 =================
def admin_required():
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            username = get_jwt_identity()
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
            conn.close()
            if not user or user['role'] != 'admin':
                return jsonify({'code': 403, 'msg': '权限不足，仅管理员可访问'}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper


# ================= 3. 后台数据大盘 API =================
@app.route('/api/admin/stats', methods=['GET'])
@admin_required()
def get_admin_stats():
    today = datetime.date.today().strftime('%Y-%m-%d')
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # 今日新增用户
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE DATE(created_at) = %s", (today,))
        new_users = cursor.fetchone()['count']
        # 待审核文章
        cursor.execute("SELECT COUNT(*) as count FROM articles WHERE status = 'pending'")
        pending_articles = cursor.fetchone()['count']
        # 总阅读量
        cursor.execute("SELECT SUM(views) as total_views FROM articles")
        total_views = cursor.fetchone()['total_views'] or 0
    conn.close()
    
    return jsonify({'code': 0, 'data': {
        'new_users_today': new_users,
        'pending_articles': pending_articles,
        'total_views': int(total_views)
    }})


# ================= 4. 处理举报 & DMCA =================
@app.route('/api/report', methods=['POST'])
@jwt_required()
def submit_report():
    """兼容旧前端的通用举报接口。"""
    data = request.get_json(silent=True) or {}
    target_type = data.get('type') or data.get('target_type') or 'website'
    target_id = data.get('target_id') or data.get('website_id')
    reason = (data.get('reason') or '').strip()

    if not target_id:
        return fail('举报对象不能为空', 400, 400)
    if not reason:
        return fail('举报原因不能为空', 400, 400)

    try:
        db.session.execute(
            text("""
                INSERT INTO reports (user_id, target_type, target_id, reason, status)
                VALUES (:user_id, :target_type, :target_id, :reason, 'pending')
            """),
            {
                'user_id': get_current_user_id(),
                'target_type': target_type,
                'target_id': target_id,
                'reason': reason,
            }
        )
        db.session.commit()
        log_user_behavior('report', website_id=target_id if target_type == 'website' else None)
        return ok({'target_type': target_type, 'target_id': target_id}, '举报已提交，我们会尽快处理', 201)
    except Exception:
        db.session.rollback()
        return fail('举报提交失败，请先执行数据库迁移', 500, 500)

@app.route('/api/dmca', methods=['POST'])
@limiter.limit("3 per day") # 防止恶意提交表单
def submit_dmca():
    """提交 DMCA 版权申诉 (无需登录)"""
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip()
    url = (data.get('url') or '').strip()
    description = (data.get('desc') or data.get('description') or '').strip()

    if not all([name, email, url, description]):
        return fail('请完整填写 DMCA 投诉信息', 400, 400)

    try:
        db.session.execute(
            text("""
                INSERT INTO dmca_complaints (complainant_name, contact_email, target_url, description, status)
                VALUES (:name, :email, :url, :description, 'pending')
            """),
            {'name': name, 'email': email, 'url': url, 'description': description}
        )
        db.session.commit()
        return ok({'url': url}, '版权投诉已收到，法务团队将在 3 个工作日内联系您', 201)
    except Exception:
        db.session.rollback()
        return fail('DMCA 提交失败，请先执行数据库迁移', 500, 500)

# (文章审核、封禁用户的 CRUD API 逻辑与之前类似，此处省略重复的 UPDATE 语句，重点在于 @admin_required 保护)

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
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    category_id = request.args.get('category', request.args.get('category_id', type=int), type=int)
    search = request.args.get('search', request.args.get('q', ''), type=str)
    tag = request.args.get('tag', '', type=str)
    occupation = request.args.get('occupation', '', type=str)

    query = Website.query.filter(Website.status != 'rejected')
    if category_id:
        query = query.filter_by(category_id=category_id)
    if search:
        like = f'%{search}%'
        query = query.filter(or_(Website.name.ilike(like), Website.description.ilike(like)))

    pagination = query.order_by(Website.clicks.desc(), Website.id.asc()).paginate(page=page, per_page=per_page, error_out=False)
    items = add_site_metadata([site_to_dict(site) for site in pagination.items])

    if tag:
        items = [item for item in items if tag in item.get('tags', []) or tag in item.get('description', '')]
    if occupation:
        items = [item for item in items if occupation in item.get('occupations', [])]

    return ok({
        'items': items,
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
    })
# 2. 新增网站 (POST)
@app.route('/api/websites', methods=['POST'])
def create_website():
    data = request.get_json(silent=True) or {}
    name = data.get('name')
    url = data.get('url')
    category_id = data.get('category') or data.get('category_id')

    # 字段校验
    if not name or not url:
        return jsonify({"error": "name和url为必填项"}), 400
    if not is_valid_url(url):
        return jsonify({"error": "URL格式不正确，需包含http/https"}), 400

    new_site = Website(
        name=name,
        url=url,
        category_id=category_id,
        description=data.get('description') or '',
        logo_url=data.get('logo_url') or '',
        status=data.get('status') or 'approved',
        source=data.get('source') or 'admin',
    )
    db.session.add(new_site)
    db.session.commit()
    if data.get('tags'):
        try:
            db.session.execute(
                text("UPDATE websites SET tags = :tags WHERE id = :id"),
                {'tags': data.get('tags'), 'id': new_site.id}
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
    return jsonify({"message": "创建成功", "id": new_site.id}), 201

# 3. 获取单个详情 (GET)
@app.route('/api/websites/<int:id>', methods=['GET'])
def get_website(id):
    site = Website.query.get(id)
    if not site or site.status == 'rejected':
        return fail('网站不存在', 404, 404)
    item = add_site_metadata([site_to_dict(site)])[0]
    try:
        rating_row = db.session.execute(
            text("""
                SELECT ROUND(AVG(rating), 1) AS avg_rating, COUNT(*) AS rating_count
                FROM site_ratings WHERE website_id = :website_id
            """),
            {'website_id': id}
        ).fetchone()
        item['avg_rating'] = float(rating_row[0] or 0) if rating_row else 0
        item['rating_count'] = int(rating_row[1] or 0) if rating_row else 0
    except Exception:
        item['avg_rating'] = 0
        item['rating_count'] = 0
    return ok(item)


@app.route('/api/websites/<int:id>/comments', methods=['GET'])
def get_website_comments(id):
    site = Website.query.get(id)
    if not site or site.status == 'rejected':
        return fail('网站不存在', 404, 404)

    try:
        rows = db.session.execute(
            text("""
                SELECT id, website_id, user_id, username, content, created_at
                FROM site_comments
                WHERE website_id = :website_id AND status = 'approved'
                ORDER BY created_at DESC
                LIMIT 50
            """),
            {'website_id': id}
        ).fetchall()
        comments = [{
            'id': row[0],
            'website_id': row[1],
            'user_id': row[2],
            'username': row[3] or '匿名用户',
            'content': row[4],
            'created_at': row[5].strftime('%Y-%m-%d %H:%M') if row[5] else '',
        } for row in rows]
        return ok({'items': comments, 'total': len(comments)})
    except Exception:
        return ok({'items': [], 'total': 0})


@app.route('/api/websites/<int:id>/comments', methods=['POST'])
@jwt_required()
def create_website_comment(id):
    site = Website.query.get(id)
    if not site or site.status == 'rejected':
        return fail('网站不存在', 404, 404)

    data = request.get_json(silent=True) or {}
    content = (data.get('content') or '').strip()
    if not content:
        return fail('评论内容不能为空', 400, 400)
    if len(content) > 500:
        return fail('评论内容不能超过 500 字', 400, 400)

    user = User.query.filter_by(username=get_jwt_identity()).first()
    try:
        db.session.execute(
            text("""
                INSERT INTO site_comments (website_id, user_id, username, content)
                VALUES (:website_id, :user_id, :username, :content)
            """),
            {
                'website_id': id,
                'user_id': user.id if user else None,
                'username': user.username if user else get_jwt_identity(),
                'content': content,
            }
        )
        db.session.commit()
        log_user_behavior('comment', website_id=id)
        return ok({'website_id': id}, '评论已发布', 201)
    except Exception:
        db.session.rollback()
        return fail('评论保存失败，请先执行数据库迁移', 500, 500)


@app.route('/api/websites/<int:id>/rating', methods=['POST'])
@jwt_required()
def rate_website(id):
    site = Website.query.get(id)
    if not site or site.status == 'rejected':
        return fail('网站不存在', 404, 404)

    data = request.get_json(silent=True) or {}
    rating = int(data.get('rating') or 0)
    if rating < 1 or rating > 5:
        return fail('评分必须在 1 到 5 之间', 400, 400)

    user_id = get_current_user_id()
    if not user_id:
        return fail('用户不存在', 404, 404)

    try:
        db.session.execute(
            text("""
                INSERT INTO site_ratings (website_id, user_id, rating)
                VALUES (:website_id, :user_id, :rating)
                ON DUPLICATE KEY UPDATE rating = VALUES(rating), updated_at = CURRENT_TIMESTAMP
            """),
            {'website_id': id, 'user_id': user_id, 'rating': rating}
        )
        db.session.commit()
        log_user_behavior('rate', website_id=id)
        return ok({'website_id': id, 'rating': rating}, '评分已保存')
    except Exception:
        db.session.rollback()
        return fail('评分保存失败，请先执行数据库迁移', 500, 500)
# 4. 更新网站 (PUT)
@app.route('/api/websites/<int:id>', methods=['PUT'])
def update_website(id):
    site = Website.query.get(id)
    if not site:
        return jsonify({"error": "网站不存在"}), 404
        
    data = request.get_json(silent=True) or {}
    if 'name' in data: 
        site.name = data['name']
    if 'url' in data:
        if not is_valid_url(data['url']):
            return jsonify({"error": "URL格式不正确"}), 400
        site.url = data['url']
    if 'category_id' in data: 
        site.category_id = data['category_id']
    if 'category' in data:
        site.category_id = data['category']
    if 'description' in data:
        site.description = data['description']
    if 'logo_url' in data:
        site.logo_url = data['logo_url']
    if 'status' in data:
        site.status = data['status']
    if 'tags' in data:
        try:
            db.session.execute(
                text("UPDATE websites SET tags = :tags WHERE id = :id"),
                {'tags': data.get('tags') or '', 'id': id}
            )
        except Exception:
            pass

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


@app.route('/api/search', methods=['GET'])
def search_websites():
    keyword = request.args.get('q', '', type=str).strip()
    category_id = request.args.get('category_id', request.args.get('category', type=int), type=int)
    tag = request.args.get('tag', '', type=str).strip()
    occupation = request.args.get('occupation', '', type=str).strip()
    limit = min(request.args.get('limit', 30, type=int), 100)

    query = Website.query.filter(Website.status != 'rejected')
    if category_id:
        query = query.filter_by(category_id=category_id)
    if keyword:
        like = f'%{keyword}%'
        query = query.filter(or_(Website.name.ilike(like), Website.description.ilike(like), Website.url.ilike(like)))

    items = add_site_metadata([site_to_dict(site) for site in query.order_by(Website.clicks.desc()).limit(limit).all()])
    if tag:
        items = [item for item in items if tag in item.get('tags', []) or tag in item.get('description', '')]
    if occupation:
        items = [item for item in items if occupation in item.get('occupations', [])]

    if keyword:
        log_user_behavior('search', keyword=keyword)

    return ok({'items': items, 'total': len(items), 'query': keyword})


@app.route('/api/admin/websites', methods=['GET'])
def admin_list_websites():
    return get_websites()


@app.route('/api/admin/websites', methods=['POST'])
def admin_create_website():
    return create_website()


@app.route('/api/admin/websites/<int:id>', methods=['PUT'])
def admin_update_website(id):
    return update_website(id)


@app.route('/api/admin/websites/<int:id>', methods=['DELETE'])
def admin_delete_website(id):
    return delete_website(id)


@app.route('/api/admin/categories', methods=['GET', 'POST'])
def admin_categories():
    if request.method == 'GET':
        categories = Category.query.order_by(Category.sort_order.asc(), Category.id.asc()).all()
        return ok([{
            'id': c.id,
            'name': c.name,
            'profession_type': c.profession_type or 'general',
            'sort_order': c.sort_order or 0,
        } for c in categories])

    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return fail('分类名称不能为空', 400, 400)
    category = Category(
        name=name,
        profession_type=data.get('profession_type') or 'general',
        sort_order=data.get('sort_order') or 0,
    )
    db.session.add(category)
    db.session.commit()
    return ok({'id': category.id}, '分类已创建', 201)


@app.route('/api/admin/categories/<int:id>', methods=['PUT', 'DELETE'])
def admin_category_detail(id):
    category = Category.query.get(id)
    if not category:
        return fail('分类不存在', 404, 404)

    if request.method == 'DELETE':
        db.session.delete(category)
        db.session.commit()
        return ok({'id': id}, '分类已删除')

    data = request.get_json(silent=True) or {}
    if 'name' in data:
        category.name = data['name']
    if 'profession_type' in data:
        category.profession_type = data['profession_type']
    if 'sort_order' in data:
        category.sort_order = data['sort_order']
    db.session.commit()
    return ok({'id': id}, '分类已更新')


@app.route('/api/admin/tags', methods=['GET', 'POST'])
def admin_tags():
    if request.method == 'GET':
        try:
            rows = db.session.execute(text("SELECT id, name, slug, type FROM tags ORDER BY id ASC")).fetchall()
            return ok([{'id': r[0], 'name': r[1], 'slug': r[2], 'type': r[3]} for r in rows])
        except Exception:
            return ok([])

    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return fail('标签名称不能为空', 400, 400)
    slug = data.get('slug') or re.sub(r'\\s+', '-', name.lower())
    tag_type = data.get('type') or 'interest'
    db.session.execute(
        text("INSERT INTO tags (name, slug, type) VALUES (:name, :slug, :type)"),
        {'name': name, 'slug': slug, 'type': tag_type}
    )
    db.session.commit()
    return ok({'name': name, 'slug': slug, 'type': tag_type}, '标签已创建', 201)


@app.route('/api/admin/tags/<int:id>', methods=['PUT', 'DELETE'])
def admin_tag_detail(id):
    if request.method == 'DELETE':
        db.session.execute(text("DELETE FROM tags WHERE id = :id"), {'id': id})
        db.session.commit()
        return ok({'id': id}, '标签已删除')

    data = request.get_json(silent=True) or {}
    db.session.execute(
        text("""
            UPDATE tags
            SET name = COALESCE(:name, name),
                slug = COALESCE(:slug, slug),
                type = COALESCE(:type, type)
            WHERE id = :id
        """),
        {'id': id, 'name': data.get('name'), 'slug': data.get('slug'), 'type': data.get('type')}
    )
    db.session.commit()
    return ok({'id': id}, '标签已更新')


@app.route('/api/user/profile', methods=['GET'])
@jwt_required()
def user_profile():
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    if not user:
        return fail('用户不存在', 404, 404)

    favorite_count = 0
    comment_count = 0
    try:
        favorite_count = UserFavorite.query.filter_by(user_id=user.id).count()
    except Exception:
        favorite_count = 0
    try:
        row = db.session.execute(
            text("SELECT COUNT(*) FROM site_comments WHERE user_id = :user_id"),
            {'user_id': user.id}
        ).fetchone()
        comment_count = int(row[0] or 0) if row else 0
    except Exception:
        comment_count = 0

    return ok({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'avatar': user.avatar_url or '',
        'created_at': user.created_at.strftime('%Y-%m-%d') if user.created_at else '',
        'has_survey': getattr(user, 'has_survey', 0) or 0,
        'user_tags': getattr(user, 'user_tags', '') or getattr(user, 'interests', '') or '',
        'favorite_count': favorite_count,
        'comment_count': comment_count,
    })


@app.route('/api/user/activity', methods=['GET'])
@jwt_required()
def user_activity():
    user = User.query.filter_by(username=get_jwt_identity()).first()
    if not user:
        return fail('用户不存在', 404, 404)

    activity = []
    comments = []
    try:
        rows = db.session.execute(
            text("""
                SELECT ub.id, ub.action, ub.website_id, ub.keyword, ub.created_at, w.name
                FROM user_behavior ub
                LEFT JOIN websites w ON w.id = ub.website_id
                WHERE ub.user_id = :user_id
                ORDER BY ub.created_at DESC
                LIMIT 50
            """),
            {'user_id': user.id}
        ).fetchall()
        activity = [{
            'id': row[0],
            'action': row[1],
            'website_id': row[2],
            'keyword': row[3],
            'created_at': row[4].strftime('%Y-%m-%d %H:%M') if row[4] else '',
            'website_name': row[5] or '',
        } for row in rows]
    except Exception:
        activity = []

    try:
        rows = db.session.execute(
            text("""
                SELECT sc.id, sc.website_id, sc.content, sc.status, sc.created_at, w.name
                FROM site_comments sc
                LEFT JOIN websites w ON w.id = sc.website_id
                WHERE sc.user_id = :user_id
                ORDER BY sc.created_at DESC
                LIMIT 30
            """),
            {'user_id': user.id}
        ).fetchall()
        comments = [{
            'id': row[0],
            'website_id': row[1],
            'content': row[2],
            'status': row[3],
            'created_at': row[4].strftime('%Y-%m-%d %H:%M') if row[4] else '',
            'website_name': row[5] or '',
        } for row in rows]
    except Exception:
        comments = []

    return ok({'activity': activity, 'comments': comments})


@app.route('/api/admin/overview', methods=['GET'])
def admin_overview():
    def scalar(sql):
        try:
            row = db.session.execute(text(sql)).fetchone()
            return int(row[0] or 0) if row else 0
        except Exception:
            return 0

    return ok({
        'users': scalar("SELECT COUNT(*) FROM users WHERE deleted_at IS NULL"),
        'websites': scalar("SELECT COUNT(*) FROM websites WHERE status != 'rejected'"),
        'favorites': scalar("SELECT COUNT(*) FROM user_favorites"),
        'comments': scalar("SELECT COUNT(*) FROM site_comments"),
        'today_visits': scalar("SELECT COUNT(*) FROM user_behavior WHERE action = 'visit' AND DATE(created_at) = CURDATE()"),
        'reports': scalar("SELECT COUNT(*) FROM reports WHERE status = 'pending'"),
        'dmca': scalar("SELECT COUNT(*) FROM dmca_complaints WHERE status = 'pending'"),
    })


@app.route('/api/admin/comments', methods=['GET'])
def admin_comments():
    try:
        rows = db.session.execute(
            text("""
                SELECT sc.id, sc.website_id, sc.user_id, sc.username, sc.content, sc.status, sc.created_at, w.name
                FROM site_comments sc
                LEFT JOIN websites w ON w.id = sc.website_id
                ORDER BY sc.created_at DESC
                LIMIT 100
            """)
        ).fetchall()
        return ok([{
            'id': row[0],
            'website_id': row[1],
            'user_id': row[2],
            'username': row[3] or '匿名用户',
            'content': row[4],
            'status': row[5],
            'created_at': row[6].strftime('%Y-%m-%d %H:%M') if row[6] else '',
            'website_name': row[7] or '',
        } for row in rows])
    except Exception:
        return ok([])


@app.route('/api/admin/comments/<int:id>/review', methods=['POST'])
def admin_review_comment(id):
    data = request.get_json(silent=True) or {}
    status = data.get('status') or data.get('action') or 'approved'
    if status not in ['approved', 'pending', 'rejected']:
        return fail('评论状态无效', 400, 400)
    try:
        db.session.execute(
            text("UPDATE site_comments SET status = :status WHERE id = :id"),
            {'status': status, 'id': id}
        )
        db.session.commit()
        return ok({'id': id, 'status': status}, '评论状态已更新')
    except Exception:
        db.session.rollback()
        return fail('评论状态更新失败，请先执行数据库迁移', 500, 500)


@app.route('/api/admin/comments/<int:id>', methods=['DELETE'])
def admin_delete_comment(id):
    try:
        db.session.execute(text("DELETE FROM site_comments WHERE id = :id"), {'id': id})
        db.session.commit()
        return ok({'id': id}, '评论已删除')
    except Exception:
        db.session.rollback()
        return fail('评论删除失败，请先执行数据库迁移', 500, 500)


@app.route('/api/websites/<int:id>/report', methods=['POST'])
@jwt_required()
def report_website(id):
    data = request.get_json(silent=True) or {}
    reason = (data.get('reason') or '').strip()
    if not reason:
        return fail('举报原因不能为空', 400, 400)
    user_id = get_current_user_id()
    try:
        db.session.execute(
            text("""
                INSERT INTO reports (user_id, target_type, target_id, reason, status)
                VALUES (:user_id, 'website', :target_id, :reason, 'pending')
            """),
            {'user_id': user_id, 'target_id': id, 'reason': reason}
        )
        db.session.commit()
        log_user_behavior('report', website_id=id)
        return ok({'website_id': id}, '举报已提交', 201)
    except Exception:
        db.session.rollback()
        return fail('举报提交失败，请先执行数据库迁移', 500, 500)


@app.route('/api/admin/reports', methods=['GET'])
def admin_reports():
    try:
        rows = db.session.execute(
            text("""
                SELECT r.id, r.user_id, r.target_type, r.target_id, r.reason, r.status, r.created_at, w.name
                FROM reports r
                LEFT JOIN websites w ON w.id = r.target_id AND r.target_type = 'website'
                ORDER BY r.created_at DESC
                LIMIT 100
            """)
        ).fetchall()
        return ok([{
            'id': row[0],
            'user_id': row[1],
            'target_type': row[2],
            'target_id': row[3],
            'reason': row[4],
            'status': row[5],
            'created_at': row[6].strftime('%Y-%m-%d %H:%M') if row[6] else '',
            'target_name': row[7] or '',
        } for row in rows])
    except Exception:
        return ok([])


@app.route('/api/admin/reports/<int:id>/status', methods=['POST'])
def admin_report_status(id):
    data = request.get_json(silent=True) or {}
    status = data.get('status') or 'processed'
    if status not in ['pending', 'processed', 'rejected']:
        return fail('举报状态无效', 400, 400)
    try:
        db.session.execute(text("UPDATE reports SET status = :status WHERE id = :id"), {'status': status, 'id': id})
        db.session.commit()
        return ok({'id': id, 'status': status}, '举报状态已更新')
    except Exception:
        db.session.rollback()
        return fail('举报状态更新失败，请先执行数据库迁移', 500, 500)


@app.route('/api/admin/dmca', methods=['GET'])
def admin_dmca():
    try:
        rows = db.session.execute(
            text("""
                SELECT id, complainant_name, contact_email, target_url, description, status, created_at
                FROM dmca_complaints
                ORDER BY created_at DESC
                LIMIT 100
            """)
        ).fetchall()
        return ok([{
            'id': row[0],
            'name': row[1],
            'email': row[2],
            'url': row[3],
            'description': row[4],
            'status': row[5],
            'created_at': row[6].strftime('%Y-%m-%d %H:%M') if row[6] else '',
        } for row in rows])
    except Exception:
        return ok([])


@app.route('/api/admin/dmca/<int:id>/status', methods=['POST'])
def admin_dmca_status(id):
    data = request.get_json(silent=True) or {}
    status = data.get('status') or 'processed'
    if status not in ['pending', 'processed', 'rejected']:
        return fail('DMCA 状态无效', 400, 400)
    try:
        db.session.execute(text("UPDATE dmca_complaints SET status = :status WHERE id = :id"), {'status': status, 'id': id})
        db.session.commit()
        return ok({'id': id, 'status': status}, 'DMCA 状态已更新')
    except Exception:
        db.session.rollback()
        return fail('DMCA 状态更新失败，请先执行数据库迁移', 500, 500)

# ================= 📝 个性化问卷与推荐接口 =================
# 注：问卷与推荐路由已统一迁移到 app_extensions.register_survey_routes() 中管理
# 详见 backend/app_extensions.py 第 786 行起

@app.route('/api/user/survey_status', methods=['GET'])
@jwt_required()
def get_survey_status():
    """查询当前用户的问卷状态（供前端判断是否需要弹出问卷）"""
    username = get_jwt_identity()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT has_survey, user_tags FROM users WHERE username = %s",
                (username,)
            )
            row = cursor.fetchone()
            return jsonify({
                'code': 0,
                'data': {
                    'has_survey': row['has_survey'] if row else 0,
                    'user_tags': row['user_tags'] if row else ''
                }
            })
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e)}), 500
    finally:
        conn.close()


# ⚠️ 以下两个路由 (/api/user/survey、/api/recommendations/websites)
# 已由 app_extensions.register_survey_routes() 统一注册，此处删除重复定义。
# 如需查看推荐路由实现，参见 backend/app_extensions.py

# =====================================================================
# 注册所有扩展模块
# =====================================================================
app_extensions.register_redis_sync_scheduler(app, scheduler, redis_client)
app_extensions.register_password_reset_routes(app, redis_client)
app_extensions.register_token_refresh_route(app)
app_extensions.register_content_filter_routes(app)
app_extensions.register_notification_routes(app, db)
app_extensions.register_hot_ranking_routes(app, redis_client)
app_extensions.register_admin_user_routes(app, db)
app_extensions.register_stats_overview_routes(app, db)
app_extensions.register_content_audit_routes(app, db)
app_extensions.register_survey_routes(app, db)
app.logger.info('所有扩展模块注册完成')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # 启动时自动同步所有分类和网站到数据库
        try:
            from init_db import all_categories, all_sites, get_logo_url
            conn = pool_get_connection()
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


