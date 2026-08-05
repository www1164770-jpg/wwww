"""Rule-first Phase 3 analysis with a bounded optional model fallback."""

from .service import (
    ANALYSIS_RULE_VERSION,
    AnalysisDocument,
    AnalysisOutcome,
    ModelFailure,
    analyze_document,
    detect_language,
)

__all__ = [
    "ANALYSIS_RULE_VERSION",
    "AnalysisDocument",
    "AnalysisOutcome",
    "ModelFailure",
    "analyze_document",
    "detect_language",
]
