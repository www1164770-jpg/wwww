function canonicalUrl(value) {
  const text = String(value || "").trim();
  if (!text) return "";

  try {
    const url = new URL(/^https?:\/\//i.test(text) ? text : `https://${text}`);
    url.hash = "";
    const hostname = url.hostname.toLowerCase().replace(/^www\./, "");
    const port = url.port ? `:${url.port}` : "";
    const pathname = url.pathname.replace(/\/+$/, "") || "/";
    return `${hostname}${port}${pathname}${url.search}`.toLowerCase();
  } catch {
    return text.replace(/\/+$/, "").toLowerCase();
  }
}

export const COMMON_TOOL_CATEGORY_IDS = new Set([
  "docs",
  "ai",
  "prototype",
  "ui",
  "assets",
  "office",
  "learning",
  "productivity",
  "data",
]);

const COMMON_TOOL_CATEGORY_KEYWORDS = [
  "学习",
  "课程",
  "办公",
  "文档",
  "开发",
  "代码",
  "设计",
  "图片",
  "图标",
  "素材",
  "原型",
  "效率",
  "协作",
  "AI",
  "人工智能",
  "数据",
  "可视化",
];

const COMMON_TOOL_GENERAL_KEYWORDS = [
  "搜索",
  "翻译",
  "百科",
  "词典",
  "阅读",
  "知识",
  "问答",
  "邮箱",
  "邮件",
  "网盘",
  "云盘",
  "笔记",
  "地图",
  "导航",
  "浏览器",
  "效率",
  "政务",
  "查询",
  "在线办理",
];

const COMMON_TOOL_BLOCKED_KEYWORDS = [
  "游戏",
  "手游",
  "娱乐",
  "音乐",
  "音频",
  "影音",
  "影视",
  "电影",
  "电视剧",
  "综艺",
  "直播",
  "短视频",
  "在线视频",
  "视频平台",
  "媒体播放",
  "新闻",
  "资讯",
  "外卖",
  "订餐",
  "酒店",
  "旅行",
  "旅游",
  "购物",
  "电商",
];

function hasEligibleQuality(site) {
  const rawScore = site.quality_score ?? site.qualityScore;
  if (rawScore === undefined || rawScore === null || rawScore === "") {
    return true;
  }
  const score = Number(rawScore);
  if (!Number.isFinite(score) || score <= 0) return true;
  if (score <= 1) return score >= 0.6;
  if (score <= 5) return score >= 3;
  return score >= 60;
}

export function isEligibleCommonTool(site = {}) {
  const name = String(site.name ?? site.title ?? "").trim();
  if (!name || !canonicalUrl(site.url ?? site.website_url ?? site.href)) {
    return false;
  }
  if (name === "百度") return false;
  if (
    site.is_active === false ||
    site.is_active === 0 ||
    site.active === false
  ) {
    return false;
  }

  const status = String(site.status || "")
    .trim()
    .toLowerCase();
  if (
    ["inactive", "disabled", "deleted", "rejected", "pending"].includes(status)
  ) {
    return false;
  }
  if (!hasEligibleQuality(site)) return false;

  const categoryId = String(
    site.category_id ?? site.categoryId ?? site.category_code ?? "",
  )
    .trim()
    .toLowerCase();
  const categoryText = [
    site.category_name,
    site.categoryName,
    typeof site.category === "string" ? site.category : site.category?.name,
    ...(Array.isArray(site.tags) ? site.tags : []),
  ]
    .filter(Boolean)
    .join(" ");
  const fullText = [
    name,
    site.shortDescription,
    site.summary,
    site.description,
    categoryText,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  if (
    COMMON_TOOL_BLOCKED_KEYWORDS.some((keyword) =>
      fullText.includes(keyword.toLowerCase()),
    )
  ) {
    return false;
  }

  if (COMMON_TOOL_CATEGORY_IDS.has(categoryId)) return true;
  if (categoryId === "common") {
    return COMMON_TOOL_GENERAL_KEYWORDS.some((keyword) =>
      fullText.includes(keyword.toLowerCase()),
    );
  }
  return COMMON_TOOL_CATEGORY_KEYWORDS.some((keyword) =>
    categoryText.toLowerCase().includes(keyword.toLowerCase()),
  );
}

export function getCommonToolKey(site = {}) {
  const urlKey = canonicalUrl(
    site.url ?? site.website_url ?? site.href ?? site.link,
  );
  if (urlKey) return `url:${urlKey}`;

  const id = String(site.id ?? site.site_id ?? site.siteId ?? "").trim();
  if (id) return `id:${id}`;

  const name = String(site.name ?? site.title ?? "")
    .trim()
    .toLowerCase();
  return name ? `name:${name}` : "";
}

export function dedupeCommonTools(candidates = []) {
  const seenKeys = new Set();
  const seenIds = new Set();
  const seenUrls = new Set();
  const result = [];

  for (const site of Array.isArray(candidates) ? candidates : []) {
    if (!site || typeof site !== "object") continue;
    const key = getCommonToolKey(site);
    const id = String(site.id ?? site.site_id ?? site.siteId ?? "").trim();
    const url = canonicalUrl(
      site.url ?? site.website_url ?? site.href ?? site.link,
    );
    if (
      !key ||
      seenKeys.has(key) ||
      (id && seenIds.has(id)) ||
      (url && seenUrls.has(url))
    ) {
      continue;
    }

    seenKeys.add(key);
    if (id) seenIds.add(id);
    if (url) seenUrls.add(url);
    result.push(site);
  }

  return result;
}

export function fisherYatesShuffle(items = [], random = Math.random) {
  const shuffled = [...items];
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(random() * (index + 1));
    [shuffled[index], shuffled[randomIndex]] = [
      shuffled[randomIndex],
      shuffled[index],
    ];
  }
  return shuffled;
}

function movePreviouslyShownToEnd(queue, avoidedSites = []) {
  const avoidedKeys = new Set(
    avoidedSites.map(getCommonToolKey).filter(Boolean),
  );
  if (!avoidedKeys.size) return queue;

  const fresh = [];
  const repeated = [];
  queue.forEach((site) => {
    (avoidedKeys.has(getCommonToolKey(site)) ? repeated : fresh).push(site);
  });
  return [...fresh, ...repeated];
}

export function createCommonToolsQueue(
  candidates = [],
  avoidedSites = [],
  random = Math.random,
) {
  return movePreviouslyShownToEnd(
    fisherYatesShuffle(dedupeCommonTools(candidates), random),
    avoidedSites,
  );
}

export function takeNextCommonToolsBatch({
  candidates = [],
  shuffled = [],
  cursor = 0,
  previousBatch = [],
  batchSize = 3,
  random = Math.random,
} = {}) {
  const pool = dedupeCommonTools(candidates);
  const targetSize = Math.min(Math.max(0, Number(batchSize) || 0), pool.length);
  if (!targetSize) return { batch: [], shuffled: [], cursor: 0 };

  let queue = dedupeCommonTools(shuffled);
  let nextCursor = Math.max(0, Number(cursor) || 0);
  const batch = [];
  const batchKeys = new Set();

  while (batch.length < targetSize) {
    if (!queue.length || nextCursor >= queue.length) {
      queue = createCommonToolsQueue(
        pool,
        [...previousBatch, ...batch],
        random,
      );
      nextCursor = 0;
    }

    const site = queue[nextCursor];
    nextCursor += 1;
    const key = getCommonToolKey(site);
    if (!key || batchKeys.has(key)) continue;
    batchKeys.add(key);
    batch.push(site);
  }

  return { batch, shuffled: queue, cursor: nextCursor };
}
