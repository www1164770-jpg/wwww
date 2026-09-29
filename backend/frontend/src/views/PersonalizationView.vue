<template>
  <div
    class="personalization-page"
    :class="{
      page: !embedded,
      'personalization-page--embedded': embedded,
      'is-default-background': draft.background.type === 'default',
    }"
  >
    <main class="personalization-shell">
      <RecommendationPreferencePanel />
      <header v-if="!embedded" class="personalization-header">
        <div class="header-copy"><p class="eyebrow">外观偏好</p><AnimatedPageTitle>个性化设置</AnimatedPageTitle><p>背景切换后会先校验可读性，再开放其他视觉调整。</p></div>
      </header>
      <header v-else class="personalization-panel-heading">
        <p class="eyebrow">外观偏好</p>
        <h1>个性化设置</h1>
        <p>打造属于你的专属界面，让每一次使用都更舒适、更高效。</p>
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
          <section id="card-style-settings" class="editor-card personalization-section" :class="{ 'is-dark-theme': draft.themeKey === 'night' }">
            <fieldset class="card-style-settings">
              <h2>卡片样式</h2>
              <label class="card-color-control">卡片颜色 <input v-model="draft.card.color" type="color" /></label>
              <div class="slider-grid">
                <div class="setting-slider-item">
                  <div class="slider-header">
                    <div><div class="slider-title">透明度</div><p class="slider-desc">调整卡片背景的透明程度</p></div>
                    <output class="slider-value" for="card-opacity">{{ sliderProgress(draft.card.opacity, 100) }}%</output>
                  </div>
                  <input id="card-opacity" v-model.number="draft.card.opacity" class="setting-range" :style="{ '--progress': `${sliderProgress(draft.card.opacity, 100)}%` }" type="range" min="0" max="100" aria-label="卡片透明度" />
                </div>
                <div class="setting-slider-item">
                  <div class="slider-header">
                    <div><div class="slider-title">毛玻璃强度</div><p class="slider-desc">调整背景模糊程度</p></div>
                    <output class="slider-value" for="card-blur">{{ sliderProgress(draft.card.blur, 32) }}%</output>
                  </div>
                  <input id="card-blur" v-model.number="draft.card.blur" class="setting-range" :style="{ '--progress': `${sliderProgress(draft.card.blur, 32)}%` }" type="range" min="0" max="32" aria-label="卡片毛玻璃强度" />
                </div>
                <div class="setting-slider-item">
                  <div class="slider-header">
                    <div><div class="slider-title">边框强度</div><p class="slider-desc">调整卡片边界显示强度</p></div>
                    <output class="slider-value" for="card-border">{{ sliderProgress(draft.card.border, 40) }}%</output>
                  </div>
                  <input id="card-border" v-model.number="draft.card.border" class="setting-range" :style="{ '--progress': `${sliderProgress(draft.card.border, 40)}%` }" type="range" min="0" max="40" aria-label="卡片边框强度" />
                </div>
                <div class="setting-slider-item">
                  <div class="slider-header">
                    <div><div class="slider-title">阴影强度</div><p class="slider-desc">调整卡片层级和悬浮感</p></div>
                    <output class="slider-value" for="card-shadow">{{ sliderProgress(draft.card.shadow, 50) }}%</output>
                  </div>
                  <input id="card-shadow" v-model.number="draft.card.shadow" class="setting-range" :style="{ '--progress': `${sliderProgress(draft.card.shadow, 50)}%` }" type="range" min="0" max="50" aria-label="卡片阴影强度" />
                </div>
              </div>
            </fieldset>
          </section>
          <section id="advanced-settings" class="editor-card personalization-section"><fieldset class="advanced-settings"><h2>高级选项</h2><p class="advanced-intro">用于当前浏览器。相同冲突会自动处理；本机或账户设置明显变化时仍会重新询问。</p><div class="preference-group"><h3>登录冲突处理</h3><div class="preference-options"><label class="preference-option" :class="{ 'is-selected': conflictDecision === 'account' }"><input v-model="conflictDecision" type="radio" value="account" @change="changeConflictDecision" /><span class="preference-radio" aria-hidden="true"></span><span class="preference-option-content"><strong class="preference-option-title">优先使用账户设置</strong><span class="preference-option-description">以你的账户个性化设置为准，在本机发生冲突时可能会被覆盖。</span></span></label><label class="preference-option" :class="{ 'is-selected': conflictDecision === 'local' }"><input v-model="conflictDecision" type="radio" value="local" @change="changeConflictDecision" /><span class="preference-radio" aria-hidden="true"></span><span class="preference-option-content"><strong class="preference-option-title">优先保留本机设置</strong><span class="preference-option-description">以此设备上的设置为准，账户设置变更时不会自动覆盖本机偏好。</span></span></label></div></div></fieldset></section>
          <footer class="editor-card actions settings-actions"><button class="secondary reset-button" @click="restore">恢复默认</button><div class="actions-primary"><button class="secondary cancel-button" @click="cancel">取消修改</button><button class="primary save-button" :disabled="saving" @click="save">{{ saving ? '正在保存…' : '保存设置' }}</button></div></footer>
        </div>
        <aside v-if="embedded" class="personalization-live-preview" aria-label="实时预览">
          <div class="personalization-live-preview__heading">
            <div>
              <h2>实时预览</h2>
              <p>调整会立即反映在此处，保存后才会同步到全站。</p>
            </div>
            <span>预览中</span>
          </div>
          <div class="personalization-live-preview__canvas" :class="{ 'is-dark-preview': isDarkPreview }" :style="previewSurfaceStyle">
            <div class="preview-topbar"><i></i><i></i><i></i></div>
            <div class="preview-hero">
              <b>知航屿</b>
              <strong>为下一次探索，留出更舒适的界面。</strong>
              <em>当前主题：{{ currentThemeName }}</em>
            </div>
            <div class="preview-cards">
              <span></span><span></span><span></span>
            </div>
          </div>
          <p class="personalization-live-preview__note">背景、主题、字体与卡片效果均使用当前草稿设置渲染。</p>
        </aside>
      </div>
    </main>
  </div>

  <Teleport to="body">
    <div
      v-if="themeNameModalOpen"
      class="theme-modal-overlay"
      @click.self="closeThemeNameModal"
    >
      <form
        class="theme-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="theme-modal-title"
        aria-describedby="theme-modal-description"
        @keydown.esc.prevent="closeThemeNameModal"
        @submit.prevent="submitThemeName"
      >
        <h2 id="theme-modal-title">{{ themeNameModalTitle }}</h2>
        <p id="theme-modal-description">{{ themeNameModalDescription }}</p>
        <label class="theme-name-field" for="theme-name-input">
          <input
            id="theme-name-input"
            ref="themeNameInput"
            v-model="themeName"
            type="text"
            maxlength="30"
            placeholder="请输入主题名称"
            aria-label="主题名称"
            :aria-invalid="Boolean(themeNameError)"
            :aria-describedby="themeNameError ? 'theme-name-error' : undefined"
            @input="themeNameError = ''"
          />
        </label>
        <p v-if="themeNameError" id="theme-name-error" class="theme-name-error" role="alert">
          {{ themeNameError }}
        </p>
        <div class="theme-modal-actions">
          <button type="button" class="theme-modal-cancel" :disabled="themeNameSubmitting" @click="closeThemeNameModal">
            取消
          </button>
          <button type="submit" class="theme-modal-save" :disabled="themeNameSubmitting">
            {{ themeNameSubmitting ? '正在保存…' : '保存' }}
          </button>
        </div>
      </form>
    </div>
  </Teleport>
</template>

<script setup>
import RecommendationPreferencePanel from "../components/site/RecommendationPreferencePanel.vue";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import AnimatedPageTitle from "../components/common/AnimatedPageTitle.vue";
import { personalizationAPI } from "../utils/api";
import { compositionFor, cloneSettings, defaultPersonalization, normalizeHexColor, officialThemes, readPersonalizationConflictPreference, readabilityFor, savePersonalizationConflictPreference } from "../utils/personalization";
import { usePersonalizationStore } from "../stores/personalization";
import { errorToast, successToast } from "../utils/toast";

const props = defineProps({
  embedded: { type: Boolean, default: false },
});

const store = usePersonalizationStore(); const draft = ref(cloneSettings(store.settings)); const saving = ref(false);
const conflictDecision = ref(readPersonalizationConflictPreference()?.decision || "");
const themeNameModalOpen = ref(false);
const themeNameModalMode = ref("save");
const themeName = ref("");
const themeNameError = ref("");
const themeNameInput = ref(null);
const themeNameSubmitting = ref(false);
const themeBeingRenamed = ref(null);
const themeNameModalTitle = computed(() => themeNameModalMode.value === "rename" ? "重命名主题" : "保存为我的主题");
const themeNameModalDescription = computed(() => themeNameModalMode.value === "rename" ? "为该主题设置一个新的名称。" : "为当前个性化设置设置一个名称，方便以后快速使用。");
const modes = [{ id: "default", label: "系统默认" }, { id: "color", label: "纯色" }, { id: "gradient", label: "渐变" }, { id: "image", label: "图片" }];
const typographyModes = [{ id: "auto", label: "自动" }, { id: "custom", label: "自定义" }, { id: "light", label: "浅色" }, { id: "dark", label: "深色" }];
const textColorInput = ref(normalizeHexColor(draft.value.typography.color, "#253044"));
const textColorInputError = ref(false);
const readable = computed(() => readabilityFor(draft.value, store.backgroundAnalysis, { checking: store.readabilityStatus === "checking" }));
const readabilityWarning = computed(() => draft.value.typography.mode === "custom" && readable.value.warning);
const previewDevice = ref("desktop");
const composition = computed(() => draft.value.background[previewDevice.value] || (draft.value.background[previewDevice.value] = compositionFor(draft.value, previewDevice.value === "mobile" ? 375 : 1440)));
const previewImageStyle = computed(() => ({ transform: `translate(${composition.value.positionX - 50}%, ${composition.value.positionY - 50}%) scale(${composition.value.scale}) rotate(${composition.value.rotation}deg)`, filter: `brightness(${draft.value.background.brightness}%) blur(${draft.value.background.blur}px)` }));
const currentTheme = computed(() => officialThemes.find((theme) => theme.key === draft.value.themeKey));
const currentThemeName = computed(() => currentTheme.value?.name || "系统默认");
const isDarkPreview = computed(() => currentTheme.value?.key === "night");
function sliderProgress(value, max) { return Math.round((Number(value) / max) * 100); }
const previewSurfaceStyle = computed(() => {
  const background = draft.value.background;
  if (background.type === "gradient") {
    const stops = draft.value.gradient.stops.map((stop) => `${stop.color} ${stop.position}%`).join(", ");
    return { background: `linear-gradient(${draft.value.gradient.angle}deg, ${stops})` };
  }
  if (background.type === "image" && store.imageUrl) {
    return {
      backgroundImage: `linear-gradient(rgba(15, 23, 42, ${Number(background.overlay || 0) / 100}), rgba(15, 23, 42, ${Number(background.overlay || 0) / 100})), url("${store.imageUrl}")`,
      backgroundPosition: "center",
      backgroundRepeat: "no-repeat",
      backgroundSize: background.size === "repeat" ? "auto" : background.size || "cover",
      filter: `brightness(${background.brightness || 100}%)`,
    };
  }
  return { background: background.type === "color" ? background.color : currentTheme.value?.colors?.[0] || "#ffffff" };
});
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
function openThemeNameModal(mode = "save", theme = null) { themeNameModalMode.value = mode; themeBeingRenamed.value = theme; themeName.value = theme?.name || ""; themeNameError.value = ""; themeNameModalOpen.value = true; void nextTick(() => themeNameInput.value?.focus()); }
function closeThemeNameModal(force = false) { if (themeNameSubmitting.value && !force) return; themeNameModalOpen.value = false; themeName.value = ""; themeNameError.value = ""; themeBeingRenamed.value = null; }
function renameTheme(theme) { openThemeNameModal("rename", theme); }
async function removeTheme(theme) { if (!window.confirm(`确定删除主题“${theme.name}”吗？`)) return; try { if (store.isLoggedIn) await personalizationAPI.deleteTheme(theme.key); draft.value.customThemes = draft.value.customThemes.filter((item) => item.key !== theme.key); if (!store.isLoggedIn) await store.save(draft.value); } catch { errorToast("主题删除失败"); } }
async function selectImage(event) { const file = event.target.files?.[0]; if (!file) return; if (file.size > 10 * 1024 * 1024 || !["image/jpeg", "image/png", "image/webp"].includes(file.type)) { errorToast("请选择 10MB 以内的 JPG、JPEG、PNG 或 WEBP 图片"); return; } try { if (store.isLoggedIn) { const response = await personalizationAPI.uploadBackground(file); draft.value.background.imageId = response.data?.data?.id; draft.value.background.analysis = response.data?.data?.analysis || {}; store.setImageBlob(file); await store.refreshBackgrounds(); } else await store.setGuestImage(file); draft.value.background.type = "image"; } catch { errorToast("图片上传失败，请稍后重试"); } }
async function useSavedBackground(background) { try { await store.selectBackground(background); draft.value.background.type = "image"; draft.value.background.imageId = background.id; draft.value.background.analysis = background.analysis || {}; successToast("已应用背景，点击保存后同步"); } catch (error) { errorToast(error.response?.data?.msg || "背景读取失败，请稍后重试"); } }
async function removeSavedBackground(background) { if (!window.confirm(`确定删除“${background.original_name || `背景 #${background.id}`}”吗？`)) return; try { await store.deleteBackground(background); if (String(draft.value.background.imageId) === String(background.id)) draft.value.background = defaultPersonalization().background; successToast("背景已删除"); } catch (error) { errorToast(error.response?.data?.msg || "背景删除失败，请稍后重试"); } }
async function changeBackgroundPrivacy(background, privacy) { const previous = background.privacy; try { await store.updateBackgroundPrivacy(background, privacy); successToast(privacy === "private" ? "已设为仅自己可见" : "已设为公开"); } catch (error) { background.privacy = previous; errorToast(error.response?.data?.msg || "隐私设置更新失败"); } }
function resetImageAdjustments() { draft.value.background.desktop = { positionX: 50, positionY: 50, scale: 1, rotation: 0 }; draft.value.background.mobile = { positionX: 50, positionY: 50, scale: 1, rotation: 0 }; draft.value.background.brightness = 100; draft.value.background.blur = 0; draft.value.background.overlay = 0; }
function startDrag(event) { const start = { x: event.clientX, y: event.clientY, positionX: composition.value.positionX, positionY: composition.value.positionY }; const move = (moveEvent) => { composition.value.positionX = Math.max(0, Math.min(100, start.positionX + (moveEvent.clientX - start.x) / 2)); composition.value.positionY = Math.max(0, Math.min(100, start.positionY + (moveEvent.clientY - start.y) / 2)); }; const end = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", end); }; window.addEventListener("pointermove", move); window.addEventListener("pointerup", end); }
async function save() { saving.value = true; try { await store.save(draft.value); draft.value = cloneSettings(store.settings); successToast("个性化设置已保存"); } catch (error) { if (import.meta.env.DEV) console.error("个性化设置保存请求失败", { status: error.response?.status, message: error.response?.data?.msg || error.message }); errorToast(error.response?.data?.msg || "设置保存失败，请稍后重试"); } finally { saving.value = false; } }
async function cancel() { await store.cancel(); draft.value = cloneSettings(store.settings); }
async function restore() { await store.restoreDefault(); draft.value = cloneSettings(store.settings); }
function saveAsTheme() { openThemeNameModal(); }
async function submitThemeName() { const name = themeName.value.trim(); if (!name) { themeNameError.value = "请输入主题名称"; void nextTick(() => themeNameInput.value?.focus()); return; } themeNameSubmitting.value = true; try { if (themeNameModalMode.value === "rename") { const theme = themeBeingRenamed.value; if (!theme) return; if (store.isLoggedIn) await personalizationAPI.updateTheme(theme.key, { name }); theme.name = name; if (!store.isLoggedIn) await store.save(draft.value); closeThemeNameModal(true); return; } if (draft.value.customThemes.length >= 5) { errorToast("最多可以保存 5 套自定义主题，请删除已有主题后再创建。"); return; } const theme = { key: `custom-${Date.now()}`, name: name.slice(0, 30), settings: cloneSettings(draft.value) }; if (store.isLoggedIn) { const response = await personalizationAPI.createTheme(theme); draft.value.customThemes.push(response.data?.data || theme); } else { draft.value.customThemes.push(theme); await store.save(draft.value); } successToast("主题已保存"); closeThemeNameModal(true); } catch (error) { errorToast(themeNameModalMode.value === "rename" ? "主题重命名失败" : error.response?.data?.msg || "主题保存失败"); } finally { themeNameSubmitting.value = false; } }
</script>

<style scoped>
.personalization-page {
  min-height: auto;
  padding-bottom: 32px;
  background: transparent;
}

.personalization-page--embedded {
  --app-border: var(--surface-border);
  --app-panel-bg: var(--surface);
  --app-panel-soft-bg: var(--surface-soft);
  --app-control-bg: var(--surface-soft);
  --app-button-bg: var(--surface);
  --app-button-bg-hover: var(--surface-hover);
  --app-button-border: var(--surface-border);
  --app-button-shadow: none;
  --app-button-primary-bg: var(--primary);
  --app-button-primary-border: var(--primary);
  --app-button-primary-shadow: 0 4px 12px color-mix(in srgb, var(--primary) 12%, transparent);
  --personalization-card-shadow: var(--surface-shadow);
  width: 100%;
  padding: 0;
  /* ProfileView owns the single page background layer. */
  background: transparent;
}

.personalization-page--embedded .personalization-shell {
  width: 100%;
  gap: 20px;
}

.personalization-page--embedded .settings-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(280px, .8fr);
  align-items: start;
  gap: 20px;
}

.personalization-live-preview {
  position: sticky;
  top: 92px;
  display: grid;
  gap: 14px;
  border: 1px solid var(--surface-border);
  border-radius: 16px;
  background: var(--surface);
  padding: 18px;
  box-shadow: var(--surface-shadow);
}

.personalization-live-preview__heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.personalization-live-preview__heading h2,
.personalization-live-preview__heading p,
.personalization-live-preview__note {
  margin: 0;
}

.personalization-live-preview__heading h2 {
  color: var(--app-text-primary);
  font-size: 17px;
  line-height: 1.4;
}

.personalization-live-preview__heading p,
.personalization-live-preview__note {
  color: var(--app-text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.personalization-live-preview__heading span {
  flex: 0 0 auto;
  border-radius: 999px;
  background: var(--primary-soft);
  color: var(--primary);
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 700;
}

.personalization-live-preview__canvas {
  display: grid;
  min-height: 250px;
  align-content: start;
  gap: 18px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, .7);
  border-radius: 12px;
  color: var(--app-text-primary);
  padding: 12px;
  transition: background 180ms ease, filter 180ms ease;
}

.personalization-live-preview__canvas.is-dark-preview {
  border-color: rgba(255, 255, 255, .12);
  color: var(--text-primary);
}

.personalization-live-preview__canvas.is-dark-preview .preview-hero,
.personalization-live-preview__canvas.is-dark-preview .preview-cards span {
  border-color: rgba(255, 255, 255, .1);
  background: rgba(11, 16, 24, .84);
}

.preview-topbar {
  display: flex;
  gap: 5px;
}

.preview-topbar i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  opacity: .28;
}

.preview-hero,
.preview-cards {
  display: grid;
  gap: 8px;
}

.preview-hero {
  border: 1px solid rgba(255, 255, 255, .58);
  border-radius: 10px;
  background: rgba(255, 255, 255, .72);
  padding: 14px;
  backdrop-filter: blur(8px);
}

.preview-hero b { font-size: 12px; }
.preview-hero strong { font-size: 15px; line-height: 1.45; }
.preview-hero em { font-size: 11px; font-style: normal; opacity: .7; }

.preview-cards {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.preview-cards span {
  min-height: 48px;
  border: 1px solid rgba(255, 255, 255, .6);
  border-radius: 9px;
  background: rgba(255, 255, 255, .66);
  backdrop-filter: blur(8px);
}

.personalization-panel-heading {
  display: grid;
  gap: 6px;
  padding: 4px 2px 2px;
}

.personalization-panel-heading h1,
.personalization-panel-heading p {
  margin: 0;
}

.personalization-panel-heading h1 {
  color: var(--app-text-primary);
  font-size: clamp(25px, 3vw, 32px);
  font-weight: 700;
  line-height: 1.3;
}

.personalization-panel-heading > p:last-child {
  color: var(--app-text-secondary);
  font-size: 14px;
  line-height: 1.65;
}

html[data-personalization="on"] .personalization-page.is-default-background {
  --app-text-primary: var(--text-primary);
  --app-text-secondary: var(--text-secondary);
  --app-text-tertiary: var(--text-tertiary);
  --app-text-muted: var(--text-muted);
  --app-border: var(--surface-border);
  --app-card-border: var(--surface-border);
  --app-panel-bg: var(--surface);
  --app-panel-soft-bg: var(--surface-soft);
  --app-control-bg: var(--surface-soft);
  --app-button-bg: var(--surface);
  --app-button-bg-hover: var(--surface-hover);
  --app-button-border: var(--surface-border);
  --app-button-shadow: none;
  --app-button-primary-bg: var(--primary);
  --app-button-primary-border: var(--primary);
  --app-button-primary-shadow: 0 4px 12px color-mix(in srgb, var(--primary) 12%, transparent);
  --personalization-card-shadow: var(--surface-shadow);
  background: var(--page-bg) !important;
}

.personalization-page.is-default-background .personalization-header,
.personalization-page.is-default-background .personalization-section,
.personalization-page.is-default-background .settings-actions {
  border-color: var(--surface-border);
  background: var(--surface);
  box-shadow: var(--surface-shadow);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

.personalization-page.is-default-background .personalization-header,
.personalization-page.is-default-background .personalization-section,
.personalization-page.is-default-background .settings-actions {
  border-radius: 16px;
}

.personalization-page.is-default-background .personalization-layout button,
.personalization-page.is-default-background .personalization-layout .secondary,
.personalization-page.is-default-background .back-link,
.personalization-page.is-default-background .editor-card input:not([type="range"]):not([type="radio"]),
.personalization-page.is-default-background .editor-card select,
.personalization-page.is-default-background .official-theme-card,
.personalization-page.is-default-background .custom-theme-grid article,
.personalization-page.is-default-background .background-grid article,
.personalization-page.is-default-background .editor-card .preference-option {
  border-color: var(--surface-border);
  background: var(--surface-soft);
}

.personalization-page.is-default-background .personalization-layout button.selected {
  border: 1.5px solid var(--primary);
  background: var(--primary-soft);
  color: var(--primary);
}

.personalization-page.is-default-background .official-theme-card.is-active {
  border: 1.5px solid var(--primary);
  background: var(--surface);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary) 8%, transparent);
}

.personalization-page.is-default-background .editor-card .text-color-mode.is-selected {
  border-color: var(--primary);
  background: var(--primary-soft);
}

.personalization-page.is-default-background .editor-card .preference-option.is-selected {
  border-color: #9dd5bd;
  background: #f7fbf9;
  box-shadow: none;
}

.personalization-page.is-default-background .preference-option.is-selected .preference-radio,
.personalization-page.is-default-background .preference-option.is-selected .preference-radio::after {
  border-color: #67b98e;
  background: #67b98e;
}

.personalization-page.is-default-background .personalization-layout button:hover:not(:disabled),
.personalization-page.is-default-background .back-link:hover {
  background: var(--surface-hover);
}

.personalization-page.is-default-background .editor-card input:not([type="range"]):not([type="radio"]):focus,
.personalization-page.is-default-background .editor-card select:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary) 12%, transparent);
}

.personalization-page.is-default-background .editor-card input[type="range"] {
  accent-color: var(--primary);
}

.personalization-shell {
  width: min(1180px, calc(100% - 48px));
  margin: 0 auto;
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

.card-style-settings {
  gap: 20px !important;
}

.card-color-control {
  width: fit-content;
}

.slider-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 22px 28px;
}

.setting-slider-item {
  min-width: 0;
  display: grid;
  gap: 12px;
  padding: 12px 4px;
  --slider-track: #e7ebf2;
}

.is-dark-theme .setting-slider-item {
  --slider-track: rgba(255, 255, 255, .15);
}

.slider-header {
  min-width: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.slider-title {
  color: var(--app-text-primary);
  font-size: 14px;
  font-weight: 750;
  line-height: 1.35;
}

.slider-desc {
  margin: 4px 0 0;
  color: var(--app-text-muted);
  font-size: 12px;
  font-weight: 400;
  line-height: 1.5;
}

.slider-value {
  flex: 0 0 auto;
  min-width: 48px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 10px;
  border-radius: 999px;
  background: var(--primary-soft);
  color: var(--primary);
  font-size: 13px;
  font-weight: 700;
  line-height: 1;
}

.setting-range {
  width: 100%;
  height: 18px;
  margin: 0;
  appearance: none;
  -webkit-appearance: none;
  border: 0;
  border-radius: 999px;
  outline: none;
  background: linear-gradient(to right, var(--primary) 0%, var(--primary) var(--progress), var(--slider-track) var(--progress), var(--slider-track) 100%) center / 100% 6px no-repeat;
  cursor: pointer;
}

.setting-range::-webkit-slider-runnable-track {
  width: 100%;
  height: 6px;
  border: 0;
  border-radius: 999px;
  background: transparent;
}

.setting-range::-webkit-slider-thumb {
  width: 18px;
  height: 18px;
  margin-top: -6px;
  box-sizing: border-box;
  appearance: none;
  -webkit-appearance: none;
  border: 3px solid var(--primary);
  border-radius: 50%;
  background: var(--surface, #fff);
  box-shadow: 0 2px 8px rgba(15, 23, 42, .16);
  cursor: grab;
  transition: transform .18s ease, box-shadow .18s ease;
}

.setting-range::-moz-range-track {
  width: 100%;
  height: 6px;
  border: 0;
  border-radius: 999px;
  background: var(--slider-track);
}

.setting-range::-moz-range-progress {
  height: 6px;
  border-radius: 999px;
  background: var(--primary);
}

.setting-range::-moz-range-thumb {
  width: 18px;
  height: 18px;
  box-sizing: border-box;
  border: 3px solid var(--primary);
  border-radius: 50%;
  background: var(--surface, #fff);
  box-shadow: 0 2px 8px rgba(15, 23, 42, .16);
  cursor: grab;
  transition: transform .18s ease, box-shadow .18s ease;
}

.setting-range:hover::-webkit-slider-thumb,
.setting-range:hover::-moz-range-thumb {
  transform: scale(1.08);
  box-shadow: 0 3px 10px rgba(15, 23, 42, .2);
}

.setting-range:active::-webkit-slider-thumb,
.setting-range:active::-moz-range-thumb {
  transform: scale(1.12);
  cursor: grabbing;
}

.setting-range:focus-visible {
  box-shadow: 0 0 0 4px var(--primary-soft);
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
  color: var(--text-on-primary);
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

.theme-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(15, 23, 42, .28);
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
}

.theme-modal {
  width: min(420px, calc(100vw - 40px));
  display: grid;
  gap: 14px;
  padding: 24px;
  border: 1px solid #e7ecf3;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 20px 60px rgba(15, 23, 42, .16);
  color: #1f2937;
}

.theme-modal h2,
.theme-modal p {
  margin: 0;
}

.theme-modal h2 {
  font-size: 20px;
  font-weight: 600;
  line-height: 1.35;
}

.theme-modal > p {
  color: #7c879d;
  font-size: 14px;
  line-height: 1.6;
}

.theme-name-field {
  display: block;
}

.theme-name-field input {
  box-sizing: border-box;
  width: 100%;
  height: 44px;
  padding: 0 12px;
  border: 1px solid #dde4ee;
  border-radius: 10px;
  outline: 0;
  background: #fff;
  color: #1f2937;
  font: inherit;
  transition: border-color .18s ease, box-shadow .18s ease;
}

.theme-name-field input::placeholder {
  color: #9aa5b5;
}

.theme-name-field input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary) 20%, transparent);
}

.theme-name-field input[aria-invalid="true"] {
  border-color: #e05252;
}

.theme-name-error {
  margin-top: -8px !important;
  color: #e05252 !important;
  font-size: 13px !important;
  line-height: 1.4 !important;
}

.theme-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 2px;
}

.theme-modal-actions button {
  min-width: 76px;
  height: 38px;
  padding: 0 15px;
  border-radius: 10px;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: background-color .18s ease, border-color .18s ease, opacity .18s ease;
}

.theme-modal-cancel {
  border: 1px solid #dde4ee;
  background: #fff;
  color: #596579;
}

.theme-modal-cancel:hover:not(:disabled) {
  background: #f7f9fc;
}

.theme-modal-save {
  border: 1px solid var(--color-primary);
  background: var(--color-primary);
  color: #fff;
}

.theme-modal-save:hover:not(:disabled) {
  filter: brightness(.96);
}

.theme-modal-actions button:disabled {
  cursor: not-allowed;
  opacity: .58;
}

@media (max-width: 899px) {
  .personalization-shell {
    width: min(100% - 28px, 1180px);
  }

  .personalization-page--embedded .settings-layout {
    grid-template-columns: 1fr;
  }

  .personalization-live-preview {
    position: static;
  }
}

@media (max-width: 600px) {
  .theme-modal-overlay {
    padding: 16px;
  }

  .theme-modal {
    width: calc(100vw - 32px);
    padding: 20px;
  }

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

  .slider-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 16px;
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
