"""Service-level tests for the injected-session questionnaire read contract."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
import unittest

from tests.questionnaire_foundation_test_support import (
    FakeRoleConnectionFactory,
    QuestionnaireFoundationTestCase,
    SqlStatementCounter,
    add_condition,
    add_definition,
    add_occupation,
    add_option,
    add_question,
    add_version,
    dispose_sqlite_app,
    make_sqlite_app,
    sqlite_session,
)


class QuestionnaireReadServiceTests(QuestionnaireFoundationTestCase):
    def setUp(self) -> None:
        self.app = make_sqlite_app()

    def tearDown(self) -> None:
        dispose_sqlite_app(self.app)

    def _add_user(self, session, username: str):
        from models import User

        user = User(
            username=username,
            email=f"{username}@example.test",
            password_hash="not-a-password",
        )
        session.add(user)
        session.flush()
        return user

    def _add_definition(self, session, creator, **overrides):
        fields = {
            "definition_code": "general_profile",
            "name": "General profile",
            "description": "A general questionnaire",
            "scope_type": "general",
            "scope_key": "general",
            "occupation_id": None,
            "user_type": None,
            "enabled": True,
            "created_by_user_id": creator.id,
        }
        fields.update(overrides)
        return add_definition(session, **fields)

    def _add_version(self, session, definition, creator, **overrides):
        fields = {
            "definition_id": definition.id,
            "version_number": 1,
            "status": "draft",
            "current_effective_scope_key": None,
            "source_version_id": None,
            "version_description": "Initial version",
            "created_by_user_id": creator.id,
            "published_by_user_id": None,
            "published_at": None,
        }
        fields.update(overrides)
        return add_version(session, **fields)

    def test_list_occupations_filters_paginates_and_orders_by_stable_code(self) -> None:
        from questionnaire_read_service import list_occupations

        with sqlite_session(self.app) as session:
            add_occupation(
                session,
                occupation_code="zebra",
                name="Zebra",
                category="creative",
                sort_order=1,
                enabled=True,
                new_occupation_policy="use_general",
            )
            add_occupation(
                session,
                occupation_code="alpha",
                name="Alpha",
                category="creative",
                sort_order=1,
                enabled=True,
                new_occupation_policy="closed",
            )
            add_occupation(
                session,
                occupation_code="hidden",
                name="Hidden",
                category="technical",
                sort_order=0,
                enabled=False,
                new_occupation_policy="closed",
            )

            result = list_occupations(
                session, {"enabled": True, "category": "creative", "page": 2, "page_size": 1}
            )

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["page_size"], 1)
        self.assertEqual([item["occupation_code"] for item in result["items"]], ["zebra"])
        self.assertEqual(
            set(result["items"][0]),
            {"id", "occupation_code", "name", "category", "sort_order", "enabled", "new_occupation_policy"},
        )

    def test_list_definitions_filters_paginates_and_uses_stable_definition_code_order(self) -> None:
        from questionnaire_read_service import list_definitions

        with sqlite_session(self.app) as session:
            creator = self._add_user(session, "definition-list-creator")
            occupation = add_occupation(
                session,
                occupation_code="designer",
                name="Designer",
                category="creative",
                sort_order=0,
                enabled=True,
                new_occupation_policy="use_general",
            )
            self._add_definition(
                session,
                creator,
                definition_code="zebra_designer",
                scope_type="occupation",
                scope_key="occupation:designer",
                occupation_id=occupation.id,
            )
            self._add_definition(
                session,
                creator,
                definition_code="alpha_designer",
                scope_type="occupation",
                scope_key="occupation:designer:alternate",
                occupation_id=occupation.id,
            )
            self._add_definition(
                session,
                creator,
                definition_code="student_profile",
                scope_type="user_type",
                scope_key="user_type:student",
                user_type="student",
            )

            result = list_definitions(
                session,
                {
                    "scope_type": "occupation",
                    "occupation_code": "designer",
                    "page": 1,
                    "page_size": 10,
                },
            )

        self.assertEqual(result["total"], 2)
        self.assertEqual(
            [item["definition_code"] for item in result["items"]],
            ["alpha_designer", "zebra_designer"],
        )
        self.assertEqual(result["items"][0]["occupation_code"], "designer")
        self.assertEqual(result["items"][0]["is_current_effective"], False)

    def test_get_definition_returns_serialized_definition_or_none(self) -> None:
        from questionnaire_read_service import get_definition

        with sqlite_session(self.app) as session:
            creator = self._add_user(session, "definition-detail-creator")
            definition = self._add_definition(session, creator)

            result = get_definition(session, definition.id)
            missing = get_definition(session, definition.id + 99)

        self.assertEqual(result["definition_code"], "general_profile")
        self.assertEqual(result["scope_key"], "general")
        self.assertIsNone(result["occupation_code"])
        self.assertIsNone(missing)

    def test_list_versions_filters_paginates_orders_and_computes_current_effective(self) -> None:
        from questionnaire_read_service import list_versions

        with sqlite_session(self.app) as session:
            creator = self._add_user(session, "version-list-creator")
            definition = self._add_definition(session, creator)
            self._add_version(
                session,
                definition,
                creator,
                version_number=3,
                status="published",
                current_effective_scope_key="general",
                published_by_user_id=creator.id,
                published_at=datetime.now(UTC),
            )
            self._add_version(session, definition, creator, version_number=1)
            self._add_version(session, definition, creator, version_number=2, status="disabled")

            result = list_versions(
                session,
                definition.id,
                {"status": "published", "current_effective": True, "page": 1, "page_size": 5},
            )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["version_number"], 3)
        self.assertTrue(result["items"][0]["is_current_effective"])
        self.assertEqual(result["items"][0]["current_effective_scope_key"], "general")

    def test_get_version_snapshot_serializes_stable_keys_options_and_target_condition(self) -> None:
        from questionnaire_read_service import get_version_snapshot

        with sqlite_session(self.app) as session:
            creator = self._add_user(session, "snapshot-creator")
            definition = self._add_definition(session, creator)
            version = self._add_version(session, definition, creator)
            source = add_question(
                session,
                version_id=version.id,
                question_code="interest",
                title="What interests you?",
                description=None,
                question_type="single_choice",
                required=True,
                sort_order=1,
                enabled=True,
                is_general=True,
                min_selections=None,
                max_selections=None,
                max_length=None,
            )
            expected = add_option(
                session,
                question_id=source.id,
                option_value="art",
                label="Art",
                sort_order=2,
                enabled=True,
            )
            add_option(
                session,
                question_id=source.id,
                option_value="science",
                label="Science",
                sort_order=1,
                enabled=False,
            )
            target = add_question(
                session,
                version_id=version.id,
                question_code="portfolio",
                title="Show your portfolio",
                description="Optional URL",
                question_type="short_text",
                required=False,
                sort_order=2,
                enabled=True,
                is_general=False,
                min_selections=None,
                max_selections=None,
                max_length=200,
            )
            add_condition(
                session,
                version_id=version.id,
                source_question_id=source.id,
                target_question_id=target.id,
                expected_option_id=expected.id,
                operator="equals",
            )

            snapshot = get_version_snapshot(session, version.id)

        self.assertEqual(snapshot["definition_code"], "general_profile")
        self.assertFalse(snapshot["is_current_effective"])
        self.assertEqual([question["question_code"] for question in snapshot["questions"]], ["interest", "portfolio"])
        self.assertEqual(
            [option["option_value"] for option in snapshot["questions"][0]["option_values"]],
            ["science", "art"],
        )
        self.assertEqual(
            snapshot["questions"][1]["condition"],
            {
                "source_question_code": "interest",
                "target_question_code": "portfolio",
                "expected_option_value": "art",
                "operator": "equals",
            },
        )

    def test_get_version_snapshot_breaks_tied_sort_orders_by_stable_codes(self) -> None:
        from questionnaire_read_service import get_version_snapshot

        with sqlite_session(self.app) as session:
            creator = self._add_user(session, "tied-sort-creator")
            definition = self._add_definition(session, creator)
            version = self._add_version(session, definition, creator)
            second = add_question(
                session,
                version_id=version.id,
                question_code="zebra",
                title="Zebra question",
                description=None,
                question_type="single_choice",
                required=False,
                sort_order=1,
                enabled=True,
                is_general=False,
                min_selections=None,
                max_selections=None,
                max_length=None,
            )
            add_option(
                session,
                question_id=second.id,
                option_value="zebra",
                label="Zebra option",
                sort_order=1,
                enabled=True,
            )
            add_option(
                session,
                question_id=second.id,
                option_value="alpha",
                label="Alpha option",
                sort_order=1,
                enabled=True,
            )
            add_question(
                session,
                version_id=version.id,
                question_code="alpha",
                title="Alpha question",
                description=None,
                question_type="short_text",
                required=False,
                sort_order=1,
                enabled=True,
                is_general=False,
                min_selections=None,
                max_selections=None,
                max_length=None,
            )

            snapshot = get_version_snapshot(session, version.id)

        self.assertEqual(
            [question["question_code"] for question in snapshot["questions"]],
            ["alpha", "zebra"],
        )
        self.assertEqual(
            [option["option_value"] for option in snapshot["questions"][1]["option_values"]],
            ["alpha", "zebra"],
        )

    def test_snapshot_serialization_sorts_tied_relationship_collections_by_code(self) -> None:
        from questionnaire_read_service import get_version_snapshot

        def question(question_code: str, options: list[object]) -> object:
            return SimpleNamespace(
                id=1,
                question_code=question_code,
                title=question_code,
                description=None,
                question_type="single_choice",
                required=False,
                sort_order=1,
                enabled=True,
                is_general=False,
                min_selections=None,
                max_selections=None,
                max_length=None,
                options=options,
                target_condition=None,
            )

        def option(option_value: str) -> object:
            return SimpleNamespace(
                id=1,
                option_value=option_value,
                label=option_value,
                sort_order=1,
                enabled=True,
            )

        version = SimpleNamespace(
            id=1,
            definition_id=1,
            version_number=1,
            status="draft",
            current_effective_scope_key=None,
            source_version_id=None,
            version_description=None,
            created_by_user_id=1,
            published_by_user_id=None,
            published_at=None,
            definition=SimpleNamespace(
                definition_code="general_profile",
                name="General profile",
                scope_key="general",
                occupation=None,
            ),
            questions=[
                question("zebra", [option("zebra"), option("alpha")]),
                question("alpha", []),
            ],
        )

        snapshot = get_version_snapshot(SimpleNamespace(scalar=lambda _: version), 1)

        self.assertEqual(
            [item["question_code"] for item in snapshot["questions"]],
            ["alpha", "zebra"],
        )
        self.assertEqual(
            [item["option_value"] for item in snapshot["questions"][1]["option_values"]],
            ["alpha", "zebra"],
        )

    def test_malformed_condition_snapshot_raises_value_error(self) -> None:
        from questionnaire_read_service import _serialize_condition

        malformed = SimpleNamespace(
            source_question=None,
            target_question=SimpleNamespace(question_code="target"),
            expected_option=SimpleNamespace(option_value="yes"),
        )

        with self.assertRaisesRegex(ValueError, "missing relationships"):
            _serialize_condition(malformed)

    def test_get_version_snapshot_returns_none_for_a_missing_version(self) -> None:
        from questionnaire_read_service import get_version_snapshot

        with sqlite_session(self.app) as session:
            self.assertIsNone(get_version_snapshot(session, 999))

    def test_snapshot_preloads_questions_options_and_conditions_without_per_question_queries(self) -> None:
        from questionnaire_read_service import get_version_snapshot
        from models import db

        with sqlite_session(self.app) as session:
            creator = self._add_user(session, "query-budget-creator")
            definition = self._add_definition(session, creator)
            version = self._add_version(session, definition, creator)
            for index in range(20):
                record = add_question(
                    session,
                    version_id=version.id,
                    question_code=f"question_{index:02d}",
                    title=f"Question {index}",
                    description=None,
                    question_type="single_choice",
                    required=False,
                    sort_order=index,
                    enabled=True,
                    is_general=False,
                    min_selections=None,
                    max_selections=None,
                    max_length=None,
                )
                add_option(
                    session,
                    question_id=record.id,
                    option_value="yes",
                    label="Yes",
                    sort_order=0,
                    enabled=True,
                )
            version_id = version.id
            session.expire_all()

            with SqlStatementCounter(db.engine) as counter:
                snapshot = get_version_snapshot(session, version_id)

        self.assertEqual(len(snapshot["questions"]), 20)
        self.assertLessEqual(counter.count, 5)


class QuestionnaireAdminReadApiTests(QuestionnaireFoundationTestCase):
    def setUp(self) -> None:
        self.app = make_sqlite_app()
        self.roles = FakeRoleConnectionFactory(
            {
                "admin": "admin",
                "super": "super_admin",
                "member": "user",
                "forged": "user",
            }
        )
        from questionnaire_admin_read_routes import register_questionnaire_admin_read_routes

        register_questionnaire_admin_read_routes(self.app, self.roles)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        dispose_sqlite_app(self.app)

    def _headers(self, identity: str) -> dict[str, str]:
        from tests.questionnaire_foundation_test_support import make_jwt_headers

        return make_jwt_headers(self.app, identity)

    def _add_user(self, session, username: str):
        from models import User

        user = User(
            username=username,
            email=f"{username}@example.test",
            password_hash="not-a-password",
        )
        session.add(user)
        session.flush()
        return user

    def _add_definition(self, session, creator, **overrides):
        fields = {
            "definition_code": "general_profile",
            "name": "General profile",
            "description": "A general questionnaire",
            "scope_type": "general",
            "scope_key": "general",
            "occupation_id": None,
            "user_type": None,
            "enabled": True,
            "created_by_user_id": creator.id,
        }
        fields.update(overrides)
        return add_definition(session, **fields)

    def test_new_endpoints_require_a_jwt_and_return_five_key_errors(self) -> None:
        response = self.client.get("/api/admin/questionnaires/occupations")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(set(response.get_json()), {"code", "legacy_code", "message", "msg", "data"})
        self.assertEqual(response.get_json()["code"], 401)

    def test_role_lookup_rejects_missing_and_non_admin_users(self) -> None:
        for identity in ("missing", "member"):
            response = self.client.get(
                "/api/admin/questionnaires/occupations", headers=self._headers(identity)
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.get_json()["code"], 403)

        self.assertEqual(self.roles.identities, ["missing", "member"])

    def test_database_role_lookup_ignores_a_forged_jwt_role_claim(self) -> None:
        from flask_jwt_extended import create_access_token

        with self.app.app_context():
            token = create_access_token(
                identity="forged", additional_claims={"role": "super_admin"}
            )
        response = self.client.get(
            "/api/admin/questionnaires/occupations",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.roles.identities, ["forged"])

    def test_admin_can_list_occupations_and_response_has_five_keys(self) -> None:
        with sqlite_session(self.app) as session:
            add_occupation(
                session,
                occupation_code="designer",
                name="Designer",
                category="creative",
                sort_order=1,
                enabled=True,
                new_occupation_policy="use_general",
            )
            add_occupation(
                session,
                occupation_code="hidden",
                name="Hidden",
                category="creative",
                sort_order=2,
                enabled=False,
                new_occupation_policy="closed",
            )

            response = self.client.get(
                "/api/admin/questionnaires/occupations?enabled=true&page=1&page_size=1",
                headers=self._headers("super"),
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(set(payload), {"code", "legacy_code", "message", "msg", "data"})
        self.assertEqual(payload["data"]["total"], 1)
        self.assertEqual(payload["data"]["items"][0]["occupation_code"], "designer")

    def test_admin_can_list_and_get_definitions(self) -> None:
        with sqlite_session(self.app) as session:
            creator = self._add_user(session, "api-definition-creator")
            definition = self._add_definition(session, creator)

            list_response = self.client.get(
                "/api/admin/questionnaires/definitions?enabled=true",
                headers=self._headers("admin"),
            )
            detail_response = self.client.get(
                f"/api/admin/questionnaires/definitions/{definition.id}",
                headers=self._headers("admin"),
            )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(
            list_response.get_json()["data"]["items"][0]["definition_code"],
            "general_profile",
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.get_json()["data"]["id"], definition.id)

    def test_invalid_parameters_and_missing_definition_use_new_error_shape(self) -> None:
        with sqlite_session(self.app):
            bad_response = self.client.get(
                "/api/admin/questionnaires/occupations?enabled=maybe",
                headers=self._headers("admin"),
            )
            missing_response = self.client.get(
                "/api/admin/questionnaires/definitions/999",
                headers=self._headers("admin"),
            )

        self.assertEqual(bad_response.status_code, 400)
        self.assertEqual(missing_response.status_code, 404)
        self.assertEqual(
            set(bad_response.get_json()), {"code", "legacy_code", "message", "msg", "data"}
        )
        self.assertEqual(
            set(missing_response.get_json()), {"code", "legacy_code", "message", "msg", "data"}
        )

    def test_registering_new_routes_keeps_the_existing_v1_error_unchanged(self) -> None:
        from flask import Flask
        from flask_jwt_extended import JWTManager
        from questionnaire_admin_read_routes import register_questionnaire_admin_read_routes
        from v1_routes import register_v1_routes

        def build_app(register_questionnaire_routes: bool) -> Flask:
            app = Flask(__name__)
            app.config.update(TESTING=True, JWT_SECRET_KEY="v1-regression-secret")
            JWTManager(app)
            register_v1_routes(app, lambda: None)
            if register_questionnaire_routes:
                register_questionnaire_admin_read_routes(
                    app, FakeRoleConnectionFactory({"admin": "admin"})
                )
            return app

        before = build_app(False).test_client().get("/api/admin/dashboard")
        after = build_app(True).test_client().get("/api/admin/dashboard")

        self.assertEqual(after.status_code, before.status_code)
        self.assertEqual(after.get_json(), before.get_json())
        self.assertNotIn("legacy_code", before.get_json())


if __name__ == "__main__":
    unittest.main()
