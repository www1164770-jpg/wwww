"""
MySQL 连接池模块 (基于 DBUtils.PooledDB)
=========================================
替代原先每次请求都 connect()/close() 的原始模式，
通过连接池复用数据库连接，避免高并发下的 "Too many connections" 崩溃。

使用方式：
    from db_pool import get_connection
    conn = get_connection()
    # ... 使用 conn ...
    conn.close()  # 并非真正关闭，而是归还到连接池

配置从 .env 环境变量读取，如未配置则使用默认值。
"""

import os
from dotenv import load_dotenv
from dbutils.pooled_db import PooledDB
import pymysql

load_dotenv()

# 连接池配置
POOL_CONFIG = {
    'creator': pymysql,  # 使用 pymysql 作为数据库驱动
    'maxconnections': 20,      # 最大连接数（可根据服务器配置调整）
    'mincached': 2,            # 初始化时预创建的空闲连接数
    'maxcached': 10,           # 连接池中最大空闲连接数
    'maxshared': 10,           # 最大共享连接数（通常与 maxcached 一致）
    'blocking': True,          # 连接池满时阻塞等待，False 则直接抛异常
    'maxusage': None,          # 单个连接最多被重复使用的次数（None 表示无限制）
    'setsession': None,        # 连接创建后可执行的初始化 SQL 命令列表
    'ping': 0,                 # ping MySQL 服务端检测连接活性: 0=不检测, 1=默认, 2=每次, 4=每4次
    'host': os.getenv('MYSQL_HOST') or os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT') or os.getenv('DB_PORT', '3306')),
    'user': os.getenv('MYSQL_USER') or os.getenv('DB_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD') or os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE') or os.getenv('DB_NAME', 'nav_site'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,  # 返回字典格式的查询结果
    'autocommit': False,       # 关闭自动提交，由业务代码手动 commit
}

# 全局连接池实例（单例）
_pool = None

def get_pool():
    """获取或创建连接池实例（懒初始化单例）"""
    global _pool
    if _pool is None:
        _pool = PooledDB(**POOL_CONFIG)
    return _pool

def get_connection():
    """
    从连接池获取一个数据库连接。

    用法：
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT ...")
            conn.commit()
        finally:
            conn.close()  # 归还到连接池，并非真正关闭

    注意：调用 conn.close() 会将连接归还到池中供复用，
    不会真的断开与 MySQL 的连接。
    """
    return get_pool().connection()
