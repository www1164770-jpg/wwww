<template>
  <AdminLayout>
    <h1>数据概览</h1>
    <p v-if="error" class="error">{{ error }}</p>
    <LoadingState v-if="loading" text="正在加载后台数据..." />
    <template v-else>
      <div class="stats">
        <AdminStatsCard label="总用户数" :value="stats.users" />
        <AdminStatsCard label="新增用户数" :value="stats.new_users" />
        <AdminStatsCard label="网站资源数" :value="stats.sites" />
        <AdminStatsCard label="分类数" :value="stats.categories" />
        <AdminStatsCard label="标签数" :value="stats.tags" />
        <AdminStatsCard label="总点击量" :value="stats.total_clicks" />
        <AdminStatsCard label="总收藏量" :value="stats.total_favorites" />
      </div>
      <div class="dashboard-grid">
        <section>
          <h2>网站点击排行</h2>
          <div v-if="clickRanking.length">
            <div v-for="site in clickRanking" :key="site.id" class="rank-row">
              <span>{{ site.name }}</span>
              <strong>{{ site.click_count || site.clicks || 0 }}</strong>
            </div>
          </div>
          <EmptyState
            v-else
            title="暂无排行"
            description="有访问数据后会显示网站点击排行。"
          />
        </section>
        <section>
          <h2>网站收藏排行</h2>
          <div v-if="favoriteRanking.length">
            <div
              v-for="site in favoriteRanking"
              :key="site.id"
              class="rank-row"
            >
              <span>{{ site.name }}</span>
              <strong>{{ site.favorite_count || 0 }}</strong>
            </div>
          </div>
          <EmptyState
            v-else
            title="暂无排行"
            description="有收藏数据后会显示网站收藏排行。"
          />
        </section>
        <section>
          <h2>职业分布</h2>
          <div v-if="occupationDistribution.length">
            <div
              v-for="item in occupationDistribution"
              :key="item.occupation || item.name"
              class="rank-row"
            >
              <span>{{ item.occupation || item.name || "未填写" }}</span>
              <strong>{{ item.count || 0 }}</strong>
            </div>
          </div>
          <EmptyState
            v-else
            title="暂无数据"
            description="用户填写问卷后会显示职业分布。"
          />
        </section>
        <section>
          <h2>分类访问排行</h2>
          <div v-if="categoryVisitRanking.length">
            <div
              v-for="site in categoryVisitRanking"
              :key="site.id || site.name"
              class="rank-row"
            >
              <span>{{ site.name }}</span>
              <strong>{{ site.visit_count || site.count || 0 }}</strong>
            </div>
          </div>
          <EmptyState
            v-else
            title="暂无排行"
            description="有访问数据后会显示分类访问排行。"
          />
        </section>
      </div>
    </template>
  </AdminLayout>
</template>

<script setup>
import { onMounted, ref } from "vue";
import AdminLayout from "../../components/admin/AdminLayout.vue";
import AdminStatsCard from "../../components/admin/AdminStatsCard.vue";
import EmptyState from "../../components/common/EmptyState.vue";
import LoadingState from "../../components/common/LoadingState.vue";
import { adminAPI } from "../../utils/api";

const loading = ref(false);
const error = ref("");
const stats = ref({});
const clickRanking = ref([]);
const favoriteRanking = ref([]);
const occupationDistribution = ref([]);
const categoryVisitRanking = ref([]);

function payload(response) {
  return response?.data?.data ?? response?.data ?? {};
}

onMounted(async () => {
  loading.value = true;
  error.value = "";
  try {
    const data = payload(await adminAPI.getDashboard());
    stats.value = data.stats || data;
    clickRanking.value = data.click_ranking || data.top_click_sites || [];
    favoriteRanking.value =
      data.favorite_ranking || data.top_favorite_sites || [];
    occupationDistribution.value = data.occupation_distribution || [];
    categoryVisitRanking.value =
      data.category_visit_ranking || data.category_ranking || [];
  } catch (err) {
    error.value = err.response?.data?.msg || "后台数据加载失败";
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
h1,
h2 {
  margin-top: 0;
}
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 14px;
  margin-bottom: 22px;
}
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}
section {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
}
.rank-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border-top: 1px solid #f3f4f6;
  padding: 10px 0;
}
.error {
  color: #b91c1c;
  font-weight: 750;
}
</style>
