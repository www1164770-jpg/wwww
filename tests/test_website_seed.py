import json
from pathlib import Path
from urllib.parse import urlsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEED_DIR = PROJECT_ROOT / "backend" / "website_seed"
REQUIRED_FIELDS = {
    "name", "url", "description", "category", "tags", "icon", "quality_score"
}


def load_sites():
    sites = []
    for path in sorted(SEED_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        sites.extend(payload["sites"] if isinstance(payload, dict) else payload)
    return sites


def test_phase_one_seed_has_at_least_500_complete_unique_sites():
    sites = load_sites()
    assert len(sites) >= 500
    normalized_urls = set()
    descriptions = set()
    for site in sites:
        assert REQUIRED_FIELDS <= site.keys()
        assert isinstance(site["tags"], list) and site["tags"]
        assert 0 <= float(site["quality_score"]) <= 100
        parsed = urlsplit(site["url"])
        assert parsed.scheme in {"http", "https"} and parsed.hostname
        normalized = (
            parsed.hostname.lower().removeprefix("www."),
            parsed.path.rstrip("/") or "/",
        )
        assert normalized not in normalized_urls
        normalized_urls.add(normalized)
        assert site["description"] not in descriptions
        descriptions.add(site["description"])


def test_phase_one_seed_covers_priority_directions():
    sites = load_sites()
    tags = {tag for site in sites for tag in site["tags"]}
    for required in {
        "AI工具", "AI开发", "在线IDE", "API工具", "数据库",
        "UI设计", "设计灵感", "编程学习", "AI学习", "知识管理",
        "项目管理", "团队协作",
    }:
        assert required in tags
