import { readFileSync, existsSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')

const read = (path) => readFileSync(resolve(root, path), 'utf8')
const exists = (path) => existsSync(resolve(root, path))

const checks = [
  {
    name: 'home page is split into focused components',
    run() {
      const expectedFiles = [
        'src/components/home/HeroSearch.vue',
        'src/components/home/CareerRecommend.vue',
        'src/components/home/PopularCategories.vue',
        'src/components/home/ToolCard.vue',
        'src/components/home/FavoriteStack.vue',
        'src/components/modals/LoginModal.vue',
        'src/components/modals/SiteFormModal.vue',
        'src/components/modals/CategoryModal.vue',
        'src/components/modals/AppearanceModal.vue'
      ]

      for (const file of expectedFiles) {
        if (!exists(file)) throw new Error(`Missing split component: ${file}`)
      }

      const home = read('src/views/Home.vue')
      for (const name of ['HeroSearch', 'CareerRecommend', 'PopularCategories', 'ToolCard', 'FavoriteStack']) {
        if (!home.includes(name)) throw new Error(`Home.vue does not use ${name}`)
      }
      if (home.includes("currentPage === 'profile'")) {
        throw new Error('Home.vue still contains the embedded profile page branch')
      }
    }
  },
  {
    name: 'career recommendation is interactive and keyword driven',
    run() {
      const career = read('src/components/home/CareerRecommend.vue')
      const home = read('src/views/Home.vue')

      for (const snippet of [
        "defineEmits(['select-career'])",
        'careerRecommendations',
        '学生',
        '程序员',
        '设计师',
        '运营'
      ]) {
        if (!career.includes(snippet)) throw new Error(`CareerRecommend is missing: ${snippet}`)
      }

      for (const snippet of ['selectCareer', 'careerKeywords', 'activeCareer', 'searchQuery.value = career']) {
        if (!home.includes(snippet)) throw new Error(`Home.vue is missing career interaction code: ${snippet}`)
      }
    }
  },
  {
    name: 'profile route uses dedicated view under views folder',
    run() {
      const router = read('src/router/index.js')
      if (!router.includes("component: () => import('../views/ProfileView.vue')")) {
        throw new Error('Profile route does not import ../views/ProfileView.vue')
      }
      if (!router.includes("meta: { requiresAuth: true }")) {
        throw new Error('Profile route is not protected by requiresAuth')
      }

      const profileFiles = [
        'src/views/ProfileView.vue',
        'src/components/profile/ProfileSidebar.vue',
        'src/components/profile/ProfileBasic.vue',
        'src/components/profile/ProfileSecurity.vue',
        'src/components/profile/ProfilePrivacy.vue',
        'src/components/profile/ProfileContent.vue'
      ]
      for (const file of profileFiles) {
        if (!exists(file)) throw new Error(`Missing profile file: ${file}`)
      }
    }
  },
  {
    name: 'API base URL is configurable and local URLs are not hardcoded',
    run() {
      const api = read('src/utils/api.js')
      const home = read('src/views/Home.vue')
      const audit = read('src/views/AuditBoard.vue')
      const envPath = resolve(root, '.env.development')

      if (!api.includes('export const API_BASE_URL')) {
        throw new Error('api.js does not export API_BASE_URL')
      }
      if (!existsSync(envPath)) {
        throw new Error('.env.development does not exist')
      }
      if (!readFileSync(envPath, 'utf8').includes('VITE_API_BASE_URL=http://127.0.0.1:5000/api')) {
        throw new Error('.env.development does not define VITE_API_BASE_URL')
      }

      const apiFallbackCount = api.match(/http:\/\/127\.0\.0\.1:5000\/api/g)?.length || 0
      if (apiFallbackCount !== 1) {
        throw new Error(`api.js should contain exactly one local fallback URL, found ${apiFallbackCount}`)
      }

      for (const [name, content] of [['Home.vue', home], ['AuditBoard.vue', audit]]) {
        if (content.includes('http://127.0.0.1:5000/api')) {
          throw new Error(`${name} still contains a hardcoded local API URL`)
        }
      }
    }
  },
  {
    name: 'frontend src contains only frontend source files',
    run() {
      for (const file of [
        'src/build_final_sql.py',
        'src/convert_to_64.py',
        'src/init_db.sql',
        'src/insert_websites_data.sql',
        'src/result.txt'
      ]) {
        if (exists(file)) throw new Error(`Non-frontend file still in src: ${file}`)
      }
      if (exists('src/__pycache__')) throw new Error('Python cache directory still exists in frontend src')

      for (const file of [
        '../scripts/build_final_sql.py',
        '../scripts/convert_to_64.py',
        '../sql/init_db.sql',
        '../sql/insert_websites_data.sql'
      ]) {
        if (!exists(file)) throw new Error(`Moved backend artifact is missing: ${file}`)
      }

      const srcEntries = readdirSync(resolve(root, 'src'))
      for (const entry of srcEntries) {
        if (entry.endsWith('.py') || entry.endsWith('.sql') || entry === '__pycache__') {
          throw new Error(`Unexpected backend artifact in src: ${entry}`)
        }
      }
    }
  },
  {
    name: 'deployment notes document Vercel frontend root and API env',
    run() {
      const readme = read('README.md')
      for (const snippet of [
        'Root Directory: backend/frontend',
        'Build Command: npm run build',
        'Output Directory: dist',
        'VITE_API_BASE_URL=https://你的后端域名/api'
      ]) {
        if (!readme.includes(snippet)) throw new Error(`README is missing deployment note: ${snippet}`)
      }
    }
  }
]

let failed = false

for (const check of checks) {
  try {
    check.run()
    console.log(`PASS ${check.name}`)
  } catch (error) {
    failed = true
    console.error(`FAIL ${check.name}`)
    console.error(error.message)
  }
}

if (failed) {
  process.exitCode = 1
}
