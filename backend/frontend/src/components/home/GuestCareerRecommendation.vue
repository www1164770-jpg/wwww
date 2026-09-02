<template>
  <div class="guest-career">
    <header class="guest-career__heading">
      <span class="eyebrow reveal-child" style="--reveal-delay: 0ms"
        >职业推荐</span
      >
      <AnimatedPageTitle
        class="reveal-child reveal-title"
        style="--reveal-delay: 80ms"
        as="h2"
        :animation="false"
      >
        发现适合你职业的网站工具
      </AnimatedPageTitle>
      <p class="reveal-child reveal-description" style="--reveal-delay: 150ms">
        选择你的职业，快速浏览常用网站和工具。登录并完成问卷后，可获得更加精准的个性化推荐。
      </p>
    </header>

    <div
      class="guest-career__tabs reveal-child"
      style="--reveal-delay: 210ms"
      role="tablist"
      aria-label="选择职业"
    >
      <button
        v-for="career in guestCareers"
        :key="career.code"
        type="button"
        role="tab"
        :aria-selected="selectedCareer === career.code"
        :class="{ active: selectedCareer === career.code }"
        @click="selectGuestCareer(career.code)"
      >
        {{ career.label }}
      </button>
    </div>

    <div
      class="guest-career__label-row reveal-child reveal-description"
      style="--reveal-delay: 250ms"
    >
      <span>职业通用推荐</span>
      <small>登录后升级为个性化推荐</small>
    </div>

    <div class="guest-career__grid">
      <a
        v-for="(site, index) in selectedSites"
        :key="site.url"
        class="guest-site-card reveal-child reveal-card"
        :class="{ 'card-refresh-item': guestCareerChanged }"
        :style="guestCardStyle(index)"
        :href="site.url"
        target="_blank"
        rel="noopener noreferrer"
        @click="emit('visit', site, $event)"
      >
        <span class="guest-site-card__head">
          <SiteLogo :name="site.name" :url="site.url" size="md" />
          <strong>{{ site.name }}</strong>
        </span>
        <p>{{ site.description }}</p>
        <span class="guest-site-card__arrow" aria-hidden="true">↗</span>
      </a>
    </div>

    <aside class="guest-career__cta reveal-child" style="--reveal-delay: 650ms">
      <div>
        <h3>登录后获取更精准的网站推荐</h3>
        <p>
          完成职业问卷后，系统会结合你的能力、兴趣、使用目的和资源偏好，为你筛选更加适合的网站和工具。
        </p>
      </div>
      <button type="button" @click="emit('login')">登录获取精准推荐</button>
    </aside>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import AnimatedPageTitle from "../common/AnimatedPageTitle.vue";
import SiteLogo from "../site/SiteLogo.vue";

const emit = defineEmits(["visit", "login"]);

const guestCareers = [
  { code: "developer", label: "开发" },
  { code: "designer", label: "设计" },
  { code: "student", label: "学生" },
  { code: "office", label: "办公" },
  { code: "creator", label: "创作" },
  { code: "product_operation", label: "产品运营" },
];

const guestCareerSites = {
  developer: [
    ["GitHub", "https://github.com", "代码托管、版本管理与开发协作平台。"],
    [
      "Stack Overflow",
      "https://stackoverflow.com",
      "面向开发者的技术问答与经验社区。",
    ],
    [
      "MDN Web Docs",
      "https://developer.mozilla.org/zh-CN/",
      "权威的 Web 标准、API 与前端开发文档。",
    ],
    [
      "Vercel",
      "https://vercel.com",
      "面向现代 Web 应用的构建、预览与部署平台。",
    ],
    [
      "Docker",
      "https://www.docker.com",
      "用于容器化开发、交付和运行应用的平台。",
    ],
    [
      "Postman",
      "https://www.postman.com",
      "API 设计、调试、测试与团队协作工具。",
    ],
    [
      "GitLab",
      "https://gitlab.com",
      "集成代码托管、CI/CD 与项目协作的 DevOps 平台。",
    ],
    [
      "CodePen",
      "https://codepen.io",
      "在线编写和展示 HTML、CSS 与 JavaScript 示例。",
    ],
    [
      "Replit",
      "https://replit.com",
      "支持多种语言的在线编程、运行与协作环境。",
    ],
    ["LeetCode", "https://leetcode.cn", "通过算法题库练习编程并准备技术面试。"],
    [
      "Hugging Face",
      "https://huggingface.co",
      "查找、体验和共享开源 AI 模型与数据集。",
    ],
    [
      "npm",
      "https://www.npmjs.com",
      "JavaScript 软件包检索、发布与依赖管理平台。",
    ],
    ["PyPI", "https://pypi.org", "Python 官方第三方软件包索引与发布平台。"],
    [
      "VS Code",
      "https://code.visualstudio.com",
      "可扩展的跨平台代码编辑器与开发工具。",
    ],
    [
      "Supabase",
      "https://supabase.com",
      "提供数据库、认证和存储能力的开源后端平台。",
    ],
  ],
  designer: [
    [
      "Figma",
      "https://www.figma.com",
      "界面设计、原型制作与产品团队协作平台。",
    ],
    [
      "Dribbble",
      "https://dribbble.com",
      "设计师作品展示、灵感发现与交流社区。",
    ],
    [
      "Behance",
      "https://www.behance.net",
      "覆盖多类创意领域的作品集展示平台。",
    ],
    [
      "Canva",
      "https://www.canva.com",
      "适合快速制作海报、演示和社交媒体视觉内容。",
    ],
    ["Coolors", "https://coolors.co", "快速生成、调整和探索配色方案的工具。"],
    ["Unsplash", "https://unsplash.com", "提供高质量摄影图片的免费素材平台。"],
    [
      "Pixabay",
      "https://pixabay.com",
      "提供图片、插画、矢量图和视频等免费素材。",
    ],
    [
      "Adobe Express",
      "https://www.adobe.com/express/",
      "快速制作社交图片、短视频和品牌内容。",
    ],
    [
      "Framer",
      "https://www.framer.com",
      "将交互设计快速发布为响应式网站的平台。",
    ],
    [
      "Awwwards",
      "https://www.awwwards.com",
      "发现优秀网页设计案例、趋势与行业作品。",
    ],
    [
      "Font Awesome",
      "https://fontawesome.com",
      "覆盖多种场景的矢量图标库与工具集。",
    ],
    [
      "Google Fonts",
      "https://fonts.google.com",
      "浏览并使用开源网页字体与字族资源。",
    ],
    [
      "Iconfont",
      "https://www.iconfont.cn",
      "阿里巴巴提供的图标搜索、管理和协作平台。",
    ],
    ["UI8", "https://ui8.net", "提供 UI 套件、字体、图标和设计资产市场。"],
    [
      "Designspiration",
      "https://www.designspiration.com",
      "通过视觉收藏探索设计、配色与创意灵感。",
    ],
  ],
  student: [
    [
      "中国大学MOOC",
      "https://www.icourse163.org",
      "汇集中国高校课程的综合在线学习平台。",
    ],
    [
      "Coursera",
      "https://www.coursera.org",
      "提供全球大学与机构课程的在线学习平台。",
    ],
    [
      "Khan Academy",
      "https://www.khanacademy.org",
      "覆盖基础学科的免费课程与练习资源。",
    ],
    ["Quizlet", "https://quizlet.com", "通过记忆卡、测试和练习辅助知识复习。"],
    [
      "Notion",
      "https://www.notion.so",
      "用于课堂笔记、知识整理和学习规划的工作空间。",
    ],
    [
      "Zotero",
      "https://www.zotero.org",
      "收集、管理和引用论文文献的研究工具。",
    ],
    [
      "哔哩哔哩",
      "https://www.bilibili.com",
      "通过课程视频和知识区内容辅助自主学习。",
    ],
    ["edX", "https://www.edx.org", "学习全球高校和机构提供的在线课程与项目。"],
    [
      "学堂在线",
      "https://www.xuetangx.com",
      "汇集清华等高校课程的中文在线学习平台。",
    ],
    [
      "DeepL",
      "https://www.deepl.com/translator",
      "用于外语资料阅读和写作辅助的智能翻译工具。",
    ],
    [
      "Wolfram Alpha",
      "https://www.wolframalpha.com",
      "提供数学计算、科学数据和知识查询能力。",
    ],
    ["中国知网", "https://www.cnki.net", "检索中文论文、期刊和学术研究资料。"],
    [
      "ResearchGate",
      "https://www.researchgate.net",
      "查找学术成果并与研究人员交流的社区。",
    ],
    ["GitMind", "https://gitmind.cn", "在线制作思维导图、流程图和学习笔记。"],
    ["XMind", "https://xmind.app", "用结构化思维导图整理知识与学习计划。"],
  ],
  office: [
    [
      "Microsoft 365",
      "https://www.microsoft.com/microsoft-365",
      "办公文档、邮件、会议与团队协作工具套件。",
    ],
    [
      "Notion",
      "https://www.notion.so",
      "整合文档、知识库、任务和项目管理的工作空间。",
    ],
    [
      "Trello",
      "https://trello.com",
      "通过可视化看板管理任务、流程和团队项目。",
    ],
    ["Slack", "https://slack.com", "面向团队的频道式即时沟通与工作协作平台。"],
    ["Zoom", "https://zoom.us", "支持视频会议、线上沟通和远程协作的平台。"],
    [
      "Smallpdf",
      "https://smallpdf.com",
      "提供转换、压缩、合并等 PDF 在线处理能力。",
    ],
    [
      "飞书",
      "https://www.feishu.cn",
      "集即时沟通、文档、会议和多维表格于一体。",
    ],
    [
      "腾讯文档",
      "https://docs.qq.com",
      "支持多人实时编辑文档、表格和演示文稿。",
    ],
    ["石墨文档", "https://shimo.im", "面向团队的云端文档编辑与内容协作平台。"],
    [
      "ProcessOn",
      "https://www.processon.com",
      "在线绘制流程图、思维导图和组织结构图。",
    ],
    [
      "Google Docs",
      "https://docs.google.com",
      "在线创建、编辑并协作文档和表格。",
    ],
    [
      "Dropbox",
      "https://www.dropbox.com",
      "跨设备同步、共享和协作管理云端文件。",
    ],
    [
      "百度网盘",
      "https://pan.baidu.com",
      "用于文件存储、备份、同步与分享的云盘。",
    ],
    ["Miro", "https://miro.com", "支持会议共创、流程梳理和规划的在线白板。"],
    ["Todoist", "https://todoist.com", "跨平台管理个人待办、日程和团队任务。"],
  ],
  creator: [
    [
      "Canva",
      "https://www.canva.com",
      "快速制作图片、视频与社交媒体视觉内容。",
    ],
    [
      "CapCut",
      "https://www.capcut.com",
      "提供剪辑、字幕和模板的视频内容制作工具。",
    ],
    [
      "Unsplash",
      "https://unsplash.com",
      "适合创作配图使用的高质量摄影素材平台。",
    ],
    [
      "Pixabay",
      "https://pixabay.com",
      "提供图片、插画、视频与音频等免费素材。",
    ],
    [
      "Audacity",
      "https://www.audacityteam.org",
      "开源免费的多轨音频录制与编辑软件。",
    ],
    [
      "YouTube Studio",
      "https://studio.youtube.com",
      "管理视频内容、频道数据和观众互动的平台。",
    ],
    [
      "剪映",
      "https://www.capcut.cn",
      "面向中文创作者的视频剪辑、字幕和模板工具。",
    ],
    [
      "Runway",
      "https://runwayml.com",
      "使用生成式 AI 创建和编辑图片及视频内容。",
    ],
    [
      "Pexels",
      "https://www.pexels.com",
      "提供可用于内容创作的免费图片和视频素材。",
    ],
    ["Mixkit", "https://mixkit.co", "下载免费视频、音乐、音效和视频模板素材。"],
    [
      "SoundCloud",
      "https://soundcloud.com",
      "发布、发现和分享音乐及音频作品的平台。",
    ],
    ["Artlist", "https://artlist.io", "为视频创作提供授权音乐、音效与素材。"],
    ["Coverr", "https://coverr.co", "提供适合网页和视频项目的免费影像素材。"],
    ["OBS Studio", "https://obsproject.com", "开源的直播推流与屏幕录制软件。"],
    [
      "Descript",
      "https://www.descript.com",
      "以文本方式编辑播客、录音和视频内容。",
    ],
  ],
  product_operation: [
    [
      "Notion",
      "https://www.notion.so",
      "用于产品文档、需求整理和团队知识管理。",
    ],
    [
      "Trello",
      "https://trello.com",
      "通过看板管理产品任务、运营节奏和项目流程。",
    ],
    [
      "Google Trends",
      "https://trends.google.com",
      "观察搜索趋势、话题热度和用户兴趣变化。",
    ],
    [
      "Similarweb",
      "https://www.similarweb.com",
      "分析网站流量、渠道表现和竞品市场数据。",
    ],
    [
      "Miro",
      "https://miro.com",
      "用于产品梳理、头脑风暴和远程协作的在线白板。",
    ],
    [
      "Typeform",
      "https://www.typeform.com",
      "创建在线问卷、用户调研和互动表单的平台。",
    ],
    ["飞书", "https://www.feishu.cn", "协同管理运营内容、项目进度与团队信息。"],
    ["墨刀", "https://modao.cc", "快速制作产品原型、交互演示并收集团队反馈。"],
    [
      "MasterGo",
      "https://mastergo.com",
      "面向产品团队的界面设计与实时协作平台。",
    ],
    [
      "百度统计",
      "https://tongji.baidu.com",
      "分析网站流量来源、访客行为和转化效果。",
    ],
    [
      "GrowingIO",
      "https://www.growingio.com",
      "提供用户行为分析、增长洞察和运营数据能力。",
    ],
    [
      "友盟+",
      "https://www.umeng.com",
      "覆盖移动应用和网站的数据统计与运营分析。",
    ],
    ["石墨文档", "https://shimo.im", "协作编写运营方案、排期表和共享资料。"],
    [
      "ProcessOn",
      "https://www.processon.com",
      "梳理业务流程、用户旅程和产品结构。",
    ],
    [
      "Figma",
      "https://www.figma.com",
      "协作评审产品界面、原型和设计交付内容。",
    ],
  ],
};

const selectedCareer = ref(guestCareers[0].code);
const guestCareerChanged = ref(false);
const selectedSites = computed(() =>
  (guestCareerSites[selectedCareer.value] || []).map(
    ([name, url, description]) => ({
      name,
      url,
      description,
      external_only: true,
    }),
  ),
);

function guestCardStyle(index) {
  return {
    "--reveal-delay": `${290 + Math.min(index * 35, 350)}ms`,
    "--refresh-delay": `${Math.min(index * 24, 168)}ms`,
  };
}

function selectGuestCareer(careerCode) {
  if (selectedCareer.value === careerCode) return;
  guestCareerChanged.value = true;
  selectedCareer.value = careerCode;
}
</script>

<style scoped>
.guest-career {
  display: grid;
  width: min(var(--container), calc(100% - 40px));
  margin: 0 auto;
  gap: 24px;
}
.guest-career__heading {
  display: grid;
  gap: 8px;
  max-width: 760px;
}
.guest-career__heading h2 {
  margin: 0;
  color: var(--app-text-primary);
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1.15;
}
.guest-career__heading p {
  margin: 0;
  color: var(--app-text-secondary);
  line-height: 1.7;
}
.guest-career__tabs {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding: 2px 2px 6px;
  scrollbar-width: thin;
}
.guest-career__tabs button {
  flex: 0 0 auto;
  min-height: 40px;
  padding: 8px 18px;
  border: 1px solid var(--app-border);
  border-radius: 999px;
  color: var(--app-text-secondary);
  background: var(--app-panel-soft-bg);
  font-weight: 700;
  transition: 180ms ease;
}
.guest-career__tabs button:hover {
  color: var(--app-text-primary);
  border-color: rgba(255, 112, 88, 0.46);
}
.guest-career__tabs button.active {
  color: var(--app-text-primary);
  border-color: rgba(255, 112, 88, 0.58);
  background: rgba(255, 112, 88, 0.13);
}
.guest-career__label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.guest-career__label-row span {
  color: var(--app-text-primary);
  font-weight: 800;
}
.guest-career__label-row small {
  color: var(--app-text-muted);
}
.guest-career__grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
}
.guest-site-card {
  position: relative;
  display: grid;
  min-width: 0;
  min-height: 118px;
  gap: 8px;
  padding: 14px 15px;
  border: 1px solid var(--app-border);
  border-radius: 18px;
  color: inherit;
  background: var(--app-card-bg);
  box-shadow: var(--app-card-shadow);
  text-decoration: none;
  backdrop-filter: blur(var(--app-blur));
  transition: 180ms ease;
}
.guest-site-card:hover {
  border-color: rgba(255, 112, 88, 0.42);
  background: var(--app-card-hover-bg);
  box-shadow: var(--app-card-hover-shadow);
  transform: translateY(-2px);
}
.guest-site-card__head {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 9px;
}
.guest-site-card__head strong {
  overflow: hidden;
  color: var(--app-text-primary);
  font-size: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.guest-site-card p {
  display: -webkit-box;
  overflow: hidden;
  margin: 0;
  padding-right: 18px;
  color: var(--app-text-secondary);
  font-size: 13px;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.guest-site-card__arrow {
  position: absolute;
  right: 14px;
  bottom: 12px;
  color: var(--color-primary);
  font-size: 18px;
}
.guest-career__cta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
  padding: 24px 26px;
  border: 1px solid var(--app-border);
  border-radius: 20px;
  background: var(--app-panel-soft-bg);
}
.guest-career__cta h3 {
  margin: 0 0 7px;
  color: var(--app-text-primary);
  font-size: 18px;
}
.guest-career__cta p {
  max-width: 760px;
  margin: 0;
  color: var(--app-text-secondary);
  line-height: 1.65;
}
.guest-career__cta button {
  flex: 0 0 auto;
  min-height: 44px;
  padding: 10px 20px;
  border: 1px solid var(--color-primary);
  border-radius: 999px;
  color: #fff;
  background: var(--color-primary);
  font-weight: 800;
}
.guest-career__cta button:hover {
  background: var(--color-primary-dark);
}
@media (max-width: 1199px) {
  .guest-career__grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 799px) {
  .guest-career__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .guest-career__cta {
    align-items: flex-start;
    flex-direction: column;
  }
}
@media (max-width: 600px) {
  .guest-career {
    width: min(100% - 28px, var(--container));
    gap: 20px;
  }
  .guest-career__grid {
    grid-template-columns: 1fr;
  }
  .guest-career__label-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }
  .guest-career__cta {
    padding: 20px;
  }
  .guest-career__cta button {
    width: 100%;
  }
}
</style>
