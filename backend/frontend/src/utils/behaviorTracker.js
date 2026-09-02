import { api } from "./api";
import { getAccessToken, isValidAuthToken } from "./auth";

export const BEHAVIOR_SESSION_STORAGE_KEY = "zhihangyu_behavior_session_id";
const IMPRESSION_DEDUPE_KEY = "zhihangyu:behavior:impressions:v1";

function browser() {
  return typeof window !== "undefined";
}

export function getBehaviorSessionId() {
  if (!browser()) return "";
  try {
    let value = window.sessionStorage.getItem(BEHAVIOR_SESSION_STORAGE_KEY);
    if (!value) {
      value = `sess_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
      window.sessionStorage.setItem(BEHAVIOR_SESSION_STORAGE_KEY, value);
    }
    return value;
  } catch {
    return "";
  }
}

function siteId(site) {
  const value = site?.website_id ?? site?.site_id ?? site?.siteId ?? site?.id;
  return /^\d+$/.test(String(value ?? "").trim()) ? Number(value) : null;
}

function context(site = {}, options = {}) {
  const rawSource = options.source || site.visit_source || "other";
  const source = rawSource === "career_recommend" || rawSource === "home_recommend"
    ? "personalized_recommendation"
    : rawSource;
  return {
    website_id: siteId(site) ?? options.website_id,
    source,
    recommendation_batch_id:
      options.recommendation_batch_id || site.recommendation_batch_id || "",
    questionnaire_version:
      options.questionnaire_version || site.questionnaire_version || "",
    profile_version: options.profile_version || site.profile_version || "",
    profile_schema_version:
      options.profile_schema_version || site.profile_schema_version || options.profile_version || site.profile_version || "",
    session_id: options.session_id || getBehaviorSessionId(),
    metadata: {
      ...(options.metadata || {}),
      ...(site.candidate_pool_id
        ? { candidate_pool_id: site.candidate_pool_id }
        : {}),
      ...(site.personalization_type
        ? { personalization_type: site.personalization_type }
        : {}),
      ...(site.match_score != null
        ? { match_score: site.match_score }
        : {}),
      ...(site.algorithm_version
        ? { algorithm_version: site.algorithm_version }
        : {}),
      ...(site.profile_schema_version || options.profile_schema_version
        ? { profile_schema_version: site.profile_schema_version || options.profile_schema_version }
        : {}),
    },
  };
}

function authenticated() {
  return isValidAuthToken(getAccessToken());
}

async function send(event) {
  if (!authenticated() || !event.website_id) return { recorded: false, anonymous: true };
  try {
    const response = await api.post("/behavior/events", event, {
      timeout: 2500,
      transitional: { clarifyTimeoutError: true },
    });
    return response?.data?.data || response?.data || { recorded: false };
  } catch (error) {
    console.warn("[behaviorTracker] event failed", error?.message || error);
    return { recorded: false, error: true };
  }
}

export function trackClick(site, options = {}) {
  return send({ event_type: "click", ...context(site, options) });
}

export function trackFavorite(site, options = {}) {
  return send({ event_type: "favorite", ...context(site, { ...options, source: options.source || "favorite" }) });
}

export function trackRepeatVisit(site, options = {}) {
  return send({ event_type: "repeat_visit", ...context(site, options) });
}

function readImpressionKeys() {
  if (!browser()) return new Set();
  try {
    const values = JSON.parse(window.sessionStorage.getItem(IMPRESSION_DEDUPE_KEY) || "[]");
    return new Set(Array.isArray(values) ? values : []);
  } catch {
    return new Set();
  }
}

function writeImpressionKeys(keys) {
  if (!browser()) return;
  try {
    window.sessionStorage.setItem(IMPRESSION_DEDUPE_KEY, JSON.stringify([...keys].slice(-500)));
  } catch {
    // Tracking must never block rendering.
  }
}

export async function trackImpressions(sites, options = {}) {
  const list = Array.isArray(sites) ? sites : [];
  const batchId = options.recommendation_batch_id || options.batch_id || "";
  const keys = readImpressionKeys();
  const websiteIds = list
    .map((site) => siteId(site))
    .filter(Boolean)
    .filter((id) => {
      const key = `${batchId}:${id}`;
      if (keys.has(key)) return false;
      keys.add(key);
      return true;
    });
  if (!websiteIds.length || !authenticated()) return { recorded: 0 };
  writeImpressionKeys(keys);
  const first = context(list[0] || {}, options);
  try {
    const response = await api.post("/behavior/events/batch", {
      ...first,
      event_type: "impression",
      website_ids: websiteIds,
    }, { timeout: 3000 });
    return response?.data?.data || response?.data || { recorded: 0 };
  } catch (error) {
    websiteIds.forEach((id) => keys.delete(`${batchId}:${id}`));
    writeImpressionKeys(keys);
    console.warn("[behaviorTracker] impression batch failed", error?.message || error);
    return { recorded: 0, error: true };
  }
}
