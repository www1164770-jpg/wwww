import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
const root = resolve(import.meta.dirname, "..");
const read = (path) => readFile(resolve(root, path), "utf8");
const [router, view, store, utility, app, header, style, toast] =
  await Promise.all([
    read("src/router/index.js"),
    read("src/views/PersonalizationView.vue"),
    read("src/stores/personalization.js"),
    read("src/utils/personalization.js"),
    read("src/App.vue"),
    read("src/components/layout/AppHeader.vue"),
    read("src/style.css"),
    read("src/components/ToastNotification.vue"),
  ]);
for (const [source, needle] of [
  [router, 'path: "/personalization"'],
  [view, "个性化设置"],
  [view, 'type="color"'],
  [view, "textColorInput"],
  [view, "恢复自动"],
  [view, "#FFF 或 #FFFFFF"],
  [view, "image-editor"],
  [view, "previewDevice"],
  [view, "desktop"],
  [view, "mobile"],
  [view, "startDrag"],
  [view, "rotation"],
  [view, "background-library"],
  [view, "我的背景"],
  [view, "privacy-select"],
  [view, "toggleFavorite"],
  [view, "customThemes"],
  [view, "recent"],
  [store, "readabilityStatus"],
  [store, "readabilityReady"],
  [store, "readabilityVersion"],
  [store, "version !== readabilityVersion.value"],
  [store, "if (!isImage)"],
  [store, "validateReadability"],
  [store, "analyzeImageBlob"],
  [store, "handleAuthTransition"],
  [store, "syncGuestToAccount"],
  [store, "getBackgroundThumbnail"],
  [store, "URL.revokeObjectURL"],
  [utility, "zhihangyu_guest_personalization"],
  [utility, "gradientLuminance"],
  [utility, "readabilityFor"],
  [utility, "normalizeHexColor"],
  [utility, "relativeLuminance"],
  [utility, "indexedDB"],
  [header, "--app-surface-strong"],
  [header, "--app-text-primary"],
  [style, "--app-surface-safe"],
  [style, "--app-input-text"],
  [app, "personalization-conflict"],
  [app, 'path.startsWith("/admin")'],
])
  if (!source.includes(needle))
    throw new Error(`Missing personalization requirement: ${needle}`);
for (const forbidden of [
  "正在调整文字可读性",
  "readability-status",
  "readabilityMessage",
  "visualEditingDisabled",
  ':disabled="!readabilityReady"',
])
  if (view.includes(forbidden))
    throw new Error(`Visible readability UI must be removed: ${forbidden}`);
const {
  applyPersonalization,
  defaultPersonalization,
  gradientLuminance,
  mergeAccountWithGuestBackground,
  personalizationConflictHash,
  personalizationHash,
  readabilityFor,
  rememberedConflictDecision,
} = await import(
  pathToFileURL(resolve(root, "src/utils/personalization.js")).href
);
const color = (hex, typography = { mode: "auto", color: "#253044" }) => ({
  ...defaultPersonalization(),
  background: {
    ...defaultPersonalization().background,
    type: "color",
    color: hex,
  },
  typography,
});
const gradient = {
  ...defaultPersonalization(),
  background: { ...defaultPersonalization().background, type: "gradient" },
  gradient: {
    angle: 135,
    stops: [
      { color: "#FFFFFF", position: 0 },
      { color: "#111827", position: 100 },
    ],
  },
};
const guestConflict = { ...defaultPersonalization(), themeKey: "starlight" };
const accountConflict = { ...defaultPersonalization(), themeKey: "ocean" };
if (
  personalizationHash(guestConflict) !==
  personalizationHash({
    themeKey: "starlight",
    ...defaultPersonalization(),
    themeKey: "starlight",
  })
)
  throw new Error("Personalization hash must be stable across key order");
if (
  personalizationConflictHash(guestConflict, accountConflict) ===
  personalizationConflictHash(accountConflict, guestConflict)
)
  throw new Error("Conflict hash must preserve guest/account roles");
const conflictHash = personalizationConflictHash(
  guestConflict,
  accountConflict,
);
if (rememberedConflictDecision(null, conflictHash) !== null)
  throw new Error("First conflict must display the dialog");
if (
  rememberedConflictDecision(
    { decision: "account", lastConflictHash: conflictHash },
    conflictHash,
  ) !== "account"
)
  throw new Error("Same conflict must automatically use account settings");
if (
  rememberedConflictDecision(
    { decision: "local", lastConflictHash: conflictHash },
    conflictHash,
  ) !== "local"
)
  throw new Error("Same conflict must automatically sync local settings");
if (
  rememberedConflictDecision(
    { decision: "local", lastConflictHash: "" },
    conflictHash,
  ) !== "local"
)
  throw new Error("A user-updated preference must apply to the next conflict");
if (
  rememberedConflictDecision(
    { decision: "account", lastConflictHash: conflictHash },
    personalizationConflictHash(
      { ...guestConflict, favorites: ["night"] },
      accountConflict,
    ),
  ) !== null
)
  throw new Error("Changed settings must display the dialog again");
if (
  !utility.includes("zhihangyu_personalization_conflict_preference") ||
  !store.includes("rememberedConflictDecision")
)
  throw new Error("Conflict preference persistence is missing");
if (!view.includes("登录冲突处理") || !view.includes("changeConflictDecision"))
  throw new Error("Advanced conflict preference control is missing");
for (const needle of [
  "backgroundSyncState",
  "backgroundSyncLock",
  "retryPendingBackgroundSync",
  "mergeAccountWithGuestBackground",
  "retryCount >= 3",
])
  if (!store.includes(needle))
    throw new Error(`Missing recoverable background sync behavior: ${needle}`);
if (
  !view.includes("同步本机背景") ||
  !app.includes('path === "/" || path === "/personalization"')
)
  throw new Error("Background sync retry entry is missing");
if (app.includes("背景图片同步失败，请稍后重试"))
  throw new Error("Blocking background sync error message must be removed");
const accountWithBackground = {
  ...defaultPersonalization(),
  background: {
    ...defaultPersonalization().background,
    type: "image",
    imageId: 41,
  },
  typography: { mode: "custom", color: "#123456" },
};
const guestWithImage = {
  ...defaultPersonalization(),
  background: {
    ...defaultPersonalization().background,
    type: "image",
    imageId: null,
  },
  themeKey: "starlight",
};
const mergedAfterRetry = mergeAccountWithGuestBackground(
  accountWithBackground,
  guestWithImage,
  99,
);
if (mergedAfterRetry.background.imageId !== 99)
  throw new Error("Successful retry must save the uploaded background id");
if (mergedAfterRetry.typography.color !== "#123456")
  throw new Error(
    "Guest background sync must preserve account non-background settings",
  );
if (
  !store.includes("pendingImageId") ||
  /deleteGuestImage|indexedDB\.deleteDatabase/.test(store)
)
  throw new Error(
    "Failed sync must retain the IndexedDB blob and avoid duplicate upload",
  );
for (const variable of [
  "--app-page-bg",
  "--app-container-bg",
  "--app-card-bg",
  "--app-card-hover-bg",
  "--app-card-shadow",
  "--app-card-hover-shadow",
  "--app-blur",
])
  if (!style.includes(variable) || !utility.includes(variable))
    throw new Error(`Missing adaptive glass variable: ${variable}`);
for (const variable of [
  "--app-button-bg",
  "--app-button-bg-hover",
  "--app-button-border",
  "--app-button-shadow",
  "--app-button-primary-bg",
  "--app-button-primary-border",
])
  if (!style.includes(variable) || !view.includes(variable))
    throw new Error(
      `Missing personalization glass button variable: ${variable}`,
    );
if (
  !toast.includes("background: var(--app-button-bg)") ||
  !toast.includes("border: 1px solid var(--app-button-border)") ||
  !toast.includes("color: var(--app-text-primary)") ||
  !toast.includes("backdrop-filter: blur(18px)")
)
  throw new Error("Toast feedback must use the shared glass button system");
if (
  !view.includes(".personalization-shell > footer .primary") ||
  !view.includes(".personalization-shell > footer button:disabled") ||
  /\.personalization-shell > footer \.primary[^}]*background:\s*var\(--color-primary\)/.test(
    view,
  )
)
  throw new Error("Personalization footer actions must retain glass hierarchy");
for (const variable of [
  "--app-panel-bg",
  "--app-panel-soft-bg",
  "--app-control-bg",
])
  if (
    !style.includes(variable) ||
    !utility.includes(variable) ||
    !view.includes(variable)
  )
    throw new Error(`Missing personalization glass variable: ${variable}`);
if (
  !style.includes('html[data-personalization="on"] .page') ||
  !style.includes('html[data-personalization="on"] .career-profile-panel')
)
  throw new Error(
    "Personalized pages and career containers must use the transparent glass hierarchy",
  );
if (!view.includes("个性化设置") || !style.includes("background: transparent"))
  throw new Error(
    "Protected personalization controls must remain over the global background",
  );
const appliedVariables = new Map();
globalThis.document = {
  documentElement: {
    dataset: {},
    style: {
      setProperty: (key, value) => appliedVariables.set(key, value),
      removeProperty: (key) => appliedVariables.delete(key),
    },
  },
};
applyPersonalization(color("#FFFFFF"));
if (appliedVariables.get("--app-card-bg") !== "rgba(255, 255, 255, 0.70)")
  throw new Error("White backgrounds must use a local white glass card");
if (appliedVariables.get("--app-panel-bg") !== "rgba(255, 255, 255, 0.70)")
  throw new Error("White backgrounds must use a local white settings panel");
if (
  appliedVariables.get("--app-overlay") !== "rgba(0, 0, 0, 0)" ||
  appliedVariables.get("--app-tag-text") !== "#1F2937"
)
  throw new Error("White backgrounds must not use a global overlay");
if (
  appliedVariables.get("--app-text-primary") !== "#111827" ||
  appliedVariables.get("--app-text-secondary") !== "#4B5563" ||
  appliedVariables.get("--app-text-muted") !== "#6B7280" ||
  appliedVariables.get("--app-text-placeholder") !==
    "rgba(75, 85, 99, 0.76)"
)
  throw new Error("White backgrounds must use the dedicated dark text palette");
if (appliedVariables.get("--app-surface") !== "rgba(255, 255, 255, 0.75)")
  throw new Error("White backgrounds must use a translucent white header");
if (!style.includes("background: var(--app-card-bg)"))
  throw new Error("The personalized header must use the shared card glass");
if (
  appliedVariables.get("--app-card-shadow") !== "0 4px 12px rgba(0, 0, 0, 0.05)"
)
  throw new Error("White backgrounds must use the soft neutral card shadow");
applyPersonalization(color("#111827"));
if (
  appliedVariables.get("--app-text-primary") !==
    "rgba(255, 255, 255, 0.92)" ||
  appliedVariables.get("--app-text-secondary") !==
    "rgba(255, 255, 255, 0.78)" ||
  appliedVariables.get("--app-text-muted") !==
    "rgba(255, 255, 255, 0.64)" ||
  appliedVariables.get("--app-text-placeholder") !==
    "rgba(255, 255, 255, 0.58)" ||
  appliedVariables.get("--app-text-disabled") !==
    "rgba(255, 255, 255, 0.42)"
)
  throw new Error("Dark backgrounds must expose the complete readable text scale");
if (appliedVariables.get("--app-card-bg") !== "rgba(255, 255, 255, 0.12)")
  throw new Error("Dark backgrounds must use a visible light glass card");
if (appliedVariables.get("--app-panel-bg") !== "rgba(255, 255, 255, 0.12)")
  throw new Error("Dark backgrounds must use a visible light settings panel");
if (
  appliedVariables.get("--app-overlay") !== "rgba(0, 0, 0, 0)" ||
  appliedVariables.get("--app-tag-text") !== "#FFFFFF"
)
  throw new Error("Solid dark backgrounds must keep their original color");
if (
  appliedVariables.get("--app-card-shadow") !== "0 2px 8px rgba(0, 0, 0, 0.18)"
)
  throw new Error(
    "Dark backgrounds must retain a visible but compact card shadow",
  );
applyPersonalization(
  {
    ...defaultPersonalization(),
    background: { ...defaultPersonalization().background, type: "image" },
  },
  { imageUrl: "blob:test" },
);
if (
  !appliedVariables
    .get("--personalization-background")
    .includes('url("blob:test")')
)
  throw new Error("Image backgrounds must remain the root page background");
applyPersonalization(
  {
    ...defaultPersonalization(),
    background: { ...defaultPersonalization().background, type: "image" },
  },
  {
    imageUrl: "blob:complex",
    readability: {
      surfaceMode: "dark",
      textColor: "#FFFFFF",
      overlayStrength: 28,
      contrastSpread: 0.6,
    },
  },
);
if (appliedVariables.get("--app-overlay") !== "rgba(15, 23, 42, 0.12)")
  throw new Error(
    "Complex images must use the neutral interference-reduction overlay",
  );
if (
  appliedVariables.get("--app-card-shadow") !== "0 2px 8px rgba(0, 0, 0, 0.12)"
)
  throw new Error("Complex images must use the balanced card shadow");
applyPersonalization(gradient);
if (
  !appliedVariables
    .get("--personalization-background")
    .includes("linear-gradient")
)
  throw new Error("Gradient backgrounds must remain the root page background");
if (appliedVariables.get("--app-overlay") === "rgba(0, 0, 0, 0)")
  throw new Error("Gradient backgrounds must retain a light adaptive overlay");
if (readabilityFor(color("#FFFFFF")).textColor !== "#1F2937")
  throw new Error("White background must resolve dark text");
if (readabilityFor(color("#111827")).textColor !== "#F8FAFC")
  throw new Error("Black background must resolve light text");
if (readabilityFor(color("#FEF3C7")).textColor !== "#1F2937")
  throw new Error("Light yellow background must resolve dark text");
if (
  gradientLuminance(gradient.gradient).spread < 0.4 ||
  !readabilityFor(gradient).surfaceRequired
)
  throw new Error("Gradient must use multi-stop analysis and protection");
const customWhite = readabilityFor(
  color("#FFFFFF", { mode: "custom", color: "#FFFFFF" }),
);
if (!customWhite.surfaceRequired || customWhite.surfaceMode !== "light")
  throw new Error(
    "Low-contrast custom text must retain the background-driven surface mode",
  );
if (customWhite.textColor !== "#FFFFFF")
  throw new Error("Low-contrast custom text must keep the user's exact color");
applyPersonalization(
  color("#FFFFFF", { mode: "custom", color: "#3B82F6" }),
);
if (
  appliedVariables.get("--heading-text-color") !== "#3B82F6" ||
  appliedVariables.get("--app-text-primary") !== "#3B82F6" ||
  appliedVariables.get("--app-text-secondary") !== "rgba(59, 130, 246, 0.82)" ||
  appliedVariables.get("--app-chrome-text-primary") !== "#111827"
)
  throw new Error("Custom text must update content variables without changing app chrome");
console.log("personalization source verification passed");
