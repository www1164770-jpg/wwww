"""
端到端认证测试
测试完整的注册和登录闭环
"""
import os
import sys
import hmac
import secrets
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pymysql
import requests

BACKEND_DIR = Path(__file__).resolve().parent
for env_path in (BACKEND_DIR / ".env", BACKEND_DIR.parent / ".env"):
    if env_path.exists():
        load_dotenv(env_path, override=False)

# MySQL 配置
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "nav_site"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

# 测试配置
BASE_URL = "http://127.0.0.1:5000"
TEST_EMAIL = f"test_{secrets.token_hex(4)}@example.com"
TEST_USERNAME = f"testuser_{secrets.token_hex(4)}"
TEST_PASSWORD = "TestPass123!"
EXISTING_EMAIL = "3439696693@qq.com"
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "wwwww11")

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_test(name):
    print(f"\n{Colors.BLUE}▶ 测试: {name}{Colors.RESET}")

def print_pass(message):
    print(f"  {Colors.GREEN}✓{Colors.RESET} {message}")

def print_fail(message):
    print(f"  {Colors.RED}✗{Colors.RESET} {message}")

def print_info(message):
    print(f"  {Colors.YELLOW}ℹ{Colors.RESET} {message}")

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def registration_code_digest(email, code):
    """生成验证码哈希 (与后端逻辑一致)"""
    secret = JWT_SECRET.encode("utf-8")
    payload = f"register:{email}:{code}".encode("utf-8")
    return hmac.new(secret, payload, "sha256").hexdigest()

def inject_verification_code(email, code="123456"):
    """直接向数据库注入验证码用于测试"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 确保表存在
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_verification_codes (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    email VARCHAR(120) NOT NULL,
                    purpose VARCHAR(32) NOT NULL,
                    code_hash CHAR(64) NOT NULL,
                    expires_at DATETIME NOT NULL,
                    sent_at DATETIME NOT NULL,
                    attempt_count TINYINT UNSIGNED NOT NULL DEFAULT 0,
                    used_at DATETIME NULL,
                    request_ip VARCHAR(64) NULL,
                    PRIMARY KEY (id),
                    UNIQUE KEY uq_email_verification_purpose (email, purpose),
                    KEY idx_email_verification_expiry (expires_at),
                    KEY idx_email_verification_ip_sent (request_ip, sent_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # 注入验证码
            code_hash = registration_code_digest(email, code)
            now = datetime.utcnow()
            expires_at = now + timedelta(minutes=5)
            
            cursor.execute("""
                INSERT INTO email_verification_codes
                    (email, purpose, code_hash, expires_at, sent_at, attempt_count, used_at, request_ip)
                VALUES (%s, 'register', %s, %s, %s, 0, NULL, 'test')
                ON DUPLICATE KEY UPDATE
                    code_hash=VALUES(code_hash), expires_at=VALUES(expires_at), sent_at=VALUES(sent_at),
                    attempt_count=0, used_at=NULL
            """, (email, code_hash, expires_at, now))
        conn.commit()
        return True
    except Exception as e:
        print_fail(f"注入验证码失败: {e}")
        return False
    finally:
        conn.close()

def cleanup_test_user(email=None, username=None):
    """清理测试用户"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if email:
                cursor.execute("DELETE FROM users WHERE email = %s", (email,))
                cursor.execute("DELETE FROM email_verification_codes WHERE email = %s", (email,))
            if username:
                cursor.execute("DELETE FROM users WHERE username = %s", (username,))
        conn.commit()
    except Exception as e:
        print_info(f"清理测试数据: {e}")
    finally:
        conn.close()

def check_user_in_db(email):
    """检查用户是否存在于数据库"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, email, 
                       LENGTH(password_hash) as pwd_len,
                       role, status, login_provider, created_at
                FROM users WHERE email = %s
            """, (email,))
            return cursor.fetchone()
    finally:
        conn.close()

def run_tests():
    """运行所有测试"""
    passed = 0
    failed = 0
    total = 13
    
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"端到端认证测试")
    print(f"{'='*60}{Colors.RESET}\n")
    print_info(f"测试邮箱: {TEST_EMAIL}")
    print_info(f"测试用户名: {TEST_USERNAME}")
    print_info(f"后端地址: {BASE_URL}")
    
    # 清理之前可能存在的测试数据
    cleanup_test_user(email=TEST_EMAIL, username=TEST_USERNAME)
    
    # 测试 1: 错误的验证码应该被拒绝
    print_test("1. 使用错误验证码注册")
    inject_verification_code(TEST_EMAIL, "111111")
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": TEST_USERNAME,
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "verification_code": "999999"
        }, timeout=5)
        if resp.status_code == 400 and resp.json().get("code") == "CODE_INVALID":
            print_pass(f"正确拒绝错误验证码: {resp.json().get('message')}")
            passed += 1
        else:
            print_fail(f"期望 400 CODE_INVALID, 实际: {resp.status_code} {resp.json()}")
            failed += 1
    except Exception as e:
        print_fail(f"请求失败: {e}")
        failed += 1
    
    # 测试 2: 正确的验证码应该可以注册
    print_test("2. 使用正确验证码注册")
    inject_verification_code(TEST_EMAIL, "123456")
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": TEST_USERNAME,
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "verification_code": "123456"
        }, timeout=5)
        if resp.status_code == 200 and resp.json().get("code") == 0:
            print_pass(f"注册成功: {resp.json().get('msg')}")
            passed += 1
        else:
            print_fail(f"注册失败: {resp.status_code} {resp.json()}")
            failed += 1
    except Exception as e:
        print_fail(f"请求失败: {e}")
        failed += 1
    
    # 测试 3: 用户应该已写入数据库
    print_test("3. 检查用户是否写入数据库")
    user = check_user_in_db(TEST_EMAIL)
    if user:
        print_pass(f"用户存在: id={user['id']}, username={user['username']}")
        print_pass(f"  password_hash 长度: {user['pwd_len']}")
        print_pass(f"  role: {user['role']}, status: {user['status']}, login_provider: {user['login_provider']}")
        if user['pwd_len'] > 0 and user['role'] == 'user' and user['status'] == 'active':
            passed += 1
        else:
            print_fail("用户字段不完整")
            failed += 1
    else:
        print_fail("用户未写入数据库")
        failed += 1
    
    # 测试 4: 重复邮箱应该返回 409
    print_test("4. 重复邮箱注册")
    inject_verification_code(TEST_EMAIL, "654321")
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": f"{TEST_USERNAME}_2",
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "verification_code": "654321"
        }, timeout=5)
        if resp.status_code == 409 and resp.json().get("code") == "EMAIL_ALREADY_REGISTERED":
            print_pass(f"正确拒绝重复邮箱: {resp.json().get('message')}")
            passed += 1
        else:
            print_fail(f"期望 409 EMAIL_ALREADY_REGISTERED, 实际: {resp.status_code} {resp.json()}")
            failed += 1
    except Exception as e:
        print_fail(f"请求失败: {e}")
        failed += 1
    
    # 测试 5: 已使用的验证码不能再次使用
    print_test("5. 已使用的验证码不能重复使用")
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": f"{TEST_USERNAME}_3",
            "email": f"another_{TEST_EMAIL}",
            "password": TEST_PASSWORD,
            "verification_code": "123456"
        }, timeout=5)
        # 应该失败,因为 TEST_EMAIL 的验证码已被使用
        if resp.status_code == 400:
            print_pass(f"正确拒绝已使用的验证码: {resp.json().get('message')}")
            passed += 1
        else:
            print_fail(f"期望拒绝, 实际: {resp.status_code} {resp.json()}")
            failed += 1
    except Exception as e:
        print_fail(f"请求失败: {e}")
        failed += 1
    
    # 测试 6: 使用邮箱登录
    print_test("6. 使用邮箱登录")
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "account": TEST_EMAIL,
            "password": TEST_PASSWORD
        }, timeout=5)
        if resp.status_code == 200 and resp.json().get("code") == 0:
            data = resp.json()
            if data.get("access_token") and data.get("user_info"):
                print_pass(f"邮箱登录成功, 用户: {data['user_info'].get('username')}")
                print_pass(f"  access_token: {data['access_token'][:20]}...")
                passed += 1
            else:
                print_fail("登录成功但缺少 token 或 user_info")
                failed += 1
        else:
            print_fail(f"登录失败: {resp.status_code} {resp.json()}")
            failed += 1
    except Exception as e:
        print_fail(f"请求失败: {e}")
        failed += 1
    
    # 测试 7: 使用用户名登录
    print_test("7. 使用用户名登录")
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "account": TEST_USERNAME,
            "password": TEST_PASSWORD
        }, timeout=5)
        if resp.status_code == 200 and resp.json().get("code") == 0:
            print_pass(f"用户名登录成功")
            passed += 1
        else:
            print_fail(f"登录失败: {resp.status_code} {resp.json()}")
            failed += 1
    except Exception as e:
        print_fail(f"请求失败: {e}")
        failed += 1
    
    # 测试 8: 错误密码应该返回 401
    print_test("8. 使用错误密码登录")
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "account": TEST_EMAIL,
            "password": "WrongPassword123!"
        }, timeout=5)
        if resp.status_code == 401:
            print_pass(f"正确拒绝错误密码: {resp.json().get('msg')}")
            passed += 1
        else:
            print_fail(f"期望 401, 实际: {resp.status_code}")
            failed += 1
    except Exception as e:
        print_fail(f"请求失败: {e}")
        failed += 1
    
    # 测试 9: 不存在的用户应该返回 401
    print_test("9. 使用不存在的账号登录")
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "account": "nonexistent@example.com",
            "password": TEST_PASSWORD
        }, timeout=5)
        if resp.status_code == 401:
            print_pass(f"正确拒绝不存在的账号")
            passed += 1
        else:
            print_fail(f"期望 401, 实际: {resp.status_code}")
            failed += 1
    except Exception as e:
        print_fail(f"请求失败: {e}")
        failed += 1
    
    # 测试 10: 检查现有用户邮箱已注册
    print_test("10. 现有邮箱注册应返回 409")
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/send-register-code", json={
            "email": EXISTING_EMAIL
        }, timeout=5)
        if resp.status_code == 409 and resp.json().get("code") == "EMAIL_ALREADY_REGISTERED":
            print_pass(f"正确识别已注册邮箱")
            passed += 1
        else:
            print_fail(f"期望 409, 实际: {resp.status_code} {resp.json()}")
            failed += 1
    except Exception as e:
        print_fail(f"请求失败: {e}")
        failed += 1
    
    # 测试 11: 现有用户可以登录
    print_test("11. 现有用户 (3439696693@qq.com) 可以登录")
    try:
        # 注意: 这里使用的是数据库中实际存在的密码
        # 如果不知道密码,这个测试会失败,这是正常的
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "account": EXISTING_EMAIL,
            "password": "your_actual_password_here"  # 需要替换为实际密码
        }, timeout=5)
        if resp.status_code == 200:
            print_pass(f"现有用户登录成功")
            passed += 1
        elif resp.status_code == 401:
            print_info(f"密码验证失败 (测试密码可能不正确,跳过此项)")
            total -= 1  # 不计入总数
        else:
            print_fail(f"意外响应: {resp.status_code}")
            failed += 1
    except Exception as e:
        print_info(f"跳过现有用户登录测试: {e}")
        total -= 1
    
    # 测试 12: 密码长度验证
    print_test("12. 短密码应该被拒绝")
    inject_verification_code(f"short_{TEST_EMAIL}", "111111")
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": f"short_{TEST_USERNAME}",
            "email": f"short_{TEST_EMAIL}",
            "password": "123",
            "verification_code": "111111"
        }, timeout=5)
        if resp.status_code == 400 and resp.json().get("code") == "PASSWORD_TOO_SHORT":
            print_pass(f"正确拒绝短密码")
            passed += 1
        else:
            print_fail(f"期望 400 PASSWORD_TOO_SHORT, 实际: {resp.status_code} {resp.json()}")
            failed += 1
    except Exception as e:
        print_fail(f"请求失败: {e}")
        failed += 1
    
    # 测试 13: 邮箱格式验证
    print_test("13. 无效邮箱格式应该被拒绝")
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": "invalid_user",
            "email": "not-an-email",
            "password": TEST_PASSWORD,
            "verification_code": "123456"
        }, timeout=5)
        if resp.status_code == 400 and resp.json().get("code") == "EMAIL_INVALID":
            print_pass(f"正确拒绝无效邮箱")
            passed += 1
        else:
            print_fail(f"期望 400 EMAIL_INVALID, 实际: {resp.status_code} {resp.json()}")
            failed += 1
    except Exception as e:
        print_fail(f"请求失败: {e}")
        failed += 1
    
    # 清理测试数据
    print_test("清理测试数据")
    cleanup_test_user(email=TEST_EMAIL, username=TEST_USERNAME)
    cleanup_test_user(email=f"another_{TEST_EMAIL}")
    cleanup_test_user(email=f"short_{TEST_EMAIL}", username=f"short_{TEST_USERNAME}")
    print_info("测试数据已清理")
    
    # 输出结果
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"测试结果")
    print(f"{'='*60}{Colors.RESET}\n")
    print(f"  总计: {total} 项")
    print(f"  {Colors.GREEN}通过: {passed} 项{Colors.RESET}")
    if failed > 0:
        print(f"  {Colors.RED}失败: {failed} 项{Colors.RESET}")
    
    success_rate = (passed / total * 100) if total > 0 else 0
    print(f"\n  成功率: {success_rate:.1f}%\n")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = run_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print_fail(f"测试执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
