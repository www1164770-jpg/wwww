import json
from functools import wraps

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from recommend_service import rank_sites


def register_v1_routes(app, get_db_connection):
    def api_success(data=None, msg="success", status=200):
        return jsonify({"code": 0, "msg": msg, "data": data if data is not None else {}}), status

    def api_error(msg, code=400, status=400, data=None):
        return jsonify({"code": code, "msg": msg, "data": data if data is not None else {}}), status

    def current_user_row():
        username = get_jwt_identity()
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username=%s OR email=%s", (username, username))
                return cursor.fetchone()
        finally:
            conn.close()

    def admin_required(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            user = current_user_row()
            if not user or user.get("role") not in ("admin", "super_admin"):
                return api_error("forbidden", 403, 403)
            return fn(*args, **kwargs)
        return decorator

    def grouped_values(sql, site_ids, key):
        if not site_ids:
            return {}
        placeholders = ",".join(["%s"] * len(site_ids))
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql.format(placeholders=placeholders), site_ids)
                rows = cursor.fetchall()
        except Exception:
            rows = []
        finally:
            conn.close()
        grouped = {}
        for row in rows:
            grouped.setdefault(row["site_id"], []).append(row[key])
        return grouped

    def site_tags(site_ids):
        return grouped_values(
            """
            SELECT st.site_id, t.name
            FROM site_tags st
            JOIN tags t ON t.id = st.tag_id
            WHERE st.site_id IN ({placeholders})
            """,
            site_ids,
            "name",
        )

    def site_occupations(site_ids):
        return grouped_values(
            "SELECT site_id, occupation FROM site_occupations WHERE site_id IN ({placeholders})",
            site_ids,
            "occupation",
        )

    def normalize_site(row, tags=None, occupations=None):
        summary = row.get("summary") or row.get("description") or row.get("desc") or ""
        return {
            "id": row.get("id"),
            "name": row.get("name"),
            "url": row.get("url"),
            "logo_url": row.get("logo_url"),
            "summary": summary,
            "description": row.get("description") or summary,
            "category_id": row.get("category_id"),
            "category_name": row.get("category_name"),
            "tags": tags or [],
            "occupations": occupations or [],
            "is_free": bool(row.get("is_free", True)),
            "need_login": bool(row.get("need_login", False)),
            "region": row.get("region") or "domestic",
            "quality_score": float(row.get("quality_score") or 0),
            "recommend_level": row.get("recommend_level") or 0,
            "click_count": row.get("click_count") or row.get("clicks") or 0,
            "favorite_count": row.get("favorite_count") or 0,
            "rating_avg": float(row.get("rating_avg") or 0),
            "created_at": row.get("created_at"),
        }

    def query_sites(limit=20, offset=0, category_id=None, keyword=None, tag=None, is_free=None, region=None, sort="recommend"):
        where = ["COALESCE(w.status, 'approved') IN ('approved', 'active')"]
        params = []
        joins = "LEFT JOIN categories c ON c.id = w.category_id"
        if category_id:
            where.append("(w.category_id=%s OR c.parent_id=%s)")
            params.extend([category_id, category_id])
        if keyword:
            where.append("(w.name LIKE %s OR w.summary LIKE %s OR w.description LIKE %s OR w.url LIKE %s)")
            like = f"%{keyword}%"
            params.extend([like, like, like, like])
        if tag:
            joins += " LEFT JOIN site_tags st_filter ON st_filter.site_id = w.id LEFT JOIN tags t_filter ON t_filter.id = st_filter.tag_id"
            where.append("t_filter.name=%s")
            params.append(tag)
        if is_free in ("free", "1", "true", True):
            where.append("COALESCE(w.is_free, 1)=1")
        elif is_free in ("paid", "0", "false", False):
            where.append("COALESCE(w.is_free, 1)=0")
        if region:
            where.append("w.region=%s")
            params.append(region)
        order_map = {
            "hot": "COALESCE(w.click_count, w.clicks, 0) DESC",
            "latest": "w.created_at DESC",
            "rating": "w.rating_avg DESC",
            "recommend": "w.recommend_level DESC, w.quality_score DESC, COALESCE(w.click_count, w.clicks, 0) DESC",
        }
        params.extend([limit, offset])
        sql = f"""
            SELECT w.*, c.name AS category_name
            FROM websites w
            {joins}
            WHERE {' AND '.join(where)}
            GROUP BY w.id
            ORDER BY {order_map.get(sort, order_map['recommend'])}
            LIMIT %s OFFSET %s
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
        finally:
            conn.close()
        ids = [row["id"] for row in rows]
        tags = site_tags(ids)
        occupations = site_occupations(ids)
        return [normalize_site(row, tags.get(row["id"], []), occupations.get(row["id"], [])) for row in rows]

    @app.route("/api/auth/logout", methods=["POST"])
    @jwt_required(optional=True)
    def v1_logout():
        return api_success()

    @app.route("/api/user/profile", methods=["GET"])
    @jwt_required()
    def v1_get_profile():
        user = current_user_row()
        if not user:
            return api_error("user not found", 404, 404)
        profile = {}
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM user_profiles WHERE user_id=%s", (user["id"],))
                profile = cursor.fetchone() or {}
        except Exception:
            profile = {}
        finally:
            conn.close()
        return api_success({
            "user": {
                "id": user.get("id"),
                "username": user.get("username"),
                "email": user.get("email"),
                "avatar": user.get("avatar") or user.get("avatar_url"),
                "role": user.get("role") or "user",
                "questionnaire_completed": bool(user.get("questionnaire_completed") or user.get("has_survey")),
            },
            "profile": profile,
            "recommendations": query_sites(limit=6),
            "favorites": [],
            "history": [],
        })

    @app.route("/api/user/profile", methods=["PUT"])
    @jwt_required()
    def v1_update_profile():
        user = current_user_row()
        if not user:
            return api_error("user not found", 404, 404)
        data = request.get_json(silent=True) or {}
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET username=COALESCE(%s, username), avatar=COALESCE(%s, avatar) WHERE id=%s",
                    (data.get("username"), data.get("avatar"), user["id"]),
                )
            conn.commit()
        finally:
            conn.close()
        return api_success()

    @app.route("/api/questionnaire", methods=["GET"])
    @jwt_required(optional=True)
    def v1_questionnaire_options():
        return api_success({
            "occupations": ["programmer", "designer", "product_manager", "operations", "marketing", "ecommerce", "teacher", "student", "creator", "other"],
            "purposes": ["efficiency", "learning", "ai_tools", "project_development", "design_assets", "data_analysis", "content_creation", "industry_news"],
            "interests": ["AI tools", "programming", "design resources", "product management", "growth", "data analysis", "office efficiency", "learning platforms", "startup resources", "assets"],
            "skill_levels": ["beginner", "junior", "intermediate", "senior"],
            "preferences": ["free first", "professional first", "domestic first", "international first", "tutorial first", "efficiency first"],
        })

    @app.route("/api/questionnaire/submit", methods=["POST"])
    @jwt_required()
    def v1_submit_questionnaire():
        user = current_user_row()
        if not user:
            return api_error("user not found", 404, 404)
        data = request.get_json(silent=True) or {}
        interests = data.get("interests") or []
        preferences = data.get("preferences") or []
        purposes = data.get("purposes") or data.get("purpose") or []
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO user_profiles (user_id, occupation, skill_level, interests, preferences, purposes)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE occupation=VALUES(occupation), skill_level=VALUES(skill_level),
                    interests=VALUES(interests), preferences=VALUES(preferences), purposes=VALUES(purposes)
                    """,
                    (user["id"], data.get("occupation"), data.get("skill_level"), json.dumps(interests, ensure_ascii=False), json.dumps(preferences, ensure_ascii=False), json.dumps(purposes, ensure_ascii=False)),
                )
                cursor.execute(
                    "UPDATE users SET questionnaire_completed=1, has_survey=1, user_tags=%s, interests=%s WHERE id=%s",
                    (",".join(interests), json.dumps(interests, ensure_ascii=False), user["id"]),
                )
            conn.commit()
        finally:
            conn.close()
        return api_success({"questionnaire_completed": True})

    @app.route("/api/user/profile-tags", methods=["GET"])
    @jwt_required()
    def v1_profile_tags():
        user = current_user_row()
        tags = []
        if user and user.get("user_tags"):
            tags = [item for item in str(user["user_tags"]).split(",") if item]
        return api_success({"tags": tags})

    @app.route("/api/categories", methods=["GET"])
    def v1_categories():
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, parent_id, name, icon, sort_order, status FROM categories WHERE COALESCE(status, 'active')='active' ORDER BY COALESCE(parent_id, 0), sort_order, id")
                rows = cursor.fetchall()
        finally:
            conn.close()
        return api_success(rows)

    @app.route("/api/tags", methods=["GET"])
    def v1_tags():
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, name, type FROM tags ORDER BY name")
                rows = cursor.fetchall()
        except Exception:
            rows = []
        finally:
            conn.close()
        return api_success(rows)

    @app.route("/api/sites", methods=["GET"])
    def v1_sites():
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        items = query_sites(
            limit=per_page,
            offset=max(page - 1, 0) * per_page,
            category_id=request.args.get("category_id") or request.args.get("category"),
            keyword=request.args.get("q") or request.args.get("keyword"),
            tag=request.args.get("tag"),
            is_free=request.args.get("is_free"),
            region=request.args.get("region"),
            sort=request.args.get("sort", "recommend"),
        )
        return api_success({"items": items, "page": page, "per_page": per_page})

    @app.route("/api/sites/hot", methods=["GET"])
    def v1_hot_sites():
        return api_success(query_sites(limit=request.args.get("limit", 8, type=int), sort="hot"))

    @app.route("/api/sites/latest", methods=["GET"])
    def v1_latest_sites():
        return api_success(query_sites(limit=request.args.get("limit", 8, type=int), sort="latest"))

    @app.route("/api/sites/recommend", methods=["GET"])
    @jwt_required(optional=True)
    def v1_recommend_sites():
        profile = {"occupation": "", "interests": []}
        if get_jwt_identity():
            user = current_user_row()
            if user:
                conn = get_db_connection()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT occupation, interests FROM user_profiles WHERE user_id=%s", (user["id"],))
                        row = cursor.fetchone() or {}
                    profile = {"occupation": row.get("occupation") or "", "interests": json.loads(row.get("interests") or "[]")}
                except Exception:
                    profile = {"occupation": "", "interests": []}
                finally:
                    conn.close()
        return api_success(rank_sites(query_sites(limit=40), profile, request.args.get("limit", 8, type=int)))

    @app.route("/api/sites/<int:site_id>", methods=["GET"])
    def v1_site_detail(site_id):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT w.*, c.name AS category_name FROM websites w LEFT JOIN categories c ON c.id=w.category_id WHERE w.id=%s", (site_id,))
                row = cursor.fetchone()
        finally:
            conn.close()
        if not row:
            return api_error("site not found", 404, 404)
        tags = site_tags([site_id]).get(site_id, [])
        occupations = site_occupations([site_id]).get(site_id, [])
        site = normalize_site(row, tags, occupations)
        site["similar_sites"] = [item for item in query_sites(limit=6, category_id=site["category_id"]) if item["id"] != site_id][:4]
        return api_success(site)

    @app.route("/api/sites/<int:site_id>/click", methods=["POST"])
    def v1_record_click(site_id):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE websites SET click_count=COALESCE(click_count,0)+1, clicks=COALESCE(clicks,0)+1 WHERE id=%s", (site_id,))
            conn.commit()
        finally:
            conn.close()
        return api_success()

    @app.route("/api/favorites", methods=["GET"])
    @jwt_required()
    def v1_favorites():
        user = current_user_row()
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT w.*, c.name AS category_name, f.note FROM favorites f JOIN websites w ON w.id=f.site_id LEFT JOIN categories c ON c.id=w.category_id WHERE f.user_id=%s ORDER BY f.created_at DESC", (user["id"],))
                rows = cursor.fetchall()
        except Exception:
            rows = []
        finally:
            conn.close()
        ids = [row["id"] for row in rows]
        tags = site_tags(ids)
        occupations = site_occupations(ids)
        items = []
        for row in rows:
            item = normalize_site(row, tags.get(row["id"], []), occupations.get(row["id"], []))
            item["note"] = row.get("note")
            items.append(item)
        return api_success(items)

    @app.route("/api/sites/<int:site_id>/favorite", methods=["POST"])
    @jwt_required()
    def v1_add_favorite(site_id):
        user = current_user_row()
        data = request.get_json(silent=True) or {}
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("INSERT IGNORE INTO favorites (user_id, site_id, note) VALUES (%s,%s,%s)", (user["id"], site_id, data.get("note")))
                cursor.execute("UPDATE websites SET favorite_count=COALESCE(favorite_count,0)+1 WHERE id=%s", (site_id,))
            conn.commit()
        finally:
            conn.close()
        return api_success()

    @app.route("/api/sites/<int:site_id>/favorite", methods=["DELETE"])
    @jwt_required()
    def v1_remove_favorite(site_id):
        user = current_user_row()
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM favorites WHERE user_id=%s AND site_id=%s", (user["id"], site_id))
                cursor.execute("UPDATE websites SET favorite_count=GREATEST(COALESCE(favorite_count,0)-1,0) WHERE id=%s", (site_id,))
            conn.commit()
        finally:
            conn.close()
        return api_success()

    @app.route("/api/search", methods=["GET"])
    def v1_search():
        q = request.args.get("q", "")
        return api_success({"items": query_sites(limit=request.args.get("limit", 30, type=int), keyword=q, tag=request.args.get("tag"), category_id=request.args.get("category_id"), sort=request.args.get("sort", "recommend")), "q": q})

    @app.route("/api/search/suggest", methods=["GET"])
    def v1_search_suggest():
        q = request.args.get("q", "")
        return api_success([{"id": item["id"], "name": item["name"]} for item in (query_sites(limit=6, keyword=q) if q else [])])

    @app.route("/api/search/hot-keywords", methods=["GET"])
    def v1_hot_keywords():
        return api_success(["AI tools", "programming", "design resources", "data analysis", "office efficiency"])

    @app.route("/api/admin/sites", methods=["GET", "POST"])
    @admin_required
    def v1_admin_sites():
        if request.method == "GET":
            return v1_sites()
        data = request.get_json(silent=True) or {}
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO websites (name,url,logo_url,summary,description,category_id,is_free,need_login,region,quality_score,recommend_level,status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'approved')", (data.get("name"), data.get("url"), data.get("logo_url"), data.get("summary"), data.get("description"), data.get("category_id"), data.get("is_free", 1), data.get("need_login", 0), data.get("region", "domestic"), data.get("quality_score", 0), data.get("recommend_level", 0)))
                site_id = cursor.lastrowid
            conn.commit()
        finally:
            conn.close()
        return api_success({"id": site_id}, status=201)

    @app.route("/api/admin/sites/<int:site_id>", methods=["PUT", "DELETE"])
    @admin_required
    def v1_admin_site_detail(site_id):
        if request.method == "DELETE":
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE websites SET status='deleted' WHERE id=%s", (site_id,))
                conn.commit()
            finally:
                conn.close()
            return api_success()
        data = request.get_json(silent=True) or {}
        allowed = ["name", "url", "logo_url", "summary", "description", "category_id", "is_free", "need_login", "region", "quality_score", "recommend_level", "status"]
        updates = [f"{key}=%s" for key in allowed if key in data]
        params = [data[key] for key in allowed if key in data]
        if not updates:
            return api_success()
        params.append(site_id)
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"UPDATE websites SET {', '.join(updates)} WHERE id=%s", params)
            conn.commit()
        finally:
            conn.close()
        return api_success()

    @app.route("/api/admin/categories", methods=["GET", "POST"])
    @admin_required
    def v1_admin_categories():
        if request.method == "GET":
            return v1_categories()
        data = request.get_json(silent=True) or {}
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO categories (name,parent_id,icon,sort_order,status) VALUES (%s,%s,%s,%s,'active')", (data.get("name"), data.get("parent_id"), data.get("icon"), data.get("sort_order", 0)))
                category_id = cursor.lastrowid
            conn.commit()
        finally:
            conn.close()
        return api_success({"id": category_id}, status=201)

    @app.route("/api/admin/categories/<int:category_id>", methods=["PUT", "DELETE"])
    @admin_required
    def v1_admin_category_detail(category_id):
        data = request.get_json(silent=True) or {}
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                if request.method == "DELETE":
                    cursor.execute("UPDATE categories SET status='deleted' WHERE id=%s", (category_id,))
                else:
                    cursor.execute("UPDATE categories SET name=COALESCE(%s,name), parent_id=%s, icon=COALESCE(%s,icon), sort_order=COALESCE(%s,sort_order) WHERE id=%s", (data.get("name"), data.get("parent_id"), data.get("icon"), data.get("sort_order"), category_id))
            conn.commit()
        finally:
            conn.close()
        return api_success()

    @app.route("/api/admin/tags", methods=["GET", "POST"])
    @admin_required
    def v1_admin_tags():
        if request.method == "GET":
            return v1_tags()
        data = request.get_json(silent=True) or {}
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO tags (name,type) VALUES (%s,%s)", (data.get("name"), data.get("type", "general")))
                tag_id = cursor.lastrowid
            conn.commit()
        finally:
            conn.close()
        return api_success({"id": tag_id}, status=201)

    @app.route("/api/admin/tags/<int:tag_id>", methods=["PUT", "DELETE"])
    @admin_required
    def v1_admin_tag_detail(tag_id):
        data = request.get_json(silent=True) or {}
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                if request.method == "DELETE":
                    cursor.execute("DELETE FROM tags WHERE id=%s", (tag_id,))
                else:
                    cursor.execute("UPDATE tags SET name=COALESCE(%s,name), type=COALESCE(%s,type) WHERE id=%s", (data.get("name"), data.get("type"), tag_id))
            conn.commit()
        finally:
            conn.close()
        return api_success()

    @app.route("/api/admin/users/<int:user_id>/status", methods=["PUT"])
    @admin_required
    def v1_admin_user_status(user_id):
        status = (request.get_json(silent=True) or {}).get("status", "active")
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET status=%s WHERE id=%s", (status, user_id))
            conn.commit()
        finally:
            conn.close()
        return api_success()
