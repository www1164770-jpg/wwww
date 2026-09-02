import json
import os
import random
import re
from uuid import uuid4
from time import perf_counter
from functools import wraps
from urllib.parse import urlsplit

import pymysql
from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ai_site_recommend_service import normalize_text, recommend_sites_for_query
from career_catalog import career_site_keywords
from career_recommend_service import build_career_recommendations
from occupation_utils import (
    OCCUPATION_LABELS,
    get_occupation_label,
    normalize_occupation,
)
from recommend_service import rank_sites
from questionnaire_v2 import (
    QUESTIONNAIRE_VERSION,
    build_recommendation_profile,
    get_config as get_questionnaire_v2_config,
    legacy_payload_to_answers,
    validate_answers as validate_questionnaire_v2_answers,
)
from questionnaire_v3 import (
    QUESTIONNAIRE_VERSION as QUESTIONNAIRE_V3_VERSION,
    build_recommendation_profile as build_questionnaire_v3_profile,
    get_config as get_questionnaire_v3_config,
    v2_defaults as questionnaire_v2_defaults,
    validate_answers as validate_questionnaire_v3_answers,
)


AI_SITE_CANDIDATE_LIMIT = 1000
SEARCH_CACHE_TTL_SECONDS = 5 * 60
SEARCH_DATA_VERSION = "site-search-v1"
RECOMMENDATION_ALGORITHM_VERSION = "phase1-v1"


def is_search_database_unavailable(error):
    """Distinguish connectivity/pool failures from broken search SQL."""
    if type(error).__name__ == "TooManyConnectionsError":
        return True
    if not isinstance(error, pymysql.err.OperationalError):
        return False
    error_code = error.args[0] if error.args else None
    return error_code in {
        1040, 1042, 1045, 1049, 1158, 1159, 1160, 1161,
        1203, 2002, 2003, 2006, 2013,
    }
PHASE_2_3_READINESS_THRESHOLDS = {
    "impressions": 1000,
    "clicks": 100,
    "favorites": 20,
    "repeat_visits": 10,
    "occupations": 3,
    "profile_combinations": 5,
    "profile_impressions": 50,
    "recommendation_batches": 20,
    "duplicate_impression_rate": 2,
}

# Phase 2.1: the event vocabulary is deliberately small and centralized.
BEHAVIOR_EVENT_TYPES = {"impression", "click", "favorite", "repeat_visit"}
BEHAVIOR_SOURCES = {
    "personalized_recommendation",
    "category",
    "search",
    "favorite",
    "history",
    "direct",
    "other",
}
BEHAVIOR_WEIGHTS = {"impression": 0, "click": 1, "favorite": 3, "repeat_visit": 2}
REPEAT_VISIT_WINDOW_MINUTES = 30
BEHAVIOR_LOOKBACK_DAYS = 90
SEARCH_SORTS = {"relevance", "recommend", "latest", "name"}
SEARCH_QUERY_ALIASES = {
    "b站": ("哔哩哔哩", "bilibili", "学习视频"),
    "zhihu": ("知乎",),
    "juejin": ("掘金",),
    "xiaohongshu": ("小红书", "灵感", "生活分享"),
    "代码托管": ("github", "gitlab", "gitee", "开源项目"),
    "前端框架": ("vue", "react", "angular", "svelte", "nuxt", "前端", "框架"),
    "论文写作": (
        "论文",
        "文献",
        "学术",
        "写作",
        "google scholar",
        "semantic scholar",
        "connected papers",
        "researchgate",
        "zotero",
        "overleaf",
        "scispace",
        "知网",
        "万方",
        "百度学术",
    ),
    "ppt": (
        "ppt",
        "演示",
        "幻灯片",
        "模板",
        "presentation",
        "powerpoint",
        "canva",
        "稿定设计",
        "创客贴",
        "beautiful.ai",
        "gamma",
        "slidesgo",
    ),
    "ai编程": ("ai", "编程", "cursor", "copilot", "codeium", "代码助手"),
    "图片素材": ("图片", "素材", "图库", "摄影", "icon"),
    "数据分析": ("数据分析", "python", "sql", "tableau", "power bi", "可视化"),
    "原型设计": ("原型", "figma", "axure", "墨刀", "processon"),
    "在线学习": ("学习", "课程", "coursera", "mooc", "慕课", "bilibili"),
}

SEARCH_SCENARIO_SITE_HINTS = {
    "论文写作": (
        "google scholar",
        "semantic scholar",
        "connected papers",
        "researchgate",
        "zotero",
        "overleaf",
        "scispace",
        "知网",
        "万方",
        "百度学术",
    ),
    "ppt": (
        "powerpoint",
        "canva",
        "稿定设计",
        "创客贴",
        "beautiful.ai",
        "gamma",
        "slidesgo",
    ),
    "ai编程": (
        "cursor",
        "github copilot",
        "copilot",
        "codeium",
        "windsurf",
        "claude code",
    ),
}


def normalize_search_query(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def search_term_groups(query):
    normalized = normalize_search_query(query)
    tokens = normalized.split(" ") if " " in normalized else [normalized]
    groups = []
    for token in (item for item in tokens if item):
        key = token.casefold()
        expanded = SEARCH_QUERY_ALIASES.get(key, ())
        groups.append(tuple(dict.fromkeys([token, *expanded])))
    return groups


def score_search_site(site, query, term_groups=None):
    normalized_query = normalize_search_query(query).casefold()
    groups = term_groups or search_term_groups(query)
    name = str(site.get("name") or "").casefold()
    summary = " ".join(
        str(site.get(field) or "") for field in ("summary", "description")
    ).casefold()
    category = " ".join(
        str(site.get(field) or "")
        for field in ("category_name", "category_code")
    ).casefold()
    tags = [str(item).casefold() for item in (site.get("tags") or [])]
    occupations = [
        str(item).casefold() for item in (site.get("occupations") or [])
    ]
    aliases = str(site.get("aliases") or "").casefold()
    use_cases = str(site.get("use_cases") or site.get("scenarios") or "").casefold()
    url = str(site.get("url") or "").casefold()
    score = 0
    matched_fields = set()

    if normalized_query and name == normalized_query:
        score += 100
        matched_fields.add("name")
    elif normalized_query and name.startswith(normalized_query):
        score += 90
        matched_fields.add("name")
    elif normalized_query and normalized_query in name:
        score += 80
        matched_fields.add("name")

    for group in groups:
        terms = [str(term).casefold() for term in group if str(term).strip()]
        if any(term in name for term in terms):
            score += 65
            matched_fields.add("name")
        if any(any(term == tag or term in tag for tag in tags) for term in terms):
            score += 75
            matched_fields.add("tags")
        if any(term in category for term in terms):
            score += 70
            matched_fields.add("category")
        if any(term in summary for term in terms):
            score += 55
            matched_fields.add("summary")
        if any(any(term in occupation for occupation in occupations) for term in terms):
            score += 50
            matched_fields.add("occupations")
        if any(term in aliases for term in terms):
            score += 45
            matched_fields.add("aliases")
        if any(term in use_cases for term in terms):
            score += 45
            matched_fields.add("useCases")
        if any(term in url for term in terms):
            score += 35
            matched_fields.add("url")

    score += min(int(site.get("recommend_level") or 0), 10)
    score += min(float(site.get("quality_score") or 0) / 20, 5)
    scenario_hints = SEARCH_SCENARIO_SITE_HINTS.get(normalized_query, ())
    if any(hint in name or hint in url for hint in scenario_hints):
        score += 85
        matched_fields.add("scenario")
    return round(score, 2), sorted(matched_fields)


def search_name_match_tier(site, query):
    normalized_query = normalize_search_query(query).casefold()
    name = str(site.get("name") or "").casefold().strip()
    if not normalized_query or not name:
        return 0
    if name == normalized_query:
        return 4
    if name.startswith(normalized_query):
        suffix = name[len(normalized_query) :].strip()
        if suffix in {".js", "js", ".com", "官网", "官方", "官方文档"}:
            return 3
        return 2
    if normalized_query in name:
        return 1
    return 0


def rank_search_sites(items, query, sort="relevance"):
    term_groups = search_term_groups(query)
    ranked = []
    for raw_site in items:
        site = dict(raw_site)
        score, matched_fields = score_search_site(site, query, term_groups)
        site["score"] = score
        site["matchedFields"] = matched_fields
        ranked.append(site)

    if sort == "name":
        ranked.sort(key=lambda item: str(item.get("name") or "").casefold())
    elif sort == "latest":
        ranked.sort(
            key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""),
            reverse=True,
        )
    elif sort == "recommend":
        ranked.sort(
            key=lambda item: (
                item.get("recommend_level") or 0,
                item.get("quality_score") or 0,
                item.get("favorite_count") or 0,
                item.get("click_count") or 0,
                item.get("score") or 0,
            ),
            reverse=True,
        )
    else:
        ranked.sort(
            key=lambda item: (
                search_name_match_tier(item, query),
                item.get("score") or 0,
                item.get("recommend_level") or 0,
                item.get("quality_score") or 0,
                item.get("click_count") or 0,
            ),
            reverse=True,
        )
    return ranked


def register_v1_routes(app, get_db_connection):
    columns_cache = {}
    search_cache = {}

    CATEGORY_CODE_ALIASES = {
        "常用推荐": "common",
        "开发社区": "community",
        "摸鱼娱乐": "entertainment",
        "实用工具": "productivity",
        "AI 神器": "ai",
        "框架文档": "framework_docs",
        "UI 组件库": "ui_components",
        "可视化/3D": "visualization_3d",
        "工具/构建": "build_tools",
        "灵感采集": "inspiration",
        "素材资源": "assets",
        "在线工具": "online_tools",
        "字体/配色": "fonts_colors",
        "原型设计": "prototype",
        "文档办公": "office",
        "数据分析": "data_analysis",
        "竞品调研": "competitive_research",
    }

    def category_code_for_name(name):
        value = str(name or "").strip()
        if value in CATEGORY_CODE_ALIASES:
            return CATEGORY_CODE_ALIASES[value]
        return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "category"

    def api_success(data=None, msg="success", status=200):
        return jsonify({
            "success": True,
            "code": status,
            "legacy_code": 0,
            "message": msg,
            "msg": msg,
            "data": data if data is not None else {},
        }), status

    def api_error(msg, code=400, status=400, data=None):
        return jsonify({
            "success": False,
            "code": code,
            "error_code": code if isinstance(code, str) else None,
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
        conn = None
        try:
            conn = get_db_connection()
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
        except Exception:
            safe_rollback(conn)
            raise
        finally:
            safe_close(conn)

    behavior_schema_ready = False
    observation_snapshot_schema_ready = False

    def ensure_behavior_events_table(cursor=None):
        """Create the Phase 2 event table lazily for existing installations."""
        nonlocal behavior_schema_ready
        if behavior_schema_ready:
            return
        owns_connection = cursor is None
        conn = None
        try:
            if owns_connection:
                conn = get_db_connection()
                cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_behavior_events (
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  user_id INT NULL,
                  website_id INT NOT NULL,
                  event_type VARCHAR(32) NOT NULL,
                  source VARCHAR(64) NOT NULL DEFAULT 'other',
                  recommendation_batch_id VARCHAR(128) NULL,
                  questionnaire_version VARCHAR(64) NULL,
                  profile_version VARCHAR(64) NULL,
                  session_id VARCHAR(128) NULL,
                  metadata_json JSON NULL,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  INDEX idx_behavior_events_user_created (user_id, created_at),
                  INDEX idx_behavior_events_user_site_created (user_id, website_id, created_at),
                  INDEX idx_behavior_events_type_created (event_type, created_at),
                  INDEX idx_behavior_events_site_type (website_id, event_type),
                  INDEX idx_behavior_events_batch (recommendation_batch_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            if owns_connection:
                conn.commit()
            behavior_schema_ready = True
        finally:
            if owns_connection:
                safe_close(conn)

    def ensure_observation_snapshots_table(cursor=None):
        """Create immutable, aggregate-only observation snapshots lazily."""
        nonlocal observation_snapshot_schema_ready
        if observation_snapshot_schema_ready:
            return
        owns_connection = cursor is None
        conn = None
        try:
            if owns_connection:
                conn = get_db_connection()
                cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS recommendation_observation_snapshots (
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  snapshot_id VARCHAR(64) NOT NULL UNIQUE,
                  algorithm_version VARCHAR(64) NOT NULL,
                  lookback_days VARCHAR(16) NOT NULL,
                  exclude_test_users TINYINT(1) NOT NULL DEFAULT 1,
                  captured_by_user_id INT NULL,
                  summary_json JSON NOT NULL,
                  data_quality_json JSON NOT NULL,
                  readiness_json JSON NOT NULL,
                  match_score_buckets_json JSON NOT NULL,
                  primary_need_metrics_json JSON NOT NULL,
                  tag_metrics_json JSON NOT NULL,
                  personalization_metrics_json JSON NOT NULL,
                  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  INDEX idx_observation_snapshots_created (created_at),
                  INDEX idx_observation_snapshots_algorithm_created (algorithm_version, created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            if owns_connection:
                conn.commit()
            observation_snapshot_schema_ready = True
        finally:
            if owns_connection:
                safe_close(conn)

    def behavior_context(payload):
        """Return only safe, bounded recommendation context fields."""
        metadata = payload.get("metadata_json", payload.get("metadata"))
        if not isinstance(metadata, dict):
            metadata = {}
        # Do not persist raw form fields, credentials, or arbitrary URLs.
        safe_metadata = {}
        for key in ("display_batch_index", "candidate_pool_id", "position", "surface", "personalization_type", "match_score", "algorithm_version", "profile_schema_version"):
            value = metadata.get(key)
            if value is not None:
                safe_metadata[key] = str(value)[:128]
        safe_metadata.setdefault("algorithm_version", RECOMMENDATION_ALGORITHM_VERSION)
        return {
            "recommendation_batch_id": str(payload.get("recommendation_batch_id") or "").strip()[:128] or None,
            "questionnaire_version": str(payload.get("questionnaire_version") or "").strip()[:64] or None,
            "profile_version": str(payload.get("profile_version") or "").strip()[:64] or None,
            "session_id": str(payload.get("session_id") or "").strip()[:128] or None,
            "metadata_json": json.dumps(safe_metadata, ensure_ascii=False) if safe_metadata else None,
        }

    def insert_behavior_event(user_id, website_id, event_type, source, context, cursor, *, dedupe=False):
        """Insert one event and return whether a row was written."""
        if dedupe:
            cursor.execute(
                """
                SELECT id FROM user_behavior_events
                WHERE user_id=%s AND website_id=%s AND event_type=%s
                  AND COALESCE(source,'')=COALESCE(%s,'')
                  AND COALESCE(recommendation_batch_id,'')=COALESCE(%s,'')
                  AND COALESCE(session_id,'')=COALESCE(%s,'')
                LIMIT 1
                """,
                (user_id, website_id, event_type, source,
                 context.get("recommendation_batch_id"), context.get("session_id")),
            )
            if cursor.fetchone():
                return False
        cursor.execute(
            """
            INSERT INTO user_behavior_events
              (user_id, website_id, event_type, source, recommendation_batch_id,
               questionnaire_version, profile_version, session_id, metadata_json)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (user_id, website_id, event_type, source,
             context.get("recommendation_batch_id"), context.get("questionnaire_version"),
             context.get("profile_version"), context.get("session_id"),
             context.get("metadata_json")),
        )
        return True

    def record_unified_behavior(user_id, website_id, event_type, source="other", payload=None, *, dedupe=False):
        if not user_id or not website_id or event_type not in BEHAVIOR_EVENT_TYPES:
            return False
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                ensure_behavior_events_table(cursor)
                wrote = insert_behavior_event(
                    user_id, website_id, event_type, source, behavior_context(payload or {}), cursor,
                    dedupe=dedupe,
                )
            conn.commit()
            return wrote
        except Exception:
            safe_rollback(conn)
            app.logger.exception("behavior event write failed user_id=%s website_id=%s event=%s", user_id, website_id, event_type)
            return False
        finally:
            safe_close(conn)

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

    def log_favorite_timing(action, timing, site_id=None):
        def elapsed(stage):
            started = timing.get(f"{stage}_started")
            finished = timing.get(f"{stage}_finished")
            if started is None or finished is None:
                return 0.0
            return round((finished - started) * 1000, 2)

        app.logger.info(
            "favorite_%s_timing site_id=%s auth_ms=%.2f schema_ms=%.2f "
            "site_lookup_ms=%.2f favorite_lookup_ms=%.2f commit_ms=%.2f "
            "behavior_ms=%.2f total_ms=%.2f",
            action,
            site_id or "",
            elapsed("auth"),
            elapsed("schema"),
            elapsed("site_lookup"),
            elapsed("favorite_lookup"),
            elapsed("commit"),
            elapsed("behavior"),
            round((perf_counter() - timing["started"]) * 1000, 2),
        )

    def table_columns(table, *, strict=False):
        if table in columns_cache:
            return columns_cache[table]
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM {table}")
                columns_cache[table] = {row["Field"] for row in cursor.fetchall()}
        except Exception:
            safe_rollback(conn)
            # A transient database outage is not evidence that a table has no
            # columns. Never poison the process-wide schema cache with a
            # fabricated empty schema; core search callers also need the real
            # exception so they can return an explicit service error.
            if strict:
                raise
            return set()
        finally:
            safe_close(conn)
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

    def ensure_user_questionnaire_responses_table(cursor):
        """Keep V2 storage available on installations pending the SQL migration."""
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_questionnaire_responses (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
              user_id INT NOT NULL,
              questionnaire_version INT NOT NULL,
              occupation VARCHAR(64) NOT NULL,
              answers_json LONGTEXT NOT NULL,
              profile_json LONGTEXT NOT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              UNIQUE KEY uq_user_questionnaire_version (user_id, questionnaire_version),
              CONSTRAINT fk_user_questionnaire_responses_user
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

    def load_questionnaire_v2_response(cursor, user_id):
        return load_questionnaire_response(cursor, user_id, QUESTIONNAIRE_VERSION)

    def load_questionnaire_v3_response(cursor, user_id):
        return load_questionnaire_response(cursor, user_id, QUESTIONNAIRE_V3_VERSION)

    def load_questionnaire_response(cursor, user_id, version):
        try:
            ensure_user_questionnaire_responses_table(cursor)
            cursor.execute(
                "SELECT questionnaire_version, occupation, answers_json, profile_json, updated_at "
                "FROM user_questionnaire_responses "
                "WHERE user_id=%s AND questionnaire_version=%s",
                (user_id, version),
            )
            row = cursor.fetchone() or {}
            if not row:
                return {}
            return {
                "version": row.get("questionnaire_version"),
                "occupation": row.get("occupation"),
                "answers": json.loads(row.get("answers_json") or "{}"),
                "profile": json.loads(row.get("profile_json") or "{}"),
                "updated_at": row.get("updated_at"),
            }
        except Exception:
            return {}

    def default_questionnaire_config():
        return {
            "questions": [
                {
                    "key": "occupation",
                    "label": "职业",
                    "required": True,
                    "options": list(OCCUPATION_LABELS),
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
                "frontend_developer": ["programming", "AI tools", "project_development"],
                "backend_developer": ["programming", "API", "database"],
                "ai_app_developer": ["AI tools", "programming", "project_development"],
                "llm_engineer": ["AI tools", "model", "programming"],
                "product_manager": ["product management", "startup resources", "data analysis"],
                "ui_ux_designer": ["design resources", "assets", "AI tools"],
                "data_analyst": ["data analysis", "programming", "AI tools"],
                "operations": ["growth", "content_creation", "office efficiency"],
                "technical_operations": ["operations", "monitoring", "automation"],
                "teacher": ["learning platforms", "AI tools", "content_creation"],
                "student": ["learning platforms", "programming", "AI tools"],
                "creator": ["content_creation", "assets", "AI tools"],
                "other": ["AI tools", "office efficiency"],
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

        normalized_occupations = list(dict.fromkeys(
            normalized
            for item in options("occupation")
            if (normalized := normalize_occupation(item))
        ))
        raw_tag_map = config.get("occupation_tag_map") or fallback["occupation_tag_map"]
        normalized_tag_map = {}
        for occupation, tags in raw_tag_map.items():
            canonical = normalize_occupation(occupation)
            if canonical:
                normalized_tag_map.setdefault(canonical, tags)

        return {
            "occupations": normalized_occupations or list(OCCUPATION_LABELS),
            "purposes": options("purposes"),
            "interests": options("interests"),
            "skill_levels": options("skill_level"),
            "preferences": options("preferences"),
            "questions": questions or fallback["questions"],
            "occupation_tag_map": normalized_tag_map,
        }

    def default_recommend_rules():
        return {
            "occupation_site_weights": {
                "frontend_developer": ["frontend", "Vue", "React", "JavaScript", "code"],
                "backend_developer": ["backend", "Python", "API", "database", "code"],
                "ai_app_developer": ["AI", "API", "agent", "application", "code"],
                "llm_engineer": ["LLM", "model", "prompt", "RAG", "AI"],
                "product_manager": ["product", "prototype", "analytics", "collaboration"],
                "ui_ux_designer": ["design", "ui", "ux", "assets", "prototype"],
                "data_analyst": ["data", "analytics", "SQL", "Python", "visualization"],
                "operations": ["growth", "marketing", "content", "office"],
                "technical_operations": ["monitoring", "automation", "deployment", "operations"],
                "teacher": ["learning", "writing", "knowledge", "course"],
                "student": ["learning", "docs", "AI", "programming"],
                "creator": ["content", "video", "writing", "image", "AIGC"],
                "other": ["AI", "office", "learning", "efficiency"],
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
            "site_name": "知航屿",
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
        category_name = row.get("category_name") or ""
        category_code = row.get("category_code") or category_code_for_name(category_name)
        return {
            "id": row.get("id"),
            "name": row.get("name"),
            "url": row.get("url"),
            "logo_url": row.get("logo_url"),
            "logoUrl": row.get("logo_url"),
            "summary": summary,
            "description": row.get("description") or summary,
            "category_id": row.get("category_id"),
            "category_name": category_name,
            "categoryName": category_name,
            "category_code": category_code,
            "categoryCode": category_code,
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
        "AI 应用开发": ["AI", "AIGC", "智能体", "API", "应用开发", "代码", "编程"],
        "大模型工程师": ["大模型", "LLM", "模型", "RAG", "向量", "Prompt", "AI", "Python"],
        "产品经理": ["产品", "原型", "需求", "文档", "流程图", "数据分析", "AI"],
        "UI/UX 设计师": ["设计", "UI", "UX", "Figma", "图标", "图片", "绘图", "AI"],
        "运营": ["运营", "文案", "内容", "数据分析", "增长", "办公", "AI"],
        "技术运营": ["技术运营", "监控", "自动化", "部署", "数据分析", "AI"],
        "教师": ["教学", "课件", "PPT", "学习", "题库", "教育", "AI"],
        "自媒体创作者": ["写作", "视频", "剪辑", "图片", "内容创作", "AIGC", "AI"],
        "数据分析师": ["数据分析", "可视化", "Python", "SQL", "报表", "AI"],
        "其他": ["AI", "效率", "学习", "办公", "写作"],
    }
    career_preferred_names = {
        "学生": ["ChatGPT", "Kimi", "Perplexity", "Poe", "Notion", "ProcessOn", "Bilibili", "Coursera"],
        "前端开发": ["GitHub", "MDN Web Docs", "Vue 官方文档", "Stack Overflow", "Vercel", "CodePen", "ChatGPT"],
        "后端开发": ["GitHub", "Flask 官方文档", "Postman", "Stack Overflow", "Docker", "LeetCode", "ChatGPT"],
        "AI 应用开发": ["OpenAI", "Hugging Face", "GitHub", "LangChain", "Vercel", "ChatGPT"],
        "大模型工程师": ["Hugging Face", "GitHub", "Kaggle", "Jupyter", "OpenAI", "ChatGPT"],
        "产品经理": ["Notion", "ProcessOn", "飞书", "Figma", "Trello", "ChatGPT"],
        "UI/UX 设计师": ["Figma", "Canva", "Iconfont", "Unsplash", "Midjourney", "Dribbble", "Runway"],
        "运营": ["ChatGPT", "Canva", "Notion", "飞书", "ProcessOn", "豆包"],
        "技术运营": ["GitHub", "Docker", "Grafana", "Postman", "Notion", "ChatGPT"],
        "教师": ["ChatGPT", "Kimi", "Canva", "ProcessOn", "Bilibili", "Coursera"],
        "自媒体创作者": ["ChatGPT", "Canva", "Runway", "Midjourney", "豆包", "Bilibili"],
        "数据分析师": ["Kaggle", "Tableau", "Power BI", "Jupyter", "Python", "SQL", "ChatGPT"],
        "其他": ["ChatGPT", "Claude", "Gemini", "Notion", "Figma", "Canva"],
    }
    career_reasons = {
        "学生": "适合学习、论文写作和知识整理。",
        "前端开发": "适合前端开发、代码学习和项目构建。",
        "后端开发": "适合后端开发、接口调试和代码辅助。",
        "AI 应用开发": "适合 AI 应用搭建、接口集成和智能体开发。",
        "大模型工程师": "适合模型研发、RAG 构建和大模型工程实践。",
        "产品经理": "适合需求分析、产品文档和流程梳理。",
        "UI/UX 设计师": "适合界面设计、素材查找和创意生成。",
        "运营": "适合内容运营、文案生成和数据分析。",
        "技术运营": "适合监控分析、流程自动化和技术支持。",
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
        raw_occupation = str(occupation or "").strip()
        canonical_occupation = normalize_occupation(raw_occupation)
        occupation_label = get_occupation_label(canonical_occupation)
        exclude_ids = exclude_ids or []
        rules = rules or {}
        if not canonical_occupation or not occupation_label:
            return []

        def occupation_rule(mapping):
            for key in (canonical_occupation, occupation_label, raw_occupation):
                if key in mapping:
                    return mapping[key]
            for key, value in mapping.items():
                if normalize_occupation(key) == canonical_occupation:
                    return value
            return None

        configured_keywords = occupation_rule(
            rules.get("occupation_site_weights") or {}
        )
        keywords = configured_keywords or career_site_keywords(canonical_occupation) or career_ai_keywords.get(occupation_label, fallback_keywords)
        preferred_names = career_preferred_names.get(occupation_label, [])
        resource_keywords = list(dict.fromkeys(ai_keywords + fallback_keywords + keywords))
        reason = occupation_rule(
            rules.get("reason_templates") or {}
        ) or career_reasons.get(occupation_label, "根据职业画像与当前任务匹配推荐")
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
            site_occupation_values = site.get("occupations") or []
            exact_occupation = occupation_label in site_occupation_values or any(
                normalize_occupation(value) == canonical_occupation
                for value in site_occupation_values
            )
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
        has_click_metric = "click_count" in website_columns or "clicks" in website_columns
        if "click_count" in website_columns and "clicks" in website_columns:
            click_expr = "COALESCE(w.click_count, w.clicks, 0)"
        elif "click_count" in website_columns:
            click_expr = "COALESCE(w.click_count, 0)"
        elif "clicks" in website_columns:
            click_expr = "COALESCE(w.clicks, 0)"
        else:
            click_expr = None
        latest_expr = (
            "w.created_at DESC"
            if "created_at" in website_columns
            else "w.id DESC"
        )
        quality_value = (
            "COALESCE(w.quality_score, 0)"
            if "quality_score" in website_columns
            else None
        )
        favorite_value = (
            "COALESCE(w.favorite_count, 0)"
            if "favorite_count" in website_columns
            else None
        )
        rating_value = (
            "COALESCE(w.rating_avg, 0)"
            if "rating_avg" in website_columns
            else None
        )
        # 热门排序
        hot_order_terms = []
        if has_click_metric:
            hot_order_terms.append(f"{click_expr} DESC")
        if favorite_value:
            hot_order_terms.append(f"{favorite_value} DESC")
        if rating_value:
            hot_order_terms.append(f"{rating_value} DESC")
        if quality_value:
            hot_order_terms.append(f"{quality_value} DESC")
        # 始终提供稳定兜底排序
        hot_order_terms.append("w.id DESC")
        # 推荐排序
        recommend_order_terms = []
        if "recommend_level" in website_columns:
            recommend_order_terms.append(
                "COALESCE(w.recommend_level, 0) DESC"
            )
        if quality_value:
            recommend_order_terms.append(
                f"{quality_value} DESC"
            )
        if has_click_metric:
            recommend_order_terms.append(
                f"{click_expr} DESC"
            )
        # 防止 ORDER BY 0，同时保证分页顺序稳定
        recommend_order_terms.append("w.id DESC")
        # 评分排序
        if rating_value:
            rating_order_sql = f"{rating_value} DESC, w.id DESC"
        elif quality_value:
            rating_order_sql = f"{quality_value} DESC, w.id DESC"
        elif has_click_metric:
            rating_order_sql = f"{click_expr} DESC, w.id DESC"
        else:
            rating_order_sql = "w.id DESC"
        order_map = {
            "hot": ", ".join(hot_order_terms),
            "latest": latest_expr,
            "rating": rating_order_sql,
            "recommend": ", ".join(recommend_order_terms),
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

    def count_sites(category_id=None, keyword=None, tag=None, is_free=None, region=None):
        """Count the same filtered site set used by /api/sites without loading cards."""
        website_columns = table_columns("websites")
        category_columns = table_columns("categories")
        where = []
        params = []
        joins = "LEFT JOIN categories c ON c.id = w.category_id"
        if "status" in website_columns:
            where.append("COALESCE(w.status, 'approved') IN ('approved', 'active')")
        if category_id:
            category_value = str(category_id).strip()
            if category_value.isdigit():
                if "parent_id" in category_columns:
                    where.append("(w.category_id=%s OR c.parent_id=%s)")
                    params.extend([int(category_value), int(category_value)])
                else:
                    where.append("w.category_id=%s")
                    params.append(int(category_value))
            elif "name" in category_columns:
                if "parent_id" in category_columns:
                    joins += " LEFT JOIN categories pc ON pc.id=c.parent_id"
                    where.append("(c.name=%s OR pc.name=%s)")
                    params.extend([category_value, category_value])
                else:
                    where.append("c.name=%s")
                    params.append(category_value)
        if keyword:
            search_fields = []
            for column in ("name", "summary", "description", "url"):
                if column in website_columns:
                    search_fields.append(f"w.{column} LIKE %s")
            if "name" in category_columns:
                search_fields.append("c.name LIKE %s")
            if table_columns("site_tags"):
                joins += " LEFT JOIN site_tags st_search ON st_search.site_id=w.id LEFT JOIN tags t_search ON t_search.id=st_search.tag_id"
                search_fields.append("t_search.name LIKE %s")
            if search_fields:
                where.append(f"({' OR '.join(search_fields)})")
                params.extend([f"%{keyword}%"] * len(search_fields))
        if tag:
            joins += " LEFT JOIN site_tags st_filter ON st_filter.site_id=w.id LEFT JOIN tags t_filter ON t_filter.id=st_filter.tag_id"
            where.append("t_filter.name=%s")
            params.append(tag)
        if "is_free" in website_columns and is_free in ("free", "1", "true", True):
            where.append("COALESCE(w.is_free, 1)=1")
        elif "is_free" in website_columns and is_free in ("paid", "0", "false", False):
            where.append("COALESCE(w.is_free, 1)=0")
        if region and "region" in website_columns:
            where.append("w.region=%s")
            params.append(region)
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT COUNT(DISTINCT w.id) AS total FROM websites w {joins} {where_sql}",
                    params,
                )
                row = cursor.fetchone() or {}
                return int(row.get("total") or 0)
        except Exception:
            return 0
        finally:
            conn.close()

    def resolve_search_category(category):
        value = normalize_search_query(category)
        if not value:
            return None
        category_columns = table_columns("categories", strict=True)
        code_expr = "code" if "code" in category_columns else "NULL AS code"
        status_where = (
            "AND COALESCE(status, 'active')='active'"
            if "status" in category_columns
            else ""
        )
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                if value.isdigit():
                    cursor.execute(
                        f"SELECT id, name, {code_expr} FROM categories WHERE id=%s {status_where} LIMIT 1",
                        (int(value),),
                    )
                elif "code" in category_columns:
                    cursor.execute(
                        f"SELECT id, name, {code_expr} FROM categories "
                        f"WHERE (LOWER(code)=LOWER(%s) OR LOWER(name)=LOWER(%s)) {status_where} LIMIT 1",
                        (value, value),
                    )
                else:
                    cursor.execute(
                        f"SELECT id, name, {code_expr} FROM categories "
                        f"WHERE LOWER(name)=LOWER(%s) {status_where} LIMIT 1",
                        (value,),
                    )
                return cursor.fetchone()
        finally:
            conn.close()

    def query_search_candidates(query, category_id=None, match_all=True):
        website_columns = table_columns("websites", strict=True)
        category_columns = table_columns("categories", strict=True)
        has_tags = bool(table_columns("site_tags")) and bool(table_columns("tags"))
        has_occupations = bool(table_columns("site_occupations"))
        summary_expr = "COALESCE(w.summary, '')" if "summary" in website_columns else "''"
        description_expr = (
            "COALESCE(w.description, '')" if "description" in website_columns else "''"
        )
        alias_expr = "COALESCE(w.aliases, '')" if "aliases" in website_columns else "''"
        use_case_expr = (
            "COALESCE(w.use_cases, '')" if "use_cases" in website_columns else "''"
        )
        category_code_expr = (
            "MAX(c.code)" if "code" in category_columns else "NULL"
        )
        tag_join = (
            "LEFT JOIN site_tags st ON st.site_id=w.id "
            "LEFT JOIN tags t ON t.id=st.tag_id"
            if has_tags
            else ""
        )
        occupation_join = (
            "LEFT JOIN site_occupations so ON so.site_id=w.id"
            if has_occupations
            else ""
        )
        tag_aggregate = (
            "GROUP_CONCAT(DISTINCT t.name ORDER BY t.name SEPARATOR '|||')"
            if has_tags
            else "''"
        )
        occupation_aggregate = (
            "GROUP_CONCAT(DISTINCT so.occupation ORDER BY so.occupation SEPARATOR '|||')"
            if has_occupations
            else "''"
        )
        search_text = (
            "LOWER(CONCAT_WS(' ', COALESCE(w.name,''), "
            f"{summary_expr}, {description_expr}, COALESCE(w.url,''), "
            "COALESCE(MAX(c.name),''), "
            f"COALESCE({category_code_expr},''), {alias_expr}, {use_case_expr}, "
            f"COALESCE({tag_aggregate},''), COALESCE({occupation_aggregate},'')))"
        )
        where = []
        params = []
        if "enabled" in website_columns:
            where.append("COALESCE(w.enabled, 1)=1")
        if "status" in website_columns:
            where.append("COALESCE(w.status, 'approved') IN ('approved', 'active')")
        if category_id:
            where.append("w.category_id=%s")
            params.append(int(category_id))

        group_clauses = []
        for group in search_term_groups(query):
            alternatives = []
            for term in group:
                alternatives.append(f"{search_text} LIKE LOWER(%s)")
                params.append(f"%{term}%")
            if alternatives:
                group_clauses.append(f"({' OR '.join(alternatives)})")
        if not group_clauses:
            return []
        having_joiner = " AND " if match_all else " OR "
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT w.*, MAX(c.name) AS category_name,
                           {category_code_expr} AS category_code,
                           {tag_aggregate} AS tags_text,
                           {occupation_aggregate} AS occupations_text,
                           {alias_expr} AS aliases,
                           {use_case_expr} AS use_cases
                    FROM websites w
                    LEFT JOIN categories c ON c.id=w.category_id
                    {tag_join}
                    {occupation_join}
                    {where_sql}
                    GROUP BY w.id
                    HAVING {having_joiner.join(group_clauses)}
                    """,
                    params,
                )
                rows = cursor.fetchall() or []
        finally:
            conn.close()

        candidates = []
        seen_urls = set()
        for row in rows:
            raw_url = str(row.get("url") or "").strip()
            try:
                parsed_url = urlsplit(
                    raw_url if "://" in raw_url else f"https://{raw_url}"
                )
                url_key = (
                    f"{(parsed_url.hostname or '').lower().removeprefix('www.')}"
                    f"{parsed_url.path.rstrip('/') or '/'}"
                )
            except ValueError:
                url_key = raw_url.rstrip("/").casefold()
            if not url_key or url_key in seen_urls:
                continue
            seen_urls.add(url_key)
            tags = [item for item in str(row.get("tags_text") or "").split("|||") if item]
            occupations = [
                item
                for item in str(row.get("occupations_text") or "").split("|||")
                if item
            ]
            site = normalize_site(row, tags, occupations)
            site["aliases"] = row.get("aliases") or ""
            site["use_cases"] = row.get("use_cases") or ""
            site["updated_at"] = row.get("updated_at")
            candidates.append(site)
        return candidates

    def cached_site_search(query, category, sort):
        category_row = resolve_search_category(category) if category else None
        if category and not category_row:
            raise ValueError("INVALID_CATEGORY")
        cache_key = (
            query.casefold(),
            int(category_row["id"]) if category_row else None,
            sort,
            SEARCH_DATA_VERSION,
        )
        cached = search_cache.get(cache_key)
        now = perf_counter()
        if cached and now - cached["saved_at"] < SEARCH_CACHE_TTL_SECONDS:
            return cached["items"], category_row, cached["relaxed"], True

        items = query_search_candidates(
            query,
            category_id=category_row["id"] if category_row else None,
            match_all=True,
        )
        relaxed = False
        if not items and len(search_term_groups(query)) > 1:
            items = query_search_candidates(
                query,
                category_id=category_row["id"] if category_row else None,
                match_all=False,
            )
            relaxed = True
        ranked = rank_search_sites(items, query, sort)
        search_cache[cache_key] = {
            "items": ranked,
            "saved_at": now,
            "relaxed": relaxed,
        }
        if len(search_cache) > 100:
            oldest_key = min(
                search_cache,
                key=lambda key: search_cache[key]["saved_at"],
            )
            search_cache.pop(oldest_key, None)
        return ranked, category_row, relaxed, False

    def search_category_suggestions(query, limit=2):
        category_columns = table_columns("categories", strict=True)
        code_expr = "code" if "code" in category_columns else "NULL AS code"
        order_sql = "sort_order, id" if "sort_order" in category_columns else "id"
        status_where = (
            "AND COALESCE(status, 'active')='active'"
            if "status" in category_columns
            else ""
        )
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT id, name, {code_expr} FROM categories "
                    f"WHERE (LOWER(name) LIKE LOWER(%s) "
                    + ("OR LOWER(code) LIKE LOWER(%s)" if "code" in category_columns else "")
                    + f") {status_where} ORDER BY {order_sql} LIMIT %s",
                    ((f"%{query}%", f"%{query}%", limit) if "code" in category_columns else (f"%{query}%", limit)),
                )
                return cursor.fetchall() or []
        finally:
            conn.close()

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
        # V3 is a graph rather than a fixed list so clients follow branches
        # without occupation-specific UI code. V2 remains stored and readable.
        config = get_questionnaire_v3_config()
        user = current_user_row()
        if user:
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    response_v3 = load_questionnaire_v3_response(cursor, user["id"])
                    response_v2 = load_questionnaire_v2_response(cursor, user["id"])
                if not response_v3 and response_v2.get("answers"):
                    config["initial_answers"] = questionnaire_v2_defaults(response_v2["answers"])
            finally:
                conn.close()
        return api_success(config)

    @app.route("/api/questionnaire/status", methods=["GET"])
    @jwt_required()
    def v1_questionnaire_status():
        """Keep legacy completion compatible while publishing V3 as current."""
        user = current_user_row()
        if not user:
            return api_error("user not found", 404, 404)
        conn = get_db_connection()
        response_v2 = {}
        response_v3 = {}
        try:
            with conn.cursor() as cursor:
                response_v2 = load_questionnaire_v2_response(cursor, user["id"])
                response_v3 = load_questionnaire_v3_response(cursor, user["id"])
        finally:
            conn.close()
        # Product policy: a legacy completed user is not forced through V3 on
        # login. V3 is entered through the explicit update-preferences flow.
        completed = bool(response_v3.get("version") == QUESTIONNAIRE_V3_VERSION or response_v2.get("version") == QUESTIONNAIRE_VERSION)
        latest_version = response_v3.get("version") or response_v2.get("version")
        if not completed and (user.get("questionnaire_completed") or user.get("has_survey")):
            completed = True
            latest_version = latest_version or 1
        return api_success({
            "completed": completed,
            "questionnaire_version": QUESTIONNAIRE_V3_VERSION,
            "latest_completed_version": latest_version,
        })

    @app.route("/api/questionnaire/submit", methods=["POST"])
    @jwt_required()
    def v1_submit_questionnaire():
        user = current_user_row()
        if not user:
            return api_error("user not found", 404, 404)
        data = request.get_json(silent=True) or {}
        try:
            if data.get("version") not in (None, QUESTIONNAIRE_V3_VERSION, str(QUESTIONNAIRE_V3_VERSION)):
                return api_error("questionnaire version is not supported", 400, 400)
            answers, _path = validate_questionnaire_v3_answers(data.get("answers") or {})
        except ValueError as exc:
            return api_error(str(exc), 400, 400)
        profile_v2 = build_questionnaire_v3_profile(answers)
        career_occupation = profile_v2["career_code"]
        interests = profile_v2["tags"]
        preferences = [profile_v2["priority"]] if profile_v2.get("priority") else []
        purposes = [profile_v2["primary_need"]] if profile_v2.get("primary_need") else []
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                ensure_user_questionnaire_responses_table(cursor)
                cursor.execute(
                    """
                    INSERT INTO user_questionnaire_responses
                      (user_id, questionnaire_version, occupation, answers_json, profile_json)
                    VALUES (%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE questionnaire_version=VALUES(questionnaire_version),
                      occupation=VALUES(occupation), answers_json=VALUES(answers_json),
                      profile_json=VALUES(profile_json)
                    """,
                    (
                        user["id"], QUESTIONNAIRE_V3_VERSION, answers["occupation"],
                        json.dumps(answers, ensure_ascii=False),
                        json.dumps(profile_v2, ensure_ascii=False),
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO user_profiles (user_id, occupation, skill_level, interests, preferences, purposes)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE occupation=VALUES(occupation), skill_level=VALUES(skill_level),
                    interests=VALUES(interests), preferences=VALUES(preferences), purposes=VALUES(purposes)
                    """,
                    (user["id"], career_occupation, "", json.dumps(interests, ensure_ascii=False), json.dumps(preferences, ensure_ascii=False), json.dumps(purposes, ensure_ascii=False)),
                )
                cursor.execute(
                    "UPDATE users SET questionnaire_completed=1, has_survey=1, user_tags=%s, interests=%s WHERE id=%s",
                    (",".join(profile_v2["tags"]), json.dumps(interests, ensure_ascii=False), user["id"]),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return api_success({
            "questionnaire_completed": True,
            "questionnaire_version": QUESTIONNAIRE_V3_VERSION,
            "profile": profile_v2,
        })

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
                response_v2 = load_questionnaire_v2_response(cursor, user["id"])
                response_v3 = load_questionnaire_v3_response(cursor, user["id"])
        finally:
            conn.close()
        return api_success({
            "version": response_v3.get("version") or response_v2.get("version") or 1,
            "answers": response_v3.get("answers") or response_v2.get("answers") or {},
            "recommendation_profile": response_v3.get("profile") or response_v2.get("profile") or {},
            "occupation": profile.get("occupation") or "",
            "skill_level": profile.get("skill_level") or "",
            "interests": parse_json_list(profile.get("interests") or user.get("interests")),
            "preferences": parse_json_list(profile.get("preferences")),
            "purposes": parse_json_list(profile.get("purposes")),
            "questionnaire_completed": bool(user.get("questionnaire_completed") or user.get("has_survey")),
        })

    @app.route("/api/career/recommend", methods=["GET"])
    @app.route("/api/career/recommendations", methods=["GET"])
    @jwt_required()
    def v1_career_recommendations():
        """Build the logged-in user's career and website recommendations."""
        user = current_user_row()
        if not user:
            return api_error("user not found", 404, 404)

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM user_profiles WHERE user_id=%s", (user["id"],))
                profile_row = cursor.fetchone() or {}
                response_v2 = load_questionnaire_v2_response(cursor, user["id"])
                response_v3 = load_questionnaire_v3_response(cursor, user["id"])
        finally:
            conn.close()

        profile = {
            "occupation": profile_row.get("occupation") or "",
            "skill_level": profile_row.get("skill_level") or "",
            "interests": parse_json_list(profile_row.get("interests") or user.get("interests")),
            "preferences": parse_json_list(profile_row.get("preferences")),
            "purposes": parse_json_list(profile_row.get("purposes")),
        }
        # Prefer V3 whenever it exists; V2 stays a valid historical fallback.
        response_v2 = response_v3 or response_v2
        recommendation_profile = response_v2.get("profile") or {}
        if recommendation_profile:
            # Preserve the broad identity (developer/student/creator/etc.) for
            # career scoring; a detailed career code is selected afterwards.
            profile["occupation"] = recommendation_profile.get("occupation") or profile["occupation"]
            profile["interests"] = list(dict.fromkeys([
                *profile["interests"], *recommendation_profile.get("tags", []),
            ]))
            if recommendation_profile.get("priority"):
                profile["preferences"] = list(dict.fromkeys([
                    *profile["preferences"], recommendation_profile["priority"],
                ]))
        completed = bool(
            user.get("questionnaire_completed")
            or user.get("has_survey")
            or profile.get("occupation")
            or profile.get("interests")
        )
        if not completed:
            return api_success(
                {
                    "questionnaire_completed": False,
                    "profile": profile,
                    "ability_tags": [],
                    "interest_tags": [],
                    "careers": [],
                    "selected_career": "",
                    "websites": [],
                }
            )

        career_profile = {
            **profile,
            **recommendation_profile,
            "interests": profile["interests"],
            "purposes": profile["purposes"],
        }
        careers = build_career_recommendations(
            career_profile,
            limit=8,
        )

        source_sites = query_sites(limit=1000, sort="recommend")
        recommend_rules = load_json_setting("recommend_rules", default_recommend_rules())
        profile_interest_values = list(profile["interests"]) + list(profile["purposes"])
        recommendation_session_id = f"rec_{uuid4().hex}"
        profile_version = str(response_v2.get("version") or QUESTIONNAIRE_VERSION)
        for career in careers:
            career_code = career["code"]
            career_label = career["label"]
            career_candidate_pool_id = f"pool_{career_code}_{uuid4().hex}"
            # Rank the full catalog. Career filtering alone would discard a
            # design or API tool before a V2 primary-need signal (for example,
            # frontend + ui_generation) has a chance to promote it.
            career_candidates = source_sites
            ranked_sites = rank_sites(
                career_candidates,
                {
                    "occupation": career_code,
                    "interests": profile_interest_values,
                    "direction": recommendation_profile.get("direction", ""),
                    "primary_need": recommendation_profile.get("primary_need", ""),
                    "priority": recommendation_profile.get("priority", ""),
                },
                # Keep a high-relevance pool for the homepage's 16-item
                # batches. The client rotates it deterministically instead of
                # introducing random, lower-quality recommendations.
                limit=60,
                rules=recommend_rules,
            )
            for site in ranked_sites:
                site["career_code"] = career_code
                site["career_codes"] = [career_code]
                site["career_label"] = career_label
                site["career_match_score"] = career["match_score"]
                site["recommendation_reason"] = site.get("reason") or career["reason"]
                site["reason"] = f"{career_label}：{site['recommendation_reason']}"
                # Observe the natural personalized/general mix before any
                # Phase 2.3 quota or behavior-score change is considered.
                if (site.get("need_score") or 0) > 0 or (site.get("direction_score") or 0) > 0:
                    site["personalization_type"] = "personalized"
                elif (site.get("occupation_score") or 0) > 0:
                    site["personalization_type"] = "general"
                else:
                    site["personalization_type"] = "fallback"
                site["recommendation_session_id"] = recommendation_session_id
                site["candidate_pool_id"] = career_candidate_pool_id
                site["questionnaire_version"] = profile_version
                site["profile_version"] = profile_version
                site["profile_schema_version"] = int(recommendation_profile.get("profile_schema_version") or profile_version or 1)
                site["algorithm_version"] = RECOMMENDATION_ALGORITHM_VERSION
            career["careerCode"] = career_code
            career["careerName"] = career_label
            career["score"] = career["match_score"]
            career["sites"] = ranked_sites
            career["websites"] = ranked_sites

        selected_career = careers[0] if careers else None
        selected_sites = selected_career.get("websites", []) if selected_career else []
        ability_tags = []
        if profile.get("skill_level"):
            ability_tags.append(profile["skill_level"])
        if profile.get("occupation"):
            ability_tags.append(get_occupation_label(profile["occupation"]))
        return api_success(
            {
                "questionnaire_completed": True,
                "questionnaire_version": str(
                    response_v2.get("version")
                    or profile_row.get("updated_at")
                    or profile_row.get("created_at")
                    or "current"
                ),
                "profile_version": profile_version,
                "profile_schema_version": int(recommendation_profile.get("profile_schema_version") or profile_version or 1),
                "algorithm_version": RECOMMENDATION_ALGORITHM_VERSION,
                "recommendation_session_id": recommendation_session_id,
                "candidate_pool_id": selected_sites[0].get("candidate_pool_id", "") if selected_sites else "",
                "batch_id": recommendation_session_id,
                "candidate_pool_size": len(selected_sites),
                "profile": profile,
                "recommendation_profile": recommendation_profile,
                "ability_tags": list(dict.fromkeys(ability_tags)),
                "interest_tags": list(dict.fromkeys(profile["interests"] + profile["purposes"])),
                "careers": careers,
                "selected_career": selected_career["code"] if selected_career else "",
                # `items` is a compatibility alias for clients that consume
                # a generic recommendation envelope; `websites` remains the
                # stable career API field.
                "items": selected_sites,
                "websites": selected_sites,
            }
        )

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
        conn = None
        try:
            category_columns = table_columns("categories", strict=True)
            parent_expr = "parent_id" if "parent_id" in category_columns else "NULL AS parent_id"
            icon_expr = "icon" if "icon" in category_columns else "'' AS icon"
            sort_expr = "sort_order" if "sort_order" in category_columns else "0 AS sort_order"
            status_expr = "status" if "status" in category_columns else "'active' AS status"
            code_expr = "code" if "code" in category_columns else "NULL AS code"
            where_sql = "WHERE COALESCE(status, 'active')='active'" if "status" in category_columns else ""
            order_sql = "COALESCE(parent_id, 0), sort_order, id" if "parent_id" in category_columns else "sort_order, id"
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, {parent_expr}, name, {icon_expr}, {sort_expr}, {status_expr}, {code_expr}
                    FROM categories
                    {where_sql}
                    ORDER BY {order_sql}
                    """
                )
                rows = cursor.fetchall()
        except Exception as error:
            app.logger.exception(
                "categories query failed error_type=%s", type(error).__name__
            )
            if is_search_database_unavailable(error):
                return api_error(
                    "分类服务暂时不可用，请稍后重试",
                    "CATEGORY_DATABASE_ERROR",
                    503,
                )
            return api_error(
                "分类数据加载失败，请稍后重试",
                "CATEGORY_INTERNAL_ERROR",
                500,
            )
        finally:
            safe_close(conn)
        for row in rows:
            code = row.get("code") or category_code_for_name(row.get("name"))
            row["code"] = code
            row["category_code"] = code
            row["categoryCode"] = code
            row["categoryName"] = row.get("name")
            row["description"] = row.get("description") or f"浏览{row.get('name') or '该分类'}下收录的网站资源。"
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
        category_id = clean_arg(request.args.get("category_id")) or clean_arg(request.args.get("category"))
        category_code = clean_arg(request.args.get("category_code")) or clean_arg(request.args.get("categoryCode"))
        if category_code and not category_id:
            category_columns = table_columns("categories")
            code_expr = "code" if "code" in category_columns else "NULL AS code"
            category_status = "status IS NULL OR status='active'" if "status" in category_columns else "1=1"
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT id, name, {code_expr} FROM categories WHERE {category_status}")
                    category_rows = cursor.fetchall()
            except Exception:
                category_rows = []
            finally:
                conn.close()
            matched = next(
                (
                    row
                    for row in category_rows
                    if str(row.get("code") or category_code_for_name(row.get("name"))).lower()
                    == str(category_code).lower()
                ),
                None,
            )
            if matched:
                category_id = matched.get("id")
        keyword = clean_arg(request.args.get("q")) or clean_arg(request.args.get("keyword"))
        tag = clean_arg(request.args.get("tag"))
        is_free = clean_arg(request.args.get("is_free"))
        region = clean_arg(request.args.get("region"))
        items = query_sites(
            limit=per_page,
            offset=max(page - 1, 0) * per_page,
            category_id=category_id,
            keyword=keyword,
            tag=tag,
            is_free=is_free,
            region=region,
            sort=clean_arg(request.args.get("sort")) or "recommend",
            exclude_ids=parse_id_list(request.args.get("exclude_ids")),
        )
        total = count_sites(
            category_id=category_id,
            keyword=keyword,
            tag=tag,
            is_free=is_free,
            region=region,
        )
        total_pages = (total + per_page - 1) // per_page if total else 0
        pagination = {
            "page": page,
            "pageSize": per_page,
            "total": total,
            "totalPages": total_pages,
            "hasMore": page < total_pages,
        }
        return api_success(
            {
                "items": items,
                "page": page,
                "pageSize": per_page,
                "per_page": per_page,
                "total": total,
                "total_count": total,
                "totalPages": total_pages,
                "hasMore": page < total_pages,
                "pagination": pagination,
                "category": {
                    "code": category_code,
                    "id": category_id,
                }
                if category_code or category_id
                else None,
            }
        )

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
        click_payload = request.get_json(silent=True) or {}
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE websites SET click_count=COALESCE(click_count,0)+1, clicks=COALESCE(clicks,0)+1 WHERE id=%s", (site_id,))
            conn.commit()
        finally:
            conn.close()
        record_behavior(user.get("id") if user else None, site_id, "click")
        if user:
            record_unified_behavior(
                user["id"], site_id, "click",
                str(click_payload.get("source") or "other").strip().lower(),
                click_payload,
            )
        return api_success()

    def validate_behavior_payload(payload, *, batch=False):
        if not isinstance(payload, dict):
            return None, api_error("invalid behavior payload", "INVALID_EVENT", 400)
        event_type = str(payload.get("event_type") or "").strip().lower()
        source = str(payload.get("source") or "other").strip().lower()
        if event_type not in BEHAVIOR_EVENT_TYPES:
            return None, api_error("unsupported event_type", "INVALID_EVENT_TYPE", 400)
        if source not in BEHAVIOR_SOURCES:
            return None, api_error("unsupported source", "INVALID_SOURCE", 400)
        if batch:
            raw_ids = payload.get("website_ids")
            if not isinstance(raw_ids, list) or not raw_ids:
                return None, api_error("website_ids is required", "INVALID_WEBSITE_IDS", 400)
            website_ids = []
            for raw_id in raw_ids[:100]:
                if str(raw_id).strip().isdigit():
                    website_ids.append(int(raw_id))
            if not website_ids:
                return None, api_error("website_ids is required", "INVALID_WEBSITE_IDS", 400)
            payload = dict(payload)
            payload["website_ids"] = list(dict.fromkeys(website_ids))
        else:
            raw_id = payload.get("website_id", payload.get("site_id", payload.get("id")))
            if not str(raw_id or "").strip().isdigit():
                return None, api_error("website_id is required", "INVALID_WEBSITE_ID", 400)
            payload = dict(payload)
            payload["website_id"] = int(raw_id)
        payload["event_type"] = event_type
        payload["source"] = source
        return payload, None

    def behavior_user_optional():
        try:
            return current_user_row() if get_jwt_identity() else None
        except Exception:
            app.logger.exception("behavior user lookup failed")
            return None

    @app.route("/api/behavior/events", methods=["POST"])
    @jwt_required(optional=True)
    def v1_record_behavior_event():
        payload, error = validate_behavior_payload(request.get_json(silent=True) or {})
        if error:
            return error
        user = behavior_user_optional()
        # Anonymous users keep the existing local click/history behavior.  Do
        # not manufacture user_id=0 rows in the unified table.
        if not user:
            return api_success({"recorded": False, "anonymous": True})
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                ensure_behavior_events_table(cursor)
                cursor.execute("SELECT id FROM websites WHERE id=%s LIMIT 1", (payload["website_id"],))
                if not cursor.fetchone():
                    return api_error("site not found", "SITE_NOT_FOUND", 404)
                context = behavior_context(payload)
                event_type = payload["event_type"]
                if event_type == "repeat_visit":
                    cursor.execute(
                        """
                        SELECT created_at FROM user_behavior_events
                        WHERE user_id=%s AND website_id=%s
                          AND event_type IN ('click','repeat_visit')
                        ORDER BY created_at DESC LIMIT 2
                        """,
                        (user["id"], payload["website_id"]),
                    )
                    visits = cursor.fetchall() or []
                    if len(visits) < 2:
                        # Existing history is also a valid source when this is
                        # the first request after the migration.
                        cursor.execute(
                            """
                            SELECT created_at FROM user_behaviors
                            WHERE user_id=%s AND site_id=%s AND behavior_type='visit'
                            ORDER BY created_at DESC LIMIT 2
                            """,
                            (user["id"], payload["website_id"]),
                        )
                        visits = cursor.fetchall() or []
                    if len(visits) < 2:
                        return api_success({"recorded": False, "reason": "no_previous_visit"})
                    cursor.execute(
                        """
                        SELECT id FROM user_behavior_events
                        WHERE user_id=%s AND website_id=%s AND event_type='repeat_visit'
                          AND created_at >= DATE_SUB(NOW(), INTERVAL %s MINUTE)
                        ORDER BY created_at DESC LIMIT 1
                        """,
                        (user["id"], payload["website_id"], REPEAT_VISIT_WINDOW_MINUTES),
                    )
                    if cursor.fetchone():
                        return api_success({"recorded": False, "reason": "within_dedupe_window"})
                    # The second-most-recent visit must be outside the window.
                    cursor.execute(
                        """
                        SELECT id FROM user_behavior_events
                        WHERE user_id=%s AND website_id=%s AND event_type IN ('click','repeat_visit')
                          AND created_at <= DATE_SUB(NOW(), INTERVAL %s MINUTE)
                        ORDER BY created_at DESC LIMIT 1 OFFSET 1
                        """,
                        (user["id"], payload["website_id"], REPEAT_VISIT_WINDOW_MINUTES),
                    )
                    if not cursor.fetchone() and visits:
                        cursor.execute(
                            """
                            SELECT id FROM user_behaviors
                            WHERE user_id=%s AND site_id=%s AND behavior_type='visit'
                              AND created_at <= DATE_SUB(NOW(), INTERVAL %s MINUTE)
                            ORDER BY created_at DESC LIMIT 1 OFFSET 1
                            """,
                            (user["id"], payload["website_id"], REPEAT_VISIT_WINDOW_MINUTES),
                        )
                        if not cursor.fetchone():
                            return api_success({"recorded": False, "reason": "within_dedupe_window"})
                wrote = insert_behavior_event(
                    user["id"], payload["website_id"], event_type, payload["source"], context, cursor,
                    dedupe=event_type in {"impression", "favorite"},
                )
            conn.commit()
            return api_success({"recorded": wrote, "event_type": event_type})
        except Exception:
            safe_rollback(conn)
            app.logger.exception("behavior event endpoint failed")
            return api_error("behavior event could not be recorded", "BEHAVIOR_DATABASE_ERROR", 503)
        finally:
            safe_close(conn)

    @app.route("/api/behavior/events/batch", methods=["POST"])
    @jwt_required(optional=True)
    def v1_record_behavior_events_batch():
        payload, error = validate_behavior_payload(request.get_json(silent=True) or {}, batch=True)
        if error:
            return error
        user = behavior_user_optional()
        if not user:
            return api_success({"recorded": 0, "anonymous": True})
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                ensure_behavior_events_table(cursor)
                ids = payload["website_ids"]
                placeholders = ",".join(["%s"] * len(ids))
                cursor.execute(f"SELECT id FROM websites WHERE id IN ({placeholders})", ids)
                existing_ids = {int(row["id"]) for row in cursor.fetchall()}
                missing_ids = [website_id for website_id in ids if website_id not in existing_ids]
                if missing_ids:
                    return api_error("site not found", "SITE_NOT_FOUND", 404, {"website_ids": missing_ids})
                context = behavior_context(payload)
                recorded = 0
                for website_id in ids:
                    if insert_behavior_event(
                        user["id"], website_id, payload["event_type"], payload["source"], context, cursor,
                        dedupe=payload["event_type"] in {"impression", "favorite"},
                    ):
                        recorded += 1
            conn.commit()
            return api_success({"recorded": recorded, "requested": len(ids)})
        except Exception:
            safe_rollback(conn)
            app.logger.exception("behavior batch endpoint failed")
            return api_error("behavior events could not be recorded", "BEHAVIOR_DATABASE_ERROR", 503)
        finally:
            safe_close(conn)

    METRIC_PROFILE_FROM = """
        FROM user_behavior_events e
        LEFT JOIN websites w ON w.id=e.website_id
        LEFT JOIN user_profiles up ON up.user_id=e.user_id
        LEFT JOIN user_questionnaire_responses qr
          ON qr.user_id=e.user_id
         AND CAST(qr.questionnaire_version AS CHAR)=COALESCE(e.questionnaire_version, '')
    """
    METRIC_PROFILE_EXPRESSIONS = {
        "day": "DATE(e.created_at)",
        "user": "e.user_id",
        "occupation": "COALESCE(qr.occupation, up.occupation, 'unknown')",
        "direction": "COALESCE(JSON_UNQUOTE(JSON_EXTRACT(qr.profile_json, '$.direction')), 'unknown')",
        "primary_need": "COALESCE(JSON_UNQUOTE(JSON_EXTRACT(qr.profile_json, '$.primary_need')), 'unknown')",
        "recommendation_batch": "COALESCE(e.recommendation_batch_id, 'direct')",
        "website": "e.website_id",
        "source": "e.source",
        "tag": "COALESCE(t.name, 'untagged')",
        "personalization_type": "COALESCE(JSON_UNQUOTE(JSON_EXTRACT(e.metadata_json, '$.personalization_type')), 'unknown')",
        "match_score_bucket": """CASE
            WHEN JSON_EXTRACT(e.metadata_json, '$.match_score') IS NULL THEN 'unrecorded'
            WHEN CAST(JSON_UNQUOTE(JSON_EXTRACT(e.metadata_json, '$.match_score')) AS DECIMAL(6,2)) < 60 THEN '0-59'
            WHEN CAST(JSON_UNQUOTE(JSON_EXTRACT(e.metadata_json, '$.match_score')) AS DECIMAL(6,2)) < 70 THEN '60-69'
            WHEN CAST(JSON_UNQUOTE(JSON_EXTRACT(e.metadata_json, '$.match_score')) AS DECIMAL(6,2)) < 80 THEN '70-79'
            WHEN CAST(JSON_UNQUOTE(JSON_EXTRACT(e.metadata_json, '$.match_score')) AS DECIMAL(6,2)) < 90 THEN '80-89'
            ELSE '90-100' END""",
    }

    def recommendation_metrics_test_user_ids():
        """Explicit configuration only; never infer test accounts from a name."""
        raw = os.getenv("RECOMMENDATION_METRICS_TEST_USER_IDS", "")
        return [int(value) for value in re.findall(r"\d+", raw)]

    def metrics_exclude_test_users(args, *, user_id=None):
        if user_id:
            return False
        value = str(args.get("exclude_test_users", "true")).strip().lower()
        return value not in {"0", "false", "no", "off"}

    def metric_filters(args, *, user_id=None):
        clauses = []
        params = []
        raw_days = args.get("lookback_days", BEHAVIOR_LOOKBACK_DAYS)
        if str(raw_days).strip().lower() in {"all", "0"}:
            lookback_days = "all"
        else:
            try:
                lookback_days = max(1, min(int(raw_days), 365))
            except (TypeError, ValueError):
                raise ValueError("lookback_days must be between 1 and 365, or all")
            clauses.append("e.created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY)")
            params.append(lookback_days)
        for key, column in (("date_from", ">="), ("date_to", "< DATE_ADD")):
            value = str(args.get(key) or "").strip()
            if not value:
                continue
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError(f"{key} must use YYYY-MM-DD")
            if key == "date_from":
                clauses.append("e.created_at >= %s")
            else:
                clauses.append("e.created_at < DATE_ADD(%s, INTERVAL 1 DAY)")
            params.append(value)
        if user_id:
            clauses.append("e.user_id=%s")
            params.append(user_id)
        elif str(args.get("user_id") or "").isdigit():
            clauses.append("e.user_id=%s")
            params.append(int(args["user_id"]))
        for argument, expression in (
            ("occupation", METRIC_PROFILE_EXPRESSIONS["occupation"]),
            ("direction", METRIC_PROFILE_EXPRESSIONS["direction"]),
            ("primary_need", METRIC_PROFILE_EXPRESSIONS["primary_need"]),
            ("recommendation_batch_id", "e.recommendation_batch_id"),
            ("website_id", "e.website_id"),
            ("source", "e.source"),
        ):
            value = str(args.get(argument) or "").strip()
            if not value:
                continue
            if argument == "website_id" and not value.isdigit():
                raise ValueError("website_id must be numeric")
            clauses.append(f"{expression}=%s")
            params.append(int(value) if argument == "website_id" else value)
        test_user_ids = recommendation_metrics_test_user_ids()
        if metrics_exclude_test_users(args, user_id=user_id) and test_user_ids:
            placeholders = ",".join(["%s"] * len(test_user_ids))
            clauses.append(f"(e.user_id IS NULL OR e.user_id NOT IN ({placeholders}))")
            params.extend(test_user_ids)
        return " WHERE " + " AND ".join(clauses), params, lookback_days

    def metric_values(row):
        impressions = int(row.get("impressions") or 0)
        clicks = int(row.get("clicks") or 0)
        favorites = int(row.get("favorites") or 0)
        repeat_visits = int(row.get("repeat_visits") or 0)
        return {
            **row,
            "impressions": impressions,
            "clicks": clicks,
            "favorites": favorites,
            "repeat_visits": repeat_visits,
            "ctr": round(clicks * 100 / impressions, 2) if impressions else 0,
            "favorite_rate": round(favorites * 100 / impressions, 2) if impressions else 0,
            "favorite_per_click_rate": round(favorites * 100 / clicks, 2) if clicks else 0,
            "repeat_visit_rate": round(repeat_visits * 100 / clicks, 2) if clicks else 0,
        }

    def query_metric_summary(args, *, user_id=None, group_by=None):
        where_sql, params, lookback_days = metric_filters(args, user_id=user_id)
        group_by = group_by or ""
        if group_by and group_by not in METRIC_PROFILE_EXPRESSIONS:
            raise ValueError("unsupported group_by")
        tag_join = " LEFT JOIN site_tags st ON st.site_id=e.website_id LEFT JOIN tags t ON t.id=st.tag_id" if group_by == "tag" else ""
        expression = METRIC_PROFILE_EXPRESSIONS.get(group_by, "")
        select_dimension = f", {expression} AS dimension" if expression else ""
        group_sql = f" GROUP BY {expression} ORDER BY impressions DESC, clicks DESC" if expression else ""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT COUNT(*) AS event_count,
                      SUM(CASE WHEN e.event_type='impression' THEN 1 ELSE 0 END) AS impressions,
                      SUM(CASE WHEN e.event_type='click' THEN 1 ELSE 0 END) AS clicks,
                      SUM(CASE WHEN e.event_type='favorite' THEN 1 ELSE 0 END) AS favorites,
                      SUM(CASE WHEN e.event_type='repeat_visit' THEN 1 ELSE 0 END) AS repeat_visits
                      {select_dimension}
                    {METRIC_PROFILE_FROM}{tag_join}{where_sql}{group_sql}
                    """,
                    params,
                )
                rows = cursor.fetchall()
        finally:
            conn.close()
        values = [metric_values(row) for row in rows]
        return (values if group_by else (values[0] if values else metric_values({}))), lookback_days

    @app.route("/api/recommendation/metrics/summary", methods=["GET"])
    @admin_required
    def v1_recommendation_metrics_summary():
        try:
            group_by = str(request.args.get("group_by") or "").strip().lower()
            summary, lookback_days = query_metric_summary(request.args, group_by=group_by)
        except ValueError as error:
            return api_error(str(error), "INVALID_METRIC_FILTER", 400)
        return api_success({
            "lookback_days": lookback_days,
            "behavior_weights": BEHAVIOR_WEIGHTS,
            "group_by": group_by or None,
            "summary": summary,
        })

    def quality_issue(metric, value, *, severity="warning", message=""):
        return {
            "metric": metric,
            "count": int(value or 0),
            "severity": severity,
            "message": message,
        }

    def query_data_quality(args):
        """Read-only integrity diagnostics for observation-period events.

        The checks deliberately detect suspicious writes without deleting,
        merging, or otherwise changing the factual event table.
        """
        where_sql, params, lookback_days = metric_filters(args)
        event_from = f"{METRIC_PROFILE_FROM} LEFT JOIN users u ON u.id=e.user_id"
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT COUNT(*) AS total_events,
                      SUM(CASE WHEN e.event_type='impression' THEN 1 ELSE 0 END) AS impressions,
                      SUM(CASE WHEN e.event_type='click' THEN 1 ELSE 0 END) AS clicks,
                      SUM(CASE WHEN e.event_type='favorite' THEN 1 ELSE 0 END) AS favorites,
                      SUM(CASE WHEN e.event_type='repeat_visit' THEN 1 ELSE 0 END) AS repeat_visits,
                      SUM(CASE WHEN w.id IS NULL THEN 1 ELSE 0 END) AS invalid_websites,
                      SUM(CASE WHEN e.user_id IS NOT NULL AND u.id IS NULL THEN 1 ELSE 0 END) AS invalid_users,
                      SUM(CASE WHEN e.event_type NOT IN ('impression','click','favorite','repeat_visit') THEN 1 ELSE 0 END) AS invalid_event_types,
                      SUM(CASE WHEN e.source='personalized_recommendation'
                                AND (e.recommendation_batch_id IS NULL OR TRIM(e.recommendation_batch_id)='')
                               THEN 1 ELSE 0 END) AS missing_batch_id,
                      SUM(CASE WHEN e.session_id IS NULL OR TRIM(e.session_id)='' THEN 1 ELSE 0 END) AS missing_session_id,
                      SUM(CASE WHEN JSON_UNQUOTE(JSON_EXTRACT(e.metadata_json, '$.personalization_type'))='personalized'
                                AND (e.source IS NULL OR TRIM(e.source)='') THEN 1 ELSE 0 END) AS personalized_missing_source
                    {event_from}{where_sql}
                    """,
                    params,
                )
                totals = cursor.fetchone() or {}

                def duplicate_count(event_type, include_created_at=False):
                    created_group = ", e.created_at" if include_created_at else ""
                    cursor.execute(
                        f"""
                        SELECT COALESCE(SUM(duplicate_count), 0) AS count FROM (
                          SELECT COUNT(*) - 1 AS duplicate_count
                          {METRIC_PROFILE_FROM}{where_sql} AND e.event_type=%s
                          GROUP BY e.user_id, e.website_id, e.source,
                            COALESCE(e.recommendation_batch_id,''), COALESCE(e.session_id,''){created_group}
                          HAVING COUNT(*) > 1
                        ) duplicate_rows
                        """,
                        [*params, event_type],
                    )
                    return int((cursor.fetchone() or {}).get("count") or 0)

                duplicate_impressions = duplicate_count("impression")
                duplicate_favorites = duplicate_count("favorite")
                # Clicks are not normally deduplicated, so only identical
                # context written in the same timestamp is flagged as a likely
                # double-write instead of treating genuine repeat clicks as bad.
                duplicate_clicks = duplicate_count("click", include_created_at=True)
                cursor.execute(
                    f"""
                    SELECT COUNT(*) AS count
                    {METRIC_PROFILE_FROM}{where_sql}
                      AND e.event_type='repeat_visit'
                      AND EXISTS (
                        SELECT 1 FROM user_behavior_events prior
                        WHERE prior.user_id=e.user_id AND prior.website_id=e.website_id
                          AND prior.event_type IN ('click','repeat_visit')
                          AND (prior.created_at < e.created_at
                               OR (prior.created_at=e.created_at AND prior.id < e.id))
                          AND prior.created_at > DATE_SUB(e.created_at, INTERVAL {REPEAT_VISIT_WINDOW_MINUTES} MINUTE)
                      )
                    """,
                    params,
                )
                repeat_window_violations = int((cursor.fetchone() or {}).get("count") or 0)
        finally:
            conn.close()

        report = {
            **metric_values(totals),
            "total_events": int(totals.get("total_events") or 0),
            "duplicate_impressions": duplicate_impressions,
            "duplicate_impression_rate": round(
                duplicate_impressions * 100 / int(totals.get("impressions") or 0), 2
            ) if totals.get("impressions") else 0,
            "duplicate_clicks": duplicate_clicks,
            "duplicate_favorites": duplicate_favorites,
            "invalid_websites": int(totals.get("invalid_websites") or 0),
            "invalid_users": int(totals.get("invalid_users") or 0),
            "missing_batch_id": int(totals.get("missing_batch_id") or 0),
            "missing_session_id": int(totals.get("missing_session_id") or 0),
            "personalized_missing_source": int(totals.get("personalized_missing_source") or 0),
            "invalid_event_types": int(totals.get("invalid_event_types") or 0),
            "repeat_visit_window_violations": repeat_window_violations,
            "lookback_days": lookback_days,
            "exclude_test_users": metrics_exclude_test_users(args),
        }
        critical = ("invalid_websites", "invalid_users", "invalid_event_types", "duplicate_clicks")
        warning = (
            "duplicate_impressions", "duplicate_favorites", "missing_batch_id",
            "missing_session_id", "personalized_missing_source", "repeat_visit_window_violations",
        )
        if any(report[name] for name in critical):
            report["status"] = "error"
        elif any(report[name] for name in warning):
            report["status"] = "warning"
        else:
            report["status"] = "healthy"
        report["issues"] = [
            quality_issue("duplicate_impressions", report["duplicate_impressions"], message="重复曝光"),
            quality_issue("duplicate_clicks", report["duplicate_clicks"], severity="error", message="疑似重复点击"),
            quality_issue("duplicate_favorites", report["duplicate_favorites"], message="重复收藏"),
            quality_issue("invalid_websites", report["invalid_websites"], severity="error", message="无效网站"),
            quality_issue("invalid_users", report["invalid_users"], severity="error", message="无效用户"),
            quality_issue("missing_batch_id", report["missing_batch_id"], message="缺少推荐批次"),
            quality_issue("missing_session_id", report["missing_session_id"], message="缺少会话"),
            quality_issue("repeat_visit_window_violations", report["repeat_visit_window_violations"], message="回访窗口异常"),
            quality_issue("invalid_event_types", report["invalid_event_types"], severity="error", message="未知事件类型"),
        ]
        return report

    @app.route("/api/recommendation/metrics/data-quality", methods=["GET"])
    @admin_required
    def v1_recommendation_metrics_data_quality():
        try:
            return api_success(query_data_quality(request.args))
        except ValueError as error:
            return api_error(str(error), "INVALID_METRIC_FILTER", 400)

    def readiness_requirement(value, required):
        return {"value": int(value or 0), "required": int(required), "passed": int(value or 0) >= int(required)}

    def query_phase_2_3_readiness(args):
        summary, lookback_days = query_metric_summary(args)
        quality = query_data_quality(args)
        where_sql, params, _ = metric_filters(args)
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT COUNT(*) AS qualifying_occupations FROM (
                      SELECT COALESCE(qr.occupation, up.occupation, 'unknown') AS occupation
                      {METRIC_PROFILE_FROM}{where_sql} AND e.event_type='impression'
                      GROUP BY occupation HAVING COUNT(*) >= %s
                    ) coverage
                    """,
                    [*params, PHASE_2_3_READINESS_THRESHOLDS["profile_impressions"]],
                )
                occupations = int((cursor.fetchone() or {}).get("qualifying_occupations") or 0)
                cursor.execute(
                    f"""
                    SELECT COUNT(*) AS qualifying_profiles FROM (
                      SELECT COALESCE(JSON_UNQUOTE(JSON_EXTRACT(qr.profile_json, '$.direction')), 'unknown') AS direction,
                             COALESCE(JSON_UNQUOTE(JSON_EXTRACT(qr.profile_json, '$.primary_need')), 'unknown') AS primary_need
                      {METRIC_PROFILE_FROM}{where_sql} AND e.event_type='impression'
                      GROUP BY direction, primary_need HAVING COUNT(*) >= %s
                    ) coverage
                    """,
                    [*params, PHASE_2_3_READINESS_THRESHOLDS["profile_impressions"]],
                )
                profile_combinations = int((cursor.fetchone() or {}).get("qualifying_profiles") or 0)
                cursor.execute(
                    f"""
                    SELECT COUNT(DISTINCT e.recommendation_batch_id) AS batches,
                           COUNT(DISTINCT e.user_id) AS batch_users,
                           MIN(e.created_at) AS first_event_at,
                           COALESCE(DATEDIFF(CURDATE(), MIN(e.created_at)), 0) AS observed_days
                    {METRIC_PROFILE_FROM}{where_sql}
                      AND e.event_type='impression' AND e.recommendation_batch_id IS NOT NULL
                    """,
                    params,
                )
                batch_row = cursor.fetchone() or {}
        finally:
            conn.close()
        events = {
            "impressions": readiness_requirement(summary.get("impressions"), PHASE_2_3_READINESS_THRESHOLDS["impressions"]),
            "clicks": readiness_requirement(summary.get("clicks"), PHASE_2_3_READINESS_THRESHOLDS["clicks"]),
            "favorites": readiness_requirement(summary.get("favorites"), PHASE_2_3_READINESS_THRESHOLDS["favorites"]),
            "repeat_visits": readiness_requirement(summary.get("repeat_visits"), PHASE_2_3_READINESS_THRESHOLDS["repeat_visits"]),
        }
        profile_coverage = {
            "occupations": readiness_requirement(occupations, PHASE_2_3_READINESS_THRESHOLDS["occupations"]),
            "direction_primary_need_combinations": readiness_requirement(profile_combinations, PHASE_2_3_READINESS_THRESHOLDS["profile_combinations"]),
            "minimum_impressions_per_profile": PHASE_2_3_READINESS_THRESHOLDS["profile_impressions"],
        }
        batch_coverage = {
            **readiness_requirement(batch_row.get("batches"), PHASE_2_3_READINESS_THRESHOLDS["recommendation_batches"]),
            "distinct_users": int(batch_row.get("batch_users") or 0),
            "multiple_users": int(batch_row.get("batch_users") or 0) >= 2,
        }
        quality_passed = (
            quality["duplicate_impression_rate"] < PHASE_2_3_READINESS_THRESHOLDS["duplicate_impression_rate"]
            and quality["duplicate_clicks"] == 0
            and quality["invalid_websites"] == 0
            and quality["invalid_event_types"] == 0
        )
        data_quality = {
            "status": quality["status"], "passed": quality_passed,
            "duplicate_impression_rate": quality["duplicate_impression_rate"],
            "required_duplicate_impression_rate": f"<{PHASE_2_3_READINESS_THRESHOLDS['duplicate_impression_rate']}%",
            "duplicate_clicks": quality["duplicate_clicks"],
            "invalid_websites": quality["invalid_websites"],
            "invalid_event_types": quality["invalid_event_types"],
        }
        trend_stability = {
            "observed_days": int(batch_row.get("observed_days") or 0),
            "minimum_observed_days": 7,
            "recommended_windows": [7, 30],
            "passed": int(batch_row.get("observed_days") or 0) >= 7,
            "note": "数据周期不足 30 天时，可先按实际累计周期观察，但不得据此自动调参。",
        }
        readiness_groups = [
            *(item["passed"] for item in events.values()),
            profile_coverage["occupations"]["passed"],
            profile_coverage["direction_primary_need_combinations"]["passed"],
            batch_coverage["passed"], batch_coverage["multiple_users"], quality_passed, trend_stability["passed"],
        ]
        remaining = [
            {"metric": name, "remaining": max(0, item["required"] - item["value"])}
            for name, item in events.items() if not item["passed"]
        ]
        if not profile_coverage["occupations"]["passed"]:
            remaining.append({"metric": "occupations", "remaining": profile_coverage["occupations"]["required"] - profile_coverage["occupations"]["value"]})
        if not profile_coverage["direction_primary_need_combinations"]["passed"]:
            item = profile_coverage["direction_primary_need_combinations"]
            remaining.append({"metric": "profile_combinations", "remaining": item["required"] - item["value"]})
        if not batch_coverage["passed"]:
            remaining.append({"metric": "recommendation_batches", "remaining": batch_coverage["required"] - batch_coverage["value"]})
        if not batch_coverage["multiple_users"]:
            remaining.append({"metric": "batch_users", "remaining": max(0, 2 - batch_coverage["distinct_users"])})
        if not trend_stability["passed"]:
            remaining.append({"metric": "observation_days", "remaining": trend_stability["minimum_observed_days"] - trend_stability["observed_days"]})
        return {
            "ready": all(readiness_groups), "lookback_days": lookback_days,
            "events": events, "profile_coverage": profile_coverage,
            "batch_coverage": batch_coverage, "data_quality": data_quality, "trend_stability": trend_stability,
            "remaining": remaining, "thresholds": PHASE_2_3_READINESS_THRESHOLDS,
        }

    @app.route("/api/recommendation/metrics/phase-2-3-readiness", methods=["GET"])
    @admin_required
    def v1_recommendation_metrics_phase_2_3_readiness():
        try:
            return api_success(query_phase_2_3_readiness(request.args))
        except ValueError as error:
            return api_error(str(error), "INVALID_METRIC_FILTER", 400)

    def snapshot_json(value):
        return json.dumps(value, ensure_ascii=False, default=str)

    def parse_snapshot_json(value, default):
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value) if value else default
        except (TypeError, ValueError):
            return default

    def snapshot_summary(row):
        summary = parse_snapshot_json(row.get("summary_json"), {})
        readiness = parse_snapshot_json(row.get("readiness_json"), {})
        quality = parse_snapshot_json(row.get("data_quality_json"), {})
        return {
            "snapshot_id": row.get("snapshot_id"),
            "algorithm_version": row.get("algorithm_version"),
            "lookback_days": row.get("lookback_days"),
            "exclude_test_users": bool(row.get("exclude_test_users")),
            "created_at": row.get("created_at"),
            "summary": summary,
            "readiness": {"ready": bool(readiness.get("ready"))},
            "data_quality": {"status": quality.get("status", "unknown")},
        }

    def observation_snapshot_data(args):
        summary, lookback_days = query_metric_summary(args)
        quality = query_data_quality(args)
        readiness = query_phase_2_3_readiness(args)
        match_score_buckets, _ = query_metric_summary(args, group_by="match_score_bucket")
        primary_need_metrics, _ = query_metric_summary(args, group_by="primary_need")
        tag_metrics, _ = query_metric_summary(args, group_by="tag")
        personalization_metrics, _ = query_metric_summary(args, group_by="personalization_type")
        return {
            "algorithm_version": RECOMMENDATION_ALGORITHM_VERSION,
            "lookback_days": str(lookback_days),
            "exclude_test_users": metrics_exclude_test_users(args),
            "summary": summary,
            "data_quality": quality,
            "readiness": readiness,
            "match_score_buckets": match_score_buckets,
            "primary_need_metrics": primary_need_metrics[:50],
            "tag_metrics": tag_metrics[:100],
            "personalization_metrics": personalization_metrics,
        }

    @app.route("/api/recommendation/metrics/observation-snapshots", methods=["POST"])
    @admin_required
    def v1_create_recommendation_observation_snapshot():
        try:
            snapshot = observation_snapshot_data(request.args)
        except ValueError as error:
            return api_error(str(error), "INVALID_METRIC_FILTER", 400)
        user = current_user_row()
        snapshot_id = f"obs_{uuid4().hex}"
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                ensure_observation_snapshots_table(cursor)
                cursor.execute(
                    """
                    INSERT INTO recommendation_observation_snapshots
                      (snapshot_id, algorithm_version, lookback_days, exclude_test_users,
                       captured_by_user_id, summary_json, data_quality_json, readiness_json,
                       match_score_buckets_json, primary_need_metrics_json, tag_metrics_json,
                       personalization_metrics_json)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        snapshot_id, snapshot["algorithm_version"], snapshot["lookback_days"],
                        int(snapshot["exclude_test_users"]), user.get("id") if user else None,
                        snapshot_json(snapshot["summary"]), snapshot_json(snapshot["data_quality"]),
                        snapshot_json(snapshot["readiness"]), snapshot_json(snapshot["match_score_buckets"]),
                        snapshot_json(snapshot["primary_need_metrics"]), snapshot_json(snapshot["tag_metrics"]),
                        snapshot_json(snapshot["personalization_metrics"]),
                    ),
                )
            conn.commit()
        except Exception:
            safe_rollback(conn)
            app.logger.exception("observation snapshot write failed")
            return api_error("observation snapshot could not be saved", "SNAPSHOT_DATABASE_ERROR", 503)
        finally:
            safe_close(conn)
        return api_success({"snapshot_id": snapshot_id, **snapshot}, status=201)

    @app.route("/api/recommendation/metrics/observation-snapshots", methods=["GET"])
    @admin_required
    def v1_list_recommendation_observation_snapshots():
        try:
            limit = max(1, min(int(request.args.get("limit", 20)), 100))
        except (TypeError, ValueError):
            return api_error("limit must be numeric", "INVALID_SNAPSHOT_LIMIT", 400)
        algorithm_version = str(request.args.get("algorithm_version") or "").strip()[:64]
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                ensure_observation_snapshots_table(cursor)
                clauses, params = [], []
                if algorithm_version:
                    clauses.append("algorithm_version=%s")
                    params.append(algorithm_version)
                where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
                cursor.execute(
                    f"""
                    SELECT snapshot_id, algorithm_version, lookback_days, exclude_test_users,
                           created_at, summary_json, data_quality_json, readiness_json
                    FROM recommendation_observation_snapshots{where}
                    ORDER BY created_at DESC, id DESC LIMIT %s
                    """,
                    [*params, limit],
                )
                rows = cursor.fetchall()
        except Exception:
            app.logger.exception("observation snapshot list failed")
            return api_error("observation snapshots unavailable", "SNAPSHOT_DATABASE_ERROR", 503)
        finally:
            safe_close(conn)
        return api_success({"items": [snapshot_summary(row) for row in rows]})

    @app.route("/api/recommendation/metrics/observation-snapshots/compare", methods=["GET"])
    @admin_required
    def v1_compare_recommendation_observation_snapshots():
        left_id = str(request.args.get("left_snapshot_id") or "").strip()
        right_id = str(request.args.get("right_snapshot_id") or "").strip()
        if not re.fullmatch(r"obs_[a-f0-9]{32}", left_id) or not re.fullmatch(r"obs_[a-f0-9]{32}", right_id):
            return api_error("two valid snapshot ids are required", "INVALID_SNAPSHOT_IDS", 400)
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                ensure_observation_snapshots_table(cursor)
                cursor.execute(
                    """
                    SELECT snapshot_id, algorithm_version, lookback_days, exclude_test_users,
                           created_at, summary_json, data_quality_json, readiness_json
                    FROM recommendation_observation_snapshots WHERE snapshot_id IN (%s,%s)
                    """,
                    (left_id, right_id),
                )
                rows = {row["snapshot_id"]: snapshot_summary(row) for row in cursor.fetchall()}
        except Exception:
            app.logger.exception("observation snapshot comparison failed")
            return api_error("observation snapshots unavailable", "SNAPSHOT_DATABASE_ERROR", 503)
        finally:
            safe_close(conn)
        if left_id not in rows or right_id not in rows:
            return api_error("snapshot not found", "SNAPSHOT_NOT_FOUND", 404)
        left, right = rows[left_id], rows[right_id]
        fields = ("impressions", "clicks", "favorites", "repeat_visits", "ctr", "favorite_rate", "repeat_visit_rate")
        return api_success({
            "left": left, "right": right,
            "delta": {
                field: round(float(right["summary"].get(field) or 0) - float(left["summary"].get(field) or 0), 2)
                for field in fields
            },
            "same_algorithm_version": left["algorithm_version"] == right["algorithm_version"],
        })

    @app.route("/api/recommendation/metrics/websites", methods=["GET"])
    @admin_required
    def v1_recommendation_metrics_websites():
        try:
            where_sql, params, lookback_days = metric_filters(request.args)
            limit = max(1, min(int(request.args.get("limit", 100)), 500))
        except (TypeError, ValueError) as error:
            return api_error(str(error), "INVALID_METRIC_FILTER", 400)
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT e.website_id, MAX(w.name) AS name, MAX(w.url) AS url,
                      SUM(CASE WHEN e.event_type='impression' THEN 1 ELSE 0 END) AS impressions,
                      SUM(CASE WHEN e.event_type='click' THEN 1 ELSE 0 END) AS clicks,
                      SUM(CASE WHEN e.event_type='favorite' THEN 1 ELSE 0 END) AS favorites,
                      SUM(CASE WHEN e.event_type='repeat_visit' THEN 1 ELSE 0 END) AS repeat_visits
                    {METRIC_PROFILE_FROM}{where_sql}
                    GROUP BY e.website_id ORDER BY clicks DESC, favorites DESC, impressions DESC LIMIT %s
                    """,
                    [*params, limit],
                )
                rows = cursor.fetchall()
        finally:
            conn.close()
        return api_success({"lookback_days": lookback_days, "items": [metric_values(row) for row in rows]})

    @app.route("/api/recommendation/metrics/batches", methods=["GET"])
    @admin_required
    def v1_recommendation_metrics_batches():
        try:
            where_sql, params, lookback_days = metric_filters(request.args)
        except ValueError as error:
            return api_error(str(error), "INVALID_METRIC_FILTER", 400)
        batch_where = f"{where_sql} AND e.recommendation_batch_id IS NOT NULL"
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT e.recommendation_batch_id AS batch_id, MIN(e.created_at) AS first_seen_at,
                      MAX(COALESCE(qr.occupation, up.occupation, 'unknown')) AS occupation,
                      MAX(COALESCE(JSON_UNQUOTE(JSON_EXTRACT(qr.profile_json, '$.direction')), 'unknown')) AS direction,
                      MAX(COALESCE(JSON_UNQUOTE(JSON_EXTRACT(qr.profile_json, '$.primary_need')), 'unknown')) AS primary_need,
                      MAX(JSON_UNQUOTE(JSON_EXTRACT(e.metadata_json, '$.candidate_pool_id'))) AS candidate_pool_id,
                      MAX(JSON_UNQUOTE(JSON_EXTRACT(e.metadata_json, '$.display_batch_index'))) AS display_batch_index,
                      SUM(CASE WHEN e.event_type='impression' THEN 1 ELSE 0 END) AS impressions,
                      SUM(CASE WHEN e.event_type='click' THEN 1 ELSE 0 END) AS clicks,
                      SUM(CASE WHEN e.event_type='favorite' THEN 1 ELSE 0 END) AS favorites,
                      SUM(CASE WHEN e.event_type='repeat_visit' THEN 1 ELSE 0 END) AS repeat_visits,
                      SUM(CASE WHEN e.event_type='impression' AND JSON_UNQUOTE(JSON_EXTRACT(e.metadata_json, '$.personalization_type'))='personalized' THEN 1 ELSE 0 END) AS personalized_impressions,
                      SUM(CASE WHEN e.event_type='impression' AND JSON_UNQUOTE(JSON_EXTRACT(e.metadata_json, '$.personalization_type'))='general' THEN 1 ELSE 0 END) AS general_impressions
                      ,SUM(CASE WHEN e.event_type='impression' AND JSON_UNQUOTE(JSON_EXTRACT(e.metadata_json, '$.personalization_type'))='fallback' THEN 1 ELSE 0 END) AS fallback_impressions
                    {METRIC_PROFILE_FROM}{batch_where}
                    GROUP BY e.recommendation_batch_id ORDER BY first_seen_at ASC
                    """,
                    params,
                )
                batches = cursor.fetchall()
                cursor.execute(
                    f"""
                    SELECT e.recommendation_batch_id AS batch_id, e.website_id
                    {METRIC_PROFILE_FROM}{batch_where} AND e.event_type='impression'
                    GROUP BY e.recommendation_batch_id, e.website_id
                    """,
                    params,
                )
                impression_rows = cursor.fetchall()
                cursor.execute(
                    f"""
                    SELECT e.recommendation_batch_id AS batch_id, COUNT(DISTINCT t.id) AS tag_coverage
                    {METRIC_PROFILE_FROM}
                    LEFT JOIN site_tags st ON st.site_id=e.website_id
                    LEFT JOIN tags t ON t.id=st.tag_id
                    {batch_where} AND e.event_type='impression'
                    GROUP BY e.recommendation_batch_id
                    """,
                    params,
                )
                coverage_rows = cursor.fetchall()
        finally:
            conn.close()
        sites_by_batch = {}
        for row in impression_rows:
            sites_by_batch.setdefault(row["batch_id"], set()).add(row["website_id"])
        coverage_by_batch = {row["batch_id"]: int(row["tag_coverage"] or 0) for row in coverage_rows}
        previous_by_profile = {}
        items = []
        for row in batches:
            item = metric_values(row)
            batch_id = item["batch_id"]
            current_sites = sites_by_batch.get(batch_id, set())
            profile_key = "|".join(str(item.get(key) or "unknown") for key in ("occupation", "direction", "primary_need", "candidate_pool_id"))
            previous_sites = previous_by_profile.get(profile_key, set())
            overlap_count = len(current_sites & previous_sites)
            item["displayed_website_count"] = len(current_sites)
            item["tag_coverage"] = coverage_by_batch.get(batch_id, 0)
            item["batch_repeat_rate"] = round(overlap_count * 100 / len(current_sites), 2) if current_sites else 0
            item["personalized_ratio"] = round(
                int(item.get("personalized_impressions") or 0) * 100 / item["impressions"], 2
            ) if item["impressions"] else 0
            item["general_ratio"] = round(
                int(item.get("general_impressions") or 0) * 100 / item["impressions"], 2
            ) if item["impressions"] else 0
            item["fallback_ratio"] = round(
                int(item.get("fallback_impressions") or 0) * 100 / item["impressions"], 2
            ) if item["impressions"] else 0
            previous_by_profile[profile_key] = current_sites
            items.append(item)
        return api_success({"lookback_days": lookback_days, "items": items})

    @app.route("/api/recommendation/metrics/profile-overlap", methods=["GET"])
    @admin_required
    def v1_recommendation_metrics_profile_overlap():
        """Compare the most recently displayed Top16 for distinct profiles."""
        try:
            where_sql, params, lookback_days = metric_filters(request.args)
        except ValueError as error:
            return api_error(str(error), "INVALID_METRIC_FILTER", 400)
        overlap_where = f"{where_sql} AND e.event_type='impression' AND e.recommendation_batch_id IS NOT NULL"
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT e.recommendation_batch_id AS batch_id, e.website_id,
                      MIN(e.created_at) AS first_seen_at,
                      MAX(COALESCE(qr.occupation, up.occupation, 'unknown')) AS occupation,
                      MAX(COALESCE(JSON_UNQUOTE(JSON_EXTRACT(qr.profile_json, '$.direction')), 'unknown')) AS direction,
                      MAX(COALESCE(JSON_UNQUOTE(JSON_EXTRACT(qr.profile_json, '$.primary_need')), 'unknown')) AS primary_need
                    {METRIC_PROFILE_FROM}{overlap_where}
                    GROUP BY e.recommendation_batch_id, e.website_id
                    ORDER BY first_seen_at DESC
                    """,
                    params,
                )
                rows = cursor.fetchall()
        finally:
            conn.close()
        latest_by_profile = {}
        for row in rows:
            key = "|".join(str(row.get(field) or "unknown") for field in ("occupation", "direction", "primary_need"))
            batch = latest_by_profile.setdefault(key, {
                "profile": {field: row.get(field) or "unknown" for field in ("occupation", "direction", "primary_need")},
                "batch_id": row["batch_id"],
                "first_seen_at": row["first_seen_at"],
                "website_ids": set(),
            })
            # The query is newest-first; only retain the newest batch for a profile.
            if batch["batch_id"] == row["batch_id"]:
                batch["website_ids"].add(row["website_id"])
        profiles = list(latest_by_profile.values())[:50]
        pairs = []
        for index, left in enumerate(profiles):
            for right in profiles[index + 1:]:
                overlap_count = len(left["website_ids"] & right["website_ids"])
                smaller_pool = min(len(left["website_ids"]), len(right["website_ids"]))
                union = len(left["website_ids"] | right["website_ids"])
                pairs.append({
                    "left": {**left["profile"], "batch_id": left["batch_id"]},
                    "right": {**right["profile"], "batch_id": right["batch_id"]},
                    "overlap_count": overlap_count,
                    "overlap_rate": round(overlap_count * 100 / smaller_pool, 2) if smaller_pool else 0,
                    "jaccard_rate": round(overlap_count * 100 / union, 2) if union else 0,
                })
        return api_success({"lookback_days": lookback_days, "profiles": len(profiles), "items": pairs})

    @app.route("/api/me/behavior-summary", methods=["GET"])
    @jwt_required()
    def v1_my_behavior_summary():
        user = current_user_row()
        if not user:
            return api_error("user not found", 404, 404)
        try:
            summary, lookback_days = query_metric_summary(request.args, user_id=user["id"])
            websites, _ = query_metric_summary(request.args, user_id=user["id"], group_by="website")
        except ValueError as error:
            return api_error(str(error), "INVALID_METRIC_FILTER", 400)
        return api_success({
            "lookback_days": lookback_days,
            "summary": summary,
            "top_websites": websites[:20],
        })

    @app.route("/api/favorites", methods=["GET"])
    @jwt_required()
    def v1_favorites():
        started_at = perf_counter()
        try:
            user = current_user_row()
        except Exception:
            app.logger.exception("favorites user lookup failed")
            return api_error(
                "收藏服务暂时不可用，请稍后重试",
                "DATABASE_UNAVAILABLE",
                503,
            )
        if not user:
            return api_error("登录状态已失效，请重新登录", 401, 401)
        try:
            conn = get_db_connection()
        except Exception:
            app.logger.exception("favorites database connection failed")
            return api_error(
                "收藏服务暂时不可用，请稍后重试",
                "DATABASE_UNAVAILABLE",
                503,
            )
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        w.id, w.name, w.url, w.logo_url, w.summary, w.description,
                        w.category_id, w.is_free, w.need_login, w.region,
                        w.quality_score, w.recommend_level, w.click_count, w.clicks,
                        w.favorite_count, w.rating_avg, w.status, w.created_at,
                        w.updated_at, c.name AS category_name, f.note,
                        f.id AS favorite_id, f.created_at AS favorited_at
                    FROM favorites f
                    JOIN websites w ON w.id = f.site_id
                    LEFT JOIN categories c ON c.id = w.category_id
                    WHERE f.user_id = %s
                    ORDER BY f.created_at DESC
                    """,
                    (user["id"],),
                )
                rows = cursor.fetchall()
        except Exception:
            app.logger.exception("favorites list query failed")
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
            item["favoriteId"] = row.get("favorite_id")
            item["siteId"] = row["id"]
            item["logoUrl"] = row.get("logo_url") or ""
            item["categoryName"] = row.get("category_name") or ""
            item["favoritedAt"] = row.get("favorited_at")
            item["updatedAt"] = row.get("updated_at")
            items.append(item)
        app.logger.info(
            "Favorites loaded",
            extra={
                "user_id": user["id"],
                "count": len(items),
                "duration_ms": round((perf_counter() - started_at) * 1000, 2),
            },
        )
        return api_success(items)

    def resolve_favorite_site_id(cursor, data):
        raw_site_id = data.get("site_id") or data.get("siteId") or data.get("id")
        site_id = str(raw_site_id or "").strip()
        if site_id.isdigit():
            cursor.execute("SELECT id FROM websites WHERE id=%s LIMIT 1", (int(site_id),))
            return int(site_id) if cursor.fetchone() else None

        raw_url = data.get("url") or data.get("website_url") or data.get("link")
        url = str(raw_url or "").strip()
        if not url:
            return None

        try:
            parsed_url = urlsplit(url if "://" in url else f"https://{url}")
            parsed_hostname = parsed_url.hostname
            parsed_url.port
        except ValueError:
            return None
        hostname = (parsed_hostname or "").lower().removeprefix("www.")
        if not hostname:
            return None
        port = f":{parsed_url.port}" if parsed_url.port else ""
        path = parsed_url.path.rstrip("/") or "/"
        url_key = f"{hostname}{port}{path}"
        if parsed_url.query:
            url_key += f"?{parsed_url.query}"

        without_trailing_slash = url.rstrip("/")
        host_patterns = (
            f"https://{hostname}%",
            f"http://{hostname}%",
            f"https://www.{hostname}%",
            f"http://www.{hostname}%",
        )
        cursor.execute(
            """
            SELECT id, url
            FROM websites
            WHERE LOWER(url) IN (LOWER(%s), LOWER(%s))
               OR LOWER(url) LIKE LOWER(%s)
               OR LOWER(url) LIKE LOWER(%s)
               OR LOWER(url) LIKE LOWER(%s)
               OR LOWER(url) LIKE LOWER(%s)
            LIMIT 20
            """,
            (url, without_trailing_slash, *host_patterns),
        )
        for row in cursor.fetchall() or []:
            stored_url = str(row.get("url") or "").strip()
            parsed_stored_url = urlsplit(
                stored_url if "://" in stored_url else f"https://{stored_url}"
            )
            stored_hostname = (parsed_stored_url.hostname or "").lower().removeprefix(
                "www."
            )
            stored_port = f":{parsed_stored_url.port}" if parsed_stored_url.port else ""
            stored_path = parsed_stored_url.path.rstrip("/") or "/"
            stored_key = f"{stored_hostname}{stored_port}{stored_path}"
            if parsed_stored_url.query:
                stored_key += f"?{parsed_stored_url.query}"
            if stored_key == url_key:
                return int(row["id"])
        return None

    def favorite_reference_error(data):
        raw_site_id = data.get("site_id") or data.get("siteId") or data.get("id")
        raw_url = data.get("url") or data.get("website_url") or data.get("link")
        if raw_site_id and not str(raw_site_id).strip().isdigit():
            return api_error("网站信息不完整，暂时无法收藏", "INVALID_SITE", 422)
        if not str(raw_url or "").strip():
            return api_error("网站信息不完整，暂时无法收藏", "INVALID_SITE", 422)
        try:
            parsed_url = urlsplit(
                str(raw_url).strip()
                if "://" in str(raw_url).strip()
                else f"https://{str(raw_url).strip()}"
            )
            hostname = parsed_url.hostname
            parsed_url.port
        except ValueError:
            hostname = None
        if not hostname:
            return api_error("网站信息不完整，暂时无法收藏", "INVALID_SITE", 422)
        return api_error("该网站尚未录入资源库", "SITE_NOT_FOUND", 404)

    def safe_rollback(conn):
        if conn is None or not hasattr(conn, "rollback"):
            return
        try:
            conn.rollback()
        except Exception:
            app.logger.warning("favorite transaction rollback failed")

    def safe_close(conn):
        if conn is None:
            return
        try:
            conn.close()
        except Exception:
            app.logger.warning("favorite database connection close failed")

    def is_duplicate_favorite_error(error):
        error_args = getattr(error, "args", ()) or ()
        return (
            any(str(value) == "1062" for value in error_args)
            or "duplicate entry" in str(error).lower()
            or "duplicate key" in str(error).lower()
            or "unique constraint" in str(error).lower()
        )

    def favorite_database_error(action, error, conn=None):
        safe_rollback(conn)
        app.logger.exception(
            "favorite_%s database operation failed error_type=%s",
            action,
            type(error).__name__,
        )
        return api_error(
            "收藏服务暂时不可用，请稍后重试",
            "FAVORITE_DATABASE_ERROR",
            503,
        )

    def favorite_user_or_error():
        try:
            user = current_user_row()
        except Exception as error:
            return None, favorite_database_error("auth", error)
        if not user:
            return None, api_error("请先登录后操作收藏", "AUTH_REQUIRED", 401)
        return user, None

    def favorite_record_payload(favorite_id, site_id):
        return {
            "id": favorite_id,
            "favoriteId": favorite_id,
            "favorite_id": favorite_id,
            "siteId": site_id,
            "site_id": site_id,
        }

    def insert_favorite(user_id, site_id, note, has_favorite_count, timing):
        try:
            conn = get_db_connection()
        except Exception as error:
            return None, False, favorite_database_error("add", error)

        inserted = False
        favorite_id = None
        try:
            with conn.cursor() as cursor:
                timing["favorite_lookup_started"] = perf_counter()
                cursor.execute(
                    "SELECT id FROM favorites WHERE user_id=%s AND site_id=%s LIMIT 1",
                    (user_id, site_id),
                )
                existing = cursor.fetchone()
                timing["favorite_lookup_finished"] = perf_counter()
                if existing:
                    favorite_id = existing.get("id")
                else:
                    try:
                        cursor.execute(
                            "INSERT INTO favorites (user_id, site_id, note) VALUES (%s,%s,%s)",
                            (user_id, site_id, note),
                        )
                    except Exception as error:
                        if not is_duplicate_favorite_error(error):
                            raise
                        safe_rollback(conn)
                        cursor.execute(
                            "SELECT id FROM favorites WHERE user_id=%s AND site_id=%s LIMIT 1",
                            (user_id, site_id),
                        )
                        existing = cursor.fetchone()
                        if not existing:
                            raise
                        favorite_id = existing.get("id")
                    else:
                        inserted = True
                        favorite_id = getattr(cursor, "lastrowid", None)
                        if has_favorite_count:
                            cursor.execute(
                                "UPDATE websites SET favorite_count=COALESCE(favorite_count,0)+1 WHERE id=%s",
                                (site_id,),
                            )
                        if favorite_id is None:
                            cursor.execute(
                                "SELECT id FROM favorites WHERE user_id=%s AND site_id=%s LIMIT 1",
                                (user_id, site_id),
                            )
                            created_record = cursor.fetchone()
                            favorite_id = created_record.get("id") if created_record else None
                timing["favorite_lookup_finished"] = perf_counter()
            timing["commit_started"] = perf_counter()
            conn.commit()
            timing["commit_finished"] = perf_counter()
            return favorite_id, inserted, None
        except Exception as error:
            return None, False, favorite_database_error("add", error, conn)
        finally:
            safe_close(conn)

    def delete_favorite(user_id, site_id, has_favorite_count, timing):
        try:
            conn = get_db_connection()
        except Exception as error:
            return False, favorite_database_error("remove", error)

        removed = False
        try:
            with conn.cursor() as cursor:
                timing["favorite_lookup_started"] = perf_counter()
                cursor.execute(
                    "DELETE FROM favorites WHERE user_id=%s AND site_id=%s",
                    (user_id, site_id),
                )
                removed = bool(cursor.rowcount)
                timing["favorite_lookup_finished"] = perf_counter()
                if removed and has_favorite_count:
                    cursor.execute(
                        "UPDATE websites SET favorite_count=GREATEST(COALESCE(favorite_count,0)-1,0) WHERE id=%s",
                        (site_id,),
                    )
            timing["commit_started"] = perf_counter()
            conn.commit()
            timing["commit_finished"] = perf_counter()
            return removed, None
        except Exception as error:
            return False, favorite_database_error("remove", error, conn)
        finally:
            safe_close(conn)

    @app.route("/api/favorites", methods=["POST"])
    @jwt_required()
    def v1_add_favorite_by_reference():
        timing = {"started": perf_counter()}
        user, user_error = favorite_user_or_error()
        timing["auth_finished"] = perf_counter()
        if user_error:
            return user_error
        data = request.get_json(silent=True) or {}
        timing["schema_started"] = perf_counter()
        has_favorite_count = "favorite_count" in table_columns("websites")
        timing["schema_finished"] = perf_counter()
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                timing["site_lookup_started"] = perf_counter()
                site_id = resolve_favorite_site_id(cursor, data)
                timing["site_lookup_finished"] = perf_counter()
        except Exception as error:
            return favorite_database_error("add", error, conn)
        finally:
            safe_close(conn)
        if not site_id:
            return favorite_reference_error(data)
        favorite_id, inserted, database_error = insert_favorite(
            user["id"], site_id, data.get("note"), has_favorite_count, timing
        )
        if database_error:
            return database_error
        if inserted:
            record_unified_behavior(
                user["id"], site_id, "favorite", str(data.get("source") or "favorite").strip().lower(),
                data, dedupe=True,
            )
        log_favorite_timing("add", timing, site_id)
        return api_success(
            {
                "favorited": True,
                "created": inserted,
                "alreadyExists": not inserted,
                "site_id": site_id,
                "favorite": favorite_record_payload(favorite_id, site_id),
            }
        )

    @app.route("/api/favorites", methods=["DELETE"])
    @jwt_required()
    def v1_remove_favorite_by_reference():
        timing = {"started": perf_counter()}
        user, user_error = favorite_user_or_error()
        timing["auth_finished"] = perf_counter()
        if user_error:
            return user_error
        data = request.get_json(silent=True) or {}
        timing["schema_started"] = perf_counter()
        has_favorite_count = "favorite_count" in table_columns("websites")
        timing["schema_finished"] = perf_counter()
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                timing["site_lookup_started"] = perf_counter()
                site_id = resolve_favorite_site_id(cursor, data)
                timing["site_lookup_finished"] = perf_counter()
        except Exception as error:
            return favorite_database_error("remove", error, conn)
        finally:
            safe_close(conn)
        if not site_id:
            return favorite_reference_error(data)
        removed, database_error = delete_favorite(
            user["id"], site_id, has_favorite_count, timing
        )
        if database_error:
            return database_error
        log_favorite_timing("remove", timing, site_id)
        return api_success(
            {
                "favorited": False,
                "removed": removed,
                "alreadyRemoved": not removed,
                "site_id": site_id,
            }
        )

    @app.route("/api/sites/<int:site_id>/favorite", methods=["POST"])
    @jwt_required()
    def v1_add_favorite(site_id):
        timing = {"started": perf_counter()}
        user, user_error = favorite_user_or_error()
        timing["auth_finished"] = perf_counter()
        if user_error:
            return user_error
        data = request.get_json(silent=True) or {}
        timing["schema_started"] = perf_counter()
        has_favorite_count = "favorite_count" in table_columns("websites")
        timing["schema_finished"] = perf_counter()
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                timing["site_lookup_started"] = perf_counter()
                cursor.execute("SELECT id FROM websites WHERE id=%s LIMIT 1", (site_id,))
                website = cursor.fetchone()
                timing["site_lookup_finished"] = perf_counter()
        except Exception as error:
            return favorite_database_error("add", error, conn)
        finally:
            safe_close(conn)
        if not website:
            return api_error("该网站尚未录入资源库", "SITE_NOT_FOUND", 404)
        favorite_id, inserted, database_error = insert_favorite(
            user["id"], site_id, data.get("note"), has_favorite_count, timing
        )
        if database_error:
            return database_error
        if inserted:
            record_unified_behavior(
                user["id"], site_id, "favorite", str(data.get("source") or "favorite").strip().lower(),
                data, dedupe=True,
            )
        log_favorite_timing("add", timing, site_id)
        return api_success(
            {
                "favorited": True,
                "created": inserted,
                "alreadyExists": not inserted,
                "favorite": favorite_record_payload(favorite_id, site_id),
            }
        )

    @app.route("/api/sites/<int:site_id>/favorite", methods=["DELETE"])
    @jwt_required()
    def v1_remove_favorite(site_id):
        timing = {"started": perf_counter()}
        user, user_error = favorite_user_or_error()
        timing["auth_finished"] = perf_counter()
        if user_error:
            return user_error
        timing["schema_started"] = perf_counter()
        has_favorite_count = "favorite_count" in table_columns("websites")
        timing["schema_finished"] = perf_counter()
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                timing["site_lookup_started"] = perf_counter()
                cursor.execute("SELECT id FROM websites WHERE id=%s LIMIT 1", (site_id,))
                website = cursor.fetchone()
                timing["site_lookup_finished"] = perf_counter()
        except Exception as error:
            return favorite_database_error("remove", error, conn)
        finally:
            safe_close(conn)
        if not website:
            return api_error("该网站尚未录入资源库", "SITE_NOT_FOUND", 404)
        removed, database_error = delete_favorite(
            user["id"], site_id, has_favorite_count, timing
        )
        if database_error:
            return database_error
        log_favorite_timing("remove", timing, site_id)
        return api_success(
            {
                "favorited": False,
                "removed": removed,
                "alreadyRemoved": not removed,
                "site_id": site_id,
            }
        )

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

    @app.route("/api/sites/search", methods=["GET"])
    @app.route("/api/search", methods=["GET"])
    def v1_search():
        started_at = perf_counter()
        query = normalize_search_query(request.args.get("q"))
        if not query:
            return api_error("请输入有效的搜索关键词", "INVALID_SEARCH_QUERY", 400)
        if len(query) > 100:
            return api_error("搜索关键词不能超过100个字符", "SEARCH_QUERY_TOO_LONG", 400)
        sort = normalize_search_query(request.args.get("sort") or "relevance").lower()
        if sort not in SEARCH_SORTS:
            return api_error("不支持的搜索排序方式", "INVALID_SEARCH_SORT", 400)
        try:
            page = int(request.args.get("page", 1))
            page_size = int(
                request.args.get(
                    "page_size",
                    request.args.get("per_page", request.args.get("limit", 20)),
                )
            )
        except (TypeError, ValueError):
            return api_error("分页参数无效", "INVALID_SEARCH_PAGINATION", 400)
        if page < 1 or page_size < 1:
            return api_error("分页参数无效", "INVALID_SEARCH_PAGINATION", 400)
        page_size = min(page_size, 50)
        category = normalize_search_query(
            request.args.get("category")
            or request.args.get("category_code")
            or request.args.get("category_id")
        )

        try:
            ranked, category_row, relaxed, cached = cached_site_search(
                query, category, sort
            )
        except ValueError:
            return api_error("搜索分类无效", "INVALID_SEARCH_CATEGORY", 400)
        except Exception as error:
            app.logger.exception(
                "site search failed error_type=%s query_length=%s",
                type(error).__name__,
                len(query),
            )
            if not is_search_database_unavailable(error):
                return api_error(
                    "搜索处理失败，请稍后重试",
                    "SEARCH_INTERNAL_ERROR",
                    500,
                )
            return api_error(
                "搜索服务暂时不可用，请稍后重试",
                "SEARCH_DATABASE_ERROR",
                503,
            )

        total = len(ranked)
        total_pages = (total + page_size - 1) // page_size if total else 0
        offset = (page - 1) * page_size
        items = ranked[offset : offset + page_size]
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        app.logger.info(
            "site_search query_length=%s total=%s cached=%s duration_ms=%.2f",
            len(query),
            total,
            cached,
            duration_ms,
        )
        return api_success(
            {
                "query": query,
                "items": items,
                "category": {
                    "id": category_row.get("id"),
                    "code": category_row.get("code")
                    or category_code_for_name(category_row.get("name")),
                    "name": category_row.get("name"),
                }
                if category_row
                else None,
                "sort": sort,
                "relaxed": relaxed,
                "cached": cached,
                "dataVersion": SEARCH_DATA_VERSION,
                "durationMs": duration_ms,
                "pagination": {
                    "page": page,
                    "pageSize": page_size,
                    "total": total,
                    "totalPages": total_pages,
                    "hasMore": page < total_pages,
                },
            }
        )

    @app.route("/api/sites/search/suggest", methods=["GET"])
    @app.route("/api/search/suggest", methods=["GET"])
    def v1_search_suggest():
        query = normalize_search_query(request.args.get("q"))
        if not query:
            return api_success({"items": [], "sites": [], "categories": [], "hotKeywords": []})
        if len(query) > 100:
            return api_error("搜索关键词不能超过100个字符", "SEARCH_QUERY_TOO_LONG", 400)
        try:
            ranked, _, _, _ = cached_site_search(query, "", "relevance")
            site_items = [
                {
                    "type": "site",
                    "id": item.get("id"),
                    "siteId": item.get("id"),
                    "name": item.get("name"),
                    "url": item.get("url"),
                    "logoUrl": item.get("logoUrl") or item.get("logo_url"),
                    "categoryName": item.get("categoryName")
                    or item.get("category_name"),
                }
                for item in ranked[:5]
            ]
            category_rows = search_category_suggestions(query, limit=2)
        except Exception as error:
            app.logger.exception(
                "site search suggestions failed error_type=%s", type(error).__name__
            )
            if not is_search_database_unavailable(error):
                return api_error(
                    "搜索建议处理失败，请稍后重试",
                    "SEARCH_INTERNAL_ERROR",
                    500,
                )
            return api_error(
                "搜索服务暂时不可用，请稍后重试",
                "SEARCH_DATABASE_ERROR",
                503,
            )
        category_items = [
            {
                "type": "category",
                "id": item.get("id"),
                "name": item.get("name"),
                "code": item.get("code")
                or category_code_for_name(item.get("name")),
            }
            for item in category_rows[:2]
        ]
        hot_keywords = [
            "AI编程",
            "前端框架",
            "论文写作",
            "图片素材",
            "数据分析",
            "原型设计",
            "在线学习",
            "PPT模板",
        ]
        hot_item = next(
            (
                {"type": "keyword", "name": keyword}
                for keyword in hot_keywords
                if query.casefold() in keyword.casefold()
            ),
            {"type": "keyword", "name": hot_keywords[0]},
        )
        combined = [*site_items, *category_items, hot_item][:8]
        return api_success(
            {
                "items": combined,
                "sites": site_items,
                "categories": category_items,
                "hotKeywords": [hot_item["name"]],
            }
        )

    @app.route("/api/search/hot-keywords", methods=["GET"])
    def v1_hot_keywords():
        return api_success(
            [
                "AI编程",
                "前端框架",
                "论文写作",
                "图片素材",
                "数据分析",
                "原型设计",
                "在线学习",
                "PPT模板",
            ]
        )

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
