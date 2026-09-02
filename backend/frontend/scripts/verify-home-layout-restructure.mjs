import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (relativePath) =>
  readFileSync(resolve(root, relativePath), "utf8");
const header = read("src/components/layout/AppHeader.vue");
const hero = read("src/components/home/HeroSearch.vue");
const home = read("src/views/Home.vue");
const categories = read("src/components/home/CategorySection.vue");
const favoriteStack = read("src/components/home/FavoriteStack.vue");
const marquee = read("src/components/home/ToolMarquee.vue");
const recommendations = read("src/components/home/RecommendSection.vue");
const globalStyle = read("src/style.css");
const appHeader = read("src/components/layout/AppHeader.vue");

const checks = [
  [
    "Header exposes semantic navigation test ids",
    /data-testid="primary-navigation"[\s\S]*?data-testid="home-navigation-link"[\s\S]*?data-testid="ai-assistant-entry"/.test(
      header,
    ),
  ],
  [
    "Header removes legacy navigation items",
    !/\u5206\u7c7b\u5bfc\u822a|AI\u5de5\u5177|\u6700\u65b0\u6536\u5f55/.test(
      header,
    ),
  ],
  [
    "Popular sites expose a dedicated marquee test id",
    /<ToolMarquee\s+data-testid="popular-sites-marquee"/.test(home),
  ],
  [
    "Home exposes ordered semantic section test ids",
    home.indexOf('data-testid="career-recommendations"') <
      home.indexOf('data-testid="featured-recommendations"') &&
      home.indexOf('data-testid="featured-recommendations"') <
        home.indexOf('data-testid="popular-sites-marquee"') &&
      home.indexOf('data-testid="popular-sites-marquee"') <
        home.indexOf('data-testid="popular-categories"'),
  ],
  [
    "Home assigns one semantic screen class to each core module",
    /class="home-screen hero-screen home-first-screen"/.test(home) &&
      /class="home-screen career-screen home-anchor-section career-recommendation-section reveal-on-scroll"/.test(
        home,
      ) &&
      /class="home-screen popular-screen home-anchor-section reveal-on-scroll"/.test(
        home,
      ) &&
      /class="home-screen category-screen home-anchor-section reveal-on-scroll"/.test(
        home,
      ),
  ],
  [
    "Desktop home uses mandatory scroll snap below the measured compact header",
    /@media \(min-width: 1024px\)[\s\S]*?scroll-snap-type:\s*y mandatory;/.test(
      home,
    ) &&
      /--home-header-offset:\s*56px/.test(home) &&
      /scroll-snap-align:\s*start/.test(home) &&
      /scroll-snap-stop:\s*always/.test(home),
  ],
  [
    "Desktop wheel paging prevents native scrolling and uses a non-passive listener",
    /window\.addEventListener\("wheel", handleHomeWheel, \{ passive: false \}\)/.test(
      home,
    ) &&
      /window\.removeEventListener\("wheel", handleHomeWheel\)/.test(home) &&
      /function handleHomeWheel\(event\)[\s\S]*?event\.preventDefault\(\)/.test(
        home,
      ),
  ],
  [
    "Wheel paging uses one 600ms requestAnimationFrame animation",
    /const HOME_WHEEL_THRESHOLD = 10/.test(home) &&
      /const HOME_SCROLL_DURATION_MS = 600/.test(home) &&
      /currentSectionIndex\.value \+ direction/.test(home) &&
      /function easeInOutCubic\(progress\)/.test(home) &&
      /homeScrollAnimationFrame = window\.requestAnimationFrame\(animate\)/.test(
        home,
      ) &&
      /window\.scrollTo\(0, targetY\)/.test(home) &&
      !/HOME_SCROLL_LOCK_MS|homeWheelUnlockTimer/.test(home),
  ],
  [
    "Programmatic paging disables snap and restores it after the exact landing",
    /html\.home-scroll-snap\.home-page-scrolling/.test(home) &&
      /scroll-snap-type:\s*none/.test(home) &&
      /document\.documentElement\.classList\.add\("home-page-scrolling"\)/.test(
        home,
      ) &&
      /home-page-scrolling \.home-screen\.reveal-on-scroll[\s\S]*?\)\s*\{[\s\S]*?transform:\s*none;[\s\S]*?transition-property:\s*opacity;/.test(
        home,
      ) &&
      /homeSnapRestoreFrame = window\.requestAnimationFrame\([\s\S]*?homeSnapRestoreSecondFrame = window\.requestAnimationFrame\([\s\S]*?classList\.remove\("home-page-scrolling"\)[\s\S]*?homeScrollLocked = false/.test(
        home,
      ) &&
      /scroll-behavior:\s*auto/.test(home) &&
      !/sections\[nextIndex\]\.scrollIntoView/.test(home),
  ],
  [
    "IntersectionObserver keeps the active home screen synchronized",
    /homeScreenObserver = new IntersectionObserver/.test(home) &&
      /threshold: \[0\.5, 0\.6, 0\.75\]/.test(home) &&
      /homeScreenObserver\?\.disconnect\(\)/.test(home),
  ],
  [
    "Oversized career and category content uses internal scrolling",
    /\.career-options\s*\{[\s\S]*?overflow-y:\s*auto/.test(home) &&
      /class="category-results-scroll"/.test(categories) &&
      /\.category-results-scroll\s*\{[\s\S]*?overflow-y:\s*auto/.test(
        categories,
      ),
  ],
  [
    "Home gives common tools an independent anchor",
    /id="recommend-tools"[\s\S]*?<RecommendSection/.test(home),
  ],
  ["Home no longer mounts latest sites", !/<LatestSitesSection\b/.test(home)],
  [
    "Latest sites component remains available",
    existsSync(resolve(root, "src/components/home/LatestSitesSection.vue")),
  ],
  [
    "AI prompt sits after the two-column career layout",
    home.indexOf('class="ai-login-prompt career-section-cta"') >
      home.indexOf('class="career-recommendation-layout"'),
  ],
  [
    "Home retains one authenticated assistant",
    (home.match(/<AiSiteAssistant\b/g) || []).length === 1 &&
      /<AiSiteAssistant\s+v-if="loggedIn"/.test(home),
  ],
  [
    "Category section removes the split copy column",
    !/category-copy|category-menu|\u6309\u573a\u666f\u6d4f\u89c8 AI \u5de5\u5177/.test(
      categories,
    ),
  ],
  [
    "Category section uses a full-width heading and grid",
    /class="category-heading\b/.test(categories) &&
      /grid-template-columns:\s*repeat\(5, minmax\(0, 1fr\)\)/.test(categories),
  ],
  [
    "Website grid becomes one column on mobile",
    /@media \(max-width:\s*480px\)[\s\S]*?\.website-card-grid[\s\S]*?grid-template-columns:\s*minmax\(0, 1fr\)/.test(
      categories,
    ),
  ],
  [
    "Category cards have no fixed 330px minimum height",
    !/min-height:\s*330px/.test(categories),
  ],
  [
    "Hero is substantially shorter than the previous 660px maximum",
    /min-height:\s*clamp\(380px, 46vh, 480px\)/.test(hero),
  ],
  [
    "Hero exposes a semantic title contract",
    /data-testid="home-hero"[\s\S]*?aria-labelledby="home-hero-title"[\s\S]*?<HeroStrokeTitle[\s\S]*?id="home-hero-title"[\s\S]*?text="根据你的职业，推荐最适合的工具"/.test(
      hero,
    ),
  ],
  ["Hero retains the search bar", /hero-search__bar/.test(hero)],
  [
    "Hero title stays on one line on desktop and wraps on mobile",
    /h1\s*\{[^}]*font-size:\s*clamp\(42px, 4vw, 64px\)[^}]*white-space:\s*nowrap/.test(
      hero,
    ) &&
      /@media \(max-width:\s*767px\)[\s\S]*?h1\s*\{[^}]*white-space:\s*normal/.test(
        hero,
      ),
  ],
  [
    "Hero copy is a transparent content layer without a card frame",
    /\.hero-copy\s*\{[^}]*border:\s*0[^}]*background:\s*transparent[^}]*box-shadow:\s*none/.test(
      hero,
    ) &&
      !/\.hero-copy\s*\{[^}]*background:\s*(?:#|rgb|var\(--app-container-bg\))/.test(
        hero,
      ),
  ],
  [
    "Hero copy uses adaptive text colors",
    hero.includes("color: var(--app-text-primary)") &&
      hero.includes("color: var(--app-text-secondary)"),
  ],
  [
    "Header pill reuses the shared adaptive glass card variables",
    /\.app-header\s*\{[\s\S]*?border:\s*1px solid var\(--app-card-border\)[\s\S]*?background-color:\s*var\(--app-card-bg\)[\s\S]*?box-shadow:\s*var\(--app-card-shadow\)[\s\S]*?backdrop-filter:\s*blur\(var\(--app-blur\)\)/.test(
      appHeader,
    ) &&
      /html\[data-personalization="on"\] \.app-header,[\s\S]*?background:\s*var\(--app-card-bg\)[\s\S]*?border-color:\s*var\(--app-card-border\)[\s\S]*?box-shadow:\s*var\(--app-card-shadow\)/.test(
        globalStyle,
      ),
  ],
  [
    "AI assistant prompt uses the same adaptive glass card variables",
    /\.ai-login-prompt\s*\{[\s\S]*?border:\s*1px solid var\(--app-card-border\)[\s\S]*?background:\s*var\(--app-card-bg\)[\s\S]*?box-shadow:\s*var\(--app-card-shadow\)[\s\S]*?backdrop-filter:\s*blur\(var\(--app-blur\)\)/.test(
      home,
    ) &&
      !/\.ai-login-prompt\s*\{[^}]*background:\s*(?:#|var\(--color-soft-orange\))/.test(
        home,
      ),
  ],
  [
    "Home page-level tool regions stay transparent",
    /\.favorite-band\s*\{[^}]*background:\s*transparent/.test(favoriteStack) &&
      /\.brand-marquee\s*\{[^}]*background:\s*transparent/.test(marquee) &&
      !/\.favorite-band\s*\{[^}]*#(?:fff|ffffff|f8fafc)/i.test(favoriteStack),
  ],
  [
    "Common tool cards retain adaptive glass surfaces",
    /\.compact-tool-card\s*\{[\s\S]*?background:\s*var\(--app-card-bg\)[\s\S]*?backdrop-filter:\s*blur\(18px\)/.test(
      favoriteStack,
    ),
  ],
  [
    "Home recommendation copy uses adaptive text colors",
    recommendations.includes("color: var(--app-text-primary)") &&
      recommendations.includes("color: var(--app-text-secondary)"),
  ],
  [
    "Application roots do not cover the personalized background",
    /--app-background:\s*var\(--personalization-background/.test(globalStyle) &&
      /#app,\s*\n#app-root\s*\{[^}]*background:\s*transparent/.test(
        globalStyle,
      ),
  ],
  [
    "Home keeps recommendation reasons and removes the old hot anchor",
    /:show-reason="true"/.test(home) && !/id="hot"/.test(home),
  ],
];

let failed = false;
for (const [name, passed] of checks) {
  if (passed) console.log(`PASS ${name}`);
  else {
    failed = true;
    console.error(`FAIL ${name}`);
  }
}

if (failed) process.exitCode = 1;
