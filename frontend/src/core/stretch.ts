// Esticamento de contraste: valor físico (MJy/sr) → intensidade 0..1.

export type Stretch = "linear" | "asinh" | "log" | "sqrt";

const ASINH_SOFTENING = 10; // mesmo valor do PNG gerado pelo backend
const LOG_SCALE = 1000;

export function normalize(value: number, vmin: number, vmax: number, stretch: Stretch): number {
  if (Number.isNaN(value)) return NaN;
  const t = Math.min(1, Math.max(0, (value - vmin) / Math.max(vmax - vmin, 1e-12)));
  switch (stretch) {
    case "linear":
      return t;
    case "asinh":
      return Math.asinh(ASINH_SOFTENING * t) / Math.asinh(ASINH_SOFTENING);
    case "log":
      return Math.log1p(LOG_SCALE * t) / Math.log1p(LOG_SCALE);
    case "sqrt":
      return Math.sqrt(t);
  }
}
