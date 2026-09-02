from pathlib import Path
import os
import sys

import pymysql
from dotenv import load_dotenv


backend_dir = Path(__file__).resolve().parent
env_file = backend_dir / ".env"

print("=" * 60)
print("管理员账号检查与设置工具")
print("=" * 60)

if not env_file.exists():
    print(f"错误：找不到配置文件：{env_file}")
    sys.exit(1)

load_dotenv(env_file)

# 同时兼容 MYSQL_* 和当前项目使用的 DB_* 配置
db_host = (
    os.getenv("MYSQL_HOST")
    or os.getenv("DB_HOST")
    or "localhost"
).strip()

db_port = int(
    os.getenv("MYSQL_PORT")
    or os.getenv("DB_PORT")
    or "3306"
)

db_user = (
    os.getenv("MYSQL_USER")
    or os.getenv("DB_USER")
    or ""
).strip()

db_password = os.getenv("MYSQL_PASSWORD")
if db_password is None:
    db_password = os.getenv("DB_PASSWORD", "")

db_name = (
    os.getenv("MYSQL_DATABASE")
    or os.getenv("DB_NAME")
    or ""
).strip()

if not db_user:
    print("错误：backend/.env 中没有配置 DB_USER 或 MYSQL_USER。")
    sys.exit(1)

if not db_name:
    print("错误：backend/.env 中没有配置 DB_NAME 或 MYSQL_DATABASE。")
    sys.exit(1)

print(f"数据库地址：{db_host}:{db_port}")
print(f"数据库用户：{db_user}")
print(f"数据库名称：{db_name}")

connection = None

try:
    print("\n正在连接数据库……")

    connection = pymysql.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_name,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        autocommit=False,
    )

    print("数据库连接成功。")

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, username, email, role
            FROM users
            ORDER BY id ASC
            """
        )
        users = cursor.fetchall()

        if not users:
            print("\n数据库中暂时没有用户账号。")
            print("请先在网站注册账号。")
            sys.exit(0)

        print("\n当前所有用户：")
        print("-" * 80)

        for user in users:
            role = user.get("role") or "user"
            print(
                f"ID：{user['id']} | "
                f"用户名：{user['username']} | "
                f"邮箱：{user['email']} | "
                f"角色：{role}"
            )

        print("-" * 80)

        administrators = [
            user
            for user in users
            if str(user.get("role") or "").strip().lower()
            in ("admin", "super_admin")
        ]

        if administrators:
            print(f"\n已经存在 {len(administrators)} 个管理员账号：")

            for user in administrators:
                print(
                    f"ID：{user['id']}，"
                    f"用户名：{user['username']}，"
                    f"角色：{user['role']}"
                )
        else:
            print("\n当前不存在管理员账号。")

        print("\n只查看管理员时，直接按回车退出。")
        user_id_text = input(
            "需要设置管理员时，请输入用户 ID："
        ).strip()

        if not user_id_text:
            print("检查完成，没有修改数据库。")
            sys.exit(0)

        try:
            user_id = int(user_id_text)
        except ValueError:
            print("错误：用户 ID 必须是数字。")
            sys.exit(1)

        target_user = next(
            (user for user in users if int(user["id"]) == user_id),
            None,
        )

        if not target_user:
            print(f"错误：找不到 ID 为 {user_id} 的用户。")
            sys.exit(1)

        print("\n准备设置以下账号为管理员：")
        print(f"用户名：{target_user['username']}")
        print(f"邮箱：{target_user['email']}")
        print(f"当前角色：{target_user.get('role') or 'user'}")

        confirm = input("输入 y 确认修改：").strip().lower()

        if confirm != "y":
            print("操作已取消，没有修改数据库。")
            sys.exit(0)

        cursor.execute(
            """
            UPDATE users
            SET role = 'admin'
            WHERE id = %s
            """,
            (user_id,),
        )

        connection.commit()

        print("\n设置成功。")
        print(f"用户 {target_user['username']} 已成为管理员。")
        print("请退出网站账号，然后重新登录。")

except pymysql.err.OperationalError as error:
    if connection:
        connection.rollback()

    print("\n数据库连接失败。")
    print(f"错误信息：{error}")
    print("请检查 backend/.env 中的数据库地址、用户名和密码。")
    sys.exit(1)

except pymysql.MySQLError as error:
    if connection:
        connection.rollback()

    print("\n数据库操作失败。")
    print(f"错误信息：{error}")
    sys.exit(1)

except Exception as error:
    if connection:
        connection.rollback()

    print("\n程序执行失败。")
    print(f"错误类型：{type(error).__name__}")
    print(f"错误信息：{error}")
    sys.exit(1)

finally:
    if connection:
        connection.close()
        print("\n数据库连接已关闭。")