<template>
  <AdminLayout>
    <div class="page-head">
      <h1>爬虫审核</h1>
      <p>AI 结果仅作建议；审核、预览和发布均需管理员明确操作。</p>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="layout">
      <section>
        <button type="button" @click="load" :disabled="loading">{{ loading ? "加载中…" : "刷新" }}</button>
        <ul class="reviews">
          <li v-for="review in reviews" :key="review.review_uid">
            <button type="button" :class="{ selected: selected?.review_uid === review.review_uid }" @click="selectReview(review.review_uid)">
              <strong>{{ review.selected_title || review.review_uid }}</strong>
              <small>{{ review.status }} · v{{ review.version }}</small>
            </button>
          </li>
        </ul>
      </section>
      <section v-if="selected" class="detail">
        <label>标题<input v-model.trim="form.selected_title" /></label>
        <label>摘要<textarea v-model.trim="form.selected_summary" /></label>
        <label>描述<textarea v-model.trim="form.selected_description" /></label>
        <label>分类<input v-model.trim="form.selected_category" /></label>
        <label>地区<input v-model.trim="form.selected_region" /></label>
        <label>语言<input v-model.trim="form.selected_language" /></label>
        <label>URL<input v-model.trim="form.selected_url" /></label>
        <p class="risk">风险确认：{{ selected.risk_acknowledgements || "无" }}<br />覆盖理由：{{ selected.override_reasons || "无" }}</p>
        <div class="actions">
          <button v-if="selected.status === 'pending'" type="button" :disabled="actionBusy" @click="assign">领取审核</button>
          <button v-if="selected.status === 'reviewing'" type="button" :disabled="actionBusy" @click="approve">保存并通过</button>
          <button v-if="['pending', 'reviewing'].includes(selected.status)" class="danger" type="button" :disabled="actionBusy" @click="reject">拒绝</button>
          <button v-if="selected.status === 'approved'" type="button" :disabled="actionBusy" @click="preview">生成发布预览</button>
          <button v-if="selected.status === 'publish_ready'" class="primary" type="button" :disabled="actionBusy" @click="publish">确认发布</button>
        </div>
        <pre v-if="previewData">{{ JSON.stringify(previewData, null, 2) }}</pre>
      </section>
      <p v-else>请选择一个审核项。</p>
    </div>
  </AdminLayout>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import AdminLayout from "../../components/admin/AdminLayout.vue";
import { adminAPI, unwrapList, unwrapResponse } from "../../utils/api";
import { errorToast, successToast } from "../../utils/toast";

const reviews = ref([]), selected = ref(null), loading = ref(false), actionBusy = ref(false), error = ref(""), previewData = ref(null);
const form = reactive({ selected_title: "", selected_summary: "", selected_description: "", selected_category: "", selected_region: "", selected_language: "", selected_url: "" });
const syncForm = (review) => Object.assign(form, Object.fromEntries(Object.keys(form).map((key) => [key, review?.[key] || ""])));
const errorMessage = (err) => err.response?.data?.msg || "审核操作失败";
async function load() { loading.value = true; error.value = ""; try { reviews.value = unwrapList(await adminAPI.getCrawlerReviews()); if (selected.value) await selectReview(selected.value.review_uid); } catch (err) { error.value = errorMessage(err); errorToast(error.value); } finally { loading.value = false; } }
async function selectReview(uid) { try { selected.value = unwrapResponse(await adminAPI.getCrawlerReview(uid)); syncForm(selected.value); previewData.value = null; } catch (err) { error.value = errorMessage(err); errorToast(error.value); } }
const changes = () => ({ ...form });
async function action(request) { actionBusy.value = true; try { const data = unwrapResponse(await request()); if (data?.review_uid) { selected.value = data; syncForm(data); } successToast("操作成功"); await load(); } catch (err) { error.value = err.response?.status === 409 ? "审核版本已变化，请刷新后重试" : errorMessage(err); errorToast(error.value); } finally { actionBusy.value = false; } }
const assign = () => action(() => adminAPI.assignCrawlerReview(selected.value.review_uid, { reviewer_id: "admin", version: selected.value.version }));
const approve = () => action(() => adminAPI.approveCrawlerReview(selected.value.review_uid, { version: selected.value.version, changes: changes() }));
async function reject() { if (window.confirm("确认拒绝该审核项？")) await action(() => adminAPI.rejectCrawlerReview(selected.value.review_uid, { version: selected.value.version })); }
async function preview() { actionBusy.value = true; try { previewData.value = unwrapResponse(await adminAPI.previewCrawlerPublish(selected.value.review_uid, { version: selected.value.version })); selected.value = previewData.value.review; syncForm(selected.value); await load(); } catch (err) { error.value = err.response?.status === 409 ? "审核版本已变化，请刷新后重试" : errorMessage(err); errorToast(error.value); } finally { actionBusy.value = false; } }
async function publish() { if (window.confirm("确认发布到导航站？")) await action(() => adminAPI.publishCrawlerReview(selected.value.review_uid, { confirm: true, version: selected.value.version })); }
onMounted(load);
</script>

<style scoped>
.layout { display: grid; grid-template-columns: minmax(220px, .7fr) minmax(360px, 1.3fr); gap: 20px; }
.reviews { padding: 0; list-style: none; }.reviews button { width: 100%; margin: 4px 0; text-align: left; }.reviews small { display: block; }.selected { outline: 2px solid var(--color-primary); }
.detail { display: grid; gap: 10px; }.detail label { display: grid; gap: 4px; }.detail input, .detail textarea { width: 100%; }.detail textarea { min-height: 72px; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; }.primary { background: var(--color-primary); color: white; }.danger { color: #b42318; }.risk, pre { overflow: auto; background: var(--color-soft); padding: 10px; } .error { color: #b42318; }
@media (max-width: 860px) { .layout { grid-template-columns: 1fr; } }
</style>
