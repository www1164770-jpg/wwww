import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { normalizeFavoriteError } from "../src/utils/favoriteError.js";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const store = read("src/stores/favorites.js");
const api = read("src/utils/api.js");
const siteDetail = read("src/views/SiteDetail.vue");
const backend = read("../v1_routes.py");
const migration = read("../sql/migrations/20260804_add_favorites_indexes.sql");

function axiosError(status, code, data = {}) {
  return {
    response: {
      status,
      data: { success: false, code, error_code: code, ...data },
    },
  };
}

const cases = [
  [401, "AUTH_REQUIRED", "请先登录后操作收藏"],
  [404, "SITE_NOT_FOUND", "该网站暂时无法收藏"],
  [409, "FAVORITE_ALREADY_EXISTS", "该网站已经收藏"],
  [422, "INVALID_SITE", "网站信息不完整，暂时无法收藏"],
  [503, "FAVORITE_DATABASE_ERROR", "收藏服务暂时不可用，请稍后重试"],
  [500, "FAVORITE_SERVER_ERROR", "收藏服务出现异常，请稍后重试"],
];

for (const [status, code, message] of cases) {
  assert.equal(
    normalizeFavoriteError(axiosError(status, code)).message,
    message,
  );
}

assert.equal(
  normalizeFavoriteError({ code: "ECONNABORTED" }).message,
  "收藏请求超时，状态已恢复",
);
assert.equal(
  normalizeFavoriteError({ code: "ERR_NETWORK" }).message,
  "无法连接收藏服务，请检查后端状态",
);
assert.equal(
  normalizeFavoriteError({
    response: { status: 500, data: { data: { code: "DATABASE_ERROR" } } },
  }).code,
  "DATABASE_ERROR",
);

assert.match(store, /getFavoriteErrorDetails/);
assert.match(store, /FAVORITE_ALREADY_EXISTS/);
assert.match(store, /FAVORITE_ALREADY_REMOVED/);
assert.match(store, /restoreStateSnapshot\(snapshot, userId\)/);
assert.match(store, /response\?\.data\?\.data \?\? response\?\.data/);
assert.doesNotMatch(
  store.match(
    /function scheduleFavoriteSync[\s\S]*?function toggleFavorite/,
  )?.[0] || "",
  /loadFavorites\(/,
);
assert.match(api, /withCredentials:\s*true/);
assert.match(api, /payload: requestConfig\.payload/);
assert.match(api, /\[Favorite sync failed\]/);
assert.match(siteDetail, /normalizeFavoriteError\(requestError\)/);
assert.match(backend, /FAVORITE_DATABASE_ERROR/);
assert.match(backend, /safe_rollback\(conn\)/);
assert.match(backend, /is_duplicate_favorite_error/);
assert.match(backend, /alreadyExists/);
assert.match(backend, /alreadyRemoved/);
assert.match(
  migration,
  /ADD UNIQUE KEY uq_favorites_user_site \(user_id, site_id\)/,
);
assert.match(migration, /GROUP_CONCAT\(column_name ORDER BY seq_in_index\)/);
assert.doesNotMatch(
  backend.match(
    /def v1_add_favorite\(site_id\)[\s\S]*?def v1_update_favorite_note/,
  )?.[0] || "",
  /record_behavior\(/,
);

console.log("favorite error contract checks passed");
