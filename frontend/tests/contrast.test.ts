// Contraste inicial no alvo: o WISE 0855 tem de aparecer.
import { describe, expect, it } from "vitest";
import { Grid } from "../src/core/frames";
import { normalize } from "../src/core/stretch";
import { peakNear, targetLimits } from "../src/core/contrast";

// Valores medidos no campo publicado do WISE 0855 em D6.
const CAMPO = { vmin: -0.0546, vmax: 1.975 };
const WISE = [{ peak: 0.092, snr: 2.2 }, { peak: 0.161, snr: 10.5 }, { peak: 0.238, snr: 7.0 }, { peak: 0.193, snr: 14.6 }];
const ruido = 0.013; // σ por pixel numa época boa (pico 0,193 com S/R 14,6)
const tinta = (v: number, l: { vmin: number; vmax: number }) => normalize(v, l.vmin, l.vmax, "asinh");

describe("contraste inicial no alvo", () => {
  it("antes: o WISE 0855 saía cinza-claro com os limites do campo", () => {
    expect(tinta(0.193, CAMPO)).toBeLessThan(0.4);
  });

  it("agora: o alvo sai quase tinta e o céu continua claro", () => {
    const l = targetLimits(WISE, CAMPO)!;
    expect(tinta(0.193, l)).toBeGreaterThan(0.85);
    expect(tinta(0, l)).toBe(0); // céu vazio = vidro
    expect(tinta(ruido, l)).toBeLessThan(0.25); // 1σ de ruído fica bem mais claro que o alvo
  });

  it("época de S/R baixo não decide o contraste (ruído não vira alvo)", () => {
    expect(targetLimits([{ peak: 1.5, snr: 2 }], CAMPO)).toBeNull();
  });

  it("alvo que já é o mais brilhante (R Dra, Barnard) fica com os limites do campo", () => {
    expect(targetLimits([{ peak: 1.9, snr: 900 }], CAMPO)).toBeNull();
  });

  it("pico na caixa 3×3 em volta da posição prevista", () => {
    const dado = new Grid(4, Float32Array.from([0, 0, 0, 0, 0, 1, 2, 0, 0, 0, 9, 0, 0, 0, 0, 50]));
    const variancia = new Grid(4, new Float32Array(16).fill(4));
    expect(peakNear(dado, variancia, 1.2, 1.4)).toEqual({ peak: 9, snr: 4.5 }); // 50 fica fora da caixa
  });
});
