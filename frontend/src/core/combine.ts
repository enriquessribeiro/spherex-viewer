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
