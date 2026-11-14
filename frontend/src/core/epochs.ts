// Escolhas padrão sobre as épocas de um campo.

export interface EpochLike {
  index: number;
  mjd_mid: number;
  frames: Record<string, { n_exposures: number }>;
}

/**
 * Par de épocas para a diferença padrão: maximiza o sinal da pior das duas
 * (mínimo de exposições); empate → o par mais afastado no tempo.
 * Lição do Marco 1: a época 1 do WISE 0855 em D6 tem só 3 exposições e vira ruído.
 */
export function defaultDiffPair(epochs: EpochLike[], det: string): [number, number] | null {
  const withDet = epochs.filter((e) => det in e.frames);
  let best: { score: number; span: number; pair: [number, number] } | null = null;
  for (let i = 0; i < withDet.length; i++) {
    for (let j = i + 1; j < withDet.length; j++) {
      const a = withDet[i], b = withDet[j];
      const score = Math.min(a.frames[det].n_exposures, b.frames[det].n_exposures);
      const span = Math.abs(b.mjd_mid - a.mjd_mid);
      if (!best || score > best.score || (score === best.score && span > best.span)) {
        best = { score, span, pair: [a.index, b.index] };
      }
    }
  }
  return best ? best.pair : null;
}
