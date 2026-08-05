import assert from "node:assert/strict";
import {
  websiteCatalog,
  websiteCatalogCategories,
} from "../src/data/websiteCatalog.js";

assert.ok(websiteCatalog.length >= 100, "内置网站目录应至少包含 100 个资源");
assert.ok(websiteCatalogCategories.length >= 10, "内置目录应覆盖主要分类");

const urls = new Set();
const counts = new Map();
for (const website of websiteCatalog) {
  assert.ok(website.name, "网站必须有名称");
  assert.ok(/^https?:\/\//i.test(website.url), `${website.name} 缺少有效 URL`);
  assert.ok(website.category_id, `${website.name} 缺少分类 ID`);
  assert.ok(website.category_name, `${website.name} 缺少分类名称`);
  assert.ok(!urls.has(website.url), `网站 URL 重复: ${website.url}`);
  urls.add(website.url);
  counts.set(
    website.category_name,
    (counts.get(website.category_name) || 0) + 1,
  );
}

for (const category of websiteCatalogCategories) {
  assert.ok(
    (counts.get(category.name) || 0) >= 10,
    `${category.name} 应至少包含 10 个网站资源`,
  );
}

console.log(
  `内置网站目录校验通过：${websiteCatalog.length} 个网站，${counts.size} 个分类。`,
);
