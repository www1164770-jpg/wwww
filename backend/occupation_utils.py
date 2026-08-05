"""Shared occupation protocol for backend API and recommendation queries."""

OCCUPATION_LABELS = {
    "frontend_developer": "前端开发",
    "backend_developer": "后端开发",
    "ai_app_developer": "AI 应用开发",
    "llm_engineer": "大模型工程师",
    "product_manager": "产品经理",
    "ui_ux_designer": "UI/UX 设计师",
    "data_analyst": "数据分析师",
    "operations": "运营",
    "technical_operations": "技术运营",
    "student": "学生",
    "teacher": "教师",
    "creator": "自媒体创作者",
    "other": "其他",
}

OCCUPATION_ALIASES = {
    "programmer": "frontend_developer",
    "frontend": "frontend_developer",
    "程序员": "frontend_developer",
    "backend": "backend_developer",
    "ai_application_developer": "ai_app_developer",
    "large_language_model_engineer": "llm_engineer",
    "product": "product_manager",
    "designer": "ui_ux_designer",
    "uiux": "ui_ux_designer",
    "ui_ux": "ui_ux_designer",
    "设计师": "ui_ux_designer",
    "data": "data_analyst",
    "marketing": "operations",
    "ecommerce": "operations",
    "tech_operations": "technical_operations",
    "content_creator": "creator",
    "self_media_creator": "creator",
    "内容创作者": "creator",
}

_OCCUPATION_LOOKUP = {
    code.casefold(): code for code in OCCUPATION_LABELS
}
_OCCUPATION_LOOKUP.update(
    {label.casefold(): code for code, label in OCCUPATION_LABELS.items()}
)
_OCCUPATION_LOOKUP.update(
    {alias.casefold(): code for alias, code in OCCUPATION_ALIASES.items()}
)


def normalize_occupation(value):
    """Return a canonical occupation code, or None for missing/unknown values."""
    key = str(value or "").strip().casefold()
    return _OCCUPATION_LOOKUP.get(key) if key else None


def get_occupation_label(value):
    """Return the existing Chinese query label for a recognized occupation."""
    canonical = normalize_occupation(value)
    return OCCUPATION_LABELS.get(canonical)

