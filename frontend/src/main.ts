// SPHEREx Viewer: controlador da tela principal.
import "@fontsource-variable/archivo/wdth.css";
import "./style.css";
import { createElement, ChevronLeft, ChevronRight, Link, Pause, Play, Search } from "lucide";
import { difference, diffScale } from "./core/combine";
import { defaultDiffPair } from "./core/epochs";
import { renderDiff, renderGray } from "./core/render";
import { chooseSource, type Manifest, type ManifestTarget } from "./core/source";
import { parseState, serializeState, type Mode, type ViewState } from "./core/state";
import { DETECTORS, type Detector, type EpochDoc } from "./core/types";
import { worldToPixel } from "./core/wcs";
import { loadApiField, loadFrame, loadManifest, loadStaticField, type FieldHandle } from "./data";
import { pencilArrow, pencilCircle } from "./ui/marks";

const API_BASE: string | null = import.meta.env.VITE_API_BASE || null;
const ICONS = { ChevronLeft, ChevronRight, Link, Pause, Play, Search };

const DET_RANGE: Record<Detector, [number, number]> = {
  D1: [0.75, 1.09], D2: [1.1, 1.62], D3: [1.63, 2.41], D4: [2.42, 3.82], D5: [3.83, 4.41], D6: [4.42, 5.0],
};
const DET_HELP: Record<Detector, string> = {
  D1: "Infravermelho mais curto: estrelas comuns aparecem bem.",
  D2: "Estrelas e a banda de absorção da água.",
  D3: "Anãs frias começam a aparecer (metano em ~2,2 µm).",
  D4: "Gelo de água e metano.",
  D5: "Dióxido de carbono (CO₂).",
  D6: "Infravermelho mais longo: anãs marrons frias, como WISE 0855, brilham aqui.",
};
const MODE_HELP: Record<Mode, string> = {
  play: "Passa pelas épocas em ordem, como um filme curto.",
  blink: "Alterna entre duas épocas, como o comparador que achou Plutão em 1930.",
  diff: "Subtrai uma época da outra: o que ficou parado some.",
};
const MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

// ---------------------------------------------------------------------------- estado

const parsed = parseState(location.search);
let state: ViewState = parsed.state;
const view = { zoom: 1, gain: 0, negative: true, marks: true, playing: true, cursor: 0 };
let manifest: Manifest | null = null;
let field: FieldHandle | null = null;
let currentTarget: ManifestTarget | null = null;
let loadAbort: AbortController | null = null;
let timer: number | undefined;
let drawToken = 0;

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const canvas = $<HTMLCanvasElement>("plate-canvas");
const marks = document.getElementById("plate-marks") as unknown as SVGSVGElement;
const offscreen = document.createElement("canvas");

// ---------------------------------------------------------------------------- utilidades

function icon(el: Element, name: keyof typeof ICONS) {
  el.replaceChildren(createElement(ICONS[name], { width: 18, height: 18, "stroke-width": 1.75, "aria-hidden": "true" }));
}

function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}

function epochSpan(e: EpochDoc): string {
  return e.date_start === e.date_end ? formatDate(e.date_start) : `${formatDate(e.date_start)} – ${formatDate(e.date_end)}`;
}

function um(v: number): string {
  return v.toFixed(2).replace(".", ",");
}

function setStatus(message: string | null, kind: "info" | "error" = "info") {
  const el = $("plate-status");
  el.hidden = message === null;
  el.textContent = message ?? "";
  el.dataset.kind = kind;
}

function updateUrl() {
  const query = serializeState(state);
  history.replaceState(null, "", query ? `?${query}` : location.pathname);
}

/** Épocas que têm o detector atual. */
function epochsWithDet(): EpochDoc[] {
  if (!field || !state.det) return [];
  return field.doc.epochs.filter((e) => state.det! in e.frames);
}

// ---------------------------------------------------------------------------- carregamento

async function openFromState() {
  loadAbort?.abort();
  loadAbort = new AbortController();
  const signal = loadAbort.signal;
  stopTimer();
  field = null;
  const source = chooseSource(state, manifest, API_BASE);
  currentTarget = source.kind === "static" ? manifest!.targets.find((t) => t.id === source.targetId) ?? null : null;
  renderTargets();
  try {
    if (source.kind === "unavailable") {
      setStatus(`Não dá para abrir isso aqui: ${source.reason}. Escolha um dos alvos ao lado.`, "error");
      return;
    }
    if (source.kind === "resolve") {
      setStatus(`Procurando “${state.name}” no catálogo SIMBAD…`);
      const r = await fetch(source.resolveUrl, { signal });
      const body = await r.json();
      if (!r.ok) throw new Error(body?.error?.message ?? "objeto não encontrado");
      state = { ...state, name: undefined, target: undefined, ra: body.ra, dec: body.dec };
      updateUrl();
      return openFromState();
    }
    setStatus("Carregando a placa…");
    field = source.kind === "static"
      ? await loadStaticField(source.fieldUrl)
      : await loadApiField(source.fieldUrl, (p) => {
          setStatus(p.total
            ? `Baixando imagens do SPHEREx: ${p.done} de ${p.total}. Na primeira vez pode levar alguns minutos.`
            : "Consultando o arquivo da NASA (IRSA)…");
        }, signal);
    if (signal.aborted) return;
    setupField();
  } catch (err) {
    if ((err as Error).name === "AbortError") return;
    setStatus(`Não foi possível carregar: ${(err as Error).message}. Tente de novo ou escolha um dos alvos.`, "error");
  }
}

function setupField() {
  const doc = field!.doc;
  const available = DETECTORS.filter((d) => doc.epochs.some((e) => d in e.frames));
  if (!state.det || !available.includes(state.det)) {
    const preferred = currentTarget?.default_detector;
    state.det = preferred && available.includes(preferred) ? preferred : available.includes("D2") ? "D2" : available[0];
  }
  ensurePair();
  view.cursor = 0;
  setStatus(null);
  renderDetectors();
  renderPairSelects();
  renderModes();
  renderRuler();
  updateUrl();
  restartTimer();
  draw();
}

function ensurePair() {
  const indices = epochsWithDet().map((e) => e.index);
  if (state.a === undefined || state.b === undefined || !indices.includes(state.a) || !indices.includes(state.b) || state.a === state.b) {
    const pair = defaultDiffPair(epochsWithDet(), state.det!);
    state.a = pair?.[0];
    state.b = pair?.[1];
  }
}

// ---------------------------------------------------------------------------- desenho

function currentEpochIndex(): number | undefined {
  const epochs = epochsWithDet();
  if (epochs.length === 0) return undefined;
  if (state.mode === "blink") return view.cursor % 2 === 0 ? state.a : state.b;
  if (state.mode === "diff") return state.b;
  return epochs[view.cursor % epochs.length].index;
}

async function draw() {
  if (!field || !state.det) return;
  const token = ++drawToken;
  const doc = field.doc;
  const n = doc.grid.n;
  const det = state.det;
  const display = doc.display[det]!;
  const vmax = display.vmin + (display.vmax - display.vmin) * Math.pow(10, -view.gain);
  let rgba: Uint8ClampedArray;
  let shownEpoch: number | undefined;

  if (state.mode === "diff" && state.a !== undefined && state.b !== undefined) {
    const [fa, fb] = await Promise.all([loadFrame(field, state.a, det), loadFrame(field, state.b, det)]);
    if (token !== drawToken || !fa || !fb) return;
    const diff = difference(fa.data, fb.data);
    // O controle de contraste também realça a diferença.
    rgba = renderDiff(diff, diffScale(diff) * Math.pow(10, -view.gain));
    shownEpoch = state.b;
  } else {
    shownEpoch = currentEpochIndex();
    if (shownEpoch === undefined) return;
    const frame = await loadFrame(field, shownEpoch, det);
    if (token !== drawToken || !frame) return;
    rgba = renderGray(frame.data, frame.mask, display.vmin, vmax, display.stretch, view.negative);
  }

  offscreen.width = n;
  offscreen.height = n;
  offscreen.getContext("2d")!.putImageData(new ImageData(new Uint8ClampedArray(rgba), n, n), 0, 0);
  const crop = cropRect(n);
  const size = Math.round(canvas.clientWidth * devicePixelRatio) || 590;
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(offscreen, crop.x, crop.y, crop.w, crop.w, 0, 0, size, size);
  drawMarks(crop, shownEpoch);
  renderLabel(shownEpoch);
  highlightRuler(shownEpoch);
}

/** Recorte da placa conforme o zoom, centrado na posição do alvo (ou no centro do campo). */
function cropRect(n: number) {
  const w = n / view.zoom;
  const center = targetPixel(currentEpochIndex() ?? state.b) ?? { row: (n - 1) / 2, col: (n - 1) / 2 };
  const clamp = (v: number) => Math.min(Math.max(v, 0), n - w);
  return { x: clamp(center.col + 0.5 - w / 2), y: clamp(center.row + 0.5 - w / 2), w };
}

function targetPixel(epochIndex: number | undefined) {
  const doc = field?.doc;
  const p = doc?.target?.predicted_positions.find((x) => x.epoch === epochIndex);
  return doc && p ? worldToPixel(doc.grid.wcs, doc.grid.n, p.ra, p.dec) : null;
}

function drawMarks(crop: { x: number; y: number; w: number }, epochIndex: number | undefined) {
  const n = field!.doc.grid.n;
  marks.setAttribute("viewBox", `${crop.x} ${crop.y} ${crop.w} ${crop.w}`);
  const parts: string[] = [];
  if (view.marks) {
    const c = n / 2;
    const unit = crop.w / Math.max(canvas.clientWidth, 1); // tamanho de 1 px de tela em pixels da placa
    const g = 12 * unit, l = 20 * unit;
    parts.push(`<g class="reticle"><path d="M${c} ${c - g - l}V${c - g}M${c} ${c + g}V${c + g + l}M${c - g - l} ${c}H${c - g}M${c + g} ${c}H${c + g + l}"/></g>`);
    const here = targetPixel(epochIndex);
    if (here) {
      // Raio fixo em pixels de tela (~22 px), qualquer que seja o zoom.
      const x = here.col + 0.5, y = here.row + 0.5, r = (crop.w / Math.max(canvas.clientWidth, 1)) * 22;
      if (state.mode === "diff" && state.a !== undefined) {
        const before = targetPixel(state.a);
        if (before) parts.push(`<path class="pencil pencil-ghost" d="${pencilCircle(before.col + 0.5, before.row + 0.5, r, 2)}"/>`);
      }
      const arrow = pencilArrow(x, y, r);
      parts.push(`<path class="pencil" d="${pencilCircle(x, y, r, 1)}"/><path class="pencil" d="${arrow.shaft}"/><path class="pencil" d="${arrow.head}"/>`);
    }
  }
  marks.innerHTML = parts.join("");
}

function renderLabel(epochIndex: number | undefined) {
  const doc = field!.doc;
  const det = state.det!;
  const name = currentTarget?.name ?? doc.target?.name ?? `RA ${doc.center.ra.toFixed(4)}°, Dec ${doc.center.dec.toFixed(4)}°`;
  $("label-target").textContent = name;
  const epoch = doc.epochs.find((e) => e.index === epochIndex);
  const facts: [string, string][] = [];
  if (state.mode === "diff") {
    const a = doc.epochs.find((e) => e.index === state.a), b = epoch;
    $("label-epoch").textContent = a && b ? `${formatDate(a.date_start)} → ${formatDate(b.date_start)}` : "";
    if (a && b) facts.push(["Intervalo", `${Math.round(b.mjd_mid - a.mjd_mid)} dias`]);
  } else {
    $("label-epoch").textContent = epoch ? epochSpan(epoch) : "";
    if (epoch) facts.push(["Época", `${epochsWithDet().findIndex((e) => e.index === epoch.index) + 1} de ${epochsWithDet().length}`]);
    if (epoch?.frames[det]) facts.push(["Exposições", String(epoch.frames[det]!.n_exposures)]);
  }
  facts.push(["Detector", `${det} · ${um(DET_RANGE[det][0])}–${um(DET_RANGE[det][1])} µm`]);
  facts.push(["Campo", `${doc.fov_arcmin}′ × ${doc.fov_arcmin}′`]);
  $("label-facts").innerHTML = facts.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join("");
}

// ---------------------------------------------------------------------------- controles

function renderTargets() {
  const list = $("targets");
  list.innerHTML = "";
  for (const t of manifest?.targets ?? []) {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "target";
    button.setAttribute("aria-pressed", String(currentTarget?.id === t.id));
    button.innerHTML = `<img src="data/${t.thumbnail}" alt="" width="64" height="64" loading="lazy" />
      <span class="target-text"><span class="target-name">${t.name}</span><span class="target-desc">${t.description ?? ""}</span></span>`;
    button.addEventListener("click", () => {
      state = { ...state, target: t.id, ra: undefined, dec: undefined, name: undefined, det: undefined, a: undefined, b: undefined, fov: t.fov_arcmin };
      view.zoom = 1;
      renderZoom();
      updateUrl();
      openFromState();
    });
    li.append(button);
    list.append(li);
  }
}

function renderDetectors() {
  const box = $("detectors");
  box.innerHTML = "";
  const doc = field?.doc;
  const lo = 0.75, hi = 5.0;
  for (const d of DETECTORS) {
    const has = !!doc?.epochs.some((e) => d in e.frames);
    const button = document.createElement("button");
    button.type = "button";
    button.setAttribute("role", "radio");
    button.setAttribute("aria-checked", String(state.det === d));
    button.disabled = !has;
    const [a, b] = DET_RANGE[d];
    button.innerHTML = `<span class="det-name">${d}</span>
      <span class="det-band" aria-hidden="true"><span style="left:${((a - lo) / (hi - lo)) * 100}%;width:${((b - a) / (hi - lo)) * 100}%"></span></span>
      <span class="det-range">${um(a)}–${um(b)} µm</span>`;
    button.title = has ? DET_HELP[d] : "Sem imagens deste detector neste campo";
    button.addEventListener("click", () => {
      state = { ...state, det: d, a: undefined, b: undefined };
      ensurePair();
      view.cursor = 0;
      renderDetectors();
      renderPairSelects();
      renderRuler();
      updateUrl();
      draw();
    });
    box.append(button);
  }
  $("det-help").textContent = state.det ? DET_HELP[state.det] : "";
}

function renderModes() {
  for (const b of document.querySelectorAll<HTMLButtonElement>("#modes [data-mode]")) {
    b.setAttribute("aria-checked", String(b.dataset.mode === state.mode));
  }
  $("mode-help").textContent = MODE_HELP[state.mode];
  $("pair").hidden = state.mode === "play";
  $("diff-legend").hidden = state.mode !== "diff";
  const transport = state.mode !== "diff";
  for (const id of ["play", "prev", "next"]) ($(id) as HTMLButtonElement).disabled = !transport;
}

function renderPairSelects() {
  const options = epochsWithDet().map((e) => `<option value="${e.index}">${formatDate(e.date_start)} (${e.frames[state.det!]!.n_exposures} exp.)</option>`).join("");
  for (const [id, key] of [["epoch-a", "a"], ["epoch-b", "b"]] as const) {
    const select = $<HTMLSelectElement>(id);
    select.innerHTML = options;
    select.value = String(state[key]);
  }
}

function renderRuler() {
  const ruler = $("ruler");
  ruler.innerHTML = "";
  const doc = field?.doc;
  if (!doc) return;
  const all = doc.epochs;
  const t0 = Math.min(...all.map((e) => e.mjd_start)), t1 = Math.max(...all.map((e) => e.mjd_end));
  const span = Math.max(t1 - t0, 1);
  const pos = (mjd: number) => 3 + ((mjd - t0) / span) * 94;

  // marcas de mês na régua
  const start = new Date(Date.UTC(1858, 10, 17) + t0 * 864e5);
  const months = document.createElement("div");
  months.className = "ruler-months";
  for (let d = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + 1, 1)); ; d.setUTCMonth(d.getUTCMonth() + 1)) {
    const mjd = (d.getTime() - Date.UTC(1858, 10, 17)) / 864e5;
    if (mjd > t1) break;
    const tick = document.createElement("span");
    tick.className = d.getUTCMonth() === 0 ? "month year" : "month";
    tick.style.left = `${pos(mjd)}%`;
    if (d.getUTCMonth() === 0 || d.getUTCMonth() === 6) tick.dataset.label = d.getUTCMonth() === 0 ? String(d.getUTCFullYear()) : "jul";
    months.append(tick);
  }
  ruler.append(months);

  for (const e of all) {
    const has = !!state.det && state.det in e.frames;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "ruler-epoch";
    button.dataset.epoch = String(e.index);
    button.disabled = !has;
    button.style.left = `${pos(e.mjd_mid)}%`;
    const n = has ? e.frames[state.det!]!.n_exposures : 0;
    button.innerHTML = `<span class="tick" style="height:${Math.min(100, 30 + n * 3)}%"></span><span class="ruler-date">${MONTHS[Number(e.date_start.slice(5, 7)) - 1]} ${e.date_start.slice(2, 4)}</span>`;
    button.setAttribute("aria-label", `${epochSpan(e)}${has ? `, ${n} exposições` : ", sem este detector"}`);
    button.addEventListener("click", () => {
      if (state.mode === "play") {
        view.cursor = epochsWithDet().findIndex((x) => x.index === e.index);
        setPlaying(false);
      } else {
        state = { ...state, b: e.index };
        renderPairSelects();
        updateUrl();
      }
      draw();
    });
    ruler.append(button);
  }
}

function highlightRuler(epochIndex: number | undefined) {
  for (const b of document.querySelectorAll<HTMLButtonElement>(".ruler-epoch")) {
    const i = Number(b.dataset.epoch);
    b.classList.toggle("current", i === epochIndex);
    b.classList.toggle("pair", state.mode !== "play" && (i === state.a || i === state.b));
  }
}

function renderZoom() {
  for (const b of document.querySelectorAll<HTMLButtonElement>("[data-zoom]")) {
    b.setAttribute("aria-checked", String(Number(b.dataset.zoom) === view.zoom));
  }
}

function renderNegative() {
  for (const b of document.querySelectorAll<HTMLButtonElement>("[data-negative]")) {
    b.setAttribute("aria-checked", String((b.dataset.negative === "1") === view.negative));
  }
}

// ---------------------------------------------------------------------------- animação

function stopTimer() {
  if (timer !== undefined) clearInterval(timer);
  timer = undefined;
}

function restartTimer() {
  stopTimer();
  if (!view.playing || state.mode === "diff" || !field) return;
  timer = window.setInterval(() => {
    view.cursor++;
    draw();
  }, 1000 / state.fps);
}

function setPlaying(playing: boolean) {
  view.playing = playing;
  const button = $("play");
  icon(button.querySelector("[data-icon]") ?? button.firstElementChild!, playing ? "Pause" : "Play");
  button.querySelector(".label")!.textContent = playing ? "Pausar" : "Animar";
  restartTimer();
}

function step(delta: number) {
  const count = state.mode === "blink" ? 2 : epochsWithDet().length;
  if (!count) return;
  view.cursor = (view.cursor + delta + count) % count;
  setPlaying(false);
  draw();
}

// ---------------------------------------------------------------------------- eventos

function wire() {
  for (const el of document.querySelectorAll<HTMLElement>("[data-icon]")) icon(el, el.dataset.icon as keyof typeof ICONS);

  $("play").addEventListener("click", () => setPlaying(!view.playing));
  $("prev").addEventListener("click", () => step(-1));
  $("next").addEventListener("click", () => step(1));

  const fps = $<HTMLInputElement>("fps");
  fps.value = String(state.fps);
  $("fps-value").textContent = `${state.fps}/s`.replace(".", ",");
  fps.addEventListener("input", () => {
    state.fps = Number(fps.value);
    $("fps-value").textContent = `${state.fps}/s`.replace(".", ",");
    updateUrl();
    restartTimer();
  });

  for (const b of document.querySelectorAll<HTMLButtonElement>("#modes [data-mode]")) {
    b.addEventListener("click", () => {
      state.mode = b.dataset.mode as Mode;
      view.cursor = 0;
      ensurePair();
      renderModes();
      renderPairSelects();
      updateUrl();
      restartTimer();
      draw();
    });
  }
  for (const [id, key] of [["epoch-a", "a"], ["epoch-b", "b"]] as const) {
    $<HTMLSelectElement>(id).addEventListener("change", (ev) => {
      state[key] = Number((ev.target as HTMLSelectElement).value);
      updateUrl();
      draw();
    });
  }
  for (const b of document.querySelectorAll<HTMLButtonElement>("[data-zoom]")) {
    b.addEventListener("click", () => {
      view.zoom = Number(b.dataset.zoom);
      renderZoom();
      draw();
    });
  }
  for (const b of document.querySelectorAll<HTMLButtonElement>("[data-negative]")) {
    b.addEventListener("click", () => {
      view.negative = b.dataset.negative === "1";
      renderNegative();
      draw();
    });
  }
  const gain = $<HTMLInputElement>("gain");
  gain.addEventListener("input", () => {
    view.gain = Number(gain.value);
    draw();
  });
  $<HTMLInputElement>("marks").addEventListener("change", (ev) => {
    view.marks = (ev.target as HTMLInputElement).checked;
    draw();
  });

  $("copy-link").addEventListener("click", async () => {
    const label = $("copy-link").querySelector(".label")!;
    try {
      await navigator.clipboard.writeText(location.href);
      label.textContent = "Link copiado";
    } catch {
      label.textContent = "Copie da barra de endereço";
    }
    setTimeout(() => (label.textContent = "Copiar link"), 2200);
  });

  $<HTMLFormElement>("search").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const q = $<HTMLInputElement>("search-input").value.trim();
    if (!q) return;
    const known = manifest?.targets.find((t) => t.id === q.toLowerCase() || t.name.toLowerCase() === q.toLowerCase());
    const numeric = q.match(/^\s*([+-]?\d+(?:\.\d+)?)\s*[,\s]\s*([+-]?\d+(?:\.\d+)?)\s*$/);
    const base = { ...state, target: undefined, ra: undefined, dec: undefined, name: undefined, det: undefined, a: undefined, b: undefined };
    if (known) state = { ...base, target: known.id, fov: known.fov_arcmin };
    else if (numeric) state = { ...base, ra: Number(numeric[1]), dec: Number(numeric[2]) };
    else state = { ...base, name: q };
    updateUrl();
    openFromState();
  });

  document.addEventListener("keydown", (ev) => {
    if ((ev.target as HTMLElement).closest("input, select, textarea")) return;
    if (ev.key === " ") { ev.preventDefault(); setPlaying(!view.playing); }
    if (ev.key === "ArrowLeft") step(-1);
    if (ev.key === "ArrowRight") step(1);
  });

  new ResizeObserver(() => draw()).observe(canvas);
}

// ---------------------------------------------------------------------------- início

async function main() {
  document.body.classList.toggle("embed", state.embed);
  wire();
  renderZoom();
  renderNegative();
  renderModes();
  if (parsed.warnings.length) console.warn(parsed.warnings.join("\n"));
  manifest = await loadManifest();
  renderTargets();
  await openFromState();
}

main();
