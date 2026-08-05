const PRODUCTION_API_BASE_URL = "/api";


function normalizeBaseURL(value) {
  const normalized = String(value || "").trim();
  if (!normalized) return "";
  if (/^\/+$/u.test(normalized)) return "";

  const withoutTrailingSlashes = normalized.replace(/\/+$/u, "");
  if (
    withoutTrailingSlashes === "undefined"
    || withoutTrailingSlashes.startsWith("//")
    || /\/api(?:\/api)+$/iu.test(withoutTrailingSlashes)
  ) {
    throw new Error(`Invalid VITE_API_BASE_URL: ${normalized}`);
  }
  return withoutTrailingSlashes;
}


export function resolveApiBaseURL(env = {}, fallback = PRODUCTION_API_BASE_URL) {
  const configuredValue = String(env.VITE_API_BASE_URL || "").trim();
  if (configuredValue) return normalizeBaseURL(configuredValue);
  return normalizeBaseURL(fallback) || PRODUCTION_API_BASE_URL;
}
