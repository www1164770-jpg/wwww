"""Strict rule-first risk decisions that models cannot override."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from backend.crawler.analysis import AnalysisDocument, AnalysisOutcome


RISK_RULE_VERSION = "risk-rules-v1"
_HARD_RULES = {
    "hard_adult": ("pornography", "explicit adult", "色情", "成人视频"),
    "hard_gambling": ("gambling", "online casino", "betting", "赌博", "博彩"),
    "hard_drugs": ("illegal narcotics", "cocaine", "buy drugs", "毒品", "冰毒"),
    "hard_weapons": ("firearms", "weapons marketplace", "buy weapons", "枪支", "武器交易"),
    "hard_phishing": ("credential phishing", "steal password", "钓鱼登录", "盗取密码"),
    "hard_malware": ("malware", "ransomware", "恶意软件", "勒索软件"),
    "hard_piracy": ("pirated", "cracked software", "盗版下载", "破解软件"),
    "hard_extremism": ("violent extremist", "extremist propaganda", "暴力极端", "仇恨极端"),
}


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    status: str
    risk_score: float
    confidence: float
    hard_reject: bool
    rule_codes: tuple[str, ...]
    evidence_hashes: tuple[str, ...]
    rule_version: str


def assess_risk(
    document: AnalysisDocument,
    analysis: AnalysisOutcome,
    *,
    rule_version: str = RISK_RULE_VERSION,
) -> RiskAssessment:
    source = " ".join(
        item for item in (document.title, document.description, document.heading, document.text_excerpt) if item
    ).casefold()
    codes: list[str] = []
    evidence: list[str] = []
    for code, terms in _HARD_RULES.items():
        for term in terms:
            if term.casefold() in source:
                codes.append(code)
                evidence.append(sha256(f"{code}:{term.casefold()}".encode("utf-8")).hexdigest())
                break
    if codes:
        return RiskAssessment(
            status="rejected",
            risk_score=1.0,
            confidence=1.0,
            hard_reject=True,
            rule_codes=tuple(codes),
            evidence_hashes=tuple(evidence),
            rule_version=rule_version,
        )

    if (
        analysis.category_confidence < 0.75
        or analysis.quality_score < 0.55
        or (analysis.model_status == "model_unavailable" and analysis.category == "other")
    ):
        review_codes = ["low_analysis_confidence"]
        if analysis.quality_score < 0.55:
            review_codes.append("low_content_quality")
        if analysis.model_status == "model_unavailable" and analysis.category == "other":
            review_codes.append("model_unavailable")
        return RiskAssessment(
            status="review_required",
            risk_score=0.5,
            confidence=round(max(analysis.category_confidence, analysis.language_confidence), 4),
            hard_reject=False,
            rule_codes=tuple(review_codes),
            evidence_hashes=analysis.evidence_hashes,
            rule_version=rule_version,
        )
    return RiskAssessment(
        status="approved",
        risk_score=0.1,
        confidence=round(min(analysis.category_confidence, analysis.quality_score), 4),
        hard_reject=False,
        rule_codes=("no_hard_risk",),
        evidence_hashes=analysis.evidence_hashes,
        rule_version=rule_version,
    )
