<template>
  <!-- ✨ 修复 1：在 class 和 style 之间加上空格 -->
  <div class="layout" :class="{ 'dark-theme': isDarkMode }" :style="dynamicBgStyle">
    
    <!-- ✨ 修复 2：补上缺失的 <header> 标签 -->
    <header class="header-block block-shadow">
      <div class="header-left">
        <div class="logo">
          <span>🚀 智汇导航</span>
        </div>

        <div class="profession-selector">
          <div class="current-prof-box">
            <span class="prof-icon">{{ professionData[currentProfession].icon }}</span>
            <span class="prof-name">{{ professionData[currentProfession].name }}</span>
            <span class="prof-arrow">▼</span>
          </div>
          
          <div class="prof-dropdown">
            <div 
              v-for="(data, key) in professionData" 
              :key="key"
              class="prof-item"
              :class="{ active: currentProfession === key }"
              @click="selectProfession(key)"
            >
              <span class="item-icon">{{ data.icon }}</span>
              <div class="item-info">
                <span class="item-name">{{ data.name }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="header-right">
        <!-- ✨ 个性化背景调色板 -->
        <button class="theme-toggle" @click="showBgModal = true" title="个性化背景">🎨</button>
        <button class="theme-toggle" @click="toggleTheme">{{ isDarkMode ? '☀️' : '🌙' }}</button>
        <div v-if="isLoggedIn" class="user-profile-container">
          <img :src="userInfo.avatar" class="header-avatar profile-link" @click="goToProfile" alt="头像" @error="(e) => e.target.src = 'https://api.dicebear.com/7.x/avataaars/svg?seed=fallback'">
        </div>
        <div v-else class="auth-group">
          <button class="pill-btn" @click="showAuthModal = true">登录</button>
          <button class="btn-primary" @click="showAuthModal = true">免费注册</button>
        </div>
      </div>
    </header> <!-- 这个闭合标签现在有对应的开启标签了 -->
    <div v-if="currentPage === 'home'" class="main-container">
      <main class="content">
        <div class="center-action-area">
          <div class="category-tabs-wrapper">
            <div class="nav-tab-box" :class="{ 'active': activeCategoryId === 'all' }" @mouseenter="activeCategoryId = 'all'">
              全部分类
            </div>
            <div v-for="cat in visibleCategories" :key="cat.id" class="nav-tab-box" :class="{ 'active': activeCategoryId === cat.id }" @mouseenter="activeCategoryId = cat.id">
              {{ cat.name }}
            </div>
            <!-- 1. 在这里插入添加分类按钮 -->
            <div class="nav-tab-box add-category-btn" @click="showAddCategoryModal = true">
              + 添加分类
            </div>
            <!-- 隐藏的文件选择框 -->
            <input type="file" accept=".html" class="hidden-file-input" ref="bookmarkInputRef" @change="handleBookmarkImport">
            
            <!-- ✨ 新增：导入书签按钮 -->
            <div class="nav-tab-box import-btn" @click="triggerBookmarkImport" style="background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px dashed #10b981;">
              📥 导入浏览器书签
            </div>
            <div class="more-dropdown-wrapper" v-if="hiddenCategories.length > 0">
              <div class="nav-tab-box more-btn">更多 <span class="arrow-down">▼</span></div>
              <div class="dropdown-menu">
                <div v-for="cat in hiddenCategories" :key="cat.id" class="dropdown-item" :class="{ 'active': activeCategoryId === cat.id }" @mouseenter="activeCategoryId = cat.id">
                  {{ cat.name }}
                </div>
              </div>
            </div>
          </div>
          <div class="search-section">
            <div class="search-box block-shadow">
              <input ref="searchInputRef" v-model="searchQuery" @keyup.enter="doSearch" type="text" :placeholder="`在 ${allEngines[currentEngine]?.name} 中搜索 (Ctrl+K 唤醒)`" />
              <button @click="doSearch" class="search-btn-oval">搜索</button>
            </div>

            <!-- ✨ 完美复刻：搜索框下方的单选按钮区 -->
            <div class="engine-radio-group">
              <label v-for="engine in activeEnginesList" :key="engine.key" class="engine-radio-label" :class="{ active: currentEngine === engine.key }">
                <input type="radio" :value="engine.key" v-model="currentEngine" class="hidden-radio">
                <span class="radio-custom"></span>
                {{ engine.name }}
              </label>
              
              <!-- 设置齿轮图标 -->
              <!-- 给点击事件加上 .stop 防止冒泡拦截，并打印日志来测试是否真的点到了 -->
<span class="engine-settings-icon" @click.stop="showEngineModal = true; console.log('齿轮被点击啦！状态变为:', showEngineModal)" title="自定义搜索引擎">⚙️</span>            </div>
          </div>
        </div>
        <!-- 骨架屏占位与真实数据切换 -->
        <!-- 骨架屏占位与真实数据切换 -->
        <div v-if="isLoading" class="site-grid">
          <div v-for="i in 12" :key="'skeleton-'+i" class="site-card block-shadow skeleton-card">
            <div class="logo-wrapper skeleton-box"></div>
            <div class="skeleton-text skeleton-box"></div>
          </div>
        </div>
        <div v-else-if="filteredWebsites.length === 0" class="empty-state-container">
          <div class="empty-icon">📭</div>
          <h3 class="empty-title">哎呀，这里空空如也</h3>
          <p class="empty-desc">没有找到相关网站，不如点击下方添加一个吧？</p>
          <button class="btn-primary" @click="openAddSiteModal">+ 立即添加网站</button>
        </div>
        <div v-else class="site-grid">
          <!-- 1. 正常渲染网站列表 (支持拖拽、右键、点击) -->
          <div v-for="site in filteredWebsites" :key="site.id" class="site-card block-shadow" 
               draggable="true"
               @dragstart="onDragStart($event, site)"
               @dragover="onDragOver($event)"
               @drop="onDrop($event, site)"
               @dragend="onDragEnd"
               @click="handleSiteClick(site)" 
               @contextmenu.prevent="openContextMenu($event, site)">
            <div class="logo-wrapper">
              <!-- ✨ 修复：将传入 @error 的参数改为完整的 site 对象 -->
              <img class="site-logo" :src="site.logo_url || getLogoUrl(site.url)" :alt="site.name" @error="handleIconError($event, site)" />
            </div>
            <span class="site-name">{{ site.name }}</span>
          </div>

          <!-- 2. 添加网站卡片 -->
          <div class="site-card add-site-card" @click="openAddSiteModal">
            <div class="logo-wrapper add-icon-wrapper"><span class="plus-icon">+</span></div>
            <span class="site-name">添加网站</span>
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

        <div class="sidebar-box trending-box block-shadow">
          <div class="box-header">
            <h3 class="box-title">🔥 今日排行</h3>
            <span class="box-subtitle">在线热度涨跌</span>
          </div>
          <div class="scroll-viewport">
            <!-- ✨ 新增：排行榜骨架屏 -->
            <div v-if="isLoading" class="scroll-track" style="animation: none;">
              <div v-for="i in 6" :key="'rank-skel-'+i" class="trending-item" style="pointer-events: none; border: none;">
                <div class="rank-badge skeleton-box" style="background: transparent; box-shadow: none;"></div>
                <div class="skeleton-text skeleton-box" style="width: 80px; margin: 0; height: 16px;"></div>
                <div class="skeleton-text skeleton-box" style="width: 40px; margin-left: auto; height: 14px;"></div>
              </div>
            </div>

            <!-- 原有的真实数据渲染 -->
            <TransitionGroup v-else name="rank-list" tag="div" class="scroll-track">
              <!-- 排行榜数据渲染 -->
              <a v-for="site in sortedLeaderboard" :key="site.id" @click.prevent="handleSiteClick(site)" class="trending-item">
                <span class="rank-badge" :class="'rank-' + site.rank">{{ site.rank }}</span>
                <span class="site-name">{{ site.name }}</span>
                <span class="click-count">
                    <span v-if="site.delta > 0" style="color: #ef4444; font-size: 13px; font-weight: 600;">
                      ↑ {{ site.growth_rate }}%
                    </span>
                    <span v-else-if="site.delta < 0" style="color: #10b981; font-size: 13px; font-weight: 600;">
                      ↓ {{ Math.abs(site.growth_rate) }}%
                    </span>
                    <span v-else style="color: #94a3b8; font-size: 13px;">—</span>
                </span>
              </a>
              
              <!-- 复制列表 (用于无缝滚动) -->
              <a v-for="site in sortedLeaderboard" :key="'dup-'+site.id" @click.prevent="handleSiteClick(site)" class="trending-item">
                <span class="rank-badge" :class="'rank-' + site.rank">{{ site.rank }}</span>
                <span class="site-name">{{ site.name }}</span>
                <span class="click-count">
                    <span v-if="site.delta > 0" style="color: #ef4444; font-size: 13px; font-weight: 600;">
                      ↑ {{ site.growth_rate }}%
                    </span>
                    <span v-else-if="site.delta < 0" style="color: #10b981; font-size: 13px; font-weight: 600;">
                      ↓ {{ Math.abs(site.growth_rate) }}%
                    </span>
                    <span v-else style="color: #94a3b8; font-size: 13px;">—</span>
                </span>
              </a>
            </TransitionGroup>
          </div>
        </div>
      </aside>
    </div>

    <!-- ================= 个人中心页 (直接修改版) ================= -->
    <div v-else-if="currentPage === 'profile'" class="profile-fullscreen-wrapper">
      <div class="profile-inner-container">
        <div class="profile-header-section">
          <button class="nav-back-btn" @click="goHome">← 返回</button>
          <h1 class="main-title">个人信息</h1>
          <p class="sub-title">在这里直接修改您的资料，点击底部保存即可生效</p>
        </div>

        <div class="profile-cards-gap">
          <div class="info-card-box block-shadow">
            <div class="card-head"><h2>基本信息</h2><span>部分信息可能对其他用户可见</span></div>
            
            <!-- ✨ 彻底清理后的头像上传行 -->
            <div class="form-row">
              <span class="row-label">个人资料照片</span>
              
              <div class="row-content avatar-edit-row">
                <!-- 隐藏的文件输入框 -->
                <input type="file" accept="image/*" class="hidden-file-input" ref="avatarInputRef" @change="handleAvatarUpload">
                
                <!-- 仅保留这个可点击的头像区域 -->
                <div class="avatar-upload-wrapper" @click="triggerAvatarUpload" title="点击更换头像">
                  <img :src="userInfo.avatar" class="circle-avatar" @error="(e) => e.target.src = 'https://api.dicebear.com/7.x/avataaars/svg?seed=fallback'">
                  
                  <!-- 悬浮提示遮罩 -->
                  <div class="avatar-hover-mask">
                    <span>更换头像</span>
                  </div>
                </div>

                <!-- 💡 右边的文字和按钮已经彻底删除 -->
              </div>
            </div>
            
            <div class="form-row">
              <span class="row-label">名称</span>
              <div class="row-content">
                <input type="text" v-model="userInfo.username" class="inline-input" placeholder="请输入名称">
              </div>
            </div>
            
            <div class="form-row">
              <span class="row-label">性别</span>
              <div class="row-content">
                <select v-model="userInfo.gender" class="inline-input">
                  <option value="男">男</option>
                  <option value="女">女</option>
                  <option value="保密">保密</option>
                </select>
              </div>
            </div>
            
            <div class="form-row">
              <span class="row-label">生日</span>
              <div class="row-content">
                <input type="date" v-model="userInfo.birthday" class="inline-input">
              </div>
            </div>
          </div>

          <div class="info-card-box block-shadow">
            <div class="card-head"><h2>联系方式与个性化</h2></div>
            <div class="form-row">
              <span class="row-label">电子邮箱</span>
              <div class="row-content">
                <input type="email" v-model="userInfo.email" class="inline-input" placeholder="例如: name@example.com">
              </div>
            </div>
            <div class="form-row align-top">
              <span class="row-label">个性签名</span>
              <div class="row-content">
                <textarea v-model="userInfo.bio" class="inline-input" rows="3" placeholder="介绍一下你自己吧..."></textarea>
              </div>
            </div>
          </div>
        </div>
        <!-- 底部操作区 -->
        <div class="bottom-sticky-area">
          <button class="save-action-btn" @click="saveProfileDirectly">保存所有修改</button>
          <button class="logout-action-btn" @click="handleLogout">退出当前账号</button>
        </div>
      </div>
    </div>
    <!-- ================= 个人中心页结束 ================= -->

    <div v-if="showAuthModal" class="auth-overlay" @click="showAuthModal = false">
      <div class="auth-modal" @click.stop>
        <button class="close-btn" @click="showAuthModal = false">×</button>
        <transition name="fade-slide" mode="out-in">
          <div v-if="authStage === 'methods'" key="methods" class="vertical-layout">
            <h2 class="modal-title">快速登录 / 注册</h2>
            <button class="method-btn github" @click="handleGithubLogin">🐱 GitHub 登录</button>
            <button class="method-btn phone" @click="switchTo('mobile')">📱 手机号验证码</button>
            <button class="method-btn email" @click="switchTo('email')">✉️ 邮箱密码登录</button>
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
        </transition>
        <div class="modal-footer">注册/登录即代表同意 <a href="#" target="_blank">用户协议</a></div>
      </div>
    </div>

    <!-- 动态单项修改弹窗 -->
    <div v-if="showEditModal" class="auth-overlay" @click="showEditModal = false">
      <div class="auth-modal edit-modal" @click.stop>
        <button class="close-btn" @click="showEditModal = false">×</button>
        <!-- 标题动态变化 -->
        <h2 class="modal-title">{{ editingTitle }}</h2>
        
        <div class="edit-form-container">
          
          <!-- 情况1：修改头像 -->
          <div v-if="editingField === 'avatar'" class="avatar-edit-section">
            <div class="avatar-preview-wrapper" style="margin: 0 auto 15px auto;">
              <img :src="editForm.avatar || userInfo.avatar" class="avatar-img" alt="头像" @error="(e) => e.target.src = 'https://api.dicebear.com/7.x/avataaars/svg?seed=fallback'">
            </div>
            <input type="text" v-model="editForm.avatar" placeholder="请输入新的头像图片链接 URL" class="auth-input">
            <p style="font-size:12px; color:#64748b; margin-top:8px; text-align:center;">暂不支持本地上传，请输入网络图片地址</p>
          </div>

          <!-- 情况2：修改名称 -->
          <div v-else-if="editingField === 'username'" class="input-group">
            <input type="text" v-model="editForm.username" placeholder="请输入新名称" class="auth-input">
          </div>

          <!-- 情况3：修改性别 -->
          <div v-else-if="editingField === 'gender'" class="input-group">
            <select v-model="editForm.gender" class="auth-input custom-select">
              <option value="男">男</option>
              <option value="女">女</option>
              <option value="保密">保密</option>
            </select>
          </div>

          <!-- 情况4：修改生日 -->
          <div v-else-if="editingField === 'birthday'" class="input-group">
            <input type="date" v-model="editForm.birthday" class="auth-input">
          </div>

          <!-- 情况5：修改邮箱 -->
          <div v-else-if="editingField === 'email'" class="input-group">
            <input type="email" v-model="editForm.email" placeholder="例如: name@example.com" class="auth-input">
          </div>

          <!-- 情况6：修改签名 -->
          <div v-else-if="editingField === 'bio'" class="input-group">
            <textarea v-model="editForm.bio" placeholder="介绍一下你自己吧..." class="auth-input" rows="3" maxlength="50"></textarea>
            <span class="char-counter">{{ editForm.bio?.length || 0 }}/50</span>
          </div>

          <button class="btn-submit" @click="saveProfile">保存修改</button>
        </div>
      </div>
    </div>

  </div>

  <!-- 添加网站弹窗 -->
<div v-if="showAddSiteModal" class="auth-overlay" @click="showAddSiteModal = false">
  <div class="auth-modal edit-modal" @click.stop>
    <button class="close-btn" @click="showAddSiteModal = false">×</button>
    <h2 class="modal-title">✨ 推荐新网站</h2>
    <div class="vertical-layout">
      <input type="text" v-model="newSiteForm.name" placeholder="网站名称" class="auth-input">
      <input type="text" v-model="newSiteForm.url" placeholder="网站链接" class="auth-input">
      <select v-model="newSiteForm.category_id" class="auth-input custom-select">
        <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
      </select>
      <button class="btn-submit" @click="submitNewSite">立即添加</button>
    </div>
  </div>
</div>

<!-- 添加分类弹窗 -->
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
<!-- 优雅的全局轻提示 Toast -->
    <transition name="toast-fade">
      <div v-if="toast.show" class="toast-message block-shadow" :class="toast.type">
        <span class="toast-icon">{{ toast.type === 'success' ? '✨' : '⚠️' }}</span>
        <span>{{ toast.message }}</span>
      </div>
    </transition>
    <!-- 桌面级右键菜单 -->
    <transition name="fade-slide">
      <div v-show="contextMenu.show" class="context-menu block-shadow" 
           :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }" 
           @click.stop>
        <div class="context-header">管理 {{ contextMenu.site?.name }}</div>
        <!-- 右键菜单 -->
        <div class="context-item" @click="editSite">✏️ 编辑此网站</div>

        <!-- 添加/编辑 网站弹窗 -->
        <div v-if="showAddSiteModal" class="auth-overlay" @click="showAddSiteModal = false">
          <div class="auth-modal edit-modal" @click.stop>
            <button class="close-btn" @click="showAddSiteModal = false">×</button>
            <!-- ✨ 根据状态动态显示标题 -->
            <h2 class="modal-title">{{ isEditingSite ? '✏️ 编辑网站' : '✨ 推荐新网站' }}</h2>
            <div class="vertical-layout">
              <input type="text" v-model="newSiteForm.name" placeholder="网站名称" class="auth-input">
              <input type="text" v-model="newSiteForm.url" placeholder="网站链接" class="auth-input">
              <select v-model="newSiteForm.category_id" class="auth-input custom-select">
                <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
              </select>
              <!-- ✨ 根据状态动态显示按钮文字 -->
              <button class="btn-submit" @click="submitNewSite">{{ isEditingSite ? '保存修改' : '立即添加' }}</button>
            </div>
          </div>
        </div>
        <div class="context-item danger" @click="deleteSite">🗑️ 移除此网站</div>
      </div>
    </transition>
<!-- ✨ 常用搜索设置弹窗 -->
    <!-- ================= 搜索引擎设置弹窗 ================= -->
    <!-- ================= 搜索引擎设置弹窗 ================= -->
    <div v-if="showEngineModal" class="auth-overlay" @click="showEngineModal = false">
      <div class="auth-modal engine-modal" @click.stop>
        
        <!-- 弹窗头部 -->
        <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0;">常用搜索设置 ({{ selectedEngines.length }}/{{ searchEngines.length }})</h3>
          <button class="close-btn" @click="showEngineModal = false">×</button>
        </div>

        <!-- 顶部：已选中的胶囊标签区域 -->
        <div class="selected-tags-area">
          <span 
            v-for="id in selectedEngines" 
            :key="id" 
            class="engine-tag"
          >
            {{ getEngineName(id) }}
            <span class="tag-close" @click="removeEngine(id)">×</span>
          </span>
        </div>

        <!-- 渐变分割线 -->
        <div class="modal-divider"></div>

        <!-- 底部：所有可选引擎的复选框网格 -->
        <!-- 底部：全新的果冻块状按钮网格 -->
        <div class="engine-checkbox-grid">
          <label 
            v-for="item in searchEngines" 
            :key="item.id" 
            class="engine-toggle-card" 
            :class="{ 'is-active': selectedEngines.includes(item.id) }"
          >
            <!-- 隐藏的原生复选框，负责数据绑定 -->
            <input 
              type="checkbox" 
              class="hidden-checkbox" 
              :value="item.id" 
              v-model="selectedEngines"
            >
            <!-- 直接显示居中的名称 -->
            <span class="engine-name">{{ item.name }}</span>
          </label>
        </div>

      </div>
    </div>
    <!-- ================= 🎨 个性化背景设置弹窗 ================= -->
    <div v-if="showBgModal" class="auth-overlay" @click="showBgModal = false">
      <div class="auth-modal engine-modal" @click.stop>
        
        <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0;">✨ 个性化外观</h3>
          <button class="close-btn" @click="showBgModal = false">×</button>
        </div>

        <div class="bg-options-container">
          <!-- 1. 纯色定制 -->
          <div class="bg-section">
            <h4>🎨 纯色定制</h4>
            <div class="color-picker-wrapper block-shadow">
              <input type="color" v-model="customColorPicker" @input="applyColorBg" class="native-color-picker" title="点击选择颜色">
              <span style="font-weight: 600; font-family: monospace;">{{ customColorPicker.toUpperCase() }}</span>
            </div>
          </div>

          <!-- 2. 绝美渐变 -->
          <div class="bg-section">
            <h4>🌈 绝美渐变 (推荐)</h4>
            <div class="gradient-grid">
              <div v-for="(grad, index) in presetGradients" :key="index"
                   class="gradient-swatch"
                   :style="{ background: grad }"
                   @click="applyGradientBg(grad)"
                   :class="{'is-active': customWallpaper === grad}">
              </div>
            </div>
          </div>

          <!-- 3. 本地上传 -->
          <div class="bg-section">
            <h4>🖼️ 图片壁纸</h4>
            <div class="upload-btn-group">
              <button class="btn-submit w-full" @click="triggerWallpaperUpload">从电脑选择高清图片</button>
              <input type="file" accept="image/*" class="hidden-file-input" ref="wallpaperInputRef" @change="handleWallpaperUpload">
            </div>
          </div>

          <!-- 恢复默认 -->
          <div class="bg-section" style="margin-top: 15px;" v-if="customWallpaper">
            <button class="logout-action-btn w-full" @click="clearBackground" style="text-align: center;">🗑️ 恢复默认动态背景</button>
          </div>
        </div>

      </div>
    </div>
    <!-- ================= 弹窗结束 ================= -->
</template>

<script setup>
// 修改引入
import { ref, computed, onMounted, onUnmounted, nextTick, watch} from 'vue'
import axios from 'axios'


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
const showAuthModal = ref(false);
const showEditModal = ref(false);
const authStage = ref('methods');
const showAddSiteModal = ref(false);
const showAddCategoryModal = ref(false);
const newCategoryName = ref('');
const newSiteForm = ref({ id: null, name: '', url: '', category_id: '' });
const isEditingSite = ref(false); // ✨ 新增：标识当前是添加还是编辑

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

// ✨ 新增：打开编辑弹窗的逻辑 (从右键菜单触发)
const editSite = () => {
  if (!contextMenu.value.site) return;
  isEditingSite.value = true;
  // 深拷贝当前网站的数据到表单中
  newSiteForm.value = { ...contextMenu.value.site };
  showAddSiteModal.value = true;
  closeContextMenu();
};

const submitNewSite = async () => {
  if (!newSiteForm.value.name.trim() || !newSiteForm.value.url.trim()) return alert("请填写完整！");
  const newSite = {
    id: Date.now(),
    name: newSiteForm.value.name,
    url: newSiteForm.value.url.startsWith('http') ? newSiteForm.value.url : 'https://' + newSiteForm.value.url,
    category_id: newSiteForm.value.category_id,
    clicks: 0
  };
  websites.value.unshift(newSite);
  showAddSiteModal.value = false;
  activeCategoryId.value = newSite.category_id;
};

const submitNewCategory = () => {
  if (!newCategoryName.value.trim()) return alert("请填写名称！");
  const newCat = { id: Date.now(), name: newCategoryName.value };
  // 注意：由于 categories 是基于 professionData 计算出来的，
  // 这里建议直接推入 professionData[currentProfession.value].categories
  professionData[currentProfession.value].categories.push(newCat);
  showAddCategoryModal.value = false;
  newCategoryName.value = '';
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
// ================= 排行榜逻辑 =================
const rawLeaderboard = ref([]);

const fetchRankingData = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:5000/api/ranking');
    rawLeaderboard.value = response.data; 
  } catch (error) { 
    console.warn('获取排行数据失败，已启用本地模拟数据'); 
    if (rawLeaderboard.value.length === 0) {
      // ✨ 补全了每个网站的 url 字段
      rawLeaderboard.value = [
        { id: 101, name: '哔哩哔哩', url: 'https://www.bilibili.com', clicks: 1250 },
        { id: 201, name: 'GitHub', url: 'https://github.com', clicks: 980 },
        { id: 102, name: '知乎', url: 'https://www.zhihu.com', clicks: 856 },
        { id: 501, name: 'ChatGPT', url: 'https://chat.openai.com', clicks: 760 },
        { id: 301, name: '抖音', url: 'https://www.douyin.com', clicks: 520 },
        { id: 204, name: '掘金', url: 'https://juejin.cn', clicks: 430 }
      ];
    }
  }
};

const sortedLeaderboard = computed(() => {
  let sorted = [...rawLeaderboard.value].sort((a, b) => b.clicks - a.clicks);
  return sorted.map((item, index) => ({ ...item, rank: index + 1 }));
});

// ================= 核心：网站点击处理 (完美合并原逻辑) =================
// ================= 核心：网站点击处理 (增加前端即时排序) =================
// frontend/src/App.vue 或相关组件

const handleSiteClick = async (site) => {
  // 1. 立即在新窗口打开目标网址，不耽误用户时间
  window.open(site.url, '_blank');
  
  // 2. 静默发送点击统计请求
  try {
    await axios.post('http://127.0.0.1:5000/api/click', { id: site.id });
    
    // 3. 统计完成后，刷新排行榜数据（fetchRankingData）
    // 这样用户回到页面时，就能看到排行榜实时变化了
    fetchRankingData(); 
  } catch (error) {
    console.error('统计点击失败:', error);
  }
  
  // 1. 前端乐观更新 (立刻 +1)
  site.clicks = (site.clicks || 0) + 1; 
  
  const rankItem = rawLeaderboard.value.find(item => item.id === site.id);
  if (rankItem) {
    rankItem.clicks += 1;
  } else {
    fetchRankingData();
  }

  try {
    // 2. 发送真实请求给后端
    await axios.post(`http://127.0.0.1:5000/api/click/${site.id}`);

    // 3. 缓存 Logo
    if (site.id && (!site.logo_url || !site.logo_url.startsWith('data:image'))) {
      const response = await axios.post('http://127.0.0.1:5000/api/cache_logo', { id: site.id, url: site.url });
      if (response.data.status === 'success') {
        site.logo_url = response.data.logo_url;
      }
    }
  } catch (error) { console.error('处理点击失败:', error); }
};


// ================= 生命周期与轮询 (同步全网数据) =================
let pollingTimer = null; // 轮询定时器

// ================= 登录与鉴权 =================
const phoneNumber = ref('');
const verifyCode = ref('');

const switchTo = (stage) => { authStage.value = stage; };
const handleGithubLogin = () => { window.location.href = AUTH_URLS.GITHUB; };

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
  alert("已安全退出账号");
};

// ================= 个人信息管理 =================
const goToProfile = () => { currentPage.value = 'profile'; };
const goHome = () => { currentPage.value = 'home'; };

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

// 1. 定义所有职业及该职业下的分类映射
const professionData = {
  general: {
    name: '综合导航',
    icon: '🌐',
    categories: [
      { id: 1, name: '常用推荐' }, { id: 2, name: '开发社区' },
      { id: 3, name: '摸鱼娱乐' }, { id: 4, name: '实用工具' }, { id: 5, name: 'AI 神器' }
    ]
  },
  frontend: {
    name: '前端开发',
    icon: '🎨',
    categories: [
      { id: 201, name: '框架文档' }, { id: 202, name: 'UI 组件库' },
      { id: 203, name: '可视化/3D' }, { id: 204, name: '工具/构建' }
    ]
  },
  designer: {
    name: 'UI 设计师',
    icon: '🖌️',
    categories: [
      { id: 301, name: '灵感采集' }, { id: 302, name: '素材资源' },
      { id: 303, name: '在线工具' }, { id: 304, name: '字体/配色' }
    ]
  },
  product: {
    name: '产品经理',
    icon: '📋',
    categories: [
      { id: 401, name: '原型设计' }, { id: 402, name: '文档办公' },
      { id: 403, name: '数据分析' }, { id: 404, name: '竞品调研' }
    ]
  }
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

// ================= 智能过滤与本地秒搜 =================
const filteredWebsites = computed(() => {
  let list = websites.value;
  
  // 1. 分类过滤
  if (activeCategoryId.value !== 'all') {
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
// ================= 搜索功能 =================
// ================= 搜索功能与搜索引擎配置 =================
const searchQuery = ref('');

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

// 6. 执行真实搜索跳转
const doSearch = () => {
  if (searchQuery.value && allEngines[currentEngine.value]) {
    window.open(allEngines[currentEngine.value].url + encodeURIComponent(searchQuery.value), '_blank');
  }
};

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
  } finally {
    isAiThinking.value = false
    scrollToBottom()
  }
};
const scrollToBottom = () => { nextTick(() => { if (chatWindow.value) chatWindow.value.scrollTop = chatWindow.value.scrollHeight }) };

// ================= 右键菜单 (Context Menu) =================
const contextMenu = ref({ show: false, x: 0, y: 0, site: null });

const openContextMenu = (e, site) => {
  contextMenu.value = { show: true, x: e.clientX, y: e.clientY, site };
};

const closeContextMenu = () => { contextMenu.value.show = false; };

// ✨ 新增一个通用关闭函数
const closeAllDropdowns = () => {
  closeContextMenu();
};
const deleteSite = () => {
  if (!contextMenu.value.site) return;
  const siteName = contextMenu.value.site.name;
  websites.value = websites.value.filter(s => s.id !== contextMenu.value.site.id);
  // 这里假设您已经替换了我们上一轮聊过的 showToast
  if(typeof showToast === 'function') showToast(`已删除 [${siteName}]`, 'info'); 
  else alert(`已删除 [${siteName}]`);
  closeContextMenu();
};

// ================= 🎨 终极外观引擎 (支持图片、颜色、渐变) =================
const showBgModal = ref(false);
const customWallpaper = ref('');
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
onMounted(async () => {
  // 1. 读取所有缓存 (保持不变)
  if (localStorage.getItem('dark_mode') === 'true') isDarkMode.value = true;
  const savedBg = localStorage.getItem('custom_wallpaper');
  if (savedBg) customWallpaper.value = savedBg;
  const savedCurrentEngine = localStorage.getItem('current_engine');
  if (savedCurrentEngine) currentEngine.value = savedCurrentEngine;
  const savedEngines = JSON.parse(localStorage.getItem('selected_engines'));
  if (savedEngines && savedEngines.length > 0) selectedEngines.value = savedEngines;

  // 2. 绑定全局快捷键
  document.addEventListener('keydown', handleGlobalKeydown);

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
/* 沉浸式壁纸 */
.layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-image: url('https://images.unsplash.com/photo-1579546929518-9e396f3cc809?q=80&w=2070&auto=format&fit=crop');
  background-size: cover;
  background-position: center;
  background-attachment: fixed; /* ✨ 关键：背景图固定不动 */
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
/* 修改原有的 .layout 样式块，或者在底部追加 */
.layout.dark-theme {
  /* 移除图片背景，改用丝滑的纯色深邃渐变 */
  background-image: radial-gradient(circle at top right, #1a1a1a, #000000) !important;
  background-color: #000000;
}

/* 移除我们之前加的深色半透明遮罩 ::before，因为背景已经是黑色了 */
.layout.dark-theme::before {
  display: none;
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
.layout.dark-theme::before {
  content: "";
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(2, 6, 23, 0.4); /* 给背景图蒙上一层深色薄纱 */
  z-index: -1; /* 放在背景图之上，内容之下 */
  pointer-events: none;
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
  right: 0; 
  margin-top: 12px; 
  background: rgba(255, 255, 255, 0.7); /* 统一毛玻璃质感 */
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
  min-width: 120px;
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
.main-container { display: flex; flex: 1; overflow: hidden; padding: 25px; gap: 25px; }
/* ✨ 修复排版收缩的关键：给 content 加上 width: 100% */
.content { flex: 1; width: 100%; overflow-y: auto; display: flex; flex-direction: column; align-items: center; padding: 10px 20px; }
.center-action-area { width: 100%; display: flex; flex-direction: column; align-items: center; margin-bottom: 30px; margin-top: 10px; }

/* 搜索框完美尺寸 */
.search-section { width: 100%; max-width: 650px; display: flex; flex-direction: column; align-items: center; }
.search-box { width: 100%; display: flex; align-items: center; border-radius: 40px; padding: 6px 6px 6px 20px; position: relative; z-index: 20; transition: 0.3s; }
.search-box:focus-within { box-shadow: 0 10px 30px rgba(59, 130, 246, 0.12); border-color: rgba(59, 130, 246, 0.4); }
.search-box input { flex: 1; border: none; outline: none; font-size: 15px; background: transparent; color: var(--text-main); min-width: 0; }
.search-btn-oval { background: var(--primary-bright); color: #fff; border: none; border-radius: 30px; padding: 10px 28px; cursor: pointer; font-weight: 600; letter-spacing: 1px; transition: 0.3s; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2); margin-left: 10px; }

/* 分类 Tabs */
.category-tabs-wrapper { display: flex; gap: 16px; justify-content: center; margin-bottom: 25px; flex-wrap: wrap; }
.nav-tab-box { cursor: pointer; font-size: 14px; font-weight: 500; padding: 8px 20px; border-radius: 12px; transition: 0.3s; text-shadow: 0 1px 2px rgba(255,255,255,0.8); }
.layout.dark-theme .nav-tab-box {
  color: var(--text-muted);
  font-weight: 400; /* 未选中态保持轻盈 */
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
.engine-radio-group { display: flex; align-items: center; justify-content: center; gap: 15px; margin-top: 15px; flex-wrap: wrap; }
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
  width: 520px; /* 稍微加宽一点，给复选框更多呼吸空间 */
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
.site-grid { 
  display: grid; 
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); 
  gap: 24px; 
  width: 100%; 
  max-width: 900px; 
  margin: 0 auto; /* ✨ 核心修复：让整个网格容器在页面中水平居中 */
  justify-content: center; /* 当卡片很少时，依然保持整体居中偏向 */
  align-content: start; 
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
}.site-card { padding: 20px 10px; display: flex; flex-direction: column; align-items: center; cursor: pointer; transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1); border-radius: 20px; text-decoration: none; }
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
.sidebar-right { width: 300px; display: flex; flex-direction: column; gap: 20px; flex-shrink: 0; }
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
}

.auth-modal { 
  background: rgba(255, 255, 255, 0.85); /* ✨ 苹果风透亮毛玻璃材质 */
  backdrop-filter: blur(30px); -webkit-backdrop-filter: blur(30px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 25px 50px rgba(0,0,0,0.15); 
  padding: 2.5rem 2.2rem; 
  border-radius: 24px; 
  width: 400px; 
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

.vertical-layout { display: flex; flex-direction: column; gap: 16px; }

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
.verify-code-row { display: flex; gap: 10px; }
.get-code-btn { background: transparent; border: 1px solid #60a5fa; color: #3b82f6; border-radius: 12px; padding: 0 15px; cursor: pointer; white-space: nowrap; font-weight: 600; transition: 0.2s;}
.get-code-btn:hover { background: rgba(59, 130, 246, 0.1); }
.link-btn { background: transparent; border: none; color: var(--text-muted); cursor: pointer; font-size: 13px; margin-top: 10px; transition: 0.2s;}
.link-btn:hover { color: #3b82f6; text-decoration: underline; }
.modal-footer { margin-top: 25px; text-align: center; font-size: 12px; color: var(--text-muted); }
.modal-footer a { color: #3b82f6; text-decoration: none; font-weight: 600;}

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
</style>