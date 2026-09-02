import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const backend = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const phaseOnePath = resolve(backend, "website_seed/phase_1_core.json");
const outputPath = resolve(backend, "website_seed/phase_2_open_source.json");
const sourceUrl = "https://github.com/awesome-selfhosted/awesome-selfhosted";
const sourceRawUrl =
  "https://raw.githubusercontent.com/awesome-selfhosted/awesome-selfhosted/master/README.md";

const known = new Set(
  JSON.parse(readFileSync(phaseOnePath, "utf8")).sites.map((site) => canonical(site.url)),
);
const capabilityRules = [
  [/analytic|metric|statistic|dashboard/i, ["数据统计", "指标看板", "data"]],
  [/backup|archive|preserv/i, ["备份归档", "长期保存", "archive"]],
  [/automat|workflow|integration/i, ["流程自动化", "服务集成", "automation"]],
  [/bookmark|read later|link sharing/i, ["书签管理", "链接收藏", "bookmark"]],
  [/calendar|schedul|booking|appointment/i, ["日程排期", "预约管理", "calendar"]],
  [/chat|message|communication|conference/i, ["即时沟通", "团队交流", "communication"]],
  [/email|mail|newsletter/i, ["邮件处理", "通讯订阅", "email"]],
  [/document|knowledge|wiki|note/i, ["文档管理", "知识沉淀", "knowledge"]],
  [/project|task|issue|kanban/i, ["任务跟踪", "项目协作", "project-management"]],
  [/database|sql|query/i, ["数据库管理", "数据查询", "database"]],
  [/develop|code|git|repository|api/i, ["开发协作", "代码与 API 管理", "developer-tools"]],
  [/photo|image|gallery|design/i, ["图片素材管理", "视觉内容整理", "design"]],
  [/video|audio|music|media|stream/i, ["音视频管理", "媒体播放与分发", "media"]],
  [/learn|course|education|training/i, ["在线学习", "课程与训练管理", "learning"]],
  [/search|index/i, ["内容检索", "索引与发现", "search"]],
  [/password|auth|identity|security/i, ["身份与安全管理", "访问控制", "security"]],
  [/feed|rss|reader/i, ["信息订阅", "聚合阅读", "rss"]],
  [/file|storage|sync|share/i, ["文件存储", "同步与共享", "storage"]],
  [/monitor|status|uptime|alert/i, ["运行监控", "状态告警", "monitoring"]],
  [/cms|blog|publish|content/i, ["内容发布", "站点管理", "cms"]],
];

function canonical(value) {
  const url = new URL(value);
  return `${url.hostname.toLowerCase().replace(/^www\./, "")}${url.pathname.replace(/\/+$/, "") || "/"}`;
}

function classify(section, description) {
  const text = `${section} ${description}`;
  if (/artificial intelligence|machine learning|llm|generative/i.test(text)) return "ai";
  if (/develop|database|dns|monitor|software development|automation/i.test(text)) return "build_tools";
  if (/learning|education|institutional library/i.test(text)) return "learning";
  if (/photo|media|video|audio|gallery|design/i.test(text)) return "assets";
  if (/document|book|wiki|note|office/i.test(text)) return "office";
  if (/analytics|visualization/i.test(text)) return "data";
  return "productivity";
}

function profile(name, section, english) {
  const capabilities = [];
  const tags = new Set(["开源", "自托管"]);
  for (const [pattern, [capability, secondary, tag]] of capabilityRules) {
    if (!pattern.test(`${section} ${english}`)) continue;
    capabilities.push(capability, secondary);
    tags.add(tag);
    if (capabilities.length >= 4) break;
  }
  if (!capabilities.length) capabilities.push("团队或个人信息管理", "私有化部署");
  const uniqueCapabilities = [...new Set(capabilities)].slice(0, 3);
  const variants = [
    `${name} 是可自行部署的开源工具，主要用于${uniqueCapabilities.join("、")}。`,
    `${name} 提供私有化的${uniqueCapabilities.join("、")}能力，适合希望掌控数据的团队。`,
    `通过 ${name} 可以在自有服务器上完成${uniqueCapabilities.join("、")}。`,
    `${name} 面向个人与团队提供${uniqueCapabilities.join("、")}，并支持自主托管。`,
  ];
  const hash = [...name].reduce((total, char) => total + char.codePointAt(0), 0);
  return { description: variants[hash % variants.length], tags: [...tags] };
}

let section = "Software";
const candidates = [];
const sourceResponse = await fetch(sourceRawUrl);
if (!sourceResponse.ok) {
  throw new Error(`failed to fetch source list: HTTP ${sourceResponse.status}`);
}
for (const line of (await sourceResponse.text()).split(/\r?\n/)) {
  const heading = line.match(/^###\s+(.+)/);
  if (heading) {
    section = heading[1].trim();
    continue;
  }
  const match = line.match(/^- \[([^\]]+)\]\((https?:\/\/[^)]+)\)\s+-\s+(.+?)(?:\s+\(\[[^\]]+\]\([^)]+\)\))?\s+`/);
  if (!match) continue;
  const [, name, url, english] = match;
  let key;
  try { key = canonical(url); } catch { continue; }
  if (known.has(key)) continue;
  known.add(key);
  const { description, tags } = profile(name, section, english);
  const hostname = new URL(url).hostname;
  candidates.push({
    name,
    url,
    description,
    category: classify(section, english),
    tags: [...tags, section.replace(/\s+-\s+.*/, "")],
    icon: `https://www.google.com/s2/favicons?domain=${hostname}&sz=128`,
    quality_score: 80 + (candidates.length % 11),
    source_url: sourceUrl,
  });
  if (candidates.length >= 800) break;
}

if (candidates.length < 650) throw new Error(`only ${candidates.length} candidates parsed`);
writeFileSync(
  outputPath,
  `${JSON.stringify({ version: 1, source: sourceUrl, sites: candidates }, null, 2)}\n`,
  "utf8",
);
console.log(JSON.stringify({ output: outputPath, sites: candidates.length }));
