// Gráfico do espectro do alvo: fluxo × comprimento de onda, uma bolinha por exposição.
// A época que está na placa fica em lápis (maior); as outras em manila (menores), a mediana em tinta.
import { binnedMedian, contaminatedDetectors, medianSegments, fluxRange, niceTicks, type SpectrumDoc, type SpectrumPoint } from "../core/spectrum";
import type { Detector } from "../core/types";
import { fmtNum as fmt, monthName, t } from "../i18n";

const W = 760, H = 340;
const M = { top: 16, right: 16, bottom: 78, left: 64 };
const LAMBDA: [number, number] = [0.7, 5.05];
const DET_RANGE: Record<Detector, [number, number]> = {
  D1: [0.75, 1.09], D2: [1.1, 1.62], D3: [1.63, 2.41], D4: [2.42, 3.82], D5: [3.83, 4.41], D6: [4.42, 5.0],
};
/** Abaixo disso não há espectro que valha um gráfico: o alvo satura o detector (R Dra, Barnard). */
export const MIN_SPECTRUM_POINTS = 10;
const mjdDate = (mjd: number) => {
  const d = new Date(Date.UTC(1858, 10, 17) + mjd * 864e5);
  return `${d.getUTCDate()} ${monthName(d.getUTCMonth())} ${d.getUTCFullYear()}`;
};

export class SpectrumView {
  private doc: SpectrumDoc | null = null;
  private epoch: number | undefined;
  private readonly section: HTMLElement;
  private readonly svg: SVGSVGElement;
  private readonly tooltip: HTMLElement;

  constructor(section: HTMLElement) {
    this.section = section;
    this.svg = section.querySelector("svg")!;
    this.tooltip = section.querySelector(".spectrum-tooltip")!;
  }

  /** Mostra o espectro (ou esconde a seção, se o campo não tem). */
  show(doc: SpectrumDoc | null, targetName: string): void {
    this.doc = doc;
    this.section.hidden = doc === null;
    if (!doc) return;
    this.section.querySelector<HTMLElement>(".spectrum-title")!.textContent = t("sp.title", { name: targetName });
    const enough = doc.points.length >= MIN_SPECTRUM_POINTS;
    for (const sel of [".spectrum-chart", ".spectrum-table", ".spectrum-legend"]) {
      this.section.querySelector<HTMLElement>(sel)!.hidden = !enough;
    }
    this.renderNotes(targetName, enough);
    if (!enough) return;
    this.renderTable();
    this.render();
  }

  /** Destaca os pontos da época que está na placa (undefined = nenhuma, ex.: Somar e Diferença). */
  highlight(epoch: number | undefined): void {
    if (epoch === this.epoch) return;
    this.epoch = epoch;
    if (this.doc) this.render();
  }

  private renderNotes(targetName: string, enough: boolean): void {
    const doc = this.doc!;
    if (!enough) {
      // Estrela brilhante: o núcleo vem sem valor (saturado) e a abertura não pode ser medida.
      // As "vizinhas" achadas nesse caso são o halo da própria estrela, então não viram aviso.
      this.section.querySelector(".spectrum-notes")!.innerHTML =
        `<p>${t("sp.saturated", { name: targetName, bad: doc.exposures.total - doc.exposures.measured, total: doc.exposures.total })}</p>`;
      return;
    }
    const notes: string[] = [
      t("sp.intro", { measured: doc.exposures.measured, total: doc.exposures.total, aperture: fmt(doc.aperture_arcsec, 1) }),
    ];
    const dets = contaminatedDetectors(doc);
    if (dets.length) {
      const d = Math.min(...doc.neighbors.map((n) => n.distance_arcsec));
      notes.push(t("sp.warn", { dist: fmt(d, 1), dets: dets.join(", "), name: targetName }));
    }
    this.section.querySelector(".spectrum-notes")!.innerHTML = notes.map((n, i) =>
      `<p${i === 1 && dets.length ? ' class="spectrum-warning"' : ""}>${n}</p>`).join("");
  }

  private renderTable(): void {
    const rows = this.doc!.points.map((p) =>
      `<tr><td>${fmt(p.wavelength, 3)}</td><td>${fmt(p.flux, 1)}</td><td>${fmt(p.flux_err, 1)}</td>` +
      `<td>${p.det}</td><td>${mjdDate(p.mjd)}</td><td>${p.flagged ? t("sp.yes") : ""}</td></tr>`).join("");
    this.section.querySelector(".spectrum-table tbody")!.innerHTML = rows;
  }

  private render(): void {
    const doc = this.doc!;
    const pts = doc.points;
    const [f0, f1] = fluxRange(pts);
    const x = (lam: number) => M.left + ((lam - LAMBDA[0]) / (LAMBDA[1] - LAMBDA[0])) * (W - M.left - M.right);
    const y = (f: number) => M.top + (1 - (Math.min(Math.max(f, f0), f1) - f0) / (f1 - f0)) * (H - M.top - M.bottom);
    const plotBottom = H - M.bottom;
    const parts: string[] = [];

    // grade e eixo do fluxo
    for (const t of niceTicks(f0, f1, 5)) {
      parts.push(`<line class="sp-grid${t === 0 ? " sp-zero" : ""}" x1="${M.left}" x2="${W - M.right}" y1="${y(t)}" y2="${y(t)}"/>`);
      parts.push(`<text class="sp-tick" x="${M.left - 8}" y="${y(t)}" text-anchor="end" dominant-baseline="middle">${fmt(t)}</text>`);
    }
    parts.push(`<text class="sp-axis" transform="translate(16 ${(M.top + plotBottom) / 2}) rotate(-90)" text-anchor="middle">${t("sp.flux")}</text>`);

    // eixo do comprimento de onda, com a faixa de cada detector embaixo
    for (const t of [1, 2, 3, 4, 5]) {
      parts.push(`<line class="sp-axisline" x1="${x(t)}" x2="${x(t)}" y1="${plotBottom}" y2="${plotBottom + 5}"/>`);
      parts.push(`<text class="sp-tick" x="${x(t)}" y="${plotBottom + 18}" text-anchor="middle">${t}</text>`);
    }
    parts.push(`<line class="sp-axisline" x1="${M.left}" x2="${W - M.right}" y1="${plotBottom}" y2="${plotBottom}"/>`);
    const dirty = new Set(contaminatedDetectors(doc));
    for (const [det, [a, b]] of Object.entries(DET_RANGE) as [Detector, [number, number]][]) {
      parts.push(`<rect class="sp-band${dirty.has(det) ? " sp-band-dirty" : ""}" x="${x(a)}" y="${plotBottom + 26}" width="${x(b) - x(a)}" height="4" rx="2"/>`);
      parts.push(`<text class="sp-det" x="${(x(a) + x(b)) / 2}" y="${plotBottom + 44}" text-anchor="middle">${det}${dirty.has(det) ? "*" : ""}</text>`);
    }
    parts.push(`<text class="sp-axis" x="${(M.left + W - M.right) / 2}" y="${plotBottom + 66}" text-anchor="middle">${t("sp.wavelength")}</text>`);

    // barras de erro e pontos: contexto primeiro, a época da placa por cima
    const current = (p: SpectrumPoint) => this.epoch !== undefined && p.epoch === this.epoch;
    const ordered = [...pts.filter((p) => !current(p)), ...pts.filter(current)];
    for (const p of ordered) {
      const cls = current(p) ? "sp-now" : "sp-other";
      parts.push(`<line class="sp-err ${cls}" x1="${x(p.wavelength)}" x2="${x(p.wavelength)}" y1="${y(p.flux - p.flux_err)}" y2="${y(p.flux + p.flux_err)}"/>`);
    }
    for (const segment of medianSegments(binnedMedian(pts))) {
      if (segment.length > 1) {
        parts.push(`<polyline class="sp-median" points="${segment.map((m) => `${x(m.wavelength)},${y(m.flux)}`).join(" ")}"/>`);
      }
    }
    ordered.forEach((p) => {
      const now = current(p);
      parts.push(`<circle class="sp-dot ${now ? "sp-now" : "sp-other"}${p.flagged ? " sp-flagged" : ""}" ` +
        `cx="${x(p.wavelength)}" cy="${y(p.flux)}" r="${now ? 5 : 3.5}" data-i="${pts.indexOf(p)}"/>`);
    });
    this.svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    this.svg.innerHTML = parts.join("");
    this.wireHover();
  }

  private wireHover(): void {
    const pts = this.doc!.points;
    this.svg.onpointermove = (ev) => {
      const dot = (ev.target as Element).closest?.("circle[data-i]");
      if (!dot) { this.tooltip.hidden = true; return; }
      const p = pts[Number(dot.getAttribute("data-i"))];
      this.tooltip.innerHTML =
        `<strong>${fmt(p.wavelength, 3)} µm</strong> · ${p.det}<br>${fmt(p.flux, 1)} ± ${fmt(p.flux_err, 1)} µJy` +
        `<br>${mjdDate(p.mjd)}${p.flagged ? `<br>${t("sp.flagged")}` : ""}`;
      const box = this.section.querySelector(".spectrum-chart")!.getBoundingClientRect();
      this.tooltip.style.left = `${ev.clientX - box.left + 14}px`;
      this.tooltip.style.top = `${ev.clientY - box.top + 14}px`;
      this.tooltip.hidden = false;
    };
    this.svg.onpointerleave = () => { this.tooltip.hidden = true; };
  }
}
