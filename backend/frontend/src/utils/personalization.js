export const GUEST_PERSONALIZATION_KEY = "zhihangyu_guest_personalization";
export const PERSONALIZATION_CONFLICT_PREFERENCE_KEY =
  "zhihangyu_personalization_conflict_preference";
export const PERSONALIZATION_CONFLICT_PREFERENCE_VERSION = 1;
export const GUEST_BACKGROUND_SYNC_STATE_KEY =
  "zhihangyu_guest_background_sync_state";

export function normalizeHexColor(value, fallback = "") {
  const candidate = String(value || "").trim();
  if (/^#[0-9A-Fa-f]{6}$/.test(candidate)) return candidate.toUpperCase();
  if (/^#[0-9A-Fa-f]{3}$/.test(candidate)) {
    return `#${candidate
      .slice(1)
      .split("")
      .map((character) => `${character}${character}`)
      .join("")}`.toUpperCase();
  }
  return fallback;
}

export function isValidHexColor(value) {
  return Boolean(normalizeHexColor(value));
}

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object")
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`)
      .join(",")}}`;
  return JSON.stringify(value);
}

// A small deterministic digest is enough here: only the digest, never the
// personalization payload, is stored in the conflict preference record.
export function personalizationHash(settings) {
  const source = stableJson(settings || defaultPersonalization());
  let hash = 2166136261;
  for (let index = 0; index < source.length; index += 1) {
    hash ^= source.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function personalizationConflictHash(guest, account) {
  return `${personalizationHash(guest)}:${personalizationHash(account)}`;
}

export function readPersonalizationConflictPreference() {
  try {
    const value = JSON.parse(
      localStorage.getItem(PERSONALIZATION_CONFLICT_PREFERENCE_KEY) || "null",
    );
    if (
      value?.version !== PERSONALIZATION_CONFLICT_PREFERENCE_VERSION ||
      !["account", "local"].includes(value?.decision) ||
      typeof value.lastConflictHash !== "string"
    )
      return null;
    return value;
  } catch {
    return null;
  }
}

export function savePersonalizationConflictPreference(
  decision,
  lastConflictHash = "",
) {
  if (!["account", "local"].includes(decision)) return null;
  const value = {
    decision,
    version: PERSONALIZATION_CONFLICT_PREFERENCE_VERSION,
    lastConflictHash,
    updatedAt: new Date().toISOString(),
  };
  localStorage.setItem(
    PERSONALIZATION_CONFLICT_PREFERENCE_KEY,
    JSON.stringify(value),
  );
  return value;
}

export function rememberedConflictDecision(preference, currentConflictHash) {
  if (!preference || !["account", "local"].includes(preference.decision))
    return null;
  return !preference.lastConflictHash ||
    preference.lastConflictHash === currentConflictHash
    ? preference.decision
    : null;
}

export function defaultBackgroundSyncState() {
  return {
    status: "idle",
    retryCount: 0,
    lastError: "",
    pendingImageId: null,
    updatedAt: "",
  };
}

export function readBackgroundSyncState() {
  try {
    const value = JSON.parse(
      localStorage.getItem(GUEST_BACKGROUND_SYNC_STATE_KEY) || "null",
    );
    if (
      !value ||
      !["idle", "pending", "syncing", "success", "failed"].includes(
        value.status,
      )
    )
      return defaultBackgroundSyncState();
    return {
      ...defaultBackgroundSyncState(),
      ...value,
      status: value.status === "syncing" ? "pending" : value.status,
      retryCount: Math.max(0, Number(value.retryCount) || 0),
    };
  } catch {
    return defaultBackgroundSyncState();
  }
}

export function saveBackgroundSyncState(next) {
  const value = {
    ...defaultBackgroundSyncState(),
    ...next,
    updatedAt: new Date().toISOString(),
  };
  localStorage.setItem(GUEST_BACKGROUND_SYNC_STATE_KEY, JSON.stringify(value));
  return value;
}

export function mergeAccountWithGuestBackground(account, guest, imageId) {
  const next = cloneSettings(account);
  const guestCopy = cloneSettings(guest);
  next.background = { ...guestCopy.background, imageId };
  next.gradient = guestCopy.gradient;
  next.themeKey = guestCopy.themeKey;
  return next;
}

export const officialThemes = [
  { key: "default", name: "系统默认", colors: ["#F8FAFC", "#FF7058"] },
  { key: "ocean", name: "深海蓝", colors: ["#E0F2FE", "#0284C7"] },
  { key: "forest", name: "森野绿", colors: ["#ECFDF5", "#059669"] },
  { key: "starlight", name: "星光紫", colors: ["#F5F3FF", "#7C3AED"] },
  { key: "night", name: "夜航", colors: ["#111827", "#818CF8"] },
  { key: "sunset", name: "落日橙", colors: ["#FFF7ED", "#EA580C"] },
  { key: "minimal-gray", name: "极简灰", colors: ["#F3F4F6", "#4B5563"] },
  { key: "sakura", name: "樱花粉", colors: ["#FFF1F2", "#DB2777"] },
];

export const defaultPersonalization = () => ({
  version: 1,
  background: {
    type: "default",
    color: "#F8FAFC",
    imageId: null,
    size: "cover",
    position: "center center",
    overlay: 0,
    brightness: 100,
    blur: 0,
    desktop: { positionX: 50, positionY: 50, scale: 1, rotation: 0 },
    mobile: { positionX: 50, positionY: 50, scale: 1, rotation: 0 },
  },
  gradient: {
    angle: 135,
    stops: [
      { color: "#7DD3FC", position: 0 },
      { color: "#A78BFA", position: 100 },
    ],
  },
  typography: { mode: "auto", color: "#253044" },
  card: { color: "#FFFFFF", opacity: 88, blur: 18, border: 12, shadow: 18 },
  themeKey: "default",
  customThemes: [],
  favorites: [],
  recent: [],
});

export function cloneSettings(settings) {
  return JSON.parse(JSON.stringify(settings || defaultPersonalization()));
}

export function readGuestSettings() {
  try {
    const defaults = defaultPersonalization();
    const stored = JSON.parse(
      localStorage.getItem(GUEST_PERSONALIZATION_KEY) || "null",
    );
    return {
      ...defaults,
      ...stored,
      typography: {
        ...defaults.typography,
        ...(stored?.typography || {}),
      },
    };
  } catch {
    return defaultPersonalization();
  }
}

export function saveGuestSettings(settings) {
  localStorage.setItem(GUEST_PERSONALIZATION_KEY, JSON.stringify(settings));
}

export function gradientCss(gradient = {}) {
  const stops = (gradient.stops || [])
    .map((stop) => `${stop.color} ${stop.position}%`)
    .join(", ");
  return `linear-gradient(${gradient.angle ?? 135}deg, ${stops || "#7DD3FC 0%, #A78BFA 100%"})`;
}

export function compositionFor(
  settings,
  viewport = typeof window === "undefined" ? 1280 : window.innerWidth,
) {
  const background = settings?.background || {};
  return (
    background[viewport <= 768 ? "mobile" : "desktop"] || {
      positionX: 50,
      positionY: 50,
      scale: 1,
      rotation: 0,
    }
  );
}

export function gradientLuminance(gradient = {}) {
  const stops = [...(gradient.stops || [])].sort(
    (a, b) => a.position - b.position,
  );
  if (stops.length < 2)
    return { average: relativeLuminance("#F8FAFC"), spread: 0 };
  const sample = (position) => {
    const right =
      stops.find((stop) => stop.position >= position) || stops.at(-1);
    const left =
      [...stops].reverse().find((stop) => stop.position <= position) ||
      stops[0];
    const ratio =
      left === right
        ? 0
        : (position - left.position) / (right.position - left.position);
    const channels = [0, 1, 2].map((index) =>
      Math.round(
        parseInt(left.color.slice(1 + index * 2, 3 + index * 2), 16) *
          (1 - ratio) +
          parseInt(right.color.slice(1 + index * 2, 3 + index * 2), 16) * ratio,
      ),
    );
    return `#${channels.map((channel) => channel.toString(16).padStart(2, "0")).join("")}`;
  };
  const values = [0, 20, 40, 60, 80, 100].map((position) =>
    relativeLuminance(sample(position)),
  );
  return {
    average: values.reduce((sum, value) => sum + value, 0) / values.length,
    spread: Math.max(...values) - Math.min(...values),
  };
}

function rgb(hex) {
  const cleaned = normalizeHexColor(hex, "#FFFFFF").slice(1);
  const value = Number.parseInt(cleaned, 16);
  return `${(value >> 16) & 255}, ${(value >> 8) & 255}, ${value & 255}`;
}

export function relativeLuminance(hex) {
  const channels = rgb(hex)
    .split(",")
    .map((part) => Number(part.trim()) / 255);
  const linear = channels.map((channel) =>
    channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4,
  );
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

function baseColorFor(settings) {
  const background = settings?.background || {};
  const palette = officialThemes.find(
    (theme) => theme.key === settings?.themeKey,
  );
  return background.type === "color"
    ? background.color
    : palette?.colors?.[0] || "#F8FAFC";
}

export function analyzeBackground(settings) {
  const background = settings?.background || {};
  if (background.type === "image") {
    const source = background.analysis || {};
    if (Number.isFinite(Number(source.averageLuminance))) {
      const average = Math.max(0, Math.min(1, Number(source.averageLuminance)));
      return {
        average,
        spread: Math.max(0, Math.min(1, Number(source.contrastSpread || 0))),
        darkRatio: Math.max(0, Math.min(1, Number(source.darkRatio || 0))),
        lightRatio: Math.max(0, Math.min(1, Number(source.lightRatio || 0))),
        recommendedTextMode:
          source.recommendedTextMode === "dark" ? "dark" : "light",
        pending: false,
      };
    }
    // An unanalysed image always starts from a dark safe surface and light text.
    return {
      average: 0.12,
      spread: 0.72,
      darkRatio: 0.5,
      lightRatio: 0.5,
      recommendedTextMode: "light",
      pending: true,
    };
  }
  if (background.type === "gradient") {
    const result = gradientLuminance(settings?.gradient);
    return {
      average: result.average,
      spread: result.spread,
      darkRatio: 0,
      lightRatio: 0,
      recommendedTextMode: result.average > 0.45 ? "dark" : "light",
      pending: false,
    };
  }
  const average = relativeLuminance(baseColorFor(settings));
  return {
    average,
    spread: 0,
    darkRatio: average < 0.35 ? 1 : 0,
    lightRatio: average > 0.7 ? 1 : 0,
    recommendedTextMode: average > 0.45 ? "dark" : "light",
    pending: false,
  };
}

export async function analyzeImageBlob(blob) {
  if (!blob || typeof document === "undefined" || typeof URL === "undefined")
    return null;
  const url = URL.createObjectURL(blob);
  try {
    const image = await new Promise((resolve, reject) => {
      const element = new Image();
      element.onload = () => resolve(element);
      element.onerror = reject;
      element.src = url;
    });
    const canvas = document.createElement("canvas");
    canvas.width = 32;
    canvas.height = 32;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
    const values = [];
    for (let index = 0; index < pixels.length; index += 4) {
      const channels = [
        pixels[index],
        pixels[index + 1],
        pixels[index + 2],
      ].map((channel) => channel / 255);
      const linear = channels.map((channel) =>
        channel <= 0.03928
          ? channel / 12.92
          : ((channel + 0.055) / 1.055) ** 2.4,
      );
      values.push(0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]);
    }
    const average =
      values.reduce((sum, value) => sum + value, 0) / values.length;
    return {
      average,
      spread: Math.max(...values) - Math.min(...values),
      darkRatio: values.filter((value) => value < 0.35).length / values.length,
      lightRatio: values.filter((value) => value > 0.7).length / values.length,
      recommendedTextMode: average > 0.45 ? "dark" : "light",
      pending: false,
    };
  } finally {
    URL.revokeObjectURL(url);
  }
}

export function readabilityFor(
  settings,
  analysis = analyzeBackground(settings),
  { checking = false } = {},
) {
  const mode = settings?.typography?.mode || "auto";
  const recommendedTextMode =
    analysis.recommendedTextMode === "dark" ? "dark" : "light";
  const recommendedTextColor =
    recommendedTextMode === "dark" ? "#1F2937" : "#F8FAFC";
  const requestedTextColor =
    mode === "auto"
      ? recommendedTextColor
      : mode === "light"
        ? "#F8FAFC"
        : mode === "dark"
          ? "#1F2937"
          : normalizeHexColor(settings?.typography?.color, "#253044");
  const background = settings?.background || {};
  const baseContrast =
    background.type === "image"
      ? 0
      : contrastRatio(requestedTextColor, baseColorFor(settings));
  const complex =
    background.type === "image" ||
    background.type === "gradient" ||
    analysis.spread >= 0.3;
  const manualLowContrast =
    mode !== "auto" &&
    (background.type === "image" || complex || baseContrast < 4.5);
  const lightSurfaceContrast = contrastRatio(requestedTextColor, "#F8FAFC");
  const darkSurfaceContrast = contrastRatio(requestedTextColor, "#0F172A");
  const requestedSurfaceMode =
    lightSurfaceContrast >= darkSurfaceContrast ? "light" : "dark";
  const automaticSurfaceMode =
    recommendedTextMode === "dark" ? "light" : "dark";
  const textColor = mode === "custom"
    ? requestedTextColor
    : checking
      ? "#F8FAFC"
      : requestedTextColor;
  const surfaceMode = checking
    ? "dark"
    : mode === "auto" || mode === "custom"
      ? automaticSurfaceMode
      : requestedSurfaceMode;
  const surfaceRequired =
    checking || complex || manualLowContrast;
  return {
    ...analysis,
    checking,
    recommendedTextMode,
    recommendedTextColor,
    textColor,
    surfaceMode,
    surfaceRequired,
    overlayStrength: checking
      ? 42
      : background.type === "image" && (complex || manualLowContrast)
        ? 28
        : 0,
    warning: manualLowContrast,
  };
}

export function textColorFor(settings) {
  return readabilityFor(settings).textColor;
}

export function needsProtectiveSurface(settings) {
  return readabilityFor(settings).surfaceRequired;
}

export function contrastRatio(a, b) {
  const [one, two] = [relativeLuminance(a), relativeLuminance(b)].sort(
    (x, y) => y - x,
  );
  return (one + 0.05) / (two + 0.05);
}

export function applyPersonalization(
  settings,
  { imageUrl = "", disabled = false, readability = null } = {},
) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  if (disabled) {
    root.dataset.personalization = "off";
    [
      "--personalization-background",
      "--personalization-background-size",
      "--personalization-background-position",
      "--personalization-overlay",
      "--personalization-image-filter",
      "--color-primary",
      "--color-primary-dark",
      "--color-heading",
      "--color-text",
      "--color-border",
      "--personalization-card",
      "--personalization-card-blur",
      "--personalization-card-shadow",
      "--app-text-primary",
      "--app-text-secondary",
      "--app-text-muted",
      "--heading-text-color",
      "--user-text-color",
      "--user-muted-text-color",
      "--app-chrome-text-primary",
      "--app-chrome-text-secondary",
      "--app-chrome-text-muted",
      "--app-text-placeholder",
      "--app-text-disabled",
      "--app-text-inverse",
      "--app-tab-text",
      "--app-tab-text-active",
      "--app-tab-hover-bg",
      "--app-tab-active-bg",
      "--favorite-color",
      "--favorite-muted-color",
      "--app-surface",
      "--app-surface-safe",
      "--app-surface-strong",
      "--app-border",
      "--app-input-bg",
      "--app-input-text",
      "--app-control-muted",
      "--app-readable-overlay",
      "--app-page-bg",
      "--app-container-bg",
      "--app-card-bg",
      "--app-card-hover-bg",
      "--app-panel-bg",
      "--app-panel-soft-bg",
      "--app-control-bg",
      "--background-overlay",
      "--app-overlay",
      "--app-card-border",
      "--app-tag-bg",
      "--app-tag-text",
      "--app-safe-surface",
      "--app-card-content-overlay",
      "--app-blur",
      "--app-card-shadow-color",
      "--app-card-shadow",
      "--app-card-hover-shadow",
      "--app-control-shadow",
    ].forEach((name) => root.style.removeProperty(name));
    return;
  }
  const safe = settings || defaultPersonalization();
  const bg = safe.background || {};
  const composition = compositionFor(safe);
  const palette = officialThemes.find((theme) => theme.key === safe.themeKey);
  const base =
    bg.type === "color"
      ? bg.color
      : bg.type === "gradient"
        ? gradientCss(safe.gradient)
        : palette?.colors?.[0] || "#F8FAFC";
  const readable = readability || readabilityFor(safe);
  const customTextColor = normalizeHexColor(
    safe.typography?.color,
    "#253044",
  );
  const isCustomText = safe.typography?.mode === "custom";
  const isColorBackground = bg.type === "color";
  const colorLuminance = isColorBackground
    ? relativeLuminance(bg.color || base)
    : 0;
  const nearWhiteBackground = isColorBackground && colorLuminance > 0.9;
  const foreground = isCustomText
    ? customTextColor
    : nearWhiteBackground
      ? "#111827"
      : readable.textColor;
  const surfaceIsLight = readable.surfaceMode === "light";
  const chromePrimary = nearWhiteBackground
    ? "#111827"
    : surfaceIsLight
      ? readable.recommendedTextColor
      : "rgba(255, 255, 255, 0.92)";
  const chromeSecondary = nearWhiteBackground
    ? "#4B5563"
    : surfaceIsLight
      ? "#475569"
      : "rgba(255, 255, 255, 0.78)";
  const chromeMuted = nearWhiteBackground
    ? "#6B7280"
    : surfaceIsLight
      ? "#64748B"
      : "rgba(255, 255, 255, 0.64)";
  const primary = isCustomText
    ? customTextColor
    : nearWhiteBackground
    ? "#111827"
    : surfaceIsLight
      ? foreground
      : "rgba(255, 255, 255, 0.92)";
  const surface = nearWhiteBackground
    ? "rgba(255, 255, 255, 0.75)"
    : surfaceIsLight
      ? "rgba(255, 255, 255, 0.92)"
      : "rgba(15, 23, 42, 0.88)";
  const strongSurface = nearWhiteBackground
    ? "rgba(255, 255, 255, 0.85)"
    : surfaceIsLight
      ? "rgba(255, 255, 255, 0.97)"
      : "rgba(15, 23, 42, 0.95)";
  const secondary = isCustomText
    ? `rgba(${rgb(customTextColor)}, 0.82)`
    : nearWhiteBackground
    ? "#4B5563"
    : surfaceIsLight
      ? "#475569"
      : "rgba(255, 255, 255, 0.78)";
  const muted = isCustomText
    ? `rgba(${rgb(customTextColor)}, 0.66)`
    : nearWhiteBackground
    ? "#6B7280"
    : surfaceIsLight
      ? "#64748B"
      : "rgba(255, 255, 255, 0.64)";
  const placeholder = nearWhiteBackground
    ? "rgba(75, 85, 99, 0.76)"
    : surfaceIsLight
      ? "rgba(71, 85, 105, 0.76)"
      : "rgba(255, 255, 255, 0.58)";
  const disabledText = nearWhiteBackground
    ? "rgba(107, 114, 128, 0.66)"
    : surfaceIsLight
      ? "rgba(100, 116, 139, 0.66)"
      : "rgba(255, 255, 255, 0.42)";
  const containerBackground = nearWhiteBackground
    ? "rgba(255, 255, 255, 0.65)"
    : surfaceIsLight
      ? "rgba(15, 23, 42, 0.04)"
      : "rgba(255, 255, 255, 0.08)";
  const cardBackground = nearWhiteBackground
    ? "rgba(255, 255, 255, 0.70)"
    : surfaceIsLight
      ? "rgba(15, 23, 42, 0.08)"
      : "rgba(255, 255, 255, 0.12)";
  const cardHoverBackground = nearWhiteBackground
    ? "rgba(255, 255, 255, 0.85)"
    : surfaceIsLight
      ? "rgba(15, 23, 42, 0.10)"
      : "rgba(255, 255, 255, 0.18)";
  const controlBackground = nearWhiteBackground
    ? "rgba(255, 255, 255, 0.85)"
    : surfaceIsLight
      ? "rgba(15, 23, 42, 0.10)"
      : "rgba(255, 255, 255, 0.18)";
  const analysisSpread = Number(
    readable.contrastSpread ?? readable.spread ?? 0,
  );
  const complexImage = bg.type === "image" && analysisSpread >= 0.3;
  const appOverlay = isColorBackground
    ? "rgba(0, 0, 0, 0)"
    : bg.type === "gradient"
      ? surfaceIsLight
        ? "rgba(15, 23, 42, 0.04)"
        : "rgba(255, 255, 255, 0.03)"
      : complexImage
        ? "rgba(15, 23, 42, 0.12)"
        : surfaceIsLight
          ? "rgba(15, 23, 42, 0.08)"
          : "rgba(255, 255, 255, 0.08)";
  const cardBorder = nearWhiteBackground
    ? "rgba(15, 23, 42, 0.08)"
    : surfaceIsLight
      ? "rgba(15, 23, 42, 0.16)"
      : "rgba(255, 255, 255, 0.28)";
  const tagBackground = surfaceIsLight
    ? "rgba(255, 255, 255, 0.65)"
    : "rgba(255, 255, 255, 0.18)";
  const tagText = surfaceIsLight ? "#1F2937" : "#FFFFFF";
  const safeSurface = nearWhiteBackground
    ? "rgba(255, 255, 255, 0.85)"
    : surfaceIsLight
      ? "rgba(15, 23, 42, 0.08)"
      : "rgba(255, 255, 255, 0.18)";
  const cardContentOverlay = surfaceIsLight
    ? "rgba(255, 255, 255, 0.24)"
    : "rgba(15, 23, 42, 0.22)";
  const cardShadowAlpha = nearWhiteBackground
    ? 0.05
    : complexImage
      ? 0.12
      : surfaceIsLight
        ? 0.08
        : 0.18;
  const cardHoverShadowAlpha = Math.min(cardShadowAlpha + 0.04, 0.22);
  const overlay =
    bg.type === "image"
      ? Math.max(Number(bg.overlay || 0), readable.overlayStrength || 0) / 100
      : 0;
  const imageBackground =
    bg.type === "image" && imageUrl
      ? `linear-gradient(rgba(${surfaceIsLight ? "255,255,255" : "15,23,42"}, ${overlay}), rgba(${surfaceIsLight ? "255,255,255" : "15,23,42"}, ${overlay})), url("${imageUrl}")`
      : base;
  root.dataset.personalization = "on";
  root.style.setProperty("--personalization-background", imageBackground);
  root.style.setProperty(
    "--personalization-background-size",
    bg.type === "image"
      ? bg.size === "stretch"
        ? "100% 100%"
        : bg.size
      : "cover",
  );
  root.style.setProperty(
    "--personalization-background-position",
    `${composition.positionX ?? 50}% ${composition.positionY ?? 50}%`,
  );
  root.style.setProperty("--personalization-overlay", String(overlay));
  root.style.setProperty(
    "--personalization-image-filter",
    `brightness(${bg.brightness || 100}%) blur(${bg.blur || 0}px)`,
  );
  root.style.setProperty(
    "--personalization-background-scale",
    String(composition.scale || 1),
  );
  root.dataset.personalizationProtective = readable.surfaceRequired
    ? "on"
    : "off";
  root.style.setProperty("--color-primary", palette?.colors?.[1] || "#FF7058");
  root.style.setProperty(
    "--color-primary-dark",
    palette?.colors?.[1] || "#EF5B45",
  );
  root.style.setProperty("--app-text-primary", primary);
  root.style.setProperty("--app-text-secondary", secondary);
  root.style.setProperty("--app-text-muted", muted);
  root.style.setProperty("--heading-text-color", foreground);
  root.style.setProperty("--user-text-color", primary);
  root.style.setProperty("--user-muted-text-color", muted);
  root.style.setProperty("--app-chrome-text-primary", chromePrimary);
  root.style.setProperty("--app-chrome-text-secondary", chromeSecondary);
  root.style.setProperty("--app-chrome-text-muted", chromeMuted);
  root.style.setProperty("--app-text-placeholder", placeholder);
  root.style.setProperty("--app-text-disabled", disabledText);
  root.style.setProperty("--app-text-inverse", "#FFFFFF");
  root.style.setProperty(
    "--app-tab-text",
    surfaceIsLight ? muted : secondary,
  );
  root.style.setProperty("--app-tab-text-active", primary);
  root.style.setProperty(
    "--app-tab-hover-bg",
    surfaceIsLight
      ? "rgba(15, 23, 42, 0.04)"
      : "rgba(255, 255, 255, 0.06)",
  );
  root.style.setProperty(
    "--app-tab-active-bg",
    surfaceIsLight
      ? "rgba(15, 23, 42, 0.08)"
      : "rgba(255, 255, 255, 0.12)",
  );
  root.style.setProperty(
    "--favorite-color",
    palette?.colors?.[1] || "#FF7058",
  );
  root.style.setProperty(
    "--favorite-muted-color",
    surfaceIsLight
      ? "rgba(30, 40, 60, 0.45)"
      : "rgba(255, 255, 255, 0.55)",
  );
  root.style.setProperty("--app-surface", surface);
  root.style.setProperty("--app-surface-safe", surface);
  root.style.setProperty("--app-surface-strong", strongSurface);
  root.style.setProperty(
    "--app-border",
    nearWhiteBackground
      ? "rgba(15, 23, 42, 0.08)"
      : surfaceIsLight
        ? "rgba(15, 23, 42, 0.16)"
        : "rgba(226, 232, 240, 0.24)",
  );
  root.style.setProperty("--app-input-bg", strongSurface);
  root.style.setProperty(
    "--app-input-text",
    surfaceIsLight ? "#1F2937" : "#F8FAFC",
  );
  root.style.setProperty("--app-control-muted", muted);
  root.style.setProperty("--app-readable-overlay", appOverlay);
  root.style.setProperty("--app-page-bg", "transparent");
  root.style.setProperty("--app-container-bg", containerBackground);
  root.style.setProperty("--app-card-bg", cardBackground);
  root.style.setProperty("--app-card-hover-bg", cardHoverBackground);
  root.style.setProperty("--app-panel-bg", cardBackground);
  root.style.setProperty("--app-panel-soft-bg", containerBackground);
  root.style.setProperty("--app-control-bg", controlBackground);
  root.style.setProperty("--background-overlay", appOverlay);
  root.style.setProperty("--app-overlay", appOverlay);
  root.style.setProperty("--app-card-border", cardBorder);
  root.style.setProperty("--app-tag-bg", tagBackground);
  root.style.setProperty("--app-tag-text", tagText);
  root.style.setProperty("--app-safe-surface", safeSurface);
  root.style.setProperty("--app-card-content-overlay", cardContentOverlay);
  root.style.setProperty("--app-blur", "20px");
  root.style.setProperty(
    "--app-card-shadow-color",
    `rgba(0, 0, 0, ${cardShadowAlpha})`,
  );
  root.style.setProperty(
    "--app-card-shadow",
    nearWhiteBackground
      ? "0 4px 12px rgba(0, 0, 0, 0.05)"
      : `0 2px 8px rgba(0, 0, 0, ${cardShadowAlpha})`,
  );
  root.style.setProperty(
    "--app-card-hover-shadow",
    `0 6px 18px rgba(0, 0, 0, ${cardHoverShadowAlpha})`,
  );
  root.style.setProperty(
    "--app-control-shadow",
    `0 2px 6px rgba(0, 0, 0, ${Math.min(cardShadowAlpha, 0.1)})`,
  );
  root.style.setProperty("--color-heading", foreground);
  root.style.setProperty("--color-text", secondary);
  root.style.setProperty("--color-muted", muted);
  root.style.setProperty(
    "--color-border",
    nearWhiteBackground
      ? "rgba(15, 23, 42, 0.08)"
      : `rgba(${rgb(foreground)}, ${Math.max(0.16, Number(safe.card?.border || 12) / 100)})`,
  );
  root.style.setProperty(
    "--personalization-card",
    `rgba(${rgb(safe.card?.color)}, ${Number(safe.card?.opacity ?? 88) / 100})`,
  );
  root.style.setProperty(
    "--personalization-card-blur",
    `${safe.card?.blur ?? 18}px`,
  );
  root.style.setProperty(
    "--personalization-card-shadow",
    "var(--app-card-shadow)",
  );
}

const IMAGE_DB = "zhihangyu-personalization";
export async function saveGuestImage(blob) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(IMAGE_DB, 1);
    request.onupgradeneeded = () => request.result.createObjectStore("images");
    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      const tx = request.result.transaction("images", "readwrite");
      tx.objectStore("images").put(blob, "background");
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    };
  });
}

export async function readGuestImage() {
  return new Promise((resolve) => {
    const request = indexedDB.open(IMAGE_DB, 1);
    request.onerror = () => resolve(null);
    request.onsuccess = () => {
      const tx = request.result.transaction("images", "readonly");
      const get = tx.objectStore("images").get("background");
      get.onsuccess = () => resolve(get.result || null);
      get.onerror = () => resolve(null);
    };
  });
}
