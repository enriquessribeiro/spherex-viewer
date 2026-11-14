// Fronteira 5 — renderização, coordenadas e escolha de épocas.
import { describe, expect, it } from "vitest";
import { Grid, MaskGrid, MASK_SATURATED } from "../src/core/frames";
import { renderGray, renderDiff } from "../src/core/render";
import { worldToPixel, type Wcs } from "../src/core/wcs";
import { defaultDiffPair, type EpochLike } from "../src/core/epochs";

const grade = (vs: number[]) => new Grid(Math.sqrt(vs.length), Float32Array.from(vs));
const mascara = (vs: number[]) => new MaskGrid(Math.sqrt(vs.length), Uint8Array.from(vs));
const pixel = (rgba: Uint8ClampedArray, i: number) => Array.from(rgba.slice(i * 4, i * 4 + 4));

describe("renderização (mundo das placas: negativo sobre vidro)", () => {
  const VIDRO = [242, 239, 231, 255], TINTA = [20, 20, 20, 255];
  const LAPIS = [196, 48, 43, 255], AZUL = [43, 76, 156, 255];

  it("negativo (padrão): sem brilho = vidro, brilho máximo = tinta, saturado = tinta, sem dado = vidro", () => {
    const rgba = renderGray(grade([0, 10, NaN, NaN]), mascara([0, 0, 0, MASK_SATURATED]), 0, 10, "linear", true);
    expect(pixel(rgba, 0)).toEqual(VIDRO);
    expect(pixel(rgba, 1)).toEqual(TINTA);
    expect(pixel(rgba, 2)).toEqual(VIDRO);
    expect(pixel(rgba, 3)).toEqual(TINTA); // núcleo saturado: brilho máximo, não buraco
  });

  it("positivo: céu escuro e estrelas claras", () => {
    const rgba = renderGray(grade([0, 10, 0, 10]), null, 0, 10, "linear", false);
    expect(pixel(rgba, 0)).toEqual(TINTA);
    expect(pixel(rgba, 1)).toEqual(VIDRO);
  });

  it("diferença em σ: abaixo de 2σ some (vidro); a partir de 5σ cor cheia; vermelho = apareceu, azul = sumiu", () => {
    const rgba = renderDiff(grade([5, -6, 1.9, NaN]), 2, 5);
    expect(pixel(rgba, 0)).toEqual(LAPIS);
    expect(pixel(rgba, 1)).toEqual(AZUL);
    expect(pixel(rgba, 2)).toEqual(VIDRO); // ruído: o céu parado desaparece
    expect(pixel(rgba, 3)).toEqual(VIDRO);
  });

  it("entre os limites a cor cresce linearmente (3,5σ = metade do caminho)", () => {
    const [r, g, b] = pixel(renderDiff(grade([3.5]), 2, 5), 0);
    expect([r, g, b]).toEqual([219, 144, 137]); // ponto médio entre vidro (242,239,231) e lápis (196,48,43)
  });
});

describe("coordenadas (WCS TAN, norte na primeira linha)", () => {
  // Grade de 59 x 59 do campo do WISE 0855 (field.json real).
  const wcs: Wcs = {
    CTYPE1: "RA---TAN", CTYPE2: "DEC--TAN",
    CRVAL1: 133.79513, CRVAL2: -7.24515, CRPIX1: 30, CRPIX2: 30,
    CDELT1: -6.15 / 3600, CDELT2: 6.15 / 3600,
  };
  const n = 59;

  it("centro do campo cai no pixel central", () => {
    const { row, col } = worldToPixel(wcs, n, 133.79513, -7.24515);
    expect(row).toBeCloseTo(29, 6);
    expect(col).toBeCloseTo(29, 6);
  });

  it("1 pixel a leste = coluna −1; 1 pixel ao norte = linha −1", () => {
    const umPixel = 6.15 / 3600;
    const leste = worldToPixel(wcs, n, 133.79513 + umPixel / Math.cos((-7.24515 * Math.PI) / 180), -7.24515);
    expect(leste.col).toBeCloseTo(28, 3);
    const norte = worldToPixel(wcs, n, 133.79513, -7.24515 + umPixel);
    expect(norte.row).toBeCloseTo(28, 3);
  });
});

describe("épocas padrão da diferença (as de mais sinal)", () => {
  const epoca = (index: number, mjd: number, n?: number): EpochLike => ({
    index, mjd_mid: mjd, frames: n === undefined ? {} : { D6: { n_exposures: n } },
  });

  it("WISE 0855 real em D6 (3, 18, 3, 21 exposições) → épocas 2 e 4", () => {
    const epocas = [epoca(1, 60800, 3), epoca(2, 60990, 18), epoca(3, 61021, 3), epoca(4, 61160, 21)];
    expect(defaultDiffPair(epocas, "D6")).toEqual([2, 4]);
  });

  it("empate no sinal → o par mais afastado no tempo", () => {
    const epocas = [epoca(1, 60900, 18), epoca(3, 61100, 18), epoca(6, 61270, 24), epoca(7, 61300, 1)];
    expect(defaultDiffPair(epocas, "D6")).toEqual([1, 6]);
  });

  it("menos de duas épocas com o detector → null", () => {
    expect(defaultDiffPair([epoca(1, 60800, 5), epoca(2, 60900)], "D6")).toBeNull();
  });
});
