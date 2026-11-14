// Recorte da placa no zoom. O recorte é FIXO no céu para todas as épocas: se ele seguisse o
// alvo época a época, o alvo ficaria parado e as estrelas é que andariam, escondendo o movimento.

export interface PixelPos { row: number; col: number }
export interface Crop { x: number; y: number; w: number }

/** Ponto médio das posições previstas (o alvo passeia em volta dele); sem posições, o centro do campo. */
export function cropAnchor(n: number, positions: PixelPos[]): PixelPos {
  if (positions.length === 0) return { row: (n - 1) / 2, col: (n - 1) / 2 };
  const rows = positions.map((p) => p.row), cols = positions.map((p) => p.col);
  return {
    row: (Math.min(...rows) + Math.max(...rows)) / 2,
    col: (Math.min(...cols) + Math.max(...cols)) / 2,
  };
}

/** Janela quadrada de lado n/zoom centrada na âncora, sem sair da placa. */
export function zoomCrop(n: number, zoom: number, anchor: PixelPos): Crop {
  const w = n / zoom;
  const clamp = (v: number) => Math.min(Math.max(v, 0), n - w);
  return { x: clamp(anchor.col + 0.5 - w / 2), y: clamp(anchor.row + 0.5 - w / 2), w };
}
