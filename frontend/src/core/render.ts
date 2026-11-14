// Quadros → pixels RGBA para o <canvas>, nas cores das placas fotográficas.
import { Grid, MaskGrid, MASK_SATURATED } from "./frames";
import { normalize, type Stretch } from "./stretch";

type Rgb = readonly [number, number, number];

/** Paleta das placas (ver .impeccable/surfaces/frontend-index-html.md). */
export const PLATE = {
  glass: [242, 239, 231] as Rgb, // vidro da placa (céu vazio no negativo)
  ink: [20, 20, 20] as Rgb, // tinta do negativo (estrela)
  pencil: [196, 48, 43] as Rgb, // lápis vermelho: apareceu
  inkBlue: [43, 76, 156] as Rgb, // azul-tinta: sumiu
};

function mix(from: Rgb, to: Rgb, t: number): [number, number, number, number] {
  return [
    Math.round(from[0] + (to[0] - from[0]) * t),
    Math.round(from[1] + (to[1] - from[1]) * t),
    Math.round(from[2] + (to[2] - from[2]) * t),
    255,
  ];
}

/**
 * Quadro em tons de placa. Negativo (padrão): estrelas em tinta sobre vidro; positivo: o inverso.
 * Sem dado = céu vazio; núcleo saturado = brilho máximo (não um buraco).
 */
export function renderGray(
  grid: Grid, mask: MaskGrid | null, vmin: number, vmax: number, stretch: Stretch, negative = true,
): Uint8ClampedArray {
  const [sky, star] = negative ? [PLATE.glass, PLATE.ink] : [PLATE.ink, PLATE.glass];
  const out = new Uint8ClampedArray(grid.values.length * 4);
  for (let i = 0; i < grid.values.length; i++) {
    const saturated = mask !== null && (mask.values[i] & MASK_SATURATED) !== 0;
    const t = saturated ? 1 : normalize(grid.values[i], vmin, vmax, stretch);
    out.set(mix(sky, star, Number.isNaN(t) ? 0 : t), i * 4);
  }
  return out;
}

/** Diferença b − a sobre o vidro: lápis vermelho = apareceu/ficou mais brilhante, azul-tinta = sumiu. */
export function renderDiff(diff: Grid, scale: number): Uint8ClampedArray {
  const out = new Uint8ClampedArray(diff.values.length * 4);
  for (let i = 0; i < diff.values.length; i++) {
    const d = diff.values[i];
    const t = Number.isFinite(d) ? Math.min(1, Math.abs(d) / Math.max(scale, 1e-12)) : 0;
    out.set(mix(PLATE.glass, d > 0 ? PLATE.pencil : PLATE.inkBlue, t), i * 4);
  }
  return out;
}
