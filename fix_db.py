import sys
from pathlib import Path

import pymysql

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR if (SCRIPT_DIR / "backend").is_dir() else SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.db_pool import get_database_config, validate_database_config


def run():
    config = validate_database_config(get_database_config())
    conn = pymysql.connect(**config)
    try:
        cursor = conn.cursor()
        cursor.execute('DESCRIBE categories')
        cols = [row[0] for row in cursor.fetchall()]
        print('当前categories表字段:', cols)
        if 'profession_type' not in cols:
            cursor.execute("ALTER TABLE categories ADD COLUMN profession_type VARCHAR(20) DEFAULT 'general' AFTER name")
            print('已添加 profession_type 字段')
        if 'sort_order' not in cols:
            cursor.execute('ALTER TABLE categories ADD COLUMN sort_order INT DEFAULT 0 AFTER profession_type')
            print('已添加 sort_order 字段')
        conn.commit()
    finally:
        conn.close()
    print('完成')


if __name__ == "__main__":
    run()
