"""Idempotently import reviewable JSON website seeds into the navigation DB.

Files under ``backend/website_seed`` are the source of truth. The importer
matches normalized URLs before inserting, so reruns are safe and duplicates
are reported as updates instead of being counted as new resources.
"""

from __future__ import annotations

import json
import argparse
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
SEED_DIR = BACKEND_DIR / "website_seed"
REQUIRED_SITE_FIELDS = {
    "name", "url", "description", "category", "tags", "icon", "quality_score"
}

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db_pool import get_connection, validate_database_config  # noqa: E402


CATEGORY_META = {
    "common": ("常用推荐", "general", 0),
    "docs": ("框架文档", "frontend", 10),
    "ai": ("AI 神器", "general", 20),
    "inspiration": ("灵感采集", "designer", 30),
    "prototype": ("原型设计", "product", 40),
    "community": ("开发社区", "general", 50),
    "ui": ("UI 组件库", "frontend", 60),
    "assets": ("素材资源", "designer", 70),
    "office": ("文档办公", "product", 80),
    "learning": ("学习资源", "general", 90),
    "productivity": ("效率工具", "general", 100),
    "data": ("数据分析", "product", 110),
    "entertainment": ("摸鱼娱乐", "general", 120),
    "visualization_3d": ("可视化/3D", "frontend", 130),
    "build_tools": ("工具/构建", "frontend", 140),
    "online_tools": ("在线工具", "designer", 150),
    "fonts_colors": ("字体/配色", "designer", 160),
    "competitive_research": ("竞品调研", "product", 170),
}

LEGACY_SITE_GROUPS = {
    "entertainment": [("网易", "https://www.163.com")],
    "visualization_3d": [
        ("Three.js", "https://threejs.org"), ("D3.js", "https://d3js.org"),
        ("Babylon.js", "https://www.babylonjs.com"), ("deck.gl", "https://deck.gl"),
        ("Kepler.gl", "https://kepler.gl"), ("Cesium", "https://cesium.com"),
        ("Mapbox", "https://www.mapbox.com"), ("OpenLayers", "https://openlayers.org"),
        ("Leaflet", "https://leafletjs.com"), ("MapLibre", "https://maplibre.org"),
        ("Vega-Lite", "https://vega.github.io/vega-lite"), ("Apache ECharts", "https://echarts.apache.org"),
        ("Highcharts", "https://www.highcharts.com"), ("Chart.js", "https://www.chartjs.org"),
        ("Plotly.js", "https://plotly.com/javascript"), ("p5.js", "https://p5js.org"),
        ("PixiJS", "https://pixijs.com"), ("Babylon Playground", "https://playground.babylonjs.com"),
        ("Spline", "https://spline.design"), ("Rive", "https://rive.app"),
        ("MapTiler", "https://www.maptiler.com"), ("ArcGIS", "https://www.arcgis.com"),
        ("Esri", "https://www.esri.com"), ("FusionCharts", "https://www.fusioncharts.com"),
        ("amCharts", "https://www.amcharts.com"), ("AnyChart", "https://www.anychart.com"),
        ("ChartBlocks", "https://www.chartblocks.com"), ("RAWGraphs", "https://www.rawgraphs.io"),
        ("Infogram", "https://infogram.com"), ("Visme", "https://www.visme.co"),
        ("Flourish Visualization", "https://flourish.studio/visualisations"),
    ],
    "build_tools": [
        ("esbuild", "https://esbuild.github.io"), ("SWC", "https://swc.rs"),
        ("pnpm", "https://pnpm.io"), ("Yarn", "https://yarnpkg.com"),
        ("Babel", "https://babeljs.io"), ("Rome Tools", "https://rome.tools"),
        ("Biome", "https://biomejs.dev"), ("Prettier", "https://prettier.io"),
        ("ESLint", "https://eslint.org"), ("Stylelint", "https://stylelint.io"),
        ("Husky", "https://typicode.github.io/husky"), ("lint-staged", "https://github.com/lint-staged/lint-staged"),
        ("Changesets", "https://github.com/changesets/changesets"), ("Release Please", "https://github.com/googleapis/release-please"),
        ("Volta", "https://volta.sh"), ("nvm", "https://github.com/nvm-sh/nvm"),
        ("Corepack", "https://nodejs.org/api/corepack.html"), ("npm Docs", "https://docs.npmjs.com"),
        ("Gulp", "https://gulpjs.com"), ("Grunt", "https://gruntjs.com"),
        ("Lerna", "https://lerna.js.org"), ("Turborepo", "https://turbo.build"),
        ("Nx", "https://nx.dev"), ("Bazel", "https://bazel.build"),
        ("Buck2", "https://buck2.build"), ("Just", "https://just.systems"),
    ],
    "online_tools": [
        ("Postman", "https://www.postman.com"), ("Insomnia", "https://insomnia.rest"),
        ("Hoppscotch", "https://hoppscotch.io"), ("Regex101", "https://regex101.com"),
        ("JSON Formatter", "https://jsonformatter.org"), ("JSON Crack", "https://jsoncrack.com"),
        ("JWT.io", "https://jwt.io"), ("Base64 Guru", "https://base64.guru"),
        ("URL Encode Decode", "https://www.url-encode-decode.com"), ("Diffchecker", "https://www.diffchecker.com"),
        ("Carbon", "https://carbon.now.sh"), ("Bundlephobia", "https://bundlephobia.com"),
        ("npm Trends", "https://npmtrends.com"), ("Can I Use", "https://caniuse.com"),
        ("HTTP Status Dogs", "https://httpstatusdogs.com"), ("WebPageTest", "https://www.webpagetest.org"),
        ("PageSpeed Insights", "https://pagespeed.web.dev"), ("GTmetrix", "https://gtmetrix.com"),
        ("SVGOMG", "https://jakearchibald.github.io/svgomg"), ("Favicon Generator", "https://favicon.io"),
        ("XML Validation", "https://www.xmlvalidation.com"), ("HTML5 Editor", "https://www.html5editor.net"),
        ("Hastebin", "https://www.toptal.com/developers/hastebin"), ("Pastebin", "https://pastebin.com"),
    ],
    "fonts_colors": [
        ("Font Squirrel", "https://www.fontsquirrel.com"), ("FontPair", "https://fontpair.co"),
        ("Typewolf", "https://www.typewolf.com"), ("Fontjoy", "https://fontjoy.com"),
        ("Typograph", "https://typograph.app"), ("Fonts In Use", "https://fontsinuse.com"),
        ("Fontshare", "https://www.fontshare.com"), ("Adobe Fonts", "https://fonts.adobe.com"),
        ("Fontfabric", "https://www.fontfabric.com"), ("Lost Type", "https://www.losttype.com"),
        ("Colophon Foundry", "https://www.colophon-foundry.org"), ("Type.today", "https://type.today"),
        ("ColorSpace", "https://mycolor.space"), ("Colorable", "https://colorable.jxnblk.com"),
        ("Contrast Checker", "https://webaim.org/resources/contrastchecker"), ("Accessible Colors", "https://accessible-colors.com"),
        ("Paletton", "https://paletton.com"), ("ColorZilla", "https://www.colorzilla.com"),
        ("Gradient Hunt", "https://gradienthunt.com"), ("Mesh Gradients", "https://meshgradient.com"),
        ("Fontspring", "https://www.fontspring.com"), ("Fonts.com", "https://www.fonts.com"),
        ("Typekit", "https://typekit.com"), ("MyFonts", "https://www.myfonts.com"),
        ("FontSpace", "https://www.fontspace.com"), ("Abstract Fonts", "https://www.abstractfonts.com"),
    ],
    "competitive_research": [
        ("BuiltWith", "https://builtwith.com"), ("Wappalyzer", "https://www.wappalyzer.com"),
        ("Similarweb", "https://www.similarweb.com"), ("Semrush", "https://www.semrush.com"),
        ("Ahrefs", "https://ahrefs.com"), ("SpyFu", "https://www.spyfu.com"),
        ("G2", "https://www.g2.com"), ("Capterra", "https://www.capterra.com"),
        ("Product Hunt", "https://www.producthunt.com"), ("Crunchbase", "https://www.crunchbase.com"),
        ("Dealroom", "https://dealroom.co"), ("Tracxn", "https://tracxn.com"),
        ("Owler", "https://www.owler.com"), ("Exploding Topics", "https://explodingtopics.com"),
        ("Google Trends", "https://trends.google.com"), ("AnswerThePublic", "https://answerthepublic.com"),
        ("SparkToro", "https://sparktoro.com"), ("Social Blade", "https://socialblade.com"),
        ("Meta Ad Library", "https://www.facebook.com/ads/library"), ("TikTok Creative Center", "https://ads.tiktok.com/business/creativecenter"),
        ("SimilarTech", "https://www.similartech.com"),
        ("CB Insights", "https://www.cbinsights.com"), ("PitchBook", "https://pitchbook.com"),
        ("Consumer Barometer", "https://www.consumerbarometer.com"), ("Google Market Finder", "https://marketfinder.thinkwithgoogle.com"),
        ("SEMrush Traffic Analytics", "https://www.semrush.com/analytics/traffic"), ("Wappalyzer Lookup", "https://www.wappalyzer.com/lookup"),
        ("Similarweb Website", "https://www.similarweb.com/website"), ("BuiltWith Trends", "https://trends.builtwith.com"),
        ("ProductPlan", "https://www.productplan.com"), ("UserVoice", "https://www.uservoice.com"),
    ],
}

LEGACY_SITE_GROUPS["assets"] = [("Stockvault", "https://www.stockvault.net")]
LEGACY_SITE_GROUPS["prototype"] = [
    ("InVision Freehand", "https://www.invisionapp.com/freehand"),
    ("Mockup World", "https://www.mockupworld.co"),
    ("FlowMapp", "https://flowmapp.com"),
    ("Prototypr", "https://prototypr.io"),
]
LEGACY_SITE_GROUPS["learning"] = [("Educative", "https://www.educative.io")]
LEGACY_SITE_GROUPS["productivity"] = [
    ("Focuster", "https://www.focuster.com"), ("Due", "https://www.dueapp.com"),
    ("OmniFocus", "https://www.omnigroup.com/omnifocus"), ("Focus To-Do", "https://www.focustodo.cn"),
    ("Sunsama", "https://www.sunsama.com"), ("Akiflow", "https://akiflow.com"),
    ("Routine", "https://routine.co"), ("Amplenote", "https://www.amplenote.com"),
    ("SkedPal", "https://skedpal.com"), ("Timeular", "https://timeular.com"),
    ("Pumble", "https://pumble.com"), ("Quire", "https://quire.io"),
]


def legacy_sites() -> list[dict]:
    summaries = {
        "assets": "提供可用于设计和内容创作的图片素材。",
        "prototype": "提供产品原型、线框或交互协作能力。",
        "learning": "提供课程、编程练习或职业学习内容。",
        "productivity": "用于任务安排、时间管理或个人效率提升。",
        "entertainment": "提供新闻与综合内容资讯。",
        "visualization_3d": "提供可视化、地图或三维图形开发能力。",
        "build_tools": "提供前端构建、代码质量或依赖管理能力。",
        "online_tools": "提供开发调试、格式转换或性能检查工具。",
        "fonts_colors": "提供字体、色彩和无障碍视觉检查资源。",
        "competitive_research": "用于竞品信息、市场趋势或产品技术栈调研。",
    }
    return [
        {
            "name": name,
            "url": url,
            "category_code": code,
            # Keep the stored description independent from the card title.
            # The category fallback is only used when no site profile exists.
            "summary": summaries[code],
            "description": summaries[code],
            "logo_url": f"https://www.google.com/s2/favicons?domain={urlsplit(url).hostname}&sz=128",
        }
        for code, sites in LEGACY_SITE_GROUPS.items()
        for name, url in sites
    ]


def normalized_url(value: str) -> str:
    parsed = urlsplit(str(value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    hostname = parsed.hostname.lower().removeprefix("www.")
    path = parsed.path.rstrip("/") or "/"
    query = [
        item
        for item in parse_qsl(parsed.query, keep_blank_values=True)
        if item[0] != "zhihangyu_source"
    ]
    return urlunsplit((parsed.scheme.lower(), hostname, path, urlencode(query), ""))


def load_catalog() -> list[dict]:
    catalog: list[dict] = []
    seed_files = sorted(SEED_DIR.glob("*.json"))
    if not seed_files:
        raise RuntimeError(f"no website seed files found under {SEED_DIR}")
    for seed_file in seed_files:
        payload = json.loads(seed_file.read_text(encoding="utf-8"))
        sites = payload.get("sites") if isinstance(payload, dict) else payload
        if not isinstance(sites, list):
            raise RuntimeError(f"{seed_file.name}: sites must be an array")
        for index, site in enumerate(sites, start=1):
            if not isinstance(site, dict):
                raise RuntimeError(f"{seed_file.name}:{index}: site must be an object")
            missing = REQUIRED_SITE_FIELDS.difference(site)
            if missing:
                raise RuntimeError(
                    f"{seed_file.name}:{index}: missing {', '.join(sorted(missing))}"
                )
            if not isinstance(site["tags"], list) or not site["tags"]:
                raise RuntimeError(f"{seed_file.name}:{index}: tags must not be empty")
            score = float(site["quality_score"])
            if not 0 <= score <= 100:
                raise RuntimeError(f"{seed_file.name}:{index}: invalid quality_score")
            catalog.append(site)
    normalized = [normalized_url(site["url"]) for site in catalog]
    if any(not value for value in normalized):
        raise RuntimeError("seed contains an invalid HTTP(S) URL")
    if len(set(normalized)) != len(normalized):
        raise RuntimeError("seed contains duplicate normalized URLs")
    return catalog


def columns(cursor, table: str) -> set[str]:
    cursor.execute(f"SHOW COLUMNS FROM `{table}`")
    return {row["Field"] for row in cursor.fetchall()}


def value_columns(available: set[str], values: dict) -> tuple[str, ...]:
    return tuple(key for key in values if key in available)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    catalog = load_catalog()
    if args.validate_only:
        print(json.dumps({"catalog": len(catalog), "valid": True}, ensure_ascii=False))
        return 0
    validate_database_config()
    conn = get_connection()
    counts = {"inserted": 0, "updated": 0, "skipped": 0, "failed": 0}

    try:
        with conn.cursor() as cursor:
            category_columns = columns(cursor, "categories")
            website_columns = columns(cursor, "websites")
            tag_columns = columns(cursor, "tags")

            if "code" not in category_columns:
                try:
                    cursor.execute(
                        "ALTER TABLE categories ADD COLUMN code VARCHAR(80) NULL UNIQUE"
                    )
                    category_columns = columns(cursor, "categories")
                except Exception:
                    # Older deployments can still use the generated code in the API.
                    pass

            category_ids = {}
            for code, (name, profession, sort_order) in CATEGORY_META.items():
                cursor.execute("SELECT id FROM categories WHERE name=%s LIMIT 1", (name,))
                row = cursor.fetchone()
                if row:
                    category_ids[code] = row["id"]
                    if "code" in category_columns:
                        cursor.execute(
                            "UPDATE categories SET code=COALESCE(code,%s) WHERE id=%s",
                            (code, row["id"]),
                        )
                    continue

                values = {"name": name}
                if "code" in category_columns:
                    values["code"] = code
                if "profession_type" in category_columns:
                    values["profession_type"] = profession
                if "sort_order" in category_columns:
                    values["sort_order"] = sort_order
                fields = value_columns(category_columns, values)
                placeholders = ",".join(["%s"] * len(fields))
                cursor.execute(
                    f"INSERT INTO categories ({','.join(fields)}) VALUES ({placeholders})",
                    tuple(values[field] for field in fields),
                )
                category_ids[code] = cursor.lastrowid

            cursor.execute("SELECT id, url FROM websites")
            known_urls = {
                normalized_url(row["url"]): row["id"]
                for row in cursor.fetchall()
                if normalized_url(row["url"])
            }

            for site in catalog:
                code = str(site.get("category") or "").strip()
                if code not in category_ids:
                    counts["skipped"] += 1
                    continue
                url = str(site.get("url") or "").strip()
                normalized = normalized_url(url)
                name = str(site.get("name") or "").strip()
                summary = str(site.get("summary") or site.get("description") or "").strip()
                if not normalized or not name or not summary:
                    counts["failed"] += 1
                    continue

                existing_id = known_urls.get(normalized)
                if existing_id:
                    updates = {}
                    if "logo_url" in website_columns and site.get("icon"):
                        updates["logo_url"] = site["icon"]
                    if "summary" in website_columns:
                        updates["summary"] = summary
                    if "description" in website_columns:
                        updates["description"] = site.get("description") or summary
                    if "status" in website_columns:
                        updates["status"] = "approved"
                    if "quality_score" in website_columns:
                        updates["quality_score"] = float(site["quality_score"])
                    if updates:
                        assignments = ",".join(f"{field}=COALESCE(NULLIF({field},''),%s)" for field in updates)
                        cursor.execute(
                            f"UPDATE websites SET {assignments} WHERE id=%s",
                            (*updates.values(), existing_id),
                        )
                    counts["updated"] += 1
                    site_id = existing_id
                else:
                    values = {
                        "category_id": category_ids[code],
                        "name": name,
                        "url": url,
                        "logo_url": site.get("icon") or "",
                        "summary": summary,
                        "description": site.get("description") or summary,
                        "quality_score": float(site["quality_score"]),
                        "status": "approved",
                        "source": "website_seed",
                    }
                    fields = value_columns(website_columns, values)
                    placeholders = ",".join(["%s"] * len(fields))
                    cursor.execute(
                        f"INSERT INTO websites ({','.join(fields)}) VALUES ({placeholders})",
                        tuple(values[field] for field in fields),
                    )
                    cursor.execute("SELECT id FROM websites WHERE url=%s LIMIT 1", (url,))
                    created_site = cursor.fetchone()
                    if not created_site:
                        raise RuntimeError(f"website insert did not persist: {url}")
                    site_id = created_site["id"]
                    known_urls[normalized] = site_id
                    counts["inserted"] += 1

                if tag_columns:
                    for tag_name in dict.fromkeys(str(tag).strip() for tag in site["tags"]):
                        if not tag_name:
                            continue
                        cursor.execute("SELECT id FROM tags WHERE name=%s LIMIT 1", (tag_name,))
                        tag_row = cursor.fetchone()
                        if tag_row:
                            pass
                        else:
                            cursor.execute("INSERT INTO tags (name,type) VALUES (%s,%s)", (tag_name, "seed"))
                            cursor.execute("SELECT id FROM tags WHERE name=%s LIMIT 1", (tag_name,))
                            created_tag = cursor.fetchone()
                            if not created_tag:
                                raise RuntimeError(f"tag insert did not persist: {tag_name}")
                        cursor.execute(
                            """INSERT INTO site_tags (site_id,tag_id)
                               SELECT w.id,t.id FROM websites w JOIN tags t
                               WHERE w.id=%s AND t.name=%s
                                 AND NOT EXISTS (
                                   SELECT 1 FROM site_tags st
                                   WHERE st.site_id=w.id AND st.tag_id=t.id
                                 )""",
                            (site_id, tag_name),
                        )

                # The shared DBUtils pool recycles a physical connection after
                # maxusage statements. Keep each website as its own transaction
                # so a recycle can never discard hundreds of earlier inserts.
                conn.commit()

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(json.dumps({"catalog": len(catalog), **counts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
