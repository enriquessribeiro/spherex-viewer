// Coordenada de catálogo → alvo pré-processado. Objetos próximos andam vários ″/ano: a posição
// que o desafio dá para o WISE 0855 (designação de 2010) está ~2′ de onde ele está hoje, e a J2000
// ~3,5′. Sem isso o campo abriria no lugar antigo, com o objeto fora da imagem.
import { separationDeg } from "./sky";
import type { RaDec } from "./coords";

export interface MovingTarget {
  id: string;
  /** Posição na época dos campos (centro do campo publicado). */
  ra: number;
  dec: number;
  pm_ra_masyr: number;
  pm_dec_masyr: number;
  /** Época do catálogo de onde o movimento é contado (J2000 = 51544.5). */
  ref_mjd: number;
  /** Época do centro do campo. */
  field_mjd: number;
}

/** Folga além do caminho percorrido: erros de catálogo e coordenadas digitadas com poucas casas. */
export const MATCH_SLACK_DEG = 1 / 60;

/** Quanto o alvo andou entre a época do catálogo e a do campo, em graus. */
export function travelDeg(t: MovingTarget): number {
  const years = Math.abs(t.field_mjd - t.ref_mjd) / 365.25;
  return (Math.hypot(t.pm_ra_masyr, t.pm_dec_masyr) * years) / 3.6e6;
}

/**
 * Alvo cuja trajetória passa perto do ponto: distância ao centro do campo menor que o caminho
 * percorrido desde o catálogo + 1′. Para estrelas quase paradas (RW Aur, R Dra) isso é ~1′,
 * então um ponto vizinho de propósito continua sendo um campo próprio.
 */
export function nearbyTarget(p: RaDec, targets: MovingTarget[]): { id: string; distanceDeg: number } | null {
  let best: { id: string; distanceDeg: number } | null = null;
  for (const t of targets) {
    const distanceDeg = separationDeg(p.ra, p.dec, t.ra, t.dec);
    if (distanceDeg <= travelDeg(t) + MATCH_SLACK_DEG && (!best || distanceDeg < best.distanceDeg)) {
      best = { id: t.id, distanceDeg };
    }
  }
  return best;
}
