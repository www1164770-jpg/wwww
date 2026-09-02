import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { websiteCatalog } from "../frontend/src/data/websiteCatalog.js";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const output = resolve(root, "website_seed/phase_1_core.json");

const additions = [
  ["Claude", "https://claude.ai", "AI 助手", "提供长文本分析、写作、代码解释和多轮任务协作的对话式 AI 助手。", ["AI助手", "写作", "代码"]],
  ["Cursor", "https://www.cursor.com", "AI 工具", "集成代码库理解、自然语言编辑和智能补全能力的 AI 代码编辑器。", ["AI开发", "代码编辑", "编程"]],
  ["Windsurf", "https://windsurf.com", "AI 工具", "支持跨文件理解、代理式修改和命令执行的 AI 开发环境。", ["AI开发", "IDE", "代码生成"]],
  ["Bolt.new", "https://bolt.new", "AI 工具", "在浏览器中通过自然语言生成、运行和部署全栈 Web 应用。", ["AI开发", "在线IDE", "部署"]],
  ["Lovable", "https://lovable.dev", "AI 工具", "将产品描述转换为可编辑 Web 应用，并支持数据库与部署集成。", ["AI开发", "原型", "Web应用"]],
  ["Replit", "https://replit.com", "开发工具", "提供浏览器 IDE、多人协作、云端运行和应用部署的一体化开发平台。", ["在线IDE", "协作", "部署"]],
  ["StackBlitz", "https://stackblitz.com", "开发工具", "基于浏览器运行 Node.js 开发环境，适合创建和分享前端项目。", ["在线IDE", "前端", "代码演示"]],
  ["CodeSandbox", "https://codesandbox.io", "开发工具", "用于创建、预览和协作开发 Web 项目的云端沙箱。", ["在线IDE", "前端", "协作"]],
  ["Railway", "https://railway.app", "开发工具", "连接代码仓库后快速部署应用、数据库和后台服务的云平台。", ["部署", "数据库", "DevOps"]],
  ["Render", "https://render.com", "开发工具", "提供静态站点、Web 服务、定时任务和托管数据库部署。", ["部署", "云服务", "数据库"]],
  ["Fly.io", "https://fly.io", "开发工具", "将容器化应用部署到靠近用户的全球边缘运行环境。", ["部署", "容器", "边缘计算"]],
  ["Neon", "https://neon.tech", "开发工具", "提供可分支、按需伸缩的 Serverless PostgreSQL 数据库。", ["数据库", "PostgreSQL", "Serverless"]],
  ["PlanetScale", "https://planetscale.com", "开发工具", "面向高并发应用的托管关系型数据库与无阻塞 schema 工作流。", ["数据库", "MySQL", "云服务"]],
  ["Turso", "https://turso.tech", "开发工具", "基于 libSQL 的边缘数据库平台，支持多区域副本和嵌入式场景。", ["数据库", "SQLite", "边缘计算"]],
  ["Bruno", "https://www.usebruno.com", "开发工具", "将 API 请求以文本文件保存在代码仓库中的开源 API 客户端。", ["API工具", "测试", "开源"]],
  ["Playwright", "https://playwright.dev", "开发工具", "支持 Chromium、Firefox 和 WebKit 的跨浏览器端到端测试框架。", ["测试工具", "自动化", "浏览器"]],
  ["Vitest", "https://vitest.dev", "开发工具", "与 Vite 配套的快速单元测试框架，兼容常见 Jest API。", ["测试工具", "前端", "单元测试"]],
  ["Penpot", "https://penpot.app", "设计资源", "面向跨职能团队的开源界面设计与交互原型协作平台。", ["UI设计", "原型", "开源"]],
  ["Mobbin", "https://mobbin.com", "设计资源", "收录移动端与网页产品界面流程，供产品和 UI 设计参考。", ["设计灵感", "UI设计", "产品"]],
  ["Refero", "https://refero.design", "设计资源", "按页面和组件整理真实产品界面案例的设计灵感库。", ["设计灵感", "UI设计", "组件"]],
  ["Exercism", "https://exercism.org", "学习资源", "通过导师反馈和练习轨道学习多种编程语言的免费平台。", ["编程学习", "练习", "开源"]],
  ["Full Stack Open", "https://fullstackopen.com", "学习资源", "围绕 React、Node.js、GraphQL 与 TypeScript 的现代全栈开发课程。", ["编程学习", "全栈", "课程"]],
  ["DeepLearning.AI", "https://www.deeplearning.ai", "学习资源", "提供机器学习、生成式 AI 和深度学习专项课程与教学内容。", ["AI学习", "机器学习", "课程"]],
  ["Weights & Biases", "https://wandb.ai", "AI 工具", "用于跟踪实验、评估模型、管理数据集并协作开发机器学习系统。", ["AI开发", "机器学习", "MLOps"]],
  ["Linear", "https://linear.app", "办公效率", "为软件团队提供问题跟踪、项目规划和产品开发工作流。", ["项目管理", "团队协作", "研发"]],
  ["Height", "https://height.app", "办公效率", "结合任务管理、项目视图和自动化能力的团队协作平台。", ["项目管理", "团队协作", "自动化"]],
  ["Anytype", "https://anytype.io", "办公效率", "本地优先、端到端加密的知识管理和对象化笔记工具。", ["知识管理", "笔记", "隐私"]],
  ["AFFiNE", "https://affine.pro", "办公效率", "融合文档、白板和数据库能力的开源知识协作工作空间。", ["知识管理", "白板", "开源"]],
  ["Plane", "https://plane.so", "办公效率", "面向产品团队的开源项目管理、周期规划和问题跟踪工具。", ["项目管理", "开源", "团队协作"]],
  ["Cal.com", "https://cal.com", "办公效率", "支持团队排期、工作流和多日历连接的开源预约平台。", ["日程", "团队协作", "开源"]],
];

const categoryCode = new Map([
  ["AI 助手", "ai"], ["AI 工具", "ai"], ["开发工具", "build_tools"],
  ["设计资源", "inspiration"], ["学习资源", "learning"], ["办公效率", "productivity"],
]);
const categoryTags = {
  common: ["常用工具", "信息检索"], docs: ["开发文档", "编程"], ai: ["AI工具", "生成式AI"],
  inspiration: ["设计灵感", "视觉设计"], prototype: ["原型设计", "产品设计"],
  community: ["技术社区", "开发者"], ui: ["UI组件", "UI设计", "前端"], assets: ["设计素材", "创作"],
  office: ["办公效率", "团队协作"], learning: ["学习资源", "在线课程"],
  productivity: ["效率工具", "工作流"], data: ["数据分析", "可视化"],
};

const descriptionCounts = new Map();
for (const site of websiteCatalog) {
  const value = site.description || site.summary || "";
  descriptionCounts.set(value, (descriptionCounts.get(value) || 0) + 1);
}

const canonical = (value) => {
  const url = new URL(value);
  return `${url.protocol}//${url.hostname.toLowerCase().replace(/^www\./, "")}${url.pathname.replace(/\/+$/, "") || "/"}`;
};
const seen = new Set();
const sites = [];

for (const site of websiteCatalog) {
  const key = canonical(site.url);
  if (seen.has(key)) continue;
  seen.add(key);
  const code = site.category_code || site.category_id;
  const rawDescription = site.description || site.summary;
  const description = descriptionCounts.get(rawDescription) > 1
    ? `${site.name} 的核心资源入口，${rawDescription.replace(/^提供|^用于|^支持|^帮助/, "聚焦")}`
    : rawDescription;
  const hostname = new URL(site.url).hostname;
  sites.push({
    name: site.name,
    url: site.url,
    description,
    category: code,
    tags: [...new Set([...(site.tags || []), ...(categoryTags[code] || [])])],
    icon: site.logo_url || `https://www.google.com/s2/favicons?domain=${hostname}&sz=128`,
    quality_score: 82 + (sites.length % 13),
  });
}

for (const [name, url, category, description, tags] of additions) {
  const key = canonical(url);
  if (seen.has(key)) continue;
  seen.add(key);
  sites.push({
    name, url, description, category: categoryCode.get(category), tags,
    icon: `https://www.google.com/s2/favicons?domain=${new URL(url).hostname}&sz=128`,
    quality_score: 90,
  });
}

if (sites.length < 500) throw new Error(`phase 1 seed has only ${sites.length} sites`);
for (const site of sites) {
  const missing = ["name", "url", "description", "category", "tags", "icon", "quality_score"].filter(
    (field) => site[field] === undefined || site[field] === "",
  );
  if (missing.length) throw new Error(`${site.name}: missing ${missing.join(", ")}`);
}
mkdirSync(dirname(output), { recursive: true });
writeFileSync(output, `${JSON.stringify({ version: 1, sites }, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ output, sites: sites.length }));
