"""Questionnaire ORM models registered on the application's existing metadata."""

from __future__ import annotations

from datetime import UTC, datetime

from models import db


class Occupation(db.Model):
    """A stable occupation scope available to questionnaire definitions."""

    __tablename__ = "occupations"

    id = db.Column(db.Integer, primary_key=True)
    occupation_code = db.Column(db.String(64), nullable=False, unique=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    category = db.Column(db.String(120), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    new_occupation_policy = db.Column(
        db.String(32), nullable=False, default="use_general"
    )
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class QuestionnaireDefinition(db.Model):
    """A questionnaire definition for one stable matching scope."""

    __tablename__ = "questionnaire_definitions"
    __table_args__ = (
        db.UniqueConstraint(
            "scope_key", name="uq_questionnaire_definitions_scope_key"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    definition_code = db.Column(db.String(96), nullable=False, unique=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    scope_type = db.Column(db.String(32), nullable=False)
    scope_key = db.Column(db.String(192), nullable=False)
    occupation_id = db.Column(
        db.Integer,
        db.ForeignKey("occupations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    user_type = db.Column(db.String(32), nullable=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    occupation = db.relationship("Occupation", foreign_keys=[occupation_id])
    created_by = db.relationship("User", foreign_keys=[created_by_user_id])
    versions = db.relationship(
        "QuestionnaireVersion",
        foreign_keys="QuestionnaireVersion.definition_id",
        back_populates="definition",
        order_by="QuestionnaireVersion.version_number",
    )


class QuestionnaireVersion(db.Model):
    """An immutable-in-use version belonging to a questionnaire definition."""

    __tablename__ = "questionnaire_versions"
    __table_args__ = (
        db.UniqueConstraint(
            "definition_id", "version_number", name="uq_questionnaire_versions_number"
        ),
        db.UniqueConstraint(
            "current_effective_scope_key",
            name="uq_questionnaire_versions_current_scope",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    definition_id = db.Column(
        db.Integer,
        db.ForeignKey("questionnaire_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(32), nullable=False, default="draft")
    current_effective_scope_key = db.Column(db.String(192), nullable=True)
    source_version_id = db.Column(
        db.Integer,
        db.ForeignKey("questionnaire_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    version_description = db.Column(db.Text, nullable=True)
    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    published_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    published_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    definition = db.relationship(
        "QuestionnaireDefinition",
        foreign_keys=[definition_id],
        back_populates="versions",
    )
    source_version = db.relationship(
        "QuestionnaireVersion",
        remote_side=[id],
        foreign_keys=[source_version_id],
    )
    created_by = db.relationship("User", foreign_keys=[created_by_user_id])
    published_by = db.relationship("User", foreign_keys=[published_by_user_id])
