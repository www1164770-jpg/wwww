"""Stable, versioned catalog for profile-based career recommendations.

This module is deliberately independent from website recommendation rules.  It
describes careers and their evidence only; it neither reads nor writes a
database and does not participate in the Phase 1 site-ranking weights.
"""
from __future__ import annotations

from collections import OrderedDict


def _career(code, name, category, occupation, directions, strong, supporting=(), tasks=(), pain_points=()):
    return {
        "code": code, "name": name, "category": category,
        "description": f"面向{name}的工作内容、技能成长与常见问题的职业方向。",
        "occupation": tuple(occupation), "directions": tuple(directions),
        "strong_tags": tuple(strong), "supporting_tags": tuple(supporting),
        "tasks": tuple(tasks), "pain_points": tuple(pain_points),
    }


# code, name, category, occupations, directions, strong tags, supporting tags, tasks, pain points
CAREERS = (
    # 技术研发
    _career("frontend_engineer", "前端工程师", "技术研发", ("developer", "freelancer"), ("frontend",), ("frontend",), ("javascript", "typescript", "html_css"), ("new_features", "maintenance"), ("slow_coding", "hard_debugging")),
    _career("vue_engineer", "Vue 工程师", "技术研发", ("developer", "freelancer"), ("frontend", "fullstack"), ("vue", "frontend"), ("javascript", "typescript"), ("new_features", "maintenance"), ("slow_coding", "hard_debugging")),
    _career("react_engineer", "React 工程师", "技术研发", ("developer", "freelancer"), ("frontend", "fullstack"), ("react", "frontend"), ("javascript", "typescript"), ("new_features", "maintenance"), ("slow_coding", "hard_debugging")),
    _career("backend_engineer", "后端工程师", "技术研发", ("developer", "freelancer"), ("backend", "fullstack"), ("backend",), ("api", "database", "python", "java", "go", "node"), ("api", "database", "maintenance"), ("api_debugging", "hard_debugging")),
    _career("python_engineer", "Python 开发工程师", "技术研发", ("developer", "freelancer"), ("backend", "ai_ml", "data"), ("python",), ("backend", "api", "database"), ("api", "data_processing", "new_features"), ("api_debugging", "slow_coding")),
    _career("java_engineer", "Java 开发工程师", "技术研发", ("developer", "freelancer"), ("backend",), ("java",), ("backend", "api", "database"), ("api", "maintenance", "new_features"), ("api_debugging", "hard_debugging")),
    _career("go_engineer", "Go 开发工程师", "技术研发", ("developer", "freelancer"), ("backend", "devops"), ("go",), ("backend", "api", "deployment"), ("api", "deployment", "new_features"), ("api_debugging", "hard_debugging")),
    _career("node_engineer", "Node.js 工程师", "技术研发", ("developer", "freelancer"), ("backend", "fullstack"), ("node",), ("javascript", "backend", "api"), ("api", "new_features", "maintenance"), ("api_debugging", "slow_coding")),
    _career("fullstack_engineer", "全栈工程师", "技术研发", ("developer", "freelancer"), ("fullstack",), ("fullstack",), ("frontend", "backend", "javascript", "node", "api"), ("new_features", "api", "deployment"), ("slow_coding", "hard_debugging")),
    _career("mobile_engineer", "移动端工程师", "技术研发", ("developer", "freelancer"), ("mobile",), ("mobile",), ("javascript", "typescript", "java"), ("new_features", "maintenance"), ("hard_debugging",)),
    _career("android_engineer", "Android 工程师", "技术研发", ("developer", "freelancer"), ("mobile",), ("android",), ("java", "mobile"), ("new_features", "maintenance"), ("hard_debugging",)),
    _career("ios_engineer", "iOS 工程师", "技术研发", ("developer", "freelancer"), ("mobile",), ("ios",), ("mobile",), ("new_features", "maintenance"), ("hard_debugging",)),
    _career("game_engineer", "游戏工程师", "技术研发", ("developer", "freelancer"), ("game",), ("game",), ("cpp", "csharp"), ("new_features", "maintenance"), ("hard_debugging",)),
    _career("embedded_engineer", "嵌入式工程师", "技术研发", ("developer", "freelancer"), ("embedded",), ("embedded",), ("cpp", "python"), ("new_features", "maintenance"), ("hard_debugging",)),
    _career("qa_engineer", "测试工程师", "技术研发", ("developer", "freelancer"), ("frontend", "backend", "fullstack"), ("testing",), ("debugging", "code_analysis"), ("testing", "code_review"), ("hard_debugging",)),
    _career("automation_test_engineer", "自动化测试工程师", "技术研发", ("developer", "freelancer"), ("frontend", "backend", "fullstack"), ("testing", "automation"), ("javascript", "python", "debugging"), ("testing", "code_review"), ("hard_debugging", "slow_coding")),
    _career("devops_engineer", "DevOps 工程师", "技术研发", ("developer", "freelancer"), ("devops",), ("devops", "deployment"), ("docker", "kubernetes", "cloud"), ("deployment", "maintenance"), ("deployment", "hard_debugging")),
    _career("sre_engineer", "SRE 工程师", "技术研发", ("developer", "freelancer"), ("devops",), ("sre", "deployment"), ("devops", "debugging", "cloud"), ("maintenance", "deployment"), ("hard_debugging", "deployment")),
    _career("operations_engineer", "运维工程师", "技术研发", ("developer", "freelancer"), ("devops",), ("devops",), ("deployment", "docker", "cloud"), ("deployment", "maintenance"), ("deployment",)),
    _career("database_engineer", "数据库工程师", "技术研发", ("developer", "freelancer"), ("backend", "data"), ("database",), ("backend", "sql", "data_processing"), ("database", "maintenance"), ("hard_debugging",)),
    _career("api_engineer", "API 工程师", "技术研发", ("developer", "freelancer"), ("backend", "fullstack"), ("api",), ("backend", "database", "deployment"), ("api", "testing"), ("api_debugging", "hard_debugging")),
    _career("cloud_engineer", "云工程师", "技术研发", ("developer", "freelancer"), ("devops", "backend"), ("cloud", "deployment"), ("docker", "kubernetes", "devops"), ("deployment", "maintenance"), ("deployment",)),
    # 人工智能
    _career("ai_application_engineer", "AI 应用开发工程师", "人工智能", ("developer", "freelancer"), ("ai_ml",), ("ai", "ai_ml"), ("code_generation", "python", "api", "deployment"), ("new_features", "api"), ("slow_coding", "api_debugging")),
    _career("ai_agent_engineer", "AI Agent 工程师", "人工智能", ("developer", "freelancer"), ("ai_ml",), ("ai", "ai_ml", "llm"), ("python", "api", "code_generation"), ("new_features", "api"), ("slow_coding", "api_debugging")),
    _career("llm_application_engineer", "LLM 应用开发工程师", "人工智能", ("developer", "freelancer"), ("ai_ml",), ("ai_ml", "llm", "python"), ("api", "deployment", "database", "code_generation"), ("api", "new_features", "deployment"), ("api_debugging", "slow_coding")),
    _career("prompt_engineer", "提示词工程师", "人工智能", ("developer", "creator", "product_operation", "freelancer"), ("ai_ml", "writing", "social_media"), ("ai", "llm"), ("content_creation", "code_generation", "ai_usage"), ("writing", "new_features"), ("slow_coding",)),
    _career("machine_learning_engineer", "机器学习工程师", "人工智能", ("developer", "freelancer"), ("ai_ml",), ("ai_ml", "python"), ("pytorch", "tensorflow", "data_science"), ("data_processing", "new_features"), ("hard_debugging",)),
    _career("deep_learning_engineer", "深度学习工程师", "人工智能", ("developer", "freelancer"), ("ai_ml",), ("ai_ml", "pytorch", "tensorflow"), ("python", "data_science"), ("data_processing", "new_features"), ("hard_debugging",)),
    _career("nlp_engineer", "自然语言处理工程师", "人工智能", ("developer", "freelancer"), ("ai_ml",), ("ai_ml", "llm", "python"), ("data_science", "api"), ("data_processing", "new_features"), ("hard_debugging",)),
    _career("computer_vision_engineer", "计算机视觉工程师", "人工智能", ("developer", "freelancer"), ("ai_ml",), ("ai_ml", "pytorch", "tensorflow"), ("python", "data_science"), ("data_processing", "new_features"), ("hard_debugging",)),
    _career("ai_backend_engineer", "AI 后端工程师", "人工智能", ("developer", "freelancer"), ("ai_ml",), ("ai", "ai_ml", "python"), ("api", "deployment", "database", "llm", "backend"), ("api", "deployment"), ("api_debugging", "hard_debugging")),
    _career("mlops_engineer", "MLOps 工程师", "人工智能", ("developer", "freelancer"), ("ai_ml",), ("ai_ml", "deployment"), ("python", "docker", "kubernetes", "cloud", "devops"), ("deployment", "maintenance"), ("deployment", "hard_debugging")),
    # 数据
    _career("data_analyst", "数据分析师", "数据", ("developer", "student", "product_operation", "freelancer"), ("data",), ("data", "data_processing"), ("python", "data_science", "sql"), ("data_analysis", "data_processing"), ("organize_materials",)),
    _career("data_engineer", "数据工程师", "数据", ("developer", "freelancer"), ("data", "backend"), ("data", "data_processing", "database"), ("python", "sql", "backend"), ("data_processing", "database"), ("hard_debugging",)),
    _career("data_scientist", "数据科学家", "数据", ("developer", "student", "freelancer"), ("data", "ai_ml"), ("data_science", "python"), ("ai_ml", "data_processing", "pytorch"), ("data_processing", "research"), ("find_resources",)),
    _career("business_analyst", "商业分析师", "数据", ("product_operation", "office", "student", "freelancer"), ("data", "product_manager"), ("data", "analytics"), ("spreadsheets", "data_processing", "project_management"), ("data_analysis", "research"), ("organize_materials",)),
    _career("bi_engineer", "BI 工程师", "数据", ("developer", "product_operation", "freelancer"), ("data",), ("data", "database"), ("sql", "data_processing", "analytics"), ("data_processing", "database"), ("hard_debugging",)),
    # 设计
    _career("ui_designer", "UI 设计师", "设计", ("designer", "freelancer"), ("ui_ux",), ("ui_design", "ui_ux"), ("prototype", "design"), ("ui", "prototype"), ("design_assets",)),
    _career("ux_designer", "UX 设计师", "设计", ("designer", "freelancer"), ("ui_ux",), ("ux_analysis", "ui_ux"), ("user_research", "prototype"), ("ux", "research"), ("design_assets",)),
    _career("ui_ux_designer", "UI/UX 设计师", "设计", ("designer", "freelancer"), ("ui_ux",), ("ui_ux",), ("ui_design", "ux_analysis", "prototype"), ("ui", "ux", "prototype"), ("design_assets",)),
    _career("web_designer", "网页设计师", "设计", ("designer", "freelancer"), ("ui_ux",), ("design", "ui_design"), ("html_css", "prototype"), ("ui", "prototype"), ("design_assets",)),
    _career("graphic_designer", "平面设计师", "设计", ("designer", "freelancer"), ("graphic",), ("graphic",), ("design", "image_generation", "editing"), ("design", "editing"), ("design_assets",)),
    _career("brand_designer", "品牌设计师", "设计", ("designer", "freelancer"), ("branding",), ("branding",), ("graphic", "design", "marketing"), ("design", "content"), ("design_assets",)),
    _career("visual_designer", "视觉设计师", "设计", ("designer", "freelancer"), ("graphic", "branding"), ("graphic", "design"), ("image_generation", "editing"), ("design", "editing"), ("design_assets",)),
    _career("illustrator", "插画师", "设计", ("designer", "creator", "freelancer"), ("illustration", "image"), ("illustration", "image_generation"), ("design", "editing"), ("design", "content"), ("design_assets",)),
    _career("3d_designer", "3D 设计师", "设计", ("designer", "freelancer"), ("3d",), ("3d",), ("design", "motion"), ("design", "editing"), ("design_assets",)),
    _career("motion_designer", "动效设计师", "设计", ("designer", "creator", "freelancer"), ("motion",), ("motion",), ("video", "editing", "design"), ("editing", "video"), ("design_assets",)),
    _career("interaction_designer", "交互设计师", "设计", ("designer", "freelancer"), ("ui_ux",), ("interaction", "ui_ux"), ("prototype", "ux_analysis"), ("prototype", "ux"), ("design_assets",)),
    _career("product_designer", "产品设计师", "设计", ("designer", "product_operation", "freelancer"), ("ui_ux", "product_manager"), ("product_design", "ui_ux"), ("prototype", "user_research"), ("prototype", "research"), ("design_assets",)),
    # 产品运营
    _career("product_manager", "产品经理", "产品运营", ("product_operation", "freelancer"), ("product_manager",), ("product_manager", "product_design"), ("prototype", "user_research", "project_management"), ("prototype", "research"), ("time_management",)),
    _career("ai_product_manager", "AI 产品经理", "产品运营", ("product_operation", "developer", "freelancer"), ("product_manager", "ai_ml"), ("ai", "product_design"), ("ai_ml", "llm", "prototype", "user_research"), ("prototype", "research"), ("time_management",)),
    _career("technical_product_manager", "技术产品经理", "产品运营", ("product_operation", "developer", "freelancer"), ("product_manager", "backend"), ("product_manager", "api"), ("backend", "database", "project_management"), ("api", "prototype"), ("api_debugging", "time_management")),
    _career("product_operation", "产品运营", "产品运营", ("product_operation", "freelancer"), ("product_operation",), ("product_operation", "content"), ("analytics", "project_management", "ai_assistant"), ("content", "data_analysis"), ("time_management",)),
    _career("user_operation", "用户运营", "产品运营", ("product_operation", "freelancer"), ("product_operation",), ("user_operation", "content"), ("analytics", "community"), ("content", "data_analysis"), ("time_management",)),
    _career("content_operation", "内容运营", "产品运营", ("product_operation", "creator", "freelancer"), ("product_operation", "social_media"), ("content", "content_creation"), ("seo", "analytics", "writing"), ("content", "data_analysis"), ("time_management",)),
    _career("community_operation", "社区运营", "产品运营", ("product_operation", "creator", "freelancer"), ("product_operation", "social_media"), ("community", "content"), ("collaboration", "analytics"), ("content", "data_analysis"), ("time_management",)),
    _career("growth_operation", "增长运营", "产品运营", ("product_operation", "freelancer"), ("product_operation",), ("growth", "analytics"), ("marketing", "content", "data_processing"), ("data_analysis", "content"), ("time_management",)),
    _career("marketing_operation", "市场运营", "产品运营", ("product_operation", "freelancer"), ("product_operation",), ("marketing",), ("content", "analytics", "seo"), ("content", "data_analysis"), ("time_management",)),
    _career("seo_operation", "SEO 运营", "产品运营", ("product_operation", "creator", "freelancer"), ("product_operation", "writing"), ("seo",), ("content", "analytics", "writing"), ("content", "research"), ("time_management",)),
    _career("ecommerce_operation", "电商运营", "产品运营", ("product_operation", "freelancer"), ("product_operation",), ("ecommerce", "marketing"), ("content", "analytics", "data_processing"), ("content", "data_analysis"), ("time_management",)),
    _career("data_operation", "数据运营", "产品运营", ("product_operation", "freelancer"), ("data", "product_operation"), ("data", "analytics"), ("data_processing", "content"), ("data_analysis", "research"), ("time_management",)),
    # 内容
    _career("content_creator", "内容创作者", "内容", ("creator", "freelancer"), ("writing", "image", "social_media"), ("content_creation",), ("writing", "editing", "ai_writing"), ("content", "writing"), ("find_resources",)),
    _career("short_video_creator", "短视频创作者", "内容", ("creator", "freelancer"), ("short_video",), ("short_video", "video"), ("editing", "subtitle", "cover", "ai_video"), ("video", "editing"), ("slow_coding",)),
    _career("video_editor", "视频剪辑师", "内容", ("creator", "freelancer"), ("short_video", "long_video"), ("editing", "video"), ("subtitle", "cover", "audio_editing"), ("editing", "video"), ("time_management",)),
    _career("video_creator", "视频创作者", "内容", ("creator", "freelancer"), ("short_video", "long_video"), ("video", "content_creation"), ("script", "editing", "ai_video"), ("video", "editing"), ("find_resources",)),
    _career("graphic_content_creator", "图文内容创作者", "内容", ("creator", "freelancer"), ("writing", "image", "social_media"), ("content_creation", "image_generation"), ("writing", "editing", "cover"), ("content", "editing"), ("find_resources",)),
    _career("wechat_creator", "公众号创作者", "内容", ("creator", "freelancer"), ("writing", "social_media"), ("writing", "content_creation"), ("seo", "ai_writing", "research"), ("content", "writing"), ("find_resources",)),
    _career("technical_blogger", "技术博主", "内容", ("creator", "developer", "freelancer"), ("writing", "backend", "frontend", "ai_ml"), ("writing", "programming"), ("documentation", "research", "code_generation"), ("writing", "research"), ("find_resources",)),
    _career("copywriter", "文案策划", "内容", ("creator", "freelancer"), ("writing",), ("copywriting", "writing"), ("ai_writing", "seo", "research"), ("writing",), ("find_resources",)),
    _career("script_writer", "脚本编剧", "内容", ("creator", "freelancer"), ("writing", "video"), ("script", "writing"), ("research", "ai_writing"), ("writing", "video"), ("find_resources",)),
    _career("streamer", "主播", "内容", ("creator", "freelancer"), ("social_media", "video", "audio"), ("social_media", "content_creation"), ("script", "voice", "cover"), ("content", "video"), ("time_management",)),
    _career("podcast_creator", "播客创作者", "内容", ("creator", "freelancer"), ("audio",), ("audio", "content_creation"), ("script", "voice", "audio_editing"), ("audio", "editing"), ("find_resources",)),
    _career("photographer", "摄影师", "内容", ("creator", "designer", "freelancer"), ("image",), ("image", "editing"), ("image_generation", "design"), ("editing", "content"), ("design_assets",)),
    # 教育
    _career("teacher", "教师", "教育", ("teacher",), ("education",), ("teaching",), ("lesson_plan", "ppt", "ai_teaching"), ("lesson_plan", "grading"), ("time_management",)),
    _career("college_teacher", "高校教师", "教育", ("teacher",), ("college",), ("teaching", "research"), ("lesson_plan", "paper", "citation"), ("research", "lesson_plan"), ("find_resources",)),
    _career("middle_school_teacher", "中学教师", "教育", ("teacher",), ("middle",), ("teaching",), ("lesson_plan", "question_generation", "class_management"), ("lesson_plan", "grading"), ("time_management",)),
    _career("primary_school_teacher", "小学教师", "教育", ("teacher",), ("primary",), ("teaching",), ("lesson_plan", "question_generation", "class_management"), ("lesson_plan", "grading"), ("time_management",)),
    _career("trainer", "培训师", "教育", ("teacher", "freelancer"), ("education",), ("teaching", "course_design"), ("lesson_plan", "ppt", "content_creation"), ("lesson_plan", "content"), ("time_management",)),
    _career("course_designer", "课程设计师", "教育", ("teacher", "freelancer"), ("education",), ("course_design", "teaching"), ("lesson_plan", "ppt", "content_creation"), ("lesson_plan", "research"), ("find_resources",)),
    _career("researcher", "研究人员", "教育", ("student", "teacher", "freelancer"), ("graduate", "research"), ("research",), ("paper", "citation", "data_analysis"), ("research", "data_analysis"), ("find_resources", "organize_materials")),
    _career("graduate_student", "研究生", "教育", ("student",), ("graduate",), ("graduate", "research"), ("paper", "citation", "data_analysis"), ("research", "paper"), ("find_resources", "organize_materials")),
    _career("college_student", "大学生", "教育", ("student",), ("college",), ("college",), ("programming", "research", "learning"), ("homework", "programming"), ("understanding", "exam")),
    _career("programming_learner", "编程学习者", "教育", ("student", "developer", "freelancer"), ("college", "vocational", "frontend", "backend"), ("programming", "learning"), ("python", "javascript", "documentation"), ("programming", "learning"), ("learning_curve", "understanding")),
    # 商务办公
    _career("administration", "行政专员", "商务办公", ("office",), ("administration",), ("documents", "automation"), ("spreadsheets", "meeting", "file_management"), ("documents", "automation"), ("time_management",)),
    _career("hr", "人力资源", "商务办公", ("office",), ("hr",), ("hr", "documents"), ("spreadsheets", "meeting", "automation"), ("documents", "data_analysis"), ("time_management",)),
    _career("finance", "财务", "商务办公", ("office",), ("finance",), ("finance", "spreadsheets"), ("automation", "data_processing"), ("spreadsheets", "data_analysis"), ("time_management",)),
    _career("accountant", "会计", "商务办公", ("office",), ("finance",), ("finance", "spreadsheets"), ("automation", "documents"), ("spreadsheets", "documents"), ("time_management",)),
    _career("sales", "销售", "商务办公", ("office", "freelancer"), ("sales",), ("sales", "collaboration"), ("documents", "meeting", "ai_assistant"), ("meeting", "documents"), ("time_management",)),
    _career("customer_service", "客户服务", "商务办公", ("office",), ("customer_service",), ("customer_service", "communication"), ("documents", "ai_assistant", "automation"), ("documents", "automation"), ("time_management",)),
    _career("project_manager", "项目经理", "商务办公", ("office", "product_operation", "freelancer"), ("project_manager",), ("project_management", "collaboration"), ("documents", "meeting", "automation"), ("project_management", "meeting"), ("time_management",)),
    _career("consultant", "咨询顾问", "商务办公", ("office", "freelancer"), ("consulting",), ("consulting", "research"), ("documents", "spreadsheets", "ai_assistant"), ("research", "documents"), ("find_resources",)),
    _career("freelancer", "自由职业者", "商务办公", ("freelancer",), ("consulting", "marketing", "other"), ("freelance",), ("project_management", "content_creation", "automation"), ("documents", "content"), ("time_management",)),
    _career("entrepreneur", "创业者", "商务办公", ("freelancer", "office", "product_operation"), ("consulting", "marketing", "product_manager"), ("entrepreneur", "project_management"), ("marketing", "content", "automation", "ai_assistant"), ("project_management", "content"), ("time_management",)),
)

BY_CODE = {career["code"]: career for career in CAREERS}
BY_CATEGORY = OrderedDict()
for _career_item in CAREERS:
    BY_CATEGORY.setdefault(_career_item["category"], []).append(_career_item)

# Old codes continue to resolve to their closest stable detailed direction.
LEGACY_CODE_MAP = {
    "frontend_developer": "frontend_engineer", "backend_developer": "backend_engineer",
    "ai_app_developer": "ai_application_engineer", "ai_application_developer": "ai_application_engineer",
    "llm_engineer": "llm_application_engineer", "large_language_model_engineer": "llm_application_engineer",
    "technical_operations": "operations_engineer", "tech_operations": "operations_engineer",
    "operations": "product_operation", "creator": "content_creator",
    "uiux": "ui_ux_designer", "ui_ux": "ui_ux_designer",
}


def get_career(value):
    key = str(value or "").strip().casefold()
    code = LEGACY_CODE_MAP.get(key, key)
    return BY_CODE.get(code)


def career_codes():
    return tuple(BY_CODE)


def career_site_keywords(code):
    career = get_career(code)
    if not career:
        return []
    return list(dict.fromkeys((*career["strong_tags"], *career["supporting_tags"], *career["tasks"])))
