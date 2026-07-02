<template>
  <div class="page">
    <AppHeader />
    <main class="detail">
      <LoadingState v-if="loading" text="正在加载网站详情..." />
      <EmptyState
        v-else-if="!site"
        title="未找到网站"
        description="该网站不存在或暂时不可用。"
      />
      <template v-else>
        <section class="hero">
          <img
            :src="logoSrc"
            :alt="`${site.name || '网站'} Logo`"
            @error="logoFailed = true"
          />
          <div class="hero-copy">
            <p>{{ site.category_name || "AI 资源" }}</p>
            <h1>{{ site.name }}</h1>
            <span>{{ site.summary || "暂无简介" }}</span>
            <div class="actions">
              <button
                type="button"
                :aria-label="site.is_favorited ? '取消收藏' : '收藏'"
                @click="toggleFavorite"
              >
                {{ site.is_favorited ? "取消收藏" : "收藏" }}
              </button>
              <button
                type="button"
                class="primary"
                aria-label="访问官网"
                @click="visit"
              >
                访问官网
              </button>
            </div>
          </div>
        </section>

        <div class="detail-layout">
          <div class="main-column">
            <section class="content">
              <h2>详细介绍</h2>
              <p>{{ site.description || "暂无详细介绍" }}</p>
              <a
                class="site-url"
                :href="site.url"
                target="_blank"
                rel="noopener noreferrer"
              >
                {{ site.url }}
              </a>
            </section>

            <section class="comments">
              <div class="section-head">
                <h2>评论区域</h2>
                <p>分享你的使用体验，帮助其他用户判断是否适合。</p>
              </div>
              <form
                v-if="loggedIn"
                class="comment-form"
                @submit.prevent="submitComment"
              >
                <label>
                  评分
                  <select v-model.number="commentForm.rating">
                    <option :value="5">5 分</option>
                    <option :value="4">4 分</option>
                    <option :value="3">3 分</option>
                    <option :value="2">2 分</option>
                    <option :value="1">1 分</option>
                  </select>
                </label>
                <label>
                  评论内容
                  <textarea
                    v-model.trim="commentForm.content"
                    placeholder="分享你的使用体验..."
                    required
                  ></textarea>
                </label>
                <button type="submit" :disabled="commentSubmitting">
                  {{ commentSubmitting ? "正在提交..." : "发表评论" }}
                </button>
              </form>
              <button
                v-else
                type="button"
                class="login-comment"
                @click="goLogin"
              >
                登录后发表评论
              </button>
              <LoadingState v-if="commentsLoading" text="正在加载评论..." />
              <div v-else-if="comments.length" class="comment-list">
                <article
                  v-for="comment in comments"
                  :key="comment.id"
                  class="comment-item"
                >
                  <div>
                    <strong>{{ comment.username || "匿名用户" }}</strong>
                    <span>
                      {{ comment.rating || 0 }} 分 ·
                      {{ toDate(comment.created_at) }}
                    </span>
                  </div>
                  <p>{{ comment.content }}</p>
                  <button
                    v-if="comment.can_delete"
                    type="button"
                    class="ghost"
                    @click="deleteComment(comment)"
                  >
                    删除自己的评论
                  </button>
                </article>
              </div>
              <EmptyState
                v-else
                title="暂无评论"
                description="成为第一个分享使用体验的人。"
              />
            </section>
          </div>

          <aside class="side-column">
            <section class="facts">
              <h2>基础信息</h2>
              <div>
                <strong>是否免费</strong>
                <span>{{ site.is_free ? "是" : "否" }}</span>
              </div>
              <div>
                <strong>是否需要登录</strong>
                <span>{{ site.need_login ? "是" : "否" }}</span>
              </div>
              <div>
                <strong>地区</strong>
                <span>{{ site.region || "暂未填写" }}</span>
              </div>
              <div>
                <strong>推荐指数</strong>
                <span>{{
                  site.recommend_level || site.quality_score || "暂无"
                }}</span>
              </div>
              <div>
                <strong>用户评分</strong>
                <span>{{ site.rating_avg || 0 }}</span>
              </div>
            </section>

            <section class="tags-card">
              <h2>标签</h2>
              <div class="chips">
                <span v-for="tag in site.tags || []" :key="tag">{{ tag }}</span>
                <span v-if="!(site.tags || []).length">暂无标签</span>
              </div>
            </section>

            <section class="tags-card">
              <h2>适用职业</h2>
              <div class="chips">
                <span
                  v-for="occupation in site.occupations || []"
                  :key="occupation"
                >
                  {{ occupation }}
                </span>
                <span v-if="!(site.occupations || []).length"
                  >暂无适用职业</span
                >
              </div>
            </section>

            <section class="similar">
              <h2>相似网站推荐</h2>
              <SiteList
                :sites="site.similar_sites || []"
                empty-title="暂无相似网站"
                empty-description="后续会根据标签和职业推荐更多相似资源"
                @favorite="favoriteSimilar"
                @visit="visitSimilar"
              />
            </section>
          </aside>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppHeader from "../components/layout/AppHeader.vue";
import EmptyState from "../components/common/EmptyState.vue";
import LoadingState from "../components/common/LoadingState.vue";
import SiteList from "../components/site/SiteList.vue";
import { commentAPI, favoriteAPI, siteAPI } from "../utils/api";

const route = useRoute();
const router = useRouter();
const site = ref(null);
const loading = ref(false);
const comments = ref([]);
const commentsLoading = ref(false);
const commentSubmitting = ref(false);
const commentForm = reactive({ rating: 5, content: "" });
const fallbackLogo = "https://api.dicebear.com/7.x/shapes/svg?seed=site";
const logoFailed = ref(false);
const loggedIn = computed(() => Boolean(localStorage.getItem("access_token")));
const logoSrc = computed(() =>
  logoFailed.value ? fallbackLogo : site.value?.logo_url || fallbackLogo,
);

watch(
  () => site.value?.logo_url,
  () => {
    logoFailed.value = false;
  },
);

function toDate(value) {
  if (!value) return "";
  return String(value).slice(0, 10);
}

function goLogin() {
  return router.push({
    path: "/login",
    query: { redirect: route.fullPath },
  });
}

async function load() {
  loading.value = true;
  try {
    const response = await siteAPI.getSite(route.params.id);
    site.value = response.data?.data ?? response.data ?? null;
    await loadComments();
  } finally {
    loading.value = false;
  }
}
async function loadComments() {
  commentsLoading.value = true;
  try {
    const response = await commentAPI.getComments(route.params.id);
    comments.value = response.data?.data ?? response.data ?? [];
  } finally {
    commentsLoading.value = false;
  }
}
async function toggleFavorite() {
  if (!loggedIn.value) return goLogin();
  if (site.value.is_favorited) {
    await favoriteAPI.removeFavorite(site.value.id);
    site.value.is_favorited = false;
  } else {
    await favoriteAPI.addFavorite(site.value.id);
    site.value.is_favorited = true;
  }
}
async function visit() {
  await siteAPI.recordClick(site.value.id).catch(() => {});
  window.open(site.value.url, "_blank", "noopener,noreferrer");
}
async function favoriteSimilar(item) {
  if (!loggedIn.value) return goLogin();
  if (item.is_favorited) {
    await favoriteAPI.removeFavorite(item.id);
    item.is_favorited = false;
  } else {
    await favoriteAPI.addFavorite(item.id);
    item.is_favorited = true;
  }
}
async function visitSimilar(item) {
  await siteAPI.recordClick(item.id).catch(() => {});
  window.open(item.url, "_blank", "noopener,noreferrer");
}
async function submitComment() {
  if (!loggedIn.value) return goLogin();
  commentSubmitting.value = true;
  try {
    await commentAPI.addComment(site.value.id, { ...commentForm });
    commentForm.content = "";
    commentForm.rating = 5;
    await loadComments();
  } finally {
    commentSubmitting.value = false;
  }
}
async function deleteComment(comment) {
  await commentAPI.deleteComment(comment.id);
  comments.value = comments.value.filter((item) => item.id !== comment.id);
}
onMounted(load);
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #ffffff;
}

.detail {
  display: grid;
  gap: 26px;
  width: min(1180px, calc(100% - 40px));
  margin: 48px auto 78px;
}

.hero,
.content,
.comments,
.facts,
.similar,
.tags-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: #ffffff;
  padding: 24px;
  box-shadow: var(--shadow-soft);
}

.hero {
  display: flex;
  gap: 24px;
  align-items: center;
  border-radius: 24px;
  background:
    radial-gradient(
      circle at 12% 22%,
      rgba(191, 245, 237, 0.32),
      transparent 30%
    ),
    linear-gradient(135deg, #ffffff 0%, #fff4f1 100%);
  padding: clamp(30px, 5vw, 62px);
}

.hero img {
  flex: 0 0 auto;
  width: 108px;
  height: 108px;
  border: 1px solid var(--color-border);
  border-radius: 24px;
  object-fit: cover;
  background: var(--color-soft);
}

.hero-copy {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.hero-copy p {
  margin: 0;
  color: var(--color-primary);
  font-weight: 850;
}

h1,
h2,
p {
  margin-top: 0;
}

h1 {
  margin-bottom: 0;
  color: var(--color-heading);
  font-size: clamp(36px, 5vw, 58px);
  line-height: 1.08;
  word-break: break-word;
}

h2 {
  margin-bottom: 14px;
  color: var(--color-heading);
}

.hero-copy span,
.content p,
.comment-item p,
.section-head p {
  color: #718096;
  line-height: 1.7;
}

.detail-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 24px;
  align-items: start;
}

.main-column,
.side-column {
  display: grid;
  gap: 24px;
  min-width: 0;
}

.side-column {
  position: sticky;
  top: 92px;
}

.actions,
.chips,
.comment-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.comment-form {
  display: grid;
}

button,
.site-url {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: #ffffff;
  color: var(--color-heading);
  padding: 11px 16px;
  font-weight: 800;
  text-decoration: none;
  transition:
    transform var(--transition),
    border-color var(--transition),
    color var(--transition),
    background var(--transition);
}

button:hover,
button:focus-visible,
.site-url:hover,
.site-url:focus-visible {
  border-color: rgba(255, 112, 88, 0.38);
  color: var(--color-primary);
  transform: translateY(-1px);
  outline: none;
}

button.primary,
.comment-form button {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: #ffffff;
  box-shadow: 0 14px 28px rgba(255, 112, 88, 0.18);
}

button.primary:hover,
button.primary:focus-visible,
.comment-form button:hover,
.comment-form button:focus-visible {
  background: var(--color-primary-dark);
  color: #ffffff;
}

.site-url {
  display: inline-flex;
  max-width: 100%;
  overflow-wrap: anywhere;
}

.facts {
  display: grid;
  gap: 12px;
}

.facts div {
  display: grid;
  gap: 6px;
  border-radius: 16px;
  background: var(--color-soft);
  padding: 12px;
}

.facts span {
  color: var(--color-text);
}

.chips span {
  display: inline-block;
  max-width: 100%;
  border-radius: var(--radius-pill);
  background: var(--color-soft-orange);
  color: var(--color-primary-dark);
  padding: 8px 12px;
  overflow-wrap: anywhere;
  font-weight: 750;
}

.comment-form label {
  display: grid;
  gap: 8px;
  color: var(--color-heading);
  font-weight: 750;
}

.comment-form select,
.comment-form textarea {
  border: 1px solid var(--color-border);
  border-radius: 14px;
  padding: 12px;
  font: inherit;
}

.comment-form textarea {
  min-height: 116px;
  resize: vertical;
}

.comment-list {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.comment-item {
  display: grid;
  gap: 8px;
  border-top: 1px solid var(--color-border);
  padding-top: 14px;
}

.comment-item div {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
  color: var(--color-muted);
}

.ghost {
  justify-self: start;
  color: #b91c1c;
}

.login-comment {
  margin-bottom: 16px;
}

.similar :deep(.site-list) {
  grid-template-columns: 1fr;
}

@media (max-width: 960px) {
  .detail-layout {
    grid-template-columns: 1fr;
  }

  .side-column {
    position: static;
  }
}

@media (max-width: 768px) {
  .detail {
    width: min(100% - 28px, 1180px);
    margin-top: 32px;
  }
}

@media (max-width: 640px) {
  .hero {
    align-items: flex-start;
    flex-direction: column;
  }

  .actions {
    align-items: stretch;
    flex-direction: column;
  }

  .actions button {
    width: 100%;
  }
}
</style>
