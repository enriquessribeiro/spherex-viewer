// Projeção TAN (gnomônica) do campo: (RA, Dec) → pixel do quadro (norte na primeira linha).

export interface Wcs {
  CTYPE1: string; CTYPE2: string;
  CRVAL1: number; CRVAL2: number;
  CRPIX1: number; CRPIX2: number; // convenção FITS: base 1, linha 1 = sul
  CDELT1: number; CDELT2: number;
}

const RAD = Math.PI / 180;

/** Pixel (linha, coluna) base 0 nos arquivos do campo, com a linha 0 = norte. */
export function worldToPixel(wcs: Wcs, n: number, ra: number, dec: number): { row: number; col: number } {
  const a0 = wcs.CRVAL1 * RAD, d0 = wcs.CRVAL2 * RAD;
  const a = ra * RAD, d = dec * RAD;
  const cosc = Math.sin(d0) * Math.sin(d) + Math.cos(d0) * Math.cos(d) * Math.cos(a - a0);
  const xi = (Math.cos(d) * Math.sin(a - a0)) / cosc / RAD; // graus, leste positivo
  const eta = (Math.cos(d0) * Math.sin(d) - Math.sin(d0) * Math.cos(d) * Math.cos(a - a0)) / cosc / RAD;
  const colFits = wcs.CRPIX1 + xi / wcs.CDELT1; // base 1
  const rowFitsSouth = wcs.CRPIX2 + eta / wcs.CDELT2; // base 1, linha 1 = sul
  return { row: n - rowFitsSouth, col: colFits - 1 };
}
