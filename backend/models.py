from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

# 创建全局 SQLAlchemy 实例，在 app.py 中通过 db.init_app(app) 与 Flask 应用绑定
db = SQLAlchemy()

class User(db.Model):
    """
    用户表，存储注册用户的账号信息和个性化配置。
    对应数据库表名：users
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)                          # 用户唯一 ID，自增主键
    username = db.Column(db.String(50), nullable=False, unique=True)      # 用户名，不可为空且全局唯一
    avatar_url = db.Column(db.String(255))                                # 用户头像 URL，可为空
    # ✨ 新增：认证核心字段
    email = db.Column(db.String(120), unique=True, nullable=False)        # 邮箱地址，用于登录，全局唯一
    password_hash = db.Column(db.String(255), nullable=False)             # 经过哈希处理的密码，不存明文
    created_at = db.Column(db.DateTime, default=datetime.utcnow)          # 账号注册时间，默认取 UTC 当前时间
    
    # ✨ 核心：个性化配置字段
    dark_mode = db.Column(db.Boolean, default=False)                      # 是否开启深色模式，默认关闭
    custom_wallpaper = db.Column(db.Text)                                 # 壁纸可能是很长的 Base64 图片，用 Text
    current_engine = db.Column(db.String(20), default='bing')             # 当前选用的搜索引擎，默认 bing
    selected_engines = db.Column(db.Text)                                 # 用户勾选的搜索引擎列表，JSON 字符串存储

class Category(db.Model):
    """
    分类表，用于对导航网站进行分组管理。
    支持按职业类型（profession_type）区分不同人群的分类，如前端开发、UI 设计师等。
    对应数据库表名：categories
    """
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)                          # 分类唯一 ID，自增主键
    name = db.Column(db.String(50), nullable=False)                       # 分类名称，如"常用推荐"、"框架文档"
    profession_type = db.Column(db.String(20), default='general')         # 职业类型标识，如 general/frontend/designer/product
    sort_order = db.Column(db.Integer, default=0)                         # 同一职业类型下的排列顺序，数字越小越靠前
    # 建立与网站的反向关联
    websites = db.relationship('Website', backref='category', lazy=True, cascade="all, delete-orphan")
    # websites：一对多关系，通过 backref 在 Website 上注入 .category 属性；
    # cascade="all, delete-orphan" 表示删除分类时同步删除其下所有网站

class Website(db.Model):
    """
    网站表，存储导航站收录的每一个网站条目。
    包含基本信息（名称、URL、Logo）、统计数据（点击量）以及审核状态。
    对应数据库表名：websites
    """
    __tablename__ = 'websites'
    id = db.Column(db.Integer, primary_key=True)                          # 网站唯一 ID，自增主键
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)  # 所属分类 ID，外键关联 categories 表
    name = db.Column(db.String(100), nullable=False)                      # 网站名称，如"GitHub"
    url = db.Column(db.String(500), nullable=False)                       # 网站地址，最长 500 字符
    logo_url = db.Column(db.String(500))                                  # 网站 Logo 图片地址，通常为 Google Favicon 接口 URL
    clicks = db.Column(db.Integer, default=0)                             # 累计点击次数，用于热度排序
    #created_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(500), nullable=True)                # 网站简介，可为空
    # 状态：'approved' (已发布), 'pending' (待审核), 'rejected' (已拒绝)
    status = db.Column(db.String(20), default='approved')                 # 审核状态，新增网站默认直接发布
    
    # 来源：打个标记，比如 'admin', 'hackernews', 'github'
    source = db.Column(db.String(50), default='admin')                    # 数据来源标记，区分管理员录入还是爬虫抓取

class ClickLog(db.Model):
    """
    点击日志表，记录每次用户点击网站的时间戳。
    可用于统计网站的访问趋势，或按时间段分析热度。
    对应数据库表名：click_logs
    """
    __tablename__ = 'click_logs'
    id = db.Column(db.Integer, primary_key=True)                          # 日志唯一 ID，自增主键
    website_id = db.Column(db.Integer, db.ForeignKey('websites.id'), nullable=False)  # 被点击的网站 ID，外键关联 websites 表
    created_at = db.Column(db.DateTime, default=datetime.utcnow)          # 点击发生的时间，默认取 UTC 当前时间
