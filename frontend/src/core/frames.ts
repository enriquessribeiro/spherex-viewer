// Quadros do campo: matrizes N x N com a linha 0 = norte (docs/04-api.md §5).

export class Grid {
  readonly n: number;
  readonly values: Float32Array;

  constructor(n: number, values: Float32Array) {
    if (values.length !== n * n) {
      throw new Error(`tamanho ${values.length} não corresponde a uma grade ${n} x ${n}`);
    }
    this.n = n;
    this.values = values;
  }

  /** Valor na (linha, coluna); linha 0 = norte, coluna 0 = leste. */
  at(row: number, col: number): number {
    return this.values[row * this.n + col];
  }
}

export class MaskGrid {
  readonly n: number;
  readonly values: Uint8Array;

  constructor(n: number, values: Uint8Array) {
    if (values.length !== n * n) {
      throw new Error(`tamanho ${values.length} não corresponde a uma grade ${n} x ${n}`);
    }
    this.n = n;
    this.values = values;
  }
}

export const MASK_SATURATED = 1;
export const MASK_LOW_QUALITY = 2;

/** Arquivo .f32: float32 little-endian, N x N, norte na primeira linha. */
export function decodeF32(buffer: ArrayBuffer, n: number): Grid {
  if (buffer.byteLength !== n * n * 4) {
    throw new Error(`tamanho ${buffer.byteLength} bytes não corresponde a uma grade ${n} x ${n} de float32`);
  }
  const view = new DataView(buffer);
  const values = new Float32Array(n * n);
  for (let i = 0; i < values.length; i++) values[i] = view.getFloat32(i * 4, true);
  return new Grid(n, values);
}

/** Arquivo .mask.u8: bit 0 = saturado, bit 1 = baixa qualidade. */
export function decodeMask(buffer: ArrayBuffer, n: number): MaskGrid {
  return new MaskGrid(n, new Uint8Array(buffer.slice(0)));
}
