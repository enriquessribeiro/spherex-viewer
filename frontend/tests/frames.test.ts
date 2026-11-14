// Fronteira 5 — núcleo do frontend: quadros e operações (docs/06-testes.md §2.5).
import { describe, expect, it } from "vitest";
import { decodeF32, decodeMask } from "../src/core/frames";
import { normalize } from "../src/core/stretch";
import { difference, diffScale, weightedMean } from "../src/core/combine";
import { Grid } from "../src/core/frames";

function f32le(values: number[]): ArrayBuffer {
  const view = new DataView(new ArrayBuffer(values.length * 4));
  values.forEach((v, i) => view.setFloat32(i * 4, v, true));
  return view.buffer;
}

describe("decodificação dos quadros", () => {
  it("lê float32 little-endian linha a linha, preservando NaN", () => {
    const quadro = decodeF32(f32le([1, 2, NaN, 4]), 2);
    expect(quadro.n).toBe(2);
    expect(quadro.at(0, 0)).toBe(1); // (linha, coluna); linha 0 = norte
    expect(quadro.at(0, 1)).toBe(2);
    expect(quadro.at(1, 0)).toBeNaN();
    expect(quadro.at(1, 1)).toBe(4);
  });

  it("rejeita arquivo com tamanho que não corresponde à grade", () => {
    expect(() => decodeF32(f32le([1, 2, 3]), 2)).toThrow(/tamanho/);
  });

  it("lê a máscara de 1 byte por pixel", () => {
    const mascara = decodeMask(new Uint8Array([0, 1, 2, 3]).buffer, 2);
    expect(Array.from(mascara.values)).toEqual([0, 1, 2, 3]);
  });
});

describe("esticamento (contraste)", () => {
  it("linear entre vmin e vmax", () => {
    expect(normalize(5, 0, 10, "linear")).toBe(0.5);
    expect(normalize(-3, 0, 10, "linear")).toBe(0);
    expect(normalize(30, 0, 10, "linear")).toBe(1);
  });

  it("asinh realça o fraco mas preserva as pontas", () => {
    expect(normalize(0, 0, 10, "asinh")).toBe(0);
    expect(normalize(10, 0, 10, "asinh")).toBeCloseTo(1, 10);
    expect(normalize(1, 0, 10, "asinh")).toBeGreaterThan(0.1); // 10% do intervalo aparece bem mais que 10%
  });

  it("NaN continua NaN (sem dado)", () => {
    expect(normalize(NaN, 0, 10, "linear")).toBeNaN();
  });
});

describe("operações entre épocas", () => {
  it("diferença é b − a e propaga NaN", () => {
    const a = decodeF32(f32le([1, 2, 1, NaN]), 2);
    const b = decodeF32(f32le([1, 5, NaN, 1]), 2);
    expect(Array.from(difference(a, b).values)).toEqual([0, 3, NaN, NaN]);
  });

  it("média ponderada pelo inverso da variância", () => {
    const um = (v: number) => decodeF32(f32le([v]), 1);
    expect(weightedMean([um(2), um(4)], [um(1), um(1)]).at(0, 0)).toBe(3);
    expect(weightedMean([um(2), um(4)], [um(1), um(3)]).at(0, 0)).toBe(2.5);
  });

  it("média ponderada ignora NaN e só dá NaN se nenhum quadro tiver dado", () => {
    const q = (vs: number[]) => decodeF32(f32le(vs), 1);
    expect(weightedMean([q([NaN]), q([4])], [q([1]), q([1])]).at(0, 0)).toBe(4);
    expect(weightedMean([q([NaN]), q([NaN])], [q([1]), q([1])]).at(0, 0)).toBeNaN();
  });
});

describe("escala da diferença", () => {
  it("vem da própria diferença (percentil 99,5 do valor absoluto), ignorando NaN", () => {
    const d = decodeF32(f32le([1, -2, 3, -4]), 2);
    expect(diffScale(d)).toBe(4);
    const muitos = new Grid(20, Float32Array.from({ length: 400 }, (_, i) => (i % 2 ? -1 : 1) * (i + 1)));
    expect(diffScale(muitos)).toBe(398); // descarta só os 0,5% mais extremos (400 e 399)
  });

  it("diferença nula ou sem dado → escala 1 (evita divisão por zero)", () => {
    expect(diffScale(decodeF32(f32le([0, 0, NaN, NaN]), 2))).toBe(1);
  });
});
