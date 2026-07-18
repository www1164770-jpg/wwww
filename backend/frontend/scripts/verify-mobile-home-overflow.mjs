import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { homedir } from "node:os";
import { dirname, resolve } from "node:path";
import { existsSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(scriptDirectory, "..");
const viteCli = resolve(frontendRoot, "node_modules", "vite", "bin", "vite.js");
const host = "127.0.0.1";
const port = Number(process.env.MOBILE_HOME_TEST_PORT || 4173);
const baseUrl = `http://${host}:${port}`;

function delay(milliseconds) {
  return new Promise((resolveDelay) => setTimeout(resolveDelay, milliseconds));
}

function loadPlaywright() {
  const overridePath = process.env.MOBILE_HOME_PLAYWRIGHT_PATH;
  const candidates = overridePath ? [overridePath] : [];

  try {
    return require("playwright");
  } catch {
    // The project intentionally has no Playwright dependency. Codex desktop
    // bundles Playwright for browser QA, so discover that runtime as a fallback.
  }

  const pnpmRoot = resolve(
    homedir(),
    ".cache",
    "codex-runtimes",
    "codex-primary-runtime",
    "dependencies",
    "node",
    "node_modules",
    ".pnpm",
  );

  if (existsSync(pnpmRoot)) {
    for (const entry of readdirSync(pnpmRoot)) {
      if (!entry.startsWith("playwright@")) continue;
      candidates.push(resolve(pnpmRoot, entry, "node_modules", "playwright"));
    }
  }

  for (const candidate of candidates) {
    try {
      return require(candidate);
    } catch {
      // Try the next available runtime path.
    }
  }

  throw new Error(
    "Playwright is unavailable. Install it locally or set MOBILE_HOME_PLAYWRIGHT_PATH.",
  );
}

async function waitForServer(server, output) {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    if (server.exitCode !== null) {
      throw new Error(`Vite exited before startup.\n${output.text}`);
    }
    try {
      const response = await fetch(baseUrl);
      if (response.ok) return;
    } catch {
      // Vite is still starting.
    }
    await delay(100);
  }
  throw new Error(`Timed out waiting for ${baseUrl}.\n${output.text}`);
}

async function stopServer(server) {
  if (!server || server.exitCode !== null) return;
  server.kill();
  for (let attempt = 0; attempt < 20 && server.exitCode === null; attempt += 1) {
    await delay(100);
  }
}

async function mockExternalRequests(page) {
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());

    if (url.pathname.startsWith("/api/")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ code: 0, message: "success", data: [] }),
      });
      return;
    }

    if (![host, "localhost"].includes(url.hostname)) {
      await route.fulfill({ status: 204, body: "" });
      return;
    }

    await route.continue();
  });
}

async function collectMetrics(page) {
  return page.evaluate(async () => {
    const documentElement = document.documentElement;
    const body = document.body;
    const viewport = document.querySelector(".tool-marquee__viewport");

    const overflowElements = Array.from(document.querySelectorAll("body *"))
      .map((element) => {
        const rect = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        const internalScroller = element.closest(
          ".tool-marquee__viewport, .nav-links, .popular-categories",
        );

        return {
          tag: element.tagName,
          id: element.id,
          className:
            typeof element.className === "string" ? element.className : "",
          left: Math.round(rect.left * 100) / 100,
          right: Math.round(rect.right * 100) / 100,
          width: Math.round(rect.width * 100) / 100,
          clientWidth: element.clientWidth,
          scrollWidth: element.scrollWidth,
          position: style.position,
          display: style.display,
          widthStyle: style.width,
          minWidth: style.minWidth,
          marginLeft: style.marginLeft,
          marginRight: style.marginRight,
          transform: style.transform,
          internalScroller: internalScroller?.className || "",
        };
      })
      .filter((item) => item.left < -1 || item.right > window.innerWidth + 1);

    const pageLevelSuspects = overflowElements.filter(
      (item) => !item.internalScroller,
    );
    const internalScrollers = [
      ".tool-marquee__viewport",
      ".nav-links",
      ".popular-categories",
    ]
      .map((selector) => document.querySelector(selector))
      .filter(Boolean)
      .map((element) => ({
        className: element.className,
        clientWidth: element.clientWidth,
        scrollWidth: element.scrollWidth,
      }));

    const marqueeBefore = viewport?.scrollLeft ?? 0;
    if (viewport) viewport.scrollLeft = 120;
    await new Promise((resolveFrame) => requestAnimationFrame(resolveFrame));
    const marqueeAfter = viewport?.scrollLeft ?? 0;

    window.scrollTo(9999, 0);
    await new Promise((resolveFrame) => requestAnimationFrame(resolveFrame));

    return {
      documentScrollWidth: documentElement.scrollWidth,
      bodyScrollWidth: body.scrollWidth,
      clientWidth: documentElement.clientWidth,
      innerWidth: window.innerWidth,
      scrollX: window.scrollX,
      horizontalScrollDistance:
        documentElement.scrollWidth - documentElement.clientWidth,
      marquee: {
        clientWidth: viewport?.clientWidth ?? 0,
        scrollWidth: viewport?.scrollWidth ?? 0,
        before: marqueeBefore,
        after: marqueeAfter,
      },
      pageLevelSuspects,
      internalScrollers,
    };
  });
}

const output = { text: "" };
const server = spawn(
  process.execPath,
  [viteCli, "--host", host, "--port", String(port), "--strictPort"],
  { cwd: frontendRoot, stdio: ["ignore", "pipe", "pipe"], windowsHide: true },
);

server.stdout.on("data", (chunk) => {
  output.text += chunk.toString();
});
server.stderr.on("data", (chunk) => {
  output.text += chunk.toString();
});

let browser;

try {
  await waitForServer(server, output);
  const { chromium } = loadPlaywright();
  try {
    browser = await chromium.launch({ headless: true });
  } catch {
    browser = await chromium.launch({ headless: true, channel: "msedge" });
  }

  const context = await browser.newContext({
    viewport: { width: 375, height: 812 },
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  const consoleIssues = [];
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleIssues.push({ type: message.type(), text: message.text() });
    }
  });
  page.on("pageerror", (error) => {
    consoleIssues.push({ type: "pageerror", text: error.message });
  });

  await page.addInitScript(() => {
    localStorage.setItem("cookie_consent_status", "accepted");
  });
  await mockExternalRequests(page);
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.locator(".hero-search").waitFor({ state: "visible" });
  await page.locator(".tool-marquee__viewport").waitFor({ state: "visible" });

  const metrics = await collectMetrics(page);
  const failures = [];
  if (metrics.documentScrollWidth > metrics.clientWidth + 1) {
    failures.push("document scrollWidth exceeds clientWidth");
  }
  if (metrics.bodyScrollWidth > metrics.clientWidth + 1) {
    failures.push("body scrollWidth exceeds clientWidth");
  }
  if (Math.abs(metrics.scrollX) > 1) {
    failures.push("window can scroll horizontally");
  }
  if (metrics.marquee.scrollWidth <= metrics.marquee.clientWidth) {
    failures.push("marquee no longer has its intended internal overflow");
  }
  if (metrics.marquee.after <= metrics.marquee.before) {
    failures.push("marquee cannot scroll inside its own viewport");
  }
  if (consoleIssues.length) {
    failures.push("relevant browser console issues were recorded");
  }

  if (failures.length) {
    console.error(
      JSON.stringify({ failures, metrics, consoleIssues }, null, 2),
    );
    throw new Error("Mobile homepage overflow regression checks failed");
  }

  console.log(
    JSON.stringify(
      {
        result: "mobile homepage overflow regression checks passed",
        metrics,
        consoleIssues,
      },
      null,
      2,
    ),
  );
  await context.close();
} finally {
  await browser?.close();
  await stopServer(server);
}
