export const occupationDefinitions = Object.freeze([
  {
    code: "frontend_developer",
    label: "前端开发",
    direction: "技术研发",
    aliases: ["programmer", "frontend", "程序员"],
  },
  {
    code: "backend_developer",
    label: "后端开发",
    direction: "技术研发",
    aliases: ["backend"],
  },
  {
    code: "ai_app_developer",
    label: "AI 应用开发",
    direction: "技术研发",
    aliases: ["ai_application_developer"],
  },
  {
    code: "llm_engineer",
    label: "大模型工程师",
    direction: "技术研发",
    aliases: ["large_language_model_engineer"],
  },
  {
    code: "product_manager",
    label: "产品经理",
    direction: "产品与设计",
    aliases: ["product"],
  },
  {
    code: "ui_ux_designer",
    label: "UI/UX 设计师",
    direction: "产品与设计",
    aliases: ["designer", "uiux", "ui_ux", "设计师"],
  },
  {
    code: "data_analyst",
    label: "数据分析师",
    direction: "数据与运营",
    aliases: ["data"],
  },
  {
    code: "operations",
    label: "运营",
    direction: "数据与运营",
    aliases: ["marketing", "ecommerce"],
  },
  {
    code: "technical_operations",
    label: "技术运营",
    direction: "数据与运营",
    aliases: ["tech_operations"],
  },
  {
    code: "student",
    label: "学生",
    direction: "教育与内容",
    aliases: [],
  },
  {
    code: "teacher",
    label: "教师",
    direction: "教育与内容",
    aliases: [],
  },
  {
    code: "creator",
    label: "自媒体创作者",
    direction: "教育与内容",
    aliases: ["content_creator", "self_media_creator", "内容创作者"],
  },
  {
    code: "other",
    label: "其他",
    direction: "通用方向",
    aliases: [],
  },
]);

const directionDescriptions = {
  技术研发: "代码、工程与 AI 应用",
  产品与设计: "产品规划与体验设计",
  数据与运营: "数据洞察与业务增长",
  教育与内容: "学习、教学与内容创作",
  通用方向: "探索通用效率工具",
};

export const careerDirections = Object.freeze(
  [
    "技术研发",
    "产品与设计",
    "数据与运营",
    "教育与内容",
    "通用方向",
  ].map((name) => ({
    name,
    description: directionDescriptions[name],
    occupations: occupationDefinitions.filter(
      (occupation) => occupation.direction === name,
    ),
  })),
);

const occupationLookup = new Map();

for (const occupation of occupationDefinitions) {
  for (const value of [
    occupation.code,
    occupation.label,
    ...occupation.aliases,
  ]) {
    occupationLookup.set(String(value).trim().toLowerCase(), occupation.code);
  }
}

export function normalizeOccupation(value) {
  const key = String(value ?? "").trim().toLowerCase();
  return key ? occupationLookup.get(key) || "" : "";
}

export function getOccupation(value) {
  const code = normalizeOccupation(value);
  return occupationDefinitions.find((occupation) => occupation.code === code) || null;
}

export function getOccupationLabel(value) {
  return getOccupation(value)?.label || "";
}

export function resolveOccupationSelection({
  sessionValue,
  storedValue,
  questionnaireValue,
} = {}) {
  for (const value of [sessionValue, storedValue, questionnaireValue]) {
    const normalized = normalizeOccupation(value);
    if (normalized) return normalized;
  }
  return "";
}

