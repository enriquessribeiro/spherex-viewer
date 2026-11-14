// Espectro: mediana por caixas, eixo e aviso de vizinha.
import { describe, expect, it } from "vitest";
import { binnedMedian, contaminatedDetectors, medianSegments, fluxRange, niceTicks, type SpectrumDoc, type SpectrumPoint } from "../src/core/spectrum";

const ponto = (wavelength: number, flux: number, flux_err = 1): SpectrumPoint => ({
  wavelength, flux, flux_err, bandwidth: 0.03, det: "D6", epoch: 1, mjd: 60800, exposure_id: "x", flagged: false,
});

describe("espectro", () => {
  it("mediana por caixas de λ/40: o ruído de uma exposição não vira linha", () => {
    const pts = [ponto(4.50, 10), ponto(4.51, 30), ponto(4.52, 20), ponto(4.70, 99)];
    expect(binnedMedian(pts)).toEqual([{ wavelength: 4.51, flux: 20, n: 3 }]); // 4,70 fica sozinho na caixa dele: fora
  });

  it("a linha da mediana para onde faltam medidas (lacuna em D4 na ε Indi B)", () => {
    const caixas = [2.6, 2.665, 2.73, 3.6, 3.69].map((wavelength) => ({ wavelength }));
    expect(medianSegments(caixas).map((s) => s.map((b) => b.wavelength))).toEqual([[2.6, 2.665, 2.73], [3.6, 3.69]]);
  });

  it("marcas redondas no eixo", () => {
    expect(niceTicks(0, 1000, 5)).toEqual([0, 200, 400, 600, 800, 1000]);
    expect(niceTicks(-37, 610, 5)).toEqual([0, 200, 400, 600]);
  });

  it("faixa do fluxo inclui o zero e ignora um ponto absurdo", () => {
    const pts = Array.from({ length: 100 }, (_, i) => ponto(1 + i * 0.04, 100 + (i % 5), 5));
    pts.push(ponto(3, 1e6, 5));
    const [lo, hi] = fluxRange(pts);
    expect(lo).toBe(0);
    expect(hi).toBeLessThan(200);
  });

  it("detectores contaminados por vizinha, sem repetir", () => {
    const doc = { neighbors: [{ detector: "D2", distance_arcsec: 8.9, snr: 56 }, { detector: "D1", distance_arcsec: 8.9, snr: 58 }] } as SpectrumDoc;
    expect(contaminatedDetectors(doc)).toEqual(["D1", "D2"]);
  });
});
