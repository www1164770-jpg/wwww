import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (path) => readFile(resolve(root, path), "utf8");
const [style, personalization] = await Promise.all([
  read("src/style.css"),
  read("src/utils/personalization.js"),
]);

const expect = (condition, message) => {
  if (!condition) throw new Error(message);
};

expect(
  /--app-background:\s*var\(--personalization-background,\s*#FFFFFF\);/.test(
    style,
  ),
  "The global app background fallback must be #FFFFFF.",
);
expect(
  /html\s*\{[\s\S]*?background:\s*var\(--app-background\);/.test(style),
  "html must continue to render the personalized app background.",
);
expect(
  /body\s*\{[\s\S]*?background:\s*transparent;/.test(style),
  "body must remain transparent so personalized backgrounds are visible.",
);
expect(
  /background:\s*\{\s*type:\s*"default",\s*color:\s*"#FFFFFF"/.test(
    personalization,
  ),
  "defaultPersonalization must start with a white background.",
);

const themeColors = Object.fromEntries(
  [...personalization.matchAll(/key:\s*"([^"]+)",\s*name:\s*"[^"]+",\s*colors:\s*\["([^"]+)",\s*"([^"]+)"\]/g)].map(
    ([, key, first, second]) => [key, [first, second]],
  ),
);
expect(
  JSON.stringify(themeColors.default) === JSON.stringify(["#FFFFFF", "#3978F6"]),
  "The default official theme must use #FFFFFF.",
);
for (const [key, colors] of Object.entries({
  ocean: ["#E0F2FE", "#0284C7"],
  forest: ["#ECFDF5", "#059669"],
  starlight: ["#F5F3FF", "#7C3AED"],
  night: ["#111827", "#818CF8"],
  sunset: ["#FFF7ED", "#EA580C"],
  "minimal-gray": ["#F3F4F6", "#4B5563"],
  sakura: ["#FFF1F2", "#DB2777"],
}))
  expect(
    JSON.stringify(themeColors[key]) === JSON.stringify(colors),
    `The ${key} theme colors must remain unchanged.`,
  );

const defaultFallbacks = personalization.match(
  /palette\?\.colors\?\.\[0\]\s*\|\|\s*"(#[A-Fa-f0-9]{6})"/g,
) || [];
expect(
  defaultFallbacks.length >= 2 && defaultFallbacks.every((fallback) => fallback.endsWith('"#FFFFFF"')),
  "Default background palette fallbacks must be #FFFFFF.",
);
for (const marker of [
  'background.type === "image"',
  'background.type === "gradient"',
  'bg.type === "gradient"',
  'url("${imageUrl}")',
])
  expect(
    personalization.includes(marker),
    `Custom background behavior is missing: ${marker}`,
  );

console.log("default background verification passed");
