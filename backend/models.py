from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects import mysql

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    authing_sub = db.Column(db.String(128), nullable=True, unique=True)
    login_provider = db.Column(db.String(50), default="local")
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


class UserBackground(db.Model):
    __tablename__ = "user_backgrounds"

    id = db.Column(mysql.BIGINT(unsigned=True), primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE", name="fk_user_backgrounds_user"),
        nullable=False,
    )
    storage_path = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(
        db.String(32), nullable=False, default="image/webp", server_default=db.text("'image/webp'")
    )
    file_size = db.Column(mysql.INTEGER(unsigned=True), nullable=False)
    width = db.Column(mysql.SMALLINT(unsigned=True), nullable=False)
    height = db.Column(mysql.SMALLINT(unsigned=True), nullable=False)
    status = db.Column(
        db.Enum("active", "deleted"), nullable=False, default="active", server_default=db.text("'active'")
    )
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, server_default=db.text("CURRENT_TIMESTAMP")
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        server_onupdate=db.text("CURRENT_TIMESTAMP"),
    )

    __table_args__ = (
        db.UniqueConstraint("storage_path", name="uq_user_backgrounds_storage_path"),
        db.Index("idx_user_backgrounds_user_status_created", "user_id", "status", "created_at"),
        db.CheckConstraint(
            "file_size > 0 AND file_size <= 10485760", name="chk_user_backgrounds_size"
        ),
        db.CheckConstraint("width > 0 AND height > 0", name="chk_user_backgrounds_dimensions"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )


class UserBackgroundSetting(db.Model):
    __tablename__ = "user_background_settings"

    id = db.Column(mysql.BIGINT(unsigned=True), primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE", name="fk_user_background_settings_user"),
        nullable=False,
    )
    page_type = db.Column(
        db.Enum("global", "home", "category", "favorites", "ai_assistant", "profile"),
        nullable=False,
    )
    background_id = db.Column(
        mysql.BIGINT(unsigned=True),
        db.ForeignKey(
            "user_backgrounds.id",
            ondelete="SET NULL",
            name="fk_user_background_settings_background",
        ),
        nullable=True,
    )
    overlay_opacity = db.Column(
        db.Numeric(3, 2), nullable=False, default=0.36, server_default=db.text("0.36")
    )
    blur_px = db.Column(mysql.TINYINT(unsigned=True), nullable=False, default=0, server_default=db.text("0"))
    position_x = db.Column(mysql.TINYINT(unsigned=True), nullable=False, default=50, server_default=db.text("50"))
    position_y = db.Column(mysql.TINYINT(unsigned=True), nullable=False, default=50, server_default=db.text("50"))
    size_mode = db.Column(
        db.Enum("cover", "contain", "auto"), nullable=False, default="cover", server_default=db.text("'cover'")
    )
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, server_default=db.text("CURRENT_TIMESTAMP")
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        server_onupdate=db.text("CURRENT_TIMESTAMP"),
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "page_type", name="uq_user_background_settings_page"),
        db.Index("idx_user_background_settings_background", "background_id"),
        db.CheckConstraint(
            "overlay_opacity >= 0.00 AND overlay_opacity <= 0.70",
            name="chk_user_background_settings_overlay",
        ),
        db.CheckConstraint("blur_px <= 20", name="chk_user_background_settings_blur"),
        db.CheckConstraint("position_x <= 100", name="chk_user_background_settings_x"),
        db.CheckConstraint("position_y <= 100", name="chk_user_background_settings_y"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )


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
