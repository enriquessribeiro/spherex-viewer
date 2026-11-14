// Quadros → pixels RGBA para o <canvas>.
import { Grid, MaskGrid, MASK_SATURATED } from "./frames";
import { normalize, type Stretch } from "./stretch";

/** Escala de cinza; sem dado = preto; núcleo saturado = branco (brilho máximo, não buraco). */
export function renderGray(
  grid: Grid, mask: MaskGrid | null, vmin: number, vmax: number, stretch: Stretch,
): Uint8ClampedArray {
  const out = new Uint8ClampedArray(grid.values.length * 4);
  for (let i = 0; i < grid.values.length; i++) {
    const saturated = mask !== null && (mask.values[i] & MASK_SATURATED) !== 0;
    const t = saturated ? 1 : normalize(grid.values[i], vmin, vmax, stretch);
    const g = Number.isNaN(t) ? 0 : Math.round(t * 255);
    out.set([g, g, g, 255], i * 4);
  }
  return out;
}

/** Diferença em cores divergentes: vermelho = ficou mais brilhante (apareceu), azul = sumiu. */
export function renderDiff(diff: Grid, scale: number): Uint8ClampedArray {
  const out = new Uint8ClampedArray(diff.values.length * 4);
  for (let i = 0; i < diff.values.length; i++) {
    const d = diff.values[i];
    const t = Number.isFinite(d) ? Math.min(1, Math.abs(d) / Math.max(scale, 1e-12)) : 0;
    const v = Math.round(t * 255);
    out.set(d > 0 ? [v, 0, 0, 255] : [0, 0, v, 255], i * 4);
  }
  return out;
}
