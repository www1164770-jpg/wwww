export const AUTH_STORAGE_KEYS = Object.freeze({
  legacyToken: "token",
  accessToken: "access_token",
  refreshToken: "refresh_token",
  user: "user",
  userInfo: "user_info",
  userRole: "user_role",
  questionnaireCompleted: "questionnaire_completed",
  isLoggedIn: "is_logged_in",
});

const AUTH_CHANGED_EVENT = "auth-session-changed";

function firstDefined(...values) {
  return values.find((value) => value !== undefined && value !== null);
}

function parseBoolean(value) {
  return value === true || value === 1 || value === "1" || value === "true";
}

function getStorage() {
  return typeof localStorage === "undefined" ? null : localStorage;
}

function notifyAuthChange() {
  if (typeof window !== "undefined" && typeof window.dispatchEvent === "function") {
    window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
  }
}

export function isValidAuthToken(token) {
  const value = String(token || "");
  return value.length > 20 && value.split(".").length === 3;
}

export function normalizeAuthSession(payload = {}, fallback = {}) {
  const envelope = payload?.data && typeof payload.data === "object"
    ? payload.data
    : payload;
  const data = envelope?.data && typeof envelope.data === "object"
    ? envelope.data
    : envelope || {};
  const fallbackData = fallback?.data && typeof fallback.data === "object"
    ? fallback.data
    : fallback || {};

  const userInfo = firstDefined(
    data.user_info,
    data.user,
    envelope.user_info,
    envelope.user,
    fallbackData.user_info,
    fallbackData.user,
    fallback.user_info,
    fallback.user,
  );

  return {
    access_token: firstDefined(
      data.access_token,
      data.token,
      envelope.access_token,
      envelope.token,
      fallbackData.access_token,
      fallbackData.token,
      fallback.access_token,
      fallback.token,
    ),
    refresh_token: firstDefined(
      data.refresh_token,
      envelope.refresh_token,
      fallbackData.refresh_token,
      fallback.refresh_token,
    ),
    user_info: userInfo,
    user_role: firstDefined(
      data.user_role,
      envelope.user_role,
      userInfo?.role,
      fallbackData.user_role,
      fallback.user_role,
    ),
    questionnaire_completed: firstDefined(
      data.questionnaire_completed,
      data.questionnaireCompleted,
      envelope.questionnaire_completed,
      envelope.questionnaireCompleted,
      userInfo?.questionnaire_completed,
      userInfo?.questionnaireCompleted,
      fallbackData.questionnaire_completed,
      fallbackData.questionnaireCompleted,
      fallback.questionnaire_completed,
      fallback.questionnaireCompleted,
    ),
  };
}

export function saveAuthSession(payload = {}, fallback = {}) {
  const storage = getStorage();
  if (!storage) return normalizeAuthSession(payload, fallback);

  const session = normalizeAuthSession(payload, fallback);
  const accessToken = session.access_token;

  if (accessToken) {
    storage.setItem(AUTH_STORAGE_KEYS.accessToken, accessToken);
    storage.setItem(AUTH_STORAGE_KEYS.legacyToken, accessToken);
    storage.setItem(AUTH_STORAGE_KEYS.isLoggedIn, "true");
  }

  if (session.refresh_token !== undefined) {
    storage.setItem(
      AUTH_STORAGE_KEYS.refreshToken,
      session.refresh_token || "",
    );
  }

  if (session.user_info && typeof session.user_info === "object") {
    const serializedUser = JSON.stringify(session.user_info);
    storage.setItem(AUTH_STORAGE_KEYS.userInfo, serializedUser);
    storage.setItem(AUTH_STORAGE_KEYS.user, serializedUser);
  }

  if (session.user_role !== undefined) {
    storage.setItem(AUTH_STORAGE_KEYS.userRole, session.user_role || "user");
  }

  if (session.questionnaire_completed !== undefined) {
    storage.setItem(
      AUTH_STORAGE_KEYS.questionnaireCompleted,
      parseBoolean(session.questionnaire_completed) ? "true" : "false",
    );
  }

  notifyAuthChange();
  return session;
}

export function clearAuthSession() {
  const storage = getStorage();
  if (!storage) return;

  Object.values(AUTH_STORAGE_KEYS).forEach((key) => storage.removeItem(key));
  notifyAuthChange();
}

export function getAccessToken() {
  const storage = getStorage();
  if (!storage) return null;

  const accessToken = storage.getItem(AUTH_STORAGE_KEYS.accessToken);
  if (isValidAuthToken(accessToken)) return accessToken;

  const legacyToken = storage.getItem(AUTH_STORAGE_KEYS.legacyToken);
  if (isValidAuthToken(legacyToken)) {
    storage.setItem(AUTH_STORAGE_KEYS.accessToken, legacyToken);
    return legacyToken;
  }

  return null;
}

export function getRefreshToken() {
  const storage = getStorage();
  return storage?.getItem(AUTH_STORAGE_KEYS.refreshToken) || null;
}

export function applyAuthRequestHeaders(config = {}) {
  const nextConfig = config;
  nextConfig.headers = nextConfig.headers || {};

  if (nextConfig.skipAuth) {
    return nextConfig;
  }

  const accessToken = getAccessToken();
  if (isValidAuthToken(accessToken)) {
    nextConfig.headers.Authorization = `Bearer ${accessToken}`;
  } else {
    delete nextConfig.headers.Authorization;
  }

  return nextConfig;
}

export function getStoredUserInfo() {
  const storage = getStorage();
  if (!storage) return {};

  try {
    return JSON.parse(
      storage.getItem(AUTH_STORAGE_KEYS.userInfo) ||
        storage.getItem(AUTH_STORAGE_KEYS.user) ||
        "{}",
    );
  } catch {
    return {};
  }
}

export function getStoredUserRole() {
  const storage = getStorage();
  return storage?.getItem(AUTH_STORAGE_KEYS.userRole) || "user";
}

export function getStoredQuestionnaireCompleted() {
  const storage = getStorage();
  return parseBoolean(storage?.getItem(AUTH_STORAGE_KEYS.questionnaireCompleted));
}

export function setQuestionnaireCompleted(value) {
  const storage = getStorage();
  if (!storage) return;

  storage.setItem(
    AUTH_STORAGE_KEYS.questionnaireCompleted,
    parseBoolean(value) ? "true" : "false",
  );
  notifyAuthChange();
}

export function addAuthStateListener(listener) {
  if (typeof window === "undefined" || typeof window.addEventListener !== "function") {
    return () => {};
  }

  window.addEventListener(AUTH_CHANGED_EVENT, listener);
  return () => window.removeEventListener(AUTH_CHANGED_EVENT, listener);
}
