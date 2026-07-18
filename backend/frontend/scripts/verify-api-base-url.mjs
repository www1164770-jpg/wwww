import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";


const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const apiBasePath = path.resolve(
  scriptDirectory,
  "../src/utils/apiBase.js",
);

assert.ok(
  existsSync(apiBasePath),
  "apiBase.js must exist and export resolveApiBaseURL",
);

const { resolveApiBaseURL } = await import(pathToFileURL(apiBasePath).href);

assert.equal(typeof resolveApiBaseURL, "function");
assert.equal(
  resolveApiBaseURL({
    VITE_API_BASE_URL: "https://example.test/backend///",
    DEV: false,
    PROD: true,
  }),
  "https://example.test/backend",
  "explicit VITE_API_BASE_URL should win and trim trailing slashes",
);
assert.equal(
  resolveApiBaseURL({ DEV: false, PROD: true }),
  "/api",
  "production should use the current origin with the shared /api prefix",
);
assert.equal(
  resolveApiBaseURL(
    { DEV: true, PROD: false },
    "http://127.0.0.1:5000/api",
  ),
  "http://127.0.0.1:5000/api",
  "development should use the actual local backend",
);
assert.equal(
  resolveApiBaseURL(
    {
      VITE_API_BASE_URL: "   ",
      DEV: true,
      PROD: false,
    },
    "http://127.0.0.1:5000/api",
  ),
  "http://127.0.0.1:5000/api",
  "blank configuration should fall back to the environment default",
);
assert.equal(
  resolveApiBaseURL({ VITE_API_BASE_URL: "/", PROD: true }),
  "/",
  "the root base URL should not be normalized to an empty string",
);

const productionRecommendURL = `${resolveApiBaseURL({ PROD: true })}/sites/recommend`;
const developmentHealthURL = `${resolveApiBaseURL(
  { DEV: true },
  "http://127.0.0.1:5000/api",
)}/health`;

assert.equal(productionRecommendURL, "/api/sites/recommend");
assert.equal(
  developmentHealthURL,
  "http://127.0.0.1:5000/api/health",
);
assert.equal(productionRecommendURL.includes("/api/api/"), false);

console.log("api base URL verification passed");
