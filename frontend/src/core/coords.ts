// Coordenadas digitadas pelo usuário, interpretadas no navegador (sem depender da API).
// O próprio desafio dá o WISE 0855 em sexagesimal: "08h55m10.831s -07d14m42.53s".

export interface RaDec { ra: number; dec: number }

const NUM = String.raw`[+-]?\d+(?:\.\d*)?`;
const DECIMAL = new RegExp(String.raw`^\s*(${NUM})\s*[,\s]\s*(${NUM})\s*$`);
// 08h55m10.831s -07d14m42.53s | 08:55:10.8 -07:14:42.5 | 08 55 10.8 -07 14 42.5 (também com °, ′, ″)
const SEXAGESIMAL = new RegExp(
  String.raw`^\s*(\d{1,2})\s*[h:\s]\s*(\d{1,2})\s*[m:\s]\s*(\d{1,2}(?:\.\d*)?)\s*s?\s*,?\s*` +
  String.raw`([+-]?)\s*(\d{1,2})\s*[d°:\s]\s*(\d{1,2})\s*['′m:\s]\s*(\d{1,2}(?:\.\d*)?)\s*(?:["″s]|'')?\s*$`,
  "i",
);

/** RA/Dec em graus decimais ou sexagesimal (RA em horas); null se não for coordenada válida. */
export function parseCoordinates(text: string): RaDec | null {
  let ra: number, dec: number;
  const d = text.match(DECIMAL);
  const s = d ? null : text.match(SEXAGESIMAL);
  if (d) {
    ra = Number(d[1]);
    dec = Number(d[2]);
  } else if (s) {
    const [h, m, sec, sign, dd, dm, ds] = [+s[1], +s[2], +s[3], s[4], +s[5], +s[6], +s[7]];
    if (m >= 60 || sec >= 60 || dm >= 60 || ds >= 60) return null;
    ra = (h + m / 60 + sec / 3600) * 15;
    dec = (sign === "-" ? -1 : 1) * (dd + dm / 60 + ds / 3600);
  } else {
    return null;
  }
  if (!(ra >= 0 && ra < 360 && dec >= -90 && dec <= 90)) return null;
  return { ra, dec };
}
