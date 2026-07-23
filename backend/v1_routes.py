import json
import random
from functools import wraps

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ai_site_recommend_service import normalize_text, recommend_sites_for_query
from recommend_service import rank_sites


AI_SITE_CANDIDATE_LIMIT = 1000


def register_v1_routes(app, get_db_connection):
    columns_cache = {}

    def api_success(data=None, msg="success", status=200):
        return jsonify({
            "code": status,
            "legacy_code": 0,
            "message": msg,
            "msg": msg,
            "data": data if data is not None else {},
        }), status

    def api_error(msg, code=400, status=400, data=None):
        return jsonify({
            "code": code,
            "legacy_code": 0,
            "message": msg,
            "msg": msg,
            "data": data if data is not None else {},
        }), status

    def current_user_row():
        identity = get_jwt_identity()
        if identity is None:
            return None
        identity_text = str(identity).strip()
        if not identity_text:
            return None
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM (SELECT * FROM users WHERE username=%s OR email=%s) AS matched_user "
                    "WHERE deleted_at IS NULL LIMIT 1",
                    (identity_text, identity_text),
                )
                user = cursor.fetchone()
                if user:
                    return user
                if (
                    (isinstance(identity, int) and not isinstance(identity, bool))
                    or (isinstance(identity, str) and identity_text.isdigit())
                ):
                    cursor.execute(
                        "SELECT * FROM users WHERE id=%s AND deleted_at IS NULL LIMIT 1",
                        (int(identity_text),),
                    )
                    return cursor.fetchone()
                return None
        finally:
            conn.close()

    def record_behavior(user_id=None, site_id=None, behavior_type="", keyword=None):
        if not user_id:
            return
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO user_behaviors (user_id, site_id, behavior_type, keyword)
                    VALUES (%s,%s,%s,%s)
                    """,
                    (user_id, site_id, behavior_type, keyword),
                )
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

    def table_columns(table):
        if table in columns_cache:
            return columns_cache[table]
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM {table}")
                columns_cache[table] = {row["Field"] for row in cursor.fetchall()}
        except Exception:
            columns_cache[table] = set()
        finally:
            conn.close()
        return columns_cache[table]

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

    def sync_site_relations(cursor, site_id, tags=None, occupations=None):
        if tags is not None:
            cursor.execute("DELETE FROM site_tags WHERE site_id=%s", (site_id,))
            for tag_name in tags:
                if not tag_name:
                    continue
                cursor.execute("SELECT id FROM tags WHERE name=%s", (tag_name,))
                tag = cursor.fetchone()
                if tag:
                    tag_id = tag["id"]
                else:
                    cursor.execute(
                        "INSERT INTO tags (name,type) VALUES (%s,%s)",
                        (tag_name, "general"),
                    )
                    tag_id = cursor.lastrowid
                cursor.execute(
                    "INSERT IGNORE INTO site_tags (site_id, tag_id) VALUES (%s,%s)",
                    (site_id, tag_id),
                )
        if occupations is not None:
            cursor.execute("DELETE FROM site_occupations WHERE site_id=%s", (site_id,))
            for occupation in occupations:
                if occupation:
                    cursor.execute(
                        "INSERT IGNORE INTO site_occupations (site_id, occupation, weight) VALUES (%s,%s,%s)",
                        (site_id, occupation, 1),
                    )

    def parse_json_list(value):
        if not value:
            return []
        if isinstance(value, list):
            return value
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (TypeError, ValueError):
            return [item.strip() for item in str(value).split(",") if item.strip()]

    def default_questionnaire_config():
        return {
            "questions": [
                {
                    "key": "occupation",
                    "label": "职业",
                    "required": True,
                    "options": [
                        "programmer",
                        "designer",
                        "product_manager",
                        "operations",
                        "marketing",
                        "ecommerce",
                        "teacher",
                        "student",
                        "creator",
                        "other",
                    ],
                },
                {
                    "key": "purposes",
                    "label": "使用目的",
                    "required": True,
                    "multiple": True,
                    "options": [
                        "efficiency",
                        "learning",
                        "ai_tools",
                        "project_development",
                        "design_assets",
                        "data_analysis",
                        "content_creation",
                        "industry_news",
                    ],
                },
                {
                    "key": "interests",
                    "label": "兴趣方向",
                    "required": True,
                    "multiple": True,
                    "options": [
                        "AI tools",
                        "programming",
                        "design resources",
                        "product management",
                        "growth",
                        "data analysis",
                        "office efficiency",
                        "learning platforms",
                        "startup resources",
                        "assets",
                    ],
                },
                {
                    "key": "skill_level",
                    "label": "能力水平",
                    "required": True,
                    "options": ["beginner", "junior", "intermediate", "senior"],
                },
                {
                    "key": "preferences",
                    "label": "资源偏好",
                    "required": True,
                    "multiple": True,
                    "options": [
                        "free first",
                        "professional first",
                        "domestic first",
                        "international first",
                        "tutorial first",
                        "efficiency first",
                    ],
                },
            ],
            "occupation_tag_map": {
                "programmer": ["programming", "AI tools", "project_development"],
                "designer": ["design resources", "assets", "AI tools"],
                "product_manager": ["product management", "startup resources", "data analysis"],
                "operations": ["growth", "content_creation", "office efficiency"],
                "teacher": ["learning platforms", "AI tools", "content_creation"],
                "student": ["learning platforms", "programming", "AI tools"],
            },
        }

    def questionnaire_options_from_config(config):
        questions = config.get("questions") if isinstance(config, dict) else []
        by_key = {item.get("key"): item for item in questions if isinstance(item, dict)}
        fallback = default_questionnaire_config()
        fallback_by_key = {item["key"]: item for item in fallback["questions"]}

        def options(key):
            return (
                by_key.get(key, {}).get("options")
                or fallback_by_key.get(key, {}).get("options")
                or []
            )

        return {
            "occupations": options("occupation"),
            "purposes": options("purposes"),
            "interests": options("interests"),
            "skill_levels": options("skill_level"),
            "preferences": options("preferences"),
            "questions": questions or fallback["questions"],
            "occupation_tag_map": config.get("occupation_tag_map") or fallback["occupation_tag_map"],
        }

    def default_recommend_rules():
        return {
            "occupation_site_weights": {
                "programmer": ["programming", "code", "docs", "developer"],
                "designer": ["design", "ui", "assets", "prototype"],
                "product_manager": ["product", "prototype", "analytics", "collaboration"],
                "operations": ["growth", "marketing", "content", "office"],
                "teacher": ["learning", "writing", "knowledge", "course"],
                "student": ["learning", "docs", "AI", "programming"],
            },
            "weights": {
                "occupation_score": 0.4,
                "interest_score": 0.25,
                "quality_score": 0.2,
                "popularity_score": 0.1,
                "freshness_score": 0.05,
                "behavior_score": 0.05,
            },
            "blacklist": ["王者荣耀", "和平精英", "抖音", "快手", "百度"],
            "reason_templates": {
                "programmer": "适合前端开发、代码学习和项目构建",
                "designer": "适合 UI 设计、素材查找和创意生成",
                "teacher": "适合学习、论文写作和知识整理",
                "default": "根据职业、兴趣和资源质量综合推荐",
            },
        }

    def default_admin_settings():
        return {
            "site_name": "智汇导航",
            "audit_mode": "manual",
            "allow_registration": True,
            "comment_default_status": "visible",
            "home_sections": [
                "categories",
                "career",
                "recommend",
                "hot",
                "latest",
                "tools",
            ],
        }

    def ensure_app_settings_table(cursor):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
              setting_key VARCHAR(120) PRIMARY KEY,
              setting_value LONGTEXT NOT NULL,
              updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

    def load_json_setting(key, default_value):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                ensure_app_settings_table(cursor)
                cursor.execute(
                    "SELECT setting_value FROM app_settings WHERE setting_key=%s",
                    (key,),
                )
                row = cursor.fetchone()
            conn.commit()
        except Exception:
            return default_value
        finally:
            conn.close()
        if not row:
            return default_value
        try:
            return json.loads(row.get("setting_value") or "{}")
        except (TypeError, ValueError):
            return default_value

    def save_json_setting(key, value):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                ensure_app_settings_table(cursor)
                cursor.execute(
                    """
                    INSERT INTO app_settings (setting_key, setting_value)
                    VALUES (%s,%s)
                    ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value)
                    """,
                    (key, json.dumps(value, ensure_ascii=False)),
                )
            conn.commit()
        finally:
            conn.close()

    def categories_with_children(rows):
        items = [dict(row) for row in rows]
        by_id = {item.get("id"): item for item in items}
        for item in items:
            item.setdefault("children", [])
        for item in items:
            parent_id = item.get("parent_id")
            parent = by_id.get(parent_id)
            if parent_id and parent:
                parent.setdefault("children", []).append(item)
        return items

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
            "status": row.get("status") or "approved",
            "created_at": row.get("created_at"),
            "is_favorited": bool(row.get("is_favorited", False)),
            "reason": row.get("reason") or "热门优质资源",
        }

    ai_keywords = [
        "AI",
        "人工智能",
        "AI工具",
        "ChatGPT",
        "Claude",
        "Gemini",
        "AIGC",
        "生成式",
        "智能",
        "模型",
        "写作",
        "绘图",
        "编程",
        "设计",
        "效率",
    ]
    fallback_keywords = [
        "开发",
        "编程",
        "代码",
        "设计",
        "学习",
        "文档",
        "效率",
        "办公",
        "协作",
        "Figma",
        "Canva",
        "GitHub",
        "MDN",
        "Vue",
        "Flask",
        "LeetCode",
        "Notion",
        "ProcessOn",
    ]
    blocked_keywords = [
        "王者荣耀",
        "和平精英",
        "抖音",
        "快手",
        "游戏",
        "手游",
        "短视频",
    ]
    blocked_names = ["百度"]
    career_ai_keywords = {
        "学生": ["学习", "论文", "PPT", "编程入门", "效率", "AI", "写作"],
        "前端开发": ["前端", "Vue", "React", "JavaScript", "代码", "编程", "开发", "AI"],
        "后端开发": ["后端", "Python", "Flask", "API", "数据库", "代码", "编程", "AI"],
        "产品经理": ["产品", "原型", "需求", "文档", "流程图", "数据分析", "AI"],
        "UI/UX 设计师": ["设计", "UI", "UX", "Figma", "图标", "图片", "绘图", "AI"],
        "运营": ["运营", "文案", "内容", "数据分析", "增长", "办公", "AI"],
        "教师": ["教学", "课件", "PPT", "学习", "题库", "教育", "AI"],
        "自媒体创作者": ["写作", "视频", "剪辑", "图片", "内容创作", "AIGC", "AI"],
        "数据分析师": ["数据分析", "可视化", "Python", "SQL", "报表", "AI"],
        "其他": ["AI", "效率", "学习", "办公", "写作"],
    }
    career_preferred_names = {
        "学生": ["ChatGPT", "Kimi", "Perplexity", "Poe", "Notion", "ProcessOn", "Bilibili", "Coursera"],
        "前端开发": ["GitHub", "MDN Web Docs", "Vue 官方文档", "Stack Overflow", "Vercel", "CodePen", "ChatGPT"],
        "后端开发": ["GitHub", "Flask 官方文档", "Postman", "Stack Overflow", "Docker", "LeetCode", "ChatGPT"],
        "产品经理": ["Notion", "ProcessOn", "飞书", "Figma", "Trello", "ChatGPT"],
        "UI/UX 设计师": ["Figma", "Canva", "Iconfont", "Unsplash", "Midjourney", "Dribbble", "Runway"],
        "运营": ["ChatGPT", "Canva", "Notion", "飞书", "ProcessOn", "豆包"],
        "教师": ["ChatGPT", "Kimi", "Canva", "ProcessOn", "Bilibili", "Coursera"],
        "自媒体创作者": ["ChatGPT", "Canva", "Runway", "Midjourney", "豆包", "Bilibili"],
        "数据分析师": ["Kaggle", "Tableau", "Power BI", "Jupyter", "Python", "SQL", "ChatGPT"],
        "其他": ["ChatGPT", "Claude", "Gemini", "Notion", "Figma", "Canva"],
    }
    career_reasons = {
        "学生": "适合学习、论文写作和知识整理。",
        "前端开发": "适合前端开发、代码学习和项目构建。",
        "后端开发": "适合后端开发、接口调试和代码辅助。",
        "产品经理": "适合需求分析、产品文档和流程梳理。",
        "UI/UX 设计师": "适合界面设计、素材查找和创意生成。",
        "运营": "适合内容运营、文案生成和数据分析。",
        "教师": "适合课件制作、教学设计和资料整理。",
        "自媒体创作者": "适合内容创作、视频脚本和图片生成。",
        "数据分析师": "适合数据分析、报表整理和效率提升。",
        "其他": "适合学习、工作和创作场景使用。",
    }

    def parse_id_list(value):
        ids = []
        for item in str(value or "").split(","):
            item = item.strip()
            if item.isdigit():
                ids.append(int(item))
        return ids

    def clean_arg(value):
        value = str(value or "").strip()
        return value or None

    def site_text(site):
        parts = [
            site.get("name"),
            site.get("summary"),
            site.get("description"),
            site.get("category_name"),
            *(site.get("tags") or []),
            *(site.get("occupations") or []),
        ]
        return " ".join(str(item) for item in parts if item).lower()

    def is_resource_site(site, keywords):
        text = site_text(site)
        name = str(site.get("name") or "").lower()
        if any(keyword.lower() == name for keyword in blocked_names):
            return False
        if any(keyword.lower() in text for keyword in blocked_keywords):
            return False
        return any(keyword.lower() in text for keyword in keywords)

    def query_resource_sites(limit=8, category=None, tag=None, exclude_ids=None, sort="random", fallback=False):
        website_columns = table_columns("websites")
        category_columns = table_columns("categories")
        exclude_ids = exclude_ids or []
        keywords = fallback_keywords if fallback else ai_keywords
        joins = [
            "LEFT JOIN categories c ON c.id = w.category_id",
            "LEFT JOIN site_tags st_match ON st_match.site_id = w.id",
            "LEFT JOIN tags t_match ON t_match.id = st_match.tag_id",
        ]
        where = []
        params = []
        if "status" in website_columns:
            where.append("COALESCE(w.status, 'approved') IN ('approved', 'active')")
        if category:
            if str(category).isdigit():
                where.append("w.category_id=%s")
                params.append(int(category))
            elif "name" in category_columns:
                where.append("c.name=%s")
                params.append(category)
        if tag:
            joins.extend([
                "LEFT JOIN site_tags st_filter ON st_filter.site_id = w.id",
                "LEFT JOIN tags t_filter ON t_filter.id = st_filter.tag_id",
            ])
            where.append("t_filter.name=%s")
            params.append(tag)
        if exclude_ids:
            placeholders = ",".join(["%s"] * len(exclude_ids))
            where.append(f"w.id NOT IN ({placeholders})")
            params.extend(exclude_ids)

        text_fields = []
        for column in ("name", "summary", "description", "url"):
            if column in website_columns:
                text_fields.append(f"w.{column}")
        if "name" in category_columns:
            text_fields.append("c.name")
        text_fields.append("t_match.name")

        match_clauses = []
        for keyword in keywords:
            per_keyword = [f"{field} LIKE %s" for field in text_fields]
            match_clauses.append(f"({' OR '.join(per_keyword)})")
            params.extend([f"%{keyword}%"] * len(text_fields))
        where.append(f"({' OR '.join(match_clauses)})")

        blocked_clauses = []
        for keyword in blocked_keywords:
            per_keyword = [f"{field} LIKE %s" for field in text_fields]
            blocked_clauses.append(f"({' OR '.join(per_keyword)})")
            params.extend([f"%{keyword}%"] * len(text_fields))
        where.append(f"NOT ({' OR '.join(blocked_clauses)})")

        if "click_count" in website_columns and "clicks" in website_columns:
            click_expr = "COALESCE(w.click_count, w.clicks, 0)"
        elif "click_count" in website_columns:
            click_expr = "COALESCE(w.click_count, 0)"
        elif "clicks" in website_columns:
            click_expr = "COALESCE(w.clicks, 0)"
        else:
            click_expr = "0"
        order_sql = "RAND()" if sort == "random" else f"{click_expr} DESC"
        params.append(limit)
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT w.*, c.name AS category_name
                    FROM websites w
                    {' '.join(joins)}
                    WHERE {' AND '.join(where)}
                    GROUP BY w.id
                    ORDER BY {order_sql}
                    LIMIT %s
                    """,
                    params,
                )
                rows = cursor.fetchall()
        finally:
            conn.close()
        ids = [row["id"] for row in rows]
        tags = site_tags(ids)
        occupations = site_occupations(ids)
        if fallback:
            reason = "适合学习、工作和创作场景使用"
        elif sort == "hot":
            reason = "根据热门度和资源质量推荐"
        else:
            reason = "AI 工具随机推荐"
        items = [normalize_site(row, tags.get(row["id"], []), occupations.get(row["id"], [])) for row in rows]
        for item in items:
            item["reason"] = reason
        return [item for item in items if is_resource_site(item, keywords)]

    def random_resource_sites(limit=8, category=None, tag=None, scene=None, exclude_ids=None):
        exclude_ids = exclude_ids or []
        items = query_resource_sites(limit, category, tag, exclude_ids, sort="random")
        seen = {item["id"] for item in items}
        if len(items) < limit:
            fallback = query_resource_sites(
                limit - len(items),
                None,
                None,
                exclude_ids + list(seen),
                sort="random",
                fallback=True,
            )
            items.extend(fallback)
            seen.update(item["id"] for item in fallback)
        return items[:limit]

    def query_career_sites(occupation, limit=8, ai_only=False, exclude_ids=None, rules=None):
        occupation = str(occupation or "").strip()
        exclude_ids = exclude_ids or []
        rules = rules or {}
        if not occupation:
            return []
        configured_keywords = (rules.get("occupation_site_weights") or {}).get(occupation)
        keywords = configured_keywords or career_ai_keywords.get(occupation, career_ai_keywords["其他"])
        preferred_names = career_preferred_names.get(occupation, career_preferred_names["其他"])
        resource_keywords = list(dict.fromkeys(ai_keywords + fallback_keywords + keywords))
        reason = (rules.get("reason_templates") or {}).get(occupation) or career_reasons.get(occupation, career_reasons["其他"])
        blacklist = [str(item).lower() for item in (rules.get("blacklist") or [])]
        candidates = query_resource_sites(
            limit=max(limit * 8, 40),
            category=None,
            exclude_ids=exclude_ids,
            sort="hot",
        )
        candidates.extend(
            query_sites(
                limit=max(limit * 8, 40),
                sort="recommend",
                exclude_ids=exclude_ids,
            )
        )

        seen = set()
        scored = []
        for site in candidates:
            site_id = site.get("id")
            if not site_id or site_id in seen:
                continue
            seen.add(site_id)
            text = site_text(site)
            if any(keyword in text for keyword in blacklist):
                continue
            exact_occupation = occupation in (site.get("occupations") or [])
            keyword_hits = sum(1 for keyword in keywords if keyword.lower() in text)
            name = str(site.get("name") or "").lower()
            preferred_index = next(
                (
                    index
                    for index, preferred_name in enumerate(preferred_names)
                    if preferred_name.lower() in name or name in preferred_name.lower()
                ),
                None,
            )
            preferred_score = 0 if preferred_index is None else len(preferred_names) - preferred_index
            if not exact_occupation and not keyword_hits and not preferred_score:
                continue
            if not is_resource_site(site, resource_keywords):
                continue
            item = dict(site)
            item["reason"] = reason
            scored.append(
                (
                    preferred_score,
                    int(exact_occupation),
                    keyword_hits,
                    item.get("recommend_level") or 0,
                    item.get("quality_score") or 0,
                    item.get("click_count") or 0,
                    random.random(),
                    item,
                )
            )

        scored.sort(key=lambda row: row[:7], reverse=True)
        return [row[-1] for row in scored[:limit]]

    def query_sites(limit=20, offset=0, category_id=None, keyword=None, tag=None, is_free=None, region=None, sort="recommend", exclude_ids=None):
        website_columns = table_columns("websites")
        category_columns = table_columns("categories")
        exclude_ids = exclude_ids or []
        category_id = clean_arg(category_id)
        keyword = clean_arg(keyword)
        tag = clean_arg(tag)
        is_free = clean_arg(is_free)
        region = clean_arg(region)
        sort = clean_arg(sort) or "recommend"
        where = []
        params = []
        joins = "LEFT JOIN categories c ON c.id = w.category_id"
        if "status" in website_columns:
            where.append("COALESCE(w.status, 'approved') IN ('approved', 'active')")
        if category_id:
            category_value = str(category_id).strip()
            if category_value.isdigit():
                category_int = int(category_value)
                if "parent_id" in category_columns:
                    where.append("(w.category_id=%s OR c.parent_id=%s)")
                    params.extend([category_int, category_int])
                else:
                    where.append("w.category_id=%s")
                    params.append(category_int)
            elif "name" in category_columns:
                if "parent_id" in category_columns:
                    joins += " LEFT JOIN categories pc ON pc.id = c.parent_id"
                    where.append("(c.name=%s OR pc.name=%s)")
                    params.extend([category_value, category_value])
                else:
                    where.append("c.name=%s")
                    params.append(category_value)
        if keyword:
            joins += " LEFT JOIN site_tags st_search ON st_search.site_id = w.id LEFT JOIN tags t_search ON t_search.id = st_search.tag_id"
            joins += " LEFT JOIN site_occupations so_search ON so_search.site_id = w.id"
            search_fields = []
            for column in ("name", "summary", "description", "url"):
                if column in website_columns:
                    search_fields.append(f"w.{column} LIKE %s")
            if "name" in category_columns:
                search_fields.append("c.name LIKE %s")
            search_fields.extend(["t_search.name LIKE %s", "so_search.occupation LIKE %s"])
            where.append(f"({' OR '.join(search_fields)})")
            like = f"%{keyword}%"
            params.extend([like] * len(search_fields))
        if tag:
            joins += " LEFT JOIN site_tags st_filter ON st_filter.site_id = w.id LEFT JOIN tags t_filter ON t_filter.id = st_filter.tag_id"
            where.append("t_filter.name=%s")
            params.append(tag)
        if "is_free" in website_columns and is_free in ("free", "1", "true", True):
            where.append("COALESCE(w.is_free, 1)=1")
        elif "is_free" in website_columns and is_free in ("paid", "0", "false", False):
            where.append("COALESCE(w.is_free, 1)=0")
        if region and "region" in website_columns:
            where.append("w.region=%s")
            params.append(region)
        if exclude_ids:
            placeholders = ",".join(["%s"] * len(exclude_ids))
            where.append(f"w.id NOT IN ({placeholders})")
            params.extend(exclude_ids)
        if "click_count" in website_columns and "clicks" in website_columns:
            click_expr = "COALESCE(w.click_count, w.clicks, 0)"
        elif "click_count" in website_columns:
            click_expr = "COALESCE(w.click_count, 0)"
        elif "clicks" in website_columns:
            click_expr = "COALESCE(w.clicks, 0)"
        else:
            click_expr = "0"
        latest_expr = "w.created_at DESC" if "created_at" in website_columns else "w.id DESC"
        quality_value = "COALESCE(w.quality_score, 0)" if "quality_score" in website_columns else "0"
        favorite_value = "COALESCE(w.favorite_count, 0)" if "favorite_count" in website_columns else "0"
        rating_value = "COALESCE(w.rating_avg, 0)" if "rating_avg" in website_columns else "0"
        quality_expr = f"{quality_value} DESC" if "quality_score" in website_columns else click_expr + " DESC"
        recommend_expr = "w.recommend_level DESC, " if "recommend_level" in website_columns else ""
        hot_order_terms = []
        if "click_count" in website_columns or "clicks" in website_columns:
            hot_order_terms.append(f"{click_expr} DESC")
        if "favorite_count" in website_columns:
            hot_order_terms.append(f"{favorite_value} DESC")
        if "rating_avg" in website_columns:
            hot_order_terms.append(f"{rating_value} DESC")
        if "quality_score" in website_columns:
            hot_order_terms.append(f"{quality_value} DESC")
        hot_order_terms.append("w.id DESC")
        order_map = {
            "hot": ", ".join(hot_order_terms),
            "latest": latest_expr,
            "rating": "w.rating_avg DESC" if "rating_avg" in website_columns else quality_expr,
            "recommend": f"{recommend_expr}{quality_expr}, {click_expr} DESC",
        }
        params.extend([limit, offset])
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        sql = f"""
            SELECT w.*, c.name AS category_name
            FROM websites w
            {joins}
            {where_sql}
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
        config = load_json_setting("questionnaire_config", default_questionnaire_config())
        return api_success(questionnaire_options_from_config(config))

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
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return api_success({"questionnaire_completed": True})

    @app.route("/api/questionnaire/my", methods=["GET"])
    @jwt_required()
    def v1_my_questionnaire():
        user = current_user_row()
        if not user:
            return api_error("user not found", 404, 404)
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM user_profiles WHERE user_id=%s", (user["id"],))
                profile = cursor.fetchone() or {}
        finally:
            conn.close()
        return api_success({
            "occupation": profile.get("occupation") or "",
            "skill_level": profile.get("skill_level") or "",
            "interests": parse_json_list(profile.get("interests") or user.get("interests")),
            "preferences": parse_json_list(profile.get("preferences")),
            "purposes": parse_json_list(profile.get("purposes")),
            "questionnaire_completed": bool(user.get("questionnaire_completed") or user.get("has_survey")),
        })

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
        category_columns = table_columns("categories")
        parent_expr = "parent_id" if "parent_id" in category_columns else "NULL AS parent_id"
        icon_expr = "icon" if "icon" in category_columns else "'' AS icon"
        sort_expr = "sort_order" if "sort_order" in category_columns else "0 AS sort_order"
        status_expr = "status" if "status" in category_columns else "'active' AS status"
        where_sql = "WHERE COALESCE(status, 'active')='active'" if "status" in category_columns else ""
        order_sql = "COALESCE(parent_id, 0), sort_order, id" if "parent_id" in category_columns else "sort_order, id"
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, {parent_expr}, name, {icon_expr}, {sort_expr}, {status_expr}
                    FROM categories
                    {where_sql}
                    ORDER BY {order_sql}
                    """
                )
                rows = cursor.fetchall()
        finally:
            conn.close()
        return api_success(categories_with_children(rows))

    @app.route("/api/categories/<int:category_id>", methods=["GET"])
    def v1_category_detail(category_id):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, parent_id, name, icon, sort_order, status FROM categories WHERE id=%s", (category_id,))
                row = cursor.fetchone()
        finally:
            conn.close()
        if not row:
            return api_error("category not found", 404, 404)
        return api_success(row)

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
        page = max(1, request.args.get("page", 1, type=int))
        per_page = max(1, min(request.args.get(
            "limit",
            request.args.get("per_page", request.args.get("page_size", 20, type=int), type=int),
            type=int,
        ), 100))
        items = query_sites(
            limit=per_page,
            offset=max(page - 1, 0) * per_page,
            category_id=clean_arg(request.args.get("category_id")) or clean_arg(request.args.get("category")),
            keyword=clean_arg(request.args.get("q")) or clean_arg(request.args.get("keyword")),
            tag=clean_arg(request.args.get("tag")),
            is_free=clean_arg(request.args.get("is_free")),
            region=clean_arg(request.args.get("region")),
            sort=clean_arg(request.args.get("sort")) or "recommend",
            exclude_ids=parse_id_list(request.args.get("exclude_ids")),
        )
        return api_success({"items": items, "page": page, "per_page": per_page})

    @app.route("/api/sites/random", methods=["GET"])
    def v1_random_sites():
        limit = max(1, min(request.args.get("limit", 8, type=int), 50))
        exclude_ids = parse_id_list(request.args.get("exclude_ids"))
        occupation = request.args.get("occupation")
        if occupation:
            return api_success(
                query_career_sites(
                    occupation=occupation,
                    limit=limit,
                    exclude_ids=exclude_ids,
                    ai_only=request.args.get("category") == "AI工具",
                )
            )
        return api_success(
            random_resource_sites(
                limit=limit,
                category=request.args.get("category"),
                tag=request.args.get("tag"),
                scene=request.args.get("scene"),
                exclude_ids=exclude_ids,
            )
        )

    @app.route("/api/sites/hot", methods=["GET"])
    def v1_hot_sites():
        limit = max(1, min(request.args.get("limit", 8, type=int), 50))
        category = request.args.get("category")
        exclude_ids = parse_id_list(request.args.get("exclude_ids"))
        if request.args.get("ai_only") in ("1", "true", "True") or category:
            return api_success(
                query_resource_sites(
                    limit=limit,
                    category=category,
                    tag=request.args.get("tag"),
                    exclude_ids=exclude_ids,
                    sort="hot",
                )
            )
        return api_success(query_sites(limit=limit, sort="hot", exclude_ids=exclude_ids))

    @app.route("/api/sites/latest", methods=["GET"])
    def v1_latest_sites():
        return api_success(query_sites(limit=request.args.get("limit", 8, type=int), sort="latest"))

    @app.route("/api/sites/recommend", methods=["GET"])
    @jwt_required(optional=True)
    def v1_recommend_sites():
        limit = max(1, min(request.args.get("limit", 8, type=int), 50))
        exclude_ids = parse_id_list(request.args.get("exclude_ids"))
        occupation = request.args.get("occupation")
        rules = load_json_setting("recommend_rules", default_recommend_rules())
        if occupation:
            return api_success(
                query_career_sites(
                    occupation=occupation,
                    limit=limit,
                    exclude_ids=exclude_ids,
                    ai_only=request.args.get("ai_only") in ("1", "true", "True"),
                    rules=rules,
                )
            )
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
        source_sites = query_sites(limit=40, exclude_ids=exclude_ids)
        if not profile.get("occupation") and not profile.get("interests"):
            source_sites = query_sites(limit=40, sort="hot", exclude_ids=exclude_ids) or source_sites
        ranked = rank_sites(source_sites, profile, limit, rules)
        if not ranked:
            ranked = rank_sites(
                query_sites(limit=40, sort="hot", exclude_ids=exclude_ids),
                {},
                limit,
                rules,
            )
        return api_success(ranked)

    @app.route("/api/ai/site-recommend", methods=["POST"])
    @jwt_required()
    def v1_ai_site_recommend():
        user = current_user_row()
        if not user:
            return api_error("当前用户不存在或已失效", 401, 401)

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or "query" not in payload:
            return api_error("请输入需求描述")
        raw_query = payload.get("query")
        if not isinstance(raw_query, str):
            return api_error("需求描述必须是文本")
        if len(raw_query.strip()) > 500:
            return api_error("需求描述不能超过 500 个字符")
        query = normalize_text(raw_query)
        if not query:
            return api_error("请输入需求描述")
        if len(query) < 2:
            return api_error("请更具体地描述你的需求")

        try:
            limit = max(1, min(int(payload.get("limit", 5)), 5))
        except (TypeError, ValueError):
            limit = 5

        profile = {"occupation": "", "interests": []}
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT occupation, interests FROM user_profiles WHERE user_id=%s", (user["id"],))
                profile_row = cursor.fetchone() or {}
            raw_interests = profile_row.get("interests")
            try:
                parsed_interests = json.loads(raw_interests or "[]")
                interests = parsed_interests if isinstance(parsed_interests, list) else []
            except (TypeError, ValueError):
                interests = []
            profile = {
                "occupation": profile_row.get("occupation") or "",
                "interests": interests,
            }
        except Exception:
            profile = {"occupation": "", "interests": []}
        finally:
            conn.close()

        try:
            matches = recommend_sites_for_query(
                query,
                query_sites(limit=AI_SITE_CANDIDATE_LIMIT),
                occupation=profile["occupation"],
                interests=profile["interests"],
                limit=limit,
            )
        except Exception as exc:
            app.logger.error("ai site recommendation failed: %s", type(exc).__name__)
            return api_error("推荐服务暂时不可用", 500, 500)

        items = []
        for match in matches:
            site = match["site"]
            items.append({
                "id": site.get("id"),
                "name": site.get("name") or "",
                "url": site.get("url") or "",
                "logo_url": site.get("logo_url") or "",
                "summary": site.get("summary") or "",
                "description": site.get("description") or "",
                "category_name": site.get("category_name") or "",
                "tags": site.get("tags") or [],
                "reason": match["reason"],
                "match_score": match["score"],
            })
        return api_success(
            {"query": query, "items": items},
            msg="未找到匹配网站" if not items else "success",
        )

    @app.route("/api/sites/<int:site_id>", methods=["GET"])
    @jwt_required(optional=True)
    def v1_site_detail(site_id):
        user = current_user_row() if get_jwt_identity() else None
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT w.*, c.name AS category_name,
                    CASE WHEN f.site_id IS NULL THEN 0 ELSE 1 END AS is_favorited
                    FROM websites w
                    LEFT JOIN categories c ON c.id=w.category_id
                    LEFT JOIN favorites f ON f.site_id=w.id AND f.user_id=%s
                    WHERE w.id=%s
                    """,
                    (user["id"] if user else 0, site_id),
                )
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

    @app.route("/api/sites/<int:site_id>/similar", methods=["GET"])
    def v1_similar_sites(site_id):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT category_id FROM websites WHERE id=%s", (site_id,))
                row = cursor.fetchone()
        finally:
            conn.close()
        if not row:
            return api_error("site not found", 404, 404)
        seen = {site_id}
        items = []
        for item in query_sites(limit=8, category_id=row.get("category_id")):
            if item["id"] not in seen:
                items.append(item)
                seen.add(item["id"])
        for tag_name in site_tags([site_id]).get(site_id, []):
            if len(items) >= 6:
                break
            for item in query_sites(limit=6, tag=tag_name):
                if item["id"] not in seen:
                    items.append(item)
                    seen.add(item["id"])
                    if len(items) >= 6:
                        break
        items = items[:6]
        return api_success(items)

    @app.route("/api/sites/<int:site_id>/click", methods=["POST"])
    @jwt_required(optional=True)
    def v1_record_click(site_id):
        user = current_user_row() if get_jwt_identity() else None
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE websites SET click_count=COALESCE(click_count,0)+1, clicks=COALESCE(clicks,0)+1 WHERE id=%s", (site_id,))
            conn.commit()
        finally:
            conn.close()
        record_behavior(user.get("id") if user else None, site_id, "click")
        return api_success()

    @app.route("/api/favorites", methods=["GET"])
    @jwt_required()
    def v1_favorites():
        user = current_user_row()
        if not user:
            return api_error("登录状态已失效，请重新登录", 401, 401)
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT w.*, c.name AS category_name, f.note FROM favorites f JOIN websites w ON w.id=f.site_id LEFT JOIN categories c ON c.id=w.category_id WHERE f.user_id=%s ORDER BY f.created_at DESC", (user["id"],))
                rows = cursor.fetchall()
        except Exception as exc:
            app.logger.error("favorites list query failed (error_type=%s)", type(exc).__name__)
            return api_error("收藏加载失败，请稍后重试", 500, 500)
        finally:
            conn.close()
        ids = [row["id"] for row in rows]
        tags = site_tags(ids)
        occupations = site_occupations(ids)
        items = []
        for row in rows:
            item = normalize_site(row, tags.get(row["id"], []), occupations.get(row["id"], []))
            item["note"] = row.get("note")
            item["is_favorited"] = True
            items.append(item)
        return api_success(items)

    @app.route("/api/sites/<int:site_id>/favorite", methods=["POST"])
    @jwt_required()
    def v1_add_favorite(site_id):
        user = current_user_row()
        if not user:
            return api_error("登录状态已失效，请重新登录", 401, 401)
        data = request.get_json(silent=True) or {}
        has_favorite_count = "favorite_count" in table_columns("websites")
        inserted = False
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM websites WHERE id=%s LIMIT 1", (site_id,))
                if not cursor.fetchone():
                    return api_error("网站不存在", 404, 404)
                cursor.execute(
                    "SELECT id FROM favorites WHERE user_id=%s AND site_id=%s LIMIT 1",
                    (user["id"], site_id),
                )
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO favorites (user_id, site_id, note) VALUES (%s,%s,%s)",
                        (user["id"], site_id, data.get("note")),
                    )
                    inserted = True
                    if has_favorite_count:
                        cursor.execute("UPDATE websites SET favorite_count=COALESCE(favorite_count,0)+1 WHERE id=%s", (site_id,))
            conn.commit()
        finally:
            conn.close()
        if inserted:
            record_behavior(user.get("id"), site_id, "favorite")
        return api_success({"favorited": True, "created": inserted})

    @app.route("/api/sites/<int:site_id>/favorite", methods=["DELETE"])
    @jwt_required()
    def v1_remove_favorite(site_id):
        user = current_user_row()
        if not user:
            return api_error("登录状态已失效，请重新登录", 401, 401)
        has_favorite_count = "favorite_count" in table_columns("websites")
        removed = False
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM favorites WHERE user_id=%s AND site_id=%s", (user["id"], site_id))
                if cursor.rowcount:
                    removed = True
                    if has_favorite_count:
                        cursor.execute("UPDATE websites SET favorite_count=GREATEST(COALESCE(favorite_count,0)-1,0) WHERE id=%s", (site_id,))
            conn.commit()
        finally:
            conn.close()
        return api_success({"favorited": False, "removed": removed})

    @app.route("/api/sites/<int:site_id>/favorite", methods=["PUT"])
    @jwt_required()
    def v1_update_favorite_note(site_id):
        user = current_user_row()
        if not user:
            return api_error("登录状态已失效，请重新登录", 401, 401)
        data = request.get_json(silent=True) or {}
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE favorites SET note=%s WHERE user_id=%s AND site_id=%s",
                    (data.get("note", ""), user["id"], site_id),
                )
            conn.commit()
        finally:
            conn.close()
        return api_success()

    @app.route("/api/sites/<int:site_id>/comments", methods=["GET"])
    @jwt_required(optional=True)
    def v1_site_comments(site_id):
        user = current_user_row() if get_jwt_identity() else None
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT cm.id, cm.user_id, cm.site_id, cm.content, cm.rating, cm.status, cm.created_at,
                           u.username, CASE WHEN cm.user_id=%s THEN 1 ELSE 0 END AS can_delete
                    FROM comments cm
                    LEFT JOIN users u ON u.id=cm.user_id
                    WHERE cm.site_id=%s AND COALESCE(cm.status, 'visible') IN ('visible', 'approved')
                    ORDER BY cm.created_at DESC
                    """,
                    (user["id"] if user else 0, site_id),
                )
                rows = cursor.fetchall()
        finally:
            conn.close()
        return api_success(rows)

    @app.route("/api/sites/<int:site_id>/comments", methods=["POST"])
    @jwt_required()
    def v1_add_site_comment(site_id):
        user = current_user_row()
        data = request.get_json(silent=True) or {}
        content = str(data.get("content") or "").strip()
        rating = data.get("rating")
        if not content:
            return api_error("评论内容不能为空")
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO comments (user_id, site_id, content, rating, status) VALUES (%s,%s,%s,%s,%s)",
                    (user["id"], site_id, content, rating, "visible"),
                )
                comment_id = cursor.lastrowid
                cursor.execute(
                    "UPDATE websites SET rating_avg=(SELECT AVG(rating) FROM comments WHERE site_id=%s AND rating IS NOT NULL AND COALESCE(status, 'visible') IN ('visible', 'approved')) WHERE id=%s",
                    (site_id, site_id),
                )
            conn.commit()
        finally:
            conn.close()
        return api_success({"id": comment_id}, status=201)

    @app.route("/api/comments/<int:comment_id>", methods=["DELETE"])
    @jwt_required()
    def v1_delete_comment(comment_id):
        user = current_user_row()
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT user_id FROM comments WHERE id=%s", (comment_id,))
                comment = cursor.fetchone()
                if not comment:
                    return api_error("comment not found", 404, 404)
                if comment.get("user_id") != user.get("id") and user.get("role") not in ("admin", "super_admin"):
                    return api_error("forbidden", 403, 403)
                cursor.execute("UPDATE comments SET status='deleted' WHERE id=%s", (comment_id,))
            conn.commit()
        finally:
            conn.close()
        return api_success()

    @app.route("/api/search", methods=["GET"])
    @jwt_required(optional=True)
    def v1_search():
        q = request.args.get("q", "")
        user = current_user_row() if get_jwt_identity() else None
        if q:
            record_behavior(user.get("id") if user else None, None, "search", q)
        return api_success({
            "items": query_sites(
                limit=request.args.get("limit", 30, type=int),
                keyword=q,
                tag=request.args.get("tag"),
                category_id=request.args.get("category_id"),
                is_free=request.args.get("is_free"),
                region=request.args.get("region"),
                sort=request.args.get("sort", "recommend"),
            ),
            "q": q,
        })

    @app.route("/api/search/suggest", methods=["GET"])
    def v1_search_suggest():
        q = request.args.get("q", "")
        return api_success([{"id": item["id"], "name": item["name"]} for item in (query_sites(limit=6, keyword=q) if q else [])])

    @app.route("/api/search/hot-keywords", methods=["GET"])
    def v1_hot_keywords():
        return api_success(["AI 工具", "编程开发", "设计资源", "数据分析", "办公效率"])

    @app.route("/api/admin/dashboard", methods=["GET"])
    @admin_required
    def v1_admin_dashboard():
        data = {
            "stats": {
                "users": 0,
                "new_users": 0,
                "sites": 0,
                "categories": 0,
                "tags": 0,
                "total_clicks": 0,
                "total_favorites": 0,
            },
            "click_ranking": [],
            "favorite_ranking": [],
            "occupation_distribution": [],
            "category_visit_ranking": [],
        }
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS count FROM users WHERE deleted_at IS NULL")
                data["stats"]["users"] = cursor.fetchone().get("count", 0)
                cursor.execute("SELECT COUNT(*) AS count FROM users WHERE DATE(created_at)=CURDATE() AND deleted_at IS NULL")
                data["stats"]["new_users"] = cursor.fetchone().get("count", 0)
                cursor.execute("SELECT COUNT(*) AS count FROM websites WHERE COALESCE(status, 'approved') != 'deleted'")
                data["stats"]["sites"] = cursor.fetchone().get("count", 0)
                cursor.execute("SELECT COUNT(*) AS count FROM categories WHERE COALESCE(status, 'active') != 'deleted'")
                data["stats"]["categories"] = cursor.fetchone().get("count", 0)
                cursor.execute("SELECT COUNT(*) AS count FROM tags")
                data["stats"]["tags"] = cursor.fetchone().get("count", 0)
                cursor.execute("SELECT COALESCE(SUM(COALESCE(click_count, clicks, 0)),0) AS total FROM websites")
                data["stats"]["total_clicks"] = cursor.fetchone().get("total", 0)
                cursor.execute("SELECT COALESCE(SUM(COALESCE(favorite_count,0)),0) AS total FROM websites")
                data["stats"]["total_favorites"] = cursor.fetchone().get("total", 0)
                cursor.execute("SELECT id, name, COALESCE(click_count, clicks, 0) AS click_count FROM websites WHERE COALESCE(status, 'approved') IN ('approved','active') ORDER BY COALESCE(click_count, clicks, 0) DESC LIMIT 8")
                data["click_ranking"] = cursor.fetchall()
                cursor.execute("SELECT id, name, COALESCE(favorite_count,0) AS favorite_count FROM websites WHERE COALESCE(status, 'approved') IN ('approved','active') ORDER BY COALESCE(favorite_count,0) DESC LIMIT 8")
                data["favorite_ranking"] = cursor.fetchall()
                cursor.execute("SELECT occupation, COUNT(*) AS count FROM user_profiles WHERE occupation IS NOT NULL AND occupation != '' GROUP BY occupation ORDER BY count DESC LIMIT 8")
                data["occupation_distribution"] = cursor.fetchall()
                cursor.execute(
                    """
                    SELECT c.id, c.name, COALESCE(SUM(COALESCE(w.click_count, w.clicks, 0)),0) AS visit_count
                    FROM categories c
                    LEFT JOIN websites w ON w.category_id = c.id
                    WHERE COALESCE(c.status, 'active') != 'deleted'
                    GROUP BY c.id, c.name
                    ORDER BY visit_count DESC
                    LIMIT 8
                    """
                )
                data["category_visit_ranking"] = cursor.fetchall()
        finally:
            conn.close()
        return api_success(data)

    @app.route("/api/admin/sites", methods=["GET", "POST"])
    @admin_required
    def v1_admin_sites():
        if request.method == "GET":
            return v1_sites()
        data = request.get_json(silent=True) or {}
        if not str(data.get("name") or "").strip():
            return api_error("网站名称不能为空")
        if not str(data.get("url") or "").strip():
            return api_error("网站 URL 不能为空")
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO websites (name,url,logo_url,summary,description,category_id,is_free,need_login,region,quality_score,recommend_level,status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (data.get("name"), data.get("url"), data.get("logo_url"), data.get("summary"), data.get("description"), data.get("category_id"), data.get("is_free", 1), data.get("need_login", 0), data.get("region", "domestic"), data.get("quality_score", 0), data.get("recommend_level", 0), data.get("status", "approved")))
                site_id = cursor.lastrowid
                sync_site_relations(
                    cursor,
                    site_id,
                    data.get("tags"),
                    data.get("occupations"),
                )
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
        if "name" in data and not str(data.get("name") or "").strip():
            return api_error("网站名称不能为空")
        if "url" in data and not str(data.get("url") or "").strip():
            return api_error("网站 URL 不能为空")
        allowed = ["name", "url", "logo_url", "summary", "description", "category_id", "is_free", "need_login", "region", "quality_score", "recommend_level", "status"]
        updates = [f"{key}=%s" for key in allowed if key in data]
        params = [data[key] for key in allowed if key in data]
        if not updates and "tags" not in data and "occupations" not in data:
            return api_success()
        if updates:
            params.append(site_id)
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                if updates:
                    cursor.execute(f"UPDATE websites SET {', '.join(updates)} WHERE id=%s", params)
                sync_site_relations(
                    cursor,
                    site_id,
                    data.get("tags") if "tags" in data else None,
                    data.get("occupations") if "occupations" in data else None,
                )
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
        if not str(data.get("name") or "").strip():
            return api_error("分类名称不能为空")
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO categories (name,parent_id,icon,sort_order,status) VALUES (%s,%s,%s,%s,%s)", (data.get("name"), data.get("parent_id"), data.get("icon"), data.get("sort_order", 0), data.get("status", "active")))
                category_id = cursor.lastrowid
            conn.commit()
        finally:
            conn.close()
        return api_success({"id": category_id}, status=201)

    @app.route("/api/admin/categories/<int:category_id>", methods=["PUT", "DELETE"])
    @admin_required
    def v1_admin_category_detail(category_id):
        data = request.get_json(silent=True) or {}
        if request.method == "PUT" and "name" in data and not str(data.get("name") or "").strip():
            return api_error("分类名称不能为空")
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                if request.method == "DELETE":
                    cursor.execute("UPDATE categories SET status='deleted' WHERE id=%s", (category_id,))
                else:
                    cursor.execute("UPDATE categories SET name=COALESCE(%s,name), parent_id=%s, icon=COALESCE(%s,icon), sort_order=COALESCE(%s,sort_order), status=COALESCE(%s,status) WHERE id=%s", (data.get("name"), data.get("parent_id"), data.get("icon"), data.get("sort_order"), data.get("status"), category_id))
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
        if not str(data.get("name") or "").strip():
            return api_error("标签名称不能为空")
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
        if request.method == "PUT" and "name" in data and not str(data.get("name") or "").strip():
            return api_error("标签名称不能为空")
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

    @app.route("/api/admin/users", methods=["GET"])
    @admin_required
    def v1_admin_users():
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT u.id, u.username, u.email, u.role, u.questionnaire_completed,
                           u.has_survey, u.status, u.created_at, p.occupation, p.skill_level,
                           p.interests, p.preferences, p.purposes
                    FROM users u
                    LEFT JOIN user_profiles p ON p.user_id=u.id
                    WHERE u.deleted_at IS NULL
                    ORDER BY u.created_at DESC
                    """
                )
                users = cursor.fetchall()
        finally:
            conn.close()
        for user in users:
            user["questionnaire"] = {
                "occupation": user.pop("occupation", "") or "",
                "skill_level": user.pop("skill_level", "") or "",
                "interests": parse_json_list(user.pop("interests", "")),
                "preferences": parse_json_list(user.pop("preferences", "")),
                "purposes": parse_json_list(user.pop("purposes", "")),
            }
            user["questionnaire_completed"] = bool(user.get("questionnaire_completed") or user.get("has_survey"))
        return api_success(users)

    @app.route("/api/admin/questionnaires", methods=["GET", "POST"])
    @admin_required
    def v1_admin_questionnaires():
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            questions = data.get("questions")
            if not isinstance(questions, list) or not questions:
                return api_error("问卷题目不能为空")
            for question in questions:
                if not str(question.get("key") or "").strip():
                    return api_error("问卷题目标识不能为空")
                if question.get("required", False) and not question.get("options"):
                    return api_error("必填题目必须配置选项")
            config = {
                "questions": questions,
                "occupation_tag_map": data.get("occupation_tag_map") or {},
            }
            save_json_setting("questionnaire_config", config)
            return api_success(config)

        config = load_json_setting("questionnaire_config", default_questionnaire_config())
        stats = {
            "total_profiles": 0,
            "completed_users": 0,
            "occupation_distribution": [],
        }
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS count FROM user_profiles")
                stats["total_profiles"] = cursor.fetchone().get("count", 0)
                cursor.execute(
                    "SELECT COUNT(*) AS count FROM users WHERE COALESCE(questionnaire_completed, has_survey, 0)=1"
                )
                stats["completed_users"] = cursor.fetchone().get("count", 0)
                cursor.execute(
                    """
                    SELECT occupation, COUNT(*) AS count
                    FROM user_profiles
                    WHERE occupation IS NOT NULL AND occupation != ''
                    GROUP BY occupation
                    ORDER BY count DESC
                    LIMIT 12
                    """
                )
                stats["occupation_distribution"] = cursor.fetchall()
        except Exception:
            pass
        finally:
            conn.close()
        return api_success({
            "config": questionnaire_options_from_config(config),
            "raw_config": config,
            "stats": stats,
        })

    @app.route("/api/admin/recommend-rules", methods=["GET", "POST"])
    @admin_required
    def v1_admin_recommend_rules():
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            rules = {
                "occupation_site_weights": data.get("occupation_site_weights") or {},
                "weights": data.get("weights") or default_recommend_rules()["weights"],
                "blacklist": data.get("blacklist") or default_recommend_rules()["blacklist"],
                "reason_templates": data.get("reason_templates") or {},
            }
            save_json_setting("recommend_rules", rules)
            return api_success(rules)
        rules = load_json_setting("recommend_rules", default_recommend_rules())
        return api_success(rules)

    @app.route("/api/admin/settings", methods=["GET", "POST"])
    @admin_required
    def v1_admin_settings():
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            settings = {**default_admin_settings(), **data}
            save_json_setting("admin_settings", settings)
            return api_success(settings)
        return api_success(load_json_setting("admin_settings", default_admin_settings()))

    @app.route("/api/admin/comments", methods=["GET"])
    @admin_required
    def v1_admin_comments():
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT cm.id, cm.content, cm.rating, cm.status, cm.created_at,
                           u.username, w.name AS site_name
                    FROM comments cm
                    LEFT JOIN users u ON u.id=cm.user_id
                    LEFT JOIN websites w ON w.id=cm.site_id
                    WHERE COALESCE(cm.status, 'visible') != 'deleted'
                    ORDER BY cm.created_at DESC
                    """
                )
                comments = cursor.fetchall()
        finally:
            conn.close()
        return api_success(comments)

    @app.route("/api/admin/comments/<int:comment_id>/review", methods=["POST"])
    @admin_required
    def v1_admin_review_comment(comment_id):
        action = (request.get_json(silent=True) or {}).get("action", "approve")
        status_map = {
            "approve": "visible",
            "approved": "visible",
            "reject": "rejected",
            "rejected": "rejected",
            "delete": "deleted",
            "violation": "violation",
        }
        next_status = status_map.get(action, "visible")
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE comments SET status=%s WHERE id=%s", (next_status, comment_id))
            conn.commit()
        finally:
            conn.close()
        return api_success({"status": next_status})

    @app.route("/api/admin/comments/<int:comment_id>", methods=["DELETE"])
    @admin_required
    def v1_admin_delete_comment(comment_id):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE comments SET status='deleted' WHERE id=%s", (comment_id,))
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
