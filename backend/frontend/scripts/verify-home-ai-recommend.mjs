import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { execSync } from "node:child_process";

const root = resolve(import.meta.dirname, "..");
const repoRoot = resolve(root, "..", "..");

const read = (path) => readFileSync(resolve(root, path), "utf8");
const exists = (path) => existsSync(resolve(root, path));
const readRepo = (path) => readFileSync(resolve(repoRoot, path), "utf8");
const gitOutput = (command) =>
  execSync(command, {
    cwd: repoRoot,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  }).trim();

const checks = [
  {
    name: "home page renders the current category section component",
    run() {
      const home = read("src/views/Home.vue");
      const category = read("src/components/home/CategorySection.vue");

      for (const snippet of [
        'import CategorySection from "../components/home/CategorySection.vue"',
        'data-testid="popular-categories"',
        "<CategorySection",
        ':categories="categories"',
        ':category-sites-map="categorySitesMap"',
        '@visit-site="visitSite"',
      ]) {
        if (!home.includes(snippet))
          throw new Error(
            `Home.vue is missing current category behavior: ${snippet}`,
          );
      }

      for (const snippet of [
        '<nav class="category-nav"',
        'v-for="category in categoryOptions"',
        "handleCategoryChange(category.name)",
        "const filteredWebsites = computed",
        "<SiteCard",
        'variant="category"',
        "website-card-grid",
        "hide-actions",
        "EmptyState",
      ]) {
        if (!category.includes(snippet))
          throw new Error(
            `CategorySection is missing category navigation behavior: ${snippet}`,
          );
      }

      if (home.includes("currentPage === 'profile'")) {
        throw new Error(
          "Home.vue still contains the embedded profile page branch",
        );
      }
    },
  },
  {
    name: "career recommendation uses the latest questionnaire and explicit states",
    run() {
      const home = read("src/views/Home.vue");
      const api = read("src/utils/api.js");
      const routes = readRepo("backend/v1_routes.py");
      const careerService = readRepo("backend/career_recommend_service.py");

      for (const snippet of [
        "careerAPI",
        "careerRecommendations",
        "career.match_score",
        "career.reason",
        "careerAbilityTags",
        "careerInterestTags",
        "questionnaireCompleted",
        'to=\"/questionnaire\"',
        "career.websites",
      ]) {
        if (!home.includes(snippet))
          throw new Error(
            `Home.vue is missing questionnaire-driven career behavior: ${snippet}`,
          );
      }

      for (const snippet of [
        "export const careerAPI",
        '@app.route("/api/career/recommend", methods=["GET"])',
        "build_career_recommendations(",
        "SELECT * FROM user_profiles WHERE user_id=%s",
        '"careers": careers',
        '"websites": selected_career.get("websites", [])',
      ]) {
        if (
          !api.includes(snippet) &&
          !routes.includes(snippet) &&
          !careerService.includes(snippet)
        )
          throw new Error(
            `Backend is missing dynamic career recommendation behavior: ${snippet}`,
          );
      }

      for (const snippet of [
        "from occupation_utils import",
        "rank_sites(",
        "questionnaire_options_from_config",
      ]) {
        if (!routes.includes(snippet))
          throw new Error(
            `Recommendation API is missing profile-aware fallback behavior: ${snippet}`,
          );
      }
    },
  },
  {
    name: "profile route uses dedicated view under views folder",
    run() {
      const router = read("src/router/index.js");
      if (
        !/component:\s*\(\)\s*=>\s*import\(["']\.\.\/views\/ProfileView\.vue["']\)/.test(
          router,
        )
      ) {
        throw new Error(
          "Profile route does not import ../views/ProfileView.vue",
        );
      }
      if (!router.includes("meta: { requiresAuth: true }")) {
        throw new Error("Profile route is not protected by requiresAuth");
      }

      const profileFiles = [
        "src/views/ProfileView.vue",
        "src/components/profile/ProfileSidebar.vue",
        "src/components/profile/ProfileBasic.vue",
        "src/components/profile/ProfileSecurity.vue",
        "src/components/profile/ProfilePrivacy.vue",
        "src/components/profile/ProfileContent.vue",
      ];
      for (const file of profileFiles) {
        if (!exists(file)) throw new Error(`Missing profile file: ${file}`);
      }
    },
  },
  {
    name: "API base URL is configurable and local URLs are not hardcoded",
    run() {
      const api = read("src/utils/api.js");
      const home = read("src/views/Home.vue");
      const audit = read("src/views/AuditBoard.vue");
      const envPath = resolve(root, ".env.development");

      if (!api.includes("export const API_BASE_URL")) {
        throw new Error("api.js does not export API_BASE_URL");
      }
      if (!existsSync(envPath)) {
        throw new Error(".env.development does not exist");
      }
      const developmentEnv = readFileSync(envPath, "utf8");
      if (
        !/VITE_API_BASE_URL=(?:\/api|http:\/\/127\.0\.0\.1:5000\/api)/.test(
          developmentEnv,
        )
      ) {
        throw new Error(
          ".env.development does not define a usable VITE_API_BASE_URL",
        );
      }

      if (!api.includes('const DEFAULT_API_BASE_URL = "/api"')) {
        throw new Error("api.js does not define the /api fallback URL");
      }

      for (const [name, content] of [
        ["Home.vue", home],
        ["AuditBoard.vue", audit],
      ]) {
        if (content.includes("http://127.0.0.1:5000/api")) {
          throw new Error(`${name} still contains a hardcoded local API URL`);
        }
      }
    },
  },
  {
    name: "frontend src contains only frontend source files",
    run() {
      for (const file of [
        "src/build_final_sql.py",
        "src/convert_to_64.py",
        "src/init_db.sql",
        "src/insert_websites_data.sql",
        "src/result.txt",
      ]) {
        if (exists(file))
          throw new Error(`Non-frontend file still in src: ${file}`);
      }
      if (exists("src/__pycache__"))
        throw new Error("Python cache directory still exists in frontend src");

      for (const file of [
        "../scripts/build_final_sql.py",
        "../scripts/convert_to_64.py",
        "../sql/init_db.sql",
        "../sql/insert_websites_data.sql",
      ]) {
        if (!exists(file))
          throw new Error(`Moved backend artifact is missing: ${file}`);
      }

      const srcEntries = readdirSync(resolve(root, "src"));
      for (const entry of srcEntries) {
        if (
          entry.endsWith(".py") ||
          entry.endsWith(".sql") ||
          entry === "__pycache__"
        ) {
          throw new Error(`Unexpected backend artifact in src: ${entry}`);
        }
      }
    },
  },
  {
    name: "deployment notes document Vercel frontend root and API env",
    run() {
      const readme = read("README.md");
      for (const snippet of [
        "Root Directory: repository root",
        "Install Command: `npm ci --legacy-peer-deps --prefix backend/frontend`",
        "Build Command: `npm run build --prefix backend/frontend`",
        "Output Directory: `backend/frontend/dist`",
        "VITE_API_BASE_URL=https://backend.example.com/api",
      ]) {
        if (!readme.includes(snippet))
          throw new Error(`README is missing deployment note: ${snippet}`);
      }
    },
  },
  {
    name: "backend secrets are loaded from environment variables",
    run() {
      const app = readRepo("backend/app.py");
      const envExample = readRepo("backend/.env.example");

      for (const forbidden of [
        "pronav_super_secret_master_key",
        "381eeae3cd314fb80665a8235a03bc71",
        "meilisearch.Client('http://127.0.0.1:7700'",
      ]) {
        if (app.includes(forbidden))
          throw new Error(
            `backend/app.py still contains hardcoded secret/config: ${forbidden}`,
          );
      }

      for (const snippet of [
        "MEILI_HOST = os.getenv('MEILI_HOST', 'http://127.0.0.1:7700')",
        "MEILI_MASTER_KEY = os.getenv('MEILI_MASTER_KEY')",
      ]) {
        if (!app.includes(snippet))
          throw new Error(`backend/app.py is missing env config: ${snippet}`);
      }

      for (const key of ["MEILI_HOST=", "MEILI_MASTER_KEY="]) {
        if (!envExample.includes(key))
          throw new Error(`backend/.env.example is missing ${key}`);
      }
    },
  },
  {
    name: "sensitive runtime data is not tracked by git",
    run() {
      const tracked = gitOutput(
        "git ls-files backend/.env backend/meili_data backend/meilisearch.exe",
      );
      if (tracked)
        throw new Error(`Sensitive files are still tracked:\n${tracked}`);
    },
  },
  {
    name: "frontend dependencies do not include unused search/install packages",
    run() {
      const pkg = JSON.parse(read("package.json"));
      const deps = pkg.dependencies || {};

      for (const name of ["install", "meilisearch", "flexsearch"]) {
        if (deps[name])
          throw new Error(
            `Unused frontend dependency is still installed: ${name}`,
          );
      }

      const devDeps = pkg.devDependencies || {};
      if (!devDeps.prettier)
        throw new Error("Prettier is not listed as a dev dependency");
    },
  },
];

let failed = false;

for (const check of checks) {
  try {
    check.run();
    console.log(`PASS ${check.name}`);
  } catch (error) {
    failed = true;
    console.error(`FAIL ${check.name}`);
    console.error(error.message);
  }
}

if (failed) {
  process.exitCode = 1;
}
