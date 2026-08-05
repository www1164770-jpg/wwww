"""Validated mapping from crawler review choices to the known Website model."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import unicodedata
from typing import Callable

from backend.crawler.db import IconAsset, ReviewCase
from backend.crawler.net.url import InvalidUrl, normalize_http_url


class MappingValidationError(ValueError):
    pass


def _text(value: object, *, field: str, maximum: int, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise MappingValidationError(f"{field} is required")
        return None
    result = unicodedata.normalize("NFC", str(value)).strip()
    if required and not result:
        raise MappingValidationError(f"{field} is required")
    if len(result) > maximum:
        raise MappingValidationError(f"{field} exceeds its target length")
    if any(unicodedata.category(char).startswith("C") for char in result):
        raise MappingValidationError(f"{field} contains a control character")
    return result or None


@dataclass(frozen=True, slots=True)
class WebsiteFields:
    """Fields verified against ``backend.models.Website``; no inferred columns."""
    name: str
    url: str
    logo_url: str | None
    summary: str | None
    description: str | None
    category_id: int
    region: str | None

    def snapshot(self) -> dict[str, object]:
        return asdict(self)


def build_website_fields(case: ReviewCase, *, category_resolver: Callable[[str], int | None], logo_url_builder: Callable[[IconAsset], str] | None = None, logo_asset: IconAsset | None = None) -> WebsiteFields:
    title = _text(case.selected_title, field="selected_title", maximum=100, required=True)
    summary = _text(case.selected_summary, field="selected_summary", maximum=500)
    description = _text(case.selected_description, field="selected_description", maximum=65_535)
    category = _text(case.selected_category, field="selected_category", maximum=64, required=True)
    region = _text(case.selected_region, field="selected_region", maximum=32)
    raw_url = _text(case.selected_url, field="selected_url", maximum=4096, required=True)
    try:
        url = normalize_http_url(raw_url).url
    except InvalidUrl as error:
        raise MappingValidationError("selected_url is not a valid HTTP(S) URL") from error
    category_id = category_resolver(category)
    if not isinstance(category_id, int) or category_id < 1:
        raise MappingValidationError("selected_category does not resolve to an existing category")
    logo_url = None
    if case.selected_logo_asset_id is not None:
        if logo_asset is None or logo_asset.id != case.selected_logo_asset_id:
            raise MappingValidationError("selected logo asset is unavailable")
        if logo_asset.fetch_result_id != case.fetch_result_id:
            raise MappingValidationError("selected logo asset does not belong to this review source")
        logo_url = (logo_url_builder or (lambda asset: asset.relative_path))(logo_asset)
        logo_url = _text(logo_url, field="logo_url", maximum=500)
    return WebsiteFields(title, url, logo_url, summary, description, category_id, region)

