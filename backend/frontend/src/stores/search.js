import { defineStore } from "pinia";
import { reactive, ref } from "vue";
import { normalizeWebsite, searchAPI, unwrapResponse } from "../utils/api";
import { getAccessToken, getStoredUserInfo } from "../utils/auth";

export const SEARCH_CACHE_TTL_MS = 5 * 60 * 1000;
export const SEARCH_DATA_VERSION = "site-search-v1";
export const RECENT_SEARCH_LIMIT = 10;

const SENSITIVE_QUERY_PATTERN =
  /(密码|验证码|身份证|银行卡|手机号|password|passwd|verification\s*code|access[_-]?token|refresh[_-]?token|cookie|secret)/i;

function normalizeQuery(value) {
  return String(value || "")
    .trim()
    .replace(/\s+/g, " ");
}

function normalizeParams(params = {}) {
  return {
    q: normalizeQuery(params.q),
    category: normalizeQuery(params.category),
    page: Math.max(Number.parseInt(params.page, 10) || 1, 1),
    page_size: Math.min(
      Math.max(Number.parseInt(params.page_size, 10) || 20, 1),
      50,
    ),
    sort: normalizeQuery(params.sort) || "relevance",
  };
}

function cacheKey(params, dataVersion) {
  return JSON.stringify([
    params.q.toLocaleLowerCase(),
    params.category.toLocaleLowerCase(),
    params.page,
    params.page_size,
    params.sort,
    dataVersion,
  ]);
}

function normalizePayload(response) {
  const payload = unwrapResponse(response) || {};
  const pagination = payload.pagination || {};
  return {
    ...payload,
    query: normalizeQuery(payload.query),
    items: (payload.items || []).map(normalizeWebsite),
    pagination: {
      page: Number(pagination.page || 1),
      pageSize: Number(pagination.pageSize || pagination.page_size || 20),
      total: Number(pagination.total || 0),
      totalPages: Number(pagination.totalPages || pagination.total_pages || 0),
      hasMore: Boolean(pagination.hasMore ?? pagination.has_more),
    },
  };
}

export function normalizeSearchError(error) {
  if (error?.code === "ERR_CANCELED" || error?.name === "CanceledError") {
    return { type: "canceled", message: "" };
  }
  if (error?.code === "ECONNABORTED" || /timeout/i.test(error?.message || "")) {
    return { type: "timeout", message: "搜索请求超时，请重新搜索" };
  }
  const status = Number(error?.response?.status || 0);
  if (status === 400) {
    return {
      type: "invalid",
      message: error?.response?.data?.message || "请输入有效的搜索关键词",
    };
  }
  if (status === 503) {
    return {
      type: "unavailable",
      message: "搜索服务暂时不可用，请稍后重试",
    };
  }
  if (!error?.response) {
    return { type: "network", message: "无法连接搜索服务，请检查后端状态" };
  }
  return {
    type: "unknown",
    message: error?.response?.data?.message || "搜索失败，请稍后重试",
  };
}

function recentSearchScope() {
  if (!getAccessToken()) return "guest";
  const user = getStoredUserInfo();
  const identity = user.id ?? user.user_id ?? user.username;
  return identity ? `user-${encodeURIComponent(String(identity))}` : "guest";
}

export function recentSearchStorageKey() {
  return `zhihangyu:recent-searches:${recentSearchScope()}`;
}

function readRecentSearches() {
  if (typeof localStorage === "undefined") return [];
  try {
    const value = JSON.parse(
      localStorage.getItem(recentSearchStorageKey()) || "[]",
    );
    return Array.isArray(value)
      ? value.map(normalizeQuery).filter(Boolean).slice(0, RECENT_SEARCH_LIMIT)
      : [];
  } catch {
    return [];
  }
}

function writeRecentSearches(items) {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(recentSearchStorageKey(), JSON.stringify(items));
}

export const useSearchStore = defineStore("search", () => {
  const resultsByKey = reactive({});
  const statusByKey = reactive({});
  const errorByKey = reactive({});
  const lastFetchedAtByKey = reactive({});
  const dataVersion = ref(SEARCH_DATA_VERSION);

  async function search(rawParams = {}, options = {}) {
    const params = normalizeParams(rawParams);
    const key = cacheKey(params, dataVersion.value);
    const cachedPayload = resultsByKey[key] || null;
    const cacheAge = Date.now() - Number(lastFetchedAtByKey[key] || 0);

    if (!options.force && cachedPayload && cacheAge < SEARCH_CACHE_TTL_MS) {
      statusByKey[key] = "ready";
      errorByKey[key] = null;
      return { payload: cachedPayload, fromCache: true, staleError: null };
    }

    statusByKey[key] = cachedPayload ? "refreshing" : "loading";
    errorByKey[key] = null;
    try {
      const response = await searchAPI.search(params, {
        signal: options.signal,
      });
      const payload = normalizePayload(response);
      const nextVersion = payload.dataVersion || dataVersion.value;
      dataVersion.value = nextVersion;
      const nextKey = cacheKey(params, nextVersion);
      resultsByKey[nextKey] = payload;
      lastFetchedAtByKey[nextKey] = Date.now();
      statusByKey[nextKey] = "ready";
      errorByKey[nextKey] = null;
      if (nextKey !== key) {
        delete resultsByKey[key];
        delete lastFetchedAtByKey[key];
        delete statusByKey[key];
        delete errorByKey[key];
      }
      return { payload, fromCache: false, staleError: null };
    } catch (error) {
      const normalizedError = normalizeSearchError(error);
      statusByKey[key] = normalizedError.type === "canceled" ? "idle" : "error";
      errorByKey[key] = normalizedError;
      if (normalizedError.type === "canceled") throw error;
      if (cachedPayload) {
        return {
          payload: cachedPayload,
          fromCache: true,
          staleError: normalizedError,
        };
      }
      throw Object.assign(error, { searchError: normalizedError });
    }
  }

  function addRecentSearch(value) {
    const query = normalizeQuery(value);
    if (!query || query.length > 100 || SENSITIVE_QUERY_PATTERN.test(query)) {
      return readRecentSearches();
    }
    const next = [
      query,
      ...readRecentSearches().filter(
        (item) => item.toLocaleLowerCase() !== query.toLocaleLowerCase(),
      ),
    ].slice(0, RECENT_SEARCH_LIMIT);
    writeRecentSearches(next);
    return next;
  }

  function getRecentSearches() {
    return readRecentSearches();
  }

  function removeRecentSearch(value) {
    const query = normalizeQuery(value).toLocaleLowerCase();
    const next = readRecentSearches().filter(
      (item) => item.toLocaleLowerCase() !== query,
    );
    writeRecentSearches(next);
    return next;
  }

  function clearRecentSearches() {
    writeRecentSearches([]);
    return [];
  }

  return {
    resultsByKey,
    statusByKey,
    errorByKey,
    lastFetchedAtByKey,
    dataVersion,
    search,
    addRecentSearch,
    getRecentSearches,
    removeRecentSearch,
    clearRecentSearches,
  };
});
