// Recorte do zoom: fixo no céu, para o movimento do alvo continuar visível.
import { describe, expect, it } from "vitest";
import { cropAnchor, zoomCrop } from "../src/core/crop";

describe("recorte do zoom", () => {
  // WISE 0855: anda ~0,6 px entre épocas
  const epoca1 = { row: 29.0, col: 29.3 }, epoca2 = { row: 28.9, col: 29.9 };

  it("a âncora não depende da época mostrada, então o alvo se desloca dentro do recorte", () => {
    const ancora = cropAnchor(59, [epoca1, epoca2]);
    const crop = zoomCrop(59, 4, ancora);
    const noRecorte = (p: { col: number }) => p.col - crop.x;
    expect(noRecorte(epoca2) - noRecorte(epoca1)).toBeCloseTo(0.6, 6);
  });

  it("âncora no meio das posições previstas; sem alvo, no centro do campo", () => {
    expect(cropAnchor(59, [epoca1, epoca2])).toEqual({ row: 28.95, col: 29.6 });
    expect(cropAnchor(59, [])).toEqual({ row: 29, col: 29 });
  });

  it("zoom 1× mostra a placa inteira; o recorte nunca sai da placa", () => {
    expect(zoomCrop(59, 1, { row: 29, col: 29 })).toEqual({ x: 0, y: 0, w: 59 });
    const canto = zoomCrop(59, 4, { row: 0, col: 58 });
    expect(canto.x).toBeCloseTo(59 - 59 / 4, 9);
    expect(canto.y).toBe(0);
  });
});
