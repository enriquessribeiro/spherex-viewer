// Coordenadas digitadas e o caso de teste do desafio (WISE 0855 em sexagesimal).
import { describe, expect, it } from "vitest";
import { parseCoordinates } from "../src/core/coords";
import { nearbyTarget, type MovingTarget } from "../src/core/nearby";

describe("coordenadas digitadas", () => {
  it("o texto do desafio: 08h55m10.831s -07d14m42.53s", () => {
    const c = parseCoordinates("08h55m10.831s -07d14m42.53s")!;
    expect(c.ra).toBeCloseTo(133.795129, 5);
    expect(c.dec).toBeCloseTo(-7.245147, 5);
  });

  it("outras formas sexagesimais e decimais", () => {
    for (const texto of ["08:55:10.831 -07:14:42.53", "08 55 10.831 -07 14 42.53", "08h55m10.831s, -07°14′42.53″"]) {
      expect(parseCoordinates(texto)!.ra).toBeCloseTo(133.795129, 5);
    }
    expect(parseCoordinates("133.76 -7.24")).toEqual({ ra: 133.76, dec: -7.24 });
    expect(parseCoordinates("269.45, 4.69")).toEqual({ ra: 269.45, dec: 4.69 });
    expect(parseCoordinates("+00h00m01s +89d00m00s")).toBeNull(); // RA não aceita sinal
  });

  it("recusa o que não é coordenada", () => {
    for (const texto of ["R Dra", "WISE 0855-0714", "400 10", "10 95", "08h61m00s -07d14m42s"]) {
      expect(parseCoordinates(texto)).toBeNull();
    }
  });
});

describe("coordenada de catálogo → alvo pré-processado", () => {
  // Valores de targets.yaml e do manifest.json publicado.
  const WISE: MovingTarget = {
    id: "wise0855", ra: 133.76001995701068, dec: -7.242206991101986,
    pm_ra_masyr: -8123.7, pm_dec_masyr: 673.2, ref_mjd: 51544.5, field_mjd: 61000,
  };
  const RWAUR: MovingTarget = {
    id: "rwaur", ra: 76.95658631419977, dec: 30.401291980022435,
    pm_ra_masyr: 7.23, pm_dec_masyr: -20.33, ref_mjd: 51544.5, field_mjd: 61000,
  };
  const alvos = [WISE, RWAUR];

  it("a posição do desafio (2010) e a J2000 do WISE 0855 abrem o alvo", () => {
    expect(nearbyTarget(parseCoordinates("08h55m10.831s -07d14m42.53s")!, alvos)?.id).toBe("wise0855");
    expect(nearbyTarget({ ra: 133.81890825, dec: -7.247048 }, alvos)?.id).toBe("wise0855");
  });

  it("um ponto 3′ ao lado de uma estrela quase parada é outro campo", () => {
    expect(nearbyTarget({ ra: RWAUR.ra, dec: RWAUR.dec + 3 / 60 }, alvos)).toBeNull();
    expect(nearbyTarget({ ra: RWAUR.ra, dec: RWAUR.dec + 0.5 / 60 }, alvos)?.id).toBe("rwaur");
  });

  it("longe de tudo, nenhum alvo", () => {
    expect(nearbyTarget({ ra: 10, dec: 41 }, alvos)).toBeNull();
  });
});
