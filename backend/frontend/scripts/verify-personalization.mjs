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
if (!appliedVariables.get("--app-card-bg")?.startsWith("rgba(255, 255, 255,"))
  throw new Error("White backgrounds must use the configured translucent card surface");
if (appliedVariables.get("--app-panel-bg") !== appliedVariables.get("--app-card-bg"))
  throw new Error("Settings panels must share the configured card surface");
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
if (!appliedVariables.get("--app-surface")?.startsWith("rgba(255, 255, 255,"))
  throw new Error("White backgrounds must use a translucent white header");
if (!style.includes("background: var(--app-card-bg)"))
  throw new Error("The personalized header must use the shared card glass");
if (!appliedVariables.get("--app-card-shadow")?.includes("rgba(15, 23, 42,"))
  throw new Error("White backgrounds must use the configured card shadow");
applyPersonalization(color("#111827"));
if (
  appliedVariables.get("--app-text-primary") !== "#F8FAFC" ||
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
if (!appliedVariables.get("--app-card-bg")?.startsWith("rgba(15, 23, 42,"))
  throw new Error("Dark backgrounds must use a readable dark glass card");
if (appliedVariables.get("--app-panel-bg") !== appliedVariables.get("--app-card-bg"))
  throw new Error("Dark background settings panels must share the configured card surface");
if (
  appliedVariables.get("--app-overlay") !== "rgba(0, 0, 0, 0)" ||
  appliedVariables.get("--app-tag-text") !== "#FFFFFF"
)
  throw new Error("Solid dark backgrounds must keep their original color");
if (!appliedVariables.get("--app-card-shadow")?.includes("rgba(15, 23, 42,"))
  throw new Error("Dark backgrounds must retain the configured card shadow");
const appearanceSnapshot = (card) => {
  applyPersonalization({ ...color("#FFFFFF"), card });
  return Object.fromEntries(
    [
      "--app-card-bg",
      "--app-blur",
      "--app-border",
      "--app-card-shadow",
      "--app-text-primary",
      "--app-input-text",
      "--app-input-bg",
      "--app-surface-strong",
    ].map(
      (key) => [key, appliedVariables.get(key)],
    ),
  );
};
const cardAt20 = appearanceSnapshot({ color: "#FFFFFF", opacity: 20, blur: 0, border: 0, shadow: 0 });
const cardAt50 = appearanceSnapshot({ color: "#FFFFFF", opacity: 50, blur: 16, border: 20, shadow: 25 });
const cardAt90 = appearanceSnapshot({ color: "#FFFFFF", opacity: 90, blur: 32, border: 40, shadow: 50 });
if (
  cardAt20["--app-card-bg"] === cardAt50["--app-card-bg"] ||
  cardAt50["--app-card-bg"] === cardAt90["--app-card-bg"] ||
  cardAt20["--app-blur"] !== "0px" ||
  cardAt50["--app-blur"] !== "16px" ||
  cardAt90["--app-blur"] !== "32px" ||
  cardAt20["--app-border"] === cardAt90["--app-border"] ||
  cardAt20["--app-card-shadow"] === cardAt90["--app-card-shadow"]
)
  throw new Error("Card opacity, blur, border, and shadow controls must change live CSS variables");
if (
  cardAt20["--app-text-primary"] !== cardAt90["--app-text-primary"] ||
  cardAt20["--app-input-text"] !== cardAt90["--app-input-text"] ||
  cardAt20["--app-input-bg"] !== cardAt90["--app-input-bg"] ||
  cardAt20["--app-surface-strong"] !== cardAt90["--app-surface-strong"]
)
  throw new Error("Card opacity must not fade text, inputs, or fixed chrome");
const themeAccents = ["ocean", "forest", "starlight", "sunset"].map((themeKey) => {
  applyPersonalization({ ...defaultPersonalization(), themeKey });
  return appliedVariables.get("--primary");
});
if (new Set(themeAccents).size !== themeAccents.length)
  throw new Error("Official themes must expose distinct global primary colors");
for (const [themeKey, pageBg, surfaceSoft] of [
  ["default", "#FFFFFF", "#F8FAFC"],
  ["starlight", "#F5F3FF", "#F7F4FF"],
  ["forest", "#F3FAF6", "#F2F8F4"],
  ["sunset", "#FFF7F2", "#FFF4EC"],
  ["minimal-gray", "#F3F4F6", "#F7F8FA"],
]) {
  applyPersonalization({ ...defaultPersonalization(), themeKey });
  if (
    appliedVariables.get("--page-bg") !== pageBg ||
    appliedVariables.get("--surface-soft") !== surfaceSoft ||
    !appliedVariables.get("--surface")?.startsWith("rgba(") ||
    !appliedVariables.get("--surface-border")?.startsWith("rgba(") ||
    appliedVariables.get("--app-card-bg") !== appliedVariables.get("--surface")
  )
    throw new Error(`${themeKey} must expose the shared themed surface tokens`);
}
applyPersonalization({ ...defaultPersonalization(), themeKey: "night" });
for (const [variable, expected] of [
  ["--text-primary", "#F5F7FB"],
  ["--text-secondary", "#D8DEEA"],
  ["--text-tertiary", "#AEB8CB"],
  ["--text-muted", "#8A95AA"],
  ["--text-on-primary", "#FFFFFF"],
  ["--text-inverse", "#0F172A"],
])
  if (appliedVariables.get(variable) !== expected)
    throw new Error(`Night theme must set ${variable} to a readable dark-mode value`);
if (
  appliedVariables.get("--app-text-primary") !== "#F5F7FB" ||
  appliedVariables.get("--app-text-secondary") !== "#D8DEEA" ||
  appliedVariables.get("--app-text-muted") !== "#8A95AA"
)
  throw new Error("Night theme must propagate readable text colors to app variables");
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
if (!appliedVariables.get("--app-card-shadow")?.includes("rgba(15, 23, 42,"))
  throw new Error("Complex images must use the configured card shadow");
applyPersonalization(gradient);
if (
  !appliedVariables
    .get("--personalization-background")
    .includes("linear-gradient")
)
  throw new Error("Gradient backgrounds must remain the root page background");
if (
  appliedVariables.get("--app-overlay") !== "transparent" ||
  appliedVariables.get("--app-text-primary") !== "#1F2937" ||
  !appliedVariables.get("--app-card-bg")?.startsWith("rgba(255, 255, 255, 0.880)")
)
  throw new Error(
    "Gradients must stay below near-white cards, dark text, and an overlay-free page",
  );
for (const opacity of [100, 80, 60, 40]) {
  applyPersonalization({
    ...gradient,
    card: { ...gradient.card, opacity },
  });
  if (
    appliedVariables.get("--surface-opacity") !== (opacity / 100).toFixed(3) ||
    appliedVariables.get("--app-text-primary") !== "#1F2937" ||
    appliedVariables.get("--app-input-text") !== "#1F2937" ||
    appliedVariables.get("--app-input-bg") !== "rgba(255, 255, 255, 0.960)"
  )
    throw new Error("Gradient card alpha must not fade text or input controls");
}
for (const source of [view, read("src/views/ProfileView.vue")])
  if (
    /\.(?:personalization-page|profile-page|profile-shell|profile-sidebar)[^{]*\{[^}]*\bopacity\s*:/.test(
      source,
    )
  )
    throw new Error("Personalization layout containers must not use opacity");
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
