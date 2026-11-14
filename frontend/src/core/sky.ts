// Geometria no céu para o mapa: contorno do campo e distâncias angulares.

const RAD = Math.PI / 180;

/** Distância angular (graus) entre dois pontos, fórmula de haversine. */
export function separationDeg(ra1: number, dec1: number, ra2: number, dec2: number): number {
  const s = Math.sin(((dec2 - dec1) * RAD) / 2) ** 2 +
    Math.cos(dec1 * RAD) * Math.cos(dec2 * RAD) * Math.sin(((ra2 - ra1) * RAD) / 2) ** 2;
  return (2 * Math.asin(Math.min(1, Math.sqrt(s)))) / RAD;
}

/** Cantos do campo quadrado (TAN, norte para cima) em [ra, dec], na ordem NE, NW, SW, SE. */
export function fieldCorners(ra: number, dec: number, fovArcmin: number): [number, number][] {
  const h = ((fovArcmin / 60) * RAD) / 2;
  const a0 = ra * RAD, d0 = dec * RAD;
  return ([[h, h], [-h, h], [-h, -h], [h, -h]] as const).map(([xi, eta]) => {
    // projeção gnomônica inversa; xi positivo = leste
    const rho = Math.hypot(xi, eta);
    const c = Math.atan(rho);
    const d = Math.asin(Math.cos(c) * Math.sin(d0) + (eta * Math.sin(c) * Math.cos(d0)) / rho);
    const a = a0 + Math.atan2(xi * Math.sin(c), rho * Math.cos(d0) * Math.cos(c) - eta * Math.sin(d0) * Math.sin(c));
    return [((a / RAD) % 360 + 360) % 360, d / RAD];
  });
}
