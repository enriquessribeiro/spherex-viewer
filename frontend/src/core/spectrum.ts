// Espectro do alvo (schemas/spectrum.schema.json): tipos e contas do gráfico, sem DOM.
import type { Detector } from "./types";

export interface SpectrumPoint {
  wavelength: number;
  bandwidth: number;
  flux: number;
  flux_err: number;
  det: Detector;
  epoch: number;
  mjd: number;
  exposure_id: string;
  flagged: boolean;
}

export interface SpectrumDoc {
  aperture_arcsec: number;
  units: { wavelength: "um"; flux: "uJy" };
  exposures: { total: number; measured: number };
  points: SpectrumPoint[];
  neighbors: { detector: Detector; distance_arcsec: number; snr: number }[];
}

/** Resolução espectral típica do SPHEREx (R = λ/Δλ ≈ 40 em D1–D4): largura relativa de cada caixa. */
export const BIN_RESOLUTION = 40;

/**
 * Mediana em caixas de largura λ/R: a forma do espectro sem o ruído de cada exposição.
 * Caixas com menos de `minPoints` ficam de fora (uma exposição só é ruído, não espectro).
 */
export function binnedMedian(points: SpectrumPoint[], minPoints = 3): { wavelength: number; flux: number; n: number }[] {
  const sorted = [...points].sort((a, b) => a.wavelength - b.wavelength);
  const out: { wavelength: number; flux: number; n: number }[] = [];
  let i = 0;
  while (i < sorted.length) {
    const start = sorted[i].wavelength;
    const end = start * (1 + 1 / BIN_RESOLUTION);
    const bin: SpectrumPoint[] = [];
    while (i < sorted.length && sorted[i].wavelength < end) bin.push(sorted[i++]);
    if (bin.length >= minPoints) {
      out.push({ wavelength: median(bin.map((p) => p.wavelength)), flux: median(bin.map((p) => p.flux)), n: bin.length });
    }
  }
  return out;
}

/**
 * A mediana em trechos contínuos: onde faltam caixas (poucas exposições numa faixa), a linha para,
 * em vez de ligar os dois lados como se houvesse medida no meio.
 */
export function medianSegments<T extends { wavelength: number }>(bins: T[], maxGapBins = 3): T[][] {
  const segments: T[][] = [];
  for (const b of bins) {
    const last = segments.at(-1)?.at(-1);
    if (last && b.wavelength <= last.wavelength * (1 + maxGapBins / BIN_RESOLUTION)) segments.at(-1)!.push(b);
    else segments.push([b]);
  }
  return segments;
}

function median(v: number[]): number {
  const s = [...v].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/** Marcas "redondas" do eixo (1, 2, 2,5 ou 5 × 10^k) cobrindo [lo, hi], com ~`count` divisões. */
export function niceTicks(lo: number, hi: number, count = 5): number[] {
  if (!(hi > lo)) return [lo];
  const raw = (hi - lo) / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw)!;
  const ticks = [];
  for (let t = Math.ceil(lo / step) * step; t <= hi + step * 1e-9; t += step) ticks.push(Number(t.toPrecision(12)));
  return ticks;
}

/**
 * Faixa do eixo do fluxo: do menor ao maior valor que não seja ruído extremo (percentis 2 e 98 dos
 * pontos com a barra de erro), sempre incluindo o zero. Um ponto fora da faixa fica na borda.
 */
export function fluxRange(points: SpectrumPoint[]): [number, number] {
  if (points.length === 0) return [0, 1];
  const lows = points.map((p) => p.flux - p.flux_err).sort((a, b) => a - b);
  const highs = points.map((p) => p.flux + p.flux_err).sort((a, b) => a - b);
  const at = (v: number[], q: number) => v[Math.min(v.length - 1, Math.max(0, Math.round(q * (v.length - 1))))];
  const lo = Math.min(0, at(lows, 0.02)), hi = Math.max(0, at(highs, 0.98));
  return hi > lo ? [lo, hi] : [lo, lo + 1];
}

/** Detectores em que uma fonte vizinha cai na abertura (o fluxo ali pode ser dela). */
export function contaminatedDetectors(doc: SpectrumDoc): Detector[] {
  return [...new Set(doc.neighbors.map((n) => n.detector))].sort();
}
