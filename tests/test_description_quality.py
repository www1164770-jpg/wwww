from backend.description_quality import analyze_records, build_candidate, is_generic_description


GENERIC = "提供搜索、资讯、阅读或日常信息服务。"
TEMPLATE = "提供编程语言、框架或工程工具的官方文档。"


def test_reviewed_site_profile_is_high_confidence_candidate():
    candidate = build_candidate({"id": 1, "name": "飞猪旅行", "url": "https://fliggy.com", "description": ""})
    assert candidate["suggested_description"].startswith("阿里旗下在线旅行平台")
    assert candidate["confidence"] == "high"
    assert candidate["source"] == "manual_verified"


def test_name_prefixed_generic_description_is_detected_safely():
    candidate = build_candidate(
        {"id": 1, "name": "Reuters", "url": "https://reuters.com", "description": f"Reuters：{GENERIC}"}
    )
    assert candidate["reason"] == "reviewed_site_profile"
    assert candidate["confidence"] == "high"


def test_unknown_empty_description_needs_review_without_inventing_details():
    candidate = build_candidate({"id": 2, "name": "Unknown", "url": "https://unknown.example", "description": ""})
    assert candidate["suggested_description"] is None
    assert candidate["confidence"] == "needs_review"


def test_category_template_is_generic_even_when_prefixed_by_name():
    candidate = build_candidate({"id": 3, "name": "Astro", "description": f"Astro：{TEMPLATE}"})
    assert candidate["reason"] == "generic"
    assert candidate["confidence"] == "needs_review"
    assert is_generic_description(TEMPLATE)


def test_existing_usable_description_is_not_a_candidate():
    assert build_candidate({"name": "Existing", "description": "用于团队协作和项目文档管理。"}) is None


def test_report_includes_duplicate_groups_and_quality_counts():
    report = analyze_records([
        {"name": "A", "description": f"A：{TEMPLATE}"},
        {"name": "B", "description": f"B：{TEMPLATE}"},
        {"name": "C", "description": ""},
    ])
    assert report["total_websites"] == 3
    assert report["generic_descriptions"] == 2
    assert report["empty_descriptions"] == 1
    assert report["high_similarity_descriptions"] == 2
    assert report["duplicate_groups"][0]["count"] == 2
