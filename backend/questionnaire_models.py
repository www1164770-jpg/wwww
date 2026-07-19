"""Questionnaire ORM models registered on the application's existing metadata."""

from __future__ import annotations

from datetime import UTC, datetime

from models import db


class Occupation(db.Model):
    """A stable occupation scope available to questionnaire definitions."""

    __tablename__ = "occupations"

    id = db.Column(db.Integer, primary_key=True)
    occupation_code = db.Column(db.String(96), nullable=False, unique=True)
    name = db.Column(db.String(160), nullable=False, unique=True)
    category = db.Column(db.String(96), nullable=False)
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
