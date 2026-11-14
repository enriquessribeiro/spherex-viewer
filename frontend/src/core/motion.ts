// Movimento próprio: leva uma posição de catálogo (J2000) até a época dos campos do site.
// Mesma conta de backend/pipeline/targets.py (Target.position_at), para os dois lados concordarem.

export const J2000_MJD = 51544.5;
/** Época de referência dos centros dos campos (backend/pipeline/targets.py, REFERENCE_MJD). */
export const FIELD_REFERENCE_MJD = 61000;
const DAYS_PER_YEAR = 365.25;

/** pmRa é mu_alpha* (já inclui cos δ), em mas/ano, como no SIMBAD e no Gaia. */
export function propagate(
  ra: number, dec: number, pmRaMasyr: number, pmDecMasyr: number,
  fromMjd = J2000_MJD, toMjd = FIELD_REFERENCE_MJD,
): { ra: number; dec: number } {
  const years = (toMjd - fromMjd) / DAYS_PER_YEAR;
  const newDec = dec + (pmDecMasyr * years) / 3.6e6;
  const newRa = ra + (pmRaMasyr * years) / 3.6e6 / Math.cos((dec * Math.PI) / 180);
  return { ra: ((newRa % 360) + 360) % 360, dec: newDec };
}
