import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { getCommonToolKey, dedupeCommonTools } from "../src/utils/commonToolsRotation.js";

// Exercise the actual favorite key helper without importing a browser/Pinia app.
const source = readFileSync(new URL("../src/stores/favorites.js", import.meta.url), "utf8");
const helper = source.slice(source.indexOf("function getFavoriteUrlKey("), source.indexOf("function getFavoriteKey("));
assert.ok(helper.includes("function getFavoriteUrlKey"));
const favoriteKey = new Function("normalizeUrl", `${helper}; return getFavoriteUrlKey;`)((value) => value);
for (const key of [favoriteKey, (url) => getCommonToolKey({ url })]) {
  assert.equal(key("https://EXAMPLE.test/API"), key("https://example.test/API"));
  assert.notEqual(key("https://example.test/API"), key("https://example.test/api"));
  assert.notEqual(key("https://example.test/API?q=Token"), key("https://example.test/API?q=token"));
  assert.notEqual(key("https://example.test/product-a"), key("https://example.test/product-b"));
}
assert.equal(dedupeCommonTools([
  { id: 1, url: "https://example.test/API" },
  { id: 2, url: "https://example.test/api" },
]).length, 2);
console.log("PASS domain normalization preserves path/query case and same-host products");
