import { expandedSites } from "./categoryCatalogExpansion.js";

const site = (id, name, url, summary, categoryId, categoryName) => ({
  id: `catalog-${id}`,
  name,
  url,
  summary,
  category_id: categoryId,
  category_name: categoryName,
});

const categories = [
  { id: "common", name: "常用推荐", description: "日常搜索、阅读与内容发现" },
  { id: "docs", name: "框架文档", description: "开发框架、语言与工具官方文档" },
  { id: "ai", name: "AI 工具", description: "对话、创作、编程与模型平台" },
  {
    id: "inspiration",
    name: "灵感采集",
    description: "设计案例、视觉灵感与作品展示",
  },
  {
    id: "prototype",
    name: "原型设计",
    description: "界面、流程与交互原型工具",
  },
  {
    id: "community",
    name: "开发社区",
    description: "代码托管、问答与技术交流",
  },
  { id: "ui", name: "UI 组件库", description: "前端组件、样式与设计系统" },
  { id: "assets", name: "素材资源", description: "图片、图标、字体与配色素材" },
  { id: "office", name: "文档办公", description: "协作、文档与团队工作空间" },
  { id: "learning", name: "学习资源", description: "课程、教程与练习平台" },
  {
    id: "productivity",
    name: "效率工具",
    description: "任务、自动化与个人效率工具",
  },
  { id: "data", name: "数据分析", description: "数据探索、可视化与分析平台" },
];

const categoryById = Object.fromEntries(
  categories.map((category) => [category.id, category]),
);

const entries = [
  [
    "common",
    [
      ["baidu", "百度", "https://www.baidu.com", "中文网页搜索与信息发现。"],
      [
        "google",
        "Google",
        "https://www.google.com",
        "全球搜索、地图、邮箱与在线服务入口。",
      ],
      [
        "bing",
        "Bing",
        "https://www.bing.com",
        "微软提供的网页搜索与图片搜索服务。",
      ],
      [
        "wikipedia",
        "Wikipedia",
        "https://www.wikipedia.org",
        "开放协作的在线百科全书。",
      ],
      [
        "zhihu",
        "知乎",
        "https://www.zhihu.com",
        "中文问答、知识分享与经验交流社区。",
      ],
      [
        "bilibili",
        "哔哩哔哩",
        "https://www.bilibili.com",
        "视频、课程与兴趣内容社区。",
      ],
      [
        "douban",
        "豆瓣",
        "https://www.douban.com",
        "书影音内容发现与兴趣交流社区。",
      ],
      [
        "weread",
        "微信读书",
        "https://weread.qq.com",
        "在线阅读、书籍推荐与读书交流平台。",
      ],
      [
        "sspai",
        "少数派",
        "https://sspai.com",
        "数字产品、效率方法与应用评测内容。",
      ],
      [
        "huxiu",
        "虎嗅",
        "https://www.huxiu.com",
        "科技、商业与创业领域的资讯平台。",
      ],
      ["36kr", "36氪", "https://36kr.com", "创业、科技与新经济资讯平台。"],
      [
        "tencent-video",
        "腾讯视频",
        "https://v.qq.com",
        "影视、纪录片与在线视频平台。",
      ],
    ],
  ],
  [
    "docs",
    [
      [
        "vue",
        "Vue.js",
        "https://vuejs.org",
        "渐进式 JavaScript 框架官方文档。",
      ],
      [
        "react",
        "React",
        "https://react.dev",
        "构建用户界面的 React 官方文档。",
      ],
      [
        "angular",
        "Angular",
        "https://angular.dev",
        "Google 维护的 Web 应用框架文档。",
      ],
      [
        "svelte",
        "Svelte",
        "https://svelte.dev",
        "编译型前端框架与组件开发文档。",
      ],
      ["nuxt", "Nuxt", "https://nuxt.com", "基于 Vue 的全栈 Web 框架文档。"],
      [
        "nextjs",
        "Next.js",
        "https://nextjs.org",
        "React 全栈应用框架官方文档。",
      ],
      [
        "vite",
        "Vite",
        "https://vite.dev",
        "快速前端构建工具与开发服务器文档。",
      ],
      [
        "webpack",
        "webpack",
        "https://webpack.js.org",
        "JavaScript 模块打包工具官方文档。",
      ],
      [
        "typescript",
        "TypeScript",
        "https://www.typescriptlang.org",
        "JavaScript 的静态类型扩展与官方手册。",
      ],
      [
        "nodejs",
        "Node.js",
        "https://nodejs.org/docs/latest/api",
        "Node.js 运行时 API 与开发指南。",
      ],
      [
        "mdn",
        "MDN Web Docs",
        "https://developer.mozilla.org",
        "HTML、CSS、JavaScript 与 Web API 权威文档。",
      ],
      [
        "python",
        "Python 文档",
        "https://docs.python.org/3",
        "Python 语言与标准库官方文档。",
      ],
    ],
  ],
  [
    "ai",
    [
      [
        "chatgpt",
        "ChatGPT",
        "https://chatgpt.com",
        "通用对话、写作、分析与编程 AI 助手。",
      ],
      [
        "claude",
        "Claude",
        "https://claude.ai",
        "适合长文本理解、分析与编程协作的 AI 助手。",
      ],
      [
        "gemini",
        "Gemini",
        "https://gemini.google.com",
        "Google 的多模态 AI 助手与创作工具。",
      ],
      [
        "perplexity",
        "Perplexity",
        "https://www.perplexity.ai",
        "带来源检索的 AI 搜索与问答工具。",
      ],
      [
        "deepseek",
        "DeepSeek",
        "https://www.deepseek.com",
        "面向推理、对话与代码场景的 AI 平台。",
      ],
      [
        "kimi",
        "Kimi",
        "https://kimi.moonshot.cn",
        "支持长文本阅读与资料整理的 AI 助手。",
      ],
      [
        "qwen",
        "通义千问",
        "https://tongyi.aliyun.com",
        "阿里云提供的中文对话与内容创作助手。",
      ],
      [
        "doubao",
        "豆包",
        "https://www.doubao.com",
        "面向日常问答、写作与创作的 AI 助手。",
      ],
      [
        "huggingface",
        "Hugging Face",
        "https://huggingface.co",
        "开源模型、数据集与机器学习社区。",
      ],
      [
        "midjourney",
        "Midjourney",
        "https://www.midjourney.com",
        "AI 图像生成与视觉创作平台。",
      ],
      [
        "runway",
        "Runway",
        "https://runwayml.com",
        "AI 视频生成与视觉创作工具。",
      ],
      [
        "cursor",
        "Cursor",
        "https://www.cursor.com",
        "面向开发者的 AI 编程编辑器。",
      ],
    ],
  ],
  [
    "inspiration",
    [
      [
        "dribbble",
        "Dribbble",
        "https://dribbble.com",
        "设计师作品展示与视觉灵感社区。",
      ],
      [
        "behance",
        "Behance",
        "https://www.behance.net",
        "Adobe 旗下的创意作品展示平台。",
      ],
      [
        "awwwards",
        "Awwwards",
        "https://www.awwwards.com",
        "优秀网站设计与数字体验案例平台。",
      ],
      [
        "pinterest",
        "Pinterest",
        "https://www.pinterest.com",
        "图片收藏、主题灵感与视觉发现平台。",
      ],
      ["muzli", "Muzli", "https://muz.li", "面向设计师的每日视觉灵感聚合。"],
      [
        "land-book",
        "Land-book",
        "https://land-book.com",
        "精选落地页与网站设计案例。",
      ],
      [
        "designspiration",
        "Designspiration",
        "https://www.designspiration.com",
        "设计、摄影与配色灵感收藏工具。",
      ],
      [
        "arena",
        "Are.na",
        "https://www.are.na",
        "适合长期整理研究与视觉资料的收藏社区。",
      ],
      [
        "mobbin",
        "Mobbin",
        "https://mobbin.com",
        "移动端产品界面与交互案例库。",
      ],
      [
        "onepagelove",
        "One Page Love",
        "https://onepagelove.com",
        "单页网站与落地页设计灵感库。",
      ],
    ],
  ],
  [
    "prototype",
    [
      [
        "figma",
        "Figma",
        "https://www.figma.com",
        "实时协作的 UI 设计与原型工具。",
      ],
      [
        "sketch",
        "Sketch",
        "https://www.sketch.com",
        "面向产品团队的界面设计与协作工具。",
      ],
      [
        "framer",
        "Framer",
        "https://www.framer.com",
        "设计、发布与维护网站的视觉化工具。",
      ],
      [
        "penpot",
        "Penpot",
        "https://penpot.app",
        "开源的 UI 设计与原型协作平台。",
      ],
      [
        "axure",
        "Axure",
        "https://www.axure.com",
        "复杂交互与产品原型设计工具。",
      ],
      [
        "mockplus",
        "摹客",
        "https://www.mockplus.cn",
        "中文界面原型、协作与交付平台。",
      ],
      ["modao", "墨刀", "https://modao.cc", "在线原型设计与团队协作工具。"],
      [
        "protopie",
        "ProtoPie",
        "https://www.protopie.io",
        "高保真交互原型与传感器交互工具。",
      ],
      [
        "justinmind",
        "Justinmind",
        "https://www.justinmind.com",
        "Web 与移动产品原型设计工具。",
      ],
      [
        "whimsical",
        "Whimsical",
        "https://whimsical.com",
        "流程图、线框图与协作白板工具。",
      ],
    ],
  ],
  [
    "community",
    [
      [
        "github",
        "GitHub",
        "https://github.com",
        "代码托管、开源协作与项目管理平台。",
      ],
      [
        "gitlab",
        "GitLab",
        "https://gitlab.com",
        "集成代码托管、CI/CD 与项目管理的平台。",
      ],
      [
        "gitee",
        "Gitee",
        "https://gitee.com",
        "面向中文开发者的代码托管与开源平台。",
      ],
      [
        "stackoverflow",
        "Stack Overflow",
        "https://stackoverflow.com",
        "开发者技术问答与解决方案社区。",
      ],
      [
        "v2ex",
        "V2EX",
        "https://www.v2ex.com",
        "面向创意工作者与开发者的交流社区。",
      ],
      [
        "segmentfault",
        "SegmentFault",
        "https://segmentfault.com",
        "中文开发者问答与技术文章社区。",
      ],
      [
        "juejin",
        "掘金",
        "https://juejin.cn",
        "中文技术文章、课程与开发者社区。",
      ],
      [
        "csdn",
        "CSDN",
        "https://www.csdn.net",
        "中文 IT 技术博客与开发者服务平台。",
      ],
      [
        "cnblogs",
        "博客园",
        "https://www.cnblogs.com",
        "开发者博客与技术交流社区。",
      ],
      [
        "reddit-programming",
        "Reddit Programming",
        "https://www.reddit.com/r/programming",
        "全球开发者讨论与技术资讯社区。",
      ],
      [
        "devto",
        "DEV Community",
        "https://dev.to",
        "面向软件开发者的文章与交流社区。",
      ],
      [
        "codepen",
        "CodePen",
        "https://codepen.io",
        "前端代码实验、作品展示与社区。",
      ],
    ],
  ],
  [
    "ui",
    [
      [
        "ant-design",
        "Ant Design",
        "https://ant.design",
        "企业级 React UI 组件库与设计规范。",
      ],
      [
        "element-plus",
        "Element Plus",
        "https://element-plus.org",
        "Vue 3 桌面端组件库。",
      ],
      [
        "naive-ui",
        "Naive UI",
        "https://www.naiveui.com",
        "Vue 3 TypeScript 组件库。",
      ],
      [
        "vuetify",
        "Vuetify",
        "https://vuetifyjs.com",
        "基于 Material Design 的 Vue 组件库。",
      ],
      [
        "quasar",
        "Quasar",
        "https://quasar.dev",
        "跨平台 Vue 应用框架与组件库。",
      ],
      [
        "bootstrap",
        "Bootstrap",
        "https://getbootstrap.com",
        "经典的响应式前端 CSS 组件库。",
      ],
      [
        "tailwind",
        "Tailwind CSS",
        "https://tailwindcss.com",
        "实用优先的 CSS 框架与设计工具。",
      ],
      [
        "radix",
        "Radix UI",
        "https://www.radix-ui.com",
        "无样式、可访问的 React 原语组件。",
      ],
      [
        "shadcn",
        "shadcn/ui",
        "https://ui.shadcn.com",
        "基于 Tailwind 的可组合 React 组件集合。",
      ],
      ["mui", "MUI", "https://mui.com", "React Material Design 组件库。"],
      [
        "chakra",
        "Chakra UI",
        "https://chakra-ui.com",
        "简单、模块化且可访问的 React 组件库。",
      ],
      [
        "headless-ui",
        "Headless UI",
        "https://headlessui.com",
        "无样式且可访问的 UI 组件。",
      ],
    ],
  ],
  [
    "assets",
    [
      [
        "unsplash",
        "Unsplash",
        "https://unsplash.com",
        "高质量免费图片素材库。",
      ],
      [
        "pexels",
        "Pexels",
        "https://www.pexels.com",
        "免费图片与视频素材平台。",
      ],
      [
        "pixabay",
        "Pixabay",
        "https://pixabay.com",
        "图片、插画、视频与音乐素材库。",
      ],
      [
        "iconfont",
        "Iconfont",
        "https://www.iconfont.cn",
        "阿里巴巴矢量图标与素材库。",
      ],
      [
        "icons8",
        "Icons8",
        "https://icons8.com",
        "图标、插画、照片与设计工具集合。",
      ],
      [
        "flaticon",
        "Flaticon",
        "https://www.flaticon.com",
        "图标与贴图素材平台。",
      ],
      [
        "fontawesome",
        "Font Awesome",
        "https://fontawesome.com",
        "常用图标字体与 SVG 图标库。",
      ],
      [
        "google-fonts",
        "Google Fonts",
        "https://fonts.google.com",
        "开放字体与 Web 字体资源库。",
      ],
      [
        "dafont",
        "DaFont",
        "https://www.dafont.com",
        "丰富的字体下载与分类目录。",
      ],
      [
        "coolors",
        "Coolors",
        "https://coolors.co",
        "快速生成与探索配色方案的工具。",
      ],
      [
        "carbon",
        "Carbon",
        "https://carbon.now.sh",
        "把代码生成精美图片的工具。",
      ],
      [
        "undraw",
        "unDraw",
        "https://undraw.co/illustrations",
        "可自定义颜色的开源插画库。",
      ],
    ],
  ],
  [
    "office",
    [
      [
        "notion",
        "Notion",
        "https://www.notion.so",
        "笔记、知识库、数据库与团队协作工作空间。",
      ],
      [
        "feishu",
        "飞书",
        "https://www.feishu.cn",
        "文档、会议、通讯与团队协作平台。",
      ],
      [
        "tencent-docs",
        "腾讯文档",
        "https://docs.qq.com",
        "在线文档、表格与多人协作工具。",
      ],
      [
        "shimo",
        "石墨文档",
        "https://shimo.im",
        "在线文档、表格与团队协作空间。",
      ],
      [
        "google-docs",
        "Google Docs",
        "https://docs.google.com",
        "在线文档编辑与实时协作工具。",
      ],
      [
        "microsoft-365",
        "Microsoft 365",
        "https://www.microsoft.com/microsoft-365",
        "Office 文档、邮箱与云端办公服务。",
      ],
      [
        "airtable",
        "Airtable",
        "https://www.airtable.com",
        "融合表格、数据库与协作的工作平台。",
      ],
      [
        "trello",
        "Trello",
        "https://trello.com",
        "基于看板的任务与项目管理工具。",
      ],
      [
        "asana",
        "Asana",
        "https://asana.com",
        "团队任务、项目与工作流管理平台。",
      ],
      [
        "processon",
        "ProcessOn",
        "https://www.processon.com",
        "流程图、思维导图与协作绘图工具。",
      ],
      [
        "dropbox",
        "Dropbox",
        "https://www.dropbox.com",
        "文件同步、共享与团队协作服务。",
      ],
      [
        "onedrive",
        "OneDrive",
        "https://onedrive.live.com",
        "微软云存储与文件协作服务。",
      ],
    ],
  ],
  [
    "learning",
    [
      [
        "coursera",
        "Coursera",
        "https://www.coursera.org",
        "高校与企业课程、证书与在线学习平台。",
      ],
      ["edx", "edX", "https://www.edx.org", "大学公开课与职业技能学习平台。"],
      [
        "khan",
        "Khan Academy",
        "https://www.khanacademy.org",
        "免费的基础教育与技能学习平台。",
      ],
      [
        "icourse163",
        "中国大学 MOOC",
        "https://www.icourse163.org",
        "中文高校课程与在线学习平台。",
      ],
      [
        "xuetangx",
        "学堂在线",
        "https://www.xuetangx.com",
        "清华大学等高校在线课程平台。",
      ],
      [
        "mit-ocw",
        "MIT OpenCourseWare",
        "https://ocw.mit.edu",
        "麻省理工学院开放课程资料库。",
      ],
      [
        "freecodecamp",
        "freeCodeCamp",
        "https://www.freecodecamp.org",
        "免费编程课程、练习与认证平台。",
      ],
      [
        "codecademy",
        "Codecademy",
        "https://www.codecademy.com",
        "交互式编程与技术课程平台。",
      ],
      [
        "leetcode",
        "LeetCode",
        "https://leetcode.com",
        "算法练习、竞赛与面试准备平台。",
      ],
      [
        "nowcoder",
        "牛客网",
        "https://www.nowcoder.com",
        "编程练习、面试题与求职学习平台。",
      ],
      [
        "gutenberg",
        "Project Gutenberg",
        "https://www.gutenberg.org",
        "免费电子书与公共领域文本库。",
      ],
      ["ted", "TED", "https://www.ted.com", "演讲、观点与跨学科知识内容平台。"],
    ],
  ],
  [
    "productivity",
    [
      [
        "todoist",
        "Todoist",
        "https://todoist.com",
        "跨平台任务管理与个人计划工具。",
      ],
      [
        "ticktick",
        "滴答清单",
        "https://dida365.com",
        "任务、日历与习惯管理工具。",
      ],
      [
        "pomofocus",
        "Pomofocus",
        "https://pomofocus.io",
        "基于番茄工作法的专注计时器。",
      ],
      [
        "forest",
        "Forest",
        "https://www.forestapp.cc",
        "通过种树机制帮助保持专注的工具。",
      ],
      [
        "rescuetime",
        "RescueTime",
        "https://www.rescuetime.com",
        "自动记录与分析数字设备使用时间。",
      ],
      [
        "zapier",
        "Zapier",
        "https://zapier.com",
        "连接不同应用并自动化重复工作。",
      ],
      [
        "ifttt",
        "IFTTT",
        "https://ifttt.com",
        "通过条件规则连接服务与智能设备。",
      ],
      [
        "calendly",
        "Calendly",
        "https://calendly.com",
        "在线预约、日程安排与会议协调工具。",
      ],
      [
        "loom",
        "Loom",
        "https://www.loom.com",
        "录制屏幕与摄像头视频进行异步沟通。",
      ],
      [
        "grammarly",
        "Grammarly",
        "https://www.grammarly.com",
        "英文写作检查、改写与表达建议工具。",
      ],
      [
        "deepl",
        "DeepL",
        "https://www.deepl.com",
        "高质量机器翻译与写作辅助工具。",
      ],
      [
        "ilovepdf",
        "iLovePDF",
        "https://www.ilovepdf.com",
        "在线 PDF 合并、转换与压缩工具。",
      ],
    ],
  ],
  [
    "data",
    [
      [
        "kaggle",
        "Kaggle",
        "https://www.kaggle.com",
        "数据科学竞赛、数据集与 Notebook 平台。",
      ],
      [
        "tableau",
        "Tableau",
        "https://www.tableau.com",
        "商业智能与数据可视化平台。",
      ],
      [
        "powerbi",
        "Power BI",
        "https://powerbi.microsoft.com",
        "微软数据分析与商业报表平台。",
      ],
      [
        "observable",
        "Observable",
        "https://observablehq.com",
        "基于 JavaScript 的数据探索与可视化平台。",
      ],
      [
        "datawrapper",
        "Datawrapper",
        "https://www.datawrapper.de",
        "无需编码制作图表与地图的工具。",
      ],
      [
        "jupyter",
        "Jupyter",
        "https://jupyter.org",
        "交互式数据分析与代码 Notebook 工具。",
      ],
      [
        "colab",
        "Google Colab",
        "https://colab.research.google.com",
        "基于云端 Notebook 的 Python 数据分析环境。",
      ],
      [
        "looker",
        "Looker Studio",
        "https://lookerstudio.google.com",
        "连接数据源并制作在线报表的平台。",
      ],
      [
        "flourish",
        "Flourish",
        "https://flourish.studio",
        "制作交互式图表与数据故事的工具。",
      ],
      [
        "our-world-in-data",
        "Our World in Data",
        "https://ourworldindata.org",
        "全球问题相关的公开数据与可视化研究。",
      ],
    ],
  ],
];

export const websiteCatalogCategories = categories;

const rawWebsiteCatalog = [
  ...entries.flatMap(([categoryId, categoryEntries]) => {
    const category = categoryById[categoryId];
    return categoryEntries.map(([id, name, url, summary]) =>
      site(id, name, url, summary, category.id, category.name),
    );
  }),
  ...expandedSites,
];

const usedCatalogUrls = new Set();
const canonicalCatalogUrl = (value) => {
  try {
    const parsed = new URL(value);
    return `${parsed.protocol}//${parsed.hostname.toLowerCase()}${parsed.pathname.replace(/\/+$/, "") || "/"}`;
  } catch {
    return String(value || "").trim().toLowerCase();
  }
};

export const websiteCatalog = rawWebsiteCatalog.filter((website) => {
  const key = canonicalCatalogUrl(website.url);
  if (!key || usedCatalogUrls.has(key)) return false;
  usedCatalogUrls.add(key);
  return true;
});
