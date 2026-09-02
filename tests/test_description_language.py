from backend.description_language import description_language, unsupported_languages


def test_chinese_with_technical_terms_is_supported():
    assert description_language("支持 Markdown 编辑和 PDF 导出。") == "zh_en"


def test_japanese_is_unsupported():
    assert description_language("Google スプレッドシート") == "unsupported"
    assert unsupported_languages("Google スプレッドシート") == ("japanese",)


def test_korean_and_cyrillic_are_unsupported():
    assert "korean" in unsupported_languages("한국어 설명")
    assert "russian" in unsupported_languages("Русское описание")
