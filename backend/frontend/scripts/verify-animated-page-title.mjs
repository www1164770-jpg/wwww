import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (path) => readFile(resolve(root, path), "utf8");
const [
  component,
  heroComponent,
  home,
  hero,
  careerGuest,
  recommendations,
  categories,
  favorites,
] = await Promise.all([
  read("src/components/common/AnimatedPageTitle.vue"),
  read("src/components/home/HeroStrokeTitle.vue"),
  read("src/views/Home.vue"),
  read("src/components/home/HeroSearch.vue"),
  read("src/components/home/GuestCareerRecommendation.vue"),
  read("src/components/home/RecommendSection.vue"),
  read("src/components/home/CategorySection.vue"),
  read("src/components/home/FavoriteStack.vue"),
]);

for (const needle of [
  "animated-page-title__outline",
  "animated-page-title__fill",
  "-webkit-text-stroke",
  "clip-path: inset(0 100% 0 0)",
  "clip-path: inset(0 0 0 0)",
  "--animated-title-outline-duration: 520ms",
  "--animated-title-fill-delay: 630ms",
  "--animated-title-fill-duration: 650ms",
  "cubic-bezier(0.22, 1, 0.36, 1)",
  "IntersectionObserver",
  "entry.intersectionRatio >= enterThreshold",
  "entry.intersectionRatio <= exitThreshold",
  "prefers-reduced-motion: reduce",
  "var(--heading-text-color",
]) {
  if (!component.includes(needle))
    throw new Error(`Missing animated title contract: ${needle}`);
}

for (const forbidden of [
  "setInterval",
  "setTimeout",
  "animation: linear",
  "infinite",
])
  if (component.includes(forbidden))
    throw new Error(`Animated title uses forbidden behavior: ${forbidden}`);

for (const source of [careerGuest, recommendations, categories, favorites]) {
  if (
    !source.includes("<AnimatedPageTitle") ||
    !source.includes(':replay-on-enter="true"')
  )
    throw new Error(
      "Every home screen title must replay only after re-entering its viewport",
    );
}

for (const needle of [
  "hero-stroke-title__measure",
  "hero-stroke-title__stroke",
  "hero-stroke-title__fill",
  "visibility: hidden",
  "--hero-stroke-width: 1.2px",
  "--hero-stroke-duration: 1.6s",
  "--hero-fill-delay: 1.8s",
  "--hero-fill-duration: 0.9s",
  "cubic-bezier(0.22, 1, 0.36, 1)",
  "-webkit-text-stroke: 0 transparent",
  "prefers-reduced-motion: reduce",
]) {
  if (!heroComponent.includes(needle))
    throw new Error(`Missing hero title animation contract: ${needle}`);
}

if ((heroComponent.match(/hero-stroke-title__stroke\"/g) || []).length !== 1)
  throw new Error("The hero title must render exactly one outline layer");

if ((heroComponent.match(/hero-stroke-title__fill\"/g) || []).length !== 1)
  throw new Error("The hero title must render exactly one fill layer");

for (const forbidden of [
  "opacity:",
  "translate",
  "setInterval",
  "setTimeout",
  "v-for",
]) {
  if (heroComponent.includes(forbidden))
    throw new Error(`Hero title uses forbidden behavior: ${forbidden}`);
}

const heroTextShadows = [
  ...heroComponent.matchAll(/text-shadow:\s*([^;]+);/g),
].map((match) => match[1].trim());

if (heroTextShadows.some((value) => value !== "none"))
  throw new Error("Hero title must not simulate its outline with text-shadow");

if (
  !hero.includes("<HeroStrokeTitle") ||
  !hero.includes('id="home-hero-title"') ||
  !hero.includes('text="根据你的职业，推荐最适合的工具"') ||
  hero.includes("<AnimatedPageTitle") ||
  hero.includes("text-shadow:")
)
  throw new Error(
    "The first home screen is not using the isolated hero title animation",
  );

if (
  !home.includes("适合「{{ selectedOccupationLabel }}」的网站工具") ||
  !home.includes(':replay-on-enter="true"')
)
  throw new Error(
    "The authenticated career recommendation title is not animated",
  );

console.log("animated page title source verification passed");
