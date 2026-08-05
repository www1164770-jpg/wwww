"""Deterministic extraction and schema-checked local-model fallback."""

from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import re
from typing import Any, Protocol

from .contract import sanitize_provider_response


ANALYSIS_RULE_VERSION = "analysis-rules-v1"
_SUMMARY_LIMIT = 160
_MODEL_EVIDENCE_LIMIT = 2400
_SPACE = re.compile(r"\s+")
_WORD = re.compile(r"[a-z0-9][a-z0-9+.#-]*", re.IGNORECASE)

_CATEGORY_TERMS = {
    "education": (
        "course", "courses", "learn", "learning", "university", "teacher",
        "study", "tutorial", "课程", "学习", "教育", "大学", "教学", "公开课",
    ),
    "development": (
        "developer", "development", "programming", "source code", "api", "github",
        "编程", "开发", "代码", "开源",
    ),
    "productivity": (
        "task", "tasks", "project management", "collaboration", "workspace",
        "calendar", "notes", "看板", "任务管理", "协作", "效率", "笔记",
    ),
    "design": ("design", "typography", "color palette", "ui", "ux", "设计", "字体", "配色"),
    "reference": ("reference", "documentation", "dictionary", "encyclopedia", "文档", "百科", "词典"),
    "news": ("news", "journalism", "headlines", "新闻", "资讯", "报道"),
    "community": ("community", "forum", "discussion", "社区", "论坛", "交流"),
}
_ALLOWED_CATEGORIES = frozenset((*_CATEGORY_TERMS, "other"))


class ModelFailure(RuntimeError):
    """Safe model failure classified without retaining response bodies."""

    def __init__(self, code: str) -> None:
        safe = str(code).strip().lower()
        if safe not in {"timeout", "invalid_json", "invalid_schema", "resource_exhausted", "unavailable"}:
            safe = "unavailable"
        self.code = safe
        super().__init__(safe)


class AnalysisModel(Protocol):
    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class AnalysisDocument:
    source_uid: str
    candidate_uid: str
    content_hash: str
    title: str | None
    description: str | None
    heading: str | None
    text_excerpt: str
    declared_language: str | None


@dataclass(frozen=True, slots=True)
class AnalysisOutcome:
    source_uid: str
    candidate_uid: str
    content_hash: str
    original_language: str | None
    detected_language: str
    language_confidence: float
    category: str
    category_confidence: float
    quality_score: float
    title_original: str | None
    summary_zh: str
    summary_method: str
    tags_zh: tuple[str, ...]
    rule_version: str
    model_name: str | None
    model_status: str
    model_error_code: str | None
    evidence_hashes: tuple[str, ...]
    provider_response_sanitized: dict[str, Any] | None = None

    def with_confidence(self, confidence: float) -> "AnalysisOutcome":
        return replace(self, category_confidence=max(0.0, min(float(confidence), 1.0)))

    def with_model_category(self, category: str, confidence: float) -> "AnalysisOutcome":
        return replace(
            self,
            category=category,
            category_confidence=max(0.0, min(float(confidence), 1.0)),
            model_status="used",
        )


def _clean(value: str | None, limit: int) -> str:
    return _SPACE.sub(" ", value or "").strip()[:limit]


def detect_language(text: str, declared: str | None = None) -> tuple[str, float]:
    declared_code = _clean(declared, 16).lower().split("-", 1)[0].split("_", 1)[0]
    supported = {"zh", "en", "ja", "ko", "ru"}
    if declared_code in supported:
        return declared_code, 0.96
    counts = {"zh": 0, "ja": 0, "ko": 0, "ru": 0, "en": 0}
    for character in text:
        code = ord(character)
        if 0x3040 <= code <= 0x30FF:
            counts["ja"] += 1
        elif 0x4E00 <= code <= 0x9FFF:
            counts["zh"] += 1
        elif 0xAC00 <= code <= 0xD7AF:
            counts["ko"] += 1
        elif 0x0400 <= code <= 0x04FF:
            counts["ru"] += 1
        elif character.isascii() and character.isalpha():
            counts["en"] += 1
    if counts["ja"]:
        counts["ja"] += counts["zh"]
        counts["zh"] = 0
    total = sum(counts.values())
    if total == 0:
        return "und", 0.0
    language, amount = max(counts.items(), key=lambda item: item[1])
    return language, round(max(0.6, amount / total), 4)


def _rule_category(text: str) -> tuple[str, float, tuple[str, ...]]:
    lowered = text.casefold()
    scored: list[tuple[int, str, tuple[str, ...]]] = []
    for category, terms in _CATEGORY_TERMS.items():
        matched = tuple(term for term in terms if term.casefold() in lowered)
        scored.append((len(matched), category, matched))
    count, category, matched = max(scored, key=lambda item: (item[0], item[1]))
    if count == 0:
        return "other", 0.35, ()
    confidence = min(0.95, 0.56 + count * 0.075)
    return category, round(confidence, 4), matched


def _quality(document: AnalysisDocument, language: str) -> float:
    score = 0.0
    if _clean(document.title, 500):
        score += 0.2
    description = _clean(document.description, 2000)
    if len(description) >= 30:
        score += 0.25
    elif description:
        score += 0.12
    if _clean(document.heading, 1000):
        score += 0.15
    excerpt = _clean(document.text_excerpt, 4000)
    if len(excerpt) >= 80:
        score += 0.3
    elif len(excerpt) >= 30:
        score += 0.2
    elif excerpt:
        score += 0.08
    if language != "und":
        score += 0.1
    return round(min(score, 1.0), 4)


def _bounded_summary(document: AnalysisDocument, language: str) -> str:
    title = _clean(document.title, 500)
    description = _clean(document.description, 2000)
    heading = _clean(document.heading, 1000)
    excerpt = _clean(document.text_excerpt, 4000)
    facts = [item for item in (title, description, heading, excerpt) if item]
    if not facts:
        return "公开网站，当前可用元数据不足。"
    if language == "zh":
        value = "。".join(dict.fromkeys(facts[:2]))
    else:
        labels = {"en": "英文", "ja": "日文", "ko": "韩文", "ru": "俄文"}
        value = f"{labels.get(language, '外文')}网站：" + ". ".join(dict.fromkeys(facts[:2]))
    bounded = value[:_SUMMARY_LIMIT].rstrip(" ,.;，；")
    if bounded.endswith(("。", ".")):
        return bounded
    return bounded[: _SUMMARY_LIMIT - 1].rstrip() + "。"


def _hashes(values) -> tuple[str, ...]:
    return tuple(dict.fromkeys(sha256(value.casefold().encode("utf-8")).hexdigest() for value in values if value))


def _model_payload(document: AnalysisDocument) -> dict[str, Any]:
    evidence = _clean(
        "\n".join(
            item
            for item in (document.title, document.description, document.heading, document.text_excerpt)
            if item
        ),
        _MODEL_EVIDENCE_LIMIT,
    )
    return {
        "schema_version": "phase3-analysis-v1",
        "source_uid": document.source_uid,
        "declared_language": _clean(document.declared_language, 16) or None,
        "evidence_text": evidence,
    }


def _validated_model_result(raw: Any, document: AnalysisDocument) -> tuple[str, float, str, tuple[str, ...], tuple[str, ...]]:
    if not isinstance(raw, dict):
        raise ModelFailure("invalid_json")
    category = raw.get("category")
    confidence = raw.get("confidence")
    summary = _clean(raw.get("summary_zh") if isinstance(raw.get("summary_zh"), str) else None, _SUMMARY_LIMIT)
    tags = raw.get("tags_zh")
    evidence = raw.get("evidence")
    if (
        category not in _ALLOWED_CATEGORIES
        or isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not 0 <= float(confidence) <= 1
        or not summary
        or not isinstance(tags, list)
        or not 1 <= len(tags) <= 8
        or not all(isinstance(item, str) and 0 < len(_clean(item, 32)) <= 32 for item in tags)
        or not isinstance(evidence, list)
        or not evidence
        or not all(isinstance(item, str) and _clean(item, 300) for item in evidence)
    ):
        raise ModelFailure("invalid_schema")
    source = _model_payload(document)["evidence_text"].casefold()
    cleaned_evidence = tuple(_clean(item, 300) for item in evidence)
    if not all(item.casefold() in source for item in cleaned_evidence):
        raise ModelFailure("invalid_schema")
    return (
        category,
        round(float(confidence), 4),
        summary,
        tuple(dict.fromkeys(_clean(item, 32) for item in tags)),
        _hashes(cleaned_evidence),
    )


def analyze_document(
    document: AnalysisDocument,
    *,
    model: AnalysisModel | None = None,
    confidence_threshold: float = 0.85,
    rule_version: str = ANALYSIS_RULE_VERSION,
    model_name: str | None = None,
) -> AnalysisOutcome:
    text = _clean(
        " ".join(item for item in (document.title, document.description, document.heading, document.text_excerpt) if item),
        8000,
    )
    language, language_confidence = detect_language(text, document.declared_language)
    category, confidence, matched = _rule_category(text)
    quality = _quality(document, language)
    summary = _bounded_summary(document, language)
    tags = (category,) if category != "other" else ()
    evidence_hashes = _hashes(matched)
    model_status = "not_needed"
    model_error_code = None
    provider_response_sanitized = None
    summary_method = "rules"

    needs_model = confidence < confidence_threshold or quality < 0.55
    if needs_model:
        if model is None:
            model_status = "model_unavailable"
            model_error_code = "unavailable"
            summary_method = "rules_fallback"
        else:
            try:
                raw_model_response = model.analyze(_model_payload(document))
                provider_response_sanitized = sanitize_provider_response(raw_model_response)
                category, confidence, summary, tags, model_hashes = _validated_model_result(raw_model_response, document)
                evidence_hashes = tuple(dict.fromkeys((*evidence_hashes, *model_hashes)))
                model_status = "used"
                summary_method = "model"
            except ModelFailure as error:
                model_status = "model_unavailable"
                model_error_code = error.code
                summary_method = "rules_fallback"
            except TimeoutError:
                model_status = "model_unavailable"
                model_error_code = "timeout"
                summary_method = "rules_fallback"

    return AnalysisOutcome(
        source_uid=document.source_uid,
        candidate_uid=document.candidate_uid,
        content_hash=document.content_hash,
        original_language=document.declared_language,
        detected_language=language,
        language_confidence=language_confidence,
        category=category,
        category_confidence=confidence,
        quality_score=quality,
        title_original=_clean(document.title, 500) or None,
        summary_zh=summary,
        summary_method=summary_method,
        tags_zh=tags,
        rule_version=rule_version,
        model_name=model_name,
        model_status=model_status,
        model_error_code=model_error_code,
        evidence_hashes=evidence_hashes,
        provider_response_sanitized=provider_response_sanitized if isinstance(provider_response_sanitized, dict) else None,
    )
