import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (relativePath) =>
  readFileSync(resolve(root, relativePath), "utf8");
const visibleFiles = [
  "index.html",
  "public/manifest.webmanifest",
  "src/components/layout/AppHeader.vue",
  "src/components/layout/AppFooter.vue",
  "src/components/ai/AiSiteAssistant.vue",
  "src/views/Home.vue",
  "src/views/Login.vue",
  "src/views/Register.vue",
  "../../README.md",
  "README.md",
];
const visibleText = visibleFiles
  .map(read)
  .join("\n")
  .replace(/vocanav-logo\.png/giu, "")
  .replace(/zhihui/giu, "");
const oldBrands = [
  ["Voca", "Nav"].join(""),
  ["Voca", " ", "Nav"].join(""),
  ["Zhi", "hui", " Navigation"].join(""),
  ["Zhi", "hui"].join(""),
  ["zhi", "hui", "-navigation"].join(""),
  ["Zhi", "hangyu", " Navigation"].join(""),
  ["Zhi", "hangyu"].join(""),
  ["Zhi", "Hang", "Yu"].join(""),
  ["Zhi", "hangyu", " AI"].join(""),
  ["Voca", "Nav AI"].join(""),
  ["Zhi", "hui AI"].join(""),
];
const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\\]\\]/g, "\\$&");
const oldBrandPattern = new RegExp(oldBrands.map(escapeRegExp).join("|"), "iu");

assert.match(
  read("index.html"),
  /<title>知航屿｜智能网站导航与资源推荐平台<\/title>/u,
);
assert.match(read("index.html"), /name="description"[\s\S]*知航屿/u);
assert.match(read("public/manifest.webmanifest"), /"name":\s*"知航屿"/u);
assert.match(read("public/manifest.webmanifest"), /"short_name":\s*"知航屿"/u);
assert.match(
  read("src/components/layout/AppHeader.vue"),
  /<span class="brand-name">知航屿<\/span>/u,
);
assert.match(read("src/components/layout/AppHeader.vue"), /知航AI/u);
assert.match(read("src/components/layout/AppFooter.vue"), /知航屿/u);
assert.match(read("src/components/ai/AiSiteAssistant.vue"), /知航AI/u);
assert.match(read("src/views/Home.vue"), /知航AI/u);
assert.match(read("src/views/Login.vue"), /知航屿/u);
assert.match(read("src/views/Register.vue"), /知航屿/u);
assert.doesNotMatch(visibleText, oldBrandPattern);

console.log("brand naming verification passed");
