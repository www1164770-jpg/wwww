"""Personalization settings routes and server-side validation.

The module deliberately keeps user configuration in one versioned JSON document.
It lets the visual system evolve without scattering nullable columns across ``users``
and never accepts an arbitrary CSS string from the browser.
"""

import io
import json
import re
from copy import deepcopy
from datetime import datetime

from flask import jsonify, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required



HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
BACKGROUND_TYPES = {"default", "color", "gradient", "image", "theme"}
TEXT_MODES = {"auto", "light", "dark", "custom"}
SIZE_MODES = {"cover", "contain", "stretch", "repeat"}
THEME_KEYS = {"default", "ocean", "forest", "starlight", "night", "sunset", "minimal-gray", "sakura"}

DEFAULT_SETTINGS = {
    "version": 1,
    "background": {"type": "default", "color": "#F8FAFC", "imageId": None, "size": "cover", "position": "center center", "overlay": 0, "brightness": 100, "blur": 0, "desktop": {"positionX": 50, "positionY": 50, "scale": 1, "rotation": 0}, "mobile": {"positionX": 50, "positionY": 50, "scale": 1, "rotation": 0}, "analysis": {}},
    "gradient": {"angle": 135, "stops": [{"color": "#7DD3FC", "position": 0}, {"color": "#A78BFA", "position": 100}]},
    "typography": {"mode": "auto", "color": "#253044"},
    "card": {"color": "#FFFFFF", "opacity": 88, "blur": 18, "border": 12, "shadow": 18},
    "themeKey": "default",
    "customThemes": [],
    "favorites": [],
    "recent": [],
}


def default_settings():
    return deepcopy(DEFAULT_SETTINGS)


def _number(value, minimum, maximum, fallback):
    if isinstance(value, bool):
        return fallback
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    if number < minimum or number > maximum:
        return fallback
    return int(number) if number.is_integer() else round(number, 2)


def _hex(value, fallback):
    value = str(value or "").upper()
    return value if HEX_RE.fullmatch(value) else fallback


def _composition(value):
    value = value if isinstance(value, dict) else {}
    return {
        "positionX": _number(value.get("positionX"), 0, 100, 50),
        "positionY": _number(value.get("positionY"), 0, 100, 50),
        "scale": _number(value.get("scale"), 0.5, 3, 1),
        "rotation": _number(value.get("rotation"), -180, 180, 0),
    }


def _analysis(value):
    if not isinstance(value, dict):
        return {}
    mode = value.get("recommendedTextMode")
    return {
        "averageLuminance": _number(value.get("averageLuminance"), 0, 1, 0.5),
        "darkRatio": _number(value.get("darkRatio"), 0, 1, 0),
        "lightRatio": _number(value.get("lightRatio"), 0, 1, 0),
        "contrastSpread": _number(value.get("contrastSpread"), 0, 1, 0),
        "recommendedTextMode": mode if mode in {"light", "dark"} else "dark",
    }


def normalize_settings(payload):
    """Return a safe settings document or raise ValueError for invalid structures."""
    if not isinstance(payload, dict):
        raise ValueError("设置数据格式不正确")
    result = default_settings()
    background = payload.get("background", {})
    if not isinstance(background, dict):
        raise ValueError("背景设置格式不正确")
    background_type = background.get("type", result["background"]["type"])
    if background_type not in BACKGROUND_TYPES:
        raise ValueError("不支持的背景类型")
    result["background"].update({
        "type": background_type,
        "color": _hex(background.get("color"), result["background"]["color"]),
        "imageId": int(background["imageId"]) if str(background.get("imageId") or "").isdigit() else None,
        "size": background.get("size") if background.get("size") in SIZE_MODES else "cover",
        "position": str(background.get("position") or "center center")[:40],
        "overlay": _number(background.get("overlay"), 0, 70, 0),
        "brightness": _number(background.get("brightness"), 40, 160, 100),
        "blur": _number(background.get("blur"), 0, 20, 0),
        "desktop": _composition(background.get("desktop")),
        "mobile": _composition(background.get("mobile")),
        "analysis": _analysis(background.get("analysis")),
    })
    gradient = payload.get("gradient", {})
    stops = gradient.get("stops", []) if isinstance(gradient, dict) else []
    if stops and (not isinstance(stops, list) or not 2 <= len(stops) <= 12):
        raise ValueError("渐变至少需要 2 个、最多 12 个颜色节点")
    if stops:
        normalized_stops = []
        for stop in stops:
            if not isinstance(stop, dict) or not HEX_RE.fullmatch(str(stop.get("color") or "")):
                raise ValueError("渐变颜色格式不正确")
            position = _number(stop.get("position"), 0, 100, -1)
            if position < 0:
                raise ValueError("渐变节点位置必须在 0 到 100 之间")
            normalized_stops.append({"color": str(stop["color"]).upper(), "position": position})
        result["gradient"]["stops"] = sorted(normalized_stops, key=lambda item: item["position"])
    if isinstance(gradient, dict):
        result["gradient"]["angle"] = _number(gradient.get("angle"), 0, 360, 135)
    typography = payload.get("typography", {})
    if isinstance(typography, dict):
        mode = typography.get("mode", "auto")
        result["typography"] = {"mode": mode if mode in TEXT_MODES else "auto", "color": _hex(typography.get("color"), "#253044")}
    card = payload.get("card", {})
    if isinstance(card, dict):
        result["card"] = {
            "color": _hex(card.get("color"), "#FFFFFF"),
            "opacity": _number(card.get("opacity"), 35, 100, 88),
            "blur": _number(card.get("blur"), 0, 32, 18),
            "border": _number(card.get("border"), 0, 40, 12),
            "shadow": _number(card.get("shadow"), 0, 50, 18),
        }
    theme_key = str(payload.get("themeKey") or "default")
    result["themeKey"] = theme_key if theme_key in THEME_KEYS else "default"
    result["customThemes"] = _normalize_custom_themes(payload.get("customThemes", []))
    result["favorites"] = _normalize_keys(payload.get("favorites", []), 20)
    result["recent"] = _normalize_keys(payload.get("recent", []), 3)
    return result


def _normalize_keys(values, maximum):
    if not isinstance(values, list):
        return []
    return list(dict.fromkeys(str(item)[:80] for item in values if str(item).strip()))[:maximum]


def _legacy_favorite_keys(value):
    """Read the old JSON favorites without treating it as account authority."""
    return _normalize_keys(value, 20)


def _normalize_custom_themes(values):
    if not isinstance(values, list):
        return []
    result = []
    for value in values[:5]:
        if not isinstance(value, dict):
            continue
        key = str(value.get("key") or "").strip()[:80]
        name = str(value.get("name") or "").strip()[:30]
        settings = value.get("settings")
        if key and name and isinstance(settings, dict):
            result.append({"key": key, "name": name, "settings": normalize_settings({**settings, "customThemes": []})})
    return result


def register_personalization_routes(app, get_db_connection):
    def response(data=None, msg="成功", status=200):
        return jsonify({"code": 0 if status < 400 else status, "msg": msg, "data": data or {}}), status

    def current_user():
        identity = str(get_jwt_identity() or "").strip()
        if not identity:
            return None
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE (username=%s OR email=%s OR id=%s) AND deleted_at IS NULL LIMIT 1", (identity, identity, identity if identity.isdigit() else -1))
                return cursor.fetchone()
        finally:
            conn.close()

    def load_settings(user_id):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT settings_json FROM user_personalization_settings WHERE user_id=%s", (user_id,))
                row = cursor.fetchone()
            if not row:
                settings = default_settings()
                settings["favorites"] = load_theme_favorites(user_id)
                return settings
            raw = row.get("settings_json") if isinstance(row, dict) else row[0]
            settings = normalize_settings(json.loads(raw))
            settings["favorites"] = load_theme_favorites(user_id, settings["favorites"])
            return settings
        except (json.JSONDecodeError, ValueError, TypeError):
            return default_settings()
        finally:
            conn.close()

    def load_theme_favorites(user_id, legacy_favorites=()):
        """Return table-backed favorites, importing legacy JSON only once."""
        legacy = _legacy_favorite_keys(legacy_favorites)
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT theme_key FROM user_theme_favorites WHERE user_id=%s ORDER BY created_at, id",
                    (user_id,),
                )
                rows = cursor.fetchall()
                if not rows and legacy:
                    cursor.executemany(
                        "INSERT IGNORE INTO user_theme_favorites (user_id, theme_key) VALUES (%s,%s)",
                        [(user_id, key[:64]) for key in legacy],
                    )
                    conn.commit()
                    cursor.execute(
                        "SELECT theme_key FROM user_theme_favorites WHERE user_id=%s ORDER BY created_at, id",
                        (user_id,),
                    )
                    rows = cursor.fetchall()
                return _normalize_keys(
                    [row.get("theme_key") if isinstance(row, dict) else row[0] for row in rows],
                    20,
                )
        except Exception:
            # A rollout with code ahead of the migration remains readable from
            # the old document; normal migrated deployments use the table.
            try:
                conn.rollback()
            except Exception:
                pass
            return legacy
        finally:
            conn.close()

    def save_settings(user_id, settings):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Account favorites now have their own table. Keep the legacy
                # JSON value intact so a settings PUT can never erase it.
                cursor.execute(
                    "SELECT settings_json FROM user_personalization_settings WHERE user_id=%s",
                    (user_id,),
                )
                existing = cursor.fetchone()
                stored = deepcopy(settings)
                if existing:
                    raw = existing.get("settings_json") if isinstance(existing, dict) else existing[0]
                    try:
                        stored["favorites"] = _legacy_favorite_keys(json.loads(raw).get("favorites", []))
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        stored["favorites"] = []
                cursor.execute("""INSERT INTO user_personalization_settings (user_id, settings_json)
                    VALUES (%s,%s) ON DUPLICATE KEY UPDATE settings_json=VALUES(settings_json), updated_at=CURRENT_TIMESTAMP""", (user_id, json.dumps(stored, ensure_ascii=False, separators=(",", ":"))))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @app.route("/api/personalization", methods=["GET"])
    @jwt_required()
    def get_personalization():
        user = current_user()
        if not user:
            return response(msg="登录状态已失效，请重新登录", status=401)
        try:
            return response(load_settings(user["id"]))
        except Exception:
            app.logger.exception("Unable to read personalization settings")
            return response(msg="个性化设置读取失败，请稍后重试", status=500)

    @app.route("/api/personalization", methods=["PUT"])
    @jwt_required()
    def put_personalization():
        user = current_user()
        if not user:
            return response(msg="登录状态已失效，请重新登录", status=401)
        try:
            settings = normalize_settings(request.get_json(silent=True) or {})
            save_settings(user["id"], settings)
            return response(settings, "设置已保存")
        except ValueError as exc:
            return response(msg=str(exc), status=400)
        except Exception:
            app.logger.exception("Unable to save personalization settings")
            return response(msg="个性化设置保存失败，请稍后重试", status=500)

    @app.route("/api/personalization/themes", methods=["GET", "POST"])
    @jwt_required()
    def personalization_themes():
        user = current_user()
        if not user:
            return response(msg="登录状态已失效，请重新登录", status=401)
        settings = load_settings(user["id"])
        if request.method == "GET":
            return response(settings["customThemes"])
        try:
            themes = settings["customThemes"]
            if len(themes) >= 5:
                return response(msg="我的主题最多保存 5 个", status=400)
            theme = _normalize_custom_themes([request.get_json(silent=True) or {}])
            if not theme:
                return response(msg="主题内容不合法", status=400)
            themes.append(theme[0]); settings["customThemes"] = themes
            save_settings(user["id"], settings)
            return response(theme[0], "主题已保存", 201)
        except ValueError as exc:
            return response(msg=str(exc), status=400)

    @app.route("/api/personalization/themes/<theme_key>", methods=["PATCH", "DELETE"])
    @jwt_required()
    def personalization_theme(theme_key):
        user = current_user()
        if not user:
            return response(msg="登录状态已失效，请重新登录", status=401)
        settings = load_settings(user["id"])
        index = next((i for i, item in enumerate(settings["customThemes"]) if item["key"] == theme_key), None)
        if index is None:
            return response(msg="主题不存在或无权访问", status=404)
        if request.method == "DELETE":
            settings["customThemes"].pop(index); save_settings(user["id"], settings)
            return response(msg="主题已删除")
        candidate = _normalize_custom_themes([{**settings["customThemes"][index], **(request.get_json(silent=True) or {}), "key": theme_key}])
        if not candidate:
            return response(msg="主题内容不合法", status=400)
        settings["customThemes"][index] = candidate[0]; save_settings(user["id"], settings)
        return response(candidate[0], "主题已更新")

    @app.route("/api/personalization/theme-favorites/<theme_key>", methods=["POST", "DELETE"])
    @jwt_required()
    def personalization_favorite(theme_key):
        user = current_user()
        if not user:
            return response(msg="登录状态已失效，请重新登录", status=401)
        key = str(theme_key or "").strip()
        if not key or len(key) > 64:
            return response(msg="Invalid theme key", status=400)
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                if request.method == "POST":
                    cursor.execute(
                        "INSERT IGNORE INTO user_theme_favorites (user_id, theme_key) VALUES (%s,%s)",
                        (user["id"], key),
                    )
                else:
                    cursor.execute(
                        "DELETE FROM user_theme_favorites WHERE user_id=%s AND theme_key=%s",
                        (user["id"], key),
                    )
            conn.commit()
        except Exception:
            conn.rollback()
            app.logger.exception("Unable to update personalization theme favorite")
            return response(msg="Unable to save theme favorite", status=500)
        finally:
            conn.close()
        return response(load_theme_favorites(user["id"]))

    @app.route("/api/personalization/backgrounds", methods=["GET", "POST"])
    @jwt_required()
    def personalization_backgrounds():
        user = current_user()
        if not user:
            return response(msg="登录状态已失效，请重新登录", status=401)
        if request.method == "GET":
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id, original_name, mime_type, file_size, width, height, privacy, analysis_json, created_at FROM user_backgrounds WHERE user_id=%s AND status='active' ORDER BY created_at DESC", (user["id"],))
                    rows = cursor.fetchall()
                return response([{**dict(row), "analysis": json.loads(row.get("analysis_json") or "{}"), "url": f"/api/personalization/backgrounds/{row['id']}/file"} for row in rows])
            finally: conn.close()
        # Pillow is intentionally imported only for uploads so reads of the
        # lightweight settings API do not depend on the image stack.
        from backend.background_config import BACKGROUND_UPLOAD_FIELD, BACKGROUND_UPLOAD_ROOT
        from backend.background_image_service import BackgroundImageAnalysisError, BackgroundUploadTooLarge, InvalidBackgroundImage, process_background_upload
        from backend.background_storage import BackgroundStorageError, delete_background_file, store_processed_background
        upload = request.files.get(BACKGROUND_UPLOAD_FIELD)
        if not upload or not upload.filename:
            app.logger.warning("Background upload rejected code=UPLOAD_FILE_EMPTY user_id=%s", user["id"])
            return response({"error_code": "UPLOAD_FILE_EMPTY"}, msg="请选择 JPG、JPEG、PNG 或 WEBP 图片", status=400)
        app.logger.info(
            "Background upload received user_id=%s filename=%r content_type=%s request_size=%s file_size=%s",
            user["id"], upload.filename[:255], upload.content_type, request.content_length, upload.content_length,
        )
        conn = None; stored_path = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS total FROM user_backgrounds WHERE user_id=%s AND status='active'", (user["id"],))
                count = cursor.fetchone()["total"]
            if count >= 5: return response({"error_code": "UPLOAD_LIMIT_REACHED"}, msg="我的背景最多保存 5 张", status=400)
            processed = process_background_upload(upload.stream, upload.filename, upload.content_length)
            app.logger.info("Background upload processed user_id=%s width=%s height=%s output_size=%s", user["id"], processed.width, processed.height, processed.file_size)
            stored_path = store_processed_background(processed, user["id"], BACKGROUND_UPLOAD_ROOT)
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO user_backgrounds (user_id,storage_path,original_name,mime_type,file_size,width,height,status,privacy,analysis_json) VALUES (%s,%s,%s,%s,%s,%s,%s,'active','private',%s)", (user["id"], stored_path, upload.filename[:255], processed.mime_type, processed.file_size, processed.width, processed.height, json.dumps(processed.analysis or {})))
                background_id = cursor.lastrowid
            conn.commit()
            app.logger.info("Background upload committed user_id=%s background_id=%s", user["id"], background_id)
            return response({"id": background_id, "url": f"/api/personalization/backgrounds/{background_id}/file", "width": processed.width, "height": processed.height, "analysis": processed.analysis or {}}, "背景已上传", 201)
        except BackgroundUploadTooLarge:
            app.logger.warning("Background upload rejected code=UPLOAD_TOO_LARGE user_id=%s filename=%r", user["id"], upload.filename[:255])
            return response({"error_code": "UPLOAD_TOO_LARGE"}, msg="图片不能超过 10MB", status=413)
        except InvalidBackgroundImage as error:
            app.logger.warning("Background upload rejected code=%s user_id=%s filename=%r cause=%s", error.error_code, user["id"], upload.filename[:255], type(error.__cause__).__name__ if error.__cause__ else type(error).__name__)
            message = "图片文件损坏" if error.error_code == "UPLOAD_PIL_FAILED" else "图片格式或内容不合法，仅支持 JPG、JPEG、PNG、WEBP"
            return response({"error_code": error.error_code}, msg=message, status=415)
        except BackgroundImageAnalysisError:
            if conn: conn.rollback()
            if stored_path: delete_background_file(BACKGROUND_UPLOAD_ROOT, stored_path)
            app.logger.exception("Background upload failed code=UPLOAD_ANALYSIS_FAILED user_id=%s", user["id"])
            return response({"error_code": "UPLOAD_ANALYSIS_FAILED"}, msg="背景分析失败", status=500)
        except BackgroundStorageError as error:
            if conn: conn.rollback()
            if stored_path: delete_background_file(BACKGROUND_UPLOAD_ROOT, stored_path)
            permission_denied = isinstance(error.__cause__, PermissionError)
            error_code = "UPLOAD_PERMISSION_DENIED" if permission_denied else "UPLOAD_SAVE_FAILED"
            app.logger.exception("Background upload failed code=%s user_id=%s", error_code, user["id"])
            return response({"error_code": error_code}, msg="背景文件保存失败", status=500)
        except Exception:
            if conn: conn.rollback()
            if stored_path: delete_background_file(BACKGROUND_UPLOAD_ROOT, stored_path)
            app.logger.exception("Background upload failed code=UPLOAD_DB_FAILED user_id=%s", user["id"])
            return response({"error_code": "UPLOAD_DB_FAILED"}, msg="背景记录保存失败", status=500)
        finally:
            if conn: conn.close()

    @app.route("/api/personalization/backgrounds/<int:background_id>", methods=["DELETE"])
    @jwt_required()
    def delete_personalization_background(background_id):
        from backend.background_config import BACKGROUND_UPLOAD_ROOT
        from backend.background_storage import delete_background_file
        user = current_user()
        if not user: return response(msg="登录状态已失效，请重新登录", status=401)
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT storage_path FROM user_backgrounds WHERE id=%s AND user_id=%s AND status='active'", (background_id, user["id"]))
                item = cursor.fetchone()
                if not item: return response(msg="背景不存在或无权访问", status=404)
                cursor.execute("UPDATE user_backgrounds SET status='deleted' WHERE id=%s AND user_id=%s", (background_id, user["id"]))
                # Do not leave a saved setting referring to a deleted private file.
                cursor.execute("SELECT settings_json FROM user_personalization_settings WHERE user_id=%s FOR UPDATE", (user["id"],))
                saved = cursor.fetchone()
                if saved:
                    raw = saved.get("settings_json") if isinstance(saved, dict) else saved[0]
                    try:
                        next_settings = normalize_settings(json.loads(raw))
                    except (json.JSONDecodeError, ValueError, TypeError):
                        next_settings = default_settings()
                    if str(next_settings["background"].get("imageId") or "") == str(background_id):
                        next_settings["background"] = default_settings()["background"]
                        cursor.execute(
                            "UPDATE user_personalization_settings SET settings_json=%s, updated_at=CURRENT_TIMESTAMP WHERE user_id=%s",
                            (json.dumps(next_settings, ensure_ascii=False, separators=(",", ":")), user["id"]),
                        )
            conn.commit(); delete_background_file(BACKGROUND_UPLOAD_ROOT, item["storage_path"])
            return response(msg="背景已删除")
        except Exception:
            conn.rollback(); app.logger.exception("Unable to delete personalization background")
            return response(msg="背景删除失败，请稍后重试", status=500)
        finally: conn.close()

    @app.route("/api/personalization/backgrounds/<int:background_id>/privacy", methods=["PATCH"])
    @jwt_required()
    def update_personalization_background_privacy(background_id):
        user = current_user()
        privacy = (request.get_json(silent=True) or {}).get("privacy")
        if not user: return response(msg="登录状态已失效，请重新登录", status=401)
        if privacy not in {"private", "public"}: return response(msg="隐私设置不合法", status=400)
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE user_backgrounds SET privacy=%s WHERE id=%s AND user_id=%s AND status='active'", (privacy, background_id, user["id"]))
                if cursor.rowcount != 1: return response(msg="背景不存在或无权访问", status=404)
            conn.commit(); return response({"id": background_id, "privacy": privacy}, "背景隐私已更新")
        except Exception:
            conn.rollback(); app.logger.exception("Unable to update background privacy")
            return response(msg="背景隐私更新失败，请稍后重试", status=500)
        finally: conn.close()

    @app.route("/api/personalization/backgrounds/<int:background_id>/file", methods=["GET"])
    @jwt_required()
    def personalization_background_file(background_id):
        from backend.background_config import BACKGROUND_UPLOAD_ROOT
        from backend.background_storage import BackgroundFileNotFound, read_background_file
        user = current_user()
        if not user: return response(msg="登录状态已失效，请重新登录", status=401)
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT storage_path, mime_type FROM user_backgrounds WHERE id=%s AND user_id=%s AND status='active'", (background_id, user["id"]))
                item = cursor.fetchone()
            if not item: return response(msg="背景不存在或无权访问", status=404)
            return send_file(io.BytesIO(read_background_file(BACKGROUND_UPLOAD_ROOT, item["storage_path"])), mimetype=item["mime_type"], conditional=True, max_age=3600)
        except BackgroundFileNotFound: return response(msg="背景文件不存在", status=404)
        except Exception:
            app.logger.exception("Unable to read personalization background")
            return response(msg="背景读取失败，请稍后重试", status=500)
        finally: conn.close()

    @app.route("/api/personalization/backgrounds/<int:background_id>/thumbnail", methods=["GET"])
    @jwt_required()
    def personalization_background_thumbnail(background_id):
        """Return an authenticated, small WebP preview for the private library."""
        from PIL import Image
        from backend.background_config import BACKGROUND_UPLOAD_ROOT
        from backend.background_storage import BackgroundFileNotFound, read_background_file
        user = current_user()
        if not user: return response(msg="登录状态已失效，请重新登录", status=401)
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT storage_path FROM user_backgrounds WHERE id=%s AND user_id=%s AND status='active'", (background_id, user["id"]))
                item = cursor.fetchone()
            if not item: return response(msg="背景不存在或无权访问", status=404)
            with Image.open(io.BytesIO(read_background_file(BACKGROUND_UPLOAD_ROOT, item["storage_path"]))) as image:
                image = image.convert("RGB")
                image.thumbnail((480, 480))
                preview = io.BytesIO()
                image.save(preview, format="WEBP", quality=78, method=4)
            preview.seek(0)
            result = send_file(preview, mimetype="image/webp", conditional=True, max_age=0)
            result.headers["Cache-Control"] = "private, no-store"
            return result
        except BackgroundFileNotFound: return response(msg="背景文件不存在", status=404)
        except Exception:
            app.logger.exception("Unable to build personalization background thumbnail")
            return response(msg="背景缩略图读取失败，请稍后重试", status=500)
        finally: conn.close()
