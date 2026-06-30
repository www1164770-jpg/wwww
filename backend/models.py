from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar = db.Column(db.String(255))
    avatar_url = db.Column(db.String(255))
    role = db.Column(db.String(32), default="user")
    questionnaire_completed = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(32), default="active")
    dark_mode = db.Column(db.Boolean, default=False)
    custom_wallpaper = db.Column(db.Text)
    current_engine = db.Column(db.String(20), default="bing")
    selected_engines = db.Column(db.Text)
    user_tags = db.Column(db.Text)
    has_survey = db.Column(db.Boolean, default=False)
    interests = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)


class UserProfile(db.Model):
    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    occupation = db.Column(db.String(64))
    skill_level = db.Column(db.String(32))
    interests = db.Column(db.Text)
    preferences = db.Column(db.Text)
    purposes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    name = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(120))
    profession_type = db.Column(db.String(20), default="general")
    sort_order = db.Column(db.Integer, default=0)
    status = db.Column(db.String(32), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    websites = db.relationship("Website", backref="category", lazy=True)


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    type = db.Column(db.String(32), default="general")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Website(db.Model):
    __tablename__ = "websites"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    logo_url = db.Column(db.String(500))
    summary = db.Column(db.String(500))
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    is_free = db.Column(db.Boolean, default=True)
    need_login = db.Column(db.Boolean, default=False)
    region = db.Column(db.String(32), default="domestic")
    quality_score = db.Column(db.Float, default=0)
    recommend_level = db.Column(db.Integer, default=0)
    click_count = db.Column(db.Integer, default=0)
    favorite_count = db.Column(db.Integer, default=0)
    rating_avg = db.Column(db.Float, default=0)
    clicks = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="approved")
    source = db.Column(db.String(50), default="admin")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SiteTag(db.Model):
    __tablename__ = "site_tags"

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("websites.id"), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey("tags.id"), nullable=False)


class SiteOccupation(db.Model):
    __tablename__ = "site_occupations"

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("websites.id"), nullable=False)
    occupation = db.Column(db.String(64), nullable=False)
    weight = db.Column(db.Float, default=1)


class Favorite(db.Model):
    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey("websites.id"), nullable=False)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey("websites.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer)
    status = db.Column(db.String(32), default="visible")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserBehavior(db.Model):
    __tablename__ = "user_behaviors"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    site_id = db.Column(db.Integer, db.ForeignKey("websites.id"))
    behavior_type = db.Column(db.String(32), nullable=False)
    keyword = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RecommendationLog(db.Model):
    __tablename__ = "recommendation_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey("websites.id"), nullable=False)
    score = db.Column(db.Float, default=0)
    reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ClickLog(db.Model):
    __tablename__ = "click_logs"

    id = db.Column(db.Integer, primary_key=True)
    website_id = db.Column(db.Integer, db.ForeignKey("websites.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
