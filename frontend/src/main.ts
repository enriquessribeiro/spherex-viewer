// SPHEREx Viewer: controlador da tela principal.
import "@fontsource-variable/archivo/wdth.css";
import "./style.css";
import { createElement, ChevronLeft, ChevronRight, Languages, Link, Pause, Play, Search } from "lucide";
import { significance } from "./core/combine";
import { defaultDiffPair } from "./core/epochs";
import { overlayFlags, renderDiff, renderGray, renderRgb, type ColorChannel } from "./core/render";
import { sumFrames } from "./core/combine";
import type { MaskGrid } from "./core/frames";
import { chooseSource, staticFovs, type Manifest, type ManifestTarget } from "./core/source";
import { DEFAULT_STATE, parseState, serializeState, type Mode, type ViewState } from "./core/state";
import { DETECTORS, type Detector, type EpochDoc } from "./core/types";
import { worldToPixel } from "./core/wcs";
import { cropAnchor, zoomCrop } from "./core/crop";
import { peakNear, targetLimits } from "./core/contrast";
import { fetchJson, loadApiField, loadFrame, loadManifest, loadStaticField, type FieldHandle } from "./data";
import { FIELD_REFERENCE_MJD, propagate } from "./core/motion";
import { parseCoordinates } from "./core/coords";
import { nearbyTarget, type MovingTarget } from "./core/nearby";
import { pencilArrow, pencilCircle } from "./ui/marks";
import { SkyMap, type CatalogKey } from "./ui/skymap";
import { SpectrumView } from "./ui/spectrum";
import type { SpectrumDoc } from "./core/spectrum";
import { applyStatic, fmtDate, fmtNum, getLang, monthName, pickLang, setLang, t, type Lang } from "./i18n";

const API_BASE: string | null = import.meta.env.VITE_API_BASE || null;
const ICONS = { ChevronLeft, ChevronRight, Languages, Link, Pause, Play, Search };

const DET_RANGE: Record<Detector, [number, number]> = {
  D1: [0.75, 1.09], D2: [1.1, 1.62], D3: [1.63, 2.41], D4: [2.42, 3.82], D5: [3.83, 4.41], D6: [4.42, 5.0],
};
const detHelp = (d: Detector) => t(`det.${d}`);
const modeHelp = (m: Mode) => t(`mode.${m}`);

// ---------------------------------------------------------------------------- estado

const parsed = parseState(location.search);
let state: ViewState = parsed.state;
const LANG_KEY = "spherex-viewer:lang";
function storedLang(): string | null {
  try { return localStorage.getItem(LANG_KEY); } catch { return null; }
}
setLang(pickLang(state.lang, storedLang(), navigator.languages ?? [navigator.language]));
const view = { zoom: 1, gain: 0, negative: false, marks: true, flags: false, playing: true, cursor: 0, flagged: 0,
  /** Limites de contraste em uso (os do campo, ou os do alvo); o controle Contraste age sobre eles. */
  limits: null as { det: Detector; vmin: number; vmax: number } | null };
/** Falsa cor: o detector mais longo no vermelho, como no céu visível. */
const COLOR_DETS: [Detector, Detector, Detector] = ["D6", "D3", "D1"];
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
  return fmtDate(y, m - 1, d);
}

function epochSpan(e: EpochDoc): string {
  return e.date_start === e.date_end ? formatDate(e.date_start) : `${formatDate(e.date_start)} – ${formatDate(e.date_end)}`;
}

function um(v: number): string {
  return fmtNum(v, 2);
}

/** Texto do alvo no idioma atual (o manifesto traz o português e, quando há, o inglês). */
function targetText(target: ManifestTarget, key: "description" | "look_for"): string {
  return (getLang() === "en" ? target[`${key}_en`] : undefined) ?? target[key] ?? "";
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
  drawToken++; // um draw() em andamento do campo anterior não pode terminar sem campo
  let notice: string | null = null;

  // Coordenada de catálogo (ex.: a do desafio para o WISE 0855, de 2010) perto da trajetória de
  // um alvo: abre o alvo pré-processado, onde o objeto está hoje, em vez de um campo vazio.
  if (state.ra !== undefined && state.dec !== undefined && !state.target && manifest) {
    const near = nearbyTarget({ ra: state.ra, dec: state.dec }, await movingTargets());
    if (signal.aborted) return;
    const hit = near && manifest.targets.find((x) => x.id === near.id);
    const published = !!hit && staticFovs(hit).includes(state.fov);
    if (hit && published && near.distanceDeg * 3600 > 1) {
      notice = t("status.near", { dist: fmtNum(near.distanceDeg * 60, 1), name: hit.name });
    }
    // Só troca pelo pré-processado num tamanho publicado; outro tamanho em volta do alvo vem da API.
    if (hit && published) state = { ...state, target: hit.id, ra: undefined, dec: undefined };
    updateUrl();
  }

  const source = chooseSource(state, manifest, API_BASE);
  currentTarget = source.kind === "static" ? manifest!.targets.find((t) => t.id === source.targetId) ?? null : null;
  renderTargets();
  try {
    if (source.kind === "unavailable") {
      setStatus(t("status.unavailable", { reason: t(`reason.${source.reason}`) }), "error");
      return;
    }
    if (source.kind === "resolve") {
      setStatus(t("status.resolving", { name: state.name ?? "" }));
      const body = await fetchJson(source.resolveUrl, signal);
      // O SIMBAD devolve a posição J2000; objetos próximos andam vários ″/ano (WISE 0855: ~3,5′
      // até a época dos dados). Propagar para o centro do campo cair onde o objeto está agora.
      const pos = Number.isFinite(body.pm_ra_masyr) && Number.isFinite(body.pm_dec_masyr)
        ? propagate(body.ra, body.dec, body.pm_ra_masyr, body.pm_dec_masyr)
        : { ra: body.ra, dec: body.dec };
      state = { ...state, name: undefined, target: undefined, ra: Number(pos.ra.toFixed(6)), dec: Number(pos.dec.toFixed(6)) };
      updateUrl();
      return openFromState();
    }
    setStatus(t("status.loading"));
    field = source.kind === "static"
      ? await loadStaticField(source.fieldUrl)
      : await loadApiField(source.fieldUrl, (p) => {
          setStatus(p.stage === "busy"
            ? t("status.busy")
            : p.total
              ? t("status.downloading", { done: p.done ?? 0, total: p.total })
              : t("status.querying"));
        }, signal);
    if (signal.aborted) return;
    setupField();
    if (notice) showNotice(notice);
  } catch (err) {
    if ((err as Error).name === "AbortError") return;
    setStatus(t("status.loadError", { msg: (err as Error).message }), "error");
  }
}

function openTarget(id: string) {
  const t = manifest?.targets.find((x) => x.id === id);
  if (!t) return;
  state = { ...state, target: t.id, ra: undefined, dec: undefined, name: undefined, det: undefined, a: undefined, b: undefined, fov: t.fov_arcmin };
  view.zoom = 1;
  renderZoom();
  updateUrl();
  openFromState();
  $("plate").scrollIntoView({ behavior: "smooth", block: "start" });
}

function openPoint(ra: number, dec: number) {
  state = { ...state, target: undefined, name: undefined, ra: Number(ra.toFixed(5)), dec: Number(dec.toFixed(5)), det: undefined, a: undefined, b: undefined };
  view.zoom = 1;
  renderZoom();
  updateUrl();
  openFromState();
  $("plate").scrollIntoView({ behavior: "smooth", block: "start" });
}

const spectrumView = new SpectrumView($("spectrum"));

/** Espectro do alvo, quando o campo tem (alvos pré-processados). */
async function showSpectrum() {
  const handle = field;
  spectrumView.show(null, "");
  if (!handle?.doc.spectrum || state.embed) return;
  try {
    const doc = (await fetch(handle.base + handle.doc.spectrum).then((r) => r.ok ? r.json() : null)) as SpectrumDoc | null;
    if (field !== handle || !doc) return;
    spectrumView.show(doc, currentTarget?.name ?? handle.doc.target?.name ?? t("target.fallback"));
    spectrumView.highlight(state.mode === "play" || state.mode === "blink" ? currentEpochIndex() : undefined);
  } catch {
    // sem espectro: a seção fica escondida
  }
}

const skyMap = new SkyMap($("skymap"), $("skymap-status"), { onTarget: openTarget, onPoint: openPoint });

function setupField() {
  const doc = field!.doc;
  state.fov = doc.fov_arcmin; // a URL diz o tamanho do campo que está na tela
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
  renderFovs();
  updateUrl();
  restartTimer();
  draw();
  applyTargetContrast();
  showSpectrum();
  skyMap.showField(doc.center.ra, doc.center.dec, doc.fov_arcmin);
}

/**
 * Contraste inicial no alvo: com os limites até a estrela mais brilhante do campo, um alvo fraco
 * (WISE 0855 em D6) saía cinza-claro. Usa o céu como piso e o pico do alvo como topo; o controle
 * Contraste continua agindo por cima. Sem alvo detectado, ficam os limites do campo.
 */
async function applyTargetContrast() {
  const handle = field, det = state.det;
  if (!handle || !det) return;
  const display = handle.doc.display[det];
  view.limits = null;
  view.gain = 0;
  $<HTMLInputElement>("gain").value = "0";
  if (!display || !handle.doc.target) return;
  const peaks = await Promise.all(epochsWithDet().map(async (e) => {
    const here = targetPixel(e.index);
    const frame = here ? await loadFrame(handle, e.index, det)?.catch(() => null) : null;
    return frame && here ? peakNear(frame.data, frame.variance, here.row, here.col) : { peak: NaN, snr: 0 };
  }));
  if (field !== handle || state.det !== det) return; // trocou de campo ou detector enquanto baixava
  const limits = targetLimits(peaks, display);
  if (!limits) return;
  view.limits = { det, ...limits };
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
  if (state.mode === "sum") return undefined;
  return epochs[view.cursor % epochs.length].index;
}

/** Desenha a placa. Chamado sem await de vários lugares: um quadro que não baixa vira aviso, não erro solto. */
function draw(): void {
  const token = drawToken + 1;
  drawPlate().catch((err: Error) => {
    if (token === drawToken && field) setStatus(t("status.frameError", { msg: err.message }), "error");
  });
}

async function drawPlate() {
  if (!field || !state.det) return;
  const token = ++drawToken;
  const doc = field.doc;
  const n = doc.grid.n;
  const det = state.det;
  const display = doc.display[det]!;
  const base = view.limits?.det === det ? view.limits : display;
  const vmin = base.vmin;
  const vmax = base.vmin + (base.vmax - base.vmin) * Math.pow(10, -view.gain);
  let rgba: Uint8ClampedArray;
  let shownEpoch: number | undefined;

  let flagMask: MaskGrid | null = null;
  if (state.mode === "diff") {
    if (state.a === undefined || state.b === undefined) return;
    const [fa, fb] = await Promise.all([loadFrame(field, state.a, det), loadFrame(field, state.b, det)]);
    if (token !== drawToken || !fa || !fb) return;
    // Em unidades de ruído: abaixo de 2σ o céu parado some; a partir de 5σ, cor cheia.
    rgba = renderDiff(significance(fa.data, fb.data, fa.variance, fb.variance), 2, 5);
    shownEpoch = state.b;
  } else {
    shownEpoch = currentEpochIndex();
    if (state.mode !== "sum" && shownEpoch === undefined) return;
    // Uma época, ou todas somadas (modo Somar).
    const epochsFor = (d: Detector) => state.mode === "sum"
      ? doc.epochs.filter((e) => d in e.frames).map((e) => e.index)
      : (shownEpoch !== undefined && doc.epochs.find((e) => e.index === shownEpoch)?.frames[d] ? [shownEpoch] : []);
    const plate = async (d: Detector) => {
      const frames = (await Promise.all(epochsFor(d).map((i) => loadFrame(field!, i, d)))).filter((f) => f !== null);
      return frames.length ? sumFrames(frames) : null;
    };
    if (state.color) {
      const planes = await Promise.all(COLOR_DETS.map(plate));
      if (token !== drawToken) return;
      rgba = renderRgb(COLOR_DETS.map((d, k) => {
        const lim = doc.display[d];
        const top = lim ? lim.vmin + (lim.vmax - lim.vmin) * Math.pow(10, -view.gain) : 1;
        return { grid: planes[k]?.data ?? null, mask: planes[k]?.mask ?? null, vmin: lim?.vmin ?? 0, vmax: top };
      }) as [ColorChannel, ColorChannel, ColorChannel], display.stretch, n);
      flagMask = planes[COLOR_DETS.indexOf(det)]?.mask ?? null;
    } else {
      const frame = await plate(det);
      if (token !== drawToken || !frame) return;
      rgba = renderGray(frame.data, frame.mask, vmin, vmax, display.stretch, view.negative);
      flagMask = frame.mask;
    }
  }
  view.flagged = view.flags && flagMask ? overlayFlags(rgba, flagMask) : 0;

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
  renderInscription(shownEpoch);
  renderLabel(shownEpoch);
  highlightRuler(shownEpoch);
  spectrumView.highlight(state.mode === "play" || state.mode === "blink" ? shownEpoch : undefined);
}

/** Recorte da placa conforme o zoom: fixo no céu (meio da trajetória prevista), igual em todas as épocas. */
function cropRect(n: number) {
  const doc = field!.doc;
  const positions = (doc.target?.predicted_positions ?? []).map((p) => worldToPixel(doc.grid.wcs, n, p.ra, p.dec));
  return zoomCrop(n, view.zoom, cropAnchor(n, positions));
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
      const strokes = [pencilCircle(x, y, r, 1), arrow.shaft, arrow.head];
      // Halo de vidro por baixo: o lápis não se confunde com os pixels vermelhos da diferença.
      parts.push(...strokes.map((d) => `<path class="pencil-halo" d="${d}"/>`));
      parts.push(...strokes.map((d) => `<path class="pencil" d="${d}"/>`));
    }
  }
  marks.innerHTML = parts.join("");
}

/** Inscrição no canto da placa, como as anotações das placas de vidro; no Piscar, diz qual placa (A ou B) está no ocular. */
function renderInscription(epochIndex: number | undefined) {
  const doc = field!.doc;
  const epoch = doc.epochs.find((e) => e.index === epochIndex) ?? (state.mode === "sum" ? doc.epochs[0] : undefined);
  const el = $("plate-inscription");
  if (!epoch) { el.textContent = ""; return; }
  const plate = state.mode === "blink" ? (epochIndex === state.a ? "A · " : "B · ") : "";
  const fov = `${doc.fov_arcmin}′ × ${doc.fov_arcmin}′`;
  const dets = state.color && state.mode !== "diff" ? "D1·D3·D6" : state.det;
  el.textContent = state.mode === "diff"
    ? t("inscr.diff", { det: state.det ?? "", fov })
    : state.mode === "sum"
      ? t("inscr.sum", { dets: dets ?? "", n: epochsWithDet().length, fov })
      : `${plate}${dets} · ${formatDate(epoch.date_start)} · ${fov}`;
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
    if (a && b) facts.push([t("fact.interval"), t("fact.days", { n: Math.round(b.mjd_mid - a.mjd_mid) })]);
  } else if (state.mode === "sum") {
    const all = epochsWithDet();
    $("label-epoch").textContent = all.length ? `${formatDate(all[0].date_start)} – ${formatDate(all[all.length - 1].date_end)}` : "";
    facts.push([t("fact.epochs"), String(all.length)]);
    facts.push([t("fact.exposures"), String(all.reduce((s, e) => s + e.frames[det]!.n_exposures, 0))]);
  } else {
    $("label-epoch").textContent = epoch ? epochSpan(epoch) : "";
    if (epoch) facts.push([t("fact.plate"), t("fact.plateOf", { i: epochsWithDet().findIndex((e) => e.index === epoch.index) + 1, n: epochsWithDet().length })]);
    if (epoch?.frames[det]) facts.push([t("fact.exposures"), String(epoch.frames[det]!.n_exposures)]);
  }
  facts.push(state.color && state.mode !== "diff"
    ? [t("fact.color"), t("fact.colorValue")]
    : [t("fact.detector"), `${det} · ${um(DET_RANGE[det][0])}–${um(DET_RANGE[det][1])} µm`]);
  if (view.flags) facts.push([t("fact.flagged"), String(view.flagged)]);
  $("label-facts").innerHTML = facts.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join("");
}

// ---------------------------------------------------------------------------- controles

function renderTargets() {
  const list = $("targets");
  list.innerHTML = "";
  for (const target of manifest?.targets ?? []) {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "target";
    button.setAttribute("aria-pressed", String(currentTarget?.id === target.id));
    button.innerHTML = `<canvas class="thumb" width="64" height="64" aria-hidden="true"></canvas>
      <span class="target-text"><span class="target-name">${target.name}</span><span class="target-desc">${targetText(target, "description")}</span>${target.look_for ? `<span class="target-look"><strong>${t("target.lookFor")}</strong> ${targetText(target, "look_for")}</span>` : ""}</span>`;
    button.addEventListener("click", () => openTarget(target.id));
    li.append(button);
    list.append(li);
    drawThumbnail(target, button.querySelector("canvas")!);
  }
}

const fieldDocCache = new Map<string, Promise<FieldHandle>>();

/** field.json de um alvo, carregado uma vez (miniaturas e busca por coordenada usam o mesmo). */
function targetField(t: ManifestTarget): Promise<FieldHandle> {
  let pending = fieldDocCache.get(t.id);
  if (!pending) {
    pending = loadStaticField("data/" + t.field);
    pending.catch(() => fieldDocCache.delete(t.id));
    fieldDocCache.set(t.id, pending);
  }
  return pending;
}

/** Alvos com o movimento próprio do field.json (o manifesto só tem o centro do campo). */
async function movingTargets(): Promise<MovingTarget[]> {
  const docs = await Promise.all((manifest?.targets ?? []).map((t) => targetField(t).catch(() => null)));
  return (manifest?.targets ?? []).flatMap((t, i) => {
    const target = docs[i]?.doc.target;
    return [{
      id: t.id, ra: t.ra, dec: t.dec, field_mjd: FIELD_REFERENCE_MJD,
      pm_ra_masyr: target?.pm_ra_masyr ?? 0, pm_dec_masyr: target?.pm_dec_masyr ?? 0,
      ref_mjd: target?.ref_mjd ?? FIELD_REFERENCE_MJD,
    }];
  });
}

let noticeTimer: number | undefined;
function showNotice(message: string) {
  setStatus(message);
  clearTimeout(noticeTimer);
  noticeTimer = window.setTimeout(() => { if ($("plate-status").textContent === message) setStatus(null); }, 7000);
}

const thumbCache = new Map<string, Promise<ImageData | null>>();

/** Miniatura do alvo com o céu escuro (como a placa abre), contraste realçado para caber em 64 px. */
function drawThumbnail(t: ManifestTarget, el: HTMLCanvasElement) {
  let pending = thumbCache.get(t.id);
  if (!pending) {
    pending = (async () => {
      const match = t.thumbnail.match(/frames\/(\d+)\/(D\d)\.png$/);
      if (!match) return null;
      const handle = await targetField(t);
      const frame = await loadFrame(handle, Number(match[1]), match[2] as Detector);
      const display = handle.doc.display[match[2] as Detector];
      if (!frame || !display) return null;
      // Contraste pelos percentis do próprio quadro: cada miniatura lê como um campo de estrelas,
      // inclusive em D6 (WISE 0855), onde uma fração fixa do intervalo estourava o fundo.
      const finite = Array.from(frame.data.values).filter(Number.isFinite).sort((x, y) => x - y);
      const at = (q: number) => finite[Math.min(finite.length - 1, Math.floor(q * finite.length))];
      const n = handle.doc.grid.n;
      return new ImageData(new Uint8ClampedArray(renderGray(frame.data, frame.mask, at(0.5), at(0.995), "linear", false)), n, n);
    })().catch(() => null);
    thumbCache.set(t.id, pending);
  }
  pending.then((image) => {
    if (!image) return;
    const tmp = document.createElement("canvas");
    tmp.width = image.width;
    tmp.height = image.height;
    tmp.getContext("2d")!.putImageData(image, 0, 0);
    const ctx = el.getContext("2d")!;
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(tmp, 0, 0, el.width, el.height);
  });
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
    button.title = has ? detHelp(d) : t("det.none");
    button.addEventListener("click", () => {
      state = { ...state, det: d, a: undefined, b: undefined };
      ensurePair();
      view.cursor = 0;
      renderDetectors();
      renderPairSelects();
      renderRuler();
      updateUrl();
      draw();
      applyTargetContrast();
    });
    box.append(button);
  }
  $("det-help").textContent = state.det ? detHelp(state.det) : "";
}

function renderModes() {
  for (const b of document.querySelectorAll<HTMLButtonElement>("#modes [data-mode]")) {
    b.setAttribute("aria-checked", String(b.dataset.mode === state.mode));
  }
  $("mode-help").textContent = modeHelp(state.mode);
  $("pair").hidden = state.mode === "play" || state.mode === "sum";
  $("diff-legend").hidden = state.mode !== "diff";
  const still = state.mode === "diff" || state.mode === "sum";
  for (const id of ["play", "prev", "next", "speed"]) $(id).hidden = still;
  // a diferença é em σ de um detector só; a falsa cor vale nos outros modos
  $<HTMLInputElement>("color").disabled = state.mode === "diff";
}

function renderPairSelects() {
  const options = epochsWithDet().map((e) => `<option value="${e.index}">${t("pair.option", { date: formatDate(e.date_start), n: e.frames[state.det!]!.n_exposures })}</option>`).join("");
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
  const pos = (mjd: number) => 5 + ((mjd - t0) / span) * 90; // folga nas pontas para os rótulos

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
    if (d.getUTCMonth() === 0 || d.getUTCMonth() === 6) tick.dataset.label = d.getUTCMonth() === 0 ? String(d.getUTCFullYear()) : t("ruler.jul");
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
    const count = has ? t("ruler.count", { n }) : t("ruler.without", { det: state.det ?? "" });
    button.innerHTML = `<span class="tick" style="height:${Math.min(60, 12 + n * 2)}%"></span><span class="ruler-date">${monthName(Number(e.date_start.slice(5, 7)) - 1)} ${e.date_start.slice(2, 4)}<span class="ruler-count">${count}</span></span>`;
    button.setAttribute("aria-label", has ? t("ruler.aria", { span: epochSpan(e), n }) : t("ruler.ariaWithout", { span: epochSpan(e) }));
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
  declutterRuler();
  const missing = all.filter((e) => !(state.det! in e.frames)).length;
  $("ruler-note").textContent = missing
    ? t(missing === 1 ? "ruler.missing1" : "ruler.missingN", { n: missing, det: state.det ?? "" })
    : "";
}

/** Esconde rótulos de épocas próximas demais, priorizando as que têm o detector atual. */
function declutterRuler() {
  const ruler = $("ruler");
  const width = ruler.clientWidth || 1;
  const buttons = [...ruler.querySelectorAll<HTMLButtonElement>(".ruler-epoch")];
  const order = [...buttons].sort((a, b) => Number(a.disabled) - Number(b.disabled));
  const placed: number[] = [];
  const minGap = 64; // px entre rótulos
  for (const b of order) {
    const x = (parseFloat(b.style.left) / 100) * width;
    const free = placed.every((p) => Math.abs(p - x) >= minGap);
    b.classList.toggle("unlabeled", !free);
    if (free) placed.push(x);
  }
}

function highlightRuler(epochIndex: number | undefined) {
  for (const b of document.querySelectorAll<HTMLButtonElement>(".ruler-epoch")) {
    const i = Number(b.dataset.epoch);
    b.classList.toggle("current", i === epochIndex);
    b.classList.toggle("pair", (state.mode === "blink" || state.mode === "diff") && (i === state.a || i === state.b));
  }
}

function renderFovs() {
  const shown = field?.doc.fov_arcmin;
  for (const b of document.querySelectorAll<HTMLButtonElement>("[data-fov]")) {
    const fov = Number(b.dataset.fov);
    b.setAttribute("aria-checked", String(fov === shown));
    // Sem API, só existem os tamanhos pré-processados do alvo.
    b.disabled = fov !== shown && !API_BASE && !(currentTarget && staticFovs(currentTarget).includes(fov));
  }
  const instant = currentTarget ? staticFovs(currentTarget) : [];
  $("fov-help").textContent = instant.length > 1 ? t("fov.instant") : API_BASE ? t("fov.api") : t("fov.noApi");
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

// ---------------------------------------------------------------------------- idioma

/** Textos fixos da página e do botão de idioma, no idioma atual. */
function renderStatic() {
  const lang = getLang();
  document.documentElement.lang = lang === "en" ? "en" : "pt-BR";
  applyStatic();
  const button = $("lang-switch");
  button.querySelector(".label")!.textContent = t("lang.button");
  button.setAttribute("aria-label", t("lang.aria"));
  button.setAttribute("lang", lang === "en" ? "pt-BR" : "en");
  for (const b of document.querySelectorAll<HTMLButtonElement>("[data-sky-det]")) {
    const [lo, hi] = DET_RANGE[`D${b.dataset.skyDet}` as Detector];
    b.title = `${um(lo)}–${um(hi)} µm`;
  }
  if (!API_BASE) $("skymap-here").title = t("skymap.noApi");
}

/** Troca o idioma sem recarregar: textos fixos, controles, placa, espectro e mapa. */
function switchLang(lang: Lang) {
  setLang(lang);
  state = { ...state, lang };
  try { localStorage.setItem(LANG_KEY, lang); } catch { /* sem armazenamento: vale a URL */ }
  updateUrl();
  renderStatic();
  setPlaying(view.playing);
  renderModes();
  renderTargets();
  skyMap.relabel();
  if (!field) return;
  setStatus(null);
  renderDetectors();
  renderPairSelects();
  renderRuler();
  renderFovs();
  $("fps-value").textContent = `${fmtNum(state.fps, state.fps % 1 ? 1 : 0)}/s`;
  draw();
  showSpectrum();
}

// ---------------------------------------------------------------------------- animação

function stopTimer() {
  if (timer !== undefined) clearInterval(timer);
  timer = undefined;
}

function restartTimer() {
  stopTimer();
  if (!view.playing || state.mode === "diff" || state.mode === "sum" || !field) return;
  timer = window.setInterval(() => {
    view.cursor++;
    draw();
  }, 1000 / state.fps);
}

function setPlaying(playing: boolean) {
  view.playing = playing;
  const button = $("play");
  icon(button.querySelector("[data-icon]") ?? button.firstElementChild!, playing ? "Pause" : "Play");
  button.querySelector(".label")!.textContent = playing ? t("play.pause") : t("play.play");
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
  $("fps-value").textContent = `${fmtNum(state.fps, state.fps % 1 ? 1 : 0)}/s`;
  fps.addEventListener("input", () => {
    state.fps = Number(fps.value);
    $("fps-value").textContent = `${fmtNum(state.fps, state.fps % 1 ? 1 : 0)}/s`;
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
  const color = $<HTMLInputElement>("color");
  color.checked = state.color;
  color.addEventListener("change", () => {
    state.color = color.checked;
    updateUrl();
    draw();
  });
  $<HTMLInputElement>("flags").addEventListener("change", (ev) => {
    view.flags = (ev.target as HTMLInputElement).checked;
    $("flags-help").hidden = !view.flags;
    draw();
  });
  for (const b of document.querySelectorAll<HTMLButtonElement>("[data-fov]")) {
    b.addEventListener("click", () => {
      const fov = Number(b.dataset.fov);
      if (!field || fov === field.doc.fov_arcmin || b.disabled) return;
      // Tamanho publicado do alvo abre na hora; outro tamanho vem da API, centrado onde o campo está.
      const t = currentTarget && staticFovs(currentTarget).includes(fov) ? currentTarget : null;
      const { ra, dec } = field.doc.center;
      state = t
        ? { ...state, target: t.id, ra: undefined, dec: undefined, fov, a: undefined, b: undefined }
        : { ...state, target: undefined, name: undefined, ra, dec, fov, a: undefined, b: undefined };
      updateUrl();
      openFromState();
    });
  }
  $<HTMLInputElement>("marks").addEventListener("change", (ev) => {
    view.marks = (ev.target as HTMLInputElement).checked;
    draw();
  });

  $("lang-switch").addEventListener("click", () => switchLang(getLang() === "en" ? "pt" : "en"));

  $("copy-link").addEventListener("click", async () => {
    const label = $("copy-link").querySelector(".label")!;
    try {
      await navigator.clipboard.writeText(location.href);
      label.textContent = t("copy.done");
    } catch {
      label.textContent = t("copy.fail");
    }
    setTimeout(() => (label.textContent = t("copy.label")), 2200);
  });

  $<HTMLFormElement>("search").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const q = $<HTMLInputElement>("search-input").value.trim();
    if (!q) return;
    const known = manifest?.targets.find((t) => t.id === q.toLowerCase() || t.name.toLowerCase() === q.toLowerCase());
    const coords = parseCoordinates(q); // graus ou sexagesimal, sem precisar da API
    // Busca nova começa no campo padrão: herdar um 10′ escolhido antes impedia de reconhecer o alvo (6′).
    const base = { ...state, target: undefined, ra: undefined, dec: undefined, name: undefined, det: undefined, a: undefined, b: undefined, fov: DEFAULT_STATE.fov };
    if (known) state = { ...base, target: known.id, fov: known.fov_arcmin };
    else if (coords) state = { ...base, ...coords };
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
  new ResizeObserver(() => declutterRuler()).observe($("ruler"));
}

// ---------------------------------------------------------------------------- início

async function main() {
  document.body.classList.toggle("embed", state.embed);
  renderStatic();
  wire();
  renderZoom();
  renderNegative();
  renderModes();
  if (parsed.warnings.length) console.warn(parsed.warnings.join("\n"));
  manifest = await loadManifest();
  renderTargets();
  if (!state.embed) {
    skyMap.setTargets(manifest?.targets ?? []);
    skyMap.loadWhenVisible();
    $("skymap-here").addEventListener("click", () => skyMap.pick());
    $("skymap-field").addEventListener("click", () => skyMap.goToField());
    const skyDets = document.querySelectorAll<HTMLButtonElement>("[data-sky-det]");
    const markSkyDet = (d: number) => skyDets.forEach((b) => b.setAttribute("aria-checked", String(Number(b.dataset.skyDet) === d)));
    skyDets.forEach((b) => b.addEventListener("click", () => {
      const d = Number(b.dataset.skyDet);
      markSkyDet(d);
      skyMap.setDetector(d);
    }));
    markSkyDet(1);
    for (const box of document.querySelectorAll<HTMLInputElement>("[data-catalog]")) {
      box.addEventListener("change", () => skyMap.setCatalog(box.dataset.catalog as CatalogKey, box.checked));
    }
  }
  await openFromState();
}

main();
