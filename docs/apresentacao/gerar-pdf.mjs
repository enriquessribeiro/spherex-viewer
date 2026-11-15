// Gera o PDF (e uma prévia PNG de cada slide) a partir do HTML de mesmo nome.
//
//   node docs/apresentacao/gerar-pdf.mjs            # slides.html → slides.pdf (submissão, inglês)
//   node docs/apresentacao/gerar-pdf.mjs pitch-pt   # pitch-pt.html → pitch-pt.pdf (pitch, português)
//
// Usa o Playwright instalado no frontend (npm install em frontend/ e
// npx playwright install chromium-headless-shell). As capturas em img/ vêm do site publicado.
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(new URL("../../frontend/package.json", import.meta.url));
const { chromium } = require("playwright");
const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const name = process.argv[2] ?? "slides";
const prefix = name === "slides" ? "slide" : name;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto(new URL(`${name}.html`, import.meta.url).href, { waitUntil: "networkidle" });
await page.evaluate(() => document.fonts.ready);
await page.waitForFunction(() => document.querySelector("#qr img[src], #qr canvas"));

const slides = await page.locator(".slide").count();
for (let i = 0; i < slides; i++) {
  await page.locator(".slide").nth(i).screenshot({ path: here(`previa/${prefix}-${i + 1}.png`) });
}
await page.pdf({ path: here(`${name}.pdf`), width: "1920px", height: "1080px", printBackground: true, preferCSSPageSize: true });
console.log(`${name}.pdf com ${slides} slides`);
await browser.close();
