import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) =>
  readFileSync(resolve(root, relativePath), "utf8");

const appTooltip = read("src/components/common/AppTooltip.vue");
const siteCard = read("src/components/site/SiteCard.vue");
const categorySection = read("src/components/home/CategorySection.vue");
const recommendSection = read("src/components/home/RecommendSection.vue");
const favoriteStack = read("src/components/home/FavoriteStack.vue");
const toolMarquee = read("src/components/home/ToolMarquee.vue");
const siteLogo = read("src/components/site/SiteLogo.vue");
const api = read("src/utils/api.js");
const packageJson = JSON.parse(read("package.json"));
const cardSources = [
  siteCard,
  categorySection,
  recommendSection,
  favoriteStack,
];
const cardSource = cardSources.join("\n");

const checks = [
  [
    "URL is not used as a native or custom Tooltip value",
    !/:title\s*=\s*["'][^"']*\b(?:site|tool|resource|website)\.url/.test(
      cardSource,
    ) &&
      !/:content\s*=\s*["'][^"']*\b(?:site|tool|resource|website)\.url/.test(
        cardSource,
      ),
  ],
  [
    "Shared website cards use the normalized description parser",
    /getSiteDescription\(props\.site\)/.test(siteCard) &&
      /getSiteDescription\(site\)/.test(recommendSection) &&
      /getSiteDescription\(site\)/.test(favoriteStack),
  ],
  [
    "AppTooltip exposes hover, focus, Escape and tooltip semantics",
    appTooltip.includes('@mouseenter="showTooltip"') &&
      appTooltip.includes('@focusin="showTooltip"') &&
      appTooltip.includes('@keydown.esc="hideTooltip"') &&
      appTooltip.includes('role="tooltip"') &&
      appTooltip.includes(
        ':aria-describedby="visible && canInteract ? tooltipId : undefined"',
      ),
  ],
  [
    "Empty descriptions do not create an empty Tooltip",
    appTooltip.includes("<slot v-else />") &&
      /v-if="siteDescription"/.test(siteCard) &&
      /v-if="siteDescription\(site\)"/.test(favoriteStack),
  ],
  [
    "Tooltip only appears for truncated descriptions",
    appTooltip.includes("showOnOverflow") &&
      appTooltip.includes("fullHeight > element.clientHeight") &&
      cardSource.includes("data-tooltip-overflow-target"),
  ],
  [
    "Shared SiteLogo covers career, category, hot and common cards",
    /<SiteLogo/.test(siteCard) &&
      /<SiteLogo/.test(recommendSection) &&
      /<SiteLogo/.test(favoriteStack) &&
      /<SiteCard[\s\S]*?variant="category"/.test(categorySection),
  ],
  [
    "Common tools no longer maintain a second hardcoded fallback list",
    !/const\s+fallbackSites\s*=/.test(favoriteStack) &&
      !favoriteStack.includes("Notion") &&
      !favoriteStack.includes("ProcessOn"),
  ],
  [
    "Common tools hide the non-core section when there is no data",
    favoriteStack.includes('<section v-if="displaySites.length"') &&
      !favoriteStack.includes("暂无常用工具数据"),
  ],
  [
    "Common tool cards retain real safe external links",
    favoriteStack.includes(':href="normalizeUrl(site.url)"') &&
      favoriteStack.includes('target="_blank"') &&
      favoriteStack.includes('rel="noopener noreferrer"'),
  ],
  [
    "Hot recommendation cards retain safe links and an external-link affordance",
    recommendSection.includes(':href="site.url"') &&
      recommendSection.includes('target="_blank"') &&
      recommendSection.includes('rel="noopener noreferrer"') &&
      recommendSection.includes("<ExternalLink"),
  ],
  [
    "Common tool cards have border, radius, hover and responsive styles",
    /\.compact-tool-card\s*\{[\s\S]*?border:/.test(favoriteStack) &&
      /\.compact-tool-card\s*\{[\s\S]*?border-radius:/.test(favoriteStack) &&
      favoriteStack.includes(".compact-tool-card:hover") &&
      /@media \(max-width:\s*820px\)/.test(favoriteStack),
  ],
  [
    "The shared P0 description mapping remains available",
    api.includes("SITE_DESCRIPTION_FALLBACKS") &&
      api.includes("export function getSiteDescription"),
  ],
  [
    "ToolMarquee still uses the shared SiteLogo",
    toolMarquee.includes("<SiteLogo"),
  ],
  [
    "SiteCard正文 does not render the URL",
    !/\{\{\s*site\.url\s*\}\}/.test(siteCard) &&
      !siteCard.includes("displayUrl"),
  ],
  [
    "SiteLogo keeps a fixed-size failure fallback",
    siteLogo.includes("handleImageError") &&
      siteLogo.includes('loading="lazy"') &&
      siteLogo.includes("site-logo--fallback"),
  ],
  [
    "The专项 verifier is registered as an npm script",
    packageJson.scripts?.["test:tooltip-common-tools"] ===
      "node scripts/verify-tooltip-common-tools.mjs",
  ],
];

let failed = 0;
for (const [name, passed] of checks) {
  if (passed) {
    console.log(`PASS ${name}`);
  } else {
    failed += 1;
    console.error(`FAIL ${name}`);
  }
}

if (failed) {
  console.error(
    `\n${failed} tooltip/common-tools verification check(s) failed.`,
  );
  process.exit(1);
}
