<template>
  <div class="layout" :class="{ 'dark-theme': isDarkMode }">
    <header class="header-block">
      <div class="header-left">
        <div class="logo">
          <span class="logo-icon">🧭</span>
          <span class="logo-text">项目名称</span>
        </div>
      </div>
      
      <div class="auth-buttons">
        <button class="theme-toggle" @click="toggleTheme" :title="isDarkMode ? '切换浅色模式' : '切换深色模式'">
          {{ isDarkMode ? '☀️' : '🌙' }}
        </button>
        <button class="pill-btn">登陆</button>
        <button class="btn-primary">免费注册</button>
      </div>
    </header>

    <div class="main-container">
      <main class="content">
        
        <div class="center-action-area">
          
          <div class="category-tabs-wrapper">
            <span 
              class="nav-tab" 
              :class="{ 'active': activeCategoryId === 'all' }" 
              @mouseenter="activeCategoryId = 'all'"
            >
              全部分类
            </span>
            <span 
              v-for="cat in categories" 
              :key="cat.id" 
              class="nav-tab"
              :class="{ 'active': activeCategoryId === cat.id }"
              @mouseenter="activeCategoryId = cat.id"
            >
              {{ cat.name }}
            </span>
          </div>

          <div class="search-section">
            <div class="search-box block-shadow">
              <input v-model="searchQuery" @keyup.enter="doSearch" type="text" placeholder="输入内容，按回车搜索..." />
              <button @click="doSearch" class="search-btn-oval">搜索</button>
            </div>
            
            <div class="search-engines-wrapper">
              <div 
                v-for="(url, engine) in engines" 
                :key="engine"
                class="engine-option" 
                :class="{ active: currentEngine === engine }"
                @click="currentEngine = engine"
              >
                <div class="triangle-down"></div>
                <span class="engine-name">{{ engineNames[engine] }}</span>
              </div>
            </div>
          </div>
        </div>
<div class="site-grid">
  <div 
  v-for="site in filteredWebsites" 
  :key="site.id" 
  class="site-card block-shadow"
  @click="handleSiteClick(site)"
>
  <div class="logo-wrapper">
    <img 
      class="site-logo" 
      :src="site.logo_url" 
      :alt="site.name"
      @error="(e) => e.target.src = 'https://via.placeholder.com/50?text=LOGO'"
    />
  </div>
  <span class="site-name">{{ site.name }}</span>
</div>
</div>
      </main>

      <aside class="sidebar-right">
        <div class="widget block-shadow ai-widget">
          <div class="widget-header">
            <h3>✨ AI 建议</h3>
          </div>
          <div class="chat-window" ref="chatWindow">
            <div v-for="(msg, index) in chatMessages" :key="index" :class="['chat-bubble', msg.role]">
              {{ msg.content }}
            </div>
            <div v-if="isAiThinking" class="chat-bubble ai thinking">
              <span class="dot"></span><span class="dot"></span><span class="dot"></span>
            </div>
          </div>
          <div class="chat-input">
            <input v-model="userInput" @keyup.enter="sendMessage" type="text" placeholder="需要找什么网站？" :disabled="isAiThinking" />
            <button class="btn-send" @click="sendMessage" :disabled="isAiThinking">发送</button>
          </div>
        </div>

        <div class="widget block-shadow rank-widget">
          <div class="widget-header">
            <h3>🔥 今日排行</h3>
          </div>
          <ul class="rank-list">
            <li v-for="(item, index) in leaderboard" :key="index" class="rank-item">
              <span class="rank-num" :class="{'top-3': index < 3}">{{ index + 1 }}</span>
              <span class="rank-name">{{ item.name }}</span>
              <span class="rank-clicks">{{ item.click_count }}次</span>
            </li>
          </ul>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import axios from 'axios'
// 点击自动缓存逻辑
const handleSiteClick = async (site) => {
  if (!site) return;
  
  // 1. 先让用户跳转，不耽误体验
  window.open(site.url, '_blank');
  
  // 2. 检查是否需要触发缓存（只有当没有 Logo，或者 Logo 不是 Base64 时才触发）
  if (site.id && (!site.logo_url || !site.logo_url.startsWith('data:image'))) {
    console.log(`正在后台抓取 [${site.name}] 图标并存入数据库...`);
    try {
      const response = await axios.post('http://127.0.0.1:5000/api/cache_logo', {
        id: site.id,
        url: site.url
      });

      if (response.data.status === 'success') {
        // 请求成功后，将数据库返回的 Base64 实时赋给网页
        // 这样图标会“刷”的一下变出来，并且以后就是纯离线了！
        site.logo_url = response.data.logo_url;
        console.log(`[${site.name}] 离线缓存成功！`);
      }
    } catch (error) {
      console.error('缓存失败:', error);
    }
  }
};
// 基础状态
const activeCategoryId = ref('all') 
const isDarkMode = ref(false)
const toggleTheme = () => { isDarkMode.value = !isDarkMode.value }

// 1. 数据状态 (预置海量默认数据，防止后端未启动时页面空白)
const categories = ref([
  { id: 1, name: '常用推荐' },
  { id: 2, name: '开发社区' },
  { id: 3, name: '摸鱼娱乐' },
  { id: 4, name: '实用工具' },
  { id: 5, name: 'AI 神器' }
])

const websites = ref([
  // ================= 1. 常用推荐 =================
  { id: 101, category_id: 1, name: '哔哩哔哩', url: 'https://www.bilibili.com', logo_url: 'https://i0.hdslb.com/bfs/archive/04b50c00d41e7ed57e84128f7fb9b6c0e86b2404.png' },
  { id: 102, category_id: 1, name: '知乎', url: 'https://www.zhihu.com', logo_url: 'https://pic4.zhimg.com/80/v2-f6b1f64a098b891b4ea1e3104b5b71f6_720w.png' },
  { id: 103, category_id: 1, name: '微博', url: 'https://weibo.com', logo_url: 'https://h5.sinaimg.cn/m/weibo-lite/img/logo.eb449cf8.png' },
  { id: 104, category_id: 1, name: '豆瓣', url: 'https://www.douban.com', logo_url: 'https://img3.doubanio.com/favicon.ico' },
  { id: 105, category_id: 1, name: '淘宝网', url: 'https://www.taobao.com', logo_url: 'https://www.taobao.com/favicon.ico' },
  { id: 106, category_id: 1, name: '京东', url: 'https://www.jd.com', logo_url: 'https://www.jd.com/favicon.ico' },
  { id: 107, category_id: 1, name: '少数派', url: 'https://sspai.com', logo_url: 'https://sspai.com/favicon.ico' },

  // ================= 2. 开发社区 =================
  { id: 201, category_id: 2, name: 'GitHub', url: 'https://github.com', logo_url: 'https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png' },
  { id: 202, category_id: 2, name: 'Gitee', url: 'https://gitee.com', logo_url: 'https://gitee.com/assets/favicon.ico' },
  { id: 203, category_id: 2, name: 'LeetCode', url: 'https://leetcode.cn', logo_url: 'https://static.leetcode-cn.com/cn-legacy-assets/images/LeetCode_logo.png' },
  { id: 204, category_id: 2, name: '掘金', url: 'https://juejin.cn', logo_url: 'https://lf3-cdn-tos.bytescm.com/obj/static/xitu_juejin_web/e08da34488b114bd4c665ba2fa520a31.svg' },
  { id: 205, category_id: 2, name: 'CSDN', url: 'https://www.csdn.net', logo_url: 'https://g.csdnimg.cn/static/logo/favicon32.ico' },
  { id: 206, category_id: 2, name: 'Stack Overflow', url: 'https://stackoverflow.com', logo_url: 'https://cdn.sstatic.net/Sites/stackoverflow/Img/favicon.ico' },
  { id: 207, category_id: 2, name: 'V2EX', url: 'https://www.v2ex.com', logo_url: 'https://www.v2ex.com/favicon.ico' },
  { id: 208, category_id: 2, name: 'MDN 文档', url: 'https://developer.mozilla.org', logo_url: 'https://developer.mozilla.org/favicon.ico' },

  // ================= 3. 摸鱼娱乐 =================
  { id: 301, category_id: 3, name: '抖音', url: 'https://www.douyin.com', logo_url: 'https://lf1-cdn-tos.bytegoofy.com/goofy/ies/douyin_web/public/favicon.ico' },
  { id: 302, category_id: 3, name: '小红书', url: 'https://www.xiaohongshu.com', logo_url: 'https://xhs-static.xiaohongshu.com/xhs-pc-web/favicon.ico' },
  { id: 303, category_id: 3, name: '网易云音乐', url: 'https://music.163.com', logo_url: 'https://s1.music.126.net/style/favicon.ico' },
  { id: 304, category_id: 3, name: '斗鱼直播', url: 'https://www.douyu.com', logo_url: 'https://www.douyu.com/favicon.ico' },
  { id: 305, category_id: 3, name: '虎牙直播', url: 'https://www.huya.com', logo_url: 'https://www.huya.com/favicon.ico' },
  { id: 306, category_id: 3, name: '爱奇艺', url: 'https://www.iqiyi.com', logo_url: 'https://www.iqiyi.com/favicon.ico' },
  { id: 307, category_id: 3, name: '腾讯视频', url: 'https://v.qq.com', logo_url: 'https://v.qq.com/favicon.ico' },

  // ================= 4. 实用工具 =================
  { id: 401, category_id: 4, name: '阿里云盘', url: 'https://www.aliyundrive.com', logo_url: 'https://img.alicdn.com/imgextra/i1/O1CN01rGJZac1Zn37NLZ0Er_!!6000000003238-2-tps-120-120.png' },
  { id: 402, category_id: 4, name: '百度网盘', url: 'https://pan.baidu.com', logo_url: 'https://pan.baidu.com/favicon.ico' },
  { id: 403, category_id: 4, name: '语雀', url: 'https://www.yuque.com', logo_url: 'https://gw.alipayobjects.com/zos/rmsportal/UTjFYEzMSYVwzxGFxaNM.png' },
  { id: 404, category_id: 4, name: 'Canva 可画', url: 'https://www.canva.cn', logo_url: 'https://static.canva.com/static/images/favicon-1.ico' },
  { id: 405, category_id: 4, name: 'Figma', url: 'https://www.figma.com', logo_url: 'https://www.figma.com/favicon.ico' },
  { id: 406, category_id: 4, name: '石墨文档', url: 'https://shimo.im', logo_url: 'https://shimo.im/favicon.ico' },
  { id: 407, category_id: 4, name: 'DeepL 翻译', url: 'https://www.deepl.com', logo_url: 'https://www.deepl.com/favicon.ico' },

  // ================= 5. AI 神器 =================
  { id: 501, category_id: 5, name: 'ChatGPT', url: 'https://chat.openai.com', logo_url: 'https://chat.openai.com/favicon.ico' },
  { id: 502, category_id: 5, name: 'Kimi', url: 'https://kimi.moonshot.cn', logo_url: 'https://kimi.moonshot.cn/favicon.ico' },
  { id: 503, category_id: 5, name: '文心一言', url: 'https://yiyan.baidu.com', logo_url: 'https://yiyan.baidu.com/favicon.ico' },
  { id: 504, category_id: 5, name: '通义千问', url: 'https://tongyi.aliyun.com', logo_url: 'https://img.alicdn.com/imgextra/i4/O1CN013pYOWI1a7E918yFp8_!!6000000003282-2-tps-288-288.png' },
  { id: 505, category_id: 5, name: '智谱清言', url: 'https://chatglm.cn', logo_url: 'https://chatglm.cn/favicon.ico' },
  { id: 506, category_id: 5, name: '豆包', url: 'https://www.doubao.com', logo_url: 'https://www.doubao.com/favicon.ico' },
  { id: 507, category_id: 5, name: '秘塔AI搜索', url: 'https://metaso.cn', logo_url: 'https://metaso.cn/favicon.ico' },
  { id: 508, category_id: 5, name: 'Midjourney', url: 'https://www.midjourney.com', logo_url: 'https://www.midjourney.com/favicon.ico' }
])
const leaderboard = ref([])
const searchQuery = ref('')

// ✨ 2. 搜索引擎配置 (扩充了搜狗、淘宝、B站等)
const currentEngine = ref('baidu')
const engines = {
  baidu: 'https://www.baidu.com/s?wd=',
  google: 'https://www.google.com/search?q=',
  bing: 'https://cn.bing.com/search?q=',
  360: 'https://www.so.com/s?q=',
  sogou: 'https://www.sogou.com/web?query=',
  taobao: 'https://s.taobao.com/search?q=',
  bilibili: 'https://search.bilibili.com/all?keyword='
}
const engineNames = {
  baidu: '百度',
  google: '谷歌',
  bing: '必应',
  360: '360',
  sogou: '搜狗',
  taobao: '淘宝',
  bilibili: 'B站'
}

// ✨ 根据悬浮选中的分类动态过滤网站列表
const filteredWebsites = computed(() => {
  if (activeCategoryId.value === 'all') {
    return websites.value
  }
  return websites.value.filter(site => site.category_id == activeCategoryId.value)
})

// AI 聊天状态
const chatWindow = ref(null)
const chatMessages = ref([
  { role: 'ai', content: '你好！我是导航助手，想找什么神仙网站？直接问我！' }
])
const userInput = ref('')
const isAiThinking = ref(false)

const doSearch = () => {
  if (searchQuery.value) window.open(engines[currentEngine.value] + encodeURIComponent(searchQuery.value), '_blank')
}

const sendMessage = async () => {
  const text = userInput.value.trim()
  if (!text || isAiThinking.value) return

  chatMessages.value.push({ role: 'user', content: text })
  userInput.value = ''
  isAiThinking.value = true
  scrollToBottom()

  try {
    const res = await axios.post('http://127.0.0.1:5000/api/chat', { message: text })
    chatMessages.value.push({ role: 'ai', content: res.data.reply })
  } catch (error) {
    chatMessages.value.push({ role: 'ai', content: '网络走神了，请稍后再试！' })
    console.error(error)
  } finally {
    isAiThinking.value = false
    scrollToBottom()
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (chatWindow.value) {
      chatWindow.value.scrollTop = chatWindow.value.scrollHeight
    }
  })
}

// 请把代码最下方 onMounted 里面的内容完整替换为以下代码：
onMounted(async () => {
  try {
    // 尝试从后端获取最新数据
    const res = await axios.get('http://127.0.0.1:5000/api/data')
    
    if (res && res.data) {
      if (res.data.categories?.length > 0) categories.value = res.data.categories
      if (res.data.websites?.length > 0) websites.value = res.data.websites
    }

    // 获取排行榜
    const rankRes = await axios.get('http://127.0.0.1:5000/api/leaderboard')
    if (rankRes.data?.length > 0) leaderboard.value = rankRes.data
    
  } catch (e) { 
    // 如果后端没开（比如断网了），这里会报错，但因为有 try-catch，
    // 前端会保持使用代码里写好的默认 websites 数据，不会白屏
    console.warn("后端连接失败，已加载预置离线数据", e) 
  }
})
</script>

<style scoped>
/* ================= 全局色彩与布局变量 ================= */
:root {
  --primary: #2563eb;      
  --primary-bright: linear-gradient(135deg, #3b82f6, #2563eb); 
  --bg-main: #e2e8f0;      
  --bg-block: #ffffff;     
  --bg-input: #f1f5f9;     
  --text-main: #1e293b;    
  --text-muted: #64748b;   
  --border-light: #cbd5e1; 
}

.layout.dark-theme {
  --primary: #3b82f6;      
  --primary-bright: linear-gradient(135deg, #60a5fa, #3b82f6); 
  --bg-main: #000000;      
  --bg-block: #1e293b; 
  --bg-input: #0f172a;     
  --text-main: #f8fafc;    
  --text-muted: #94a3b8;   
  --border-light: #334155; 
}

/* ================= 针对深色模式的强制颜色修正 ================= */
.layout.dark-theme .nav-tab { color: #94a3b8; }
.layout.dark-theme .nav-tab:hover { color: #f8fafc; }
.layout.dark-theme .nav-tab.active { color: #f8fafc !important; }
.layout.dark-theme .nav-tab.active::after { background-color: #60a5fa; box-shadow: 0 0 8px rgba(96, 165, 250, 0.6); }

.layout.dark-theme .pill-btn { background-color: #0f172a; color: #ffffff !important; border: 1px solid #334155; }
.layout.dark-theme .pill-btn:hover { border-color: var(--primary); color: var(--primary) !important; }
.layout.dark-theme .btn-primary { background: var(--primary-bright); color: #ffffff !important; font-weight: 900; box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4); }

/* 全局基础 */
.layout { height: 100vh; display: flex; flex-direction: column; background-color: var(--bg-main); color: var(--text-main); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; transition: background-color 0.4s ease, color 0.4s ease; }
.block-shadow { background-color: var(--bg-block); box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08); border: 1px solid var(--border-light); transition: background-color 0.4s ease, border-color 0.4s ease; }
.layout.dark-theme .block-shadow { box-shadow: 0 6px 16px rgba(0, 0, 0, 0.5); }

/* ================= 1. 顶部导航栏 ================= */
.header-block { 
  height: 65px; background-color: var(--bg-block); display: flex; justify-content: space-between; align-items: center; 
  padding: 0 40px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border-bottom: 1px solid var(--border-light); 
  z-index: 100; flex-shrink: 0; transition: background-color 0.4s ease, border-color 0.4s ease; 
}
.header-left { display: flex; align-items: center; }
.logo { font-size: 22px; font-weight: 800; display: flex; align-items: center; gap: 8px; color: var(--text-main); }
.auth-buttons { display: flex; gap: 15px; align-items: center; }

.theme-toggle { background: transparent; border: none; font-size: 20px; cursor: pointer; padding: 5px; transition: 0.3s; }
.theme-toggle:hover { transform: scale(1.15) rotate(15deg); }
.pill-btn { background-color: var(--bg-block); color: #1e293b; border: 1px solid var(--border-light); padding: 8px 22px; border-radius: 25px; cursor: pointer; font-size: 14px; font-weight: 800; transition: all 0.3s ease; }
.pill-btn:hover:not(:disabled) { transform: translateY(-2px); border-color: var(--primary); }
.btn-primary { background: var(--primary-bright); color: #ffffff !important; border: none; padding: 10px 24px; border-radius: 25px; cursor: pointer; font-size: 14px; font-weight: 900; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35); transition: all 0.3s ease; }
.btn-primary:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(37, 99, 235, 0.5); }

/* ================= 2. 容器 & 布局 ================= */
.main-container { display: flex; flex: 1; overflow: hidden; padding: 25px; gap: 25px; }

/* ================= 3. 中间内容区 ================= */
.content { 
  flex: 1; overflow-y: auto; display: flex; flex-direction: column; align-items: center; 
  padding: 10px 40px 40px 40px; scroll-behavior: smooth; position: relative;
}
.content::-webkit-scrollbar { width: 6px; }
.content::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }

/* ✨ 新增：中心操作区域 (分类 + 搜索框，增加 margin-top 往下挤一点) */
.center-action-area {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 30px;  /* ✨ 让这块区域往下走，呈现稍微居中的效果 */
  margin-bottom: 30px;
}

/* ✨ 分类栏放到中间，样式重构 */
.category-tabs-wrapper {
  display: flex;
  gap: 35px;
  justify-content: center;
  margin-bottom: 30px; /* 距离下方搜索框的距离 */
  flex-wrap: wrap;
}

.nav-tab { 
  cursor: pointer; position: relative; font-size: 16px; font-weight: 600; color: var(--text-muted); 
  display: flex; align-items: center; transition: 0.3s ease; padding: 5px 10px;
}
.nav-tab:hover { color: var(--text-main); }
.nav-tab.active { color: var(--primary) !important; font-weight: 800; }
.nav-tab.active::after {
  content: ''; position: absolute; bottom: 0; left: 50%; transform: translateX(-50%);
  width: 60%; height: 3px; background-color: var(--primary); border-radius: 3px 3px 0 0;
}

/* ✨ 重塑搜索区：完全符合手绘图 */
.search-section { width: 100%; max-width: 650px; display: flex; flex-direction: column; align-items: center;margin-bottom: 30px;}

/* 输入框在上方 */
.search-box { 
  width: 100%; display: flex; align-items: center; border-radius: 40px; padding: 6px 6px 6px 25px; 
  background: var(--bg-block); border: 2px solid var(--text-main); margin-bottom: 0;
}
.search-box input { flex: 1; border: none; outline: none; font-size: 16px; background: transparent; color: var(--text-main); font-weight: 600;}
.search-box input::placeholder { color: var(--text-muted); }
.search-btn-oval { 
  background: transparent; color: var(--text-main); border: 2px solid var(--text-main); 
  border-radius: 20px; padding: 8px 25px; cursor: pointer; font-weight: 900; transition: 0.3s; 
}
.search-btn-oval:hover { background: var(--text-main); color: var(--bg-block); }

/* 引擎在下方 */
.search-engines-wrapper { display: flex; gap: 25px; justify-content: center;flex-wrap:wrap; margin-top: -5px;;}
.engine-option { display: flex; flex-direction: column; align-items: center; cursor: pointer; gap: 6px; }

/* 倒三角指示器 */
.triangle-down {
  width: 0; height: 0;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-top: 8px solid #60a5fa;
  opacity: 0; transition: 0.3s; transform: translateY(-2px);
}
.engine-option.active .triangle-down { opacity: 1; transform: translateY(4px); }

.engine-name { font-size: 15px; color: var(--text-muted); font-weight: 600; transition: 0.2s; }
.engine-option.active .engine-name { color: var(--text-main); font-weight: 800; }

/* 深色模式下的搜索引擎样式修饰 */
.layout.dark-theme .search-box { border: 2px solid #334155; }
.layout.dark-theme .search-btn-oval { border-color: #334155; color: #f8fafc; }
.layout.dark-theme .search-btn-oval:hover { background: #334155; color: #ffffff; }
.layout.dark-theme .triangle-down { border-top-color: var(--primary); }
.layout.dark-theme .engine-option.active .engine-name { color: var(--primary); }
/* 网格内容区 */
.site-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 20px; width: 100%; max-width: 900px; align-content: start;}
.site-card { border-radius: 12px; padding: 20px 10px; display: flex; flex-direction: column; align-items: center; text-decoration: none; color: var(--text-main); transition: transform 0.3s ease; }
.site-card:hover { transform: translateY(-5px); box-shadow: 0 10px 25px rgba(0,0,0,0.15); border-color: transparent;}
.layout.dark-theme .site-card:hover { box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
/* 强制约束 Logo 大小，无论原图多大 */
/* 确保 logo 容器有固定大小 */
.logo-wrapper {
  width: 54px;
  height: 54px;
  margin-bottom: 10px;
  background: #ffffff;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05); /* 让白底更好看 */
}

/* 强制图片填满容器并保持比例 */
.site-logo {
  width: 100%;
  height: 100%;
  object-fit: contain; /* 保证图片不拉伸 */
  padding: 8px;        /* 给图标留点呼吸感 */
}
.site-name { font-size: 14px; font-weight: 600; }

/* ================= 4. 右侧 AI 与排行 ================= */
.sidebar-right {
  width: 320px; display: flex; flex-direction: column; gap: 20px; 
  background: transparent !important; border: none !important; box-shadow: none !important;
}

.widget { background-color: var(--bg-block); border-radius: 16px; border: 1px solid var(--border-light); overflow: hidden; display: flex; flex-direction: column; box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08); }
.layout.dark-theme .widget { box-shadow: 0 6px 16px rgba(0, 0, 0, 0.5); }
.ai-widget { flex: 1; min-height: 400px; }
.rank-widget { flex-shrink: 0; }

.widget-header { padding: 18px 20px; border-bottom: 1px solid var(--border-light); background: var(--bg-block); margin: 0; }
.widget-header h3 { margin: 0; font-size: 16px; color: var(--text-main); font-weight: 800;}

/* AI 聊天样式 */
.chat-window { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 16px; background-color: var(--bg-input); scrollbar-width: none; transition: 0.4s ease;}
.chat-window::-webkit-scrollbar { display: none; }
.chat-bubble { max-width: 85%; padding: 12px 16px; font-size: 14px; line-height: 1.6; word-wrap: break-word; font-weight: 600; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);}
.chat-bubble.ai { align-self: flex-start; background: #2563eb; color: #ffffff !important; border-radius: 2px 18px 18px 18px; border: 1px solid #1d4ed8; }
.chat-bubble.user { align-self: flex-end; background: #1e293b; color: #ffffff !important; border-radius: 18px 18px 2px 18px; }

.thinking { display: flex; align-items: center; gap: 5px; }
.dot { width: 6px; height: 6px; background: #ffffff !important; border-radius: 50%; animation: bounce 1.4s infinite ease-in-out both; }
.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }
@keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }

.chat-input { display: flex; align-items: center; padding: 15px; background: var(--bg-block); border-top: 1px solid var(--border-light); }
.chat-input input { flex: 1; border: 1px solid var(--border-light); padding: 12px 18px; outline: none; font-size: 14px; background: var(--bg-input); border-radius: 25px; margin-right: 12px; color: var(--text-main); font-weight: 600; transition: 0.4s ease;}

/* 发送按钮修正 */
.btn-send { 
  background: var(--primary-bright); color: #ffffff !important; border: none; padding: 10px 22px; border-radius: 25px; font-weight: 900; cursor: pointer; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3); transition: 0.3s;
  display: flex; align-items: center; justify-content: center; white-space: nowrap; min-width: 70px;
}
.btn-send:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 15px rgba(37, 99, 235, 0.4);}
.btn-send:disabled { background: var(--border-light); box-shadow: none; cursor: not-allowed; color: var(--text-muted) !important;}

/* 排行榜 */
.rank-list { list-style: none; padding: 10px 20px; margin: 0; }
.rank-item { display: flex; align-items: center; gap: 12px; padding: 14px 0; border-bottom: 1px dashed var(--border-light); }
.rank-item:last-child { border-bottom: none; }
.rank-num { width: 24px; height: 24px; background: var(--bg-input); display: flex; align-items: center; justify-content: center; border-radius: 6px; font-size: 13px; font-weight: bold; color: var(--text-muted); }
.rank-num.top-3 { background: #fee2e2; color: #ef4444; }
.layout.dark-theme .rank-num.top-3 { background: #7f1d1d; color: #fca5a5; }
.rank-name { flex: 1; font-size: 14px; font-weight: 600;}
.rank-clicks { color: var(--text-muted); font-size: 12px; font-weight: 500;}
</style>