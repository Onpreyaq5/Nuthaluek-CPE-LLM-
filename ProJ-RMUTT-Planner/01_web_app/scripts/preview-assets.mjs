// Local preview fallback for Windows environments that block child processes.
// Normal team development and deployment use the Vite scripts in package.json.
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { compile } from "@tailwindcss/node";
import { Scanner } from "@tailwindcss/oxide";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const out = path.join(root, "preview-dist");
await fs.mkdir(path.join(out, "assets", "fonts"), { recursive: true });
const css = await fs.readFile(path.join(root, "src/index.css"), "utf8");
const compiled = await compile(css, {
  base: path.join(root, "src"),
  onDependency() {},
});
const scanner = new Scanner({
  sources: [{ base: root, pattern: "src/**/*.{ts,tsx}", negated: false }],
});
const built = compiled
  .build(scanner.scan())
  .replace(
    /url\(([^)]*\.woff2?)\)/g,
    (_, url) => `url("./fonts/${path.basename(url.replace(/["']/g, ""))}")`,
  );
await fs.writeFile(path.join(out, "assets/style.css"), built);
const fonts = path.join(root, "node_modules/@fontsource/noto-sans-thai/files");
for (const file of await fs.readdir(fonts))
  if (/\.woff2?$/.test(file))
    await fs.copyFile(
      path.join(fonts, file),
      path.join(out, "assets/fonts", file),
    );
await fs.cp(path.join(root, "public"), out, { recursive: true });
const html = (await fs.readFile(path.join(root, "index.html"), "utf8")).replace(
  '<script type="module" src="/src/main.tsx"></script>',
  '<link rel="stylesheet" href="/assets/style.css"/><script type="module" src="/assets/app.js"></script>',
);
await fs.writeFile(path.join(out, "index.html"), html);
console.log("Preview styles, public assets, and HTML prepared.");
