// Contorno do campo no mapa do céu.
import { describe, expect, it } from "vitest";
import { fieldCorners, separationDeg } from "../src/core/sky";

describe("cantos do campo no céu", () => {
  it("quatro cantos à distância de meia diagonal do centro", () => {
    const cantos = fieldCorners(133.76, -7.24, 6);
    expect(cantos).toHaveLength(4);
    // meia diagonal de um quadrado de 6′: 3′·√2 = 0,0707°
    for (const [ra, dec] of cantos) expect(separationDeg(133.76, -7.24, ra, dec)).toBeCloseTo((3 / 60) * Math.SQRT2, 4);
    const [ne, nw, sw] = cantos;
    expect(ne[0]).toBeGreaterThan(133.76); // leste = RA maior
    expect(ne[1]).toBeGreaterThan(-7.24); // norte = Dec maior
    expect(nw[0]).toBeLessThan(133.76);
    expect(sw[1]).toBeLessThan(-7.24);
  });

  it("perto do polo (R Dra, +66,8°) o campo continua quadrado no céu", () => {
    const [a, b, c] = fieldCorners(248.17, 66.75, 6);
    expect(separationDeg(...a, ...b)).toBeCloseTo(0.1, 4); // lado = 6′
    expect(separationDeg(...b, ...c)).toBeCloseTo(0.1, 4);
  });

  it("separação angular conhecida", () => {
    expect(separationDeg(0, 0, 90, 0)).toBeCloseTo(90, 9);
    expect(separationDeg(10, 89, 190, 89)).toBeCloseTo(2, 9);
  });
});

describe("canal do mapa por detector", () => {
  it("canal do meio de cada bloco de 17 (102 canais, 0–101)", async () => {
    const { detectorChannel } = await import("../src/ui/skymap");
    expect([1, 2, 3, 4, 5, 6].map(detectorChannel)).toEqual([8, 25, 42, 59, 76, 93]);
  });
});

describe("catálogos no mapa", () => {
  it("o raio cobre a vista (meia diagonal) e tem teto", async () => {
    const { catalogRadiusDeg, CATALOG_MAX_FOV_DEG } = await import("../src/ui/skymap");
    expect(catalogRadiusDeg(0.2)).toBeCloseTo(0.1 * Math.SQRT2, 9);
    expect(catalogRadiusDeg(CATALOG_MAX_FOV_DEG)).toBeLessThanOrEqual(0.75);
  });
});

describe("consulta ao VizieR", () => {
  it("cone em VOTable no espelho escolhido", async () => {
    const { vizierConeUrl } = await import("../src/ui/skymap");
    const url = new URL(vizierConeUrl("https://vizier.cfa.harvard.edu", "I/355/gaiadr3", "Source,RA_ICRS", 133.76, -7.2422, 0.1, 4000));
    expect(url.origin + url.pathname).toBe("https://vizier.cfa.harvard.edu/viz-bin/votable");
    expect(url.searchParams.get("-source")).toBe("I/355/gaiadr3");
    expect(url.searchParams.get("-c")).toBe("133.760000 -7.242200");
    expect(url.searchParams.get("-c.rd")).toBe("0.1000");
    expect(url.searchParams.get("-out.max")).toBe("4000");
    expect(url.searchParams.get("-out")).toBe("Source,RA_ICRS");
    expect(url.searchParams.get("-sort")).toBe("_r"); // o limite corta a borda, não o centro
  });
});
