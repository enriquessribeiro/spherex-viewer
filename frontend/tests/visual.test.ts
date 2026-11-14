// Falsa cor e camada de flags.
import { describe, expect, it } from "vitest";
import { Grid, MaskGrid, MASK_LOW_QUALITY, MASK_SATURATED } from "../src/core/frames";
import { FLAG_TINT, overlayFlags, renderRgb } from "../src/core/render";

const grade = (vs: number[]) => new Grid(Math.sqrt(vs.length), Float32Array.from(vs));
const mascara = (vs: number[]) => new MaskGrid(Math.sqrt(vs.length), Uint8Array.from(vs));
const vidro = [242, 239, 231, 255];

describe("falsa cor", () => {
  it("cada detector num canal, com o próprio contraste; céu escuro", () => {
    const rgba = renderRgb([
      { grid: grade([0, 100, 0, 0]), mask: null, vmin: 0, vmax: 100 },
      { grid: grade([0, 5, 0, 0]), mask: null, vmin: 0, vmax: 10 },
      { grid: grade([0, 0, 0, 0]), mask: null, vmin: 0, vmax: 1 },
    ], "linear", 2);
    expect(Array.from(rgba.slice(0, 8))).toEqual([0, 0, 0, 255, 255, 128, 0, 255]);
  });

  it("detector ausente fica apagado; sem dado fica escuro; saturado acende o canal", () => {
    const rgba = renderRgb([
      { grid: grade([NaN]), mask: mascara([MASK_SATURATED]), vmin: 0, vmax: 1 },
      { grid: null, mask: null, vmin: 0, vmax: 1 },
      { grid: grade([NaN]), mask: null, vmin: 0, vmax: 1 },
    ], "linear", 1);
    expect(Array.from(rgba)).toEqual([255, 0, 0, 255]);
  });
});

describe("camada de flags", () => {
  it("só os pixels marcados mudam, e a contagem sai certa", () => {
    const rgba = new Uint8ClampedArray([...vidro, ...vidro, ...vidro, ...vidro]);
    const marcados = overlayFlags(rgba, mascara([0, MASK_LOW_QUALITY, MASK_SATURATED, 0]));
    expect(marcados).toBe(2);
    expect(Array.from(rgba.slice(0, 4))).toEqual(vidro);
    expect(Array.from(rgba.slice(12, 16))).toEqual(vidro);
    expect(Array.from(rgba.slice(4, 8))).not.toEqual(vidro);
  });

  it("mistura com o manila na opacidade definida", () => {
    const rgba = new Uint8ClampedArray([0, 0, 0, 255]);
    overlayFlags(rgba, mascara([MASK_LOW_QUALITY]));
    expect(Array.from(rgba.slice(0, 3))).toEqual(FLAG_TINT.rgb.map((c) => Math.round(c * FLAG_TINT.alpha)));
  });
});

describe("soma de épocas", () => {
  it("3 épocas de variância 3 viram uma de variância 1; máscaras se juntam", async () => {
    const { sumFrames } = await import("../src/core/combine");
    const epoca = (v: number, m: number) => ({ data: grade([v]), variance: grade([3]), mask: mascara([m]) });
    const soma = sumFrames([epoca(1, 0), epoca(2, MASK_LOW_QUALITY), epoca(3, 0)]);
    expect(soma.data.at(0, 0)).toBe(2);
    expect(soma.variance.at(0, 0)).toBeCloseTo(1, 9);
    expect(soma.mask.values[0]).toBe(MASK_LOW_QUALITY);
  });

  it("saturado numa época só não vira saturado na soma (as outras mediram o pixel)", async () => {
    const { sumFrames } = await import("../src/core/combine");
    const soma = sumFrames([
      { data: grade([NaN]), variance: grade([1]), mask: mascara([MASK_SATURATED]) },
      { data: grade([5]), variance: grade([1]), mask: mascara([0]) },
    ]);
    expect(soma.data.at(0, 0)).toBe(5);
    expect(soma.mask.values[0] & MASK_SATURATED).toBe(0);
    const todas = sumFrames([
      { data: grade([NaN]), variance: grade([1]), mask: mascara([MASK_SATURATED]) },
      { data: grade([NaN]), variance: grade([1]), mask: mascara([MASK_SATURATED]) },
    ]);
    expect(todas.mask.values[0] & MASK_SATURATED).toBe(MASK_SATURATED);
  });
});
