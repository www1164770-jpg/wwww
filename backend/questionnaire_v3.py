"""Questionnaire V3: adaptive, versioned profile collection.

The graph deliberately lives in code (rather than a database row per question)
so a submitted response always has an immutable, reproducible interpretation.
"""
from __future__ import annotations

from copy import deepcopy

QUESTIONNAIRE_VERSION = 3


def option(label, value, next_question=None):
    item = {"label": label, "value": value}
    if next_question:
        item["next"] = next_question
    return item


def question(question_id, title, options, *, next_question=None, options_when=None,
             next_when=None, multi=False, min_selections=1, max_selections=None,
             stage="了解你的具体需求", description=None):
    item = {
        "id": question_id, "title": title, "description": description,
        "type": "multi" if multi else "single", "required": True,
        "options": options, "stage": stage,
    }
    if next_question:
        item["next"] = next_question
    if options_when:
        item["optionsWhen"] = options_when
    if next_when:
        item["nextWhen"] = next_when
    if multi:
        item["minSelections"] = min_selections
        item["maxSelections"] = max_selections
    return item


def opts(*values):
    return [option(item[0], item[1], item[2] if len(item) > 2 else None) for item in values]


IDENTITY = "了解你的身份"
WORKFLOW = "了解你的工作/学习方式"
NEEDS = "了解你的具体需求"
PREFERENCES = "了解你的工具偏好"

QUESTIONNAIRE_CONFIG = {
    "version": QUESTIONNAIRE_VERSION,
    "start_question_id": "occupation",
    "questions": {
        "occupation": question("occupation", "你当前的身份 / 职业是？", opts(
            ("学生", "student", "student_stage"), ("程序员 / 开发者", "developer", "developer_direction"), ("设计师", "designer", "designer_direction"),
            ("产品 / 运营", "product_operation", "product_role"), ("行政 / 办公", "office", "office_role"), ("教师 / 教育工作者", "teacher", "teaching_stage"),
            ("内容创作者", "creator", "creator_type"), ("自由职业者", "freelancer", "freelancer_secondary_role"), ("其他", "other", "general_scenario"),
        ), stage=IDENTITY),
        "developer_direction": question("developer_direction", "你的主要开发方向是？", opts(
            ("前端", "frontend"), ("后端", "backend"), ("全栈", "fullstack"), ("移动端", "mobile"),
            ("AI / 机器学习", "ai_ml"), ("数据", "data"), ("DevOps", "devops"), ("游戏", "game"),
            ("嵌入式", "embedded"), ("其他", "other"),
        ), next_question="tech_stack", stage=IDENTITY),
        "tech_stack": question("tech_stack", "你常用或希望深入哪些技术？", opts(
            ("Vue", "vue"), ("React", "react"), ("Angular", "angular"), ("JavaScript", "javascript"),
            ("TypeScript", "typescript"), ("HTML / CSS", "html_css"), ("Node.js", "node"), ("Python", "python"),
            ("Java", "java"), ("Go", "go"), ("PHP", "php"), ("C#", "csharp"), ("C++", "cpp"),
            ("PyTorch", "pytorch"), ("TensorFlow", "tensorflow"), ("LLM", "llm"), ("数据科学", "data_science"),
            ("Docker", "docker"), ("Kubernetes", "kubernetes"),
        ), multi=True, max_selections=4, next_question="developer_tasks", stage=WORKFLOW,
        options_when={"developer_direction": {
            "frontend": ["vue", "react", "angular", "javascript", "typescript", "html_css", "node"],
            "backend": ["python", "java", "go", "node", "php", "csharp", "cpp"],
            "fullstack": ["vue", "react", "javascript", "typescript", "node", "python", "java"],
            "mobile": ["javascript", "typescript", "node", "java", "cpp"],
            "ai_ml": ["python", "pytorch", "tensorflow", "llm", "data_science"],
            "data": ["python", "data_science", "llm", "java"],
            "devops": ["python", "go", "docker", "kubernetes", "node"],
            "game": ["cpp", "csharp", "javascript"], "embedded": ["cpp", "c", "python"],
            "other": ["python", "javascript", "typescript", "java", "go"],
        }}),
        "developer_tasks": question("developer_tasks", "你目前最常做哪些开发任务？", opts(
            ("新功能", "new_features"), ("维护", "maintenance"), ("调试", "debugging"), ("API", "api"),
            ("数据库", "database"), ("测试", "testing"), ("代码评审", "code_review"), ("部署", "deployment"), ("学习", "learning"),
        ), multi=True, max_selections=3, next_question="developer_pain_points", stage=NEEDS),
        "developer_pain_points": question("developer_pain_points", "哪些问题最影响你的工作？", opts(
            ("编码速度", "slow_coding"), ("难以调试", "hard_debugging"), ("测试", "testing"), ("API 调试", "api_debugging"),
            ("文档", "documentation"), ("项目管理", "project_management"), ("部署", "deployment"), ("学习曲线", "learning_curve"), ("AI 代码质量", "ai_code_quality"),
        ), multi=True, max_selections=3, next_question="developer_need", stage=NEEDS),
        "developer_need": question("developer_need", "你最希望工具优先帮你解决什么？", opts(
            ("生成代码", "code_generation", "coding_need"), ("调试", "debugging"), ("生成 UI", "ui_generation"), ("API 调试", "api_debugging"),
            ("技术文档", "documentation"), ("Git / 项目管理", "git_project_management"), ("学习技术", "learning"),
        ), next_question="experience_level", next_when={"occupation": {"freelancer": "freelancer_business_needs"}}, stage=NEEDS,
        options_when={
            "developer_tasks": {
                "new_features": ["code_generation", "ui_generation", "debugging", "documentation", "git_project_management", "learning"],
                "maintenance": ["debugging", "documentation", "git_project_management", "learning"],
                "debugging": ["debugging", "documentation", "code_generation"],
                "api": ["api_debugging", "debugging", "documentation", "code_generation"],
                "database": ["debugging", "documentation", "code_generation"],
                "testing": ["debugging", "code_generation", "documentation"],
                "code_review": ["debugging", "documentation", "learning"],
                "deployment": ["debugging", "documentation", "git_project_management"],
                "learning": ["learning", "documentation", "code_generation"],
            },
            "developer_pain_points": {
                "slow_coding": ["code_generation", "debugging", "ui_generation"],
                "hard_debugging": ["debugging", "api_debugging", "documentation"],
                "testing": ["debugging", "code_generation", "documentation"],
                "api_debugging": ["api_debugging", "debugging", "documentation"],
                "documentation": ["documentation", "learning"],
                "project_management": ["git_project_management", "documentation"],
                "deployment": ["debugging", "git_project_management", "documentation"],
                "learning_curve": ["learning", "documentation"],
                "ai_code_quality": ["debugging", "code_generation", "documentation"],
            },
        }),
        "coding_need": question("coding_need", "你更需要哪类 AI 编程能力？", opts(
            ("按需求生成", "generate_from_requirement"), ("代码补全", "code_completion"), ("修改现有代码", "modify_existing_code"),
            ("解释代码", "explain_code"), ("生成测试", "generate_tests"), ("重构", "refactor"),
        ), next_question="experience_level", next_when={"occupation": {"freelancer": "freelancer_business_needs"}}, stage=NEEDS),

        "student_stage": question("student_stage", "你目前处于哪个学习阶段？", opts(
            ("中学", "middle"), ("大学", "college"), ("研究生", "graduate"), ("职业教育", "vocational"), ("其他", "other"),
        ), next_question="study_field", stage=IDENTITY),
        "study_field": question("study_field", "你的学习领域是？", opts(
            ("计算机科学", "computer_science"), ("工程", "engineering"), ("理学", "science"), ("商科", "business"),
            ("语言", "language"), ("人文", "humanities"), ("设计", "design"), ("医学", "medicine"), ("法律", "law"), ("教育", "education"), ("其他", "other"),
        ), next_question="student_tasks", stage=IDENTITY),
        "student_tasks": question("student_tasks", "你近期主要在做什么？", opts(
            ("资料研究", "research"), ("作业", "homework"), ("论文", "paper"), ("编程", "programming"), ("记忆", "memorization"),
            ("语言学习", "language_learning"), ("PPT", "ppt"), ("数据分析", "data_analysis"), ("考试", "exam"),
        ), multi=True, max_selections=3, next_question="student_pain_points", stage=WORKFLOW),
        "student_pain_points": question("student_pain_points", "哪些环节最有困难？", opts(
            ("找资料", "find_resources"), ("整理材料", "organize_materials"), ("写作", "writing"), ("理解知识", "understanding"),
            ("论文", "paper"), ("引用", "citation"), ("考试", "exam"), ("时间管理", "time_management"),
        ), multi=True, max_selections=3, next_question="student_need", stage=NEEDS),
        "student_need": question("student_need", "你最希望优先获得哪类帮助？", opts(
            ("搜索学习资料", "research", "research_need"), ("写论文 / 作业", "homework", "research_need"), ("AI 辅助学习", "ai_learning"),
            ("语言学习", "language_learning"), ("编程学习", "programming"), ("制作 PPT", "ppt"), ("整理文档", "document_management"), ("考试复习", "exam"),
        ), next_question="experience_level", stage=NEEDS),
        "research_need": question("research_need", "研究或论文工作最需要哪类支持？", opts(
            ("检索文献", "literature_search"), ("论文结构", "outline"), ("写作润色", "writing"), ("数据分析", "data_analysis"), ("文献管理", "citation_management"), ("格式检查", "format_check"),
        ), next_question="experience_level", stage=NEEDS,
        options_when={"student_tasks": {"research": ["literature_search", "outline", "writing", "data_analysis", "citation_management", "format_check"], "paper": ["literature_search", "outline", "writing", "citation_management", "format_check"]}}),

        "designer_direction": question("designer_direction", "你主要从事哪类设计？", opts(
            ("UI / UX", "ui_ux"), ("平面", "graphic"), ("插画", "illustration"), ("品牌", "branding"), ("3D", "3d"), ("动效 / 视频", "motion"),
        ), next_question="designer_outputs", stage=IDENTITY),
        "designer_outputs": question("designer_outputs", "你通常交付哪些作品？", opts(
            ("UI", "ui"), ("网站", "website"), ("App", "app"), ("海报", "poster"), ("Logo", "logo"), ("插画", "illustration"), ("品牌", "brand"), ("3D", "3d"), ("动效", "animation"), ("视频", "video"),
        ), multi=True, max_selections=3, next_question="designer_stage", stage=WORKFLOW),
        "designer_stage": question("designer_stage", "你最常需要支持的阶段是？", opts(
            ("调研", "research"), ("构思", "ideation"), ("原型", "prototype"), ("制作", "production"), ("评审", "review"), ("交付", "delivery"),
        ), multi=True, max_selections=2, next_question="designer_pain_points", stage=WORKFLOW),
        "designer_pain_points": question("designer_pain_points", "哪些问题最困扰你？", opts(
            ("灵感", "inspiration"), ("素材", "assets"), ("图标", "icons"), ("配色", "colors"), ("字体", "fonts"), ("原型", "prototype"),
            ("AI 生成", "ai_generation"), ("图片编辑", "image_editing"), ("协作", "collaboration"), ("UX 分析", "ux_analysis"),
        ), multi=True, max_selections=3, next_question="designer_need", stage=NEEDS),
        "designer_need": question("designer_need", "当前最优先的需求是？", opts(
            ("UI 设计", "ui_design"), ("制作原型", "prototype"), ("配色", "color"), ("图标 / 素材", "icons_assets"), ("AI 生成界面", "ai_ui_generation"), ("UX 分析", "ux_analysis"),
        ), next_question="experience_level", next_when={"occupation": {"freelancer": "freelancer_business_needs"}}, stage=NEEDS),

        "creator_type": question("creator_type", "你的主要创作形式是？", opts(
            ("文字", "writing"), ("图片", "image"), ("短视频", "short_video"), ("长视频", "long_video"), ("自媒体运营", "social_media"), ("音频", "audio"),
        ), next_question="content_platforms", stage=IDENTITY),
        "content_platforms": question("content_platforms", "你主要发布在哪些平台？", opts(
            ("抖音", "douyin"), ("Bilibili", "bilibili"), ("小红书", "xiaohongshu"), ("YouTube", "youtube"), ("微信公众号", "wechat"), ("知乎", "zhihu"), ("其他", "other"),
        ), multi=True, max_selections=3, next_question="creator_tasks", stage=WORKFLOW),
        "creator_tasks": question("creator_tasks", "你需要哪些创作支持？", opts(
            ("选题", "topic"), ("资料研究", "research"), ("文案", "copywriting"), ("脚本", "script"), ("配音", "voice"), ("字幕", "subtitle"),
            ("剪辑", "editing"), ("封面", "cover"), ("素材", "assets"), ("AI 绘图", "ai_image"), ("AI 视频", "ai_video"), ("数据分析", "analytics"),
        ), multi=True, max_selections=4, next_question="creator_need", stage=NEEDS,
        options_when={"creator_type": {
            "writing": ["topic", "research", "copywriting", "assets", "analytics"],
            "image": ["topic", "copywriting", "cover", "assets", "ai_image", "analytics"],
            "short_video": ["topic", "research", "script", "voice", "subtitle", "editing", "cover", "assets", "ai_video", "analytics"],
            "long_video": ["topic", "research", "script", "voice", "subtitle", "editing", "cover", "assets", "ai_video", "analytics"],
            "social_media": ["topic", "research", "copywriting", "cover", "assets", "ai_image", "analytics"],
            "audio": ["topic", "research", "script", "voice", "assets", "analytics"],
        }}),
        "creator_need": question("creator_need", "当前最希望工具帮你完成什么？", opts(
            ("文案", "copywriting"), ("资料", "research"), ("脚本", "script"), ("图片生成", "image_generation"), ("图片编辑", "image_editing"),
            ("配音", "voice"), ("音频编辑", "audio_editing"), ("视频剪辑", "editing"), ("字幕", "subtitle"), ("封面", "cover"), ("AI 视频", "ai_video"),
        ), next_question="experience_level", next_when={"occupation": {"freelancer": "freelancer_business_needs"}}, stage=NEEDS),

        "teaching_stage": question("teaching_stage", "你的教学场景是？", opts(("小学", "primary"), ("初中", "middle"), ("高中", "high"), ("大学", "college"), ("职教", "vocational"), ("培训", "training")), next_question="teacher_subject", stage=IDENTITY),
        "teacher_subject": question("teacher_subject", "你主要教授什么学科？", opts(("语文", "language"), ("数学", "math"), ("英语", "english"), ("科学", "science"), ("计算机", "computer"), ("艺术", "arts"), ("商科", "business"), ("其他", "other")), next_question="teacher_tasks", stage=IDENTITY),
        "teacher_tasks": question("teacher_tasks", "你经常做哪些工作？", opts(("备课", "lesson_plan"), ("PPT", "ppt"), ("找资源", "resource_search"), ("出题", "question_generation"), ("批改", "grading"), ("课堂互动", "class_interaction"), ("研究", "research"), ("班级管理", "class_management"), ("AI 教学", "ai_teaching")), multi=True, max_selections=3, next_question="teacher_need", stage=WORKFLOW),
        "teacher_need": question("teacher_need", "当前最需要的支持是？", opts(("备课", "lesson_plan"), ("制作 PPT", "ppt"), ("生成题目", "question_generation"), ("作业批改", "grading"), ("教育研究", "research"), ("查找资源", "resource_search"), ("AI 教学", "ai_teaching"), ("班级管理", "class_management")), next_question="experience_level", stage=NEEDS),

        "office_role": question("office_role", "你的主要办公角色是？", opts(("行政", "administration"), ("人力", "hr"), ("财务", "finance"), ("销售", "sales"), ("客服", "customer_service"), ("管理", "management"), ("通用办公", "general")), next_question="office_tasks", stage=IDENTITY),
        "office_tasks": question("office_tasks", "你最常处理哪些任务？", opts(("文档", "documents"), ("表格", "spreadsheets"), ("PPT", "ppt"), ("邮件", "email"), ("会议", "meeting"), ("文件管理", "file_management"), ("数据录入", "data_entry"), ("表单", "forms"), ("报告", "reporting"), ("自动化", "automation")), multi=True, max_selections=3, next_question="office_automation_need", stage=WORKFLOW),
        "office_automation_need": question("office_automation_need", "哪些流程最值得自动化？", opts(("Excel", "excel"), ("生成文档", "document_generation"), ("邮件", "email"), ("数据录入", "data_entry"), ("文件整理", "file_organization"), ("会议纪要", "meeting_notes"), ("报告", "reports")), multi=True, max_selections=3, next_question="office_need", stage=NEEDS),
        "office_need": question("office_need", "当前最希望提升哪项效率？", opts(("文档", "documents"), ("表格", "spreadsheets"), ("PPT", "ppt"), ("会议", "meeting"), ("邮件", "email"), ("文件管理", "file_management"), ("自动化", "automation"), ("AI 办公", "ai_office")), next_question="experience_level", stage=NEEDS),

        "product_role": question("product_role", "你的角色更接近？", opts(("产品经理", "product_manager"), ("产品运营", "product_operation"), ("用户运营", "user_operation"), ("内容运营", "content_operation"), ("营销", "marketing"), ("SEO", "seo"), ("增长", "growth"), ("电商", "ecommerce")), next_question="product_tasks", stage=IDENTITY),
        "product_tasks": question("product_tasks", "你当前主要在做哪些事？", opts(("用户研究", "user_research"), ("原型", "prototype"), ("数据分析", "analytics"), ("项目管理", "project_management"), ("SEO", "seo"), ("内容", "content"), ("竞品分析", "competitor_analysis"), ("营销", "marketing"), ("自动化", "automation"), ("AI 助手", "ai_assistant")), multi=True, max_selections=3, next_question="product_need", stage=WORKFLOW),
        "product_need": question("product_need", "当前最需要什么能力？", opts(("产品设计", "product_design"), ("用户研究", "user_research"), ("数据分析", "analytics"), ("项目管理", "project_management"), ("营销", "marketing"), ("SEO", "seo"), ("内容运营", "content"), ("原型", "prototype"), ("AI 助手", "ai_assistant")), next_question="experience_level", next_when={"occupation": {"freelancer": "freelancer_business_needs"}}, stage=NEEDS),

        "freelancer_secondary_role": question("freelancer_secondary_role", "你的主要专业方向是？", opts(("开发", "development", "developer_direction"), ("设计", "design", "designer_direction"), ("创作", "creator", "creator_type"), ("营销", "marketing", "product_role"), ("其他", "other", "freelancer_business_needs")), stage=IDENTITY),
        "freelancer_business_needs": question("freelancer_business_needs", "自由职业工作最需要改善什么？", opts(("客户管理", "client_management"), ("合同", "contract"), ("报价", "quotation"), ("时间管理", "time_management"), ("项目管理", "project_management"), ("收款", "payment"), ("作品集", "portfolio"), ("个人品牌", "personal_brand")), multi=True, max_selections=3, next_question="experience_level", stage=NEEDS),
        "general_scenario": question("general_scenario", "你主要在哪类场景使用工具？", opts(("学习", "learning"), ("办公", "office"), ("创意", "creative"), ("技术", "technical"), ("商业", "business"), ("个人效率", "personal_productivity")), next_question="general_need", stage=IDENTITY),
        "general_need": question("general_need", "你最希望获得什么帮助？", opts(("提升效率", "efficiency"), ("学习成长", "learning"), ("内容创作", "content_creation"), ("协作 / 项目管理", "project_management"), ("AI 助手", "ai"), ("数据处理", "data_processing")), next_question="experience_level", stage=NEEDS),

        "experience_level": question("experience_level", "你对相关工具的经验程度是？", opts(("新手", "beginner"), ("基础", "basic"), ("熟练", "intermediate"), ("高级", "advanced")), next_question="goals", stage=WORKFLOW),
        "goals": question("goals", "你希望工具为你带来什么？", opts(("提升效率", "efficiency"), ("学习", "learning"), ("AI 辅助", "ai_assistance"), ("自动化", "automation"), ("内容创作", "content_creation"), ("数据处理", "data_processing"), ("协作", "collaboration"), ("项目管理", "project_management"), ("研究", "research"), ("专业工作", "professional_work")), multi=True, max_selections=3, next_question="priorities", stage=PREFERENCES),
        "priorities": question("priorities", "选择工具时，你最看重什么？", opts(("免费价值", "free_value"), ("中文支持", "chinese_support"), ("容易使用", "easy_to_use"), ("无需注册", "no_signup"), ("AI 能力", "ai"), ("专业", "professional"), ("速度", "speed"), ("隐私", "privacy"), ("跨平台", "cross_platform"), ("协作", "collaboration")), multi=True, max_selections=3, next_question="platforms", stage=PREFERENCES),
        "platforms": question("platforms", "你主要在哪些平台使用？", opts(("Windows", "windows"), ("macOS", "macos"), ("Linux", "linux"), ("Android", "android"), ("iOS", "ios"), ("Web", "web")), multi=True, max_selections=3, next_question="budget_preference", stage=PREFERENCES),
        "budget_preference": question("budget_preference", "你的预算偏好是？", opts(("仅免费", "free_only"), ("优先免费", "free_first"), ("可订阅", "subscription_ok"), ("价格不重要", "price_not_important")), next_question="ai_usage_style", stage=PREFERENCES),
        "ai_usage_style": question("ai_usage_style", "你通常如何使用 AI？", opts(("还未使用", "not_using"), ("偶尔辅助", "occasional"), ("日常工作流", "daily_workflow"), ("自动化流程", "automation")), next_question="collaboration_scenario", stage=PREFERENCES),
        "collaboration_scenario": question("collaboration_scenario", "你主要在哪种协作场景中工作？", opts(("独立完成", "solo"), ("小团队", "small_team"), ("跨部门", "cross_functional"), ("客户协作", "client"), ("课堂 / 学习小组", "study_group")), stage=PREFERENCES),
    },
}

PROFILE_CATEGORIES = {
    "developer": ["development", "ai"], "student": ["learning"], "designer": ["design"],
    "creator": ["content"], "teacher": ["education"], "office": ["office"],
    "product_operation": ["product", "operation"], "freelancer": ["freelance"], "other": ["general"],
}
DEVELOPER_DIRECTION_TO_CAREER = {"frontend": "frontend_engineer", "backend": "backend_engineer", "fullstack": "fullstack_engineer", "mobile": "mobile_engineer", "ai_ml": "ai_application_engineer", "data": "data_analyst", "devops": "devops_engineer", "game": "game_engineer", "embedded": "embedded_engineer"}
OCCUPATION_TO_CAREER = {"student": "college_student", "teacher": "teacher", "creator": "content_creator", "office": "administration", "product_operation": "product_manager", "designer": "ui_ux_designer", "other": "freelancer"}


def get_config():
    return deepcopy(QUESTIONNAIRE_CONFIG)


def _visible_options(question_id, answers):
    data = QUESTIONNAIRE_CONFIG["questions"][question_id]
    rules = data.get("optionsWhen") or {}
    allowed = None
    for source, values in rules.items():
        selected = answers.get(source)
        selected_values = selected if isinstance(selected, list) else [selected]
        matching = set()
        for selected_value in selected_values:
            matching.update(values.get(selected_value, []))
        if matching:
            allowed = matching if allowed is None else allowed & matching
    return [item for item in data["options"] if allowed is None or item["value"] in allowed]


def _next_question(question_id, value, answers):
    data = QUESTIONNAIRE_CONFIG["questions"][question_id]
    for source, choices in (data.get("nextWhen") or {}).items():
        if answers.get(source) in choices:
            return choices[answers[source]]
    for item in _visible_options(question_id, answers):
        values = value if isinstance(value, list) else [value]
        if item["value"] in values and item.get("next"):
            return item["next"]
    return data.get("next", "")


def answer_path(answers):
    answers = answers if isinstance(answers, dict) else {}
    path, current = [], QUESTIONNAIRE_CONFIG["start_question_id"]
    while current and current not in path:
        path.append(current)
        value = answers.get(current)
        if value is None:
            break
        current = _next_question(current, value, answers)
    return path


def validate_answers(answers):
    if not isinstance(answers, dict):
        raise ValueError("answers must be an object")
    clean, path = {}, answer_path(answers)
    if not path or answers.get("occupation") not in {item["value"] for item in QUESTIONNAIRE_CONFIG["questions"]["occupation"]["options"]}:
        raise ValueError("occupation is required")
    for question_id in path:
        data, value = QUESTIONNAIRE_CONFIG["questions"][question_id], answers.get(question_id)
        if value is None:
            raise ValueError(f"missing answer for {question_id}")
        valid_values = {item["value"] for item in _visible_options(question_id, answers)}
        if data["type"] == "multi":
            if not isinstance(value, list) or len(value) < data.get("minSelections", 1):
                raise ValueError(f"invalid answer for {question_id}")
            if data.get("maxSelections") and len(value) > data["maxSelections"]:
                raise ValueError(f"too many selections for {question_id}")
            if len(value) != len(set(value)) or any(item not in valid_values for item in value):
                raise ValueError(f"invalid answer for {question_id}")
            clean[question_id] = list(value)
        elif not isinstance(value, str) or value not in valid_values:
            raise ValueError(f"invalid answer for {question_id}")
        else:
            clean[question_id] = value
    if _next_question(path[-1], clean[path[-1]], clean):
        raise ValueError(f"missing answer after {path[-1]}")
    return clean, path


def _first(answers, keys):
    return next((answers[key] for key in keys if answers.get(key)), "")


def _values(answers, keys):
    result = []
    for key in keys:
        value = answers.get(key)
        result.extend(value if isinstance(value, list) else [value] if value else [])
    return list(dict.fromkeys(result))


def build_recommendation_profile(answers):
    occupation = answers.get("occupation", "other")
    secondary_role = answers.get("freelancer_secondary_role", "")
    direction = _first(answers, ("developer_direction", "designer_direction", "creator_type", "product_role", "general_scenario"))
    if occupation == "developer" or (occupation == "freelancer" and "developer_direction" in answers):
        career = DEVELOPER_DIRECTION_TO_CAREER.get(answers.get("developer_direction"), "other")
    elif occupation == "freelancer" and "designer_direction" in answers:
        career = "ui_ux_designer"
    elif occupation == "freelancer" and "creator_type" in answers:
        career = "content_creator"
    else:
        career = OCCUPATION_TO_CAREER.get(occupation, "other")
    primary_need = _first(answers, ("developer_need", "student_need", "designer_need", "creator_need", "teacher_need", "office_need", "product_need", "general_need"))
    tasks = _values(answers, ("developer_tasks", "student_tasks", "designer_stage", "creator_tasks", "teacher_tasks", "office_tasks", "product_tasks"))
    pain_points = _values(answers, ("developer_pain_points", "student_pain_points", "designer_pain_points", "freelancer_business_needs"))
    skills = _values(answers, ("tech_stack", "study_field", "teacher_subject"))
    # Only semantic, reached answers are mapped to tags.  Question IDs and
    # arbitrary answer values are never copied wholesale into the catalog tags.
    tags = list(dict.fromkeys([
        *PROFILE_CATEGORIES.get(occupation, ["general"]), direction, primary_need,
        *skills, *tasks, *pain_points, *answers.get("goals", []), *answers.get("platforms", []),
        answers.get("budget_preference", ""), answers.get("ai_usage_style", ""),
    ]))
    tags = [tag for tag in tags if tag]
    priorities = list(answers.get("priorities", []))
    return {
        "profile_schema_version": 3, "occupation": occupation, "secondary_role": secondary_role,
        "career_code": career, "direction": direction, "experience_level": answers.get("experience_level", ""),
        "primary_need": primary_need, "secondary_needs": tasks[1:], "skills": skills, "tasks": tasks,
        "pain_points": pain_points, "goals": list(answers.get("goals", [])), "priorities": priorities,
        "priority": priorities[0] if priorities else "", "primary_priority": priorities[0] if priorities else "",
        "platforms": list(answers.get("platforms", [])), "budget_preference": answers.get("budget_preference", ""),
        "categories": PROFILE_CATEGORIES.get(occupation, ["general"]), "tags": tags,
    }


def v2_defaults(v2_answers):
    """Safely seed editable V3 defaults; they are not a silent V3 submission."""
    if not isinstance(v2_answers, dict):
        return {}
    keys = ("occupation", "developer_direction", "designer_direction", "creator_type")
    defaults = {key: v2_answers[key] for key in keys if v2_answers.get(key)}
    stages = {"middle_school": "middle", "college": "college", "graduate": "graduate", "vocational": "vocational", "other": "other"}
    if v2_answers.get("student_stage") in stages:
        defaults["student_stage"] = stages[v2_answers["student_stage"]]
    if v2_answers.get("priority"):
        defaults["priorities"] = [v2_answers["priority"]]
    return defaults
