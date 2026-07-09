import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recommend_service import rank_sites


SITES = [
    {
        "id": 1,
        "name": "Designer Lab",
        "url": "https://design.example.com",
        "summary": "UI assets and prototype resources",
        "tags": ["design", "ui", "prototype"],
        "occupations": ["designer"],
        "quality_score": 90,
        "click_count": 50,
        "favorite_count": 10,
        "rating_avg": 4.8,
        "created_at": datetime.now(timezone.utc),
    },
    {
        "id": 2,
        "name": "Python Docs",
        "url": "https://python.example.com",
        "summary": "Developer documentation and code examples",
        "tags": ["code", "developer", "docs"],
        "occupations": ["programmer"],
        "quality_score": 80,
        "click_count": 40,
        "favorite_count": 8,
        "rating_avg": 4.5,
        "created_at": datetime.now(timezone.utc),
    },
    {
        "id": 3,
        "name": "王者荣耀攻略",
        "url": "https://game.example.com",
        "summary": "游戏攻略",
        "tags": ["game"],
        "occupations": [],
        "quality_score": 100,
        "click_count": 9999,
        "favorite_count": 500,
        "rating_avg": 5,
        "created_at": datetime.now(timezone.utc),
    },
]


def main():
    rules = {
        "occupation_site_weights": {
            "programmer": ["code", "developer", "docs"],
            "designer": ["design", "ui", "prototype"],
        },
        "weights": {
            "occupation_score": 0.55,
            "interest_score": 0.2,
            "quality_score": 0.1,
            "popularity_score": 0.05,
            "freshness_score": 0.05,
            "behavior_score": 0.05,
        },
        "blacklist": ["王者荣耀"],
        "reason_templates": {
            "programmer": "适合前端开发、代码学习和项目构建",
            "designer": "适合 UI 设计、素材查找和创意生成",
            "default": "根据职业、兴趣和资源质量综合推荐",
        },
    }

    programmer = rank_sites(
        SITES,
        {"occupation": "programmer", "interests": []},
        limit=3,
        rules=rules,
    )
    designer = rank_sites(
        SITES,
        {"occupation": "designer", "interests": []},
        limit=3,
        rules=rules,
    )

    assert programmer[0]["name"] == "Python Docs", programmer
    assert designer[0]["name"] == "Designer Lab", designer
    assert all("王者荣耀" not in item["name"] for item in programmer), programmer
    assert programmer[0]["reason"] == rules["reason_templates"]["programmer"]
    assert designer[0]["reason"] == rules["reason_templates"]["designer"]


if __name__ == "__main__":
    main()
