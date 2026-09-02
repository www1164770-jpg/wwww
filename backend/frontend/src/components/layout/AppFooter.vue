<script setup>
const currentYear = new Date().getFullYear();

const quickLinks = [
  { label: "首页", to: { path: "/", hash: "#home" } },
  { label: "分类浏览", to: { path: "/", hash: "#tools" } },
  { label: "搜索资源", to: { path: "/", hash: "#site-search" } },
  { label: "我的收藏", to: "/favorites" },
];

const relatedLinks = [{ label: "版权申诉", to: "/dmca" }];
</script>

<template>
  <footer class="app-footer">
    <div class="app-footer__inner">
      <section class="app-footer__brand" aria-labelledby="footer-brand-title">
        <RouterLink
          class="app-footer__brand-link"
          to="/"
          aria-label="知航屿首页"
        >
          <img
            class="app-footer__logo"
            src="/vocanav-logo.png"
            alt=""
            width="40"
            height="40"
          />
          <span id="footer-brand-title" class="app-footer__brand-name">
            知航屿
          </span>
        </RouterLink>

        <p class="app-footer__description">
          精选高质量 AI、设计与开发工具，帮助你更快找到适合当前需求的网站。
        </p>
      </section>

      <nav class="app-footer__section" aria-label="页脚快速链接">
        <h2 class="app-footer__heading">快速链接</h2>

        <ul class="app-footer__list">
          <li v-for="link in quickLinks" :key="link.label">
            <RouterLink class="app-footer__link" :to="link.to">
              {{ link.label }}
            </RouterLink>
          </li>
        </ul>
      </nav>

      <section
        class="app-footer__section"
        aria-labelledby="footer-related-title"
      >
        <h2 id="footer-related-title" class="app-footer__heading">相关信息</h2>

        <ul class="app-footer__list">
          <li v-for="link in relatedLinks" :key="link.label">
            <RouterLink class="app-footer__link" :to="link.to">
              {{ link.label }}
            </RouterLink>
          </li>
        </ul>
      </section>
    </div>

    <div class="app-footer__bottom">
      <p>© {{ currentYear }} 知航屿</p>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  margin-top: 72px;
  border-top: 0;
  background: transparent;
}

.app-footer__inner {
  display: grid;
  grid-template-columns:
    minmax(280px, 1.6fr)
    minmax(150px, 0.8fr)
    minmax(180px, 0.9fr);
  gap: clamp(28px, 6vw, 72px);
  width: min(var(--container), calc(100% - 40px));
  margin: 0 auto;
  padding: 48px clamp(24px, 4vw, 48px) 38px;
  border: 1px solid var(--app-border);
  border-radius: var(--radius-large) var(--radius-large) 0 0;
  background: var(--app-container-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.app-footer__brand,
.app-footer__section {
  min-width: 0;
}

.app-footer__brand-link {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--app-text-primary);
  text-decoration: none;
}

.app-footer__logo {
  width: 40px;
  height: 40px;
  flex: 0 0 auto;
  object-fit: contain;
}

.app-footer__brand-name {
  color: var(--app-text-primary);
  font-size: 20px;
  font-weight: 850;
  line-height: 1.2;
}

.app-footer__description {
  max-width: 380px;
  margin: 16px 0 0;
  color: var(--app-text-secondary);
  font-size: 14px;
  line-height: 1.8;
}

.app-footer__heading {
  margin: 0 0 12px;
  color: var(--app-text-primary);
  font-size: 14px;
  font-weight: 850;
  line-height: 1.4;
}

.app-footer__list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.app-footer__link {
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  color: var(--app-text-secondary);
  font-size: 14px;
  line-height: 1.5;
  text-decoration: none;
  transition: color var(--transition);
}

.app-footer__link:hover {
  color: var(--color-primary);
}

.app-footer__link:focus-visible,
.app-footer__brand-link:focus-visible {
  border-radius: 6px;
  outline: 3px solid rgba(255, 112, 88, 0.26);
  outline-offset: 3px;
}

.app-footer__bottom {
  width: min(var(--container), calc(100% - 40px));
  margin: 0 auto;
  padding: 20px clamp(24px, 4vw, 48px) 24px;
  border: 1px solid var(--app-border);
  border-top: 0;
  border-radius: 0 0 var(--radius-large) var(--radius-large);
  background: var(--app-container-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.app-footer__bottom p {
  margin: 0;
  color: var(--app-text-muted);
  font-size: 13px;
  line-height: 1.6;
}

@media (max-width: 800px) {
  .app-footer__inner {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .app-footer__brand {
    grid-column: 1 / -1;
  }
}

@media (max-width: 560px) {
  .app-footer {
    margin-top: 56px;
  }

  .app-footer__inner {
    grid-template-columns: 1fr;
    gap: 30px;
    width: min(var(--container), calc(100% - 32px));
    padding: 38px 22px 30px;
  }

  .app-footer__brand {
    grid-column: auto;
  }

  .app-footer__bottom {
    width: min(var(--container), calc(100% - 32px));
  }
}
</style>
