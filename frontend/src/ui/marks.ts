// Marcas de lápis sobre a placa: círculo à mão e seta, como nas placas de Plutão (1930).

/** Círculo levemente irregular, que não fecha exatamente: um traço de lápis, não um círculo de CSS. */
export function pencilCircle(cx: number, cy: number, r: number, seed = 1): string {
  const steps = 28;
  const start = -1.9 + seed * 0.4;
  const sweep = Math.PI * 2 * 1.06; // passa um pouco do início, como um traço feito à mão
  const points: string[] = [];
  for (let i = 0; i <= steps; i++) {
    const a = start + (sweep * i) / steps;
    const wobble = 1 + 0.06 * Math.sin(a * 3 + seed) + 0.03 * Math.sin(a * 7 + seed * 2);
    const rr = r * wobble * (1 + 0.05 * (i / steps)); // espiral leve no fim do traço
    points.push(`${(cx + rr * Math.cos(a)).toFixed(3)} ${(cy + rr * Math.sin(a)).toFixed(3)}`);
  }
  return `M${points[0]} ` + points.slice(1).map((p) => `L${p}`).join(" ");
}

/** Seta curta apontando para (x, y) a partir do canto superior direito. */
export function pencilArrow(x: number, y: number, r: number): { shaft: string; head: string } {
  const len = r * 2.2;
  const dx = Math.SQRT1_2, dy = -Math.SQRT1_2; // vem de cima e da direita
  const tipX = x + dx * r * 1.25, tipY = y + dy * r * 1.25;
  const tailX = tipX + dx * len, tailY = tipY + dy * len;
  const midX = (tipX + tailX) / 2 + r * 0.12, midY = (tipY + tailY) / 2 + r * 0.12;
  const h = r * 0.45;
  const head =
    `M${(tipX + h * (dx + dy * 0.6)).toFixed(3)} ${(tipY + h * (dy - dx * 0.6)).toFixed(3)} ` +
    `L${tipX.toFixed(3)} ${tipY.toFixed(3)} ` +
    `L${(tipX + h * (dx - dy * 0.6)).toFixed(3)} ${(tipY + h * (dy + dx * 0.6)).toFixed(3)}`;
  return {
    shaft: `M${tailX.toFixed(3)} ${tailY.toFixed(3)} Q${midX.toFixed(3)} ${midY.toFixed(3)} ${tipX.toFixed(3)} ${tipY.toFixed(3)}`,
    head,
  };
}
