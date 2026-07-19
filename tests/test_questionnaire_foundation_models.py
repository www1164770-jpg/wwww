"""Tests for the questionnaire foundation ORM models introduced task by task."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.questionnaire_foundation_test_support import (
    QuestionnaireFoundationTestCase,
    add_occupation,
    make_sqlite_app,
    sqlite_session,
)


class OccupationFoundationTests(QuestionnaireFoundationTestCase):
    def setUp(self) -> None:
        self.app = make_sqlite_app()

    def test_make_sqlite_app_registers_questionnaire_models_before_a_session_is_requested(self) -> None:
        from models import db

        make_sqlite_app()

        self.assertIn("occupations", db.metadata.tables)

    def test_occupation_uses_the_existing_global_models_db(self) -> None:
        from models import db
        from questionnaire_models import Occupation

        self.assertIs(Occupation.metadata, db.metadata)
        self.assertFalse(hasattr(__import__("questionnaire_models"), "Base"))

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


if __name__ == "__main__":
    unittest.main()
