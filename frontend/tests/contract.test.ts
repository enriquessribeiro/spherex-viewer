// Fronteira 4 — o frontend lê o formato que o backend grava (schemas/ + fixture gerada pelo backend).
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { decodeF32, decodeMask } from "../src/core/frames";
import type { FieldDoc } from "../src/core/types";
import { worldToPixel } from "../src/core/wcs";

const aqui = dirname(fileURLToPath(import.meta.url));
const raizFixture = join(aqui, "fixtures", "fields", "133.7951-7.2451_1", "2ef8b07e03b6");
const esquema = JSON.parse(readFileSync(join(aqui, "..", "..", "schemas", "field.schema.json"), "utf8"));
const campo: FieldDoc = JSON.parse(readFileSync(join(raizFixture, "field.json"), "utf8"));
const buffer = (rel: string) => {
  const b = readFileSync(join(raizFixture, rel));
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) as ArrayBuffer;
};

describe("contrato de dados", () => {
  it("field.json gravado pelo backend é válido no esquema", () => {
    const ajv = new Ajv2020({ allErrors: true });
    addFormats(ajv);
    const valido = ajv.validate(esquema, campo);
    expect(ajv.errors ?? []).toEqual([]);
    expect(valido).toBe(true);
  });

  it("quadros e máscaras do backend são lidos com a grade do field.json", () => {
    const n = campo.grid.n;
    for (const epoca of campo.epochs) {
      for (const quadro of Object.values(epoca.frames)) {
        expect(decodeF32(buffer(quadro.frame), n).n).toBe(n);
        expect(decodeF32(buffer(quadro.variance), n).n).toBe(n);
        expect(decodeMask(buffer(quadro.mask), n).n).toBe(n);
      }
    }
  });

  it("a fonte plantada aparece onde o WCS do field.json prevê, nas duas épocas", () => {
    const n = campo.grid.n;
    for (const [i, epoca] of campo.epochs.entries()) {
      const q = decodeF32(buffer(epoca.frames.D6.frame), n);
      let max = -Infinity, arg = -1;
      q.values.forEach((v, k) => { if (v > max) { max = v; arg = k; } });
      // Centroide 5x5 em volta do pico (o pico sozinho é ambíguo quando a fonte cai entre pixels;
      // uma janela 3x3 corta a gaussiana e puxa o centroide ~0,3 px para o centro da janela).
      const r0 = Math.floor(arg / n), c0 = arg % n;
      let soma = 0, sr = 0, sc = 0;
      for (let dr = -2; dr <= 2; dr++) for (let dc = -2; dc <= 2; dc++) {
        const v = Math.max(0, q.at(r0 + dr, c0 + dc) || 0);
        soma += v; sr += v * (r0 + dr); sc += v * (c0 + dc);
      }
      const prevista = campo.target!.predicted_positions[i];
      const { row, col } = worldToPixel(campo.grid.wcs, n, prevista.ra, prevista.dec);
      expect(Math.abs(sr / soma - row)).toBeLessThan(0.15);
      expect(Math.abs(sc / soma - col)).toBeLessThan(0.15);
    }
  });
});
