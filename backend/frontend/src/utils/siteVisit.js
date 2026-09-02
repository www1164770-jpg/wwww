import {
  getSiteDescription,
  historyAPI,
  normalizeUrl,
  resolveSiteLogo,
  siteAPI,
} from "./api";
import { getAccessToken, isValidAuthToken } from "./auth";
import { getBehaviorSessionId, trackRepeatVisit } from "./behaviorTracker";

export const BROWSING_HISTORY_STORAGE_KEY = "zhihui:browsing-history:v1";
export const BROWSING_HISTORY_DEDUPE_MS = 30_000;
const MAX_LOCAL_HISTORY_ITEMS = 100;

function isBrowser() {
  return typeof window !== "undefined";
}

function safeUrl(value) {
  const normalized = normalizeUrl(value);
  if (!normalized) return "";
  try {
    const parsed = new URL(normalized);
    return ["http:", "https:"].includes(parsed.protocol) ? parsed.href : "";
  } catch {
    return "";
  }
}

function validDate(value) {
  const date = new Date(value || 0);
  return Number.isNaN(date.getTime()) ? null : date;
}

function historyKey(item = {}) {
  const url = safeUrl(item.url);
  if (url) return `url:${url.toLowerCase().replace(/\/$/, "")}`;
  const siteId = item.site_id ?? item.siteId ?? item.id;
  return siteId === undefined || siteId === null ? "" : `site:${siteId}`;
}

function normalizeHistoryItem(item = {}, fallback = {}) {
  const url = safeUrl(item.url ?? item.website_url ?? item.href ?? fallback.url);
  const rawSiteId = item.site_id ?? item.siteId ?? item.id ?? fallback.site_id;
  const siteId = /^\d+$/.test(String(rawSiteId ?? ""))
    ? Number(rawSiteId)
    : null;
  const visitedAt =
    validDate(item.visited_at ?? item.visitedAt ?? item.created_at)?.toISOString() ||
    new Date().toISOString();
  const id = item.local_id ?? item.id ?? fallback.id ?? `local:${visitedAt}`;
  const description = String(
    item.description ?? item.summary ?? item.shortDescription ?? "",
  ).trim();

  return {
    id,
    local_id: item.local_id ?? (String(id).startsWith("local:") ? id : null),
    server_id:
      item.server_id ?? (/^\d+$/.test(String(item.id ?? "")) ? Number(item.id) : null),
    site_id: siteId,
    name: String(item.name ?? item.title ?? "未命名网站").trim() || "未命名网站",
    url,
    logo_url: String(item.logo_url ?? item.logoUrl ?? item.logo ?? "").trim(),
    description: /^(?:https?:\/\/|www\.)/i.test(description) ? "" : description,
    category: String(
      item.category ?? item.category_name ?? item.categoryName ?? "",
    ).trim(),
    source: String(item.source ?? fallback.source ?? "unknown").trim() || "unknown",
    visited_at: visitedAt,
    recommendation_batch_id:
      item.recommendation_batch_id ?? item.recommendationBatchId ?? fallback.recommendation_batch_id ?? "",
    questionnaire_version:
      item.questionnaire_version ?? fallback.questionnaire_version ?? "",
    profile_version: item.profile_version ?? fallback.profile_version ?? "",
    candidate_pool_id: item.candidate_pool_id ?? fallback.candidate_pool_id ?? "",
  };
}

function sitePayload(site = {}, source = "unknown") {
  const normalized = normalizeHistoryItem(
    {
      ...site,
      site_id: site.site_id ?? site.siteId ?? site.id,
      url: site.url ?? site.website_url ?? site.href ?? site.link,
      logo_url: site.logo_url ?? site.logoUrl ?? site.logo,
      description: getSiteDescription(site),
      category:
        site.category_name ?? site.categoryName ?? site.category ?? "",
      source,
      visited_at: new Date().toISOString(),
    },
    { source },
  );
  normalized.logo_url ||= resolveSiteLogo(normalized);
  normalized.id = `local:${Date.now()}:${Math.random().toString(36).slice(2, 8)}`;
  normalized.local_id = normalized.id;
  normalized.server_id = null;
  return normalized;
}

export function readLocalBrowsingHistory() {
  if (!isBrowser()) return [];
  try {
    const parsed = JSON.parse(
      window.localStorage.getItem(BROWSING_HISTORY_STORAGE_KEY) || "[]",
    );
    return (Array.isArray(parsed) ? parsed : [])
      .map((item) => normalizeHistoryItem(item))
      .filter((item) => item.url)
      .sort(
        (left, right) =>
          new Date(right.visited_at).getTime() -
          new Date(left.visited_at).getTime(),
      );
  } catch {
    return [];
  }
}

function writeLocalBrowsingHistory(items) {
  if (!isBrowser()) return;
  window.localStorage.setItem(
    BROWSING_HISTORY_STORAGE_KEY,
    JSON.stringify(items.slice(0, MAX_LOCAL_HISTORY_ITEMS)),
  );
  window.dispatchEvent(new CustomEvent("browsing-history-changed"));
}

function saveLocalBrowsingHistory(item) {
  const items = readLocalBrowsingHistory();
  const key = historyKey(item);
  const duplicateIndex = items.findIndex(
    (current) =>
      historyKey(current) === key &&
      new Date(item.visited_at).getTime() -
        new Date(current.visited_at).getTime() <
        BROWSING_HISTORY_DEDUPE_MS,
  );
  if (duplicateIndex >= 0) {
    const previous = items.splice(duplicateIndex, 1)[0];
    item.local_id = previous.local_id || previous.id;
    item.id = item.local_id;
    item.server_id = previous.server_id || null;
  }
  writeLocalBrowsingHistory([item, ...items]);
  return item;
}

function hasAuthenticatedSession() {
  return isValidAuthToken(getAccessToken());
}

export function recordBrowsingHistory(site, options = {}) {
  const item = sitePayload(site, options.source);
  if (!item.url) return Promise.resolve(null);
  saveLocalBrowsingHistory(item);

  if (import.meta.env.DEV) {
    console.debug("[BrowsingHistory] visit", {
      site_id: item.site_id,
      name: item.name,
      url: item.url,
      source: item.source,
    });
  }

  if (item.site_id && !site.external_only) {
    void siteAPI.recordClick(item.site_id, {
      source: item.source === "career_recommend" || item.source === "home_recommend"
        ? "personalized_recommendation"
        : item.source,
      recommendation_batch_id: item.recommendation_batch_id,
      questionnaire_version: item.questionnaire_version,
      profile_version: item.profile_version,
      session_id: options.session_id || getBehaviorSessionId(),
      metadata: { candidate_pool_id: item.candidate_pool_id },
    }).catch((error) => {
      if (import.meta.env.DEV) {
        console.warn("[BrowsingHistory] click count update failed", error?.message || error);
      }
    });
  }

  if (!hasAuthenticatedSession()) return Promise.resolve(item);
  const payload = {
    site_id: item.site_id,
    name: item.name,
    url: item.url,
    logo_url: item.logo_url,
    description: item.description,
    category: item.category,
    source: item.source,
    visited_at: item.visited_at,
    recommendation_batch_id: item.recommendation_batch_id,
    questionnaire_version: item.questionnaire_version,
    profile_version: item.profile_version,
    session_id: options.session_id || getBehaviorSessionId(),
    candidate_pool_id: item.candidate_pool_id,
  };
  if (import.meta.env.DEV) {
    console.debug("[BrowsingHistory] save request", {
      site_id: payload.site_id,
      source: payload.source,
    });
  }
  return historyAPI
    .recordHistory(payload)
    .then((response) => {
      if (import.meta.env.DEV) {
        console.debug("[BrowsingHistory] save response", response.status);
      }
      return response;
    })
    .catch((error) => {
      console.warn(
        "[BrowsingHistory] 保存失败，本地记录已保留",
        error?.response?.data?.msg || error?.message || error,
      );
      return item;
    });
}

export function visitSite(site, options = {}) {
  const url = safeUrl(site?.url ?? site?.website_url ?? site?.href ?? site?.link);
  if (!url) return false;
  const target = options.target || "_blank";
  const nativeLink = Boolean(options.event?.currentTarget?.href);
  let openedWindow = null;

  if (!nativeLink && target === "_blank" && isBrowser()) {
    openedWindow = window.open(url, "_blank", "noopener,noreferrer");
  }

  void recordBrowsingHistory({ ...site, url }, options).then(() =>
    trackRepeatVisit(site, options),
  );

  if (!nativeLink && target !== "_blank" && isBrowser()) {
    window.location.assign(url);
  } else if (!nativeLink && target === "_blank" && !openedWindow && isBrowser()) {
    window.open(url, "_blank", "noopener,noreferrer");
  }
  return true;
}

function mergeHistoryItems(localItems, serverItems) {
  const merged = new Map();
  [...serverItems, ...localItems].forEach((rawItem) => {
    const item = normalizeHistoryItem(rawItem);
    const key = historyKey(item);
    if (!key || !item.url) return;
    const previous = merged.get(key);
    if (!previous) {
      merged.set(key, item);
      return;
    }
    const newest =
      new Date(item.visited_at).getTime() > new Date(previous.visited_at).getTime()
        ? item
        : previous;
    merged.set(key, {
      ...previous,
      ...item,
      ...newest,
      local_id: previous.local_id || item.local_id || null,
      server_id: previous.server_id || item.server_id || null,
    });
  });
  return [...merged.values()].sort(
    (left, right) =>
      new Date(right.visited_at).getTime() -
      new Date(left.visited_at).getTime(),
  );
}

export async function loadBrowsingHistory() {
  const localItems = readLocalBrowsingHistory();
  if (!hasAuthenticatedSession()) {
    return { items: localItems, total: localItems.length, syncError: null };
  }
  try {
    const result = await historyAPI.getHistory();
    const items = mergeHistoryItems(localItems, result.items);
    if (import.meta.env.DEV) {
      console.debug("[BrowsingHistory] loaded", { count: items.length });
    }
    return { items, total: items.length, syncError: null };
  } catch (error) {
    if (!localItems.length) throw error;
    return { items: localItems, total: localItems.length, syncError: error };
  }
}

export async function deleteBrowsingHistory(item) {
  const key = historyKey(item);
  writeLocalBrowsingHistory(
    readLocalBrowsingHistory().filter((entry) => historyKey(entry) !== key),
  );
  const serverId = item?.server_id ?? (/^\d+$/.test(String(item?.id)) ? item.id : null);
  if (hasAuthenticatedSession() && serverId) {
    await historyAPI.deleteHistory(serverId);
  }
}

export async function clearBrowsingHistory() {
  writeLocalBrowsingHistory([]);
  if (hasAuthenticatedSession()) await historyAPI.clearHistory();
}
