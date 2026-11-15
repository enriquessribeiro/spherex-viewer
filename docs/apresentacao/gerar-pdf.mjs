// Gera slides.pdf (e uma prévia PNG de cada slide) a partir de slides.html.
//
//   node docs/apresentacao/gerar-pdf.mjs
//
// Usa o Playwright instalado no frontend (npm install em frontend/ e
// npx playwright install chromium-headless-shell). As capturas em img/ vêm do site publicado.
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(new URL("../../frontend/package.json", import.meta.url));
const { chromium } = require("playwright");
const here = (p) => fileURLToPath(new URL(p, import.meta.url));

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto(new URL("slides.html", import.meta.url).href, { waitUntil: "networkidle" });
await page.evaluate(() => document.fonts.ready);
await page.waitForFunction(() => document.querySelector("#qr img[src], #qr canvas"));

const slides = await page.locator(".slide").count();
for (let i = 0; i < slides; i++) {
  await page.locator(".slide").nth(i).screenshot({ path: here(`previa/slide-${i + 1}.png`) });
}
await page.pdf({ path: here("slides.pdf"), width: "1920px", height: "1080px", printBackground: true, preferCSSPageSize: true });
console.log(`slides.pdf com ${slides} slides`);
await browser.close();
