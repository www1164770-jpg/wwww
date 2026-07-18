import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const headerSource = readFileSync(
  fileURLToPath(
    new URL("../src/components/layout/AppHeader.vue", import.meta.url),
  ),
  "utf8",
);

function matchCount(pattern) {
  return [...headerSource.matchAll(pattern)].length;
}

const dropdownBlock = headerSource.match(/\.dropdown\s*\{[\s\S]*?\n\}/)?.[0];
assert.ok(dropdownBlock, "dropdown CSS block must exist");

assert.match(headerSource, /ref="userMenuRef"/);
assert.match(headerSource, /@click="toggleMenu"/);
assert.match(headerSource, /class="user-identity"/);
assert.match(headerSource, /:title="displayName"/);
assert.match(headerSource, /:title="displayEmail"/);
assert.match(
  headerSource,
  /watch\(\s*\(\) => route\.fullPath,\s*closeMenu\s*\)/,
);
assert.match(
  headerSource,
  /document\.addEventListener\("pointerdown", handlePointerDown\)/,
);
assert.match(
  headerSource,
  /!userMenuRef\.value\.contains\(event\.target\)/,
);
assert.match(headerSource, /event\.key === "Escape"/);
assert.equal(
  matchCount(/document\.addEventListener\("pointerdown", handlePointerDown\)/g),
  1,
);
assert.equal(
  matchCount(/document\.removeEventListener\("pointerdown", handlePointerDown\)/g),
  1,
);
assert.equal(
  matchCount(/document\.addEventListener\("keydown", handleKeydown\)/g),
  1,
);
assert.equal(
  matchCount(/document\.removeEventListener\("keydown", handleKeydown\)/g),
  1,
);
assert.match(
  headerSource,
  /function logout\(\)\s*\{[\s\S]*?userStore\.logout\(\);/,
);

assert.match(dropdownBlock, /position:\s*absolute;/);
assert.match(dropdownBlock, /top:\s*calc\(100% \+ 10px\);/);
assert.match(dropdownBlock, /right:\s*0;/);
assert.match(dropdownBlock, /width:\s*320px;/);
assert.match(
  dropdownBlock,
  /max-width:\s*calc\(100vw - 32px\);/,
);
assert.match(dropdownBlock, /max-height:\s*min\(520px, calc\(100vh - 96px\)\);/);
assert.match(dropdownBlock, /z-index:\s*40;/);
assert.match(dropdownBlock, /overflow-x:\s*hidden;/);
assert.match(dropdownBlock, /overflow-y:\s*auto;/);
assert.equal(
  dropdownBlock
    .split("\n")
    .some((line) => line.trim() === "width: 100%;"),
  false,
);
assert.match(
  headerSource,
  /\.user-identity strong,[\s\S]*?\.user-identity span\s*\{[\s\S]*?overflow:\s*hidden;[\s\S]*?text-overflow:\s*ellipsis;[\s\S]*?white-space:\s*nowrap;/,
);
assert.match(headerSource, /width:\s*min\(320px, calc\(100vw - 24px\)\);/);

console.log("user menu layout regression checks passed");
