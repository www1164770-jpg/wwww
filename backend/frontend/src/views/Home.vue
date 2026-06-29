<template>
<div class="layout" :class="[{ 'dark-theme': isDarkMode }, uiState]" :style="dynamicBgStyle" @click="closeAllDropdowns">    
    <transition name="space-fade">
      <div v-if="isSpaceIntroPlaying" class="space-particle-wrapper">
        <canvas ref="particleCanvas" class="particle-canvas"></canvas>
      </div>
    </transition>

    <div v-show="isFocusMode" class="focus-dark-overlay" :style="focusBgStyle"></div>
    
    <div v-if="currentPage === 'home'" class="stack-home">
      <header class="stack-header">
        <button class="stack-logo" @click="goHome" aria-label="智慧导航首页">
          <span class="stack-logo-mark">≡</span>
          <strong>智慧导航</strong>
        </button>
        <nav class="stack-nav" aria-label="主导航">
          <button class="is-active">Tools</button>
          <button @click="activeStackCategory = 'stacks'">Stacks</button>
          <button @click="activeStackCategory = 'compare'">Compare</button>
          <button @click="activeStackCategory = 'blog'">Blog</button>
          <button @click="activeStackCategory = 'about'">About</button>
        </nav>
        <div class="stack-header-actions">
          <button class="stack-icon-search" @click="searchInputRef?.focus()" aria-label="搜索">⌕</button>
          <button class="stack-browse-btn" @click="openAddSiteModal">添加网站</button>
        </div>
      </header>

      <main class="stack-main">
        <section class="stack-hero">
          <h1>The stack you'll actually use.</h1>
          <p>为高效上网、学习、创作和工作准备的网站与工具目录。</p>
          <div class="stack-search">
            <input
              ref="searchInputRef"
              v-model="searchQuery"
              @keyup.enter="doSearch"
              @focus="isSearchFocused = true"
              @blur="handleSearchBlur"
              type="text"
              placeholder="Search websites by name (e.g. GitHub, Notion, Bilibili)..."
            />
            <button @click="doSearch" aria-label="搜索">⌕</button>
            <transition name="stack-dropdown">
              <div v-show="isSearchFocused && (localSuggestions.length > 0 || searchHistory.length > 0 || searchQuery)" class="stack-search-dropdown">
                <template v-if="searchQuery && localSuggestions.length > 0">
                  <button
                    v-for="site in localSuggestions"
                    :key="'stack-sugg-' + site.id"
                    class="stack-search-row"
                    @click="handleSiteClick(site)"
                  >
                    <img :src="site.logo_url || getLogoUrl(site.url)" @error="handleIconError($event, site)" alt="">
                    <span>
                      <strong v-html="site._formatted?.name || displaySiteName(site)"></strong>
                      <small v-html="site._formatted?.url || site.url"></small>
                    </span>
                  </button>
                </template>
                <template v-else-if="searchHistory.length > 0">
                  <button v-for="item in searchHistory" :key="'stack-history-' + item" class="stack-history-row" @click="useHistory(item)">
                    {{ item }}
                  </button>
                </template>
                <button v-if="searchQuery" class="stack-search-engine" @click="doSearch">
                  在 {{ allEngines[currentEngine]?.name || '搜索引擎' }} 搜索 "{{ searchQuery }}"
                </button>
              </div>
            </transition>
          </div>
          <div class="stack-meta">{{ stackToolCount }} tools saved · {{ stackCategories.length }} active categories · data pinned</div>
          <div class="stack-quick-links">
            <button @click="activeCategoryId = 'all'">Browse all tools ›</button>
            <button @click="activeCategoryId = 'favorites'">See favorites ›</button>
            <button @click="openAddSiteModal">Submit a tool ›</button>
          </div>
        </section>

        <section class="stack-marquee" aria-label="热门网站">
          <div class="stack-marquee-track">
            <span v-for="site in marqueeSites" :key="'marquee-a-' + site.id">{{ displaySiteName(site) }}</span>
            <span v-for="site in marqueeSites" :key="'marquee-b-' + site.id">{{ displaySiteName(site) }}</span>
          </div>
        </section>

        <section class="stack-category-section">
          <div class="stack-category-menu">
            <h2>Most Popular<br>Categories</h2>
            <button
              v-for="cat in stackCategories"
              :key="cat.key"
              :class="{ 'is-active': activeStackCategory === cat.key }"
              @click="selectStackCategory(cat)"
            >
              {{ cat.label }}
            </button>
            <button class="stack-see-all" @click="activeCategoryId = 'all'">See all {{ stackToolCount }} tools ›</button>
          </div>
          <div class="stack-tools-area">
            <button class="stack-section-link" @click="activeCategoryId = 'all'">See all {{ activeStackCategoryLabel }} ›</button>
            <div class="stack-tool-grid">
              <button
                v-for="(site, index) in stackTools"
                :key="'stack-tool-' + site.id"
                class="stack-tool-card"
                :style="{ '--stagger': `${index * 45}ms` }"
                @click="handleSiteClick(site)"
                @contextmenu.prevent="openContextMenu($event, site)"
              >
                <span class="stack-tool-icon">
                  <img :src="site.logo_url || getLogoUrl(site.url)" :alt="displaySiteName(site)" @error="handleIconError($event, site)">
                </span>
                <span class="stack-tool-copy">
                  <strong>{{ displaySiteName(site) }}</strong>
                  <small>{{ siteDescription(site) }}</small>
                </span>
              </button>
            </div>
          </div>
        </section>

        <section class="stack-favorites-section">
          <div class="stack-favorites-inner">
            <p class="stack-kicker">FAV STACK</p>
            <h2>Tools I actually build with.</h2>
            <p class="stack-fav-subtitle">收藏、推荐和高频入口会汇总在这里，方便下一次直接打开。</p>
            <div class="stack-fav-list">
              <button
                v-for="site in favoriteStackTools"
                :key="'stack-fav-' + site.id"
                class="stack-fav-item"
                @click="handleSiteClick(site)"
              >
                <span class="stack-tool-icon">
                  <img :src="site.logo_url || getLogoUrl(site.url)" :alt="displaySiteName(site)" @error="handleIconError($event, site)">
                </span>
                <span>
                  <strong>{{ displaySiteName(site) }}</strong>
                  <small>{{ siteDescription(site) }}</small>
                </span>
                <em>{{ stackToolCategory(site) }}</em>
              </button>
            </div>
          </div>
        </section>
      </main>
    </div>
    <div v-else-if="currentPage === 'profile'" class="profile-fullscreen-wrapper">
      <div class="profile-layout-container block-shadow">
        
        <aside class="profile-sidebar">
          <div class="sidebar-header">
            <button class="nav-back-btn" @click="goHome">← 返回首页</button>
          </div>
          <div class="sidebar-user-brief">
            <img :src="userInfo.avatar" class="brief-avatar" @error="(e) => e.target.src = 'https://api.dicebear.com/7.x/avataaars/svg?seed=fallback'">
            <div class="brief-info">
              <span class="brief-name">{{ userInfo.username }}</span>
              <span class="brief-role">UID: 8848123</span>
            </div>
          </div>
          <nav class="sidebar-menu">
            <a :class="{ active: activeProfileTab === 'homepage' }" @click="activeProfileTab = 'homepage'">🏠 个人主页</a>
            <a :class="{ active: activeProfileTab === 'settings' }" @click="activeProfileTab = 'settings'">⚙️ 基础资料</a>
            <a :class="{ active: activeProfileTab === 'security' }" @click="activeProfileTab = 'security'">🛡️ 安全设置</a>
            <a :class="{ active: activeProfileTab === 'privacy' }" @click="activeProfileTab = 'privacy'">👁️ 隐私偏好</a>
            <a :class="{ active: activeProfileTab === 'content' }" @click="activeProfileTab = 'content'">📝 内容管理</a>
            <a :class="{ active: activeProfileTab === 'history' }" @click="activeProfileTab = 'history'">👣 互动足迹</a>
          </nav>
          <div class="sidebar-footer">
            <button class="logout-action-btn w-full" @click="handleLogout">退出当前账号</button>
          </div>
        </aside>

        <main class="profile-content-area">
          
          <div v-if="activeProfileTab === 'homepage'" class="tab-panel animate-fade-in">
            <div class="bento-layout">
              
              <div class="bento-item bento-profile block-shadow">
                <div class="avatar-container">
                  <img :src="userInfo.avatar" class="bento-avatar" @error="(e) => e.target.src = 'https://api.dicebear.com/7.x/avataaars/svg?seed=fallback'">
                  <div class="online-status-dot" title="当前在线"></div>
                </div>
                <div class="profile-info-core">
                  <div class="name-row">
                    <h2>{{ userInfo.username }}</h2>
                    <span class="pro-badge">PRO Developer</span>
                  </div>
                  <p class="uid-text">UID: 8848123</p>
                  <p class="bio-text">{{ userInfo.bio || '探索代码边界，专注极致交互与高性能架构。' }}</p>
                  <div class="tech-stack-tags">
                    <span class="tech-tag vue">Vue 3</span>
                    <span class="tech-tag flask">Flask</span>
                    <span class="tech-tag db">MySQL</span>
                  </div>
                </div>
              </div>

              <div class="bento-item bento-stats block-shadow">
                <div class="stat-row">
                  <div class="stat-icon-wrapper blue">👁️</div>
                  <div class="stat-data">
                    <strong>{{ profileStats.views || 0 }}</strong>
                    <span>总阅读量</span>
                  </div>
                </div>
                <div class="stat-row">
                  <div class="stat-icon-wrapper orange">📝</div>
                  <div class="stat-data">
                    <strong>{{ profileStats.posts || 0 }}</strong>
                    <span>发布内容</span>
                  </div>
                </div>
                <div class="stat-row">
                  <div class="stat-icon-wrapper purple">👥</div>
                  <div class="stat-data">
                    <strong>{{ profileStats.followers || 0 }}</strong>
                    <span>关注者</span>
                  </div>
                </div>
              </div>

              <div class="bento-item bento-project block-shadow">
                <div class="bento-header">
                  <h3>🚀 最新发布内容</h3>
                </div>
                <div class="project-cards-container">
                  <div v-if="!myContents || myContents.length === 0" style="color: #94a3b8; font-size: 13px; text-align: center; padding: 20px;">
                    暂无发布的文章或项目
                  </div>
                  
                  <div v-else v-for="item in myContents.slice(0, 2)" :key="item.id" class="proj-card" @click="$router.push(`/article/${item.id}`)" style="cursor: pointer;">                    <div class="proj-details">
                      <h4>{{ item.title }}</h4>
                      <p>发布于 {{ item.time }} · {{ item.views }} 浏览 · {{ item.likes }} 赞</p>
                    </div>
                  </div>
                </div>
              </div>

              <div class="bento-item bento-feed block-shadow">
                <div class="bento-header">
                  <h3>⚡ 最新动态</h3>
                <button class="btn-icon-only" title="发布新动态" @click="$router.push('/publish')">➕</button>                </div>
                <div class="mini-feed-list">
                  <div v-if="!flatHistory || flatHistory.length === 0" style="color: #94a3b8; font-size: 13px; text-align: center; padding: 20px;">
                    暂无动态
                  </div>

                  <div v-else v-for="(item, index) in flatHistory.slice(0, 3)" :key="index" class="mini-feed-item">
                    <div class="feed-dot"></div>
                    <div class="feed-content">
                      <p>
                        <span style="color: #64748b;">{{ item.action }}了</span> 
                        <a :href="item.url" target="_blank" style="color: #3b82f6; font-weight: 600; text-decoration: none;">
                          {{ item.target_name }}
                        </a>
                      </p>
                      <span class="feed-time">{{ item.date }} {{ item.time }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="bento-item bento-lab block-shadow">
                <div class="lab-content">
                  <div class="lab-text">
                    <h3>🔬 视觉体验实验室</h3>
                    <p>一键开启极致暗黑模式，体验更深邃、更专注的沉浸式编码视觉环境。</p>
                  </div>
                  <button class="btn-primary lab-btn" @click="isDarkMode = !isDarkMode; toggleTheme()">
                    <span class="icon">{{ isDarkMode ? '☀️' : '🌙' }}</span> 
                    {{ isDarkMode ? '切换回明亮模式' : '开启暗黑模式体验' }}
                  </button>
                </div>
              </div>

            </div>
          </div>

          <div v-else-if="activeProfileTab === 'settings'" class="tab-panel animate-fade-in">
            <h2 class="panel-title">基础资料</h2>
            <div class="info-card-box block-shadow" style="box-shadow: none;">
              <div class="form-row">
                <span class="row-label">个人头像</span>
                <div class="row-content avatar-edit-row">
                  <input type="file" accept="image/*" class="hidden-file-input" ref="avatarInputRef" @change="handleAvatarUpload">
                  <div class="avatar-upload-wrapper" @click="triggerAvatarUpload" title="点击更换头像">
                    <img :src="userInfo.avatar" class="circle-avatar" @error="(e) => e.target.src = 'https://api.dicebear.com/7.x/avataaars/svg?seed=fallback'">
                    <div class="avatar-hover-mask"><span>更换头像</span></div>
                  </div>
                </div>
              </div>
              <div class="form-row"><span class="row-label">名称</span><div class="row-content"><input type="text" v-model="userInfo.username" class="inline-input"></div></div>
              <div class="form-row"><span class="row-label">性别</span>
                <div class="row-content">
                  <select v-model="userInfo.gender" class="inline-input"><option value="男">男</option><option value="女">女</option><option value="保密">保密</option></select>
                </div>
              </div>
              <div class="form-row"><span class="row-label">生日</span><div class="row-content"><input type="date" v-model="userInfo.birthday" class="inline-input"></div></div>
              <div class="form-row align-top"><span class="row-label">个性签名</span><div class="row-content"><textarea v-model="userInfo.bio" class="inline-input" rows="3"></textarea></div></div>
            </div>
            <div class="panel-actions"><button class="btn-primary" @click="saveProfileDirectly">保存基础资料</button></div>
          </div>

          <div v-else-if="activeProfileTab === 'security'" class="tab-panel animate-fade-in">
            <h2 class="panel-title">安全设置</h2>
            
            <div class="security-list">
              <div class="security-item">
                <div class="sec-info"><h3>登录密码</h3><p>已设置。建议定期更换密码以提高安全性。</p></div>
                <button class="btn-cancel" @click="openModal('password')">修改</button>
              </div>
              <div class="security-item">
                <div class="sec-info"><h3>绑定邮箱</h3><p>{{ userInfo.email || '未绑定' }}</p></div>
                <button class="btn-cancel" @click="openModal('email')">换绑</button>
              </div>
              <div class="security-item">
                <div class="sec-info"><h3>绑定手机</h3><p>{{ userInfo.phone || '未绑定，绑定后可用于快速找回账号' }}</p></div>
                <button class="btn-primary" @click="openModal('phone')">去绑定</button>
              </div>
            </div>

            <h3 class="panel-subtitle" style="margin-top: 30px;">登录设备管理</h3>
            <div class="device-list">
              <div v-for="dev in loginDevices" :key="dev.id" class="device-item">
                <div class="dev-icon">{{ dev.type === 'pc' ? '💻' : '📱' }}</div>
                <div class="dev-detail">
                  <span class="dev-name">{{ dev.name }} <span v-if="dev.isCurrent" class="dev-tag">当前设备</span></span>
                  <span class="dev-meta">{{ dev.location }} · {{ dev.time }}</span>
                </div>
                <button v-if="!dev.isCurrent" class="btn-danger-text" @click="showToast('已强制下线该设备', 'success')">下线</button>
              </div>
            </div>

            <div class="danger-zone" style="margin-top: 40px; border-top: 1px solid #ef4444; padding-top: 20px;">
              <h3 style="color: #ef4444; margin-bottom: 10px;">危险区域</h3>
              <p style="font-size: 13px; color: #64748b; margin-bottom: 15px;">彻底注销您的账号。系统将保留 15 天冷静期，期间再次登录可撤销注销操作。</p>
              <button class="btn-danger" @click="showToast('已发起注销申请，请在15天内确认', 'error')">申请永久注销账号</button>
            </div>
          </div>

          <div v-else-if="activeProfileTab === 'privacy'" class="tab-panel animate-fade-in">
            <h2 class="panel-title">隐私与偏好</h2>
            <div class="security-list">
              <div class="security-item">
                <div class="sec-info"><h3>公开我的收藏夹</h3><p>允许其他人在你的个人主页查看你的收藏</p></div>
                <label class="switch"><input type="checkbox" v-model="privacySettings.publicFavorites"><span class="slider round"></span></label>
              </div>
              <div class="security-item">
                <div class="sec-info"><h3>在排行榜隐藏我的足迹</h3><p>你的点击和浏览将不会被记入全网热度公开展示</p></div>
                <label class="switch"><input type="checkbox" v-model="privacySettings.hideFootprint"><span class="slider round"></span></label>
              </div>
              <div class="security-item">
                <div class="sec-info"><h3>外观偏好 (暗黑模式)</h3><p>全局颜色主题随系统自动切换或固定</p></div>
                <label class="switch"><input type="checkbox" v-model="isDarkMode" @change="toggleTheme"><span class="slider round"></span></label>
              </div>
              <div class="security-item">
                <div class="sec-info"><h3>界面语言</h3><p>当前系统默认语言</p></div>
                <select class="inline-input" style="width: 120px;"><option>简体中文</option><option>English</option></select>
              </div>
            </div>
          </div>

          <div v-else-if="activeProfileTab === 'content'" class="tab-panel animate-fade-in">
            <h2 class="panel-title">内容管理</h2>
            <div class="content-status-tabs">
              <span :class="{ active: contentTab === 'published' }" @click="contentTab = 'published'">已发布</span>
              <span :class="{ active: contentTab === 'reviewing' }" @click="contentTab = 'reviewing'">审核中</span>
              <span :class="{ active: contentTab === 'draft' }" @click="contentTab = 'draft'">草稿箱</span>
            </div>
            
            <div class="content-list">
              <div v-if="!myContents || myContents.length === 0" class="empty-state-container" style="padding: 30px 0;">
                <div class="empty-icon">📭</div>
                <p class="empty-desc">当前状态下没有内容哦~</p>
              </div>
              
              <div v-else v-for="item in myContents" :key="item.id" class="my-content-item block-shadow">
                <div class="mc-info">
                  <h4>{{ item.title }}</h4>
                  <p>{{ item.time }} · 浏览 {{ item.views || 0 }} · 点赞 {{ item.likes || 0 }}</p>
                </div>
                <div class="mc-actions">
                  <button class="btn-cancel">编辑</button>
                  <button class="btn-danger-text" @click="deleteMyContent(item.id)">删除</button>
                </div>
              </div>
            </div>
          </div>

          <div v-else-if="activeProfileTab === 'history'" class="tab-panel animate-fade-in">
            <div class="panel-header-row">
              <h2 class="panel-title" style="margin: 0;">互动足迹</h2>
              <button class="btn-cancel" @click="clearHistory">🗑️ 清除历史</button>
            </div>
            
            <div class="history-timeline">
              <div v-if="!interactionHistory || interactionHistory.length === 0" class="empty-state-container">
                <p class="empty-desc">暂无任何互动足迹</p>
              </div>

              <div v-else v-for="group in interactionHistory" :key="group.date" class="timeline-day">
                <h4 class="day-title">{{ group.date }}</h4>
                <div v-for="item in group.items" :key="item.id" class="timeline-item">
                  <span class="tl-time">{{ item.time }}</span>
                  <span class="tl-action" :class="{ 'highlight': item.action === '点赞', 'highlight-star': item.action === '收藏' }">
                    {{ item.action }}了
                  </span>
                  <span class="tl-target" @click="window.open(item.url, '_blank')">{{ item.target_name }}</span>
                </div>
              </div>
            </div>
          </div>

          <div v-else-if="activeProfileTab === 'history'" class="tab-panel animate-fade-in">
            <div class="panel-header-row">
              <h2 class="panel-title" style="margin: 0;">互动足迹</h2>
              <button class="btn-cancel" @click="showToast('历史记录已清空', 'success')">🗑️ 清除历史</button>
            </div>
            
            <div class="history-timeline">
              <div class="timeline-day">
                <h4 class="day-title">今天</h4>
                <div class="timeline-item">
                  <span class="tl-time">10:24</span>
                  <span class="tl-action highlight">点赞了</span>
                  <span class="tl-target">文章《2026 前端发展趋势预测》</span>
                </div>
                <div class="timeline-item">
                  <span class="tl-time">09:12</span>
                  <span class="tl-action">浏览了</span>
                  <span class="tl-target">网站 [GitHub]</span>
                </div>
              </div>
              <div class="timeline-day">
                <h4 class="day-title">昨天</h4>
                <div class="timeline-item">
                  <span class="tl-time">18:30</span>
                  <span class="tl-action highlight-star">收藏了</span>
                  <span class="tl-target">网站 [DeepSeek]</span>
                </div>
              </div>
            </div>
          </div>

        </main>
      </div>
    </div>

    <div v-if="showAuthModal" class="auth-overlay" @click="showAuthModal = false">
      <div class="auth-modal" @click.stop>
        <button class="close-btn" @click="showAuthModal = false">×</button>
        <transition name="fade-slide" mode="out-in">
          <div v-if="authStage === 'methods'" key="methods" class="vertical-layout">
            <h2 class="modal-title">快速登录 / 注册</h2>
            <button class="method-btn github" @click="handleGithubLogin">🐱 GitHub 登录</button>
            <button class="method-btn phone" @click="switchTo('mobile')">📱 手机号验证码</button>
            <button class="method-btn email" @click="switchTo('email')">✉️ 邮箱密码登录</button>
            <button class="method-btn register" @click="switchTo('register')" style="margin-top: 10px; border-color: #3b82f6; color: #3b82f6;">✨ 新用户注册</button>
          </div>
          <div v-else-if="authStage === 'mobile'" key="mobile" class="vertical-layout">
            <h2 class="modal-title">手机号登录</h2>
            <input type="text" v-model="phoneNumber" placeholder="请输入手机号" class="auth-input">
            <div class="verify-code-row">
              <input type="text" v-model="verifyCode" placeholder="验证码" class="auth-input small">
              <button class="get-code-btn" @click="alert('验证码发送成功(模拟)')">获取验证码</button>
            </div>
            <button class="btn-submit" @click="handleMobileLogin">立即登录</button>
            <button class="link-btn" @click="switchTo('methods')">返回其他方式</button>
          </div>
          <div v-else-if="authStage === 'email'" key="email" class="vertical-layout">
            <h2 class="modal-title">邮箱密码登录</h2>
            <input type="email" placeholder="请输入邮箱地址" class="auth-input">
            <input type="password" placeholder="请输入密码" class="auth-input">
            <button class="btn-submit">确认登录</button>
            <button class="link-btn" @click="switchTo('methods')">返回其他方式</button>
          </div>
          <!-- ✨ 新增：用户注册面板 -->
          <div v-else-if="authStage === 'register'" key="register" class="vertical-layout">
            <h2 class="modal-title">新用户注册</h2>
            
            <input type="text" v-model="regForm.username" placeholder="给你的账号起个好听的名字" class="auth-input">
            <input type="email" v-model="regForm.email" placeholder="请输入常用邮箱" class="auth-input">
            
            <div class="verify-code-row">
              <input type="text" v-model="regForm.code" placeholder="6位验证码" class="auth-input small">
              <!-- ✨ 倒计时核心按钮 -->
              <button class="get-code-btn" :disabled="countdown > 0" @click="sendCode">
                {{ countdown > 0 ? `${countdown}s 后重发` : '获取验证码' }}
              </button>
            </div>
            
            <input type="password" v-model="regForm.password" placeholder="设置一个强密码" class="auth-input">
            
            <!-- ✨ 用户协议勾选框 -->
            <div class="terms-row" style="margin-top: 5px;">
              <label class="terms-label" style="display: flex; align-items: center; gap: 8px; font-size: 12px; color: #64748b; cursor: pointer;">
                <input type="checkbox" v-model="regForm.agreeTerms" style="width: 14px; height: 14px; cursor: pointer;">
                <span>我已阅读并同意 <a href="/terms" target="_blank" style="color: #3b82f6; text-decoration: none; font-weight: bold;">用户协议</a> 与 <a href="/privacy" target="_blank" style="color: #3b82f6; text-decoration: none; font-weight: bold;">隐私政策</a></span>
              </label>
            </div>
            
            <button class="btn-submit" @click="handleRegister">立即注册</button>
            <button class="link-btn" @click="switchTo('methods')">返回其他方式</button>
          </div>
        </transition>
        <div class="modal-footer">注册/登录即代表同意 <a href="#" target="_blank">用户协议</a></div>
      </div>
    </div>

    <div v-if="currentModalType" class="auth-overlay glass-overlay" @click.self="closeModal">
      <div class="auth-modal edit-modal" @click.stop>
        <button class="close-btn" @click="closeModal">×</button>
        
        <template v-if="currentModalType === 'password'">
          <h2 class="modal-title">修改登录密码</h2>
          <div class="vertical-layout">
            <input type="password" v-model="modalForm.oldPwd" placeholder="请输入当前旧密码" class="auth-input">
            <input type="password" v-model="modalForm.newPwd" placeholder="请输入新密码 (至少6位)" class="auth-input">
            <input type="password" v-model="modalForm.confirmPwd" placeholder="请再次确认新密码" class="auth-input">
            <button class="btn-submit" @click="submitPasswordChange">确认修改，并重新登录</button>
          </div>
        </template>

        <template v-else-if="currentModalType === 'email'">
          <h2 class="modal-title">换绑邮箱</h2>
          <div class="vertical-layout">
            <input type="email" v-model="modalForm.email" placeholder="请输入新邮箱地址" class="auth-input">
            <div class="verify-code-row">
              <input type="text" v-model="modalForm.emailCode" placeholder="6位验证码" class="auth-input small">
              <button class="get-code-btn" :disabled="emailCountdown > 0" @click="sendEmailCode">
                {{ emailCountdown > 0 ? `${emailCountdown}s 后重发` : '获取验证码' }}
              </button>
            </div>
            <button class="btn-submit" @click="submitEmailBind">确认换绑</button>
          </div>
        </template>

        <template v-else-if="currentModalType === 'phone'">
          <h2 class="modal-title">绑定手机号</h2>
          <div class="vertical-layout">
            <input type="tel" v-model="modalForm.phone" placeholder="请输入手机号码" class="auth-input">
            <div class="verify-code-row">
              <input type="text" v-model="modalForm.phoneCode" placeholder="6位短信验证码" class="auth-input small">
              <button class="get-code-btn" :disabled="phoneCountdown > 0" @click="sendPhoneCode">
                {{ phoneCountdown > 0 ? `${phoneCountdown}s 后重发` : '获取验证码' }}
              </button>
            </div>
            <button class="btn-submit" @click="submitPhoneBind">立即绑定</button>
          </div>
        </template>

      </div>
    </div>
    <div v-if="showEditModal" class="auth-overlay" @click="showEditModal = false">
      <div class="auth-modal edit-modal" @click.stop>
        <button class="close-btn" @click="showEditModal = false">×</button>
        <h2 class="modal-title">{{ editingTitle }}</h2>
        <div class="edit-form-container">
          <div v-if="editingField === 'avatar'" class="avatar-edit-section">
            <div class="avatar-preview-wrapper" style="margin: 0 auto 15px auto;">
              <img :src="editForm.avatar || userInfo.avatar" class="avatar-img" alt="头像" @error="(e) => e.target.src = 'https://api.dicebear.com/7.x/avataaars/svg?seed=fallback'">
            </div>
            <input type="text" v-model="editForm.avatar" placeholder="请输入新的头像图片链接 URL" class="auth-input">
            <p style="font-size:12px; color:#64748b; margin-top:8px; text-align:center;">暂不支持本地上传，请输入网络图片地址</p>
          </div>
          <div v-else-if="editingField === 'username'" class="input-group">
            <input type="text" v-model="editForm.username" placeholder="请输入新名称" class="auth-input">
          </div>
          <div v-else-if="editingField === 'gender'" class="input-group">
            <select v-model="editForm.gender" class="auth-input custom-select">
              <option value="男">男</option>
              <option value="女">女</option>
              <option value="保密">保密</option>
            </select>
          </div>
          <div v-else-if="editingField === 'birthday'" class="input-group">
            <input type="date" v-model="editForm.birthday" class="auth-input">
          </div>
          <div v-else-if="editingField === 'email'" class="input-group">
            <input type="email" v-model="editForm.email" placeholder="例如: name@example.com" class="auth-input">
          </div>
          <div v-else-if="editingField === 'bio'" class="input-group">
            <textarea v-model="editForm.bio" placeholder="介绍一下你自己吧..." class="auth-input" rows="3" maxlength="50"></textarea>
            <span class="char-counter">{{ editForm.bio?.length || 0 }}/50</span>
          </div>
          <button class="btn-submit" @click="saveProfile">保存修改</button>
        </div>
      </div>
    </div>

    <div v-if="showAddSiteModal" class="auth-overlay" @click="showAddSiteModal = false">
      <div class="auth-modal edit-modal" @click.stop>
        <button class="close-btn" @click="showAddSiteModal = false">×</button>
        <h2 class="modal-title">{{ isEditingSite ? '✏️ 编辑网站信息' : '✨ 推荐新网站' }}</h2>
        <div class="vertical-layout">
          <input type="text" v-model="newSiteForm.name" placeholder="网站名称" class="auth-input">
          <input type="text" v-model="newSiteForm.url" placeholder="网站链接" class="auth-input">
          <select v-model="newSiteForm.category_id" class="auth-input custom-select">
            <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
          </select>
          <button class="btn-submit" @click="submitNewSite">{{ isEditingSite ? '保存修改' : '立即添加' }}</button>
        </div>
      </div>
    </div>

    <div v-if="showAddCategoryModal" class="auth-overlay" @click="showAddCategoryModal = false">
      <div class="auth-modal edit-modal" @click.stop>
        <button class="close-btn" @click="showAddCategoryModal = false">×</button>
        <h2 class="modal-title">✨ 新建分类</h2>
        <div class="vertical-layout">
          <input type="text" v-model="newCategoryName" placeholder="分类名称" class="auth-input">
          <button class="btn-submit" @click="submitNewCategory">确定添加</button>
        </div>
      </div>
    </div>

    <div v-if="showAddProfModal" class="auth-overlay" @click="showAddProfModal = false">
      <div class="auth-modal edit-modal" @click.stop>
        <button class="close-btn" @click="showAddProfModal = false">×</button>
        <h2 class="modal-title">{{ isEditingProf ? '✏️ 编辑职业' : '✨ 自定义新职业' }}</h2>
        <div class="vertical-layout">
          <input type="text" v-model="newProf.name" placeholder="输入职业名称" class="auth-input">
          <input type="text" v-model="newProf.icon" placeholder="输入图标 (Emoji)" class="auth-input">
          <button class="btn-submit" @click="handleConfirmAdd">
            {{ isEditingProf ? '保存修改' : '确认创建' }}
          </button>
        </div>
      </div>
    </div>

    <transition name="toast-fade">
      <div v-if="toast.show" class="toast-message block-shadow" :class="toast.type">
        <span class="toast-icon">{{ toast.type === 'success' ? '✨' : '⚠️' }}</span>
        <span>{{ toast.message }}</span>
      </div>
    </transition>
<transition name="fade-slide">
      <div v-show="contextMenu.show" class="context-menu block-shadow" :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }" @click.stop>
        
        <template v-if="contextMenu.site">
          <div class="context-header">管理 {{ contextMenu.site.name }}</div>
          
          <div class="context-item" @click="toggleSiteToFocus(contextMenu.site); contextMenu.show = false">
            {{ favoriteSites.find(s => s.url === contextMenu.site.url) ? '🚀 从专注轨道收回' : '🚀 设为专注模式常用' }}
          </div>
          <div class="context-menu-divider"></div>
          
          <div class="context-item" @click="editSite">✏️ 编辑此网站</div>
          <div class="context-item danger" @click="deleteSite">🗑️ 移除此网站</div>
        </template>

        <template v-else>
          <div class="context-header">管理分类</div>
          <div class="context-item" @click="editCategory">✏️ 编辑分类</div>
          <div class="context-item danger" @click="deleteCategory">🗑️ 移除分类</div>
        </template>

      </div>
    </transition>

    <div v-if="showEngineModal" class="auth-overlay" @click="showEngineModal = false">
      <div class="auth-modal engine-modal" @click.stop>
        <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0;">常用搜索设置 ({{ selectedEngines.length }}/{{ searchEngines.length }})</h3>
          <button class="close-btn" @click="showEngineModal = false">×</button>
        </div>
        <div class="selected-tags-area">
          <span v-for="id in selectedEngines" :key="id" class="engine-tag">
            {{ getEngineName(id) }}
            <span class="tag-close" @click="removeEngine(id)">×</span>
          </span>
        </div>
        <div class="modal-divider"></div>
        <div class="engine-checkbox-grid">
          <label v-for="item in searchEngines" :key="item.id" class="engine-toggle-card" :class="{ 'is-active': selectedEngines.includes(item.id) }">
            <input type="checkbox" class="hidden-checkbox" :value="item.id" v-model="selectedEngines">
            <span class="engine-name">
              {{ item.name }}</span>
          </label>
        </div>
      </div>
    </div>

    <div v-if="showBgModal" class="auth-overlay" @click="showBgModal = false">
      <div class="auth-modal engine-modal" @click.stop>
        <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0;">✨ 个性化外观</h3>
          <button class="close-btn" @click="showBgModal = false">×</button>
          
        </div>
        <div class="bg-section" style="margin-top: 20px; padding-top: 15px; border-top: 1px dashed rgba(0,0,0,0.1);">
  <h4>🚀 专注模式星球管理</h4>
  <p style="font-size: 12px; color: #64748b; margin-bottom: 10px;">自定义公转轨道上的常用网站</p>
  <button class="btn-primary w-full" @click="showFocusManageModal = true">管理我的常用网站</button>
</div>
        <div class="bg-options-container">
          <div class="bg-section">
            <h4>🎨 纯色定制</h4>
            <div class="color-picker-wrapper block-shadow">
              <input type="color" v-model="customColorPicker" @input="applyColorBg" class="native-color-picker" title="点击选择颜色">
              <span style="font-weight: 600; font-family: monospace;">{{ customColorPicker.toUpperCase() }}</span>
            </div>
          </div>
          <div class="bg-section">
            <h4>🌈 绝美渐变 (推荐)</h4>
            <div class="gradient-grid">
              
              <div v-for="(grad, index) in presetGradients" :key="index" class="gradient-swatch-wrapper">
                <div class="gradient-swatch" :style="{ background: grad }" @click="applyGradientBg(grad)" :class="{'is-active': customWallpaper === grad}"></div>
                
                <button class="set-focus-bg-btn" @click.stop="applyFocusBg(grad)" title="设为专注模式背景">✨</button>
              </div>
              </div>
          </div>
          <div class="bg-section">
            <h4>🖼️ 图片壁纸</h4>
            <div class="upload-btn-group">
              <button class="btn-submit w-full" @click="triggerWallpaperUpload">从电脑选择高清图片</button>
              <input type="file" accept="image/*" class="hidden-file-input" ref="wallpaperInputRef" @change="handleWallpaperUpload">
            </div>
          </div>
          <div class="bg-section" style="margin-top: 15px; display: flex; gap: 10px;" v-if="customWallpaper || focusWallpaper">
            <button v-if="customWallpaper" class="logout-action-btn w-full" @click="clearBackground" style="text-align: center;">🗑️ 恢复首页默认</button>
            <button v-if="focusWallpaper" class="logout-action-btn w-full" @click="clearFocusBg" style="text-align: center;">🗑️ 恢复专注默认</button>
          </div>
        </div>
      </div>
    </div>

    <Transition name="modal">
      <div v-if="showCategoryModal" class="auth-overlay" @click="showCategoryModal = false">
        <div class="auth-modal" @click.stop>
          <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h3 style="margin: 0;">{{ editingCategory.id ? '✏️ 编辑分类' : '✨ 新建分类' }}</h3>
            <button class="close-btn" @click="showCategoryModal = false">×</button>
          </div>
          <div class="vertical-layout">
            <div class="form-group">
              <label style="display: block; margin-bottom: 8px; font-size: 14px; font-weight: 600;">分类名称</label>
              <input v-model="editingCategory.name" type="text" class="auth-input" placeholder="例如：前端开发" />
            </div>
          </div>
          <div class="modal-footer" style="display: flex; justify-content: space-between; margin-top: 25px;">
            <button v-if="editingCategory.id" class="btn-danger" @click="deleteCategory">删除分类</button>
            <div style="display: flex; gap: 10px; margin-left: auto;">
              <button class="btn-cancel" @click="showCategoryModal = false">取消</button>
              <button class="btn-primary" @click="saveCategory">保存修改</button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <Transition name="fade">
      <div v-if="catContextMenu.show" class="custom-context-menu" :style="{ top: catContextMenu.y + 'px', left: catContextMenu.x + 'px' }" @click.stop>
        <div class="context-menu-item" @click="handleEditFromMenu">✏️ 编辑分类</div>
        <div class="context-menu-divider"></div>
        <div class="context-menu-item danger" @click="handleDeleteFromMenu">🗑️ 删除分类</div>
      </div>
    </Transition>
    <Transition name="fade">
      <div v-if="profContextMenu.show" class="custom-context-menu" :style="{ top: profContextMenu.y + 'px', left: profContextMenu.x + 'px' }" @click.stop>
        <div class="context-menu-item" @click="handleEditProfFromMenu">✏️ 编辑职业</div>
        <div class="context-menu-divider"></div>
        <div class="context-menu-item danger" @click="handleDeleteProfFromMenu">🗑️ 删除职业</div>
      </div>
    </Transition>

    <div v-if="showFocusManageModal" class="auth-overlay" @click="showFocusManageModal = false">
    <div class="auth-modal engine-modal" @click.stop style="max-width: 450px;">
    <div class="modal-header">
      <h3 style="margin: 0;">🚀 星球管理 ({{ favoriteSites.length }}/8)</h3>
      <button class="close-btn" @click="showFocusManageModal = false">×</button>
    </div>

    <div class="focus-sites-list" style="max-height: 300px; overflow-y: auto; margin: 15px 0;">
      <div v-for="(site, index) in favoriteSites" :key="index" class="focus-site-item">
        <div class="site-icon-preview" style="overflow: hidden;">
          <img v-if="site.icon && (site.icon.startsWith('http') || site.icon.startsWith('data:'))" :src="site.icon" style="width: 100%; height: 100%; object-fit: contain; padding: 4px;" />
          <span v-else>{{ site.icon }}</span>
        </div>
        <div class="site-detail">
          <div class="site-name-text">{{ site.name }}</div>
          <div class="site-url-text">{{ site.url }}</div>
        </div>
        <button class="delete-site-btn" @click="removeFocusSite(index)">🗑️</button>
      </div>
    </div>

    <div class="modal-divider"></div>

    <div class="add-focus-form" v-if="favoriteSites.length < 8">
      <h4 style="margin-bottom: 10px; font-size: 14px;">✨ 添加新星球</h4>
      <div class="vertical-layout">
        <div style="display: flex; gap: 8px;">
          <input type="text" v-model="newFocusSite.icon" placeholder="图标/Emoji" class="auth-input" style="width: 80px;">
          <input type="text" v-model="newFocusSite.name" placeholder="网站名称" class="auth-input">
        </div>
        <input type="text" v-model="newFocusSite.url" placeholder="网站链接 (https://...)" class="auth-input">
        <button class="btn-primary w-full" @click="addFocusSite">确认添加</button>
      </div>
    </div>
    <p v-else style="text-align: center; color: #94a3b8; font-size: 12px;">轨道已满，请删除部分后再添加</p>
    </div>
    </div>

    <div v-if="showReviewModal" class="auth-overlay" @click="showReviewModal = false">
      <div class="auth-modal engine-modal" @click.stop style="max-width: 600px;">
        <div class="modal-header">
          <h3 style="margin: 0;">📡 采集审核池 ({{ pendingSites.length }})</h3>
          <button class="close-btn" @click="showReviewModal = false">×</button>
        </div>

        <button 
          class="btn-primary w-full" 
          style="margin: 15px 0; background: #0f172a;" 
          @click="triggerCrawl" 
          :disabled="isCrawling"
        >
          {{ isCrawling ? '🕷️ 爬虫采集中...' : '🕷️ 一键抓取 Hacker News 热门' }}
        </button>

        <div style="max-height: 400px; overflow-y: auto;">
          <div v-if="pendingSites.length === 0" style="text-align: center; color: #94a3b8; padding: 20px;">
            当前没有待审核的站点，快派出爬虫去寻找吧！
          </div>
          
          <div v-for="site in pendingSites" :key="site.id" class="focus-site-item" style="flex-direction: column; align-items: flex-start;">
            <div style="display: flex; justify-content: space-between; width: 100%;">
              <div>
                <div class="site-name-text" style="color: #3b82f6;">[{{ site.source }}]</div>
                <div class="site-name-text" style="font-size: 16px;">{{ site.name }}</div>
              </div>
              <div style="display: flex; gap: 10px;">
                <button @click="handleReview(site.id, 'approve')" style="background: #22c55e; color: white; border: none; padding: 5px 15px; border-radius: 6px; cursor: pointer;">✅ 采用</button>
                <button @click="handleReview(site.id, 'reject')" style="background: #ef4444; color: white; border: none; padding: 5px 15px; border-radius: 6px; cursor: pointer;">❌ 丢弃</button>
              </div>
            </div>
            <a :href="site.url" target="_blank" class="site-url-text" style="margin-top: 5px; text-decoration: underline;">{{ site.url }}</a>
          </div>
        </div>
      </div>
    </div>

    <!-- 🎯 兴趣问卷弹窗 -->
    <SurveyModal
      :visible="showSurveyModal"
      :username="userInfo.username"
      @submit="handleSurveySubmit"
      @skip="handleSurveySkip"
      ref="surveyModalRef"
    />

</div>
</template>

<script setup>
// 修改引入
import { ref, computed, onMounted, onUnmounted, nextTick, watch, reactive} from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import FlexSearch from 'flexsearch'
import SurveyModal from '../components/SurveyModal.vue'
import { userAPI, feedAPI } from '../utils/api'

// ================= 右侧边栏二合一选项卡 =================
const activeSidebarTab = ref('ranking');
const activeHomeCategory = ref('common');
const activeStackCategory = ref('ai-coding');

const stackCategoryFallbacks = [
  { key: 'ai-coding', label: 'AI Coding', categoryId: 4 },
  { key: 'newsletter', label: 'Newsletter', categoryId: 1 },
  { key: 'site-builder', label: 'Site Builder', categoryId: 4 },
  { key: 'ai-seo', label: 'AI SEO', categoryId: 1 },
  { key: 'sales', label: 'Sales / Outreach', categoryId: 3 },
  { key: 'ai-voice', label: 'AI Voice', categoryId: 3 },
  { key: 'email-marketing', label: 'Email Marketing', categoryId: 2 },
  { key: 'crm', label: 'CRM', categoryId: 2 }
];

const stackFallbackTools = [
  { id: 'stack-claude', name: 'Claude Code', url: 'https://claude.ai', desc: 'AI pair coder for terminal workflows', stackCategory: 'AI PAIR' },
  { id: 'stack-cursor', name: 'Cursor', url: 'https://www.cursor.com', desc: 'AI editor built for shipping faster', stackCategory: 'IDE' },
  { id: 'stack-grammarly', name: 'Grammarly', url: 'https://www.grammarly.com', desc: 'Writing assistant for sharper copy', stackCategory: 'WRITING' },
  { id: 'stack-windsurf', name: 'Windsurf', url: 'https://windsurf.com', desc: 'Agentic coding environment', stackCategory: 'AI CODING' },
  { id: 'stack-v0', name: 'v0', url: 'https://v0.dev', desc: 'Generate app interfaces from prompts', stackCategory: 'UI GEN' },
  { id: 'stack-bolt', name: 'Bolt', url: 'https://bolt.new', desc: 'Browser-native AI app builder', stackCategory: 'APP BUILDER' },
  { id: 'stack-lovable', name: 'Lovable', url: 'https://lovable.dev', desc: 'Prompt-to-full-stack product builder', stackCategory: 'PROTOTYPE' },
  { id: 'stack-replit', name: 'Replit Agent', url: 'https://replit.com', desc: 'Build and host from one workspace', stackCategory: 'HOSTED IDE' },
  { id: 'stack-github', name: 'GitHub Copilot', url: 'https://github.com/features/copilot', desc: 'Code suggestions inside your editor', stackCategory: 'CODE' },
  { id: 'stack-astro', name: 'Astro', url: 'https://astro.build', desc: 'Static-first sites that stay fast', stackCategory: 'SITE ENGINE' },
  { id: 'stack-sanity', name: 'Sanity', url: 'https://www.sanity.io', desc: 'Content platform with structured schemas', stackCategory: 'CMS' },
  { id: 'stack-cloudflare', name: 'Cloudflare', url: 'https://www.cloudflare.com', desc: 'DNS, cache and edge platform', stackCategory: 'INFRA' },
  { id: 'stack-kit', name: 'KIT', url: 'https://kit.com', desc: 'Email and creator marketing tools', stackCategory: 'NEWSLETTER' },
  { id: 'stack-supabase', name: 'Supabase', url: 'https://supabase.com', desc: 'Postgres, auth, storage and realtime', stackCategory: 'BACKEND' },
  { id: 'stack-vercel', name: 'Vercel', url: 'https://vercel.com', desc: 'Frontend cloud for fast deployments', stackCategory: 'DEPLOY' }
];

const stackCategories = computed(() => {
  const mapped = (categories.value || []).slice(0, 8).map((cat, index) => ({
    key: `cat-${cat.id ?? index}`,
    label: cat.name || stackCategoryFallbacks[index]?.label || `Category ${index + 1}`,
    categoryId: cat.id ?? 'all'
  }));
  return mapped.length >= 5 ? mapped : stackCategoryFallbacks;
});

const stackToolCount = computed(() => Math.max(websites.value?.length || 0, stackFallbackTools.length));

const normalizeStackSites = (sites, limit) => {
  const merged = [...(sites || []).filter(site => site && site.url)];
  stackFallbackTools.forEach(site => {
    if (merged.length < limit && !merged.some(item => domainOf(item.url) === domainOf(site.url))) merged.push(site);
  });
  return merged.slice(0, limit);
};

const stackTools = computed(() => normalizeStackSites(filteredWebsites.value, 9));

const marqueeSites = computed(() => normalizeStackSites([...featuredSites.value, ...recommendedSites], 20));

const favoriteStackTools = computed(() => {
  const source = favoritedSitesList.value.length ? favoritedSitesList.value : [...recommendedSites, ...featuredSites.value];
  return normalizeStackSites(source, 8);
});

const activeStackCategoryLabel = computed(() => {
  return stackCategories.value.find(cat => cat.key === activeStackCategory.value)?.label || 'tools';
});

const selectStackCategory = (cat) => {
  activeStackCategory.value = cat.key;
  activeHomeCategory.value = cat.key;
  if (cat.categoryId !== undefined) activeCategoryId.value = cat.categoryId;
};

const stackToolCategory = (site) => {
  return site?.stackCategory || activeStackCategoryLabel.value || 'TOOLS';
};

const homeCategories = [
  { key: 'common', label: '常用', categoryId: 'all', icon: '<svg viewBox="0 0 24 24"><path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6h-4v6H5a1 1 0 0 1-1-1v-9.5Z"/></svg>' },
  { key: 'social', label: '社交', categoryId: 3, icon: '<svg viewBox="0 0 24 24"><path d="M16 11a4 4 0 1 0-8 0m12 9a6 6 0 0 0-12 0m10-11a3 3 0 0 1 0 6m3 5a5 5 0 0 0-4-4.9"/></svg>' },
  { key: 'video', label: '视频', categoryId: 3, icon: '<svg viewBox="0 0 24 24"><rect x="4" y="6" width="16" height="12" rx="2"/><path d="m10 9 5 3-5 3V9Z"/></svg>' },
  { key: 'shopping', label: '购物', categoryId: 1, icon: '<svg viewBox="0 0 24 24"><path d="M6 8h12l-1 12H7L6 8Z"/><path d="M9 8a3 3 0 0 1 6 0"/></svg>' },
  { key: 'tools', label: '工具', categoryId: 4, icon: '<svg viewBox="0 0 24 24"><path d="m14 7 3-3 3 3-3 3-3-3ZM4 20l7-7m-4-1 5 5"/><path d="M5 5l4 4"/></svg>' },
  { key: 'study', label: '学习', categoryId: 2, icon: '<svg viewBox="0 0 24 24"><path d="M4 5h7a3 3 0 0 1 3 3v11a3 3 0 0 0-3-3H4V5Zm16 0h-6a3 3 0 0 0-3 3"/></svg>' },
  { key: 'news', label: '新闻', categoryId: 1, icon: '<svg viewBox="0 0 24 24"><rect x="5" y="4" width="14" height="16" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>' },
  { key: 'life', label: '生活', categoryId: 1, icon: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><path d="M9 10h.01M15 10h.01M8.5 14a5 5 0 0 0 7 0"/></svg>' }
];

const hotSearchTags = ['iPhone 16', 'AI 工具', '设计灵感', 'PDF 转换', '高清图片', '效率工具'];

const fallbackFeaturedSites = [
  { id: 'fallback-baidu', name: '百度', url: 'https://www.baidu.com', desc: '百度一下' },
  { id: 'fallback-wechat', name: '微信', url: 'https://weixin.qq.com', desc: '连接每一个生活' },
  { id: 'fallback-douyin', name: '抖音', url: 'https://www.douyin.com', desc: '记录美好生活' },
  { id: 'fallback-taobao', name: '淘宝', url: 'https://www.taobao.com', desc: '美好生活' },
  { id: 'fallback-jd', name: '京东', url: 'https://www.jd.com', desc: '多 · 快 · 好 · 省' },
  { id: 'fallback-bili', name: 'Bilibili', url: 'https://www.bilibili.com', desc: '你感兴趣的视频都在B站' }
];

const recommendedSites = [
  { id: 'rec-chatgpt', name: 'ChatGPT', url: 'https://chat.openai.com', desc: 'AI 智能对话助手' },
  { id: 'rec-notion', name: 'Notion', url: 'https://www.notion.so', desc: '笔记与项目管理' },
  { id: 'rec-canva', name: 'Canva 可画', url: 'https://www.canva.com', desc: '在线设计工具' },
  { id: 'rec-ilovepdf', name: 'iLovePDF', url: 'https://www.ilovepdf.com', desc: 'PDF 处理工具' },
  { id: 'rec-pixabay', name: 'Pixabay', url: 'https://pixabay.com', desc: '免费高清图库' },
  { id: 'rec-docs', name: '腾讯文档', url: 'https://docs.qq.com', desc: '多人协作在线文档' }
];

const recentVisits = [
  { name: '知乎', url: 'https://www.zhihu.com', domain: 'www.zhihu.com', time: '10:24' },
  { name: '微博', url: 'https://weibo.com', domain: 'weibo.com', time: '09:58' },
  { name: '高德地图', url: 'https://www.amap.com', domain: 'amap.com', time: '昨天' },
  { name: '网易云音乐', url: 'https://music.163.com', domain: 'music.163.com', time: '昨天' },
  { name: '小红书', url: 'https://www.xiaohongshu.com', domain: 'xiaohongshu.com', time: '前天' }
];

const fallbackLeaderboard = [
  { title: '神舟十八号载人飞船发射圆满成功', count: '987.6万' },
  { title: 'iPhone 16 系列最新爆料汇总', count: '876.3万' },
  { title: '2024 高考时间公布', count: '768.9万' },
  { title: 'OpenAI 发布全新模型 GPT-4o', count: '654.1万' },
  { title: '比亚迪发布第五代DM技术', count: '521.4万' }
];

const selectHomeCategory = (item) => {
  activeHomeCategory.value = item.key;
  if (item.categoryId !== undefined) activeCategoryId.value = item.categoryId;
};

const knownSiteNames = {
  'bilibili.com': { name: 'Bilibili', desc: '你感兴趣的视频都在B站' },
  'baidu.com': { name: '百度', desc: '百度一下' },
  'weixin.qq.com': { name: '微信', desc: '连接每一个生活' },
  'douyin.com': { name: '抖音', desc: '记录美好生活' },
  'taobao.com': { name: '淘宝', desc: '美好生活' },
  'jd.com': { name: '京东', desc: '多 · 快 · 好 · 省' },
  'zhihu.com': { name: '知乎', desc: '有问题，就会有答案' },
  'xiaohongshu.com': { name: '小红书', desc: '标记我的生活' },
  'weibo.com': { name: '微博', desc: '随时随地发现新鲜事' },
  'douban.com': { name: '豆瓣', desc: '发现好书好电影' },
  'amap.com': { name: '高德地图', desc: '地图导航出行必备' },
  'music.163.com': { name: '网易云音乐', desc: '音乐的力量' },
  'github.com': { name: 'GitHub', desc: '代码托管与协作' },
  'notion.so': { name: 'Notion', desc: '笔记与项目管理' }
};

const domainOf = (url = '') => {
  try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return ''; }
};

const displaySiteName = (site) => {
  const domain = domainOf(site?.url);
  return knownSiteNames[domain]?.name || site?.name || '未命名';
};

const siteDescription = (site) => {
  const domain = domainOf(site?.url);
  return site?.desc || knownSiteNames[domain]?.desc || '快速直达常用网站';
};

const featuredSites = computed(() => {
  const source = (activeHomeCategory.value === 'favorites' ? favoritedSitesList.value : filteredWebsites.value)
    .filter(site => site && site.url)
    .slice(0, 6);
  const merged = [...source];
  fallbackFeaturedSites.forEach(site => {
    if (merged.length < 6 && !merged.some(item => domainOf(item.url) === domainOf(site.url))) merged.push(site);
  });
  return merged.slice(0, 6);
});

const displayLeaderboard = computed(() => {
  const source = (rawLeaderboard.value || []).slice(0, 5).map(item => ({
    ...item,
    count: item.count || (item.clicks ? `${item.clicks}次` : item.clicksText)
  }));
  return source.length ? source : fallbackLeaderboard;
});

const greetingText = computed(() => {
  const hour = new Date().getHours();
  if (hour < 6) return '夜深了';
  if (hour < 12) return '上午好';
  if (hour < 18) return '下午好';
  return '晚上好';
}); // 默认显示排行 ('ranking' 或 'news')

// 确保这两行存在
const showCategoryModal = ref(false); // 控制弹窗显示/隐藏
const editingCategory = ref({ id: null, name: '', icon: '' }); // 存储当前正在编辑的分类

// 在 script setup 中添加这个函数
const openCategoryModal = (cat) => {
  console.log("点击了齿轮，准备打开弹窗", cat); // 调试用
  if (cat) {
    // 如果传了分类，就是编辑模式
    editingCategory.value = { ...cat }; 
  } else {
    // 如果没传，就是新建模式
    editingCategory.value = { id: null, name: '', icon: '🌟' };
  }
  showCategoryModal.value = true; // 🌟 关键：这里设为 true 弹窗才会显示
};

// ================= 分类智能切换与横向拖拽逻辑 =================
const scrollTrack = ref(null);
let isDragging = false;
let startX = 0;
let scrollLeft = 0;

// ✨ 核心：只有在没有拖拽的情况下，鼠标碰到分类才直接切换！
const hoverCategory = (categoryId) => {
  if (!isDragging) {
    activeCategoryId.value = categoryId;
  }
};

// 鼠标按下：开始拖拽
const startDrag = (e) => {
  if (!scrollTrack.value) return;
  isDragging = true;
  startX = e.pageX - scrollTrack.value.offsetLeft;
  scrollLeft = scrollTrack.value.scrollLeft;
};

// 鼠标松开：停止拖拽
const stopDrag = () => {
  isDragging = false;
};

// 鼠标移动：实时滑动滑轨
const onDrag = (e) => {
  if (!isDragging || !scrollTrack.value) return;
  e.preventDefault();
  const x = e.pageX - scrollTrack.value.offsetLeft;
  const walk = (x - startX) * 1.5; 
  scrollTrack.value.scrollLeft = scrollLeft - walk;
};

// ================= 自动采集与审核逻辑 =================
const showReviewModal = ref(false);
const pendingSites = ref([]);
const isCrawling = ref(false);

// 拉取待审核列表
const fetchPendingSites = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:5000/api/admin/pending_sites');
    pendingSites.value = res.data;
  } catch (error) {
    console.error('获取待审核列表失败:', error);
  }
};

// 打开审核面板
const openReviewModal = () => {
  showReviewModal.value = true;
  fetchPendingSites();
};

// 手动触发采集爬虫
const triggerCrawl = async () => {
  isCrawling.value = true;
  showToast('正在向 Hacker News 派出爬虫，请稍候...', 'success');
  try {
    const res = await axios.post('http://127.0.0.1:5000/api/admin/crawl_hn');
    showToast(res.data.message, 'success');
    fetchPendingSites(); // 采集完刷新列表
  } catch (error) {
    showToast('采集失败', 'error');
  } finally {
    isCrawling.value = false;
  }
};

// 处理审核 (通过 / 拒绝)
// ================= 修复版：处理审核 (通过 / 拒绝) =================
const handleReview = async (siteId, action) => {
  try {
    // ✨ 智能容错：如果当前选中的是"全部分类(all)"或"我的收藏(favorites)"，
    // 数据库无法识别字母 ID，默认把它塞进 ID 为 1 的分类里
    let targetCategoryId = activeCategoryId.value;
    if (targetCategoryId === 'all' || targetCategoryId === 'favorites') {
      targetCategoryId = 1; 
    }

    await axios.post('http://127.0.0.1:5000/api/admin/review_site', {
      id: siteId,
      action: action,
      category_id: targetCategoryId 
    });
    
    showToast(action === 'approve' ? '✅ 已通过并发布' : '🗑️ 已拒绝并丢弃', 'success');
    fetchPendingSites(); // 刷新审核池列表
    fetchNavData();      // ✨ 修正：调用你真实的首页数据刷新函数！
    
  } catch (error) {
    console.error('审核报错详情:', error);
    showToast('操作失败，请看控制台', 'error');
  }
};
// ================= 全局请求拦截器：无感刷新 Token =================
axios.interceptors.response.use(
  (response) => {
    return response; // 正常请求，直接放行
  },
  async (error) => {
    const originalRequest = error.config; // 记住刚才失败的那个请求（比如收藏）
    
    // 如果报 401 (未授权)，且这个请求还没有被重试过
    if (error.response && error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true; // 标记为已重试，防止死循环
      
      try {
        // 1. 去 localStorage 拿备用长效钥匙
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) throw new Error('没有备用钥匙');
        
        // 2. 偷偷向后端申请新钥匙
        const res = await axios.post('http://127.0.0.1:5000/api/refresh', null, {
          headers: { Authorization: `Bearer ${refreshToken}` }
        });
        
        // 3. 拿到新钥匙，存进本地
        const newAccessToken = res.data.access_token;
        localStorage.setItem('access_token', newAccessToken);
        
        // 4. 核心魔法 ✨：把刚才失败的请求换上新钥匙，自动再发一次！
        originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`;
        return axios(originalRequest); 
        
      } catch (refreshError) {
        // 如果连备用钥匙都过期了，那只能老老实实清空数据退出了
        console.log('登录已彻底过期，请重新登录');
        localStorage.clear();
        // 刷新页面让状态复原
        window.location.reload(); 
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);


// ================= 分类右键小窗口逻辑 =================
const catContextMenu = ref({
  show: false,
  x: 0,
  y: 0,
  category: null
});

const openCategoryContextMenu = (e, cat) => {
  closeAllDropdowns(); // 弹窗前，先关掉屏幕上其他的菜单
  catContextMenu.value = { 
    show: true, 
    x: e.clientX, 
    y: e.clientY, 
    category: cat 
  };
};
const router = useRouter();
// ================= 🌌 空间生成粒子引擎 (极致慢速显现版) =================
const isSpaceIntroPlaying = ref(false);
const uiState = ref(''); // 控制真实网页的隐藏与慢速显现
const particleCanvas = ref(null);

const playParticleIntro = async () => {
  if (sessionStorage.getItem('space_intro_played')) return;
  
  isSpaceIntroPlaying.value = true;
  uiState.value = 'intro-hidden'; // ✨ 初始让真实网页完全隐身
  sessionStorage.setItem('space_intro_played', 'true');
  
  await nextTick();
  const canvas = particleCanvas.value;
  if (!canvas) return;
  
  const ctx = canvas.getContext('2d');
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  
  const phantomTargets = [];
  // 1. 模拟顶部导航栏
  for(let i=0; i<30; i++) phantomTargets.push({x: canvas.width * (i/30), y: 30 + Math.random()*20});
  // 2. 模拟搜索框
  for(let i=0; i<40; i++) phantomTargets.push({x: canvas.width/2 - 250 + Math.random()*500, y: 150 + Math.random()*40});
  // 3. 模拟网格卡片
  const cols = Math.floor(canvas.width / 200);
  for(let row=0; row<3; row++) {
    for(let col=0; col<cols; col++) {
      for(let i=0; i<10; i++) {
        phantomTargets.push({
           x: (col+0.5) * (canvas.width/cols) + (Math.random()-0.5)*120,
           y: 300 + row * 180 + (Math.random()-0.5)*80
        });
      }
    }
  }

  const particles = [];
  for (let i = 0; i < 400; i++) {
    const startX = Math.random() > 0.5 ? Math.random() * canvas.width : (Math.random() > 0.5 ? -100 : canvas.width + 100);
    const startY = Math.random() > 0.5 ? (Math.random() > 0.5 ? -100 : canvas.height + 100) : Math.random() * canvas.height;
    const target = phantomTargets[i % phantomTargets.length];
    
    particles.push({
      x: startX, y: startY,
      tx: target ? target.x : canvas.width/2,
      ty: target ? target.y : canvas.height/2,
      size: Math.random() * 2 + 0.5,
      speed: 0.015 + Math.random() * 0.015 // ✨ 降低速度，让汇聚过程更像慢动作
    });
  }
  
  let frame = 0;
  
  const render = () => {
    frame++;
    ctx.fillStyle = 'rgba(15, 23, 42, 0.25)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    particles.forEach(p => {
      p.x += (p.tx - p.x) * p.speed;
      p.y += (p.ty - p.y) * p.speed;
      
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = '#38bdf8';
      ctx.shadowBlur = 12;
      ctx.shadowColor = '#38bdf8';
      ctx.fill();
    });
    
    // ✨ 汇聚时间加长到 160 帧（接近 2.5 秒）
    if (frame === 160) {
      isSpaceIntroPlaying.value = false; // 触发黑色遮罩淡出
      uiState.value = 'intro-revealing'; // 触发真实网页超慢速浮现
    }
    
    // ✨ 核心修复：即使开始淡出了，Canvas 也要继续跑！这样光点才不会冻结
    if (frame < 350) { 
      requestAnimationFrame(render);
    } else {
      uiState.value = ''; // 动画彻底跑完，清理状态
    }
  };
  
  render();
};

// ================= 🚑 紧急恢复：被误删的专注模式核心变量 =================
const isFocusMode = ref(false);
const toggleFocusMode = () => { isFocusMode.value = !isFocusMode.value; };
const showFocusManageModal = ref(false);
const favoriteSites = ref(JSON.parse(localStorage.getItem('focus_sites')) || []);
const newFocusSite = ref({ name: '', url: '', icon: '' });
const saveFocusSites = () => {
  localStorage.setItem('focus_sites', JSON.stringify(favoriteSites.value));
  showToast('✨ 常用网站已保存', 'success');
};

// 5. 添加新星球
const addFocusSite = () => {
  if (!newFocusSite.value.name || !newFocusSite.value.url) {
    showToast('⚠️ 请填写名称和链接', 'warning');
    return;
  }
  // 简单提取首字母作为默认图标（如果没有输入 emoji）
  if (!newFocusSite.value.icon) {
    newFocusSite.value.icon = newFocusSite.value.name.charAt(0).toUpperCase();
  }
  favoriteSites.value.push({ ...newFocusSite.value });
  newFocusSite.value = { name: '', url: '', icon: '' };
  saveFocusSites();
};

// 6. 删除星球
const removeFocusSite = (index) => {
  favoriteSites.value.splice(index, 1);
  saveFocusSites();
};
// ✨ 动态计算公转星球：智能切换
const orbitSites = computed(() => {
  // 如果用户有自己的收藏（favoritedSitesList），优先提取他收藏的前 6 个网站
  // 如果没收藏，就使用预设的 favoriteSites 数组
  const sites = favoritedSitesList.value.length > 0 ? favoritedSitesList.value : favoriteSites.value;
  
  // 截取前 6 个，保证轨道上最多只有 6 颗星球，维持完美的视觉间距
  return sites.slice(0, 6); 
});
const goToLogin = () => {
  router.push('/login'); // 点击按钮，瞬间跳到我们刚刚画好的登录页！
};

const sitesData = ref([]) // 初始为空数组

// 核心函数：从 Flask 获取数据
const fetchNavData = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:5000/api/nav-data');
    // 注意：后端返回的是 categories 嵌套 sites 的结构
    // 我们需要把所有的 sites 提取出来给全局的 websites.value
    const allSites = [];
    response.data.forEach(cat => {
      allSites.push(...cat.sites);
    });
    
    websites.value = allSites; // 更新网页显示的卡片
    console.log('数据库数据加载成功');
  } catch (error) {
    console.error('获取导航数据失败:', error);
  }
};

// ================= 配置与基础状态 =================
const AUTH_URLS = { GITHUB: "https://github.com/login/oauth/authorize?client_id=Ov23liK88U1KnvOET8RF&scope=user:email" };
const isDarkMode = ref(false);
const currentPage = ref('home');
const isLoggedIn = ref(false);

// ================= 🎯 兴趣问卷状态 =================
const showSurveyModal = ref(false);
const hasSurvey = ref(true);       // 默认 true，等拿到用户信息后再判断
const surveyModalRef = ref(null);  // 组件引用
const recommendedItems = ref([]);  // 个性化推荐结果
const showAuthModal = ref(false);
const showEditModal = ref(false);
const authStage = ref('methods');
const showAddSiteModal = ref(false);
const showAddCategoryModal = ref(false);
const newCategoryName = ref('');
const newSiteForm = ref({ id: null, name: '', url: '', category_id: '' });
const isEditingSite = ref(false); // ✨ 新增：标识当前是添加还是编辑
const showPasswordModal = ref(false);

// ================= 🚀 注册与倒计时逻辑 =================
const regForm = ref({ oldPwd:'', newPwd:'', confirmPwd:'', username: '', email: '', password: '', code: '', agreeTerms: false });
const countdown = ref(0);
let timer = null;

// ================= 🔒 统一安全弹窗逻辑 =================
// 记录当前弹窗类型：'password' | 'email' | 'phone' | null
const currentModalType = ref(null); 

// 统一的表单数据对象 (接收所有可能输入)
const modalForm = ref({
  oldPwd: '', newPwd: '', confirmPwd: '', // 修改密码专用
  email: '', emailCode: '',               // 邮箱换绑专用
  phone: '', phoneCode: ''                // 手机绑定专用
});

// ================= 📧📱 验证码倒计时与真实绑定逻辑 =================
const emailCountdown = ref(0);
const phoneCountdown = ref(0);
let emailTimer = null;
let phoneTimer = null;

// 1. 发送邮箱验证码
const sendEmailCode = async () => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(modalForm.value.email)) return showToast('⚠️ 请输入正确的邮箱格式', 'error');

  try {
    const res = await axios.post('http://127.0.0.1:5000/api/security/send-email-code', 
      { email: modalForm.value.email }, 
      { headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }}
    );
    if (res.data.code === 0) {
      showToast('📧 验证码已发送至邮箱，请查收', 'success');
      emailCountdown.value = 60;
      emailTimer = setInterval(() => {
        emailCountdown.value--;
        if (emailCountdown.value <= 0) clearInterval(emailTimer);
      }, 1000);
    } else { throw new Error(res.data.msg); }
  } catch (error) { showToast('❌ 发送失败：' + (error.response?.data?.msg || '网络错误'), 'error'); }
};

// 2. 发送手机验证码
const sendPhoneCode = async () => {
  const phoneRegex = /^1[3-9]\d{9}$/;
  if (!phoneRegex.test(modalForm.value.phone)) return showToast('⚠️ 请输入正确的11位手机号', 'error');

  try {
    const res = await axios.post('http://127.0.0.1:5000/api/security/send-sms-code', 
      { phone: modalForm.value.phone }, 
      { headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }}
    );
    if (res.data.code === 0) {
      showToast('📱 验证码短信已发送', 'success');
      phoneCountdown.value = 60;
      phoneTimer = setInterval(() => {
        phoneCountdown.value--;
        if (phoneCountdown.value <= 0) clearInterval(phoneTimer);
      }, 1000);
    } else { throw new Error(res.data.msg); }
  } catch (error) { showToast('❌ 发送失败：' + (error.response?.data?.msg || '网络错误'), 'error'); }
};

// 3. 提交绑定邮箱
const submitEmailBind = async () => {
  if (!modalForm.value.emailCode) return showToast('⚠️ 请输入验证码', 'error');
  try {
    const res = await axios.post('http://127.0.0.1:5000/api/security/bind-email', 
      { email: modalForm.value.email, code: modalForm.value.emailCode }, 
      { headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }}
    );
    if (res.data.code === 0) {
      showToast('🎉 邮箱绑定成功！', 'success');
      if (userInfo.value) userInfo.value.email = modalForm.value.email; // 局部更新视图
      closeModal();
    } else { throw new Error(res.data.msg); }
  } catch (error) { showToast('❌ 绑定失败：' + (error.response?.data?.msg || '验证码错误'), 'error'); }
};

// 4. 提交绑定手机
const submitPhoneBind = async () => {
  if (!modalForm.value.phoneCode) return showToast('⚠️ 请输入验证码', 'error');
  try {
    const res = await axios.post('http://127.0.0.1:5000/api/security/bind-phone', 
      { phone: modalForm.value.phone, code: modalForm.value.phoneCode }, 
      { headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }}
    );
    if (res.data.code === 0) {
      showToast('🎉 手机绑定成功！', 'success');
      if (userInfo.value) userInfo.value.phone = modalForm.value.phone; // 局部更新视图
      closeModal();
    } else { throw new Error(res.data.msg); }
  } catch (error) { showToast('❌ 绑定失败：' + (error.response?.data?.msg || '验证码错误'), 'error'); }
};

// 打开弹窗的通用方法
const openModal = (type) => {
  currentModalType.value = type;
};

// 统一的关闭与数据重置方法 (右上角 × 和 点击外部背景 共用此方法)
const closeModal = () => {
  currentModalType.value = null; // 隐藏弹窗
  // 彻底清空用户输入的所有临时数据，防止下次打开时残留
  modalForm.value = {
    oldPwd: '', newPwd: '', confirmPwd: '',
    email: '', emailCode: '',
    phone: '', phoneCode: ''
  };
  emailCountdown.value = 0;
  phoneCountdown.value = 0;
};

// 实际提交：修改密码逻辑
const submitPasswordChange = async () => {
  if (!modalForm.value.oldPwd || !modalForm.value.newPwd || !modalForm.value.confirmPwd) {
    return showToast('⚠️ 请完整填写所有密码项', 'error');
  }
  if (modalForm.value.newPwd !== modalForm.value.confirmPwd) {
    return showToast('⚠️ 两次输入的新密码不一致！', 'error');
  }
  if (modalForm.value.newPwd.length < 6) {
    return showToast('⚠️ 新密码不能少于 6 位', 'error');
  }

  try {
    const res = await axios.post('http://127.0.0.1:5000/api/user/password', {
      old_password: modalForm.value.oldPwd,
      new_password: modalForm.value.newPwd
    }, {
      headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
    });

    if (res.data.code === 0) {
      showToast('🎉 密码修改成功！请重新登录', 'success');
      closeModal(); // 提交成功后调用统一方法关闭并清空
      setTimeout(() => { handleLogout(); }, 1500);
    } else {
      showToast('❌ ' + res.data.msg, 'error');
    }
  } catch (error) {
    showToast('❌ 修改失败：' + (error.response?.data?.msg || '网络错误'), 'error');
  }
};

// 1. 发送验证码逻辑
const sendCode = async () => {
  if (!regForm.value.email.includes('@')) return alert('⚠️ 请输入有效的邮箱格式！');
  
  // 开启 60 秒倒计时
  countdown.value = 60;
  timer = setInterval(() => {
    countdown.value--;
    if (countdown.value <= 0) clearInterval(timer);
  }, 1000);

  // 向 Flask 后端发起请求
  try {
    const res = await axios.post('http://127.0.0.1:5000/api/auth/send-code', { email: regForm.value.email });
    if (res.data.code === 0) {
      if(typeof showToast === 'function') showToast('📧 验证码已发送，请查收邮箱', 'success');
    } else {
      throw new Error(res.data.msg);
    }
  } catch (error) {
    // 如果发送失败，立刻重置倒计时
    clearInterval(timer);
    countdown.value = 0;
    alert('发送失败：' + (error.message || '请检查后端 SMTP 是否配置正确'));
  }
};

// 2. 提交注册逻辑
const handleRegister = async () => {
  // 前端实时拦截
  if (!regForm.value.agreeTerms) return alert('⚠️ 请先阅读并勾选用户协议和隐私政策！');
  if (!regForm.value.username || !regForm.value.email || !regForm.value.password || !regForm.value.code) {
    return alert('⚠️ 请填写完整的注册信息！');
  }
  
  // 向 Flask 后端提交注册数据
  try {
    const res = await axios.post('http://127.0.0.1:5000/api/auth/register', regForm.value);
    
    if (res.data.code === 0) {
      if(typeof showToast === 'function') showToast('🎉 注册成功！快去登录吧', 'success');
      // 注册成功后，自动清空表单并跳转到邮箱登录面板
      regForm.value = { username: '', email: '', password: '', code: '', agreeTerms: false };
      switchTo('email'); 
    } else {
      alert('❌ 注册失败：' + res.data.msg);
    }
  } catch (error) {
    alert('❌ 网络或服务错误：' + (error.response?.data?.msg || '请检查控制台'));
  }
};

// ================= 全局轻提示 Toast 逻辑 =================
const toast = ref({ show: false, message: '', type: 'success' });
let toastTimer = null;

const showToast = (message, type = 'success') => {
  if (toastTimer) clearTimeout(toastTimer);
  toast.value = { show: true, message, type };
  // 2.5 秒后自动消失
  toastTimer = setTimeout(() => {
    toast.value.show = false;
  }, 2500);
};

// ================= 2. 全局快捷键 Ctrl + K 唤醒搜索 =================
const searchInputRef = ref(null); // 确保绑定了搜索框

const handleGlobalKeydown = (e) => {
  // 监听 Ctrl+K 或 Mac的 Cmd+K
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault(); // 阻止浏览器默认的搜索栏跳转
    
    // 如果当前不在首页，先跳回首页
    if (currentPage.value !== 'home') {
      currentPage.value = 'home';
      // 等待 DOM 渲染完成后聚焦
      nextTick(() => { searchInputRef.value?.focus(); });
    } else {
      searchInputRef.value?.focus();
    }
  }
};

const userInfo = ref({ 
  username: '', avatar: '', email: '未绑定邮箱', gender: '保密', birthday: '未设置', bio: '这个人很懒，什么都没写~' 
});
const editForm = ref({});
// ================= 智能 Logo 获取与容错逻辑 =================

// 修改打开添加弹窗的逻辑，确保是清空状态
const openAddSiteModal = () => {
  isEditingSite.value = false;
  newSiteForm.value = { id: null, name: '', url: '', category_id: activeCategoryId.value !== 'all' ? activeCategoryId.value : categories.value[0]?.id };
  showAddSiteModal.value = true;
};

// ================= 修复：网站保存与更新逻辑 =================
const submitNewSite = () => {
  if (!newSiteForm.value.name.trim() || !newSiteForm.value.url.trim()) return alert("请填写完整！");
  
  let finalUrl = newSiteForm.value.url.trim();
  if (!finalUrl.startsWith('http')) finalUrl = 'https://' + finalUrl;

  if (isEditingSite.value) {
    // ✨ 编辑模式：找到原来的网站数据并覆盖
    const index = websites.value.findIndex(s => s.id === newSiteForm.value.id);
    if (index !== -1) {
      websites.value[index] = { ...newSiteForm.value, url: finalUrl };
    }
    if(typeof showToast === 'function') showToast('网站修改已成功保存！', 'success');
  } else {
    // ✨ 新增模式：创建一个全新的网站
    const newSite = {
      id: Date.now(),
      name: newSiteForm.value.name,
      url: finalUrl,
      category_id: newSiteForm.value.category_id,
      clicks: 0
    };
    websites.value.unshift(newSite);
    activeCategoryId.value = newSite.category_id; // 自动跳转到对应分类
    if(typeof showToast === 'function') showToast('新网站已添加！', 'success');
  }
  showAddSiteModal.value = false; // ✨ 核心：保存完立刻关闭大弹窗
};

const submitNewCategory = () => {
  if (!newCategoryName.value.trim()) return alert("请填写名称！");
  const newCat = { id: Date.now(), name: newCategoryName.value };
  
  professionData[currentProfession.value].categories.push(newCat);
  
  // ✨ 核心修复：强制将新数组赋值给 categories.value，瞬间触发页面渲染
  categories.value = [...professionData[currentProfession.value].categories];
  
  showAddCategoryModal.value = false;
  newCategoryName.value = '';
};

const closeCategoryModal = () => {
  showCategoryModal.value = false;
};

// 2. 修复：保存分类 (修改/新建弹窗)
const saveCategory = () => {
  if (!editingCategory.value.name.trim()) return alert('分类名称不能为空！');
  
  const targetArr = professionData[currentProfession.value].categories;
  if (editingCategory.value.id) {
    // 编辑现有分类
    const idx = targetArr.findIndex(c => c.id === editingCategory.value.id);
    if (idx !== -1) targetArr[idx] = { ...editingCategory.value };
  } else {
    // 新增分类
    targetArr.push({ 
      id: Date.now(), 
      name: editingCategory.value.name, 
    });
  }
  
  // ✨ 核心修复：重新解构赋值，通知 Vue 界面需要重绘
  categories.value = [...targetArr]; 
  
  closeCategoryModal();
};

// 3. 删除分类
const deleteCategory = () => {
  if(confirm('确定要删除这个分类吗？')) {
    const targetArr = professionData[currentProfession.value].categories;
    
    // 过滤掉要删除的分类，生成新数组
    const newArr = targetArr.filter(c => c.id !== editingCategory.value.id);
    
    // 更新数据源
    professionData[currentProfession.value].categories = newArr;
    
    // ✨ 核心修复：把更新后的数组直接塞给 categories，分类标签会立刻消失！
    categories.value = newArr; 
    
    closeCategoryModal();
    activeCategoryId.value = 'all'; // 删除后切回全部分类
  }
};

// ================= 原生拖拽排序逻辑 =================
const draggedCategory = ref(null);

const onCategoryDragStart = (event, cat) => {
  draggedCategory.value = cat;
  event.dataTransfer.effectAllowed = 'move';
  // 拖起时加个半透明特效
  setTimeout(() => { event.target.classList.add('dragging-tab'); }, 0);
};

const onCategoryDrop = (event, targetCat) => {
  event.target.classList.remove('dragging-tab');
  // 如果没拖动或者原地放下，直接返回
  if (!draggedCategory.value || draggedCategory.value.id === targetCat.id) return;

  const targetArr = professionData[currentProfession.value].categories;
  const fromIndex = targetArr.findIndex(c => c.id === draggedCategory.value.id);
  const toIndex = targetArr.findIndex(c => c.id === targetCat.id);

  if (fromIndex !== -1 && toIndex !== -1) {
    // ✨ 核心：纯数组操作，抽出被拖拽项，插入到新位置
    const [movedItem] = targetArr.splice(fromIndex, 1);
    targetArr.splice(toIndex, 0, movedItem);
  }
  draggedCategory.value = null; // 重置
};
// ================= 智能 Logo 获取与容错逻辑 (多级瀑布流版) =================

// 1. 提取纯净域名
const getHostname = (url) => {
  if (!url) return 'default';
  try {
    let target = url.trim();
    if (!target.startsWith('http')) target = 'https://' + target;
    // 保留 www，有时对国内 Favicon 接口更友好
    return new URL(target).hostname; 
  } catch (e) {
    return 'default';
  }
};

// 2. 主力接口：换用 Google 的高分辨率 Favicon 接口 (放弃收录差的 Clearbit)
const getLogoUrl = (url) => {
  const domain = getHostname(url);
  if (domain === 'default') return '';
  return `https://www.google.com/s2/favicons?domain=${domain}&sz=128`;
};

// 3. 🛡️ 终极护航：多级错误降级 (Fallback) 处理
const handleIconError = (e, site) => {
  // 读取当前卡片已经尝试“抢救”的次数
  const currentStep = parseInt(e.target.dataset.errorStep || '0');
  const domain = getHostname(site.url);

  if (currentStep === 0) {
    // 【抢救 1】：原图防盗链或 Google 接口失败。尝试用 DuckDuckGo 接口兜底
    e.target.dataset.errorStep = '1';
    e.target.src = `https://icons.duckduckgo.com/ip3/${domain}.ico`;
    
  } else if (currentStep === 1) {
    // 【抢救 2】：如果还失败，尝试国内高稳定性 Favicon 聚合接口
    e.target.dataset.errorStep = '2';
    e.target.src = `https://api.iowen.cn/favicon/${domain}.png`;
    
  } else {
    // 【抢救 3】：彻底没救了（例如纯内网地址），启用终极优雅的文字头像
    e.target.dataset.errorStep = '3';
    e.target.src = `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(site.name)}&backgroundColor=f1f5f9&textColor=0f172a&fontWeight=700`;
  }
};

// ================= 📊 排行榜逻辑 (终极修复版) =================
const rawLeaderboard = ref([]);

const fetchRankingData = async () => {
  try {
    // ✨ 修复 1：这里必须是请求 5000 端口的 ranking 接口！
    const response = await axios.get('http://127.0.0.1:5000/api/ranking/growth');
    
    // ✨ 修复 2：使用正确的 axios 解析格式
    if (response.data && response.data.code === 0) {
      rawLeaderboard.value = response.data.data;
    } else {
      rawLeaderboard.value = [];
    }
  } catch (error) { 
    console.error('获取排行榜失败:', error); 
    rawLeaderboard.value = [];
  }
};

// 兼容原有的旧变量
const sortedLeaderboard = computed(() => rawLeaderboard.value);

// ================= 🖱️ 核心：网站点击处理 (极简无冲突版) =================
const handleSiteClick = async (site) => {
  // 1. 立即在新窗口打开网址，保持丝滑
  window.open(site.url, '_blank');
  
  // 2. 静默发送请求给后端，写入 click_log 数据库
  try {
    await axios.post('http://127.0.0.1:5000/api/click', { id: site.id });
    
    // 3. 记录完成后，立刻拉取最新排行榜数据
    fetchRankingData(); 
  } catch (error) {
    console.error('统计点击失败:', error);
  }
};

// ================= 生命周期与轮询 (同步全网数据) =================
let pollingTimer = null; // 轮询定时器

// ================= 登录与鉴权 =================
const phoneNumber = ref('');
const verifyCode = ref('');

const switchTo = (stage) => { authStage.value = stage; };
const handleGithubLogin = () => { window.location.href = 'http://127.0.0.1:5000/api/login/github'; };

const handleMobileLogin = async () => {
  if (!phoneNumber.value || !verifyCode.value) return alert("请输入手机号和验证码");
  isLoggedIn.value = true;
  userInfo.value.username = `用户_${phoneNumber.value.slice(-4)}`;
  
  localStorage.setItem('is_logged_in', 'true');
  localStorage.setItem('user_info', JSON.stringify(userInfo.value));
  showAuthModal.value = false;
  authStage.value = 'methods'; 

  // ✨ 登录成功的一瞬间，立刻拉取云端配置覆盖本地！
  await loadSettingsFromCloud(userInfo.value.username);
  
  if (typeof showToast === 'function') showToast('登录成功！', 'success');
  else alert("登录成功！");
};

const handleLogout = () => {
  isLoggedIn.value = false;
  userInfo.value = { username: '', avatar: '' };
  currentPage.value = 'home';
  localStorage.removeItem('user_info');
  localStorage.removeItem('is_logged_in');
  showSurveyModal.value = false;
  hasSurvey.value = true;
  alert("已安全退出账号");
};

// ================= 🎯 问卷处理逻辑 =================

/** 检查是否需要弹出问卷 */
function checkAndShowSurvey() {
  // 已登录 + 未做过问卷 + 弹窗未在显示
  if (isLoggedIn.value && !hasSurvey.value && !showSurveyModal.value) {
    // 延迟 0.5s 弹出，避免与登录弹窗关闭动画冲突
    setTimeout(() => {
      showSurveyModal.value = true;
    }, 500);
  }
}

/** 处理问卷提交 */
async function handleSurveySubmit(interests) {
  try {
    const res = await userAPI.submitSurvey(interests);
    if (res.data?.code === 0) {
      showSurveyModal.value = false;
      hasSurvey.value = true;
      // 更新本地 userInfo
      if (userInfo.value) {
        userInfo.value.has_survey = 1;
        userInfo.value.user_tags = interests.join(',');
        localStorage.setItem('user_info', JSON.stringify(userInfo.value));
      }
      showToast('🎉 问卷已保存！正在加载专属推荐...', 'success');
      // 重新拉取推荐
      await loadRecommendations();
    } else {
      // 后端返回了业务错误码（如 400 标签无效）
      showToast('❌ ' + (res.data?.msg || '保存失败'), 'error');
      if (surveyModalRef.value) surveyModalRef.value.done();
    }
  } catch (error) {
    // 网络错误 / 401 未登录 / 500 服务器异常
    const detail = error.response?.data?.msg || error.message || '网络错误';
    showToast('❌ 提交失败：' + detail, 'error');
    if (surveyModalRef.value) surveyModalRef.value.done();
  }
}

/** 处理跳过问卷 */
function handleSurveySkip() {
  showSurveyModal.value = false;
  // 跳过也能加载默认推荐
  loadRecommendations();
}

/** 加载个性化推荐 */
async function loadRecommendations() {
  try {
    const res = await feedAPI.getRecommendations();
    if (res.data?.code === 0) {
      recommendedItems.value = res.data.data.items || [];
    }
  } catch (error) {
    console.warn('加载推荐失败:', error);
  }
}

// ✨ 核心逻辑：将网站一键送入/移出专注轨道
const toggleSiteToFocus = (site) => {
  // 检查是否已经在轨道里（通过 URL 判断唯一性）
  const index = favoriteSites.value.findIndex(s => s.url === site.url);
  
  if (index > -1) {
    // 如果已存在，则移除
    favoriteSites.value.splice(index, 1);
    showToast('收回成功：已从专注轨道移除', 'success');
  } else {
    // 如果不存在，检查是否超过 8 个限制
    if (favoriteSites.value.length >= 8) {
      showToast('⚠️ 轨道已满（最多8个），请先删除部分', 'warning');
      return;
    }
    // 添加到轨道（转换数据格式以适配星球渲染）
    favoriteSites.value.push({
      id: site.id,
      name: site.name,
      url: site.url,
      icon: site.logo_url || getLogoUrl(site.url) // 优先使用原有 logo
    });
    showToast('✨ 成功：已发射到专注轨道', 'success');
  }
  
  // 别忘了持久化保存到本地
  localStorage.setItem('focus_sites', JSON.stringify(favoriteSites.value));
};

// ================= 个人信息管理 =================
const goToProfile = () => { currentPage.value = 'profile'; };
const goHome = () => { currentPage.value = 'home'; };

// ================= 🚀 个人中心 (真实数据接入版) =================
const activeProfileTab = ref('homepage');
const contentTab = ref('published'); 

// 1. 响应式空容器，等待后端数据注入
const profileStats = ref({ views: 0, followers: 0, posts: 0 });
const privacySettings = ref({ publicFavorites: true, hideFootprint: false });
const loginDevices = ref([]);
const myContents = ref([]);
const interactionHistory = ref([]);

// ================= 🚀 处理展示在首页动态流的真实数据 =================
// 因为后端返回的 history 是按日期分组的：[{ date: '今天', items: [...] }]
// 我们在首页百宝箱里只需要平铺的最近 3 条记录，所以用 computed 打平它：
const flatHistory = computed(() => {
  if (!interactionHistory.value || interactionHistory.value.length === 0) return [];
  
  let list = [];
  interactionHistory.value.forEach(group => {
    group.items.forEach(item => {
      // 把外层的日期塞进每一条数据里，方便展示
      list.push({ ...item, date: group.date });
    });
  });
  return list;
});

// 2. 核心：从 Flask 后端拉取所有个人中心真实数据
const loadProfileData = async () => {
  if (!isLoggedIn.value || !userInfo.value.username) return;
  const token = localStorage.getItem('access_token');
  const headers = { Authorization: `Bearer ${token}` };

  try {
    // 💡 请求：主页数据概览 (获赞/粉丝/文章数)
    const statsRes = await axios.get(`http://127.0.0.1:5000/api/user/stats?username=${userInfo.value.username}`, { headers });
    if (statsRes.data.code === 0) profileStats.value = statsRes.data.data;

    // 💡 请求：安全设置-登录设备列表
    const devRes = await axios.get('http://127.0.0.1:5000/api/user/devices', { headers });
    if (devRes.data.code === 0) loginDevices.value = devRes.data.data;

    // 💡 请求：互动足迹记录
    const histRes = await axios.get('http://127.0.0.1:5000/api/user/history', { headers });
    if (histRes.data.code === 0) interactionHistory.value = histRes.data.data;
    
  } catch (error) {
    console.warn('获取个人中心部分真实数据失败，请确保后端接口已部署', error);
  }
};

// 3. 动态加载内容管理列表 (跟随 Tabs 切换)
const fetchUserContents = async () => {
  const token = localStorage.getItem('access_token');
  try {
    // 💡 接口附带参数 status (published/reviewing/draft)
    const res = await axios.get(`http://127.0.0.1:5000/api/user/contents?status=${contentTab.value}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (res.data.code === 0) myContents.value = res.data.data;
    else myContents.value = [];
  } catch (e) {
    myContents.value = [];
  }
};

// 监听动作 1：用户切换了内容状态 Tab 时，立刻向后端请求该状态的数据
watch(contentTab, () => {
  fetchUserContents();
});

// 监听动作 2：用户打开个人中心页面时，触发全局数据拉取
watch(currentPage, (newPage) => {
  if (newPage === 'profile') {
    loadProfileData();
    fetchUserContents(); // 默认拉取“已发布”列表
  }
});

// ================= 删除与清理接口 =================
const deleteMyContent = async (id) => {
  if (!confirm('确定要永久删除这条内容吗？')) return;
  try {
    await axios.post('http://127.0.0.1:5000/api/user/contents/delete', { id }, {
      headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
    });
    showToast('删除成功', 'success');
    fetchUserContents(); // 刷新真实列表
  } catch (e) {
    showToast('删除失败', 'error');
  }
};

const clearHistory = async () => {
  if (!confirm('确定要清空所有互动足迹吗？此操作不可恢复！')) return;
  try {
    await axios.post('http://127.0.0.1:5000/api/user/history/clear', {}, {
      headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
    });
    interactionHistory.value = []; // 清空前端数组
    showToast('足迹已清空', 'success');
  } catch (e) {
    showToast('清空失败', 'error');
  }
};

const editingField = ref(''); 
const editingTitle = ref('');
const openEditModal = (field, title) => {
  editingField.value = field; // 记录当前修改的字段 (如 'username')
  editingTitle.value = title; // 动态设置弹窗标题 (如 '修改名称')
  
  // 只把当前需要修改的那个字段拷贝到 editForm 中
  editForm.value = { [field]: userInfo.value[field] }; 
  showEditModal.value = true;
};
const saveProfile = () => {
  const field = editingField.value; // 获取当前正在修改的字段名
  
  // 简单校验：如果修改的是用户名，不能为空
  if (field === 'username' && !editForm.value[field]?.trim()) {
    return alert("名称不能为空！");
  }

  // 仅保存当前修改的单项数据，合并回 userInfo
  userInfo.value = { ...userInfo.value, [field]: editForm.value[field] };
  
  // 更新到本地缓存
  localStorage.setItem('user_info', JSON.stringify(userInfo.value));
  showEditModal.value = false;
};

// ================= 直接修改与保存逻辑 =================
const saveProfileDirectly = () => {
  if (!userInfo.value.username?.trim()) {
    return alert("名称不能为空！");
  }
  // 将最新的数据直接写入本地缓存
  localStorage.setItem('user_info', JSON.stringify(userInfo.value));
  
  // 提示成功
  if (typeof showToast === 'function') {
    showToast('个人资料已成功保存', 'success');
  } else {
    alert('个人资料已成功保存');
  }
};

// ================= 头像本地上传逻辑 =================
const avatarInputRef = ref(null); // 绑定隐藏的文件输入框

// 1. 点击头像或按钮，触发隐藏的 input
const triggerAvatarUpload = () => {
  avatarInputRef.value?.click();
};

// 2. 处理文件选择
const handleAvatarUpload = (event) => {
  const file = event.target.files[0];
  if (!file) return;

  // 校验格式
  if (!file.type.startsWith('image/')) {
  return alert('只能上传图片文件哦！');
}
  
  // 校验大小 (防止 Base64 过大撑爆 localStorage，限制在 2MB)
  if (file.size > 2 * 1024 * 1024) {
    return alert('图片太大啦，请上传不超过 2MB 的图片！');
  }

  // 使用 FileReader 将图片转换为 Base64
  const reader = new FileReader();
  reader.onload = (e) => {
    // 转换成功后，直接赋值给 userInfo.avatar 进行预览
    userInfo.value.avatar = e.target.result;
    
    // 如果有轻提示，可以顺便提示一下
    if (typeof showToast === 'function') showToast('头像已加载，请点击底部保存生效', 'success');
  };
  reader.readAsDataURL(file);
  
  // 清空 input 的 value，确保用户下次选同一张图也能触发 change 事件
  event.target.value = '';
};

// ✨ 1. 把当前配置打包，静默发送到服务器
const syncSettingsToCloud = async () => {
  // 如果没登录，就不向服务器发请求
  if (!isLoggedIn.value || !userInfo.value.username) return;
  
  try {
    await axios.post('http://127.0.0.1:5000/api/user/sync', {
      username: userInfo.value.username,
      dark_mode: isDarkMode.value,
      custom_wallpaper: customWallpaper.value,
      selected_engines: selectedEngines.value,
      current_engine: currentEngine.value,
      avatar_url: userInfo.value.avatar
    });
    console.log('配置已无缝同步至云端 ☁️');
  } catch (error) {
    console.error('云端同步失败', error);
  }
};

// ✨ 2. 登录成功后，从云端拉取覆盖本地配置
const loadSettingsFromCloud = async (username) => {
  try {
    const res = await axios.get(`http://127.0.0.1:5000/api/user/settings?username=${username}`);
    const data = res.data;
    
    // 把云端的数据覆盖到当前的响应式变量上
    if (data.dark_mode !== undefined) isDarkMode.value = data.dark_mode;
    if (data.custom_wallpaper !== null) customWallpaper.value = data.custom_wallpaper || '';
    if (data.selected_engines) selectedEngines.value = data.selected_engines;
    if (data.current_engine) currentEngine.value = data.current_engine;
    if (data.avatar_url) userInfo.value.avatar = data.avatar_url;

    if (typeof showToast === 'function') showToast('云端专属配置已加载 ✨', 'success');
  } catch (e) {
    console.log('新用户或未找到云端配置，使用默认外观');
  }
};

// ================= 主页展示逻辑 =================
const activeCategoryId = ref('all') 
const toggleTheme = () => { isDarkMode.value = !isDarkMode.value }

// ================= 1. 定义默认职业数据 =================
const defaultProfessionData = {
  general: {
    name: '综合导航', icon: '🌐',
    categories: [
      { id: 1, name: '常用推荐' }, { id: 2, name: '开发社区' },
      { id: 3, name: '摸鱼娱乐' }, { id: 4, name: '实用工具' }, { id: 5, name: 'AI 神器' }
    ]
  },
  frontend: {
    name: '前端开发', icon: '🎨',
    categories: [
      { id: 201, name: '框架文档' }, { id: 202, name: 'UI 组件库' },
      { id: 203, name: '可视化/3D' }, { id: 204, name: '工具/构建' }
    ]
  },
  designer: {
    name: 'UI 设计师', icon: '🖌️',
    categories: [
      { id: 301, name: '灵感采集' }, { id: 302, name: '素材资源' },
      { id: 303, name: '在线工具' }, { id: 304, name: '字体/配色' }
    ]
  },
  product: {
    name: '产品经理', icon: '📋',
    categories: [
      { id: 401, name: '原型设计' }, { id: 402, name: '文档办公' },
      { id: 403, name: '数据分析' }, { id: 404, name: '竞品调研' }
    ]
  }
};

// ================= 2. 读取缓存并初始化响应式对象 =================
const loadProfessionData = () => {
  const savedData = localStorage.getItem('pro_nav_professions');
  if (savedData) {
    try {
      return JSON.parse(savedData);
    } catch (e) {
      console.error("读取本地职业数据失败", e);
      return defaultProfessionData;
    }
  }
  return defaultProfessionData;
};

const professionData = reactive(loadProfessionData());

// ================= 3. 开启深度监听保存 =================
watch(professionData, (newVal) => {
  localStorage.setItem('pro_nav_professions', JSON.stringify(newVal));
}, { deep: true });

// 添加用户自定义职业
const addNewProfession = (name, icon, initialSites = []) => {
  const newKey = 'custom_' + Date.now();
  professionData.value[newKey] = {
    name: name,
    icon: icon || '✨',
    sites: initialSites
  };
};

// 2. 当前选中的职业（默认全能）
const currentProfession = ref('general');

// 3. 动态计算当前职业对应的分类列表
const categories = ref([]);
// 使用 watch 监听职业切换，动态更新分类
watch(currentProfession, (newVal) => {
  categories.value = professionData[newVal].categories;
  activeCategoryId.value = 'all';
}, { immediate: true }); // immediate 确保初始化时就有数据

// 4. 切换职业的函数
const selectProfession = (key) => {
  currentProfession.value = key;
  // 切换职业后，默认选中该职业下的“全部分类”或第一个分类
  activeCategoryId.value = 'all'; 
};

// ================= 📰 行业前沿资讯流 =================
const newsList = ref([]);
const isLoadingNews = ref(false);

const fetchIndustryNews = async () => {
  isLoadingNews.value = true;
  try {
    // 动态传入当前的行业分类参数，让后端返回精准数据
    const res = await axios.get(`http://127.0.0.1:5000/api/news?prof=${currentProfession.value}`);
    newsList.value = res.data;
  } catch (error) {
    console.error('获取行业资讯失败:', error);
  } finally {
    isLoadingNews.value = false;
  }
};

// 监听行业分类变化，一旦用户切换身份，立刻刷新资讯流！
watch(currentProfession, () => {
  fetchIndustryNews();
});

const maxVisibleCategories = 4;
const visibleCategories = computed(() => categories.value.slice(0, maxVisibleCategories));
const hiddenCategories = computed(() => categories.value.slice(maxVisibleCategories));

const websites = ref([
  // ===== 分类 1：常用推荐 =====
  { id: 101, category_id: 1, name: '哔哩哔哩', url: 'https://www.bilibili.com', logo_url: '', clicks: 1250 },
  { id: 102, category_id: 1, name: '知乎', url: 'https://www.zhihu.com', logo_url: '', clicks: 856 },
  { id: 103, category_id: 1, name: '微博', url: 'https://weibo.com', logo_url: '', clicks: 720 },
  { id: 104, category_id: 1, name: '淘宝', url: 'https://www.taobao.com', logo_url: '', clicks: 1100 },
  { id: 105, category_id: 1, name: '京东', url: 'https://www.jd.com', logo_url: '', clicks: 980 },
  { id: 106, category_id: 1, name: '百度', url: 'https://www.baidu.com', logo_url: '', clicks: 2000 },
  { id: 107, category_id: 1, name: '腾讯视频', url: 'https://v.qq.com', logo_url: '', clicks: 650 },
  { id: 108, category_id: 1, name: '爱奇艺', url: 'https://www.iqiyi.com', logo_url: '', clicks: 600 },
  { id: 109, category_id: 1, name: '优酷', url: 'https://www.youku.com', logo_url: '', clicks: 480 },
  { id: 110, category_id: 1, name: '网易云音乐', url: 'https://music.163.com', logo_url: '', clicks: 870 },
  { id: 111, category_id: 1, name: 'QQ音乐', url: 'https://y.qq.com', logo_url: '', clicks: 760 },
  { id: 112, category_id: 1, name: '天猫', url: 'https://www.tmall.com', logo_url: '', clicks: 890 },
  { id: 113, category_id: 1, name: '拼多多', url: 'https://www.pinduoduo.com', logo_url: '', clicks: 950 },
  { id: 114, category_id: 1, name: '12306', url: 'https://www.12306.cn', logo_url: '', clicks: 430 },
  { id: 115, category_id: 1, name: '高德地图', url: 'https://www.amap.com', logo_url: '', clicks: 560 },
  // ===== 分类 2：开发社区 =====
  { id: 201, category_id: 2, name: 'GitHub', url: 'https://github.com', logo_url: '', clicks: 980 },
  { id: 202, category_id: 2, name: 'GitLab', url: 'https://gitlab.com', logo_url: '', clicks: 420 },
  { id: 203, category_id: 2, name: 'Gitee', url: 'https://gitee.com', logo_url: '', clicks: 380 },
  { id: 204, category_id: 2, name: '掘金', url: 'https://juejin.cn', logo_url: '', clicks: 430 },
  { id: 205, category_id: 2, name: 'CSDN', url: 'https://www.csdn.net', logo_url: '', clicks: 560 },
  { id: 206, category_id: 2, name: '博客园', url: 'https://www.cnblogs.com', logo_url: '', clicks: 310 },
  { id: 207, category_id: 2, name: 'Stack Overflow', url: 'https://stackoverflow.com', logo_url: '', clicks: 670 },
  { id: 208, category_id: 2, name: 'MDN Web Docs', url: 'https://developer.mozilla.org', logo_url: '', clicks: 590 },
  { id: 209, category_id: 2, name: 'npm', url: 'https://www.npmjs.com', logo_url: '', clicks: 480 },
  { id: 210, category_id: 2, name: 'Docker Hub', url: 'https://hub.docker.com', logo_url: '', clicks: 350 },
  { id: 211, category_id: 2, name: 'LeetCode', url: 'https://leetcode.cn', logo_url: '', clicks: 720 },
  { id: 212, category_id: 2, name: '牛客网', url: 'https://www.nowcoder.com', logo_url: '', clicks: 540 },
  { id: 213, category_id: 2, name: 'V2EX', url: 'https://www.v2ex.com', logo_url: '', clicks: 390 },
  { id: 214, category_id: 2, name: 'SegmentFault', url: 'https://segmentfault.com', logo_url: '', clicks: 280 },
  { id: 215, category_id: 2, name: 'Vercel', url: 'https://vercel.com', logo_url: '', clicks: 460 },
  // ===== 分类 3：摸鱼娱乐 =====
  { id: 301, category_id: 3, name: '抖音', url: 'https://www.douyin.com', logo_url: '', clicks: 520 },
  { id: 302, category_id: 3, name: '小红书', url: 'https://www.xiaohongshu.com', logo_url: '', clicks: 480 },
  { id: 303, category_id: 3, name: '微信读书', url: 'https://weread.qq.com', logo_url: '', clicks: 320 },
  { id: 304, category_id: 3, name: '豆瓣', url: 'https://www.douban.com', logo_url: '', clicks: 410 },
  { id: 305, category_id: 3, name: '虎扑', url: 'https://www.hupu.com', logo_url: '', clicks: 290 },
  { id: 306, category_id: 3, name: 'NGA玩家社区', url: 'https://nga.178.com', logo_url: '', clicks: 260 },
  { id: 307, category_id: 3, name: 'Steam', url: 'https://store.steampowered.com', logo_url: '', clicks: 680 },
  { id: 308, category_id: 3, name: 'Epic Games', url: 'https://www.epicgames.com', logo_url: '', clicks: 350 },
  { id: 309, category_id: 3, name: '网易游戏', url: 'https://game.163.com', logo_url: '', clicks: 420 },
  { id: 310, category_id: 3, name: '腾讯游戏', url: 'https://game.qq.com', logo_url: '', clicks: 510 },
  { id: 311, category_id: 3, name: '漫画柜', url: 'https://www.manhuagui.com', logo_url: '', clicks: 230 },
  { id: 312, category_id: 3, name: '哔哩哔哩漫画', url: 'https://manga.bilibili.com', logo_url: '', clicks: 280 },
  { id: 313, category_id: 3, name: '网易新闻', url: 'https://news.163.com', logo_url: '', clicks: 370 },
  { id: 314, category_id: 3, name: '今日头条', url: 'https://www.toutiao.com', logo_url: '', clicks: 440 },
  { id: 315, category_id: 3, name: '虎嗅', url: 'https://www.huxiu.com', logo_url: '', clicks: 310 },
  // ===== 分类 4：实用工具 =====
  { id: 401, category_id: 4, name: 'ProcessOn', url: 'https://www.processon.com', logo_url: '', clicks: 380 },
  { id: 402, category_id: 4, name: 'Excalidraw', url: 'https://excalidraw.com', logo_url: '', clicks: 290 },
  { id: 403, category_id: 4, name: 'TinyPNG', url: 'https://tinypng.com', logo_url: '', clicks: 450 },
  { id: 404, category_id: 4, name: 'Squoosh', url: 'https://squoosh.app', logo_url: '', clicks: 220 },
  { id: 405, category_id: 4, name: 'Carbon', url: 'https://carbon.now.sh', logo_url: '', clicks: 310 },
  { id: 406, category_id: 4, name: 'Regex101', url: 'https://regex101.com', logo_url: '', clicks: 340 },
  { id: 407, category_id: 4, name: 'Can I Use', url: 'https://caniuse.com', logo_url: '', clicks: 390 },
  { id: 408, category_id: 4, name: 'Notion', url: 'https://www.notion.so', logo_url: '', clicks: 620 },
  { id: 409, category_id: 4, name: '飞书', url: 'https://www.feishu.cn', logo_url: '', clicks: 540 },
  { id: 410, category_id: 4, name: '腾讯文档', url: 'https://docs.qq.com', logo_url: '', clicks: 480 },
  { id: 411, category_id: 4, name: '石墨文档', url: 'https://shimo.im', logo_url: '', clicks: 320 },
  { id: 412, category_id: 4, name: '百度翻译', url: 'https://fanyi.baidu.com', logo_url: '', clicks: 560 },
  { id: 413, category_id: 4, name: 'DeepL翻译', url: 'https://www.deepl.com', logo_url: '', clicks: 490 },
  { id: 414, category_id: 4, name: 'Cloudflare', url: 'https://www.cloudflare.com', logo_url: '', clicks: 270 },
  { id: 415, category_id: 4, name: 'iLovePDF', url: 'https://www.ilovepdf.com', logo_url: '', clicks: 350 },
  { id: 416, category_id: 4, name: 'Unsplash', url: 'https://unsplash.com', logo_url: '', clicks: 410 },
  // ===== 分类 5：AI 神器 =====
  { id: 501, category_id: 5, name: 'ChatGPT', url: 'https://chat.openai.com', logo_url: '', clicks: 760 },
  { id: 502, category_id: 5, name: 'Claude', url: 'https://claude.ai', logo_url: '', clicks: 580 },
  { id: 503, category_id: 5, name: 'Gemini', url: 'https://gemini.google.com', logo_url: '', clicks: 490 },
  { id: 504, category_id: 5, name: '文心一言', url: 'https://yiyan.baidu.com', logo_url: '', clicks: 420 },
  { id: 505, category_id: 5, name: '通义千问', url: 'https://tongyi.aliyun.com', logo_url: '', clicks: 380 },
  { id: 506, category_id: 5, name: '讯飞星火', url: 'https://xinghuo.xfyun.cn', logo_url: '', clicks: 310 },
  { id: 507, category_id: 5, name: 'Kimi', url: 'https://kimi.moonshot.cn', logo_url: '', clicks: 450 },
  { id: 508, category_id: 5, name: '豆包', url: 'https://www.doubao.com', logo_url: '', clicks: 390 },
  { id: 509, category_id: 5, name: 'Midjourney', url: 'https://www.midjourney.com', logo_url: '', clicks: 520 },
  { id: 510, category_id: 5, name: 'Stable Diffusion', url: 'https://stability.ai', logo_url: '', clicks: 340 },
  { id: 511, category_id: 5, name: 'Runway', url: 'https://runwayml.com', logo_url: '', clicks: 280 },
  { id: 512, category_id: 5, name: 'Suno AI', url: 'https://suno.ai', logo_url: '', clicks: 360 },
  { id: 513, category_id: 5, name: 'GitHub Copilot', url: 'https://github.com/features/copilot', logo_url: '', clicks: 470 },
  { id: 514, category_id: 5, name: 'Cursor', url: 'https://www.cursor.com', logo_url: '', clicks: 530 },
  { id: 515, category_id: 5, name: 'Perplexity', url: 'https://www.perplexity.ai', logo_url: '', clicks: 410 },
  { id: 516, category_id: 5, name: 'Hugging Face', url: 'https://huggingface.co', logo_url: '', clicks: 350 },
  { id: 517, category_id: 5, name: 'DeepSeek', url: 'https://www.deepseek.com', logo_url: '', clicks: 620 },
  { id: 518, category_id: 5, name: '智谱清言', url: 'https://chatglm.cn', logo_url: '', clicks: 290 },
  // ===== 前端开发 - 201：框架文档 =====
  { id: 2001, category_id: 201, name: 'Vue.js', url: 'https://cn.vuejs.org', logo_url: '' },
  { id: 2002, category_id: 201, name: 'React', url: 'https://react.dev', logo_url: '' },
  { id: 2003, category_id: 201, name: 'Angular', url: 'https://angular.dev', logo_url: '' },
  { id: 2004, category_id: 201, name: 'Svelte', url: 'https://svelte.dev', logo_url: '' },
  { id: 2005, category_id: 201, name: 'Nuxt.js', url: 'https://nuxt.com', logo_url: '' },
  { id: 2006, category_id: 201, name: 'Next.js', url: 'https://nextjs.org', logo_url: '' },
  { id: 2007, category_id: 201, name: 'Vite', url: 'https://vitejs.dev', logo_url: '' },
  { id: 2008, category_id: 201, name: 'Node.js', url: 'https://nodejs.org', logo_url: '' },
  { id: 2009, category_id: 201, name: 'TypeScript', url: 'https://www.typescriptlang.org', logo_url: '' },
  { id: 2010, category_id: 201, name: 'Astro', url: 'https://astro.build', logo_url: '' },
  { id: 2011, category_id: 201, name: 'Remix', url: 'https://remix.run', logo_url: '' },
  { id: 2012, category_id: 201, name: 'NestJS', url: 'https://nestjs.com', logo_url: '' },
  // ===== 前端开发 - 202：UI 组件库 =====
  { id: 2021, category_id: 202, name: 'Element Plus', url: 'https://element-plus.org', logo_url: '' },
  { id: 2022, category_id: 202, name: 'Ant Design', url: 'https://ant.design', logo_url: '' },
  { id: 2023, category_id: 202, name: 'Naive UI', url: 'https://www.naiveui.com', logo_url: '' },
  { id: 2024, category_id: 202, name: 'Tailwind CSS', url: 'https://tailwindcss.com', logo_url: '' },
  { id: 2025, category_id: 202, name: 'shadcn/ui', url: 'https://ui.shadcn.com', logo_url: '' },
  { id: 2026, category_id: 202, name: 'Material UI', url: 'https://mui.com', logo_url: '' },
  { id: 2027, category_id: 202, name: 'Chakra UI', url: 'https://chakra-ui.com', logo_url: '' },
  { id: 2028, category_id: 202, name: 'DaisyUI', url: 'https://daisyui.com', logo_url: '' },
  { id: 2029, category_id: 202, name: 'Vant', url: 'https://vant-ui.github.io/vant', logo_url: '' },
  { id: 2030, category_id: 202, name: 'Arco Design', url: 'https://arco.design', logo_url: '' },
  // ===== 前端开发 - 203：可视化/3D =====
  { id: 2031, category_id: 203, name: 'ECharts', url: 'https://echarts.apache.org', logo_url: '' },
  { id: 2032, category_id: 203, name: 'D3.js', url: 'https://d3js.org', logo_url: '' },
  { id: 2033, category_id: 203, name: 'Three.js', url: 'https://threejs.org', logo_url: '' },
  { id: 2034, category_id: 203, name: 'Chart.js', url: 'https://www.chartjs.org', logo_url: '' },
  { id: 2035, category_id: 203, name: 'AntV', url: 'https://antv.antgroup.com', logo_url: '' },
  { id: 2036, category_id: 203, name: 'Babylon.js', url: 'https://www.babylonjs.com', logo_url: '' },
  { id: 2037, category_id: 203, name: 'Spline', url: 'https://spline.design', logo_url: '' },
  { id: 2038, category_id: 203, name: 'React Flow', url: 'https://reactflow.dev', logo_url: '' },
  // ===== 前端开发 - 204：工具/构建 =====
  { id: 2041, category_id: 204, name: 'ESLint', url: 'https://eslint.org', logo_url: '' },
  { id: 2042, category_id: 204, name: 'Prettier', url: 'https://prettier.io', logo_url: '' },
  { id: 2043, category_id: 204, name: 'Vitest', url: 'https://vitest.dev', logo_url: '' },
  { id: 2044, category_id: 204, name: 'Jest', url: 'https://jestjs.io', logo_url: '' },
  { id: 2045, category_id: 204, name: 'Playwright', url: 'https://playwright.dev', logo_url: '' },
  { id: 2046, category_id: 204, name: 'Storybook', url: 'https://storybook.js.org', logo_url: '' },
  { id: 2047, category_id: 204, name: 'pnpm', url: 'https://pnpm.io', logo_url: '' },
  { id: 2048, category_id: 204, name: 'Bun', url: 'https://bun.sh', logo_url: '' },
  // ===== UI 设计师 - 301：灵感采集 =====
  { id: 3001, category_id: 301, name: 'Dribbble', url: 'https://dribbble.com', logo_url: '' },
  { id: 3002, category_id: 301, name: 'Behance', url: 'https://www.behance.net', logo_url: '' },
  { id: 3003, category_id: 301, name: '站酷', url: 'https://www.zcool.com.cn', logo_url: '' },
  { id: 3004, category_id: 301, name: '花瓣网', url: 'https://huaban.com', logo_url: '' },
  { id: 3005, category_id: 301, name: 'Awwwards', url: 'https://www.awwwards.com', logo_url: '' },
  { id: 3006, category_id: 301, name: 'Mobbin', url: 'https://mobbin.com', logo_url: '' },
  { id: 3007, category_id: 301, name: 'Pinterest', url: 'https://www.pinterest.com', logo_url: '' },
  { id: 3008, category_id: 301, name: 'Lapa Ninja', url: 'https://www.lapa.ninja', logo_url: '' },
  // ===== UI 设计师 - 302：素材资源 =====
  { id: 3021, category_id: 302, name: 'Unsplash', url: 'https://unsplash.com', logo_url: '' },
  { id: 3022, category_id: 302, name: 'Pexels', url: 'https://www.pexels.com', logo_url: '' },
  { id: 3023, category_id: 302, name: 'iconfont', url: 'https://www.iconfont.cn', logo_url: '' },
  { id: 3024, category_id: 302, name: 'Iconify', url: 'https://iconify.design', logo_url: '' },
  { id: 3025, category_id: 302, name: 'Lucide Icons', url: 'https://lucide.dev', logo_url: '' },
  { id: 3026, category_id: 302, name: 'unDraw', url: 'https://undraw.co', logo_url: '' },
  { id: 3027, category_id: 302, name: 'LottieFiles', url: 'https://lottiefiles.com', logo_url: '' },
  { id: 3028, category_id: 302, name: 'Freepik', url: 'https://www.freepik.com', logo_url: '' },
  // ===== UI 设计师 - 303：在线工具 =====
  { id: 3031, category_id: 303, name: 'Figma', url: 'https://www.figma.com', logo_url: '' },
  { id: 3032, category_id: 303, name: 'MasterGo', url: 'https://mastergo.com', logo_url: '' },
  { id: 3033, category_id: 303, name: '即时设计', url: 'https://js.design', logo_url: '' },
  { id: 3034, category_id: 303, name: 'Canva', url: 'https://www.canva.com', logo_url: '' },
  { id: 3035, category_id: 303, name: 'Remove.bg', url: 'https://www.remove.bg', logo_url: '' },
  { id: 3036, category_id: 303, name: 'Photopea', url: 'https://www.photopea.com', logo_url: '' },
  { id: 3037, category_id: 303, name: 'Pixso', url: 'https://pixso.cn', logo_url: '' },
  // ===== UI 设计师 - 304：字体/配色 =====
  { id: 3041, category_id: 304, name: 'Google Fonts', url: 'https://fonts.google.com', logo_url: '' },
  { id: 3042, category_id: 304, name: 'Coolors', url: 'https://coolors.co', logo_url: '' },
  { id: 3043, category_id: 304, name: 'Adobe Color', url: 'https://color.adobe.com', logo_url: '' },
  { id: 3044, category_id: 304, name: 'Colorhunt', url: 'https://colorhunt.co', logo_url: '' },
  { id: 3045, category_id: 304, name: 'Fontshare', url: 'https://www.fontshare.com', logo_url: '' },
  { id: 3046, category_id: 304, name: '字体天下', url: 'https://www.fonts.net.cn', logo_url: '' },
  // ===== 产品经理 - 401：原型设计 =====
  { id: 4001, category_id: 401, name: 'Axure RP', url: 'https://www.axure.com', logo_url: '' },
  { id: 4002, category_id: 401, name: '墨刀', url: 'https://modao.cc', logo_url: '' },
  { id: 4003, category_id: 401, name: 'Figma', url: 'https://www.figma.com', logo_url: '' },
  { id: 4004, category_id: 401, name: 'Framer', url: 'https://www.framer.com', logo_url: '' },
  { id: 4005, category_id: 401, name: 'Miro', url: 'https://miro.com', logo_url: '' },
  { id: 4006, category_id: 401, name: 'Whimsical', url: 'https://whimsical.com', logo_url: '' },
  // ===== 产品经理 - 402：文档办公 =====
  { id: 4021, category_id: 402, name: 'Notion', url: 'https://www.notion.so', logo_url: '' },
  { id: 4022, category_id: 402, name: '飞书', url: 'https://www.feishu.cn', logo_url: '' },
  { id: 4023, category_id: 402, name: '语雀', url: 'https://www.yuque.com', logo_url: '' },
  { id: 4024, category_id: 402, name: 'Jira', url: 'https://www.atlassian.com/software/jira', logo_url: '' },
  { id: 4025, category_id: 402, name: 'Linear', url: 'https://linear.app', logo_url: '' },
  { id: 4026, category_id: 402, name: 'Trello', url: 'https://trello.com', logo_url: '' },
  // ===== 产品经理 - 403：数据分析 =====
  { id: 4031, category_id: 403, name: '百度统计', url: 'https://tongji.baidu.com', logo_url: '' },
  { id: 4032, category_id: 403, name: 'Google Analytics', url: 'https://analytics.google.com', logo_url: '' },
  { id: 4033, category_id: 403, name: 'Mixpanel', url: 'https://mixpanel.com', logo_url: '' },
  { id: 4034, category_id: 403, name: 'Amplitude', url: 'https://amplitude.com', logo_url: '' },
  { id: 4035, category_id: 403, name: 'Tableau', url: 'https://www.tableau.com', logo_url: '' },
  { id: 4036, category_id: 403, name: 'Grafana', url: 'https://grafana.com', logo_url: '' },
  // ===== 产品经理 - 404：竞品调研 =====
  { id: 4041, category_id: 404, name: 'SimilarWeb', url: 'https://www.similarweb.com', logo_url: '' },
  { id: 4042, category_id: 404, name: '七麦数据', url: 'https://www.qimai.cn', logo_url: '' },
  { id: 4043, category_id: 404, name: 'ProductHunt', url: 'https://www.producthunt.com', logo_url: '' },
  { id: 4044, category_id: 404, name: 'SEMrush', url: 'https://www.semrush.com', logo_url: '' },
  { id: 4045, category_id: 404, name: 'BuiltWith', url: 'https://builtwith.com', logo_url: '' },

]);

// ================= 自由拖拽排序逻辑 =================
const draggedSite = ref(null);

const onDragStart = (e, site) => {
  draggedSite.value = site;
  e.dataTransfer.effectAllowed = 'move';
  // 给拖拽的元素加一个半透明样式
  setTimeout(() => { e.target.classList.add('dragging'); }, 0);
};

const onDragOver = (e) => {
  e.preventDefault(); // 必须阻止默认行为，否则无法触发 drop
  e.dataTransfer.dropEffect = 'move';
};

const onDrop = (e, targetSite) => {
  if (!draggedSite.value || draggedSite.value.id === targetSite.id) return;

  // 找到拖拽项和目标项在数组中的索引
  const fromIndex = websites.value.findIndex(s => s.id === draggedSite.value.id);
  const toIndex = websites.value.findIndex(s => s.id === targetSite.id);

  if (fromIndex !== -1 && toIndex !== -1) {
    // 互换或插入位置 (这里采用插入模式)
    const [movedItem] = websites.value.splice(fromIndex, 1);
    websites.value.splice(toIndex, 0, movedItem);
    
    // 如果有 toast，提示一下保存成功
    if(typeof showToast === 'function') showToast('排序已保存', 'success');
  }
};

const onDragEnd = (e) => {
  e.target.classList.remove('dragging');
  draggedSite.value = null;
};

const isLoading = ref(true);

// ================= 智能过滤与本地秒搜 (加入收藏夹逻辑) =================
const filteredWebsites = computed(() => {
  let list = websites.value;
  
  // 1. 分类过滤
  if (activeCategoryId.value === 'favorites') {
    // ✨ 核心：当处于“我的收藏”分类时，仅过滤出在 favoriteSiteIds 数组里的网站
    list = list.filter(site => favoriteSiteIds.value.includes(site.id));
  } else if (activeCategoryId.value !== 'all') {
    // 常规分类过滤
    list = list.filter(site => site.category_id == activeCategoryId.value);
  }
  
  // 2. 本地秒搜过滤 (实时监听输入框 searchQuery)
  const keyword = searchQuery.value.trim().toLowerCase();
  if (keyword) {
    list = list.filter(site => 
      site.name.toLowerCase().includes(keyword) || 
      (site.url && site.url.toLowerCase().includes(keyword))
    );
  }
  
  return list;
});

// ================= 搜索建议与历史记录 =================
const isSearchFocused = ref(false); // 搜索框是否获得焦点
const searchHistory = ref([]); // 搜索历史数组

// 1. 处理搜索框失焦 (延迟 200ms，以确保点击下拉框条目的事件能先触发)
const handleSearchBlur = () => {
  setTimeout(() => {
    isSearchFocused.value = false;
  }, 200);
};

// 2. 从 localStorage 读取历史记录
const loadSearchHistory = () => {
  const history = localStorage.getItem('search_history');
  if (history) {
    searchHistory.value = JSON.parse(history);
  }
};

// 3. 保存历史记录 (在调用引擎搜索时触发)
const saveSearchToHistory = (keyword) => {
  const k = keyword.trim();
  if (!k) return;
  
  // 去除重复的历史，并把最新的放到数组最前面
  const filtered = searchHistory.value.filter(item => item !== k);
  filtered.unshift(k);
  
  // 只保留最近的 5 个
  searchHistory.value = filtered.slice(0, 5);
  localStorage.setItem('search_history', JSON.stringify(searchHistory.value));
};

// 4. 清空历史
const clearSearchHistory = () => {
  searchHistory.value = [];
  localStorage.removeItem('search_history');
};

// 5. 点击历史记录直接搜索
const useHistory = (keyword) => {
  searchQuery.value = keyword;
  doSearch();
};

// 7. 【关键修改】：替换你原来的 doSearch 函数！
// 让它在跳走前，顺便保存一下搜索词
const doSearch = () => {
  if (searchQuery.value && allEngines[currentEngine.value]) {
    saveSearchToHistory(searchQuery.value); // ✨ 新增：保存历史
    window.open(allEngines[currentEngine.value].url + encodeURIComponent(searchQuery.value), '_blank');
    isSearchFocused.value = false; // 搜索后收起下拉框
  }
};

// ================= 浏览器书签一键导入 =================
const bookmarkInputRef = ref(null);

const triggerBookmarkImport = () => {
  bookmarkInputRef.value?.click();
};

const handleBookmarkImport = (event) => {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    const htmlContent = e.target.result;
    // 使用 DOMParser 解析 HTML 字符串
    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlContent, 'text/html');
    
    // 提取所有的 <a> 标签 (书签链接)
    const links = doc.querySelectorAll('a');
    let importedCount = 0;

    links.forEach(link => {
      const url = link.href;
      const name = link.textContent || '未命名书签';
      
      // 简单去重：检查是否已经存在相同 URL 的网站
      if (!websites.value.find(s => s.url === url)) {
        websites.value.push({
          id: Date.now() + Math.random(), // 生成唯一 ID
          category_id: activeCategoryId.value !== 'all' ? activeCategoryId.value : 1, // 塞入当前分类
          name: name.slice(0, 15), // 限制名字长度
          url: url,
          clicks: 0
        });
        importedCount++;
      }
    });

    if (importedCount > 0) {
      if (typeof showToast === 'function') showToast(`🎉 成功导入 ${importedCount} 个书签！`, 'success');
      else alert(`🎉 成功导入 ${importedCount} 个书签！`);
    } else {
      alert("没有发现新书签，或书签已存在。");
    }
    event.target.value = ''; // 清空 input
  };
  reader.readAsText(file); // 以文本方式读取 HTML 文件
};


// ================= 搜索功能与搜索引擎配置 =================
const searchQuery = ref('');
const localSuggestions = ref([]);

// 1. 初始化纯前端搜索引擎 (使用 let 允许我们在数据变化时重置它)
let searchIndex = new FlexSearch.Document({
  document: { id: "id", index: ["name", "url"] },
  tokenize: "forward" // 前缀匹配模式，输入 "b" 就能搜出 "bilibili"
});

// 2. 监听全局网站数据变化，自动更新搜索索引库
watch(websites, (newVal) => {
  // 每次有新数据时，直接创建一个新的干净索引，避免旧数据残留和 removeAll 报错
  searchIndex = new FlexSearch.Document({
    document: { id: "id", index: ["name", "url"] },
    tokenize: "forward"
  });
  // 把最新的网站数据极速装载入搜索引擎
  newVal.forEach(site => searchIndex.add(site));
}, { immediate: true, deep: true });

// 3. 监听用户输入，执行前端秒搜 (替代了原来的 fetch 远程请求)
watch(searchQuery, (newQuery) => {
  const query = newQuery.trim();
  
  // 如果清空了输入框，立刻清空建议列表
  if (!query) {
    localSuggestions.value = [];
    return;
  }

  // 在浏览器内存中极速搜索，最多返回 6 条结果
  const results = searchIndex.search(query, { limit: 6 });
  
  // 提取搜到的网站 ID
  const ids = results.flatMap(res => res.result);
  
  // 组装结果，并完美兼容你现有的 HTML 模板
  localSuggestions.value = ids.map(id => {
    const site = websites.value.find(s => s.id === id);
    if (!site) return null;
    
    // 动态生成高亮标签，包裹匹配到的关键字 (完美对应你 CSS 里的 <em> 样式)
    const regex = new RegExp(`(${query})`, 'gi');
    const highlightedName = site.name.replace(regex, '<em>$1</em>');
    const highlightedUrl = site.url ? site.url.replace(regex, '<em>$1</em>') : '';
    
    return {
      ...site, // 继承原本的数据
      _formatted: { // 伪装成 Meilisearch 的格式结构，这样你的 HTML 完全不用改！
        name: highlightedName,
        url: highlightedUrl
      }
    };
  }).filter(Boolean); // 过滤掉无效的空结果
});


// 1. 所有引擎的完整数据字典 (含名称和真实搜索跳转链接)
const allEngines = {
  '360': { name: '360', url: 'https://www.so.com/s?q=' },
  'baidu': { name: '百度', url: 'https://www.baidu.com/s?wd=' },
  'bing': { name: '必应', url: 'https://cn.bing.com/search?q=' },
  'google': { name: 'Google', url: 'https://www.google.com/search?q=' },
  'quark': { name: '夸克', url: 'https://quark.sm.cn/s?q=' },
  'bilibili': { name: 'B站', url: 'https://search.bilibili.com/all?keyword=' },
  'douyin': { name: '抖音', url: 'https://www.douyin.com/search/' },
  'zhihu': { name: '知乎', url: 'https://www.zhihu.com/search?type=content&q=' },
  'weibo': { name: '微博', url: 'https://s.weibo.com/weibo?q=' },
  'github': { name: 'GitHub', url: 'https://github.com/search?q=' },
  'juejin': { name: '掘金', url: 'https://juejin.cn/search?query=' },
  'translate': { name: '翻译', url: 'https://fanyi.baidu.com/#en/zh/' }
};

// 2. 弹窗中用于渲染全部选项的列表
const searchEngines = ref(
  Object.keys(allEngines).map(key => ({ id: key, name: allEngines[key].name }))
);

// 3. 当前被勾选的引擎 ID 列表
const selectedEngines = ref(['bing', 'google', 'bilibili', 'github', 'baidu', 'douyin']);

// 4. 动态计算主页搜索框下方显示的按钮
const activeEnginesList = computed(() => {
  return selectedEngines.value.map(id => ({ key: id, name: allEngines[id]?.name || id }));
});

// 5. 当前真正正在使用的搜索引擎
const currentEngine = ref(selectedEngines.value[0] || 'bing');

// 控制设置弹窗开关
const showEngineModal = ref(false);

// 弹窗功能：获取胶囊标签名字
const getEngineName = (id) => allEngines[id]?.name || id;

// 弹窗功能：点击标签上的 × 移除该引擎
const removeEngine = (id) => {
  selectedEngines.value = selectedEngines.value.filter(item => item !== id);
  // 如果把当前正在使用的移除了，自动切换到下一个
  if (currentEngine.value === id && selectedEngines.value.length > 0) {
    currentEngine.value = selectedEngines.value[0];
  }
};
// ================= 1. 持久化存储 (暗色模式 & 搜索引擎) =================
// 监听暗色模式变化并保存
watch(isDarkMode, (newVal) => {
  localStorage.setItem('dark_mode', newVal);
  syncSettingsToCloud();
});

// 监听当前搜索引擎并保存
watch(currentEngine, (newVal) => {
  localStorage.setItem('current_engine', newVal);
  syncSettingsToCloud();
});

// 监听选中的引擎列表并保存
watch(selectedEngines, (newVal) => {
  localStorage.setItem('selected_engines', JSON.stringify(newVal));
  syncSettingsToCloud();
}, { deep: true });

// ================= AI 聊天功能 =================
const chatWindow = ref(null);
const chatMessages = ref([{ role: 'ai', content: '你好！我是导航助手，想找什么神仙网站？直接问我！' }]);
const userInput = ref('');
const isAiThinking = ref(false);

// ================= 🤖 核心：AI 智能建议请求 (直连 DeepSeek) =================
const sendMessage = async () => {
  const text = userInput.value.trim();
  if (!text || isAiThinking.value) return;
  
  // 1. 把用户的输入展示在界面上
  chatMessages.value.push({ role: 'user', content: text });
  userInput.value = '';
  isAiThinking.value = true;
  scrollToBottom();

  // 🔽 开始尝试 (try)
  try {
    const res = await axios.get(`http://127.0.0.1:5001/api/ai/suggest?q=${encodeURIComponent(text)}`);
    
    if (res.data.code === 0 && res.data.data.length > 0) {
      let replyHtml = '为您找到以下精选网站（点击名称直达）：<br>';
      
      res.data.data.forEach((site) => {
        replyHtml += `
          <div class="ai-site-card" style="margin-top: 8px; padding: 8px; background: rgba(255,255,255,0.1); border-radius: 6px; transition: all 0.2s ease;">
            <a href="${site.url}" target="_blank" class="ai-site-link" style="color: #60a5fa; font-weight: bold; text-decoration: none;">
              🔗 ${site.title}
            </a>
            <div style="font-size: 12px; color: #cbd5e1; margin-top: 4px;">${site.snippet}</div>
          </div>
        `;
      });
      
      chatMessages.value.push({ role: 'ai', content: replyHtml });
    } else {
      chatMessages.value.push({ role: 'ai', content: '抱歉，没有找到匹配的推荐。' });
    }
  } 
  // 🔽 如果出错就捕获 (catch) —— 你刚才很可能就是漏掉了这里！
  catch (error) {
    if (error.response && error.response.status === 429) {
      chatMessages.value.push({ role: 'ai', content: '⚠️ 思考太快啦，请休息一分钟再试！' });
    } else {
      chatMessages.value.push({ role: 'ai', content: '⚠️ 网络走神了，请检查 5001 端口是否启动。' });
    }
  } 
  // 🔽 最终必须执行 (finally)
  finally {
    isAiThinking.value = false;
    scrollToBottom();
  }
};
// 🔼 函数完整结束
const scrollToBottom = () => { nextTick(() => { if (chatWindow.value) chatWindow.value.scrollTop = chatWindow.value.scrollHeight }) };


// ================= 右键菜单 (Context Menu) 完整逻辑 =================
const contextMenu = ref({ show: false, x: 0, y: 0, site: null });

// ✨ 1. 终极通用关闭函数：瞬间消灭所有悬浮菜单
const closeAllDropdowns = () => {
  if (contextMenu.value) contextMenu.value.show = false;
  if (catContextMenu.value) catContextMenu.value.show = false;
  if (profContextMenu.value) profContextMenu.value.show = false; // ✨ 新增这一行
};

// ✨ 2. 唤醒网站专属的右键菜单
const openContextMenu = (e, site) => {
  closeAllDropdowns(); // 互斥机制：弹窗前，先强制清理屏幕上的其他菜单！
  contextMenu.value = { show: true, x: e.clientX, y: e.clientY, site };
};

// 3. 动作：编辑此网站
const editSite = () => {
  if (!contextMenu.value.site) return;
  isEditingSite.value = true;
  newSiteForm.value = { ...contextMenu.value.site }; // 拷入该网站的数据
  showAddSiteModal.value = true; // 弹出大弹窗
  closeAllDropdowns(); // 强制收回右键小菜单
};

// 4. 动作：删除此网站
const deleteSite = () => {
  if (!contextMenu.value.site) return;
  const siteName = contextMenu.value.site.name;
  websites.value = websites.value.filter(s => s.id !== contextMenu.value.site.id);
  if (typeof showToast === 'function') showToast(`已删除 [${siteName}]`, 'info');
  closeAllDropdowns(); // 强制收回右键小菜单
};

// 3. 分类右键菜单动作
const handleEditFromMenu = () => {
  openCategoryModal(catContextMenu.value.category); 
  closeAllDropdowns(); // ✨ 强制收回右键菜单！
};

const handleDeleteFromMenu = () => {
  editingCategory.value = catContextMenu.value.category;
  deleteCategory(); 
  closeAllDropdowns(); // ✨ 强制收回右键菜单！
};
// ================= 🎨 终极外观引擎 (支持图片、颜色、渐变) =================
const showBgModal = ref(false);
const customWallpaper = ref('');
// ================= 专注模式专属背景逻辑 (与首页彻底分离) =================
const focusWallpaper = ref(localStorage.getItem('focus_wallpaper') || '');

// 设置专注背景
const applyFocusBg = (bg) => {
  focusWallpaper.value = bg;
  localStorage.setItem('focus_wallpaper', bg);
  if (typeof showToast === 'function') showToast('✨ 专注背景设置成功', 'success');
};

// 清除专注背景
const clearFocusBg = () => {
  focusWallpaper.value = '';
  localStorage.removeItem('focus_wallpaper');
  if (typeof showToast === 'function') showToast('🗑️ 已恢复专注模式默认底色', 'success');
};

// 计算专注模式样式 (不再借用首页壁纸！)
const focusBgStyle = computed(() => {
  // ✨ 核心断开点：如果没有设置专注背景，直接返回空，使用 CSS 自带的经典白/深空黑
  if (!focusWallpaper.value) return {}; 

  const bg = focusWallpaper.value;
  const overlay = isDarkMode.value ? 'rgba(15, 23, 42, 0.85)' : 'rgba(255, 255, 255, 0.85)';
  const isImage = bg.startsWith('http') || bg.startsWith('data:');
  
  return {
    backgroundImage: isImage 
      ? `linear-gradient(${overlay}, ${overlay}), url(${bg})`
      : `linear-gradient(${overlay}, ${overlay}), ${bg}`,
    backgroundSize: 'cover',
    backgroundPosition: 'center'
  };
});
const customColorPicker = ref('#3b82f6');
const wallpaperInputRef = ref(null);

// 精选绝美 CSS 渐变库 (非常适配毛玻璃)
const presetGradients = [
  'linear-gradient(135deg, #f6d365 0%, #fda085 100%)',
  'linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%)',
  'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
  'linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)',
  'linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)' // 暗色星空渐变
];

// 1. 设置纯色
const applyColorBg = (event) => { customWallpaper.value = event.target.value; };

// 2. 设置渐变色
const applyGradientBg = (grad) => { customWallpaper.value = grad; };

// 3. 上传图片
const triggerWallpaperUpload = () => { wallpaperInputRef.value?.click(); };
const handleWallpaperUpload = (event) => {
  const file = event.target.files[0];
  if (!file) return;
  if (!file.type.startsWith('image/')) return alert('只能上传图片文件哦！');
  if (file.size > 2.5 * 1024 * 1024) return alert('图片太大了，请选择 2.5MB 以内的壁纸！');

  const reader = new FileReader();
  reader.onload = (e) => {
    customWallpaper.value = e.target.result;
    if (typeof showToast === 'function') showToast('专属壁纸设置成功！', 'success');
  };
  reader.readAsDataURL(file);
  event.target.value = ''; 
};

// 4. 清除自定义背景
const clearBackground = () => { customWallpaper.value = ''; };

// 监听保存
// ================= 🧠 智能色彩适配算法 =================
// 提取颜色并计算人眼感知亮度 (YIQ 亮度公式)
const isDarkBackground = (bgStr) => {
  if (!bgStr) return false; // 默认为浅色
  
  // 尝试用正则提取背景中的第一个 HEX 颜色值
  const hexMatch = bgStr.match(/#([0-9a-fA-F]{3,6})/);
  
  if (!hexMatch) {
    // 如果找不到颜色（说明上传的是真实照片图片），
    // 对于复杂照片，深色毛玻璃 + 白字往往是最清晰、最有质感的，所以默认切到暗色模式
    return true; 
  }
  
  let hex = hexMatch[1];
  // 处理简写 hex (如 #fff -> ffffff)
  if (hex.length === 3) {
    hex = hex.split('').map(c => c + c).join('');
  }
  
  // 转换为 RGB
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);
  
  // 根据人眼对绿光最敏感的物理特性，计算感知亮度 (取值 0~255)
  const brightness = (r * 299 + g * 587 + b * 114) / 1000;
  
  // 亮度小于 128 判定为深色背景
  return brightness < 128;
};

// 升级版监听器：不仅保存，还自动切换全站 UI 颜色！
watch(customWallpaper, (newVal) => {
  if (newVal) {
    localStorage.setItem('custom_wallpaper', newVal);
    // ✨ 魔法生效：根据背景亮度自动切换昼夜模式！
    isDarkMode.value = isDarkBackground(newVal);
  } else {
    localStorage.removeItem('custom_wallpaper');
    // 恢复默认壁纸时，切回白天模式
    isDarkMode.value = false; 
  }
  syncSettingsToCloud();
});

// ✨ 核心：智能解析渲染
const dynamicBgStyle = computed(() => {
  if (!customWallpaper.value) return {};
  const bg = customWallpaper.value;
  
  // 如果是 Base64 或 http 图片链接
  if (bg.startsWith('http') || bg.startsWith('data:')) {
    return { backgroundImage: `url(${bg})`, backgroundSize: 'cover', backgroundAttachment: 'fixed' };
  }
  // 如果是 HEX 纯色 或 linear-gradient 渐变
  return { background: bg, backgroundAttachment: 'fixed' };
});

// 1. 改用数组，Vue 响应式最稳定！
const favoriteSiteIds = ref([]); 

// ================= 藏宝图彩蛋逻辑 (随机刷新版) =================
// 独立奖池：保证点击某个小岛时，其他小岛不会乱跳
const currentTreasurePool = ref([]);

// 🎯 核心玩法：随机抽取 3 个未收藏的网站
const refreshTreasures = () => {
  const sourceList = typeof websites !== 'undefined' ? websites.value : (typeof allWebsites !== 'undefined' ? allWebsites.value : []);
  if (!sourceList || sourceList.length === 0) return;

  // 筛出还没被收藏的网站
  const unFavorited = sourceList.filter(site => !favoriteSiteIds.value.includes(site.id));

  // ✨ 将数组随机打乱 (经典的 Fisher-Yates 洗牌平替法)
  const shuffled = [...unFavorited].sort(() => 0.5 - Math.random());
  
  // 截取前 3 个放入当前奖池
  currentTreasurePool.value = shuffled.slice(0, 3);
};

// 监听：当进入“我的收藏”时，如果奖池是空的，就刷一批出来
watch(() => activeCategoryId.value, (newCat) => {
  if (newCat === 'favorites' && currentTreasurePool.value.length === 0) {
    refreshTreasures();
  }
});

// 给抽取出的宝藏按顺序分配绝美图标
// 给抽取出的宝藏分配真实数据
const treasureIslands = computed(() => {
  // ✨ 直接返回抽取的网站数据，不再强行塞入 Emoji
  return currentTreasurePool.value;
});

// 领取宝藏
const claimTreasure = async (island) => {
  console.log("挖掘宝藏:", island.name);

  // ✨ 细节优化：点击后立刻从小岛列表中移除它，制造“被挖走”的视觉效果
  currentTreasurePool.value = currentTreasurePool.value.filter(s => s.id !== island.id);

  if (typeof toggleFavorite === 'function') {
    await toggleFavorite(island); // 调用全局收藏，瞬间响应！
  }

  // ✨ 彩蛋中的彩蛋：如果 3 个小岛都被你挖空了，延迟 0.5 秒自动再刷一批新的出来！
  if (currentTreasurePool.value.length === 0) {
    setTimeout(() => { refreshTreasures(); }, 500); 
  }
};

// 2. 获取收藏列表
const fetchFavorites = async () => {
  if (!isLoggedIn.value) {
    favoriteSiteIds.value = [];
    return;
  }
  try {
    const token = localStorage.getItem('access_token');
    const res = await axios.get('http://127.0.0.1:5000/api/favorites', {
      headers: { Authorization: `Bearer ${token}` } 
    });
    favoriteSiteIds.value = res.data; // 直接把后端返回的数组存起来
  } catch (error) {
    console.error('获取收藏列表失败:', error);
  }
};

// ================= 职业操作与右键菜单逻辑 =================
const showAddProfModal = ref(false);
const newProf = ref({ name: '', icon: '' });
const isEditingProf = ref(false); // 标识是否处于编辑模式
const editingProfKey = ref(null); // 记录当前正在编辑的职业 Key

// 职业右键菜单状态
const profContextMenu = ref({ show: false, x: 0, y: 0, profKey: null, profData: null });

// 1. 点击“+ 添加职业”按钮
const openAddModal = () => {
  isEditingProf.value = false;
  editingProfKey.value = null;
  newProf.value = { name: '', icon: '' };
  showAddProfModal.value = true;
};

// 2. 右键唤醒菜单
const openProfContextMenu = (e, key, data) => {
  closeAllDropdowns();
  profContextMenu.value = { show: true, x: e.clientX, y: e.clientY, profKey: key, profData: data };
};

// 3. 点击菜单中的“编辑”
const handleEditProfFromMenu = () => {
  isEditingProf.value = true;
  editingProfKey.value = profContextMenu.value.profKey;
  // 拷贝现有数据到输入框
  newProf.value = { name: profContextMenu.value.profData.name, icon: profContextMenu.value.profData.icon };
  showAddProfModal.value = true;
  closeAllDropdowns();
};

// 4. 点击菜单中的“删除”
const handleDeleteProfFromMenu = () => {
  const key = profContextMenu.value.profKey;
  
  // 给内置职业加个保护锁
  if (['general', 'frontend', 'designer', 'product'].includes(key)) {
    alert('系统预设职业无法删除！');
    closeAllDropdowns();
    return;
  }

  if (confirm(`确定要删除职业 [${profContextMenu.value.profData.name}] 吗？`)) {
    delete professionData[key]; // 从数据源中剔除
    
    // 如果删除的正是当前正在看的职业，自动切回综合导航
    if (currentProfession.value === key) {
      currentProfession.value = 'general';
    }
  }
  closeAllDropdowns();
};

// 5. 核心保存逻辑（兼容新增与修改）
const handleConfirmAdd = () => {
  if (!newProf.value.name) return;

  if (isEditingProf.value && editingProfKey.value) {
    // ✨ 修改模式：直接更新原有属性，保留其 categories 列表不变
    professionData[editingProfKey.value].name = newProf.value.name;
    professionData[editingProfKey.value].icon = newProf.value.icon || '✨';
  } else {
    // ✨ 新增模式：创建新属性
    const newKey = 'prof_' + Date.now();
    professionData[newKey] = {
      name: newProf.value.name,
      icon: newProf.value.icon || '✨',
      categories: [{ id: 999, name: '默认分类' }]
    };
    currentProfession.value = newKey; // 切到新职业
  }

  // 状态复原
  showAddProfModal.value = false;
  isEditingProf.value = false;
  editingProfKey.value = null;
  newProf.value = { name: '', icon: '' };
};

// ================= 切换收藏状态 (极致丝滑版) =================
const toggleFavorite = async (site) => {
  if (!site || !site.id) return;

  // 1. 判断当前是不是已经被收藏了
  const index = favoriteSiteIds.value.indexOf(site.id);
  const isCurrentlyFavorited = index !== -1;

  // ✨ 2. 乐观更新魔法：不管后端同不同意，前端立刻做出反应！
  if (isCurrentlyFavorited) {
    // 瞬间取消收藏：从前端数组中拔掉它，卡片立马消失/星星立马变空！
    favoriteSiteIds.value.splice(index, 1);
    console.log("前端已瞬间取消收藏:", site.name);
  } else {
    // 瞬间加入收藏
    favoriteSiteIds.value.push(site.id);
    console.log("前端已瞬间加入收藏:", site.name);
  }

  // 3. 静默去跟后端同步数据
  try {
    // 这里是你原本发给后端的 API 请求代码
    // 比如：await fetch('/api/favorites/toggle', { ... }) 
    // 👇 请确保下面这行是你真实的后端接口请求（如果没有，可以先注释掉）
    
    /* const response = await fetch('/api/favorites', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ site_id: site.id })
    });
    if (!response.ok) throw new Error("后端同步失败");
    */

    // 可以在这里加个成功的小提示（可选）
    showToast(isCurrentlyFavorited ? '已取消收藏' : '⭐ 收藏成功');

  } catch (error) {
    console.warn("后端同步出错了，但前端体验依然丝滑！", error);
    
    // 🛡️ 兜底机制：如果后端真的彻底挂了，为了保证数据不乱，再悄悄把状态改回去
    // 如果你不需要这么严谨，这段 catch 里的代码甚至可以不写。
    if (isCurrentlyFavorited) {
      favoriteSiteIds.value.push(site.id); // 还原回收藏状态
    } else {
      const revertIdx = favoriteSiteIds.value.indexOf(site.id);
      if (revertIdx !== -1) favoriteSiteIds.value.splice(revertIdx, 1); // 还原回未收藏
    }
  }
};
// 4. 动态计算收藏列表
const favoritedSitesList = computed(() => {
  // 使用 .includes 而不是 .has
  return websites.value.filter(site => favoriteSiteIds.value.includes(site.id));
});

// 核心逻辑：动态筛选
const filteredSites = computed(() => {
  const currentSites = professionData.value[currentProfession.value].sites;
  // 如果当前职业的 sites 列表为空，或者你想实现基于算法的推送：
  // 可以根据 currentSites 里的标签去 websites 总库中搜索匹配
  return websites.value.filter(site => 
    currentSites.includes(site.name) || site.tags.some(t => currentSites.includes(t))
  );
});

// --- 💡 关键：确保在 refreshStatus() 函数里调用它 ---
// 找到你刚写好的 refreshStatus 函数，在里面补充 fetchFavorites()
const refreshStatus = () => {
  const savedStatus = localStorage.getItem('is_logged_in');
  const savedUser = localStorage.getItem('user_info');
  if (savedStatus === 'true' && savedUser) {
    isLoggedIn.value = true;
    userInfo.value = JSON.parse(savedUser);
    // 🎯 检查用户是否已完成问卷
    hasSurvey.value = userInfo.value?.has_survey === 1;
    loadSettingsFromCloud(userInfo.value.username);
    fetchFavorites(); // ✨ 登录成功后，立刻拉取收藏列表
    loadRecommendations(); // 🎯 登录后加载推荐
    // 🎯 未做问卷则弹窗
    checkAndShowSurvey();
  } else {
    isLoggedIn.value = false;
    favoriteSiteIds.value = [];
    hasSurvey.value = true; // 未登录时不弹窗
  }
};

// 2. 监听路由变化，确保从登录页跳回来时状态立即刷新
watch(() => router.currentRoute.value.path, () => {
  refreshStatus();
});

onMounted(async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const accessToken = urlParams.get('access_token');
  const refreshToken = urlParams.get('refresh_token');
  const username = urlParams.get('username');
  const avatar = urlParams.get('avatar');

  playParticleIntro(); // ✨ 启动粒子动画！
  if (accessToken && refreshToken) {
    // 把后端签发的钥匙存进保险箱
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    localStorage.setItem('is_logged_in', 'true');
    
    localStorage.setItem('user_info', JSON.stringify({
      username: username || 'GitHub 用户',
      avatar: avatar || ''
    }));

    // ✨ 核心清理：清除 URL 里的 token 参数，防止一刷新又走一遍，保护隐私
    window.history.replaceState({}, document.title, window.location.pathname);

    // 提示用户并关闭弹窗
    if (typeof showToast === 'function') showToast('GitHub 授权登录成功！', 'success');
    showAuthModal.value = false;
  }
  refreshStatus();
  fetchIndustryNews();
  // 1. 读取所有缓存 (保持不变)
// 1. 读取所有缓存 (保持不变)
  if (localStorage.getItem('dark_mode') === 'true') isDarkMode.value = true;
  const savedBg = localStorage.getItem('custom_wallpaper');
  if (savedBg) customWallpaper.value = savedBg;
  const savedCurrentEngine = localStorage.getItem('current_engine');
  if (savedCurrentEngine) currentEngine.value = savedCurrentEngine;
  const savedEngines = JSON.parse(localStorage.getItem('selected_engines'));
  if (savedEngines && savedEngines.length > 0) selectedEngines.value = savedEngines;

  // 2. 绑定全局快捷键与全局点击
// 2. 绑定全局快捷键与全局鼠标点击（必须绑定，否则菜单不消失）
  document.addEventListener('keydown', handleGlobalKeydown);
  document.addEventListener('click', closeAllDropdowns);

  // 3. 恢复本地登录状态
  const savedUser = localStorage.getItem('user_info');
  if (localStorage.getItem('is_logged_in') === 'true' && savedUser) {
    userInfo.value = JSON.parse(savedUser);
    isLoggedIn.value = true;
    loadSettingsFromCloud(userInfo.value.username);
  }

  // 4. 获取数据（核心修改区）
  try {
    isLoading.value = true; // 开启骨架屏

    // 并发执行：获取排行榜 和 获取主导航数据
    fetchRankingData(); 
    // ⚠️ 关键：直接调用 fetchNavData，它内部会处理好所有分类和网站的赋值
    await fetchNavData(); 

    // 设置排行榜轮询
    pollingTimer = setInterval(() => { fetchRankingData(); }, 5000);

  } catch (e) { 
    console.warn("全栈对接失败，请检查 Flask 后端:", e); 
  } finally {
    // 稍微延迟关闭骨架屏，确保视觉丝滑
    setTimeout(() => { 
      isLoading.value = false; 
    }, 300);
  }

  
});
onUnmounted(() => {
  if (pollingTimer) clearInterval(pollingTimer);

  // document.removeEventListener('keydown', handleGlobalKeydown);
  document.removeEventListener('click', closeAllDropdowns); // ✨ 换成这个
  document.removeEventListener('keydown', handleGlobalKeydown);

});
</script>

<style scoped>
/* ================= 1. 全局色彩与基础布局 ================= */
:root {
  --primary: #3b82f6;      
  --primary-bright: linear-gradient(135deg, #60a5fa, #3b82f6); 
  --bg-main: #f8fafc;      
  --bg-block: #ffffff;     
  --bg-input: #ffffff;     
  --text-main: #1e293b;    
  --text-muted: #64748b;   
  --border-light: #e2e8f0; 
}
/* 默认纯净背景 (未登录或未设置壁纸时的初始状态) */
.layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #f8fafc; /* 清爽护眼的淡灰白底色 */
  background-image: none;    /* 彻底移除默认的彩色背景图 */
  background-size: cover;
  background-position: center;
  background-attachment: fixed;
}
.layout.dark-theme {
  /* 使用极深蓝黑（非死黑），这样毛玻璃透出的质感会更高级 */
  --bg-main: #0a0a0a;      
  --bg-block: rgba(28, 28, 28, 0.6);  /* 略微加深卡片背景，增强对比 */
  --bg-input: rgba(0, 0, 0, 0.4);
  
  /* 刚才优化的护眼文字颜色保持不变 */
  --text-main: #e2e8f0;    
  --text-muted: #94a3b8;   
  --border-light: rgba(255, 255, 255, 0.05); 
}

/* 核心毛玻璃质感 (Glassmorphism) */
.block-shadow, .widget, .sidebar-box, .info-card-box, .site-card, .search-box, .header-block, .prof-dropdown, .engine-modal, .context-menu {
  background: rgba(255, 255, 255, 0.4) !important;
  backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 8px 32px rgba(31, 38, 135, 0.1);
  border-radius: 24px;
}
.layout.dark-theme .block-shadow, .layout.dark-theme .widget, .layout.dark-theme .sidebar-box, .layout.dark-theme .info-card-box, .layout.dark-theme .site-card, .layout.dark-theme .search-box, .layout.dark-theme .header-block, .layout.dark-theme .prof-dropdown, .layout.dark-theme .engine-modal, .layout.dark-theme .context-menu {
  background: rgba(15, 23, 42, 0.45) !important;
  backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}
.layout.dark-theme .search-box {
  background: rgba(15, 23, 42, 0.6) !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.2);
}

.layout.dark-theme .search-box input {
  color: #fff;
}

.layout.dark-theme .search-box input::placeholder {
  color: #64748b;
}
.layout.dark-theme .site-card {
  background: rgba(255, 255, 255, 0.03) !important; /* 极薄的亮色，透出背后的黑 */
  border: 1px solid rgba(255, 255, 255, 0.05);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}

.layout.dark-theme .site-card:hover {
  background: rgba(59, 130, 246, 0.1) !important; /* 悬浮时依然保持微弱蓝光 */
  border-color: rgba(59, 130, 246, 0.2);
}

/* 🌙 让 Logo 在纯黑下显示更清晰 */
.layout.dark-theme .logo-wrapper {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
}
.layout.dark-theme .chat-bubble.user {
  background: #334155; /* 深灰蓝 */
  color: #f1f5f9;
}

.layout.dark-theme .trending-item {
  border-bottom-color: rgba(255, 255, 255, 0.03);
}

.layout.dark-theme .trending-item:hover {
  background: rgba(255, 255, 255, 0.03);
}


/* 🌙 让网页滚动条也适配暗色 */
.layout.dark-theme {
  -webkit-font-smoothing: subpixel-antialiased;
  -moz-osx-font-smoothing: auto;
  color-scheme: dark;
}
/* ================= 2. 顶部导航栏 ================= */
.header-block { height: 65px; display: flex; justify-content: space-between; align-items: center; padding: 0 40px; z-index: 100; flex-shrink: 0; border-radius: 0; border-top: none; border-left: none; border-right: none;}
.header-left { display: flex; align-items: center; gap: 25px; }
.logo { font-size: 22px; font-weight: 800; display: flex; align-items: center; color: var(--text-main); }
.header-right { display: flex; align-items: center; gap: 16px; margin-left: auto; }
.theme-toggle { background: transparent; border: none; font-size: 20px; cursor: pointer; transition: 0.3s; }
.theme-toggle:hover { transform: scale(1.15) rotate(15deg); }
.auth-group { display: flex; gap: 12px; }
.pill-btn { background: transparent; color: var(--text-main); border: 1px solid var(--border-light); padding: 8px 22px; border-radius: 25px; cursor: pointer; font-size: 14px; font-weight: 600; transition: 0.3s; }
.btn-primary { background: var(--primary-bright); color: #fff; border: none; padding: 8px 22px; border-radius: 25px; cursor: pointer; font-size: 14px; font-weight: 600; transition: 0.3s; }

/* 职业下拉 */
.profession-selector { position: relative; cursor: pointer; padding: 5px 0; }
.current-prof-box { display: flex; align-items: center; gap: 8px; padding: 6px 15px; border-radius: 10px; border: 1px solid var(--border-light); transition: 0.3s; }
.prof-name { font-size: 14px; font-weight: 600; }
.prof-arrow { font-size: 10px; transition: 0.3s; }
.profession-selector:hover .prof-dropdown { opacity: 1; visibility: visible; transform: translateY(0); }
.prof-dropdown { position: absolute; top: 100%; left: 0; margin-top: 10px; width: 180px; padding: 8px; opacity: 0; visibility: hidden; transform: translateY(-10px); transition: 0.3s; z-index: 1000; }
.prof-item { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 8px; transition: 0.2s; }
.prof-item:hover { background: rgba(59, 130, 246, 0.1); color: var(--primary); }

/* ================= 修复：分类“更多”下拉菜单 ================= */
.more-dropdown-wrapper { 
  position: relative; 
  display: flex; 
  align-items: center; 
}

.dropdown-menu { 
  position: absolute; 
  top: 100%; 
  right: 0; /* 右对齐，防止撑出屏幕 */
  margin-top: 12px; 
  background: rgba(255, 255, 255, 0.7); 
  backdrop-filter: blur(20px); 
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.6); 
  border-radius: 12px; 
  padding: 8px; 
  box-shadow: 0 10px 30px rgba(0,0,0,0.1); 
  opacity: 0; 
  visibility: hidden; 
  transform: translateY(-10px); 
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1); 
  z-index: 100; 
  min-width: 160px; /* ✨ 关键：保证能放下“导入浏览器书签”几个字 */
  text-align: left; /* 菜单里的文字靠左对齐更好看 */
}

/* 悬浮时平滑展开 */
.more-dropdown-wrapper:hover .dropdown-menu { 
  opacity: 1; 
  visibility: visible; 
  transform: translateY(0); 
}

.dropdown-item { 
  padding: 10px 15px; 
  border-radius: 8px; 
  font-size: 14px; 
  font-weight: 600; 
  cursor: pointer; 
  color: var(--text-muted); 
  transition: 0.2s;
}

.dropdown-item:hover { 
  background: rgba(255, 255, 255, 0.5); 
  color: var(--primary); 
}

/* ✨ 核心修复：防止右上角头像 SVG 爆炸放大，并恢复圆形 */
.user-profile-container { 
  width: 42px; 
  height: 42px; 
  border-radius: 50%; 
  overflow: hidden; 
  display: flex; 
  align-items: center; 
  justify-content: center;
  flex-shrink: 0; /* 防止被其他元素挤压 */
  border: 2px solid rgba(255, 255, 255, 0.6); /* 增加一个精致的高光边框 */
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: 0.3s;
}

.user-profile-container:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(59, 130, 246, 0.3);
  border-color: #60a5fa;
}

.header-avatar { 
  width: 100%; 
  height: 100%; 
  object-fit: cover; 
  transition: 0.3s; 
}

.user-profile-container:hover .header-avatar { 
  transform: scale(1.1); /* 鼠标悬浮时头像微微放大 */
}

/* ================= 3. 主体内容与搜索区 ================= */
.main-container { display: flex; flex: 1; padding: 25px; gap: 25px; }
/* ✨ 修复排版收缩的关键：给 content 加上 width: 100% */
.content { flex: 1; width: 100%; display: flex; flex-direction: column; align-items: center; padding: 10px 20px; }
.center-action-area { width: 100%; display: flex; flex-direction: column; align-items: center; margin-bottom: 30px; margin-top: 10px; }

/* 搜索框完美尺寸 */
.search-section { width: 100%; max-width: 650px; display: flex; flex-direction: column; align-items: center; }
.search-box { width: 100%; display: flex; align-items: center; border-radius: 40px; padding: 6px 6px 6px 20px; position: relative; z-index: 20; transition: 0.3s; }
.search-box:focus-within { box-shadow: 0 10px 30px rgba(59, 130, 246, 0.12); border-color: rgba(59, 130, 246, 0.4); }
.search-box input { flex: 1; border: none; outline: none; font-size: 15px; background: transparent; color: var(--text-main); min-width: 0; }
.search-btn-oval { background: var(--primary-bright); color: #fff; border: none; border-radius: 30px; padding: 10px 28px; cursor: pointer; font-weight: 600; letter-spacing: 1px; transition: 0.3s; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2); margin-left: 10px; }

/* 分类 Tabs */
.category-tabs-wrapper { 
  display: flex; 
  gap: 12px; /* 把间距稍微调小一点，显得更紧凑精致 */
  justify-content: center; /* 确保居中 */
  margin: 0 auto 25px auto; 
  flex-wrap: wrap; 
  max-width: 900px; /* 限制最大宽度，防止在大屏上被拉得太散 */
}
.nav-tab-box {
  cursor: pointer;
  /* ✨ 核心修改：减小字号和内边距 */
  font-size: 13px;       /* 从 14px 降到 13px */
  padding: 6px 14px;     /* 从 8px 20px 缩减到 6px 14px */
  
  display: flex;         /* 确保图标和文字对齐 */
  align-items: center;
  gap: 5px;              /* 缩小图标和文字的间距 */
  border-radius: 10px;   /* 圆角也相应调小一点点，更协调 */
  transition: 0.3s;
  
  /* 保持原有的文字投影或背景逻辑 */
  text-shadow: 0 1px 2px rgba(255,255,255,0.8);
  white-space: nowrap;   /* 防止文字换行 */
}
.layout.dark-theme .nav-tab-box {
  color: var(--text-muted);
  font-weight: 400; /* 未选中态保持轻盈 */
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.layout.dark-theme .nav-tab-box.active {
  color: #60a5fa; /* 选中态使用明亮的淡蓝色 */
  font-weight: 600;
  background: rgba(59, 130, 246, 0.15) !important;
  border-color: rgba(96, 165, 250, 0.4);
}
.nav-tab-box:hover { background: rgba(0,0,0,0.05); }
/* ================= 优化：当前选中分类的高亮质感 ================= */
.nav-tab-box.active { 
  background: rgba(255, 255, 255, 0.65); /* 提升亮度，呈现冰块般的质感 */
  border: 1px solid rgba(255, 255, 255, 0.8);
  color: #2563eb; 
  font-weight: 700; 
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}
/* ================= 4. 搜索引擎单选与弹窗 ================= */
.engine-radio-group { display: flex; align-items: center; justify-content: center; gap: 15px; margin-top: 0px; flex-wrap: wrap; }
.engine-radio-label { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--text-main); cursor: pointer; transition: 0.2s; opacity: 0.8; }
.engine-radio-label:hover { opacity: 1; }
.hidden-radio { display: none; }
.radio-custom { width: 14px; height: 14px; border-radius: 50%; border: 1px solid var(--text-muted); display: flex; justify-content: center; align-items: center; }
.engine-radio-label.active .radio-custom { border-color: #3b82f6; }
.engine-radio-label.active .radio-custom::after { content: ''; width: 6px; height: 6px; background: #3b82f6; border-radius: 50%; }
.engine-radio-label.active { color: #3b82f6; font-weight: 600; opacity: 1; }
.engine-settings-icon { cursor: pointer; font-size: 14px; opacity: 0.5; transition: 0.3s; margin-left: 5px; }
.engine-settings-icon:hover { opacity: 1; transform: rotate(45deg); }

/* 搜索引擎弹窗 (修复对齐) */
/* ================= 11. 搜索引擎设置弹窗 (极致质感进化版) ================= */
.engine-modal { 
  width: min(520px, calc(100vw - 32px)); /* 稍微加宽一点，给复选框更多呼吸空间 */
  padding: 35px 40px !important; 
  background: rgba(255, 255, 255, 0.85) !important; /* ✨ 恢复顶级的透亮毛玻璃质感 */
  backdrop-filter: blur(30px); 
  -webkit-backdrop-filter: blur(30px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 25px 50px rgba(0,0,0,0.15); 
  border-radius: 28px; /* 更大、更柔和的圆角 */
}

/* 暗色模式适配 */
.layout.dark-theme .engine-modal {
  background: rgba(15, 23, 42, 0.8) !important;
  border-color: rgba(255, 255, 255, 0.1);
  box-shadow: 0 25px 50px rgba(0,0,0,0.5);
}

/* 顶部已选标签区 */
.selected-tags-area {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  min-height: 44px;
  margin-bottom: 25px;
}

/* ✨ 标签：苹果风胶囊设计 (Pill Shape) */
.engine-tag {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  background: rgba(59, 130, 246, 0.1);
  color: #2563eb;
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 24px; /* 彻底变为圆润的胶囊状 */
  font-size: 13px;
  font-weight: 600;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.layout.dark-theme .engine-tag {
  background: rgba(96, 165, 250, 0.15);
  color: #60a5fa;
  border-color: rgba(96, 165, 250, 0.3);
}

/* 标签悬浮：危险操作反馈 (变红并上浮) */
.engine-tag:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(239, 68, 68, 0.15);
}

.tag-close {
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  font-weight: bold;
  opacity: 0.6;
  transition: 0.2s;
}
.engine-tag:hover .tag-close { opacity: 1; }

/* 分割线：改为优雅的两端渐变消失 */
.modal-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border-light), transparent);
  margin: 0 0 25px 0;
  opacity: 0.8;
}

/* 底部复选框网格 */
.engine-checkbox-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 22px 12px; /* 拉大行间距 */
}

/* 页面主体框架（左右布局改上下） */
.main-content { /* 请替换为你代码中实际的主体容器类名 */
  display: flex;
  gap: 20px;
  width: 100%; /* 确保撑满屏幕 */
  max-width: 1200px;
  margin: 0 auto;
}

/* 搜索栏适配 */
.search-box { /* 请替换为你搜索框外层的实际类名 */
  width: 100%;
  max-width: 800px;
  margin: 0 auto 2rem auto;
}

.search-input { /* 请替换为 <input> 实际的类名 */
  width: 100%;
  min-height: 44px; /* 满足移动端手指触摸面积 */
  font-size: 1rem;  /* 跟随 html 的 rem 自动缩放 */
  padding: 0 20px;
}

/* ================= 12. 终极修复：消灭双黄蛋复选框与文字挤压 ================= */

/* ✨ 极其强硬地隐藏掉所有原生的 input 复选框，绝对不让它出来捣乱 */
.engine-checkbox-label input[type="checkbox"],
.hidden-checkbox {
  display: none !important;
}

/* ================= 搜索引擎网格升级：果冻块状按钮 ================= */
.engine-checkbox-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr); /* 保持 4 列 */
  gap: 14px; /* 间距拉大，呼吸感更强 */
}

/* 强硬隐藏原生 checkbox */
.hidden-checkbox { display: none !important; }

/* ✨ 全新的块状按钮外壳 */
.engine-toggle-card {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 12px 0;
  background: rgba(0, 0, 0, 0.03); /* 未选中时的浅灰透底 */
  border: 1px solid rgba(0, 0, 0, 0.04);
  border-radius: 12px; /* 圆滑的苹果风圆角 */
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  user-select: none;
}

/* 未选中态的悬浮反馈 */
.engine-toggle-card:not(.is-active):hover {
  background: rgba(0, 0, 0, 0.06);
  transform: translateY(-1px);
}

.engine-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-muted);
  transition: all 0.3s ease;
}

/* ✨ 选中态：发光果冻效果 */
.engine-toggle-card.is-active {
  background: rgba(59, 130, 246, 0.1); /* 泛蓝光底色 */
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.15); /* 漂亮的蓝色悬浮阴影 */
  transform: translateY(-2px); /* 选中后微微上浮 */
}

.engine-toggle-card.is-active .engine-name {
  color: #2563eb;
  font-weight: 700; /* 文字加粗变蓝 */
}

/* ================= 暗色模式完美适配 ================= */
.layout.dark-theme .engine-toggle-card {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.05);
}
.layout.dark-theme .engine-toggle-card:not(.is-active):hover {
  background: rgba(255, 255, 255, 0.08);
}
.layout.dark-theme .engine-toggle-card.is-active {
  background: rgba(96, 165, 250, 0.15);
  border-color: rgba(96, 165, 250, 0.3);
  box-shadow: 0 6px 16px rgba(96, 165, 250, 0.15);
}
.layout.dark-theme .engine-toggle-card.is-active .engine-name {
  color: #60a5fa;
}

/* 选中状态：发光膨胀 */
.engine-checkbox-label.is-checked .checkbox-custom {
  background: #3b82f6;
  border-color: #3b82f6;
  box-shadow: 0 4px 10px rgba(59, 130, 246, 0.3);
  transform: scale(1.1); /* 选中的瞬间会轻微放大 */
}

/* 绘制完美的对号 */
.engine-checkbox-label.is-checked .checkbox-custom::after {
  content: '';
  width: 5px;
  height: 10px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg) translate(-1px, -1px);
}

/* 选中后的文字高亮 */
.engine-checkbox-label.is-checked { 
  color: #2563eb; 
  font-weight: 700; 
  opacity: 1; 
}
.layout.dark-theme .engine-checkbox-label.is-checked { color: #60a5fa; }
/* ================= 5. 网站卡片与网格完美布局 ================= */
/* ✨ 修复网格崩塌的关键 */
/* ================= 修复：网站网格居中对齐 ================= */
.site-grid { /* 请替换为你实际的类名 */
  display: grid;
  width: 100%; /* ✨ 关键修复：让网格撑满父容器，不再缩成一团！*/
  max-width: 1000px; /* 可选：限制最大宽度，保持内容区整洁 */
  margin: 0 auto; /* ✨ 关键修复：让网格在父容器中水平居中 */
  gap: 1rem;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  min-height: calc(100vh - 200px); 
  
  /* 确保当卡片很少时，它们依然从最上方开始整齐排列，而不会垂直居中乱跑 */
  align-content: flex-start;
}

/* 平板端适配 (768px - 1024px) */
@media (max-width: 1024px) {
  .site-grid {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  }
}

/* 手机端适配 (<768px) */
@media (max-width: 767px) {
  .site-grid {
    /* 手机上强制变成单列上下排布 */
    grid-template-columns: 1fr;
    gap: 1rem; 
  }
}

/* ================= 优化：轻量化的“添加网站”卡片 ================= */
.site-card.add-site-card {
  background: rgba(255, 255, 255, 0.15) !important; /* 更高的透明度 */
  border: 2px dashed rgba(255, 255, 255, 0.6); /* 虚线边框暗示这是操作区 */
  box-shadow: none;
}

.site-card.add-site-card:hover {
  background: rgba(255, 255, 255, 0.3) !important;
  border-color: #fff;
  transform: translateY(-4px);
}

/* 去掉原本加号外面的白底壳子 */
.add-site-card .logo-wrapper {
  background: transparent;
  border: none;
  box-shadow: none;
}

.add-site-card .plus-icon {
  font-size: 36px;
  color: var(--text-muted);
  font-weight: 300;
  transition: 0.3s;
}

.site-card.add-site-card:hover .plus-icon {
  color: var(--primary);
  transform: scale(1.1);
}
.site-card { padding: 20px 12px; display: flex; flex-direction: column; align-items: center; cursor: pointer; transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1); border-radius: 20px; text-decoration: none; min-height: 44px;}
.site-card:hover { transform: translateY(-6px); box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1); border-color: rgba(59, 130, 246, 0.4); }
.layout.dark-theme .site-card:hover { box-shadow: 0 15px 35px rgba(0, 0, 0, 0.4); }

/* Logo 视差高光动画 */
.logo-wrapper { width: 58px; height: 58px; margin-bottom: 12px; background: rgba(255, 255, 255, 0.85); border-radius: 18px; border: 1px solid rgba(255, 255, 255, 0.9); box-shadow: 0 4px 10px rgba(0, 0, 0, 0.06), inset 0 2px 5px rgba(255, 255, 255, 1); display: flex; align-items: center; justify-content: center; overflow: hidden; flex-shrink: 0; transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1); }
.layout.dark-theme .logo-wrapper { background: rgba(255, 255, 255, 0.95); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3); }
.site-logo { width: 100%; height: 100%; object-fit: contain; padding: 12px; transition: transform 0.4s ease; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1)); }
.site-card:hover .logo-wrapper { transform: translateY(-5px) scale(1.05); box-shadow: 0 10px 20px rgba(0, 0, 0, 0.12), inset 0 2px 5px rgba(255, 255, 255, 1); }
.site-card:hover .site-logo { transform: scale(1.15); }
.site-name { font-size: 13px; font-weight: 600; text-shadow: 0 1px 2px rgba(255,255,255,0.8); }
.layout.dark-theme .site-name {
  color: var(--text-main);
  font-weight: 400; /* 夜间阅读，常规字重比加粗更舒适 */
  opacity: 0.9;
  transition: all 0.3s ease;
}

.layout.dark-theme .site-card:hover .site-name {
  color: #60a5fa;
  opacity: 1;
  text-shadow: 0 0 10px rgba(96, 165, 250, 0.3);
}
.layout.dark-theme .nav-tab-box {
  color: var(--text-muted);
  font-weight: 300;
}

.layout.dark-theme .nav-tab-box.active {
  color: #60a5fa; /* 使用更亮的蓝色 */
  font-weight: 300;
  background: rgba(59, 130, 246, 0.15) !important;
  border-color: rgba(96, 165, 250, 0.4);
}
/* ================= 6. 侧边栏与骨架屏 ================= */
.sidebar-right {
  position: sticky;        /* ✨ 核心：开启吸顶悬浮 */
  top: 85px;               /* ✨ 核心：距离顶部保留导航栏的距离 */
  height: calc(100vh - 110px); /* ✨ 核心：锁死右侧高度，防止被撑长 */
  
  width: 280px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}
.widget, .sidebar-box { height: 380px; display: flex; flex-direction: column; overflow: hidden; }
.widget-header, .box-header { padding: 15px 20px; border-bottom: 1px solid var(--border-light); display: flex; justify-content: space-between; align-items: center; }
.widget-header h3, .box-title { margin: 0; font-size: 15px; font-weight: 800; }
.chat-window { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 12px; }
.chat-bubble { max-width: 85%; padding: 10px 14px; font-size: 13px; line-height: 1.5; background: rgba(0,0,0,0.05); border-radius: 16px 16px 16px 2px;}
.layout.dark-theme .chat-bubble { background: rgba(255,255,255,0.1); }
.chat-bubble.ai { align-self: flex-start; background: var(--primary-bright); color: #fff; border-radius: 4px 16px 16px 16px; }
.chat-input { display: flex; padding: 12px; border-top: 1px solid var(--border-light); }
.chat-input input { flex: 1; border: 1px solid var(--border-light); padding: 8px 12px; border-radius: 20px; background: transparent; color: var(--text-main); outline: none;}
.btn-send { margin-left: 10px; background: var(--primary); color: #fff; border: none; padding: 6px 16px; border-radius: 20px; font-weight: bold; cursor: pointer; }

/* 排行榜 */
.scroll-viewport { flex: 1; overflow: hidden; position: relative; mask-image: linear-gradient(to bottom, transparent, black 5%, black 95%, transparent); -webkit-mask-image: linear-gradient(to bottom, transparent, black 5%, black 95%, transparent); }
.scroll-track { display: flex; flex-direction: column; animation: seamlessScroll 15s linear infinite; }
.scroll-track:hover { animation-play-state: paused; }
@keyframes seamlessScroll { 0% { transform: translateY(0); } 100% { transform: translateY(-50%); } }
.trending-item { display: flex; align-items: center; padding: 12px 20px; gap: 12px; border-bottom: 1px solid rgba(0,0,0,0.05); text-decoration: none; color: var(--text-main); transition: 0.2s; }
.trending-item:hover { background: rgba(0,0,0,0.02); transform: translateX(4px); }
.rank-badge { width: 26px; height: 26px; border-radius: 8px; display: flex; justify-content: center; align-items: center; font-size: 13px; font-weight: 800; background: rgba(0,0,0,0.05); flex-shrink: 0; }
.rank-1 { background: linear-gradient(135deg, #fcd34d, #f59e0b); color: #fff; } 
.rank-2 { background: linear-gradient(135deg, #e2e8f0, #94a3b8); color: #fff; } 
.rank-3 { background: linear-gradient(135deg, #fdba74, #ea580c); color: #fff; }

/* 骨架屏 */
.skeleton-card { pointer-events: none; border-color: transparent !important; box-shadow: none !important;}
.skeleton-box { background: linear-gradient(90deg, rgba(255,255,255,0.1) 25%, rgba(255,255,255,0.3) 50%, rgba(255,255,255,0.1) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
.layout.dark-theme .skeleton-box { background: linear-gradient(90deg, rgba(0,0,0,0.1) 25%, rgba(0,0,0,0.3) 50%, rgba(0,0,0,0.1) 75%); background-size: 200% 100%; }
.skeleton-text { width: 60px; height: 14px; border-radius: 4px; margin-top: 4px; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* ================= 7. 轻提示与右键菜单 ================= */
.toast-message { position: fixed; top: 30px; left: 50%; transform: translateX(-50%); z-index: 999999; display: flex; align-items: center; gap: 8px; padding: 12px 24px; border-radius: 30px; font-size: 14px; font-weight: 600; }
.toast-message.success { border-bottom: 3px solid #10b981; }
.toast-message.error { border-bottom: 3px solid #ef4444; }
.toast-fade-enter-active, .toast-fade-leave-active { transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1); }
.toast-fade-enter-from, .toast-fade-leave-to { opacity: 0; transform: translate(-50%, -20px) scale(0.9); }

.context-menu { position: fixed; z-index: 999999; width: 150px; padding: 8px; }
.context-header { font-size: 11px; color: var(--text-muted); padding: 4px 10px 8px; border-bottom: 1px solid var(--border-light); margin-bottom: 4px; }
.context-item { padding: 10px; font-size: 13px; font-weight: 500; border-radius: 8px; cursor: pointer; transition: 0.2s; }
.context-item:hover { background: rgba(59, 130, 246, 0.1); color: var(--primary); }
.context-item.danger:hover { background: rgba(239, 68, 68, 0.15); color: #ef4444; }

/* ================= 8. 个人中心页 (Profile) ================= */
.profile-fullscreen-wrapper {
  flex: 1;
  width: 100%;
  background: rgba(255, 255, 255, 0.15) !important; /* 更透明的底层 */
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  display: flex;
  justify-content: center;
  padding: 40px 0;
}

/* 暗色模式适配保持不变 */
.layout.dark-theme .profile-fullscreen-wrapper { 
  background: rgba(15, 23, 42, 0.6) !important; 
}/* 1. 修复容器居中，并稍微收窄让排版更紧凑 */
.profile-inner-container {
  width: 90%;
  max-width: 800px;
  background: rgba(255, 255, 255, 0.6); /* 容器主色调 */
  backdrop-filter: blur(30px);
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 32px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.1);
  padding: 40px;
  display: flex;
  flex-direction: column;
}
/* 2. 优化标题区与返回按钮的对齐 */
.profile-header-section { 
  text-align: center; 
  margin-bottom: 40px; 
  position: relative; 
  display: flex; 
  flex-direction: column;
  align-items: center;
}

/* 2. 修复返回按钮：取消整体居中，直接与大标题顶部对齐 */
.nav-back-btn { 
  position: absolute; 
  left: 0; 
  top: 8px; /* ✨ 直接微调到和大标题处于同一水平线 */
  transform: none; /* 移除之前的垂直偏移 */
  background: transparent; 
  border: none; 
  color: var(--text-muted); 
  cursor: pointer; 
  font-size: 15px; 
  font-weight: 600; 
  transition: 0.3s;
}

.nav-back-btn:hover { 
  color: #3b82f6; 
  transform: translateX(-5px); /* 悬浮时向左微动，暗示返回 */
}
.main-title { font-size: 32px; color: var(--text-main); margin-bottom: 8px; font-weight: 800;}
.sub-title { color: var(--text-muted); font-size: 14px; }

.profile-cards-gap { display: flex; flex-direction: column; gap: 25px; }
.info-card-box { background: var(--bg-block); border-radius: 16px; border: 1px solid var(--border-light); overflow: hidden; backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); box-shadow: 0 10px 30px rgba(0,0,0,0.05);}
.card-head { padding: 25px; border-bottom: 1px solid var(--border-light); display: flex; flex-direction: column; gap: 5px; }
.card-head h2 { margin: 0; font-size: 18px; font-weight: 700;}
.card-head span { font-size: 13px; color: var(--text-muted); }

.clickable-row { display: flex; align-items: center; padding: 20px 25px; cursor: pointer; transition: 0.2s; border-bottom: 1px solid var(--border-light); }
.clickable-row:last-child { border-bottom: none; }
.clickable-row:hover { background: rgba(0,0,0,0.02); }
.layout.dark-theme .clickable-row:hover { background: rgba(255,255,255,0.05); }
.row-label { 
  width: 120px; /* ✨ 缩短标签宽度，给输入框腾出更多呼吸空间 */
  color: var(--text-muted); 
  font-size: 14px; 
  font-weight: 600; 
  flex-shrink: 0;
}

.row-content { 
  flex: 1; 
  display: flex; 
  align-items: center; 
}.row-arrow { color: var(--text-muted); font-family: monospace; font-size: 18px; }
.circle-avatar { width: 60px; height: 60px; border-radius: 50%; object-fit: cover; border: 1px solid var(--border-light); }

/* 3. 底部操作区：增加底部留白与按钮间距 */
.bottom-sticky-area {
  margin-top: 50px;
  display: flex;
  justify-content: flex-end;
  gap: 16px;
}
.logout-action-btn { padding: 12px 25px; border: 1px solid #ef4444; color: #ef4444; background: transparent; border-radius: 10px; cursor: pointer; font-weight: bold; transition: 0.3s; }
.logout-action-btn:hover { background: #fef2f2; }
.layout.dark-theme .logout-action-btn:hover { background: #450a0a; }

/* ================= 9. 极致打磨：弹窗公共样式 (登录/修改资料/添加) ================= */
.auth-overlay { 
  position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; 
  background: rgba(0, 0, 0, 0.35); /* ✨ 降低黑底浓度，让美丽的背景渐变透出来 */
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); /* 加强整体背景模糊 */
  display: flex; justify-content: center; align-items: center; z-index: 100000;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 24px;
}

.auth-modal { 
  background: rgba(255, 255, 255, 0.85); /* ✨ 苹果风透亮毛玻璃材质 */
  backdrop-filter: blur(30px); -webkit-backdrop-filter: blur(30px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 25px 50px rgba(0,0,0,0.15); 
  padding: 2.5rem 2.2rem; 
  border-radius: 24px; 
  width: min(400px, calc(100vw - 32px));
  max-height: calc(100vh - 48px);
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable both-edges;
  position: relative; 
  color: var(--text-main); 
  animation: modalPop 0.4s cubic-bezier(0.34, 1.56, 0.64, 1); /* ✨ Q弹入场动画 */
}

.layout.dark-theme .auth-modal { 
  background: rgba(15, 23, 42, 0.8); 
  border-color: rgba(255, 255, 255, 0.1);
  box-shadow: 0 25px 50px rgba(0,0,0,0.5);
}

@keyframes modalPop {
  0% { transform: scale(0.92); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

.modal-title { font-size: 1.3rem; margin-bottom: 1.8rem; font-weight: 800; text-align: center; letter-spacing: 0.5px;}

/* ✨ 圆形悬浮关闭按钮 (带旋转动画) */
.close-btn { 
  position: absolute; top: 18px; right: 18px; 
  z-index: 3;
  width: 32px; height: 32px; 
  border-radius: 50%; 
  background: rgba(0,0,0,0.05); 
  border: none; color: var(--text-muted); 
  font-size: 18px; display: flex; justify-content: center; align-items: center; 
  cursor: pointer; transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.layout.dark-theme .close-btn { background: rgba(255,255,255,0.08); }
.close-btn:hover { 
  background: rgba(239, 68, 68, 0.15); color: #ef4444; 
  transform: scale(1.1) rotate(90deg); 
}

.vertical-layout { position: relative; z-index: 1; display: flex; flex-direction: column; gap: 16px; min-width: 0; }

/* 其他登录方式按钮 */
.method-btn { padding: 14px; background: rgba(0,0,0,0.03); border: 1px solid var(--border-light); border-radius: 12px; color: var(--text-main); cursor: pointer; font-weight: 600; transition: 0.3s; }
.layout.dark-theme .method-btn { background: rgba(255,255,255,0.05); }
.method-btn:hover { background: rgba(59, 130, 246, 0.08); border-color: #60a5fa; color: #3b82f6;}

/* ✨ 高级感输入框 (内嵌阴影 + 柔和高光边框) */
.auth-input { 
  background: #f1f5f9; 
  border: 1.5px solid transparent; 
  color: var(--text-main); 
  padding: 14px 16px; 
  border-radius: 12px; 
  width: 100%; 
  outline: none; 
  font-size: 15px; 
  transition: all 0.3s ease;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
}
.layout.dark-theme .auth-input { 
  background: rgba(0,0,0,0.3); 
  border-color: rgba(255,255,255,0.05); 
}
.auth-input:focus { 
  background: var(--bg-block); 
  border-color: #3b82f6; 
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.15); 
}

/* ✨ 具有呼吸感和浮雕效果的提交按钮 */
.btn-submit { 
  position: relative;
  z-index: 2;
  margin-top: 10px;
  background: linear-gradient(135deg, #3b82f6, #2563eb); 
  color: #fff; border: none; padding: 14px; border-radius: 12px; 
  font-weight: 600; cursor: pointer; font-size: 15px; letter-spacing: 1px;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);
}
.btn-submit:hover { 
  transform: translateY(-2px); 
  box-shadow: 0 8px 25px rgba(37, 99, 235, 0.4); 
  background: linear-gradient(135deg, #4f46e5, #2563eb); /* 悬浮时带一点流光紫 */
}
.btn-submit:active { transform: translateY(1px); box-shadow: 0 2px 10px rgba(37, 99, 235, 0.3); }

/* 验证码与底部链接 */
.verify-code-row { display: flex; gap: 10px; min-width: 0; }
.verify-code-row .auth-input { flex: 1 1 auto; min-width: 0; }
.get-code-btn { position: relative; z-index: 2; background: transparent; border: 1px solid #60a5fa; color: #3b82f6; border-radius: 12px; padding: 0 15px; cursor: pointer; white-space: nowrap; font-weight: 600; transition: 0.2s;}
.get-code-btn:hover { background: rgba(59, 130, 246, 0.1); }
.link-btn { position: relative; z-index: 2; background: transparent; border: none; color: var(--text-muted); cursor: pointer; font-size: 13px; margin-top: 10px; transition: 0.2s;}
.link-btn:hover { color: #3b82f6; text-decoration: underline; }
.modal-footer { position: relative; z-index: 2; margin-top: 25px; text-align: center; font-size: 12px; color: var(--text-muted); }
.modal-footer a { color: #3b82f6; text-decoration: none; font-weight: 600;}

@media (max-width: 768px) {
  .auth-overlay {
    align-items: flex-start;
    padding: 16px;
  }

  .auth-modal {
    width: min(100%, calc(100vw - 32px));
    max-height: calc(100dvh - 32px);
    padding: 24px 18px !important;
  }

  .engine-modal {
    width: min(100%, calc(100vw - 32px));
    padding: 24px 18px !important;
  }

  .verify-code-row {
    flex-direction: column;
    align-items: stretch;
  }
}

/* 修改资料专属布局优化 */
.edit-form-container { display: flex; flex-direction: column; gap: 20px; margin-top: 5px; }
.avatar-edit-section { display: flex; flex-direction: column; align-items: center; margin-bottom: 15px; }
.avatar-preview-wrapper { width: 88px; height: 88px; position: relative; border-radius: 50%; padding: 4px; background: linear-gradient(135deg, #3b82f6, #8b5cf6); transition: 0.3s; cursor: pointer;}
.avatar-preview-wrapper:hover { transform: scale(1.05) rotate(5deg); }
.avatar-img { width: 100%; height: 100%; border-radius: 50%; object-fit: cover; border: 3px solid var(--bg-block); background: var(--bg-main); }
.input-group { display: flex; flex-direction: column; gap: 8px; position: relative; }
textarea.auth-input { resize: none; line-height: 1.5; padding-bottom: 30px;}
.char-counter { position: absolute; bottom: 12px; right: 14px; font-size: 11px; color: var(--text-muted); pointer-events: none; }

/* ================= 10. 直接输入表单质感 (Inline Form) ================= */
.form-row {
  display: flex;
  align-items: center;
  padding: 24px 0; /* ✨ 核心：去掉左右 padding，让内容对齐容器边缘 */
  border-bottom: 1px solid rgba(0, 0, 0, 0.05); /* 极淡的分割线 */
}

.form-row:last-child {
  border-bottom: none;
}
.form-row.align-top { align-items: flex-start; }

.avatar-edit-row { display: flex; align-items: center; gap: 15px; }
.avatar-edit-row .inline-input { flex: 1; }

/* 优雅的内嵌输入框 */
.inline-input {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 14px;
  padding: 12px 18px;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.02);
  transition: all 0.3s ease;
}
/* 暗色模式的输入框适配 */
.layout.dark-theme .inline-input { 
  background: rgba(0, 0, 0, 0.2); 
  border-color: rgba(255, 255, 255, 0.05); 
}

.inline-input:focus {
  background: #fff;
  border-color: #3b82f6;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
}

textarea.inline-input { resize: none; line-height: 1.5; }

/* 保存按钮的流光质感 */
.save-action-btn {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  padding: 14px 32px;
  border-radius: 16px;
  font-weight: 700;
  box-shadow: 0 10px 20px rgba(37, 99, 235, 0.2);
  transition: 0.3s;
}

.save-action-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 15px 30px rgba(37, 99, 235, 0.3);
}
.logout-action-btn {
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.2);
  padding: 14px 24px;
  border-radius: 16px;
  font-weight: 600;
  transition: 0.3s;
}

.logout-action-btn:hover {
  background: #ef4444;
  color: white;
}
/* ================= 头像上传交互样式 ================= */
.hidden-file-input { display: none; }

/* 1. 让头像容器稍微变大一点，更有视觉重心 */
.avatar-upload-wrapper {
  position: relative;
  width: 68px; /* 稍微缩小一点，更精致 */
  height: 68px;
  border-radius: 50%;
  cursor: pointer;
  overflow: hidden;
  /* ✨ 这种双层边框感会让图片像嵌在玻璃里一样 */
  border: 3px solid rgba(255, 255, 255, 0.5); 
  box-shadow: 
    0 4px 12px rgba(0, 0, 0, 0.08),
    0 0 0 1px rgba(0, 0, 0, 0.02); /* 极细的轮廓线 */
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  background: var(--bg-block);
}

/* 3. 增强悬浮时的反馈 */
.avatar-upload-wrapper:hover {
  transform: scale(1.05);
  border-color: #3b82f6; /* 悬浮时边框变蓝 */
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.2);
}

.avatar-hover-mask {
  background: rgba(0, 0, 0, 0.4); /* 遮罩稍微变浅一点，透出底图 */
  backdrop-filter: blur(2px); /* 遮罩自带微弱模糊，更高级 */
}
.avatar-upload-wrapper:hover .avatar-hover-mask {
  opacity: 1;
}

/* 上传提示文字区 */
.upload-hint-col {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.upload-btn-text {
  background: transparent;
  border: 1px solid var(--border-light);
  padding: 6px 12px;
  border-radius: 6px;
  color: var(--text-main);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  align-self: flex-start;
  transition: 0.2s;
}
.upload-btn-text:hover {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  border-color: #60a5fa;
}
.upload-hint {
  font-size: 12px;
  color: var(--text-muted);
}
/* ================= 13. 空状态 (Empty State) ================= */
.empty-state-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(10px);
  border-radius: 24px;
  border: 1px dashed var(--border-light);
  margin-top: 20px;
  text-align: center;
  animation: modalPop 0.4s ease;
}

.layout.dark-theme .empty-state-container {
  background: rgba(15, 23, 42, 0.3);
}

.empty-icon {
  font-size: 56px;
  margin-bottom: 16px;
  opacity: 0.8;
  filter: drop-shadow(0 10px 15px rgba(0,0,0,0.1));
  animation: float 3s ease-in-out infinite;
}

.empty-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0 0 8px 0;
}

.empty-desc {
  font-size: 14px;
  color: var(--text-muted);
  margin-bottom: 24px;
}

@keyframes float {
  0% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
  100% { transform: translateY(0px); }
}
/* ================= 14. 个性化背景弹窗 ================= */
.bg-options-container { display: flex; flex-direction: column; gap: 24px; }
.bg-section h4 { margin: 0 0 12px 0; font-size: 14px; font-weight: 700; color: var(--text-muted); display: flex; align-items: center; gap: 6px;}

/* 纯色选择器 */
.color-picker-wrapper { display: flex; align-items: center; gap: 15px; padding: 12px 16px; border-radius: 16px; border: 1px solid var(--border-light); }
.native-color-picker { width: 50px; height: 35px; border: none; border-radius: 8px; cursor: pointer; outline: none; padding: 0; background: transparent; transition: 0.2s;}
.native-color-picker:hover { transform: scale(1.05); }
.native-color-picker::-webkit-color-swatch-wrapper { padding: 0; }
.native-color-picker::-webkit-color-swatch { border: 2px solid rgba(255,255,255,0.4); border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }

/* 渐变色色块网格 */
.gradient-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.gradient-swatch { height: 50px; border-radius: 14px; cursor: pointer; border: 2px solid transparent; transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); box-shadow: 0 4px 10px rgba(0,0,0,0.08); }
.gradient-swatch:hover { transform: translateY(-4px) scale(1.05); box-shadow: 0 8px 20px rgba(0,0,0,0.15); }
.gradient-swatch.is-active { border-color: var(--text-main); transform: scale(1.05); box-shadow: 0 0 0 3px rgba(255,255,255,0.4); }

.w-full { width: 100%; display: flex; justify-content: center;}

/* ================= 15. 极限环境文字可读性保障 ================= */
/* 白天模式下：给文字加上极淡的白色发光，防止在杂乱浅色图片上看不清黑字 */
.logo span, .prof-name, .theme-toggle, .main-title {
  text-shadow: 0 2px 10px rgba(255, 255, 255, 0.8), 
               0 0 4px rgba(255, 255, 255, 0.5);
  transition: text-shadow 0.4s ease, color 0.4s ease;
}

/* 夜间模式下：给文字加上深色投影，保证白字在任何发光背景下都锐利可见 */
.layout.dark-theme .logo span, 
.layout.dark-theme .prof-name, 
.layout.dark-theme .theme-toggle,
.layout.dark-theme .main-title {
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.8),
               0 0 15px rgba(59, 130, 246, 0.4); /* 保留一点点科技蓝晕 */
}
/* ================= 16. 全局文字色彩与动画强制接管 ================= */

/* 1. 给根基注入灵魂：确保所有后代元素默认继承当前主题色 */
.layout {
  color: var(--text-main);
  overflow-x: hidden;
}

/* 2. 赋予页面所有常见标签“丝滑变色”的超能力 */
h1, h2, h3, h4, p, span, a, div, button, input, textarea, select {
  transition: color 0.4s cubic-bezier(0.4, 0, 0.2, 1), 
              text-shadow 0.4s ease, 
              background-color 0.4s ease, 
              border-color 0.4s ease, 
              box-shadow 0.4s ease;
}

/* 3. 查漏补缺：强制将所有游离的文本绑定到智能 CSS 变量 */
/* [主色调文字] - 标题、名称、重要选项 */
.logo span, .prof-name, .item-name, .nav-tab-box, .widget-header h3, 
.box-title, .main-title, .empty-title, .card-head h2, .site-name, 
.engine-radio-label, .dropdown-item, .trending-item, .modal-title, .row-label {
  color: var(--text-main) !important;
}

/* [辅助色文字] - 占位符、副标题、说明文本 */
.box-subtitle, .sub-title, .empty-desc, .upload-hint, .card-head span, 
.char-counter, .prof-arrow, .engine-name, .context-header {
  color: var(--text-muted) !important;
}

/* 4. 输入框与占位符专属修复 */
.search-box input, .auth-input, .inline-input {
  color: var(--text-main);
}
.search-box input::placeholder, .auth-input::placeholder, .inline-input::placeholder {
  color: var(--text-muted);
  transition: color 0.4s ease;
}

/* 5. 修复弹窗 (Modal) 和下拉面板的底层颜色 */
.auth-modal, .prof-dropdown, .dropdown-menu, .context-menu {
  color: var(--text-main);
}

/* 6. 确保 AI 对话气泡（用户发送的）跟随昼夜变化 */
.chat-bubble:not(.ai) {
  color: var(--text-main);
}
/* ================= 17. 终极修复：AI 建议面板文字与底色脱节 ================= */

/* 1. 修复用户发送的聊天气泡 (平滑改变文字颜色和底色) */
.chat-bubble.user {
  color: var(--text-main) !important;
  transition: color 0.4s cubic-bezier(0.4, 0, 0.2, 1), 
              background-color 0.4s ease !important;
}

/* 昼夜模式下，用户气泡底色的平滑切换 */
.layout:not(.dark-theme) .chat-bubble.user {
  background: rgba(0, 0, 0, 0.06) !important;
}
.layout.dark-theme .chat-bubble.user {
  background: rgba(255, 255, 255, 0.1) !important;
}

/* 2. 修复 AI 机器人的气泡 */
/* 因为 AI 气泡是品牌蓝底色，所以文字锁死纯白最清晰，但加上平滑阴影防刺眼 */
.chat-bubble.ai {
  color: #ffffff !important;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.4s ease !important;
}

/* 3. 修复底部输入框正在敲击的文字 */
.chat-input input {
  color: var(--text-main) !important;
  background: transparent !important;
  transition: color 0.4s ease, border-color 0.4s ease !important;
}

/* 4. 修复输入框里的占位符 ("需要找什么网站？") */
.chat-input input::placeholder {
  color: var(--text-muted) !important;
  transition: color 0.4s ease !important;
}

/* 5. 修复发送按钮的过渡 */
.btn-send {
  transition: background-color 0.4s ease, transform 0.2s ease !important;
}
/* ================= 17. 终极修复：AI 建议面板完整护航样式 ================= */

/* 1. 强制找回 AI 机器人的蓝色渐变气泡 */
.chat-bubble.ai {
  align-self: flex-start !important;       /* 靠左显示 */
  background: linear-gradient(135deg, #60a5fa, #3b82f6) !important; /* 强制锁定高光蓝底色 */
  color: #ffffff !important;               /* 强制纯白文字 */
  border-radius: 4px 16px 16px 16px !important; /* 机器人气泡尾巴在左上角 */
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.15) !important; /* 保护文字不发虚 */
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25) !important; /* 增加高级弥散阴影 */
  border: none !important;
}

/* 2. 强制规范用户发送的气泡 (跟随昼夜模式自适应) */
.chat-bubble.user {
  align-self: flex-end !important;         /* 靠右显示 */
  background: rgba(0, 0, 0, 0.06) !important; /* 白天浅灰底 */
  color: var(--text-main) !important;      /* 文字跟随系统亮暗 */
  border-radius: 16px 16px 2px 16px !important; /* 用户气泡尾巴在右下角 */
  border: 1px solid var(--border-light) !important;
  transition: color 0.4s ease, background-color 0.4s ease !important;
}

/* 夜间模式下用户的气泡变深色 */
.layout.dark-theme .chat-bubble.user {
  background: rgba(255, 255, 255, 0.1) !important;
}

/* 3. 基础排版兜底，防止被其他样式挤扁 */
.chat-bubble {
  padding: 10px 14px !important;
  font-size: 13.5px !important;
  line-height: 1.6 !important;
  margin-bottom: 5px;
}

/* 4. 保护底部的输入框和占位符 */
.chat-input input {
  color: var(--text-main) !important;
  background: transparent !important;
}
.chat-input input::placeholder {
  color: var(--text-muted) !important;
  opacity: 0.8 !important;
}

/* 5. 保护发送按钮 */
.btn-send {
  background: linear-gradient(135deg, #60a5fa, #3b82f6) !important;
  color: #ffffff !important;
  box-shadow: 0 4px 10px rgba(59, 130, 246, 0.2) !important;
}
/* ================= 18. 终极修复：保护“免费注册”等主按钮不被隐身 ================= */
.auth-group .btn-primary {
  background: linear-gradient(135deg, #60a5fa, #3b82f6) !important; /* 强制锁定高亮蓝渐变 */
  color: #ffffff !important;               /* 强制纯白文字 */
  border: none !important;                 /* 清除多余边框 */
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important; /* 补充呼吸感发光阴影 */
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1) !important;      /* 防止白字在蓝底上发虚 */
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
}

.auth-group .btn-primary:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 18px rgba(59, 130, 246, 0.45) !important; /* 悬浮时光晕放大 */
}

/* 顺手保护一下旁边的“登录”按钮，确保它也有清晰的轮廓 */
.auth-group .pill-btn {
  color: var(--text-main) !important;
  border: 1px solid var(--border-light) !important;
  background: rgba(128, 128, 128, 0.05) !important;
}
.auth-group .pill-btn:hover {
  background: rgba(128, 128, 128, 0.1) !important;
}
/* ================= 19. 终极修复：保护“搜索”及核心提交按钮不被隐身 ================= */
.search-btn-oval, .btn-submit, .save-action-btn {
  background: linear-gradient(135deg, #60a5fa, #3b82f6) !important; /* 强制锁定品牌蓝渐变 */
  color: #ffffff !important;               /* 强制纯白文字 */
  border: none !important;                 /* 清除多余边框 */
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2) !important;  /* 恢复按钮的光晕阴影 */
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1) !important;      /* 防止白字发虚 */
  font-weight: 600 !important;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
}

/* 悬浮时的放大与发光效果 */
.search-btn-oval:hover, .btn-submit:hover, .save-action-btn:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 18px rgba(59, 130, 246, 0.4) !important;
}
/* ================= 20. 终极修复：全局接管所有主操作按钮 (btn-primary) ================= */
/* 去掉之前的 .auth-group 限制，让页面里所有的 btn-primary 都满血复活 */
.btn-primary {
  background: linear-gradient(135deg, #60a5fa, #3b82f6) !important; /* 强制锁定高亮蓝渐变 */
  color: #ffffff !important;               /* 强制纯白文字 */
  border: none !important;                 /* 清除多余边框 */
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important; /* 补充呼吸感发光阴影 */
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1) !important;      /* 防止白字发虚 */
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
}

.btn-primary:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 18px rgba(59, 130, 246, 0.45) !important; /* 悬浮时光晕放大 */
}

/* 1. 全局大框架修改（假设你的外层容器叫 .main-layout 或 .container） */
.main-layout {
  display: flex;
  gap: 20px;
}

/* 2. 搜索栏适配：占满宽度，高度至少 44px */
.search-container { /* 替换为你搜索框真正的类名 */
  width: 100%;
  max-width: 800px; /* 限制桌面端的最大宽度 */
  margin: 0 auto;
}

.search-input { /* 替换为 <input> 真正的类名 */
  width: 100%;
  min-height: 44px; /* 满足移动端手指触摸面积 */
  padding: 10px 20px;
  font-size: 1rem; /* 这里会跟随 html 的 rem 设置自动缩放 */
  border-radius: 22px;
}

/* 移动端排版重置 */
@media (max-width: 767px) {
  .main-layout {
    flex-direction: column; /* 手机端改为上下排列 */
  }
  
  /* 如果有右侧的排行榜或 AI 建议模块，让它们在手机上排在下面 */
  .sidebar-right { 
    order: 2; 
    width: 100%;
  }
  
  .content-center { 
    order: 1; 
    width: 100%;
  }
}
/* ================= 收藏功能专属样式 ================= */
.site-card {
  position: relative; /* 确保子元素 absolute 定位有效 */
}

/* 悬浮在卡片上时，显示或者高亮星星 */
.site-card:hover .favorite-btn {
  opacity: 1;
  transform: scale(1.1);
}

.favorite-btn {
  position: absolute;
  top: 8px;
  right: 10px;
  font-size: 18px;
  cursor: pointer;
  opacity: 0.2; /* 默认微弱显示，不喧宾夺主 */
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  z-index: 10;
  text-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* 如果已经是收藏状态（实心星），让它常亮 */
.favorite-btn:has(.star-solid) {
  opacity: 1;
}

.star-empty {
  color: var(--text-muted);
}
.star-solid {
  color: #fbbf24; /* 漂亮的琥珀金 */
  text-shadow: 0 0 10px rgba(251, 191, 36, 0.5); /* 发光特效 */
}

.favorite-btn:hover {
  transform: scale(1.3) !important; /* 点击时反馈放大 */
}

/* 个人中心的收藏列表特殊排版 */
.favorites-container {
  padding: 20px;
}
.empty-favorites {
  text-align: center;
  padding: 30px;
  color: var(--text-muted);
  font-size: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.favorite-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 15px;
}
.mini-fav-card {
  padding: 15px 10px;
  min-height: auto;
}
.mini-logo {
  width: 42px;
  height: 42px;
  border-radius: 12px;
}

/* 收藏夹标签专属样式 */
.nav-tab-box.fav-tab {
  color: #d97706; /* 暗金色 */
  background: rgba(245, 158, 11, 0.1); 
  border: 1px dashed rgba(245, 158, 11, 0.4);
}
.nav-tab-box.fav-tab:hover {
  background: rgba(245, 158, 11, 0.2);
}
.nav-tab-box.fav-tab.active {
  background: linear-gradient(135deg, #fcd34d, #fbbf24) !important;
  color: #fff !important;
  border: none;
  box-shadow: 0 4px 12px rgba(251, 191, 36, 0.3);
  text-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

.layout.dark-theme .nav-tab-box.fav-tab.active {
  background: linear-gradient(135deg, #d97706, #b45309) !important;
  box-shadow: 0 4px 12px rgba(217, 119, 6, 0.4);
}

/* ================= 搜索建议下拉框 ================= */
.search-dropdown {
  position: absolute;
  top: 110%; /* 悬浮在搜索框正下方 */
  left: 0;
  width: 100%;
  background: rgba(255, 255, 255, 0.85) !important;
  backdrop-filter: blur(25px);
  -webkit-backdrop-filter: blur(25px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  padding: 16px;
  z-index: 1000;
  box-shadow: 0 15px 40px rgba(0,0,0,0.1);
  text-align: left;
}
.layout.dark-theme .search-dropdown {
  background: rgba(15, 23, 42, 0.85) !important;
  border-color: rgba(255, 255, 255, 0.1);
  box-shadow: 0 15px 40px rgba(0,0,0,0.5);
}

.dropdown-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-muted);
  padding: 0 4px;
  font-weight: 600;
}

.clear-btn {
  cursor: pointer;
  transition: 0.2s;
}
.clear-btn:hover {
  color: #ef4444;
}

.history-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.history-tag {
  font-size: 13px;
  padding: 6px 14px;
  background: rgba(0,0,0,0.04);
  border: 1px solid rgba(0,0,0,0.02);
  border-radius: 15px;
  cursor: pointer;
  color: var(--text-main);
  transition: all 0.2s ease;
}
.layout.dark-theme .history-tag {
  background: rgba(255,255,255,0.05);
  border-color: rgba(255,255,255,0.02);
}
.history-tag:hover {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  border-color: #60a5fa;
  transform: translateY(-2px);
}

.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.suggestion-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 12px;
  cursor: pointer;
  transition: 0.2s;
  gap: 12px;
}
.suggestion-item:hover {
  background: rgba(59, 130, 246, 0.08); /* 统一用微光蓝作为悬浮色 */
}
.layout.dark-theme .suggestion-item:hover {
  background: rgba(96, 165, 250, 0.15);
}

.sugg-logo {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  object-fit: cover;
  background: #fff;
}

.sugg-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
}

.sugg-url {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: auto; /* 把 URL 推到最右边 */
  opacity: 0.6;
  max-width: 180px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.engine-sugg {
  color: #3b82f6;
}

/* 下拉菜单 Q 弹进场动画 */
.fade-slide-down-enter-active,
.fade-slide-down-leave-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.fade-slide-down-enter-from,
.fade-slide-down-leave-to {
  opacity: 0;
  transform: translateY(-15px) scale(0.98);
}

/* ================= 丝滑网格过渡动画 (TransitionGroup) ================= */
.site-grid {
  position: relative; /* 确保子元素 absolute 定位时不乱跑 */
}
/* 高亮样式：Meilisearch 默认会给命中的词加 <em> 标签 */
:deep(em) {
  font-style: normal;
  color: #3b82f6; /* 经典的品牌蓝 */
  font-weight: bold;
  background-color: rgba(59, 130, 246, 0.1);
  padding: 0 2px;
  border-radius: 2px;
}

.sugg-info {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* =========================================
   🌟 场景 1 & 2: 卡片网格 (Fade + Scale + 交错淡入)
   ========================================= */

/* 1. 基础过渡设置与交错延迟 */
.grid-move, /* 处理分类切换时的平滑位移（Vue 独有魔法） */
.grid-enter-active,
.grid-leave-active {
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
}

/* 🚀 交错淡入核心：利用模板里绑定的 --i 变量，索引越大的卡片动画越晚执行 */
.grid-enter-active {
  transition-delay: calc(var(--i) * 30ms); 
}

/* 2. 进入前和离开后的状态 (Fade + Scale) */
.grid-enter-from,
.grid-leave-to {
  opacity: 0;
  transform: scale(0.85); /* 初始缩小一点点 */
}

/* 3. 关键补丁：离开的元素需要脱离文档流，否则后面的卡片无法顺滑补位 */
.grid-leave-active {
  position: absolute; 
}


/* =========================================
   🌟 场景 3: 模态框 (中心放大弹出)
   ========================================= */

/* 背景遮罩的淡入淡出 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

/* 内容面板的弹性放大过渡 */
.modal-enter-active .modal-content,
.modal-leave-active .modal-content {
  transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); /* 带一点Q弹的曲线 */
}

/* 初始状态 */
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

/* 内容面板初始状态：缩小 */
.modal-enter-from .modal-content,
.modal-leave-to .modal-content {
  transform: scale(0.5);
}


/* =========================================
   🌟 场景 4: 通知消息 (右上角滑入)
   ========================================= */

/* 固定右上角容器 */
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
}

/* 吐司通知的过渡属性 */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55); /* 滑入时带一点回弹效果 */
}

/* 进场：从右侧屏幕外滑入 */
.toast-enter-from {
  opacity: 0;
  transform: translateX(120%); 
}

/* 退场：向上飘走并淡出（比向右退场更优雅） */
.toast-leave-to {
  opacity: 0;
  transform: translateY(-30px);
}
/* ================= 极简丝滑网格过渡 ================= */
/* 1. 基础过渡：速度极快，曲线柔和 */
.smooth-grid-move,
.smooth-grid-enter-active,
.smooth-grid-leave-active {
  transition: all 0.25s cubic-bezier(0.25, 0.8, 0.25, 1);
}

/* 2. 进入前/离开后：只做透明度和微微下沉 10px 的处理，不做缩放 */
.smooth-grid-enter-from,
.smooth-grid-leave-to {
  opacity: 0;
  transform: translateY(10px); 
}

/* 3. 让离开的元素瞬间脱离排版，新元素无缝顶上 */
.smooth-grid-leave-active {
  position: absolute;
  /* 离开时稍微加快一点，防止重叠残留 */
  transition-duration: 0.15s; 
}
/* ================= 进阶丝滑过渡 (Pro-Smooth) ================= */

/* 1. 处理位置移动：当其他卡片挪位时，平滑滑过去 */
.pro-smooth-move {
  transition: transform 0.4s cubic-bezier(0.23, 1, 0.32, 1);
}

/* 2. 进入动画：渐显 + 微微向上滑动 15px */
.pro-smooth-enter-active {
  transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
}

.pro-smooth-enter-from {
  opacity: 0;
  transform: translateY(15px);
}

/* 3. 离开动画：这是关键！不要位移，只做原地淡出，且时间减半 */
.pro-smooth-leave-active {
  transition: opacity 0.2s ease;
  /* 强制原地淡出，不给它乱跑的机会 */
  position: absolute; 
  pointer-events: none;
}

.pro-smooth-leave-to {
  opacity: 0;
}
/* ================= 分类标签扩展样式 ================= */
.nav-tab-box {
  display: flex;
  align-items: center;
  gap: 6px;
  position: relative;
  /* 允许拖拽的手型 */
  cursor: grab; 
}

.nav-tab-box:active {
  cursor: grabbing;
}

.cat-icon {
  font-size: 14px;       /* 缩小 Emoji 的视觉大小 */
  line-height: 1;
  display: inline-block;
  transform: translateY(-1px); /* 微调位置，让图标和文字视觉居中 */
}

/* 拖拽时的幽灵半透明状态 */
.dragging-tab {
  opacity: 0.4;
  border: 1px dashed #3b82f6;
}

/* 补充你代码结尾的弹窗按钮样式 */
.modal-actions { display: flex; justify-content: space-between; margin-top: 20px; }
.action-right { display: flex; gap: 10px; margin-left: auto; }
.btn-danger { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); padding: 8px 16px; border-radius: 8px; cursor: pointer; transition: 0.2s; }
.btn-danger:hover { background: #ef4444; color: white; }
.btn-cancel { background: transparent; border: 1px solid var(--border-light); color: var(--text-main); padding: 8px 16px; border-radius: 8px; cursor: pointer; transition: 0.2s; }
.btn-save { background: #3b82f6; color: white; border: none; padding: 8px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; transition: 0.2s; box-shadow: 0 4px 10px rgba(59, 130, 246, 0.3); }
.btn-save:hover { background: #2563eb; transform: translateY(-2px); }

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 9999; /* 🚀 确保这个数值足够大 */
  backdrop-filter: blur(4px); /* 增加一点模糊感显得更高级 */
}

.modal-content {
  background: var(--bg-card); /* 适配你的深色模式变量 */
  padding: 24px;
  border-radius: 16px;
  width: 350px;
  box-shadow: 0 20px 40px rgba(0,0,0,0.3);
}
/* ================= 分类齿轮与模态框按钮样式 ================= */
.nav-tab-box {
  display: flex;
  align-items: center;
  gap: 6px;
  position: relative;
}

/* 神奇的齿轮按钮：平时隐藏，悬浮浮现 */
.cat-edit-btn {
  background: none;
  border: none;
  cursor: pointer;
  opacity: 0;
  width: 0;
  overflow: hidden;
  transform: scale(0.5) rotate(-90deg);
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  padding: 0;
  color: var(--text-muted);
}

.nav-tab-box:hover .cat-edit-btn {
  opacity: 1;
  width: 20px;
  transform: scale(1) rotate(0deg);
  margin-left: 4px;
}

.cat-edit-btn:hover {
  filter: brightness(1.2);
  transform: scale(1.2) !important;
}

/* 弹窗里面的按钮 */
.modal-actions { display: flex; justify-content: space-between; margin-top: 20px; }
.action-right { display: flex; gap: 10px; margin-left: auto; }
.btn-danger { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); padding: 8px 16px; border-radius: 8px; cursor: pointer; transition: 0.2s; }
.btn-danger:hover { background: #ef4444; color: white; }
.btn-cancel { background: transparent; border: 1px solid var(--border-light); color: var(--text-main); padding: 8px 16px; border-radius: 8px; cursor: pointer; transition: 0.2s; }
.add-category-btn {
  font-size: 12px;       /* 辅助按钮可以更小一点 */
  padding: 5px 12px;
  border: 1px dashed var(--border-light);
  opacity: 0.8;
}
/* ================= 藏宝图空状态 ================= */
.treasure-map-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
  margin: 20px auto;
  width: 100%;
  max-width: 700px;
  /* 羊皮纸底色与虚线边框 */
  background: #fdf8e4; 
  border: 2px dashed #d4b572;
  border-radius: 24px;
  position: relative;
  /* 用一点内发光制造陈旧感 */
  box-shadow: inset 0 0 40px rgba(212, 181, 114, 0.3);
  animation: modalPop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

/* 适配你的深色模式 */
.layout.dark-theme .treasure-map-empty {
  background: rgba(42, 36, 26, 0.8);
  border-color: #5c4e33;
  box-shadow: inset 0 0 40px rgba(0,0,0,0.5);
}

/* ================= 藏宝图标题与按钮区域 ================= */
.map-title-row {
  width: 100%;
  padding: 0 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  z-index: 2;
}

.map-title-row span {
  font-size: 16px;
  font-weight: bold;
  color: #8b6b33;
  letter-spacing: 1px;
}

.layout.dark-theme .map-title-row span {
  color: #d4b572;
}

/* 换一批按钮 */
.refresh-map-btn {
  background: rgba(212, 181, 114, 0.2);
  border: 1px dashed #d4b572;
  color: #8b6b33;
  padding: 6px 14px;
  border-radius: 20px; /* 圆润感 */
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  display: flex;
  align-items: center;
  gap: 4px;
}

.refresh-map-btn:hover {
  background: #d4b572;
  color: #fff;
  transform: translateY(-2px) rotate(2deg); /* 悬浮时微动感 */
  box-shadow: 0 4px 10px rgba(212, 181, 114, 0.4);
}

.layout.dark-theme .refresh-map-btn {
  background: rgba(92, 78, 51, 0.3);
  border-color: #5c4e33;
  color: #d4b572;
}

.layout.dark-theme .refresh-map-btn:hover {
  background: #5c4e33;
  color: #fff;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5);
}

.map-container {
  position: relative;
  width: 100%;
  max-width: 500px;
  height: 160px;
}

.map-path {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
  color: #d4b572; /* 航线的颜色 */
  opacity: 0.6;
  pointer-events: none;
}

.layout.dark-theme .map-path {
  color: #5c4e33;
}

/* 宝藏小岛动画与样式 */
.treasure-island {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  z-index: 2;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  /* 海浪般浮动动画 */
  animation: float-island 3s ease-in-out infinite;
}

.treasure-island:hover {
  animation-play-state: paused;
  transform: translateY(-8px) scale(1.15) !important;
}

/* ================= 宝藏小岛 Logo 样式 ================= */
.island-icon {
  display: flex;
  justify-content: center;
  align-items: center;
  transition: 0.3s;
}

/* 专门针对里面的 img 标签进行美化 */
.island-icon img {
  width: 48px;
  height: 48px;
  border-radius: 14px; /* 圆角矩形更契合现代 UI，如果想要纯圆可以改成 50% */
  background-color: #fff;
  padding: 4px; /* 留出一点白色内边距，像相框一样 */
  object-fit: contain;
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15); /* 加深投影，增强立体感 */
}

.treasure-island:hover .island-icon img {
  box-shadow: 0 10px 20px rgba(59, 130, 246, 0.3); /* 悬浮时发蓝光 */
}
.island-name {
  margin-top: 5px;
  font-size: 13px;
  font-weight: bold;
  color: #5c4e33;
  background: rgba(255, 255, 255, 0.9);
  padding: 4px 12px;
  border-radius: 20px;
  border: 1px dashed #d4b572;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.layout.dark-theme .island-name {
  color: #e4c482;
  background: rgba(30, 30, 30, 0.9);
  border-color: #5c4e33;
}

.add-badge {
  position: absolute;
  top: -5px;
  right: -10px;
  background: linear-gradient(135deg, #60a5fa, #3b82f6);
  color: white;
  border-radius: 50%;
  font-size: 12px;
  padding: 4px;
  opacity: 0;
  transform: scale(0.5);
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.4);
}

.treasure-island:hover .add-badge {
  opacity: 1;
  transform: scale(1);
}

/* 分配三个小岛的具体位置，制造交错感 */
.island-0 { top: 40px; left: 5%; animation-delay: 0s; }
.island-1 { top: 80px; left: 45%; animation-delay: 0.5s; }
.island-2 { top: 10px; left: 80%; animation-delay: 1s; }

/* 浮动关键帧 */
@keyframes float-island {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-12px); }
}
/* ================= 分类右键小窗口样式 ================= */
.custom-context-menu {
  position: fixed;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(0,0,0,0.08);
  box-shadow: 0 8px 24px rgba(0,0,0,0.15);
  border-radius: 10px;
  padding: 6px 0;
  min-width: 130px;
  z-index: 9999;
  transform-origin: top left;
}

.layout.dark-theme .custom-context-menu {
  background: rgba(40, 40, 40, 0.85);
  border-color: rgba(255,255,255,0.1);
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}

.context-menu-item {
  padding: 10px 16px;
  font-size: 13px;
  cursor: pointer;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s ease;
}

.context-menu-item:hover {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.context-menu-item.danger:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.context-menu-divider {
  height: 1px;
  background: rgba(0,0,0,0.06);
  margin: 4px 0;
}

.layout.dark-theme .context-menu-divider {
  background: rgba(255,255,255,0.06);
}

/* ================= 分类悬浮预览窗样式 ================= */
.category-hover-tooltip {
  position: fixed;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 12px;
  padding: 12px;
  width: 170px;
  z-index: 99999; /* 保证在最上层 */
  transform: translateX(-50%); /* 中心点对准鼠标 */
  pointer-events: none; /* ✨ 绝对核心：让鼠标穿透它，完全不影响你的左右拖拽操作 */
  box-shadow: 0 10px 30px rgba(0,0,0,0.12);
}

.layout.dark-theme .category-hover-tooltip {
  background: rgba(40, 40, 40, 0.85);
  border-color: rgba(255,255,255,0.1);
  box-shadow: 0 10px 30px rgba(0,0,0,0.6);
}

.tooltip-title {
  font-size: 12px;
  font-weight: bold;
  color: var(--text-secondary);
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px dashed rgba(0,0,0,0.1);
}

.layout.dark-theme .tooltip-title {
  border-bottom-color: rgba(255,255,255,0.1);
}

.tooltip-site-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tt-site-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tt-logo {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  background: #fff;
  padding: 1px;
}

.tt-name {
  font-size: 13px;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tt-more, .tt-empty {
  font-size: 12px;
  color: #94a3b8;
  text-align: center;
  margin-top: 8px;
}
/* 定义公转轨道动画 */
.orbit-planet {
  position: absolute;
  top: 0;
  left: 0;
  margin-top: -28px; 
  margin-left: -28px; 

  /* 🚀 1. 以后想改速度，只需修改这里的时间 (比如 30s, 40s) */
  --duration: 40s;
  animation: orbit var(--duration) linear infinite;

  /* ✨ 2. 终极自适应魔法：不管你时间改多少，星球数量有几个，这里会自动计算完美均分的角度！永远不乱！ */
  animation-delay: calc(-1 * var(--duration) / var(--total) * var(--delay));
}

/* 🚀 3. 以后想改轨道大小，只需修改这里的像素 (我已经帮你加到了 480px，绝对碰不到搜索框) */
@keyframes orbit {
  0% { transform: rotate(0deg) translateX(480px) rotate(0deg); }
  100% { transform: rotate(360deg) translateX(480px) rotate(-360deg); }
}

/* 鼠标悬浮时暂停公转 */
.orbit-planet:hover {
  animation-play-state: paused;
  z-index: 50;
}

/* 鼠标悬浮时暂停公转 */
.orbit-planet:hover {
  animation-play-state: paused;
  z-index: 50;
}

/* ✨ 专注模式下的全屏居中容器 */
.focus-center-wrapper {
  position: fixed !important; 
  top: 0;
  left: 0;
  width: 100vw !important;
  height: 100vh !important;
  max-width: none !important; /* 🚀 核心魔法：打破原有的 650px 最大宽度结界！ */
  display: flex !important;
  flex-direction: column;
  justify-content: center; 
  align-items: center;     
  z-index: 100;            
  margin: 0 !important;
  padding: 0 !important;
  pointer-events: none;    
}

.focus-center-wrapper .search-box {
  pointer-events: auto;    
  max-width: 650px !important; /* 🚀 确保外壳全屏后，内部的搜索框依然保持完美比例不被拉爆 */
}
/* 优化星球旋转中心 */
.focus-center-wrapper .orbit-planet {
  /* 在全屏居中模式下，确保旋转轴心依然是屏幕中心 */
  top: 50%;
  left: 50%;
}
/* ================= 专注模式：星球专属样式 ================= */

/* 星球的外层玻璃球容器 */
.planet-link {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;           /* 严格限制外圈大小 */
  height: 56px;
  border-radius: 50%;    /* 变成完美的圆形 */
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 0 15px rgba(255, 255, 255, 0.15);
  pointer-events: auto;  /* 恢复鼠标点击响应 */
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  text-decoration: none;
}

/* 鼠标悬浮时：玻璃球变大且发光 */
.planet-link:hover {
  transform: scale(1.15);
  background: rgba(255, 255, 255, 0.2);
  box-shadow: 0 0 25px rgba(255, 255, 255, 0.3);
}

/* 内部真实的 Logo 图片 */
.planet-logo {
  width: 32px;           /* 严格限制 Logo 本身的大小 */
  height: 32px;
  object-fit: contain;   /* 保证图片比例不被拉伸 */
  border-radius: 6px;    /* 稍微带一点圆角 */
  transition: transform 0.3s ease;
  background: transparent;
}

/* 鼠标悬浮时：里面的 Logo 跟着微微放大 */
.planet-link:hover .planet-logo {
  transform: scale(1.1);
}
/* ================= ✨ 专注模式：纯 CSS 终极修复版 ✨ ================= */

/* 专注模式遮罩：默认经典白，暗色模式自动变黑 */
.focus-dark-overlay {
  position: fixed;
  top: 0; left: 0; width: 100vw; height: 100vh;
  background: rgba(255, 255, 255, 0.9); /* ✨ 默认的经典白底 */
  backdrop-filter: blur(15px);
  -webkit-backdrop-filter: blur(15px);
  z-index: 5;
  transition: all 0.7s ease;
}
.layout.dark-theme .focus-dark-overlay {
  background: rgba(15, 23, 42, 0.85); /* 暗色模式时的深空黑 */
}
/* 2. 星系公转中心锚点：改为 fixed 确保绝对居中不受上下流影响 */
.orbit-center-container {
  position: fixed; 
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  z-index: 1; /* 保证在搜索框之下，遮罩之上 */
  pointer-events: none;
  transition: opacity 1s;
}

/* 3. 🚀 缩小公转轨道半径：调整到 360px，更紧凑精致 */
@keyframes orbit {
  0% { transform: rotate(0deg) translateX(250px) rotate(0deg); }
  100% { transform: rotate(360deg) translateX(250px) rotate(-360deg); }
}

.orbit-planet {
  position: absolute;
  top: 0; left: 0;
  margin-top: -24px; /* ✨ 匹配新尺寸 48px 的一半，保持绝对居中 */
  margin-left: -24px; 
  --duration: 40s;
  animation: orbit var(--duration) linear infinite;
  animation-delay: calc(-1 * var(--duration) / var(--total) * var(--delay));
}
/* 鼠标悬浮时，整个星系暂停运转 */
.orbit-planet:hover {
  animation-play-state: paused;
  z-index: 50;
}

/* 4. 星球的高级玻璃球外壳：缩小容器 (56px -> 48px) */
.planet-link {
  display: flex; align-items: center; justify-content: center;
  width: 50px; height: 50px; /* ✨ 容器减小 */
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.6); /* 白底专属的半透明毛玻璃 */
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 0, 0, 0.08); /* 极淡的灰边框勾勒轮廓 */
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05); /* 柔和清新的投影 */
  pointer-events: auto;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  text-decoration: none;
}
/* 暗色模式下恢复深色质感 */
.layout.dark-theme .planet-link {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.2);
}

/* 悬浮时的质感反馈 */
.planet-link:hover {
  transform: scale(1.15);
  background: rgba(255, 255, 255, 0.95);
  border-color: rgba(59, 130, 246, 0.5);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.15);
}

/* 5. 内部真实的 Logo 尺寸：缩小 (30px -> 24px) */
.planet-logo {
  width: 24px; /* ✨ Logo 变小，显得更小巧精致 */
  height: 24px;
  object-fit: contain; border-radius: 4px;
  transition: transform 0.3s ease; background: transparent;
}
.planet-link:hover .planet-logo {
  transform: scale(1.15);
}
.gradient-swatch-wrapper {
  position: relative;
}
.set-focus-bg-btn {
  position: absolute;
  top: -5px;
  right: -5px;
  background: white;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  font-size: 10px;
  border: 1px solid #eee;
  cursor: pointer;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}
.set-focus-bg-btn:hover {
  transform: scale(1.2);
  background: #f0f9ff;
}
.focus-site-item {
  display: flex;
  align-items: center;
  padding: 10px;
  background: rgba(0,0,0,0.03);
  border-radius: 10px;
  margin-bottom: 8px;
  gap: 12px;
}
.site-icon-preview {
  width: 36px;
  height: 36px;
  background: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.05);
}
.site-detail {
  flex: 1;
  overflow: hidden;
}
.site-name-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
}
.site-url-text {
  font-size: 11px;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.delete-site-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 5px;
  opacity: 0.5;
  transition: opacity 0.2s;
}
.delete-site-btn:hover {
  opacity: 1;
}
.focus-badge {
  position: absolute;
  top: 6px;
  right: 32px; /* 避开收藏星星的位置 */
  font-size: 12px;
  filter: drop-shadow(0 0 2px rgba(59, 130, 246, 0.5));
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(1); opacity: 0.7; }
  50% { transform: scale(1.2); opacity: 1; }
  100% { transform: scale(1); opacity: 0.7; }
}
/* ================= 🌌 极简空间粒子遮罩 ================= */
.space-particle-wrapper {
  position: fixed;
  inset: 0;
  background: #0f172a; 
  z-index: 99999;
}

/* 遮罩缓慢消失，时间拉长到 3 秒 */
.space-fade-leave-active {
  transition: opacity 3s cubic-bezier(0.25, 0.8, 0.25, 1);
}
.space-fade-leave-to {
  opacity: 0;
}

/* ================= 🌌 真实网页超慢速浮现 ================= */
/* 1. 隐藏阶段：全透明、强模糊、微微缩小 */
.intro-hidden .header-block,
.intro-hidden .search-section,
.intro-hidden .category-tabs-wrapper,
.intro-hidden .site-grid,
.intro-hidden .sidebar-right {
  opacity: 0 !important;
  filter: blur(15px);
  transform: scale(0.95);
}

/* 2. 显现阶段：用长达 3 秒的时间慢慢清晰，且带有错位延迟 */
.intro-revealing .header-block,
.intro-revealing .search-section,
.intro-revealing .category-tabs-wrapper,
.intro-revealing .site-grid,
.intro-revealing .sidebar-right {
  opacity: 1 !important;
  filter: blur(0);
  transform: scale(1);
  transition: all 3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

/* 给各个模块加上不同的延迟，产生“从上到下依次亮起”的优雅层次感 */
.intro-revealing .header-block { transition-delay: 0s; }
.intro-revealing .search-section { transition-delay: 0.2s; }
.intro-revealing .category-tabs-wrapper { transition-delay: 0.4s; }
.intro-revealing .site-grid { transition-delay: 0.6s; }
.intro-revealing .sidebar-right { transition-delay: 0.8s; }

/* ================= 📰 资讯看板样式 ================= */
.sidebar-right {
  width: 280px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
  /* 如果是在深色模式下 */
}
.dark-theme .sidebar-right {
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.news-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(0,0,0,0.05);
  padding-bottom: 10px;
}
.dark-theme .news-header { border-color: rgba(255,255,255,0.05); }

.refresh-news-btn {
  background: none; border: none; font-size: 18px; cursor: pointer; color: #64748b; transition: 0.3s;
}
.refresh-news-btn:hover { color: #3b82f6; }
.refresh-news-btn.spinning { animation: spin 1s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }

.news-list { display: flex; flex-direction: column; gap: 12px; }
.news-item {
  display: flex; align-items: flex-start; gap: 10px; text-decoration: none; color: inherit;
  padding: 8px; border-radius: 8px; transition: 0.2s;
}
.news-item:hover { background: rgba(59, 130, 246, 0.1); transform: translateX(5px); }

.news-dot {
  width: 6px; height: 6px; border-radius: 50%; background: #3b82f6; margin-top: 6px; flex-shrink: 0;
}
.news-title {
  font-size: 13px; line-height: 1.5; font-weight: 500;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.dark-theme .news-title { color: #e2e8f0; }

.news-meta { font-size: 11px; color: #94a3b8; margin-top: 4px; }

/* 骨架屏动画 */
.news-loading-skeleton { display: flex; flex-direction: column; gap: 15px; }
.skeleton-pulse { height: 40px; border-radius: 8px; background: rgba(0,0,0,0.05); animation: pulse 1.5s infinite; }
.dark-theme .skeleton-pulse { background: rgba(255,255,255,0.05); }

/* ================= 🚀 终极一屏排版：左侧滑动，右侧固定 ================= */

/* 1. 锁死全局网页，彻底消灭浏览器外层大滚动条 */
.layout {
  height: 100vh !important;
  min-height: 100vh !important;
  overflow: hidden !important;
}

/* 2. 中间大盒子必须限制高度，允许内部滑动 */
.main-container {
  flex: 1 !important;
  overflow: hidden !important;
  min-height: 0 !important; /* 关键魔法：允许 flex 子元素收缩 */
}

/* 3. 左侧网站卡片区：开启独立的内部丝滑滚动 */
.content {
  flex: 1 !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
  min-height: 0 !important;
  padding-right: 5px !important;
  scroll-behavior: smooth;
}

/* 4. 右侧边栏：解除原来 380px 的高度死锁，让 3 个模块弹性平分！ */
.sidebar-right {
  height: 100% !important;
  overflow: hidden !important;
}

.widget, .sidebar-box {
  height: auto !important;
  flex: 1 !important;
  min-height: 0 !important; /* 允许模块在高度不够时触发各自的内部滚动 */
}

/* 5. 附赠：苹果风透明悬浮滚动条，让内部滑动极其优雅 */
.content::-webkit-scrollbar,
.news-list-container::-webkit-scrollbar,
.scroll-viewport::-webkit-scrollbar,
.chat-window::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.content::-webkit-scrollbar-track,
.news-list-container::-webkit-scrollbar-track,
.scroll-viewport::-webkit-scrollbar-track,
.chat-window::-webkit-scrollbar-track {
  background: transparent;
}
.content::-webkit-scrollbar-thumb,
.news-list-container::-webkit-scrollbar-thumb,
.scroll-viewport::-webkit-scrollbar-thumb,
.chat-window::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.3);
  border-radius: 10px;
}
.content::-webkit-scrollbar-thumb:hover,
.news-list-container::-webkit-scrollbar-thumb:hover,
.scroll-viewport::-webkit-scrollbar-thumb:hover,
.chat-window::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.6);
}

/* 6. 修复卡片被压扁的问题：禁止网格被强行压缩 */
.site-grid {
  flex-shrink: 0 !important;       /* ✨ 核心：宁死不屈，绝对不许被压扁！ */
  height: max-content !important;  /* ✨ 核心：高度由里面的卡片数量真实决定 */
  padding-bottom: 40px !important; /* 底部留一点呼吸空间，滑到底才好看 */
}

/* 顺手给卡片加个基础高度保护 */
.site-card {
  min-height: 130px !important;
  flex-shrink: 0 !important;
}

/* ================= 🚀 终极打磨：搜索框固定，仅网站卡片区滚动 ================= */

/* 1. 收回中间大盒子的滚动权，让它变成纯粹的固定不变的框架 */
.content {
  overflow: hidden !important; 
}

/* 2. 保护搜索框和分类标签，绝对不许被压扁，稳稳固定在卡片上方 */
.search-section, 
.category-tabs-wrapper {
  flex-shrink: 0 !important;
  padding-bottom: 10px !important; /* 留出一点缝隙，别让卡片滚上来时贴得太死 */
}

/* 3. ✨ 见证奇迹：把滚动权全权移交给卡片网格自己！ */
.site-grid {
  flex: 1 !important;             /* 自动填满搜索框下方的所有剩余高度 */
  height: auto !important;        /* 解除之前的 max-content 限制 */
  overflow-y: auto !important;    /* ✨ 核心：全网页只有卡片在这里滑动 */
  overflow-x: hidden !important;
  align-content: start !important;/* 卡片数量少时，依然整齐地靠上对齐 */
  padding-right: 5px !important;  
  padding-bottom: 40px !important;
  scroll-behavior: smooth;
}

/* 4. 把刚才的高级透明滚动条，转移给网格区域 */
.site-grid::-webkit-scrollbar {
  width: 6px;
}
.site-grid::-webkit-scrollbar-track {
  background: transparent;
}
.site-grid::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.3);
  border-radius: 10px;
}
.site-grid::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.6);
}
.layout.dark-theme .site-grid::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
}
.layout.dark-theme .site-grid::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* ================= 🚀 视觉终极舒展：释放网格空间，修复滚动条悬空 ================= */

/* 1. 让左侧主容器“拥抱全屏”，不再强行把所有东西往中间挤 */
.content {
  align-items: stretch !important; 
  padding-right: 5px !important;
}

/* 2. 单独保护顶部的分类和搜索框，让它们依然保持完美的居中 */
.center-action-area {
  width: 100% !important;
  max-width: 900px !important;         /* 控制搜索区域的最佳阅读宽度 */
  margin: 0 auto 20px auto !important; /* 强制水平居中 */
}

/* 3. ✨ 彻底砸碎网格的宽度封印，让它像水一样填满左侧所有的空白！ */
.site-grid {
  max-width: none !important;     /* 核心：打破原来的 1000px 限制 */
  width: 100% !important;
  margin: 0 !important;
  padding-left: 10px !important;  
  padding-right: 15px !important; /* 让滚动条优雅地贴在最右侧边缘，不再悬空 */
}

/* 顺手把半透明滚动条再稍微优化一下，更加贴边和纤细 */
.site-grid::-webkit-scrollbar {
  width: 5px !important;
}

/* ================= 🚀 终极修复：消除 Vue 吞卡片 Bug，保证数量 100% 完整 ================= */

/* 1. 正常的入场和移动动画，保持丝滑 */
.fade-grid-move,
.fade-grid-enter-active {
  transition: all 0.35s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
}

.fade-grid-enter-from {
  opacity: 0 !important;
  transform: translateY(15px) scale(0.95) !important;
}

/* 2. ✨ 核心解药：绝对不能用 display: none！
   使用 transition: none 让 Vue 瞬间走完销毁流程，卡片绝对不会再被“吃掉”！ */
.fade-grid-leave-active {
  position: absolute !important; 
  opacity: 0 !important; 
  transition: none !important; /* 核心魔法：0毫秒瞬间安全退场，不留残影 */
  pointer-events: none !important;
}

.fade-grid-leave-to {
  opacity: 0 !important;
}

/* 3. 给网格容器加上“宽度金钟罩”，防止任何横向抖动 */
.site-grid {
  width: 100% !important;
  min-width: 100% !important;
  overflow-x: hidden !important; 
}

/* 4. 确保每张卡片死死撑满自己的格子，绝不妥协 */
.site-card {
  width: 100% !important;
  box-sizing: border-box !important;
}

.search-section { position: relative; }

/* 搜索结果高亮样式 */
.highlight {
  color: #3b82f6;
  font-weight: bold;
  background: rgba(59, 130, 246, 0.2);
}

/* 搜索建议浮层 */
.search-dropdown {
  position: absolute;
  top: 100%; left: 0; right: 0;
  background: var(--bg-glass);
  backdrop-filter: blur(15px);
  border-radius: 12px;
  max-height: 300px;
  overflow-y: auto;
  box-shadow: 0 10px 25px rgba(0,0,0,0.1);
  z-index: 100;
}

/* ================= 🚀 强制修复：提升职业选择器层级 ================= */

.header-block {
  /* 确保 header 本身具备足够的上下文 */
  position: relative !important;
  z-index: 20 !important; 
}

.profession-selector {
  position: relative !important;
  z-index: 100 !important; /* 必须高于 header 的 z-index */
  cursor: pointer !important;
  pointer-events: auto !important; /* 确保能响应点击 */
}

/* 确保下拉菜单不会被遮挡 */
.prof-dropdown {
  position: absolute !important;
  top: 100% !important;
  left: 0 !important;
  z-index: 1000 !important;
  background: white; /* 确保背景色不是透明，否则无法触发点击 */
}

/* 1. 分割线样式 */
.prof-divider {
  height: 1px;
  background: rgba(0, 0, 0, 0.05);
  margin: 5px 10px;
}

/* 2. 添加按钮的特殊样式 */
.add-prof-trigger {
  color: #3b82f6 !important; /* 给一个品牌色，突出可点击性 */
  font-weight: 600;
  transition: all 0.2s ease;
}

.add-prof-trigger:hover {
  background: rgba(59, 130, 246, 0.1) !important;
  cursor: pointer;
}
/* ================= 🎨 网站栏全透明/极简悬浮接管 ================= */

/* 1. 让网站卡片本身完全透明，移除遮挡的毛玻璃底色和阴影 */
.site-grid .site-card {
  background: transparent !important;          /* 彻底去掉白底，100% 透明 */
  backdrop-filter: none !important;            /* 关掉毛玻璃模糊，不遮挡壁纸角色 */
  -webkit-backdrop-filter: none !important;
  border: 1px solid transparent !important;    /* 隐去边框 */
  box-shadow: none !important;                 /* 隐去阴影 */
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
}

/* 2. 精致的悬浮（Hover）反馈：当鼠标放上去时，卡片再亮起微光 */
.site-grid .site-card:hover {
  background: rgba(255, 255, 255, 0.2) !important; /* 鼠标悬浮时呈现一层晶莹剔透的小果冻块 */
  border-color: rgba(255, 255, 255, 0.4) !important;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1) !important;
  transform: translateY(-6px) scale(1.05) !important; /* 保持原有的灵动浮动效果 */
}

/* 3. 暗色主题下的悬浮反馈适配 */
.layout.dark-theme .site-grid .site-card:hover {
  background: rgba(0, 0, 0, 0.3) !important;
  border-color: rgba(255, 255, 255, 0.1) !important;
}

/* 4. 优化文字可读性：给透明卡片下的文字加上清晰的微投影，防止遇到浅色壁纸时看不清字 */
.site-grid .site-name {
  color: #ffffff !important; /* 强制为白色或明亮色 */
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.8) !important; /* 浓郁的黑投影，确保在任何壁纸上字迹都绝对锐利 */
  font-weight: 700 !important;
}

/* 5. 顺手把“添加网站”虚线卡片也变透明 */
.site-grid .site-card.add-site-card {
  background: rgba(255, 255, 255, 0.05) !important;
  border: 2px dashed rgba(255, 255, 255, 0.4) !important;
}
.site-grid .site-card.add-site-card:hover {
  background: rgba(255, 255, 255, 0.2) !important;
  border-color: #ffffff !important;
}
/* ================= 🌌 智汇导航：全站极客纯净透明流接管 ================= */

/* 1. 顶栏全透明：移除白底与重度模糊，让壁纸延伸到最顶部 */
.header-block {
  background: transparent !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.15) !important;
  box-shadow: none !important;
}

/* 2. 右侧边栏主容器完全透明 */
.sidebar-right {
  background: transparent !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  box-shadow: none !important;
}

/* 3. 右侧三个小组件（排行、前沿、AI）全面剥离底色与边框 */
.sidebar-right .sidebar-box,
.sidebar-right .widget.ai-widget {
  background: transparent !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  border: none !important;
  box-shadow: none !important;
}

/* 4. 优化右侧组件的标题分割线：使其隐约可见，维持空间感 */
.sidebar-right .widget-header, 
.sidebar-right .box-header {
  border-bottom: 1px solid rgba(255, 255, 255, 0.2) !important;
  padding: 10px 0 !important; /* 稍微内缩，更精致 */
}

/* 5. 优化排行列表条目：去掉硬边框，改为悬浮时晶莹剔透的白润感 */
.sidebar-right .trending-item {
  border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
  transition: all 0.25s ease !important;
}
.sidebar-right .trending-item:hover {
  background: rgba(255, 255, 255, 0.15) !important;
  border-radius: 10px;
}

/* 6. AI 建议面板深度透明化适配 */
.sidebar-right .chat-window {
  background: transparent !important;
}
/* AI 底部输入框外壳透明化 */
.sidebar-right .chat-input {
  border-top: 1px solid rgba(255, 255, 255, 0.2) !important;
  background: transparent !important;
}
/* AI 真实的输入框框体改为精致微白透 */
.sidebar-right .chat-input input {
  background: rgba(255, 255, 255, 0.15) !important;
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
  backdrop-filter: blur(5px);
}

/* 7. 终极可读性防御：给全站所有暴露在壁纸上的文字强制加上清晰的阴影投影 */
.logo span,
.prof-name,
.nav-tab-box,
.box-title,
.box-subtitle,
.site-name,
.news-title,
.news-meta,
.widget-header h3 {
  color: #ffffff !important; /* 全局强制白字 */
  text-shadow: 0 2px 5px rgba(0, 0, 0, 0.7), 0 1px 2px rgba(0, 0, 0, 0.5) !important; /* 浓郁的黑投影 */
}

/* 分类 Tab 的高亮状态微调，使其在透明流中更醒目 */
.nav-tab-box.active {
  background: rgba(255, 255, 255, 0.25) !important;
  border: 1px solid rgba(255, 255, 255, 0.4) !important;
  text-shadow: none !important;
  color: #ffffff !important;
}

/* ================= 🌓 1. 全站文字智能色彩自适应与清晰度强化 ================= */
.layout.dark-theme .logo span,
.layout.dark-theme .prof-name,
.layout.dark-theme .nav-tab-box,
.layout.dark-theme .box-title,
.layout.dark-theme .box-subtitle,
.layout.dark-theme .site-name,
.layout.dark-theme .news-title,
.layout.dark-theme .news-meta,
.layout.dark-theme .widget-header h3,
.layout.dark-theme .trending-item,
.layout.dark-theme .chat-window {
  color: #ffffff !important;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.8), 0 1px 2px rgba(0, 0, 0, 0.5) !important;
}

.layout:not(.dark-theme) .logo span,
.layout:not(.dark-theme) .prof-name,
.layout:not(.dark-theme) .nav-tab-box,
.layout:not(.dark-theme) .box-title,
.layout:not(.dark-theme) .box-subtitle,
.layout:not(.dark-theme) .site-name,
.layout:not(.dark-theme) .news-title,
.layout:not(.dark-theme) .news-meta,
.layout:not(.dark-theme) .widget-header h3,
.layout:not(.dark-theme) .trending-item,
.layout:not(.dark-theme) .chat-window {
  color: #1a1a1a !important;
  text-shadow: 0 1px 3px rgba(255, 255, 255, 0.9), 0 0 1px rgba(255, 255, 255, 0.5) !important;
}

.layout.dark-theme .nav-tab-box.active {
  background: rgba(255, 255, 255, 0.25) !important;
  border: 1px solid rgba(255, 255, 255, 0.4) !important;
  color: #ffffff !important;
  text-shadow: none !important;
}

.layout:not(.dark-theme) .nav-tab-box.active {
  background: rgba(0, 0, 0, 0.08) !important;
  border: 1px solid rgba(0, 0, 0, 0.15) !important;
  color: #000000 !important;
  text-shadow: none !important;
}

.layout.dark-theme .prof-arrow { color: rgba(255, 255, 255, 0.7) !important; }
.layout:not(.dark-theme) .prof-arrow { color: rgba(0, 0, 0, 0.5) !important; }

/* ================= 🌌 2. 调色盘完全接管全局背景与卡片方案 ================= */
.layout {
  min-height: 100vh;
  background-color: #f8fafc; 
  background-size: cover;
  background-position: center;
  background-attachment: fixed;
  transition: background-color 0.4s cubic-bezier(0.4, 0, 0.2, 1),
              background-image 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

/* 浅色模式：全透明 */
.layout:not(.dark-theme) .header-block,
.layout:not(.dark-theme) .sidebar-right,
.layout:not(.dark-theme) .sidebar-right .sidebar-box,
.layout:not(.dark-theme) .sidebar-right .widget.ai-widget,
.layout:not(.dark-theme) .site-grid .site-card {
  background: transparent !important;          
  backdrop-filter: none !important;            
  -webkit-backdrop-filter: none !important;
  border: 1px solid transparent !important;    
  box-shadow: none !important;                 
}

/* 深色模式：高级黑透 */
.layout.dark-theme .header-block,
.layout.dark-theme .sidebar-right .sidebar-box,
.layout.dark-theme .sidebar-right .widget.ai-widget,
.layout.dark-theme .site-grid .site-card {
  background: rgba(15, 15, 15, 0.35) !important;  
  backdrop-filter: blur(20px) saturate(140%) !important; 
  -webkit-backdrop-filter: blur(20px) saturate(140%) !important;
  border: 1px solid rgba(255, 255, 255, 0.05) !important; 
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2) !important;  
}

/* 卡片悬浮交互 */
.layout:not(.dark-theme) .site-grid .site-card:hover {
  background: rgba(0, 0, 0, 0.04) !important;
  transform: translateY(-5px) scale(1.03) !important;
}

.layout.dark-theme .site-grid .site-card:hover {
  background: rgba(255, 255, 255, 0.08) !important; 
  border-color: rgba(255, 255, 255, 0.15) !important;
  transform: translateY(-5px) scale(1.03) !important;
}

/* ================= ⚙️ 3. 侧边栏及组件深度适配细节 ================= */
.layout.dark-theme .sidebar-right {
  background: transparent !important;
  box-shadow: none !important;
}

.layout.dark-theme .chat-window { background: transparent !important; }

.layout.dark-theme .chat-input { 
  border-top: 1px solid rgba(255, 255, 255, 0.06) !important; 
  background: transparent !important; 
}

.layout.dark-theme .chat-input input { 
  background: rgba(0, 0, 0, 0.4) !important; 
  border: 1px solid rgba(255, 255, 255, 0.06) !important; 
  color: #ffffff !important; 
}

/* “添加网站”虚线卡片 */
.layout:not(.dark-theme) .site-grid .site-card.add-site-card {
  border: 2px dashed rgba(0, 0, 0, 0.15) !important;
}
.layout.dark-theme .site-grid .site-card.add-site-card {
  border: 2px dashed rgba(255, 255, 255, 0.12) !important;
}

/* ================= 🌙 强制锁定深色模式为纯黑背景 ================= */

/* 当系统进入深色模式（.dark-theme）时，强行覆盖 inline 的调色盘样式 */
.layout.dark-theme {
  background-color: #000000 !important; /* 绝对纯黑，拒绝任何彩色 */
  background-image: none !important;    /* 彻底清除渐变色 */
}

/* 保持深色模式下卡片的高级“黑透”毛玻璃质感，在纯黑底色上悬浮 */
.layout.dark-theme .header-block,
.layout.dark-theme .sidebar-right .sidebar-box,
.layout.dark-theme .sidebar-right .widget.ai-widget,
.layout.dark-theme .site-grid .site-card {
  background: rgba(255, 255, 255, 0.03) !important; /* 极淡的微白透，在纯黑背景上像暗色玻璃 */
  backdrop-filter: blur(20px) saturate(140%) !important;
  -webkit-backdrop-filter: blur(20px) saturate(140%) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important; /* 精致的微光边框线 */
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.8) !important;   /* 深邃的阴影 */
}

/* ================= 🚀 终极滚动修复：打通 Flexbox 任督二脉 ================= */

/* 1. 防止主外壳被内部无数的卡片无限撑高 */
.main-container {
  min-height: 0 !important; 
}

/* 2. 限制内容区的高度，坚决不允许它超出屏幕 */
.content {
  display: flex !important;
  flex-direction: column !important;
  overflow: hidden !important; 
  min-height: 0 !important;       /* ✨ 核心魔法 1：防止 Flex 子元素撑破父容器 */
}

/* 3. 把真正的“自由滑动权”彻底移交给卡片网格自己 */
.site-grid {
  flex: 1 1 0% !important;        /* 强制网格只占用剩余的可用空间 */
  min-height: 0 !important;       /* ✨ 核心魔法 2：打破内容撑开限制，强行唤出内部滚动条！ */
  overflow-y: auto !important;    /* 开启垂直滑动 */
  overflow-x: hidden !important;
  align-content: flex-start !important; /* 确保卡片从最上面开始整齐排列 */
  padding-bottom: 80px !important; /* 底部留足留白空间，滑到底部才优雅 */
}

/* （可选）给右侧固定面板的滚动也加一层保护 */
.scroll-viewport, .chat-window {
  min-height: 0 !important;
}

/* ================= 🚀 右侧边栏二合一选项卡样式 (苹果胶囊版) ================= */

/* 1. 重新分配右侧比例：让上面选项卡占大头，AI 占小头 */
.sidebar-right .combined-box {
  flex: 1.3 !important; 
}
.sidebar-right .ai-widget {
  flex: 0.9 !important; 
}

/* 2. 选项卡标题头部 - 重构对齐方式 */
.tabs-header {
  padding-bottom: 12px !important;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.15) !important;
  display: flex;
  justify-content: center; /* ✨ 核心：大容器绝对居中 */
  align-items: center;
  width: 100%;
}

/* ✨ 3. 全新轨道：苹果风胶囊背景 */
.sidebar-tabs {
  display: flex;
  width: 100%; /* ✨ 核心：轨道撑满整个头部，完美对称 */
  background: rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  padding: 4px;
  gap: 4px;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
}
.layout.dark-theme .sidebar-tabs {
  background: rgba(255, 255, 255, 0.08);
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
}

/* ✨ 4. 选项卡按钮本身 (未选中状态) */
.tab-title {
  flex: 1; /* ✨ 核心：两个按钮等分 1:1 宽度 */
  display: flex;
  justify-content: center; /* ✨ 核心：文字绝对居中 */
  align-items: center;
  cursor: pointer;
  font-size: 13px !important;
  font-weight: 600 !important;
  padding: 8px 0 !important; /* 调整内边距，统一高度 */
  border-radius: 8px;
  opacity: 0.7;
  margin: 0;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
/* 悬浮时的微微亮起 */
.tab-title:hover {
  opacity: 0.9;
}

/* ✨ 5. 选项卡选中状态：化身凸起的果冻白块/发光块 */
.tab-title.active {
  opacity: 1;
  background: #ffffff; /* 白天模式：纯白凸起 */
  color: #2563eb !important; /* 文字变为高级蓝 */
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0,0,0,0.04);
  transform: translateY(-1px); /* 微微悬浮感 */
}
.layout.dark-theme .tab-title.active {
  background: rgba(255, 255, 255, 0.18); /* 夜间模式：晶莹剔透的高光块 */
  color: #ffffff !important;
  border: 1px solid rgba(255, 255, 255, 0.15);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3) !important;
}

/* 清除以前多余的下划线动画 */
.tab-title::after {
  display: none !important;
}

/* 6. 右侧小组件微调，确保不喧宾夺主 */
.tabs-header .box-subtitle {
  font-size: 11px;
  opacity: 0.7;
  font-weight: 500;
}
.tabs-header .refresh-news-btn {
  font-size: 16px;
  opacity: 0.8;
}

/* 7. 内容容器适配 */
.tab-content-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.tab-content-container > div {
  flex: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.news-list-container {
  overflow-y: auto;
  padding-right: 5px;
}

/* ================= 📊 排行榜真实数据空状态 ================= */
.empty-ranking-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 20px;
  opacity: 0.8;
  animation: modalPop 0.4s ease;
}

.empty-rank-icon {
  font-size: 32px;
  margin-bottom: 10px;
  filter: grayscale(100%);
  opacity: 0.5;
}

.empty-rank-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 4px;
}

.empty-rank-desc {
  font-size: 11px;
  color: var(--text-muted);
  text-align: center;
  line-height: 1.5;
}

/* ================= 🤖 终极优化：AI 建议面板专属样式 ================= */

/* 1. 对话记录展示区 */
.sidebar-right .chat-window {
  flex: 1;
  overflow-y: auto;
  padding: 12px 15px !important;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: transparent !important;
}

/* 2. 气泡基础防撑破设置 */
.chat-bubble {
  max-width: 90% !important; /* 给左右留点呼吸空间 */
  padding: 10px 14px !important;
  font-size: 13px !important;
  line-height: 1.6 !important;
  border-radius: 16px !important;
  word-break: break-word !important; /* ✨ 核心：防止长串英文字母或链接把气泡撑爆 */
  box-sizing: border-box !important;
}

/* 3. 底部输入控制台 (完美修复按钮被切掉的 Bug) */
.sidebar-right .chat-input {
  display: flex !important;
  align-items: center !important;
  gap: 10px !important; /* ✨ 用 gap 替代以前的 margin-left，完美控制间距 */
  padding: 12px 15px !important;
  border-top: 1px dashed rgba(0, 0, 0, 0.08) !important; /* 改为柔和的虚线分割 */
  background: transparent !important;
  box-sizing: border-box !important; /* ✨ 绝对防御：确保 padding 不会撑破宽度 */
  width: 100% !important;
}
.layout.dark-theme .chat-input {
  border-top-color: rgba(255, 255, 255, 0.08) !important;
}

/* 4. 输入框本体优化 */
.sidebar-right .chat-input input {
  flex: 1 !important;
  min-width: 0 !important; /* ✨ Flex 布局终极解药：防止输入框内容过长时强行撑开父容器 */
  border: 1px solid rgba(0, 0, 0, 0.1) !important;
  padding: 9px 14px !important;
  border-radius: 20px !important;
  background: rgba(0, 0, 0, 0.03) !important; /* 微微的灰底，增加层次 */
  color: var(--text-main) !important;
  font-size: 13px !important;
  outline: none !important;
  transition: all 0.3s ease !important;
  box-sizing: border-box !important;
}

.layout.dark-theme .chat-input input {
  background: rgba(255, 255, 255, 0.05) !important;
  border-color: rgba(255, 255, 255, 0.1) !important;
}

/* 聚焦时的发光效果 */
.sidebar-right .chat-input input:focus {
  border-color: #3b82f6 !important;
  background: transparent !important;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
}

/* 5. 发送按钮优化 (坚若磐石) */
.btn-send {
  flex-shrink: 0 !important; /* ✨ 核心：宁死不屈，绝对不允许被输入框挤扁！ */
  margin: 0 !important;      /* 抹除之前导致溢出的 margin */
  background: linear-gradient(135deg, #60a5fa, #3b82f6) !important;
  color: #fff !important;
  border: none !important;
  padding: 9px 16px !important;
  border-radius: 20px !important;
  font-size: 13px !important;
  font-weight: bold !important;
  cursor: pointer !important;
  white-space: nowrap !important; /* ✨ 核心：文字绝对不允许换行成上下排 */
  box-shadow: 0 4px 10px rgba(59, 130, 246, 0.2) !important;
  transition: all 0.2s ease !important;
}

.btn-send:hover:not(:disabled) {
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 15px rgba(59, 130, 246, 0.3) !important;
}

.btn-send:disabled {
  opacity: 0.6 !important;
  cursor: not-allowed !important;
  transform: none !important;
}

/* 直接粘贴在 style 结束标签的正上方 */
:deep(.ai-site-card) {
  transition: all 0.2s ease;
}
:deep(.ai-site-card:hover) {
  background: rgba(255, 255, 255, 0.15) !important;
  transform: translateY(-1px);
}
:deep(.ai-site-card a:hover) {
  text-decoration: underline !important;
  color: #93c5fd !important; /* 悬浮时变成更亮的浅蓝色 */
}

/* ================= 🚀 个人中心专属商业级 UI ================= */

.profile-layout-container {
  display: flex;
  width: 100%;
  max-width: 1100px; /* 限制超大屏宽度 */
  margin: 0 auto;
  height: calc(100vh - 120px);
  background: rgba(255, 255, 255, 0.6) !important;
  border-radius: 20px;
  overflow: hidden;
}

.layout.dark-theme .profile-layout-container {
  background: rgba(15, 23, 42, 0.6) !important;
}

/* --- 左侧边栏 --- */
.profile-sidebar {
  width: 240px;
  background: rgba(0, 0, 0, 0.03);
  border-right: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  padding: 20px;
  flex-shrink: 0;
}
.layout.dark-theme .profile-sidebar {
  background: rgba(255, 255, 255, 0.02);
}

.sidebar-header { margin-bottom: 20px; }
.sidebar-user-brief { display: flex; align-items: center; gap: 12px; margin-bottom: 30px; padding: 10px; background: rgba(255,255,255,0.4); border-radius: 12px;}
.layout.dark-theme .sidebar-user-brief { background: rgba(0,0,0,0.2); }
.brief-avatar { width: 44px; height: 44px; border-radius: 50%; object-fit: cover;}
.brief-info { display: flex; flex-direction: column;}
.brief-name { font-weight: 600; font-size: 14px; color: var(--text-main); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 120px;}
.brief-role { font-size: 11px; color: var(--text-muted); }

.sidebar-menu { display: flex; flex-direction: column; gap: 8px; flex: 1; }
.sidebar-menu a {
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 10px;
}
.sidebar-menu a:hover { background: rgba(0,0,0,0.05); color: var(--text-main); }
.sidebar-menu a.active { background: var(--primary-bright); color: #fff; font-weight: 600; box-shadow: 0 4px 10px rgba(59,130,246,0.3);}
.sidebar-footer { margin-top: auto; }

/* --- 右侧内容区 --- */
.profile-content-area {
  flex: 1;
  padding: 30px 40px;
  overflow-y: auto;
  position: relative;
}

.panel-title { font-size: 22px; font-weight: 800; margin-bottom: 30px; color: var(--text-main); }
.panel-actions { margin-top: 30px; padding-top: 20px; border-top: 1px dashed var(--border-light); display: flex; justify-content: flex-end; }
.animate-fade-in { animation: modalPop 0.3s ease-out; }

/* --- 面板 1：个人主页风格 --- */
.profile-cover { height: 160px; background: linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 100%); border-radius: 16px; margin-bottom: -50px; }
.homepage-header { display: flex; align-items: flex-end; gap: 20px; padding: 0 20px; margin-bottom: 30px; }
.homepage-avatar { width: 100px; height: 100px; border-radius: 50%; border: 4px solid var(--bg-block); box-shadow: 0 4px 12px rgba(0,0,0,0.1); object-fit: cover; background: #fff;}
.homepage-user-info { flex: 1; margin-bottom: 10px; }
.homepage-user-info h2 { margin: 0 0 5px 0; font-size: 24px; display: flex; align-items: center; gap: 10px;}
.gender-tag { font-size: 12px; padding: 2px 8px; background: rgba(0,0,0,0.05); border-radius: 12px; font-weight: normal; color: var(--text-muted);}
.homepage-bio { font-size: 13px; color: var(--text-muted); margin: 0 0 15px 0; }
.homepage-stats { display: flex; gap: 30px; }
.stat-item { display: flex; flex-direction: column; align-items: center; }
.stat-item strong { font-size: 18px; color: var(--text-main); }
.stat-item span { font-size: 12px; color: var(--text-muted); }

.homepage-content-tabs { display: flex; gap: 30px; border-bottom: 1px solid var(--border-light); margin-bottom: 20px;}
.homepage-content-tabs span { padding: 10px 0; font-weight: 600; color: var(--text-muted); cursor: pointer; position: relative;}
.homepage-content-tabs span.active { color: var(--primary); }
.homepage-content-tabs span.active::after { content: ''; position: absolute; bottom: -1px; left: 0; width: 100%; height: 3px; background: var(--primary); border-radius: 3px;}

/* --- 设置相关组件 (安全/隐私/内容) --- */
.security-list { display: flex; flex-direction: column; gap: 15px; }
.security-item { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; background: rgba(0,0,0,0.02); border-radius: 12px; border: 1px solid var(--border-light); }
.layout.dark-theme .security-item { background: rgba(255,255,255,0.02); }
.sec-info h3 { margin: 0 0 4px 0; font-size: 15px; color: var(--text-main); }
.sec-info p { margin: 0; font-size: 12px; color: var(--text-muted); }

/* Switch 开关样式 */
.switch { position: relative; display: inline-block; width: 46px; height: 24px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #cbd5e1; transition: .4s; border-radius: 24px; }
.slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}
input:checked + .slider { background-color: #3b82f6; }
input:checked + .slider:before { transform: translateX(22px); }

/* 设备管理 */
.device-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; }
.device-item { display: flex; align-items: center; gap: 15px; padding: 15px; background: rgba(0,0,0,0.02); border-radius: 12px; border: 1px solid var(--border-light); }
.dev-icon { font-size: 24px; }
.dev-detail { flex: 1; display: flex; flex-direction: column; }
.dev-name { font-size: 14px; font-weight: 600; color: var(--text-main); display: flex; align-items: center; gap: 8px;}
.dev-tag { font-size: 10px; padding: 2px 6px; background: #10b981; color: white; border-radius: 4px; font-weight: normal;}
.dev-meta { font-size: 11px; color: var(--text-muted); margin-top: 4px; }

/* 内容管理 & 足迹 */
.content-status-tabs { display: flex; gap: 15px; margin-bottom: 20px;}
.content-status-tabs span { padding: 6px 16px; border-radius: 20px; background: rgba(0,0,0,0.05); font-size: 13px; cursor: pointer; color: var(--text-muted); font-weight: 600;}
.content-status-tabs span.active { background: var(--text-main); color: var(--bg-block); }
.layout.dark-theme .content-status-tabs span.active { background: #fff; color: #000; }

.my-content-item { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; margin-bottom: 12px; }
.mc-info h4 { margin: 0 0 6px 0; font-size: 15px; color: var(--text-main); }
.mc-info p { margin: 0; font-size: 12px; color: var(--text-muted); }
.mc-actions { display: flex; gap: 10px; }

/* 时间轴 */
.history-timeline { padding-left: 10px; border-left: 2px solid var(--border-light); margin-left: 10px; }
.timeline-day { margin-bottom: 25px; position: relative;}
.day-title { margin: 0 0 15px -20px; font-size: 14px; background: var(--bg-main); display: inline-block; padding: 0 10px; color: var(--text-muted); font-weight: 600;}
.timeline-item { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; font-size: 13px; position: relative;}
.timeline-item::before { content: ''; position: absolute; left: -14px; top: 50%; transform: translateY(-50%); width: 6px; height: 6px; border-radius: 50%; background: #94a3b8; }
.tl-time { color: var(--text-muted); min-width: 40px;}
.tl-action { color: var(--text-muted); }
.tl-action.highlight { color: #ef4444; font-weight: 600;}
.tl-action.highlight-star { color: #f59e0b; font-weight: 600;}
.tl-target { color: var(--text-main); font-weight: 600; cursor: pointer; }
.tl-target:hover { color: var(--primary); text-decoration: underline; }

/* 基础按钮修复 */
.btn-cancel { background: rgba(0,0,0,0.05); border: none; padding: 6px 16px; border-radius: 8px; cursor: pointer; color: var(--text-main); font-weight: 600;}
.layout.dark-theme .btn-cancel { background: rgba(255,255,255,0.1); color: #fff;}
.btn-danger { background: #fef2f2; color: #ef4444; border: 1px solid #fecaca; padding: 8px 20px; border-radius: 8px; cursor: pointer; font-weight: bold;}
.btn-danger-text { background: transparent; color: #ef4444; border: none; cursor: pointer; font-weight: 600;}

/* ================= 🚀 UI 终极进化：毛玻璃、软阴影与科技感 ================= */

/* --- 1. 全局容器极客化改造 --- */
.profile-layout-container {
  border-radius: 24px !important; /* 更柔和的圆角 */
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.08), inset 0 1px 0 rgba(255,255,255,0.6) !important; /* 顶级软阴影 + 内置高光 */
  background: rgba(255, 255, 255, 0.65) !important;
  backdrop-filter: blur(25px) saturate(150%) !important;
  -webkit-backdrop-filter: blur(25px) saturate(150%) !important;
  border: 1px solid rgba(255, 255, 255, 0.8) !important;
}

.layout.dark-theme .profile-layout-container {
  background: rgba(15, 23, 42, 0.55) !important;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255,255,255,0.05) !important;
  border-color: rgba(255, 255, 255, 0.1) !important;
}

/* --- 2. 侧边栏科技感高亮指示器 --- */
.sidebar-menu a { border-left: 4px solid transparent; }
.sidebar-menu a.active {
  background: linear-gradient(90deg, rgba(59, 130, 246, 0.12) 0%, transparent 100%) !important;
  color: #3b82f6 !important;
  border-left: 4px solid #3b82f6; /* 科技感左侧高亮 */
  border-radius: 0 12px 12px 0 !important;
  box-shadow: none !important;
  font-weight: 700 !important;
}
.layout.dark-theme .sidebar-menu a.active {
  background: linear-gradient(90deg, rgba(96, 165, 250, 0.15), transparent) !important;
  color: #60a5fa !important;
  border-left-color: #60a5fa;
}

/* --- 3. 头部科技感横幅 --- */
.profile-banner-wrapper {
  position: relative;
  border-radius: 20px;
  overflow: hidden;
  margin-bottom: -60px; /* 缩进，让头像浮上来 */
  box-shadow: 0 10px 30px rgba(0,0,0,0.05);
}
.profile-cover {
  height: 220px;
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}
/* 科技感网格图层 */
.tech-pattern-bg::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background-image: 
    linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px);
  background-size: 30px 30px;
  opacity: 0.6;
}
.change-cover-btn {
  position: absolute;
  top: 20px;
  right: 20px;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  color: white;
  border: 1px solid rgba(255,255,255,0.2);
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  transition: 0.3s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.change-cover-btn:hover { background: rgba(0, 0, 0, 0.6); transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }

/* --- 4. 头像与状态指示器 --- */
.modern-header { position: relative; padding: 0 30px; z-index: 2; }
.avatar-container { position: relative; margin-right: 25px; flex-shrink: 0; }
.homepage-avatar {
  width: 130px; height: 130px;
  border-radius: 50%;
  border: 6px solid var(--bg-block);
  box-shadow: 0 12px 30px rgba(0,0,0,0.15);
  background: #fff;
  position: relative;
  z-index: 2;
}
/* 绿色在线圆点 */
.online-status-dot {
  position: absolute;
  bottom: 15px; right: 15px;
  width: 22px; height: 22px;
  background: #10b981;
  border: 4px solid var(--bg-block);
  border-radius: 50%;
  z-index: 3;
}

/* --- 5. 信息行与高级徽章 --- */
.name-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.name-row h2 { margin: 0; font-size: 26px; font-weight: 800; color: var(--text-main); }
.gender-tag { font-size: 12px; padding: 3px 12px; border-radius: 20px; font-weight: 600; display: flex; align-items: center; gap: 4px; border: 1px solid transparent; }
.gender-tag.female { background: #fdf2f8; color: #db2777; border-color: #fbcfe8; }
.gender-tag.male { background: #f0f9ff; color: #0284c7; border-color: #bae6fd; }
.gender-tag.secret { background: #f1f5f9; color: #475569; }
.pro-badge { background: linear-gradient(135deg, #f59e0b, #ef4444); color: white; padding: 3px 10px; border-radius: 8px; font-size: 11px; font-weight: 900; letter-spacing: 1px; box-shadow: 0 4px 10px rgba(239,68,68,0.3); }

/* --- 6. 现代横向数据统计栏 --- */
.modern-stats {
  display: inline-flex;
  gap: 30px;
  background: rgba(0,0,0,0.02);
  padding: 15px 30px;
  border-radius: 18px;
  border: 1px solid var(--border-light);
  margin-top: 5px;
}
.layout.dark-theme .modern-stats { background: rgba(255,255,255,0.02); }
.modern-stats .stat-item { flex-direction: row; align-items: center; gap: 8px; }
.stat-icon { font-size: 18px; opacity: 0.9; }
.modern-stats strong { font-size: 22px; color: var(--text-main); }
.modern-stats span { font-size: 13px; font-weight: 600; color: var(--text-muted); }

/* --- 7. 空白状态 CTA 创作卡片 --- */
.creation-cta-card {
  margin-top: 30px;
  padding: 50px 40px;
  text-align: center;
  background: linear-gradient(135deg, rgba(255,255,255,0.9), rgba(255,255,255,0.5)) !important;
  border: 2px dashed rgba(59, 130, 246, 0.3) !important;
  display: flex; flex-direction: column; align-items: center;
  border-radius: 24px;
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
  box-shadow: none !important;
}
.layout.dark-theme .creation-cta-card {
  background: linear-gradient(135deg, rgba(15,23,42,0.8), rgba(15,23,42,0.4)) !important;
  border-color: rgba(96,165,250,0.2) !important;
}
.creation-cta-card:hover {
  border-style: solid !important;
  border-color: rgba(59, 130, 246, 0.6) !important;
  box-shadow: 0 20px 50px rgba(59, 130, 246, 0.15) !important;
  transform: translateY(-5px);
}
.cta-icon-ring {
  width: 70px; height: 70px;
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 32px;
  margin-bottom: 20px;
  box-shadow: 0 0 0 12px rgba(59, 130, 246, 0.05);
  transition: 0.3s;
}
.creation-cta-card:hover .cta-icon-ring { transform: scale(1.1); background: rgba(59, 130, 246, 0.15); }
.creation-cta-card h3 { margin: 0 0 12px 0; font-size: 22px; color: var(--text-main); font-weight: 800; }
.creation-cta-card p { margin: 0 0 30px 0; font-size: 14px; color: var(--text-muted); max-width: 300px; line-height: 1.6; }

/* 创作工具按钮组 */
.cta-tools { display: flex; gap: 15px; }
.tool-btn {
  padding: 12px 24px;
  border-radius: 24px;
  border: 1px solid var(--border-light);
  background: var(--bg-block);
  color: var(--text-main);
  font-weight: 600; font-size: 14px;
  cursor: pointer;
  transition: 0.3s;
  display: flex; align-items: center; gap: 8px;
  box-shadow: 0 4px 15px rgba(0,0,0,0.03);
}
.tool-btn:hover { background: var(--primary-bright); color: white; border-color: transparent; transform: translateY(-3px); box-shadow: 0 8px 20px rgba(59,130,246,0.3); }

/* --- 8. 内容 Tabs 现代化升级 --- */
.modern-tabs { gap: 40px; padding-left: 10px; margin-top: 40px; border-bottom-width: 2px; }
.modern-tabs span { font-size: 16px; padding-bottom: 14px; transition: 0.3s; }
.modern-tabs span:hover { color: var(--primary); }
.modern-tabs span.active::after {
  height: 4px;
  border-radius: 4px 4px 0 0;
  background: linear-gradient(90deg, #60a5fa, #3b82f6);
  box-shadow: 0 -2px 10px rgba(59,130,246,0.5);
}

/* ================= 🚀 终极进化：Bento Grid (百宝箱网格) 布局 ================= */

/* --- 1. 网格系统核心 --- */
.bento-layout {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-auto-rows: minmax(140px, auto);
  gap: 20px;
  padding: 10px 0;
}

/* Bento 基础卡片质感 */
.bento-item {
  background: rgba(255, 255, 255, 0.65) !important;
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  border: 1px solid rgba(255, 255, 255, 0.8) !important;
  border-radius: 28px !important; /* 更大的苹果风圆角 */
  padding: 24px;
  display: flex;
  flex-direction: column;
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.6) !important;
}

.layout.dark-theme .bento-item {
  background: rgba(15, 23, 42, 0.5) !important;
  border-color: rgba(255, 255, 255, 0.08) !important;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
}

.bento-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 40px rgba(59, 130, 246, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.8) !important;
  border-color: rgba(59, 130, 246, 0.3) !important;
}
.layout.dark-theme .bento-item:hover {
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
  border-color: rgba(96, 165, 250, 0.3) !important;
}

/* --- 2. 空间分配规划 --- */
.bento-profile { grid-column: span 2; flex-direction: row; align-items: center; gap: 30px; }
.bento-stats { grid-column: span 1; justify-content: space-around; padding: 20px 24px; }
.bento-project { grid-column: span 2; grid-row: span 2; }
.bento-feed { grid-column: span 1; grid-row: span 2; }
.bento-lab { grid-column: span 3; }

/* 响应式降级策略 */
@media (max-width: 960px) {
  .bento-layout { grid-template-columns: 1fr; }
  .bento-profile, .bento-stats, .bento-project, .bento-feed, .bento-lab { grid-column: span 1; grid-row: auto; }
  .bento-profile { flex-direction: column; text-align: center; }
}

/* --- 3. 模块内部细节打磨 --- */
.bento-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.bento-header h3 { margin: 0; font-size: 18px; font-weight: 800; color: var(--text-main); }

/* 名片区 */
.bento-avatar { width: 110px; height: 110px; border-radius: 50%; border: 4px solid var(--bg-block); box-shadow: 0 8px 24px rgba(0,0,0,0.12); object-fit: cover;}
.uid-text { font-size: 12px; color: var(--text-muted); margin: 0 0 8px 0; font-family: monospace; }
.tech-stack-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 15px; }
.tech-tag { padding: 4px 12px; border-radius: 8px; font-size: 12px; font-weight: 600; border: 1px solid transparent; }
.tech-tag.vue { background: rgba(16, 185, 129, 0.1); color: #059669; border-color: rgba(16, 185, 129, 0.2); }
.tech-tag.flask { background: rgba(99, 102, 241, 0.1); color: #4f46e5; border-color: rgba(99, 102, 241, 0.2); }
.tech-tag.db { background: rgba(245, 158, 11, 0.1); color: #d97706; border-color: rgba(245, 158, 11, 0.2); }
.tech-tag.hardware { background: rgba(59, 130, 246, 0.1); color: #2563eb; border-color: rgba(59, 130, 246, 0.2); }

.layout.dark-theme .tech-tag.vue { color: #34d399; }
.layout.dark-theme .tech-tag.flask { color: #818cf8; }
.layout.dark-theme .tech-tag.db { color: #fbbf24; }
.layout.dark-theme .tech-tag.hardware { color: #60a5fa; }

/* 数据区 */
.stat-row { display: flex; align-items: center; gap: 15px; }
.stat-icon-wrapper { width: 44px; height: 44px; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
.stat-icon-wrapper.blue { background: rgba(59, 130, 246, 0.1); }
.stat-icon-wrapper.orange { background: rgba(245, 158, 11, 0.1); }
.stat-icon-wrapper.purple { background: rgba(168, 85, 247, 0.1); }
.stat-data { display: flex; flex-direction: column; }
.stat-data strong { font-size: 20px; color: var(--text-main); line-height: 1.2; }
.stat-data span { font-size: 12px; color: var(--text-muted); font-weight: 600; }

/* 项目与动态区 */
.project-cards-container { display: flex; flex-direction: column; gap: 15px; }
.proj-card { display: flex; gap: 16px; padding: 16px; background: rgba(0,0,0,0.03); border-radius: 16px; transition: 0.3s; border: 1px solid var(--border-light); }
.layout.dark-theme .proj-card { background: rgba(255,255,255,0.02); }
.proj-card:hover { background: rgba(59, 130, 246, 0.05); border-color: rgba(59, 130, 246, 0.2); transform: translateX(4px); }
.proj-icon { font-size: 32px; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.1)); }
.proj-details h4 { margin: 0 0 6px 0; font-size: 15px; color: var(--text-main); }
.proj-details p { margin: 0; font-size: 13px; color: var(--text-muted); line-height: 1.5; }

.mini-feed-list { display: flex; flex-direction: column; gap: 20px; position: relative; }
.mini-feed-list::before { content: ''; position: absolute; left: 5px; top: 10px; bottom: 10px; width: 2px; background: var(--border-light); }
.mini-feed-item { display: flex; gap: 15px; position: relative; }
.feed-dot { width: 12px; height: 12px; border-radius: 50%; background: #3b82f6; border: 3px solid var(--bg-block); position: relative; z-index: 2; flex-shrink: 0; margin-top: 4px; }
.feed-content p { margin: 0 0 8px 0; font-size: 13px; color: var(--text-main); line-height: 1.6; }
.feed-time { font-size: 11px; color: var(--text-muted); }
.btn-icon-only { background: transparent; border: none; cursor: pointer; opacity: 0.6; transition: 0.2s; }
.btn-icon-only:hover { opacity: 1; transform: scale(1.1); }

/* 实验室交互区 */
.lab-content { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px; }
.lab-text h3 { margin: 0 0 6px 0; color: var(--text-main); font-size: 18px; }
.lab-text p { margin: 0; color: var(--text-muted); font-size: 13px; }
.lab-btn { padding: 12px 28px; font-size: 14px; border-radius: 20px; box-shadow: 0 8px 20px rgba(59, 130, 246, 0.25); }

/* ✨ 弹窗背景毛玻璃效果 */
.glass-overlay {
  backdrop-filter: blur(4px);          /* 开启毛玻璃模糊 */
  -webkit-backdrop-filter: blur(4px);  /* 兼容 Safari */
  background-color: rgba(15, 23, 42, 0.4); /* 配色微调，使其更显高级感 */
}

/* ===== Reference-inspired navigation home redesign ===== */
.nav-topbar,
.nav-home-shell,
.nav-home-shell * { box-sizing: border-box; }

.nav-topbar {
  height: 88px;
  display: grid;
  grid-template-columns: 260px 1fr auto;
  align-items: center;
  gap: 24px;
  padding: 0 32px;
  margin: 8px 12px 0;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(208, 218, 235, 0.78);
  border-bottom-color: rgba(197, 209, 228, 0.9);
  border-radius: 18px 18px 0 0;
  box-shadow: 0 16px 44px rgba(71, 94, 132, 0.08);
  backdrop-filter: blur(18px);
}

.nav-brand { display: inline-flex; align-items: center; gap: 14px; color: #071636; font-size: 28px; font-weight: 800; letter-spacing: -0.03em; }
.nav-brand-mark { width: 38px; height: 38px; display: inline-grid; place-items: center; color: #2563eb; }
.nav-brand-mark svg { width: 100%; height: 100%; fill: none; stroke: currentColor; stroke-width: 2.4; stroke-linecap: round; stroke-linejoin: round; }
.nav-main-tabs { display: flex; justify-content: center; align-self: stretch; gap: 58px; }
.nav-main-tabs button { position: relative; border: 0; background: transparent; color: #111c35; font-size: 16px; font-weight: 700; padding: 0 4px; cursor: pointer; }
.nav-main-tabs button::after { content: ''; position: absolute; left: 50%; bottom: 0; width: 0; height: 4px; border-radius: 999px 999px 0 0; background: #2f70ff; transform: translateX(-50%); transition: width 0.22s ease; }
.nav-main-tabs button.is-active, .nav-main-tabs button:hover { color: #1763f6; }
.nav-main-tabs button.is-active::after, .nav-main-tabs button:hover::after { width: 58px; }
.nav-actions { display: flex; align-items: center; justify-content: flex-end; gap: 16px; }
.nav-icon-btn, .nav-login-btn, .nav-avatar-btn { border: 0; background: transparent; color: #071636; cursor: pointer; }
.nav-icon-btn { width: 34px; height: 34px; display: grid; place-items: center; font-size: 25px; line-height: 1; border-radius: 12px; }
.nav-icon-btn:hover { background: rgba(37, 99, 235, 0.08); }
.nav-login-btn, .nav-avatar-btn { display: inline-flex; align-items: center; gap: 10px; font-size: 15px; font-weight: 700; }
.nav-login-avatar, .nav-avatar-btn img { width: 40px; height: 40px; border-radius: 50%; background: radial-gradient(circle at 50% 32%, #f9fbff 0 18%, #95a9d7 19% 42%, #dfe7f7 43% 100%); box-shadow: inset 0 0 0 1px rgba(255,255,255,0.75); }
.nav-avatar-btn img { object-fit: cover; }
.nav-caret { color: #273653; font-size: 18px; }

.nav-home-shell {
  min-height: calc(100vh - 96px);
  display: grid;
  grid-template-columns: 184px minmax(620px, 1fr) 376px;
  grid-template-rows: 1fr auto;
  gap: 24px;
  padding: 24px 32px 22px;
  margin: 0 12px 8px;
  background: radial-gradient(circle at 50% 42%, rgba(209, 224, 255, 0.36), transparent 34%), linear-gradient(180deg, #f7faff 0%, #f4f7fc 100%);
  border: 1px solid rgba(208, 218, 235, 0.78);
  border-top: 0;
  border-radius: 0 0 18px 18px;
  color: #071636;
}

.nav-side, .nav-panel, .nav-section-card, .nav-hero-card { border: 1px solid rgba(213, 223, 239, 0.9); background: rgba(255, 255, 255, 0.76); box-shadow: 0 18px 50px rgba(52, 78, 122, 0.08); backdrop-filter: blur(18px); }
.nav-side { position: sticky; top: 112px; height: calc(100vh - 138px); min-height: 640px; display: flex; flex-direction: column; gap: 14px; padding: 14px 12px; border-radius: 18px; }
.nav-side-item { width: 100%; min-height: 52px; display: flex; align-items: center; gap: 16px; padding: 0 20px; border: 0; border-radius: 12px; background: transparent; color: #102344; font-size: 15px; font-weight: 700; cursor: pointer; transition: transform 0.2s ease, background 0.2s ease, color 0.2s ease; }
.nav-side-item:hover, .nav-side-item.is-active { background: rgba(241, 246, 255, 0.96); color: #2467ff; }
.nav-side-item:hover { transform: translateX(2px); }
.nav-side-icon { width: 24px; height: 24px; display: inline-grid; place-items: center; flex: 0 0 auto; }
.nav-side-icon svg { width: 24px; height: 24px; fill: none; stroke: currentColor; stroke-width: 2.1; stroke-linecap: round; stroke-linejoin: round; }
.nav-side-divider { height: 1px; margin: 20px 18px 4px; background: #dfe7f4; }
.nav-side-add { margin-top: 4px; color: #495d80; }
.nav-side-footer { margin-top: auto; padding: 12px 0 2px; color: #7889aa; font-size: 13px; }
.nav-home-main { min-width: 0; display: flex; flex-direction: column; gap: 20px; }

.nav-hero-card { position: relative; min-height: 330px; padding: 54px 52px 32px; border-radius: 18px; overflow: hidden; background: linear-gradient(107deg, rgba(255,255,255,0.94) 0%, rgba(247,250,255,0.92) 47%, rgba(226,235,255,0.88) 100%), radial-gradient(circle at 78% 24%, rgba(104, 139, 255, 0.2), transparent 28%); }
.nav-hero-card::before { content: ''; position: absolute; inset: 0; background-image: linear-gradient(90deg, rgba(255,255,255,0) 0 74%, rgba(90, 126, 205, 0.08) 75%, transparent 76%), linear-gradient(rgba(255,255,255,0) 0 74%, rgba(90, 126, 205, 0.08) 75%, transparent 76%); background-size: 58px 58px; opacity: 0.55; pointer-events: none; }
.nav-hero-copy { position: relative; z-index: 1; }
.nav-hero-copy h1 { margin: 0 0 12px; color: #06163a; font-size: clamp(36px, 4vw, 50px); line-height: 1; font-weight: 900; letter-spacing: -0.05em; }
.nav-hero-copy h1::after { content: '✦'; margin-left: 18px; color: #3475ff; font-size: 30px; vertical-align: 12px; }
.nav-hero-copy p { margin: 0; color: #506488; font-size: 17px; font-weight: 600; }
.nav-orbit-art { position: absolute; top: 12px; right: 54px; width: 380px; height: 185px; pointer-events: none; opacity: 0.92; }
.nav-orbit-core { position: absolute; top: 22px; right: 82px; width: 132px; height: 132px; border-radius: 50%; background: radial-gradient(circle at 38% 30%, #ffffff 0 10%, #eaf1ff 25%, #abc0ff 62%, #eff4ff 100%); box-shadow: inset -14px -18px 28px rgba(98, 126, 203, 0.22), 0 22px 48px rgba(93, 125, 198, 0.18); }
.nav-orbit-ring { position: absolute; top: 55px; right: 30px; width: 256px; height: 70px; border: 1px solid rgba(132, 156, 214, 0.38); border-radius: 50%; transform: rotate(-12deg); }
.nav-orbit-ring.ring-two { top: 42px; right: 4px; width: 306px; height: 96px; opacity: 0.42; }
.nav-orbit-dot { position: absolute; width: 15px; height: 15px; border-radius: 50%; background: radial-gradient(circle, #ffffff 0 20%, #89a5ff 55%, #dfe8ff 100%); box-shadow: 0 0 20px rgba(78, 112, 210, 0.32); }
.nav-orbit-dot.dot-one { top: 32px; right: 35px; }
.nav-orbit-dot.dot-two { top: 132px; right: 266px; width: 9px; height: 9px; }

.nav-search-wrap { position: relative; z-index: 2; width: min(100%, 920px); height: 82px; display: flex; align-items: center; gap: 18px; margin-top: 28px; padding: 8px 12px 8px 30px; border: 1px solid rgba(121, 157, 255, 0.46); border-radius: 999px; background: rgba(255,255,255,0.86); box-shadow: 0 18px 42px rgba(65, 101, 175, 0.12); transition: border-color 0.2s ease, box-shadow 0.2s ease; }
.nav-search-wrap:focus-within { border-color: rgba(63, 113, 255, 0.78); box-shadow: 0 22px 48px rgba(65, 101, 175, 0.18); }
.nav-search-icon { color: #102344; font-size: 36px; line-height: 1; }
.nav-search-wrap input { flex: 1; min-width: 0; border: 0; outline: none; background: transparent; color: #122244; font-size: 17px; font-weight: 600; }
.nav-search-wrap input::placeholder { color: #8b9ab7; }
.nav-search-submit { width: 58px; height: 58px; border: 0; border-radius: 50%; color: #fff; background: linear-gradient(135deg, #8d6bff 0%, #2f7bff 100%); box-shadow: 0 14px 26px rgba(59, 111, 255, 0.32); font-size: 34px; line-height: 1; cursor: pointer; transition: transform 0.18s ease, box-shadow 0.18s ease; }
.nav-search-submit:hover { transform: translateX(2px) scale(1.02); box-shadow: 0 18px 32px rgba(59, 111, 255, 0.38); }
.nav-search-dropdown { position: absolute; left: 34px; right: 34px; top: calc(100% + 12px); z-index: 20; display: flex; flex-direction: column; gap: 8px; padding: 12px; border: 1px solid #dfe7f4; border-radius: 18px; background: rgba(255,255,255,0.96); box-shadow: 0 24px 52px rgba(38, 62, 104, 0.16); }
.nav-search-suggestion, .nav-search-engine-row, .nav-history-chip { border: 0; background: transparent; cursor: pointer; }
.nav-search-suggestion { display: flex; align-items: center; gap: 12px; padding: 10px; border-radius: 12px; text-align: left; }
.nav-search-suggestion:hover, .nav-search-engine-row:hover, .nav-history-chip:hover { background: #f4f7ff; }
.nav-search-suggestion img { width: 28px; height: 28px; border-radius: 8px; }
.nav-search-suggestion span { display: grid; gap: 3px; }
.nav-search-suggestion strong { color: #14213e; font-size: 14px; }
.nav-search-suggestion small { color: #7a88a4; font-size: 12px; }
.nav-search-engine-row, .nav-history-chip { padding: 10px 12px; border-radius: 12px; color: #465a7d; font-size: 13px; text-align: left; }
.nav-hot-tags { position: relative; z-index: 1; display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin-top: 28px; color: #20304e; font-size: 14px; font-weight: 700; }
.nav-hot-tags button { min-height: 34px; padding: 0 18px; border: 1px solid #dce5f4; border-radius: 999px; background: rgba(255,255,255,0.7); color: #52627d; font-size: 14px; cursor: pointer; transition: transform 0.18s ease, background 0.18s ease; }
.nav-hot-tags button:hover { transform: translateY(-1px); background: #fff; }

.nav-section-card { padding: 20px; border-radius: 18px; }
.nav-section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.nav-section-head h2, .nav-panel-head h2 { margin: 0; color: #091936; font-size: 20px; font-weight: 850; letter-spacing: -0.02em; }
.nav-text-action, .nav-panel-head button { border: 0; background: transparent; color: #7483a0; font-size: 14px; cursor: pointer; }
.nav-feature-grid { display: grid; grid-template-columns: repeat(7, minmax(92px, 1fr)); gap: 18px; }
.nav-site-card { min-height: 138px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; border: 1px solid #e2e9f5; border-radius: 13px; background: rgba(255,255,255,0.82); color: #101f3d; cursor: pointer; box-shadow: 0 12px 28px rgba(72, 92, 128, 0.06); transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease; }
.nav-site-card:hover { transform: translateY(-4px); border-color: #c8d8f3; box-shadow: 0 18px 36px rgba(72, 92, 128, 0.11); }
.nav-site-logo { width: 46px; height: 46px; display: grid; place-items: center; }
.nav-site-logo img { width: 42px; height: 42px; object-fit: contain; border-radius: 12px; }
.nav-site-card strong { font-size: 15px; font-weight: 800; }
.nav-site-card small { width: 100%; max-width: 108px; overflow: hidden; color: #7586a5; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.nav-add-card { border-style: dashed; color: #7a8bab; background: rgba(255,255,255,0.42); }
.nav-add-sign { width: 48px; height: 48px; display: grid; place-items: center; color: #647796; font-size: 34px; font-weight: 300; }
.nav-recommend-card { position: relative; overflow: hidden; }
.nav-recommend-row { position: relative; display: grid; grid-template-columns: repeat(6, minmax(112px, 1fr)); gap: 16px; padding-right: 18px; }
.nav-recommend-item { min-height: 72px; display: flex; align-items: center; gap: 13px; padding: 10px 16px; border: 1px solid #e3eaf6; border-radius: 12px; background: rgba(255,255,255,0.86); color: #14213d; cursor: pointer; text-align: left; box-shadow: 0 10px 22px rgba(72, 92, 128, 0.05); transition: transform 0.18s ease, box-shadow 0.18s ease; }
.nav-recommend-item:hover { transform: translateY(-3px); box-shadow: 0 16px 28px rgba(72, 92, 128, 0.1); }
.nav-recommend-item img { width: 36px; height: 36px; flex: 0 0 auto; object-fit: contain; border-radius: 10px; }
.nav-recommend-item span { display: grid; gap: 3px; min-width: 0; }
.nav-recommend-item strong { overflow: hidden; font-size: 14px; font-weight: 800; text-overflow: ellipsis; white-space: nowrap; }
.nav-recommend-item small { overflow: hidden; color: #7e8daa; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.nav-circle-next { position: absolute; top: 50%; right: 0; width: 34px; height: 34px; border: 1px solid #dfe7f4; border-radius: 50%; background: rgba(255,255,255,0.94); color: #516384; font-size: 26px; transform: translateY(-50%); cursor: pointer; box-shadow: 0 10px 24px rgba(72, 92, 128, 0.12); }

.nav-info-rail { display: flex; flex-direction: column; gap: 16px; }
.nav-panel { padding: 22px; border-radius: 18px; }
.nav-panel-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
.nav-panel-head h2 span { display: inline-flex; align-items: center; height: 20px; margin-left: 6px; padding: 0 8px; border-radius: 999px; background: #edf3ff; color: #3475ff; font-size: 12px; font-weight: 800; vertical-align: middle; }
.nav-rank-list, .nav-recent-list { display: grid; gap: 14px; }
.nav-rank-row, .nav-recent-row { display: grid; align-items: center; gap: 10px; color: #12213f; text-decoration: none; }
.nav-rank-row { grid-template-columns: 22px 1fr auto 10px; }
.nav-rank-num { color: #64748b; font-size: 15px; font-weight: 800; }
.nav-rank-num.hot { color: #ff6a00; }
.nav-rank-row strong, .nav-recent-row strong { overflow: hidden; font-size: 14px; font-weight: 750; text-overflow: ellipsis; white-space: nowrap; }
.nav-rank-row small, .nav-recent-row small, .nav-recent-row span { color: #7889aa; font-size: 13px; }
.nav-fire { color: #ff4d2d; font-size: 10px; }
.nav-recent-row { grid-template-columns: 26px 52px 1fr auto 14px; }
.nav-recent-row img { width: 24px; height: 24px; object-fit: contain; border-radius: 7px; }
.nav-recent-row button { border: 0; background: transparent; color: #8b9ab7; cursor: pointer; }
.nav-ai-panel { position: relative; min-height: 185px; overflow: hidden; background: linear-gradient(135deg, rgba(255,255,255,0.94), rgba(226,237,255,0.9)); }
.nav-ai-panel p { position: relative; z-index: 1; margin: 0 0 20px; color: #162847; font-size: 15px; font-weight: 650; line-height: 1.7; }
.nav-ai-art { position: absolute; right: 28px; top: 42px; width: 120px; height: 96px; border-radius: 50%; background: radial-gradient(circle at 42% 36%, #ffffff 0 12%, #b9c9ff 32%, #4d83ff 72%, rgba(255,255,255,0.1) 73%); filter: drop-shadow(0 20px 26px rgba(61, 112, 220, 0.24)); opacity: 0.88; }
.nav-ai-art::before, .nav-ai-art::after { content: ''; position: absolute; inset: 32px -18px; border: 1px solid rgba(91, 126, 214, 0.36); border-radius: 50%; transform: rotate(-14deg); }
.nav-ai-art::after { inset: 38px -28px; opacity: 0.5; }
.nav-ai-input { position: relative; z-index: 1; height: 46px; display: flex; align-items: center; gap: 8px; padding: 5px 7px 5px 18px; border-radius: 999px; background: rgba(255,255,255,0.92); box-shadow: inset 0 0 0 1px rgba(220, 229, 245, 0.9), 0 12px 24px rgba(72, 92, 128, 0.08); }
.nav-ai-input input { flex: 1; min-width: 0; border: 0; outline: none; background: transparent; color: #132344; font-size: 13px; }
.nav-ai-input input::placeholder { color: #8fa0bd; }
.nav-ai-input button { width: 34px; height: 34px; border: 0; border-radius: 50%; background: #3174ff; color: #fff; font-size: 20px; cursor: pointer; }
.nav-home-footer { grid-column: 2 / 4; display: flex; align-items: center; justify-content: space-between; padding: 12px 6px 0; color: #6f80a0; font-size: 14px; }
.nav-home-footer span { color: #4d6591; letter-spacing: 0.24em; }
.nav-home-footer nav { display: flex; gap: 38px; }
.nav-home-footer a { color: #7b8cab; text-decoration: none; }

.layout.dark-theme .nav-topbar, .layout.dark-theme .nav-home-shell { background: #0e1628; color: #e7edf7; }
.layout.dark-theme .nav-home-shell { background: linear-gradient(180deg, #0e1628, #111a2c); }
.layout.dark-theme .nav-side, .layout.dark-theme .nav-panel, .layout.dark-theme .nav-section-card, .layout.dark-theme .nav-hero-card, .layout.dark-theme .nav-topbar { border-color: rgba(148, 163, 184, 0.18); background: rgba(17, 26, 44, 0.78); }

@media (max-width: 1280px) {
  .nav-home-shell { grid-template-columns: 160px minmax(0, 1fr); }
  .nav-info-rail { grid-column: 2; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .nav-feature-grid { grid-template-columns: repeat(4, minmax(100px, 1fr)); }
  .nav-recommend-row { grid-template-columns: repeat(3, minmax(150px, 1fr)); }
  .nav-home-footer { grid-column: 1 / -1; }
}

@media (max-width: 900px) {
  .nav-topbar { grid-template-columns: 1fr auto; height: auto; padding: 18px; }
  .nav-main-tabs { grid-column: 1 / -1; order: 3; justify-content: flex-start; gap: 28px; overflow-x: auto; }
  .nav-home-shell { grid-template-columns: 1fr; padding: 18px; }
  .nav-side { position: static; height: auto; min-height: 0; flex-direction: row; overflow-x: auto; }
  .nav-side-footer, .nav-side-divider { display: none; }
  .nav-side-item { min-width: 92px; justify-content: center; padding: 0 14px; }
  .nav-info-rail { grid-column: auto; grid-template-columns: 1fr; }
  .nav-hero-card { padding: 34px 24px 28px; }
  .nav-orbit-art { opacity: 0.42; right: -72px; }
  .nav-search-wrap { height: 68px; padding-left: 20px; }
  .nav-search-submit { width: 48px; height: 48px; }
  .nav-feature-grid { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
  .nav-recommend-row { grid-template-columns: 1fr; padding-right: 0; }
  .nav-circle-next { display: none; }
  .nav-home-footer { grid-column: auto; flex-direction: column; gap: 12px; }
}

/* ===== Monochrome motion UI override ===== */
.nav-topbar,
.nav-home-shell,
.nav-side,
.nav-panel,
.nav-section-card,
.nav-hero-card {
  color: var(--mono-text);
}

.nav-topbar {
  margin: 10px 10px 0;
  background: rgba(255, 255, 255, 0.78) !important;
  border: 1px solid var(--mono-border) !important;
  border-radius: 24px 24px 0 0;
  box-shadow: var(--mono-shadow-sm);
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  animation: mono-rise-in 0.6s var(--mono-ease);
}

.nav-brand {
  color: var(--mono-text);
  letter-spacing: -0.05em;
}

.nav-brand-mark {
  color: var(--mono-text) !important;
  background: #ffffff;
  border: 1px solid var(--mono-border);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.9);
}

.nav-brand-mark svg {
  stroke: currentColor;
}

.nav-main-tabs button {
  position: relative;
  color: var(--mono-muted) !important;
  background: transparent !important;
  border: 0 !important;
  transition: color 0.24s var(--mono-ease), transform 0.24s var(--mono-ease);
}

.nav-main-tabs button::after {
  content: "";
  position: absolute;
  left: 16%;
  right: 16%;
  bottom: -18px;
  height: 2px;
  border-radius: 999px;
  background: currentColor;
  transform: scaleX(0);
  transform-origin: center;
  transition: transform 0.28s var(--mono-ease);
}

.nav-main-tabs button:hover,
.nav-main-tabs button.is-active {
  color: var(--mono-text) !important;
  transform: translateY(-1px);
}

.nav-main-tabs button.is-active::after {
  transform: scaleX(1);
}

.nav-icon-btn,
.nav-login-btn,
.nav-avatar-btn {
  color: var(--mono-text) !important;
  background: rgba(255,255,255,0.64) !important;
  border: 1px solid var(--mono-border) !important;
  box-shadow: none !important;
}

.nav-icon-btn:hover,
.nav-login-btn:hover,
.nav-avatar-btn:hover {
  background: #ffffff !important;
  transform: translateY(-2px);
}

.nav-login-avatar {
  background: radial-gradient(circle at 50% 34%, #d9d9d4 0 20%, #9a9a94 21% 44%, #e7e7e3 45% 100%) !important;
  filter: grayscale(1);
}

.nav-home-shell {
  margin: 0 10px 10px;
  background:
    radial-gradient(circle at 82% 8%, rgba(17,17,17,0.055), transparent 26rem),
    linear-gradient(180deg, #fafaf8 0%, #f1f1ee 100%) !important;
  border: 1px solid var(--mono-border);
  border-top: 0;
  border-radius: 0 0 24px 24px;
  overflow: hidden;
}

.nav-home-shell::before {
  content: "";
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background:
    linear-gradient(90deg, transparent 0 82%, rgba(17,17,17,0.035) 83%, transparent 84%),
    linear-gradient(transparent 0 82%, rgba(17,17,17,0.035) 83%, transparent 84%);
  background-size: 64px 64px;
  opacity: 0.65;
  animation: nav-mono-drift 22s linear infinite;
}

.nav-side,
.nav-panel,
.nav-section-card,
.nav-hero-card {
  background: rgba(255,255,255,0.72) !important;
  border: 1px solid var(--mono-border) !important;
  box-shadow: var(--mono-shadow-sm) !important;
  backdrop-filter: blur(20px) saturate(145%);
  -webkit-backdrop-filter: blur(20px) saturate(145%);
}

.nav-side {
  animation: mono-rise-in 0.62s var(--mono-ease) both;
}

.nav-side-item {
  color: var(--mono-text-soft) !important;
  background: transparent !important;
  border: 1px solid transparent !important;
  transition: transform 0.24s var(--mono-ease), background 0.24s var(--mono-ease), border-color 0.24s var(--mono-ease), color 0.24s var(--mono-ease);
}

.nav-side-icon,
.nav-side-icon :deep(svg) {
  color: currentColor !important;
  stroke: currentColor !important;
}

.nav-side-item:hover,
.nav-side-item.is-active {
  color: #000000 !important;
  background: rgba(255,255,255,0.9) !important;
  border-color: var(--mono-border) !important;
  transform: translateX(3px);
}

.nav-side-item.is-active {
  box-shadow: inset 3px 0 0 #111111;
}

.nav-side-divider {
  background: var(--mono-border) !important;
}

.nav-side-footer,
.nav-home-footer,
.nav-home-footer a,
.nav-home-footer span {
  color: var(--mono-muted) !important;
}

.nav-hero-card {
  min-height: 326px;
  background:
    radial-gradient(circle at 78% 26%, rgba(0,0,0,0.08), transparent 15rem),
    linear-gradient(112deg, rgba(255,255,255,0.94), rgba(245,245,242,0.82)) !important;
  animation: mono-rise-in 0.68s var(--mono-ease) both;
}

.nav-hero-card::before {
  background-image:
    linear-gradient(90deg, transparent 0 74%, rgba(17,17,17,0.055) 75%, transparent 76%),
    linear-gradient(transparent 0 74%, rgba(17,17,17,0.045) 75%, transparent 76%) !important;
  animation: nav-mono-drift 24s linear infinite;
}

.nav-hero-card::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(115deg, transparent 0%, rgba(255,255,255,0.62) 42%, transparent 64%);
  transform: translateX(-120%);
  animation: nav-soft-sheen 8s var(--mono-ease) infinite;
}

.nav-hero-copy h1 {
  color: var(--mono-text) !important;
  letter-spacing: -0.07em;
}

.nav-hero-copy p,
.nav-hot-tags span,
.nav-section-head h2,
.nav-panel-head h2 {
  color: var(--mono-text-soft) !important;
}

.nav-orbit-art {
  opacity: 0.5 !important;
  filter: grayscale(1) contrast(1.05);
}

.nav-orbit-core {
  background: radial-gradient(circle at 38% 28%, #ffffff 0 12%, #e6e6e2 32%, #bdbdb7 66%, #f6f6f3 100%) !important;
  box-shadow: inset -14px -18px 28px rgba(0,0,0,0.12), 0 24px 54px rgba(0,0,0,0.12) !important;
  animation: nav-float 7s var(--mono-ease) infinite alternate;
}

.nav-orbit-ring,
.nav-orbit-dot,
.nav-ai-art::before,
.nav-ai-art::after {
  border-color: rgba(17,17,17,0.22) !important;
}

.nav-orbit-dot,
.nav-ai-art {
  background: #111111 !important;
  box-shadow: 0 8px 20px rgba(17,17,17,0.15) !important;
  animation: nav-float 5.5s var(--mono-ease) infinite alternate;
}

.nav-search-wrap {
  background: rgba(255,255,255,0.86) !important;
  border: 1px solid rgba(17,17,17,0.16) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.9), 0 20px 54px rgba(17,17,17,0.08) !important;
  transition: transform 0.28s var(--mono-ease), box-shadow 0.28s var(--mono-ease), border-color 0.28s var(--mono-ease);
}

.nav-search-wrap:focus-within {
  border-color: rgba(17,17,17,0.34) !important;
  box-shadow: 0 0 0 7px rgba(17,17,17,0.055), 0 26px 66px rgba(17,17,17,0.12) !important;
  transform: translateY(-2px);
}

.nav-search-icon,
.nav-search-wrap input,
.nav-search-wrap input::placeholder {
  color: var(--mono-muted) !important;
}

.nav-search-submit,
.nav-ai-input button,
.nav-circle-next {
  color: #ffffff !important;
  background: #111111 !important;
  border: 1px solid #111111 !important;
  box-shadow: 0 14px 34px rgba(17,17,17,0.18) !important;
  transition: transform 0.24s var(--mono-ease), box-shadow 0.24s var(--mono-ease), background 0.24s var(--mono-ease);
}

.nav-search-submit:hover,
.nav-ai-input button:hover,
.nav-circle-next:hover {
  background: #000000 !important;
  transform: translateX(2px) scale(1.04);
  box-shadow: 0 18px 44px rgba(17,17,17,0.24) !important;
}

.nav-hot-tags button,
.nav-panel-head button {
  color: var(--mono-text-soft) !important;
  background: rgba(255,255,255,0.64) !important;
  border: 1px solid var(--mono-border) !important;
  box-shadow: none !important;
}

.nav-hot-tags button:hover,
.nav-panel-head button:hover {
  color: #000000 !important;
  background: #ffffff !important;
  transform: translateY(-1px);
}

.nav-section-card,
.nav-panel {
  animation: mono-rise-in 0.68s var(--mono-ease) both;
}

.nav-section-card:nth-of-type(2) { animation-delay: 70ms; }
.nav-section-card:nth-of-type(3) { animation-delay: 130ms; }
.nav-panel:nth-child(1) { animation-delay: 100ms; }
.nav-panel:nth-child(2) { animation-delay: 160ms; }
.nav-panel:nth-child(3) { animation-delay: 220ms; }

.nav-site-card,
.nav-recommend-item,
.nav-rank-row,
.nav-recent-row {
  color: var(--mono-text) !important;
  background: rgba(255,255,255,0.7) !important;
  border: 1px solid var(--mono-border) !important;
  box-shadow: none !important;
  transition: transform 0.24s var(--mono-ease), background 0.24s var(--mono-ease), border-color 0.24s var(--mono-ease), box-shadow 0.24s var(--mono-ease);
}

.nav-site-card:hover,
.nav-recommend-item:hover {
  background: #ffffff !important;
  border-color: var(--mono-border-strong) !important;
  box-shadow: 0 18px 44px rgba(17,17,17,0.08) !important;
  transform: translateY(-6px);
}

.nav-rank-row:hover,
.nav-recent-row:hover {
  background: #ffffff !important;
  transform: translateX(3px);
}

.nav-site-card small,
.nav-recommend-item small,
.nav-rank-row small,
.nav-recent-row small {
  color: var(--mono-muted) !important;
}

.nav-site-logo {
  background: #ffffff !important;
  border: 1px solid var(--mono-border) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.85) !important;
}

.nav-add-card {
  border-style: dashed !important;
}

.nav-add-sign,
.nav-rank-num.hot,
.nav-fire {
  color: #111111 !important;
  background: #f2f2ef !important;
  border-color: var(--mono-border) !important;
  box-shadow: none !important;
}

.nav-fire {
  color: transparent !important;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #111111 !important;
}

.nav-ai-panel {
  background: linear-gradient(140deg, rgba(255,255,255,0.82), rgba(235,235,231,0.76)) !important;
  overflow: hidden;
}

.nav-ai-art {
  filter: grayscale(1);
  opacity: 0.72;
}

.nav-ai-input {
  background: rgba(255,255,255,0.82) !important;
  border: 1px solid var(--mono-border) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.9) !important;
}

.nav-ai-input input {
  color: var(--mono-text) !important;
}

.nav-ai-input input::placeholder {
  color: var(--mono-muted) !important;
}

.nav-search-dropdown {
  background: rgba(255,255,255,0.92) !important;
  border: 1px solid var(--mono-border) !important;
  box-shadow: var(--mono-shadow-md) !important;
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.nav-search-suggestion,
.nav-history-chip,
.nav-search-engine-row {
  color: var(--mono-text) !important;
  background: transparent !important;
}

.nav-search-suggestion:hover,
.nav-history-chip:hover,
.nav-search-engine-row:hover {
  background: rgba(17,17,17,0.055) !important;
}

.layout.dark-theme .nav-topbar,
.layout.dark-theme .nav-home-shell {
  background: #070707 !important;
  color: var(--mono-text) !important;
}

.layout.dark-theme .nav-home-shell {
  background:
    radial-gradient(circle at 84% 8%, rgba(255,255,255,0.07), transparent 25rem),
    linear-gradient(180deg, #070707, #101010) !important;
  border-color: var(--mono-border) !important;
}

.layout.dark-theme .nav-topbar,
.layout.dark-theme .nav-side,
.layout.dark-theme .nav-panel,
.layout.dark-theme .nav-section-card,
.layout.dark-theme .nav-hero-card,
.layout.dark-theme .nav-site-card,
.layout.dark-theme .nav-recommend-item,
.layout.dark-theme .nav-rank-row,
.layout.dark-theme .nav-recent-row {
  background: rgba(18,18,18,0.76) !important;
  border-color: var(--mono-border) !important;
  color: var(--mono-text) !important;
}

.layout.dark-theme .nav-hero-card {
  background:
    radial-gradient(circle at 78% 24%, rgba(255,255,255,0.09), transparent 15rem),
    linear-gradient(112deg, rgba(18,18,18,0.92), rgba(9,9,9,0.86)) !important;
}

.layout.dark-theme .nav-brand-mark,
.layout.dark-theme .nav-icon-btn,
.layout.dark-theme .nav-login-btn,
.layout.dark-theme .nav-avatar-btn,
.layout.dark-theme .nav-search-wrap,
.layout.dark-theme .nav-ai-input,
.layout.dark-theme .nav-hot-tags button,
.layout.dark-theme .nav-panel-head button {
  background: rgba(255,255,255,0.06) !important;
  border-color: var(--mono-border) !important;
  color: var(--mono-text) !important;
}

.layout.dark-theme .nav-search-submit,
.layout.dark-theme .nav-ai-input button,
.layout.dark-theme .nav-circle-next {
  color: #111111 !important;
  background: #f4f4f2 !important;
  border-color: #f4f4f2 !important;
}

.layout.dark-theme .nav-side-item:hover,
.layout.dark-theme .nav-side-item.is-active,
.layout.dark-theme .nav-site-card:hover,
.layout.dark-theme .nav-recommend-item:hover,
.layout.dark-theme .nav-rank-row:hover,
.layout.dark-theme .nav-recent-row:hover {
  color: #ffffff !important;
  background: rgba(255,255,255,0.08) !important;
}

@keyframes nav-mono-drift {
  from { background-position: 0 0, 0 0; }
  to { background-position: 64px 64px, 64px 64px; }
}

@keyframes nav-soft-sheen {
  0%, 58% { transform: translateX(-120%); opacity: 0; }
  70% { opacity: 0.8; }
  100% { transform: translateX(120%); opacity: 0; }
}

@keyframes nav-float {
  from { transform: translate3d(0, 0, 0) scale(1); }
  to { transform: translate3d(0, -8px, 0) scale(1.015); }
}

@media (prefers-reduced-motion: reduce) {
  .nav-home-shell::before,
  .nav-hero-card::before,
  .nav-hero-card::after,
  .nav-orbit-core,
  .nav-orbit-dot,
  .nav-ai-art {
    animation: none !important;
  }
}

/* ===== Vibe Tool Stack inspired home ===== */
.stack-home {
  position: relative;
  z-index: 10;
  min-height: 100vh;
  color: #263140;
  background:
    radial-gradient(circle at 7% 12%, rgba(151, 219, 211, 0.26), transparent 280px),
    radial-gradient(circle at 92% 18%, rgba(239, 111, 84, 0.18), transparent 310px),
    #fbfcfb;
  font-family: "Inter", "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
  overflow: hidden;
}

.stack-home button {
  font-family: inherit;
}

.stack-header {
  height: 52px;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 0 clamp(18px, 8vw, 110px);
  border-bottom: 1px solid #dfe3e7;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  animation: stack-drop 520ms cubic-bezier(.2,.9,.2,1) both;
}

.stack-logo {
  width: max-content;
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 0;
  color: #253140;
  background: transparent;
  border: 0;
  font-size: 18px;
  letter-spacing: -0.03em;
}

.stack-logo-mark {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #d5dbe1;
  border-radius: 8px;
  color: #ef725c;
  background: #ffffff;
  box-shadow: 0 5px 16px rgba(38, 49, 64, 0.06);
}

.stack-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 28px;
}

.stack-nav button,
.stack-icon-search {
  min-width: 0;
  min-height: 34px;
  padding: 0;
  color: #718092;
  background: transparent;
  border: 0;
  font-size: 13px;
  font-weight: 650;
  transition: color 180ms ease, transform 180ms ease;
}

.stack-nav button:hover,
.stack-nav button.is-active,
.stack-icon-search:hover {
  color: #263140;
  transform: translateY(-1px);
}

.stack-header-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 14px;
}

.stack-browse-btn {
  min-height: 34px;
  padding: 0 18px;
  color: #ffffff;
  background: #ef725c;
  border: 1px solid #ef725c;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 760;
  box-shadow: 0 10px 26px rgba(239, 114, 92, 0.22);
  transition: transform 200ms ease, box-shadow 200ms ease, background 200ms ease;
}

.stack-browse-btn:hover {
  background: #e6614b;
  transform: translateY(-2px);
  box-shadow: 0 14px 34px rgba(239, 114, 92, 0.28);
}

.stack-main {
  width: 100%;
}

.stack-hero {
  max-width: 920px;
  margin: 0 auto;
  padding: 92px 20px 56px;
  text-align: center;
  animation: stack-rise 680ms cubic-bezier(.2,.9,.2,1) 70ms both;
}

.stack-hero h1 {
  margin: 0;
  color: #273343;
  font-size: clamp(42px, 5vw, 76px);
  line-height: 0.98;
  font-weight: 860;
  letter-spacing: -0.055em;
}

.stack-hero p {
  margin: 18px 0 24px;
  color: #8793a1;
  font-size: clamp(18px, 2vw, 28px);
  font-weight: 520;
  letter-spacing: -0.03em;
}

.stack-search {
  position: relative;
  width: min(100%, 610px);
  height: 56px;
  display: flex;
  align-items: center;
  margin: 0 auto;
  padding: 0 6px 0 22px;
  border: 1px solid #d8dde3;
  border-radius: 999px;
  background: rgba(255,255,255,0.92);
  box-shadow: 0 18px 42px rgba(38,49,64,0.08);
  transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
}

.stack-search:focus-within {
  border-color: #bcc5cf;
  transform: translateY(-3px);
  box-shadow: 0 24px 58px rgba(38,49,64,0.13);
}

.stack-search input {
  flex: 1;
  min-width: 0;
  height: 100%;
  color: #263140;
  background: transparent;
  border: 0;
  outline: none;
  font-size: 15px;
}

.stack-search input::placeholder {
  color: #a4aeb9;
}

.stack-search > button {
  width: 42px;
  height: 42px;
  min-width: 42px;
  min-height: 42px;
  border-radius: 50%;
  color: #ffffff;
  background: #243241;
  border: 0;
  box-shadow: 0 10px 20px rgba(36,50,65,0.22);
  transition: transform 220ms ease, background 220ms ease;
}

.stack-search > button:hover {
  background: #121b25;
  transform: scale(1.04);
}

.stack-search-dropdown {
  position: absolute;
  top: calc(100% + 10px);
  left: 0;
  right: 0;
  z-index: 20;
  display: grid;
  gap: 6px;
  padding: 10px;
  border: 1px solid #dfe3e7;
  border-radius: 16px;
  background: rgba(255,255,255,0.96);
  box-shadow: 0 24px 60px rgba(38,49,64,0.13);
  text-align: left;
}

.stack-search-row,
.stack-history-row,
.stack-search-engine {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 42px;
  padding: 8px 10px;
  color: #263140;
  background: transparent;
  border: 0;
  border-radius: 10px;
  text-align: left;
}

.stack-search-row:hover,
.stack-history-row:hover,
.stack-search-engine:hover {
  background: #f4f6f7;
}

.stack-search-row img {
  width: 24px;
  height: 24px;
  border-radius: 7px;
}

.stack-search-row span {
  display: grid;
  gap: 2px;
}

.stack-search-row small {
  color: #8a96a4;
}

.stack-meta {
  margin-top: 12px;
  color: #a0aab5;
  font-size: 11px;
  font-weight: 650;
}

.stack-quick-links {
  display: flex;
  justify-content: center;
  gap: 30px;
  margin-top: 20px;
}

.stack-quick-links button,
.stack-section-link,
.stack-see-all {
  min-height: 0;
  min-width: 0;
  padding: 0;
  color: #ef725c;
  background: transparent;
  border: 0;
  font-size: 12px;
  font-weight: 760;
}

.stack-quick-links button:nth-child(3) {
  color: #8793a1;
}

.stack-marquee {
  width: 100%;
  border-top: 1px solid #dfe3e7;
  border-bottom: 1px solid #dfe3e7;
  background: rgba(255,255,255,0.58);
  overflow: hidden;
}

.stack-marquee-track {
  width: max-content;
  display: flex;
  align-items: center;
  gap: 46px;
  padding: 26px 0;
  animation: stack-marquee 34s linear infinite;
}

.stack-marquee-track span {
  color: #8b96a2;
  font-size: clamp(18px, 2vw, 28px);
  font-weight: 760;
  white-space: nowrap;
}

.stack-category-section {
  max-width: 1120px;
  display: grid;
  grid-template-columns: 290px 1fr;
  gap: 62px;
  margin: 0 auto;
  padding: 78px 22px 118px;
}

.stack-category-menu {
  animation: stack-rise 640ms cubic-bezier(.2,.9,.2,1) 160ms both;
}

.stack-category-menu h2 {
  margin: 0 0 26px;
  color: #2c3747;
  font-size: 40px;
  line-height: 1.02;
  letter-spacing: -0.05em;
}

.stack-category-menu button:not(.stack-see-all) {
  width: 100%;
  min-height: 42px;
  display: flex;
  align-items: center;
  padding: 0 18px;
  margin-bottom: 10px;
  color: #647181;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 760;
  text-align: left;
  transition: background 180ms ease, border-color 180ms ease, color 180ms ease, transform 180ms ease;
}

.stack-category-menu button:not(.stack-see-all):hover,
.stack-category-menu button:not(.stack-see-all).is-active {
  color: #ef725c;
  background: #fff3f0;
  border-color: #f5c3ba;
  transform: translateX(3px);
}

.stack-see-all {
  margin-top: 18px;
}

.stack-tools-area {
  min-width: 0;
}

.stack-section-link {
  margin-bottom: 16px;
}

.stack-tool-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px 16px;
}

.stack-tool-card {
  min-height: 108px;
  display: grid;
  grid-template-columns: 38px 1fr;
  align-items: start;
  gap: 12px;
  padding: 16px;
  border: 1px solid #d8dde3;
  border-radius: 10px;
  color: #2c3747;
  background: rgba(255,255,255,0.76);
  text-align: left;
  box-shadow: 0 10px 28px rgba(38,49,64,0.035);
  animation: stack-card-in 540ms cubic-bezier(.2,.9,.2,1) var(--stagger) both;
  transition: transform 200ms ease, border-color 200ms ease, box-shadow 200ms ease, background 200ms ease;
}

.stack-tool-card:hover {
  transform: translateY(-5px);
  border-color: #bdc6cf;
  background: #ffffff;
  box-shadow: 0 18px 44px rgba(38,49,64,0.08);
}

.stack-tool-icon {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #dfe3e7;
  border-radius: 8px;
  background: #ffffff;
  overflow: hidden;
  transition: transform 200ms ease;
}

.stack-tool-card:hover .stack-tool-icon,
.stack-fav-item:hover .stack-tool-icon {
  transform: scale(1.08);
}

.stack-tool-icon img {
  width: 22px;
  height: 22px;
  object-fit: contain;
}

.stack-tool-copy {
  min-width: 0;
  display: grid;
  gap: 7px;
}

.stack-tool-copy strong,
.stack-fav-item strong {
  color: #2b3544;
  font-size: 14px;
  line-height: 1.1;
}

.stack-tool-copy small,
.stack-fav-item small {
  color: #728091;
  font-size: 11px;
  line-height: 1.45;
}

.stack-favorites-section {
  background: #e9ecef;
  border-top: 1px solid #dce1e6;
}

.stack-favorites-inner {
  max-width: 1120px;
  margin: 0 auto;
  padding: 78px 22px 90px;
}

.stack-kicker {
  margin: 0 0 8px;
  color: #ef725c;
  font-size: 16px;
  font-weight: 900;
  letter-spacing: -0.02em;
  transform: rotate(-3deg);
}

.stack-favorites-inner h2 {
  max-width: 650px;
  margin: 0;
  color: #2c3747;
  font-size: 42px;
  line-height: 1.05;
  letter-spacing: -0.05em;
}

.stack-fav-subtitle {
  max-width: 520px;
  margin: 14px 0 48px;
  color: #738091;
  font-size: 15px;
  line-height: 1.55;
}

.stack-fav-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 36px;
}

.stack-fav-item {
  min-height: 86px;
  display: grid;
  grid-template-columns: 34px 1fr auto;
  align-items: start;
  gap: 16px;
  padding: 20px 0;
  border: 0;
  border-top: 1px solid #ccd3da;
  color: #2c3747;
  background: transparent;
  text-align: left;
  transition: transform 180ms ease;
}

.stack-fav-item:hover {
  transform: translateX(5px);
}

.stack-fav-item span:not(.stack-tool-icon) {
  display: grid;
  gap: 7px;
}

.stack-fav-item em {
  color: #ef725c;
  font-size: 10px;
  font-style: normal;
  font-weight: 850;
  letter-spacing: 0.11em;
  text-transform: uppercase;
}

.stack-dropdown-enter-active,
.stack-dropdown-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.stack-dropdown-enter-from,
.stack-dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@keyframes stack-drop {
  from { opacity: 0; transform: translateY(-14px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes stack-rise {
  from { opacity: 0; transform: translateY(22px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes stack-card-in {
  from { opacity: 0; transform: translateY(18px) scale(.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes stack-marquee {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}

@media (max-width: 1100px) {
  .stack-header {
    padding: 0 24px;
  }

  .stack-category-section {
    grid-template-columns: 240px 1fr;
    gap: 34px;
  }

  .stack-tool-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .stack-header {
    height: auto;
    grid-template-columns: 1fr auto;
    gap: 12px;
    padding: 14px 18px;
  }

  .stack-nav {
    grid-column: 1 / -1;
    justify-content: flex-start;
    gap: 18px;
    overflow-x: auto;
  }

  .stack-hero {
    padding-top: 58px;
  }

  .stack-quick-links {
    flex-wrap: wrap;
    gap: 14px 22px;
  }

  .stack-category-section,
  .stack-fav-list {
    grid-template-columns: 1fr;
  }

  .stack-category-section {
    padding-top: 52px;
  }

  .stack-tool-grid {
    grid-template-columns: 1fr;
  }

  .stack-fav-item {
    grid-template-columns: 34px 1fr;
  }

  .stack-fav-item em {
    grid-column: 2;
  }
}

@media (prefers-reduced-motion: reduce) {
  .stack-header,
  .stack-hero,
  .stack-category-menu,
  .stack-tool-card,
  .stack-marquee-track {
    animation: none !important;
  }
}
</style>
