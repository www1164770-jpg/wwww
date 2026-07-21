"""Task 10 scope-regression coverage for the questionnaire foundation."""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

from flask import Flask
from flask_jwt_extended import JWTManager

from tests.questionnaire_foundation_test_support import (
    FakeRoleConnectionFactory,
    dispose_sqlite_app,
    make_sqlite_app,
)


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
FOUNDATION_FILES = (
    "questionnaire_constants.py",
    "questionnaire_models.py",
    "questionnaire_validation.py",
    "questionnaire_read_service.py",
    "questionnaire_admin_support.py",
    "questionnaire_admin_read_routes.py",
)
NEW_ROUTES = frozenset(
    {
        "/api/admin/questionnaires/occupations",
        "/api/admin/questionnaires/definitions",
        "/api/admin/questionnaires/definitions/<int:definition_id>",
        "/api/admin/questionnaires/definitions/<int:definition_id>/versions",
        "/api/admin/questionnaires/versions/<int:version_id>",
        "/api/admin/questionnaires/versions/<int:version_id>/preview",
    }
)
LEGACY_ROUTES = frozenset(
    {
        "/api/questionnaire",
        "/api/questionnaire/submit",
        "/api/questionnaire/my",
    }
)


def _tree(filename: str) -> ast.Module:
    return ast.parse((BACKEND_DIR / filename).read_text(encoding="utf-8"), filename=filename)


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else None
    return None


def _route_declarations(tree: ast.Module) -> list[tuple[str, str, set[str] | None]]:
    declarations: list[tuple[str, str, set[str] | None]] = []
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in function.decorator_list:
            if not isinstance(decorator, ast.Call) or not decorator.args:
                continue
            decorator_name = _dotted_name(decorator.func)
            first_argument = decorator.args[0]
            if decorator_name not in {"app.get", "app.route"} or not isinstance(
                first_argument, ast.Constant
            ) or not isinstance(first_argument.value, str):
                continue
            methods = None
            for keyword in decorator.keywords:
                if keyword.arg != "methods" or not isinstance(keyword.value, (ast.List, ast.Tuple)):
                    continue
                methods = {
                    item.value
                    for item in keyword.value.elts
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)
                }
            declarations.append((first_argument.value, decorator_name, methods))
    return declarations


def _imports(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _is_db_session_mutation(call: ast.Call) -> bool:
    return _dotted_name(call.func) in {"db.session.commit", "db.session.delete"}


def _is_write_sql_execute(call: ast.Call) -> bool:
    if not isinstance(call.func, ast.Attribute) or call.func.attr != "execute" or not call.args:
        return False
    statement = call.args[0]
    if not isinstance(statement, ast.Constant) or not isinstance(statement.value, str):
        return False
    return statement.value.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))


class QuestionnaireFoundationRouteRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        from questionnaire_admin_read_routes import register_questionnaire_admin_read_routes

        self.app = make_sqlite_app()
        register_questionnaire_admin_read_routes(
            self.app, FakeRoleConnectionFactory({"admin": "admin"})
        )

    def tearDown(self) -> None:
        dispose_sqlite_app(self.app)

    def test_new_questionnaire_routes_are_exactly_the_six_get_endpoints(self) -> None:
        rules = {
            rule.rule: set(rule.methods)
            for rule in self.app.url_map.iter_rules()
            if rule.rule.startswith("/api/admin/questionnaires")
        }

        self.assertEqual(set(rules), NEW_ROUTES)
        for methods in rules.values():
            self.assertEqual(methods, {"GET", "HEAD", "OPTIONS"})

        declarations = _route_declarations(_tree("questionnaire_admin_read_routes.py"))
        self.assertEqual(
            {(path, decorator, methods) for path, decorator, methods in declarations},
            {(path, "app.get", None) for path in NEW_ROUTES},
        )

    def test_new_questionnaire_routes_reject_all_write_verbs_with_get_allow_header(self) -> None:
        client = self.app.test_client()
        concrete_paths = {
            path.replace("<int:definition_id>", "1").replace("<int:version_id>", "1")
            for path in NEW_ROUTES
        }

        for path in concrete_paths:
            for method in ("post", "put", "patch", "delete"):
                with self.subTest(path=path, method=method):
                    response = getattr(client, method)(path)
                    self.assertEqual(response.status_code, 405)
                    self.assertIn("GET", response.headers["Allow"])


class QuestionnaireFoundationLegacyRegressionTests(unittest.TestCase):
    def test_legacy_questionnaire_routes_remain_in_the_real_v1_url_map(self) -> None:
        from v1_routes import register_v1_routes

        app = Flask(__name__)
        app.config.update(TESTING=True, JWT_SECRET_KEY="questionnaire-v1-regression-secret")
        JWTManager(app)
        register_v1_routes(app, lambda: None)

        rules = {rule.rule for rule in app.url_map.iter_rules()}
        self.assertTrue(LEGACY_ROUTES.issubset(rules))

        declared_paths = {
            path
            for path, _decorator, _methods in _route_declarations(_tree("v1_routes.py"))
            if path in LEGACY_ROUTES
        }
        self.assertEqual(declared_paths, LEGACY_ROUTES)

    def test_legacy_questionnaire_user_fields_remain_model_columns(self) -> None:
        from models import User

        self.assertTrue(
            {"questionnaire_completed", "has_survey", "user_tags", "interests"}.issubset(
                User.__table__.columns.keys()
            )
        )


class QuestionnaireFoundationScopeRegressionTests(unittest.TestCase):
    def test_foundation_modules_remain_read_only_without_write_interfaces(self) -> None:
        for filename in FOUNDATION_FILES:
            with self.subTest(filename=filename):
                tree = _tree(filename)
                route_decorators = {
                    _dotted_name(decorator.func)
                    for node in ast.walk(tree)
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    for decorator in node.decorator_list
                    if isinstance(decorator, ast.Call)
                }
                calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]

                self.assertFalse(
                    route_decorators & {"app.post", "app.put", "app.patch", "app.delete"}
                )
                self.assertFalse(any(_is_db_session_mutation(call) for call in calls))
                self.assertFalse(any(_is_write_sql_execute(call) for call in calls))

    def test_foundation_module_boundaries_do_not_reach_unrelated_systems(self) -> None:
        imports_by_file = {filename: _imports(_tree(filename)) for filename in FOUNDATION_FILES}
        forbidden_prefixes = ("authing_service", "recommend_service", "frontend")
        for filename, imports in imports_by_file.items():
            with self.subTest(filename=filename):
                self.assertFalse(
                    any(
                        imported == prefix or imported.startswith(f"{prefix}.")
                        for imported in imports
                        for prefix in forbidden_prefixes
                    )
                )

        self.assertNotIn("app", imports_by_file["questionnaire_read_service.py"])
        self.assertNotIn("app", imports_by_file["questionnaire_models.py"])
        self.assertIn("models", imports_by_file["questionnaire_models.py"])

    def test_foundation_keeps_one_shared_sqlalchemy_base_and_no_later_phase_models_or_services(self) -> None:
        model_tree = _tree("questionnaire_models.py")
        model_imports = _imports(model_tree)
        model_calls = [node for node in ast.walk(model_tree) if isinstance(node, ast.Call)]
        names = {
            node.name
            for node in ast.walk(model_tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }

        self.assertIn("models", model_imports)
        self.assertNotIn("flask", model_imports)
        self.assertFalse(
            any(_dotted_name(call.func) in {"SQLAlchemy", "declarative_base"} for call in model_calls)
        )
        self.assertFalse(
            names
            & {
                "QuestionnaireResponse",
                "QuestionnaireAnswer",
                "QuestionnaireDraft",
                "publish_questionnaire",
                "rollback_questionnaire",
                "delete_questionnaire",
            }
        )


if __name__ == "__main__":
    unittest.main()
