<template>
  <AdminLayout>
    <header class="page-head metrics-head">
      <div>
        <span class="eyebrow">Recommendation observability</span>
        <h1>推荐质量分析</h1>
        <p>观察个性化推荐曝光、点击、收藏、回访和候选池质量；本页不会修改推荐排序。</p>
      </div>
      <div class="controls">
        <label>
          时间范围
          <select v-model="lookbackDays" :disabled="loading" @change="refreshCore">
            <option value="7">最近 7 天</option>
            <option value="30">最近 30 天</option>
            <option value="90">最近 90 天</option>
            <option value="all">全部</option>
          </select>
        </label>
        <label class="test-user-toggle"><input v-model="excludeTestUsers" type="checkbox" @change="refreshCore" /> 排除测试账号</label>
        <button type="button" class="snapshot-button" :disabled="loading || snapshotSaving" @click="saveObservationSnapshot">{{ snapshotSaving ? "正在保存…" : "保存本次观察快照" }}</button>
        <button type="button" :disabled="loading" @click="refreshCore">
          {{ loading ? "正在刷新…" : "刷新数据" }}
        </button>
      </div>
    </header>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <LoadingState v-if="loading && !hasCoreData" text="正在加载推荐质量指标…" />

    <template v-else>
      <section class="metric-grid" aria-label="核心推荐质量指标">
        <MetricCard label="总曝光" :value="formatNumber(summary.impressions)" />
        <MetricCard label="总点击" :value="formatNumber(summary.clicks)" />
        <MetricCard label="总收藏" :value="formatNumber(summary.favorites)" />
        <MetricCard label="总回访" :value="formatNumber(summary.repeat_visits)" />
        <MetricCard label="CTR" :value="formatPercent(summary.ctr)" accent />
        <MetricCard label="收藏率" :value="formatPercent(summary.favorite_rate)" />
        <MetricCard label="收藏 / 点击" :value="formatPercent(summary.favorite_per_click_rate)" />
        <MetricCard label="回访率" :value="formatPercent(summary.repeat_visit_rate)" />
      </section>

      <section v-if="!hasEvents" class="empty-banner" role="status">
        暂无真实行为数据，用户产生推荐曝光和点击后将在此显示。
      </section>

      <section class="panel quality-panel">
        <div class="panel-head"><div><h2>数据质量</h2><span>只读诊断；不会修改真实行为事件。</span></div><span class="diagnostic" :class="qualityStatus(dataQuality.status)">{{ qualityText(dataQuality.status) }}</span></div>
        <div class="quality-events"><span>事件总量 <b>{{ formatNumber(dataQuality.total_events) }}</b></span><span>曝光 <b>{{ formatNumber(dataQuality.impressions) }}</b></span><span>点击 <b>{{ formatNumber(dataQuality.clicks) }}</b></span><span>收藏 <b>{{ formatNumber(dataQuality.favorites) }}</b></span><span>回访 <b>{{ formatNumber(dataQuality.repeat_visits) }}</b></span></div>
        <div v-if="qualityIssues.length" class="quality-issues"><span v-for="item in qualityIssues" :key="item.metric" :class="item.severity === 'error' ? 'danger' : 'warning'">{{ item.message }}：{{ formatNumber(item.count) }}</span></div>
        <p v-else class="quality-ok">✓ 数据正常</p>
      </section>

      <section class="panel readiness-panel">
        <div class="panel-head"><div><h2>Phase 2.3 数据准备度</h2><span>达到全部观察门槛前，不会启用行为画像融合。</span></div><span class="diagnostic" :class="readiness.ready ? 'good' : 'warning'">{{ readiness.ready ? '已满足启动条件' : '尚未达到启动条件' }}</span></div>
        <div class="readiness-grid"><div v-for="item in readinessGroups" :key="item.key"><span>{{ item.label }}</span><b>{{ item.percent }}%</b><i><em :style="{ width: `${item.percent}%` }"></em></i></div></div>
        <p v-if="readinessRemaining.length" class="readiness-remaining">还需要：{{ readinessRemaining.map((item) => `${readinessLabel(item.metric)} ${item.remaining}`).join('；') }}</p>
        <p v-else class="quality-ok">所有已定义门槛均已满足；仍需人工检查趋势是否稳定。</p>
      </section>

      <section class="panel snapshot-panel">
        <div class="panel-head"><div><h2>观察期快照</h2><span>保存当前聚合统计，供 phase1-v1 与未来算法版本对比；不复制或修改原始事件。</span></div><button type="button" :disabled="snapshotSaving" @click="saveObservationSnapshot">保存本次观察快照</button></div>
        <div v-if="snapshotHistory.length" class="snapshot-list">
          <div v-for="item in snapshotHistory" :key="item.snapshot_id" class="snapshot-item"><div><b>{{ item.algorithm_version }}</b><span>{{ formatDate(item.created_at) }} · {{ formatLookback(item.lookback_days) }}</span></div><div>曝光 {{ formatNumber(item.summary?.impressions) }} · CTR {{ formatPercent(item.summary?.ctr) }} · <span :class="item.readiness?.ready ? 'good' : 'warning'">{{ item.readiness?.ready ? 'ready' : 'not ready' }}</span></div></div>
        </div>
        <EmptyState v-else title="尚无观察快照" description="管理员可在任意观察时点保存当前聚合结果。" />
        <div v-if="snapshotHistory.length >= 2" class="snapshot-compare"><label>基准快照<select v-model="leftSnapshotId"><option v-for="item in snapshotHistory" :key="item.snapshot_id" :value="item.snapshot_id">{{ snapshotOption(item) }}</option></select></label><label>对比快照<select v-model="rightSnapshotId"><option v-for="item in snapshotHistory" :key="item.snapshot_id" :value="item.snapshot_id">{{ snapshotOption(item) }}</option></select></label><button type="button" @click="compareObservationSnapshots">比较</button></div>
        <p v-if="snapshotComparison" class="snapshot-delta">{{ snapshotComparison.same_algorithm_version ? '同一算法版本趋势' : '跨算法版本基础对比' }}：曝光 {{ signedNumber(snapshotComparison.delta?.impressions) }}，点击 {{ signedNumber(snapshotComparison.delta?.clicks) }}，CTR {{ signedPercent(snapshotComparison.delta?.ctr) }}，收藏率 {{ signedPercent(snapshotComparison.delta?.favorite_rate) }}。</p>
      </section>

      <nav class="metric-tabs" aria-label="推荐质量分析模块">
        <button :class="{ active: activeTab === 'overview' }" @click="selectTab('overview')">趋势与批次</button>
        <button :class="{ active: activeTab === 'segments' }" @click="selectTab('segments')">分群表现</button>
        <button :class="{ active: activeTab === 'websites' }" @click="selectTab('websites')">网站表现</button>
        <button :class="{ active: activeTab === 'overlap' }" @click="selectTab('overlap')">画像重合度</button>
      </nav>

      <template v-if="activeTab === 'overview'">
        <div class="panel-grid trend-grid">
          <section class="panel">
            <div class="panel-head"><h2>行为量趋势</h2><span>按日聚合</span></div>
            <TrendBars v-if="trend.length" :rows="trend" />
            <EmptyState v-else title="暂无趋势数据" description="产生推荐行为后，将按日显示曝光、点击、收藏与回访。" />
          </section>
          <section class="panel">
            <div class="panel-head"><h2>CTR 趋势</h2><span>按日聚合</span></div>
            <TrendLine v-if="trend.length" :rows="trend" />
            <EmptyState v-else title="暂无 CTR 数据" description="曝光和点击产生后即可观察 CTR 变化。" />
          </section>
        </div>

        <section class="panel source-panel">
          <div class="panel-head"><h2>推荐来源比例</h2><span>观察目标：个性化约 70%，通用约 30%</span></div>
          <div class="source-grid">
            <SourceRatio label="个性化" :value="sourceRatios.personalized" target="60%–80% 为接近目标" />
            <SourceRatio label="通用" :value="sourceRatios.general" target="作为自然排序观察项" />
            <SourceRatio label="回补" :value="sourceRatios.fallback" target="不设强制配额" />
          </div>
        </section>

        <div class="panel-grid observation-grid">
          <section class="panel"><div class="panel-head"><h2>match_score 分层</h2><span>验证高匹配分是否带来更高 CTR。</span></div><div v-if="matchScoreRows.length" class="table-wrap"><table><thead><tr><th>分数段</th><th>曝光</th><th>点击</th><th>CTR</th><th>收藏率</th><th>回访</th></tr></thead><tbody><tr v-for="item in matchScoreRows" :key="item.dimension"><td>{{ item.dimension }}</td><td>{{ formatNumber(item.impressions) }}</td><td>{{ formatNumber(item.clicks) }}</td><td>{{ formatPercent(item.ctr) }}</td><td>{{ formatPercent(item.favorite_rate) }}</td><td>{{ formatNumber(item.repeat_visits) }}</td></tr></tbody></table></div><EmptyState v-else title="暂无分层数据" description="新产生的推荐事件会记录 match_score，用于后续验证。" /></section>
          <section class="panel"><div class="panel-head"><h2>推荐来源对照</h2><span>仅观察 personalized / general / fallback 表现。</span></div><div v-if="personalizationRows.length" class="table-wrap"><table><thead><tr><th>类型</th><th>曝光</th><th>CTR</th><th>收藏率</th><th>回访率</th></tr></thead><tbody><tr v-for="item in personalizationRows" :key="item.dimension"><td>{{ item.dimension }}</td><td>{{ formatNumber(item.impressions) }}</td><td>{{ formatPercent(item.ctr) }}</td><td>{{ formatPercent(item.favorite_rate) }}</td><td>{{ formatPercent(item.repeat_visit_rate) }}</td></tr></tbody></table></div><EmptyState v-else title="暂无对照数据" description="不会据此自动调整 70/30 或推荐排序。" /></section>
        </div>

        <div class="panel-grid observation-grid">
          <section class="panel"><div class="panel-head"><h2>primary_need 行为表现</h2><span>问卷核心需求与真实行为的对照。</span></div><div v-if="primaryNeedRows.length" class="table-wrap"><table><thead><tr><th>需求</th><th>曝光</th><th>CTR</th><th>收藏率</th><th>回访率</th></tr></thead><tbody><tr v-for="item in primaryNeedRows" :key="item.dimension"><td>{{ item.dimension }}</td><td>{{ formatNumber(item.impressions) }}</td><td>{{ formatPercent(item.ctr) }}</td><td>{{ formatPercent(item.favorite_rate) }}</td><td>{{ formatPercent(item.repeat_visit_rate) }}</td></tr></tbody></table></div><EmptyState v-else title="暂无需求数据" description="真实样本积累后将显示。" /></section>
          <section class="panel"><div class="panel-head"><h2>tag 兴趣观察</h2><span>仅统计，尚不写入行为画像或排序。</span></div><div v-if="tagRows.length" class="table-wrap"><table><thead><tr><th>标签</th><th>曝光</th><th>CTR</th><th>收藏率</th><th>回访</th></tr></thead><tbody><tr v-for="item in tagRows.slice(0, 12)" :key="item.dimension"><td>{{ item.dimension }}</td><td>{{ formatNumber(item.impressions) }}</td><td>{{ formatPercent(item.ctr) }}</td><td>{{ formatPercent(item.favorite_rate) }}</td><td>{{ formatNumber(item.repeat_visits) }}</td></tr></tbody></table></div><EmptyState v-else title="暂无标签数据" description="真实样本积累后将显示。" /></section>
        </div>

        <section class="panel">
          <div class="panel-head"><h2>推荐批次质量</h2><span>重复率是诊断信号，不是排序规则</span></div>
          <div v-if="batches.length" class="table-wrap">
            <table>
              <thead><tr><th>批次</th><th>画像 / 批次</th><th>曝光</th><th>点击</th><th>CTR</th><th>标签覆盖</th><th>上一批重复</th><th>来源比例</th></tr></thead>
              <tbody>
                <tr v-for="item in batches" :key="item.batch_id">
                  <td class="mono" :title="item.batch_id">{{ shortBatchId(item.batch_id) }}</td>
                  <td>{{ profileText(item) }}<small>第 {{ item.display_batch_index ?? '-' }} 批</small></td>
                  <td>{{ formatNumber(item.impressions) }}</td><td>{{ formatNumber(item.clicks) }}</td><td>{{ formatPercent(item.ctr) }}</td>
                  <td>{{ item.tag_coverage || 0 }}</td>
                  <td><span class="diagnostic" :class="repeatStatus(item.batch_repeat_rate)">{{ formatPercent(item.batch_repeat_rate) }}</span></td>
                  <td>{{ formatPercent(item.personalized_ratio) }} / {{ formatPercent(item.general_ratio) }} / {{ formatPercent(item.fallback_ratio) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <EmptyState v-else title="暂无批次数据" description="推荐卡片实际渲染并上报曝光后，会在这里显示批次健康度。" />
        </section>
      </template>

      <section v-else-if="activeTab === 'segments'" class="panel">
        <div class="panel-head segment-head">
          <div><h2>分群表现</h2><span>样本不足只提示，不会修改真实 CTR。</span></div>
          <label>分组<select v-model="segmentGroup" @change="loadSegments"><option v-for="item in segmentOptions" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
        </div>
        <div class="sort-row"><button v-for="item in segmentSorts" :key="item.value" :class="{ active: segmentSort === item.value }" @click="segmentSort = item.value">{{ item.label }}</button></div>
        <LoadingState v-if="sectionLoading.segments" text="正在加载分群指标…" />
        <div v-else-if="segments.length" class="table-wrap">
          <table><thead><tr><th>分群</th><th>曝光</th><th>点击</th><th>收藏</th><th>回访</th><th>CTR</th><th>收藏率</th><th>回访率</th><th>样本</th></tr></thead>
            <tbody><tr v-for="item in sortedSegments" :key="item.dimension"><td>{{ item.dimension || '未分类' }}</td><td>{{ formatNumber(item.impressions) }}</td><td>{{ formatNumber(item.clicks) }}</td><td>{{ formatNumber(item.favorites) }}</td><td>{{ formatNumber(item.repeat_visits) }}</td><td>{{ formatPercent(item.ctr) }}</td><td>{{ formatPercent(item.favorite_rate) }}</td><td>{{ formatPercent(item.repeat_visit_rate) }}</td><td><span :class="sampleClass(item)">{{ sampleText(item) }}</span></td></tr></tbody>
          </table>
        </div>
        <EmptyState v-else title="暂无分群数据" description="当前筛选范围内还没有推荐行为。" />
      </section>

      <section v-else-if="activeTab === 'websites'" class="panel">
        <div class="panel-head segment-head"><div><h2>网站表现</h2><span>CTR 高但曝光少的网站会显示低样本提示。</span></div><label>搜索网站<input v-model.trim="websiteQuery" placeholder="按网站名称搜索" /></label></div>
        <div class="sort-row"><button v-for="item in websiteSorts" :key="item.value" :class="{ active: websiteSort === item.value }" @click="websiteSort = item.value">{{ item.label }}</button></div>
        <LoadingState v-if="sectionLoading.websites" text="正在加载网站表现…" />
        <div v-else-if="filteredWebsites.length" class="table-wrap"><table><thead><tr><th>网站</th><th>曝光</th><th>点击</th><th>CTR</th><th>收藏</th><th>收藏率</th><th>回访</th><th>回访率</th><th>样本</th></tr></thead><tbody><tr v-for="item in filteredWebsites" :key="item.website_id"><td><a v-if="item.url" :href="item.url" target="_blank" rel="noreferrer">{{ item.name || item.website_id }}</a><span v-else>{{ item.name || item.website_id }}</span></td><td>{{ formatNumber(item.impressions) }}</td><td>{{ formatNumber(item.clicks) }}</td><td>{{ formatPercent(item.ctr) }}</td><td>{{ formatNumber(item.favorites) }}</td><td>{{ formatPercent(item.favorite_rate) }}</td><td>{{ formatNumber(item.repeat_visits) }}</td><td>{{ formatPercent(item.repeat_visit_rate) }}</td><td><span :class="sampleClass(item)">{{ sampleText(item) }}</span></td></tr></tbody></table></div>
        <EmptyState v-else title="暂无网站数据" description="当前筛选范围内还没有推荐网站行为。" />
      </section>

      <section v-else class="panel">
        <div class="panel-head"><h2>画像重合度</h2><span>&lt;20% 差异明显，20%–50% 合理共享，&gt;50% 需要关注。</span></div>
        <LoadingState v-if="sectionLoading.overlap" text="正在加载画像重合度…" />
        <div v-else-if="overlaps.length" class="table-wrap"><table><thead><tr><th>画像 A</th><th>画像 B</th><th>共同网站</th><th>Top16 重合</th><th>Jaccard</th><th>诊断</th></tr></thead><tbody><tr v-for="item in overlaps" :key="`${item.left.batch_id}-${item.right.batch_id}`"><td>{{ profileText(item.left) }}</td><td>{{ profileText(item.right) }}</td><td>{{ item.overlap_count }}</td><td>{{ formatPercent(item.overlap_rate) }}</td><td>{{ formatPercent(item.jaccard_rate) }}</td><td><span class="diagnostic" :class="overlapStatus(item.overlap_rate)">{{ overlapText(item.overlap_rate) }}</span></td></tr></tbody></table></div>
        <EmptyState v-else title="暂无画像对比数据" description="至少需要两个不同画像产生实际推荐曝光后，才能比较其 Top16 重合度。" />
      </section>
    </template>
  </AdminLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import AdminLayout from "../../components/admin/AdminLayout.vue";
import MetricCard from "../../components/admin/MetricCard.vue";
import SourceRatio from "../../components/admin/SourceRatio.vue";
import TrendBars from "../../components/admin/TrendBars.vue";
import TrendLine from "../../components/admin/TrendLine.vue";
import EmptyState from "../../components/common/EmptyState.vue";
import LoadingState from "../../components/common/LoadingState.vue";
import { recommendationMetricsAPI, unwrapResponse } from "../../utils/api";
import { errorToast, successToast } from "../../utils/toast";

const loading = ref(false); const error = ref(""); const lookbackDays = ref("30"); const activeTab = ref("overview"); const excludeTestUsers = ref(true);
const summary = ref({}); const trend = ref([]); const batches = ref([]); const segments = ref([]); const websites = ref([]); const overlaps = ref([]); const dataQuality = ref({}); const readiness = ref({});
const matchScoreRows = ref([]); const primaryNeedRows = ref([]); const tagRows = ref([]); const personalizationRows = ref([]);
const snapshotHistory = ref([]); const snapshotSaving = ref(false); const leftSnapshotId = ref(""); const rightSnapshotId = ref(""); const snapshotComparison = ref(null);
const segmentGroup = ref("occupation"); const segmentSort = ref("ctr"); const websiteQuery = ref(""); const websiteSort = ref("impressions");
const sectionLoading = reactive({ segments: false, websites: false, overlap: false });
const segmentOptions = [{ value: "occupation", label: "职业" }, { value: "direction", label: "方向" }, { value: "primary_need", label: "核心需求" }, { value: "source", label: "来源" }, { value: "tag", label: "标签" }];
const segmentSorts = [{ value: "ctr", label: "CTR" }, { value: "clicks", label: "点击数" }, { value: "favorites", label: "收藏数" }, { value: "impressions", label: "曝光数" }];
const websiteSorts = [{ value: "impressions", label: "曝光最高" }, { value: "ctr", label: "CTR 最高" }, { value: "favorites", label: "收藏最多" }, { value: "repeat_visits", label: "回访最多" }];
const params = () => ({ lookback_days: lookbackDays.value, exclude_test_users: excludeTestUsers.value });
const hasCoreData = computed(() => Object.keys(summary.value).length > 0);
const hasEvents = computed(() => Number(summary.value.event_count || 0) > 0);
const sourceRatios = computed(() => { const total = batches.value.reduce((sum, item) => sum + Number(item.impressions || 0), 0); const ratio = (key) => total ? batches.value.reduce((sum, item) => sum + Number(item[key] || 0), 0) * 100 / total : 0; return { personalized: formatPercent(ratio("personalized_impressions")), general: formatPercent(ratio("general_impressions")), fallback: formatPercent(ratio("fallback_impressions")) }; });
const sortedSegments = computed(() => [...segments.value].sort((left, right) => Number(right[segmentSort.value] || 0) - Number(left[segmentSort.value] || 0)));
const filteredWebsites = computed(() => [...websites.value].filter((item) => !websiteQuery.value || String(item.name || "").toLowerCase().includes(websiteQuery.value.toLowerCase())).sort((left, right) => Number(right[websiteSort.value] || 0) - Number(left[websiteSort.value] || 0)));
const qualityIssues = computed(() => (dataQuality.value.issues || []).filter((item) => Number(item.count || 0) > 0));
const readinessRemaining = computed(() => readiness.value.remaining || []);
const readinessGroups = computed(() => {
  const ratio = (items) => { const list = Array.isArray(items) ? items : []; return list.length ? Math.round(list.filter((item) => item?.passed).length * 100 / list.length) : 0; };
  const profile = readiness.value.profile_coverage || {}; const batches = readiness.value.batch_coverage || {}; const quality = readiness.value.data_quality || {};
  return [
    { key: "events", label: "事件规模", percent: ratio(Object.values(readiness.value.events || {})) },
    { key: "profiles", label: "画像覆盖", percent: ratio([profile.occupations, profile.direction_primary_need_combinations]) },
    { key: "batches", label: "批次数量", percent: ratio([batches, { passed: batches.multiple_users }]) },
    { key: "quality", label: "数据质量", percent: quality.passed ? 100 : 0 },
    { key: "trend", label: "趋势稳定", percent: readiness.value.trend_stability?.passed ? 100 : 0 },
  ];
});
function formatNumber(value) { return new Intl.NumberFormat("zh-CN").format(Number(value || 0)); }
function formatPercent(value) { return `${Number(value || 0).toFixed(1)}%`; }
function formatDate(value) { if (!value) return "刚刚"; const date = new Date(value); return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString("zh-CN", { hour12: false }); }
function formatLookback(value) { return String(value) === "all" ? "全部时间" : `最近 ${value || 0} 天`; }
function snapshotOption(item) { return `${item.algorithm_version} · ${formatDate(item.created_at)}`; }
function signedNumber(value) { const number = Number(value || 0); return `${number > 0 ? "+" : ""}${formatNumber(number)}`; }
function signedPercent(value) { const number = Number(value || 0); return `${number > 0 ? "+" : ""}${number.toFixed(1)}pp`; }
function sampleText(item) { return Number(item.impressions || 0) < 20 ? "样本不足" : "样本充足"; }
function sampleClass(item) { return Number(item.impressions || 0) < 20 ? "sample-low" : "sample-ok"; }
function profileText(item = {}) { return [item.occupation, item.direction, item.primary_need].filter(Boolean).join(" / ") || "未标记画像"; }
function shortBatchId(value) { return String(value || "-").length > 18 ? `${String(value).slice(0, 18)}…` : String(value || "-"); }
function repeatStatus(value) { const number = Number(value || 0); return number > 25 ? "danger" : number > 10 ? "warning" : "good"; }
function overlapStatus(value) { const number = Number(value || 0); return number > 50 ? "warning" : number < 20 ? "good" : "neutral"; }
function overlapText(value) { const number = Number(value || 0); return number > 50 ? "需要关注" : number < 20 ? "差异明显" : "合理共享"; }
function qualityStatus(value) { return value === "healthy" ? "good" : value === "error" ? "danger" : "warning"; }
function qualityText(value) { return value === "healthy" ? "数据正常" : value === "error" ? "需要处理" : "需要关注"; }
function readinessLabel(value) { return ({ impressions: "曝光", clicks: "点击", favorites: "收藏", repeat_visits: "回访", occupations: "个职业画像", profile_combinations: "个画像组合", recommendation_batches: "个推荐批次", batch_users: "个批次用户", observation_days: "个观察日" })[value] || value; }
async function request(fn) { return unwrapResponse(await fn()) || {}; }
async function refreshCore() { loading.value = true; error.value = ""; try { const [summaryData, trendData, batchData, qualityData, readinessData, scoreData, needData, tagData, personalizationData] = await Promise.all([request(() => recommendationMetricsAPI.getSummary(params())), request(() => recommendationMetricsAPI.getSummary({ ...params(), group_by: "day" })), request(() => recommendationMetricsAPI.getBatches(params())), request(() => recommendationMetricsAPI.getDataQuality(params())), request(() => recommendationMetricsAPI.getPhase23Readiness(params())), request(() => recommendationMetricsAPI.getSummary({ ...params(), group_by: "match_score_bucket" })), request(() => recommendationMetricsAPI.getSummary({ ...params(), group_by: "primary_need" })), request(() => recommendationMetricsAPI.getSummary({ ...params(), group_by: "tag" })), request(() => recommendationMetricsAPI.getSummary({ ...params(), group_by: "personalization_type" }))]); summary.value = summaryData.summary || {}; trend.value = Array.isArray(trendData.summary) ? trendData.summary : []; batches.value = batchData.items || []; dataQuality.value = qualityData || {}; readiness.value = readinessData || {}; matchScoreRows.value = Array.isArray(scoreData.summary) ? scoreData.summary : []; primaryNeedRows.value = Array.isArray(needData.summary) ? needData.summary : []; tagRows.value = Array.isArray(tagData.summary) ? tagData.summary : []; personalizationRows.value = Array.isArray(personalizationData.summary) ? personalizationData.summary : []; } catch (err) { error.value = err.response?.data?.msg || "推荐质量指标加载失败"; errorToast(error.value); } finally { loading.value = false; void loadObservationSnapshots(); } }
async function loadObservationSnapshots() { try { const data = await request(() => recommendationMetricsAPI.getObservationSnapshots({ limit: 12 })); snapshotHistory.value = data.items || []; if (!rightSnapshotId.value && snapshotHistory.value[0]) rightSnapshotId.value = snapshotHistory.value[0].snapshot_id; if (!leftSnapshotId.value && snapshotHistory.value[1]) leftSnapshotId.value = snapshotHistory.value[1].snapshot_id; } catch (err) { error.value = err.response?.data?.msg || "观察快照加载失败"; } }
async function saveObservationSnapshot() { snapshotSaving.value = true; try { const data = await request(() => recommendationMetricsAPI.createObservationSnapshot(params())); successToast("观察快照已保存"); await loadObservationSnapshots(); rightSnapshotId.value = data.snapshot_id || rightSnapshotId.value; } catch (err) { error.value = err.response?.data?.msg || "观察快照保存失败"; errorToast(error.value); } finally { snapshotSaving.value = false; } }
async function compareObservationSnapshots() { if (!leftSnapshotId.value || !rightSnapshotId.value || leftSnapshotId.value === rightSnapshotId.value) { errorToast("请选择两份不同的观察快照"); return; } try { snapshotComparison.value = await request(() => recommendationMetricsAPI.compareObservationSnapshots({ left_snapshot_id: leftSnapshotId.value, right_snapshot_id: rightSnapshotId.value })); } catch (err) { error.value = err.response?.data?.msg || "观察快照比较失败"; errorToast(error.value); } }
async function loadSegments() { sectionLoading.segments = true; try { const data = await request(() => recommendationMetricsAPI.getSummary({ ...params(), group_by: segmentGroup.value })); segments.value = Array.isArray(data.summary) ? data.summary : []; } catch (err) { error.value = err.response?.data?.msg || "分群指标加载失败"; } finally { sectionLoading.segments = false; } }
async function loadWebsites() { sectionLoading.websites = true; try { const data = await request(() => recommendationMetricsAPI.getWebsites({ ...params(), limit: 500 })); websites.value = data.items || []; } catch (err) { error.value = err.response?.data?.msg || "网站指标加载失败"; } finally { sectionLoading.websites = false; } }
async function loadOverlap() { sectionLoading.overlap = true; try { const data = await request(() => recommendationMetricsAPI.getProfileOverlap(params())); overlaps.value = data.items || []; } catch (err) { error.value = err.response?.data?.msg || "画像重合度加载失败"; } finally { sectionLoading.overlap = false; } }
function selectTab(tab) { activeTab.value = tab; if (tab === "segments" && !segments.value.length) void loadSegments(); if (tab === "websites" && !websites.value.length) void loadWebsites(); if (tab === "overlap" && !overlaps.value.length) void loadOverlap(); }
onMounted(refreshCore);
</script>

<style>
@import "./adminTable.css";
.metrics-head { display:flex; justify-content:space-between; align-items:end; gap:20px; }.eyebrow{color:#f06450;font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase}.controls,.controls label,.segment-head label{display:flex;align-items:end;gap:8px}.controls label,.segment-head label{display:grid;font-size:13px;font-weight:750;color:#475569}.controls select,.segment-head select,.segment-head input{border:1px solid var(--color-border);border-radius:12px;padding:9px 10px;background:#fff;font:inherit}.test-user-toggle{display:flex!important;align-items:center!important;grid-template-columns:none!important;white-space:nowrap}.test-user-toggle input{accent-color:#f06450}.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:18px}.metric-card{display:grid;gap:8px;padding:16px;border:1px solid var(--color-border);border-radius:14px;background:#fff}.metric-card span,.source-ratio span,.panel-head span{color:#64748b;font-size:13px;font-weight:700}.metric-card strong{font-size:26px;color:#172033}.metric-card.accent{border-color:#fdbaae;background:#fff8f6}.metric-card.accent strong{color:#d9503d}.empty-banner{margin:0 0 18px;padding:13px 15px;border:1px solid #fed7aa;border-radius:12px;background:#fffbeb;color:#92400e}.quality-events{display:flex;flex-wrap:wrap;gap:18px;color:#64748b;font-size:13px}.quality-events b{margin-left:4px;color:#172033}.quality-issues{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}.quality-ok{margin:12px 0 0;color:#047857;font-weight:750}.readiness-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}.readiness-grid>div{display:grid;gap:7px}.readiness-grid span{color:#64748b;font-size:13px}.readiness-grid b{font-size:22px;color:#172033}.readiness-grid i{height:8px;border-radius:999px;background:#e2e8f0;overflow:hidden}.readiness-grid em{display:block;height:100%;border-radius:inherit;background:#f06450}.readiness-remaining{margin:16px 0 0;color:#92400e}.snapshot-button{white-space:nowrap}.snapshot-list{display:grid;gap:8px}.snapshot-item{display:flex;justify-content:space-between;gap:16px;padding:12px 14px;border:1px solid #edf2f7;border-radius:12px;background:#f8fafc;color:#475569;font-size:13px}.snapshot-item div{display:grid;gap:4px}.snapshot-item b{color:#172033}.snapshot-item span{color:#64748b}.snapshot-compare{display:flex;align-items:end;gap:10px;margin-top:16px}.snapshot-compare label{display:grid;gap:6px;color:#475569;font-size:13px;font-weight:750}.snapshot-compare select{min-width:220px;border:1px solid var(--color-border);border-radius:10px;padding:8px;background:#fff;font:inherit}.snapshot-delta{margin:14px 0 0;padding:11px 13px;border-radius:10px;background:#fff8f6;color:#9f3f30}.metric-tabs,.sort-row{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 18px}.metric-tabs button,.sort-row button{color:#475569}.metric-tabs button.active,.sort-row button.active{background:#172033;border-color:#172033;color:#fff}.panel-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-bottom:16px}.panel{border:1px solid var(--color-border);border-radius:16px;background:#fff;padding:18px;margin-bottom:16px}.panel-head{display:flex;align-items:start;justify-content:space-between;gap:14px;margin-bottom:16px}.panel-head h2{margin:0 0 4px;font-size:18px;color:#172033}.source-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.source-ratio{display:grid;gap:7px;padding:14px;border-radius:12px;background:#f8fafc}.source-ratio strong{font-size:24px;color:#172033}.source-ratio small{color:#64748b}.trend-bars{display:grid;gap:9px}.trend-row{display:grid;grid-template-columns:42px 1fr;gap:8px;align-items:center;font-size:12px;color:#64748b}.trend-row>div{display:grid;gap:3px}.trend-row i{display:block;height:6px;min-width:2px;border-radius:999px}.impressions{background:#94a3b8}.clicks{background:#3b82f6}.favorites{background:#f97316}.repeat{background:#10b981}.trend-bars p{display:flex;gap:10px;margin:4px 0 0;font-size:11px;color:#64748b}.trend-bars p b{font-weight:700}.trend-line svg{width:100%;height:150px}.trend-line line{stroke:#e2e8f0}.trend-line polyline{fill:none;stroke:#f06450;stroke-width:3}.trend-line{display:grid;grid-template-columns:repeat(auto-fit,minmax(62px,1fr));gap:6px}.trend-line svg{grid-column:1/-1}.trend-point{display:grid;gap:3px;font-size:11px;color:#64748b}.trend-point b{color:#172033}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:820px}th,td{padding:11px 10px;border-bottom:1px solid #edf2f7;text-align:left;vertical-align:top;font-size:13px}th{color:#64748b;font-weight:800;white-space:nowrap}td small{display:block;margin-top:3px;color:#94a3b8}.mono{font-family:ui-monospace,monospace;font-size:12px}.diagnostic,.sample-low,.sample-ok{display:inline-flex;padding:4px 8px;border-radius:999px;font-size:12px;font-weight:750}.good,.sample-ok{background:#ecfdf5;color:#047857}.warning,.sample-low{background:#fffbeb;color:#b45309}.danger{background:#fef2f2;color:#b91c1c}.neutral{background:#f1f5f9;color:#475569}.segment-head{align-items:end}.error{color:#b91c1c;font-weight:750}@media(max-width:780px){.metrics-head,.panel-head{align-items:start;flex-direction:column}.panel-grid,.source-grid{grid-template-columns:1fr}.readiness-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.snapshot-item,.snapshot-compare{align-items:stretch;flex-direction:column}.controls{align-items:start;flex-wrap:wrap}}
</style>
