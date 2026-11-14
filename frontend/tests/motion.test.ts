// Busca por nome: o SIMBAD devolve J2000; os campos dos alvos estão na época dos dados.
import { describe, expect, it } from "vitest";
import { propagate } from "../src/core/motion";
import { chooseSource, type Manifest } from "../src/core/source";
import { DEFAULT_STATE } from "../src/core/state";

// WISE 0855 em targets.yaml (SIMBAD, J2000) e o centro do campo publicado (manifest.json).
const WISE_J2000 = { ra: 133.81890825, dec: -7.247048, pmRa: -8123.7, pmDec: 673.2 };
const WISE_CAMPO = { ra: 133.76001995701068, dec: -7.242206991101986 };

describe("movimento próprio", () => {
  it("a posição J2000 do WISE 0855 está ~3,5′ fora do centro do campo", () => {
    const deslocamento = Math.abs(WISE_J2000.ra - WISE_CAMPO.ra) * Math.cos((WISE_CAMPO.dec * Math.PI) / 180) * 60;
    expect(deslocamento).toBeGreaterThan(3); // mais que meio campo de 6′: o alvo ficaria de fora
  });

  it("propagada até a época dos campos, cai no centro publicado (< 0,1″)", () => {
    const p = propagate(WISE_J2000.ra, WISE_J2000.dec, WISE_J2000.pmRa, WISE_J2000.pmDec);
    expect(Math.abs(p.ra - WISE_CAMPO.ra) * 3600).toBeLessThan(0.1);
    expect(Math.abs(p.dec - WISE_CAMPO.dec) * 3600).toBeLessThan(0.1);
  });

  it("e com isso o nome resolvido abre o campo pré-processado do alvo", () => {
    const manifest: Manifest = {
      schema_version: 1, generated_at: "2026-11-14T00:00:00Z",
      targets: [{
        id: "wise0855", name: "WISE 0855-0714", ...WISE_CAMPO, fov_arcmin: 6, default_detector: "D6",
        field: "fields/x/y/field.json", latest_exposure_mjd: 61174, thumbnail: "fields/x/y/frames/4/D6.png",
      }],
    };
    const p = propagate(WISE_J2000.ra, WISE_J2000.dec, WISE_J2000.pmRa, WISE_J2000.pmDec);
    expect(chooseSource({ ...DEFAULT_STATE, ...p }, manifest, "https://api").kind).toBe("static");
  });

  it("RA continua em [0, 360) ao cruzar o zero", () => {
    const p = propagate(0.0001, 0, -100, 0); // -100 mas/ano × ~26 anos ≈ -2,6″
    expect(p.ra).toBeGreaterThan(359.99);
    expect(p.ra).toBeLessThan(360);
  });
});
