from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    avatar_url = db.Column(db.String(255))
    
    # ✨ 核心：个性化配置字段
    dark_mode = db.Column(db.Boolean, default=False)
    custom_wallpaper = db.Column(db.Text)  # 壁纸可能是很长的 Base64 图片，用 Text
    current_engine = db.Column(db.String(20), default='bing')
    selected_engines = db.Column(db.Text)

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    profession_type = db.Column(db.String(20), default='general')
    sort_order = db.Column(db.Integer, default=0)
    # 建立与网站的反向关联
    websites = db.relationship('Website', backref='category', lazy=True, cascade="all, delete-orphan")

class Website(db.Model):
    __tablename__ = 'websites'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    logo_url = db.Column(db.String(500))
    clicks = db.Column(db.Integer, default=0)
    #created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ClickLog(db.Model):
    __tablename__ = 'click_logs'
    id = db.Column(db.Integer, primary_key=True)
    website_id = db.Column(db.Integer, db.ForeignKey('websites.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)