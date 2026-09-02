"""Website-description quality rules and reviewed replacement profiles.

Descriptions describe a website's enduring purpose.  They must never be a
career-match explanation, nor a category-wide fallback copied to many sites.
This module is deliberately read-only; :mod:`apply_description_fixes` owns the
guarded database write path.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any, Iterable


RETIRED_GENERIC_DESCRIPTIONS = frozenset(
    {
        "提供适合当前职业方向的学习与实践资源。",
        "提供适合当前职业方向的工具与资源。",
        "提供搜索、资讯、阅读或日常信息服务。",
        "提供相关资源与服务。",
        "提供实用工具。",
        "适合当前职业方向使用。",
        "提供编程语言、框架或工程工具的官方文档。",
        "展示界面、品牌、插画或数字产品案例，适合收集视觉参考。",
        "提供对话、生成式创作、模型调用或 AI 开发服务。",
        "用于数据集探索、统计分析、报表或交互式可视化。",
        "支持页面结构、交互流程、线框或高保真原型制作。",
        "用于文档编辑、知识管理、会议协作或团队沟通。",
        "提供代码协作、技术问答、开源项目或开发者交流。",
        "用于竞品信息、市场趋势或产品技术栈调研。",
        "提供课程、公开课、编程练习或专业学习资料。",
        "提供可复用的 UI 组件、设计系统或前端样式资源。",
        "提供可视化、地图或三维图形开发能力。",
        "帮助管理任务、流程、时间或个人工作效率。",
        "提供图片、插画、图标、字体或颜色等设计素材。",
        "提供前端构建、代码质量或依赖管理能力。",
        "提供字体、色彩和无障碍视觉检查资源。",
        "提供开发调试、格式转换或性能检查工具。",
        "提供产品原型、线框或交互协作能力。",
        "用于任务安排、时间管理或个人效率提升。",
    }
)

# Backwards-compatible import used by the previous recovery script.
GENERIC_FALLBACKS = RETIRED_GENERIC_DESCRIPTIONS

# Only entries whose purpose is known from reviewed project data or a stable,
# well-known service profile belong here.  Unknown records remain review-only.
SPECIFIC_DESCRIPTIONS = {
    "飞猪旅行": "阿里旗下在线旅行平台，提供机票、酒店、火车票、度假及景点预订服务。",
    "去哪儿旅行": "在线旅行服务平台，提供机票、酒店、火车票、门票及旅游产品查询和预订。",
    "华为商城": "华为官方购物平台，销售手机、电脑、穿戴设备和智能家居等产品。",
    "小米商城": "小米官方购物平台，提供手机、智能硬件、家电及生态链产品。",
    "得物": "潮流商品交易与社区平台，覆盖球鞋、服饰、美妆和数码等品类。",
    "亚马逊中国": "亚马逊面向中国用户的在线服务入口，覆盖跨境购物、阅读及数字服务。",
    "当当网": "综合网络购物平台，以图书销售为特色，同时提供百货和数字阅读内容。",
    "唯品会": "品牌特卖电商平台，提供服饰、美妆、家居等商品的限时折扣销售。",
    "苏宁易购": "综合零售电商平台，提供家电、数码、家居及生活消费品购买服务。",
    "网易严选": "网易旗下生活方式电商平台，销售家居、食品、服饰和日用消费品。",
    "斗鱼直播": "在线直播平台，内容覆盖游戏直播、电竞赛事、娱乐及互动社区。",
    "虎牙直播": "以游戏和电竞内容为主的直播平台，同时提供娱乐和赛事直播。",
    "哔哩哔哩直播": "哔哩哔哩旗下直播服务，覆盖游戏、虚拟主播、娱乐及兴趣内容。",
    "夸克网盘": "夸克提供的云存储服务，可保存、同步、管理和分享个人文件。",
    "阿里云盘": "阿里巴巴推出的个人云存储服务，支持文件备份、同步、管理和分享。",
    "百度网盘": "百度提供的云存储服务，支持文件保存、备份、同步、分享和在线预览。",
    "QQ邮箱": "腾讯提供的电子邮件服务，支持邮件收发、附件管理和多端同步。",
    "网易邮箱": "网易提供的电子邮箱服务，支持个人及办公邮件收发和邮箱管理。",
    "钉钉": "企业协同办公平台，提供即时沟通、会议、考勤、文档和组织管理功能。",
    "微信": "腾讯推出的即时通讯与社交平台，支持聊天、公众号、小程序和支付等服务。",
    "支付宝": "数字支付与生活服务平台，覆盖支付、转账及多种便民服务。",
    "滴滴出行": "在线出行服务平台，提供网约车、出租车及多种城市交通服务。",
    "腾讯地图": "腾讯提供的地图与导航服务，支持地点查询、路线规划和实时导航。",
    "百度地图": "百度提供的地图服务，支持地点搜索、路线规划、公交查询及驾车导航。",
    "豆瓣": "以书籍、电影、音乐评分和兴趣社区为核心的文化内容平台。",
    "微信读书": "腾讯推出的数字阅读平台，提供电子书、听书和阅读笔记功能。",
    "少数派": "关注数字工具、效率方法和科技生活方式的内容社区。",
    "腾讯视频": "腾讯旗下在线视频平台，提供剧集、电影、综艺和纪录片内容。",
    "DuckDuckGo": "强调隐私保护的搜索引擎，减少对用户搜索行为的追踪。",
    "Startpage": "注重隐私保护的搜索引擎，可减少网页搜索中的用户追踪。",
    "Yandex": "提供网页、图片、地图和邮箱等服务的综合互联网平台。",
    "Brave Search": "Brave 推出的隐私搜索引擎，强调独立索引和减少追踪。",
    "Ecosia": "将搜索广告收入用于植树和环保项目的公益型搜索引擎。",
    "Internet Archive": "非营利数字档案馆，收录历史网页、书籍、音视频和软件资源。",
    "Wiktionary": "Wikimedia 旗下开放式多语言词典，提供词义、发音和词源信息。",
    "Wikimedia Commons": "Wikimedia 的开放媒体资源库，提供可自由使用的图像和音视频素材。",
    "Google News": "Google 的新闻聚合服务，汇集多家媒体的实时新闻与专题报道。",
    "Reuters": "国际新闻通讯机构，报道全球政治、财经、商业和突发新闻。",
    "BBC": "英国广播公司旗下资讯平台，提供国际新闻、文化、科技和视听内容。",
    "The Guardian": "英国新闻媒体平台，报道国际新闻、政治、文化、环境和社会议题。",
    "澎湃新闻": "中文时政与思想资讯平台，报道时事、财经、文化和社会新闻。",
    "界面新闻": "面向商业与财经领域的中文新闻平台，关注公司、产业和金融市场。",
    "财新网": "财经新闻与商业资讯平台，重点报道金融、经济、公司和公共政策。",
    "得到": "知识学习平台，提供课程、电子书、听书和个人成长内容。",
    "荔枝": "中文音频社区与播客平台，提供电台节目和声音内容。",
    "网易公开课": "汇集公开课程、演讲和知识视频的在线学习平台。",
    "腾讯新闻": "腾讯旗下新闻资讯平台，提供时政、社会、财经和热点报道。",
    "凤凰网": "综合中文资讯平台，报道新闻、财经、文化和国际时事。",
    "观察者网": "关注时政、国际关系和社会议题的中文新闻评论平台。",
    "知乎盐选": "知乎推出的付费内容服务，提供电子书、专栏和精选知识内容。",
    "喜马拉雅": "中文音频平台，提供有声书、播客、课程和知识类节目。",
    "人民网": "人民日报社旗下综合新闻平台，提供时政、国际、社会和财经资讯。",
    "新华网": "新华社主办的综合新闻网站，提供国内外新闻及政务、财经等资讯。",
    "携程": "在线旅行服务平台，提供酒店、机票、火车票、度假和旅游预订服务。",
    "美团": "本地生活服务平台，提供餐饮外卖、到店消费、酒店和休闲娱乐服务。",
    "饿了么": "即时配送与外卖服务平台，可在线订餐并获取本地生活配送服务。",
    "大众点评": "本地生活消费平台，提供商户信息、用户评价和餐饮休闲推荐。",
    "国家政务服务平台": "国家级政务服务入口，提供政务事项查询、在线办理和便民服务。",
    "ComfyUI": "基于节点工作流的开源生成式 AI 图像界面，可组合模型和处理节点完成图像生成流程。",
    "Poe": "聚合多种人工智能模型的对话平台，可使用不同 AI 助手进行问答、写作和内容处理。",
    "Character.AI": "AI 角色对话平台，可创建或选择不同虚拟角色进行个性化聊天和互动。",
    "You.com": "融合搜索与人工智能助手的平台，可进行网页检索、问答、写作和信息整理。",
    "Phind": "面向开发者的 AI 搜索与编程助手，可查找技术资料、解释代码和解决开发问题。",
    "Mistral Le Chat": "Mistral AI 推出的智能对话助手，可用于问答、写作、分析和内容处理。",
    "Cohere": "面向企业和开发者的生成式 AI 平台，提供语言模型、文本理解和检索增强能力。",
    "AI21 Labs": "生成式人工智能平台，提供语言模型及面向文本生成、理解和企业应用的 AI 能力。",
    "Replicate": "提供机器学习模型在线运行与 API 调用的平台，可快速使用和部署多种开源 AI 模型。",
    "Together AI": "面向开发者的 AI 模型云平台，提供开源模型推理、训练和 API 服务。",
    "Groq": "提供高速 AI 模型推理服务的平台，可通过 API 运行多种大型语言模型。",
    "Ollama": "本地运行大型语言模型的工具，可下载、管理并运行多种开源模型。",
    "LM Studio": "桌面端本地大模型运行工具，可下载、管理兼容模型并提供本地推理服务。",
}

# Human-reviewed profiles for sites whose public homepage blocks metadata
# collection.  Each entry describes the individual product; none is a
# category-wide fallback.  Keeping them beside the quality rules makes the
# source, audit and future editorial maintenance explicit.
SPECIFIC_DESCRIPTIONS.update({
    "QQ音乐": "腾讯旗下音乐流媒体平台，提供正版歌曲、歌单、电台和数字专辑播放服务。",
    "12306": "中国铁路官方购票服务平台，可查询车次、购买火车票并办理退改签。",
    "今日头条": "个性化资讯平台，聚合新闻、视频和图文内容并提供热点信息阅读。",
    "闲鱼": "阿里旗下闲置交易社区，可发布、购买和转让二手商品及提供同城交易服务。",
    "智联招聘": "招聘求职平台，提供职位搜索、简历投递、企业招聘和职业发展服务。",
    "马蜂窝": "旅行攻略与社区平台，提供目的地攻略、用户游记和旅行产品预订信息。",
    "npm": "JavaScript 包管理与发布平台，用于安装、共享和维护前端及 Node.js 依赖包。",
    "腾讯云": "腾讯提供的云计算服务平台，涵盖云服务器、数据库、存储、AI 与安全产品。",
    "华为云": "华为提供的云服务平台，提供计算、存储、网络、数据库和人工智能服务。",
    "Kubernetes": "开源容器编排系统，用于部署、扩缩容和管理容器化应用程序。",
    "Grafana": "开源可观测性与数据可视化平台，可构建指标、日志和链路追踪仪表盘。",
    "Elasticsearch": "分布式搜索与分析引擎，常用于全文检索、日志分析和实时数据查询。",
    "RabbitMQ": "开源消息代理软件，通过消息队列支持应用之间的异步通信和任务分发。",
    "Apache Kafka": "分布式事件流平台，用于高吞吐消息传递、数据管道和实时流处理。",
    "Nginx": "高性能 Web 服务器和反向代理软件，可处理静态资源、负载均衡与网关转发。",
    "Linux命令大全": "提供 Linux 常用命令说明、参数示例和系统运维知识的中文学习网站。",
    "阮一峰的网络日志": "阮一峰维护的技术博客，发布编程、互联网和科技领域的原创文章。",
    "开源中国": "中文开源技术社区，提供开源软件资讯、项目托管、技术文章和开发者交流。",
    "SourceForge": "开源软件发布与下载平台，提供项目托管、版本发布和社区协作服务。",
    "Bitbucket": "Atlassian 提供的 Git 代码托管平台，支持团队协作、拉取请求和流水线集成。",
    "Gerrit": "面向 Git 项目的代码评审系统，用于提交审核、变更讨论和权限管理。",
    "Hacker News": "Y Combinator 运营的科技新闻社区，聚焦创业、编程和互联网行业讨论。",
    "OpenSource.com": "Red Hat 支持的开源资讯网站，发布开源文化、工具和实践经验文章。",
    "Linux 中国": "中文 Linux 与开源技术社区，提供行业新闻、教程和技术文章。",
    "CodeProject": "开发者技术社区，发布编程文章、示例代码、项目教程和软件开发资源。",
    "Exercism": "免费编程练习平台，通过多语言题目和导师反馈帮助学习编程。",
    "Gitter": "面向开源项目和开发团队的在线聊天社区，支持围绕代码库进行实时交流。",
    "抖音": "短视频与直播平台，提供视频创作、内容浏览、直播互动和电商服务。",
    "小红书": "生活方式内容社区，用户可发布图文和短视频并分享购物、旅行等经验。",
    "NGA玩家社区": "以游戏讨论为核心的中文社区，涵盖网游、主机游戏和玩家交流内容。",
    "Epic Games": "游戏发行与数字商店平台，提供 PC 游戏购买、下载和虚幻引擎服务。",
    "网易游戏": "网易旗下游戏门户，提供自研及代理游戏资讯、下载和账号服务。",
    "漫画柜": "在线漫画阅读网站，收录多种题材的连载漫画与章节阅读内容。",
    "哔哩哔哩番剧": "哔哩哔哩的正版动画专区，提供番剧、国创动画和相关视频内容。",
    "网易漫画": "网易旗下漫画阅读平台，提供国漫、日漫等数字漫画内容与连载阅读。",
    "快手": "短视频和直播社区，支持内容创作、直播互动及本地生活服务。",
    "西瓜视频": "中长视频内容平台，提供影视、知识、生活和原创视频观看服务。",
    "微博热搜": "微博实时热点榜单，展示当前社会、娱乐和公共话题的热门讨论。",
    "知乎热榜": "知乎的热门话题榜单，汇集问答社区中正在讨论的新闻和知识话题。",
    "番茄小说": "免费网络文学阅读平台，提供小说连载、听书和个性化书籍推荐。",
    "起点中文网": "网络文学阅读与创作平台，提供原创小说连载、作者创作和版权运营服务。",
    "晋江文学城": "原创网络文学平台，聚焦言情、耽美等小说连载与读者社区互动。",
    "网易云游戏": "网易提供的云游戏平台，可通过云端串流体验多款游戏。",
    "Nintendo": "任天堂中国官方网站，提供 Switch 主机、游戏产品和官方资讯服务。",
    "原神": "开放世界角色扮演游戏，玩家可探索幻想世界、收集角色并进行战斗冒险。",
    "和平精英": "腾讯运营的战术竞技手游，提供多人组队、射击对战和赛季玩法。",
    "蜻蜓FM": "中文音频平台，提供广播、有声书、播客、新闻和知识节目收听服务。",
    "Regex101": "在线正则表达式测试工具，可实时匹配文本、查看解释并生成代码片段。",
    "Unsplash": "免费高质量摄影图片平台，提供可用于创作的图片搜索、下载和授权信息。",
    "MD5加密": "在线 MD5 哈希计算工具，可将文本快速转换为 MD5 摘要值。",
    "IP查询": "提供 IP 地址归属地、运营商和网络信息查询的在线服务。",
    "在线代码运行": "在线代码执行工具，可在浏览器中编写、运行和测试多种编程语言代码。",
    "Roam Research": "双向链接笔记工具，用于建立关联知识库、记录思考和组织研究资料。",
    "Make": "可视化自动化平台，可连接多种应用并编排无代码工作流。",
    "n8n": "开源工作流自动化工具，可通过节点连接应用、API 和数据处理流程。",
    "Arco Design": "字节跳动开源的企业级设计系统，提供设计规范和 React、Vue 组件库。",
    "NextUI": "面向 React 的现代 UI 组件库，提供可访问且可定制的界面组件。",
    "Flowbite": "基于 Tailwind CSS 的开源组件库，提供常用网页界面组件和模板。",
    "Cult UI": "面向 React 与 Tailwind CSS 的开源界面组件集合，提供可复制的交互元素。",
    "NutUI": "京东开源的移动端 Vue 组件库，适用于电商和移动 Web 界面开发。",
    "React Aria": "Adobe 提供的 React 无障碍交互库，用于构建可访问的自定义组件。",
    "HeroUI": "面向 React 的组件库，提供现代化、可访问且可定制的界面基础组件。",
    "dnd kit": "面向 React 的拖拽交互工具包，可构建排序、看板和自定义拖放界面。",
    "Kobalte": "面向 SolidJS 的无障碍 UI 原语库，用于构建可定制的交互组件。",
    "Reach UI": "面向 React 的无障碍组件库，提供菜单、对话框等常用交互原语。",
    "Three.js": "JavaScript 3D 图形库，可在浏览器中创建和渲染交互式三维场景。",
    "Babylon.js": "基于 JavaScript 的 3D 引擎，用于构建网页游戏和交互式三维应用。",
    "Recharts": "基于 React 与 D3 的图表库，可快速构建响应式数据可视化图表。",
    "Deck.gl": "面向大规模地理空间数据的 WebGL 可视化框架，常用于地图图层渲染。",
    "Vis.js": "JavaScript 可视化库，提供网络图、时间轴和数据集展示组件。",
    "Vega-Lite": "声明式统计图表语法，可用简洁配置描述并生成交互式可视化。",
    "Cesium": "面向地理空间应用的 3D 地球平台，可渲染地图、地形和时空数据。",
    "OpenLayers": "开源 Web 地图库，用于在网页中展示地图、图层和地理空间数据。",
    "Plotly.js": "JavaScript 交互式图表库，支持科学图表、统计图和三维可视化。",
    "p5.js": "面向创意编程的 JavaScript 库，适合制作交互艺术、动画和视觉实验。",
    "ArcGIS": "Esri 提供的地理信息系统平台，支持地图制作、空间分析和 GIS 数据管理。",
    "AnyChart": "跨平台数据可视化库，可创建交互式商务、金融和统计图表。",
    "ChartBlocks": "在线图表制作工具，可通过可视化界面创建并嵌入数据图表。",
    "Jest": "JavaScript 测试框架，常用于编写和运行前端及 Node.js 单元测试。",
    "Storybook": "组件开发与展示工具，可独立构建、测试和文档化 UI 组件。",
    "Rollup": "JavaScript 模块打包器，擅长将库代码打包为高效的发布文件。",
    "Husky": "Git 钩子管理工具，可在提交或推送代码前自动执行检查任务。",
    "Nx": "面向单体仓库的构建系统，可管理项目依赖、任务编排和代码生成。",
    "Nitro": "JavaScript 服务端框架与部署引擎，可构建 API、服务端渲染和边缘服务。",
    "esbuild": "极速 JavaScript 与 CSS 构建工具，支持打包、压缩和代码转换。",
    "SWC": "基于 Rust 的 JavaScript 与 TypeScript 编译器，提供高速代码转换能力。",
    "Babel": "JavaScript 编译工具链，可将现代语法转换为兼容旧环境的代码。",
    "Rome Tools": "面向 JavaScript 的统一工具链，整合格式化、静态检查和代码分析能力。",
    "Stylelint": "CSS 静态检查工具，可发现样式代码问题并统一团队编写规范。",
    "Gulp": "基于任务流的前端构建工具，可自动处理编译、压缩和文件转换。",
    "Grunt": "JavaScript 任务运行器，可自动执行构建、测试和发布等重复工作。",
    "Just": "命令运行器，可通过 justfile 定义并执行项目常用开发任务。",
    "花瓣网": "设计灵感与素材收藏社区，提供图片采集、画板整理和视觉参考浏览。",
    "UI8": "设计资源交易平台，提供 UI 套件、图标、字体、模板和插画素材。",
    "Godly": "网页设计灵感库，收录优秀网站案例并按风格和行业进行浏览。",
    "UI Sources": "移动应用界面灵感库，收录真实产品的交互流程和界面截图。",
    "SiteInspire": "网页设计案例库，按布局、风格和技术标签收集优秀网站作品。",
    "UI Garage": "界面设计灵感网站，提供移动端和网页 UI 案例与交互参考。",
    "CSS Design Awards": "网页设计奖项与作品展示平台，收录获奖网站和创意数字项目。",
    "CSS Winner": "网页设计作品展示与评选平台，提供优秀网站案例和设计灵感。",
    "Dribbble Shots": "Dribbble 的设计作品浏览页，展示设计师发布的界面、插画和品牌案例。",
    "Pinterest Design": "Pinterest 的设计灵感浏览入口，可收藏和发现视觉设计内容。",
    "Design Better": "InVision 出版的设计学习资源，提供产品设计、协作和设计管理内容。",
    "Uplabs": "设计资源社区，提供 UI 套件、图标、模板和产品设计灵感。",
    "Mobile Patterns": "移动应用交互模式库，收集常见功能场景的真实界面设计案例。",
    "Design Notes": "设计师社区与灵感平台，分享产品设计作品、经验和行业资讯。",
    "Freepik": "设计素材平台，提供矢量图、照片、PSD、图标和模板资源。",
    "LottieFiles": "Lottie 动画资源平台，可浏览、编辑、下载和分享轻量级矢量动画。",
    "Flaticon": "图标素材平台，提供可下载的矢量和位图图标资源。",
    "SVG Repo": "开源 SVG 图标资源库，提供可搜索、下载和编辑的矢量图标。",
    "Phosphor Icons": "开源图标库，提供多种粗细和风格的可定制 SVG 图标。",
    "DrawKit": "插画与图形素材平台，提供可用于产品设计的矢量插画和图标资源。",
    "Unsplash Source": "Unsplash 提供的随机图片服务，可通过 URL 获取可商用的摄影图片。",
    "Huemint": "AI 辅助配色工具，可为品牌、网页和插画生成协调的色彩方案。",
    "Simple Icons": "开源品牌图标库，提供大量服务和产品的标准 SVG 标志。",
    "Rawpixel": "创意素材平台，提供照片、插画、纹理和公共领域图片资源。",
    "Iconscout": "设计素材平台，提供图标、插画、3D 素材和界面资源下载。",
    "MasterGo": "在线协作式 UI 设计工具，支持界面设计、原型制作和团队评审。",
    "Pixlr": "在线图片编辑器，提供图像修饰、合成、滤镜和 AI 图片处理功能。",
    "Haikei": "在线 SVG 生成工具，可快速创建波浪、渐变和抽象背景图形。",
    "JWT.io": "JSON Web Token 调试工具，可解析、验证和生成 JWT 令牌。",
    "WebPageTest": "网站性能测试工具，可分析页面加载速度、网络请求和优化建议。",
    "PageSpeed Insights": "Google 网站性能分析工具，评估网页体验并给出优化建议。",
    "GTmetrix": "网页性能检测平台，可生成加载速度、资源请求和优化报告。",
    "HTML5 Editor": "在线 HTML 编辑器，可编写、预览和测试网页标记代码。",
    "Adobe Fonts": "Adobe 提供的在线字体服务，可为网站和设计项目同步和使用字体。",
    "Happy Hues": "配色灵感网站，提供适用于界面设计的成套颜色方案和示例页面。",
    "Type Scale": "排版比例计算工具，可根据字体和比例生成层级化字号方案。",
    "Palette Ninja": "在线配色工具，可通过色相轮和图片提取创建、调整颜色方案。",
    "Paletton": "色彩方案设计工具，可基于色轮生成单色、互补和多色配色。",
    "Fontshare": "免费字体服务，提供可用于个人和商业项目的高质量字体下载。",
    "Font Squirrel": "免费商用字体资源网站，提供字体下载和网页字体生成工具。",
    "Typograph": "在线排版工具，可预览字体组合、字号层级和文本版式效果。",
    "Fontfabric": "字体设计工作室与字体商店，提供展示字体和商业字体授权。",
    "Lost Type": "独立字体合作社，提供多款展示字体及按需付费下载方式。",
    "Colophon Foundry": "独立字体厂牌，发布和销售原创显示字体与排版字体。",
    "Type.today": "字体设计与排版资讯平台，提供字体发行、试用和相关内容。",
    "Colorable": "颜色对比度检查工具，可评估文字与背景组合的可读性和无障碍等级。",
    "Contrast Checker": "WebAIM 提供的颜色对比度检测工具，用于检查网页文本的无障碍可读性。",
    "Mesh Gradients": "渐变背景资源网站，提供网格渐变示例、灵感和生成方法。",
    "Fontspring": "商业字体授权平台，提供字体试用、购买和网页字体服务。",
    "Typekit": "Adobe 的网页字体服务名称，现已整合为 Adobe Fonts 字体库。",
    "MyFonts": "商业字体市场，提供大量字体的试用、购买和授权服务。",
    "Abstract Fonts": "字体下载网站，收集免费和商业字体供设计与排版使用。",
    "Principle": "macOS 动效原型工具，可制作界面过渡、交互动效和高保真演示。",
    "Flinto": "macOS 原型设计工具，用于创建移动应用的交互流程和动画效果。",
    "FlowMapp": "信息架构与用户流程设计工具，可创建站点地图、用户旅程和内容计划。",
    "Framer Templates": "Framer 官方模板市场，提供可复制的网站模板和组件资源。",
    "Figma Community": "Figma 社区资源库，提供设计文件、插件、组件库和模板下载。",
    "Prototypr": "产品设计灵感与学习社区，分享 UI 案例、工具和设计职业内容。",
    "Basecamp": "团队项目协作工具，提供任务、消息、文件、日程和项目沟通功能。",
    "Microsoft 365": "微软办公云服务套件，包含 Word、Excel、PowerPoint、邮件和协作工具。",
    "Google Drive": "Google 云存储与协作服务，可保存、共享和协同编辑各类文件。",
    "Microsoft Teams": "微软团队协作平台，提供聊天、视频会议、频道和文件协作功能。",
    "ONLYOFFICE": "在线办公套件，提供文档、表格和演示文稿的创建及协同编辑功能。",
    "Collabora Online": "基于 LibreOffice 的在线办公套件，支持文档、表格和演示协作编辑。",
    "Fellow": "会议管理与协作工具，可创建议程、记录会议事项并跟踪后续任务。",
    "百度统计": "百度提供的网站流量分析工具，可查看访问来源、用户行为和转化数据。",
    "Google Analytics": "Google 的网站与应用分析服务，用于追踪流量、用户行为和转化指标。",
    "FullStory": "数字体验分析平台，可通过会话回放和行为数据定位产品使用问题。",
    "Qlik": "商业智能与数据分析平台，提供数据整合、交互式仪表盘和自助分析。",
    "Domo": "云端商业智能平台，可整合业务数据并创建实时分析看板。",
    "DataCamp": "在线数据技能学习平台，提供 Python、SQL、机器学习等互动课程。",
    "Gapminder": "全球发展数据可视化平台，通过交互图表展示人口、经济和健康趋势。",
    "Google Dataset Search": "Google 提供的数据集搜索服务，可发现公开研究、政府和机构数据集。",
    "国家数据": "国家统计局数据查询平台，提供中国人口、经济和社会统计数据。",
    "UN Data": "联合国公开数据门户，提供各成员国的人口、经济和社会统计指标。",
    "SQLPad": "Web 版 SQL 查询工具，可连接数据源、编写查询并可视化查询结果。",
    "Vega": "声明式可视化语法与运行库，可通过 JSON 配置构建交互式统计图表。",
    "Vega Voyager": "基于 Vega-Lite 的可视化探索工具，可通过字段拖放发现数据图表。",
    "中国数据开放平台": "中国政府数据开放平台，提供各领域可下载、查询和复用的公共数据资源。",
    "App Annie": "移动应用市场数据平台，现更名为 data.ai，提供下载、收入和市场洞察。",
    "七麦数据": "移动应用数据分析平台，提供 App Store 和应用市场的榜单、关键词与竞品数据。",
    "艾瑞咨询": "互联网与新经济研究机构，发布行业研究报告、市场数据和咨询洞察。",
    "G2": "企业软件评价与选型平台，汇集用户评分、产品对比和采购决策信息。",
    "Capterra": "企业软件目录与评价平台，可按需求比较 SaaS 产品和用户评论。",
    "IT桔子": "创投数据服务平台，提供中国公司、融资、投资机构和行业研究信息。",
    "36氪研究院": "36氪旗下产业研究平台，发布新经济行业报告和商业趋势分析。",
    "SpyFu": "SEO 与搜索广告分析工具，可研究关键词排名、竞争对手和广告投放历史。",
    "Owler": "企业情报平台，提供公司新闻、竞争对手、融资和市场动态信息。",
    "Google Trends": "Google 搜索趋势工具，可比较关键词热度和地区、时间维度变化。",
    "Meta Ad Library": "Meta 广告资料库，可检索 Facebook 与 Instagram 上投放的广告内容。",
    "TikTok Creative Center": "TikTok 广告创意与趋势平台，提供热门素材、关键词和行业洞察。",
    "SimilarTech": "网站技术栈分析工具，可识别网站使用的技术并进行竞品对比。",
    "CB Insights": "市场研究平台，跟踪创业公司、融资、行业趋势和新兴技术。",
    "PitchBook": "私募市场数据平台，提供公司、融资、基金和并购交易研究信息。",
    "BuiltWith Trends": "BuiltWith 的技术趋势服务，用于查看网站技术使用量和市场变化。",
    "Luma AI": "AI 视觉创作平台，可生成视频、三维场景和沉浸式视觉内容。",
    "Ideogram": "AI 图像生成工具，擅长在生成图片中呈现清晰文字和海报设计。",
    "Meta AI": "Meta 推出的人工智能助手，可进行对话、信息查询和内容创作。",
    "Fal.ai": "面向开发者的生成式媒体云平台，提供图像与视频模型的推理 API。",
    "Leonardo AI": "AI 图像生成平台，提供角色、游戏资产和视觉设计创作工具。",
    "Gamma": "AI 辅助演示与文档工具，可根据主题快速生成网页式内容和幻灯片。",
    "Tome": "AI 演示文稿工具，可通过文字提示创建叙事页面和视觉内容。",
    "Copy.ai": "AI 文案写作平台，可生成营销文案、邮件、文章和销售内容。",
    "Weights & Biases": "机器学习开发平台，用于实验跟踪、模型评估、数据集管理和团队协作。",
    "Canva Magic Studio": "Canva 的 AI 创作套件，提供图片生成、文案辅助和设计自动化功能。",
    "NotebookLM": "Google 的 AI 笔记与研究工具，可基于用户资料进行问答、总结和整理。",
    "HTMX": "前端库，可通过 HTML 属性发起请求并实现局部页面更新与交互。",
    "NestJS": "基于 TypeScript 的 Node.js 服务端框架，适合构建可维护的企业级应用。",
    "Koa.js": "由 Express 团队成员开发的轻量 Node.js Web 框架，使用中间件组织服务。",
    "Elysia": "面向 Bun 运行时的高性能 TypeScript Web 框架，可快速构建 API 服务。",
    "Flask": "Python 轻量级 Web 框架，可快速构建网站、REST API 和后端服务。",
    "Go": "Go 语言官方文档入口，提供语言教程、标准库和开发工具资料。",
    "Kotlin": "Kotlin 语言官方文档，提供语法指南、教程和跨平台开发资料。",
    "Java": "Java 官方学习入口，提供语言基础、开发教程和平台相关资源。",
    "C#": "微软 C# 文档中心，提供语言参考、教程和 .NET 开发指南。",
    "Swift": "Apple 的 Swift 语言文档，提供语法参考、开发指南和生态资料。",
    "Electron": "跨平台桌面应用框架，可使用 JavaScript、HTML 和 CSS 构建桌面软件。",
    "Bootstrap": "流行的前端 CSS 框架，提供响应式布局、样式规范和常用 UI 组件。",
    "Parcel": "零配置 Web 应用打包器，可自动处理模块、资源和开发环境构建。",
    "FutureLearn": "在线课程平台，与大学和机构合作提供职业、学术和兴趣学习课程。",
    "OpenLearn": "英国开放大学的免费学习平台，提供多学科开放课程和学习材料。",
    "Exercism Learning": "Exercism 的学习路径入口，通过编程练习和导师反馈训练编码能力。",
    "MDN Learn": "MDN Web Docs 的学习专区，提供 HTML、CSS、JavaScript 和 Web 开发教程。",
    "Google Codelabs": "Google 的互动教程平台，通过分步实验学习产品和开发技术。",
    "AWS Skill Builder": "AWS 云技能学习平台，提供云计算课程、实验和认证备考资源。",
    "Linux Journey": "免费 Linux 学习网站，通过交互式课程介绍命令行、系统和网络知识。",
    "慕课网": "中文在线编程学习平台，提供前端、后端、移动开发等课程和实战项目。",
    "实验楼": "在线 IT 技能学习平台，提供 Linux、编程和云计算实验环境与课程。",
    "SoloLearn": "移动优先的编程学习社区，提供多语言课程、练习和开发者互动。",
    "egghead": "面向前端开发者的视频学习平台，提供简短的 JavaScript 与框架课程。",
    "Microsoft To Do": "微软待办清单工具，可创建任务、提醒、列表并在多设备间同步。",
    "Height": "团队项目管理工具，提供任务看板、自动化工作流和协作跟踪功能。",
    "Cron": "日历与日程管理工具，后被 Notion 收购并整合为 Notion Calendar。",
    "SavvyCal": "会议排期工具，可共享可用时间并减少跨时区约会协调成本。",
    "Focusmate": "线上专注陪伴服务，通过视频共工时段帮助用户完成待办任务。",
    "Focuster": "专注时间管理工具，可安排任务、阻断干扰并跟踪工作节奏。",
    "Focus To-Do": "番茄钟与待办事项工具，可结合专注计时、任务清单和数据统计。",
    "Amplenote": "集笔记、任务和日历于一体的效率工具，支持双向链接和计划管理。",
    "虎扑": "以体育赛事讨论为核心的中文社区，提供篮球、足球、电竞等内容和用户交流。",
    "Boss直聘": "直聊式招聘求职平台，支持求职者与招聘方在线沟通、投递简历和发布职位。",
    "LangChain": "用于构建大语言模型应用的开源框架，提供模型调用、检索、代理和工作流组件。",
    "Alpine.js": "轻量级 JavaScript 前端框架，可直接在 HTML 中声明响应式状态和交互行为。",
    "丁香医生": "健康医疗科普与服务平台，提供疾病知识、医生咨询和健康管理内容。",
    "UI Patterns": "用户界面模式资源库，收集常见产品功能的交互设计案例与最佳实践。",
    "Wix Studio": "Wix 面向专业创作者的网站搭建平台，支持响应式设计、协作和客户项目管理。",
    "LinkedIn Learning": "LinkedIn 在线学习平台，提供商业、技术和创意技能的视频课程。",
    "Any.do": "待办事项与日程管理工具，可创建任务、提醒、清单并同步团队协作事项。",
    "Consumer Barometer": "Google 提供的消费者行为研究工具，可查看不同市场的线上消费与媒体使用数据。",
    "Google Market Finder": "Google 的市场拓展工具，可根据产品和受众寻找潜在海外市场并获取本地化建议。",
    "Stockvault": "免费图库网站，提供摄影图片、纹理和设计素材供创作项目下载使用。",
    "Confluence": "Atlassian 的团队知识库工具，可协作编写文档、沉淀项目资料并组织内部信息。",
    "Jira": "Atlassian 的项目管理工具，可跟踪需求、缺陷、迭代任务和团队工作流程。",
    "Coda": "将文档、表格和自动化结合的协作平台，可构建团队工作台和轻量业务应用。",
    "Project Euler": "数学与编程解题平台，通过逐步递进的问题训练算法思维和编码能力。",
    "AppFlowy": "开源的本地优先工作空间工具，提供笔记、任务、数据库和团队协作功能。",
    "Reclaim AI": "智能日程管理工具，可自动安排任务、习惯和会议时间并保护专注时段。",
    "Due": "简洁的提醒应用，可创建循环提醒和持续通知以避免遗漏重要事项。",
    "Timeular": "时间追踪工具，结合实体追踪器和软件记录项目工时并生成分析报告。",
    "Grok": "xAI 推出的人工智能助手，可进行实时信息问答、写作、编程和图像创作。",
    "SaaSFrame": "SaaS 产品设计资源库，收录真实网站、界面和邮件流程的 UI/UX 案例。",
    "Mockuuups Studio": "设备样机制作工具，可将界面截图快速生成手机、电脑和印刷品展示图。",
    "Miro": "在线协作白板工具，可用于头脑风暴、流程梳理、项目规划和团队工作坊。",
    "InVision": "数字产品设计与协作平台，提供原型演示、设计评审和团队反馈工具。",
    "InVision Studio": "InVision 的界面设计与动效原型工具，可制作高保真交互和动画演示。",
    "InVision Freehand": "InVision 的在线协作白板，用于团队讨论、流程图绘制和创意工作坊。",
    "Canva": "在线视觉设计平台，可制作海报、演示文稿、社交媒体图片和视频内容。",
    "Canva AI": "Canva 的 AI 创作功能，支持根据提示生成图片、文案和设计素材。",
    "Smart Mockups": "在线设备样机生成工具，可将设计作品嵌入手机、电脑等真实场景展示图。",
    "Google Sheets": "在线电子表格工具，支持数据处理、公式计算、图表制作和多人实时协作。",
    "Google Slides": "在线演示文稿工具，支持幻灯片制作、模板使用和多人实时协作。",
    "Box": "企业内容管理与云存储平台，支持文件保存、共享、协作和权限管理。",
    "Evernote": "笔记与知识管理工具，可记录文字、网页、图片和任务，并支持多端同步。",
    "Heptabase": "可视化知识管理工具，通过白板和卡片组织笔记与复杂信息。",
    "Slite": "面向团队的知识库与协作文档平台，可用于记录、共享和维护内部知识。",
    "Craft": "现代化笔记与文档工具，支持内容编辑、知识整理、分享和团队协作。",
    "Quip": "实时协作文档平台，结合文档、表格和团队沟通功能进行多人协作。",
    "Zoho Writer": "在线文字处理工具，支持文档创建、编辑、多人协作和云端保存。",
    "Zoom": "视频会议与团队协作平台，支持在线会议、屏幕共享、聊天和会议录制。",
    "Slack": "团队沟通与协作平台，支持频道聊天、文件共享、工作流自动化和应用集成。",
    "Discord": "语音、文字和社区交流平台，可创建服务器并进行实时聊天与内容分享。",
    "Xbox": "微软游戏平台，提供主机与 PC 游戏、Game Pass 订阅及玩家社区服务。",
    "PlayStation": "索尼游戏平台，提供 PlayStation 主机游戏、数字商店和在线多人服务。",
    "腾讯游戏": "腾讯旗下游戏业务平台，提供自研及代理游戏、赛事和玩家社区服务。",
    "LOL": "英雄联盟官方游戏入口，提供客户端、赛事资讯、角色资料和玩家服务。",
    "AnswerThePublic": "关键词与用户问题研究工具，可从搜索数据中发现受众关心的话题和提问。",
    "Linear": "面向产品与研发团队的项目管理工具，可规划需求、跟踪问题和协调产品开发流程。",
    "Monday.com": "团队工作管理平台，可通过看板、自动化和仪表盘管理项目、任务和协作流程。",
    "Airtable": "结合表格与数据库的协作平台，可构建内容管理、项目跟踪和业务工作流。",
    "Slab": "团队知识库工具，支持文档编写、内容组织、全文搜索和常用协作工具集成。",
    "Tettra": "面向团队的 AI 知识库，可集中维护内部文档并通过问答快速获取信息。",
    "Guru": "企业知识管理平台，可在团队工作流中沉淀、验证和调用内部知识。",
    "Nuclino": "轻量级团队知识库与协作工具，可通过文档、集合和图谱组织共享信息。",
    "Almanac": "协作文档平台，支持版本控制、多人编辑和团队知识内容的共享维护。",
    "Outline": "现代团队知识库工具，可编写内部文档、组织项目规范并进行权限协作。",
})

# Profiles which intentionally replace an otherwise syntactically valid
# homepage description because that metadata was shared by a different product.
REVIEWED_DESCRIPTION_OVERRIDES = frozenset({
    "Miro", "InVision", "InVision Studio", "InVision Freehand",
    "Canva", "Canva AI", "Smart Mockups",
})

# Rewrites applied by the language-governance job.  They are deliberately
# limited to reviewed products that had an unsupported script or an entire
# English marketing sentence in the Chinese-language catalogue.
LANGUAGE_NORMALIZATION_OVERRIDES = frozenset({
    "Google Sheets", "Google Slides", "Box", "Evernote", "Heptabase",
    "Slite", "Craft", "Quip", "Zoho Writer", "Zoom", "Slack", "Discord",
    "Xbox", "PlayStation", "腾讯游戏", "LOL", "AnswerThePublic",
    "Linear", "Monday.com", "Airtable", "Slab", "Tettra", "Guru", "Nuclino",
    "Almanac", "Outline",
})


def clean_text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def description_without_name_prefix(record: dict[str, Any]) -> str:
    """Return text after an exact leading ``name:`` / ``name：`` prefix."""
    name = clean_text(record.get("name"))
    description = clean_text(record.get("description"))
    if not name:
        return description
    prefix = re.compile(rf"^{re.escape(name)}\s*[:：]\s*", re.IGNORECASE)
    return prefix.sub("", description, count=1).strip()


def has_name_prefix(record: dict[str, Any]) -> bool:
    return description_without_name_prefix(record) != clean_text(record.get("description"))


def normalize_description(description: object) -> str:
    text = clean_text(description).lower()
    return re.sub(r"[\s，,。.!！?？:：;；、…\-—_]+", "", text)


def is_generic_description(description: object) -> bool:
    text = clean_text(description)
    if not text:
        return False
    if text in RETIRED_GENERIC_DESCRIPTIONS:
        return True
    career_terms = ("当前职业方向", "职业方向", "推荐给你", "学习与实践资源")
    generic_patterns = (
        r"^提供(?:相关|实用|适合.*职业).*?(?:资源|服务|工具)。?$",
        r"^适合.*?(?:使用|学习)。?$",
    )
    return any(term in text for term in career_terms) or any(
        re.match(pattern, text) for pattern in generic_patterns
    )


def description_status(record: dict[str, Any]) -> str | None:
    description = clean_text(record.get("description"))
    normalized = description_without_name_prefix(record)
    if not description:
        return "empty"
    if is_generic_description(normalized):
        return "generic"
    if has_name_prefix(record):
        return "name_prefix"
    if len(description) < 12:
        return "too_short"
    if len(description) > 95:
        return "too_long"
    return None


def suggested_description(record: dict[str, Any]) -> tuple[str | None, str, str]:
    name = clean_text(record.get("name"))
    if name in SPECIFIC_DESCRIPTIONS:
        return SPECIFIC_DESCRIPTIONS[name], "reviewed_site_profile", "high"
    return None, "insufficient_reliable_metadata", "needs_review"


def build_candidate(record: dict[str, Any]) -> dict[str, Any] | None:
    status = description_status(record)
    if status is None:
        return None
    suggestion, reason, confidence = suggested_description(record)
    return {
        "website_id": record.get("website_id", record.get("id")),
        "name": clean_text(record.get("name")),
        "url": clean_text(record.get("url")),
        "current_description": clean_text(record.get("description")),
        "suggested_description": suggestion,
        "category": clean_text(record.get("category", record.get("category_name"))),
        "tags": clean_text(record.get("tags")),
        "reason": status if reason == "insufficient_reliable_metadata" else reason,
        "confidence": confidence,
        "source": "manual_verified" if confidence == "high" else "needs_review",
    }


def _groups(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        description = description_without_name_prefix(record)
        if description:
            grouped[description].append(record)
    return [
        {
            "description": description,
            "count": len(rows),
            "websites": [
                {"website_id": row.get("website_id", row.get("id")), "name": clean_text(row.get("name")), "url": clean_text(row.get("url"))}
                for row in rows
            ],
        }
        for description, rows in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
        if len(rows) > 1
    ]


def analyze_records(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    descriptions = [clean_text(row.get("description")) for row in rows]
    counts = Counter(item for item in descriptions if item)
    normalized_counts = Counter(
        item for item in (description_without_name_prefix(row) for row in rows) if item
    )
    statuses = Counter(description_status(row) or "usable" for row in rows)
    duplicate_groups = _groups(rows)
    exact_duplicates = sum(count for count in counts.values() if count > 1)
    normalized_duplicates = sum(count for count in normalized_counts.values() if count > 1)
    high_similarity_groups = [group for group in duplicate_groups if group["count"] >= 4]
    return {
        "total_websites": len(rows),
        "valid_website_count": len(rows),
        "valid_descriptions": statuses["usable"],
        "empty_descriptions": statuses["empty"],
        "empty_description_count": statuses["empty"],
        "generic_descriptions": statuses["generic"],
        "generic_fallback_count": statuses["generic"],
        "low_quality_descriptions": sum(statuses[key] for key in ("empty", "generic", "too_short", "too_long", "name_prefix")),
        "name_prefixed_descriptions": statuses["name_prefix"],
        "name_prefix_count": statuses["name_prefix"],
        "duplicate_descriptions": exact_duplicates,
        "exact_duplicate_description_count": exact_duplicates,
        "high_similarity_descriptions": normalized_duplicates,
        "normalized_duplicate_description_count": normalized_duplicates,
        "too_short_count": statuses["too_short"],
        "too_long_count": statuses["too_long"],
        "duplicate_groups": duplicate_groups,
        "high_similarity_groups": high_similarity_groups,
        "description_usage_top_20": [
            {"description": description, "count": count}
            for description, count in counts.most_common(20)
        ],
        "normalized_description_usage_top_20": [
            {"description": description, "count": count}
            for description, count in normalized_counts.most_common(20)
        ],
    }
