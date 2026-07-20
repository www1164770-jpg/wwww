"""Tests for the questionnaire foundation ORM models introduced task by task."""

from __future__ import annotations

from datetime import UTC, datetime
import unittest
from unittest.mock import patch

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import configure_mappers

from tests.questionnaire_foundation_test_support import (
    QuestionnaireFoundationTestCase,
    add_occupation,
    make_sqlite_app,
    dispose_sqlite_app,
    sqlite_session,
)


class OccupationFoundationTests(QuestionnaireFoundationTestCase):
    def setUp(self) -> None:
        self.app = make_sqlite_app()

    def tearDown(self) -> None:
        dispose_sqlite_app(self.app)

    def test_make_sqlite_app_registers_questionnaire_models_before_a_session_is_requested(self) -> None:
        from models import db

        self.assertIn("occupations", db.metadata.tables)

    def test_occupation_uses_the_existing_global_models_db(self) -> None:
        from models import db
        from questionnaire_models import Occupation

        self.assertIs(Occupation.metadata, db.metadata)
        self.assertFalse(hasattr(__import__("questionnaire_models"), "Base"))

    def test_foundation_constants_and_occupation_columns_match_contract(self) -> None:
        from questionnaire_constants import (
            NEW_OCCUPATION_POLICIES, QUESTIONNAIRE_SCOPE_TYPES,
            QUESTIONNAIRE_VERSION_STATUSES, USER_TYPES,
        )
        from questionnaire_models import Occupation

        self.assertEqual(NEW_OCCUPATION_POLICIES, frozenset({"use_general", "closed"}))
        self.assertEqual(QUESTIONNAIRE_SCOPE_TYPES, frozenset({"general", "occupation", "user_type", "occupation_user_type"}))
        self.assertEqual(USER_TYPES, frozenset({"student", "employed", "organization"}))
        self.assertEqual(QUESTIONNAIRE_VERSION_STATUSES, frozenset({"draft", "published", "disabled", "archived"}))
        self.assertEqual(Occupation.__table__.c.occupation_code.type.length, 64)
        self.assertEqual(Occupation.__table__.c.name.type.length, 120)
        self.assertEqual(Occupation.__table__.c.category.type.length, 120)
        self.assertTrue(Occupation.__table__.c.category.nullable)

    def test_occupation_supports_keyword_construction_and_shared_sqlite_lifecycle(self) -> None:
        from questionnaire_models import Occupation

        with sqlite_session(self.app) as session:
            foreign_keys_enabled = session.execute(text("PRAGMA foreign_keys")).scalar_one()
            occupation = add_occupation(
                session,
                occupation_code="designer",
                name="Designer",
                category="creative",
                sort_order=3,
                enabled=True,
                new_occupation_policy="use_general",
            )

            self.assertEqual(foreign_keys_enabled, 1)
            self.assertIsInstance(occupation, Occupation)
            self.assertEqual(occupation.occupation_code, "designer")
            self.assertEqual(occupation.name, "Designer")

    def test_sqlite_session_disposes_the_static_pool_after_test_cleanup(self) -> None:
        from models import db

        with self.app.app_context():
            with patch.object(db.engine, "dispose", wraps=db.engine.dispose) as dispose:
                with sqlite_session(self.app):
                    pass

            dispose.assert_called_once_with()

    def test_occupation_code_and_name_are_unique(self) -> None:
        from questionnaire_models import Occupation

        with sqlite_session(self.app) as session:
            add_occupation(
                session,
                occupation_code="designer",
                name="Designer",
                category="creative",
                sort_order=0,
                enabled=True,
                new_occupation_policy="use_general",
            )
            session.add(
                Occupation(
                    occupation_code="designer",
                    name="Different designer",
                    category="creative",
                    sort_order=1,
                    enabled=True,
                    new_occupation_policy="closed",
                )
            )
            with self.assertRaises(IntegrityError):
                session.flush()
            session.rollback()

            add_occupation(
                session,
                occupation_code="developer",
                name="Developer",
                category="technical",
                sort_order=2,
                enabled=True,
                new_occupation_policy="use_general",
            )
            session.add(
                Occupation(
                    occupation_code="engineer",
                    name="Developer",
                    category="technical",
                    sort_order=3,
                    enabled=True,
                    new_occupation_policy="closed",
                )
            )
            with self.assertRaises(IntegrityError):
                session.flush()

    def test_validate_occupation_rejects_invalid_stable_fields(self) -> None:
        from questionnaire_models import Occupation
        from questionnaire_validation import validate_occupation

        invalid_occupations = (
            Occupation(
                occupation_code="Designer",
                name="Designer",
                category="creative",
                sort_order=0,
                enabled=True,
                new_occupation_policy="use_general",
            ),
            Occupation(
                occupation_code="designer",
                name="   ",
                category="creative",
                sort_order=0,
                enabled=True,
                new_occupation_policy="use_general",
            ),
            Occupation(
                occupation_code="designer",
                name="Designer",
                category="creative",
                sort_order=-1,
                enabled=True,
                new_occupation_policy="use_general",
            ),
            Occupation(
                occupation_code="designer",
                name="Designer",
                category="creative",
                sort_order=0,
                enabled=True,
                new_occupation_policy="open",
            ),
        )

        for occupation in invalid_occupations:
            with self.subTest(occupation=occupation.occupation_code):
                with self.assertRaises(ValueError):
                    validate_occupation(occupation)

    def test_validate_occupation_accepts_lowercase_stable_code_and_known_policy(self) -> None:
        from questionnaire_models import Occupation
        from questionnaire_validation import validate_occupation

        occupation = Occupation(
            occupation_code="product_manager",
            name="Product manager",
            category="product",
            sort_order=0,
            enabled=False,
            new_occupation_policy="closed",
        )

        self.assertIsNone(validate_occupation(occupation))


class QuestionnaireDefinitionAndVersionTests(QuestionnaireFoundationTestCase):
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

    def _add_occupation(self, session, code: str = "designer"):
        return add_occupation(
            session,
            occupation_code=code,
            name=code.title(),
            category="creative",
            sort_order=0,
            enabled=True,
            new_occupation_policy="use_general",
        )

    def _definition_fields(self, creator, **overrides):
        fields = {
            "definition_code": "designer_profile",
            "name": "Designer profile",
            "description": None,
            "scope_type": "general",
            "scope_key": "general",
            "occupation_id": None,
            "user_type": None,
            "enabled": True,
            "created_by_user_id": creator.id,
        }
        fields.update(overrides)
        return fields

    def _version_fields(self, definition, creator, **overrides):
        fields = {
            "definition_id": definition.id,
            "version_number": 1,
            "status": "draft",
            "current_effective_scope_key": None,
            "source_version_id": None,
            "version_description": None,
            "created_by_user_id": creator.id,
            "published_by_user_id": None,
            "published_at": None,
        }
        fields.update(overrides)
        return fields

    def test_definition_and_version_models_are_registered_with_expected_relationships(self) -> None:
        from questionnaire_models import QuestionnaireDefinition, QuestionnaireVersion

        configure_mappers()
        self.assertIn("questionnaire_definitions", QuestionnaireDefinition.metadata.tables)
        self.assertIn("questionnaire_versions", QuestionnaireVersion.metadata.tables)
        self.assertIs(
            QuestionnaireVersion.definition.property.mapper.class_,
            QuestionnaireDefinition,
        )
        self.assertIs(
            QuestionnaireDefinition.versions.property.mapper.class_,
            QuestionnaireVersion,
        )
        self.assertIs(
            QuestionnaireVersion.source_version.property.mapper.class_,
            QuestionnaireVersion,
        )
        self.assertFalse(hasattr(QuestionnaireVersion, "questions"))
        self.assertFalse(hasattr(QuestionnaireVersion, "is_current_effective"))
        self.assertEqual(
            tuple(QuestionnaireDefinition.versions.property.order_by),
            (QuestionnaireVersion.version_number,),
        )

    def test_definition_scope_keys_use_stable_occupation_codes_for_all_scope_types(self) -> None:
        from questionnaire_validation import build_scope_key

        self.assertEqual(build_scope_key("general", None, None), "general")
        self.assertEqual(
            build_scope_key("occupation", "designer", None), "occupation:designer"
        )
        self.assertEqual(
            build_scope_key("user_type", None, "student"), "user_type:student"
        )
        self.assertEqual(
            build_scope_key("occupation_user_type", "designer", "student"),
            "occupation:designer:user_type:student",
        )

    def test_build_scope_key_rejects_invalid_occupation_codes(self) -> None:
        from questionnaire_validation import build_scope_key

        invalid_codes = (None, "", "designer:admin", "designer profile", 1)
        for occupation_code in invalid_codes:
            with self.subTest(occupation_code=occupation_code):
                with self.assertRaises(ValueError):
                    build_scope_key("occupation", occupation_code, None)
                with self.assertRaises(ValueError):
                    build_scope_key(
                        "occupation_user_type", occupation_code, "student"
                    )

    def test_definition_scope_validation_rejects_invalid_type_and_field_combinations(self) -> None:
        from questionnaire_models import QuestionnaireDefinition
        from questionnaire_validation import validate_definition_scope

        cases = (
            {"scope_type": "unknown", "scope_key": "unknown"},
            {"scope_type": "general", "scope_key": "general", "occupation_id": 1},
            {"scope_type": "general", "scope_key": "general", "user_type": "student"},
            {"scope_type": "occupation", "scope_key": "occupation:designer"},
            {"scope_type": "user_type", "scope_key": "user_type:student"},
            {
                "scope_type": "occupation_user_type",
                "scope_key": "occupation:designer:user_type:student",
                "occupation_id": 1,
            },
        )
        for fields in cases:
            definition = QuestionnaireDefinition(**fields)
            with self.subTest(fields=fields):
                with self.assertRaises(ValueError):
                    validate_definition_scope(definition)

    def test_definition_scope_rejects_transient_occupation_relation_for_non_occupation_scope(self) -> None:
        from questionnaire_models import Occupation, QuestionnaireDefinition
        from questionnaire_validation import validate_definition_scope

        occupation = Occupation(
            occupation_code="designer",
            name="Designer",
            category="creative",
            sort_order=0,
            enabled=True,
            new_occupation_policy="use_general",
        )
        for scope_type, scope_key, user_type in (
            ("general", "general", None),
            ("user_type", "user_type:student", "student"),
        ):
            definition = QuestionnaireDefinition(
                definition_code=f"{scope_type}_transient_relation",
                name="Invalid relation",
                scope_type=scope_type,
                scope_key=scope_key,
                user_type=user_type,
                created_by_user_id=1,
                occupation=occupation,
            )
            with self.subTest(scope_type=scope_type):
                with self.assertRaises(ValueError):
                    validate_definition_scope(definition)

    def test_definition_scope_rejects_occupation_relation_and_id_mismatch(self) -> None:
        from questionnaire_models import Occupation, QuestionnaireDefinition
        from questionnaire_validation import validate_definition_scope

        occupation = Occupation(
            id=2,
            occupation_code="designer",
            name="Designer",
            category="creative",
            sort_order=0,
            enabled=True,
            new_occupation_policy="use_general",
        )
        definition = QuestionnaireDefinition(
            definition_code="mismatched_occupation",
            name="Mismatched occupation",
            scope_type="occupation",
            scope_key="occupation:designer",
            occupation_id=1,
            created_by_user_id=1,
            occupation=occupation,
        )

        with self.assertRaises(ValueError):
            validate_definition_scope(definition)

    def test_definition_scope_rejects_known_occupation_id_with_transient_relation(self) -> None:
        from questionnaire_models import Occupation, QuestionnaireDefinition
        from questionnaire_validation import validate_definition_scope

        occupation = Occupation(
            occupation_code="designer",
            name="Designer",
            category="creative",
            sort_order=0,
            enabled=True,
            new_occupation_policy="use_general",
        )
        definition = QuestionnaireDefinition(
            definition_code="known_id_transient_relation",
            name="Known id transient relation",
            scope_type="occupation",
            scope_key="occupation:designer",
            occupation_id=1,
            created_by_user_id=1,
            occupation=occupation,
        )

        with self.assertRaises(ValueError):
            validate_definition_scope(definition)

    def test_definition_scope_validation_accepts_all_four_scope_combinations(self) -> None:
        from questionnaire_models import QuestionnaireDefinition
        from questionnaire_validation import validate_definition_scope

        with sqlite_session(self.app) as session:
            creator = self._add_user(session, "all-scopes-creator")
            occupation = self._add_occupation(session, "designer")
            definitions = (
                QuestionnaireDefinition(**self._definition_fields(creator)),
                QuestionnaireDefinition(
                    **self._definition_fields(
                        creator,
                        definition_code="designer_scope",
                        scope_type="occupation",
                        scope_key="occupation:designer",
                        occupation_id=occupation.id,
                    )
                ),
                QuestionnaireDefinition(
                    **self._definition_fields(
                        creator,
                        definition_code="student_scope",
                        scope_type="user_type",
                        scope_key="user_type:student",
                        user_type="student",
                    )
                ),
                QuestionnaireDefinition(
                    **self._definition_fields(
                        creator,
                        definition_code="designer_student_scope",
                        scope_type="occupation_user_type",
                        scope_key="occupation:designer:user_type:student",
                        occupation_id=occupation.id,
                        user_type="student",
                    )
                ),
            )
            definitions[1].occupation = occupation
            definitions[3].occupation = occupation
            for definition in definitions:
                with self.subTest(scope_type=definition.scope_type):
                    self.assertIsNone(validate_definition_scope(definition))

    def test_definition_code_and_scope_key_are_unique(self) -> None:
        from questionnaire_models import QuestionnaireDefinition

        with sqlite_session(self.app) as session:
            creator = self._add_user(session, "definition-creator")
            first = QuestionnaireDefinition(**self._definition_fields(creator))
            session.add(first)
            session.flush()
            session.add(
                QuestionnaireDefinition(
                    **self._definition_fields(
                        creator,
                        definition_code="different_code",
                    )
                )
            )
            with self.assertRaises(IntegrityError):
                session.flush()
            session.rollback()

    def test_definition_code_is_unique_independently_of_scope_key(self) -> None:
        from questionnaire_models import QuestionnaireDefinition

        with sqlite_session(self.app) as session:
            creator = self._add_user(session, "definition-code-creator")
            session.add(QuestionnaireDefinition(**self._definition_fields(creator)))
            session.flush()
            session.add(
                QuestionnaireDefinition(
                    **self._definition_fields(creator, scope_key="another_scope")
                )
            )
            with self.assertRaises(IntegrityError):
                session.flush()

    def test_version_database_constraints_allow_multiple_historical_null_keys(self) -> None:
        from questionnaire_models import QuestionnaireVersion

        with sqlite_session(self.app) as session:
            creator = self._add_user(session, "version-creator")
            definition = self._make_definition(session, creator)
            first = QuestionnaireVersion(**self._version_fields(definition, creator))
            second = QuestionnaireVersion(
                **self._version_fields(definition, creator, version_number=2)
            )
            session.add_all((first, second))
            session.flush()

            session.add(
                QuestionnaireVersion(
                    **self._version_fields(definition, creator, version_number=2)
                )
            )
            with self.assertRaises(IntegrityError):
                session.flush()
            session.rollback()

    def _make_definition(self, session, creator, **overrides):
        from questionnaire_models import QuestionnaireDefinition

        definition = QuestionnaireDefinition(**self._definition_fields(creator, **overrides))
        session.add(definition)
        session.flush()
        return definition

    def test_current_effective_scope_key_is_unique(self) -> None:
        from questionnaire_models import QuestionnaireVersion

        with sqlite_session(self.app) as session:
            creator = self._add_user(session, "effective-key-creator")
            general = self._make_definition(session, creator)
            other = self._make_definition(
                session,
                creator,
                definition_code="other_general",
                scope_key="other",
            )
            session.add(
                QuestionnaireVersion(
                    **self._version_fields(
                        general,
                        creator,
                        status="published",
                        current_effective_scope_key="general",
                        published_by_user_id=creator.id,
                        published_at=datetime.now(UTC),
                    )
                )
            )
            session.flush()
            session.add(
                QuestionnaireVersion(
                    **self._version_fields(
                        other,
                        creator,
                        status="published",
                        current_effective_scope_key="general",
                        published_by_user_id=creator.id,
                        published_at=datetime.now(UTC),
                    )
                )
            )
            with self.assertRaises(IntegrityError):
                session.flush()

    def test_validate_definition_scope_accepts_occupation_scope_from_stable_code(self) -> None:
        from questionnaire_models import QuestionnaireDefinition
        from questionnaire_validation import validate_definition_scope

        with sqlite_session(self.app) as session:
            creator = self._add_user(session, "scope-creator")
            occupation = self._add_occupation(session, "designer")
            definition = QuestionnaireDefinition(
                **self._definition_fields(
                    creator,
                    scope_type="occupation",
                    scope_key="occupation:designer",
                    occupation_id=occupation.id,
                )
            )
            definition.occupation = occupation
            self.assertIsNone(validate_definition_scope(definition))

    def test_validate_version_state_rejects_invalid_state_combinations(self) -> None:
        from questionnaire_models import QuestionnaireVersion
        from questionnaire_validation import validate_version_state

        with sqlite_session(self.app) as session:
            creator = self._add_user(session, "state-creator")
            definition = self._make_definition(session, creator)
            cases = (
                {"version_number": 0},
                {"status": "unknown"},
                {"status": "draft", "current_effective_scope_key": "general"},
                {"status": "disabled", "current_effective_scope_key": "general"},
                {"status": "archived", "current_effective_scope_key": "general"},
                {
                    "status": "published",
                    "current_effective_scope_key": "wrong",
                    "published_by_user_id": creator.id,
                    "published_at": datetime.now(UTC),
                },
                {
                    "status": "published",
                    "current_effective_scope_key": "general",
                    "published_at": datetime.now(UTC),
                },
                {
                    "status": "published",
                    "current_effective_scope_key": "general",
                    "published_by_user_id": creator.id,
                },
                {"published_at": datetime.now(UTC)},
            )
            for overrides in cases:
                version = QuestionnaireVersion(
                    **self._version_fields(definition, creator, **overrides)
                )
                with self.subTest(overrides=overrides):
                    with self.assertRaises(ValueError):
                        validate_version_state(version, definition)

    def test_validate_version_state_rejects_a_definition_from_another_version_scope(self) -> None:
        from questionnaire_models import QuestionnaireVersion
        from questionnaire_validation import validate_version_state

        with sqlite_session(self.app) as session:
            creator = self._add_user(session, "state-definition-creator")
            version_definition = self._make_definition(session, creator)
            other_definition = self._make_definition(
                session,
                creator,
                definition_code="other_state_definition",
                scope_key="other_state_scope",
            )
            version = QuestionnaireVersion(
                **self._version_fields(version_definition, creator)
            )

            with self.assertRaises(ValueError):
                validate_version_state(version, other_definition)

    def test_validate_version_state_rejects_internal_definition_id_and_relation_mismatch(self) -> None:
        from questionnaire_models import QuestionnaireDefinition, QuestionnaireVersion
        from questionnaire_validation import validate_version_state

        persisted_definition = QuestionnaireDefinition(
            id=1,
            definition_code="persisted_definition",
            name="Persisted definition",
            scope_type="general",
            scope_key="general",
            created_by_user_id=1,
        )
        conflicting_relation = QuestionnaireDefinition(
            id=2,
            definition_code="conflicting_definition",
            name="Conflicting definition",
            scope_type="general",
            scope_key="other_scope",
            created_by_user_id=1,
        )
        version = QuestionnaireVersion(
            definition_id=persisted_definition.id,
            definition=conflicting_relation,
            version_number=1,
            status="draft",
            created_by_user_id=1,
        )

        with self.assertRaises(ValueError):
            validate_version_state(version, persisted_definition)

    def test_historical_published_version_with_null_effective_key_is_valid(self) -> None:
        from questionnaire_models import QuestionnaireVersion
        from questionnaire_validation import validate_version_state

        with sqlite_session(self.app) as session:
            creator = self._add_user(session, "historical-creator")
            definition = self._make_definition(session, creator)
            historical = QuestionnaireVersion(
                **self._version_fields(
                    definition,
                    creator,
                    status="published",
                    published_by_user_id=creator.id,
                    published_at=datetime.now(UTC),
                )
            )
            self.assertIsNone(validate_version_state(historical, definition))

    def test_validate_version_source_rejects_self_and_other_definition(self) -> None:
        from questionnaire_models import QuestionnaireVersion
        from questionnaire_validation import validate_version_source

        with sqlite_session(self.app) as session:
            creator = self._add_user(session, "source-creator")
            first_definition = self._make_definition(session, creator)
            other_definition = self._make_definition(
                session,
                creator,
                definition_code="second_definition",
                scope_key="second",
            )
            version = QuestionnaireVersion(
                **self._version_fields(first_definition, creator)
            )
            session.add(version)
            session.flush()
            other_version = QuestionnaireVersion(
                **self._version_fields(other_definition, creator)
            )
            session.add(other_version)
            session.flush()
            with self.assertRaises(ValueError):
                validate_version_source(version, version)
            with self.assertRaises(ValueError):
                validate_version_source(version, other_version)

    def test_source_id_without_source_record_is_rejected(self) -> None:
        from questionnaire_models import QuestionnaireVersion
        from questionnaire_validation import validate_version_source
        version = QuestionnaireVersion(id=7, definition_id=1, source_version_id=6, version_number=2, status="draft", created_by_user_id=1)
        with self.assertRaises(ValueError):
            validate_version_source(version, None)

    def test_source_id_cannot_reference_the_same_version(self) -> None:
        from questionnaire_models import QuestionnaireVersion
        from questionnaire_validation import validate_version_source
        version = QuestionnaireVersion(id=7, definition_id=1, source_version_id=7, version_number=2, status="draft", created_by_user_id=1)
        with self.assertRaises(ValueError):
            validate_version_source(version, None)

    def test_source_relationship_must_match_source_version_id(self) -> None:
        from questionnaire_models import QuestionnaireVersion
        from questionnaire_validation import validate_version_source
        version = QuestionnaireVersion(definition_id=1, source_version_id=2, version_number=3, status="draft", created_by_user_id=1)
        source = QuestionnaireVersion(id=3, definition_id=1, version_number=2, status="draft", created_by_user_id=1)
        with self.assertRaises(ValueError):
            validate_version_source(version, source)

    def test_validate_version_source_rejects_distinct_transient_definitions(self) -> None:
        from questionnaire_models import QuestionnaireDefinition, QuestionnaireVersion
        from questionnaire_validation import validate_version_source

        left = QuestionnaireDefinition(
            definition_code="left",
            name="Left",
            scope_type="general",
            scope_key="left",
            created_by_user_id=1,
        )
        right = QuestionnaireDefinition(
            definition_code="right",
            name="Right",
            scope_type="general",
            scope_key="right",
            created_by_user_id=1,
        )
        version = QuestionnaireVersion(
            definition=left,
            version_number=2,
            status="draft",
            created_by_user_id=1,
        )
        source = QuestionnaireVersion(
            definition=right,
            version_number=1,
            status="draft",
            created_by_user_id=1,
        )

        with self.assertRaises(ValueError):
            validate_version_source(version, source)

    def test_validate_version_source_accepts_equivalent_persisted_definition_ids(self) -> None:
        from questionnaire_models import QuestionnaireDefinition, QuestionnaireVersion
        from questionnaire_validation import validate_version_source

        left = QuestionnaireDefinition(
            id=7,
            definition_code="left",
            name="Left",
            scope_type="general",
            scope_key="general",
            created_by_user_id=1,
        )
        equivalent = QuestionnaireDefinition(
            id=7,
            definition_code="equivalent",
            name="Equivalent",
            scope_type="general",
            scope_key="general",
            created_by_user_id=1,
        )
        version = QuestionnaireVersion(
            definition=left,
            version_number=2,
            status="draft",
            created_by_user_id=1,
        )
        source = QuestionnaireVersion(
            definition=equivalent,
            version_number=1,
            status="draft",
            created_by_user_id=1,
        )

        self.assertIsNone(validate_version_source(version, source))


if __name__ == "__main__":
    unittest.main()
