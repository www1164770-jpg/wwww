import os
import sys


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from db_pool import get_connection


CATEGORIES = ["AI工具", "编程开发", "设计资源", "学习成长", "效率办公", "数据分析", "产品运营", "原型设计"]
TAGS = ["AI", "AIGC", "编程", "设计", "文档", "效率", "学习", "写作", "绘图", "办公", "数据"]
OCCUPATIONS = [
    "学生",
    "前端开发",
    "后端开发",
    "产品经理",
    "UI/UX 设计师",
    "运营",
    "教师",
    "自媒体创作者",
    "数据分析师",
]

SITE_OCCUPATIONS = {
    "ChatGPT": ["学生", "前端开发", "后端开发", "产品经理", "运营", "教师", "自媒体创作者", "数据分析师"],
    "Claude": ["学生", "前端开发", "后端开发", "产品经理", "运营", "教师", "自媒体创作者", "数据分析师"],
    "Gemini": ["学生", "产品经理", "运营", "教师", "自媒体创作者", "数据分析师"],
    "Perplexity": ["学生", "产品经理", "教师", "数据分析师"],
    "Poe": ["学生", "前端开发", "后端开发", "运营", "自媒体创作者"],
    "Kimi": ["学生", "产品经理", "运营", "教师", "数据分析师"],
    "通义千问": ["学生", "前端开发", "后端开发", "运营", "教师", "自媒体创作者"],
    "文心一言": ["学生", "产品经理", "运营", "教师", "自媒体创作者"],
    "豆包": ["学生", "运营", "教师", "自媒体创作者"],
    "Midjourney": ["UI/UX 设计师", "运营", "自媒体创作者"],
    "Runway": ["UI/UX 设计师", "运营", "自媒体创作者"],
    "Stable Diffusion": ["UI/UX 设计师", "运营", "自媒体创作者"],
    "GitHub": ["前端开发", "后端开发", "数据分析师"],
    "MDN Web Docs": ["学生", "前端开发"],
    "Vue 官方文档": ["学生", "前端开发"],
    "Flask 官方文档": ["学生", "后端开发"],
    "LeetCode": ["学生", "前端开发", "后端开发", "数据分析师"],
    "Figma": ["产品经理", "UI/UX 设计师"],
    "Canva": ["学生", "产品经理", "UI/UX 设计师", "运营", "教师", "自媒体创作者"],
    "Iconfont": ["前端开发", "UI/UX 设计师"],
    "Unsplash": ["UI/UX 设计师", "运营", "教师", "自媒体创作者"],
    "Notion": ["学生", "产品经理", "运营", "教师", "自媒体创作者", "数据分析师"],
    "飞书": ["产品经理", "运营", "教师", "数据分析师"],
    "ProcessOn": ["学生", "产品经理", "教师", "数据分析师"],
    "Stack Overflow": ["前端开发", "后端开发"],
    "Dribbble": ["UI/UX 设计师", "自媒体创作者"],
    "Trello": ["产品经理", "运营"],
    "Bilibili 学习区": ["学生", "教师", "自媒体创作者"],
    "Coursera": ["学生", "教师", "数据分析师"],
    "Khan Academy": ["学生", "教师"],
    "中国大学 MOOC": ["学生", "教师"],
    "Kaggle": ["数据分析师", "学生"],
    "Tableau": ["数据分析师", "产品经理"],
    "Power BI": ["数据分析师", "产品经理"],
    "Jupyter": ["数据分析师", "后端开发"],
    "SQL 教程": ["数据分析师", "后端开发"],
}

SITES = [
    {
        "name": "ChatGPT",
        "url": "https://chatgpt.com",
        "logo_url": "https://chatgpt.com/favicon.ico",
        "summary": "OpenAI 的 AI 对话与效率工具。",
        "description": "适合问答、写作、编程、学习和办公自动化。",
        "category": "AI工具",
        "tags": ["AI", "效率", "学习"],
        "quality_score": 98,
        "recommend_level": 5,
        "click_count": 980,
    },
    {
        "name": "Claude",
        "url": "https://claude.ai",
        "logo_url": "https://claude.ai/favicon.ico",
        "summary": "Anthropic 的 AI 助手。",
        "description": "适合长文档处理、编程辅助和知识工作。",
        "category": "AI工具",
        "tags": ["AI", "效率"],
        "quality_score": 96,
        "recommend_level": 5,
        "click_count": 920,
    },
    {
        "name": "Gemini",
        "url": "https://gemini.google.com",
        "logo_url": "https://www.gstatic.com/lamda/images/gemini_sparkle_aurora_33f86dc0c0257da337c63.svg",
        "summary": "Google 的 AI 助手与多模态智能工具。",
        "description": "适合搜索整理、写作、学习和创意生成。",
        "category": "AI工具",
        "tags": ["AI", "AIGC", "效率"],
        "quality_score": 95,
        "recommend_level": 5,
        "click_count": 900,
    },
    {
        "name": "Perplexity",
        "url": "https://www.perplexity.ai",
        "logo_url": "https://www.perplexity.ai/favicon.ico",
        "summary": "面向资料检索和问答的 AI 搜索工具。",
        "description": "适合学习、研究、资料引用和快速理解复杂主题。",
        "category": "AI工具",
        "tags": ["AI", "学习", "效率"],
        "quality_score": 94,
        "recommend_level": 5,
        "click_count": 860,
    },
    {
        "name": "Poe",
        "url": "https://poe.com",
        "logo_url": "https://poe.com/favicon.ico",
        "summary": "聚合多种 AI 模型的对话平台。",
        "description": "适合体验不同 AI 助手、写作、编程和学习场景。",
        "category": "AI工具",
        "tags": ["AI", "AIGC", "写作"],
        "quality_score": 91,
        "recommend_level": 4,
        "click_count": 720,
    },
    {
        "name": "Midjourney",
        "url": "https://www.midjourney.com",
        "logo_url": "https://www.midjourney.com/favicon.ico",
        "summary": "AI 绘图与视觉创作工具。",
        "description": "适合生成式图像创作、灵感探索和设计参考。",
        "category": "AI工具",
        "tags": ["AI", "AIGC", "绘图", "设计"],
        "quality_score": 93,
        "recommend_level": 5,
        "click_count": 840,
    },
    {
        "name": "Runway",
        "url": "https://runwayml.com",
        "logo_url": "https://runwayml.com/favicon.ico",
        "summary": "AI 视频生成与创意制作平台。",
        "description": "适合生成式视频、视觉实验和内容创作工作流。",
        "category": "AI工具",
        "tags": ["AI", "AIGC", "设计"],
        "quality_score": 92,
        "recommend_level": 4,
        "click_count": 690,
    },
    {
        "name": "Stable Diffusion",
        "url": "https://stability.ai",
        "logo_url": "https://stability.ai/favicon.ico",
        "summary": "开源生态活跃的 AI 图像生成模型与工具。",
        "description": "适合生成式图片、视觉探索、设计参考和创意内容制作。",
        "category": "AI工具",
        "tags": ["AI", "AIGC", "绘图", "设计"],
        "quality_score": 92,
        "recommend_level": 4,
        "click_count": 700,
    },
    {
        "name": "Kimi",
        "url": "https://kimi.moonshot.cn",
        "logo_url": "https://kimi.moonshot.cn/favicon.ico",
        "summary": "长文本阅读和资料整理 AI 助手。",
        "description": "适合文档理解、写作、学习和办公效率场景。",
        "category": "AI工具",
        "tags": ["AI", "文档", "效率"],
        "quality_score": 92,
        "recommend_level": 5,
        "click_count": 790,
    },
    {
        "name": "通义千问",
        "url": "https://tongyi.aliyun.com",
        "logo_url": "https://img.alicdn.com/imgextra/i2/O1CN01asLYVg1WhbsyEZn5u_!!6000000002818-2-tps-64-64.png",
        "summary": "阿里云推出的 AI 智能助手。",
        "description": "适合问答、写作、办公、编程和多模态生成。",
        "category": "AI工具",
        "tags": ["AI", "写作", "办公"],
        "quality_score": 90,
        "recommend_level": 4,
        "click_count": 670,
    },
    {
        "name": "文心一言",
        "url": "https://yiyan.baidu.com",
        "logo_url": "https://nlp-eb.cdn.bcebos.com/logo/favicon.ico",
        "summary": "百度推出的生成式 AI 助手。",
        "description": "适合智能问答、写作、办公和知识整理。",
        "category": "AI工具",
        "tags": ["AI", "写作", "效率"],
        "quality_score": 89,
        "recommend_level": 4,
        "click_count": 640,
    },
    {
        "name": "豆包",
        "url": "https://www.doubao.com",
        "logo_url": "https://www.doubao.com/favicon.ico",
        "summary": "字节跳动推出的 AI 智能助手。",
        "description": "适合日常问答、写作、学习和办公提效。",
        "category": "AI工具",
        "tags": ["AI", "写作", "学习"],
        "quality_score": 90,
        "recommend_level": 4,
        "click_count": 660,
    },
    {
        "name": "GitHub",
        "url": "https://github.com",
        "logo_url": "https://github.githubassets.com/favicons/favicon.svg",
        "summary": "代码托管与协作开发平台。",
        "description": "适合开源项目、团队协作和工程实践。",
        "category": "编程开发",
        "tags": ["编程"],
        "quality_score": 97,
        "recommend_level": 5,
        "click_count": 880,
    },
    {
        "name": "MDN Web Docs",
        "url": "https://developer.mozilla.org",
        "logo_url": "https://developer.mozilla.org/favicon-48x48.png",
        "summary": "权威 Web 开发文档。",
        "description": "覆盖 HTML、CSS、JavaScript 和 Web API。",
        "category": "编程开发",
        "tags": ["编程", "文档", "学习"],
        "quality_score": 95,
        "recommend_level": 5,
        "click_count": 820,
    },
    {
        "name": "Vue 官方文档",
        "url": "https://cn.vuejs.org",
        "logo_url": "https://cn.vuejs.org/logo.svg",
        "summary": "Vue.js 官方中文文档。",
        "description": "适合学习 Vue 3、组合式 API 和前端工程实践。",
        "category": "编程开发",
        "tags": ["编程", "文档", "学习"],
        "quality_score": 94,
        "recommend_level": 5,
        "click_count": 760,
    },
    {
        "name": "Flask 官方文档",
        "url": "https://flask.palletsprojects.com",
        "logo_url": "https://flask.palletsprojects.com/en/stable/_static/flask-vertical.png",
        "summary": "Flask Web 框架官方文档。",
        "description": "适合学习 Python Web 服务开发。",
        "category": "编程开发",
        "tags": ["编程", "文档", "学习"],
        "quality_score": 92,
        "recommend_level": 4,
        "click_count": 700,
    },
    {
        "name": "LeetCode",
        "url": "https://leetcode.cn",
        "logo_url": "https://leetcode.cn/favicon.ico",
        "summary": "算法练习和面试准备平台。",
        "description": "适合程序员刷题、提升算法能力。",
        "category": "学习成长",
        "tags": ["编程", "学习"],
        "quality_score": 91,
        "recommend_level": 4,
        "click_count": 680,
    },
    {
        "name": "Figma",
        "url": "https://www.figma.com",
        "logo_url": "https://static.figma.com/app/icon/1/favicon.png",
        "summary": "在线协作设计工具。",
        "description": "适合 UI 设计、产品原型和团队协作。",
        "category": "设计资源",
        "tags": ["设计", "效率"],
        "quality_score": 93,
        "recommend_level": 5,
        "click_count": 650,
    },
    {
        "name": "Iconfont",
        "url": "https://www.iconfont.cn",
        "logo_url": "https://img.alicdn.com/imgextra/i4/O1CN01mEefzq1JPC6wCbXqY_!!6000000001017-2-tps-114-114.png",
        "summary": "阿里巴巴矢量图标库。",
        "description": "适合查找图标、管理项目图标资源。",
        "category": "设计资源",
        "tags": ["设计"],
        "quality_score": 88,
        "recommend_level": 4,
        "click_count": 560,
    },
    {
        "name": "Canva",
        "url": "https://www.canva.com",
        "logo_url": "https://www.canva.com/favicon.ico",
        "summary": "在线设计与内容创作工具。",
        "description": "适合海报、演示文稿、社交媒体图片和团队设计协作。",
        "category": "设计资源",
        "tags": ["设计", "效率"],
        "quality_score": 91,
        "recommend_level": 4,
        "click_count": 590,
    },
    {
        "name": "Unsplash",
        "url": "https://unsplash.com",
        "logo_url": "https://unsplash.com/favicon.ico",
        "summary": "高质量免费图片素材站。",
        "description": "适合设计、内容创作和灵感搜索。",
        "category": "设计资源",
        "tags": ["设计"],
        "quality_score": 90,
        "recommend_level": 4,
        "click_count": 520,
    },
    {
        "name": "Notion",
        "url": "https://www.notion.so",
        "logo_url": "https://www.notion.so/front-static/favicon.ico",
        "summary": "笔记、知识库和项目管理工具。",
        "description": "适合个人知识管理和团队协作。",
        "category": "效率办公",
        "tags": ["效率", "学习"],
        "quality_score": 91,
        "recommend_level": 4,
        "click_count": 610,
    },
    {
        "name": "飞书",
        "url": "https://www.feishu.cn",
        "logo_url": "https://www.feishu.cn/favicon.ico",
        "summary": "团队协作、文档和项目沟通平台。",
        "description": "适合知识管理、办公协作、文档沉淀和团队效率提升。",
        "category": "效率办公",
        "tags": ["效率", "办公", "文档"],
        "quality_score": 89,
        "recommend_level": 4,
        "click_count": 570,
    },
    {
        "name": "ProcessOn",
        "url": "https://www.processon.com",
        "logo_url": "https://www.processon.com/favicon.ico",
        "summary": "在线流程图和思维导图工具。",
        "description": "适合流程梳理、结构化表达和协作画图。",
        "category": "效率办公",
        "tags": ["效率", "设计"],
        "quality_score": 87,
        "recommend_level": 4,
        "click_count": 480,
    },
    {
        "name": "Stack Overflow",
        "url": "https://stackoverflow.com",
        "logo_url": "https://stackoverflow.com/favicon.ico",
        "summary": "全球开发者问答社区。",
        "description": "适合查询编程问题、框架用法、工程实践和错误排查方案。",
        "category": "编程开发",
        "tags": ["编程", "学习"],
        "quality_score": 94,
        "recommend_level": 5,
        "click_count": 760,
    },
    {
        "name": "Dribbble",
        "url": "https://dribbble.com",
        "logo_url": "https://cdn.dribbble.com/assets/favicon-452601a223b2b01b396e7e33c7bb8820f27f3f5bdf3a21c1cf7ad2472bf66df6.ico",
        "summary": "设计师作品展示与灵感社区。",
        "description": "适合查找 UI、插画、品牌视觉和产品界面灵感。",
        "category": "设计资源",
        "tags": ["设计"],
        "quality_score": 90,
        "recommend_level": 4,
        "click_count": 540,
    },
    {
        "name": "Trello",
        "url": "https://trello.com",
        "logo_url": "https://trello.com/favicon.ico",
        "summary": "轻量看板式项目管理工具。",
        "description": "适合任务拆分、项目协作、内容排期和团队进度跟踪。",
        "category": "效率办公",
        "tags": ["效率", "办公"],
        "quality_score": 88,
        "recommend_level": 4,
        "click_count": 520,
    },
    {
        "name": "Bilibili 学习区",
        "url": "https://www.bilibili.com/v/knowledge",
        "logo_url": "https://www.bilibili.com/favicon.ico",
        "summary": "覆盖课程、技能和知识内容的视频学习区。",
        "description": "适合查找中文学习视频、公开课、技能教程和考试资料。",
        "category": "学习成长",
        "tags": ["学习"],
        "quality_score": 86,
        "recommend_level": 4,
        "click_count": 700,
    },
    {
        "name": "Coursera",
        "url": "https://www.coursera.org",
        "logo_url": "https://www.coursera.org/favicon.ico",
        "summary": "国际在线课程与职业证书平台。",
        "description": "适合系统学习计算机、数据分析、商业和通识课程。",
        "category": "学习成长",
        "tags": ["学习"],
        "quality_score": 92,
        "recommend_level": 5,
        "click_count": 620,
    },
    {
        "name": "Khan Academy",
        "url": "https://www.khanacademy.org",
        "logo_url": "https://www.khanacademy.org/favicon.ico",
        "summary": "免费的基础学科与通识学习平台。",
        "description": "适合数学、科学、经济和基础能力的系统学习。",
        "category": "学习成长",
        "tags": ["学习"],
        "quality_score": 91,
        "recommend_level": 4,
        "click_count": 560,
    },
    {
        "name": "中国大学 MOOC",
        "url": "https://www.icourse163.org",
        "logo_url": "https://www.icourse163.org/favicon.ico",
        "summary": "中文高校在线开放课程平台。",
        "description": "适合学习高校课程、专业基础课和职业能力课程。",
        "category": "学习成长",
        "tags": ["学习"],
        "quality_score": 89,
        "recommend_level": 4,
        "click_count": 540,
    },
    {
        "name": "Kaggle",
        "url": "https://www.kaggle.com",
        "logo_url": "https://www.kaggle.com/favicon.ico",
        "summary": "数据科学竞赛、数据集和 Notebook 平台。",
        "description": "适合数据分析练习、机器学习项目、公开数据集和案例学习。",
        "category": "数据分析",
        "tags": ["数据", "学习"],
        "quality_score": 94,
        "recommend_level": 5,
        "click_count": 720,
    },
    {
        "name": "Tableau",
        "url": "https://www.tableau.com",
        "logo_url": "https://www.tableau.com/themes/custom/tableau_www/favicon.ico",
        "summary": "商业智能与数据可视化平台。",
        "description": "适合构建数据看板、业务报表和可视化分析流程。",
        "category": "数据分析",
        "tags": ["数据", "效率"],
        "quality_score": 91,
        "recommend_level": 4,
        "click_count": 610,
    },
    {
        "name": "Power BI",
        "url": "https://powerbi.microsoft.com",
        "logo_url": "https://powerbi.microsoft.com/favicon.ico",
        "summary": "Microsoft 数据分析与报表平台。",
        "description": "适合整理业务数据、搭建仪表盘和发布分析报表。",
        "category": "数据分析",
        "tags": ["数据", "办公"],
        "quality_score": 90,
        "recommend_level": 4,
        "click_count": 590,
    },
    {
        "name": "Jupyter",
        "url": "https://jupyter.org",
        "logo_url": "https://jupyter.org/favicon.ico",
        "summary": "交互式数据分析与代码笔记本工具。",
        "description": "适合 Python 数据分析、实验记录、可视化和教学演示。",
        "category": "数据分析",
        "tags": ["数据", "编程"],
        "quality_score": 92,
        "recommend_level": 5,
        "click_count": 640,
    },
    {
        "name": "SQL 教程",
        "url": "https://www.w3schools.com/sql/",
        "logo_url": "https://www.w3schools.com/favicon.ico",
        "summary": "面向入门者的 SQL 在线教程。",
        "description": "适合学习查询语句、数据库基础和数据分析常用 SQL 技能。",
        "category": "数据分析",
        "tags": ["数据", "编程", "学习"],
        "quality_score": 88,
        "recommend_level": 4,
        "click_count": 520,
    },
    {
        "name": "Notion 产品文档",
        "url": "https://www.notion.so/product",
        "logo_url": "https://www.notion.so/front-static/favicon.ico",
        "summary": "产品文档、需求整理与团队知识库工具。",
        "description": "适合产品需求、项目计划、用户研究资料和运营文档沉淀。",
        "category": "产品运营",
        "tags": ["效率", "文档", "办公"],
        "quality_score": 91,
        "recommend_level": 4,
        "click_count": 560,
    },
    {
        "name": "飞书产品协作",
        "url": "https://www.feishu.cn/product/docs",
        "logo_url": "https://www.feishu.cn/favicon.ico",
        "summary": "团队协作文档与项目推进平台。",
        "description": "适合产品运营团队进行文档协作、会议沉淀和跨部门沟通。",
        "category": "产品运营",
        "tags": ["效率", "办公", "文档"],
        "quality_score": 90,
        "recommend_level": 4,
        "click_count": 540,
    },
    {
        "name": "ProcessOn 产品流程",
        "url": "https://www.processon.com/diagraming",
        "logo_url": "https://www.processon.com/favicon.ico",
        "summary": "流程图、结构图和产品思路整理工具。",
        "description": "适合画业务流程、信息架构、产品结构和运营流程。",
        "category": "产品运营",
        "tags": ["效率", "设计"],
        "quality_score": 88,
        "recommend_level": 4,
        "click_count": 510,
    },
    {
        "name": "Canva 运营设计",
        "url": "https://www.canva.com/create/",
        "logo_url": "https://www.canva.com/favicon.ico",
        "summary": "运营活动、海报和演示设计工具。",
        "description": "适合运营物料、产品展示、社交媒体图片和活动视觉制作。",
        "category": "产品运营",
        "tags": ["设计", "效率"],
        "quality_score": 89,
        "recommend_level": 4,
        "click_count": 500,
    },
    {
        "name": "Figma 原型设计",
        "url": "https://www.figma.com/prototyping/",
        "logo_url": "https://static.figma.com/app/icon/1/favicon.png",
        "summary": "产品原型与 UI 协作设计工具。",
        "description": "适合快速搭建交互原型、设计界面并与团队协作评审。",
        "category": "原型设计",
        "tags": ["设计", "效率"],
        "quality_score": 94,
        "recommend_level": 5,
        "click_count": 680,
    },
    {
        "name": "墨刀",
        "url": "https://modao.cc",
        "logo_url": "https://modao.cc/favicon.ico",
        "summary": "在线产品原型设计与协作工具。",
        "description": "适合产品经理和设计师制作交互原型、流程演示和团队评审。",
        "category": "原型设计",
        "tags": ["设计", "效率"],
        "quality_score": 90,
        "recommend_level": 4,
        "click_count": 520,
    },
    {
        "name": "ProcessOn 原型流程",
        "url": "https://www.processon.com/diagrams",
        "logo_url": "https://www.processon.com/favicon.ico",
        "summary": "流程图与产品结构设计工具。",
        "description": "适合梳理产品结构、页面流程、业务流程和交互逻辑。",
        "category": "原型设计",
        "tags": ["设计", "效率"],
        "quality_score": 88,
        "recommend_level": 4,
        "click_count": 500,
    },
    {
        "name": "Canva 原型表达",
        "url": "https://www.canva.com/prototypes/",
        "logo_url": "https://www.canva.com/favicon.ico",
        "summary": "设计模板与产品视觉表达工具。",
        "description": "适合制作产品展示、低保真页面、运营视觉和方案表达。",
        "category": "原型设计",
        "tags": ["设计", "效率"],
        "quality_score": 87,
        "recommend_level": 4,
        "click_count": 490,
    },
]


def table_columns(cursor, table):
    cursor.execute(f"SHOW COLUMNS FROM {table}")
    return {row["Field"] for row in cursor.fetchall()}


def insert_with_known_columns(cursor, table, data, columns):
    available = {key: value for key, value in data.items() if key in columns}
    names = list(available.keys())
    placeholders = ", ".join(["%s"] * len(names))
    sql = f"INSERT INTO {table} ({', '.join(names)}) VALUES ({placeholders})"
    cursor.execute(sql, [available[name] for name in names])
    return cursor.lastrowid


def get_or_create_category(cursor, name, columns):
    cursor.execute("SELECT id FROM categories WHERE name=%s LIMIT 1", (name,))
    row = cursor.fetchone()
    if row:
        return row["id"]
    data = {"name": name, "parent_id": None, "icon": "", "sort_order": 0, "status": "active"}
    return insert_with_known_columns(cursor, "categories", data, columns)


def get_or_create_tag(cursor, name, columns):
    cursor.execute("SELECT id FROM tags WHERE name=%s LIMIT 1", (name,))
    row = cursor.fetchone()
    if row:
        return row["id"]
    return insert_with_known_columns(cursor, "tags", {"name": name, "type": "general"}, columns)


def get_or_create_site(cursor, site, website_columns, category_id):
    cursor.execute("SELECT id FROM websites WHERE url=%s OR name=%s LIMIT 1", (site["url"], site["name"]))
    row = cursor.fetchone()
    if row:
        return row["id"], False
    data = {
        "name": site["name"],
        "url": site["url"],
        "logo_url": site["logo_url"],
        "summary": site["summary"],
        "description": site["description"],
        "category_id": category_id,
        "is_free": 1,
        "need_login": 0,
        "region": "international",
        "quality_score": site["quality_score"],
        "recommend_level": site["recommend_level"],
        "click_count": site["click_count"],
        "clicks": site["click_count"],
        "favorite_count": 0,
        "rating_avg": 4.8,
        "status": "approved",
    }
    return insert_with_known_columns(cursor, "websites", data, website_columns), True


def link_site_tag(cursor, site_id, tag_id):
    cursor.execute(
        "INSERT IGNORE INTO site_tags (site_id, tag_id) VALUES (%s, %s)",
        (site_id, tag_id),
    )


def link_site_occupation(cursor, site_id, occupation, columns):
    data = {"site_id": site_id, "occupation": occupation, "weight": 1}
    available = {key: value for key, value in data.items() if key in columns}
    names = list(available.keys())
    placeholders = ", ".join(["%s"] * len(names))
    cursor.execute(
        f"INSERT IGNORE INTO site_occupations ({', '.join(names)}) VALUES ({placeholders})",
        [available[name] for name in names],
    )


def main():
    conn = get_connection()
    inserted = 0
    try:
        with conn.cursor() as cursor:
            category_columns = table_columns(cursor, "categories")
            tag_columns = table_columns(cursor, "tags")
            website_columns = table_columns(cursor, "websites")
            try:
                occupation_columns = table_columns(cursor, "site_occupations")
            except Exception:
                occupation_columns = set()

            category_ids = {
                name: get_or_create_category(cursor, name, category_columns)
                for name in CATEGORIES
            }
            tag_ids = {name: get_or_create_tag(cursor, name, tag_columns) for name in TAGS}

            for site in SITES:
                site_id, created = get_or_create_site(
                    cursor,
                    site,
                    website_columns,
                    category_ids[site["category"]],
                )
                inserted += int(created)
                for tag_name in site["tags"]:
                    link_site_tag(cursor, site_id, tag_ids[tag_name])
                if {"site_id", "occupation"}.issubset(occupation_columns):
                    for occupation in SITE_OCCUPATIONS.get(site["name"], OCCUPATIONS):
                        link_site_occupation(cursor, site_id, occupation, occupation_columns)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"Seed complete. Inserted {inserted} new websites.")


if __name__ == "__main__":
    main()
