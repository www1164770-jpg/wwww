import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { personalizationAPI } from "../utils/api";
import { getAccessToken } from "../utils/auth";
import { analyzeBackground, analyzeImageBlob, applyPersonalization, cloneSettings, defaultPersonalization, mergeAccountWithGuestBackground, personalizationConflictHash, readBackgroundSyncState, readGuestImage, readGuestSettings, readPersonalizationConflictPreference, readabilityFor, rememberedConflictDecision, saveBackgroundSyncState, saveGuestImage, saveGuestSettings, savePersonalizationConflictPreference } from "../utils/personalization";

export const usePersonalizationStore = defineStore("personalization", () => {
  const settings = ref(defaultPersonalization());
  const originalSettings = ref(defaultPersonalization());
  const imageUrl = ref("");
  const backgrounds = ref([]);
  const loading = ref(false);
  const conflict = ref(null);
  const backgroundSyncState = ref(readBackgroundSyncState());
  const activeUserId = ref("");
  const readabilityStatus = ref("idle");
  const readabilityReady = ref(true);
  const backgroundAnalysis = ref(analyzeBackground(settings.value));
  const readabilityVersion = ref(0);
  const isLoggedIn = computed(() => Boolean(getAccessToken()));
  let lastBackgroundSignature = "";
  let pendingImageBlob = null;
  let backgroundSyncLock = false;

  function updateBackgroundSyncState(next) {
    backgroundSyncState.value = saveBackgroundSyncState({ ...backgroundSyncState.value, ...next });
  }
  function backgroundSyncError(error) {
    const status = Number(error?.response?.status || 0);
    if (status === 401) return { code: "auth", message: "登录状态已失效，请重新登录。" };
    if (status === 413) return { code: "too_large", message: "图片超过限制，请重新选择。" };
    if (status >= 500) return { code: "server", message: "服务器暂时异常，已保留本机图片。" };
    if (!error?.response) return { code: "network", message: "网络异常，背景将在下次自动同步。" };
    return { code: "upload", message: "背景图片暂未同步，已保留本机图片，稍后可继续同步。" };
  }
  function notifyBackgroundSyncFailure(failure, quiet) {
    if (quiet) return;
    window.dispatchEvent(new CustomEvent("app-toast", { detail: { type: failure.code === "auth" || failure.code === "too_large" ? "warning" : "info", message: failure.message } }));
  }

  function backgroundSignature(value) {
    const background = value?.background || {};
    return JSON.stringify({ type: background.type, color: background.color, imageId: background.imageId, size: background.size, overlay: background.overlay, brightness: background.brightness, blur: background.blur, analysis: background.analysis, gradient: value?.gradient, themeKey: value?.themeKey });
  }
  function applyWithReadability(value, result) {
    applyPersonalization(value, { imageUrl: imageUrl.value, readability: result });
  }
  async function checkReadability(value, { force = false, debounce = true } = {}) {
    const candidate = cloneSettings(value);
    const signature = backgroundSignature(candidate);
    if (!force && signature === lastBackgroundSignature && readabilityStatus.value === "ready") {
      applyWithReadability(candidate, readabilityFor(candidate, backgroundAnalysis.value));
      return backgroundAnalysis.value;
    }
    lastBackgroundSignature = signature;
    const version = readabilityVersion.value + 1;
    readabilityVersion.value = version;
    const fallback = analyzeBackground(candidate);
    backgroundAnalysis.value = fallback;
    const isImage = candidate.background?.type === "image";
    // Colors and gradients are sampled synchronously before their background
    // CSS is applied, eliminating a temporary old-foreground flash.
    if (!isImage) {
      readabilityStatus.value = "ready";
      readabilityReady.value = true;
      applyWithReadability(candidate, readabilityFor(candidate, fallback));
      return fallback;
    }
    // Local images have no metadata until canvas sampling finishes. Keep a
    // safe surface internally, without exposing a loading state to the user.
    readabilityStatus.value = "checking";
    readabilityReady.value = true;
    applyWithReadability(candidate, readabilityFor(candidate, fallback, { checking: fallback.pending }));
    try {
      let analysis = analyzeBackground(candidate);
      if (candidate.background?.type === "image" && analysis.pending && pendingImageBlob) {
        analysis = await analyzeImageBlob(pendingImageBlob) || analysis;
      }
      if (version !== readabilityVersion.value) return null;
      backgroundAnalysis.value = analysis;
      readabilityStatus.value = analysis.pending ? "fallback" : "ready";
      readabilityReady.value = true;
      applyWithReadability(candidate, readabilityFor(candidate, analysis));
      return analysis;
    } catch (error) {
      if (version !== readabilityVersion.value) return null;
      readabilityStatus.value = "fallback";
      readabilityReady.value = true;
      applyWithReadability(candidate, readabilityFor(candidate, fallback, { checking: true }));
      return fallback;
    }
  }

  function clearBackgroundPreviews() {
    (Array.isArray(backgrounds.value) ? backgrounds.value : []).forEach((background) => {
      if (background.previewUrl) URL.revokeObjectURL(background.previewUrl);
    });
    backgrounds.value = [];
  }
  async function refreshBackgrounds() {
    if (!isLoggedIn.value) { clearBackgroundPreviews(); return; }
    clearBackgroundPreviews();
    const items = (await personalizationAPI.getBackgrounds()).data?.data || [];
    backgrounds.value = items;
    await Promise.all(items.map(async (background) => {
      try {
        const response = await personalizationAPI.getBackgroundThumbnail(background.id);
        background.previewUrl = URL.createObjectURL(response.data);
      } catch { background.previewUrl = ""; }
    }));
  }

  async function apply(settingsToApply = settings.value, options = {}) {
    if (settingsToApply.background?.type === "image" && !imageUrl.value && (!isLoggedIn.value || ["pending", "failed"].includes(backgroundSyncState.value.status))) {
      const blob = await readGuestImage();
      if (blob) imageUrl.value = URL.createObjectURL(blob);
    }
    const readable = readabilityFor(settingsToApply, backgroundAnalysis.value, { checking: readabilityStatus.value === "checking" });
    applyPersonalization(settingsToApply, { imageUrl: imageUrl.value, readability: readable, ...options });
  }
  async function hydrateServerImage() {
    const imageId = settings.value.background?.imageId;
    if (["pending", "failed"].includes(backgroundSyncState.value.status) && settings.value.background?.type === "image") {
      const blob = await readGuestImage();
      if (blob) { setImageBlob(blob); return; }
    }
    if (!isLoggedIn.value) return;
    if (!imageId || !/^\d+$/.test(String(imageId))) {
      if (imageUrl.value) URL.revokeObjectURL(imageUrl.value);
      imageUrl.value = "";
      return;
    }
    const response = await personalizationAPI.getBackgroundImage(imageId);
    if (imageUrl.value) URL.revokeObjectURL(imageUrl.value);
    imageUrl.value = URL.createObjectURL(response.data);
  }
  function initFromStorage() { settings.value = readGuestSettings(); originalSettings.value = cloneSettings(settings.value); void preview(settings.value); }
  async function load() {
    loading.value = true;
    settings.value = readGuestSettings();
    try {
      if (isLoggedIn.value) {
        const response = await personalizationAPI.get();
        settings.value = ["pending", "failed"].includes(backgroundSyncState.value.status) ? readGuestSettings() : response.data?.data || settings.value;
        try { await refreshBackgrounds(); } catch { clearBackgroundPreviews(); }
      }
      await hydrateServerImage(); await preview(settings.value); originalSettings.value = cloneSettings(settings.value);
    } finally { loading.value = false; }
  }
  function hasGuestChanges(value = readGuestSettings()) {
    const baseline = defaultPersonalization();
    return JSON.stringify({ ...value, favorites: [], recent: [] }) !== JSON.stringify({ ...baseline, favorites: [], recent: [] }) || Boolean(value.background?.type === "image");
  }
  async function handleAuthTransition({ loggedIn, userId }) {
    const nextUserId = String(userId || "");
    if (!loggedIn) {
      activeUserId.value = ""; conflict.value = null; clearBackgroundPreviews();
      if (imageUrl.value) { URL.revokeObjectURL(imageUrl.value); imageUrl.value = ""; }
      settings.value = readGuestSettings(); originalSettings.value = cloneSettings(settings.value); await preview(settings.value); return;
    }
    if (!nextUserId || activeUserId.value === nextUserId) return;
    const guest = readGuestSettings(); const guestChanged = hasGuestChanges(guest);
    activeUserId.value = nextUserId;
    if (imageUrl.value) { URL.revokeObjectURL(imageUrl.value); imageUrl.value = ""; }
    try {
      const response = await personalizationAPI.get();
      const account = response.data?.data || defaultPersonalization();
      const accountChanged = hasGuestChanges(account);
      if (guestChanged && accountChanged && JSON.stringify(guest) !== JSON.stringify(account)) {
        const lastConflictHash = personalizationConflictHash(guest, account);
        const preference = readPersonalizationConflictPreference();
        const rememberedDecision = rememberedConflictDecision(preference, lastConflictHash);
        conflict.value = { guest: cloneSettings(guest), account: cloneSettings(account), lastConflictHash };
        if (rememberedDecision) {
          if (rememberedDecision === "account") await useAccountSettings({ remember: true });
          else await syncGuestToAccount({ remember: true });
          return;
        }
        settings.value = guest; originalSettings.value = cloneSettings(guest); await preview(settings.value); return;
      }
      settings.value = accountChanged ? account : guestChanged ? guest : account;
      originalSettings.value = cloneSettings(settings.value); await refreshBackgrounds(); await preview(settings.value);
      if (["pending", "failed"].includes(backgroundSyncState.value.status)) void retryPendingBackgroundSync({ account, quiet: true });
    } catch { settings.value = guest; originalSettings.value = cloneSettings(guest); await preview(settings.value); }
  }
  async function useAccountSettings({ remember = true } = {}) {
    if (!conflict.value) return;
    const resolved = conflict.value;
    settings.value = cloneSettings(resolved.account); originalSettings.value = cloneSettings(settings.value); conflict.value = null;
    if (remember) savePersonalizationConflictPreference("account", resolved.lastConflictHash);
    await refreshBackgrounds(); await hydrateServerImage(); await preview(settings.value);
  }
  async function syncGuestToAccount({ remember = true } = {}) {
    if (!conflict.value) return;
    const resolved = conflict.value;
    const next = cloneSettings(resolved.guest);
    if (next.background?.type === "image" && !String(next.background.imageId || "").match(/^\d+$/)) {
      conflict.value = null;
      if (remember) savePersonalizationConflictPreference("local", resolved.lastConflictHash);
      updateBackgroundSyncState({ status: "pending", retryCount: 0, lastError: "" });
      settings.value = cloneSettings(resolved.guest); originalSettings.value = cloneSettings(settings.value);
      await preview(settings.value);
      return retryPendingBackgroundSync({ account: resolved.account, quiet: false });
    }
    await personalizationAPI.save(next); settings.value = next; originalSettings.value = cloneSettings(next); conflict.value = null;
    if (remember) savePersonalizationConflictPreference("local", resolved.lastConflictHash);
    await refreshBackgrounds(); await hydrateServerImage(); await preview(settings.value);
  }
  async function retryPendingBackgroundSync({ account = null, quiet = false } = {}) {
    if (backgroundSyncLock || !isLoggedIn.value || !["pending", "failed"].includes(backgroundSyncState.value.status) || backgroundSyncState.value.retryCount >= 3) return false;
    backgroundSyncLock = true;
    updateBackgroundSyncState({ status: "syncing" });
    try {
      const guest = readGuestSettings();
      const image = await readGuestImage();
      if (guest.background?.type !== "image" || !image) throw Object.assign(new Error("Guest background is unavailable"), { syncCode: "missing" });
      const currentAccount = account || (await personalizationAPI.get()).data?.data || defaultPersonalization();
      let imageId = backgroundSyncState.value.pendingImageId;
      if (!imageId) {
        const upload = await personalizationAPI.uploadBackground(new File([image], "guest-background.webp", { type: image.type || "image/webp" }));
        imageId = upload.data?.data?.id;
        if (imageId) updateBackgroundSyncState({ status: "syncing", pendingImageId: imageId });
      }
      if (!imageId) throw new Error("Background upload returned no id");
      const next = mergeAccountWithGuestBackground(currentAccount, guest, imageId);
      await personalizationAPI.save(next);
      settings.value = next; originalSettings.value = cloneSettings(next);
      updateBackgroundSyncState({ status: "success", retryCount: 0, lastError: "", pendingImageId: null });
      await refreshBackgrounds(); await hydrateServerImage(); await preview(settings.value);
      return true;
    } catch (error) {
      const failure = error?.syncCode === "missing" ? { code: "missing", message: "本机背景图片不可用，请重新选择。" } : backgroundSyncError(error);
      updateBackgroundSyncState({ status: "failed", retryCount: backgroundSyncState.value.retryCount + 1, lastError: failure.code });
      const guest = readGuestSettings(); settings.value = guest; originalSettings.value = cloneSettings(guest); await preview(settings.value);
      notifyBackgroundSyncFailure(failure, quiet);
      return false;
    } finally { backgroundSyncLock = false; }
  }
  async function preview(next) { settings.value = cloneSettings(next); return checkReadability(settings.value); }
  async function validateReadability(next = settings.value) { settings.value = cloneSettings(next); return checkReadability(settings.value, { force: true, debounce: false }); }
  function markRecent(next) {
    const key = next.themeKey && next.themeKey !== "default" ? `theme:${next.themeKey}` : next.background?.type === "image" ? `image:${next.background.imageId || "guest"}` : `${next.background?.type || "default"}:${next.background?.color || ""}`;
    next.recent = [key, ...(next.recent || []).filter((item) => item !== key)].slice(0, 3);
  }
  async function save(next = settings.value) {
    await validateReadability(next);
    markRecent(settings.value);
    if (isLoggedIn.value) await personalizationAPI.save(settings.value);
    else saveGuestSettings(settings.value);
    originalSettings.value = cloneSettings(settings.value); applyWithReadability(settings.value, readabilityFor(settings.value, backgroundAnalysis.value));
  }
  async function cancel() { settings.value = cloneSettings(originalSettings.value); await preview(settings.value); }
  async function restoreDefault() { await preview(defaultPersonalization()); }
  function setImageBlob(blob) { pendingImageBlob = blob || null; if (imageUrl.value) URL.revokeObjectURL(imageUrl.value); imageUrl.value = URL.createObjectURL(blob); }
  async function setGuestImage(file) { await saveGuestImage(file); setImageBlob(file); }
  async function selectBackground(background) {
    const response = await personalizationAPI.getBackgroundImage(background.id);
    setImageBlob(response.data);
  }
  async function deleteBackground(background) {
    await personalizationAPI.deleteBackground(background.id);
    if (background.previewUrl) URL.revokeObjectURL(background.previewUrl);
    if (String(settings.value.background?.imageId) === String(background.id) && imageUrl.value) {
      URL.revokeObjectURL(imageUrl.value);
      imageUrl.value = "";
    }
    backgrounds.value = backgrounds.value.filter((item) => item.id !== background.id);
  }
  async function updateBackgroundPrivacy(background, privacy) {
    await personalizationAPI.updateBackgroundPrivacy(background.id, privacy);
    background.privacy = privacy;
  }
  return { settings, originalSettings, imageUrl, backgrounds, loading, isLoggedIn, conflict, backgroundSyncState, activeUserId, readabilityStatus, readabilityReady, backgroundAnalysis, readabilityVersion, initFromStorage, load, refreshBackgrounds, handleAuthTransition, useAccountSettings, syncGuestToAccount, retryPendingBackgroundSync, preview, validateReadability, save, cancel, restoreDefault, setGuestImage, setImageBlob, selectBackground, deleteBackground, updateBackgroundPrivacy, apply };
});
