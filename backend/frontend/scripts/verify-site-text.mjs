import assert from "node:assert/strict";
import { cleanSiteDescription } from "../src/utils/siteText.js";

const cases = [
  ["Vue.js", "Vue.js: 围绕 developer 提供工具", "围绕 developer 提供工具"],
  ["Canva", "  Canva：在线设计平台  ", "在线设计平台"],
  ["Redis", "Redis : 高性能键值数据库", "高性能键值数据库"],
  ["GitHub Copilot", "GitHub Copilot: AI 编程助手", "AI 编程助手"],
  ["C++", "C++ - 编程语言与开发工具", "编程语言与开发工具"],
  ["GitHub", "支持 GitHub 仓库同步和代码协作。", "支持 GitHub 仓库同步和代码协作。"],
  ["", "  保留原始简介  ", "保留原始简介"],
  ["Vue.js", "", ""],
];

for (const [name, description, expected] of cases) {
  assert.equal(cleanSiteDescription(name, description), expected, name || "empty name");
}

console.log(`siteText verification passed: ${cases.length} cases.`);
