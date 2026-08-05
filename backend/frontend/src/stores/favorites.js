import { computed, onScopeDispose, ref } from "vue";
import { defineStore } from "pinia";
import { favoriteAPI, normalizeUrl, normalizeWebsite } from "../utils/api";
import { addAuthStateListener } from "../utils/auth";
import {
  getFavoriteErrorDetails,
  normalizeFavoriteError as normalizeFavoriteErrorMessage,
} from "../utils/favoriteError";
import { normalizeSite } from "../utils/normalizeSite";
import { useUserStore } from "./user";

export { getFavoriteErrorDetails } from "../utils/favoriteError";

export const FAVORITE_CACHE_KEY_PREFIX = "zhihangyu:favorites:";
export const FAVORITE_CACHE_TTL_MS = 5 * 60_000;
export const FAVORITE_CACHE_VERSION = 1;
export const FAVORITE_STATE_CHANGED_EVENT = "favorite-state-changed";

function getFavoriteUserId(userStore) {
  if (!userStore.isLoggedIn) return "";
  const user = userStore.userInfo || {};
  const value = user.id ?? user.user_id;
  return value === undefined || value === null ? "" : String(value).trim();
}

function getSiteId(site = {}) {
  const value =
    site && typeof site === "object" ? normalizeSite(site).siteId : site;
  const normalized = value === undefined || value === null ? "" : String(value).trim();
  return /^\d+$/.test(normalized) ? normalized : "";
}

function getFavoriteName(site = {}) {
  return String(normalizeSite(site).name || "").trim();
}

function getFavoriteUrl(site = {}) {
  return String(normalizeSite(site).url || "").trim();
}

function getFavoriteUrlKey(url) {
  const normalized = normalizeUrl(url).trim();
  if (!normalized) return "";

  try {
    const parsed = new URL(normalized);
    parsed.hash = "";
    const hostname = parsed.hostname.toLowerCase().replace(/^www\./, "");
    const port = parsed.port ? `:${parsed.port}` : "";
    const pathname = parsed.pathname.replace(/\/$/, "") || "/";
    return `${hostname}${port}${pathname}${parsed.search}`.toLowerCase();
  } catch {
    return normalized.replace(/\/$/, "").toLowerCase();
  }
}

function getFavoriteKey(site = {}) {
  const siteId = getSiteId(site);
  if (siteId) return `id:${siteId}`;
  const urlKey = getFavoriteUrlKey(getFavoriteUrl(site));
  return urlKey ? `url:${urlKey}` : "";
}

function matchesFavorite(left, right) {
  const leftId = getSiteId(left);
  const rightId = getSiteId(right);
  if (leftId && rightId && leftId === rightId) return true;
  const leftUrl = getFavoriteUrlKey(getFavoriteUrl(left));
  const rightUrl = getFavoriteUrlKey(getFavoriteUrl(right));
  return Boolean(leftUrl && rightUrl && leftUrl === rightUrl);
}

export function getFavoriteCacheKey(userId) {
  return `${FAVORITE_CACHE_KEY_PREFIX}${String(userId).trim()}`;
}

export function normalizeFavorite(site = {}) {
  const normalizedSite = normalizeSite(site);
  const siteId = normalizedSite.siteId || "";
  const name = getFavoriteName(normalizedSite);
  const url = getFavoriteUrl(normalizedSite);
  const favoriteKey = getFavoriteKey(normalizedSite);
  if (!favoriteKey || !name || !url) return null;

  const normalized = normalizeWebsite({
    ...site,
    id: siteId,
    name: normalizedSite.name,
    url: normalizedSite.url,
    logo_url: normalizedSite.logoUrl,
    summary: normalizedSite.summary,
    category_name: normalizedSite.categoryName,
  });
  const categoryName =
    site.categoryName ?? site.category_name ?? normalized.category_name ?? "";

  return {
    ...normalized,
    id: siteId || favoriteKey,
    siteId: siteId || "",
    name,
    url,
    favoriteId: site.favoriteId ?? site.favorite_id ?? "",
    logoUrl: normalizedSite.logoUrl || normalized.logo_url || "",
    categoryName,
    category_name: categoryName,
    favoritedAt: site.favoritedAt ?? site.favorited_at ?? site.created_at ?? "",
    updatedAt: site.updatedAt ?? site.updated_at ?? "",
    is_favorited: true,
  };
}

export function normalizeFavorites(items = []) {
  const seenFavoriteKeys = new Set();
  const seenUrls = new Set();

  return (Array.isArray(items) ? items : [])
    .map(normalizeFavorite)
    .filter((site) => {
      if (!site) return false;
      const favoriteKey = getFavoriteKey(site);
      const urlKey = getFavoriteUrlKey(site.url);
      if (
        !favoriteKey ||
        !urlKey ||
        seenFavoriteKeys.has(favoriteKey) ||
        seenUrls.has(urlKey)
      ) {
        return false;
      }
      seenFavoriteKeys.add(favoriteKey);
      seenUrls.add(urlKey);
      return true;
    });
}

export const normalizeFavoriteError = normalizeFavoriteErrorMessage;

export const useFavoritesStore = defineStore("favorites", () => {
  const userStore = useUserStore();
  const items = ref([]);
  const status = ref("idle");
  const error = ref(null);
  const loadedUserId = ref("");
  const activeUserId = ref("");
  const lastFetchedAt = ref(0);
  const cacheRestored = ref(false);
  const hasSnapshot = ref(false);
  const favoriteCount = ref(0);
  const pendingKeys = ref(new Set());
  const pendingActions = ref(new Map());
  const favoritePendingIds = computed(() => Array.from(pendingKeys.value));

  let loadPromise = null;
  let loadPromiseUserId = "";
  const desiredStateByKey = new Map();
  const confirmedStateByKey = new Map();
  const syncPromiseByKey = new Map();

  const cacheKey = getFavoriteCacheKey;

  const favoriteKeySet = computed(
    () =>
      new Set(
        items.value
          .map((site) => getFavoriteKey(site))
          .filter(Boolean),
      ),
  );

  function beginPending(favoriteKey, action, site) {
    if (!favoriteKey || pendingKeys.value.has(favoriteKey)) return false;
    pendingKeys.value = new Set(pendingKeys.value).add(favoriteKey);
    pendingActions.value = new Map(pendingActions.value).set(favoriteKey, {
      action,
      site,
    });
    return true;
  }

  function endPending(favoriteKey) {
    const nextKeys = new Set(pendingKeys.value);
    nextKeys.delete(favoriteKey);
    pendingKeys.value = nextKeys;
    const nextActions = new Map(pendingActions.value);
    nextActions.delete(favoriteKey);
    pendingActions.value = nextActions;
  }

  function captureStateSnapshot(userId) {
    let cacheValue = null;
    if (typeof localStorage !== "undefined" && userId) {
      try {
        cacheValue = localStorage.getItem(cacheKey(userId));
      } catch {
        cacheValue = null;
      }
    }
    return {
      items: items.value.slice(),
      status: status.value,
      error: error.value,
      loadedUserId: loadedUserId.value,
      activeUserId: activeUserId.value,
      lastFetchedAt: lastFetchedAt.value,
      cacheRestored: cacheRestored.value,
      hasSnapshot: hasSnapshot.value,
      favoriteCount: favoriteCount.value,
      cacheValue,
    };
  }

  function restoreStateSnapshot(snapshot, userId) {
    items.value = snapshot.items;
    status.value = snapshot.status;
    error.value = snapshot.error;
    loadedUserId.value = snapshot.loadedUserId;
    activeUserId.value = snapshot.activeUserId;
    lastFetchedAt.value = snapshot.lastFetchedAt;
    cacheRestored.value = snapshot.cacheRestored;
    hasSnapshot.value = snapshot.hasSnapshot;
    favoriteCount.value = snapshot.favoriteCount;
    if (typeof localStorage === "undefined" || !userId) return;
    try {
      if (snapshot.cacheValue === null) localStorage.removeItem(cacheKey(userId));
      else localStorage.setItem(cacheKey(userId), snapshot.cacheValue);
    } catch {
      // A storage failure must never block rollback.
    }
  }

  function getPendingAction(site) {
    const favoriteKey = getFavoriteKey(site);
    const directAction = pendingActions.value.get(favoriteKey);
    if (directAction) return directAction.action;

    for (const pendingAction of pendingActions.value.values()) {
      if (matchesFavorite(pendingAction.site, site)) {
        return pendingAction.action;
      }
    }
    return "";
  }

  function reconcileFavoriteResponse(site, response) {
    const payload = response?.data?.data ?? response?.data ?? {};
    const serverFavorite = payload?.favorite || payload?.item;
    const responseSiteId =
      serverFavorite?.siteId ??
      serverFavorite?.site_id ??
      payload?.siteId ??
      payload?.site_id;
    const normalized = normalizeFavorite({
      ...site,
      ...(serverFavorite && typeof serverFavorite === "object"
        ? serverFavorite
        : {}),
      ...(responseSiteId === undefined || responseSiteId === null
        ? {}
        : { id: responseSiteId, siteId: responseSiteId }),
      optimistic: false,
    });
    if (!normalized) return;
    const index = items.value.findIndex(
      (item) => matchesFavorite(item, site) || matchesFavorite(item, normalized),
    );
    if (index < 0) return;
    const nextItems = items.value.slice();
    nextItems[index] = {
      ...nextItems[index],
      ...normalized,
      optimistic: false,
    };
    items.value = nextItems;
  }

  function readCache(userId) {
    if (typeof localStorage === "undefined" || !userId) return null;

    try {
      const raw = localStorage.getItem(cacheKey(userId));
      if (!raw) return null;
      const cached = JSON.parse(raw);
      if (
        cached?.version !== FAVORITE_CACHE_VERSION ||
        String(cached.userId) !== String(userId) ||
        !Array.isArray(cached.items)
      ) {
        localStorage.removeItem(cacheKey(userId));
        return null;
      }
      return cached;
    } catch {
      try {
        localStorage.removeItem(cacheKey(userId));
      } catch {
        // A storage failure must never block the live request.
      }
      return null;
    }
  }

  function persistCache(userId = activeUserId.value) {
    if (typeof localStorage === "undefined" || !userId) return;

    const savedAt = Date.now();
    const cachedItems = items.value.map((site) => ({
      favoriteId: site.favoriteId || site.favorite_id || "",
      siteId: site.siteId || site.id,
      name: site.name,
      url: site.url,
      logoUrl: site.logoUrl || site.logo_url || "",
      summary: site.summary || site.description || "",
      categoryName: site.categoryName || site.category_name || "",
      favoritedAt: site.favoritedAt || "",
    }));

    try {
      localStorage.setItem(
        cacheKey(userId),
        JSON.stringify({
          version: FAVORITE_CACHE_VERSION,
          userId,
          items: cachedItems,
          savedAt,
        }),
      );
      loadedUserId.value = userId;
      activeUserId.value = userId;
      lastFetchedAt.value = savedAt;
      cacheRestored.value = true;
      hasSnapshot.value = true;
    } catch {
      // Cache failures must never block the live request or UI updates.
    }
  }

  function restoreFavoriteCache(userId) {
    const scopedUserId = String(userId ?? "").trim();
    cacheRestored.value = false;
    if (!scopedUserId) return false;

    activeUserId.value = scopedUserId;
    status.value = "restoring";
    const cached = readCache(scopedUserId);
    if (!cached) {
      cacheRestored.value = true;
      status.value = "idle";
      return false;
    }

    items.value = normalizeFavorites(cached.items);
    favoriteCount.value = items.value.length;
    loadedUserId.value = scopedUserId;
    lastFetchedAt.value = Number(cached.savedAt) || 0;
    cacheRestored.value = true;
    hasSnapshot.value = true;
    error.value = null;
    status.value = items.value.length ? "ready" : "empty";
    return true;
  }

  function clearFavoriteState() {
    items.value = [];
    status.value = "idle";
    error.value = null;
    loadedUserId.value = "";
    activeUserId.value = "";
    lastFetchedAt.value = 0;
    hasSnapshot.value = false;
    cacheRestored.value = false;
    favoriteCount.value = 0;
    pendingKeys.value = new Set();
    pendingActions.value = new Map();
    desiredStateByKey.clear();
    confirmedStateByKey.clear();
    syncPromiseByKey.clear();
    loadPromise = null;
    loadPromiseUserId = "";
  }

  function syncUserScope() {
    const nextUserId = getFavoriteUserId(userStore);
    if (nextUserId === activeUserId.value) {
      if (nextUserId && !cacheRestored.value) restoreFavoriteCache(nextUserId);
      return nextUserId;
    }

    items.value = [];
    status.value = "idle";
    error.value = null;
    loadedUserId.value = "";
    lastFetchedAt.value = 0;
    cacheRestored.value = false;
    hasSnapshot.value = false;
    favoriteCount.value = 0;
    pendingKeys.value = new Set();
    pendingActions.value = new Map();
    desiredStateByKey.clear();
    confirmedStateByKey.clear();
    syncPromiseByKey.clear();
    activeUserId.value = nextUserId;

    if (nextUserId) restoreFavoriteCache(nextUserId);
    return nextUserId;
  }

  async function loadFavorites(options = {}) {
    await userStore.ensureHydrated?.();
    const {
      force = false,
      keepExistingData = true,
      background = false,
    } = options;
    const userId = syncUserScope();

    if (!userId) {
      clearFavoriteState();
      return [];
    }

    const cacheIsFresh =
      !force &&
      loadedUserId.value === userId &&
      cacheRestored.value &&
      hasSnapshot.value &&
      Date.now() - lastFetchedAt.value < FAVORITE_CACHE_TTL_MS;
    if (cacheIsFresh) return items.value;

    if (loadPromise && loadPromiseUserId === userId) return loadPromise;

    status.value = background && hasSnapshot.value ? "refreshing" : "loading";
    error.value = null;
    const requestUserId = userId;
    const requestPromise = favoriteAPI
      .getFavorites({ timeout: 10_000 })
      .then((response) => {
        if (getFavoriteUserId(userStore) !== requestUserId) return items.value;

        const payload = response?.data?.data ?? response?.data ?? [];
        const rawItems = Array.isArray(payload)
          ? payload
          : payload?.items || payload?.favorites || [];
        const serverItems = normalizeFavorites(rawItems);
        const nextItems = normalizeFavorites([
          ...serverItems.filter(
            (item) => getPendingAction(item) !== "remove",
          ),
          ...items.value.filter(
            (item) => getPendingAction(item) === "add",
          ),
        ]);
        items.value = nextItems;
        favoriteCount.value = nextItems.length;
        loadedUserId.value = requestUserId;
        activeUserId.value = requestUserId;
        lastFetchedAt.value = Date.now();
        hasSnapshot.value = true;
        error.value = null;
        status.value = nextItems.length ? "ready" : "empty";
        persistCache(requestUserId);
        return nextItems;
      })
      .catch((requestError) => {
        if (getFavoriteUserId(userStore) !== requestUserId) return items.value;

        error.value = normalizeFavoriteError(requestError);
        if (keepExistingData && hasSnapshot.value) {
          status.value = items.value.length ? "ready" : "empty";
        } else {
          status.value = "error";
        }
        return items.value;
      })
      .finally(() => {
        if (loadPromise === requestPromise) {
          loadPromise = null;
          loadPromiseUserId = "";
        }
      });

    loadPromise = requestPromise;
    loadPromiseUserId = requestUserId;
    return requestPromise;
  }

  async function addFavorite(site, note = "") {
    const userId = syncUserScope();
    const favoriteKey = getFavoriteKey(site);
    const normalized = normalizeFavorite(site);
    if (
      !userId ||
      !favoriteKey ||
      !normalized
    )
      return false;

    const snapshot = captureStateSnapshot(userId);
    if (!beginPending(favoriteKey, "add", normalized)) return false;
    if (!items.value.some((item) => matchesFavorite(item, normalized))) {
      items.value = [...items.value, { ...normalized, optimistic: true }];
    }
    favoriteCount.value = items.value.length;
    hasSnapshot.value = true;
    loadedUserId.value = userId;
    activeUserId.value = userId;
    status.value = "ready";
    error.value = null;
    persistCache(userId);

    try {
      const response = await favoriteAPI.addFavorite(site, note);
      reconcileFavoriteResponse(site, response);
      persistCache(userId);
      return true;
    } catch (requestError) {
      if (isAlreadyDesiredFavoriteState(requestError, true)) {
        reconcileFavoriteResponse(site, requestError.response);
        persistCache(userId);
        return true;
      }
      restoreStateSnapshot(snapshot, userId);
      throw requestError;
    } finally {
      endPending(favoriteKey);
    }
  }

  async function removeFavorite(site) {
    const userId = syncUserScope();
    const favoriteKey = getFavoriteKey(site);
    if (!userId || !favoriteKey) {
      return false;
    }

    const snapshot = captureStateSnapshot(userId);
    if (!beginPending(favoriteKey, "remove", site)) return false;
    items.value = items.value.filter((item) => !matchesFavorite(item, site));
    favoriteCount.value = items.value.length;
    status.value = items.value.length ? "ready" : "empty";
    persistCache(userId);

    try {
      const response = await favoriteAPI.removeFavorite(site);
      reconcileFavoriteResponse(site, response);
      persistCache(userId);
      return true;
    } catch (requestError) {
      if (isAlreadyDesiredFavoriteState(requestError, false)) {
        persistCache(userId);
        return true;
      }
      restoreStateSnapshot(snapshot, userId);
      throw requestError;
    } finally {
      endPending(favoriteKey);
    }
  }

  function isFavorite(site) {
    const favoriteKey = getFavoriteKey(site);
    if (!favoriteKey) return false;
    if (favoriteKeySet.value.has(favoriteKey)) return true;
    if (items.value.some((item) => matchesFavorite(item, site))) return true;
    return !hasSnapshot.value && Boolean(site?.is_favorited);
  }

  function isPending(site) {
    const favoriteKey = getFavoriteKey(site);
    return Boolean(
      favoriteKey &&
        (pendingKeys.value.has(favoriteKey) || getPendingAction(site)),
    );
  }

  function persistFavoriteCacheSoon(userId) {
    const persist = () => persistCache(userId);
    if (typeof queueMicrotask === "function") queueMicrotask(persist);
    else Promise.resolve().then(persist);
  }

  function applyFavoriteStateLocally(site, favorited, userId) {
    const normalized = normalizeFavorite(site);
    const favoriteKey = getFavoriteKey(normalized || site);
    if (!normalized || !favoriteKey || !userId) return false;

    if (favorited) {
      if (!favoriteKeySet.value.has(favoriteKey)) {
        items.value = [...items.value, { ...normalized, optimistic: true }];
      }
    } else {
      items.value = items.value.filter(
        (item) => !matchesFavorite(item, normalized),
      );
    }
    favoriteCount.value = items.value.length;
    hasSnapshot.value = true;
    loadedUserId.value = userId;
    activeUserId.value = userId;
    status.value = items.value.length ? "ready" : "empty";
    error.value = null;
    persistFavoriteCacheSoon(userId);
    return true;
  }

  function isAlreadyDesiredFavoriteState(requestError, desiredState) {
    const status = requestError?.response?.status;
    const { code } = getFavoriteErrorDetails(requestError);
    if (desiredState) {
      return status === 409 || code === "FAVORITE_ALREADY_EXISTS";
    }
    return (
      code === "FAVORITE_ALREADY_REMOVED" ||
      code === "ALREADY_REMOVED" ||
      (status === 404 && !["SITE_NOT_FOUND", "INVALID_SITE"].includes(code))
    );
  }

  function scheduleFavoriteSync(site, favoriteKey, note, userId) {
    const existingPromise = syncPromiseByKey.get(favoriteKey);
    if (existingPromise) return existingPromise;

    const syncPromise = (async () => {
      let failure = null;
      while (desiredStateByKey.has(favoriteKey)) {
        const desiredState = desiredStateByKey.get(favoriteKey);
        try {
          const response = desiredState
            ? await favoriteAPI.addFavorite(site, note)
            : await favoriteAPI.removeFavorite(site);
          confirmedStateByKey.set(favoriteKey, desiredState);
          if (desiredState) reconcileFavoriteResponse(site, response);
          persistFavoriteCacheSoon(userId);
        } catch (requestError) {
          const alreadyInDesiredState = isAlreadyDesiredFavoriteState(
            requestError,
            desiredState,
          );
          if (alreadyInDesiredState) {
            confirmedStateByKey.set(favoriteKey, desiredState);
            persistFavoriteCacheSoon(userId);
          } else if (desiredStateByKey.get(favoriteKey) === desiredState) {
            failure = requestError;
            applyFavoriteStateLocally(
              site,
              confirmedStateByKey.get(favoriteKey),
              userId,
            );
            break;
          }
        }

        if (desiredStateByKey.get(favoriteKey) === desiredState) break;
      }
      if (failure) throw failure;
      return true;
    })().finally(() => {
      if (syncPromiseByKey.get(favoriteKey) === syncPromise) {
        syncPromiseByKey.delete(favoriteKey);
        desiredStateByKey.delete(favoriteKey);
        confirmedStateByKey.delete(favoriteKey);
        endPending(favoriteKey);
      }
    });

    syncPromiseByKey.set(favoriteKey, syncPromise);
    return syncPromise;
  }

  async function toggleFavorite(site, note = "") {
    const userId = syncUserScope();
    const normalized = normalizeFavorite(site);
    const favoriteKey = getFavoriteKey(normalized || site);
    if (!userId || !normalized || !favoriteKey) return false;

    const currentState = isFavorite(normalized);
    const desiredState = !currentState;
    if (!confirmedStateByKey.has(favoriteKey)) {
      confirmedStateByKey.set(favoriteKey, currentState);
    }
    desiredStateByKey.set(favoriteKey, desiredState);
    if (!pendingKeys.value.has(favoriteKey)) {
      beginPending(
        favoriteKey,
        desiredState ? "add" : "remove",
        normalized,
      );
    } else {
      const nextActions = new Map(pendingActions.value);
      nextActions.set(favoriteKey, {
        action: desiredState ? "add" : "remove",
        site: normalized,
      });
      pendingActions.value = nextActions;
    }

    applyFavoriteStateLocally(normalized, desiredState, userId);
    return scheduleFavoriteSync(normalized, favoriteKey, note, userId);
  }

  function handleFavoriteStateChanged(event) {
    const siteId = String(event.detail?.siteId || "");
    const url = String(event.detail?.url || "");
    const favoriteKey = getFavoriteKey({ id: siteId, url });
    if (
      !favoriteKey ||
      !activeUserId.value ||
      pendingKeys.value.has(favoriteKey)
    ) {
      return;
    }

    if (event.detail?.favorited) {
      if (!items.value.some((item) => getFavoriteKey(item) === favoriteKey)) {
        const site = normalizeFavorite(event.detail?.site);
        if (site) {
          items.value = [...items.value, site];
          favoriteCount.value = items.value.length;
        }
      }
    } else {
      const nextItems = items.value.filter(
        (item) => getFavoriteKey(item) !== favoriteKey,
      );
      if (nextItems.length !== items.value.length) {
        items.value = nextItems;
        favoriteCount.value = Math.max(favoriteCount.value - 1, 0);
      }
    }
    lastFetchedAt.value = 0;
    persistCache(activeUserId.value);
  }

  function handleStorage(event) {
    const userId = getFavoriteUserId(userStore);
    if (!userId || event.key !== cacheKey(userId) || !event.newValue) {
      return;
    }

    try {
      const cached = JSON.parse(event.newValue);
      if (
        cached?.version !== FAVORITE_CACHE_VERSION ||
        String(cached.userId) !== String(userId) ||
        !Array.isArray(cached.items)
      ) {
        return;
      }

      items.value = normalizeFavorites(cached.items);
      favoriteCount.value = items.value.length;
      activeUserId.value = userId;
      loadedUserId.value = userId;
      lastFetchedAt.value = Number(cached.savedAt) || 0;
      cacheRestored.value = true;
      hasSnapshot.value = true;
      error.value = null;
      status.value = items.value.length ? "ready" : "empty";
    } catch {
      // Ignore malformed cross-tab cache updates.
    }
  }

  const stopAuthStateListener = addAuthStateListener(() => {
    const userId = syncUserScope();
    if (userId)
      void loadFavorites({ keepExistingData: true, background: true });
  });
  if (typeof window !== "undefined") {
    window.addEventListener(
      FAVORITE_STATE_CHANGED_EVENT,
      handleFavoriteStateChanged,
    );
    window.addEventListener("storage", handleStorage);
    onScopeDispose(() => {
      stopAuthStateListener();
      window.removeEventListener(
        FAVORITE_STATE_CHANGED_EVENT,
        handleFavoriteStateChanged,
      );
      window.removeEventListener("storage", handleStorage);
    });
  }

  return {
    items,
    status,
    error,
    loadedUserId,
    lastFetchedAt,
    cacheRestored,
    hasSnapshot,
    favoriteCount: computed(() => favoriteCount.value),
    hasFavorites: computed(() => items.value.length > 0),
    pendingKeys,
    favoritePendingIds,
    pendingSiteIds: favoritePendingIds,
    favoriteKeySet,
    isRefreshing: computed(() => status.value === "refreshing"),
    restoreFavoriteCache,
    persistFavoriteCache: persistCache,
    clearFavoriteState,
    getFavoriteKey,
    loadFavorites,
    addFavorite,
    removeFavorite,
    isFavorite,
    isPending,
    toggleFavorite,
  };
});
