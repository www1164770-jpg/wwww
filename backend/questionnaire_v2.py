"""Configuration and pure helpers for the adaptive questionnaire (version 2)."""

from __future__ import annotations

from copy import deepcopy


QUESTIONNAIRE_VERSION = 2


def option(label, value, next_question=None):
    return {"label": label, "value": value, "next": next_question}


def question(question_id, title, options, *, description=None, options_when=None):
    payload = {
        "id": question_id,
        "title": title,
        "description": description,
        "type": "single",
        "required": True,
        "options": options,
    }
    if options_when:
        payload["optionsWhen"] = options_when
    return payload


QUESTIONNAIRE_CONFIG = {
    "version": QUESTIONNAIRE_VERSION,
    "start_question_id": "occupation",
    "questions": {
        "occupation": question("occupation", "你当前的身份 / 职业是？", [
            option("学生", "student", "student_stage"),
            option("程序员 / 开发者", "developer", "developer_direction"),
            option("设计师", "designer", "designer_direction"),
            option("产品 / 运营", "product_operation", "product_need"),
            option("行政 / 办公", "office", "office_need"),
            option("教师 / 教育工作者", "teacher", "teacher_need"),
            option("内容创作者", "creator", "creator_type"),
            option("自由职业者", "freelancer", "freelancer_type"),
            option("其他", "other", "general_need"),
        ]),
        "developer_direction": question("developer_direction", "你的主要开发方向是？", [
            option("前端开发", "frontend", "developer_need"), option("后端开发", "backend", "developer_need"),
            option("全栈开发", "fullstack", "developer_need"), option("移动端开发", "mobile", "developer_need"),
            option("AI / 机器学习", "ai_ml", "developer_need"), option("数据开发", "data", "developer_need"),
            option("运维 / DevOps", "devops", "developer_need"), option("其他", "other", "developer_need"),
        ]),
        "developer_need": question("developer_need", "你目前最希望工具帮你解决什么？", [
            option("快速生成代码", "code_generation", "coding_need"), option("排查代码问题", "debugging", "usage_frequency"),
            option("UI / 页面生成", "ui_generation", "usage_frequency"), option("API 调试", "api_debugging", "usage_frequency"),
            option("技术文档查询", "documentation", "usage_frequency"), option("Git / 项目管理", "git_project_management", "usage_frequency"),
            option("学习新技术", "learning", "usage_frequency"),
        ]),
        "coding_need": question("coding_need", "你更需要哪类 AI 编程能力？", [
            option("根据需求生成代码", "generate_from_requirement", "usage_frequency"), option("自动补全代码", "code_completion", "usage_frequency"),
            option("修改现有代码", "modify_existing_code", "usage_frequency"), option("解释代码", "explain_code", "usage_frequency"),
            option("自动生成测试", "generate_tests", "usage_frequency"), option("重构代码", "refactor", "usage_frequency"),
        ]),
        "student_stage": question("student_stage", "你目前主要处于哪个学习阶段？", [
            option("中学", "middle_school", "student_need"), option("大专 / 本科", "college", "student_need"),
            option("研究生", "graduate", "student_need"), option("职业技能学习", "vocational", "student_need"), option("其他", "other", "student_need"),
        ]),
        "student_need": question("student_need", "你最希望解决什么问题？", [
            option("搜索学习资料", "research", "research_need"), option("写论文 / 作业", "homework", "research_need"),
            option("AI 辅助学习", "ai_learning", "usage_frequency"), option("外语学习", "language_learning", "usage_frequency"),
            option("编程学习", "programming", "usage_frequency"), option("制作 PPT", "ppt", "usage_frequency"),
            option("文档整理", "document_management", "usage_frequency"), option("考试复习", "exam", "usage_frequency"),
        ]),
        "research_need": question("research_need", "你更需要哪方面的帮助？", [
            option("查找文献", "literature_search", "usage_frequency"), option("整理论文结构", "outline", "usage_frequency"),
            option("写作润色", "writing", "usage_frequency"), option("数据分析", "data_analysis", "usage_frequency"),
            option("文献管理", "citation_management", "usage_frequency"), option("查重 / 格式检查", "format_check", "usage_frequency"),
        ]),
        "designer_direction": question("designer_direction", "你主要从事哪类设计？", [
            option("UI / UX", "ui_ux", "designer_need"), option("平面设计", "graphic", "designer_need"), option("插画", "illustration", "designer_need"),
            option("品牌设计", "branding", "designer_need"), option("3D 设计", "3d", "designer_need"), option("视频 / 动效", "motion", "designer_need"),
        ]),
        "designer_need": question("designer_need", "当前最需要解决的问题是？", [
            option("UI 设计", "ui_design", "usage_frequency"), option("原型制作", "prototype", "usage_frequency"), option("配色", "color", "usage_frequency"),
            option("图标 / 素材", "icons_assets", "usage_frequency"), option("AI 生成界面", "ai_ui_generation", "usage_frequency"), option("用户体验分析", "ux_analysis", "usage_frequency"),
        ]),
        "creator_type": question("creator_type", "你的主要创作形式是？", [
            option("文字", "writing", "creator_need"), option("图片", "image", "creator_need"), option("短视频", "short_video", "creator_need"),
            option("长视频", "long_video", "creator_need"), option("自媒体运营", "social_media", "creator_need"), option("音频", "audio", "creator_need"),
        ]),
        "creator_need": question("creator_need", "你目前最需要什么？", [
            option("文案", "copywriting", "usage_frequency"), option("查找资料", "research", "usage_frequency"), option("SEO", "seo", "usage_frequency"), option("写作润色", "proofreading", "usage_frequency"), option("AI 写作", "ai_writing", "usage_frequency"),
            option("图片生成", "image_generation", "usage_frequency"), option("图片编辑", "editing", "usage_frequency"), option("抠图 / 去背景", "background_removal", "usage_frequency"), option("AI 配音", "voice", "usage_frequency"), option("音频剪辑", "audio_editing", "usage_frequency"), option("降噪", "noise_reduction", "usage_frequency"), option("音乐", "music", "usage_frequency"), option("脚本", "script", "usage_frequency"),
            option("视频剪辑", "editing", "usage_frequency"), option("字幕", "subtitle", "usage_frequency"), option("封面", "cover", "usage_frequency"), option("AI 视频生成", "ai_video", "usage_frequency"), option("素材", "stock_assets", "usage_frequency"),
        ], options_when={
            "creator_type": {
                "writing": ["copywriting", "research", "seo", "proofreading", "ai_writing"],
                "image": ["image_generation", "editing", "background_removal", "stock_assets", "cover"],
                "short_video": ["copywriting", "voice", "editing", "subtitle", "cover", "ai_video", "stock_assets"],
                "long_video": ["copywriting", "voice", "editing", "subtitle", "cover", "ai_video", "stock_assets"],
                "social_media": ["copywriting", "editing", "cover", "ai_video", "stock_assets"],
                "audio": ["script", "voice", "audio_editing", "noise_reduction", "music"],
            },
            "freelancer_type": {
                "writing": ["copywriting", "research", "seo", "proofreading", "ai_writing"],
                "video": ["copywriting", "voice", "editing", "subtitle", "cover", "ai_video", "stock_assets"],
            },
        }),
        "product_need": question("product_need", "你目前最需要的工具能力是？", [
            option("产品设计", "product_design", "usage_frequency"), option("用户研究", "user_research", "usage_frequency"), option("数据分析", "analytics", "usage_frequency"),
            option("项目管理", "project_management", "usage_frequency"), option("营销", "marketing", "usage_frequency"), option("SEO", "seo", "usage_frequency"), option("内容运营", "content", "usage_frequency"), option("原型制作", "prototype", "usage_frequency"), option("AI 助手", "ai_assistant", "usage_frequency"),
        ]),
        "office_need": question("office_need", "你最需要提升哪项办公效率？", [
            option("文档", "documents", "usage_frequency"), option("表格", "spreadsheets", "usage_frequency"), option("PPT", "ppt", "usage_frequency"), option("会议", "meeting", "usage_frequency"), option("邮件", "email", "usage_frequency"), option("文件管理", "file_management", "usage_frequency"), option("自动化", "automation", "usage_frequency"), option("AI 办公", "ai_office", "usage_frequency"),
        ]),
        "teacher_need": question("teacher_need", "你最需要什么教学支持？", [
            option("备课", "lesson_plan", "usage_frequency"), option("制作 PPT", "ppt", "usage_frequency"), option("生成题目", "question_generation", "usage_frequency"), option("作业批改", "grading", "usage_frequency"), option("教育研究", "research", "usage_frequency"), option("查找资源", "resource_search", "usage_frequency"), option("AI 教学", "ai_teaching", "usage_frequency"), option("班级管理", "class_management", "usage_frequency"),
        ]),
        "freelancer_type": question("freelancer_type", "你的主要工作类别是？", [
            option("开发", "development", "developer_direction"), option("设计", "design", "designer_direction"), option("写作", "writing", "creator_need"), option("视频", "video", "creator_need"), option("营销", "marketing", "product_need"), option("咨询", "consulting", "general_need"), option("其他", "other", "general_need"),
        ]),
        "general_need": question("general_need", "你目前最希望工具帮助什么？", [
            option("提高效率", "efficiency", "usage_frequency"), option("学习成长", "learning", "usage_frequency"), option("内容创作", "content_creation", "usage_frequency"), option("协作与项目管理", "project_management", "usage_frequency"), option("AI 助手", "ai", "usage_frequency"),
        ]),
        "usage_frequency": question("usage_frequency", "你使用在线工具的频率是？", [
            option("每天", "daily", "priority"), option("每周数次", "several_times_week", "priority"), option("偶尔", "occasionally", "priority"), option("很少", "rarely", "priority"),
        ]),
        "priority": question("priority", "选择工具时你最关注什么？", [
            option("容易上手", "easy_to_use"), option("功能强大", "powerful"), option("免费 / 性价比", "free_value"), option("AI 能力", "ai"), option("专业性", "professional"), option("效率", "efficiency"),
        ]),
    },
}


OCCUPATION_TO_CAREER = {
    "student": "student", "teacher": "teacher", "creator": "creator", "office": "other",
    "product_operation": "product_manager", "designer": "ui_ux_designer", "other": "other",
}
DEVELOPER_DIRECTION_TO_CAREER = {
    "frontend": "frontend_developer", "backend": "backend_developer", "fullstack": "frontend_developer",
    "mobile": "frontend_developer", "ai_ml": "ai_app_developer", "data": "data_analyst",
    "devops": "technical_operations", "other": "other",
}
PROFILE_CATEGORIES = {
    "developer": ["development", "ai"], "student": ["learning"], "designer": ["design"],
    "creator": ["content"], "teacher": ["education"], "office": ["office"],
    "product_operation": ["product", "operation"], "freelancer": ["freelance"], "other": ["general"],
}


def get_config():
    return deepcopy(QUESTIONNAIRE_CONFIG)


def answer_path(answers: dict) -> list[str]:
    """Return the configured path implied by answers, stopping at the first gap."""
    answers = answers if isinstance(answers, dict) else {}
    path, question_id = [], QUESTIONNAIRE_CONFIG["start_question_id"]
    while question_id:
        question_data = QUESTIONNAIRE_CONFIG["questions"].get(question_id)
        if question_data is None or question_id in path:
            break
        path.append(question_id)
        value = answers.get(question_id)
        selected = next((item for item in _visible_options(question_id, answers) if item["value"] == value), None)
        if selected is None:
            break
        question_id = selected.get("next")
    return path


def validate_answers(answers: dict) -> tuple[dict, list[str]]:
    if not isinstance(answers, dict):
        raise ValueError("answers must be an object")
    clean = {str(key): value for key, value in answers.items() if value is not None}
    path = answer_path(clean)
    if not path or path[0] != "occupation":
        raise ValueError("occupation is required")
    for question_id in path:
        question_data = QUESTIONNAIRE_CONFIG["questions"][question_id]
        value = clean.get(question_id)
        if not isinstance(value, str) or not any(option["value"] == value for option in _visible_options(question_id, clean)):
            raise ValueError(f"invalid answer for {question_id}")
    last_question = QUESTIONNAIRE_CONFIG["questions"][path[-1]]
    last_value = clean[path[-1]]
    if next(option for option in _visible_options(path[-1], clean) if option["value"] == last_value).get("next"):
        raise ValueError(f"missing answer after {path[-1]}")
    return {question_id: clean[question_id] for question_id in path}, path


def _visible_options(question_id: str, answers: dict) -> list[dict]:
    question_data = QUESTIONNAIRE_CONFIG["questions"][question_id]
    options_when = question_data.get("optionsWhen") or {}
    allowed = None
    for source_question, conditions in options_when.items():
        if answers.get(source_question) in conditions:
            allowed = set(conditions[answers[source_question]])
            break
    if allowed is None and options_when:
        # If the controlling answer is not one of the configured values, show
        # the union only until the path is complete; validation still rejects
        # an answer that cannot be reached from the selected creator type.
        allowed = set().union(*(
            set(option_values)
            for conditions in options_when.values()
            for option_values in conditions.values()
        ))
    return [option for option in question_data["options"] if allowed is None or option["value"] in allowed]


def build_recommendation_profile(answers: dict) -> dict:
    occupation = answers.get("occupation", "other")
    secondary_role = answers.get("freelancer_type", "")
    direction = answers.get("developer_direction") or answers.get("designer_direction") or answers.get("creator_type") or secondary_role
    if occupation == "developer" or (occupation == "freelancer" and "developer_direction" in answers):
        career = DEVELOPER_DIRECTION_TO_CAREER.get(answers.get("developer_direction"), "other")
    elif occupation == "freelancer" and "designer_direction" in answers:
        career = "ui_ux_designer"
    elif occupation == "freelancer" and "creator_need" in answers:
        career = "creator"
    else:
        career = OCCUPATION_TO_CAREER.get(occupation, "other")
    excluded = {"occupation", "usage_frequency"}
    tags = [value for key, value in answers.items() if key not in excluded]
    tags = list(dict.fromkeys([*PROFILE_CATEGORIES.get(occupation, ["general"]), *tags]))
    return {
        "occupation": occupation,
        "career_code": career,
        "categories": PROFILE_CATEGORIES.get(occupation, ["general"]),
        "tags": tags,
        "direction": direction or "",
        "secondary_role": secondary_role,
        "primary_need": next((answers[key] for key in ("developer_need", "student_need", "designer_need", "creator_need", "product_need", "office_need", "teacher_need", "general_need") if key in answers), ""),
        "priority": answers.get("priority", ""),
    }


def legacy_payload_to_answers(payload: dict) -> dict:
    """Translate the former flat submit payload into a valid V2 path."""
    payload = payload if isinstance(payload, dict) else {}
    raw = str(payload.get("occupation") or "").strip().lower()
    direction_by_career = {
        "frontend_developer": "frontend", "backend_developer": "backend",
        "ai_app_developer": "ai_ml", "llm_engineer": "ai_ml", "data_analyst": "data",
        "technical_operations": "devops",
    }
    if raw in direction_by_career:
        occupation, direction = "developer", direction_by_career[raw]
    elif raw in {"ui_ux_designer", "designer"}:
        occupation, direction = "designer", "ui_ux"
    elif raw in {"product_manager", "operations", "product_operation"}:
        occupation, direction = "product_operation", ""
    elif raw in {"student", "teacher", "creator", "office", "freelancer", "other"}:
        occupation, direction = raw, ""
    else:
        occupation, direction = "other", ""
    answers = {"occupation": occupation}
    if occupation == "developer":
        answers.update({"developer_direction": direction, "developer_need": "learning"})
    elif occupation == "designer":
        answers.update({"designer_direction": direction or "ui_ux", "designer_need": "ui_design"})
    elif occupation == "student":
        answers.update({"student_stage": "college", "student_need": "ai_learning"})
    elif occupation == "creator":
        answers.update({"creator_type": "social_media", "creator_need": "copywriting"})
    elif occupation == "teacher":
        answers["teacher_need"] = "ai_teaching"
    elif occupation == "office":
        answers["office_need"] = "documents"
    elif occupation == "product_operation":
        answers["product_need"] = "ai_assistant"
    else:
        answers["general_need"] = "efficiency"
    answers.update({"usage_frequency": "daily", "priority": "efficiency"})
    return answers
