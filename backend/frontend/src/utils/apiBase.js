const PRODUCTION_API_BASE_URL = "/api";


function normalizeBaseURL(value) {
  const normalized = String(value || "").trim();
  if (!normalized) return "";
  if (/^\/+$/u.test(normalized)) return "/";
  return normalized.replace(/\/+$/u, "");
}


export function resolveApiBaseURL(env = {}, fallback = PRODUCTION_API_BASE_URL) {
  const configured = normalizeBaseURL(env.VITE_API_BASE_URL);
  if (configured) return configured;
  return normalizeBaseURL(fallback) || PRODUCTION_API_BASE_URL;
}
