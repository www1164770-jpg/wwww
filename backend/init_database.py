"""
初始化数据库表结构
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
for env_path in (BACKEND_DIR / ".env", BACKEND_DIR.parent / ".env"):
    if env_path.exists():
        load_dotenv(env_path, override=False)

sys.path.insert(0, str(BACKEND_DIR))

from flask import Flask
from models import db
import questionnaire_models  # noqa: 导入问卷模型以注册到元数据

app = Flask(__name__)
db_path = BACKEND_DIR / "instance" / "zhihui.db"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{db_path}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 确保 instance 目录存在
db_path.parent.mkdir(parents=True, exist_ok=True)

db.init_app(app)

with app.app_context():
    print(f"Creating all tables in: {app.config['SQLALCHEMY_DATABASE_URI']}")
    db.create_all()
    print("✓ Database tables created successfully")
    
    # 列出创建的表
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"\nCreated {len(tables)} tables:")
    for table in tables:
        print(f"  - {table}")
