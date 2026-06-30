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
          <img :src="site.logo_url || fallbackLogo" :alt="site.name" />
          <div>
            <p>{{ site.category_name || "AI 资源" }}</p>
            <h1>{{ site.name }}</h1>
            <span>{{ site.summary }}</span>
            <div class="actions">
              <button @click="toggleFavorite">
                {{ site.is_favorited ? "取消收藏" : "收藏" }}
              </button>
              <button @click="visit">访问官网</button>
            </div>
          </div>
        </section>
        <section class="facts">
          <div>
            <strong>是否免费</strong
            ><span>{{ site.is_free ? "是" : "否" }}</span>
          </div>
          <div>
            <strong>是否需要登录</strong
            ><span>{{ site.need_login ? "是" : "否" }}</span>
          </div>
          <div>
            <strong>地区</strong><span>{{ site.region }}</span>
          </div>
          <div>
            <strong>推荐指数</strong
            ><span>{{ site.recommend_level || site.quality_score }}</span>
          </div>
          <div>
            <strong>用户评分</strong><span>{{ site.rating_avg || 0 }}</span>
          </div>
        </section>
        <section class="content">
          <h2>详细介绍</h2>
          <p><strong>链接：</strong> {{ site.url }}</p>
          <p>{{ site.description || site.summary }}</p>
          <div class="chips">
            <span v-for="tag in site.tags" :key="tag">{{ tag }}</span>
            <span v-for="occupation in site.occupations" :key="occupation">{{
              occupation
            }}</span>
          </div>
        </section>
        <section>
          <h2>相似网站推荐</h2>
          <SiteList
            :sites="site.similar_sites || []"
            @favorite="favoriteSimilar"
            @visit="visitSimilar"
          />
        </section>
        <section>
          <h2>评论</h2>
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
          <button v-else type="button" @click="goLogin">登录后发表评论</button>
          <LoadingState v-if="commentsLoading" text="正在加载评论..." />
          <div v-else-if="comments.length" class="comment-list">
            <article
              v-for="comment in comments"
              :key="comment.id"
              class="comment-item"
            >
              <div>
                <strong>{{ comment.username || "匿名用户" }}</strong>
                <span
                  >{{ comment.rating || 0 }} 分 ·
                  {{ toDate(comment.created_at) }}</span
                >
              </div>
              <p>{{ comment.content }}</p>
              <button
                v-if="comment.can_delete"
                type="button"
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
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
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
const loggedIn = computed(() => Boolean(localStorage.getItem("access_token")));

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
  background: #f8fafc;
}
.detail {
  display: grid;
  gap: 24px;
  width: min(1080px, calc(100% - 36px));
  margin: 36px auto;
}
.hero,
.facts,
.content,
section {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 22px;
}
.hero {
  display: flex;
  gap: 20px;
}
img {
  width: 86px;
  height: 86px;
  border-radius: 8px;
}
h1,
h2,
p {
  margin-top: 0;
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
button {
  border: 0;
  border-radius: 8px;
  background: #111827;
  color: #fff;
  padding: 11px 14px;
  font-weight: 800;
}
.facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 14px;
}
.facts div,
.chips span {
  display: grid;
  gap: 6px;
  border-radius: 8px;
  background: #f3f4f6;
  padding: 12px;
}
.chips span {
  display: inline-block;
}
.comment-form label {
  display: grid;
  gap: 8px;
  color: #374151;
  font-weight: 750;
}
.comment-form select,
.comment-form textarea {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 10px;
  font: inherit;
}
.comment-form textarea {
  min-height: 96px;
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
  border-top: 1px solid #e5e7eb;
  padding-top: 14px;
}
.comment-item div {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
  color: #6b7280;
}
.comment-item p {
  margin: 0;
  color: #374151;
}
</style>
