// Grava o vídeo de reserva do pitch (~60 s, sem som) no site publicado, em português,
// na ordem da demonstração do roteiro (docs/11-apresentacao.md): WISE 0855 animando → D1 →
// Diferença → espectro → Barnard's Star.
//
//   node docs/apresentacao/gravar-video.mjs
//
// Saída: docs/apresentacao/demo-pitch.webm (abre no Chrome, Edge, Firefox e VLC).
// Usa o Playwright do frontend. A API fica bloqueada: só dados publicados.
import { createRequire } from "node:module";
import { copyFileSync, rmSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(new URL("../../frontend/package.json", import.meta.url));
const { chromium } = require("playwright");
const OUT = fileURLToPath(new URL("demo-pitch.webm", import.meta.url));
const BASE = "https://enriquessribeiro.github.io/spherex-viewer/";
const W = 1600, H = 900;

const dir = mkdtempSync(join(tmpdir(), "video-"));
const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: W, height: H }, locale: "pt-BR", recordVideo: { dir, size: { width: W, height: H } },
});
await ctx.route("**/api/**", (r) => r.abort());
const page = await ctx.newPage();
const wait = (s) => page.waitForTimeout(s * 1000);

// Legenda e marca de clique: o vídeo não mostra o cursor.
const overlay = () => page.evaluate(() => {
  if (document.getElementById("demo-caption")) return;
  const style = document.createElement("style");
  style.textContent = `
    #demo-caption { position: fixed; left: 24px; bottom: 24px; z-index: 9999; max-width: 760px;
      padding: 12px 18px; background: #141414; color: #f2efe7; font: 600 24px/1.3 "Archivo Variable", sans-serif;
      border-left: 5px solid #c4302b; opacity: 0; transition: opacity 300ms; }
    #demo-caption.on { opacity: 1; }
    .demo-tap { position: fixed; z-index: 9998; width: 44px; height: 44px; margin: -22px 0 0 -22px; border-radius: 50%;
      border: 4px solid #c4302b; pointer-events: none; animation: demo-tap 700ms ease-out forwards; }
    @keyframes demo-tap { from { transform: scale(.4); opacity: 1 } to { transform: scale(1.6); opacity: 0 } }`;
  document.head.append(style);
  const cap = document.createElement("div");
  cap.id = "demo-caption";
  document.body.append(cap);
  document.addEventListener("click", (ev) => {
    const dot = document.createElement("div");
    dot.className = "demo-tap";
    dot.style.left = `${ev.clientX}px`;
    dot.style.top = `${ev.clientY}px`;
    document.body.append(dot);
    setTimeout(() => dot.remove(), 800);
  }, true);
});
const caption = (text) => page.evaluate((t) => {
  const el = document.getElementById("demo-caption");
  el.textContent = t;
  el.classList.toggle("on", !!t);
}, text);
const scrollTo = (selector, offset = 0) => page.evaluate(([sel, off]) => {
  const top = document.querySelector(sel).getBoundingClientRect().top + window.scrollY - off;
  window.scrollTo({ top, behavior: "smooth" });
}, [selector, offset]);

await page.goto(`${BASE}?target=wise0855&lang=pt`, { waitUntil: "networkidle" });
await overlay();
await wait(1.5);
await caption("SPHEREx Viewer: fotos reais do SPHEREx, época por época");
await wait(3);
await scrollTo(".workbench", 16);
await wait(1);

await caption("WISE 0855, a anã marrom mais fria que se conhece, andando dentro do círculo");
await wait(11);

await caption("D1, infravermelho curto: ela some, é fria demais. A estrela de fundo fica parada");
await page.click('#detectors button:nth-child(1)');
await wait(7);
await page.click('#detectors button:nth-child(6)');
await wait(1);

await caption("Diferença: o céu parado some e sobra só o que mudou");
await page.click('[data-mode="diff"]');
await wait(8);

await caption("Espectro de 0,75 a 5 µm montado com as 258 exposições");
await page.click('[data-mode="play"]');
await scrollTo("#spectrum", 16);
await wait(9);

await caption("Barnard's Star: a estrela que mais rápido muda de lugar no céu");
await scrollTo(".workbench", 16);
await wait(1.5);
await page.click('.target:has-text("Barnard")');
await wait(11);

await caption("enriquessribeiro.github.io/spherex-viewer");
await wait(3);

const video = page.video();
await ctx.close();
await browser.close();
copyFileSync(await video.path(), OUT);
rmSync(dir, { recursive: true, force: true });
console.log(`vídeo gravado em ${OUT}`);
