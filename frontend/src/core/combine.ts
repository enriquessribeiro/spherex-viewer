// Operações entre quadros de épocas diferentes, feitas no navegador.
import { Grid } from "./frames";

/** b − a, pixel a pixel (NaN se faltar dado em qualquer um). */
export function difference(a: Grid, b: Grid): Grid {
  const out = new Float32Array(a.values.length);
  for (let i = 0; i < out.length; i++) out[i] = b.values[i] - a.values[i];
  return new Grid(a.n, out);
}

/** Média ponderada pelo inverso da variância, ignorando pixels sem dado. */
export function weightedMean(frames: Grid[], variances: Grid[]): Grid {
  const n = frames[0].n;
  const out = new Float32Array(n * n);
  for (let i = 0; i < out.length; i++) {
    let sum = 0;
    let weight = 0;
    for (let k = 0; k < frames.length; k++) {
      const v = frames[k].values[i];
      const s2 = variances[k].values[i];
      if (Number.isFinite(v) && Number.isFinite(s2) && s2 > 0) {
        sum += v / s2;
        weight += 1 / s2;
      }
    }
    out[i] = weight > 0 ? sum / weight : NaN;
  }
  return new Grid(n, out);
}

/**
 * Escala de cor da diferença: percentil 99,5 de |b − a|, ignorando NaN.
 * Vem da própria diferença, não do brilho máximo do campo: no WISE 0855 as mudanças
 * são pequenas perto da estrela mais brilhante e a diferença saía quase em branco.
 */
export function diffScale(diff: Grid, quantile = 0.995): number {
  const values: number[] = [];
  for (const v of diff.values) if (Number.isFinite(v)) values.push(Math.abs(v));
  if (values.length === 0) return 1;
  values.sort((x, y) => x - y);
  const scale = values[Math.max(0, Math.ceil(quantile * values.length) - 1)];
  return scale > 0 ? scale : 1;
}
