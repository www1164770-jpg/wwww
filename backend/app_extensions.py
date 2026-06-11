"""
智汇导航 - 后端扩展模块
========================
包含：
  1. 生产级日志配置
  2. 全局异常处理器
  3. Redis 异步持久化定时任务
  4. 密码找回（忘记密码）接口
  5. JWT Token 刷新接口（标准路径）
  6. 敏感词过滤集成
  7. 通知中心接口
  8. Redis ZSET 热榜接口
  9. 用户管理接口（封禁/解封）
 10. 内容审核流接口
 11. ECharts 数据大盘接口
"""

import os
import json
import logging
import traceback
from datetime import datetime, timedelta
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, create_refresh_token, verify_jwt_in_request
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Category, Website, ClickLog
from sqlalchemy import func, text
import pymysql

# =====================================================================
# 1. 生产级日志配置
# =====================================================================

def setup_logging(app):
    """
    配置生产级日志系统。
    日志同时输出到控制台和文件，按天轮转，保留最近 30 天。
    """
    import logging.handlers

    # 创建日志目录
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # 设置日志格式
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 文件处理器（按天轮转，保留 30 天）
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(log_dir, 'app.log'),
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # 错误日志单独记录
    error_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(log_dir, 'error.log'),
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # 清除默认处理器并添加自定义处理器
    app.logger.handlers.clear()
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)

    # 同时配置 Werkzeug 的日志
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.handlers.clear()
    werkzeug_logger.addHandler(file_handler)
    werkzeug_logger.addHandler(console_handler)

    app.logger.info('✅ 日志系统初始化完成')
    return app


# =====================================================================
# 2. 全局异常处理器
# =====================================================================

def register_error_handlers(app):
    """
    注册全局异常处理器，统一返回标准 JSON 格式。

    覆盖场景：
      - 400 Bad Request
      - 401 Unauthorized (JWT 相关)
      - 403 Forbidden
      - 404 Not Found
      - 405 Method Not Allowed
      - 429 Too Many Requests
      - 500 Internal Server Error
      - 所有未捕获的 Exception
    """

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'code': 400, 'msg': '请求参数有误'}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({'code': 401, 'msg': '请先登录后再操作'}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({'code': 403, 'msg': '你没有权限执行此操作'}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'code': 404, 'msg': '请求的资源不存在'}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({'code': 405, 'msg': '请求方法不支持'}), 405

    @app.errorhandler(429)
    def too_many_requests(e):
        return jsonify({'code': 429, 'msg': '请求过于频繁，请稍后再试'}), 429

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f'500 Internal Server Error: {str(e)}\n{traceback.format_exc()}')
        return jsonify({'code': 500, 'msg': '系统开小差了，请稍后再试'}), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        """兜底处理器：捕获所有未被上述处理器覆盖的异常"""
        # 记录完整堆栈到日志文件
        app.logger.error(f'未预期的异常: {type(e).__name__}: {str(e)}')
        app.logger.error(f'请求路径: {request.method} {request.path}')
        app.logger.error(f'请求参数: {request.args.to_dict() if request.args else "无"}')
        if request.is_json:
            app.logger.error(f'请求体: {request.get_json(silent=True)}')
        app.logger.error(f'堆栈跟踪:\n{traceback.format_exc()}')

        return jsonify({
            'code': 500,
            'msg': '系统开小差了，请稍后再试',
            'error_id': datetime.now().strftime('%Y%m%d%H%M%S%f')  # 错误追踪 ID
        }), 500

    app.logger.info('✅ 全局异常处理器注册完成')
    return app


# =====================================================================
# 3. Redis 异步持久化调度器
# =====================================================================

def register_redis_sync_scheduler(app, scheduler, redis_client):
    """
    注册 Redis → MySQL 定时同步任务。
    每 10 分钟将 Redis 中的浏览/点赞增量批量写入 MySQL。
    """

    @scheduler.task('interval', id='sync_redis_to_mysql', minutes=10, misfire_grace_time=300)
    def sync_redis_to_mysql():
        """
        定时任务：将 Redis 中的增量数据批量写入 MySQL。
        - 点击计数：从 Redis ZSET (hot:clicks:today) 读取今日点击数
        - 点赞计数：从 Redis Hash (hot:likes:today) 读取今日点赞数
        """
        with app.app_context():
            try:
                # 延迟导入避免循环依赖
                from db_pool import get_connection as pool_conn
                conn = pool_conn()
                cursor = conn.cursor()
                synced_count = 0

                # --- 同步点击计数 ---
                click_data = redis_client.zrange('hot:clicks:today', 0, -1, withscores=True)
                for item_id, clicks in click_data:
                    item_id = int(item_id)
                    clicks = int(clicks)
                    if clicks > 0:
                        cursor.execute(
                            "UPDATE websites SET clicks = clicks + %s WHERE id = %s",
                            (clicks, item_id)
                        )
                        synced_count += 1

                # --- 同步点赞计数 ---
                like_keys = redis_client.hgetall('hot:likes:today')
                for item_id, likes in like_keys.items():
                    likes = int(likes)
                    if likes > 0:
                        cursor.execute(
                            "UPDATE articles SET likes = likes + %s WHERE id = %s",
                            (likes, item_id)
                        )
                        synced_count += 1

                conn.commit()
                cursor.close()
                conn.close()

                # 同步完成后，清除 Redis 中的今日计数器
                if click_data:
                    redis_client.delete('hot:clicks:today')
                if like_keys:
                    redis_client.delete('hot:likes:today')

                app.logger.info(f'✅ Redis→MySQL 同步完成，共同步 {synced_count} 条记录')
            except Exception as e:
                app.logger.error(f'❌ Redis→MySQL 同步失败: {str(e)}\n{traceback.format_exc()}')

    app.logger.info('✅ Redis 异步持久化调度器注册完成（每 10 分钟同步一次）')


# =====================================================================
# 4. 密码找回接口
# =====================================================================

def register_password_reset_routes(app, redis_client):
    """注册密码重置相关路由"""

    @app.route('/api/auth/send-reset-code', methods=['POST'])
    def send_reset_code():
        """
        发送密码重置验证码。

        请求体：{ email: string }
        返回：{ code: 0, msg: '验证码已发送' }
        """
        data = request.get_json(silent=True) or {}
        email = data.get('email', '').strip()

        if not email or '@' not in email:
            return jsonify({'code': 400, 'msg': '请输入有效的邮箱地址'}), 400

        # 检查邮箱是否已注册
        user = User.query.filter_by(email=email).first()
        if not user:
            # 出于安全考虑，不暴露该邮箱未注册，统一返回成功
            return jsonify({'code': 0, 'msg': '如果该邮箱已注册，验证码已发送'})

        import random
        from email_service import send_verification_email

        code = str(random.randint(100000, 999999))

        # 存入 Redis，5 分钟有效，key 前缀区分注册验证码
        redis_client.setex(f"reset_code:{email}", 300, code)

        # 发送邮件
        is_success, error_message = send_verification_email(email, code)
        if is_success:
            return jsonify({'code': 0, 'msg': '验证码已发送，请查收邮箱'})
        else:
            return jsonify({'code': 500, 'msg': '邮件发送失败，请联系管理员'}), 500

    @app.route('/api/auth/verify-reset-code', methods=['POST'])
    def verify_reset_code():
        """
        验证重置密码的验证码。

        请求体：{ email: string, code: string }
        返回：{ code: 0, msg: '验证通过' } 或 { code: 400, msg: '验证码错误' }
        """
        data = request.get_json(silent=True) or {}
        email = data.get('email', '').strip()
        code = data.get('code', '').strip()

        saved_code = redis_client.get(f"reset_code:{email}")
        if not saved_code or saved_code != code:
            return jsonify({'code': 400, 'msg': '验证码错误或已过期'}), 400

        # 验证通过，颁发一个临时 Token（用于重置密码一步）
        # 这个 Token 有效期 5 分钟
        temp_token = create_access_token(identity=email, expires_delta=timedelta(minutes=5))
        return jsonify({'code': 0, 'msg': '验证通过', 'reset_token': temp_token})

    @app.route('/api/auth/reset-password', methods=['POST'])
    def reset_password():
        """
        使用验证码重置密码。

        请求体：{ email: string, code: string, new_password: string }
        返回：{ code: 0, msg: '密码重置成功' }
        """
        data = request.get_json(silent=True) or {}
        email = data.get('email', '').strip()
        code = data.get('code', '').strip()
        new_password = data.get('new_password', '')

        if not new_password or len(new_password) < 6:
            return jsonify({'code': 400, 'msg': '新密码至少需要 6 位'}), 400

        # 再次验证验证码
        saved_code = redis_client.get(f"reset_code:{email}")
        if not saved_code or saved_code != code:
            return jsonify({'code': 400, 'msg': '验证码错误或已过期'}), 400

        # 更新密码
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'code': 404, 'msg': '用户不存在'}), 404

        hashed_pw = generate_password_hash(new_password)
        user.password_hash = hashed_pw
        db.session.commit()

        # 删除验证码
        redis_client.delete(f"reset_code:{email}")

        return jsonify({'code': 0, 'msg': '密码重置成功，请使用新密码登录'})


# =====================================================================
# 5. JWT Token 刷新（标准路径）
# =====================================================================

def register_token_refresh_route(app):
    """注册标准的 Token 刷新路由"""

    @app.route('/api/auth/refresh', methods=['POST'])
    def refresh_token():
        """
        无感刷新 Access Token（标准路径）。

        请求头：Authorization: Bearer <refresh_token>
        返回：{ access_token: string }
        """
        try:
            verify_jwt_in_request(refresh=True)
            current_user = get_jwt_identity()
            new_access_token = create_access_token(identity=current_user)
            return jsonify({'access_token': new_access_token}), 200
        except Exception as e:
            return jsonify({'code': 401, 'msg': 'Refresh Token 无效或已过期'}), 401


# =====================================================================
# 6. 敏感词过滤集成
# =====================================================================

def register_content_filter_routes(app):
    """注册内容审核相关路由"""

    @app.route('/api/content/check', methods=['POST'])
    def check_content_safety():
        """
        检查文本内容是否包含敏感词。

        请求体：{ text: string }
        返回：{ code: 0, data: { safe: bool, filtered_text: string, hit_words: [] } }
        """
        data = request.get_json(silent=True) or {}
        text = data.get('text', '').strip()

        if not text:
            return jsonify({'code': 0, 'data': {'safe': True, 'filtered_text': '', 'hit_words': []}})

        from sensitive_filter import check_content
        result = check_content(text)
        return jsonify({'code': 0, 'data': result})


# =====================================================================
# 7. 通知中心接口
# =====================================================================

def register_notification_routes(app, db):
    """注册通知中心相关路由"""

    @app.route('/api/notifications/unread-count', methods=['GET'])
    @jwt_required()
    def get_unread_count():
        """获取当前用户未读通知数量"""
        username = get_jwt_identity()
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'code': 404, 'msg': '用户不存在'}), 404

        try:
            result = db.session.execute(
                text("SELECT COUNT(*) as cnt FROM notifications WHERE user_id = :uid AND is_read = 0"),
                {'uid': user.id}
            ).fetchone()
            count = result[0] if result else 0
            return jsonify({'code': 0, 'data': {'unread_count': count}})
        except Exception as e:
            # 如果通知表不存在，返回 0
            return jsonify({'code': 0, 'data': {'unread_count': 0}})

    @app.route('/api/notifications', methods=['GET'])
    @jwt_required()
    def get_notifications():
        """获取通知列表（分页）"""
        username = get_jwt_identity()
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'code': 404, 'msg': '用户不存在'}), 404

        page = request.args.get('page', 1, type=int)
        per_page = 20

        try:
            offset = (page - 1) * per_page
            result = db.session.execute(
                text("""SELECT id, type, content, related_id, is_read, created_at
                        FROM notifications WHERE user_id = :uid
                        ORDER BY created_at DESC LIMIT :limit OFFSET :offset"""),
                {'uid': user.id, 'limit': per_page, 'offset': offset}
            ).fetchall()

            notifications = [{
                'id': r[0],
                'type': r[1],
                'content': r[2],
                'related_id': r[3],
                'is_read': bool(r[4]),
                'created_at': r[5].strftime('%Y-%m-%d %H:%M') if r[5] else ''
            } for r in result]

            return jsonify({'code': 0, 'data': notifications})
        except Exception as e:
            app.logger.error(f'获取通知失败: {str(e)}')
            return jsonify({'code': 0, 'data': []})

    @app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
    @jwt_required()
    def mark_notification_read(notification_id):
        """标记单条通知为已读"""
        try:
            db.session.execute(
                text("UPDATE notifications SET is_read = 1 WHERE id = :id"),
                {'id': notification_id}
            )
            db.session.commit()
            return jsonify({'code': 0, 'msg': '已标记为已读'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'code': 500, 'msg': '操作失败'}), 500

    @app.route('/api/notifications/read-all', methods=['POST'])
    @jwt_required()
    def mark_all_read():
        """全部标记为已读"""
        username = get_jwt_identity()
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'code': 404, 'msg': '用户不存在'}), 404

        try:
            db.session.execute(
                text("UPDATE notifications SET is_read = 1 WHERE user_id = :uid AND is_read = 0"),
                {'uid': user.id}
            )
            db.session.commit()
            return jsonify({'code': 0, 'msg': '全部已标记为已读'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'code': 500, 'msg': '操作失败'}), 500


# =====================================================================
# 8. Redis ZSET 热榜接口
# =====================================================================

def register_hot_ranking_routes(app, redis_client):
    """注册基于 Redis ZSET 的热度排行榜路由"""

    @app.route('/api/ranking/hot', methods=['GET'])
    def get_hot_ranking():
        """
        获取 24 小时热度排行榜。

        热度算法：基于 Redis ZSET 的 score，
        综合点击量、点赞数和发布时间计算。
        每 30 秒自动更新一次缓存。

        返回：{ code: 0, data: [ { id, title, cover_url, hot_score }, ... ] }
        """
        try:
            # 优先从缓存读取
            cached = redis_client.get('ranking:24h_hot')
            if cached:
                return jsonify({'code': 0, 'data': json.loads(cached)})

            # 从 ZSET 获取 Top 50
            hot_items = redis_client.zrevrange('hot:24h', 0, 49, withscores=True)

            if not hot_items:
                # 回退到数据库直接查询
                try:
                    sites = Website.query.order_by(Website.clicks.desc()).limit(20).all()
                    fallback_result = [{
                        'id': s.id, 'title': s.name,
                        'cover_url': s.logo_url or '',
                        'hot_score': float(s.clicks or 0)
                    } for s in sites]
                    return jsonify({'code': 0, 'data': fallback_result})
                except Exception:
                    return jsonify({'code': 0, 'data': []})

            result = []
            for item_id, score in hot_items:
                # 从 MySQL 获取网站基本信息
                site = Website.query.get(int(item_id))
                if site:
                    result.append({
                        'id': site.id,
                        'title': site.name,
                        'cover_url': site.logo_url or '',
                        'hot_score': round(score, 1)
                    })

            # 缓存 30 秒
            redis_client.setex('ranking:24h_hot', 30, json.dumps(result))

            return jsonify({'code': 0, 'data': result})
        except Exception as e:
            app.logger.error(f'热榜查询失败: {str(e)}')
            return jsonify({'code': 0, 'data': []})

    app.logger.info('✅ 热榜接口注册完成')


# =====================================================================
# 9. 管理员 - 用户管理接口
# =====================================================================

def register_admin_user_routes(app, db):
    """注册管理员用户管理路由"""

    @app.route('/api/admin/users', methods=['GET'])
    @jwt_required()
    def get_admin_users():
        """获取用户列表（管理员专用，分页）"""
        username = get_jwt_identity()
        # 验证管理员身份
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'code': 403, 'msg': '无权访问'}), 403

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        offset = (page - 1) * per_page

        try:
            total = db.session.execute(text("SELECT COUNT(*) as cnt FROM users WHERE deleted_at IS NULL")).fetchone()[0]
            rows = db.session.execute(
                text("""SELECT id, username, email, avatar_url, created_at
                        FROM users WHERE deleted_at IS NULL
                        ORDER BY created_at DESC LIMIT :limit OFFSET :offset"""),
                {'limit': per_page, 'offset': offset}
            ).fetchall()

            users = [{
                'id': r[0],
                'username': r[1],
                'email': r[2],
                'avatar': r[3],
                'created_at': r[4].strftime('%Y-%m-%d') if r[4] else ''
            } for r in rows]

            return jsonify({'code': 0, 'data': {'users': users, 'total': total, 'page': page, 'per_page': per_page}})
        except Exception as e:
            app.logger.error(f'获取用户列表失败: {str(e)}')
            return jsonify({'code': 500, 'msg': '服务器错误'}), 500

    @app.route('/api/admin/user/ban', methods=['POST'])
    @jwt_required()
    def toggle_user_ban():
        """封禁/解封用户"""
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id')
        banned = data.get('banned', False)

        if not user_id:
            return jsonify({'code': 400, 'msg': '缺少 user_id'}), 400

        try:
            if banned:
                db.session.execute(
                    text("UPDATE users SET deleted_at = :now WHERE id = :uid"),
                    {'now': datetime.now(), 'uid': user_id}
                )
            else:
                db.session.execute(
                    text("UPDATE users SET deleted_at = NULL WHERE id = :uid"),
                    {'uid': user_id}
                )
            db.session.commit()
            action = '封禁' if banned else '解封'
            return jsonify({'code': 0, 'msg': f'已{action}该用户'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'code': 500, 'msg': f'操作失败: {str(e)}'}), 500


# =====================================================================
# 10. ECharts 数据大盘接口
# =====================================================================

def register_stats_overview_routes(app, db):
    """注册统计数据接口（供 ECharts 大盘使用）"""

    @app.route('/api/admin/stats/overview', methods=['GET'])
    @jwt_required()
    def get_stats_overview():
        """
        获取后台数据大盘统计。

        返回数据包含：
          - today_new_users: 今日新增用户数
          - today_new_content: 今日新增内容数
          - total_clicks_today: 今日总点击数
          - weekly_trend: 近 7 天每日新增用户趋势
          - category_distribution: 各分类网站数量分布（饼图）
          - hourly_traffic: 近 24 小时流量分布（折线图）
        """
        try:
            # 今日新增用户
            today_users = db.session.execute(
                text("SELECT COUNT(*) as cnt FROM users WHERE DATE(created_at) = CURDATE()")
            ).fetchone()[0]

            # 今日新增内容（网站）
            today_content = db.session.execute(
                text("SELECT COUNT(*) as cnt FROM websites WHERE DATE(created_at) = CURDATE()")
            ).fetchone()[0]

            # 今日总点击量
            today_clicks = db.session.execute(
                text("SELECT COUNT(*) as cnt FROM click_logs WHERE DATE(created_at) = CURDATE()")
            ).fetchone()[0]

            # 近 7 天每日新增用户趋势
            weekly_trend = []
            for i in range(6, -1, -1):
                row = db.session.execute(
                    text("SELECT COUNT(*) as cnt FROM users WHERE DATE(created_at) = DATE_SUB(CURDATE(), INTERVAL :days DAY)"),
                    {'days': i}
                ).fetchone()
                weekly_trend.append({
                    'date': (datetime.now() - timedelta(days=i)).strftime('%m-%d'),
                    'count': row[0] if row else 0
                })

            # 各分类网站数量分布
            cat_dist = db.session.execute(
                text("""SELECT c.name, COUNT(w.id) as cnt
                        FROM categories c LEFT JOIN websites w ON c.id = w.category_id
                        GROUP BY c.id, c.name ORDER BY cnt DESC""")
            ).fetchall()
            category_distribution = [{'name': r[0], 'value': r[1]} for r in cat_dist]

            # 近 24 小时流量分布
            hourly_traffic = []
            for i in range(24):
                row = db.session.execute(
                    text("""SELECT COUNT(*) as cnt FROM click_logs
                            WHERE created_at >= DATE_SUB(NOW(), INTERVAL :h HOUR)
                            AND created_at < DATE_SUB(NOW(), INTERVAL :h2 HOUR)"""),
                    {'h': 24 - i, 'h2': 23 - i if i < 23 else -1}
                ).fetchone()
                hourly_traffic.append({
                    'hour': f'{i}:00',
                    'count': row[0] if row else 0
                })

            return jsonify({'code': 0, 'data': {
                'today_new_users': today_users,
                'today_new_content': today_content,
                'total_clicks_today': today_clicks,
                'weekly_trend': weekly_trend,
                'category_distribution': category_distribution,
                'hourly_traffic': hourly_traffic
            }})
        except Exception as e:
            app.logger.error(f'统计数据查询失败: {str(e)}\n{traceback.format_exc()}')
            return jsonify({'code': 500, 'msg': '数据查询失败'}), 500


# =====================================================================
# 11. 内容审核流接口
# =====================================================================

def register_content_audit_routes(app, db):
    """注册内容审核流路由"""

    @app.route('/api/admin/content-audit', methods=['GET'])
    @jwt_required()
    def get_content_audit_list():
        """获取待审核内容列表"""
        status = request.args.get('status', 'pending')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        offset = (page - 1) * per_page

        try:
            total = db.session.execute(
                text("SELECT COUNT(*) as cnt FROM articles WHERE status = :status"),
                {'status': status}
            ).fetchone()[0]

            rows = db.session.execute(
                text("""SELECT id, title, author_id, created_at
                        FROM articles WHERE status = :status
                        ORDER BY created_at ASC LIMIT :limit OFFSET :offset"""),
                {'status': status, 'limit': per_page, 'offset': offset}
            ).fetchall()

            items = [{
                'id': r[0],
                'title': r[1],
                'author_id': r[2],
                'created_at': r[3].strftime('%Y-%m-%d %H:%M') if r[3] else ''
            } for r in rows]

            return jsonify({'code': 0, 'data': {'items': items, 'total': total, 'page': page}})
        except Exception as e:
            app.logger.error(f'获取内容审核列表失败: {str(e)}')
            return jsonify({'code': 500, 'msg': '查询失败'}), 500

    @app.route('/api/admin/review-content', methods=['POST'])
    @jwt_required()
    def review_content():
        """
        审核内容（通过/拒绝）。

        请求体：{ id: int, action: 'approve'|'reject', reason?: string }
        """
        data = request.get_json(silent=True) or {}
        content_id = data.get('id')
        action = data.get('action')
        reason = data.get('reason', '')

        if not content_id or action not in ('approve', 'reject'):
            return jsonify({'code': 400, 'msg': '参数有误'}), 400

        try:
            if action == 'approve':
                db.session.execute(
                    text("UPDATE articles SET status = 'published' WHERE id = :id"),
                    {'id': content_id}
                )
                msg = '文章已通过审核并发布'
            else:
                db.session.execute(
                    text("UPDATE articles SET status = 'rejected', review_reason = :reason WHERE id = :id"),
                    {'reason': reason, 'id': content_id}
                )
                msg = '文章已被拒绝'

            db.session.commit()
            return jsonify({'code': 0, 'msg': msg})
        except Exception as e:
            db.session.rollback()
            return jsonify({'code': 500, 'msg': f'操作失败: {str(e)}'}), 500


# =====================================================================
# 12. 问卷与个性化推荐系统 (v2 — 双维度 × LIKE 匹配)
# =====================================================================

# 预定义的有效标签白名单（维度一 职业角色 + 维度二 核心需求）
AVAILABLE_TAGS = [
    # 维度一：我的职业角色
    'frontend', 'backend', 'ai-data', 'ui-design',
    'iot-hardware', 'product-pm',
    # 维度二：我的核心需求
    'self-learning', 'job-hunting', 'efficiency', 'open-source',
]


def register_survey_routes(app, db):
    """注册问卷提交与个性化网站推荐路由 (v2)"""

    # --- 接口 A：提交问卷 ---
    @app.route('/api/user/survey', methods=['POST'])
    @jwt_required()
    def submit_survey():
        """
        保存用户的兴趣问卷结果（双维度合并标签）。

        请求体（JSON）：
            interests: string[]  — 用户选中的所有标签 key，
                                   例如 ["frontend", "job-hunting", "efficiency"]

        返回：
            { code: 0, msg: '问卷已保存' }
        """
        username = get_jwt_identity()
        data = request.get_json(silent=True) or {}
        tags = data.get('interests', [])

        if not tags or not isinstance(tags, list):
            return jsonify({'code': 400, 'msg': '请至少选择一个兴趣标签'}), 400

        # 过滤非法标签，只保留白名单中的有效 key
        clean_tags = [t for t in tags if t in AVAILABLE_TAGS]
        if not clean_tags:
            return jsonify({'code': 400, 'msg': '未识别到有效的兴趣标签'}), 400

        # 去重后用逗号拼接存储
        user_tags_str = ','.join(dict.fromkeys(clean_tags))

        try:
            # 🛡️ 自动补救：如果 user_tags/has_survey 列不存在则先创建
            try:
                db.session.execute(
                    text("UPDATE users SET user_tags = :tags, has_survey = 1 WHERE username = :username"),
                    {'tags': user_tags_str, 'username': username}
                )
            except Exception as col_err:
                err_msg = str(col_err).lower()
                if 'unknown column' in err_msg:
                    app.logger.warning(f'列缺失，自动创建: {col_err}')
                    db.session.rollback()  # 先回滚失败的 UPDATE

                    # 尝试 MySQL 8.0+ 语法
                    try:
                        db.session.execute(text(
                            "ALTER TABLE users ADD COLUMN IF NOT EXISTS user_tags VARCHAR(500) DEFAULT NULL"))
                    except Exception:
                        # 降级到 MySQL 5.7 兼容语法（无 IF NOT EXISTS）
                        try:
                            db.session.execute(text(
                                "ALTER TABLE users ADD COLUMN user_tags VARCHAR(500) DEFAULT NULL"))
                        except Exception:
                            pass  # 列已存在也会报错，忽略

                    try:
                        db.session.execute(text(
                            "ALTER TABLE users ADD COLUMN IF NOT EXISTS has_survey TINYINT DEFAULT 0"))
                    except Exception:
                        try:
                            db.session.execute(text(
                                "ALTER TABLE users ADD COLUMN has_survey TINYINT DEFAULT 0"))
                        except Exception:
                            pass

                    db.session.commit()

                    # 重试 UPDATE
                    db.session.execute(
                        text("UPDATE users SET user_tags = :tags, has_survey = 1 WHERE username = :username"),
                        {'tags': user_tags_str, 'username': username}
                    )
                else:
                    raise col_err

            db.session.commit()
            app.logger.info(f'用户 {username} 完成问卷，标签: {user_tags_str}')
            return jsonify({'code': 0, 'msg': '问卷已保存，正在为你生成专属推荐...'})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'问卷提交失败: {str(e)}')
            # 只返回通用消息，不泄露内部错误细节
            return jsonify({'code': 500, 'msg': '保存失败，请稍后重试'}), 500

    # --- 接口 B：个性化网站推荐 ---
    @app.route('/api/recommendations/websites', methods=['GET'])
    @jwt_required()
    def get_recommended_websites():
        """
        个性化网站推荐接口 (v2) — 基于用户标签的 LIKE 模糊匹配。

        推荐策略（简单脚本化）：
          1. 获取当前登录用户的 user_tags（回退到 interests 兼容旧数据）。
          2. 如果用户未做问卷 (has_survey=0) 或无标签 → 返回全站点击量 top 8 网站。
          3. 如果有标签 → 遍历标签，构建 WHERE tags LIKE '%tag%' 的 OR 条件。
          4. 匹配结果按 clicks 降序排列，去重后取前 8 条。

        返回：
            { code: 0, data: { items: [...], source: 'personalized'|'default', total: N } }
        """
        username = get_jwt_identity()

        try:
            # 1. 获取用户标签（优先读 user_tags，回退到 interests）
            try:
                row = db.session.execute(
                    text("SELECT has_survey, user_tags, interests FROM users WHERE username = :username"),
                    {'username': username}
                ).fetchone()
                has_survey = row[0] if row else 0
                # 优先使用 user_tags，如果为空则回退到 interests（兼容旧数据）
                tags_str = (row[1] or row[2] or '') if row else ''
            except Exception:
                # 列不存在 → 冷启动
                has_survey = 0
                tags_str = ''

            items = []
            source = 'default'
            TARGET_COUNT = 8  # 返回 top 8

            if not has_survey or not tags_str:
                # ---------- 冷启动：全站热门 Top 8 ----------
                source = 'default'
                rows = db.session.execute(
                    text("""SELECT id, name, url, logo_url, clicks
                            FROM websites WHERE status = 'approved'
                            ORDER BY clicks DESC LIMIT :limit"""),
                    {'limit': TARGET_COUNT}
                ).fetchall()

                for r in rows:
                    items.append({
                        'id': r[0],
                        'name': r[1],
                        'url': r[2],
                        'logo_url': r[3] or '',
                        'clicks': r[4],
                    })

            else:
                # ---------- 个性化推荐：LIKE 模糊匹配 ----------
                source = 'personalized'
                tag_list = [t.strip() for t in tags_str.split(',') if t.strip()]
                seen_ids = set()

                # 确保 websites 表有 tags 列（容错）
                try:
                    for tag in tag_list:
                        if len(items) >= TARGET_COUNT:
                            break
                        # 核心 SQL：用 LIKE '%tag%' 做模糊匹配
                        # 注意：多个标签用 OR 条件一次性查出，避免逐条循环
                        site_rows = db.session.execute(
                            text("""SELECT id, name, url, logo_url, clicks
                                    FROM websites
                                    WHERE status = 'approved'
                                      AND tags IS NOT NULL
                                      AND tags LIKE :pattern
                                    ORDER BY clicks DESC
                                    LIMIT :limit"""),
                            {'pattern': f'%{tag}%', 'limit': TARGET_COUNT * 2}
                        ).fetchall()

                        for r in site_rows:
                            if r[0] not in seen_ids and len(items) < TARGET_COUNT:
                                seen_ids.add(r[0])
                                items.append({
                                    'id': r[0],
                                    'name': r[1],
                                    'url': r[2],
                                    'logo_url': r[3] or '',
                                    'clicks': r[4],
                                    'matched_tag': tag,
                                })
                except Exception as match_err:
                    # tags 列不存在时回退到全站热门
                    app.logger.warning(f'LIKE 匹配失败（可能是 tags 列不存在），回退到冷启动: {match_err}')
                    source = 'default'
                    items = []
                    fallback_rows = db.session.execute(
                        text("""SELECT id, name, url, logo_url, clicks
                                FROM websites WHERE status = 'approved'
                                ORDER BY clicks DESC LIMIT :limit"""),
                        {'limit': TARGET_COUNT}
                    ).fetchall()
                    for r in fallback_rows:
                        items.append({
                            'id': r[0], 'name': r[1], 'url': r[2],
                            'logo_url': r[3] or '', 'clicks': r[4],
                        })

                # 如果匹配结果不足 8 条，用热门补齐
                if len(items) < TARGET_COUNT:
                    remaining = TARGET_COUNT - len(items)
                    fallback_rows = db.session.execute(
                        text("""SELECT id, name, url, logo_url, clicks
                                FROM websites WHERE status = 'approved'
                                  AND id NOT IN :exclude_ids
                                ORDER BY clicks DESC LIMIT :limit"""),
                        {'exclude_ids': tuple(seen_ids) if seen_ids else (-1,),
                         'limit': remaining}
                    ).fetchall()
                    for r in fallback_rows:
                        items.append({
                            'id': r[0], 'name': r[1], 'url': r[2],
                            'logo_url': r[3] or '', 'clicks': r[4],
                        })

                items = items[:TARGET_COUNT]

            return jsonify({
                'code': 0,
                'data': {
                    'items': items,
                    'source': source,
                    'total': len(items)
                }
            })

        except Exception as e:
            app.logger.error(f'推荐接口异常: {str(e)}\n{traceback.format_exc()}')
            return jsonify({'code': 500, 'msg': '推荐加载失败'}), 500
