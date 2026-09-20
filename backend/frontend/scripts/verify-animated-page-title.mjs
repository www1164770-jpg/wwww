import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (path) => readFile(resolve(root, path), "utf8");
const [
  particleTitle,
  hero,
  home,
  careerGuest,
  recommendations,
  categories,
  favorites,
  revealDirective,
  globalStyles,
] = await Promise.all([
  read("src/components/home/ParticleText.vue"),
  read("src/components/home/HeroSearch.vue"),
  read("src/views/Home.vue"),
  read("src/components/home/GuestCareerRecommendation.vue"),
  read("src/components/home/RecommendSection.vue"),
  read("src/components/home/CategorySection.vue"),
  read("src/components/home/FavoriteStack.vue"),
  read("src/directives/reveal.js"),
  read("src/style.css"),
]);

for (const needle of [
  '<ParticleText',
  'id="home-hero-title"',
  'text="根据你的职业，推荐最适合的工具"',
  'class="hero-particle-title"',
  "--particle-title-color",
  "particleTitleColor",
  "var(--heading-text-color, var(--app-text-primary))",
]) {
  assert.ok(hero.includes(needle), `Missing hero title integration: ${needle}`);
}

for (const forbidden of ["<HeroStrokeTitle", "<AnimatedPageTitle"]) {
  assert.ok(
    !hero.includes(forbidden),
    `Hero title must not reintroduce a legacy title implementation: ${forbidden}`,
  );
}

for (const needle of [
  'class="particle-text"',
  "particle-text__canvas",
  "particle-text__fallback",
  "particle-text__sr-only",
  'getContext("2d")',
  "createTextMask",
  "rebuildParticles",
  "drawFrame",
  "requestAnimationFrame",
  "targetX: point.x",
  "targetY: point.y",
  "--particle-title-color",
  "prefers-reduced-motion: reduce",
]) {
  assert.ok(
    particleTitle.includes(needle),
    `Missing canvas particle title behavior: ${needle}`,
  );
}

assert.match(
  particleTitle,
  /<canvas[\s\S]*?class="particle-text__canvas"[\s\S]*?aria-hidden="true"/,
  "Particle canvas must be visual-only so the title remains accessible",
);
assert.match(
  particleTitle,
  /class="particle-text__sr-only"[^>]*>\{\{ text \}\}/,
  "Particle title must expose exactly one accessible text alternative",
);

for (const forbidden of [
  "HeroStrokeTitle",
  "-webkit-text-stroke",
  "clip-path:",
  "scaleY",
]) {
  assert.ok(
    !particleTitle.includes(forbidden),
    `Particle title must not use obsolete stroke or vertical-compression behavior: ${forbidden}`,
  );
}

const sectionTitles = [careerGuest, recommendations, categories, favorites, home];
for (const source of sectionTitles) {
  assert.ok(
    source.includes("<AnimatedPageTitle"),
    "Each home section must keep its existing semantic title component",
  );
  assert.ok(
    source.includes('class="reveal-child reveal-title"'),
    "Each home section title must participate in the section reveal lifecycle",
  );
  assert.ok(
    source.includes(':animation="false"'),
    "Home section titles must keep their current reveal-owned animation setting",
  );
}

assert.match(
  home,
  /适合「\{\{ selectedOccupationLabel \}\}」的网站工具/,
  "Authenticated career recommendation title must remain present",
);

for (const needle of [
  "IntersectionObserver",
  "reveal-child",
  "is-revealed",
  "reveal-complete",
]) {
  assert.ok(
    revealDirective.includes(needle),
    `Missing section reveal runtime behavior: ${needle}`,
  );
}

for (const needle of [
  ".reveal-child",
  ".reveal-title",
  ".reveal-section.is-revealed .reveal-child",
]) {
  assert.ok(
    globalStyles.includes(needle),
    `Missing section reveal styling: ${needle}`,
  );
}

console.log("animated page title current-behavior verification passed");
