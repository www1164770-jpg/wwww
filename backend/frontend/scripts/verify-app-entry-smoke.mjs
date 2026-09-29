import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { createServer } from "vite";

const HOST = "127.0.0.1";
const PORT = 4173;
const routerSource = readFileSync(resolve(import.meta.dirname, "../src/router/index.js"), "utf8");
const routes = [
  "/",
  "/login",
  "/register",
  "/forgot-password",
  "/search",
];

const server = await createServer({
  server: {
    host: HOST,
    port: PORT,
    strictPort: true,
  },
  logLevel: "error",
});

assert.doesNotMatch(routerSource, /path:\s*["']\/categories["']/);
assert.doesNotMatch(routerSource, /path:\s*["']\/category\/:id["']/);

try {
  await server.listen();

  for (const route of routes) {
    const response = await fetch(`http://${HOST}:${PORT}${route}`, {
      headers: { connection: "close" },
    });
    assert.equal(response.status, 200, `${route} should return HTTP 200`);

    const contentType = response.headers.get("content-type") || "";
    assert.match(contentType, /text\/html/i, `${route} should return HTML`);

    const html = await response.text();
    assert.match(
      html,
      /<div\s+id=["']app["']><\/div>/,
      `${route} should contain Vue app root`,
    );
    assert.match(
      html,
      /\/src\/main\.js/,
      `${route} should load the frontend entry`,
    );

    console.log(`PASS ${route}`);
  }

  console.log(`Frontend entry smoke test passed: ${routes.length} routes.`);
} finally {
  // Vite 8 can keep a dependency-optimizer handle alive after all fetches
  // finish. Closing initiates shutdown synchronously; awaiting its internal
  // promise causes Node 24 to report an unsettled top-level await.
  server.close();
}
