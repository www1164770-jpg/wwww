"""Admin API registration for the crawler review boundary.

The nav-site adapter is deliberately disabled unless the process explicitly sets
``CRAWLER_NAV_SITE_SYNC_ENABLED=true``.  Therefore a crawler deployment cannot
accidentally write the application database merely by exposing these routes.
"""

from __future__ import annotations

from typing import Any

from flask import jsonify, request
from sqlalchemy import select

from backend.crawler.config import CrawlerConfigError, CrawlerSettings
from backend.crawler.db import PublishRecord, ReviewCase
from backend.crawler.db.session import create_crawler_engine, create_session_factory, session_scope
from backend.crawler.review.preview import create_local_preview
from backend.crawler.review.service import (
    ReviewValidationError, ReviewVersionConflict, approve_review, assign_review,
    create_review, mark_publish_ready, reject_review, update_review,
)
from backend.crawler.review.states import APPROVED


def _case_payload(case: ReviewCase) -> dict[str, Any]:
    return {
        "review_uid": case.review_uid, "fetch_result_id": case.fetch_result_id,
        "analysis_result_id": case.analysis_result_id, "status": case.status,
        "priority": case.priority, "assigned_reviewer_id": case.assigned_reviewer_id,
        "selected_title": case.selected_title, "selected_summary": case.selected_summary,
        "selected_description": case.selected_description, "selected_category": case.selected_category,
        "selected_region": case.selected_region, "selected_language": case.selected_language,
        "selected_tags": case.selected_tags, "selected_risk_level": case.selected_risk_level,
        "selected_quality_score": case.selected_quality_score,
        "selected_url": case.selected_url, "selected_logo_asset_id": case.selected_logo_asset_id,
        "risk_acknowledgements": case.risk_acknowledgements,
        "override_reasons": case.override_reasons, "content_hash": case.review_content_hash,
        "version": case.version,
    }


def register_review_routes(app, admin_required) -> None:
    """Register only authenticated admin endpoints; errors are intentionally generic."""
    def factory():
        settings = CrawlerSettings.from_env(require_database=True)
        return create_session_factory(create_crawler_engine(settings))

    def with_session(handler):
        def wrapped(*args, **kwargs):
            try:
                session_factory = factory()
                with session_scope(session_factory) as crawler_session:
                    return handler(crawler_session, *args, **kwargs)
            except CrawlerConfigError:
                return jsonify({"code": 503, "msg": "crawler review service unavailable"}), 503
            except ReviewVersionConflict:
                return jsonify({"code": 409, "msg": "review was changed by another administrator"}), 409
            except (ReviewValidationError, ValueError, PermissionError):
                return jsonify({"code": 400, "msg": "review request was rejected"}), 400
            except RuntimeError:
                return jsonify({"code": 503, "msg": "nav-site synchronization is unavailable"}), 503
        wrapped.__name__ = handler.__name__
        return wrapped

    @app.route("/api/admin/crawler/reviews", methods=["GET"])
    @admin_required()
    @with_session
    def crawler_reviews(session):
        limit = min(max(request.args.get("limit", 50, type=int), 1), 200)
        query = select(ReviewCase).order_by(ReviewCase.priority, ReviewCase.created_at).limit(limit)
        status = request.args.get("status")
        if status:
            query = query.where(ReviewCase.status == status)
        return jsonify({"code": 0, "data": [_case_payload(case) for case in session.scalars(query)]})

    @app.route("/api/admin/crawler/reviews/<review_uid>", methods=["GET"])
    @admin_required()
    @with_session
    def crawler_review(session, review_uid):
        case = session.scalar(select(ReviewCase).where(ReviewCase.review_uid == review_uid))
        if case is None:
            return jsonify({"code": 404, "msg": "review not found"}), 404
        return jsonify({"code": 0, "data": _case_payload(case)})

    def case_for(session, review_uid):
        case = session.scalar(select(ReviewCase).where(ReviewCase.review_uid == review_uid))
        if case is None:
            raise ReviewValidationError("review not found")
        return case

    @app.route("/api/admin/crawler/reviews/<review_uid>/assign", methods=["POST"])
    @admin_required()
    @with_session
    def crawler_assign(session, review_uid):
        body = request.get_json(silent=True) or {}
        case = assign_review(session, case_for(session, review_uid), reviewer_id=body.get("reviewer_id", ""), expected_version=int(body.get("version")), actor_id="admin")
        return jsonify({"code": 0, "data": _case_payload(case)})

    @app.route("/api/admin/crawler/reviews/<review_uid>/approve", methods=["POST"])
    @admin_required()
    @with_session
    def crawler_approve(session, review_uid):
        body = request.get_json(silent=True) or {}
        case = case_for(session, review_uid)
        if body.get("changes"):
            case = update_review(session, case, expected_version=int(body.get("version")), changes=body["changes"], actor_id="admin", notes=body.get("notes"))
        case = approve_review(session, case, expected_version=case.version, actor_id="admin", reason_code=body.get("reason_code"), notes=body.get("notes"), can_override_risk=bool(body.get("risk_override_authorized")))
        return jsonify({"code": 0, "data": _case_payload(case)})

    @app.route("/api/admin/crawler/reviews/<review_uid>/reject", methods=["POST"])
    @admin_required()
    @with_session
    def crawler_reject(session, review_uid):
        body = request.get_json(silent=True) or {}
        case = reject_review(session, case_for(session, review_uid), expected_version=int(body.get("version")), actor_id="admin", reason_code=body.get("reason_code"), notes=body.get("notes"))
        return jsonify({"code": 0, "data": _case_payload(case)})

    @app.route("/api/admin/crawler/reviews/<review_uid>/publish-preview", methods=["POST"])
    @admin_required()
    @with_session
    def crawler_publish_preview(session, review_uid):
        case = case_for(session, review_uid)
        body = request.get_json(silent=True) or {}
        case, preview = create_local_preview(
            session, case, expected_version=int(body.get("version")), actor_id="admin",
            ttl_seconds=CrawlerSettings.from_env().publish_preview_ttl_seconds,
        )
        return jsonify({"code": 0, "data": {"preview_uid": preview.preview_uid,
            "preview": preview.result_json, "review_version": preview.review_version,
            "content_hash": preview.content_hash, "expires_at": preview.expires_at.isoformat() if preview.expires_at else None,
            "review": _case_payload(case)}})

    @app.route("/api/admin/crawler/reviews/<review_uid>/publish", methods=["POST"])
    @admin_required()
    @with_session
    def crawler_publish(session, review_uid):
        # A real adapter is deliberately absent until an isolated target database
        # is explicitly configured and its database name is allow-listed.
        raise RuntimeError("publish target adapter is not configured")

    @app.route("/api/admin/crawler/publishes/<publish_uid>", methods=["GET"])
    @admin_required()
    @with_session
    def crawler_publish_status(session, publish_uid):
        record = session.scalar(select(PublishRecord).where(PublishRecord.publish_uid == publish_uid))
        if record is None:
            return jsonify({"code": 404, "msg": "publish not found"}), 404
        return jsonify({"code": 0, "data": {"publish_uid": record.publish_uid, "status": record.status, "attempt_count": record.attempt_count, "last_error_code": record.last_error_code}})

    @app.route("/api/admin/crawler/publishes/<publish_uid>/retry", methods=["POST"])
    @admin_required()
    @with_session
    def crawler_publish_retry(session, publish_uid):
        record = session.scalar(select(PublishRecord).where(PublishRecord.publish_uid == publish_uid))
        if record is None:
            return jsonify({"code": 404, "msg": "publish not found"}), 404
        body = request.get_json(silent=True) or {}
        if body.get("confirm") is not True:
            return jsonify({"code": 400, "msg": "publish retry requires explicit confirmation"}), 400
        raise RuntimeError("publish target adapter is not configured")
