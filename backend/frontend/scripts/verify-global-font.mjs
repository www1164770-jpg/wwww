import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = new URL("../", import.meta.url);
const sourceRoot = new URL("src/", root);
const style = readFileSync(new URL("src/style.css", root), "utf8");
const failures = [];

if (!style.includes('--font-main: "Songti SC", "STSong", "SimSun", "Noto Serif SC", serif') || !style.includes('--app-font-family: var(--font-main)')) {
  failures.push("src/style.css 缺少完整的 --app-font-family 字体栈");
}
if (!/body\s*\{[\s\S]*?font-family:\s*var\(--app-font-family\)/.test(style)) {
  failures.push("src/style.css 的 body 未使用 var(--app-font-family)");
}

function visit(directory) {
  for (const entry of readdirSync(directory)) {
    const path = join(directory, entry);
    const stat = statSync(path);
    if (stat.isDirectory()) visit(path);
    else if (/\.(vue|css|js|ts)$/.test(entry)) {
      const text = readFileSync(path, "utf8");
      const lines = text.split(/\r?\n/);
      lines.forEach((line, index) => {
        if (/font-family\s*:\s*sans-serif\b/.test(line) && !/font-family:\s*var\(--app-font-family\)/.test(line)) {
          failures.push(`${path}:${index + 1} 仍定义界面字体 sans-serif`);
        }
        if (/font-family\s*:\s*(?:Inter|Arial|Helvetica|system-ui|ui-sans-serif|["']Microsoft YaHei["']|["']Segoe UI["'])\b/i.test(line)) {
          failures.push(`${path}:${index + 1} 仍定义被禁止的界面字体`);
        }
      });
    }
  }
}

visit(fileURLToPath(sourceRoot));
const app = readFileSync(new URL("src/App.vue", root), "utf8");
if (/body\s*\{[^}]*font-family\s*:\s*sans-serif/i.test(app)) {
  failures.push("src/App.vue 仍定义 body font-family: sans-serif");
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
console.log("全局字体检查 PASS");
