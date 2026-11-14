// Contraste inicial pensado no alvo. Os limites do campo vão até a estrela mais brilhante (para
// variáveis como R Dra não estourarem); um alvo fraco como o WISE 0855, 10× mais fraco que a estrela
// mais brilhante do campo, ficava cinza-claro. Aqui os limites iniciais são escolhidos para o alvo sair escuro sobre o céu claro.
import type { Grid } from "./frames";

/** Fração do intervalo de contraste em que o pico do alvo deve cair (asinh de 0,8 ≈ 93% de tinta). */
export const TARGET_LEVEL = 0.8;
/** Só conta o pico de épocas em que o alvo foi detectado de verdade. */
export const MIN_SNR = 5;

/** Pico (e S/R do pico) numa caixa 3×3 em volta da posição prevista. */
export function peakNear(data: Grid, variance: Grid, row: number, col: number): { peak: number; snr: number } {
  let peak = -Infinity, snr = 0;
  for (let r = Math.round(row) - 1; r <= Math.round(row) + 1; r++) {
    for (let c = Math.round(col) - 1; c <= Math.round(col) + 1; c++) {
      if (r < 0 || c < 0 || r >= data.n || c >= data.n) continue;
      const v = data.at(r, c), s2 = variance.at(r, c);
      if (Number.isFinite(v) && v > peak) {
        peak = v;
        snr = Number.isFinite(s2) && s2 > 0 ? v / Math.sqrt(s2) : 0;
      }
    }
  }
  return { peak, snr };
}

/**
 * Limites de contraste para o alvo: piso no céu (0, porque o fundo já foi subtraído no pipeline) e
 * topo com o pico mais brilhante do alvo em TARGET_LEVEL. Estrelas mais brilhantes saturam, o que
 * não atrapalha. null se o alvo não foi detectado ou já é o objeto mais brilhante (R Dra, Barnard):
 * aí ficam os limites do campo.
 */
export function targetLimits(
  peaks: { peak: number; snr: number }[], field: { vmin: number; vmax: number },
): { vmin: number; vmax: number } | null {
  const good = peaks.filter((p) => p.snr >= MIN_SNR && Number.isFinite(p.peak) && p.peak > 0);
  if (good.length === 0) return null;
  const vmax = Math.max(...good.map((p) => p.peak)) / TARGET_LEVEL;
  return vmax < field.vmax ? { vmin: 0, vmax } : null;
}
