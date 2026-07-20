"""Constants shared by the versioned questionnaire foundation."""

NEW_OCCUPATION_POLICIES = frozenset({"use_general", "closed"})

QUESTIONNAIRE_SCOPE_TYPES = frozenset({
    "general",
    "occupation",
    "user_type",
    "occupation_user_type",
})

USER_TYPES = frozenset({"student", "employed", "organization"})

QUESTIONNAIRE_VERSION_STATUSES = frozenset({"draft", "published", "disabled", "archived"})

QUESTION_TYPES = frozenset({"single_choice", "multiple_choice", "short_text"})
