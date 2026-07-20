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
        self.assertTrue(hasattr(QuestionnaireVersion, "questions"))
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


class QuestionOptionModelTests(QuestionnaireFoundationTestCase):
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

    def _add_version(self, session):
        from questionnaire_models import QuestionnaireDefinition, QuestionnaireVersion

        creator = self._add_user(session, "question-option-creator")
        definition = QuestionnaireDefinition(
            definition_code="question_option_definition",
            name="Question option definition",
            scope_type="general",
            scope_key="general",
            created_by_user_id=creator.id,
        )
        session.add(definition)
        session.flush()
        version = QuestionnaireVersion(
            definition_id=definition.id,
            version_number=1,
            status="draft",
            created_by_user_id=creator.id,
        )
        session.add(version)
        session.flush()
        return version

    def _question_fields(self, version, **overrides):
        fields = {
            "version_id": version.id,
            "question_code": "favorite_tools",
            "title": "Which tools do you use?",
            "description": None,
            "question_type": "multiple_choice",
            "required": True,
            "sort_order": 1,
            "enabled": True,
            "is_general": True,
            "min_selections": 1,
            "max_selections": 2,
            "max_length": None,
        }
        fields.update(overrides)
        return fields

    def _option_fields(self, question, **overrides):
        fields = {
            "question_id": question.id,
            "option_value": "design",
            "label": "Design tools",
            "sort_order": 1,
            "enabled": True,
        }
        fields.update(overrides)
        return fields

    def test_question_and_option_contract_constants_columns_and_restrict_foreign_keys(self) -> None:
        from questionnaire_constants import QUESTION_TYPES
        from questionnaire_models import QuestionnaireOption, QuestionnaireQuestion

        self.assertEqual(
            QUESTION_TYPES,
            frozenset({"single_choice", "multiple_choice", "short_text"}),
        )
        self.assertEqual(QuestionnaireQuestion.__table__.c.question_code.type.length, 96)
        self.assertEqual(QuestionnaireQuestion.__table__.c.title.type.length, 300)
        self.assertEqual(QuestionnaireQuestion.__table__.c.question_type.type.length, 32)
        self.assertEqual(QuestionnaireOption.__table__.c.option_value.type.length, 96)
        self.assertEqual(QuestionnaireOption.__table__.c.label.type.length, 300)
        self.assertEqual(
            next(iter(QuestionnaireQuestion.__table__.c.version_id.foreign_keys)).ondelete,
            "RESTRICT",
        )
        self.assertEqual(
            next(iter(QuestionnaireOption.__table__.c.question_id.foreign_keys)).ondelete,
            "RESTRICT",
        )

    def test_question_and_option_relationships_are_explicit_bidirectional_and_sorted(self) -> None:
        from questionnaire_models import (
            QuestionnaireOption,
            QuestionnaireQuestion,
            QuestionnaireVersion,
        )

        configure_mappers()
        self.assertIs(QuestionnaireQuestion.version.property.mapper.class_, QuestionnaireVersion)
        self.assertIs(QuestionnaireVersion.questions.property.mapper.class_, QuestionnaireQuestion)
        self.assertIs(QuestionnaireOption.question.property.mapper.class_, QuestionnaireQuestion)
        self.assertIs(QuestionnaireQuestion.options.property.mapper.class_, QuestionnaireOption)
        self.assertEqual(QuestionnaireQuestion.version.property.back_populates, "questions")
        self.assertEqual(QuestionnaireVersion.questions.property.back_populates, "version")
        self.assertEqual(QuestionnaireOption.question.property.back_populates, "options")
        self.assertEqual(QuestionnaireQuestion.options.property.back_populates, "question")
        self.assertEqual(
            tuple(QuestionnaireVersion.questions.property.order_by),
            (QuestionnaireQuestion.sort_order,),
        )
        self.assertEqual(
            tuple(QuestionnaireQuestion.options.property.order_by),
            (QuestionnaireOption.sort_order,),
        )

    def test_question_code_is_unique_per_version_and_option_value_is_unique_per_question(self) -> None:
        from questionnaire_models import QuestionnaireOption, QuestionnaireQuestion

        with sqlite_session(self.app) as session:
            version = self._add_version(session)
            first = QuestionnaireQuestion(**self._question_fields(version))
            session.add(first)
            session.flush()
            session.add(QuestionnaireQuestion(**self._question_fields(version, title="Different")))
            with self.assertRaises(IntegrityError):
                session.flush()
            session.rollback()

            version = self._add_version(session)
            question = QuestionnaireQuestion(**self._question_fields(version))
            session.add(question)
            session.flush()
            session.add_all((
                QuestionnaireOption(**self._option_fields(question)),
                QuestionnaireOption(**self._option_fields(question, label="Different label")),
            ))
            with self.assertRaises(IntegrityError):
                session.flush()

    def test_question_and_option_helpers_persist_rows_and_relationships_in_sort_order(self) -> None:
        from tests.questionnaire_foundation_test_support import add_option, add_question

        with sqlite_session(self.app) as session:
            version = self._add_version(session)
            question = add_question(session, **self._question_fields(version))
            second = add_option(
                session,
                **self._option_fields(question, option_value="develop", sort_order=2),
            )
            first = add_option(
                session,
                **self._option_fields(question, option_value="design", sort_order=1),
            )
            self.assertEqual(question.version, version)
            self.assertEqual(question.options, [first, second])
            self.assertIs(second.question, question)

    def test_validate_question_rejects_invalid_stable_fields_and_version_relationship_mismatch(self) -> None:
        from questionnaire_models import QuestionnaireQuestion, QuestionnaireVersion
        from questionnaire_validation import validate_question

        version = QuestionnaireVersion(id=1, definition_id=1, version_number=1, status="draft", created_by_user_id=1)
        other_version = QuestionnaireVersion(id=2, definition_id=1, version_number=2, status="draft", created_by_user_id=1)
        mismatched_version = self._question_fields(version, version_id=other_version.id)
        mismatched_version["version"] = version
        cases = (
            self._question_fields(version, question_code="Favorite tools"),
            self._question_fields(version, title="   "),
            self._question_fields(version, question_type="unknown"),
            self._question_fields(version, sort_order=-1),
            mismatched_version,
        )
        for fields in cases:
            with self.subTest(fields=fields):
                with self.assertRaises(ValueError):
                    validate_question(QuestionnaireQuestion(**fields))

    def test_validate_question_rejects_a_transient_version_with_a_nonempty_foreign_key(self) -> None:
        from questionnaire_models import QuestionnaireQuestion, QuestionnaireVersion
        from questionnaire_validation import validate_question

        fields = self._question_fields(
            QuestionnaireVersion(id=1, version_number=1, status="draft"),
            question_type="short_text",
            min_selections=None,
            max_selections=None,
            max_length=1,
        )
        fields["version"] = QuestionnaireVersion(version_number=1, status="draft")
        question = QuestionnaireQuestion(**fields)

        with self.assertRaises(ValueError):
            validate_question(question)

    def test_validate_question_accepts_coherent_version_relationship_keys(self) -> None:
        from questionnaire_models import QuestionnaireQuestion, QuestionnaireVersion
        from questionnaire_validation import validate_question

        persisted_version = QuestionnaireVersion(id=1, version_number=1, status="draft")
        same_id_version = QuestionnaireVersion(id=1, version_number=1, status="draft")
        transient_version = QuestionnaireVersion(version_number=1, status="draft")
        matching_relationship = self._question_fields(
            persisted_version,
            question_type="short_text",
            min_selections=None,
            max_selections=None,
            max_length=1,
        )
        matching_relationship["version"] = same_id_version
        relationship_without_foreign_key = self._question_fields(
            persisted_version,
            version_id=None,
            question_type="short_text",
            min_selections=None,
            max_selections=None,
            max_length=1,
        )
        relationship_without_foreign_key["version"] = transient_version
        cases = (
            self._question_fields(
                persisted_version,
                question_type="short_text",
                min_selections=None,
                max_selections=None,
                max_length=1,
            ),
            matching_relationship,
            relationship_without_foreign_key,
        )

        for fields in cases:
            with self.subTest(fields=fields):
                self.assertIsNone(validate_question(QuestionnaireQuestion(**fields)))

    def test_validate_option_rejects_invalid_stable_fields_and_question_relationship_mismatch(self) -> None:
        from questionnaire_models import QuestionnaireOption, QuestionnaireQuestion
        from questionnaire_validation import validate_option

        question = QuestionnaireQuestion(id=1, version_id=1, question_code="tools", title="Tools", question_type="single_choice", sort_order=1)
        other_question = QuestionnaireQuestion(id=2, version_id=1, question_code="other", title="Other", question_type="single_choice", sort_order=2)
        mismatched_question = self._option_fields(question, question_id=other_question.id)
        mismatched_question["question"] = question
        cases = (
            self._option_fields(question, option_value="Design tools"),
            self._option_fields(question, label="  "),
            self._option_fields(question, sort_order=-1),
            mismatched_question,
        )
        for fields in cases:
            with self.subTest(fields=fields):
                with self.assertRaises(ValueError):
                    validate_option(QuestionnaireOption(**fields))

    def test_validate_option_rejects_a_transient_question_with_a_nonempty_foreign_key(self) -> None:
        from questionnaire_models import QuestionnaireOption, QuestionnaireQuestion
        from questionnaire_validation import validate_option

        option = QuestionnaireOption(
            question_id=1,
            question=QuestionnaireQuestion(
                question_code="tools",
                title="Tools",
                question_type="single_choice",
                sort_order=1,
            ),
            option_value="design",
            label="Design tools",
            sort_order=1,
            enabled=True,
        )

        with self.assertRaises(ValueError):
            validate_option(option)

    def test_validate_option_accepts_coherent_question_relationship_keys(self) -> None:
        from questionnaire_models import QuestionnaireOption, QuestionnaireQuestion
        from questionnaire_validation import validate_option

        persisted_question = QuestionnaireQuestion(
            id=1,
            version_id=1,
            question_code="tools",
            title="Tools",
            question_type="single_choice",
            sort_order=1,
        )
        same_id_question = QuestionnaireQuestion(
            id=1,
            version_id=1,
            question_code="tools_copy",
            title="Tools copy",
            question_type="single_choice",
            sort_order=1,
        )
        transient_question = QuestionnaireQuestion(
            question_code="transient",
            title="Transient",
            question_type="single_choice",
            sort_order=1,
        )
        matching_relationship = self._option_fields(persisted_question)
        matching_relationship["question"] = same_id_question
        relationship_without_foreign_key = self._option_fields(
            persisted_question,
            question_id=None,
        )
        relationship_without_foreign_key["question"] = transient_question
        cases = (
            self._option_fields(persisted_question),
            matching_relationship,
            relationship_without_foreign_key,
        )

        for fields in cases:
            with self.subTest(fields=fields):
                self.assertIsNone(validate_option(QuestionnaireOption(**fields)))

    def test_required_multiple_choice_requires_a_positive_minimum_and_optional_allows_zero(self) -> None:
        from questionnaire_models import QuestionnaireOption, QuestionnaireQuestion
        from questionnaire_validation import validate_question

        version = self._add_transient_version()
        for required, minimum, valid in (
            (True, None, False),
            (True, 0, False),
            (True, 1, True),
            (False, 0, True),
            (False, None, True),
        ):
            question = QuestionnaireQuestion(
                **self._question_fields(version, required=required, min_selections=minimum)
            )
            with self.subTest(required=required, minimum=minimum):
                if valid:
                    question.options.extend((
                        QuestionnaireOption(
                            option_value="first",
                            label="First",
                            sort_order=1,
                            enabled=True,
                        ),
                        QuestionnaireOption(
                            option_value="second",
                            label="Second",
                            sort_order=2,
                            enabled=True,
                        ),
                    ))
                    self.assertIsNone(validate_question(question))
                else:
                    with self.assertRaises(ValueError):
                        validate_question(question)

    def test_multiple_choice_maximum_must_fit_enabled_options_and_not_be_less_than_minimum(self) -> None:
        from questionnaire_models import QuestionnaireOption, QuestionnaireQuestion
        from questionnaire_validation import validate_question

        version = self._add_transient_version()
        question = QuestionnaireQuestion(**self._question_fields(version, min_selections=2, max_selections=3))
        options = [
            QuestionnaireOption(option_value="one", label="One", sort_order=1, enabled=True),
            QuestionnaireOption(option_value="two", label="Two", sort_order=2, enabled=True),
            QuestionnaireOption(option_value="three", label="Three", sort_order=3, enabled=False),
        ]
        with self.assertRaises(ValueError):
            validate_question(question, options)
        question.max_selections = 1
        with self.assertRaises(ValueError):
            validate_question(question, options)
        question.max_selections = 2
        self.assertIsNone(validate_question(question, options))

    def test_single_choice_forbids_selection_limits_and_max_length(self) -> None:
        from questionnaire_models import QuestionnaireQuestion
        from questionnaire_validation import validate_question

        version = self._add_transient_version()
        for fields in (
            self._question_fields(version, question_type="single_choice", min_selections=1, max_selections=None),
            self._question_fields(version, question_type="single_choice", min_selections=None, max_selections=1),
            self._question_fields(version, question_type="single_choice", min_selections=None, max_selections=None, max_length=100),
        ):
            with self.subTest(fields=fields):
                with self.assertRaises(ValueError):
                    validate_question(QuestionnaireQuestion(**fields))

    def test_short_text_requires_positive_max_length_and_no_options(self) -> None:
        from questionnaire_models import QuestionnaireOption, QuestionnaireQuestion
        from questionnaire_validation import validate_question

        version = self._add_transient_version()
        for max_length in (None, 0, -1):
            with self.subTest(max_length=max_length):
                with self.assertRaises(ValueError):
                    validate_question(
                        QuestionnaireQuestion(
                            **self._question_fields(
                                version,
                                question_type="short_text",
                                min_selections=None,
                                max_selections=None,
                                max_length=max_length,
                            )
                        )
                    )
        question = QuestionnaireQuestion(
            **self._question_fields(
                version,
                question_type="short_text",
                min_selections=None,
                max_selections=None,
                max_length=200,
            )
        )
        with self.assertRaises(ValueError):
            validate_question(
                question,
                [QuestionnaireOption(option_value="invalid", label="Invalid", sort_order=1, enabled=True)],
            )
        self.assertIsNone(validate_question(question, ()))

    def test_choice_questions_require_an_enabled_option(self) -> None:
        from questionnaire_models import QuestionnaireOption, QuestionnaireQuestion
        from questionnaire_validation import validate_question

        version = self._add_transient_version()
        question = QuestionnaireQuestion(**self._question_fields(version, question_type="single_choice", min_selections=None, max_selections=None))
        disabled_option = QuestionnaireOption(option_value="disabled", label="Disabled", sort_order=1, enabled=False)
        with self.assertRaises(ValueError):
            validate_question(question, ())
        with self.assertRaises(ValueError):
            validate_question(question, (disabled_option,))
        enabled_option = QuestionnaireOption(option_value="enabled", label="Enabled", sort_order=2, enabled=True)
        self.assertIsNone(validate_question(question, (enabled_option,)))

    def test_validate_question_defaults_to_its_relationship_options(self) -> None:
        from questionnaire_models import QuestionnaireOption, QuestionnaireQuestion
        from questionnaire_validation import validate_question

        version = self._add_transient_version()
        choice = QuestionnaireQuestion(
            **self._question_fields(
                version,
                question_type="single_choice",
                min_selections=None,
                max_selections=None,
            )
        )
        with self.assertRaises(ValueError):
            validate_question(choice)
        choice.options.append(
            QuestionnaireOption(
                option_value="enabled",
                label="Enabled",
                sort_order=1,
                enabled=True,
            )
        )
        self.assertIsNone(validate_question(choice))

        short_text = QuestionnaireQuestion(
            **self._question_fields(
                version,
                question_type="short_text",
                min_selections=None,
                max_selections=None,
                max_length=200,
            )
        )
        short_text.options.append(
            QuestionnaireOption(
                option_value="invalid",
                label="Invalid",
                sort_order=1,
                enabled=True,
            )
        )
        with self.assertRaises(ValueError):
            validate_question(short_text)

        multiple = QuestionnaireQuestion(
            **self._question_fields(version, max_selections=2)
        )
        multiple.options.append(
            QuestionnaireOption(
                option_value="only_option",
                label="Only option",
                sort_order=1,
                enabled=True,
            )
        )
        with self.assertRaises(ValueError):
            validate_question(multiple)

    def test_display_text_changes_do_not_change_stable_question_or_option_keys(self) -> None:
        from questionnaire_models import QuestionnaireOption, QuestionnaireQuestion
        from questionnaire_validation import validate_option, validate_question

        version = self._add_transient_version()
        question = QuestionnaireQuestion(**self._question_fields(version))
        option = QuestionnaireOption(option_value="design", label="Design", sort_order=1, enabled=True)
        question.title = "Which creative tools do you use most?"
        option.label = "Visual design tools"
        self.assertEqual(question.question_code, "favorite_tools")
        self.assertEqual(option.option_value, "design")
        question.options.extend((
            option,
            QuestionnaireOption(
                option_value="develop",
                label="Development tools",
                sort_order=2,
                enabled=True,
            ),
        ))
        self.assertIsNone(validate_question(question))
        self.assertIsNone(validate_option(option))

    @staticmethod
    def _add_transient_version():
        from questionnaire_models import QuestionnaireVersion

        return QuestionnaireVersion(
            id=1,
            definition_id=1,
            version_number=1,
            status="draft",
            created_by_user_id=1,
        )


class QuestionnaireConditionModelTests(QuestionOptionModelTests):
    """Task 5 condition relationships and validation rules."""

    def _condition_question_fields(self, version, **overrides):
        fields = {
            "version_id": version.id,
            "question_code": "source_question",
            "title": "Source question",
            "description": None,
            "question_type": "single_choice",
            "required": False,
            "sort_order": 1,
            "enabled": True,
            "is_general": True,
            "min_selections": None,
            "max_selections": None,
            "max_length": None,
        }
        fields.update(overrides)
        return fields

    def _add_condition_records(self, session):
        from tests.questionnaire_foundation_test_support import add_option, add_question

        version = self._add_version(session)
        source = add_question(session, **self._condition_question_fields(version))
        target = add_question(
            session,
            **self._condition_question_fields(
                version,
                question_code="target_question",
                title="Target question",
                question_type="short_text",
                sort_order=2,
                max_length=200,
            ),
        )
        expected_option = add_option(
            session,
            **self._option_fields(source, option_value="approved", label="Approved"),
        )
        return version, source, target, expected_option

    def test_condition_contract_uses_stable_operator_values_and_restrict_foreign_keys(self) -> None:
        from questionnaire_constants import CONDITION_OPERATORS
        from questionnaire_models import QuestionnaireCondition

        self.assertEqual(CONDITION_OPERATORS, frozenset({"equals", "contains"}))
        self.assertEqual(QuestionnaireCondition.__table__.c.operator.type.length, 16)
        self.assertEqual(
            {foreign_key.ondelete for column in (
                QuestionnaireCondition.__table__.c.version_id,
                QuestionnaireCondition.__table__.c.source_question_id,
                QuestionnaireCondition.__table__.c.target_question_id,
                QuestionnaireCondition.__table__.c.expected_option_id,
            ) for foreign_key in column.foreign_keys},
            {"RESTRICT"},
        )

    def test_condition_relationships_are_explicit_bidirectional_and_mappers_configure(self) -> None:
        from questionnaire_models import (
            QuestionnaireCondition,
            QuestionnaireOption,
            QuestionnaireQuestion,
            QuestionnaireVersion,
        )

        configure_mappers()
        self.assertIs(QuestionnaireCondition.version.property.mapper.class_, QuestionnaireVersion)
        self.assertIs(QuestionnaireVersion.conditions.property.mapper.class_, QuestionnaireCondition)
        self.assertIs(QuestionnaireCondition.source_question.property.mapper.class_, QuestionnaireQuestion)
        self.assertIs(QuestionnaireQuestion.source_conditions.property.mapper.class_, QuestionnaireCondition)
        self.assertIs(QuestionnaireCondition.target_question.property.mapper.class_, QuestionnaireQuestion)
        self.assertIs(QuestionnaireQuestion.target_condition.property.mapper.class_, QuestionnaireCondition)
        self.assertIs(QuestionnaireCondition.expected_option.property.mapper.class_, QuestionnaireOption)
        self.assertIs(QuestionnaireOption.condition_references.property.mapper.class_, QuestionnaireCondition)
        self.assertEqual(QuestionnaireQuestion.target_condition.property.uselist, False)
        self.assertEqual(QuestionnaireCondition.source_question.property.back_populates, "source_conditions")
        self.assertEqual(QuestionnaireCondition.target_question.property.back_populates, "target_condition")
        self.assertEqual(QuestionnaireCondition.expected_option.property.back_populates, "condition_references")

    def test_add_condition_persists_and_exposes_bidirectional_relationships(self) -> None:
        from tests.questionnaire_foundation_test_support import add_condition

        with sqlite_session(self.app) as session:
            version, source, target, expected_option = self._add_condition_records(session)
            condition = add_condition(
                session,
                version_id=version.id,
                source_question_id=source.id,
                target_question_id=target.id,
                expected_option_id=expected_option.id,
                operator="equals",
            )

            self.assertEqual(version.conditions, [condition])
            self.assertEqual(source.source_conditions, [condition])
            self.assertIs(target.target_condition, condition)
            self.assertEqual(expected_option.condition_references, [condition])

    def test_target_question_has_only_one_condition(self) -> None:
        from questionnaire_models import QuestionnaireCondition

        with sqlite_session(self.app) as session:
            version, source, target, expected_option = self._add_condition_records(session)
            session.add(
                QuestionnaireCondition(
                    version_id=version.id,
                    source_question_id=source.id,
                    target_question_id=target.id,
                    expected_option_id=expected_option.id,
                    operator="equals",
                )
            )
            session.flush()
            session.add(
                QuestionnaireCondition(
                    version_id=version.id,
                    source_question_id=source.id,
                    target_question_id=target.id,
                    expected_option_id=expected_option.id,
                    operator="equals",
                )
            )
            with self.assertRaises(IntegrityError):
                session.flush()

    def test_validate_condition_rejects_cross_version_source_or_target(self) -> None:
        from questionnaire_models import QuestionnaireQuestion
        from questionnaire_validation import validate_condition

        source = QuestionnaireQuestion(id=1, version_id=1, question_code="source", title="Source", question_type="single_choice", sort_order=1)
        target = QuestionnaireQuestion(id=2, version_id=2, question_code="target", title="Target", question_type="short_text", sort_order=2, max_length=1)
        from questionnaire_models import QuestionnaireOption
        option = QuestionnaireOption(id=1, question_id=source.id, option_value="yes", label="Yes", sort_order=1, enabled=True, question=source)

        with self.assertRaises(ValueError):
            validate_condition(source, target, option, "equals")

    def test_validate_condition_rejects_distinct_transient_versions(self) -> None:
        from questionnaire_models import (
            QuestionnaireOption,
            QuestionnaireQuestion,
            QuestionnaireVersion,
        )
        from questionnaire_validation import validate_condition

        left_version = QuestionnaireVersion(version_number=1, status="draft")
        right_version = QuestionnaireVersion(version_number=1, status="draft")
        source = QuestionnaireQuestion(version=left_version, question_code="source", title="Source", question_type="single_choice", sort_order=1)
        target = QuestionnaireQuestion(version=right_version, question_code="target", title="Target", question_type="short_text", sort_order=2, max_length=1)
        option = QuestionnaireOption(option_value="yes", label="Yes", sort_order=1, enabled=True, question=source)

        with self.assertRaises(ValueError):
            validate_condition(source, target, option, "equals")

    def test_validate_condition_rejects_conflicting_question_and_option_relationship_keys(self) -> None:
        from questionnaire_models import (
            QuestionnaireOption,
            QuestionnaireQuestion,
            QuestionnaireVersion,
        )
        from questionnaire_validation import validate_condition

        source_version = QuestionnaireVersion(id=1, version_number=1, status="draft")
        other_version = QuestionnaireVersion(id=2, version_number=1, status="draft")
        source = QuestionnaireQuestion(id=1, version_id=1, question_code="source", title="Source", question_type="single_choice", sort_order=1)
        target = QuestionnaireQuestion(id=2, version_id=1, question_code="target", title="Target", question_type="short_text", sort_order=2, max_length=1)
        other_question = QuestionnaireQuestion(id=3, version_id=1, question_code="other", title="Other", question_type="single_choice", sort_order=1)
        option = QuestionnaireOption(id=1, question_id=source.id, option_value="yes", label="Yes", sort_order=1, enabled=True, question=source)
        cases = (
            (QuestionnaireQuestion(id=source.id, version_id=source_version.id, version=other_version, question_code="source", title="Source", question_type="single_choice", sort_order=1), target, option),
            (source, QuestionnaireQuestion(id=target.id, version_id=source_version.id, version=other_version, question_code="target", title="Target", question_type="short_text", sort_order=2, max_length=1), option),
            (source, target, QuestionnaireOption(id=option.id, question_id=other_question.id, question=source, option_value="yes", label="Yes", sort_order=1, enabled=True)),
        )
        for invalid_source, invalid_target, invalid_option in cases:
            with self.subTest(source=invalid_source.question_code, target=invalid_target.question_code, option=invalid_option.option_value):
                with self.assertRaises(ValueError):
                    validate_condition(invalid_source, invalid_target, invalid_option, "equals")

    def test_validate_condition_rejects_boolean_sort_order(self) -> None:
        from questionnaire_models import QuestionnaireOption, QuestionnaireQuestion
        from questionnaire_validation import validate_condition

        source = QuestionnaireQuestion(id=1, version_id=1, question_code="source", title="Source", question_type="single_choice", sort_order=True)
        target = QuestionnaireQuestion(id=2, version_id=1, question_code="target", title="Target", question_type="short_text", sort_order=2, max_length=1)
        option = QuestionnaireOption(id=1, question_id=source.id, option_value="yes", label="Yes", sort_order=1, enabled=True, question=source)

        with self.assertRaises(ValueError):
            validate_condition(source, target, option, "equals")

    def test_validate_condition_rejects_transient_relationships_with_nonempty_foreign_keys(self) -> None:
        from questionnaire_models import (
            QuestionnaireOption,
            QuestionnaireQuestion,
            QuestionnaireVersion,
        )
        from questionnaire_validation import validate_condition

        source = QuestionnaireQuestion(id=1, version_id=1, question_code="source", title="Source", question_type="single_choice", sort_order=1)
        target = QuestionnaireQuestion(id=2, version_id=1, question_code="target", title="Target", question_type="short_text", sort_order=2, max_length=1)
        option = QuestionnaireOption(id=1, question_id=source.id, option_value="yes", label="Yes", sort_order=1, enabled=True, question=source)
        cases = (
            (QuestionnaireQuestion(id=source.id, version_id=1, version=QuestionnaireVersion(version_number=1, status="draft"), question_code="source", title="Source", question_type="single_choice", sort_order=1), target, option),
            (source, QuestionnaireQuestion(id=target.id, version_id=1, version=QuestionnaireVersion(version_number=1, status="draft"), question_code="target", title="Target", question_type="short_text", sort_order=2, max_length=1), option),
            (source, target, QuestionnaireOption(id=option.id, question_id=source.id, question=QuestionnaireQuestion(question_code="transient", title="Transient", question_type="single_choice", sort_order=1), option_value="yes", label="Yes", sort_order=1, enabled=True)),
        )
        for invalid_source, invalid_target, invalid_option in cases:
            with self.subTest(source=invalid_source.question_code, target=invalid_target.question_code, option=invalid_option.option_value):
                with self.assertRaises(ValueError):
                    validate_condition(invalid_source, invalid_target, invalid_option, "equals")

    def test_validate_condition_rejects_backward_or_self_references(self) -> None:
        from questionnaire_models import QuestionnaireOption, QuestionnaireQuestion
        from questionnaire_validation import validate_condition

        source = QuestionnaireQuestion(id=1, version_id=1, question_code="source", title="Source", question_type="single_choice", sort_order=2)
        option = QuestionnaireOption(id=1, question_id=source.id, option_value="yes", label="Yes", sort_order=1, enabled=True, question=source)
        backward = QuestionnaireQuestion(id=2, version_id=1, question_code="backward", title="Backward", question_type="short_text", sort_order=1, max_length=1)
        with self.assertRaises(ValueError):
            validate_condition(source, backward, option, "equals")
        with self.assertRaises(ValueError):
            validate_condition(source, source, option, "equals")

    def test_validate_condition_rejects_option_from_another_question_or_disabled_option(self) -> None:
        from questionnaire_models import QuestionnaireOption, QuestionnaireQuestion
        from questionnaire_validation import validate_condition

        source = QuestionnaireQuestion(id=1, version_id=1, question_code="source", title="Source", question_type="single_choice", sort_order=1)
        target = QuestionnaireQuestion(id=2, version_id=1, question_code="target", title="Target", question_type="short_text", sort_order=2, max_length=1)
        other = QuestionnaireQuestion(id=3, version_id=1, question_code="other", title="Other", question_type="single_choice", sort_order=1)
        foreign_option = QuestionnaireOption(id=1, question_id=other.id, option_value="yes", label="Yes", sort_order=1, enabled=True, question=other)
        disabled_option = QuestionnaireOption(id=2, question_id=source.id, option_value="no", label="No", sort_order=2, enabled=False, question=source)
        for option in (foreign_option, disabled_option):
            with self.subTest(option=option.option_value):
                with self.assertRaises(ValueError):
                    validate_condition(source, target, option, "equals")

    def test_validate_condition_accepts_only_matching_choice_operator_types(self) -> None:
        from questionnaire_models import QuestionnaireOption, QuestionnaireQuestion
        from questionnaire_validation import validate_condition

        target = QuestionnaireQuestion(id=3, version_id=1, question_code="target", title="Target", question_type="short_text", sort_order=3, max_length=1)
        single = QuestionnaireQuestion(id=1, version_id=1, question_code="single", title="Single", question_type="single_choice", sort_order=1)
        multiple = QuestionnaireQuestion(id=2, version_id=1, question_code="multiple", title="Multiple", question_type="multiple_choice", sort_order=2)
        single_option = QuestionnaireOption(id=1, question_id=single.id, option_value="one", label="One", sort_order=1, enabled=True, question=single)
        multiple_option = QuestionnaireOption(id=2, question_id=multiple.id, option_value="many", label="Many", sort_order=1, enabled=True, question=multiple)
        self.assertIsNone(validate_condition(single, target, single_option, "equals"))
        self.assertIsNone(validate_condition(multiple, target, multiple_option, "contains"))
        for source, option, operator in (
            (single, single_option, "contains"),
            (multiple, multiple_option, "equals"),
            (single, single_option, "unknown"),
        ):
            with self.subTest(operator=operator):
                with self.assertRaises(ValueError):
                    validate_condition(source, target, option, operator)

    def test_validate_condition_graph_rejects_cross_version_conditions_and_cycles(self) -> None:
        from questionnaire_models import QuestionnaireCondition, QuestionnaireOption, QuestionnaireQuestion
        from questionnaire_validation import validate_condition_graph

        questions = [
            QuestionnaireQuestion(id=index, version_id=1, question_code=f"q{index}", title=f"Question {index}", question_type="single_choice", sort_order=index)
            for index in range(1, 4)
        ]
        options = [
            QuestionnaireOption(id=index, question_id=question.id, option_value=f"option_{index}", label=f"Option {index}", sort_order=1, enabled=True, question=question)
            for index, question in enumerate(questions, start=1)
        ]
        cycle = [
            QuestionnaireCondition(version_id=1, source_question_id=questions[0].id, target_question_id=questions[1].id, expected_option_id=options[0].id, operator="equals", source_question=questions[0], target_question=questions[1], expected_option=options[0]),
            QuestionnaireCondition(version_id=1, source_question_id=questions[1].id, target_question_id=questions[2].id, expected_option_id=options[1].id, operator="equals", source_question=questions[1], target_question=questions[2], expected_option=options[1]),
            QuestionnaireCondition(version_id=1, source_question_id=questions[2].id, target_question_id=questions[0].id, expected_option_id=options[2].id, operator="equals", source_question=questions[2], target_question=questions[0], expected_option=options[2]),
        ]
        with self.assertRaisesRegex(ValueError, "cycle"):
            validate_condition_graph(questions, cycle)

        cross_version = QuestionnaireCondition(
            version_id=2,
            source_question_id=questions[0].id,
            target_question_id=questions[1].id,
            expected_option_id=options[0].id,
            operator="equals",
            source_question=questions[0],
            target_question=questions[1],
            expected_option=options[0],
        )
        with self.assertRaises(ValueError):
            validate_condition_graph(questions, (cross_version,))

    def test_validate_condition_graph_rejects_a_disconnected_question_with_a_transient_version_relationship(self) -> None:
        from questionnaire_models import QuestionnaireQuestion, QuestionnaireVersion
        from questionnaire_validation import validate_condition_graph

        version = QuestionnaireVersion(id=1, version_number=1, status="draft")
        source = QuestionnaireQuestion(
            id=1,
            version_id=version.id,
            question_code="source",
            title="Source",
            question_type="single_choice",
            sort_order=1,
        )
        disconnected = QuestionnaireQuestion(
            id=2,
            version_id=version.id,
            version=QuestionnaireVersion(version_number=1, status="draft"),
            question_code="disconnected",
            title="Disconnected",
            question_type="short_text",
            sort_order=2,
            max_length=1,
        )

        with self.assertRaises(ValueError):
            validate_condition_graph((source, disconnected), ())

    def test_validate_condition_graph_rejects_duplicate_transient_targets(self) -> None:
        from questionnaire_models import QuestionnaireCondition, QuestionnaireOption, QuestionnaireQuestion
        from questionnaire_validation import validate_condition_graph

        first_source = QuestionnaireQuestion(id=1, version_id=1, question_code="first", title="First", question_type="single_choice", sort_order=1)
        second_source = QuestionnaireQuestion(id=2, version_id=1, question_code="second", title="Second", question_type="single_choice", sort_order=2)
        target = QuestionnaireQuestion(id=3, version_id=1, question_code="target", title="Target", question_type="short_text", sort_order=3, max_length=1)
        first_option = QuestionnaireOption(id=1, question_id=first_source.id, option_value="one", label="One", sort_order=1, enabled=True, question=first_source)
        second_option = QuestionnaireOption(id=2, question_id=second_source.id, option_value="two", label="Two", sort_order=1, enabled=True, question=second_source)
        conditions = (
            QuestionnaireCondition(version_id=1, source_question=first_source, target_question=target, expected_option=first_option, operator="equals"),
            QuestionnaireCondition(version_id=1, source_question=second_source, target_question=target, expected_option=second_option, operator="equals"),
        )

        with self.assertRaisesRegex(ValueError, "target"):
            validate_condition_graph((first_source, second_source, target), conditions)

    def test_validate_condition_graph_rejects_conflicting_condition_relationship_keys(self) -> None:
        from questionnaire_models import QuestionnaireCondition, QuestionnaireOption, QuestionnaireQuestion, QuestionnaireVersion
        from questionnaire_validation import validate_condition_graph

        version = QuestionnaireVersion(id=1, version_number=1, status="draft")
        other_version = QuestionnaireVersion(id=2, version_number=1, status="draft")
        source = QuestionnaireQuestion(id=1, version_id=version.id, question_code="source", title="Source", question_type="single_choice", sort_order=1)
        target = QuestionnaireQuestion(id=2, version_id=version.id, question_code="target", title="Target", question_type="short_text", sort_order=2, max_length=1)
        other_question = QuestionnaireQuestion(id=3, version_id=version.id, question_code="other", title="Other", question_type="single_choice", sort_order=1)
        option = QuestionnaireOption(id=1, question_id=source.id, option_value="yes", label="Yes", sort_order=1, enabled=True, question=source)
        other_option = QuestionnaireOption(id=2, question_id=source.id, option_value="no", label="No", sort_order=2, enabled=True, question=source)
        cases = (
            QuestionnaireCondition(version_id=version.id, version=other_version, source_question_id=source.id, source_question=source, target_question_id=target.id, target_question=target, expected_option_id=option.id, expected_option=option, operator="equals"),
            QuestionnaireCondition(version_id=version.id, version=version, source_question_id=other_question.id, source_question=source, target_question_id=target.id, target_question=target, expected_option_id=option.id, expected_option=option, operator="equals"),
            QuestionnaireCondition(version_id=version.id, version=version, source_question_id=source.id, source_question=source, target_question_id=other_question.id, target_question=target, expected_option_id=option.id, expected_option=option, operator="equals"),
            QuestionnaireCondition(version_id=version.id, version=version, source_question_id=source.id, source_question=source, target_question_id=target.id, target_question=target, expected_option_id=other_option.id, expected_option=option, operator="equals"),
        )
        for condition in cases:
            with self.subTest(condition=condition):
                with self.assertRaises(ValueError):
                    validate_condition_graph((source, target), (condition,))

    def test_validate_condition_graph_rejects_transient_relationships_with_nonempty_foreign_keys(self) -> None:
        from questionnaire_models import QuestionnaireCondition, QuestionnaireOption, QuestionnaireQuestion, QuestionnaireVersion
        from questionnaire_validation import validate_condition_graph

        version = QuestionnaireVersion(id=1, version_number=1, status="draft")
        source = QuestionnaireQuestion(id=1, version_id=version.id, question_code="source", title="Source", question_type="single_choice", sort_order=1)
        target = QuestionnaireQuestion(id=2, version_id=version.id, question_code="target", title="Target", question_type="short_text", sort_order=2, max_length=1)
        option = QuestionnaireOption(id=1, question_id=source.id, option_value="yes", label="Yes", sort_order=1, enabled=True, question=source)
        cases = (
            QuestionnaireCondition(version_id=version.id, version=QuestionnaireVersion(version_number=1, status="draft"), source_question_id=source.id, source_question=source, target_question_id=target.id, target_question=target, expected_option_id=option.id, expected_option=option, operator="equals"),
            QuestionnaireCondition(version_id=version.id, version=version, source_question_id=source.id, source_question=QuestionnaireQuestion(question_code="transient_source", title="Transient source", question_type="single_choice", sort_order=1), target_question_id=target.id, target_question=target, expected_option_id=option.id, expected_option=option, operator="equals"),
            QuestionnaireCondition(version_id=version.id, version=version, source_question_id=source.id, source_question=source, target_question_id=target.id, target_question=QuestionnaireQuestion(question_code="transient_target", title="Transient target", question_type="short_text", sort_order=2, max_length=1), expected_option_id=option.id, expected_option=option, operator="equals"),
            QuestionnaireCondition(version_id=version.id, version=version, source_question_id=source.id, source_question=source, target_question_id=target.id, target_question=target, expected_option_id=option.id, expected_option=QuestionnaireOption(option_value="transient", label="Transient", sort_order=1, enabled=True), operator="equals"),
        )
        for condition in cases:
            with self.subTest(condition=condition):
                with self.assertRaises(ValueError):
                    validate_condition_graph((source, target), (condition,))

    def test_validate_condition_graph_rejects_distinct_transient_condition_version(self) -> None:
        from questionnaire_models import (
            QuestionnaireCondition,
            QuestionnaireOption,
            QuestionnaireQuestion,
            QuestionnaireVersion,
        )
        from questionnaire_validation import validate_condition_graph

        question_version = QuestionnaireVersion(version_number=1, status="draft")
        condition_version = QuestionnaireVersion(version_number=1, status="draft")
        source = QuestionnaireQuestion(version=question_version, question_code="source", title="Source", question_type="single_choice", sort_order=1)
        target = QuestionnaireQuestion(version=question_version, question_code="target", title="Target", question_type="short_text", sort_order=2, max_length=1)
        option = QuestionnaireOption(option_value="yes", label="Yes", sort_order=1, enabled=True, question=source)
        condition = QuestionnaireCondition(version=condition_version, source_question=source, target_question=target, expected_option=option, operator="equals")

        with self.assertRaisesRegex(ValueError, "version"):
            validate_condition_graph((source, target), (condition,))

    def test_condition_stable_snapshot_fields_survive_display_text_changes(self) -> None:
        from questionnaire_models import QuestionnaireCondition, QuestionnaireOption, QuestionnaireQuestion

        source = QuestionnaireQuestion(id=1, version_id=1, question_code="source", title="Source", question_type="single_choice", sort_order=1)
        target = QuestionnaireQuestion(id=2, version_id=1, question_code="target", title="Target", question_type="short_text", sort_order=2, max_length=1)
        option = QuestionnaireOption(id=1, question_id=source.id, option_value="yes", label="Yes", sort_order=1, enabled=True, question=source)
        condition = QuestionnaireCondition(source_question=source, target_question=target, expected_option=option, operator="equals")
        source.title, target.title, option.label = "Changed source", "Changed target", "Changed yes"
        self.assertEqual(
            (condition.source_question.question_code, condition.target_question.question_code, condition.expected_option.option_value),
            ("source", "target", "yes"),
        )


if __name__ == "__main__":
    unittest.main()
