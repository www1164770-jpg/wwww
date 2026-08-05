import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (path) => readFileSync(resolve(root, path), "utf8");

const marquee = read("src/components/home/ToolMarquee.vue");
const logo = read("src/components/site/SiteLogo.vue");
const api = read("src/utils/api.js");

const checks = [
  [
    "Marquee uses the shared SiteLogo component without duplicating the tools anchor",
    !marquee.includes('id="tools"') && marquee.includes("<SiteLogo"),
  ],
  [
    "Brand names use explicit normalization instead of suffix stripping",
    marquee.includes("BRAND_DISPLAY_NAME_MAP") &&
      marquee.includes('"vue 官方文档": "Vue"') &&
      !marquee.includes("replace(/官方"),
  ],
  [
    "Links retain safe external navigation without visible URL text",
    marquee.includes('target="_blank"') &&
      marquee.includes('rel="noopener noreferrer"') &&
      !marquee.includes("{{ site.url"),
  ],
  [
    "The duplicate group is hidden from assistive technology and tab order",
    /class="brand-marquee__group" aria-hidden="true"[\s\S]*?tabindex="-1"/.test(
      marquee,
    ),
  ],
  [
    "Hover and keyboard focus pause the animation, with reduced-motion support",
    marquee.includes(".brand-marquee:hover .brand-marquee__track") &&
      marquee.includes(".brand-marquee:focus-within .brand-marquee__track") &&
      marquee.includes("prefers-reduced-motion"),
  ],
  [
    "SiteLogo declares fixed dimensions and a stable error fallback",
    logo.includes('loading="lazy"') &&
      logo.includes('decoding="async"') &&
      logo.includes("watch(imageSrc") &&
      logo.includes("handleImageError"),
  ],
  [
    "Logo resolution prefers an existing HTTPS logo before favicon fallback",
    api.includes("export function resolveSiteLogo") &&
      api.includes("normalizeLogoUrl(site.logo_url)") &&
      api.includes("https://www.google.com/s2/favicons"),
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

if (failed) process.exitCode = 1;
