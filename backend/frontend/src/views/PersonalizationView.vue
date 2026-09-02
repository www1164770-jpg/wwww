<template>
  <div class="page personalization-page">
    <AppHeader />
    <main class="personalization-shell">
      <header class="personalization-header">
        <div class="header-copy"><p class="eyebrow">外观偏好</p><AnimatedPageTitle>个性化设置</AnimatedPageTitle><p>背景切换后会先校验可读性，再开放其他视觉调整。</p></div>
        <RouterLink class="back-link" to="/profile">返回个人中心</RouterLink>
      </header>
      <div class="personalization-layout settings-layout">
        <div class="settings-content">
          <section id="background-settings" class="editor-card personalization-section">
            <h2>背景设置</h2>
            <div class="mode-grid"><button v-for="item in modes" :key="item.id" :class="{ selected: draft.background.type === item.id }" @click="draft.background.type = item.id">{{ item.label }}</button></div>
            <label v-if="draft.background.type === 'color'">背景颜色 <input v-model="draft.background.color" type="color" /><input v-model="draft.background.color" pattern="^#[0-9A-Fa-f]{6}$" aria-label="背景 HEX 颜色" /></label>
            <div v-if="draft.background.type === 'gradient'" class="control-group"><label>渐变角度 <input v-model.number="draft.gradient.angle" type="range" min="0" max="360" /></label><div v-for="(stop, index) in draft.gradient.stops" :key="index" class="gradient-stop"><input v-model="stop.color" type="color" :aria-label="`渐变颜色 ${index + 1}`" /><input v-model.number="stop.position" type="range" min="0" max="100" :aria-label="`渐变位置 ${index + 1}`" /><button :disabled="draft.gradient.stops.length <= 2" aria-label="删除颜色节点" @click="draft.gradient.stops.splice(index, 1)">删除</button></div><button @click="addStop">添加颜色节点</button></div>
            <div v-if="draft.background.type === 'image'" class="control-group"><label>背景图片 <input accept="image/jpeg,image/png,image/webp" type="file" @change="selectImage" /></label><p class="helper">仅支持 JPG、JPEG、PNG、WEBP，最大 10MB。访客图片保存在浏览器 IndexedDB。</p><label>显示方式 <select v-model="draft.background.size"><option value="cover">铺满 Cover</option><option value="contain">适应 Contain</option><option value="stretch">拉伸 Stretch</option><option value="repeat">平铺 Repeat</option></select></label><fieldset><label>遮罩 <input v-model.number="draft.background.overlay" type="range" min="0" max="70" /></label><label>亮度 <input v-model.number="draft.background.brightness" type="range" min="40" max="160" /></label><label>模糊 <input v-model.number="draft.background.blur" type="range" min="0" max="20" /></label></fieldset></div>

            <div v-if="draft.background.type === 'image'" class="image-editor"><div :class="['device-preview', previewDevice]" @pointerdown="startDrag"><img v-if="store.imageUrl" :src="store.imageUrl" alt="背景实时预览" :style="previewImageStyle" draggable="false" /><span v-else>上传或选择一张背景图后可进行构图</span></div><div class="device-toggle"><button :class="{ selected: previewDevice === 'desktop' }" @click="previewDevice = 'desktop'">桌面端 16:9</button><button :class="{ selected: previewDevice === 'mobile' }" @click="previewDevice = 'mobile'">手机端 9:16</button></div><label>缩放 <input v-model.number="composition.scale" type="range" min="0.5" max="3" step="0.01" /></label><label>旋转 <input v-model.number="composition.rotation" type="range" min="-180" max="180" /></label><label>水平位置 <input v-model.number="composition.positionX" type="range" min="0" max="100" /></label><label>垂直位置 <input v-model.number="composition.positionY" type="range" min="0" max="100" /></label><button class="secondary" type="button" @click="resetImageAdjustments">重置图片调整</button></div>
            <section v-if="store.isLoggedIn" class="background-library" aria-label="我的背景"><div class="library-heading"><div><h3>我的背景</h3><p>最多保存 5 张；缩略图仅通过登录鉴权读取。</p></div><span>{{ store.backgrounds.length }}/5</span></div><p v-if="!store.backgrounds.length" class="empty-library">还没有已上传背景。选择图片并上传后会显示在这里。</p><div v-else class="background-grid"><article v-for="background in store.backgrounds" :key="background.id" :class="{ active: String(draft.background.imageId) === String(background.id) }"><img v-if="background.previewUrl" :src="background.previewUrl" :alt="background.original_name || '我的背景缩略图'" /><div v-else class="thumbnail-placeholder">缩略图加载失败</div><div class="background-meta"><strong>{{ background.original_name || `背景 #${background.id}` }}</strong><small>{{ background.width }} × {{ background.height }}</small></div><label class="privacy-select">隐私 <select :value="background.privacy" @change="changeBackgroundPrivacy(background, $event.target.value)"><option value="private">仅自己可见</option><option value="public">公开</option></select></label><div class="background-actions"><button type="button" @click="useSavedBackground(background)">使用</button><button type="button" class="danger" @click="removeSavedBackground(background)">删除</button></div></article></div></section>
            <div class="recent-list"><h3>最近使用</h3><p v-if="!draft.recent.length" class="helper">保存设置或应用主题后会显示最近使用记录。</p><button v-for="item in draft.recent" :key="item" @click="applyRecent(item)">{{ recentLabel(item) }}</button></div>
            <section v-if="['pending', 'syncing', 'failed'].includes(store.backgroundSyncState.status)" class="background-sync-card" aria-live="polite"><div><h3>本机背景尚未同步</h3><p class="helper">图片仍安全保存在当前浏览器中。已尝试 {{ store.backgroundSyncState.retryCount }}/3 次。</p></div><button type="button" :disabled="store.backgroundSyncState.status === 'syncing' || store.backgroundSyncState.retryCount >= 3" @click="retryBackgroundSync">{{ store.backgroundSyncState.status === 'syncing' ? '正在同步…' : '同步本机背景' }}</button></section>
          </section>

          <section id="official-themes" class="editor-card personalization-section"><div class="official-theme-section"><h2>官方主题</h2><div class="official-theme-grid"><article v-for="theme in officialThemes" :key="theme.key" class="official-theme-card" :class="{ 'is-active': draft.themeKey === theme.key, 'is-favorite': draft.favorites.includes(theme.key) }"><button class="theme-card-main" type="button" @click="selectTheme(theme)"><i class="theme-preview" :style="{ background: `linear-gradient(135deg, ${theme.colors.join(', ')})` }"></i><span class="theme-name">{{ theme.name }}</span><small v-if="draft.themeKey === theme.key" class="theme-active-label">当前使用</small></button><button class="theme-favorite-button" type="button" :class="{ 'is-favorite': draft.favorites.includes(theme.key) }" :aria-label="`${draft.favorites.includes(theme.key) ? '取消收藏' : '收藏主题'} ${theme.name}`" :title="draft.favorites.includes(theme.key) ? '取消收藏' : '收藏主题'" @click.stop="toggleFavorite(theme)">{{ draft.favorites.includes(theme.key) ? '★' : '☆' }}</button></article></div></div><section class="custom-theme-section"><h3>我的主题</h3><p class="helper">保存当前设置可作为自定义主题（登录后同步，最多 5 个）。</p><button class="save-custom-theme" type="button" @click="saveAsTheme">保存为我的主题</button><div v-if="draft.customThemes.length" class="custom-theme-grid"><article v-for="theme in draft.customThemes" :key="theme.key"><strong>{{ theme.name }}</strong><div class="custom-theme-actions"><button type="button" @click="applyCustomTheme(theme)">应用</button><button type="button" @click="renameTheme(theme)">重命名</button><button type="button" @click="removeTheme(theme)">删除</button></div></article></div></section></section>

          <section id="font-settings" class="editor-card personalization-section">
            <fieldset class="setting-section typography-settings">
              <h2>字体设置</h2>
              <div class="setting-group">
                <span class="setting-label">文字颜色</span>
                <div class="text-color-modes" role="radiogroup" aria-label="文字颜色模式">
                  <label
                    v-for="mode in typographyModes"
                    :key="mode.id"
                    class="text-color-mode"
                    :class="{ 'is-selected': draft.typography.mode === mode.id }"
                  >
                    <input v-model="draft.typography.mode" type="radio" :value="mode.id" />
                    <span>{{ mode.label }}</span>
                  </label>
                </div>
                <p class="setting-help">自动模式继续根据当前背景选择可读文字；自定义模式始终保留你选择的颜色。</p>
              </div>
              <div v-if="draft.typography.mode === 'custom'" class="custom-text-color">
                <label class="color-picker-control">
                  <span>选择颜色</span>
                  <input
                    :value="draft.typography.color"
                    type="color"
                    aria-label="选择文字颜色"
                    @input="updateTextColorFromPicker($event.target.value)"
                  />
                </label>
                <label class="hex-color-control">
                  <span>HEX</span>
                  <input
                    :value="textColorInput"
                    type="text"
                    inputmode="text"
                    maxlength="7"
                    placeholder="#111827"
                    aria-label="文字颜色 HEX 值"
                    :aria-invalid="textColorInputError"
                    @input="updateTextColorFromHex($event.target.value)"
                    @blur="commitTextColorInput"
                  />
                </label>
                <button class="secondary text-color-reset" type="button" @click="resetTextColor">
                  恢复自动
                </button>
              </div>
              <p v-if="textColorInputError" class="color-input-error" role="status">
                请输入 #FFF 或 #FFFFFF 格式；当前仍使用最后一个有效颜色。
              </p>
              <p v-if="readabilityWarning" class="warning">
                当前文字与背景对比度较低；系统不会修改你的自定义颜色。
              </p>
            </fieldset>
          </section>
          <section id="card-style-settings" class="editor-card personalization-section"><fieldset><h2>卡片样式</h2><label>卡片颜色 <input v-model="draft.card.color" type="color" /></label><label>透明度 <input v-model.number="draft.card.opacity" type="range" min="35" max="100" /></label><label>毛玻璃强度 <input v-model.number="draft.card.blur" type="range" min="0" max="32" /></label><label>边框强度 <input v-model.number="draft.card.border" type="range" min="0" max="40" /></label><label>阴影强度 <input v-model.number="draft.card.shadow" type="range" min="0" max="50" /></label></fieldset></section>
          <section id="advanced-settings" class="editor-card personalization-section"><fieldset class="advanced-settings"><h2>高级选项</h2><p class="advanced-intro">用于当前浏览器。相同冲突会自动处理；本机或账户设置明显变化时仍会重新询问。</p><div class="preference-group"><h3>登录冲突处理</h3><div class="preference-options"><label class="preference-option" :class="{ 'is-selected': conflictDecision === 'account' }"><input v-model="conflictDecision" type="radio" value="account" @change="changeConflictDecision" /><span class="preference-radio" aria-hidden="true"></span><span class="preference-option-content"><strong class="preference-option-title">优先使用账户设置</strong><span class="preference-option-description">以你的账户个性化设置为准，在本机发生冲突时可能会被覆盖。</span></span></label><label class="preference-option" :class="{ 'is-selected': conflictDecision === 'local' }"><input v-model="conflictDecision" type="radio" value="local" @change="changeConflictDecision" /><span class="preference-radio" aria-hidden="true"></span><span class="preference-option-content"><strong class="preference-option-title">优先保留本机设置</strong><span class="preference-option-description">以此设备上的设置为准，账户设置变更时不会自动覆盖本机偏好。</span></span></label></div></div></fieldset></section>
          <footer class="editor-card actions settings-actions"><button class="secondary reset-button" @click="restore">恢复默认</button><div class="actions-primary"><button class="secondary cancel-button" @click="cancel">取消修改</button><button class="primary save-button" :disabled="saving" @click="save">{{ saving ? '正在保存…' : '保存设置' }}</button></div></footer>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { onBeforeRouteLeave, RouterLink } from "vue-router";
import AnimatedPageTitle from "../components/common/AnimatedPageTitle.vue";
import AppHeader from "../components/layout/AppHeader.vue";
import { personalizationAPI } from "../utils/api";
import { compositionFor, cloneSettings, defaultPersonalization, normalizeHexColor, officialThemes, readPersonalizationConflictPreference, readabilityFor, savePersonalizationConflictPreference } from "../utils/personalization";
import { usePersonalizationStore } from "../stores/personalization";
import { errorToast, successToast } from "../utils/toast";

const store = usePersonalizationStore(); const draft = ref(cloneSettings(store.settings)); const saving = ref(false);
const conflictDecision = ref(readPersonalizationConflictPreference()?.decision || "");
const modes = [{ id: "default", label: "系统默认" }, { id: "color", label: "纯色" }, { id: "gradient", label: "渐变" }, { id: "image", label: "图片" }];
const typographyModes = [{ id: "auto", label: "自动" }, { id: "custom", label: "自定义" }, { id: "light", label: "浅色" }, { id: "dark", label: "深色" }];
const textColorInput = ref(normalizeHexColor(draft.value.typography.color, "#253044"));
const textColorInputError = ref(false);
const readable = computed(() => readabilityFor(draft.value, store.backgroundAnalysis, { checking: store.readabilityStatus === "checking" }));
const readabilityWarning = computed(() => draft.value.typography.mode === "custom" && readable.value.warning);
const previewDevice = ref("desktop");
const composition = computed(() => draft.value.background[previewDevice.value] || (draft.value.background[previewDevice.value] = compositionFor(draft.value, previewDevice.value === "mobile" ? 375 : 1440)));
const previewImageStyle = computed(() => ({ transform: `translate(${composition.value.positionX - 50}%, ${composition.value.positionY - 50}%) scale(${composition.value.scale}) rotate(${composition.value.rotation}deg)`, filter: `brightness(${draft.value.background.brightness}%) blur(${draft.value.background.blur}px)` }));
watch(draft, (value) => { void store.preview(value); }, { deep: true });
watch(() => draft.value.typography.color, (value) => { const normalized = normalizeHexColor(value); if (normalized && !textColorInputError.value) textColorInput.value = normalized; });
onMounted(async () => { await store.load(); draft.value = cloneSettings(store.settings); });
async function retryBackgroundSync() { const success = await store.retryPendingBackgroundSync(); draft.value = cloneSettings(store.settings); if (success) successToast("本机背景已同步"); }
function addStop() { if (draft.value.gradient.stops.length < 12) draft.value.gradient.stops.push({ color: "#F9A8D4", position: 50 }); }
function changeConflictDecision() { savePersonalizationConflictPreference(conflictDecision.value, ""); successToast("登录冲突处理偏好已更新"); }
function updateTextColorFromPicker(value) { const normalized = normalizeHexColor(value, draft.value.typography.color); draft.value.typography.color = normalized; textColorInput.value = normalized; textColorInputError.value = false; }
function updateTextColorFromHex(value) { textColorInput.value = value; const normalized = normalizeHexColor(value); textColorInputError.value = !normalized; if (normalized) draft.value.typography.color = normalized; }
function commitTextColorInput() { const normalized = normalizeHexColor(textColorInput.value); if (normalized) { draft.value.typography.color = normalized; textColorInput.value = normalized; } else { textColorInput.value = normalizeHexColor(draft.value.typography.color, "#253044"); } textColorInputError.value = false; }
function resetTextColor() { draft.value.typography.mode = "auto"; textColorInput.value = normalizeHexColor(draft.value.typography.color, "#253044"); textColorInputError.value = false; }
function selectTheme(theme) { draft.value.themeKey = theme.key; draft.value.background.type = "color"; draft.value.background.color = theme.colors[0]; }
function recentLabel(item) { const key = String(item || ""); if (key.startsWith("theme:")) return officialThemes.find((theme) => theme.key === key.slice(6))?.name || "主题"; if (key.startsWith("image:")) return "图片背景"; return key.startsWith("gradient") ? "渐变背景" : key.startsWith("color") ? "纯色背景" : "系统默认"; }
function applyRecent(item) { const key = String(item || ""); if (key.startsWith("theme:")) { const theme = officialThemes.find((entry) => entry.key === key.slice(6)); if (theme) selectTheme(theme); } else if (key.startsWith("image:")) draft.value.background.type = "image"; else if (key.startsWith("gradient:")) draft.value.background.type = "gradient"; else if (key.startsWith("color:")) { draft.value.background.type = "color"; draft.value.background.color = key.slice(6) || draft.value.background.color; } else draft.value.background.type = "default"; }
async function toggleFavorite(theme) { const wasFavorite = draft.value.favorites.includes(theme.key); draft.value.favorites = wasFavorite ? draft.value.favorites.filter((key) => key !== theme.key) : [...draft.value.favorites, theme.key]; try { if (store.isLoggedIn) await (wasFavorite ? personalizationAPI.unfavoriteTheme(theme.key) : personalizationAPI.favoriteTheme(theme.key)); else await store.save(draft.value); } catch (error) { draft.value.favorites = wasFavorite ? [...draft.value.favorites, theme.key] : draft.value.favorites.filter((key) => key !== theme.key); errorToast(error.response?.data?.msg || "主题收藏失败"); } }
function applyCustomTheme(theme) { const applied = cloneSettings(theme.settings); applied.customThemes = cloneSettings(draft.value).customThemes; applied.favorites = [...draft.value.favorites]; applied.recent = [...draft.value.recent]; draft.value = applied; }
async function renameTheme(theme) { const name = window.prompt("请输入新名称", theme.name); if (!name?.trim()) return; try { if (store.isLoggedIn) await personalizationAPI.updateTheme(theme.key, { name: name.trim() }); theme.name = name.trim(); if (!store.isLoggedIn) await store.save(draft.value); } catch { errorToast("主题重命名失败"); } }
async function removeTheme(theme) { if (!window.confirm(`确定删除主题“${theme.name}”吗？`)) return; try { if (store.isLoggedIn) await personalizationAPI.deleteTheme(theme.key); draft.value.customThemes = draft.value.customThemes.filter((item) => item.key !== theme.key); if (!store.isLoggedIn) await store.save(draft.value); } catch { errorToast("主题删除失败"); } }
async function selectImage(event) { const file = event.target.files?.[0]; if (!file) return; if (file.size > 10 * 1024 * 1024 || !["image/jpeg", "image/png", "image/webp"].includes(file.type)) { errorToast("请选择 10MB 以内的 JPG、JPEG、PNG 或 WEBP 图片"); return; } try { if (store.isLoggedIn) { const response = await personalizationAPI.uploadBackground(file); draft.value.background.imageId = response.data?.data?.id; draft.value.background.analysis = response.data?.data?.analysis || {}; store.setImageBlob(file); await store.refreshBackgrounds(); } else await store.setGuestImage(file); draft.value.background.type = "image"; } catch { errorToast("图片上传失败，请稍后重试"); } }
async function useSavedBackground(background) { try { await store.selectBackground(background); draft.value.background.type = "image"; draft.value.background.imageId = background.id; draft.value.background.analysis = background.analysis || {}; successToast("已应用背景，点击保存后同步"); } catch (error) { errorToast(error.response?.data?.msg || "背景读取失败，请稍后重试"); } }
async function removeSavedBackground(background) { if (!window.confirm(`确定删除“${background.original_name || `背景 #${background.id}`}”吗？`)) return; try { await store.deleteBackground(background); if (String(draft.value.background.imageId) === String(background.id)) draft.value.background = defaultPersonalization().background; successToast("背景已删除"); } catch (error) { errorToast(error.response?.data?.msg || "背景删除失败，请稍后重试"); } }
async function changeBackgroundPrivacy(background, privacy) { const previous = background.privacy; try { await store.updateBackgroundPrivacy(background, privacy); successToast(privacy === "private" ? "已设为仅自己可见" : "已设为公开"); } catch (error) { background.privacy = previous; errorToast(error.response?.data?.msg || "隐私设置更新失败"); } }
function resetImageAdjustments() { draft.value.background.desktop = { positionX: 50, positionY: 50, scale: 1, rotation: 0 }; draft.value.background.mobile = { positionX: 50, positionY: 50, scale: 1, rotation: 0 }; draft.value.background.brightness = 100; draft.value.background.blur = 0; draft.value.background.overlay = 0; }
function startDrag(event) { const start = { x: event.clientX, y: event.clientY, positionX: composition.value.positionX, positionY: composition.value.positionY }; const move = (moveEvent) => { composition.value.positionX = Math.max(0, Math.min(100, start.positionX + (moveEvent.clientX - start.x) / 2)); composition.value.positionY = Math.max(0, Math.min(100, start.positionY + (moveEvent.clientY - start.y) / 2)); }; const end = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", end); }; window.addEventListener("pointermove", move); window.addEventListener("pointerup", end); }
async function save() { saving.value = true; try { await store.save(draft.value); draft.value = cloneSettings(store.settings); successToast("个性化设置已保存"); } catch (error) { errorToast(error.response?.data?.msg || "设置保存失败，请稍后重试"); } finally { saving.value = false; } }
async function cancel() { await store.cancel(); draft.value = cloneSettings(store.settings); }
async function restore() { await store.restoreDefault(); draft.value = cloneSettings(store.settings); }
async function saveAsTheme() { const name = window.prompt("请输入主题名称"); if (!name?.trim()) return; if (draft.value.customThemes.length >= 5) { errorToast("最多可以保存 5 套自定义主题，请删除已有主题后再创建。"); return; } const theme = { key: `custom-${Date.now()}`, name: name.trim().slice(0, 30), settings: cloneSettings(draft.value) }; try { if (store.isLoggedIn) { const response = await personalizationAPI.createTheme(theme); draft.value.customThemes.push(response.data?.data || theme); } else { draft.value.customThemes.push(theme); await store.save(draft.value); } successToast("主题已保存"); } catch (error) { errorToast(error.response?.data?.msg || "主题保存失败"); } }
onBeforeRouteLeave(() => { if (JSON.stringify(draft.value) !== JSON.stringify(store.originalSettings) && !saving.value) return window.confirm("当前修改尚未保存，确定离开吗？"); return true; });
</script>

<style scoped>
.personalization-page {
  min-height: auto;
  padding-bottom: 32px;
  background: transparent;
}

.personalization-shell {
  width: min(1180px, calc(100% - 48px));
  margin: 18px auto 0;
  display: grid;
  gap: 18px;
  color: var(--app-text-primary);
}

.personalization-header,
.library-heading,
.background-actions,
.actions,
.actions-primary {
  display: flex;
  align-items: center;
}

.personalization-header {
  min-height: auto;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 26px;
  border: 1px solid var(--app-border);
  border-radius: 20px;
  background: var(--app-panel-bg);
  backdrop-filter: blur(var(--app-blur));
  -webkit-backdrop-filter: blur(var(--app-blur));
}

.header-copy {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.personalization-shell h1,
.personalization-shell h2,
.personalization-shell h3,
.personalization-shell p {
  margin: 0;
}

.personalization-shell h1,
.personalization-shell h2,
.personalization-shell h3 {
  color: var(--app-text-primary);
}

.personalization-shell p {
  color: var(--app-text-secondary);
}

.eyebrow,
.helper {
  color: var(--app-text-muted) !important;
}

.eyebrow {
  font-size: 13px;
  font-weight: 800;
}

.back-link {
  flex: 0 0 auto;
  padding: 10px 14px;
  border: 1px solid var(--app-border);
  border-radius: 14px;
  background: var(--app-control-bg);
  color: var(--app-text-primary);
  text-decoration: none;
}

.settings-layout {
  width: 100%;
}

.personalization-section,
.settings-actions {
  border: 1px solid var(--app-border);
  border-radius: 20px;
  box-shadow: var(--personalization-card-shadow);
  transition: color 180ms ease, background-color 180ms ease, border-color 180ms ease;
}

.settings-content {
  min-width: 0;
  display: grid;
  gap: 22px;
}

.personalization-layout button,
.personalization-layout .secondary {
  border: 1px solid var(--app-border);
  border-radius: 12px;
  background: var(--app-control-bg);
  color: var(--app-text-primary);
  text-align: left;
  transition: color 180ms ease, background-color 180ms ease, border-color 180ms ease;
}

.personalization-layout button {
  padding: 11px 13px;
}

.personalization-layout button.selected {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: #fff;
}

.personalization-section {
  min-width: 0;
  height: auto;
  min-height: 0;
  display: grid;
  gap: 18px;
  padding: 26px 28px;
  background: var(--app-panel-bg);
  backdrop-filter: blur(var(--app-blur));
  -webkit-backdrop-filter: blur(var(--app-blur));
  scroll-margin-top: 100px;
}

.personalization-section h2 {
  font-size: 22px;
  font-weight: 750;
  line-height: 1.35;
}

.editor-card label,
.control-group,
.editor-card fieldset {
  display: grid;
  gap: 10px;
  color: var(--app-text-primary);
  font-weight: 700;
}

.editor-card fieldset {
  min-inline-size: 0;
  border: 0;
  padding: 0;
  margin: 0;
}

.setting-section {
  display: flex !important;
  flex-direction: column;
  gap: 12px !important;
}

.setting-group {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.setting-help {
  color: var(--app-text-muted) !important;
  font-size: 13px;
  font-weight: 400;
  line-height: 1.6;
  opacity: .82;
}

.advanced-settings {
  gap: 10px !important;
}

.advanced-intro {
  max-width: 760px;
  color: var(--app-text-secondary) !important;
  font-size: 14px;
  line-height: 1.65;
}

.preference-group {
  display: grid;
  gap: 14px;
  margin-top: 8px;
}

.preference-group h3 {
  font-size: 15px;
  font-weight: 750;
}

.preference-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.editor-card .preference-option {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 14px;
  width: 100%;
  padding: 12px 18px;
  border: 1px solid var(--app-border);
  border-radius: 14px;
  background: color-mix(in srgb, var(--app-control-bg) 78%, transparent);
  color: var(--app-text-primary);
  cursor: pointer;
  font-weight: 400;
  transition: border-color .2s ease, background-color .2s ease, box-shadow .2s ease, transform .2s ease;
}

.editor-card .preference-option:hover {
  border-color: color-mix(in srgb, var(--color-primary) 26%, var(--app-border));
  transform: translateY(-1px);
}

.editor-card .preference-option.is-selected {
  border-color: color-mix(in srgb, var(--color-primary) 58%, var(--app-border));
  background: color-mix(in srgb, var(--color-primary) 8%, var(--app-control-bg));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-primary) 9%, transparent);
}

.preference-option input[type="radio"] {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.preference-radio {
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
  border: 2px solid color-mix(in srgb, var(--app-text-muted) 58%, var(--app-border));
  border-radius: 50%;
  transition: border-color .18s ease;
}

.preference-radio::after {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-primary);
  content: "";
  transform: scale(0);
  transition: transform .18s ease;
}

.preference-option.is-selected .preference-radio {
  border-color: var(--color-primary);
}

.preference-option.is-selected .preference-radio::after {
  transform: scale(1);
}

.preference-option:has(input:focus-visible) {
  outline: 2px solid color-mix(in srgb, var(--color-primary) 54%, transparent);
  outline-offset: 2px;
}

.preference-option-content {
  min-width: 0;
  display: grid;
  gap: 5px;
}

.preference-option-title {
  color: var(--app-text-primary);
  font-size: 16px;
  font-weight: 650;
  line-height: 1.4;
}

.preference-option-description {
  color: var(--app-text-secondary);
  font-size: 14px;
  line-height: 1.65;
  opacity: .72;
}

.editor-card input:not([type="range"]):not([type="radio"]),
.editor-card select {
  width: 100%;
  min-height: 46px;
  padding: 9px 11px;
  border: 1px solid var(--app-border);
  border-radius: 12px;
  background: var(--app-control-bg);
  color: var(--app-input-text);
  transition: color 180ms ease, background-color 180ms ease, border-color 180ms ease;
}

.setting-label {
  color: var(--app-text-primary);
  font-weight: 700;
}

.text-color-modes {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.editor-card .text-color-mode {
  position: relative;
  display: flex;
  min-height: 46px;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--app-border);
  border-radius: 12px;
  background: var(--app-control-bg);
  color: var(--app-text-primary);
  cursor: pointer;
  font-weight: 750;
  transition: border-color 180ms ease, background-color 180ms ease;
}

.text-color-mode input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.editor-card .text-color-mode.is-selected {
  border-color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 14%, var(--app-control-bg));
}

.text-color-mode:has(input:focus-visible) {
  outline: 2px solid color-mix(in srgb, var(--color-primary) 54%, transparent);
  outline-offset: 2px;
}

.custom-text-color {
  display: grid;
  grid-template-columns: auto minmax(180px, 260px) auto;
  align-items: end;
  gap: 12px;
  padding-top: 4px;
}

.editor-card .color-picker-control,
.editor-card .hex-color-control {
  gap: 7px;
  font-size: 13px;
}

.editor-card .color-picker-control input[type="color"] {
  width: 64px;
  min-height: 46px;
}

.editor-card .hex-color-control input[aria-invalid="true"] {
  border-color: #d97706;
}

.personalization-layout .text-color-reset {
  min-height: 46px;
  text-align: center;
}

.color-input-error {
  color: #b45309 !important;
  font-size: 13px;
  line-height: 1.55;
}

.editor-card input[type="color"] {
  width: 64px;
  padding: 2px;
}

.editor-card input[type="range"] {
  accent-color: var(--color-primary);
}

.mode-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px;
}

.official-theme-section,
.custom-theme-section {
  display: grid;
  gap: 12px;
}

.official-theme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(118px, 1fr));
  gap: 12px;
}

.official-theme-card {
  position: relative;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--app-border);
  border-radius: 14px;
  background: color-mix(in srgb, var(--app-control-bg) 82%, transparent);
  transition: border-color .2s ease, background-color .2s ease, box-shadow .2s ease, transform .2s ease;
}

.official-theme-card:hover {
  border-color: color-mix(in srgb, var(--color-primary) 26%, var(--app-border));
  transform: translateY(-1px);
}

.official-theme-card.is-active {
  border-color: color-mix(in srgb, var(--color-primary) 60%, var(--app-border));
  background: color-mix(in srgb, var(--color-primary) 9%, var(--app-control-bg));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-primary) 10%, transparent);
}

.personalization-layout .theme-card-main {
  width: 100%;
  min-height: 118px;
  display: grid;
  align-content: start;
  gap: 8px;
  padding: 10px;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--app-text-primary);
}

.theme-preview {
  display: block;
  width: 100%;
  height: 56px;
  border-radius: 10px;
}

.theme-name {
  overflow: hidden;
  padding-right: 30px;
  font-size: 14px;
  font-weight: 750;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.theme-active-label {
  position: absolute;
  bottom: 8px;
  left: 10px;
  color: var(--color-primary);
  font-size: 11px;
  font-weight: 800;
  line-height: 1.2;
  pointer-events: none;
}

.personalization-layout .theme-favorite-button {
  position: absolute;
  z-index: 1;
  top: 8px;
  right: 8px;
  width: 32px;
  min-height: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #64748b;
  box-shadow: none;
  font-size: 20px;
  line-height: 1;
  text-align: center;
  cursor: pointer;
  appearance: none;
  opacity: .88;
  transition: color 180ms ease, opacity 180ms ease, transform 180ms ease;
}

.personalization-layout .theme-favorite-button.is-favorite {
  background: transparent;
  color: var(--color-primary);
  opacity: 1;
}

.personalization-layout .theme-favorite-button:hover {
  background: transparent;
  color: #374151;
  opacity: 1;
  transform: scale(1.05);
}

.personalization-layout .theme-favorite-button.is-favorite:hover {
  color: var(--color-primary);
}

.personalization-layout .theme-favorite-button:active {
  background: transparent;
  transform: scale(.96);
}

.personalization-layout .theme-favorite-button:focus-visible {
  background: transparent;
  outline: 2px solid color-mix(in srgb, var(--color-primary) 55%, transparent);
  outline-offset: 1px;
}

.custom-theme-section {
  margin-top: 2px;
  padding-top: 20px;
  border-top: 1px solid var(--app-border);
}

.save-custom-theme {
  width: fit-content;
}

.custom-theme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin-top: 4px;
}

.custom-theme-grid article {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--app-border);
  border-radius: 14px;
  background: var(--app-panel-soft-bg);
}

.custom-theme-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.custom-theme-actions button {
  flex: 1 1 auto;
  text-align: center;
}

.gradient-stop {
  display: grid;
  grid-template-columns: 60px 1fr auto;
  gap: 10px;
  align-items: center;
}

.warning {
  padding: 12px;
  border-left: 3px solid #d97706;
  border-radius: 8px;
  background: var(--app-panel-soft-bg);
  color: var(--app-text-primary);
  backdrop-filter: blur(var(--app-blur));
}

.image-editor {
  display: grid;
  gap: 12px;
}

.device-preview {
  position: relative;
  width: min(100%, 620px);
  aspect-ratio: 16/9;
  overflow: hidden;
  border: 1px solid var(--app-border);
  border-radius: 14px;
  background: var(--app-surface-strong);
  touch-action: none;
}

.device-preview.mobile {
  width: min(220px, 100%);
  aspect-ratio: 9/16;
}

.device-preview img {
  position: absolute;
  inset: -20%;
  width: 140%;
  height: 140%;
  object-fit: cover;
  transform-origin: center;
  pointer-events: none;
}

.device-preview span {
  display: grid;
  height: 100%;
  place-items: center;
  padding: 20px;
  color: var(--app-text-primary);
  text-align: center;
}

.device-toggle {
  display: flex;
  gap: 8px;
}

.device-toggle button,
.background-actions button {
  flex: 1;
}

.background-library {
  display: grid;
  gap: 12px;
  padding-top: 4px;
}

.library-heading,
.background-actions {
  justify-content: space-between;
  gap: 18px;
}

.library-heading p,
.background-meta small {
  margin-top: 3px;
  color: var(--app-text-secondary);
}

.library-heading > span {
  padding: 5px 9px;
  border-radius: 999px;
  background: var(--color-primary);
  color: #fff;
  font-weight: 800;
}

.background-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 12px;
}

.background-grid article {
  overflow: hidden;
  display: grid;
  gap: 9px;
  padding: 9px;
  border: 1px solid var(--app-border);
  border-radius: 14px;
  background: var(--app-panel-soft-bg);
}

.background-grid article.active {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-primary) 25%, transparent);
}

.background-grid img,
.thumbnail-placeholder {
  width: 100%;
  aspect-ratio: 16/10;
  border-radius: 9px;
  background: var(--app-panel-soft-bg);
  object-fit: cover;
}

.thumbnail-placeholder {
  display: grid;
  place-items: center;
  padding: 8px;
  color: var(--app-text-secondary);
  text-align: center;
  backdrop-filter: blur(var(--app-blur));
}

.background-meta {
  display: grid;
  min-width: 0;
}

.background-meta strong {
  overflow: hidden;
  color: var(--app-text-primary);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.privacy-select {
  display: flex !important;
  align-items: center;
  font-size: 12px;
}

.privacy-select select {
  min-height: 32px !important;
  padding: 3px 5px !important;
}

.background-actions .danger {
  color: #b91c1c;
}

.empty-library {
  margin: 0;
  padding: 18px;
  border: 1px dashed var(--app-border);
  border-radius: 12px;
  color: var(--app-text-secondary);
}

.background-library,
.recent-list,
.background-sync-card {
  background: transparent;
}

.actions {
  justify-content: space-between;
  gap: 12px;
  padding: 20px 24px;
  background: var(--app-panel-bg);
  backdrop-filter: blur(var(--app-blur));
  -webkit-backdrop-filter: blur(var(--app-blur));
}

.actions-primary {
  margin-left: auto;
  gap: 12px;
}

.personalization-shell > footer button,
.settings-content > footer button {
  min-width: 108px;
  height: 44px;
  padding: 0 20px;
  border: 1px solid var(--app-button-border);
  border-radius: 14px;
  background: var(--app-button-bg);
  color: var(--app-text-primary);
  box-shadow: var(--app-button-shadow);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  font-weight: 800;
  text-align: center;
  transition: background-color .2s ease, border-color .2s ease, box-shadow .2s ease, transform .15s ease, opacity .2s ease;
}

.personalization-shell > footer button:hover:not(:disabled),
.settings-content > footer button:hover:not(:disabled) {
  background: var(--app-button-bg-hover);
  box-shadow: var(--app-card-hover-shadow);
  transform: translateY(-1px);
}

.personalization-shell > footer button:active:not(:disabled),
.settings-content > footer button:active:not(:disabled) {
  box-shadow: var(--app-button-shadow);
  transform: translateY(0);
}

.personalization-shell > footer .primary,
.settings-content > footer .primary {
  border-color: var(--app-button-primary-border);
  background: var(--app-button-primary-bg);
  color: var(--app-text-primary);
  box-shadow: var(--app-button-primary-shadow);
}

.personalization-shell > footer .primary:hover:not(:disabled),
.settings-content > footer .primary:hover:not(:disabled) {
  border-color: color-mix(in srgb, var(--color-primary) 42%, transparent);
  background: color-mix(in srgb, var(--color-primary) 24%, var(--app-button-bg));
  box-shadow: var(--app-button-primary-shadow);
}

.personalization-shell > footer button:disabled,
.settings-content > footer button:disabled {
  opacity: .5;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

@media (max-width: 899px) {
  .personalization-shell {
    width: min(100% - 28px, 1180px);
  }
}

@media (max-width: 600px) {
  .personalization-page {
    padding-bottom: 24px;
  }

  .personalization-header {
    align-items: flex-start;
    flex-direction: column;
    padding: 20px;
  }

  .personalization-section {
    padding: 20px;
  }

  .official-theme-grid,
  .background-grid,
  .custom-theme-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .actions {
    align-items: stretch;
    flex-direction: column;
    gap: 12px;
  }

  .actions-primary {
    width: 100%;
    margin-left: 0;
  }

  .actions > button,
  .actions-primary button {
    flex: 1;
    min-width: 0;
  }

  .gradient-stop {
    grid-template-columns: 52px 1fr;
  }

  .gradient-stop button {
    grid-column: span 2;
  }

  .text-color-modes {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .custom-text-color {
    grid-template-columns: 64px minmax(0, 1fr);
  }

  .text-color-reset {
    grid-column: span 2;
  }
}

@media (prefers-reduced-motion: reduce) {
  .personalization-section,
  .settings-actions,
  .personalization-layout button,
  .editor-card input,
  .editor-card select {
    transition: none;
  }
}
</style>
