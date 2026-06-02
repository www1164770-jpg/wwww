"""
数据库初始化脚本：一键同步分类和网站数据到 MySQL。

功能说明：
  1. 将 all_categories 中定义的所有分类写入 categories 表（已存在则更新）。
  2. 将 all_sites 中定义的所有网站写入 websites 表（已存在则跳过，避免重复）。
  3. 网站 Logo 通过 Google Favicon 接口自动获取，无需手动上传图片。

使用方式：
  直接运行 `python init_db.py` 即可完成数据初始化。
"""
import pymysql

# 数据库连接配置，指向本地 MySQL 实例的 nav_site 数据库
DB_CONFIG = {
    'host': '127.0.0.1', 'user': 'root', 'password': 'weiyijie748',
    'database': 'nav_site', 'charset': 'utf8mb4'
}

# ===== 需要确保数据库中存在的所有分类 =====
# 每条记录格式：(id, profession_type, name, sort_order)
#   id            - 分类唯一 ID（手动指定，便于与 all_sites 中的 cat 字段对应）
#   profession_type - 职业类型标识，用于前端按人群筛选分类
#                     可选值：general（综合）/ frontend（前端）/ designer（设计）/ product（产品）
#   name          - 分类显示名称
#   sort_order    - 同一职业类型下的排列顺序，数字越小越靠前
all_categories = [
    # 综合导航
    (1,   'general',  '常用推荐',   0),
    (2,   'general',  '开发社区',   1),
    (3,   'general',  '摸鱼娱乐',   2),
    (4,   'general',  '实用工具',   3),
    (5,   'general',  'AI 神器',    4),
    # 前端开发
    (201, 'frontend', '框架文档',   0),
    (202, 'frontend', 'UI 组件库',  1),
    (203, 'frontend', '可视化/3D',  2),
    (204, 'frontend', '工具/构建',  3),
    # UI 设计师
    (301, 'designer', '灵感采集',   0),
    (302, 'designer', '素材资源',   1),
    (303, 'designer', '在线工具',   2),
    (304, 'designer', '字体/配色',  3),
    # 产品经理
    (401, 'product',  '原型设计',   0),
    (402, 'product',  '文档办公',   1),
    (403, 'product',  '数据分析',   2),
    (404, 'product',  '竞品调研',   3),
]

# 把你想加的网站全部丢进来，只要有网址就行
# 每条记录格式：{"name": 网站名称, "url": 网站地址, "cat": 所属分类 ID}
#   name - 网站显示名称，对应 websites.name
#   url  - 网站完整 URL，对应 websites.url，同时用于自动生成 logo_url
#   cat  - 所属分类 ID，必须与 all_categories 中的 id 对应
all_sites = [
    # ===== 分类 1：常用推荐 =====
    {"name": "哔哩哔哩", "url": "https://www.bilibili.com", "cat": 1},
    {"name": "知乎", "url": "https://www.zhihu.com", "cat": 1},
    {"name": "微博", "url": "https://weibo.com", "cat": 1},
    {"name": "淘宝", "url": "https://www.taobao.com", "cat": 1},
    {"name": "京东", "url": "https://www.jd.com", "cat": 1},
    {"name": "百度", "url": "https://www.baidu.com", "cat": 1},
    {"name": "腾讯视频", "url": "https://v.qq.com", "cat": 1},
    {"name": "爱奇艺", "url": "https://www.iqiyi.com", "cat": 1},
    {"name": "优酷", "url": "https://www.youku.com", "cat": 1},
    {"name": "网易云音乐", "url": "https://music.163.com", "cat": 1},
    {"name": "QQ音乐", "url": "https://y.qq.com", "cat": 1},
    {"name": "天猫", "url": "https://www.tmall.com", "cat": 1},
    {"name": "拼多多", "url": "https://www.pinduoduo.com", "cat": 1},
    {"name": "12306", "url": "https://www.12306.cn", "cat": 1},
    {"name": "高德地图", "url": "https://www.amap.com", "cat": 1},
    {"name": "微信读书", "url": "https://weread.qq.com", "cat": 1},
    {"name": "豆瓣", "url": "https://www.douban.com", "cat": 1},
    {"name": "网易新闻", "url": "https://news.163.com", "cat": 1},
    {"name": "今日头条", "url": "https://www.toutiao.com", "cat": 1},
    # ===== 分类 2：开发社区 =====
    {"name": "GitHub", "url": "https://github.com", "cat": 2},
    {"name": "GitLab", "url": "https://gitlab.com", "cat": 2},
    {"name": "Gitee", "url": "https://gitee.com", "cat": 2},
    {"name": "掘金", "url": "https://juejin.cn", "cat": 2},
    {"name": "CSDN", "url": "https://www.csdn.net", "cat": 2},
    {"name": "博客园", "url": "https://www.cnblogs.com", "cat": 2},
    {"name": "Stack Overflow", "url": "https://stackoverflow.com", "cat": 2},
    {"name": "MDN Web Docs", "url": "https://developer.mozilla.org", "cat": 2},
    {"name": "npm", "url": "https://www.npmjs.com", "cat": 2},
    {"name": "Docker Hub", "url": "https://hub.docker.com", "cat": 2},
    {"name": "LeetCode", "url": "https://leetcode.cn", "cat": 2},
    {"name": "牛客网", "url": "https://www.nowcoder.com", "cat": 2},
    {"name": "V2EX", "url": "https://www.v2ex.com", "cat": 2},
    {"name": "SegmentFault", "url": "https://segmentfault.com", "cat": 2},
    {"name": "Vercel", "url": "https://vercel.com", "cat": 2},
    {"name": "Netlify", "url": "https://www.netlify.com", "cat": 2},
    {"name": "Railway", "url": "https://railway.app", "cat": 2},
    # ===== 分类 3：摸鱼娱乐 =====
    {"name": "抖音", "url": "https://www.douyin.com", "cat": 3},
    {"name": "小红书", "url": "https://www.xiaohongshu.com", "cat": 3},
    {"name": "虎扑", "url": "https://www.hupu.com", "cat": 3},
    {"name": "NGA玩家社区", "url": "https://nga.178.com", "cat": 3},
    {"name": "Steam", "url": "https://store.steampowered.com", "cat": 3},
    {"name": "Epic Games", "url": "https://www.epicgames.com", "cat": 3},
    {"name": "网易游戏", "url": "https://game.163.com", "cat": 3},
    {"name": "腾讯游戏", "url": "https://game.qq.com", "cat": 3},
    {"name": "漫画柜", "url": "https://www.manhuagui.com", "cat": 3},
    {"name": "哔哩哔哩漫画", "url": "https://manga.bilibili.com", "cat": 3},
    {"name": "虎嗅", "url": "https://www.huxiu.com", "cat": 3},
    {"name": "36氪", "url": "https://36kr.com", "cat": 3},
    # ===== 分类 4：实用工具 =====
    {"name": "ProcessOn", "url": "https://www.processon.com", "cat": 4},
    {"name": "Excalidraw", "url": "https://excalidraw.com", "cat": 4},
    {"name": "TinyPNG", "url": "https://tinypng.com", "cat": 4},
    {"name": "Squoosh", "url": "https://squoosh.app", "cat": 4},
    {"name": "Carbon", "url": "https://carbon.now.sh", "cat": 4},
    {"name": "Regex101", "url": "https://regex101.com", "cat": 4},
    {"name": "Can I Use", "url": "https://caniuse.com", "cat": 4},
    {"name": "Notion", "url": "https://www.notion.so", "cat": 4},
    {"name": "飞书", "url": "https://www.feishu.cn", "cat": 4},
    {"name": "腾讯文档", "url": "https://docs.qq.com", "cat": 4},
    {"name": "石墨文档", "url": "https://shimo.im", "cat": 4},
    {"name": "百度翻译", "url": "https://fanyi.baidu.com", "cat": 4},
    {"name": "DeepL翻译", "url": "https://www.deepl.com", "cat": 4},
    {"name": "Cloudflare", "url": "https://www.cloudflare.com", "cat": 4},
    {"name": "iLovePDF", "url": "https://www.ilovepdf.com", "cat": 4},
    {"name": "Unsplash", "url": "https://unsplash.com", "cat": 4},
    {"name": "Figma", "url": "https://www.figma.com", "cat": 4},
    # ===== 分类 5：AI 神器 =====
    {"name": "ChatGPT", "url": "https://chat.openai.com", "cat": 5},
    {"name": "Claude", "url": "https://claude.ai", "cat": 5},
    {"name": "Gemini", "url": "https://gemini.google.com", "cat": 5},
    {"name": "文心一言", "url": "https://yiyan.baidu.com", "cat": 5},
    {"name": "通义千问", "url": "https://tongyi.aliyun.com", "cat": 5},
    {"name": "讯飞星火", "url": "https://xinghuo.xfyun.cn", "cat": 5},
    {"name": "Kimi", "url": "https://kimi.moonshot.cn", "cat": 5},
    {"name": "豆包", "url": "https://www.doubao.com", "cat": 5},
    {"name": "DeepSeek", "url": "https://www.deepseek.com", "cat": 5},
    {"name": "Midjourney", "url": "https://www.midjourney.com", "cat": 5},
    {"name": "Stable Diffusion", "url": "https://stability.ai", "cat": 5},
    {"name": "Runway", "url": "https://runwayml.com", "cat": 5},
    {"name": "Suno AI", "url": "https://suno.ai", "cat": 5},
    {"name": "GitHub Copilot", "url": "https://github.com/features/copilot", "cat": 5},
    {"name": "Cursor", "url": "https://www.cursor.com", "cat": 5},
    {"name": "Perplexity", "url": "https://www.perplexity.ai", "cat": 5},
    {"name": "Hugging Face", "url": "https://huggingface.co", "cat": 5},
    {"name": "智谱清言", "url": "https://chatglm.cn", "cat": 5},

    # ===== 前端开发 - 201：框架文档 =====
    {"name": "Vue.js", "url": "https://cn.vuejs.org", "cat": 201},
    {"name": "React", "url": "https://react.dev", "cat": 201},
    {"name": "Angular", "url": "https://angular.dev", "cat": 201},
    {"name": "Svelte", "url": "https://svelte.dev", "cat": 201},
    {"name": "Nuxt.js", "url": "https://nuxt.com", "cat": 201},
    {"name": "Next.js", "url": "https://nextjs.org", "cat": 201},
    {"name": "Vite", "url": "https://vitejs.dev", "cat": 201},
    {"name": "Webpack", "url": "https://webpack.js.org", "cat": 201},
    {"name": "Node.js", "url": "https://nodejs.org", "cat": 201},
    {"name": "Express.js", "url": "https://expressjs.com", "cat": 201},
    {"name": "TypeScript", "url": "https://www.typescriptlang.org", "cat": 201},
    {"name": "Astro", "url": "https://astro.build", "cat": 201},
    {"name": "SolidJS", "url": "https://www.solidjs.com", "cat": 201},
    {"name": "Remix", "url": "https://remix.run", "cat": 201},
    # ===== 前端开发 - 202：UI 组件库 =====
    {"name": "Element Plus", "url": "https://element-plus.org", "cat": 202},
    {"name": "Ant Design", "url": "https://ant.design", "cat": 202},
    {"name": "Naive UI", "url": "https://www.naiveui.com", "cat": 202},
    {"name": "Arco Design", "url": "https://arco.design", "cat": 202},
    {"name": "Vant", "url": "https://vant-ui.github.io/vant", "cat": 202},
    {"name": "shadcn/ui", "url": "https://ui.shadcn.com", "cat": 202},
    {"name": "Tailwind CSS", "url": "https://tailwindcss.com", "cat": 202},
    {"name": "Bootstrap", "url": "https://getbootstrap.com", "cat": 202},
    {"name": "Material UI", "url": "https://mui.com", "cat": 202},
    {"name": "Chakra UI", "url": "https://chakra-ui.com", "cat": 202},
    {"name": "Radix UI", "url": "https://www.radix-ui.com", "cat": 202},
    {"name": "DaisyUI", "url": "https://daisyui.com", "cat": 202},
    {"name": "Headless UI", "url": "https://headlessui.com", "cat": 202},
    # ===== 前端开发 - 203：可视化/3D =====
    {"name": "ECharts", "url": "https://echarts.apache.org", "cat": 203},
    {"name": "D3.js", "url": "https://d3js.org", "cat": 203},
    {"name": "Three.js", "url": "https://threejs.org", "cat": 203},
    {"name": "Chart.js", "url": "https://www.chartjs.org", "cat": 203},
    {"name": "AntV", "url": "https://antv.antgroup.com", "cat": 203},
    {"name": "Highcharts", "url": "https://www.highcharts.com", "cat": 203},
    {"name": "Babylon.js", "url": "https://www.babylonjs.com", "cat": 203},
    {"name": "Spline", "url": "https://spline.design", "cat": 203},
    {"name": "Recharts", "url": "https://recharts.org", "cat": 203},
    {"name": "Victory", "url": "https://formidable.com/open-source/victory", "cat": 203},
    # ===== 前端开发 - 204：工具/构建 =====
    {"name": "ESLint", "url": "https://eslint.org", "cat": 204},
    {"name": "Prettier", "url": "https://prettier.io", "cat": 204},
    {"name": "Vitest", "url": "https://vitest.dev", "cat": 204},
    {"name": "Jest", "url": "https://jestjs.io", "cat": 204},
    {"name": "Playwright", "url": "https://playwright.dev", "cat": 204},
    {"name": "Storybook", "url": "https://storybook.js.org", "cat": 204},
    {"name": "pnpm", "url": "https://pnpm.io", "cat": 204},
    {"name": "Rollup", "url": "https://rollupjs.org", "cat": 204},
    {"name": "Bun", "url": "https://bun.sh", "cat": 204},
    {"name": "Turbopack", "url": "https://turbo.build", "cat": 204},
    {"name": "Biome", "url": "https://biomejs.dev", "cat": 204},
    {"name": "Oxlint", "url": "https://oxc.rs", "cat": 204},

    # ===== UI 设计师 - 301：灵感采集 =====
    {"name": "Dribbble", "url": "https://dribbble.com", "cat": 301},
    {"name": "Behance", "url": "https://www.behance.net", "cat": 301},
    {"name": "Pinterest", "url": "https://www.pinterest.com", "cat": 301},
    {"name": "站酷", "url": "https://www.zcool.com.cn", "cat": 301},
    {"name": "花瓣网", "url": "https://huaban.com", "cat": 301},
    {"name": "Awwwards", "url": "https://www.awwwards.com", "cat": 301},
    {"name": "Mobbin", "url": "https://mobbin.com", "cat": 301},
    {"name": "UI8", "url": "https://ui8.net", "cat": 301},
    {"name": "Lapa Ninja", "url": "https://www.lapa.ninja", "cat": 301},
    {"name": "Muzli", "url": "https://muz.li", "cat": 301},
    {"name": "Land-book", "url": "https://land-book.com", "cat": 301},
    {"name": "Godly", "url": "https://godly.website", "cat": 301},
    # ===== UI 设计师 - 302：素材资源 =====
    {"name": "Pexels", "url": "https://www.pexels.com", "cat": 302},
    {"name": "Freepik", "url": "https://www.freepik.com", "cat": 302},
    {"name": "iconfont", "url": "https://www.iconfont.cn", "cat": 302},
    {"name": "Iconify", "url": "https://iconify.design", "cat": 302},
    {"name": "Lucide Icons", "url": "https://lucide.dev", "cat": 302},
    {"name": "Heroicons", "url": "https://heroicons.com", "cat": 302},
    {"name": "unDraw", "url": "https://undraw.co", "cat": 302},
    {"name": "Storyset", "url": "https://storyset.com", "cat": 302},
    {"name": "LottieFiles", "url": "https://lottiefiles.com", "cat": 302},
    {"name": "Pixabay", "url": "https://pixabay.com", "cat": 302},
    {"name": "Flaticon", "url": "https://www.flaticon.com", "cat": 302},
    {"name": "Icons8", "url": "https://icons8.com", "cat": 302},
    # ===== UI 设计师 - 303：在线工具 =====
    {"name": "MasterGo", "url": "https://mastergo.com", "cat": 303},
    {"name": "即时设计", "url": "https://js.design", "cat": 303},
    {"name": "Canva", "url": "https://www.canva.com", "cat": 303},
    {"name": "Pixlr", "url": "https://pixlr.com", "cat": 303},
    {"name": "Remove.bg", "url": "https://www.remove.bg", "cat": 303},
    {"name": "Photopea", "url": "https://www.photopea.com", "cat": 303},
    {"name": "Vectorizer", "url": "https://vectorizer.ai", "cat": 303},
    {"name": "Cleanup.pictures", "url": "https://cleanup.pictures", "cat": 303},
    {"name": "Haikei", "url": "https://haikei.app", "cat": 303},
    {"name": "Fffuel", "url": "https://fffuel.co", "cat": 303},
    # ===== UI 设计师 - 304：字体/配色 =====
    {"name": "Google Fonts", "url": "https://fonts.google.com", "cat": 304},
    {"name": "Adobe Fonts", "url": "https://fonts.adobe.com", "cat": 304},
    {"name": "字体天下", "url": "https://www.fonts.net.cn", "cat": 304},
    {"name": "Coolors", "url": "https://coolors.co", "cat": 304},
    {"name": "Adobe Color", "url": "https://color.adobe.com", "cat": 304},
    {"name": "Colorhunt", "url": "https://colorhunt.co", "cat": 304},
    {"name": "Gradient Hunt", "url": "https://gradienthunt.com", "cat": 304},
    {"name": "Happy Hues", "url": "https://www.happyhues.co", "cat": 304},
    {"name": "Realtime Colors", "url": "https://www.realtimecolors.com", "cat": 304},
    {"name": "Fontpair", "url": "https://www.fontpair.co", "cat": 304},

    # ===== 产品经理 - 401：原型设计 =====
    {"name": "Axure RP", "url": "https://www.axure.com", "cat": 401},
    {"name": "墨刀", "url": "https://modao.cc", "cat": 401},
    {"name": "即时设计", "url": "https://js.design", "cat": 401},
    {"name": "MasterGo", "url": "https://mastergo.com", "cat": 401},
    {"name": "Balsamiq", "url": "https://balsamiq.com", "cat": 401},
    {"name": "Framer", "url": "https://www.framer.com", "cat": 401},
    {"name": "ProtoPie", "url": "https://www.protopie.io", "cat": 401},
    {"name": "Whimsical", "url": "https://whimsical.com", "cat": 401},
    {"name": "Miro", "url": "https://miro.com", "cat": 401},
    # ===== 产品经理 - 402：文档办公 =====
    {"name": "语雀", "url": "https://www.yuque.com", "cat": 402},
    {"name": "Confluence", "url": "https://www.atlassian.com/software/confluence", "cat": 402},
    {"name": "Jira", "url": "https://www.atlassian.com/software/jira", "cat": 402},
    {"name": "Trello", "url": "https://trello.com", "cat": 402},
    {"name": "Linear", "url": "https://linear.app", "cat": 402},
    {"name": "Asana", "url": "https://asana.com", "cat": 402},
    {"name": "Monday.com", "url": "https://monday.com", "cat": 402},
    {"name": "Basecamp", "url": "https://basecamp.com", "cat": 402},
    {"name": "Teambition", "url": "https://www.teambition.com", "cat": 402},
    # ===== 产品经理 - 403：数据分析 =====
    {"name": "百度统计", "url": "https://tongji.baidu.com", "cat": 403},
    {"name": "Google Analytics", "url": "https://analytics.google.com", "cat": 403},
    {"name": "神策数据", "url": "https://www.sensorsdata.cn", "cat": 403},
    {"name": "Mixpanel", "url": "https://mixpanel.com", "cat": 403},
    {"name": "Amplitude", "url": "https://amplitude.com", "cat": 403},
    {"name": "DataV", "url": "https://datav.aliyun.com", "cat": 403},
    {"name": "Tableau", "url": "https://www.tableau.com", "cat": 403},
    {"name": "Power BI", "url": "https://powerbi.microsoft.com", "cat": 403},
    {"name": "Metabase", "url": "https://www.metabase.com", "cat": 403},
    {"name": "Grafana", "url": "https://grafana.com", "cat": 403},
    # ===== 产品经理 - 404：竞品调研 =====
    {"name": "SimilarWeb", "url": "https://www.similarweb.com", "cat": 404},
    {"name": "App Annie", "url": "https://www.data.ai", "cat": 404},
    {"name": "七麦数据", "url": "https://www.qimai.cn", "cat": 404},
    {"name": "蝉大师", "url": "https://www.chandashi.com", "cat": 404},
    {"name": "ProductHunt", "url": "https://www.producthunt.com", "cat": 404},
    {"name": "艾瑞咨询", "url": "https://www.iresearch.cn", "cat": 404},
    {"name": "易观分析", "url": "https://www.analysys.cn", "cat": 404},
    {"name": "questmobile", "url": "https://www.questmobile.com.cn", "cat": 404},
    {"name": "极光大数据", "url": "https://www.jiguang.cn", "cat": 404},

    # ===== 综合导航 - 分类 1：常用推荐（补充）=====
    {"name": "携程旅行", "url": "https://www.ctrip.com", "cat": 1},
    {"name": "美团", "url": "https://www.meituan.com", "cat": 1},
    {"name": "饿了么", "url": "https://www.ele.me", "cat": 1},
    {"name": "大众点评", "url": "https://www.dianping.com", "cat": 1},
    {"name": "闲鱼", "url": "https://www.goofish.com", "cat": 1},
    {"name": "Boss直聘", "url": "https://www.zhipin.com", "cat": 1},
    {"name": "智联招聘", "url": "https://www.zhaopin.com", "cat": 1},
    {"name": "前程无忧", "url": "https://www.51job.com", "cat": 1},
    {"name": "百度地图", "url": "https://map.baidu.com", "cat": 1},
    {"name": "腾讯地图", "url": "https://map.qq.com", "cat": 1},
    {"name": "滴滴出行", "url": "https://www.didiglobal.com", "cat": 1},
    {"name": "支付宝", "url": "https://www.alipay.com", "cat": 1},
    {"name": "微信", "url": "https://weixin.qq.com", "cat": 1},
    {"name": "钉钉", "url": "https://www.dingtalk.com", "cat": 1},
    {"name": "网易邮箱", "url": "https://mail.163.com", "cat": 1},
    {"name": "QQ邮箱", "url": "https://mail.qq.com", "cat": 1},
    {"name": "百度网盘", "url": "https://pan.baidu.com", "cat": 1},
    {"name": "阿里云盘", "url": "https://www.aliyundrive.com", "cat": 1},
    {"name": "夸克网盘", "url": "https://pan.quark.cn", "cat": 1},
    {"name": "哔哩哔哩直播", "url": "https://live.bilibili.com", "cat": 1},

    # ===== 综合导航 - 分类 2：开发社区（补充）=====
    {"name": "Cloudflare Workers", "url": "https://workers.cloudflare.com", "cat": 2},
    {"name": "Supabase", "url": "https://supabase.com", "cat": 2},
    {"name": "PlanetScale", "url": "https://planetscale.com", "cat": 2},
    {"name": "Neon", "url": "https://neon.tech", "cat": 2},
    {"name": "Render", "url": "https://render.com", "cat": 2},
    {"name": "Fly.io", "url": "https://fly.io", "cat": 2},
    {"name": "AWS", "url": "https://aws.amazon.com", "cat": 2},
    {"name": "阿里云", "url": "https://www.aliyun.com", "cat": 2},
    {"name": "腾讯云", "url": "https://cloud.tencent.com", "cat": 2},
    {"name": "华为云", "url": "https://www.huaweicloud.com", "cat": 2},
    {"name": "Postman", "url": "https://www.postman.com", "cat": 2},
    {"name": "Swagger", "url": "https://swagger.io", "cat": 2},
    {"name": "Redis", "url": "https://redis.io", "cat": 2},
    {"name": "MongoDB", "url": "https://www.mongodb.com", "cat": 2},
    {"name": "PostgreSQL", "url": "https://www.postgresql.org", "cat": 2},

    # ===== 综合导航 - 分类 3：摸鱼娱乐（补充）=====
    {"name": "哔哩哔哩番剧", "url": "https://www.bilibili.com/anime", "cat": 3},
    {"name": "网易漫画", "url": "https://manhua.163.com", "cat": 3},
    {"name": "腾讯动漫", "url": "https://ac.qq.com", "cat": 3},
    {"name": "快手", "url": "https://www.kuaishou.com", "cat": 3},
    {"name": "西瓜视频", "url": "https://www.ixigua.com", "cat": 3},
    {"name": "微博热搜", "url": "https://s.weibo.com/top/summary", "cat": 3},
    {"name": "知乎热榜", "url": "https://www.zhihu.com/hot", "cat": 3},
    {"name": "百度热搜", "url": "https://top.baidu.com", "cat": 3},
    {"name": "微信读书", "url": "https://weread.qq.com", "cat": 3},
    {"name": "番茄小说", "url": "https://fanqienovel.com", "cat": 3},
    {"name": "起点中文网", "url": "https://www.qidian.com", "cat": 3},
    {"name": "晋江文学城", "url": "https://www.jjwxc.net", "cat": 3},

    # ===== 综合导航 - 分类 4：实用工具（补充）=====
    {"name": "在线PS", "url": "https://www.photopea.com", "cat": 4},
    {"name": "草料二维码", "url": "https://cli.im", "cat": 4},
    {"name": "在线JSON", "url": "https://www.json.cn", "cat": 4},
    {"name": "MD5加密", "url": "https://www.md5online.org", "cat": 4},
    {"name": "Base64编解码", "url": "https://www.base64encode.org", "cat": 4},
    {"name": "时间戳转换", "url": "https://tool.lu/timestamp", "cat": 4},
    {"name": "IP查询", "url": "https://www.ip138.com", "cat": 4},
    {"name": "在线Cron", "url": "https://cron.qqe2.com", "cat": 4},
    {"name": "菜鸟工具", "url": "https://c.runoob.com", "cat": 4},
    {"name": "在线代码运行", "url": "https://tool.lu/coderunner", "cat": 4},
    {"name": "CodePen", "url": "https://codepen.io", "cat": 4},
    {"name": "StackBlitz", "url": "https://stackblitz.com", "cat": 4},
    {"name": "CodeSandbox", "url": "https://codesandbox.io", "cat": 4},
    {"name": "Replit", "url": "https://replit.com", "cat": 4},
    {"name": "Whimsical", "url": "https://whimsical.com", "cat": 4},
    {"name": "draw.io", "url": "https://app.diagrams.net", "cat": 4},

    # ===== 综合导航 - 分类 5：AI 神器（补充）=====
    {"name": "Pika", "url": "https://pika.art", "cat": 5},
    {"name": "Kling AI", "url": "https://klingai.com", "cat": 5},
    {"name": "即梦AI", "url": "https://jimeng.jianying.com", "cat": 5},
    {"name": "文生图-通义", "url": "https://tongyi.aliyun.com/wanxiang", "cat": 5},
    {"name": "Adobe Firefly", "url": "https://firefly.adobe.com", "cat": 5},
    {"name": "Canva AI", "url": "https://www.canva.com/ai-image-generator", "cat": 5},
    {"name": "ElevenLabs", "url": "https://elevenlabs.io", "cat": 5},
    {"name": "Udio", "url": "https://www.udio.com", "cat": 5},
    {"name": "Luma AI", "url": "https://lumalabs.ai", "cat": 5},
    {"name": "Ideogram", "url": "https://ideogram.ai", "cat": 5},
    {"name": "Coze", "url": "https://www.coze.cn", "cat": 5},
    {"name": "Dify", "url": "https://dify.ai", "cat": 5},
    {"name": "LangChain", "url": "https://www.langchain.com", "cat": 5},
    {"name": "OpenRouter", "url": "https://openrouter.ai", "cat": 5},
    {"name": "Together AI", "url": "https://www.together.ai", "cat": 5},

    # ===== 前端开发 - 201：框架文档（补充）=====
    {"name": "Deno", "url": "https://deno.com", "cat": 201},
    {"name": "Hono", "url": "https://hono.dev", "cat": 201},
    {"name": "Qwik", "url": "https://qwik.dev", "cat": 201},
    {"name": "Preact", "url": "https://preactjs.com", "cat": 201},
    {"name": "Alpine.js", "url": "https://alpinejs.dev", "cat": 201},
    {"name": "HTMX", "url": "https://htmx.org", "cat": 201},
    {"name": "Electron", "url": "https://www.electronjs.org", "cat": 201},
    {"name": "Tauri", "url": "https://tauri.app", "cat": 201},

    # ===== 前端开发 - 202：UI 组件库（补充）=====
    {"name": "Vuetify", "url": "https://vuetifyjs.com", "cat": 202},
    {"name": "PrimeVue", "url": "https://primevue.org", "cat": 202},
    {"name": "Quasar", "url": "https://quasar.dev", "cat": 202},
    {"name": "Mantine", "url": "https://mantine.dev", "cat": 202},
    {"name": "NextUI", "url": "https://nextui.org", "cat": 202},
    {"name": "Flowbite", "url": "https://flowbite.com", "cat": 202},
    {"name": "UnoCSS", "url": "https://unocss.dev", "cat": 202},
    {"name": "Open Props", "url": "https://open-props.style", "cat": 202},

    # ===== 前端开发 - 203：可视化/3D（补充）=====
    {"name": "Mapbox", "url": "https://www.mapbox.com", "cat": 203},
    {"name": "Leaflet", "url": "https://leafletjs.com", "cat": 203},
    {"name": "Deck.gl", "url": "https://deck.gl", "cat": 203},
    {"name": "Sigma.js", "url": "https://www.sigmajs.org", "cat": 203},
    {"name": "Vis.js", "url": "https://visjs.org", "cat": 203},

    # ===== 前端开发 - 204：工具/构建（补充）=====
    {"name": "Cypress", "url": "https://www.cypress.io", "cat": 204},
    {"name": "Husky", "url": "https://typicode.github.io/husky", "cat": 204},
    {"name": "Commitlint", "url": "https://commitlint.js.org", "cat": 204},
    {"name": "Changesets", "url": "https://github.com/changesets/changesets", "cat": 204},
    {"name": "Nx", "url": "https://nx.dev", "cat": 204},

    # ===== UI 设计师 - 301：灵感采集（补充）=====
    {"name": "Collect UI", "url": "https://collectui.com", "cat": 301},
    {"name": "UI Sources", "url": "https://www.uisources.com", "cat": 301},
    {"name": "Screenlane", "url": "https://screenlane.com", "cat": 301},
    {"name": "Pttrns", "url": "https://www.pttrns.com", "cat": 301},
    {"name": "Designspiration", "url": "https://www.designspiration.com", "cat": 301},

    # ===== UI 设计师 - 302：素材资源（补充）=====
    {"name": "Noun Project", "url": "https://thenounproject.com", "cat": 302},
    {"name": "SVG Repo", "url": "https://www.svgrepo.com", "cat": 302},
    {"name": "Tabler Icons", "url": "https://tabler.io/icons", "cat": 302},
    {"name": "Phosphor Icons", "url": "https://phosphoricons.com", "cat": 302},
    {"name": "Remix Icon", "url": "https://remixicon.com", "cat": 302},
    {"name": "Mixkit", "url": "https://mixkit.co", "cat": 302},

    # ===== UI 设计师 - 303：在线工具（补充）=====
    {"name": "Penpot", "url": "https://penpot.app", "cat": 303},
    {"name": "Lunacy", "url": "https://icons8.com/lunacy", "cat": 303},
    {"name": "Mockup World", "url": "https://www.mockupworld.co", "cat": 303},
    {"name": "Smart Mockups", "url": "https://smartmockups.com", "cat": 303},
    {"name": "Shots.so", "url": "https://shots.so", "cat": 303},

    # ===== UI 设计师 - 304：字体/配色（补充）=====
    {"name": "Type Scale", "url": "https://typescale.com", "cat": 304},
    {"name": "Font Joy", "url": "https://fontjoy.com", "cat": 304},
    {"name": "Palette Ninja", "url": "https://palette.ninja", "cat": 304},
    {"name": "Paletton", "url": "https://paletton.com", "cat": 304},
    {"name": "Muzli Colors", "url": "https://colors.muz.li", "cat": 304},

    # ===== 产品经理 - 401：原型设计（补充）=====
    {"name": "Sketch", "url": "https://www.sketch.com", "cat": 401},
    {"name": "InVision", "url": "https://www.invisionapp.com", "cat": 401},
    {"name": "Marvel", "url": "https://marvelapp.com", "cat": 401},
    {"name": "Zeplin", "url": "https://zeplin.io", "cat": 401},
    {"name": "Overflow", "url": "https://overflow.io", "cat": 401},

    # ===== 产品经理 - 402：文档办公（补充）=====
    {"name": "Coda", "url": "https://coda.io", "cat": 402},
    {"name": "Airtable", "url": "https://www.airtable.com", "cat": 402},
    {"name": "Lark", "url": "https://www.larksuite.com", "cat": 402},
    {"name": "Slite", "url": "https://slite.com", "cat": 402},
    {"name": "Slab", "url": "https://slab.com", "cat": 402},

    # ===== 产品经理 - 403：数据分析（补充）=====
    {"name": "Looker Studio", "url": "https://lookerstudio.google.com", "cat": 403},
    {"name": "Hotjar", "url": "https://www.hotjar.com", "cat": 403},
    {"name": "FullStory", "url": "https://www.fullstory.com", "cat": 403},
    {"name": "Heap", "url": "https://www.heap.io", "cat": 403},
    {"name": "Posthog", "url": "https://posthog.com", "cat": 403},

    # ===== 产品经理 - 404：竞品调研（补充）=====
    {"name": "Crunchbase", "url": "https://www.crunchbase.com", "cat": 404},
    {"name": "G2", "url": "https://www.g2.com", "cat": 404},
    {"name": "Capterra", "url": "https://www.capterra.com", "cat": 404},
    {"name": "IT桔子", "url": "https://www.itjuzi.com", "cat": 404},
    {"name": "36氪研究院", "url": "https://36kr.com/research", "cat": 404},

    # ===== 综合导航 - 分类 1：常用推荐（第三批）=====
    {"name": "虎牙直播", "url": "https://www.huya.com", "cat": 1},
    {"name": "斗鱼直播", "url": "https://www.douyu.com", "cat": 1},
    {"name": "网易严选", "url": "https://you.163.com", "cat": 1},
    {"name": "苏宁易购", "url": "https://www.suning.com", "cat": 1},
    {"name": "唯品会", "url": "https://www.vip.com", "cat": 1},
    {"name": "当当网", "url": "https://www.dangdang.com", "cat": 1},
    {"name": "亚马逊中国", "url": "https://www.amazon.cn", "cat": 1},
    {"name": "得物", "url": "https://www.dewu.com", "cat": 1},
    {"name": "小米商城", "url": "https://www.mi.com", "cat": 1},
    {"name": "华为商城", "url": "https://www.vmall.com", "cat": 1},
    {"name": "Apple中国", "url": "https://www.apple.com.cn", "cat": 1},
    {"name": "去哪儿旅行", "url": "https://www.qunar.com", "cat": 1},
    {"name": "飞猪旅行", "url": "https://www.fliggy.com", "cat": 1},
    {"name": "同程旅行", "url": "https://www.ly.com", "cat": 1},
    {"name": "马蜂窝", "url": "https://www.mafengwo.cn", "cat": 1},
    {"name": "穷游网", "url": "https://www.qyer.com", "cat": 1},
    {"name": "丁香医生", "url": "https://dxy.com", "cat": 1},
    {"name": "好大夫在线", "url": "https://www.haodf.com", "cat": 1},
    {"name": "平安好医生", "url": "https://www.jk.cn", "cat": 1},
    {"name": "学而思", "url": "https://www.xueersi.com", "cat": 1},

    # ===== 综合导航 - 分类 2：开发社区（第三批）=====
    {"name": "Kubernetes", "url": "https://kubernetes.io", "cat": 2},
    {"name": "Terraform", "url": "https://www.terraform.io", "cat": 2},
    {"name": "Ansible", "url": "https://www.ansible.com", "cat": 2},
    {"name": "Jenkins", "url": "https://www.jenkins.io", "cat": 2},
    {"name": "GitHub Actions", "url": "https://github.com/features/actions", "cat": 2},
    {"name": "CircleCI", "url": "https://circleci.com", "cat": 2},
    {"name": "SonarQube", "url": "https://www.sonarqube.org", "cat": 2},
    {"name": "Sentry", "url": "https://sentry.io", "cat": 2},
    {"name": "Grafana", "url": "https://grafana.com", "cat": 2},
    {"name": "Prometheus", "url": "https://prometheus.io", "cat": 2},
    {"name": "Elasticsearch", "url": "https://www.elastic.co", "cat": 2},
    {"name": "RabbitMQ", "url": "https://www.rabbitmq.com", "cat": 2},
    {"name": "Apache Kafka", "url": "https://kafka.apache.org", "cat": 2},
    {"name": "Nginx", "url": "https://nginx.org", "cat": 2},
    {"name": "Linux命令大全", "url": "https://www.linuxcool.com", "cat": 2},
    {"name": "菜鸟教程", "url": "https://www.runoob.com", "cat": 2},
    {"name": "廖雪峰的官方网站", "url": "https://www.liaoxuefeng.com", "cat": 2},
    {"name": "阮一峰的网络日志", "url": "https://www.ruanyifeng.com/blog", "cat": 2},
    {"name": "InfoQ", "url": "https://www.infoq.cn", "cat": 2},
    {"name": "开源中国", "url": "https://www.oschina.net", "cat": 2},

    # ===== 综合导航 - 分类 3：摸鱼娱乐（第三批）=====
    {"name": "网易云游戏", "url": "https://cg.163.com", "cat": 3},
    {"name": "腾讯云游戏", "url": "https://start.qq.com", "cat": 3},
    {"name": "Xbox", "url": "https://www.xbox.com", "cat": 3},
    {"name": "PlayStation", "url": "https://www.playstation.com", "cat": 3},
    {"name": "Nintendo", "url": "https://www.nintendo.com.cn", "cat": 3},
    {"name": "米哈游", "url": "https://www.mihoyo.com", "cat": 3},
    {"name": "原神", "url": "https://ys.mihoyo.com", "cat": 3},
    {"name": "崩坏：星穹铁道", "url": "https://sr.mihoyo.com", "cat": 3},
    {"name": "LOL", "url": "https://lol.qq.com", "cat": 3},
    {"name": "王者荣耀", "url": "https://pvp.qq.com", "cat": 3},
    {"name": "和平精英", "url": "https://peaceelite.tencent.com", "cat": 3},
    {"name": "网易云音乐电台", "url": "https://music.163.com/#/discover/djradio", "cat": 3},
    {"name": "喜马拉雅", "url": "https://www.ximalaya.com", "cat": 3},
    {"name": "蜻蜓FM", "url": "https://www.qingting.fm", "cat": 3},
    {"name": "懒人听书", "url": "https://www.lrts.me", "cat": 3},

    # ===== 综合导航 - 分类 4：实用工具（第三批）=====
    {"name": "在线格式转换", "url": "https://www.aconvert.com", "cat": 4},
    {"name": "PDF转Word", "url": "https://smallpdf.com", "cat": 4},
    {"name": "压缩图片", "url": "https://compressor.io", "cat": 4},
    {"name": "在线OCR", "url": "https://www.onlineocr.net", "cat": 4},
    {"name": "字数统计", "url": "https://www.eteste.com", "cat": 4},
    {"name": "Markdown编辑器", "url": "https://dillinger.io", "cat": 4},
    {"name": "Typora", "url": "https://typora.io", "cat": 4},
    {"name": "Obsidian", "url": "https://obsidian.md", "cat": 4},
    {"name": "Logseq", "url": "https://logseq.com", "cat": 4},
    {"name": "Roam Research", "url": "https://roamresearch.com", "cat": 4},
    {"name": "Miro", "url": "https://miro.com", "cat": 4},
    {"name": "Loom", "url": "https://www.loom.com", "cat": 4},
    {"name": "Calendly", "url": "https://calendly.com", "cat": 4},
    {"name": "Zapier", "url": "https://zapier.com", "cat": 4},
    {"name": "Make", "url": "https://www.make.com", "cat": 4},
    {"name": "n8n", "url": "https://n8n.io", "cat": 4},
    {"name": "Airtable", "url": "https://www.airtable.com", "cat": 4},
    {"name": "Retool", "url": "https://retool.com", "cat": 4},
    {"name": "Appsmith", "url": "https://www.appsmith.com", "cat": 4},
    {"name": "Budibase", "url": "https://budibase.com", "cat": 4},

    # ===== 综合导航 - 分类 5：AI 神器（第三批）=====
    {"name": "Grok", "url": "https://grok.com", "cat": 5},
    {"name": "Meta AI", "url": "https://www.meta.ai", "cat": 5},
    {"name": "Mistral AI", "url": "https://mistral.ai", "cat": 5},
    {"name": "Groq", "url": "https://groq.com", "cat": 5},
    {"name": "Replicate", "url": "https://replicate.com", "cat": 5},
    {"name": "Fal.ai", "url": "https://fal.ai", "cat": 5},
    {"name": "Civitai", "url": "https://civitai.com", "cat": 5},
    {"name": "Leonardo AI", "url": "https://leonardo.ai", "cat": 5},
    {"name": "Playground AI", "url": "https://playground.com", "cat": 5},
    {"name": "Gamma", "url": "https://gamma.app", "cat": 5},
    {"name": "Beautiful.ai", "url": "https://www.beautiful.ai", "cat": 5},
    {"name": "Tome", "url": "https://tome.app", "cat": 5},
    {"name": "Notion AI", "url": "https://www.notion.so/product/ai", "cat": 5},
    {"name": "Jasper", "url": "https://www.jasper.ai", "cat": 5},
    {"name": "Copy.ai", "url": "https://www.copy.ai", "cat": 5},

    # ===== 前端开发 - 201：框架文档（第三批）=====
    {"name": "Ionic", "url": "https://ionicframework.com", "cat": 201},
    {"name": "React Native", "url": "https://reactnative.dev", "cat": 201},
    {"name": "Flutter", "url": "https://flutter.dev", "cat": 201},
    {"name": "Expo", "url": "https://expo.dev", "cat": 201},
    {"name": "Capacitor", "url": "https://capacitorjs.com", "cat": 201},
    {"name": "NestJS", "url": "https://nestjs.com", "cat": 201},
    {"name": "Fastify", "url": "https://fastify.dev", "cat": 201},
    {"name": "Koa.js", "url": "https://koajs.com", "cat": 201},
    {"name": "Elysia", "url": "https://elysiajs.com", "cat": 201},
    {"name": "tRPC", "url": "https://trpc.io", "cat": 201},

    # ===== 前端开发 - 202：UI 组件库（第三批）=====
    {"name": "Skeleton", "url": "https://www.skeleton.dev", "cat": 202},
    {"name": "Park UI", "url": "https://park-ui.com", "cat": 202},
    {"name": "Tremor", "url": "https://www.tremor.so", "cat": 202},
    {"name": "Aceternity UI", "url": "https://ui.aceternity.com", "cat": 202},
    {"name": "Magic UI", "url": "https://magicui.design", "cat": 202},
    {"name": "Origin UI", "url": "https://originui.com", "cat": 202},
    {"name": "Cult UI", "url": "https://cult-ui.com", "cat": 202},

    # ===== 前端开发 - 203：可视化/3D（第三批）=====
    {"name": "Observable Plot", "url": "https://observablehq.com/plot", "cat": 203},
    {"name": "Vega-Lite", "url": "https://vega.github.io/vega-lite", "cat": 203},
    {"name": "Nivo", "url": "https://nivo.rocks", "cat": 203},
    {"name": "Tremor Charts", "url": "https://www.tremor.so/docs/visualizations/area-chart", "cat": 203},
    {"name": "React Flow", "url": "https://reactflow.dev", "cat": 203},

    # ===== 前端开发 - 204：工具/构建（第三批）=====
    {"name": "Vite Plugin PWA", "url": "https://vite-pwa-org.netlify.app", "cat": 204},
    {"name": "Wrangler", "url": "https://developers.cloudflare.com/workers/wrangler", "cat": 204},
    {"name": "Nitro", "url": "https://nitro.unjs.io", "cat": 204},
    {"name": "UnJS", "url": "https://unjs.io", "cat": 204},
    {"name": "Rspack", "url": "https://rspack.dev", "cat": 204},

    # ===== UI 设计师 - 301：灵感采集（第三批）=====
    {"name": "Minimal Gallery", "url": "https://minimal.gallery", "cat": 301},
    {"name": "Httpster", "url": "https://httpster.net", "cat": 301},
    {"name": "One Page Love", "url": "https://onepagelove.com", "cat": 301},
    {"name": "SaaS Landing Page", "url": "https://saaslandingpage.com", "cat": 301},
    {"name": "Dark Mode Design", "url": "https://www.darkmodedesign.com", "cat": 301},

    # ===== UI 设计师 - 302：素材资源（第三批）=====
    {"name": "Blush Design", "url": "https://blush.design", "cat": 302},
    {"name": "Open Doodles", "url": "https://www.opendoodles.com", "cat": 302},
    {"name": "Humaaans", "url": "https://www.humaaans.com", "cat": 302},
    {"name": "DrawKit", "url": "https://www.drawkit.com", "cat": 302},
    {"name": "Vecteezy", "url": "https://www.vecteezy.com", "cat": 302},

    # ===== UI 设计师 - 303：在线工具（第三批）=====
    {"name": "Mockflow", "url": "https://www.mockflow.com", "cat": 303},
    {"name": "Uizard", "url": "https://uizard.io", "cat": 303},
    {"name": "Visily", "url": "https://www.visily.ai", "cat": 303},
    {"name": "Motiff", "url": "https://motiff.com", "cat": 303},
    {"name": "Pixso", "url": "https://pixso.cn", "cat": 303},

    # ===== UI 设计师 - 304：字体/配色（第三批）=====
    {"name": "Fontshare", "url": "https://www.fontshare.com", "cat": 304},
    {"name": "Bunny Fonts", "url": "https://fonts.bunny.net", "cat": 304},
    {"name": "Variable Fonts", "url": "https://v-fonts.com", "cat": 304},
    {"name": "Color & Contrast", "url": "https://colorandcontrast.com", "cat": 304},
    {"name": "Reasonable Colors", "url": "https://reasonable.work/colors", "cat": 304},

    # ===== 产品经理 - 401：原型设计（第三批）=====
    {"name": "UXPin", "url": "https://www.uxpin.com", "cat": 401},
    {"name": "Justinmind", "url": "https://www.justinmind.com", "cat": 401},
    {"name": "Origami Studio", "url": "https://origami.design", "cat": 401},
    {"name": "Principle", "url": "https://principleformac.com", "cat": 401},
    {"name": "Flinto", "url": "https://www.flinto.com", "cat": 401},

    # ===== 产品经理 - 402：文档办公（第三批）=====
    {"name": "Tettra", "url": "https://tettra.com", "cat": 402},
    {"name": "Guru", "url": "https://www.getguru.com", "cat": 402},
    {"name": "Nuclino", "url": "https://www.nuclino.com", "cat": 402},
    {"name": "Almanac", "url": "https://almanac.io", "cat": 402},
    {"name": "Outline", "url": "https://www.getoutline.com", "cat": 402},

    # ===== 产品经理 - 403：数据分析（第三批）=====
    {"name": "Plausible", "url": "https://plausible.io", "cat": 403},
    {"name": "Fathom", "url": "https://usefathom.com", "cat": 403},
    {"name": "Umami", "url": "https://umami.is", "cat": 403},
    {"name": "Matomo", "url": "https://matomo.org", "cat": 403},
    {"name": "Countly", "url": "https://count.ly", "cat": 403},

    # ===== 产品经理 - 404：竞品调研（第三批）=====
    {"name": "BuiltWith", "url": "https://builtwith.com", "cat": 404},
    {"name": "Wappalyzer", "url": "https://www.wappalyzer.com", "cat": 404},
    {"name": "SpyFu", "url": "https://www.spyfu.com", "cat": 404},
    {"name": "SEMrush", "url": "https://www.semrush.com", "cat": 404},
    {"name": "Ahrefs", "url": "https://ahrefs.com", "cat": 404},
]

def get_logo_url(url):
    """
    根据网站 URL 生成对应的 Logo 图片地址。

    利用 Google Favicon 服务（s2/favicons）自动获取网站图标，
    无需本地存储图片，前端直接加载该 URL 即可显示 Logo。

    参数：
        url (str): 网站完整地址，如 "https://github.com"

    返回：
        str: Google Favicon 接口 URL，图标尺寸固定为 128x128
    """
    domain = url.split('//')[-1].split('/')[0]  # 从 URL 中提取域名，如 "github.com"
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=128"

def run():
    """
    执行数据库初始化的主函数。

    步骤：
      1. 连接 MySQL 数据库。
      2. 同步所有分类：使用 INSERT ... ON DUPLICATE KEY UPDATE，
         保证分类存在且数据最新，不会因重复运行而报错。
      3. 批量插入网站：先查询是否已存在同名同分类的记录，
         存在则跳过，不存在则插入并自动生成 Logo URL。
      4. 提交事务并关闭连接，打印执行结果统计。
    """
    conn = pymysql.connect(**DB_CONFIG)   # 建立数据库连接
    cursor = conn.cursor()

    # 步骤 1：同步所有分类到 categories 表
    # 使用 ON DUPLICATE KEY UPDATE 实现"有则更新，无则插入"，保证幂等性
    for cat in all_categories:
        cat_id, profession, name, sort = cat
        cursor.execute(
            "INSERT INTO categories (id, name, profession_type, sort_order) VALUES (%s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE name=%s, profession_type=%s, sort_order=%s",
            (cat_id, name, profession, sort, name, profession, sort)
        )
    conn.commit()
    print(f"✅ 分类同步完成（共 {len(all_categories)} 个）")

    # 步骤 2：批量插入网站到 websites 表
    # 先查重，避免重复插入同名同分类的网站；Logo 通过 get_logo_url 自动生成
    inserted = 0   # 本次新增的网站数量
    skipped = 0    # 已存在、跳过的网站数量
    total = len(all_sites)
    for site in all_sites:
        # 检查同一分类下是否已存在同名网站
        cursor.execute(
            "SELECT id FROM websites WHERE name=%s AND category_id=%s",
            (site['name'], site['cat'])
        )
        if cursor.fetchone():
            skipped += 1   # 已存在，跳过不重复插入
            continue
        logo = get_logo_url(site['url'])   # 根据 URL 生成 Google Favicon 地址
        cursor.execute(
            "INSERT INTO websites (category_id, name, url, logo_url) VALUES (%s, %s, %s, %s)",
            (site['cat'], site['name'], site['url'], logo)
        )
        inserted += 1

    conn.commit()   # 提交所有插入操作
    conn.close()    # 关闭数据库连接
    print(f"✅ 全部完成！新增 {inserted} 个，跳过 {skipped} 个，共 {total} 个网站")

if __name__ == "__main__":
    run()