import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')

const read = (path) => readFileSync(resolve(root, path), 'utf8')

const checks = [
  {
    name: 'homepage copy is localized and career module exists',
    run() {
      const home = read('src/views/Home.vue')
      const expectedSnippets = [
        '工具库',
        '职业推荐',
        '热门榜单',
        '资讯文章',
        '关于本站',
        '根据你的职业，推荐最适合的 AI 工具',
        '填写职业与使用场景，智能推荐学习、办公、创作、编程等高效网站与工具。',
        '搜索 AI 工具、网站或使用场景，例如：论文写作、编程、PPT、设计',
        '个工具收录',
        '个热门分类',
        '个性化推荐已开启',
        '浏览全部工具',
        '查看收藏',
        '提交网站',
        '热门工具<br>分类',
        'career-recommend-section',
        'AI 职业推荐',
        '选择你的身份，快速找到适合的工具组合'
      ]

      for (const snippet of expectedSnippets) {
        if (!home.includes(snippet)) {
          throw new Error(`Missing homepage snippet: ${snippet}`)
        }
      }
    }
  },
  {
    name: 'profile route uses dedicated authenticated view',
    run() {
      const router = read('src/router/index.js')
      if (!router.includes("component: () => import('../ProfileView.vue')")) {
        throw new Error('Profile route does not import ../ProfileView.vue')
      }
      if (!router.includes("meta: { requiresAuth: true }")) {
        throw new Error('Profile route is not protected by requiresAuth')
      }

      const profile = read('src/ProfileView.vue')
      for (const snippet of ['个人主页', '基础资料', '安全设置', '退出当前账号']) {
        if (!profile.includes(snippet)) {
          throw new Error(`ProfileView is missing migrated UI snippet: ${snippet}`)
        }
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
